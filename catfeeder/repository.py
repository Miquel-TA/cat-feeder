"""Persistence layer for donations."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict

import aiosqlite

LOGGER = logging.getLogger(__name__)


class DonationRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        await self._ensure_directory()
        LOGGER.info("Connecting to donation database at %s", self._db_path)
        self._connection = await aiosqlite.connect(self._db_path)
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS donations (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                platform TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                message TEXT,
                donor_note TEXT,
                tier_name TEXT NOT NULL,
                motor INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await self._ensure_column("donor_note", "ALTER TABLE donations ADD COLUMN donor_note TEXT")
        await self._connection.commit()

    async def save(self, payload: Dict[str, Any]) -> None:
        if self._connection is None:
            raise RuntimeError("Repository has not been initialised")
        async with self._lock:
            await self._connection.execute(
                """
                INSERT OR REPLACE INTO donations (
                    id, username, platform, amount, currency, message, donor_note, tier_name, motor, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["username"],
                    payload["platform"],
                    payload["amount"],
                    payload["currency"],
                    payload.get("message"),
                    payload.get("donor_note"),
                    payload.get("name"),
                    payload.get("motor"),
                    payload["created_at"],
                ),
            )
            await self._connection.commit()

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def _ensure_directory(self) -> None:
        path = Path(self._db_path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

    async def _ensure_column(self, column: str, alter_statement: str) -> None:
        if self._connection is None:
            return
        cursor = await self._connection.execute("PRAGMA table_info(donations)")
        rows = await cursor.fetchall()
        columns = [row[1] for row in rows]
        if column not in columns:
            await self._connection.execute(alter_statement)
