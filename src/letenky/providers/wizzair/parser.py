from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from letenky.domain.errors import InvalidResponse, ProviderError
from letenky.domain.flight import FlightOffer
from letenky.domain.price import currency_factor


def parse_timetable(payload, query, airports, observed_at):
    """One route/day quote, never assign its price to every listed departure."""
    try:
        if not isinstance(payload, dict) or not isinstance(payload.get("outboundFlights"), list):
            raise ValueError("missing outboundFlights")
        if payload.get("handlerError") or payload.get("validationCodes"):
            raise ValueError("upstream rejected search")
        results = []
        for row in payload["outboundFlights"]:
            if row["departureStation"] != query.origin or row["arrivalStation"] != query.destination:
                raise ValueError("wrong route")
            day = datetime.fromisoformat(row["departureDate"]).date()
            if day != query.departure_date:
                raise ValueError("wrong day")
            if row.get("hasMacFlight") is True:
                raise ProviderError("Wizz Air zahrnul alternativní letiště. Cenu nelze bezpečně přiřadit k vybrané trase.")
            price = row["price"]
            if price is None:
                continue
            currency = price["currencyCode"]
            if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha() or not currency.isupper():
                raise ValueError("invalid currency")
            if query.currency is not None and currency != query.currency:
                raise ProviderError(f"Wizz Air vrátil měnu {currency} místo uložené {query.currency}. Cena nebyla přidána do historie.")
            amount = Decimal(str(price["amount"])) * currency_factor(currency)
            if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
                raise ValueError("invalid price")
            # A day boundary represents the quote's scope, not a fictitious flight.
            departure = datetime.combine(day, time.min, ZoneInfo(airports[query.origin].timezone))
            offer = FlightOffer(query.origin, query.destination, "", departure, None,
                                int(amount), currency, observed_at, source="wizzair_timetable")
            if not offer.matches(query):
                raise ValueError("wrong provider")
            results.append(offer)
        if len(results) > 1:
            raise ValueError("ambiguous daily minimum")
        return results
    except (KeyError, ValueError, TypeError, AttributeError, InvalidOperation, OverflowError) as exc:
        raise InvalidResponse("Formát cenového kalendáře Wizz Air se změnil nebo neodpovídá dotazu.") from exc
