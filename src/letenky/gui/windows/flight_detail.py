from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHeaderView

from letenky.domain.price import local_time
from letenky.gui.generated.ui_flight_detail import Ui_FlightDetailDialog
from letenky.gui.models.history_model import HistoryModel
from letenky.services.price_history import price_summary


class FlightDetailDialog(QDialog):
    def __init__(self, watch_id, repository, observations, scheduler, parent=None):
        super().__init__(parent)
        self.ui = Ui_FlightDetailDialog()
        self.ui.setupUi(self)
        self.watch_id, self.repository, self.observations = watch_id, repository, observations
        self.chart = None
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Close).setText("Zavřít")
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.historyTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.refresh()
        scheduler.changed.connect(self.refresh)

    def refresh(self):
        watch = self.repository.get(self.watch_id)
        if watch is None:
            return
        rows = self.observations.history(self.watch_id)
        signature = (len(rows), watch.state)
        if getattr(self, "_signature", None) == signature:
            return
        self._signature = signature
        self.ui.heading.setText(f"{watch.origin} → {watch.destination} · {watch.flight_number}")
        self.ui.summaryLabel.setText(f"{price_summary(watch)}\nPoslední cena zjištěna: {local_time(watch.latest_at)}")
        old_model = self.ui.historyTable.model()
        self.ui.historyTable.setModel(HistoryModel(rows, self))
        if old_model:
            old_model.deleteLater()
        from letenky.gui.widgets.price_chart import PriceChart
        if self.chart:
            self.ui.chartLayout.removeWidget(self.chart)
            self.chart.deleteLater()
        self.chart = PriceChart(rows, watch.currency, self)
        self.ui.chartLayout.addWidget(self.chart)
