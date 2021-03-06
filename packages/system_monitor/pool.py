import sys
import time

from queue import Queue, Empty
from threading import Thread, Event, Semaphore
from collections import defaultdict
from copy import copy

from .constants import WORKER_HEARTBEAT_HZ


class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""

    def __init__(self, name, logger, pool, abort, idle):
        Thread.__init__(self)
        self.name = name
        self.logger = logger
        self.pool = pool
        self.queue = pool.queue
        self.results = pool.results
        self.abort = abort
        self.idle = idle
        self.exception_handler = pool.exception_handler
        self.stats = pool.stats
        self.daemon = True
        self.start()

    """Thread work loop calling the function with the params"""

    def run(self):
        # keep running until told to abort
        while not self.abort.is_set():
            try:
                # get a task and raise immediately if none available
                job = self.queue.get(block=False)
                if not job.is_executable():
                    if not job.is_terminated():
                        self.pool.enqueue(job)
                    else:
                        self.logger.debug(
                            'Job [{:s}] was found terminated in the queue.'.format(str(job))
                        )
                    self.queue.task_done()
                    time.sleep(1.0 / WORKER_HEARTBEAT_HZ)
                    continue
                # job = self.queue.get(block=False)
                self.idle.clear()
            except Empty:
                # no work to do
                self.idle.set()
                time.sleep(1.0 / WORKER_HEARTBEAT_HZ)
                continue
            except:
                ex_type, ex, tb = sys.exc_info()
                self.exception_handler(ex_type, ex, tb)
                time.sleep(1.0 / WORKER_HEARTBEAT_HZ)
                continue

            try:
                # the function may raise
                result = job.execute()
                if result is not None:
                    self.results.put(result)
            except:
                ex_type, ex, tb = sys.exc_info()
                self.exception_handler(ex_type, ex, tb)
            finally:
                if not job.is_terminated():
                    # reset job and put back in the queue
                    job.reset()
                    self.pool.enqueue(job)
                else:
                    self.logger.debug(
                        'Job [{:s}] was found terminated in the queue.'.format(str(job))
                    )
                # task complete no matter what happened
                self.queue.task_done()


class Pool:
    """Pool of threads consuming tasks from a queue"""

    def __init__(self, logger, thread_count, exception_handler):
        self.logger = logger
        self.queue = Queue()
        self.resultQueue = Queue()
        self.thread_count = thread_count
        self.exception_handler = exception_handler
        self.stats = StatisticsCollector()
        self.aborts = []
        self.idles = []
        self.threads = []
        self._black_hole = False

    """Tell my threads to quit"""

    def __del__(self):
        self.abort()

    """Start the threads, or restart them if you've aborted"""

    def run(self, block=False):
        # either wait for them to finish or return false if some arent
        if block:
            while self.alive():
                time.sleep(1)
        elif self.alive():
            return False

        # go start them
        self.aborts = []
        self.idles = []
        self.threads = []
        for n in range(self.thread_count):
            abort = Event()
            idle = Event()
            self.aborts.append(abort)
            self.idles.append(idle)
            self.threads.append(Worker('thread-%d' % n, self.logger, self, abort, idle))
        return True

    def black_hole(self, val):
        self._black_hole = val

    """Add a task to the queue"""

    def enqueue(self, job):
        if self._black_hole:
            self.logger.debug(
                'Job [{:s}] went down the black hole.'.format(str(job))
            )
            return
        self.queue.put(job)

    """Wait for completion of all the tasks in the queue"""

    def join(self):
        self.logger.debug('Joining the pool with {:d} uncompleted jobs'.format(self.queue.qsize()))
        self.queue.join()

    """Remove all jobs that are in the queue and wait for those grabbed by the threads"""

    def terminate_all(self):
        # clear the queue
        while not self.done():
            try:
                job = self.queue.get(False)
                self.queue.task_done()
                self.logger.debug(
                    'Job [{:s}] was found in the queue. Now terminated.'.format(
                        str(job)
                    )
                )
            except:
                pass
            time.sleep(0.1)

    """Tell each worker that its done working"""

    def abort(self, block=False):
        # tell the threads to stop after they are done with what they are currently doing
        for a in self.aborts:
            a.set()
        # clear the queue
        self.terminate_all()
        # wait for them to finish if requested
        while block and self.alive():
            time.sleep(1)

    """Returns True if any threads are currently running"""

    def alive(self):
        return True in [t.is_alive() for t in self.threads]

    """Returns True if all threads are waiting for work"""

    def idle(self):
        return False not in [i.is_set() for i in self.idles]

    """Returns True if not tasks are left to be completed"""

    def done(self):
        return self.queue.empty()

    """Get the set of results that have been processed, repeatedly call until done"""

    def results(self, wait=0):
        time.sleep(wait)
        results = []
        try:
            while True:
                # get a result, raises empty exception immediately if none available
                results.append(self.resultQueue.get(False))
                self.resultQueue.task_done()
        except:
            pass
        return results

    """Wait for the pool to complete and return the results as soon as they are ready"""

    def iterate_results(self):
        while not self.done() or not self.idle():
            for r in self.results():
                yield r
        for r in self.results():
            yield r

    def get_stats(self):
        stats = self.stats.get_stats()
        stats['jobs_idle'] = len([1 for i in self.idles if i.is_set()])
        stats['jobs_max'] = len([1 for t in self.threads if t.is_alive()])
        stats['tasks_queued'] = self.queue.qsize()
        return stats


class StatisticsCollector():
    def __init__(self):
        self.lock = Semaphore(1)
        self.data = defaultdict(lambda: 0)

    def set(self, key, value):
        self.lock.acquire()
        self.data[key] = value
        self.lock.release()

    def increase(self, key):
        self.lock.acquire()
        self.data[key] += 1
        self.lock.release()

    def decrease(self, key):
        self.lock.acquire()
        self.data[key] -= 1
        self.lock.release()

    def get_stats(self):
        self.lock.acquire()
        stats = copy(self.data)
        self.lock.release()
        return stats
