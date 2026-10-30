"""Small SQLite store for the single-user demo: chat, quote versions, review events."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .costs import INITIAL_FEED_VERSION

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quote_versions (
    quote_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    offer_revenue TEXT NOT NULL,
    feed_version TEXT NOT NULL,
    appraisal TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (quote_id, version)
);
CREATE TABLE IF NOT EXISTS review_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id TEXT NOT NULL,
    quote_version INTEGER NOT NULL,
    feed_version TEXT NOT NULL,
    previous_feed_version TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    revised_appraisal TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (quote_id, quote_version, feed_version)
);
"""

CHAT_RETENTION = 200  # Transient display history only; quotes/review records are never pruned.


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    # -- key/value ---------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock, self._connect() as db:
            row = db.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set(self, key: str, value: Any) -> None:
        with self._lock, self._connect() as db:
            db.execute("INSERT INTO kv (key, value) VALUES (?, ?) "
                       "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, json.dumps(value)))

    def active_feed_version(self) -> str:
        return self.get("active_feed_version", INITIAL_FEED_VERSION)

    # -- chat ----------------------------------------------------------------
    def add_message(self, role: str, payload: dict[str, Any]) -> None:
        with self._lock, self._connect() as db:
            db.execute("INSERT INTO messages (role, payload, created_at) VALUES (?, ?, ?)",
                       (role, json.dumps(payload), _now()))
            db.execute("DELETE FROM messages WHERE id NOT IN "
                       "(SELECT id FROM messages ORDER BY id DESC LIMIT ?)", (CHAT_RETENTION,))

    def messages(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT role, payload, created_at FROM messages ORDER BY id").fetchall()
        return [{"role": r["role"], "created_at": r["created_at"], **json.loads(r["payload"])} for r in rows]

    # -- quote versions --------------------------------------------------------
    def latest_quote(self, quote_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as db:
            row = db.execute("SELECT * FROM quote_versions WHERE quote_id = ? ORDER BY version DESC LIMIT 1",
                             (quote_id,)).fetchone()
        return self._quote_row(row) if row else None

    def quote_versions(self, quote_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM quote_versions WHERE quote_id = ? ORDER BY version",
                              (quote_id,)).fetchall()
        return [self._quote_row(row) for row in rows]

    def add_quote_version(self, quote_id: str, version: int, offer_revenue: str, feed_version: str,
                          appraisal: dict[str, Any]) -> dict[str, Any]:
        """Versions are immutable once written; a price or assumption change adds a new one."""
        with self._lock, self._connect() as db:
            db.execute("INSERT INTO quote_versions VALUES (?, ?, ?, ?, ?, ?)",
                       (quote_id, version, offer_revenue, feed_version, json.dumps(appraisal), _now()))
        return self.latest_quote(quote_id)

    @staticmethod
    def _quote_row(row: sqlite3.Row) -> dict[str, Any]:
        return {"quote_id": row["quote_id"], "version": row["version"], "offer_revenue": row["offer_revenue"],
                "feed_version": row["feed_version"], "created_at": row["created_at"],
                "appraisal": json.loads(row["appraisal"])}

    # -- review events -----------------------------------------------------------
    def add_review_event(self, *, quote_id: str, quote_version: int, feed_version: str,
                         previous_feed_version: str, source: str,
                         revised_appraisal: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Insert once per quote version and feed version; return (event, created)."""
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO review_events (quote_id, quote_version, feed_version, previous_feed_version,"
                " source, status, revised_appraisal, created_at) VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
                (quote_id, quote_version, feed_version, previous_feed_version, source,
                 json.dumps(revised_appraisal), _now()))
            created = cursor.rowcount == 1
            row = db.execute("SELECT * FROM review_events WHERE quote_id = ? AND quote_version = ? "
                             "AND feed_version = ?", (quote_id, quote_version, feed_version)).fetchone()
        return self._event_row(row), created

    def review_events(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM review_events ORDER BY id").fetchall()
        return [self._event_row(row) for row in rows]

    @staticmethod
    def _event_row(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["revised_appraisal"] = json.loads(data["revised_appraisal"])
        return data

    # -- reset ---------------------------------------------------------------
    def reset(self) -> None:
        with self._lock, self._connect() as db:
            db.executescript("DELETE FROM kv; DELETE FROM messages; DELETE FROM quote_versions; "
                             "DELETE FROM review_events; DELETE FROM sqlite_sequence;")
