import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sample_payload():
    return json.loads((ROOT / "tests/fixtures/ryanair/one_way_fares.json").read_text(encoding="utf-8"))
