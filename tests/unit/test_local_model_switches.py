"""Unit tests for local-model disable switches and Perplexica gating."""

import pytest

from src.research import sota_researcher
from src.utils import model_manager


@pytest.mark.unit
def test_model_manager_disables_ollama_when_kill_switch_is_enabled(monkeypatch):
    monkeypatch.setenv("AUTOGIT_DISABLE_LOCAL_MODELS", "true")
    monkeypatch.delenv("AUTOGIT_LOCAL_MODELS_ENABLED", raising=False)

    assert model_manager._local_models_enabled() is False

    manager = model_manager.ModelManager()
    assert manager._has_key("ollama") is False


@pytest.mark.unit
def test_model_manager_defaults_to_cloud_only_when_no_overrides(monkeypatch):
    monkeypatch.delenv("AUTOGIT_DISABLE_LOCAL_MODELS", raising=False)
    monkeypatch.delenv("AUTOGIT_LOCAL_MODELS_ENABLED", raising=False)

    assert model_manager._local_models_enabled() is False

    manager = model_manager.ModelManager()
    assert manager._has_key("ollama") is False


@pytest.mark.unit
def test_model_manager_can_explicitly_enable_local_models(monkeypatch):
    monkeypatch.setenv("AUTOGIT_DISABLE_LOCAL_MODELS", "false")
    monkeypatch.setenv("AUTOGIT_LOCAL_MODELS_ENABLED", "true")

    assert model_manager._local_models_enabled() is True

    manager = model_manager.ModelManager()
    assert manager._has_key("ollama") is True


@pytest.mark.unit
def test_perplexica_is_disabled_when_local_models_are_disabled_and_provider_is_ollama(monkeypatch):
    monkeypatch.setenv("PERPLEXICA_ENABLED", "true")
    monkeypatch.setenv("AUTOGIT_DISABLE_LOCAL_MODELS", "true")
    monkeypatch.setenv("PERPLEXICA_CHAT_PROVIDER", "Ollama")
    monkeypatch.setenv("PERPLEXICA_EMBEDDING_PROVIDER", "Ollama")

    assert sota_researcher._perplexica_enabled() is False


@pytest.mark.unit
def test_perplexica_can_remain_enabled_with_cloud_providers_when_local_models_disabled(monkeypatch):
    monkeypatch.setenv("PERPLEXICA_ENABLED", "true")
    monkeypatch.setenv("AUTOGIT_DISABLE_LOCAL_MODELS", "true")
    monkeypatch.setenv("PERPLEXICA_CHAT_PROVIDER", "OpenRouter")
    monkeypatch.setenv("PERPLEXICA_EMBEDDING_PROVIDER", "OpenRouter")

    assert sota_researcher._perplexica_enabled() is True


@pytest.mark.unit
def test_perplexica_is_disabled_when_providers_unspecified_and_local_models_disabled(monkeypatch):
    monkeypatch.setenv("PERPLEXICA_ENABLED", "true")
    monkeypatch.delenv("AUTOGIT_DISABLE_LOCAL_MODELS", raising=False)
    monkeypatch.delenv("AUTOGIT_LOCAL_MODELS_ENABLED", raising=False)
    monkeypatch.delenv("PERPLEXICA_CHAT_PROVIDER", raising=False)
    monkeypatch.delenv("PERPLEXICA_EMBEDDING_PROVIDER", raising=False)

    assert sota_researcher._perplexica_enabled() is False
