"""Build on the target OS. No cross compilation."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

from generate_ui import ROOT, generate
from generate_icons import generate as generate_icons


def build():
    if sys.platform not in {"win32", "darwin", "linux"}:
        raise SystemExit(f"Nepodporovaný systém: {sys.platform}")
    if sys.platform == "win32":
        existing_executable = ROOT / "dist/Letenky/Letenky.exe"
        if existing_executable.exists():
            try:
                # A loaded Windows executable cannot be opened for writing.
                # Check before PyInstaller starts cleaning the distribution.
                with existing_executable.open("r+b"):
                    pass
            except PermissionError:
                raise SystemExit("Před buildem ukončete Letenky i v systémové liště. "
                                 "Výstupní aplikace je spuštěná nebo není zapisovatelná.")
    generate()
    generate_icons()
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    # Preserve Git's location before sanitizing PATH for Qt DLL loading.
    environment["LETENKY_GIT_EXECUTABLE"] = shutil.which("git") or "git"
    if sys.platform == "win32":
        # Do not let unrelated tools on PATH supply Qt's ICU/SSL DLLs.
        # Windows supplies its own ICU; Poppler/Conda copies can be ABI-incompatible.
        windows = Path(environment.get("SystemRoot", "C:/Windows"))
        environment["PATH"] = os.pathsep.join(map(str, [
            Path(sys.executable).parent, Path(sys.base_prefix),
            Path(sys.base_prefix) / "DLLs", windows / "System32", windows,
        ]))
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    str(ROOT / "packaging/letenky.spec")], cwd=ROOT, env=environment, check=True)
    if sys.platform == "win32":
        executable = ROOT / "dist/Letenky/Letenky.exe"
    elif sys.platform == "darwin":
        executable = ROOT / "dist/Letenky.app/Contents/MacOS/Letenky"
    else:
        executable = ROOT / "dist/Letenky/Letenky"
    environment["QT_QPA_PLATFORM"] = "offscreen"
    with tempfile.TemporaryDirectory(prefix="letenky-build-") as directory:
        result = subprocess.run([str(executable), "--smoke-test", "--data-dir", directory],
                                cwd=executable.parent, env=environment, capture_output=True, timeout=60)
        if result.returncode:
            print(result.stderr.decode(errors="replace"), file=sys.stderr)
            log = Path(directory) / "letenky.log"
            if log.exists():
                print(log.read_text(encoding="utf-8"), file=sys.stderr)
            raise SystemExit(f"Test sestavené aplikace selhal: {result.returncode}")
    print(f"Build ověřen: {executable} ({platform.system()} {platform.machine()})")


if __name__ == "__main__":
    build()
