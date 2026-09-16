from datetime import datetime
from zoneinfo import ZoneInfo
from letenky.providers.registry import as_registry
from letenky.domain.carrier import tracking_deadline


class FlightSearch:
    def __init__(self, provider):
        self.provider = as_registry(provider)

    def search(self, query):
        airport = next((item for item in self.provider.airports(query.carrier) if item.code == query.origin), None)
        if airport is None:
            raise ValueError("Neznámé letiště odletu.")
        now = datetime.now(ZoneInfo(airport.timezone))
        if query.departure_date < now.date():
            raise ValueError("Datum odletu nesmí být v minulosti.")
        return [offer for offer in self.provider.search(query)
                if offer.matches(query) and tracking_deadline(offer.departure, offer.source) > now]
