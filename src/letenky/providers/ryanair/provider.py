from letenky.domain.errors import ProviderError
from letenky.domain.flight import SearchQuery
from letenky.domain.price import utc_now

from .airports import bundled_airports
from .client import RyanairClient
from .parser import parse_fares


class RyanairProvider:
    def __init__(self, client=None):
        self.client = client or RyanairClient()
        self._airports = {airport.code: airport for airport in bundled_airports()}

    def airports(self):
        return sorted(self._airports.values(), key=lambda airport: airport.name.casefold())

    def search(self, query: SearchQuery):
        if query.origin not in self._airports or query.destination not in self._airports:
            raise ProviderError("Vyberte letiště ze seznamu.")
        payload = self.client.get("/api/farfnd/v4/oneWayFares", {
            "departureAirportIataCode": query.origin,
            "arrivalAirportIataCode": query.destination,
            "outboundDepartureDateFrom": query.departure_date.isoformat(),
            "outboundDepartureDateTo": query.departure_date.isoformat(),
            "currency": query.currency,
        })
        return parse_fares(payload, query, self._airports, utc_now())
