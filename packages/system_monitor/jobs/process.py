import time
import copy
from docker.models.containers import Container
from docker.errors import APIError

from .jobs import Job
from system_monitor.constants import FETCH_NEW_PROCESS_STATS_EVERY_S


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


class ProcessStatsJob(Job):

    def __init__(self, app: 'SystemMonitor', container: Container):
        super().__init__(period=FETCH_NEW_PROCESS_STATS_EVERY_S)
        self._app = app
        self._container = container

    def run(self):
        data = []
        template = {
            'container': self._container.id,
            'time': time.time()
        }
        # check if the container is still running
        if self._container.status != 'running':
            self.terminate()
        # try to get a new reading
        try:
            stats = self._container.top(
                ps_args='-o ppid,pid,pcpu,thcount,cputime,pmem,size,cmd'
            )
            if not stats['Processes'] or not stats['Titles']:
                return
            for process in stats['Processes']:
                # fix size KB -> B
                process[-2] = int(process[-2]) / 1000
                # fill in the data
                pdata = copy.copy(template)
                for ps_key, value in zip(stats['Titles'], process):
                    key = PS_COLUMN_TO_KEY[ps_key]
                    pdata[key] = value
                # add process
                data.append(pdata)
        except APIError:
            return
        # update log
        self._app.extend_log('process_stats', data)
