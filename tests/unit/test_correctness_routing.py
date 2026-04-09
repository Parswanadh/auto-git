"""Regression tests for truth-first correctness routing and publish gating."""

import builtins

import pytest

from src.langraph_pipeline.workflow_enhanced import (
    _apply_quality_contract,
    _build_timeout_fallback,
    _derive_correctness_snapshot,
    _persist_phase_gate_scorecard,
    _update_pipeline_todos,
    should_publish_after_goal_eval,
    should_fix_code,
    should_regen_or_publish,
)
from src.langraph_pipeline.nodes import git_publishing_node


@pytest.mark.unit
def test_should_fix_code_routes_to_fix_on_hard_failures_even_if_tests_passed(make_state):
    state = make_state(
        tests_passed=True,
        generated_code={"files": {"main.py": "print('ok')\n"}},
        test_results={"execution_errors": ["RuntimeError: boom"]},
    )

    assert should_fix_code(state) == "fix"


@pytest.mark.unit
def test_should_fix_code_routes_publish_when_correctness_passed(make_state):
    state = make_state(
        tests_passed=True,
        generated_code={"files": {"main.py": "print('ok')\n"}},
        test_results={"execution_errors": []},
    )

    assert should_fix_code(state) == "publish"


@pytest.mark.unit
def test_should_regen_or_publish_routes_fix_when_correctness_failed(make_state):
    state = make_state(
        current_stage="self_eval_approved",
        tests_passed=True,
        fix_attempts=2,
        max_fix_attempts=8,
        test_results={"execution_errors": ["TypeError: bad"]},
    )

    assert should_regen_or_publish(state) == "fix"


@pytest.mark.unit
def test_should_regen_or_publish_routes_publish_when_budget_exhausted(make_state):
    state = make_state(
        current_stage="self_eval_needs_regen",
        tests_passed=False,
        fix_attempts=8,
        max_fix_attempts=8,
        test_results={"execution_errors": ["TypeError: bad"]},
    )

    assert should_regen_or_publish(state) == "publish"
    assert state.get("phase_lock_current_phase") == 3


@pytest.mark.unit
def test_should_regen_or_publish_routes_fix_on_artifact_incomplete(make_state):
    state = make_state(
        current_stage="self_eval_approved",
        fix_attempts=2,
        max_fix_attempts=8,
        test_results={"verification_state": "artifact_incomplete", "execution_errors": []},
    )

    assert should_regen_or_publish(state) == "fix"


@pytest.mark.unit
def test_should_regen_or_publish_breaks_noop_loop_when_smoke_passes(make_state):
    state = make_state(
        current_stage="self_eval_approved",
        fix_attempts=3,
        max_fix_attempts=8,
        tests_passed=False,
        smoke_test={"passed": True},
        test_results={"execution_errors": []},
        _node_exec_frequency={"pipeline_self_eval": 2},
    )

    assert should_regen_or_publish(state) == "publish"
    assert state.get("phase_lock_current_phase") == 3
    assert state.get("phase_gate_history")


@pytest.mark.unit
def test_should_publish_after_goal_eval_blocks_when_phase_missing(make_state):
    state = make_state(
        current_stage="post_testing",
        tests_passed=True,
        correctness_passed=True,
        phase_lock_current_phase=2,
        test_results={"execution_errors": []},
    )

    assert should_publish_after_goal_eval(state) == "fix"
    history = state.get("phase_gate_history", [])
    assert history
    assert history[-1]["gate"] == "goal_eval_to_publish"
    assert history[-1]["allowed"] is False


@pytest.mark.unit
def test_should_publish_after_goal_eval_infers_goal_stage_and_allows_publish(make_state):
    state = make_state(
        current_stage="goal_eval_approved",
        tests_passed=True,
        correctness_passed=True,
        phase_lock_current_phase=0,
        test_results={"execution_errors": []},
    )

    assert should_publish_after_goal_eval(state) == "publish"
    assert state.get("phase_lock_current_phase") == 4
    history = state.get("phase_gate_history", [])
    assert any(item.get("gate") == "phase_inference" for item in history)


@pytest.mark.unit
def test_should_publish_after_goal_eval_breaks_noop_loop_when_smoke_passes(make_state):
    state = make_state(
        current_stage="goal_eval_approved",
        tests_passed=False,
        correctness_passed=False,
        phase_lock_current_phase=3,
        smoke_test={"passed": True},
        test_results={"execution_errors": []},
        _node_exec_frequency={"goal_achievement_eval": 2},
    )

    assert should_publish_after_goal_eval(state) == "publish"
    assert state.get("phase_lock_current_phase") == 4


@pytest.mark.unit
def test_should_fix_code_routes_publish_when_no_files_generated(make_state):
    state = make_state(
        current_stage="testing_complete",
        tests_passed=False,
        generated_code={"files": {}},
        test_results={"execution_errors": ["RuntimeError: boom"]},
    )

    assert should_fix_code(state) == "publish"


@pytest.mark.unit
def test_should_fix_code_routes_fix_on_artifact_incomplete(make_state):
    state = make_state(
        current_stage="testing_complete",
        tests_passed=True,
        generated_code={"files": {"main.py": "print('ok')\n"}},
        test_results={"verification_state": "artifact_incomplete", "execution_errors": []},
    )

    assert should_fix_code(state) == "fix"


@pytest.mark.unit
def test_should_fix_code_routes_fix_on_security_gate_failure(make_state):
    state = make_state(
        current_stage="testing_complete",
        tests_passed=True,
        fix_attempts=1,
        max_fix_attempts=8,
        generated_code={"files": {"main.py": "print('ok')\n"}},
        test_results={"execution_errors": [], "security_gate_failed": True},
    )

    assert should_fix_code(state) == "fix"


@pytest.mark.unit
def test_should_fix_code_routes_publish_when_security_gate_fails_and_budget_exhausted(make_state):
    state = make_state(
        current_stage="testing_complete",
        tests_passed=True,
        fix_attempts=8,
        max_fix_attempts=8,
        generated_code={"files": {"main.py": "print('ok')\n"}},
        test_results={"execution_errors": [], "security_gate_failed": True},
    )

    assert should_fix_code(state) == "publish"


@pytest.mark.unit
def test_should_fix_code_hard_limit_still_routes_fix_when_correctness_fails(make_state):
    state = make_state(
        _loop_detection_state="hard_limit",
        tests_passed=True,
        fix_attempts=1,
        max_fix_attempts=8,
        generated_code={"files": {"main.py": "print('ok')\n"}},
        test_results={"execution_errors": ["RuntimeError: boom"]},
    )

    assert should_fix_code(state) == "fix"


@pytest.mark.unit
def test_should_regen_or_publish_hard_limit_routes_fix_when_correctness_fails(make_state):
    state = make_state(
        _loop_detection_state="hard_limit",
        current_stage="self_eval_approved",
        fix_attempts=2,
        max_fix_attempts=8,
        tests_passed=True,
        test_results={"execution_errors": ["RuntimeError: boom"]},
    )

    assert should_regen_or_publish(state) == "fix"


@pytest.mark.unit
def test_should_fix_code_forces_fix_on_quality_gate_contradiction(make_state):
    state = make_state(
        generated_code={"files": {"main.py": "print('ok')\n"}},
        quality_gate={"contradiction_detected": True},
    )

    route = should_fix_code(state)

    assert route == "fix"
    rejections = state.get("phase_gate_rejections", [])
    assert rejections
    assert rejections[-1]["node"] == "should_fix_code"


@pytest.mark.unit
def test_should_regen_or_publish_forces_fix_on_quality_gate_contradiction(make_state):
    state = make_state(
        current_stage="self_eval_approved",
        quality_gate={"contradiction_detected": True},
    )

    route = should_regen_or_publish(state)

    assert route == "fix"
    rejections = state.get("phase_gate_rejections", [])
    assert rejections
    assert rejections[-1]["node"] == "should_regen_or_publish"


@pytest.mark.unit
def test_feature_verification_timeout_fallback_fails_closed():
    patch = _build_timeout_fallback("feature_verification", "hard timeout")

    assert patch["current_stage"] == "feature_verification_skipped"
    assert patch["tests_passed"] is False
    assert "test_results" in patch
    assert patch["test_results"]["verification_state"] == "feature_verification_timeout"
    assert patch["test_results"]["execution_errors"]


@pytest.mark.unit
def test_derive_correctness_snapshot_requires_no_hard_failures():
    merged_state = {
        "tests_passed": True,
        "test_results": {"execution_errors": ["ImportError: missing x"]},
        "errors": [],
    }

    snapshot = _derive_correctness_snapshot(merged_state)

    assert snapshot["correctness_passed"] is False
    assert snapshot["hard_failures"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_git_publishing_blocks_when_correctness_failed(make_state, tmp_path):
    state = make_state(
        tests_passed=True,
        correctness_passed=False,
        hard_failures=["RuntimeError: still failing"],
        auto_publish=False,
        output_dir=str(tmp_path),
        final_solution={"approach_name": "correctness-gate-test"},
        generated_code={"files": {"main.py": "print('hello')\n"}},
    )

    result = await git_publishing_node(state)

    assert result["current_stage"] == "saved_locally_tests_failed"
    assert result.get("github_url") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_git_publishing_recomputes_stale_correctness_and_saves_locally(make_state, tmp_path):
    state = make_state(
        tests_passed=True,
        correctness_passed=False,  # stale flag from a prior loop iteration
        hard_failures=[],
        test_results={"execution_errors": []},
        auto_publish=False,
        output_dir=str(tmp_path),
        final_solution={"approach_name": "stale-correctness-recompute"},
        generated_code={"files": {"main.py": "print('hello')\n"}},
    )

    result = await git_publishing_node(state)

    assert result["current_stage"] != "saved_locally_tests_failed"
    assert result["current_stage"] in {"saved_locally", "saved_locally_after_error"}
    assert result.get("github_url") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_git_publishing_missing_pygithub_falls_back_to_saved_locally(make_state, tmp_path, monkeypatch):
    original_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "github":
            raise ImportError("No module named 'github'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    state = make_state(
        tests_passed=True,
        correctness_passed=True,
        hard_failures=[],
        test_results={"execution_errors": []},
        auto_publish=True,
        output_dir=str(tmp_path),
        final_solution={"approach_name": "missing-pygithub-fallback"},
        generated_code={"files": {"main.py": "print('ok')\n"}},
    )

    result = await git_publishing_node(state)

    assert result["current_stage"] == "saved_locally"
    assert result.get("github_url") is None
    assert "PyGithub not installed" in " ".join(result.get("warnings", []))


@pytest.mark.unit
def test_apply_quality_contract_detects_contradiction_and_blocks_final_success():
    state_patch = {
        "current_stage": "published",
        "tests_passed": True,
        "test_results": {"execution_errors": ["RuntimeError: boom"]},
    }

    normalized = _apply_quality_contract(state_patch, terminal=True)

    assert normalized["correctness_passed"] is False
    assert normalized["quality_gate"]["contradiction_detected"] is True
    assert normalized["final_success"] is False
    assert normalized["final_status"] == "needs_attention"


@pytest.mark.unit
def test_apply_quality_contract_sets_final_success_when_terminal_and_clean():
    state_patch = {
        "current_stage": "saved_locally",
        "tests_passed": True,
        "test_results": {"execution_errors": [], "warnings": ["minor"]},
    }

    normalized = _apply_quality_contract(state_patch, terminal=True)

    assert normalized["correctness_passed"] is True
    assert normalized["quality_gate"]["publish_eligible"] is True
    assert normalized["final_success"] is True
    assert normalized["final_status"] == "success"


@pytest.mark.unit
def test_apply_quality_contract_preserves_prior_contradiction_signal():
    state_patch = {
        "current_stage": "saved_locally_tests_failed",
        "tests_passed": False,
        "hard_failures": ["RuntimeError: still failing"],
        "warnings": [
            "QUALITY_GATE_CONTRADICTION: publish-like stage reached while correctness gate is failing (stage=testing_complete, tests_passed=True, hard_failures=2)."
        ],
    }

    normalized = _apply_quality_contract(state_patch, terminal=True)

    assert normalized["correctness_passed"] is False
    assert normalized["quality_gate"]["contradiction_detected"] is True
    assert normalized["quality_gate"]["publish_eligible"] is False
    assert normalized["final_success"] is False


@pytest.mark.unit
def test_apply_quality_contract_contradiction_dominates_even_if_tests_are_clean():
    state_patch = {
        "current_stage": "saved_locally",
        "tests_passed": True,
        "test_results": {"execution_errors": []},
        "warnings": [
            "QUALITY_GATE_CONTRADICTION: publish-like stage reached while correctness gate is failing (stage=testing_complete, tests_passed=True, hard_failures=1)."
        ],
    }

    normalized = _apply_quality_contract(state_patch, terminal=True)

    assert normalized["quality_gate"]["contradiction_detected"] is True
    assert normalized["quality_gate"]["publish_eligible"] is False
    assert normalized["final_success"] is False
    assert normalized["final_status"] == "needs_attention"
    assert "contradiction_detected" in normalized.get("quality_gate_reason", "")


@pytest.mark.unit
def test_persist_phase_gate_scorecard_writes_json(make_state, tmp_path):
    state = make_state(
        output_dir=str(tmp_path),
        current_stage="saved_locally_tests_failed",
        tests_passed=False,
        quality_gate={
            "hard_failures_count": 2,
            "correctness_passed": False,
            "contradiction_detected": True,
            "publish_eligible": False,
        },
        phase_gate_rejections=[{"node": "should_fix_code", "reason": "example"}],
    )

    path = _persist_phase_gate_scorecard(state)

    assert path is not None
    payload = (tmp_path / "phase_gate_scorecard.json").read_text(encoding="utf-8")
    assert "\"contradiction_detected\": true" in payload
    assert "\"phase_gate_rejections\"" in payload


@pytest.mark.unit
def test_update_pipeline_todos_blocks_publish_gate_when_saved_locally_tests_failed(make_state):
    state = make_state(
        pipeline_todos=[
            {
                "id": "GATE-PUBLISH",
                "title": "Publish or save verified deliverable",
                "status": "pending",
                "updated_stage": "initialized",
            }
        ]
    )
    result = {"current_stage": "saved_locally_tests_failed"}

    updated = _update_pipeline_todos(state, "git_publishing", result)
    todos = updated["pipeline_todos"]

    assert todos[0]["status"] == "blocked"
    assert todos[0]["updated_stage"] == "saved_locally_tests_failed"
