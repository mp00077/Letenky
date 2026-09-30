CREATE TABLE watch_tabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) BETWEEN 1 AND 60)
);
INSERT INTO watch_tabs(id,name) VALUES (1,'Ostatní');
-- NULL keeps legacy watches in the default tab without rewriting their history.
ALTER TABLE watches ADD COLUMN tab_id INTEGER REFERENCES watch_tabs(id);
