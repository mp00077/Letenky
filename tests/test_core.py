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

    def test_delete_removes_history_and_orphan_flight(self):
        self.checker().check(self.watch_id)
        self.assertTrue(self.repo.delete(self.watch_id))
        self.assertIsNone(self.repo.get(self.watch_id))
        self.assertEqual(self.history.history(self.watch_id), [])
        with self.db.connect() as db:
            for table in ("flights", "watches", "check_runs", "price_observations"):
                self.assertEqual(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertFalse(self.repo.delete(self.watch_id))

    def test_delete_keeps_other_currency_watch_and_shared_flight(self):
        other_id = self.repo.add(replace(self.offer, currency="EUR", amount_minor=2500))
        self.repo.delete(self.watch_id)
        self.assertEqual(self.repo.get(other_id).latest_amount, 2500)
        self.assertEqual(len(self.history.history(other_id)), 1)
        with self.db.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM flights").fetchone()[0], 1)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_delete_failure_rolls_back_history(self):
        import sqlite3
        with self.db.connect() as db:
            db.execute("""CREATE TRIGGER prevent_delete BEFORE DELETE ON watches
                          BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.delete(self.watch_id)
        self.assertIsNotNone(self.repo.get(self.watch_id))
        self.assertEqual(len(self.history.history(self.watch_id)), 1)

    def test_late_result_cannot_recreate_deleted_or_reused_watch(self):
        old_watch = self.repo.get(self.watch_id)
        self.repo.delete(self.watch_id)
        self.assertFalse(self.repo.record_check(old_watch, NOW, NOW, "ok", offer=self.offer))
        new_id = self.repo.add(self.offer)
        self.assertEqual(new_id, old_watch.id)  # SQLite may reuse INTEGER PRIMARY KEYs.
        self.assertNotEqual(self.repo.get(new_id).instance_key, old_watch.instance_key)
        self.assertFalse(self.repo.record_check(old_watch, NOW, NOW, "ok", offer=self.offer))
        self.assertEqual(len(self.history.history(new_id)), 1)

    def test_custom_interval_applies_to_new_watches_and_failed_checks(self):
        self.repo.set_check_interval(45, NOW)
        new_id = self.repo.add(replace(self.offer, flight_number="FR2000"))
        self.assertEqual(self.repo.get(new_id).next_check_at, timestamp(NOW + timedelta(minutes=45)))
        with self.assertLogs("letenky.services.price_checker", level="ERROR"):
            self.checker(error=ProviderError("offline"), now=NOW).check(self.watch_id)
        self.assertEqual(self.repo.get(self.watch_id).next_check_at, timestamp(NOW + timedelta(minutes=45)))
        reopened = Database(self.db.path)
        reopened.initialize()
        self.assertEqual(WatchRepository(reopened).check_interval_minutes, 45)

    def test_interval_change_reschedules_from_last_check_and_clamps_overdue(self):
        self.checker(now=NOW + timedelta(hours=1)).check(self.watch_id)
        self.repo.set_check_interval(60, NOW + timedelta(hours=1, minutes=10))
        self.assertEqual(self.repo.get(self.watch_id).next_check_at, timestamp(NOW + timedelta(hours=2)))
        self.repo.set_check_interval(5, NOW + timedelta(hours=1, minutes=10))
        self.assertEqual(self.repo.get(self.watch_id).next_check_at, timestamp(NOW + timedelta(hours=1, minutes=10)))

    def test_interval_does_not_resume_paused_or_completed_watches(self):
        self.repo.set_paused(self.watch_id, True, NOW)
        before = self.repo.get(self.watch_id)
        self.repo.set_check_interval(1, NOW)
        self.assertEqual(self.repo.get(self.watch_id), before)
        self.repo.expire(self.offer.departure)
        before = self.repo.get(self.watch_id)
        self.repo.set_check_interval(10080, NOW)
        self.assertEqual(self.repo.get(self.watch_id), before)

    def test_invalid_interval_is_rejected_without_changing_schedule(self):
        before = self.repo.get(self.watch_id)
        for value in (0, -1, 10081, 2.5, "60", True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.repo.set_check_interval(value, NOW)
        self.assertEqual(self.repo.check_interval_minutes, 180)
        self.assertEqual(self.repo.get(self.watch_id), before)

    def test_running_check_uses_new_interval_when_finished(self):
        entered, release = Event(), Event()
        class SlowProvider:
            def search(_self, query):
                entered.set()
                release.wait(5)
                return [self.offer]
        finish = NOW + timedelta(hours=3)
        checker = PriceChecker(SlowProvider(), self.repo, lambda: finish)
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(checker.check, self.watch_id)
            try:
                self.assertTrue(entered.wait(3))
                self.repo.set_check_interval(30, finish)
            finally:
                release.set()
            self.assertTrue(result.result(5))
        self.assertEqual(self.repo.get(self.watch_id).next_check_at, timestamp(finish + timedelta(minutes=30)))

    def test_migration_preserves_existing_v1_watch_and_price(self):
        from tests.support import ROOT
        legacy = Database(Path(self.directory.name) / "legacy.sqlite3")
        with legacy.connect() as db:
            db.executescript((ROOT / "src/letenky/storage/migrations/001_initial.sql").read_text(encoding="utf-8"))
            db.execute("PRAGMA user_version=1")
            db.execute("""INSERT INTO flights VALUES (1,'PRG','STN','2026-11-20','FR1014',?,?,?)""",
                       (self.offer.departure.isoformat(), self.offer.arrival.isoformat(), timestamp(self.offer.departure)))
            db.execute("""INSERT INTO watches
                (id,flight_id,currency,source,created_at,next_check_at) VALUES (1,1,'CZK','ryanair_farefinder',?,?)""",
                       (timestamp(NOW), timestamp(NOW + timedelta(hours=3))))
            db.execute("INSERT INTO check_runs VALUES (1,1,?,?,'ok',NULL)", (timestamp(NOW), timestamp(NOW)))
            db.execute("INSERT INTO price_observations VALUES (1,1,1,1,?,56763,'CZK',NULL)", (timestamp(NOW),))
        legacy.initialize()
        repository = WatchRepository(legacy)
        self.assertEqual(repository.check_interval_minutes, 180)
        self.assertEqual(repository.get(1).latest_amount, 56763)
        self.assertEqual(len(repository.get(1).instance_key), 32)
        repository.set_check_interval(60, NOW)
        self.assertEqual(repository.get(1).next_check_at, timestamp(NOW + timedelta(hours=1)))


if __name__ == "__main__":
    unittest.main()
