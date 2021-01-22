import time
import subprocess

from .jobs import Job
from system_monitor.constants import FETCH_NEW_SYSTEM_PROCESS_STATS_EVERY_S


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


class SystemProcessStatsJob(Job):

    def __init__(self, app: 'SystemMonitor'):
        super().__init__(period=FETCH_NEW_SYSTEM_PROCESS_STATS_EVERY_S)
        self._app = app

    def run(self):
        data = []
        template = {
            'container': None,
            'time': time.time()
        }
        # try to get a new reading
        output = subprocess.check_output([
            'ps', '-o', 'ppid,pid,pcpu,thcount,cputime,pmem,size,pgrp,cmd', '-axww'
        ]).decode('utf-8').splitlines(keepends=False)
        header = [h for h in ' '.join(output[0].strip().split()).split() if h]
        raw_data = map(lambda s: s.strip().split(None, len(header) - 1), output[1:])
        processes = [dict(zip(header, row)) for row in raw_data]
        for process in processes:
            # fix size KB -> B
            process['SIZE'] = int(process['SIZE']) / 1000
            # keep only non-kernel processes
            if process['PGRP'] == '0':
                continue
            del process['PGRP']
            # translate fields
            process = {PS_COLUMN_TO_KEY[k]: v for k, v in process.items()}
            # fill in the data
            process.update(template)
            # add process
            data.append(process)
        # update log
        self._app.extend_log('all_process_stats', data)
