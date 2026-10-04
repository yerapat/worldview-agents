"""Repository-relative locations, overridable through environment variables."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def runs_dir() -> Path:
    return Path(os.environ.get("WVA_RUNS_DIR", REPO_ROOT / "runs"))


def db_path() -> Path:
    return Path(os.environ.get("WVA_DB_PATH", REPO_ROOT / "db" / "runs.sqlite"))


def schema_path() -> Path:
    return REPO_ROOT / "db" / "schema.sql"


def models_config_path() -> Path:
    return REPO_ROOT / "configs" / "models.yaml"
