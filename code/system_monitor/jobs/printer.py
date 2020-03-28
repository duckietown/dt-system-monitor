from .jobs import Job
from system_monitor.constants import \
    VERBOSE_PRINT_STATUS_EVERY_S


class PrinterJob(Job):

    def __init__(self, app: 'SystemMonitor'):
        super().__init__(period=VERBOSE_PRINT_STATUS_EVERY_S, ghost=True)
        self._app = app

    def run(self):
        print(self._get_status())

    def _get_status(self):
        stats = self._app.get_progress()
        return ("[{:s} {:02d}h:{:02d}m:{:02d}s] [{:s}] [{:d}/{:d} jobs] " +
                "[{:d} queued] [{:d} failed] [log: {:s}]").format(
            self._app.name(),
            *self._time(),
            str(stats['app_status']),
            stats['jobs_max'] - stats['jobs_idle'],
            stats['jobs_max'],
            stats['tasks_queued'],
            stats['tasks_failed'],
            stats['log_size']
        )

    def _time(self):
        return (
            int(self._app.uptime() / 3600),
            int(self._app.uptime() / 60) % 60,
            int(self._app.uptime()) % 60
        )
