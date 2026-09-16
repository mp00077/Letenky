CREATE TABLE monitor_settings (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    check_interval_minutes INTEGER NOT NULL DEFAULT 180
        CHECK(typeof(check_interval_minutes) = 'integer' AND check_interval_minutes BETWEEN 1 AND 10080)
);
INSERT INTO monitor_settings(id, check_interval_minutes) VALUES (1, 180);

-- A late worker result must never attach to a new watch that reused a deleted ID.
ALTER TABLE watches ADD COLUMN instance_key TEXT NOT NULL DEFAULT '';
UPDATE watches SET instance_key = lower(hex(randomblob(16)));
CREATE UNIQUE INDEX watches_instance_key ON watches(instance_key);
