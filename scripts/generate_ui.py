"""Compile Designer forms and Qt resources with this interpreter's PySide6."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def qt_tool(name, arguments):
    # Module entry points keep the tool and the runtime on the same Python.
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    subprocess.run([sys.executable, "-c",
                    f"from PySide6.scripts.pyside_tool import {name}; {name}()", *map(str, arguments)],
                   cwd=ROOT, env=environment, check=True)


def generate():
    target = ROOT / "src/letenky/gui/generated"
    target.mkdir(parents=True, exist_ok=True)
    for ui in sorted((ROOT / "ui").glob("*.ui")):
        qt_tool("uic", ["--from-imports", ui, "-o", target / f"ui_{ui.stem}.py"])
    qt_tool("rcc", [ROOT / "resources/resources.qrc", "-o", target / "resources_rc.py"])


if __name__ == "__main__":
    generate()
