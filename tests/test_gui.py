import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from dataclasses import replace
from datetime import timedelta

from tests.support import ROOT

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QDate, QEvent, QThread
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from letenky.application import create_window
from letenky.storage.database import Database
from letenky.domain.price import utc_now
from tests.test_core import sample_offer


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Database(Path(self.directory.name) / "gui.sqlite3")
        self.database.initialize()
        self.window = create_window(Path(self.directory.name), self.database)
        self.window.show()
        QTest.qWait(10)

    def tearDown(self):
        self.window.context.scheduler.timer.stop()
        self.window.context.tasks.pool.waitForDone()
        if self.window.tray:
            self.window.tray.hide()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_empty_and_populated_window_and_lazy_chart(self):
        self.assertTrue(self.window.ui.emptyLabel.isVisible())
        watch_id = self.window.context.watches.add(sample_offer())
        self.window.refresh()
        self.window.ui.table.selectRow(0)
        self.assertEqual(self.window.selected().id, watch_id)
        self.assertFalse(self.window.ui.emptyLabel.isVisible())
        self.assertTrue(self.window.ui.detailButton.isEnabled())
        from letenky.gui.windows.flight_detail import FlightDetailDialog
        dialog = FlightDetailDialog(watch_id, self.window.context.watches,
                                    self.window.context.observations, self.window.context.scheduler, self.window)
        dialog.show()
        QTest.qWait(10)
        self.assertEqual(dialog.ui.historyTable.model().rowCount(), 1)
        self.assertEqual(len(dialog.chart.chart().series()), 1)
        dialog.close()

    def test_worker_callback_is_on_gui_thread(self):
        results = []
        self.window.context.tasks.submit(lambda: 42, lambda value: results.append((value, QThread.currentThread())))
        for _ in range(100):
            QTest.qWait(10)
            if results:
                break
        self.assertEqual(results, [(42, self.app.thread())])
        self.assertFalse(self.window.context.tasks.busy)

    def test_search_dialog_rejects_unknown_airport(self):
        from letenky.gui.dialogs.add_watch import AddWatchDialog
        context = self.window.context
        dialog = AddWatchDialog(context.search, context.watch_service, context.tasks, "CZK", self.window)
        dialog.ui.originCombo.setEditText("XYZXYZ")
        dialog.search()
        self.assertIn("letiště", dialog.ui.messageLabel.text())
        self.assertFalse(dialog.busy)
        dialog.close()

    def test_async_search_then_save_records_first_price(self):
        from letenky.gui.dialogs.add_watch import AddWatchDialog
        from letenky.services.flight_search import FlightSearch
        from letenky.providers.ryanair.airports import bundled_airports
        now = utc_now()
        offer = replace(sample_offer(), observed_at=now,
                        departure=now + timedelta(days=30), arrival=now + timedelta(days=30, hours=2))
        class Provider:
            def airports(self):
                return bundled_airports()
            def search(self, query):
                return [offer]
        context = self.window.context
        dialog = AddWatchDialog(FlightSearch(Provider()), context.watch_service, context.tasks, "CZK", self.window)
        dialog.ui.dateEdit.setDate(QDate(offer.departure.date()))
        dialog.search()
        self.assertTrue(dialog.busy)
        for _ in range(100):
            QTest.qWait(10)
            if not dialog.busy:
                break
        self.assertEqual(dialog.ui.resultsList.count(), 1)
        self.assertTrue(dialog.save_button.isEnabled())
        dialog.save()
        self.assertIsNotNone(dialog.watch_id)
        self.assertEqual(context.watches.get(dialog.watch_id).latest_amount, offer.amount_minor)
        self.assertEqual(len(context.observations.history(dialog.watch_id)), 1)

    def test_graph_breaks_line_on_missing_measurement(self):
        from letenky.gui.widgets.price_chart import PriceChart
        rows = [
            {"amount_minor": 10000, "observed_at": "2026-09-15T00:00:00+00:00"},
            {"amount_minor": None, "observed_at": None},
            {"amount_minor": 9000, "observed_at": "2026-09-15T06:00:00+00:00"},
            {"amount_minor": 11000, "observed_at": "2026-09-15T09:00:00+00:00"},
        ]
        chart = PriceChart(rows, "CZK", self.window)
        self.assertEqual([series.count() for series in chart.chart().series()], [2, 3])


if __name__ == "__main__":
    unittest.main()
