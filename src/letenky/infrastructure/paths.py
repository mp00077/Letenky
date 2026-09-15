from pathlib import Path


def data_directory(override=None):
    if override:
        path = Path(override).expanduser().resolve()
    else:
        from PySide6.QtCore import QStandardPaths
        path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    path.mkdir(parents=True, exist_ok=True)
    return path
