from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def create_tray(window):
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    tray = QSystemTrayIcon(window.windowIcon(), window)
    tray.setToolTip("Letenky · Ryanair a Wizz Air")
    menu = QMenu(window)
    menu.addAction("Otevřít Letenky", window.restore)
    menu.addSeparator()
    menu.addAction("Ukončit", window.request_quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: window.restore()
                           if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                                         QSystemTrayIcon.ActivationReason.DoubleClick) else None)
    tray.show()
    return tray
