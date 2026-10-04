"""Worldview prompts, tasks, run configs, and grid expansion."""

from __future__ import annotations

import hashlib
import itertools
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from worldview_agents.paths import REPO_ROOT

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path: str | Path, base: Path = REPO_ROOT) -> Path:
    p = Path(path)
    return p if p.is_absolute() else base / p


class WorldviewMeta(BaseModel):
    name: str
    tier: int | None = None
    family: str
    source_texts: list[str] = Field(default_factory=list)


class WorldviewPrompt(BaseModel):
    path: Path
    meta: WorldviewMeta
    body: str
    content_hash: str

    @property
    def system_prompt(self) -> str | None:
        """None means no system prompt at all (the lab-default control)."""
        text = self.body.strip()
        return text or None


def load_worldview(path: str | Path) -> WorldviewPrompt:
    p = _resolve(path)
    raw = p.read_text()
    match = _FRONT_MATTER.match(raw)
    if not match:
        raise ValueError(f"{p}: worldview prompt must start with a YAML front-matter block")
    meta = WorldviewMeta.model_validate(yaml.safe_load(match.group(1)) or {})
    return WorldviewPrompt(path=p, meta=meta, body=match.group(2), content_hash=sha256_file(p))


class Task(BaseModel):
    id: str
    tier: str
    prompt: str
    expected: Any | None = None
    path: Path
    content_hash: str


def load_task(task_id: str, tasks_dir: Path | None = None) -> Task:
    """Find `<task_id>.yaml` anywhere under tasks/ and load it."""
    root = tasks_dir or REPO_ROOT / "tasks"
    matches = list(root.rglob(f"{task_id}.yaml"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected exactly one task file named {task_id}.yaml under {root}, found {len(matches)}")
    p = matches[0]
    data = yaml.safe_load(p.read_text()) or {}
    if data.get("id") != task_id:
        raise ValueError(f"{p}: id field {data.get('id')!r} does not match file name")
    return Task(path=p, content_hash=sha256_file(p), **data)


class RunConfig(BaseModel):
    """One fully specified run: worldview x model x task x seed x temperature."""

    worldview: str  # path to a prompts/worldviews/*.md file
    model: str
    task: str  # task id
    seed: int | None = None
    temperature: float = 0.7
    grid_name: str | None = None


class GridConfig(BaseModel):
    """A grid expands to the Cartesian product of its lists."""

    name: str
    worldviews: list[str]
    models: list[str]
    tasks: list[str]
    seeds: list[int | None] = Field(default_factory=lambda: [None])
    temperatures: list[float] = Field(default_factory=lambda: [0.7])
    concurrency: int = 4

    @classmethod
    def from_yaml(cls, path: str | Path) -> GridConfig:
        return cls.model_validate(yaml.safe_load(_resolve(path).read_text()))


def expand_grid(grid: GridConfig) -> list[RunConfig]:
    return [
        RunConfig(worldview=w, model=m, task=t, seed=s, temperature=temp, grid_name=grid.name)
        for w, m, t, s, temp in itertools.product(
            grid.worldviews, grid.models, grid.tasks, grid.seeds, grid.temperatures
        )
    ]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def run_id(config: RunConfig, worldview_hash: str, task_hash: str) -> str:
    """Deterministic id for a run.

    The content hashes of the worldview and task files are part of the key, so
    editing either file produces a new id: old outputs no longer match and the
    run is executed again instead of being skipped.
    """
    key = "|".join(
        [
            worldview_hash,
            task_hash,
            config.model,
            "none" if config.seed is None else str(config.seed),
            repr(float(config.temperature)),
        ]
    )
    digest = hashlib.sha256(key.encode()).hexdigest()[:12]
    stem = Path(config.worldview).stem
    return f"{_slug(stem)}__{_slug(config.model)}__{_slug(config.task)}__s{config.seed}__{digest}"
