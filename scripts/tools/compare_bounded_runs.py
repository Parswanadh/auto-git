"""Compare two bounded verification summaries and print correctness deltas.

Usage examples:
  python scripts/tools/compare_bounded_runs.py
  python scripts/tools/compare_bounded_runs.py --base logs/complex_verification_bounded_20260317_232416.json --target logs/complex_verification_bounded_20260318_233702.json
  python scripts/tools/compare_bounded_runs.py --write-md logs/bounded_dashboard_latest.md
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple


@dataclass
class RunMetrics:
    run_id: str
    file_name: str
    total_cases: int
    ok_cases: int
    timeout_cases: int
    exception_cases: int
    stage_complete_cases: int
    stage_complete_rate: float
    correctness_pass_cases: int
    correctness_fail_cases: int
    correctness_pass_rate: float
    contradiction_cases: int
    mean_hard_failures: float
    mean_soft_warnings: float
    hard_failures_coverage: float
    soft_warnings_coverage: float


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _derive_case_correctness(case: Dict[str, Any]) -> bool:
    if "correctness_passed" in case:
        return bool(case.get("correctness_passed", False))
    tests_passed = bool(case.get("tests_passed", False))
    hard_failures = _safe_int(case.get("hard_failures_count", 0), 0)
    return tests_passed and hard_failures == 0


def _load_metrics(path: Path) -> RunMetrics:
    payload = json.loads(path.read_text(encoding="utf-8"))
    results = payload.get("results", []) if isinstance(payload.get("results"), list) else []

    total_cases = _safe_int(payload.get("total_cases", len(results)), len(results))
    ok_cases = _safe_int(payload.get("ok_cases", sum(1 for r in results if r.get("status") == "ok")))
    timeout_cases = _safe_int(payload.get("timeout_cases", sum(1 for r in results if r.get("status") == "timeout")))
    exception_cases = _safe_int(payload.get("exception_cases", sum(1 for r in results if r.get("status") == "exception")))

    ok_results = [r for r in results if r.get("status") == "ok"]
    stage_complete_cases = sum(1 for r in ok_results if str(r.get("stage", "")).endswith("complete"))

    correctness_pass_cases = _safe_int(
        payload.get("correctness_pass_cases", sum(1 for r in ok_results if _derive_case_correctness(r))),
        sum(1 for r in ok_results if _derive_case_correctness(r)),
    )
    correctness_fail_cases = _safe_int(
        payload.get("correctness_fail_cases", max(0, len(ok_results) - correctness_pass_cases)),
        max(0, len(ok_results) - correctness_pass_cases),
    )

    contradiction_cases = _safe_int(
        payload.get(
            "contradiction_cases",
            sum(
                1
                for r in ok_results
                if bool(r.get("tests_passed", False)) and not _derive_case_correctness(r)
            ),
        ),
        sum(
            1
            for r in ok_results
            if bool(r.get("tests_passed", False)) and not _derive_case_correctness(r)
        ),
    )

    hard_present = [r for r in ok_results if "hard_failures_count" in r]
    soft_present = [r for r in ok_results if "soft_warnings_count" in r]
    hard_values = [_safe_float(r.get("hard_failures_count", 0), 0.0) for r in hard_present]
    soft_values = [_safe_float(r.get("soft_warnings_count", 0), 0.0) for r in soft_present]

    stage_complete_rate = (stage_complete_cases / len(ok_results)) if ok_results else 0.0
    correctness_pass_rate = (correctness_pass_cases / len(ok_results)) if ok_results else 0.0

    return RunMetrics(
        run_id=str(payload.get("run_id", "unknown")),
        file_name=path.name,
        total_cases=total_cases,
        ok_cases=ok_cases,
        timeout_cases=timeout_cases,
        exception_cases=exception_cases,
        stage_complete_cases=stage_complete_cases,
        stage_complete_rate=stage_complete_rate,
        correctness_pass_cases=correctness_pass_cases,
        correctness_fail_cases=correctness_fail_cases,
        correctness_pass_rate=correctness_pass_rate,
        contradiction_cases=contradiction_cases,
        mean_hard_failures=mean(hard_values) if hard_values else 0.0,
        mean_soft_warnings=mean(soft_values) if soft_values else 0.0,
        hard_failures_coverage=(len(hard_present) / len(ok_results)) if ok_results else 0.0,
        soft_warnings_coverage=(len(soft_present) / len(ok_results)) if ok_results else 0.0,
    )


def _fmt_delta(current: float, previous: float, pct: bool = False) -> str:
    diff = current - previous
    sign = "+" if diff >= 0 else ""
    if pct:
        return f"{sign}{diff * 100:.2f} pp"
    return f"{sign}{diff:.2f}"


def _latest_two_files(log_dir: Path) -> Tuple[Path, Path]:
    files = sorted(log_dir.glob("complex_verification_bounded_*.json"))
    if len(files) < 2:
        raise FileNotFoundError(
            "Need at least 2 bounded summary files in logs/ (complex_verification_bounded_*.json)."
        )
    return files[-2], files[-1]


def _build_report(base: RunMetrics, target: RunMetrics) -> str:
    lines: List[str] = []
    lines.append("Auto-GIT Bounded Dashboard (Before/After)")
    lines.append("=" * 47)
    lines.append(f"Before: {base.file_name} (run_id={base.run_id})")
    lines.append(f"After : {target.file_name} (run_id={target.run_id})")
    lines.append("")

    lines.append("Primary Quality KPIs")
    lines.append("-" * 22)
    lines.append(
        f"stage_complete_rate   : {base.stage_complete_rate * 100:6.2f}% -> {target.stage_complete_rate * 100:6.2f}% ({_fmt_delta(target.stage_complete_rate, base.stage_complete_rate, pct=True)})"
    )
    lines.append(
        f"correctness_pass_rate : {base.correctness_pass_rate * 100:6.2f}% -> {target.correctness_pass_rate * 100:6.2f}% ({_fmt_delta(target.correctness_pass_rate, base.correctness_pass_rate, pct=True)})"
    )
    lines.append(
        f"contradiction_cases   : {base.contradiction_cases:6d} -> {target.contradiction_cases:6d} ({_fmt_delta(float(target.contradiction_cases), float(base.contradiction_cases))})"
    )
    lines.append(
        f"mean_hard_failures    : {base.mean_hard_failures:6.2f} -> {target.mean_hard_failures:6.2f} ({_fmt_delta(target.mean_hard_failures, base.mean_hard_failures)})"
    )
    lines.append(
        f"mean_soft_warnings    : {base.mean_soft_warnings:6.2f} -> {target.mean_soft_warnings:6.2f} ({_fmt_delta(target.mean_soft_warnings, base.mean_soft_warnings)})"
    )
    lines.append(
        f"hard_metric_coverage  : {base.hard_failures_coverage * 100:6.1f}% -> {target.hard_failures_coverage * 100:6.1f}%"
    )
    lines.append(
        f"soft_metric_coverage  : {base.soft_warnings_coverage * 100:6.1f}% -> {target.soft_warnings_coverage * 100:6.1f}%"
    )
    lines.append("")

    lines.append("Run Health")
    lines.append("-" * 10)
    lines.append(
        f"ok/total              : {base.ok_cases}/{base.total_cases} -> {target.ok_cases}/{target.total_cases}"
    )
    lines.append(
        f"timeouts              : {base.timeout_cases} -> {target.timeout_cases}"
    )
    lines.append(
        f"exceptions            : {base.exception_cases} -> {target.exception_cases}"
    )

    if (
        base.hard_failures_coverage < 1.0
        or target.hard_failures_coverage < 1.0
        or base.soft_warnings_coverage < 1.0
        or target.soft_warnings_coverage < 1.0
    ):
        lines.append("")
        lines.append("Notes")
        lines.append("-" * 5)
        lines.append(
            "Some runs do not include hard/soft per-case counters; means above use available cases only."
        )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare bounded verification summaries.")
    parser.add_argument("--log-dir", default="logs", help="Directory containing bounded summary json files.")
    parser.add_argument("--base", default="", help="Baseline summary file path.")
    parser.add_argument("--target", default="", help="Target summary file path.")
    parser.add_argument(
        "--write-md",
        default="",
        help="Optional output markdown path for the report (for docs/artifacts).",
    )
    args = parser.parse_args()

    if args.base and args.target:
        base_path = Path(args.base)
        target_path = Path(args.target)
    else:
        base_path, target_path = _latest_two_files(Path(args.log_dir))

    if not base_path.exists():
        raise FileNotFoundError(f"Base file not found: {base_path}")
    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {target_path}")

    base = _load_metrics(base_path)
    target = _load_metrics(target_path)

    report = _build_report(base, target)
    print(report)

    if args.write_md:
        out = Path(args.write_md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report + "\n", encoding="utf-8")
        print(f"\nWROTE_REPORT={out}")


if __name__ == "__main__":
    main()
