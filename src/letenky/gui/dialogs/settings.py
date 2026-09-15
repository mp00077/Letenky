from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QSystemTrayIcon

from letenky.gui.generated.ui_settings import Ui_SettingsDialog
from letenky.infrastructure.settings import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings, directory, parent=None):
        super().__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.settings, self.directory = settings, directory
        self.ui.currencyCombo.addItems(["CZK", "EUR", "GBP", "PLN"])
        self.ui.currencyCombo.setCurrentText(settings.currency)
        self.ui.trayCheck.setChecked(settings.close_to_tray)
        self.ui.trayCheck.setEnabled(QSystemTrayIcon.isSystemTrayAvailable())
        self.ui.pathLabel.setText(f"Databáze a logy: {directory}")
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Save).setText("Uložit")
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Zrušit")
        self.ui.buttonBox.accepted.connect(self.save)
        self.ui.buttonBox.rejected.connect(self.reject)

    def save(self):
        updated = Settings(self.ui.currencyCombo.currentText(), self.ui.trayCheck.isChecked())
        try:
            updated.save(self.directory)
        except OSError as exc:
            QMessageBox.warning(self, "Nastavení nelze uložit", str(exc))
            return
        self.settings.currency, self.settings.close_to_tray = updated.currency, updated.close_to_tray
        self.accept()
