import time


class Job(object):

    def __init__(self, period: int, ghost: bool = False):
        self._period = period
        self._ghost = ghost
        self._terminated = False
        self._last_executed = 0

    def is_executable(self):
        if self.is_terminated():
            return False
        elapsed_since_last = time.time() - self._last_executed
        return elapsed_since_last >= self._period

    def is_ghost(self):
        return self._ghost

    def is_terminated(self):
        return self._terminated

    def execute(self):
        self.run()
        self._last_executed = time.time()

    def terminate(self):
        self._terminated = True

    def run(self):
        pass

    def reset(self):
        pass

    def __str__(self):
        return type(self).__name__
