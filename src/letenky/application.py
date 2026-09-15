from dataclasses import dataclass


@dataclass
class ApplicationContext:
    directory: object
    settings: object
    watches: object
    observations: object
    search: object
    watch_service: object
    tasks: object
    scheduler: object


def create_window(directory, database):
    from PySide6.QtCore import QFile, QIODevice
    from PySide6.QtWidgets import QApplication
    from letenky.gui.generated import resources_rc  # noqa: F401
    from letenky.gui.windows.main_window import MainWindow
    from letenky.gui.workers.check_worker import TaskManager
    from letenky.infrastructure.settings import Settings
    from letenky.providers.ryanair.provider import RyanairProvider
    from letenky.scheduling.scheduler import Scheduler
    from letenky.services.flight_search import FlightSearch
    from letenky.services.price_checker import PriceChecker
    from letenky.services.watch_service import WatchService
    from letenky.storage.repositories.observations import ObservationRepository
    from letenky.storage.repositories.watches import WatchRepository

    stylesheet = QFile(":/styles/app.qss")
    if stylesheet.open(QIODevice.OpenModeFlag.ReadOnly):
        QApplication.instance().setStyleSheet(bytes(stylesheet.readAll()).decode("utf-8"))
    watches = WatchRepository(database)
    provider = RyanairProvider()
    tasks = TaskManager(QApplication.instance())
    scheduler = Scheduler(watches, PriceChecker(provider, watches), tasks, QApplication.instance())
    context = ApplicationContext(directory, Settings.load(directory), watches,
                                 ObservationRepository(database), FlightSearch(provider),
                                 WatchService(watches), tasks, scheduler)
    return MainWindow(context)
