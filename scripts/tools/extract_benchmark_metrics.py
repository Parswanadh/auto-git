#!/usr/bin/env python3
"""Extract latest Auto-GIT run metrics and compare with baseline output.

Outputs:
- output/benchmark_comparison.json
- output/benchmark_report.md
"""

from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "logs"
OUTPUT = ROOT / "output"


def _latest(glob_pattern: str) -> Optional[Path]:
    matches = [Path(p) for p in glob.glob(glob_pattern)]
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        # Normalize trailing Z to an explicit UTC offset for fromisoformat.
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _resolve_run_duration_seconds(thread_id: Optional[str], run_id: Optional[str]) -> Optional[float]:
    if not thread_id:
        return None

    lineage_path = LOGS / f"run_lineage_{thread_id}.json"
    if not lineage_path.exists():
        return None

    lineage = _load_json(lineage_path)
    # Prefer explicit run_id match when available.
    if run_id and lineage.get("run_id") and lineage.get("run_id") != run_id:
        return None

    started = _parse_iso(lineage.get("started_at"))
    ended = _parse_iso(lineage.get("ended_at"))
    if not started or not ended:
        return None

    seconds = (ended - started).total_seconds()
    return round(max(seconds, 0.0), 3)


def _count_output_files(run_json: Dict[str, Any]) -> Optional[int]:
    output_path = run_json.get("output_path")
    if not output_path:
        return None

    output_dir = ROOT / str(output_path)
    if not output_dir.exists() or not output_dir.is_dir():
        return None

    return sum(1 for p in output_dir.iterdir() if p.is_file())


def _resolve_runtime_file_count(thread_id: Optional[str], run_id: Optional[str]) -> Optional[int]:
    if not thread_id or not run_id:
        return None

    manifest_path = LOGS / f"runtime_manifest_{thread_id}_{run_id}.json"
    if not manifest_path.exists():
        return None

    manifest = _load_json(manifest_path)
    count = manifest.get("runtime_file_count")
    if isinstance(count, int):
        return count
    return None


def _extract_autogit(run_json: Dict[str, Any], path: Path) -> Dict[str, Any]:
    qg = run_json.get("quality_gate", {})
    fv = run_json.get("test_results", {}).get("feature_verification", {}).get("summary", {})

    thread_id = run_json.get("thread_id")
    run_id = run_json.get("run_id")

    output_file_count = _count_output_files(run_json)
    runtime_file_count = _resolve_runtime_file_count(thread_id, run_id)
    duration_seconds = run_json.get("duration_seconds")
    if duration_seconds is None:
        duration_seconds = _resolve_run_duration_seconds(thread_id, run_id)

    return {
        "artifact": str(path.relative_to(ROOT)).replace("\\", "/"),
        "run_id": run_id,
        "thread_id": thread_id,
        "updated_at": run_json.get("updated_at") or run_json.get("timestamp"),
        "duration_seconds": duration_seconds,
        "current_stage": run_json.get("current_stage"),
        "final_status": run_json.get("final_status"),
        "files_generated": output_file_count,
        "runtime_files_generated": runtime_file_count,
        "tests_passed": qg.get("tests_passed", run_json.get("tests_passed")),
        "correctness_passed": qg.get("correctness_passed"),
        "hard_failures": qg.get("hard_failures_count"),
        "soft_warnings": qg.get("soft_warnings_count"),
        "publish_eligible": qg.get("publish_eligible"),
        "final_success": qg.get("final_success"),
        "quality_gate_reason": run_json.get("quality_gate_reason") or qg.get("reason"),
        "feature_passed": fv.get("passed"),
        "feature_total": fv.get("total"),
        "feature_pass_rate": fv.get("pass_rate"),
    }


def _extract_baseline(path: Path) -> Dict[str, Any]:
    data = _load_json(path)
    return {
        "artifact": str(path.relative_to(ROOT)).replace("\\", "/"),
        "mode": data.get("mode"),
        "duration_seconds": data.get("duration_seconds"),
        "generation_ok": data.get("generation_ok"),
        "syntax_ok": data.get("syntax_ok"),
        "runtime_ok": data.get("runtime_ok"),
        "fallback_used": data.get("fallback_used"),
        "fallback_reason": data.get("fallback_reason"),
        "generated_lines": data.get("generated_lines"),
        "error": data.get("error"),
    }


def _mk_markdown(comparison: Dict[str, Any]) -> str:
    ag = comparison.get("autogit", {})
    bl = comparison.get("karpathy_style_baseline", {})

    lines = [
        "# Benchmark Comparison Report",
        "",
        f"Generated: {comparison.get('generated_at')}",
        "",
        "## Auto-GIT",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Artifact | {ag.get('artifact', 'N/A')} |",
        f"| Run ID | {ag.get('run_id', 'N/A')} |",
        f"| Duration (s) | {ag.get('duration_seconds', 'N/A')} |",
        f"| Files Generated | {ag.get('files_generated', 'N/A')} |",
        f"| Runtime Files | {ag.get('runtime_files_generated', 'N/A')} |",
        f"| Current Stage | {ag.get('current_stage', 'N/A')} |",
        f"| Final Status | {ag.get('final_status', 'N/A')} |",
        f"| Quality Gate Reason | {ag.get('quality_gate_reason', 'N/A')} |",
        f"| Tests Passed | {ag.get('tests_passed', 'N/A')} |",
        f"| Correctness Passed | {ag.get('correctness_passed', 'N/A')} |",
        f"| Hard Failures | {ag.get('hard_failures', 'N/A')} |",
        f"| Feature Pass | {ag.get('feature_passed', 'N/A')}/{ag.get('feature_total', 'N/A')} |",
        "",
        "## Karpathy-Style Baseline",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Artifact | {bl.get('artifact', 'N/A')} |",
        f"| Duration (s) | {bl.get('duration_seconds', 'N/A')} |",
        f"| Generation OK | {bl.get('generation_ok', 'N/A')} |",
        f"| Syntax OK | {bl.get('syntax_ok', 'N/A')} |",
        f"| Runtime OK | {bl.get('runtime_ok', 'N/A')} |",
        f"| Fallback Used | {bl.get('fallback_used', 'N/A')} |",
        f"| Generated Lines | {bl.get('generated_lines', 'N/A')} |",
        "",
        "## Notes",
        "",
        "- Workflow-vs-workflow framing (not person-vs-person).",
        "- Same test case expected for both lanes.",
        "- Publish only source-backed numbers.",
    ]
    return "\n".join(lines)


def main() -> int:
    latest_run = _latest(str(LOGS / "run_result_e2e_moderate_*.json"))
    if latest_run is None:
        raise SystemExit("No Auto-GIT run_result_e2e_moderate_*.json found")

    baseline_path = ROOT / "output" / "benchmark_baseline" / "baseline_result.json"

    run_json = _load_json(latest_run)
    autogit = _extract_autogit(run_json, latest_run)

    baseline = _extract_baseline(baseline_path) if baseline_path.exists() else {
        "artifact": None,
        "mode": "karpathy_style_single_shot",
        "error": "baseline_result.json not found",
    }

    comparison = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "autogit": autogit,
        "karpathy_style_baseline": baseline,
    }

    output_json = OUTPUT / "benchmark_comparison.json"
    output_md = OUTPUT / "benchmark_report.md"

    output_json.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    output_md.write_text(_mk_markdown(comparison), encoding="utf-8")

    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
