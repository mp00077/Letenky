import logging
from itertools import count

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    finished = Signal(int, object, object)


class Worker(QRunnable):
    def __init__(self, task_id, function):
        super().__init__()
        self.task_id, self.function = task_id, function
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.function()
        except Exception as exc:
            logging.getLogger(__name__).exception("Operace na pozadí selhala")
            self.signals.finished.emit(self.task_id, None, str(exc))
        else:
            self.signals.finished.emit(self.task_id, result, None)


class TaskManager(QObject):
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self._ids = count()
        self._tasks = {}

    @property
    def busy(self):
        return bool(self._tasks)

    def submit(self, function, on_success=None, on_error=None, on_done=None):
        task_id = next(self._ids)
        worker = Worker(task_id, function)
        self._tasks[task_id] = (worker, on_success, on_error, on_done)
        worker.signals.finished.connect(self._finished)
        self.pool.start(worker)

    @Slot(int, object, object)
    def _finished(self, task_id, result, error):
        _, success, failure, done = self._tasks.pop(task_id)
        try:
            if error is not None:
                if failure:
                    failure(error)
                else:
                    self.failed.emit(error)
            elif success:
                success(result)
        except Exception as exc:
            logging.getLogger(__name__).exception("Zpracování výsledku selhalo")
            self.failed.emit(str(exc))
        finally:
            if done:
                done()
