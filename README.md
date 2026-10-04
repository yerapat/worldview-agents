# worldview-agents

A research harness that asks one question: does giving an LLM agent a worldview
built only from foundational texts (the Bible, the Quran, the Torah, the Pali
Canon, the Humanist Manifesto, and others) change how it does tasks, treats other
agents, and holds or shifts that worldview over time? And how does each lab's
default behavior compare?

The full research design is in [DESIGN.md](DESIGN.md).

**On the framing.** Every worldview prompt is built from a named text, not from
claims about how believers behave. The prompts are published in
[`prompts/worldviews/`](prompts/worldviews/) so anyone can check them.

## Status

Early. This repo currently holds the model gateway, the run orchestrator, and
logging. The worldview prompts are placeholders. The task ladder, the LLM judge,
the multi-agent runs, and the analysis are not built yet. See
[HANDOFF.md](HANDOFF.md) for what exists and what comes next.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and, for the free smoke test,
[Ollama](https://ollama.com) with `qwen2.5:3b-instruct` pulled.

```sh
make install          # create .venv with Python 3.11 and install deps
make test             # unit tests, no model calls
make smoke            # 2 real runs against local Ollama
make smoke MODEL=claude-haiku   # same, against a paid model (needs .env)
```

Copy `.env.example` to `.env` and fill in the API keys for the vendors you use.

## Layout

```
configs/models.yaml          model aliases -> LiteLLM ids
configs/grids/*.yaml         experiment grids (worldviews x models x tasks x seeds x temps)
prompts/worldviews/*.md      one system prompt per worldview, YAML front matter on top
tasks/                       task files (one stub for now)
src/worldview_agents/        gateway, config + grid expansion, runner, SQLite store, CLI
db/schema.sql                the `runs` table
runs/<run_id>/               transcript.jsonl + meta.json per run (git-ignored)
```

## License

MIT
