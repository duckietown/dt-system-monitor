import time
import psutil

from .jobs import Job
from system_monitor.constants import \
    FETCH_NEW_DEVICE_RESOURCES_STATS_EVERY_S


class DeviceResourcesJob(Job):

    def __init__(self, app: 'SystemMonitor'):
        super().__init__(period=FETCH_NEW_DEVICE_RESOURCES_STATS_EVERY_S)
        self._app = app

    def run(self):
        try:
            mem_stats = psutil.virtual_memory()
            swap_stats = psutil.swap_memory()
            # get system resources status
            data = {
                'time': time.time(),
                'memory': {
                    'pmem': mem_stats.percent,
                    'total': mem_stats.total,
                    'used': mem_stats.used,
                    'free': mem_stats.available
                },
                'swap': {
                    'pswap': swap_stats.percent,
                    'total': swap_stats.total,
                    'used': swap_stats.used,
                    'free': swap_stats.free
                },
                'cpu': {
                    'pcpu': psutil.cpu_percent()
                }
            }
            # send the data to the log
            self._app.extend_log('resources_stats', [data])
        except:
            return
