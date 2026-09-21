from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QHeaderView, QMessageBox

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
        self.export_button = self.ui.buttonBox.addButton("Export do PDF…", QDialogButtonBox.ButtonRole.ActionRole)
        self.export_button.clicked.connect(self.export_pdf)
        self.ui.historyTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.refresh()
        scheduler.changed.connect(self.refresh)

    def export_pdf(self):
        watch = self.repository.get(self.watch_id)
        if watch is None:
            QMessageBox.warning(self, "Export do PDF", "Sledování již neexistuje.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export grafu do PDF",
            f"{watch.origin}-{watch.destination}-{watch.departure_date}.pdf", "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
            from pathlib import Path
            if Path(path).exists() and QMessageBox.question(
                    self, "Přepsat PDF?", "Soubor již existuje. Chcete jej přepsat?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        try:
            from letenky.gui.pdf_export import export_chart_pdf
            export_chart_pdf(path, watch, self.observations.history(self.watch_id))
        except Exception as exc:
            QMessageBox.warning(self, "Export do PDF selhal", str(exc))
            return
        QMessageBox.information(self, "Export do PDF", f"PDF bylo uloženo:\n{path}")

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
