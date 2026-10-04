# Handoff — PR 1: gateway, orchestrator, logging

As of 2026-10-04.

## What exists

| Piece | Where | What it does |
| --- | --- | --- |
| Gateway | `src/worldview_agents/gateway.py` | `complete(model, messages, tools=None, seed=None, temperature=0.7)` behind LiteLLM. Returns a `CompletionResult` dataclass: text, tool calls, prompt/completion tokens, latency, estimated cost. Unsupported params (e.g. `seed` on Anthropic) are dropped, not errors. |
| Model aliases | `configs/models.yaml` | Short names (`claude-haiku`, `gpt-mini`, `grok`, `local-qwen`, `local-llama`) mapped to LiteLLM ids. `local: true` routes to `LOCAL_LLM_BASE_URL` (Ollama or vLLM). Unknown ids pass straight to LiteLLM. |
| Worldview prompts | `prompts/worldviews/*.md` | Six files matching the Phase 1 pilot list. Five are **placeholders**. `lab_default.md` has an empty body, which means no system prompt is sent. |
| Tasks | `tasks/smoke/smoke_arithmetic.yaml` | One stub task (17 + 25). Task files are found by id anywhere under `tasks/`. |
| Grid configs | `configs/grids/` | `smoke.yaml` (2 runs) and `pilot_example.yaml` (shape of the pilot; 120 runs with the stub task). |
| Runner | `src/worldview_agents/runner.py` | Expands a grid into runs, executes them on a thread pool, skips runs whose `meta.json` says `complete`, retries ones that errored. |
| Run id | `config.run_id()` | Readable prefix + hash of (worldview file hash, task file hash, model, seed, temperature). Editing a prompt or task file changes the id, so old results stop matching and the run executes again. |
| Logging | `runs/<run_id>/` | `transcript.jsonl` (one line per model call: request + normalized response) and `meta.json` (resolved config, file hashes, git commit, timestamps, totals). |
| Run index | `db/schema.sql`, `store.py` | One row per run in SQLite at `db/runs.sqlite`. Schema uses only types that also work in Postgres. |
| CLI | `wva run <grid> [--models a,b] [--concurrency N]`, `wva list <grid>` | |
| Tests | `tests/` | 12 pytest tests: grid expansion, resumability, hash invalidation. They use a fake model; no network. |

## How to run it

```sh
make install                     # uv sync: Python 3.11 venv + deps
make test                        # 12 tests, ~3 seconds
make smoke                       # 2 real runs on local Ollama (qwen2.5:3b-instruct), free
make smoke MODEL=claude-haiku    # same against a paid model; needs ANTHROPIC_API_KEY in .env
uv run wva list configs/grids/smoke.yaml   # see which runs are done
sqlite3 db/runs.sqlite "select worldview, model, status, prompt_tokens, latency_ms from runs"
```

Verified on 2026-10-04: `make test` passes and `make smoke` completes both runs on local
Ollama (both answered 42); a second `make smoke` skips both. Paid vendors are **not yet
tested** — no API keys were configured.

## Known gaps in this PR

- The paid model ids in `configs/models.yaml` (`gpt-4o-mini`, `grok-3-mini`, `claude-sonnet-5-5`) were
  not called. Confirm each is current and priced in LiteLLM before the pilot, or cost will log as 0.
- One model call per run. Multi-turn and tool-use loops come with the task ladder.
- Task order is not randomized yet (DESIGN.md Controls). Add it when there are tasks to order.
- Prompt length and reading-level matching is not checked. Worth a test once real prompts exist.

## What the next PR should build

1. **Real worldview prompts.** Write the five pilot prompts from their source texts and length-match
   them. Add a check that fails if their token counts differ by more than an agreed margin.
2. **Task ladder.** 20 tasks per tier (basic, medium, high) with answer keys or rubrics. Extend the task
   schema for multi-turn and tool-use tasks.
3. **Scoring.** Deterministic checks first, then the rubric judge (a model not under test, blind to the
   worldview condition). Add a `scores` table keyed on `run_id`.
4. **Postgres.** Move the run index off SQLite when the pilot starts, so results can be queried from
   anywhere. `db/schema.sql` should load into Postgres unchanged; `store.py` needs a Postgres connection
   path selected by a `DATABASE_URL` env var.
