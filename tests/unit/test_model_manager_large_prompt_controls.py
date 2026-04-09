"""Phase 2 resilience tests for large-prompt fallback behavior."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from threading import Lock
from types import SimpleNamespace

import pytest

from src.utils.model_manager import FallbackLLM


class _SleepyLLM:
    async def ainvoke(self, _messages):
        await asyncio.sleep(0.2)


class _OkLLM:
    def __init__(self, content: str = "ok"):
        self.content = content

    async def ainvoke(self, _messages):
        return SimpleNamespace(content=self.content)


class _TestManager:
    def __init__(self):
        self.CLOUD_CONFIGS = {
            "balanced": [
                ("openrouter", "a", 0.2),
                ("openrouter", "b", 0.2),
                ("groq", "c", 0.2),
            ]
        }
        self._rotation_counter = defaultdict(int)
        self._rotation_lock = Lock()
        self._dead = set()
        self._provider_failures = []

    def _provider_base(self, provider: str) -> str:
        return provider

    def _has_key(self, _provider: str) -> bool:
        return True

    def _is_healthy(self, provider: str, model_name: str) -> bool:
        return f"{provider}/{model_name}" not in self._dead

    def _build(self, provider: str, model_name: str, _temperature: float):
        if provider == "openrouter" and model_name == "a":
            return _SleepyLLM()
        return _OkLLM(content=f"from:{provider}_{model_name}")

    def _get_model_timeout(self, _model_name: str) -> float:
        return 0.01

    def _model_key(self, provider: str, model_name: str) -> str:
        return f"{provider}/{model_name}"

    def _mark_dead(self, provider: str, model_name: str, is_permanent: bool = False):
        _ = is_permanent
        self._dead.add(f"{provider}/{model_name}")

    def _record_provider_failure(self, provider: str, is_connection_error: bool = False):
        _ = is_connection_error
        self._provider_failures.append(provider)

    def _log_fallback_attempt(self, **_kwargs):
        return None


def _large_prompt_messages():
    return [SimpleNamespace(content="x" * 120000)]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_large_prompt_timeout_skips_same_provider_family_in_call():
    manager = _TestManager()
    llm = FallbackLLM(manager, profile="balanced")

    result = await llm.ainvoke(_large_prompt_messages())

    assert getattr(result, "content", "").startswith("from:groq_c")
    assert "openrouter" in manager._provider_failures


@pytest.mark.unit
@pytest.mark.asyncio
async def test_large_prompt_model_attempt_budget_is_respected():
    manager = _TestManager()

    def _always_timeout(_provider: str, _model_name: str, _temperature: float):
        return _SleepyLLM()

    manager._build = _always_timeout
    llm = FallbackLLM(manager, profile="balanced")

    with pytest.raises(Exception, match="exhausted"):
        await llm.ainvoke(_large_prompt_messages())

    # Large prompts should stop early (<=2 models for balanced profile).
    assert len(manager._dead) <= 2
