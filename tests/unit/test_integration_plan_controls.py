"""Unit tests for integration-plan controls (policy, offload, parity, checkpointer, failover)."""

import asyncio

import pytest

from src.langraph_pipeline.state import create_initial_state
from src.langraph_pipeline.workflow_enhanced import (
    _apply_quality_contract,
    _apply_stage_fanout_caps,
    _coerce_list_shape,
    _compute_failure_signature,
    _compute_generated_artifact_fingerprint,
    _is_runtime_relevant_file,
    _evaluate_execution_policy,
    _normalize_allowlist_mode,
    _trim_reasoning_payload,
    _normalize_failover_profile,
    _normalize_telemetry_parity_mode,
    _normalize_trust_mode,
    _cloud_provider_available,
    run_auto_git_pipeline,
    _update_failure_signature_tracking,
    _with_execution_policy,
)
from src.utils.context_offload import (
    compact_todos_with_pointer,
    restore_todo_context_if_missing,
)
from src.utils.pipeline_tracer import validate_trace_status_parity
from src.langraph_pipeline.checkpointer_factory import create_checkpointer
from src.model_router import ModelRouter, TaskType
from src.langraph_pipeline import nodes as pipeline_nodes


@pytest.mark.unit
def test_fanout_caps_trim_perspectives():
    state = create_initial_state(idea="Build a CLI")
    state["perspectives"] = [f"p{i}" for i in range(10)]

    updates = _apply_stage_fanout_caps(state, "solution_generation")

    assert updates["perspectives"] == [f"p{i}" for i in range(6)]
    assert any(evt.get("event") == "fanout_capped" for evt in updates.get("policy_events", []))


@pytest.mark.unit
def test_constrained_mode_blocks_publish_without_approval():
    state = create_initial_state(idea="Build a CLI")
    state["trust_mode"] = "constrained"
    state["tool_allowlist_mode"] = "strict"
    state["hitl_decisions"] = {}

    result = _evaluate_execution_policy(state, "git_publishing")

    assert result.get("blocked") is True
    assert result["result"]["current_stage"] == "publish_blocked_policy"


@pytest.mark.unit
def test_trace_status_parity_reports_mismatch():
    trace_snapshot = {
        "node_calls": {"research": 1, "code_generation": 1},
        "current_stage": "code_generated",
        "error_count": 0,
    }
    status_snapshot = {
        "node_calls": {"research": 1, "code_generation": 2},
        "current_stage": "code_generated",
        "error_count": 0,
    }

    parity = validate_trace_status_parity(trace_snapshot, status_snapshot)

    assert parity["ok"] is False
    assert any("count mismatch" in msg for msg in parity["mismatches"])


@pytest.mark.unit
def test_todo_pointer_restoration_note_when_inline_missing():
    updates = restore_todo_context_if_missing(
        {
            "pipeline_todos": [],
            "todo_context_pointer": "logs/offloaded_context/pipeline_todos_fake.txt",
            "warnings": [],
        }
    )

    assert "todo_generation_notes" in updates
    assert any("restored from pointer" in w.lower() for w in updates.get("warnings", []))


@pytest.mark.unit
def test_compact_todos_generates_pointer_for_large_list(tmp_path):
    todos = [{"id": f"T-{i}", "title": f"todo {i}"} for i in range(120)]

    updates = compact_todos_with_pointer(todos, output_dir=str(tmp_path), max_inline_items=50)

    assert len(updates.get("pipeline_todos", [])) == 50
    assert updates.get("todo_context_pointer")
    assert updates.get("context_offload_refs")


@pytest.mark.unit
def test_checkpointer_factory_memory_provider():
    bundle = create_checkpointer(provider="memory", logs_dir="logs")
    assert bundle.provider == "memory"
    assert bundle.checkpointer is not None


@pytest.mark.unit
def test_model_router_failover_uses_profile_when_primary_unhealthy():
    router = ModelRouter()
    primary = router.select_model(TaskType.CODE_GENERATION)

    chosen = router.select_model_with_failover(
        TaskType.CODE_GENERATION,
        profile="resilient",
        unhealthy_models=[primary],
    )

    assert chosen != primary
    assert chosen in router.models


@pytest.mark.unit
def test_workflow_normalizers_fallback_to_safe_defaults_on_invalid_inputs():
    assert _normalize_trust_mode("invalid") == "trusted"
    assert _normalize_allowlist_mode("invalid") == "permissive"
    assert _normalize_failover_profile("invalid") == "balanced"
    assert _normalize_telemetry_parity_mode("invalid") == "warn"


@pytest.mark.unit
def test_workflow_normalizers_accept_valid_inputs():
    assert _normalize_trust_mode("constrained") == "constrained"
    assert _normalize_allowlist_mode("strict") == "strict"
    assert _normalize_failover_profile("resilient") == "resilient"
    assert _normalize_telemetry_parity_mode("strict") == "strict"


@pytest.mark.unit
def test_coerce_list_shape_normalizes_scalar_fields():
    patched = _coerce_list_shape({"errors": "boom", "warnings": None})
    assert patched["errors"] == ["boom"]
    assert patched["warnings"] == []


@pytest.mark.unit
def test_generated_artifact_fingerprint_is_deterministic():
    state_a = {
        "generated_code": {
            "files": {
                "b.py": "print('b')\n",
                "a.py": "print('a')\n",
            }
        }
    }
    state_b = {
        "generated_code": {
            "files": {
                "a.py": "print('a')\n",
                "b.py": "print('b')\n",
            }
        }
    }
    assert _compute_generated_artifact_fingerprint(state_a) == _compute_generated_artifact_fingerprint(state_b)


@pytest.mark.unit
def test_runtime_artifact_fingerprint_ignores_doc_only_changes():
    state_a = {
        "generated_code": {
            "files": {
                "main.py": "print('ok')\n",
                "README.md": "v1\n",
            }
        }
    }
    state_b = {
        "generated_code": {
            "files": {
                "main.py": "print('ok')\n",
                "README.md": "v2 updated docs\n",
            }
        }
    }

    assert _compute_generated_artifact_fingerprint(state_a, mode="runtime") == _compute_generated_artifact_fingerprint(
        state_b, mode="runtime"
    )


@pytest.mark.unit
def test_runtime_relevant_file_classifier_marks_expected_files():
    assert _is_runtime_relevant_file("src/main.py") is True
    assert _is_runtime_relevant_file("requirements.txt") is True
    assert _is_runtime_relevant_file("README.md") is False


@pytest.mark.unit
def test_failure_signature_is_deterministic_for_same_failures():
    failed_state_a = {
        "current_stage": "testing_complete",
        "tests_passed": False,
        "test_results": {
            "execution_errors": ["ImportError: missing package", "AttributeError: foo"],
            "verification_state": "runtime_failed",
        },
    }
    failed_state_b = {
        "current_stage": "testing_complete",
        "tests_passed": False,
        "test_results": {
            "verification_state": "runtime_failed",
            "execution_errors": ["ImportError: missing package", "AttributeError: foo"],
        },
    }

    assert _compute_failure_signature(failed_state_a) == _compute_failure_signature(failed_state_b)


@pytest.mark.unit
def test_failure_signature_tracking_triggers_summarize_on_repetition():
    previous_state = {
        "_last_failure_signature": "",
        "_failure_signature_streak": 0,
    }
    node_state = {
        "current_stage": "testing_complete",
        "tests_passed": False,
        "test_results": {
            "execution_errors": ["ModuleNotFoundError: x"],
            "verification_state": "runtime_failed",
        },
    }

    first = _update_failure_signature_tracking(previous_state, dict(node_state), "code_testing")
    second = _update_failure_signature_tracking(first, dict(node_state), "code_testing")

    assert first.get("_failure_signature_streak") == 1
    assert second.get("_failure_signature_streak") == 2
    assert second.get("summarize_now") is True
    assert any("repeated failure signature" in w.lower() for w in second.get("warnings", []))


@pytest.mark.unit
def test_execution_policy_reuses_cached_smoke_result_when_artifacts_unchanged():
    calls = {"count": 0}

    async def _fake_smoke_node(_state):
        calls["count"] += 1
        return {
            "current_stage": "smoke_test_passed",
            "smoke_test": {"passed": True, "steps": []},
            "tests_passed": True,
        }

    wrapped = _with_execution_policy("smoke_test", _fake_smoke_node)
    base_state = create_initial_state(idea="Build a CLI")
    base_state["generated_code"] = {"files": {"main.py": "print('ok')\n"}}

    first = asyncio.run(wrapped(base_state))
    second_state = dict(base_state)
    second_state.update(first)
    second = asyncio.run(wrapped(second_state))

    assert calls["count"] == 1
    assert second.get("current_stage") == "smoke_test_passed"
    assert any("reused cached result" in w.lower() for w in second.get("warnings", []))


@pytest.mark.unit
def test_execution_policy_reuses_cached_feature_verification_result_when_runtime_unchanged():
    calls = {"count": 0}

    async def _fake_feature_node(_state):
        calls["count"] += 1
        return {
            "current_stage": "feature_verification_complete",
            "tests_passed": True,
            "test_results": {
                "feature_verification": {
                    "summary": {"pass_rate": 100}
                }
            },
        }

    wrapped = _with_execution_policy("feature_verification", _fake_feature_node)
    base_state = create_initial_state(idea="Build a CLI")
    base_state["generated_code"] = {
        "files": {
            "main.py": "print('ok')\n",
            "README.md": "v1\n",
        }
    }
    base_state["tests_passed"] = True
    base_state["test_results"] = {}

    first = asyncio.run(wrapped(base_state))
    second_state = dict(base_state)
    second_state.update(first)
    second_state["generated_code"] = {
        "files": {
            "main.py": "print('ok')\n",
            "README.md": "v2 docs only change\n",
        }
    }
    second = asyncio.run(wrapped(second_state))

    assert calls["count"] == 1
    assert second.get("current_stage") == "feature_verification_complete"
    assert any("reused cached result" in w.lower() for w in second.get("warnings", []))


@pytest.mark.unit
def test_cloud_provider_available_detects_groq_key_pool(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    for i in range(1, 8):
        monkeypatch.delenv(f"GROQ_API_KEY_{i}", raising=False)

    monkeypatch.setenv("GROQ_API_KEY_3", "gsk_test")
    assert _cloud_provider_available() is True


@pytest.mark.unit
def test_run_pipeline_fails_fast_when_cloud_only_and_no_cloud_keys(monkeypatch):
    monkeypatch.setenv("AUTOGIT_DISABLE_LOCAL_MODELS", "true")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    for i in range(1, 8):
        monkeypatch.delenv(f"GROQ_API_KEY_{i}", raising=False)

    with pytest.raises(RuntimeError, match="Cloud-only mode is enabled"):
        asyncio.run(
            run_auto_git_pipeline(
                idea="Build a CLI",
                stop_after="requirements_extraction",
                interactive=False,
                resume=False,
                checkpointer_provider="memory",
            )
        )


@pytest.mark.unit
def test_nodes_runtime_failover_profile_remaps_model_profile_calls():
    class _DummyManager:
        def get_fallback_llm(self, profile):
            return profile

    old_mgr = pipeline_nodes._model_manager
    pipeline_nodes._model_manager = _DummyManager()
    token = pipeline_nodes.set_runtime_failover_profile("cost_saver")
    try:
        assert pipeline_nodes.get_llm("powerful") == "balanced"
        assert pipeline_nodes.get_fallback_llm("reasoning") == "balanced"
        assert pipeline_nodes.get_llm("balanced") == "fast"
    finally:
        pipeline_nodes.reset_runtime_failover_profile(token)
        pipeline_nodes._model_manager = old_mgr


@pytest.mark.unit
def test_execution_policy_propagates_runtime_failover_profile_to_nodes():
    async def _fake_node(_state):
        return {
            "current_stage": "fake_done",
            "profile_seen": pipeline_nodes.get_runtime_failover_profile(),
        }

    wrapped = _with_execution_policy("requirements_extraction", _fake_node)
    state = create_initial_state(idea="Build a CLI")
    state["model_failover_profile"] = "resilient"

    result = asyncio.run(wrapped(state))

    assert result.get("current_stage") == "fake_done"
    assert result.get("profile_seen") == "resilient"


@pytest.mark.unit
def test_quality_contract_flags_contradiction_for_published_stage_with_failed_correctness():
    patched = _apply_quality_contract(
        {
            "current_stage": "published",
            "tests_passed": False,
            "hard_failures": ["runtime failure"],
        },
        terminal=True,
    )

    qg = patched.get("quality_gate", {})
    assert qg.get("contradiction_detected") is True
    assert qg.get("publish_eligible") is False
    assert patched.get("final_success") is False
    assert any("quality_gate_contradiction" in str(w).lower() for w in patched.get("warnings", []))


@pytest.mark.unit
def test_quality_contract_allows_terminal_success_only_when_publish_eligible():
    patched = _apply_quality_contract(
        {
            "current_stage": "saved_locally",
            "tests_passed": True,
            "hard_failures": [],
            "self_eval_unverified": False,
            "goal_eval_unverified": False,
        },
        terminal=True,
    )

    qg = patched.get("quality_gate", {})
    assert qg.get("contradiction_detected") is False
    assert qg.get("publish_eligible") is True
    assert patched.get("final_success") is True


@pytest.mark.unit
def test_execution_policy_marks_fix_stagnation_and_routes_regenerate_warning():
    async def _fake_code_fixing(_state):
        return {
            "current_stage": "code_fixed",
            "generated_code": {"files": {"main.py": "print('same')\n"}},
            "tests_passed": False,
        }

    wrapped = _with_execution_policy("code_fixing", _fake_code_fixing)
    base_state = create_initial_state(idea="Build a CLI")
    base_state["generated_code"] = {"files": {"main.py": "print('same')\n"}}
    base_state["tests_passed"] = False
    base_state["_last_fix_artifact_fp"] = _compute_generated_artifact_fingerprint(base_state, mode="runtime")
    base_state["_fix_stagnation_streak"] = 1

    result = asyncio.run(wrapped(base_state))

    assert result.get("current_stage") == "fix_stagnated"
    assert int(result.get("_fix_stagnation_streak", 0)) >= 2
    assert any("stagnated" in w.lower() for w in result.get("warnings", []))


@pytest.mark.unit
def test_trim_reasoning_payload_caps_error_volume_and_lengths():
    huge = {
        "errors": ["E" * 2000 for _ in range(200)],
        "warnings": ["W" * 1000 for _ in range(200)],
        "test_results": {
            "execution_errors": ["X" * 3000 for _ in range(100)],
            "smoke_test_errors": ["S" * 2200 for _ in range(100)],
            "tracebacks": ["T" * 6000 for _ in range(50)],
        },
    }

    trimmed = _trim_reasoning_payload(huge)

    assert len(trimmed.get("errors", [])) <= 40
    assert len(trimmed.get("warnings", [])) <= 30
    assert len(trimmed.get("test_results", {}).get("execution_errors", [])) <= 20
    assert len(trimmed.get("test_results", {}).get("smoke_test_errors", [])) <= 12
    assert len(trimmed.get("test_results", {}).get("tracebacks", [])) <= 8
    assert all(len(item) < 800 for item in trimmed.get("test_results", {}).get("tracebacks", []))
