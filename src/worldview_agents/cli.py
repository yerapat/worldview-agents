"""Command line entry point: `wva run <grid.yaml>`, `wva list <grid.yaml>`."""

from __future__ import annotations

import argparse
import logging
import sys

from worldview_agents.config import GridConfig, expand_grid
from worldview_agents.runner import resolve, run_grid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wva", description="Worldview Agents run orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="execute every unfinished run in a grid")
    run_p.add_argument("grid", help="path to a grid YAML file")
    run_p.add_argument("--concurrency", type=int, default=None, help="override the grid's concurrency")
    run_p.add_argument("--models", default=None, help="comma-separated model ids that replace the grid's models")
    run_p.add_argument("-v", "--verbose", action="store_true")

    list_p = sub.add_parser("list", help="show the runs a grid expands to and whether each is done")
    list_p.add_argument("grid", help="path to a grid YAML file")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    # LiteLLM is noisy at INFO.
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    grid = GridConfig.from_yaml(args.grid)
    if getattr(args, "models", None):
        grid = grid.model_copy(update={"models": [m.strip() for m in args.models.split(",") if m.strip()]})

    if args.command == "list":
        for cfg in expand_grid(grid):
            r = resolve(cfg)
            print(f"{'done' if r.is_complete() else 'todo'}  {r.run_id}")
        return 0

    summary = run_grid(grid, concurrency=args.concurrency)
    print(
        f"grid {grid.name}: {summary.total} runs | {summary.skipped} skipped (already done) | "
        f"{summary.completed} completed | {summary.failed} failed"
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    sys.exit(main())
