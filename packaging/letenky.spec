# PyInstaller executes this as Python on the target OS.
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent
datas = [
    (str(root / 'src/letenky/storage/migrations'), 'letenky/storage/migrations'),
    (str(root / 'src/letenky/providers/ryanair/airports.json'), 'letenky/providers/ryanair'),
    (str(root / 'src/letenky/providers/wizzair/airports.json'), 'letenky/providers/wizzair'),
] + collect_data_files('tzdata') + collect_data_files('certifi')
hiddenimports = [
    'letenky.gui.dialogs.add_watch', 'letenky.gui.dialogs.settings',
    'letenky.gui.windows.flight_detail', 'letenky.gui.widgets.price_chart',
    'PySide6.QtCharts', 'PySide6.QtSvg', 'tzdata',
]
a = Analysis([str(root / 'packaging/entrypoint.py')], pathex=[str(root / 'src')],
             binaries=[], datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                       'PySide6.QtQml', 'PySide6.QtQuick'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Letenky',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=os.environ.get('LETENKY_BUILD_CONSOLE') == '1', disable_windowed_traceback=False,
          target_arch=None, codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Letenky')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='Letenky.app', bundle_identifier='cz.letenky.desktop',
                 info_plist={'CFBundleDisplayName': 'Letenky',
                             'NSHighResolutionCapable': True})
