"""Model gateway: one `complete()` call for every vendor, backed by LiteLLM."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

import yaml
from dotenv import load_dotenv

from worldview_agents.paths import REPO_ROOT, models_config_path

load_dotenv(REPO_ROOT / ".env")

Message = dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class CompletionResult:
    model: str
    litellm_model: str
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    finish_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelSpec:
    alias: str
    litellm_model: str
    local: bool = False


@lru_cache(maxsize=1)
def _model_table() -> dict[str, dict[str, Any]]:
    path = models_config_path()
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def resolve_model(model: str) -> ModelSpec:
    """Turn an alias from configs/models.yaml (or a raw LiteLLM id) into a spec."""
    entry = _model_table().get(model)
    if entry is None:
        return ModelSpec(alias=model, litellm_model=model, local=False)
    return ModelSpec(alias=model, litellm_model=entry["litellm"], local=bool(entry.get("local", False)))


def _call_kwargs(spec: ModelSpec) -> dict[str, Any]:
    if not spec.local:
        return {}
    return {
        "api_base": os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"),
        "api_key": os.environ.get("LOCAL_LLM_API_KEY", "local"),
    }


def _estimate_cost(response: Any, spec: ModelSpec) -> float:
    if spec.local:
        return 0.0
    import litellm

    try:
        return float(litellm.completion_cost(completion_response=response) or 0.0)
    except Exception:
        # Unknown pricing for a new model id is not a reason to fail a run.
        return 0.0


def complete(
    model: str,
    messages: list[Message],
    tools: list[dict[str, Any]] | None = None,
    seed: int | None = None,
    temperature: float = 0.7,
) -> CompletionResult:
    """Send one chat completion to any configured vendor and normalize the result."""
    import litellm

    spec = resolve_model(model)
    kwargs: dict[str, Any] = {
        "model": spec.litellm_model,
        "messages": messages,
        "temperature": temperature,
        # Vendors that do not accept a param (e.g. Anthropic and `seed`) drop it
        # instead of erroring. The seed is still recorded in run metadata.
        "drop_params": True,
        **_call_kwargs(spec),
    }
    if tools:
        kwargs["tools"] = tools
    if seed is not None:
        kwargs["seed"] = seed

    start = time.perf_counter()
    response = litellm.completion(**kwargs)
    latency_ms = (time.perf_counter() - start) * 1000

    choice = response.choices[0]
    message = choice.message
    tool_calls = [
        ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments)
        for tc in (getattr(message, "tool_calls", None) or [])
    ]
    usage = getattr(response, "usage", None)
    return CompletionResult(
        model=spec.alias,
        litellm_model=spec.litellm_model,
        text=message.content or "",
        tool_calls=tool_calls,
        prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
        completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        latency_ms=latency_ms,
        cost_usd=_estimate_cost(response, spec),
        finish_reason=getattr(choice, "finish_reason", None),
    )
