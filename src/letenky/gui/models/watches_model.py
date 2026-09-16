from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from letenky.domain.price import local_time
from letenky.domain.carrier import is_daily_minimum
from letenky.services.price_history import STATUS_LABELS, price_summary


class WatchesModel(QAbstractTableModel):
    headers = ("Trasa / let", "Odlet · místní čas", "Poslední cena (historické minimum)", "Kontrola / stav", "Další kontrola")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.watches = []
        self.in_flight = set()

    def replace(self, watches, in_flight=()):
        self.beginResetModel()
        self.watches, self.in_flight = watches, set(in_flight)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.watches)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        watch = self.watches[index.row()]
        if role == Qt.ItemDataRole.ToolTipRole:
            return (f"{watch.carrier_label} · {watch.flight_label}\nCena zjištěna: {local_time(watch.latest_at)}\n"
                    f"Minimum zjištěno: {local_time(watch.minimum_at)}\n"
                    f"{watch.last_error or STATUS_LABELS.get(watch.last_status, '')}")
        if role == Qt.ItemDataRole.ForegroundRole and index.column() == 3 and watch.last_status == "error":
            return QColor("#a13b2c")
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if watch.id in self.in_flight:
            status = "Kontroluji…"
        elif watch.state == "paused":
            status = "Pozastaveno"
        elif watch.state == "completed":
            status = "Ukončeno · po odletu"
        else:
            status = STATUS_LABELS.get(watch.last_status, "Čeká na kontrolu")
        return (
            f"{watch.origin} → {watch.destination}\n{watch.carrier_label} · {watch.flight_label}",
            datetime.fromisoformat(watch.departure_local).strftime("%d. %m. %Y\ndenní minimum" if is_daily_minimum(watch.source) else "%d. %m. %Y\n%H:%M"),
            price_summary(watch),
            f"{status}\n{local_time(watch.checked_at)}",
            local_time(watch.next_check_at) if watch.state == "active" else "—",
        )[index.column()]
