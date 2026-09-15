"""Render deterministic UI examples into .test-data, never into the user's database."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from letenky.application import create_window
from letenky.gui.dialogs.add_watch import AddWatchDialog
from letenky.gui.windows.flight_detail import FlightDetailDialog
from letenky.storage.database import Database
from tests.test_core import sample_offer, NOW
from dataclasses import replace
from datetime import timedelta


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    # The Windows offscreen Qt plugin does not enumerate system fonts.
    font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
        app.setFont(QFont("Segoe UI", 10))
    out = ROOT / ".test-data"
    out.mkdir(exist_ok=True)
    with TemporaryDirectory() as directory:
        db = Database(Path(directory) / "visual.sqlite3")
        db.initialize()
        window = create_window(Path(directory), db)
        offer = sample_offer()
        repo = window.context.watches
        watch_id = repo.add(offer)
        for i, price in enumerate([62000, 59000, 49900, 51000, 57000], 1):
            now = NOW + timedelta(hours=i * 3)
            repo.record_check(repo.get(watch_id), now, now, "ok",
                              offer=replace(offer, amount_minor=price, observed_at=now))
        window.refresh()
        window.ui.table.selectRow(0)
        window.show()
        app.processEvents()
        window.grab().save(str(out / "main.png"))
        detail = FlightDetailDialog(watch_id, repo, window.context.observations,
                                    window.context.scheduler, window)
        detail.show()
        app.processEvents()
        detail.grab().save(str(out / "detail.png"))
        detail.hide()
        dialog = AddWatchDialog(window.context.search, window.context.watch_service,
                                 window.context.tasks, "CZK", window)
        from PySide6.QtCore import QDate
        dialog.ui.dateEdit.setDate(QDate(offer.departure.year, offer.departure.month, offer.departure.day))
        dialog.show_results([offer])
        dialog.show()
        app.processEvents()
        dialog.grab().save(str(out / "search.png"))
        if window.tray:
            window.tray.hide()
    print(f"Náhledy: {out}")


if __name__ == "__main__":
    main()
