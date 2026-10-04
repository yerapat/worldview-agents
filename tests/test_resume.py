from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from worldview_agents.config import GridConfig
from worldview_agents.runner import run_grid

from conftest import FakeComplete


def _grid(ws: dict[str, Path]) -> GridConfig:
    return GridConfig(
        name="resume-test",
        worldviews=[str(ws["worldviews"] / "alpha.md"), str(ws["worldviews"] / "control.md")],
        models=["m1"],
        tasks=["t1", "t2"],
        seeds=[1, 2],
        temperatures=[0.7],
        concurrency=4,
    )


def test_second_invocation_skips_finished_runs(workspace: dict[str, Path], fake_complete: FakeComplete) -> None:
    grid = _grid(workspace)
    first = run_grid(grid, complete_fn=fake_complete, base_dir=workspace["runs"], db=workspace["db"])
    assert (first.total, first.skipped, first.completed, first.failed) == (8, 0, 8, 0)
    assert len(fake_complete.calls) == 8

    second = run_grid(grid, complete_fn=fake_complete, base_dir=workspace["runs"], db=workspace["db"])
    assert (second.total, second.skipped, second.completed) == (8, 8, 0)
    assert len(fake_complete.calls) == 8  # no new model calls


def test_failed_runs_are_retried(workspace: dict[str, Path]) -> None:
    grid = _grid(workspace)
    failing = FakeComplete(fail=True)
    first = run_grid(grid, complete_fn=failing, base_dir=workspace["runs"], db=workspace["db"])
    assert first.failed == 8

    ok = FakeComplete()
    second = run_grid(grid, complete_fn=ok, base_dir=workspace["runs"], db=workspace["db"])
    assert (second.skipped, second.completed) == (0, 8)

    conn = sqlite3.connect(workspace["db"])
    statuses = {row[0] for row in conn.execute("SELECT status FROM runs")}
    count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    assert statuses == {"complete"}
    assert count == 8  # upserted, not duplicated


def test_run_outputs_have_expected_shape(workspace: dict[str, Path], fake_complete: FakeComplete) -> None:
    grid = _grid(workspace)
    run_grid(grid, complete_fn=fake_complete, base_dir=workspace["runs"], db=workspace["db"])

    run_dirs = sorted(p for p in workspace["runs"].iterdir() if p.is_dir())
    assert len(run_dirs) == 8
    meta = json.loads((run_dirs[0] / "meta.json").read_text())
    assert meta["status"] == "complete"
    assert set(meta["hashes"]) == {"worldview", "task"}
    assert meta["totals"]["n_calls"] == 1
    assert meta["config"]["grid_name"] == "resume-test"

    lines = (run_dirs[0] / "transcript.jsonl").read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["response"]["text"] == "42"
    assert entry["response"]["prompt_tokens"] == 10

    # control.md has no body, so its runs send only the user message.
    control_calls = [c for c in fake_complete.calls if c["messages"][0]["role"] == "user"]
    assert len(control_calls) == 4
