import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4

from letenky.domain.errors import DuplicateWatch
from letenky.domain.price import timestamp
from letenky.domain.watch import Watch


class WatchRepository:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def _interval_minutes(db):
        return db.execute("SELECT check_interval_minutes FROM monitor_settings WHERE id=1").fetchone()[0]

    @property
    def check_interval_minutes(self):
        with self.database.connect() as db:
            return self._interval_minutes(db)

    def set_check_interval(self, minutes, now):
        if type(minutes) is not int or not 1 <= minutes <= 10080:
            raise ValueError("Interval musí být celé číslo od 1 do 10 080 minut.")
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self._interval_minutes(db) == minutes:
                return
            db.execute("UPDATE monitor_settings SET check_interval_minutes=? WHERE id=1", (minutes,))
            rows = db.execute("""SELECT w.id, COALESCE(
                (SELECT finished_at FROM check_runs WHERE watch_id=w.id ORDER BY id DESC LIMIT 1),
                w.created_at) last_check FROM watches w JOIN flights f ON f.id=w.flight_id
                WHERE w.state='active' AND f.departure_utc>?""", (timestamp(now),)).fetchall()
            for row in rows:
                due = datetime.fromisoformat(row["last_check"]) + timedelta(minutes=minutes)
                db.execute("UPDATE watches SET next_check_at=? WHERE id=?",
                           (timestamp(max(now, due)), row["id"]))

    def add(self, offer):
        now = timestamp(offer.observed_at)
        try:
            with self.database.connect() as db:
                db.execute("""INSERT INTO flights
                    (origin,destination,departure_date,flight_number,departure_local,arrival_local,departure_utc)
                    VALUES (?,?,?,?,?,?,?) ON CONFLICT(origin,destination,departure_date,flight_number)
                    DO UPDATE SET departure_local=excluded.departure_local,
                    arrival_local=excluded.arrival_local, departure_utc=excluded.departure_utc""",
                    (offer.origin, offer.destination, offer.departure.date().isoformat(),
                     offer.flight_number, offer.departure.isoformat(), offer.arrival.isoformat(),
                     timestamp(offer.departure)))
                flight_id = db.execute("""SELECT id FROM flights WHERE origin=? AND destination=?
                    AND departure_date=? AND flight_number=?""", (offer.origin, offer.destination,
                    offer.departure.date().isoformat(), offer.flight_number)).fetchone()[0]
                watch_id = db.execute("""INSERT INTO watches
                    (flight_id,currency,source,created_at,next_check_at,instance_key) VALUES (?,?,?,?,?,?)""",
                    (flight_id, offer.currency, offer.source, now,
                     timestamp(offer.observed_at + timedelta(minutes=self._interval_minutes(db))),
                     uuid4().hex)).lastrowid
                run_id = db.execute("""INSERT INTO check_runs
                    (watch_id,started_at,finished_at,status) VALUES (?,?,?,'ok')""",
                    (watch_id, now, now)).lastrowid
                self.insert_observation(db, watch_id, flight_id, run_id, offer)
                return watch_id
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed: watches." in str(exc):
                raise DuplicateWatch("Tento let již sledujete v této měně.") from exc
            raise

    @staticmethod
    def insert_observation(db, watch_id, flight_id, run_id, offer):
        db.execute("""INSERT INTO price_observations
            (watch_id,flight_id,check_run_id,observed_at,amount_minor,currency,source_updated_at)
            VALUES (?,?,?,?,?,?,?)""", (watch_id, flight_id, run_id, timestamp(offer.observed_at),
            offer.amount_minor, offer.currency,
            timestamp(offer.source_updated_at) if offer.source_updated_at else None))

    def list(self):
        with self.database.connect() as db:
            rows = db.execute("""SELECT w.id,w.instance_key,w.flight_id,f.origin,f.destination,f.departure_date,
                f.flight_number,f.departure_local,f.departure_utc,w.currency,w.state,w.next_check_at,
                c.status last_status,c.error last_error,c.finished_at checked_at,
                p.amount_minor latest_amount,p.observed_at latest_at,
                (SELECT amount_minor FROM price_observations WHERE watch_id=w.id
                 ORDER BY observed_at DESC,id DESC LIMIT 1 OFFSET 1) previous_amount,
                m.amount_minor minimum_amount,m.observed_at minimum_at
                FROM watches w JOIN flights f ON f.id=w.flight_id
                LEFT JOIN check_runs c ON c.id=(SELECT id FROM check_runs WHERE watch_id=w.id ORDER BY id DESC LIMIT 1)
                LEFT JOIN price_observations p ON p.id=(SELECT id FROM price_observations WHERE watch_id=w.id ORDER BY observed_at DESC,id DESC LIMIT 1)
                LEFT JOIN price_observations m ON m.id=(SELECT id FROM price_observations WHERE watch_id=w.id ORDER BY amount_minor,observed_at,id LIMIT 1)
                ORDER BY f.departure_utc,w.id""").fetchall()
        return [Watch(**dict(row)) for row in rows]

    def get(self, watch_id):
        return next((watch for watch in self.list() if watch.id == watch_id), None)

    def due(self, now):
        return [watch for watch in self.list() if watch.state == "active" and watch.next_check_at <= timestamp(now)]

    def expire(self, now):
        with self.database.connect() as db:
            db.execute("""UPDATE watches SET state='completed' WHERE state!='completed'
                AND flight_id IN (SELECT id FROM flights WHERE departure_utc<=?)""", (timestamp(now),))

    def set_paused(self, watch_id, paused, now):
        with self.database.connect() as db:
            db.execute("""UPDATE watches SET state=?,next_check_at=? WHERE id=? AND state!='completed'""",
                       ("paused" if paused else "active", timestamp(now), watch_id))

    def record_check(self, watch, started_at, finished_at, status, error=None, offer=None):
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT id FROM watches WHERE id=? AND instance_key=?",
                          (watch.id, watch.instance_key)).fetchone() is None:
                return False
            run_id = db.execute("""INSERT INTO check_runs
                (watch_id,started_at,finished_at,status,error) VALUES (?,?,?,?,?)""",
                (watch.id, timestamp(started_at), timestamp(finished_at), status, error)).lastrowid
            if offer is not None:
                self.insert_observation(db, watch.id, watch.flight_id, run_id, offer)
                db.execute("UPDATE flights SET departure_local=?,arrival_local=?,departure_utc=? WHERE id=?",
                           (offer.departure.isoformat(), offer.arrival.isoformat(),
                            timestamp(offer.departure), watch.flight_id))
            db.execute("UPDATE watches SET next_check_at=? WHERE id=?",
                       (timestamp(finished_at + timedelta(minutes=self._interval_minutes(db))), watch.id))
            return True

    def delete(self, watch_id):
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            watch = db.execute("SELECT flight_id FROM watches WHERE id=?", (watch_id,)).fetchone()
            if watch is None:
                return False
            db.execute("DELETE FROM price_observations WHERE watch_id=?", (watch_id,))
            db.execute("DELETE FROM check_runs WHERE watch_id=?", (watch_id,))
            db.execute("DELETE FROM watches WHERE id=?", (watch_id,))
            db.execute("DELETE FROM flights WHERE id=? AND NOT EXISTS (SELECT 1 FROM watches WHERE flight_id=?)",
                       (watch["flight_id"], watch["flight_id"]))
            return True
