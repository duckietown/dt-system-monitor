import time
from docker import DockerClient
from docker.models.containers import Container
from docker.errors import APIError
from collections import defaultdict

from .jobs import Job
from .process import ProcessStatsJob
from system_monitor.constants import \
    FETCH_NEW_CONTAINER_STATS_EVERY_S, \
    FETCH_NEW_CONTAINERS_EVERY_S, \
    JOB_FETCH_CONTAINER_STATS, \
    JOB_FETCH_CONTAINER_TOP, \
    JOB_FETCH_CONTAINER_CONFIG


PS_COLUMN_TO_KEY = {
    'PPID': 'ppid',
    'PID': 'pid',
    '%CPU': 'pcpu',
    'THCNT': 'nthreads',
    'TIME': 'cputime',
    '%MEM': 'pmem',
    'SIZE': 'mem',
    'CMD': 'command'
}


class ContainerStatsJob(Job):

    def __init__(self, app: 'SystemMonitor', container: Container):
        super().__init__(period=FETCH_NEW_CONTAINER_STATS_EVERY_S)
        self._app = app
        self._container = container
        self._previous_cpu = 0.0
        self._previous_system = 0.0
        self._stream = None

    def run(self):
        data = {
            'container': self._container.id,
            'time': time.time(),
            'pcpu': 0.0,
            'io_r': 0.0,
            'io_w': 0.0,
            'mem': 0.0,
            'pmem': 0.0
        }
        # check if the container is still running
        if self._container.status != 'running':
            self.terminate()
        # try to get a new reading
        try:
            if not self._stream:
                self._stream = self._container.stats(decode=True, stream=True)
            # get another reading
            stats = next(self._stream)
            # fill in the data
            data['pcpu'] = self._calculate_cpu_percent(stats)
            data['io_r'], data['io_w'] = self._calculate_blkio_bytes(stats)
            data['mem'] = self._calculate_mem_bytes(stats)
            data['pmem'] = self._calculate_mem_perc(stats)
        except APIError:
            return
        # update log
        self._app.extend_log('container/stats', [data])

    def _calculate_cpu_percent(self, stats):
        cpu_percent = 0.0
        try:
            cpu_total = float(stats["cpu_stats"]["cpu_usage"]["total_usage"])
            cpu_delta = cpu_total - self._previous_cpu
            cpu_system = float(stats["cpu_stats"]["system_cpu_usage"])
            system_delta = cpu_system - self._previous_system
            online_cpus = stats["cpu_stats"].get(
                "online_cpus", len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
            )
            if system_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
            self._previous_cpu = cpu_total
            self._previous_system = cpu_system
        except KeyError as e:
            self._app.logger.error('{}:Container[{}]:KeyError {}'.format(
                type(self).__name__, self._container.id, str(e)
            ))
        finally:
            return cpu_percent

    def _calculate_blkio_bytes(self, stats):
        r = w = 0
        try:
            if 'blkio_stats' in stats and 'io_service_bytes_recursive' in stats['blkio_stats']:
                bytes_stats = stats['blkio_stats']['io_service_bytes_recursive']
                for s in bytes_stats:
                    if s["op"] == "Read":
                        r += s["value"]
                    elif s["op"] == "Write":
                        w += s["value"]
        except Exception as e:
            self._app.logger.error('{}:Container[{}]:Error {}'.format(
                type(self).__name__, self._container.id, str(e)
            ))
        finally:
            return r, w

    def _calculate_mem_bytes(self, stats):
        mem_bytes = 0.0
        try:
            mem_bytes = stats['memory_stats']['usage'] - stats['memory_stats']['stats']['cache']
        finally:
            return mem_bytes

    def _calculate_mem_perc(self, stats):
        mem_perc = 0.0
        try:
            if stats['memory_stats']['limit'] > 0:
                usage_bytes = self._calculate_mem_bytes(stats)
                total_bytes = stats['memory_stats']['limit']
                mem_perc = (usage_bytes / total_bytes) * 100.0
        finally:
            return mem_perc


class ContainerConfigJob(Job):

    def __init__(self, app: 'SystemMonitor', client: DockerClient, container_id: str):
        super().__init__(period=FETCH_NEW_CONTAINER_STATS_EVERY_S)
        self._app = app
        self._client = client
        self._container_id = container_id

    def run(self):
        # try to get the container configuration
        try:
            config = self._client.api.inspect_container(self._container_id)
            # update log
            self._app.extend_log(
                'container/config',
                {self._container_id: config}
            )
            # once it succeded, we no longer need to perform this job again
            self.terminate()
        except APIError:
            return


class ContainerListJob(Job):

    def __init__(self, app: 'SystemMonitor', client: DockerClient):
        super().__init__(period=FETCH_NEW_CONTAINERS_EVERY_S)
        self._app = app
        self._client = client
        self._container_to_job = defaultdict(lambda: [])
        self._containers_seen = set()

    def run(self):
        data = {
            'containers': {},
            'events': []
        }
        now = time.time()
        containers = self._client.containers.list()
        containers_keys = set([c.id for c in containers])
        # remove old containers
        for container_id in list(self._containers_seen):
            if container_id not in containers_keys:
                data['events'].append({
                    'time': now,
                    'type': 'container/remove',
                    'id': container_id
                })
                # deactivate corresponding jobs
                for j in self._container_to_job[container_id]:
                    j.terminate()
                # remove container
                self._containers_seen.remove(container_id)
                del self._container_to_job[container_id]
        for container in containers:
            # add new containers
            if container.id not in self._containers_seen:
                data['events'].append({
                    'time': now,
                    'type': 'container/add',
                    'id': container.id
                })
                data['containers'][container.id] = container.name
                # spawn new jobs
                if JOB_FETCH_CONTAINER_STATS:
                    job = ContainerStatsJob(self._app, container)
                    self._container_to_job[container.id].append(job)
                if JOB_FETCH_CONTAINER_TOP:
                    job = ProcessStatsJob(self._app, container)
                    self._container_to_job[container.id].append(job)
                if JOB_FETCH_CONTAINER_CONFIG:
                    job = ContainerConfigJob(self._app, self._client, container.id)
                    self._container_to_job[container.id].append(job)
                # start jobs
                for job in self._container_to_job[container.id]:
                    self._app.pool.enqueue(job)
                # add container to list of seen
                self._containers_seen.add(container.id)
        # update log
        for k, v in data.items():
            self._app.extend_log(k, v)

