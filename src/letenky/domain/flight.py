from dataclasses import dataclass
from datetime import date, datetime

from .carrier import CARRIERS, carrier_for_source, is_daily_minimum


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
    currency: str | None = "CZK"
    carrier: str = "ryanair"

    def __post_init__(self):
        if any(len(code) != 3 or not code.isascii() or not code.isalpha()
               or code != code.upper() for code in (self.origin, self.destination)):
            raise ValueError("Zadejte platné třípísmenné kódy letišť.")
        if self.origin == self.destination:
            raise ValueError("Odletové a příletové letiště musí být různé.")
        if self.carrier not in CARRIERS:
            raise ValueError("Nepodporovaný dopravce.")
        if self.currency is None and self.carrier == "wizzair":
            return
        if not isinstance(self.currency, str) or len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("Nepodporovaná měna.")


@dataclass(frozen=True)
class FlightOffer:
    origin: str
    destination: str
    flight_number: str
    departure: datetime
    arrival: datetime | None
    amount_minor: int
    currency: str
    observed_at: datetime
    source_updated_at: datetime | None = None
    source: str = "ryanair_farefinder"

    def __post_init__(self):
        if self.amount_minor < 0:
            raise ValueError("Cena nesmí být záporná.")
        carrier_for_source(self.source)
        if is_daily_minimum(self.source):
            if self.flight_number or self.arrival is not None:
                raise ValueError("Denní minimum nesmí předstírat konkrétní číslo letu ani čas příletu.")
        elif not self.flight_number or self.arrival is None:
            raise ValueError("Nabídka konkrétního letu musí obsahovat číslo letu a přílet.")
        for value in (self.departure, self.observed_at, *([self.arrival] if self.arrival is not None else [])):
            if value.tzinfo is None:
                raise ValueError("Čas musí obsahovat časové pásmo.")

    def matches(self, query: SearchQuery) -> bool:
        return (self.origin == query.origin and self.destination == query.destination
                and self.departure.date() == query.departure_date
                and (query.currency is None or self.currency == query.currency)
                and carrier_for_source(self.source) == query.carrier)
