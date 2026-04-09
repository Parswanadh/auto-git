"""Run a complex-problem verification suite for pipeline robustness."""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline, _apply_quality_contract


COMPLEX_IDEAS = [
    "Build a distributed event-driven fraud detection platform with streaming ingestion, online feature store, model serving, drift detection, and automated rollback policies.",
    "Design and implement a multi-tenant workflow orchestration system with RBAC, audit logs, retry semantics, cron scheduling, and plugin-based task runners.",
    "Create a retrieval-augmented code intelligence service that indexes repositories, supports semantic search, dependency graph queries, and generates patch proposals with tests.",
]


async def _run_one(idea: str, idx: int, stop_after: str) -> dict:
    start = time.time()
    state = await run_auto_git_pipeline(
        idea=idea,
        use_web_search=False,
        max_debate_rounds=2,
        auto_publish=False,
        stop_after=stop_after,
        interactive=False,
        resume=False,
        checkpointer_provider="memory",
    )
    elapsed = time.time() - start

    normalized = _apply_quality_contract(dict(state), terminal=False)
    errors = normalized.get("errors", []) if isinstance(normalized.get("errors"), list) else []
    warnings = normalized.get("warnings", []) if isinstance(normalized.get("warnings"), list) else []
    hard_failures = normalized.get("hard_failures", []) if isinstance(normalized.get("hard_failures"), list) else []
    soft_warnings = normalized.get("soft_warnings", []) if isinstance(normalized.get("soft_warnings"), list) else []
    quality_gate = normalized.get("quality_gate", {}) if isinstance(normalized.get("quality_gate"), dict) else {}
    correctness_passed = bool(normalized.get("correctness_passed", False))
    generated = state.get("generated_code", {}) if isinstance(state.get("generated_code"), dict) else {}
    files = generated.get("files", {}) if isinstance(generated.get("files"), dict) else {}

    return {
        "case_id": idx,
        "idea": idea,
        "elapsed_s": round(elapsed, 2),
        "stage": state.get("current_stage", "unknown"),
        "tests_passed": bool(state.get("tests_passed", False)),
        "correctness_passed": correctness_passed,
        "contradiction_detected": bool(quality_gate.get("contradiction_detected", False)),
        "self_eval_score": state.get("self_eval_score"),
        "goal_eval_report": state.get("goal_eval_report"),
        "generated_file_count": len(files),
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "hard_failures_count": len(hard_failures),
        "soft_warnings_count": len(soft_warnings),
        "error_head": [str(e)[:200] for e in errors[:3]],
        "warning_head": [str(w)[:200] for w in warnings[:3]],
        "hard_failure_head": [str(e)[:200] for e in hard_failures[:3]],
        "soft_warning_head": [str(w)[:200] for w in soft_warnings[:3]],
    }


async def main() -> None:
    os.environ["AUTOGIT_DISABLE_LOCAL_MODELS"] = "true"
    os.environ["PERPLEXICA_ENABLED"] = "false"

    out_dir = Path("logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"complex_verification_{run_id}.json"

    stop_after = os.getenv("AUTOGIT_COMPLEX_STOP_AFTER", "code_testing")

    results = []
    for idx, idea in enumerate(COMPLEX_IDEAS, start=1):
        try:
            result = await _run_one(idea, idx, stop_after=stop_after)
            result["status"] = "ok"
            results.append(result)
            print(
                f"CASE {idx}: stage={result['stage']} errors={result['errors_count']} "
                f"warnings={result['warnings_count']} files={result['generated_file_count']} "
                f"elapsed={result['elapsed_s']}s"
            )
        except Exception as exc:
            results.append(
                {
                    "case_id": idx,
                    "idea": idea,
                    "status": "exception",
                    "exception_type": type(exc).__name__,
                    "exception": str(exc),
                }
            )
            print(f"CASE {idx}: EXCEPTION {type(exc).__name__}: {exc}")

    summary = {
        "run_id": run_id,
        "stop_after": stop_after,
        "total_cases": len(results),
        "ok_cases": sum(1 for r in results if r.get("status") == "ok"),
        "exception_cases": sum(1 for r in results if r.get("status") == "exception"),
        "results": results,
    }
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"SUMMARY_FILE={out_file}")
    print(
        "SUMMARY_OK="
        f"{summary['ok_cases']}/{summary['total_cases']} "
        f"exceptions={summary['exception_cases']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
