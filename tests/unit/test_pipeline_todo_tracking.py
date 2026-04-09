"""Unit tests for pipeline todo generation and lifecycle tracking."""

from src.langraph_pipeline.state import create_initial_state
from src.langraph_pipeline.workflow_enhanced import _update_pipeline_todos


def _base_state():
    return create_initial_state(
        idea="Build a CLI todo manager",
        user_requirements="must support export; include retry logic",
        requirements={
            "project_type": "cli_tool",
            "complexity": "moderate",
            "core_components": ["task_store", "cli_interface"],
            "key_features": ["add task", "list tasks", "export tasks"],
            "test_scenarios": [
                {"name": "add task scenario", "expected": "task persists"},
            ],
        },
    )


def test_generates_detailed_todos_after_requirements_stage():
    state = _base_state()
    result = {
        "current_stage": "requirements_extracted",
        "requirements": state["requirements"],
    }

    updated = _update_pipeline_todos(state, "requirements_extraction", result)

    todos = updated.get("pipeline_todos", [])
    todo_ids = {t.get("id") for t in todos}

    assert "GATE-REQUIREMENTS" in todo_ids
    assert "GATE-RESEARCH" in todo_ids
    assert any((t.get("id") or "").startswith("COMP-") for t in todos)
    assert any((t.get("id") or "").startswith("FEAT-") for t in todos)
    assert any((t.get("id") or "").startswith("USER-") for t in todos)
    assert updated.get("todo_progress", {}).get("total", 0) >= 10


def test_goal_eval_maps_requirement_status_back_to_todos():
    state = _base_state()
    seeded = _update_pipeline_todos(
        state,
        "requirements_extraction",
        {
            "current_stage": "requirements_extracted",
            "requirements": state["requirements"],
        },
    )

    next_state = dict(state)
    next_state.update(seeded)

    eval_result = {
        "current_stage": "goal_eval_needs_work",
        "goal_eval_report": {
            "overall_pct_implemented": 66,
            "requirements": [
                {
                    "name": "add task",
                    "status": "implemented",
                    "evidence": "main.py::handle_add",
                },
                {
                    "name": "export tasks",
                    "status": "partial",
                    "evidence": "export command exists but CSV options incomplete",
                },
            ],
        },
    }

    updated = _update_pipeline_todos(next_state, "goal_achievement_eval", eval_result)
    todos = updated.get("pipeline_todos", [])

    add_task = next(t for t in todos if t.get("requirement_key") == "add task")
    export_tasks = next(t for t in todos if t.get("requirement_key") == "export tasks")

    assert add_task["status"] == "completed"
    assert export_tasks["status"] == "in_progress"
    assert updated.get("todo_progress", {}).get("completion_pct", 0) >= 0


def test_research_failure_marks_gate_blocked():
    state = _base_state()
    seeded = _update_pipeline_todos(
        state,
        "requirements_extraction",
        {
            "current_stage": "requirements_extracted",
            "requirements": state["requirements"],
        },
    )
    next_state = dict(state)
    next_state.update(seeded)

    updated = _update_pipeline_todos(next_state, "research", {"current_stage": "research_failed"})
    todos = updated["pipeline_todos"]
    research_gate = next(t for t in todos if t.get("id") == "GATE-RESEARCH")
    assert research_gate["status"] == "blocked"


def test_codegen_success_starts_requirement_items():
    state = _base_state()
    seeded = _update_pipeline_todos(
        state,
        "requirements_extraction",
        {
            "current_stage": "requirements_extracted",
            "requirements": state["requirements"],
        },
    )
    next_state = dict(state)
    next_state.update(seeded)

    updated = _update_pipeline_todos(next_state, "code_generation", {"current_stage": "code_generated"})
    todos = updated["pipeline_todos"]
    codegen_gate = next(t for t in todos if t.get("id") == "GATE-CODEGEN")
    assert codegen_gate["status"] == "completed"
    assert any(
        t.get("category") in {"component", "feature", "user_requirement", "test_scenario"}
        and t.get("status") == "in_progress"
        for t in todos
    )


def test_smoke_failure_marks_gate_blocked():
    state = _base_state()
    seeded = _update_pipeline_todos(
        state,
        "requirements_extraction",
        {
            "current_stage": "requirements_extracted",
            "requirements": state["requirements"],
        },
    )
    next_state = dict(state)
    next_state.update(seeded)

    updated = _update_pipeline_todos(
        next_state,
        "smoke_test",
        {
            "current_stage": "smoke_test_failed",
            "smoke_test": {"passed": False},
        },
    )
    smoke_gate = next(t for t in updated["pipeline_todos"] if t.get("id") == "GATE-SMOKE")
    assert smoke_gate["status"] == "blocked"
