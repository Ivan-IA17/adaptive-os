"""Persistent state management using SQLite."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite


class StateDB:
    """Async SQLite wrapper for storing profile history and context snapshots."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self._path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS profile_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile     TEXT    NOT NULL,
                    switched_at TEXT    NOT NULL,
                    reason      TEXT,
                    confidence  REAL,
                    triggered_by TEXT DEFAULT 'auto'
                );

                CREATE TABLE IF NOT EXISTS context_snapshots (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot    TEXT    NOT NULL,
                    recorded_at TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kv (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            await db.commit()

    async def get(self, key: str, default: Any = None) -> Any:
        async with aiosqlite.connect(self._path) as db:
            async with db.execute("SELECT value FROM kv WHERE key = ?", (key,)) as cur:
                row = await cur.fetchone()
                return json.loads(row[0]) if row else default

    async def set(self, key: str, value: Any) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )
            await db.commit()

    async def record_switch(
        self,
        profile: str,
        reason: str = "",
        confidence: float = 1.0,
        triggered_by: str = "auto",
    ) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """INSERT INTO profile_history
                   (profile, switched_at, reason, confidence, triggered_by)
                   VALUES (?, ?, ?, ?, ?)""",
                (profile, datetime.utcnow().isoformat(), reason, confidence, triggered_by),
            )
            await db.commit()

    async def record_snapshot(self, snapshot: dict[str, Any]) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO context_snapshots (snapshot, recorded_at) VALUES (?, ?)",
                (json.dumps(snapshot), datetime.utcnow().isoformat()),
            )
            await db.commit()

    async def recent_profiles(self, n: int = 5) -> list[str]:
        """Return the last N profile names from history."""
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                "SELECT profile FROM profile_history ORDER BY id DESC LIMIT ?", (n,)
            ) as cur:
                rows = await cur.fetchall()
                return [r[0] for r in rows]

    async def recent_snapshots(self, n: int = 3) -> list[dict[str, Any]]:
        """Return the last N context snapshots."""
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                "SELECT snapshot FROM context_snapshots ORDER BY id DESC LIMIT ?", (n,)
            ) as cur:
                rows = await cur.fetchall()
                return [json.loads(r[0]) for r in rows]
