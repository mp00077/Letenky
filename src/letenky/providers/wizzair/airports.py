import json
from pathlib import Path

from letenky.domain.flight import Airport
from letenky.providers.ryanair.airports import bundled_airports as common_airports


def bundled_airports():
    """Geographical input catalog, not a claim that Wizz serves every airport."""
    airports = {airport.code: airport for airport in common_airports()}
    extra = json.loads(Path(__file__).with_name("airports.json").read_text(encoding="utf-8"))
    for item in extra:
        airports[item["code"]] = Airport(item["code"], item["name"], item["timeZone"])
    return sorted(airports.values(), key=lambda airport: airport.name.casefold())
