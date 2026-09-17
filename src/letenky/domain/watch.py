from dataclasses import dataclass
from datetime import date

from .flight import SearchQuery


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
    previous_amount: int | None = None

    @property
    def price_change(self) -> int | None:
        if self.latest_amount is None or self.previous_amount is None:
            return None
        return self.latest_amount - self.previous_amount

    @property
    def query(self) -> SearchQuery:
        return SearchQuery(self.origin, self.destination,
                           date.fromisoformat(self.departure_date), self.currency)
