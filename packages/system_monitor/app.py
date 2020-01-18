import sys
import time
import copy
import logging
import traceback
import threading
import docker
import socket
import datetime

from dt_class_utils import DTProcess
from dt_class_utils import AppStatus

from typing import Iterable, Union, Dict

from .pool import Pool
from .jobs import PrinterJob, ContainerListJob, DeviceHealthJob, PublisherJob, EndpointInfoJob
from .constants import \
    APP_NAME, \
    WORKERS_NUM, \
    APP_HEARTBEAT_HZ, \
    DEFAULT_DOCKER_TCP_PORT, \
    JOB_FETCH_CONTAINER_LIST, \
    JOB_FETCH_DEVICE_HEALTH, \
    JOB_PUSH_TO_SERVER, \
    JOB_FETCH_ENDPOINT_INFO, \
    LOG_VERSION


class SystemMonitor(DTProcess):

    def __init__(self, args):
        super(SystemMonitor, self).__init__(APP_NAME)
        self.args = args
        self._start_time = time.time()
        self._start_time_iso = _iso_now()
        self._lock = threading.Semaphore(1)
        self._log = {
            'time': self._start_time_iso,
            'version': LOG_VERSION,
            'group': self.args.group,
            'type': self.args.type.lower(),
            'target': self.get_target_name(),
            'duration': self.args.duration
        }
        self._log_size = sys.getsizeof(self._log)
        # ---
        # configure logger
        if self.args.debug:
            self.logger.setLevel(logging.DEBUG)
        # setup shutdown procedure
        self.register_shutdown_callback(self._clean_shutdown)
        # create workers pool
        self.pool = Pool(WORKERS_NUM, self._exception_handler)
        # print configuration
        print("""
System-Monitor
-- Configuration --------------------------
Target: {target:s}
Target Type: {type:s}
Target Name: {target_name:s}
Log Version: {log_version:s}
Log Database: {database:s}
Log Group: {group:s}
Log duration: {duration:d} secs
Log ID: {key:s}
-------------------------------------------
        """.format(
            **self.args.__dict__,
            key=self.get_log_key(),
            target_name=self.get_target_name(),
            log_version=str(LOG_VERSION)
        ))

    def start(self):
        self.logger.info('Started logging...')
        # add printer job (if needed)
        if self.args.verbose:
            self.pool.enqueue(PrinterJob(self))
        # initialize docker client
        client = docker.DockerClient(base_url=_base_url(self.args))
        # create endpoint info job
        if JOB_FETCH_ENDPOINT_INFO:
            self.pool.enqueue(EndpointInfoJob(self, client))
        # create container updater job
        if JOB_FETCH_CONTAINER_LIST:
            self.pool.enqueue(ContainerListJob(self, client))
        # create device health job
        if JOB_FETCH_DEVICE_HEALTH:
            self.pool.enqueue(DeviceHealthJob(self, self.args.target))
        # start pool
        self.pool.run()
        # spin the app
        while not self.is_done():
            # breath
            time.sleep(1.0 / APP_HEARTBEAT_HZ)
        self.logger.info('The monitor timed out. Clearing jobs...')
        # remove all jobs from the queue
        self.pool.terminate_all()
        self.logger.info('Jobs cleared')
        # send log to server
        if not self.is_shutdown() and JOB_PUSH_TO_SERVER:
            self.logger.info('Collecting logged data')
            self.pool.enqueue(PublisherJob(self, self.get_log_key(), self.get_log()))
            self.logger.info('Pushing data to the cloud')
            self.pool.join()
        # initiate shutdown (if nobody else requested it already)
        self.logger.info('Stopping workers...')
        if not self.is_shutdown():
            self.shutdown()
        self.pool.abort()
        self.logger.info('Workers stopped!')
        # update status bar one more time and then stop it
        # ---
        self.logger.info('Done!')

    def extend_log(self, key: str, value: Union[Iterable, Dict]):
        self._lock.acquire()
        # create list/dict if not present
        if key not in self._log:
            self._log[key] = [] if isinstance(value, list) else {}
        # handle type mismatch
        if type(self._log[key]) != type(value):
            self._lock.release()
            raise ValueError('Cannot extend a log of type {} with an object of type {}'.format(
                type(self._log[key]), type(value)
            ))
        # handle lists:
        if isinstance(value, list):
            self._log[key].extend(value)
        if isinstance(value, dict):
            self._log[key].update(value)
        # update size
        self._log_size += _get_size(value)
        # release lock
        self._lock.release()


    def is_done(self):
        return 0 < self.args.duration < self.uptime()

    def _clean_shutdown(self):
        self.pool.abort(block=True)

    def get_progress(self):
        stats = self.pool.get_stats()
        stats['app_status'] = {
            AppStatus.INITIALIZING: 'init',
            AppStatus.RUNNING: 'healthy',
            AppStatus.TERMINATING: 'stop',
            AppStatus.KILLING: 'kill',
            AppStatus.DONE: 'done'
        }[self.status()]
        stats['log_size'] = _sizeof_fmt(self._log_size)
        return stats

    def get_log(self):
        self._lock.acquire()
        # return a copy
        log = copy.deepcopy(self._log)
        # release lock
        self._lock.release()
        # ---
        return log

    def get_log_key(self):
        return 'v{}__{}__{}__{}__{:d}'.format(
            LOG_VERSION,
            self.args.group,
            self.args.type.lower(),
            self.get_target_name(),
            int(self._start_time)
        )

    def get_target_name(self):
        target = socket.gethostname() if self.args.target.startswith('unix:') else self.args.target
        target, *_ = target.split(':')
        target = target.rstrip('.local')
        return target.lower()

    def _exception_handler(self, exception_type, exception, tback):
        self.pool.stats.increase('tasks_failed')
        traceback.print_exception(exception_type, exception, tback, file=sys.stderr)


def _base_url(args):
    if args.target.startswith('unix:'):
        return args.target
    else:
        hostname, port, *_ = (args.target + ':' + DEFAULT_DOCKER_TCP_PORT).split(':')
        return 'tcp://{:s}:{:d}'.format(args.target, port)


def _sizeof_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.2f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.2f%s%s" % (num, 'Yi', suffix)


def _get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([_get_size(v, seen) for v in obj.values()])
        size += sum([_get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += _get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([_get_size(i, seen) for i in obj])
    return size


def _iso_now():
    return datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc
    ).astimezone().replace(microsecond=0).isoformat()
