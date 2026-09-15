from PySide6.QtCore import QObject, QTimer, Signal

from letenky.domain.price import utc_now


class Scheduler(QObject):
    changed = Signal()

    def __init__(self, repository, checker, tasks, parent=None):
        super().__init__(parent)
        self.repository, self.checker, self.tasks = repository, checker, tasks
        self.in_flight = set()
        self.timer = QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self.tick)

    def start(self):
        self.timer.start()
        QTimer.singleShot(0, self.tick)

    def tick(self):
        self.repository.expire(utc_now())
        self.changed.emit()
        for watch in self.repository.due(utc_now()):
            self.check(watch.id)

    def check(self, watch_id):
        if watch_id in self.in_flight:
            return
        self.in_flight.add(watch_id)
        self.tasks.submit(lambda: self.checker.check(watch_id),
                          on_done=lambda: self._finished(watch_id))
        self.changed.emit()

    def _finished(self, watch_id):
        self.in_flight.discard(watch_id)
        self.changed.emit()
