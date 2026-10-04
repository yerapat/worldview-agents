from __future__ import annotations

from pathlib import Path

from worldview_agents.config import GridConfig, RunConfig, expand_grid, load_worldview, run_id
from worldview_agents.paths import REPO_ROOT


def test_expand_grid_is_full_cartesian_product() -> None:
    grid = GridConfig(
        name="g",
        worldviews=["a.md", "b.md", "c.md"],
        models=["m1", "m2"],
        tasks=["t1", "t2"],
        seeds=[1, 2, 3],
        temperatures=[0.0, 0.7],
    )
    runs = expand_grid(grid)
    assert len(runs) == 3 * 2 * 2 * 3 * 2
    keys = {(r.worldview, r.model, r.task, r.seed, r.temperature) for r in runs}
    assert len(keys) == len(runs)
    assert all(r.grid_name == "g" for r in runs)


def test_expand_grid_defaults_to_one_seed_and_temperature() -> None:
    grid = GridConfig(name="g", worldviews=["a.md"], models=["m"], tasks=["t"])
    (only,) = expand_grid(grid)
    assert only.seed is None
    assert only.temperature == 0.7


def test_pilot_example_grid_matches_design_size() -> None:
    # DESIGN.md: 6 worldviews x 4 models x 5 seeds per task.
    grid = GridConfig.from_yaml(REPO_ROOT / "configs" / "grids" / "pilot_example.yaml")
    assert len(expand_grid(grid)) == 6 * 4 * len(grid.tasks) * 5


def test_run_id_is_deterministic_and_distinguishes_conditions() -> None:
    cfg = RunConfig(worldview="w/alpha.md", model="m", task="t1", seed=1, temperature=0.7)
    assert run_id(cfg, "h1", "h2") == run_id(cfg, "h1", "h2")
    assert run_id(cfg, "h1", "h2") != run_id(cfg.model_copy(update={"seed": 2}), "h1", "h2")
    assert run_id(cfg, "h1", "h2") != run_id(cfg.model_copy(update={"temperature": 0.0}), "h1", "h2")
    assert run_id(cfg, "h1", "h2") != run_id(cfg.model_copy(update={"model": "m2"}), "h1", "h2")


def test_all_six_pilot_worldviews_load() -> None:
    names = {load_worldview(p).meta.name for p in (REPO_ROOT / "prompts" / "worldviews").glob("*.md")}
    assert names == {
        "bible_purist",
        "quran_purist",
        "torah_purist",
        "pali_canon_purist",
        "secular_humanist",
        "lab_default",
    }


def test_lab_default_sends_no_system_prompt(workspace: dict[str, Path]) -> None:
    assert load_worldview(workspace["worldviews"] / "control.md").system_prompt is None
    assert load_worldview(workspace["worldviews"] / "alpha.md").system_prompt == "You follow Book A."
