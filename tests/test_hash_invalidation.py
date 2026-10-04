from __future__ import annotations

from pathlib import Path

from worldview_agents.config import GridConfig
from worldview_agents.runner import run_grid

from conftest import FakeComplete


def _grid(ws: dict[str, Path]) -> GridConfig:
    return GridConfig(
        name="hash-test",
        worldviews=[str(ws["worldviews"] / "alpha.md"), str(ws["worldviews"] / "control.md")],
        models=["m1"],
        tasks=["t1"],
        seeds=[1],
    )


def _run(ws: dict[str, Path], fake: FakeComplete):
    return run_grid(_grid(ws), complete_fn=fake, base_dir=ws["runs"], db=ws["db"])


def test_editing_a_worldview_prompt_invalidates_only_its_runs(
    workspace: dict[str, Path], fake_complete: FakeComplete
) -> None:
    assert _run(workspace, fake_complete).completed == 2

    alpha = workspace["worldviews"] / "alpha.md"
    alpha.write_text(alpha.read_text().replace("You follow Book A.", "You follow Book A, chapter 1."))

    again = _run(workspace, fake_complete)
    assert (again.skipped, again.completed) == (1, 1)  # control untouched, alpha re-run
    assert "chapter 1" in fake_complete.calls[-1]["messages"][0]["content"]


def test_editing_a_task_invalidates_its_runs(workspace: dict[str, Path], fake_complete: FakeComplete) -> None:
    _run(workspace, fake_complete)
    task = workspace["tasks"] / "t1.yaml"
    task.write_text(task.read_text().replace("2+2", "2+3"))

    again = _run(workspace, fake_complete)
    assert (again.skipped, again.completed) == (0, 2)


def test_unchanged_files_are_not_invalidated(workspace: dict[str, Path], fake_complete: FakeComplete) -> None:
    _run(workspace, fake_complete)
    # Touching a file without changing its bytes must not trigger a re-run.
    (workspace["worldviews"] / "alpha.md").touch()
    assert _run(workspace, fake_complete).skipped == 2
