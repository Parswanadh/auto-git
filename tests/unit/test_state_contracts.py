"""
Zero-cost tests for state contract validation.

Verifies that pipeline nodes honor the state contracts —
correct input/output shapes, no silent state key explosions,
no missing fields that cause downstream crashes.

Run with: pytest tests/unit/test_state_contracts.py -v
Cost: $0.00
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.mark.unit
class TestAutoGITStateCreation:
    """Test the official create_initial_state factory."""

    @pytest.fixture(autouse=True)
    def import_factory(self):
        from src.langraph_pipeline.state import create_initial_state
        self.create = create_initial_state

    def test_minimal_creation(self):
        state = self.create(idea="test idea")
        assert state["idea"] == "test idea"
        assert state["current_stage"] == "initialized"

    def test_defaults_safe_for_pipeline(self):
        """All defaults must be safe — no None where a list/dict is expected."""
        state = self.create(idea="test")
        # Lists must be actual lists, not None
        assert isinstance(state["errors"], list)
        assert isinstance(state["warnings"], list)
        assert isinstance(state["debate_rounds"], list)
        assert isinstance(state["problems"], list)
        assert isinstance(state["_prev_fix_strategies"], list)
        # Dicts must be actual dicts, not None
        assert isinstance(state["generated_code"], dict)
        assert isinstance(state["_persistent_error_tracker"], dict)

    def test_tests_passed_defaults_false(self):
        """S22 bug: tests_passed defaulted to True → broken code got published."""
        state = self.create(idea="test")
        assert state["tests_passed"] is False

    def test_fix_attempts_starts_at_zero(self):
        state = self.create(idea="test")
        assert state["fix_attempts"] == 0
        assert state["max_fix_attempts"] == 8

    def test_custom_rounds_and_consensus(self):
        state = self.create(idea="test", max_rounds=5, min_consensus=0.9)
        assert state["max_debate_rounds"] == 5
        assert state["min_consensus_score"] == 0.9

    def test_perspectives_populated(self):
        state = self.create(idea="test")
        assert len(state["perspectives"]) >= 3

    def test_pipeline_start_time_is_valid_iso(self):
        state = self.create(idea="test")
        # Should not throw on parse
        datetime.fromisoformat(state["pipeline_start_time"])

    def test_auto_publish_defaults_false(self):
        state = self.create(idea="test")
        assert state.get("auto_publish", False) is False

    def test_self_eval_fields_present(self):
        state = self.create(idea="test")
        assert state["self_eval_attempts"] == 0
        assert state["self_eval_score"] == -1.0

    def test_goal_eval_fields_present(self):
        state = self.create(idea="test")
        assert state["goal_eval_attempts"] == 0
        assert state["goal_eval_report"] is None

    def test_eval_verification_flags_default_false(self):
        state = self.create(idea="test")
        assert state["self_eval_unverified"] is False
        assert state["goal_eval_unverified"] is False

    def test_todo_tracking_fields_present(self):
        state = self.create(idea="test")
        assert isinstance(state["pipeline_todos"], list)
        assert isinstance(state["todo_progress"], dict)
        assert isinstance(state["todo_generation_notes"], str)

    def test_loop_tracking_fields_present(self):
        state = self.create(idea="test")
        assert isinstance(state["_node_exec_frequency"], dict)
        assert isinstance(state["_current_node_path"], list)
        assert isinstance(state["_node_paths_history"], list)
        assert isinstance(state["_workflow_state_fingerprints"], list)
        assert isinstance(state["_loop_detection_notes"], list)
        assert state["_loop_detection_state"] == "clean"
        assert state["phase_lock_current_phase"] == 0
        assert isinstance(state["phase_gate_history"], list)
        assert state["phase_lock_policy_version"] == "v1"

    def test_policy_and_offload_fields_present(self):
        state = self.create(idea="test")
        assert isinstance(state["structured_errors"], list)
        assert isinstance(state["telemetry_parity"], dict)
        assert state["runtime_manifest"] is None
        assert state["run_runtime_manifest"] is None
        assert isinstance(state["context_offload_refs"], list)
        assert state["todo_context_pointer"] is None
        assert state["summarize_now"] is False
        assert state["trust_mode"] == "trusted"
        assert state["tool_allowlist_mode"] == "permissive"
        assert isinstance(state["hitl_decisions"], dict)
        assert isinstance(state["policy_events"], list)
        assert state["checkpointer_provider"] == "sqlite"
        assert state["model_failover_profile"] == "balanced"


@pytest.mark.unit
class TestStateFieldTypes:
    """Ensure state types match what nodes expect via .get() calls."""

    @pytest.fixture
    def state(self):
        from src.langraph_pipeline.state import create_initial_state
        return create_initial_state(idea="test")

    def test_appendable_lists_work(self, state):
        """Annotated[List, operator.add] fields must support append/extend."""
        state["errors"].append("err1")
        state["warnings"].append("warn1")
        state["debate_rounds"].append({"round_number": 1})
        assert len(state["errors"]) == 1
        assert len(state["warnings"]) == 1

    def test_generated_code_supports_files_key(self, state):
        """generated_code starts empty but must support files/approach keys."""
        state["generated_code"]["files"] = {"main.py": "print('hi')"}
        state["generated_code"]["approach"] = "test approach"
        assert "main.py" in state["generated_code"]["files"]


@pytest.mark.unit
class TestPerspectiveConfigs:
    """Test expert perspective definitions."""

    def test_expert_perspectives_exist(self):
        from src.langraph_pipeline.state import EXPERT_PERSPECTIVES
        assert len(EXPERT_PERSPECTIVES) >= 3

    def test_perspectives_have_names(self):
        from src.langraph_pipeline.state import EXPERT_PERSPECTIVES
        for p in EXPERT_PERSPECTIVES:
            assert "name" in p
            assert isinstance(p["name"], str)
            assert len(p["name"]) > 0
