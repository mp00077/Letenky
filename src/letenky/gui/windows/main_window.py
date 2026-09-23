from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QHeaderView, QMainWindow, QMessageBox

from letenky.domain.price import utc_now
from letenky.gui.generated.ui_main_window import Ui_MainWindow
from letenky.gui.models.watches_model import WatchesModel
from letenky.gui.tray import create_tray


class MainWindow(QMainWindow):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(":/icons/plane.svg"))
        self.model = WatchesModel(self)
        self.ui.table.setModel(self.model)
        header = self.ui.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.ui.table.verticalHeader().hide()
        self.ui.table.verticalHeader().setDefaultSectionSize(66)
        self.ui.table.selectionModel().selectionChanged.connect(self.update_actions)
        self.ui.table.doubleClicked.connect(self.show_detail)
        self.ui.addButton.clicked.connect(self.add_watch)
        self.ui.checkButton.clicked.connect(self.check_selected)
        self.ui.pauseButton.clicked.connect(self.toggle_pause)
        self.ui.deleteButton.clicked.connect(self.delete_selected)
        self.ui.detailButton.clicked.connect(self.show_detail)
        self.ui.settingsButton.clicked.connect(self.show_settings)
        self.ui.quitButton.clicked.connect(self.request_quit)
        self.ui.aboutAction.triggered.connect(self.show_about)
        context.scheduler.changed.connect(self.refresh)
        context.tasks.failed.connect(self.show_error)
        self.tray = create_tray(self)
        self._quitting = False
        self._tray_notice = False
        self.refresh()

    def selected(self):
        index = self.ui.table.currentIndex()
        return self.model.watches[index.row()] if index.isValid() and index.row() < len(self.model.watches) else None

    def refresh(self):
        selected = self.selected()
        watches = self.context.watches.list()
        self.model.replace(watches, self.context.scheduler.in_flight)
        if selected:
            row = next((i for i, watch in enumerate(watches) if watch.id == selected.id), None)
            if row is not None:
                self.ui.table.selectRow(row)
        self.ui.emptyLabel.setVisible(not watches)
        self.ui.table.setVisible(bool(watches))
        active = sum(w.state == "active" for w in watches)
        paused = sum(w.state == "paused" for w in watches)
        self.ui.summaryLabel.setText(f"Sledováno: {len(watches)}     •     Aktivní: {active}     •     Pozastaveno: {paused}")
        interval = self.context.watches.check_interval_minutes
        self.ui.subtitle.setText(f"Cena pod dohledem. Interval automatické kontroly: {interval} min při spuštěné aplikaci.")
        self.update_actions()

    def update_actions(self, *_):
        watch = self.selected()
        busy = watch is not None and watch.id in self.context.scheduler.in_flight
        self.ui.detailButton.setEnabled(watch is not None)
        self.ui.checkButton.setEnabled(watch is not None and watch.state == "active" and not busy)
        self.ui.pauseButton.setEnabled(watch is not None and watch.state != "completed" and not busy)
        self.ui.pauseButton.setText("Obnovit sledování" if watch and watch.state == "paused" else "Pozastavit")
        self.ui.deleteButton.setEnabled(watch is not None and not busy)
        self.ui.deleteButton.setToolTip("Počkejte na dokončení kontroly." if busy else "Smazat vybrané sledování včetně historie cen.")

    def add_watch(self):
        from letenky.gui.dialogs.add_watch import AddWatchDialog
        dialog = AddWatchDialog(self.context.search, self.context.watch_service, self.context.tasks,
                                self.context.settings.currency, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            for row, watch in enumerate(self.model.watches):
                if watch.id == dialog.watch_id:
                    self.ui.table.selectRow(row)
            self.statusBar().showMessage("Sledování uloženo včetně první ceny.", 8000)
        dialog.deleteLater()

    def check_selected(self):
        if watch := self.selected():
            self.context.scheduler.check(watch.id)

    def toggle_pause(self):
        if watch := self.selected():
            self.context.watches.set_paused(watch.id, watch.state == "active", utc_now())
            self.context.scheduler.tick()

    def confirm_delete(self, watch):
        message = QMessageBox(self)
        message.setWindowTitle("Smazat sledování")
        message.setIcon(QMessageBox.Icon.Warning)
        message.setTextFormat(Qt.TextFormat.PlainText)
        message.setText(f"Smazat sledování {watch.origin} → {watch.destination}, "
                        f"{watch.flight_number}, odlet {watch.departure_date}?")
        message.setInformativeText("Smaže se i celá historie cen tohoto sledování. Tuto akci nelze vrátit.")
        delete_button = message.addButton("Smazat", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = message.addButton("Zrušit", QMessageBox.ButtonRole.RejectRole)
        message.setDefaultButton(cancel_button)
        message.setEscapeButton(cancel_button)
        message.exec()
        return message.clickedButton() == delete_button

    def delete_selected(self):
        watch = self.selected()
        if watch is None or watch.id in self.context.scheduler.in_flight:
            return
        if not self.confirm_delete(watch):
            return
        # The scheduler can start a check while the confirmation dialog is open.
        if watch.id in self.context.scheduler.in_flight:
            self.statusBar().showMessage("Právě probíhá kontrola tohoto letu. Po dokončení zkuste smazání znovu.", 10000)
            return
        try:
            self.context.watch_service.delete(watch.id)
        except Exception as exc:
            self.show_error(str(exc))
            return
        self.refresh()
        self.statusBar().showMessage("Sledování a jeho historie byly smazány.", 8000)

    def show_detail(self, *_):
        if watch := self.selected():
            from letenky.gui.windows.flight_detail import FlightDetailDialog
            dialog = FlightDetailDialog(watch.id, self.context.watches, self.context.observations,
                                        self.context.scheduler, self)
            dialog.exec()
            dialog.deleteLater()

    def show_settings(self):
        from letenky.gui.dialogs.settings import SettingsDialog
        dialog = SettingsDialog(self.context.settings, self.context.directory, self.context.watches, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.context.scheduler.tick()
        dialog.deleteLater()

    def show_about(self):
        from letenky.gui.dialogs.about import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()
        dialog.deleteLater()

    def show_error(self, message):
        self.statusBar().showMessage(message, 30_000)
        if self.isVisible():
            QMessageBox.warning(self, "Operaci se nepodařilo dokončit", message)

    def restore(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def request_quit(self):
        self.context.scheduler.timer.stop()
        self._quitting = True
        if self.context.tasks.busy:
            self.restore()
            self.centralWidget().setEnabled(False)
            self.statusBar().showMessage("Dokončuji probíhající operace a ukládám výsledky…")
            QTimer.singleShot(200, self.request_quit)
            return
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.ignore()
        if self.context.settings.close_to_tray and self.tray and not self._quitting:
            self.hide()
            if not self._tray_notice:
                self.tray.showMessage("Letenky běží na pozadí", "Kontroly cen pokračují. Aplikaci ukončíte z nabídky ikony v liště.")
                self._tray_notice = True
        else:
            self.request_quit()
