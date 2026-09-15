import sys
from pathlib import Path

from generate_ui import generate

if __name__ == "__main__":
    generate()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from letenky.bootstrap import main
    raise SystemExit(main())
