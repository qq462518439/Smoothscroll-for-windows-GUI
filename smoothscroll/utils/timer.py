from queue import Empty, Queue
from threading import Lock, Thread
from time import perf_counter, sleep
from typing import Callable, Union
import logging

from ..models import TimerTask


class Timer(Thread):
    def __init__(self, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        self._queue = Queue()
        self._state_lock = Lock()
        self._closed = False

    def run(self):
        while True:
            task = self._queue.get()
            if task is None:
                self._queue.task_done()
                return
            if (remained := task.start + task.timeout - perf_counter()) > 0:
                sleep(remained)

            try:
                task.callback()
            except Exception:
                logging.exception("Timer callback failed")
            finally:
                self._queue.task_done()

    def set_timeout(self, callback: Callable, timeout: Union[int, float]):
        with self._state_lock:
            if self._closed:
                return False
            self._queue.put(TimerTask(callback, timeout))
            return True

    def __call__(self, callback: Callable, timeout: Union[int, float]):
        self.set_timeout(callback, timeout)

    def clear(self):
        with self._state_lock:
            if not self._closed:
                self._clear_pending()

    def _clear_pending(self):
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
        if self.ident is None:
            with self._state_lock:
                self._closed = True
            self.clear()
            return
        with self._state_lock:
            if not self._closed:
                self._closed = True
                self._clear_pending()
                self._queue.put(None)
        super().join(timeout=5 if timeout is None else timeout)
        if self.is_alive():
            raise TimeoutError("Timer thread did not stop")
