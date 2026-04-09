"""Parity symmetry tests for trace/status error-count contracts."""

import pytest

from src.utils.pipeline_tracer import compute_error_count, validate_trace_status_parity


@pytest.mark.unit
def test_compute_error_count_uses_max_signal_across_sources():
    state = {
        "errors": ["E1", "E2", "E3"],
        "hard_failures": ["H1"],
        "quality_gate": {"hard_failures_count": 2},
    }

    assert compute_error_count(state) == 3


@pytest.mark.unit
def test_compute_error_count_handles_non_list_fields_safely():
    state = {
        "errors": "oops",
        "hard_failures": None,
        "quality_gate": {"hard_failures_count": "4"},
    }

    assert compute_error_count(state) == 4


@pytest.mark.unit
def test_validate_trace_status_parity_ok_when_error_count_matches_shared_helper():
    state = {
        "errors": ["RuntimeError: boom"],
        "hard_failures": [],
        "quality_gate": {"hard_failures_count": 0},
    }
    shared_count = compute_error_count(state)

    trace_snapshot = {
        "node_calls": {"code_testing": 1, "feature_verification": 1},
        "current_stage": "testing_complete",
        "error_count": shared_count,
    }
    status_snapshot = {
        "node_calls": {"code_testing": 1, "feature_verification": 1},
        "current_stage": "testing_complete",
        "error_count": shared_count,
    }

    parity = validate_trace_status_parity(trace_snapshot, status_snapshot)

    assert parity["ok"] is True
    assert parity["mismatches"] == []


@pytest.mark.unit
def test_validate_trace_status_parity_reports_error_count_mismatch():
    trace_snapshot = {
        "node_calls": {"code_testing": 1},
        "current_stage": "testing_complete",
        "error_count": 1,
    }
    status_snapshot = {
        "node_calls": {"code_testing": 1},
        "current_stage": "testing_complete",
        "error_count": 0,
    }

    parity = validate_trace_status_parity(trace_snapshot, status_snapshot)

    assert parity["ok"] is False
    assert any("error_count mismatch" in item for item in parity["mismatches"])
