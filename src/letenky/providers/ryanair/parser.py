from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from letenky.domain.errors import InvalidResponse
from letenky.domain.flight import Airport, FlightOffer, SearchQuery


def parse_fares(payload, query: SearchQuery, airports: dict[str, Airport],
                observed_at: datetime) -> list[FlightOffer]:
    """Fare Finder is an indicative offers feed, not a full flight timetable."""
    try:
        if not isinstance(payload, dict) or not isinstance(payload.get("fares"), list):
            raise ValueError("missing fares")
        if payload.get("nextPage"):
            raise ValueError("unexpected pagination for one route and date")
        result = []
        for item in payload["fares"]:
            outbound = item["outbound"]
            origin = outbound["departureAirport"]["iataCode"]
            destination = outbound["arrivalAirport"]["iataCode"]
            departure = datetime.fromisoformat(outbound["departureDate"])
            arrival = datetime.fromisoformat(outbound["arrivalDate"])
            if departure.tzinfo is None:
                departure = departure.replace(tzinfo=ZoneInfo(airports[origin].timezone))
            if arrival.tzinfo is None:
                arrival = arrival.replace(tzinfo=ZoneInfo(airports[destination].timezone))
            amount = Decimal(str(outbound["price"]["value"])) * 100
            if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
                raise ValueError("invalid price")
            updated = outbound.get("priceUpdated")
            offer = FlightOffer(
                origin, destination, outbound["flightNumber"].replace(" ", ""),
                departure, arrival, int(amount), outbound["price"]["currencyCode"], observed_at,
                datetime.fromtimestamp(updated / 1000, timezone.utc) if updated is not None else None,
            )
            if not offer.matches(query):
                raise ValueError("response does not match requested route, date or currency")
            if not offer.flight_number or arrival.astimezone(timezone.utc) <= departure.astimezone(timezone.utc):
                raise ValueError("invalid flight")
            result.append(offer)
        return sorted(result, key=lambda offer: offer.departure)
    except (KeyError, ValueError, TypeError, AttributeError, InvalidOperation, OverflowError) as exc:
        raise InvalidResponse("Formát nabídky Ryanairu se změnil nebo neodpovídá dotazu.") from exc
