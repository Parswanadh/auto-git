"""Unit tests for run-lineage artifact persistence helpers."""

import json

import pytest

from src.langraph_pipeline.workflow_enhanced import (
    _finalize_run_artifacts,
    _persist_run_lineage_manifest,
    _persist_run_result_snapshot,
    _persist_runtime_manifest,
)


@pytest.mark.unit
def test_persist_run_result_snapshot_writes_expected_payload(make_state, tmp_path):
    state = make_state(
        current_stage="saved_locally",
        final_status="success",
        final_success=True,
        tests_passed=True,
        quality_gate={"publish_eligible": True},
        output_path="output/example",
        github_url="",
    )

    result_path = _persist_run_result_snapshot(
        state,
        logs_dir=str(tmp_path),
        run_id="run123",
        thread_id="thread-01",
    )

    payload = json.loads((tmp_path / "run_result_thread-01_run123.json").read_text(encoding="utf-8"))
    assert result_path.endswith("run_result_thread-01_run123.json")
    assert payload["run_id"] == "run123"
    assert payload["thread_id"] == "thread-01"
    assert payload["current_stage"] == "saved_locally"
    assert payload["final_success"] is True


@pytest.mark.unit
def test_persist_run_lineage_manifest_marks_stage_consistency_true(tmp_path):
    trace_path = tmp_path / "pipeline_trace_abc.jsonl"
    status_path = tmp_path / "agent_status_abc.md"
    result_path = tmp_path / "result_abc.json"

    trace_path.write_text(
        "\n".join(
            [
                json.dumps({"event": "node_complete", "current_stage": "code_generated"}),
                json.dumps({"event": "pipeline_end", "final_stage": "published"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    status_path.write_text("**Final Stage**: `published`\n", encoding="utf-8")
    result_path.write_text(json.dumps({"current_stage": "published"}), encoding="utf-8")

    manifest_path = _persist_run_lineage_manifest(
        logs_dir=str(tmp_path),
        run_id="run123",
        thread_id="thread-01",
        trace_file=str(trace_path),
        status_file=str(status_path),
        result_file=str(result_path),
        started_at="2026-03-31T00:00:00",
        ended_at="2026-03-31T00:01:00",
        terminal_stage="published",
    )

    manifest = json.loads((tmp_path / "run_lineage_thread-01.json").read_text(encoding="utf-8"))
    assert manifest_path.endswith("run_lineage_thread-01.json")
    assert manifest["terminal_stage"] == "published"
    assert manifest["trace_terminal_stage"] == "published"
    assert manifest["status_terminal_stage"] == "published"
    assert manifest["result_terminal_stage"] == "published"
    assert manifest["consistency"]["files_exist"] is True
    assert manifest["consistency"]["all_stage_fields_present"] is True
    assert manifest["consistency"]["missing_stage_fields"] == []
    assert manifest["consistency"]["stages_match"] is True


@pytest.mark.unit
def test_persist_run_lineage_manifest_marks_stage_consistency_false_on_mismatch(tmp_path):
    trace_path = tmp_path / "pipeline_trace_abc.jsonl"
    status_path = tmp_path / "agent_status_abc.md"
    result_path = tmp_path / "result_abc.json"

    trace_path.write_text(
        json.dumps({"event": "pipeline_end", "final_stage": "published"}) + "\n",
        encoding="utf-8",
    )
    status_path.write_text("**Final Stage**: `fixing_error`\n", encoding="utf-8")
    result_path.write_text(json.dumps({"current_stage": "published"}), encoding="utf-8")

    _persist_run_lineage_manifest(
        logs_dir=str(tmp_path),
        run_id="run123",
        thread_id="thread-01",
        trace_file=str(trace_path),
        status_file=str(status_path),
        result_file=str(result_path),
        started_at="2026-03-31T00:00:00",
        ended_at="2026-03-31T00:01:00",
        terminal_stage="published",
    )

    manifest = json.loads((tmp_path / "run_lineage_thread-01.json").read_text(encoding="utf-8"))
    assert manifest["consistency"]["files_exist"] is True
    assert manifest["consistency"]["all_stage_fields_present"] is True
    assert manifest["consistency"]["stages_match"] is False


@pytest.mark.unit
def test_persist_run_lineage_manifest_marks_stage_consistency_false_on_missing_status_stage(tmp_path):
    trace_path = tmp_path / "pipeline_trace_abc.jsonl"
    status_path = tmp_path / "agent_status_abc.md"
    result_path = tmp_path / "result_abc.json"

    trace_path.write_text(
        json.dumps({"event": "pipeline_end", "final_stage": "published"}) + "\n",
        encoding="utf-8",
    )
    status_path.write_text("# status report without final-stage marker\n", encoding="utf-8")
    result_path.write_text(json.dumps({"current_stage": "published"}), encoding="utf-8")

    _persist_run_lineage_manifest(
        logs_dir=str(tmp_path),
        run_id="run123",
        thread_id="thread-01",
        trace_file=str(trace_path),
        status_file=str(status_path),
        result_file=str(result_path),
        started_at="2026-03-31T00:00:00",
        ended_at="2026-03-31T00:01:00",
        terminal_stage="published",
    )

    manifest = json.loads((tmp_path / "run_lineage_thread-01.json").read_text(encoding="utf-8"))
    assert manifest["status_terminal_stage"] == ""
    assert manifest["consistency"]["files_exist"] is True
    assert manifest["consistency"]["all_stage_fields_present"] is False
    assert "status_terminal_stage" in manifest["consistency"]["missing_stage_fields"]
    assert manifest["consistency"]["stages_match"] is False


@pytest.mark.unit
def test_persist_runtime_manifest_writes_runtime_fingerprint_and_artifact_links(make_state, tmp_path):
    state = make_state(
        current_stage="testing_complete",
        tests_passed=False,
        generated_code={"files": {"main.py": "print('ok')\n", "requirements.txt": "rich\n"}},
        context_offload_refs=[{"path": "logs/offloaded/example.txt"}],
        todo_context_pointer="logs/todos/context.json",
    )

    lineage_path = tmp_path / "run_lineage_thread-01.json"
    lineage_path.write_text(json.dumps({"terminal_stage": "testing_complete"}), encoding="utf-8")
    result_path = tmp_path / "run_result_thread-01_run123.json"
    result_path.write_text(json.dumps({"current_stage": "testing_complete"}), encoding="utf-8")

    runtime_path = _persist_runtime_manifest(
        state=state,
        logs_dir=str(tmp_path),
        run_id="run123",
        thread_id="thread-01",
        lineage_path=str(lineage_path),
        result_path=str(result_path),
    )

    payload = json.loads((tmp_path / "runtime_manifest_thread-01_run123.json").read_text(encoding="utf-8"))
    assert runtime_path.endswith("runtime_manifest_thread-01_run123.json")
    assert payload["run_id"] == "run123"
    assert payload["thread_id"] == "thread-01"
    assert payload["artifact_fingerprints"]["runtime"]
    assert payload["artifacts"]["lineage_manifest"].endswith("run_lineage_thread-01.json")
    assert payload["consistency"]["lineage_manifest_exists"] is True
    assert payload["consistency"]["result_snapshot_exists"] is True


@pytest.mark.unit
def test_finalize_run_artifacts_fails_closed_when_lineage_inconsistent(make_state, tmp_path):
    trace_path = tmp_path / "pipeline_trace_dummy.jsonl"
    status_path = tmp_path / "agent_status_dummy.md"
    trace_path.write_text(json.dumps({"event": "pipeline_end", "final_stage": "published"}) + "\n", encoding="utf-8")
    status_path.write_text("# missing final stage marker\n", encoding="utf-8")

    class DummyTracer:
        def __init__(self):
            self.ts = "run999"
            self.trace_path = str(trace_path)
            self.status_path = str(status_path)

        def finish(self, _state):
            return None

    state = make_state(
        current_stage="published",
        tests_passed=True,
        final_success=True,
        final_status="success",
        quality_gate={"publish_eligible": True, "final_success": True},
        warnings=[],
    )

    artifacts = _finalize_run_artifacts(
        state,
        tracer=DummyTracer(),
        thread_id="thread-01",
        started_at="2026-03-31T00:00:00",
        persist_scorecard=False,
    )

    result_payload = json.loads(open(artifacts["result_path"], "r", encoding="utf-8").read())
    lineage_payload = json.loads(open(artifacts["lineage_path"], "r", encoding="utf-8").read())
    runtime_payload = json.loads(open(artifacts["runtime_manifest_path"], "r", encoding="utf-8").read())

    assert result_payload["final_success"] is False
    assert result_payload["final_status"] == "needs_attention"
    assert result_payload["quality_gate"]["publish_eligible"] is False
    assert state["quality_gate_reason"] == "lineage_inconsistent"
    assert any("RUN_LINEAGE_INCONSISTENT" in w for w in state.get("warnings", []))
    assert lineage_payload["consistency"]["stages_match"] is False
    assert runtime_payload["consistency"]["lineage_manifest_exists"] is True
    assert runtime_payload["artifacts"]["lineage_manifest"].endswith("run_lineage_thread-01.json")
