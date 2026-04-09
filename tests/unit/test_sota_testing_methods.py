"""SOTA-inspired reliability tests: property, metamorphic, mutation-style, and chaos/fault-injection checks."""

import pytest

from src.langraph_pipeline.state import create_initial_state
from src.langraph_pipeline.workflow_enhanced import (
    _compute_workflow_fingerprint,
    _update_loop_detection_state,
)


@pytest.mark.unit
def test_property_fingerprint_deterministic_under_key_permutation():
    base_a = {
        "current_stage": "code_tested",
        "tests_passed": False,
        "fix_attempts": 2,
        "generated_code": {
            "files": {
                "a.py": "print('a')\n",
                "b.py": "print('b')\n",
            }
        },
        "test_results": {
            "execution_errors": ["NameError: x is not defined", "ImportError: y"]
        },
    }

    # Same semantic state, different dict insertion order.
    base_b = {
        "fix_attempts": 2,
        "test_results": {
            "execution_errors": ["NameError: x is not defined", "ImportError: y"]
        },
        "generated_code": {
            "files": {
                "b.py": "print('b')\n",
                "a.py": "print('a')\n",
            }
        },
        "tests_passed": False,
        "current_stage": "code_tested",
    }

    fp_a = _compute_workflow_fingerprint(base_a, "code_testing", "code_tested")
    fp_b = _compute_workflow_fingerprint(base_b, "code_testing", "code_tested")

    assert fp_a == fp_b


@pytest.mark.unit
def test_metamorphic_fingerprint_changes_on_semantic_changes():
    base = {
        "current_stage": "code_tested",
        "tests_passed": False,
        "fix_attempts": 0,
        "generated_code": {"files": {"main.py": "print('x')\n"}},
        "test_results": {"execution_errors": ["NameError: x"]},
    }

    fp_base = _compute_workflow_fingerprint(base, "code_testing", "code_tested")

    changed_pass = dict(base)
    changed_pass["tests_passed"] = True
    fp_changed_pass = _compute_workflow_fingerprint(changed_pass, "code_testing", "code_tested")

    changed_attempt = dict(base)
    changed_attempt["fix_attempts"] = 1
    fp_changed_attempt = _compute_workflow_fingerprint(changed_attempt, "code_testing", "code_tested")

    assert fp_base != fp_changed_pass
    assert fp_base != fp_changed_attempt


@pytest.mark.unit
def test_mutation_style_repeatability_same_input_same_signature():
    state = {
        "current_stage": "code_tested",
        "tests_passed": False,
        "fix_attempts": 3,
        "generated_code": {"files": {"main.py": "print('x')\n"}},
        "test_results": {"execution_errors": ["TypeError: boom"]},
    }

    signatures = {
        _compute_workflow_fingerprint(state, "code_testing", "code_tested")
        for _ in range(25)
    }

    assert len(signatures) == 1


@pytest.mark.unit
def test_chaos_fault_injection_normalizes_non_list_warning_fields():
    state = create_initial_state(idea="Build a CLI")
    # Force immediate hard-limit on next update for this node.
    state["_node_exec_frequency"] = {"solution_generation": 8}

    # Intentionally malformed types from an upstream node/checkpoint.
    result = {
        "current_stage": "solution_generation_in_progress",
        "warnings": "existing warning",
        "resource_events": {"bad": "shape"},
    }

    updated = _update_loop_detection_state(state, "solution_generation", result)

    assert updated["_loop_detection_state"] == "hard_limit"
    assert isinstance(updated["warnings"], list)
    assert "existing warning" in updated["warnings"]
    assert any("Loop detector hard limit" in w for w in updated["warnings"])

    assert isinstance(updated["resource_events"], list)
    assert any(isinstance(evt, dict) and evt.get("event") == "loop_hard_limit" for evt in updated["resource_events"])
