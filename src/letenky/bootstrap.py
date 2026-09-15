import argparse
import logging
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="Letenky — sledování cen Ryanair")
    parser.add_argument("--data-dir", help="Vlastní adresář databáze, nastavení a logů")
    parser.add_argument("--check-due", action="store_true", help="Jednorázová kontrola splatných sledování bez oken")
    parser.add_argument("--smoke-test", action="store_true", help="Offline ověření spuštění a grafu, poté ukončení")
    args = parser.parse_args(argv)
    from PySide6.QtCore import QCoreApplication, QLocale, QTimer
    if args.check_due:
        app = QCoreApplication([sys.argv[0]])
    else:
        from PySide6.QtWidgets import QApplication
        app = QApplication([sys.argv[0]])
        app.setStyle("Fusion")
        app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName("Letenky")
    app.setApplicationName("Letenky")
    QLocale.setDefault(QLocale("cs_CZ"))
    try:
        from letenky.infrastructure.paths import data_directory
        from letenky.infrastructure.logging import configure_logging
        from letenky.infrastructure.single_instance import acquire_lock
        from letenky.storage.database import Database
        directory = data_directory(args.data_dir)
        configure_logging(directory)
        lock = acquire_lock(directory)
        database = Database(directory / "letenky.sqlite3")
        database.initialize()
        if args.check_due:
            from letenky.cli import check_due
            try:
                return check_due(database)
            finally:
                lock.unlock()
        from letenky.application import create_window
        window = create_window(directory, database)
        window.show()
        if args.smoke_test:
            from letenky.gui.widgets.price_chart import PriceChart
            chart = PriceChart([], "CZK", window)
            chart.hide()
            QTimer.singleShot(250, app.quit)
        else:
            window.context.scheduler.start()
        try:
            return app.exec()
        finally:
            window.context.scheduler.timer.stop()
            window.context.tasks.pool.waitForDone()
            lock.unlock()
    except Exception as exc:
        logging.exception("Spuštění aplikace selhalo")
        if args.check_due or args.smoke_test:
            if sys.stderr:
                print(str(exc), file=sys.stderr)
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Letenky — spuštění selhalo", str(exc))
        return 1
