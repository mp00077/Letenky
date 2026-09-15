from datetime import datetime
from zoneinfo import ZoneInfo


class FlightSearch:
    def __init__(self, provider):
        self.provider = provider

    def search(self, query):
        airport = next((item for item in self.provider.airports() if item.code == query.origin), None)
        if airport is None:
            raise ValueError("Neznámé letiště odletu.")
        now = datetime.now(ZoneInfo(airport.timezone))
        if query.departure_date < now.date():
            raise ValueError("Datum odletu nesmí být v minulosti.")
        return [offer for offer in self.provider.search(query) if offer.departure > now]
