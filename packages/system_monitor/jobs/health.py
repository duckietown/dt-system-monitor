import time
import requests

from .jobs import Job
from system_monitor.constants import \
    FETCH_NEW_DEVICE_STATS_EVERY_S, \
    DEFAULT_DEVICE_HEALTH_API_PORT


class DeviceHealthJob(Job):

    def __init__(self, app: 'SystemMonitor', target: str):
        super().__init__(period=FETCH_NEW_DEVICE_STATS_EVERY_S)
        self._app = app
        self._url = _device_health_url(target)

    def run(self):
        try:
            # contact device health API
            r = requests.get(self._url)
            data = r.json()
            data['time'] = time.time()
            # send the data to the log
            self._app.extend_log('health', [data])
        except:
            return


def _device_health_url(target: str):
    hostname = 'localhost'
    if not target.startswith('unix:'):
        hostname = target
    return 'http://{:s}:{:d}/'.format(hostname, DEFAULT_DEVICE_HEALTH_API_PORT)
