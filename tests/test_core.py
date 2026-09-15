from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from tests.support import sample_payload
from letenky.domain.errors import DuplicateWatch, InvalidResponse, ProviderError
from letenky.domain.flight import SearchQuery
from letenky.domain.price import timestamp
from letenky.providers.ryanair.airports import bundled_airports
from letenky.providers.ryanair.parser import parse_fares
from letenky.services.price_checker import PriceChecker
from letenky.storage.database import Database
from letenky.storage.repositories.observations import ObservationRepository
from letenky.storage.repositories.watches import WatchRepository

NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
QUERY = SearchQuery("PRG", "STN", date(2026, 11, 20))
AIRPORTS = {airport.code: airport for airport in bundled_airports()}


def sample_offer():
    return parse_fares(sample_payload(), QUERY, AIRPORTS, NOW)[0]


class ParserTests(unittest.TestCase):
    def test_live_sample_currency_and_local_time(self):
        offer = sample_offer()
        self.assertEqual(offer.flight_number, "FR1014")
        self.assertEqual(offer.amount_minor, 56763)
        self.assertEqual(offer.departure.utcoffset(), timedelta(hours=1))
        self.assertEqual(offer.arrival.utcoffset(), timedelta(0))
        self.assertEqual(offer.departure.astimezone(timezone.utc).hour, 14)
        self.assertIsNotNone(offer.source_updated_at)

    def test_empty_result_is_valid(self):
        self.assertEqual(parse_fares({"fares": []}, QUERY, AIRPORTS, NOW), [])

    def test_malformed_is_not_no_flight(self):
        for payload in ({}, {"fares": None}, {"fares": [{}]}, {"fares": [], "nextPage": "more"}):
            with self.subTest(payload=payload), self.assertRaises(InvalidResponse):
                parse_fares(payload, QUERY, AIRPORTS, NOW)

    def test_wrong_currency_route_or_date_is_rejected(self):
        for query in (replace(QUERY, currency="EUR"), replace(QUERY, destination="DUB"),
                      replace(QUERY, departure_date=date(2026, 11, 21))):
            with self.subTest(query=query), self.assertRaises(InvalidResponse):
                parse_fares(sample_payload(), query, AIRPORTS, NOW)

    def test_invalid_prices_rejected(self):
        for price in (-1, "NaN", "Infinity", "10.999", None):
            payload = sample_payload()
            payload["fares"][0]["outbound"]["price"]["value"] = price
            with self.subTest(price=price), self.assertRaises(InvalidResponse):
                parse_fares(payload, QUERY, AIRPORTS, NOW)

    def test_summer_timezone(self):
        payload = sample_payload()
        payload["fares"][0]["outbound"].update(departureDate="2026-07-20T15:30:00", arrivalDate="2026-07-20T16:30:00")
        offer = parse_fares(payload, replace(QUERY, departure_date=date(2026, 7, 20)), AIRPORTS, NOW)[0]
        self.assertEqual(offer.departure.utcoffset(), timedelta(hours=2))
        self.assertEqual(offer.arrival.utcoffset(), timedelta(hours=1))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = Database(Path(self.directory.name) / "test.sqlite3")
        self.db.initialize()
        self.repo = WatchRepository(self.db)
        self.history = ObservationRepository(self.db)
        self.offer = sample_offer()
        self.watch_id = self.repo.add(self.offer)

    def checker(self, offers=None, error=None, now=NOW + timedelta(hours=3)):
        class Provider:
            def search(_self, query):
                if error:
                    raise error
                return offers if offers is not None else [replace(self.offer, observed_at=now)]
        return PriceChecker(Provider(), self.repo, lambda: now)

    def test_atomic_initial_save_and_duplicate(self):
        self.assertEqual(len(self.history.history(self.watch_id)), 1)
        with self.assertRaises(DuplicateWatch):
            self.repo.add(replace(self.offer, departure=self.offer.departure + timedelta(minutes=30)))
        self.assertEqual(len(self.repo.list()), 1)
        self.assertEqual(self.repo.get(self.watch_id).departure_local, self.offer.departure.isoformat())

    def test_minimum_unchanged_and_new_measurements_persist(self):
        self.checker().check(self.watch_id)
        cheaper = replace(self.offer, amount_minor=49900, observed_at=NOW + timedelta(hours=6))
        self.checker([cheaper], now=NOW + timedelta(hours=6)).check(self.watch_id)
        higher = replace(self.offer, amount_minor=69900, observed_at=NOW + timedelta(hours=9))
        self.checker([higher], now=NOW + timedelta(hours=9)).check(self.watch_id)
        watch = self.repo.get(self.watch_id)
        self.assertEqual(watch.minimum_amount, 49900)
        self.assertEqual(watch.minimum_at, timestamp(cheaper.observed_at))
        self.assertEqual(watch.latest_amount, 69900)
        self.assertEqual(len(self.history.history(self.watch_id)), 4)
        reopened = Database(self.db.path)
        reopened.initialize()
        self.assertEqual(WatchRepository(reopened).get(self.watch_id), watch)

    def test_error_keeps_last_price_and_next_deadline(self):
        with self.assertLogs("letenky.services.price_checker", level="ERROR"):
            self.checker(error=ProviderError("HTTP 429")).check(self.watch_id)
        watch = self.repo.get(self.watch_id)
        self.assertEqual(watch.last_status, "error")
        self.assertEqual(watch.latest_amount, self.offer.amount_minor)
        self.assertEqual(watch.next_check_at, timestamp(NOW + timedelta(hours=6)))
        self.assertIsNone(self.history.history(self.watch_id)[-1]["amount_minor"])

    def test_other_flight_never_overwrites_watched_flight(self):
        self.checker([replace(self.offer, flight_number="FR9999", amount_minor=100)]).check(self.watch_id)
        watch = self.repo.get(self.watch_id)
        self.assertEqual(watch.last_status, "not_offered")
        self.assertEqual(watch.latest_amount, 56763)
        self.assertIsNone(self.history.history(self.watch_id)[-1]["amount_minor"])

    def test_pause_resume_and_expiration(self):
        self.repo.set_paused(self.watch_id, True, NOW)
        self.assertEqual(self.repo.due(NOW + timedelta(days=1)), [])
        self.assertFalse(self.checker().check(self.watch_id))
        self.repo.set_paused(self.watch_id, False, NOW)
        self.assertEqual(len(self.repo.due(NOW)), 1)
        self.repo.expire(self.offer.departure)
        self.assertEqual(self.repo.get(self.watch_id).state, "completed")
        self.repo.set_paused(self.watch_id, False, NOW)
        self.assertEqual(self.repo.get(self.watch_id).state, "completed")

    def test_missed_checks_run_once(self):
        now = NOW + timedelta(days=4)
        self.assertEqual(len(self.repo.due(now)), 1)
        self.checker(now=now).check(self.watch_id)
        self.assertEqual(self.repo.due(now), [])
        self.assertEqual(len(self.history.history(self.watch_id)), 2)

    def test_concurrent_duplicate_check_is_skipped(self):
        entered, release = Event(), Event()
        class SlowProvider:
            def search(_self, query):
                entered.set()
                release.wait(5)
                return [self.offer]
        checker = PriceChecker(SlowProvider(), self.repo, lambda: NOW + timedelta(hours=3))
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(checker.check, self.watch_id)
            self.assertTrue(entered.wait(3))
            try:
                self.assertFalse(checker.check(self.watch_id))
            finally:
                release.set()
            self.assertTrue(first.result(5))
        self.assertEqual(len(self.history.history(self.watch_id)), 2)

    def test_schema_from_future_is_rejected(self):
        with self.db.connect() as db:
            db.execute("PRAGMA user_version = 999")
        with self.assertRaises(RuntimeError):
            self.db.initialize()


if __name__ == "__main__":
    unittest.main()
