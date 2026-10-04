-- One row per run. Written by worldview_agents.store.
-- Kept to types and syntax that work on both SQLite and Postgres so the
-- planned move to Postgres is a connection change, not a schema rewrite.

CREATE TABLE IF NOT EXISTS runs (
    run_id            TEXT PRIMARY KEY,
    grid_name         TEXT,
    worldview         TEXT NOT NULL,
    worldview_hash    TEXT NOT NULL,
    model             TEXT NOT NULL,
    task_id           TEXT NOT NULL,
    task_hash         TEXT NOT NULL,
    seed              INTEGER,
    temperature       DOUBLE PRECISION NOT NULL,
    status            TEXT NOT NULL,          -- 'complete' | 'error'
    error             TEXT,
    started_at        TEXT NOT NULL,          -- ISO 8601 UTC
    finished_at       TEXT,
    n_calls           INTEGER NOT NULL DEFAULT 0,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    latency_ms        DOUBLE PRECISION NOT NULL DEFAULT 0,
    cost_usd          DOUBLE PRECISION NOT NULL DEFAULT 0,
    git_commit        TEXT,
    run_dir           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS runs_condition_idx ON runs (worldview, model, task_id);
