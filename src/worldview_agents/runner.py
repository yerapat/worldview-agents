"""Run orchestrator: expand a grid, execute runs concurrently, skip finished ones."""

from __future__ import annotations

import json
import logging
import subprocess
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from worldview_agents import gateway, store
from worldview_agents.config import (
    GridConfig,
    RunConfig,
    Task,
    WorldviewPrompt,
    expand_grid,
    load_task,
    load_worldview,
    run_id,
)
from worldview_agents.paths import REPO_ROOT, runs_dir

log = logging.getLogger(__name__)

CompleteFn = Callable[..., gateway.CompletionResult]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


@dataclass
class ResolvedRun:
    config: RunConfig
    worldview: WorldviewPrompt
    task: Task
    run_id: str
    run_dir: Path

    @property
    def meta_path(self) -> Path:
        return self.run_dir / "meta.json"

    @property
    def transcript_path(self) -> Path:
        return self.run_dir / "transcript.jsonl"

    def is_complete(self) -> bool:
        if not self.meta_path.exists():
            return False
        try:
            return json.loads(self.meta_path.read_text()).get("status") == "complete"
        except json.JSONDecodeError:
            return False


def resolve(config: RunConfig, base_dir: Path | None = None) -> ResolvedRun:
    worldview = load_worldview(config.worldview)
    task = load_task(config.task)
    rid = run_id(config, worldview.content_hash, task.content_hash)
    return ResolvedRun(
        config=config,
        worldview=worldview,
        task=task,
        run_id=rid,
        run_dir=(base_dir or runs_dir()) / rid,
    )


def build_messages(run: ResolvedRun) -> list[gateway.Message]:
    messages: list[gateway.Message] = []
    if run.worldview.system_prompt is not None:
        messages.append({"role": "system", "content": run.worldview.system_prompt})
    messages.append({"role": "user", "content": run.task.prompt})
    return messages


def execute(
    run: ResolvedRun,
    complete_fn: CompleteFn = gateway.complete,
    db: Path | None = None,
    commit: str | None = None,
) -> dict[str, Any]:
    """Execute one run. Writes transcript.jsonl, meta.json, and a row in the runs table."""
    run.run_dir.mkdir(parents=True, exist_ok=True)
    # A partial transcript from a crashed attempt is discarded, not appended to.
    run.transcript_path.unlink(missing_ok=True)

    started = _now()
    totals = {"n_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0.0, "cost_usd": 0.0}
    status, error = "complete", None

    try:
        messages = build_messages(run)
        result = complete_fn(
            run.config.model,
            messages,
            seed=run.config.seed,
            temperature=run.config.temperature,
        )
        with run.transcript_path.open("a") as fh:
            fh.write(
                json.dumps(
                    {
                        "call_index": 0,
                        "timestamp": _now(),
                        "request": {
                            "model": run.config.model,
                            "messages": messages,
                            "seed": run.config.seed,
                            "temperature": run.config.temperature,
                        },
                        "response": result.to_dict(),
                    }
                )
                + "\n"
            )
        totals["n_calls"] += 1
        totals["prompt_tokens"] += result.prompt_tokens
        totals["completion_tokens"] += result.completion_tokens
        totals["latency_ms"] += result.latency_ms
        totals["cost_usd"] += result.cost_usd
    except Exception as exc:  # noqa: BLE001 - every failure is recorded on the run
        status, error = "error", f"{type(exc).__name__}: {exc}"
        log.warning("run %s failed: %s", run.run_id, error)
        log.debug(traceback.format_exc())

    finished = _now()
    meta = {
        "run_id": run.run_id,
        "status": status,
        "error": error,
        "config": run.config.model_dump(),
        "resolved": {
            "worldview_path": str(run.worldview.path.relative_to(REPO_ROOT))
            if run.worldview.path.is_relative_to(REPO_ROOT)
            else str(run.worldview.path),
            "worldview_meta": run.worldview.meta.model_dump(),
            "task_path": str(run.task.path.relative_to(REPO_ROOT))
            if run.task.path.is_relative_to(REPO_ROOT)
            else str(run.task.path),
            "task_tier": run.task.tier,
            "litellm_model": gateway.resolve_model(run.config.model).litellm_model,
        },
        "hashes": {"worldview": run.worldview.content_hash, "task": run.task.content_hash},
        "git_commit": commit,
        "started_at": started,
        "finished_at": finished,
        "totals": totals,
    }
    run.meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    store.upsert_run(
        {
            "run_id": run.run_id,
            "grid_name": run.config.grid_name,
            "worldview": run.worldview.meta.name,
            "worldview_hash": run.worldview.content_hash,
            "model": run.config.model,
            "task_id": run.task.id,
            "task_hash": run.task.content_hash,
            "seed": run.config.seed,
            "temperature": run.config.temperature,
            "status": status,
            "error": error,
            "started_at": started,
            "finished_at": finished,
            "git_commit": commit,
            "run_dir": str(run.run_dir),
            **totals,
        },
        path=db,
    )
    return meta


@dataclass
class GridSummary:
    total: int
    skipped: int
    completed: int
    failed: int


def run_grid(
    grid: GridConfig,
    complete_fn: CompleteFn = gateway.complete,
    base_dir: Path | None = None,
    db: Path | None = None,
    concurrency: int | None = None,
) -> GridSummary:
    runs = [resolve(cfg, base_dir) for cfg in expand_grid(grid)]
    pending = [r for r in runs if not r.is_complete()]
    skipped = len(runs) - len(pending)
    log.info("grid %s: %d runs, %d already complete, %d to execute", grid.name, len(runs), skipped, len(pending))

    commit = git_commit()
    completed = failed = 0
    workers = max(1, concurrency or grid.concurrency)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(execute, r, complete_fn, db, commit): r for r in pending}
        for fut in as_completed(futures):
            meta = fut.result()
            if meta["status"] == "complete":
                completed += 1
            else:
                failed += 1
            log.info("[%s] %s", meta["status"], meta["run_id"])

    return GridSummary(total=len(runs), skipped=skipped, completed=completed, failed=failed)
