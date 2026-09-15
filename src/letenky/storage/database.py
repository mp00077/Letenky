import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            migrations = sorted(Path(__file__).with_name("migrations").glob("*.sql"))
            if version > len(migrations):
                raise RuntimeError("Databáze pochází z novější verze aplikace.")
            for migration in migrations[version:]:
                next_version = int(migration.stem.split("_")[0])
                sql = migration.read_text(encoding="utf-8")
                connection.executescript(f"BEGIN IMMEDIATE;\n{sql}\nPRAGMA user_version = {next_version};\nCOMMIT;")
