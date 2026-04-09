"""Unit tests for direct control-loop route helpers and timeout telemetry."""

import pytest

from src.langraph_pipeline.workflow_enhanced import (
    _append_budget_report,
    _classify_timeout_source,
    _route_after_code_testing,
    _route_after_fixing,
    _route_after_smoke_test,
)


@pytest.mark.unit
def test_route_after_fixing_routes_retest_on_quality_gate_contradiction(make_state):
    state = make_state(quality_gate={"contradiction_detected": True})

    route = _route_after_fixing(state)

    assert route == "retest"
    rejections = state.get("phase_gate_rejections", [])
    assert rejections
    assert rejections[-1]["node"] == "_after_fixing"


@pytest.mark.unit
def test_route_after_code_testing_routes_verify_when_tests_pass(make_state):
    state = make_state(
        current_stage="testing_complete",
        tests_passed=True,
        generated_code={"files": {"main.py": "print('ok')\n"}},
    )

    assert _route_after_code_testing(state) == "verify"


@pytest.mark.unit
def test_route_after_code_testing_routes_fix_when_tests_fail_with_files(make_state):
    state = make_state(
        current_stage="testing_complete",
        tests_passed=False,
        generated_code={"files": {"main.py": "print('boom')\n"}},
    )

    assert _route_after_code_testing(state) == "fix"


@pytest.mark.unit
def test_route_after_fixing_routes_regenerate_on_stagnation(make_state):
    state = make_state(current_stage="fix_stagnated")

    assert _route_after_fixing(state) == "regenerate"


@pytest.mark.unit
@pytest.mark.parametrize("stage", ["no_errors_to_fix", "fixing_failed", "fixing_error"])
def test_route_after_fixing_routes_smoke_for_non_actionable_fix_stage(make_state, stage):
    state = make_state(current_stage=stage)

    route = _route_after_fixing(state)

    assert route == "smoke"


@pytest.mark.unit
def test_route_after_fixing_routes_review_on_first_fix_cycle_when_requested(make_state):
    state = make_state(
        current_stage="code_fixed",
        fix_attempts=1,
        fix_review_required=True,
    )

    assert _route_after_fixing(state) == "review"


@pytest.mark.unit
def test_route_after_fixing_routes_retest_on_subsequent_fix_cycles(make_state):
    state = make_state(
        current_stage="code_fixed",
        fix_attempts=2,
        fix_review_required=True,
    )

    assert _route_after_fixing(state) == "retest"


@pytest.mark.unit
def test_route_after_smoke_test_routes_fix_on_quality_gate_contradiction(make_state):
    state = make_state(quality_gate={"contradiction_detected": True})

    route = _route_after_smoke_test(state)

    assert route == "fix"
    rejections = state.get("phase_gate_rejections", [])
    assert rejections
    assert rejections[-1]["node"] == "_after_smoke_test"


@pytest.mark.unit
def test_route_after_smoke_test_routes_eval_when_smoke_passes(make_state):
    state = make_state(smoke_test={"passed": True})

    assert _route_after_smoke_test(state) == "eval"


@pytest.mark.unit
def test_route_after_smoke_test_routes_fix_when_smoke_fails_and_budget_remains(make_state):
    state = make_state(
        smoke_test={"passed": False},
        current_stage="smoke_test_failed",
        fix_attempts=2,
        max_fix_attempts=5,
    )

    assert _route_after_smoke_test(state) == "fix"


@pytest.mark.unit
def test_route_after_smoke_test_routes_eval_when_smoke_fails_and_budget_exhausted(make_state):
    state = make_state(
        smoke_test={"passed": False},
        current_stage="smoke_test_failed",
        fix_attempts=5,
        max_fix_attempts=5,
    )

    route = _route_after_smoke_test(state)

    assert route == "eval"
    rejections = state.get("phase_gate_rejections", [])
    assert rejections
    assert rejections[-1]["node"] == "_after_smoke_test"


@pytest.mark.unit
def test_classify_timeout_source_hard_timeout():
    policy = {"soft_budget_s": 60, "hard_timeout_s": 120}

    source = _classify_timeout_source({}, elapsed_s=5.0, policy=policy, timed_out=True)

    assert source == "policy_hard_timeout"


@pytest.mark.unit
def test_classify_timeout_source_node_internal_timeout_marker():
    policy = {"soft_budget_s": 60, "hard_timeout_s": 120}
    result = {"current_stage": "code_generation_timeout"}

    source = _classify_timeout_source(result, elapsed_s=10.0, policy=policy, timed_out=False)

    assert source == "node_internal_timeout"


@pytest.mark.unit
def test_classify_timeout_source_hard_timeout_overrun_without_marker():
    policy = {"soft_budget_s": 60, "hard_timeout_s": 120}

    source = _classify_timeout_source({}, elapsed_s=130.0, policy=policy, timed_out=False)

    assert source == "cancellation_delay"


@pytest.mark.unit
def test_classify_timeout_source_provider_stall_when_timeout_and_rate_limit_markers_exist():
    policy = {"soft_budget_s": 60, "hard_timeout_s": 120}
    result = {
        "current_stage": "feature_verification_timeout",
        "warnings": ["OpenRouter provider cooldown active due to 429 rate limit"],
    }

    source = _classify_timeout_source(result, elapsed_s=65.0, policy=policy, timed_out=False)

    assert source == "provider_stall"


@pytest.mark.unit
def test_classify_timeout_source_soft_budget_exceeded():
    policy = {"soft_budget_s": 60, "hard_timeout_s": 120}

    source = _classify_timeout_source({}, elapsed_s=61.0, policy=policy, timed_out=False)

    assert source == "soft_budget_exceeded"


@pytest.mark.unit
def test_classify_timeout_source_none_when_within_budget_and_no_markers():
    policy = {"soft_budget_s": 60, "hard_timeout_s": 120}

    source = _classify_timeout_source({}, elapsed_s=10.0, policy=policy, timed_out=False)

    assert source == "none"


@pytest.mark.unit
def test_append_budget_report_persists_timeout_source_metadata(make_state):
    state = make_state(node_budget_report={})
    policy = {"soft_budget_s": 60, "hard_timeout_s": 120}

    report = _append_budget_report(
        state,
        node_name="code_generation",
        elapsed_s=12.345,
        policy=policy,
        waited_s=1.25,
        timed_out=False,
        timeout_source="soft_budget_exceeded",
    )

    entry = report["code_generation"]
    assert entry["elapsed_s"] == 12.345
    assert entry["soft_budget_s"] == 60
    assert entry["hard_timeout_s"] == 120
    assert entry["effective_soft_budget_s"] == 60
    assert entry["effective_hard_timeout_s"] == 120
    assert entry["waited_for_resources_s"] == 1.25
    assert entry["timed_out"] is False
    assert entry["timeout_source"] == "soft_budget_exceeded"
    assert entry["updated_at"]
