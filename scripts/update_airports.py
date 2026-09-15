"""Explicit maintenance command: refresh the public airport catalog snapshot."""
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from letenky.providers.ryanair.client import RyanairClient


def main():
    data = RyanairClient().get("/api/views/locate/5/airports/en/active")
    if not isinstance(data, list) or len(data) < 50:
        raise ValueError("Neúplný seznam letišť; původní soubor zůstává zachován.")
    records = []
    codes = set()
    for airport in data:
        record = {key: airport[key] for key in ("code", "name", "timeZone")}
        if len(record["code"]) != 3 or record["code"] in codes or not record["name"]:
            raise ValueError("Neplatné letiště v odpovědi.")
        ZoneInfo(record["timeZone"])
        codes.add(record["code"])
        records.append(record)
    target = ROOT / "src/letenky/providers/ryanair/airports.json"
    temp = target.with_suffix(".json.tmp")
    temp.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    print(f"Aktualizováno {len(records)} letišť. Pro distribuci spusťte nový build.")


if __name__ == "__main__":
    main()
