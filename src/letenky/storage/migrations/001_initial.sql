CREATE TABLE flights (
    id INTEGER PRIMARY KEY,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    flight_number TEXT NOT NULL,
    departure_local TEXT NOT NULL,
    arrival_local TEXT NOT NULL,
    departure_utc TEXT NOT NULL,
    UNIQUE(origin, destination, departure_date, flight_number)
);
CREATE TABLE watches (
    id INTEGER PRIMARY KEY,
    flight_id INTEGER NOT NULL REFERENCES flights(id),
    currency TEXT NOT NULL,
    adults INTEGER NOT NULL DEFAULT 1 CHECK(adults = 1),
    fare_type TEXT NOT NULL DEFAULT 'basic' CHECK(fare_type = 'basic'),
    source TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'active' CHECK(state IN ('active', 'paused', 'completed')),
    created_at TEXT NOT NULL,
    next_check_at TEXT NOT NULL,
    UNIQUE(flight_id, currency, adults, fare_type, source)
);
CREATE TABLE check_runs (
    id INTEGER PRIMARY KEY,
    watch_id INTEGER NOT NULL REFERENCES watches(id),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ok', 'not_offered', 'error')),
    error TEXT
);
CREATE TABLE price_observations (
    id INTEGER PRIMARY KEY,
    watch_id INTEGER NOT NULL REFERENCES watches(id),
    flight_id INTEGER NOT NULL REFERENCES flights(id),
    check_run_id INTEGER NOT NULL UNIQUE REFERENCES check_runs(id),
    observed_at TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK(amount_minor >= 0),
    currency TEXT NOT NULL,
    source_updated_at TEXT
);
CREATE INDEX observations_watch_time ON price_observations(watch_id, observed_at DESC, id DESC);
CREATE INDEX observations_watch_price ON price_observations(watch_id, amount_minor, observed_at);
CREATE INDEX checks_watch_time ON check_runs(watch_id, id DESC);
CREATE INDEX watches_next_check ON watches(state, next_check_at);
