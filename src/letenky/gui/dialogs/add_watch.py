from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox

from letenky.domain.flight import SearchQuery
from letenky.domain.price import money
from letenky.gui.generated.ui_add_watch import Ui_AddWatchDialog


class AddWatchDialog(QDialog):
    def __init__(self, search, watch_service, tasks, currency, parent=None):
        super().__init__(parent)
        self.ui = Ui_AddWatchDialog()
        self.ui.setupUi(self)
        self.search_service, self.watch_service, self.tasks = search, watch_service, tasks
        self.offers = []
        self.busy = False
        self.watch_id = None
        for combo in (self.ui.originCombo, self.ui.destinationCombo):
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            for airport in search.provider.airports():
                combo.addItem(airport.label, airport.code)
            combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            combo.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            combo.currentTextChanged.connect(self.invalidate)
        self.ui.originCombo.setCurrentIndex(self.ui.originCombo.findData("PRG"))
        self.ui.destinationCombo.setCurrentIndex(self.ui.destinationCombo.findData("STN"))
        self.ui.dateEdit.setMinimumDate(QDate.currentDate())
        self.ui.dateEdit.setDate(QDate.currentDate().addDays(30))
        self.ui.currencyCombo.addItems(["CZK", "EUR", "GBP", "PLN"])
        self.ui.currencyCombo.setCurrentText(currency)
        self.ui.dateEdit.dateChanged.connect(self.invalidate)
        self.ui.currencyCombo.currentTextChanged.connect(self.invalidate)
        self.save_button = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Sledovat vybraný let")
        self.save_button.setEnabled(False)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Zrušit")
        self.ui.buttonBox.accepted.connect(self.save)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.searchButton.clicked.connect(self.search)
        self.ui.resultsList.currentRowChanged.connect(lambda row: self.save_button.setEnabled(row >= 0 and not self.busy))

    def invalidate(self, *_):
        self.offers = []
        self.ui.resultsList.clear()

    def _airport_code(self, combo):
        text = combo.currentText().strip()
        index = combo.findText(text, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            return combo.itemData(index)
        index = combo.findData(text.upper())
        if index >= 0:
            return combo.itemData(index)
        raise ValueError("Vyberte letiště z našeptávače nebo zadejte jeho IATA kód.")

    def set_busy(self, busy):
        self.busy = busy
        for widget in (self.ui.originCombo, self.ui.destinationCombo, self.ui.dateEdit,
                       self.ui.currencyCombo, self.ui.searchButton, self.ui.buttonBox):
            widget.setEnabled(not busy)
        self.save_button.setEnabled(not busy and self.ui.resultsList.currentRow() >= 0)

    def search(self):
        try:
            query = SearchQuery(self._airport_code(self.ui.originCombo),
                                self._airport_code(self.ui.destinationCombo),
                                self.ui.dateEdit.date().toPython(), self.ui.currencyCombo.currentText())
        except ValueError as exc:
            self.ui.messageLabel.setText(str(exc))
            return
        self.invalidate()
        self.set_busy(True)
        self.ui.messageLabel.setText("Vyhledávám nabídky Ryanairu…")
        self.tasks.submit(lambda: self.search_service.search(query), self.show_results,
                          self.ui.messageLabel.setText, lambda: self.set_busy(False))

    def show_results(self, offers):
        self.offers = offers
        for offer in offers:
            self.ui.resultsList.addItem(
                f"{offer.flight_number}  ·  {offer.departure:%H:%M} → {offer.arrival:%H:%M}  ·  "
                f"{money(offer.amount_minor, offer.currency)}  (místní časy)")
        if offers:
            self.ui.resultsList.setCurrentRow(0)
            self.ui.messageLabel.setText("Vyberte nabídku pro sledování. Cena je orientační; zdroj nemusí vracet všechny spoje.")
        else:
            self.ui.messageLabel.setText("Pro tento den zdroj nevrátil žádnou nabídku. Neznamená to jistotu, že žádný let neexistuje.")

    def save(self):
        index = self.ui.resultsList.currentRow()
        if index < 0:
            return
        try:
            self.watch_id = self.watch_service.add(self.offers[index])
        except Exception as exc:
            self.ui.messageLabel.setText(str(exc))
            return
        self.accept()

    def reject(self):
        if not self.busy:
            super().reject()
