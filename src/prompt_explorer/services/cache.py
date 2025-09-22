"""Persistent metadata cache backed by SQLite."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Iterable, Optional

from ..models import PromptEntry


class PromptMetadataCache:
    """Stores prompt metadata keyed by file path for fast reloads."""

    def __init__(self, db_path: os.PathLike[str] | str) -> None:
        self._db_path = Path(db_path)
        self._lock = Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prompts (
                    path TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    modified_ts REAL NOT NULL,
                    file_size INTEGER NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prompts_mtime ON prompts(modified_ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prompts_size ON prompts(file_size)")
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, path: os.PathLike[str] | str, modified_ts: float, file_size: int) -> Optional[PromptEntry]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM prompts WHERE path = ? AND modified_ts = ? AND file_size = ?",
                (str(path), modified_ts, file_size),
            ).fetchone()
            if row:
                return PromptEntry(
                    path=Path(row["path"]),
                    prompt=row["prompt"],
                    width=int(row["width"]),
                    height=int(row["height"]),
                    modified_ts=float(row["modified_ts"]),
                    file_size=int(row["file_size"]),
                )
            return None

    def put(self, entry: PromptEntry) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO prompts (path, prompt, width, height, modified_ts, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    prompt=excluded.prompt,
                    width=excluded.width,
                    height=excluded.height,
                    modified_ts=excluded.modified_ts,
                    file_size=excluded.file_size
                """,
                (
                    str(entry.path),
                    entry.prompt,
                    entry.width,
                    entry.height,
                    entry.modified_ts,
                    entry.file_size,
                ),
            )
            conn.commit()

    def prune_missing(self, existing_paths: Iterable[str | os.PathLike[str]]) -> None:
        """Remove cache entries for files no longer present."""
        normalized = {os.fspath(Path(path)) for path in existing_paths}
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT path FROM prompts").fetchall()
            stale = [row["path"] for row in rows if row["path"] not in normalized]
            if stale:
                conn.executemany("DELETE FROM prompts WHERE path = ?", ((path,) for path in stale))
                conn.commit()

