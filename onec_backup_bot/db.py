from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Iterable
import datetime as dt

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    path TEXT,
                    status TEXT NOT NULL,
                    size_bytes INTEGER,
                    duration_sec REAL,
                    rc INTEGER,
                    stderr TEXT,
                    fingerprint TEXT
                )
                """
            )
            # ensure metrics table
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    cpu_percent REAL,
                    mem_percent REAL,
                    disk_percent REAL
                )
                """
            )
            conn.commit()

    def insert_backup(self, *, ts: dt.datetime, path: Optional[str], status: str,
                      size_bytes: Optional[int], duration_sec: Optional[float], rc: Optional[int], stderr: Optional[str],
                      fingerprint: Optional[str] = None):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO backups(ts, path, status, size_bytes, duration_sec, rc, stderr, fingerprint) VALUES(?,?,?,?,?,?,?,?)",
                (ts.isoformat(timespec='seconds'), path, status, size_bytes, duration_sec, rc, stderr, fingerprint)
            )
            conn.commit()

    def recent_backups(self, limit: int = 10) -> Iterable[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM backups ORDER BY id DESC LIMIT ?", (limit,))
            return list(cur.fetchall())

    def last_success(self) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM backups WHERE status='OK' ORDER BY id DESC LIMIT 1")
            return cur.fetchone()

    def last_fingerprint(self) -> Optional[str]:
        with self._connect() as conn:
            cur = conn.execute("SELECT fingerprint FROM backups WHERE fingerprint IS NOT NULL AND status IN ('OK','SKIP') ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None

    def insert_metrics(self, *, ts: dt.datetime, cpu_percent: float, mem_percent: float, disk_percent: float):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO metrics(ts, cpu_percent, mem_percent, disk_percent) VALUES(?,?,?,?)",
                (ts.isoformat(timespec='seconds'), cpu_percent, mem_percent, disk_percent)
            )
            conn.commit()

    def last_metrics(self) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM metrics ORDER BY id DESC LIMIT 1")
            return cur.fetchone()
