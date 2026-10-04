"""SQLite index of runs. The schema lives in db/schema.sql."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from worldview_agents.paths import db_path, schema_path

RUN_COLUMNS: tuple[str, ...] = (
    "run_id",
    "grid_name",
    "worldview",
    "worldview_hash",
    "model",
    "task_id",
    "task_hash",
    "seed",
    "temperature",
    "status",
    "error",
    "started_at",
    "finished_at",
    "n_calls",
    "prompt_tokens",
    "completion_tokens",
    "latency_ms",
    "cost_usd",
    "git_commit",
    "run_dir",
)

_write_lock = threading.Lock()


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.executescript(schema_path().read_text())
    return conn


def upsert_run(row: dict[str, Any], path: Path | None = None) -> None:
    values = [row.get(col) for col in RUN_COLUMNS]
    placeholders = ", ".join("?" for _ in RUN_COLUMNS)
    updates = ", ".join(f"{c} = excluded.{c}" for c in RUN_COLUMNS if c != "run_id")
    sql = (
        f"INSERT INTO runs ({', '.join(RUN_COLUMNS)}) VALUES ({placeholders}) "
        f"ON CONFLICT (run_id) DO UPDATE SET {updates}"
    )
    with _write_lock:
        conn = connect(path)
        try:
            conn.execute(sql, values)
            conn.commit()
        finally:
            conn.close()
