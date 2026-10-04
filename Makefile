UV ?= uv
MODEL ?= local-qwen

.PHONY: install test smoke clean-runs

install:
	$(UV) sync

test:
	$(UV) run pytest -q

# End-to-end check against one cheap model. Default is local-qwen (free, via Ollama).
# Use a paid model with: make smoke MODEL=claude-haiku
smoke:
	$(UV) run wva run configs/grids/smoke.yaml --models $(MODEL)

clean-runs:
	rm -rf runs db/runs.sqlite
