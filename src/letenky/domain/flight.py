from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Airport:
    code: str
    name: str
    timezone: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"


@dataclass(frozen=True)
class SearchQuery:
    origin: str
    destination: str
    departure_date: date
    currency: str = "CZK"

    def __post_init__(self):
        if any(len(code) != 3 or not code.isascii() or not code.isalpha()
               or code != code.upper() for code in (self.origin, self.destination)):
            raise ValueError("Zadejte platné třípísmenné kódy letišť.")
        if self.origin == self.destination:
            raise ValueError("Odletové a příletové letiště musí být různé.")
        if self.currency not in {"CZK", "EUR", "GBP", "PLN"}:
            raise ValueError("Nepodporovaná měna.")


@dataclass(frozen=True)
class FlightOffer:
    origin: str
    destination: str
    flight_number: str
    departure: datetime
    arrival: datetime
    amount_minor: int
    currency: str
    observed_at: datetime
    source_updated_at: datetime | None = None
    source: str = "ryanair_farefinder"

    def __post_init__(self):
        if self.amount_minor < 0:
            raise ValueError("Cena nesmí být záporná.")
        for value in (self.departure, self.arrival, self.observed_at):
            if value.tzinfo is None:
                raise ValueError("Čas musí obsahovat časové pásmo.")

    def matches(self, query: SearchQuery) -> bool:
        return (self.origin == query.origin and self.destination == query.destination
                and self.departure.date() == query.departure_date
                and self.currency == query.currency)
