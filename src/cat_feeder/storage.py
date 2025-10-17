"""SQLite storage helpers for donations."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import Donation


SCHEMA = """
CREATE TABLE IF NOT EXISTS donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    coins INTEGER NOT NULL,
    tier INTEGER NOT NULL,
    tier_name TEXT NOT NULL,
    message TEXT NOT NULL,
    platform_message TEXT,
    profile_picture TEXT,
    created_at TEXT NOT NULL
);
"""


class DonationStore:
    """Persist donation events to disk for auditing and recovery."""

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self._path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def add(self, donation: Donation) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO donations (
                    username, coins, tier, tier_name, message,
                    platform_message, profile_picture, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    donation.username,
                    donation.coins,
                    donation.tier,
                    donation.tier_name,
                    donation.message,
                    donation.platform_message,
                    donation.profile_picture,
                    donation.created_at.isoformat(),
                ),
            )

    def list_recent(self, limit: int = 50) -> Iterable[Donation]:
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT username, coins, tier, tier_name, message, platform_message, profile_picture, created_at "
                "FROM donations ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            for row in cursor.fetchall():
                yield Donation(
                    username=row[0],
                    coins=row[1],
                    tier=row[2],
                    tier_name=row[3],
                    message=row[4],
                    platform_message=row[5],
                    profile_picture=row[6],
                    created_at=datetime.fromisoformat(row[7]),
                )
