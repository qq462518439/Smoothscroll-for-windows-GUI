from queue import Empty, Queue
from threading import Thread
from time import perf_counter, sleep
from typing import Callable, Union
import logging

from ..models import TimerTask


class Timer(Thread):
    def __init__(self, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        self._queue = Queue()

    def run(self):
        while task := self._queue.get():
            if (remained := task.start + task.timeout - perf_counter()) > 0:
                sleep(remained)

            try:
                task.callback()
            except Exception:
                logging.exception("Timer callback failed")
            finally:
                self._queue.task_done()

    def set_timeout(self, callback: Callable, timeout: Union[int, float]):
        self._queue.put(TimerTask(callback, timeout))

    def __call__(self, callback: Callable, timeout: Union[int, float]):
        self.set_timeout(callback, timeout)

    def clear(self):
        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                break
            else:
                self._queue.task_done()

    def wait_tasks(self):
        self._queue.join()

    def join(self, timeout=None):
        self.wait_tasks()
        self._queue.put(None)
        super().join(timeout=timeout)
