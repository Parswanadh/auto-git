#!/usr/bin/env python3
"""Validate run-lineage artifacts produced by workflow_enhanced.py."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple


def _safe_filename_token(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "default")).strip("._")
    return token or "default"


def _extract_trace_terminal_stage(trace_path: str) -> str:
    last_stage = ""
    try:
        with open(trace_path, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except Exception:
                    continue
                event = str(rec.get("event", ""))
                if event == "pipeline_end":
                    stage = str(rec.get("final_stage", "") or "").strip()
                    if stage:
                        return stage
                elif event == "node_complete":
                    stage = str(rec.get("current_stage", "") or "").strip()
                    if stage:
                        last_stage = stage
    except Exception:
        return ""
    return last_stage


def _extract_status_terminal_stage(status_path: str) -> str:
    try:
        text = open(status_path, "r", encoding="utf-8").read()
    except Exception:
        return ""

    for pattern in (
        r"\*\*Final Stage\*\*:\s*`([^`]+)`",
        r"Final Stage:\s*`([^`]+)`",
        r"Final Stage:\s*([^\n\r]+)",
    ):
        m = re.search(pattern, text)
        if m:
            return str(m.group(1) or "").strip()
    return ""


def _extract_result_terminal_stage(result_path: str) -> str:
    try:
        payload = json.loads(open(result_path, "r", encoding="utf-8").read())
    except Exception:
        return ""

    if not isinstance(payload, dict):
        return ""

    for key in ("current_stage", "final_stage", "terminal_stage"):
        value = str(payload.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _resolve_manifest_path(logs_dir: str, thread_id: str, manifest: str | None) -> str:
    if manifest:
        return os.path.abspath(manifest)
    safe_thread = _safe_filename_token(thread_id)
    return os.path.abspath(os.path.join(logs_dir, f"run_lineage_{safe_thread}.json"))


def _resolve_latest_manifest_path(logs_dir: str) -> str:
    try:
        candidates = [
            os.path.join(logs_dir, name)
            for name in os.listdir(logs_dir)
            if name.startswith("run_lineage_") and name.endswith(".json")
        ]
    except Exception:
        return ""

    if not candidates:
        return ""
    latest = max(candidates, key=lambda path: os.path.getmtime(path))
    return os.path.abspath(latest)


def _validate_manifest(manifest: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
    errors: List[str] = []

    required = [
        "run_id",
        "thread_id",
        "trace_file",
        "status_file",
        "result_file",
        "started_at",
        "ended_at",
        "terminal_stage",
    ]
    for key in required:
        if key not in manifest:
            errors.append(f"missing required key: {key}")

    trace_file = os.path.abspath(str(manifest.get("trace_file", "") or ""))
    status_file = os.path.abspath(str(manifest.get("status_file", "") or ""))
    result_file = os.path.abspath(str(manifest.get("result_file", "") or ""))

    if not trace_file or not os.path.exists(trace_file):
        errors.append(f"trace_file missing or not found: {trace_file or '<empty>'}")
    if not status_file or not os.path.exists(status_file):
        errors.append(f"status_file missing or not found: {status_file or '<empty>'}")
    if not result_file or not os.path.exists(result_file):
        errors.append(f"result_file missing or not found: {result_file or '<empty>'}")

    trace_stage = _extract_trace_terminal_stage(trace_file) if os.path.exists(trace_file) else ""
    status_stage = _extract_status_terminal_stage(status_file) if os.path.exists(status_file) else ""
    result_stage = _extract_result_terminal_stage(result_file) if os.path.exists(result_file) else ""
    terminal_stage = str(manifest.get("terminal_stage", "") or "").strip()

    stage_values = {
        "manifest_terminal_stage": terminal_stage,
        "trace_terminal_stage": trace_stage,
        "status_terminal_stage": status_stage,
        "result_terminal_stage": result_stage,
    }
    missing_stage_fields = [name for name, value in stage_values.items() if not value]
    all_stage_fields_present = len(missing_stage_fields) == 0
    stages_match = all_stage_fields_present and len(set(stage_values.values())) == 1

    consistency = manifest.get("consistency") if isinstance(manifest.get("consistency"), dict) else {}
    declared_files_exist = consistency.get("files_exist")
    declared_all_stage_fields_present = consistency.get("all_stage_fields_present")
    declared_stages_match = consistency.get("stages_match")
    computed_files_exist = all(os.path.exists(path) for path in [trace_file, status_file, result_file])

    if declared_files_exist is not None and bool(declared_files_exist) != bool(computed_files_exist):
        errors.append(
            f"consistency.files_exist mismatch: manifest={declared_files_exist}, computed={computed_files_exist}"
        )

    if (
        declared_all_stage_fields_present is not None
        and bool(declared_all_stage_fields_present) != bool(all_stage_fields_present)
    ):
        errors.append(
            "consistency.all_stage_fields_present mismatch: "
            f"manifest={declared_all_stage_fields_present}, computed={all_stage_fields_present}"
        )

    if declared_stages_match is not None and bool(declared_stages_match) != bool(stages_match):
        errors.append(
            f"consistency.stages_match mismatch: manifest={declared_stages_match}, computed={stages_match}"
        )

    if not all_stage_fields_present:
        errors.append(
            "missing terminal stage fields across artifacts: "
            f"{', '.join(missing_stage_fields)}"
        )

    if not stages_match:
        errors.append(
            "terminal stage mismatch across artifacts: "
            f"manifest={terminal_stage or '<empty>'}, "
            f"trace={trace_stage or '<empty>'}, "
            f"status={status_stage or '<empty>'}, "
            f"result={result_stage or '<empty>'}"
        )

    report = {
        "run_id": str(manifest.get("run_id", "") or ""),
        "thread_id": str(manifest.get("thread_id", "") or ""),
        "trace_file": trace_file,
        "status_file": status_file,
        "result_file": result_file,
        "terminal_stage": terminal_stage,
        "trace_terminal_stage": trace_stage,
        "status_terminal_stage": status_stage,
        "result_terminal_stage": result_stage,
        "files_exist": computed_files_exist,
        "all_stage_fields_present": all_stage_fields_present,
        "missing_stage_fields": missing_stage_fields,
        "stages_match": stages_match,
    }
    return errors, report


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate run-lineage manifest and linked artifacts.")
    parser.add_argument("--logs-dir", default="logs", help="Logs directory (default: logs)")
    parser.add_argument("--thread-id", default="default", help="Thread ID used for run manifest lookup")
    parser.add_argument("--manifest", default=None, help="Explicit manifest path to validate")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the most recently modified run_lineage_*.json in --logs-dir",
    )
    parser.add_argument("--json-out", default=None, help="Optional path to write validation report JSON")
    args = parser.parse_args(argv)

    if args.latest and args.manifest:
        print("FAIL: --latest and --manifest cannot be used together")
        return 2

    if args.latest:
        manifest_path = _resolve_latest_manifest_path(args.logs_dir)
        if not manifest_path:
            print(f"FAIL: no run_lineage_*.json found in logs directory: {os.path.abspath(args.logs_dir)}")
            return 2
    else:
        manifest_path = _resolve_manifest_path(args.logs_dir, args.thread_id, args.manifest)

    if not os.path.exists(manifest_path):
        print(f"FAIL: manifest not found: {manifest_path}")
        return 2

    try:
        manifest = json.loads(open(manifest_path, "r", encoding="utf-8").read())
    except Exception as exc:
        print(f"FAIL: could not parse manifest JSON: {manifest_path}")
        print(f"  error: {exc}")
        return 2

    if not isinstance(manifest, dict):
        print(f"FAIL: manifest is not a JSON object: {manifest_path}")
        return 2

    errors, report = _validate_manifest(manifest)
    payload = {
        "manifest_path": manifest_path,
        "ok": len(errors) == 0,
        "errors": errors,
        "report": report,
    }

    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    if errors:
        print(f"FAIL: run-lineage validation failed for {manifest_path}")
        for issue in errors:
            print(f"  - {issue}")
        return 2

    print(f"PASS: run-lineage validation succeeded for {manifest_path}")
    print(f"  run_id={report['run_id']} thread_id={report['thread_id']}")
    print(
        "  stages="
        f"manifest:{report['terminal_stage']} "
        f"trace:{report['trace_terminal_stage']} "
        f"status:{report['status_terminal_stage']} "
        f"result:{report['result_terminal_stage']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
