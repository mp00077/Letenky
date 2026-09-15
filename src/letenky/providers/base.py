from typing import Protocol

from letenky.domain.flight import Airport, FlightOffer, SearchQuery


class FlightProvider(Protocol):
    def airports(self) -> list[Airport]: ...

    def search(self, query: SearchQuery) -> list[FlightOffer]: ...
