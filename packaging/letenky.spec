# PyInstaller executes this as Python on the target OS.
import os
import sys
import json
import runpy
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent
metadata_module = runpy.run_path(str(root / 'src/letenky/infrastructure/build_info.py'))
metadata_path = Path(workpath) / 'build_info.json'
metadata_path.parent.mkdir(parents=True, exist_ok=True)
metadata = metadata_module['collect_build_info'](root, built=True)
metadata_path.write_text(json.dumps(metadata,
                                    ensure_ascii=False), encoding='utf-8')
version_file = None
if sys.platform == 'win32':
    version_module = runpy.run_path(str(root / 'scripts/windows_version.py'))
    version_file = version_module['write_version_info'](Path(workpath) / 'windows_version.txt', metadata)
datas = [
    (str(root / 'resources/icons/plane.png'), 'icons'),
    (str(metadata_path), 'letenky/infrastructure'),
    (str(root / 'src/letenky/storage/migrations'), 'letenky/storage/migrations'),
    (str(root / 'src/letenky/providers/ryanair/airports.json'), 'letenky/providers/ryanair'),
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
          version=version_file,
          icon=str(root / 'resources/icons/plane.ico') if sys.platform == 'win32' else None,
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=os.environ.get('LETENKY_BUILD_CONSOLE') == '1', disable_windowed_traceback=False,
          target_arch=None, codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Letenky')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='Letenky.app', bundle_identifier='cz.letenky.desktop',
                 icon=str(root / 'resources/icons/plane.icns'),
                 info_plist={'CFBundleDisplayName': 'Letenky',
                             'NSHighResolutionCapable': True})
