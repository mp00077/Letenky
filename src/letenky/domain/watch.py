from dataclasses import dataclass
from datetime import date

from .flight import SearchQuery
from .carrier import CARRIERS, carrier_for_source, is_daily_minimum


@dataclass(frozen=True)
class Watch:
    id: int
    flight_id: int
    origin: str
    destination: str
    departure_date: str
    flight_number: str
    departure_local: str
    departure_utc: str
    currency: str
    state: str
    next_check_at: str
    last_status: str | None
    last_error: str | None
    latest_amount: int | None
    latest_at: str | None
    minimum_amount: int | None
    minimum_at: str | None
    checked_at: str | None
    instance_key: str
    source: str

    @property
    def carrier(self):
        return carrier_for_source(self.source)

    @property
    def carrier_label(self):
        return CARRIERS[self.carrier]

    @property
    def flight_label(self):
        return "Nejnižší cena dne" if is_daily_minimum(self.source) else self.flight_number

    @property
    def query(self) -> SearchQuery:
        return SearchQuery(self.origin, self.destination,
                           date.fromisoformat(self.departure_date), self.currency, self.carrier)
