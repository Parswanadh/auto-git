"""Unit tests for ops tooling additions (telemetry parity + checkpoint replay helpers)."""

import os
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from auto_git_cli import _build_checkpoint_diagnostics, _extract_checkpoint_state, app
from src.langraph_pipeline.workflow_enhanced import _enforce_telemetry_parity
from src.utils.pipeline_tracer import validate_trace_status_parity


@pytest.mark.unit
def test_validate_trace_status_parity_flags_status_only_nodes():
    trace = {
        "node_calls": {"research": 1},
        "current_stage": "research_complete",
        "error_count": 0,
    }
    status = {
        "node_calls": {"research": 1, "ghost_node": 2},
        "current_stage": "research_complete",
        "error_count": 0,
    }

    parity = validate_trace_status_parity(trace, status)

    assert parity["ok"] is False
    assert any("trace missing node count: ghost_node" in item for item in parity["mismatches"])


@pytest.mark.unit
def test_extract_checkpoint_state_supports_tuple_like_object():
    ckpt = SimpleNamespace(checkpoint={"current_stage": "code_generated", "errors": []})

    state = _extract_checkpoint_state(ckpt)

    assert state["current_stage"] == "code_generated"


@pytest.mark.unit
def test_replay_command_prints_checkpoint_summary(monkeypatch):
    runner = CliRunner()

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "errors": ["x"],
            "warnings": ["y"],
            "_node_exec_frequency": {"code_testing": 4, "code_fixing": 2},
            "_loop_detection_state": "clean",
        }

    import src.langraph_pipeline.checkpointer_factory as cf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)

    result = runner.invoke(app, ["replay", "--thread-id", "t-1", "--checkpointer", "memory"])

    assert result.exit_code == 0
    assert "Checkpoint Summary" in result.stdout
    assert "Checkpoint Diagnostics" in result.stdout
    assert "code_fixing" in result.stdout


@pytest.mark.unit
def test_enforce_telemetry_parity_strict_raises():
    parity = {
        "ok": False,
        "mismatches": ["count mismatch for research: trace=1, status=2"],
    }

    with pytest.raises(RuntimeError, match="Telemetry parity mismatch"):
        _enforce_telemetry_parity(parity, "research", "strict")


@pytest.mark.unit
def test_enforce_telemetry_parity_warn_returns_message():
    parity = {
        "ok": False,
        "mismatches": ["count mismatch for research: trace=1, status=2"],
    }

    warning = _enforce_telemetry_parity(parity, "research", "warn")

    assert warning is not None
    assert "Telemetry parity mismatch at research" in warning


@pytest.mark.unit
def test_replay_resume_run_invokes_pipeline(monkeypatch):
    runner = CliRunner()
    captured = {}

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "errors": ["x"],
            "warnings": ["y"],
            "_node_exec_frequency": {"code_testing": 4, "code_fixing": 2},
            "_loop_detection_state": "clean",
        }

    async def _fake_run_auto_git_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import src.langraph_pipeline.checkpointer_factory as cf
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    result = runner.invoke(
        app,
        [
            "replay",
            "--thread-id",
            "t-1",
            "--checkpointer",
            "memory",
            "--resume-run",
            "--idea",
            "Resume me",
            "--telemetry-parity-mode",
            "strict",
        ],
    )

    assert result.exit_code == 0
    assert "Resume Run Result" in result.stdout
    assert "published" in result.stdout.lower()
    assert captured.get("telemetry_parity_mode") == "strict"


@pytest.mark.unit
def test_replay_resume_blocked_when_checkpoint_not_resumable(monkeypatch):
    runner = CliRunner()

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    # Missing required keys -> not resumable diagnostics
    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "_node_exec_frequency": {"code_testing": 4},
        }

    import src.langraph_pipeline.checkpointer_factory as cf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)

    result = runner.invoke(
        app,
        [
            "replay",
            "--thread-id",
            "t-1",
            "--checkpointer",
            "memory",
            "--resume-run",
        ],
    )

    assert result.exit_code == 1
    assert "Resume blocked" in result.stdout


@pytest.mark.unit
def test_replay_force_resume_overrides_non_resumable(monkeypatch):
    runner = CliRunner()

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "_node_exec_frequency": {"code_testing": 2},
        }

    async def _fake_run_auto_git_pipeline(**kwargs):
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import src.langraph_pipeline.checkpointer_factory as cf
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    result = runner.invoke(
        app,
        [
            "replay",
            "--thread-id",
            "t-1",
            "--checkpointer",
            "memory",
            "--resume-run",
            "--force-resume",
        ],
    )

    assert result.exit_code == 0
    assert "Resume Run Result" in result.stdout


@pytest.mark.unit
def test_build_checkpoint_diagnostics_returns_progress_hints():
    state = {
        "current_stage": "code_generated",
        "errors": [],
        "warnings": [],
        "_node_exec_frequency": {"code_generation": 1, "research": 1},
        "_loop_detection_state": "clean",
    }

    diagnostics = _build_checkpoint_diagnostics(state)

    assert diagnostics["resumable"] is True
    assert diagnostics["top_node"] in {"code_generation", "research"}
    assert isinstance(diagnostics["next_stages"], list)
    assert len(diagnostics["next_stages"]) >= 1


@pytest.mark.unit
def test_doctor_reports_checkpoint_resumability(monkeypatch):
    runner = CliRunner()

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "errors": [],
            "warnings": [],
            "_node_exec_frequency": {"code_testing": 2},
            "_loop_detection_state": "clean",
        }

    import src.langraph_pipeline.checkpointer_factory as cf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)

    result = runner.invoke(app, ["doctor", "--checkpointer", "memory", "--thread-id", "t-1"])

    assert result.exit_code == 0
    assert "Checkpoint resume" in result.stdout


@pytest.mark.unit
def test_generate_invalid_parity_mode_normalizes_to_warn(monkeypatch):
    runner = CliRunner()
    captured = {}

    async def _fake_run_auto_git_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import auto_git_cli as cli_mod
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cli_mod.Confirm, "ask", lambda *args, **kwargs: True)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    result = runner.invoke(
        app,
        [
            "generate",
            "Build a CLI",
            "--telemetry-parity-mode",
            "not-a-mode",
            "--no-search",
        ],
    )

    assert result.exit_code == 0
    assert captured.get("telemetry_parity_mode") == "warn"


@pytest.mark.unit
def test_replay_resume_invalid_parity_mode_normalizes_to_warn(monkeypatch):
    runner = CliRunner()
    captured = {}

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "errors": [],
            "warnings": [],
            "_node_exec_frequency": {"code_testing": 2},
            "_loop_detection_state": "clean",
        }

    async def _fake_run_auto_git_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import src.langraph_pipeline.checkpointer_factory as cf
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    result = runner.invoke(
        app,
        [
            "replay",
            "--thread-id",
            "t-1",
            "--checkpointer",
            "memory",
            "--resume-run",
            "--force-resume",
            "--telemetry-parity-mode",
            "invalid-mode",
        ],
    )

    assert result.exit_code == 0
    assert captured.get("telemetry_parity_mode") == "warn"


@pytest.mark.unit
def test_generate_invalid_policy_inputs_normalize_to_safe_defaults(monkeypatch):
    runner = CliRunner()
    captured = {}

    async def _fake_run_auto_git_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import auto_git_cli as cli_mod
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cli_mod.Confirm, "ask", lambda *args, **kwargs: True)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    result = runner.invoke(
        app,
        [
            "generate",
            "Build a CLI",
            "--trust-mode",
            "unsafe-typo",
            "--allowlist-mode",
            "strict-typo",
            "--failover-profile",
            "ultra-resilient-typo",
            "--no-search",
        ],
    )

    assert result.exit_code == 0
    assert captured.get("trust_mode") == "trusted"
    assert captured.get("tool_allowlist_mode") == "permissive"
    assert captured.get("model_failover_profile") == "balanced"


@pytest.mark.unit
def test_generate_cloud_only_sets_local_disable_env(monkeypatch):
    runner = CliRunner()
    captured = {}

    async def _fake_run_auto_git_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import auto_git_cli as cli_mod
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cli_mod.Confirm, "ask", lambda *args, **kwargs: True)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    monkeypatch.delenv("AUTOGIT_DISABLE_LOCAL_MODELS", raising=False)
    monkeypatch.delenv("PERPLEXICA_ENABLED", raising=False)

    result = runner.invoke(
        app,
        [
            "generate",
            "Build a CLI",
            "--cloud-only",
            "--no-search",
        ],
    )

    assert result.exit_code == 0
    assert captured.get("idea") == "Build a CLI"
    assert os.environ.get("AUTOGIT_DISABLE_LOCAL_MODELS") == "true"
    assert os.environ.get("PERPLEXICA_ENABLED") == "false"


@pytest.mark.unit
def test_replay_resume_invalid_policy_inputs_normalize_to_safe_defaults(monkeypatch):
    runner = CliRunner()
    captured = {}

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "errors": [],
            "warnings": [],
            "_node_exec_frequency": {"code_testing": 2},
            "_loop_detection_state": "clean",
        }

    async def _fake_run_auto_git_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import src.langraph_pipeline.checkpointer_factory as cf
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    result = runner.invoke(
        app,
        [
            "replay",
            "--thread-id",
            "t-1",
            "--checkpointer",
            "memory",
            "--resume-run",
            "--force-resume",
            "--trust-mode",
            "unsafe-typo",
            "--allowlist-mode",
            "strict-typo",
            "--failover-profile",
            "ultra-resilient-typo",
        ],
    )

    assert result.exit_code == 0
    assert captured.get("trust_mode") == "trusted"
    assert captured.get("tool_allowlist_mode") == "permissive"
    assert captured.get("model_failover_profile") == "balanced"


@pytest.mark.unit
def test_replay_resume_cloud_only_sets_local_disable_env(monkeypatch):
    runner = CliRunner()

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "errors": [],
            "warnings": [],
            "_node_exec_frequency": {"code_testing": 2},
            "_loop_detection_state": "clean",
        }

    async def _fake_run_auto_git_pipeline(**kwargs):
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import src.langraph_pipeline.checkpointer_factory as cf
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    monkeypatch.delenv("AUTOGIT_DISABLE_LOCAL_MODELS", raising=False)
    monkeypatch.delenv("PERPLEXICA_ENABLED", raising=False)

    result = runner.invoke(
        app,
        [
            "replay",
            "--thread-id",
            "t-1",
            "--checkpointer",
            "memory",
            "--resume-run",
            "--force-resume",
            "--cloud-only",
        ],
    )

    assert result.exit_code == 0
    assert os.environ.get("AUTOGIT_DISABLE_LOCAL_MODELS") == "true"
    assert os.environ.get("PERPLEXICA_ENABLED") == "false"


@pytest.mark.unit
def test_generate_hitl_git_publishing_passes_through(monkeypatch):
    runner = CliRunner()
    captured = {}

    async def _fake_run_auto_git_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import auto_git_cli as cli_mod
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cli_mod.Confirm, "ask", lambda *args, **kwargs: True)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)

    result = runner.invoke(
        app,
        [
            "generate",
            "Build a CLI",
            "--trust-mode",
            "constrained",
            "--hitl-git-publishing",
            "approve",
            "--no-search",
        ],
    )

    assert result.exit_code == 0
    assert captured.get("hitl_decisions", {}).get("git_publishing") == "approve"


@pytest.mark.unit
def test_replay_resume_hitl_interactive_prompts_and_passes_decision(monkeypatch):
    runner = CliRunner()
    captured = {}

    class _Bundle:
        provider = "memory"
        checkpointer = object()
        location = "in-memory"

        @staticmethod
        def close():
            return None

    def _fake_create_checkpointer(provider=None, logs_dir="logs"):
        return _Bundle()

    def _fake_load_existing_checkpoint(checkpointer, config):
        return {
            "current_stage": "code_fixing",
            "errors": [],
            "warnings": [],
            "_node_exec_frequency": {"code_testing": 2},
            "_loop_detection_state": "clean",
        }

    async def _fake_run_auto_git_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "current_stage": "published",
            "errors": [],
            "warnings": [],
            "published": True,
            "github_url": "https://example.test/repo",
        }

    import auto_git_cli as cli_mod
    import src.langraph_pipeline.checkpointer_factory as cf
    import src.langraph_pipeline.workflow_enhanced as wf

    monkeypatch.setattr(cf, "create_checkpointer", _fake_create_checkpointer)
    monkeypatch.setattr(cf, "load_existing_checkpoint", _fake_load_existing_checkpoint)
    monkeypatch.setattr(wf, "run_auto_git_pipeline", _fake_run_auto_git_pipeline)
    monkeypatch.setattr(cli_mod.Prompt, "ask", lambda *args, **kwargs: "edit")

    result = runner.invoke(
        app,
        [
            "replay",
            "--thread-id",
            "t-1",
            "--checkpointer",
            "memory",
            "--resume-run",
            "--trust-mode",
            "constrained",
            "--hitl-interactive",
            "--force-resume",
        ],
    )

    assert result.exit_code == 0
    assert captured.get("hitl_decisions", {}).get("git_publishing") == "edit"
