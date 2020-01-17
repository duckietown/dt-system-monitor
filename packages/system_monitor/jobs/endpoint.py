from docker import DockerClient
from docker.errors import APIError
from .jobs import Job
from system_monitor.constants import \
    FETCH_NEW_CONTAINER_STATS_EVERY_S


class EndpointInfoJob(Job):

    def __init__(self, app: 'SystemMonitor', client: DockerClient):
        super().__init__(period=FETCH_NEW_CONTAINER_STATS_EVERY_S)
        self._app = app
        self._client = client

    def run(self):
        # try to get the info about the Docker endpoint
        try:
            data = self._client.info()
            # update log
            self._app.extend_log('endpoint', data)
            # terminate on success
            self.terminate()
        except APIError:
            return
