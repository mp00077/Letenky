from letenky.domain.errors import ProviderError
from letenky.domain.price import utc_now

from .airports import bundled_airports
from .client import WizzairClient
from .parser import parse_timetable


class WizzairProvider:
    def __init__(self, client=None):
        self.client = client or WizzairClient()
        self._airports = {airport.code: airport for airport in bundled_airports()}

    def airports(self):
        return sorted(self._airports.values(), key=lambda airport: airport.name.casefold())

    def search(self, query):
        if query.carrier != "wizzair":
            raise ProviderError("Nesprávný dopravce pro cenový kalendář Wizz Air.")
        if query.origin not in self._airports or query.destination not in self._airports:
            raise ProviderError("Vyberte letiště ze seznamu.")
        return parse_timetable(self.client.timetable(query), query, self._airports, utc_now())
