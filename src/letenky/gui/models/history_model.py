from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from letenky.domain.price import local_time, money
from letenky.services.price_history import STATUS_LABELS


class HistoryModel(QAbstractTableModel):
    headers = ("Datum a čas zjištění", "Cena", "Stav", "Cena aktualizována u zdroje")

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.rows = list(reversed(rows))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        if role == Qt.ItemDataRole.ToolTipRole:
            return row["error"] or STATUS_LABELS.get(row["status"])
        if role == Qt.ItemDataRole.DisplayRole:
            return (local_time(row["observed_at"] or row["finished_at"]),
                    money(row["amount_minor"], row["currency"] or ""),
                    STATUS_LABELS.get(row["status"], row["status"]),
                    local_time(row["source_updated_at"]))[index.column()]
