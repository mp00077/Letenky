from PySide6.QtCore import QLockFile


def acquire_lock(directory):
    lock = QLockFile(str(directory / "application.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        raise RuntimeError("Aplikace nebo kontrola cen již běží s touto databází.")
    return lock
