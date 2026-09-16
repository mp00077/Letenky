"""Synthetic calendar responses based on the documented schema; no live fixtures."""
from datetime import date, timedelta
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from tests.test_core import NOW, sample_offer
from letenky.domain.flight import SearchQuery
from letenky.domain.price import timestamp
from letenky.domain.errors import InvalidResponse, ProviderError
from letenky.providers.wizzair.airports import bundled_airports
from letenky.providers.wizzair.parser import parse_timetable
from letenky.providers.wizzair.client import WizzairClient
from letenky.providers.registry import ProviderRegistry
from letenky.services.price_checker import PriceChecker
from letenky.storage.database import Database
from letenky.storage.repositories.watches import WatchRepository

QUERY = SearchQuery("BUD", "LTN", date(2026, 11, 20), None, "wizzair")
AIRPORTS = {a.code: a for a in bundled_airports()}


def payload():
    return {"outboundFlights": [{"departureStation": "BUD", "arrivalStation": "LTN",
        "departureDate": "2026-11-20T06:00:00", "hasMacFlight": False,
        "price": {"amount": 23016, "currencyCode": "HUF"},
        "departureDates": [{"date": "2026-11-20T06:00:00", "isCheapestOfTheDay": True},
                           {"date": "2026-11-20T08:30:00", "isCheapestOfTheDay": False}]}]}


def offer():
    return parse_timetable(payload(), QUERY, AIRPORTS, NOW)[0]


class WizzairTests(unittest.TestCase):
    def test_daily_quote_has_no_invented_flight_or_arrival(self):
        result = offer()
        self.assertEqual(result.amount_minor, 2301600)
        self.assertEqual(result.currency, "HUF")
        self.assertEqual(result.flight_number, "")
        self.assertIsNone(result.arrival)
        self.assertEqual(result.source, "wizzair_timetable")
        self.assertTrue(result.matches(QUERY))
        self.assertFalse(result.matches(replace(QUERY, currency="HUF", carrier="ryanair")))

    def test_empty_and_unpriced_days(self):
        self.assertEqual(parse_timetable({"outboundFlights": []}, QUERY, AIRPORTS, NOW), [])
        data = payload()
        data["outboundFlights"][0]["price"] = None
        self.assertEqual(parse_timetable(data, QUERY, AIRPORTS, NOW), [])

    def test_rejects_wrong_route_date_currency_and_alternative_airports(self):
        for key, value in (("departureStation", "PRG"), ("departureDate", "2026-11-21"),
                           ("hasMacFlight", True)):
            data = payload()
            data["outboundFlights"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ProviderError):
                parse_timetable(data, QUERY, AIRPORTS, NOW)
        with self.assertRaises(ProviderError):
            parse_timetable(payload(), replace(QUERY, currency="CZK"), AIRPORTS, NOW)

    def test_bad_prices_and_bad_schema_are_errors(self):
        for value in (-1, "NaN", "Infinity", "1.001", None):
            data = payload()
            data["outboundFlights"][0]["price"]["amount"] = value
            with self.subTest(value=value), self.assertRaises(InvalidResponse):
                parse_timetable(data, QUERY, AIRPORTS, NOW)
        for data in ({}, {"outboundFlights": None}, {"outboundFlights": [{}]},
                     {"outboundFlights": [], "handlerError": "denied"}):
            with self.assertRaises(InvalidResponse):
                parse_timetable(data, QUERY, AIRPORTS, NOW)

    def test_blocked_access_is_error_without_retry(self):
        for code in (403, 405, 429):
            client = WizzairClient()
            client._opener = Mock()
            client._opener.open.side_effect = HTTPError(client.HOME, code, "blocked", {}, None)
            with self.assertRaisesRegex(ProviderError, str(code)):
                client._request(client.HOME, html=True)
            self.assertEqual(client._opener.open.call_count, 1)

    def test_calendar_request_uses_regular_price_and_exact_day(self):
        client = WizzairClient()
        client._base = "https://be.wizzair.com/1.2.3/Api"
        with patch.object(client, "_prepare_session"), patch.object(client, "_request", return_value=payload()) as request:
            client.timetable(QUERY)
        url, body = request.call_args.args
        self.assertTrue(url.endswith("/search/timetableV2"))
        self.assertEqual(body["priceType"], "regular")
        self.assertEqual(body["flightList"][0]["from"], "2026-11-20")
        self.assertEqual(body["flightList"][0]["to"], "2026-11-20")

    def test_storage_routing_history_interval_and_expiration(self):
        with TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.db")
            db.initialize()
            repo = WatchRepository(db)
            ry_id = repo.add(sample_offer())
            wizz_id = repo.add(offer())
            repo.set_check_interval(60, NOW)
            wizz = Mock()
            wizz.search.return_value = [replace(offer(), amount_minor=2000000, observed_at=NOW + timedelta(hours=1))]
            ryanair = Mock()
            checker = PriceChecker(ProviderRegistry({"ryanair": ryanair, "wizzair": wizz}), repo,
                                   clock=lambda: NOW + timedelta(hours=1))
            self.assertTrue(checker.check(wizz_id))
            ryanair.search.assert_not_called()
            saved = repo.get(wizz_id)
            self.assertEqual(saved.query.carrier, "wizzair")
            self.assertEqual(saved.minimum_amount, 2000000)
            self.assertEqual(saved.latest_amount, 2000000)
            self.assertEqual(saved.query.currency, "HUF")
            self.assertEqual(saved.next_check_at, timestamp(NOW + timedelta(hours=2)))
            repo.expire(offer().departure + timedelta(hours=23))
            self.assertEqual(repo.get(wizz_id).state, "active")
            repo.expire(offer().departure + timedelta(days=1))
            self.assertEqual(repo.get(wizz_id).state, "completed")
            repo.delete(wizz_id)
            self.assertIsNotNone(repo.get(ry_id))
