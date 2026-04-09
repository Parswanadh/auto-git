"""Regression tests for provider-level fail-fast in FallbackLLM."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from types import SimpleNamespace

import pytest

from src.utils.model_manager import FallbackLLM


class _RaisingLLM:
    def __init__(self, message: str):
        self._message = message

    async def ainvoke(self, _messages):
        raise RuntimeError(self._message)


class _OkLLM:
    async def ainvoke(self, _messages):
        return SimpleNamespace(content="ok from groq")


class _Manager:
    def __init__(self, first_error: str):
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
        self._tripped_providers = set()
        self.trip_calls = []
        self._first_error = first_error

    def _provider_base(self, provider: str) -> str:
        return provider.split("_", 1)[0] if "_" in provider else provider

    def _has_key(self, _provider: str) -> bool:
        return True

    def _is_healthy(self, provider: str, model_name: str) -> bool:
        base = self._provider_base(provider)
        if base in self._tripped_providers:
            return False
        return f"{provider}/{model_name}" not in self._dead

    def _build(self, provider: str, _model_name: str, _temperature: float):
        if self._provider_base(provider) == "openrouter":
            return _RaisingLLM(self._first_error)
        return _OkLLM()

    def _get_model_timeout(self, _model_name: str) -> float:
        return 1.0

    def _model_key(self, provider: str, model_name: str) -> str:
        return f"{provider}/{model_name}"

    def _mark_dead(self, provider: str, model_name: str, is_permanent: bool = False):
        _ = is_permanent
        self._dead.add(f"{provider}/{model_name}")

    def _record_provider_failure(self, provider: str, is_connection_error: bool = False):
        _ = provider
        _ = is_connection_error

    def _trip_provider(self, provider: str, cooldown_s: int, reason: str):
        self._tripped_providers.add(self._provider_base(provider))
        self.trip_calls.append((provider, cooldown_s, reason))


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_text,expected_reason",
    [
        ("401 unauthorized invalid api key", "auth error"),
        ("quota exceeded for this account", "provider quota"),
    ],
)
async def test_provider_failfast_trips_family_and_reaches_next_provider(error_text: str, expected_reason: str):
    manager = _Manager(first_error=error_text)
    llm = FallbackLLM(manager, profile="balanced")

    result = await llm.ainvoke([SimpleNamespace(content="hello")])

    assert getattr(result, "content", "") == "ok from groq"
    assert len(manager.trip_calls) == 1
    assert manager.trip_calls[0][2] == expected_reason
