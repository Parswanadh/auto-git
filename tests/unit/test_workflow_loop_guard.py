"""Unit tests for workflow-level loop detection and hard-limit routing."""

import pytest

from src.langraph_pipeline.state import create_initial_state
from src.langraph_pipeline.workflow_enhanced import (
    _update_loop_detection_state,
    should_continue_debate,
    should_fix_code,
    should_regen_or_publish,
)


@pytest.mark.unit
def test_loop_detector_tracks_counts_and_paths():
    state = create_initial_state(idea="Build a CLI")
    result = {"current_stage": "code_tested"}

    updated = _update_loop_detection_state(state, "code_testing", result)

    assert updated["_node_exec_frequency"]["code_testing"] == 1
    assert updated["_current_node_path"][-1] == "code_testing"
    assert len(updated["_workflow_state_fingerprints"]) == 1
    assert updated["_loop_detection_state"] in {"clean", "hard_limit"}


@pytest.mark.unit
def test_loop_detector_trips_hard_limit_on_node_count():
    state = create_initial_state(idea="Build a CLI")

    for _ in range(9):
        result = {"current_stage": "solution_generation_in_progress"}
        patch = _update_loop_detection_state(state, "solution_generation", result)
        state = dict(state)
        state.update(patch)

    assert state["_loop_detection_state"] == "hard_limit"
    assert any("solution_generation" in note for note in state.get("_loop_detection_notes", []))


@pytest.mark.unit
def test_loop_detector_trips_hard_limit_on_signature_oscillation():
    state = create_initial_state(idea="Build a CLI")

    repeated = {
        "current_stage": "fixing_in_progress",
        "tests_passed": False,
        "fix_attempts": 1,
        "generated_code": {"files": {"main.py": "print('x')\n"}},
        "test_results": {"execution_errors": ["NameError: x is not defined"]},
    }

    for _ in range(4):
        patch = _update_loop_detection_state(state, "code_fixing", dict(repeated))
        state = dict(state)
        state.update(patch)

    assert state["_loop_detection_state"] == "hard_limit"
    assert any("repeat_signature" in note for note in state.get("_loop_detection_notes", []))


@pytest.mark.unit
def test_should_continue_debate_forces_select_on_hard_limit():
    state = create_initial_state(idea="Build a CLI")
    state["_loop_detection_state"] = "hard_limit"

    assert should_continue_debate(state) == "select"


@pytest.mark.unit
def test_should_fix_code_routes_fix_on_hard_limit_when_correctness_fails():
    state = create_initial_state(idea="Build a CLI")
    state["_loop_detection_state"] = "hard_limit"
    state["generated_code"] = {"files": {"main.py": "print('x')\n"}}
    state["test_results"] = {"execution_errors": ["RuntimeError: boom"]}

    assert should_fix_code(state) == "fix"


@pytest.mark.unit
def test_should_fix_code_routes_publish_on_hard_limit_when_correctness_passes():
    state = create_initial_state(idea="Build a CLI")
    state["_loop_detection_state"] = "hard_limit"
    state["generated_code"] = {"files": {"main.py": "print('ok')\n"}}
    state["tests_passed"] = True
    state["correctness_passed"] = True
    state["test_results"] = {"execution_errors": []}

    assert should_fix_code(state) == "publish"


@pytest.mark.unit
def test_should_regen_or_publish_routes_fix_on_hard_limit_when_correctness_fails():
    state = create_initial_state(idea="Build a CLI")
    state["_loop_detection_state"] = "hard_limit"
    state["current_stage"] = "self_eval_needs_regen"
    state["test_results"] = {"execution_errors": ["RuntimeError: boom"]}

    assert should_regen_or_publish(state) == "fix"


@pytest.mark.unit
def test_should_regen_or_publish_routes_publish_on_hard_limit_when_correctness_passes():
    state = create_initial_state(idea="Build a CLI")
    state["_loop_detection_state"] = "hard_limit"
    state["current_stage"] = "self_eval_approved"
    state["tests_passed"] = True
    state["correctness_passed"] = True
    state["test_results"] = {"execution_errors": []}

    assert should_regen_or_publish(state) == "publish"
