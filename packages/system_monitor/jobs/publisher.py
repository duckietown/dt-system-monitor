import sys
import json
import requests

from typing import Dict

from .jobs import Job
from system_monitor.constants import \
    LOG_API_URL, \
    LOG_API_RETRY_EVERY_S, \
    LOG_API_RETRY_N_TIMES, \
    LOG_API_REQUEST_TIMEOUT_S


class PublisherJob(Job):

    def __init__(self, app: 'SystemMonitor', log_key: str, log: Dict):
        super().__init__(period=LOG_API_RETRY_EVERY_S)
        self._app = app
        self._log_key = log_key
        self._data = log
        self._trial = 0

    def run(self):
        if self._trial >= LOG_API_RETRY_N_TIMES:
            msg = 'We tried pushing the log to the cloud {} times. Giving up.'.format(self._trial)
            self._app.logger.info(msg)
            self.terminate()
            return
        self._app.logger.info('Pushing to the server [trial {:d}/{:d}]...'.format(
            self._trial+1, LOG_API_RETRY_N_TIMES
        ))
        try:
            # create request body
            data = {
                'app_id': self._app.args.app_id,
                'app_secret': self._app.args.app_secret,
                'database': self._app.args.database,
                'key': self._log_key,
                'value': json.dumps(self._data)
            }
            # contact log API
            r = requests.post(
                LOG_API_URL,
                data=data,
                timeout=LOG_API_REQUEST_TIMEOUT_S
            )
            # print(json.dumps(data, indent=4))
            server_msg = lambda r: 'The server says: [{}] {}'.format(r['code'], r['message'] or r['status'])
            # try to interpret the error message from the server
            try:
                data = r.json()
                if data['code'] != 200:
                    self._app.logger.error(server_msg(data))
                else:
                    self._app.logger.info(server_msg(data))
            except:
                # print the response in plain
                self._app.logger.error(r.text)
            # stop job
            self.terminate()
        except:
            ex_type, ex, _ = sys.exc_info()
            self._app.logger.error('{}: {}'.format(ex_type, ex))
            # traceback.print_exception(ex_type, ex, tb, file=sys.stderr)
        finally:
            self._trial += 1

