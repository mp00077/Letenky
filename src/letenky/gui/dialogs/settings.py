import logging
import sqlite3

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QSystemTrayIcon

from letenky.domain.price import utc_now
from letenky.gui.generated.ui_settings import Ui_SettingsDialog
from letenky.infrastructure.settings import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings, directory, repository, parent=None):
        super().__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.settings, self.directory = settings, directory
        self.repository = repository
        self.ui.currencyCombo.addItems(["CZK", "EUR", "GBP", "PLN"])
        self.ui.currencyCombo.setCurrentText(settings.currency)
        self.ui.intervalSpin.setValue(repository.check_interval_minutes)
        self.ui.trayCheck.setChecked(settings.close_to_tray)
        self.ui.trayCheck.setEnabled(QSystemTrayIcon.isSystemTrayAvailable())
        self.ui.pathLabel.setText(f"Databáze a logy: {directory}")
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Save).setText("Uložit")
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Zrušit")
        self.ui.buttonBox.accepted.connect(self.save)
        self.ui.buttonBox.rejected.connect(self.reject)

    def save(self):
        self.ui.intervalSpin.interpretText()
        updated = Settings(self.ui.currencyCombo.currentText(), self.ui.trayCheck.isChecked())
        saved = False
        try:
            updated.save(self.directory)
            saved = True
            self.repository.set_check_interval(self.ui.intervalSpin.value(), utc_now())
        except (OSError, sqlite3.Error, ValueError) as exc:
            if saved:
                try:
                    self.settings.save(self.directory)
                except OSError:
                    logging.getLogger(__name__).exception("Původní nastavení nelze obnovit")
            QMessageBox.warning(self, "Nastavení nelze uložit", str(exc))
            return
        self.settings.currency, self.settings.close_to_tray = updated.currency, updated.close_to_tray
        self.accept()
