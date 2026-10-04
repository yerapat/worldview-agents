from __future__ import annotations

from pathlib import Path

import pytest

from worldview_agents.gateway import CompletionResult


class FakeComplete:
    """Stands in for gateway.complete so tests never call a real model."""

    def __init__(self, fail: bool = False) -> None:
        self.calls: list[dict] = []
        self.fail = fail

    def __call__(self, model, messages, tools=None, seed=None, temperature=0.7) -> CompletionResult:
        self.calls.append({"model": model, "messages": messages, "seed": seed, "temperature": temperature})
        if self.fail:
            raise RuntimeError("simulated vendor outage")
        return CompletionResult(
            model=model,
            litellm_model=f"fake/{model}",
            text="42",
            prompt_tokens=10,
            completion_tokens=1,
            latency_ms=5.0,
            cost_usd=0.0001,
        )


@pytest.fixture
def fake_complete() -> FakeComplete:
    return FakeComplete()


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    """Isolated worldview and task files plus output locations."""
    wv_dir = tmp_path / "worldviews"
    wv_dir.mkdir()
    (wv_dir / "alpha.md").write_text(
        "---\nname: alpha\ntier: 1\nfamily: Test\nsource_texts: [Book A]\n---\nYou follow Book A.\n"
    )
    (wv_dir / "control.md").write_text("---\nname: control\nfamily: Lab default\n---\n")

    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "t1.yaml").write_text("id: t1\ntier: basic\nprompt: 'What is 2+2?'\nexpected: '4'\n")
    (tasks_dir / "t2.yaml").write_text("id: t2\ntier: basic\nprompt: 'What is 3+3?'\nexpected: '6'\n")

    return {
        "root": tmp_path,
        "worldviews": wv_dir,
        "tasks": tasks_dir,
        "runs": tmp_path / "runs",
        "db": tmp_path / "runs.sqlite",
    }


@pytest.fixture(autouse=True)
def _isolate_tasks_dir(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Point task lookup at the test workspace when a test uses it."""
    if "workspace" not in request.fixturenames:
        return
    ws = request.getfixturevalue("workspace")
    from worldview_agents import config, runner

    original = config.load_task
    monkeypatch.setattr(runner, "load_task", lambda task_id: original(task_id, ws["tasks"]))
