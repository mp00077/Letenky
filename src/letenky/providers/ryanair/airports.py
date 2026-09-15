import json
from pathlib import Path

from letenky.domain.flight import Airport


def bundled_airports() -> list[Airport]:
    data = json.loads(Path(__file__).with_name("airports.json").read_text(encoding="utf-8"))
    return [Airport(item["code"], item["name"], item["timeZone"]) for item in data]
