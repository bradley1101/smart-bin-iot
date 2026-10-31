import sqlite3
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS bins (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    location    TEXT NOT NULL,
    alert_sent  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS readings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    bin_id    TEXT NOT NULL REFERENCES bins(id),
    ts        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    level     INTEGER NOT NULL,
    lid_open  INTEGER NOT NULL DEFAULT 0,
    rssi      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_readings_bin_ts ON readings(bin_id, ts);
CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    bin_id  TEXT NOT NULL REFERENCES bins(id),
    ts      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    kind    TEXT NOT NULL,          -- FULL_ALERT | EMPTIED
    level   INTEGER NOT NULL,
    detail  TEXT
);
"""

DEFAULT_BINS = [
    ("bin-1", "Poubelle 1", "IFRI — entrée principale"),
    ("bin-2", "Poubelle 2", "IFRI — cafétéria"),
]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.executemany("INSERT OR IGNORE INTO bins (id, name, location) VALUES (?, ?, ?)", DEFAULT_BINS)
    db.commit()
