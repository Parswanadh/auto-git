"""Run complex verification cases with per-case timeout and concise reporting."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_complex_verification_suite import COMPLEX_IDEAS, _run_one


async def main() -> None:
    os.environ["AUTOGIT_DISABLE_LOCAL_MODELS"] = "true"
    os.environ["PERPLEXICA_ENABLED"] = "false"

    stop_after = os.getenv("AUTOGIT_COMPLEX_STOP_AFTER", "code_testing")
    timeout_s = int(os.getenv("AUTOGIT_COMPLEX_CASE_TIMEOUT_S", "900"))
    strict_correctness = os.getenv("AUTOGIT_COMPLEX_STRICT_CORRECTNESS", "0") == "1"

    results = []
    started = time.time()

    for idx, idea in enumerate(COMPLEX_IDEAS, start=1):
        case_start = time.time()
        try:
            result = await asyncio.wait_for(
                _run_one(idea, idx, stop_after=stop_after),
                timeout=timeout_s,
            )
            result["status"] = "ok"
            result["wall_s"] = round(time.time() - case_start, 2)
            results.append(result)
            print(
                f"CASE {idx}: status=ok stage={result.get('stage')} "
                f"correctness={result.get('correctness_passed')} "
                f"hard={result.get('hard_failures_count')} soft={result.get('soft_warnings_count')} "
                f"errors={result.get('errors_count')} warnings={result.get('warnings_count')} "
                f"wall_s={result['wall_s']}"
            )
        except TimeoutError:
            result = {
                "case_id": idx,
                "idea": idea,
                "status": "timeout",
                "timeout_s": timeout_s,
                "wall_s": round(time.time() - case_start, 2),
            }
            results.append(result)
            print(
                f"CASE {idx}: status=timeout timeout_s={timeout_s} "
                f"wall_s={result['wall_s']}"
            )
        except Exception as exc:  # noqa: BLE001
            result = {
                "case_id": idx,
                "idea": idea,
                "status": "exception",
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "wall_s": round(time.time() - case_start, 2),
            }
            results.append(result)
            print(
                f"CASE {idx}: status=exception type={type(exc).__name__} "
                f"wall_s={result['wall_s']}"
            )

    summary = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "stop_after": stop_after,
        "case_timeout_s": timeout_s,
        "total_wall_s": round(time.time() - started, 2),
        "total_cases": len(results),
        "ok_cases": sum(1 for r in results if r.get("status") == "ok"),
        "timeout_cases": sum(1 for r in results if r.get("status") == "timeout"),
        "exception_cases": sum(1 for r in results if r.get("status") == "exception"),
        "results": results,
    }

    ok_results = [r for r in results if r.get("status") == "ok"]
    contradiction_cases = [
        r for r in ok_results
        if bool(r.get("contradiction_detected", False))
        or (bool(r.get("tests_passed", False)) and not bool(r.get("correctness_passed", False)))
    ]
    correctness_fail_cases = [
        r for r in ok_results
        if not bool(r.get("correctness_passed", False))
    ]
    summary["correctness_pass_cases"] = sum(1 for r in ok_results if bool(r.get("correctness_passed", False)))
    summary["correctness_fail_cases"] = len(correctness_fail_cases)
    summary["contradiction_cases"] = len(contradiction_cases)
    summary["correctness_pass_rate"] = (
        round(summary["correctness_pass_cases"] / len(ok_results), 4) if ok_results else 0.0
    )

    out_dir = Path("logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"complex_verification_bounded_{summary['run_id']}.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"SUMMARY_FILE={out_file}")
    print(
        "SUMMARY "
        f"ok={summary['ok_cases']}/{summary['total_cases']} "
        f"correctness_pass={summary['correctness_pass_cases']}/{summary['ok_cases']} "
        f"contradictions={summary['contradiction_cases']} "
        f"timeouts={summary['timeout_cases']} "
        f"exceptions={summary['exception_cases']} "
        f"total_wall_s={summary['total_wall_s']}"
    )

    if strict_correctness and (summary["contradiction_cases"] > 0 or summary["correctness_fail_cases"] > 0):
        raise SystemExit(
            "Strict correctness assertion failed: bounded run contains correctness failures or contradictions"
        )


if __name__ == "__main__":
    asyncio.run(main())
