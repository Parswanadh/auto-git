#!/usr/bin/env python3
"""
E2E Test: Moderate case — Todo App with REST API
Runs the full 19-node pipeline non-interactively and reports results.
"""
import asyncio
import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force FREE-only models: disable paid OpenRouter models to test with free tier
# Free models are rate-limited at 20 RPM / 200 RPD each.
# Round-robin rotation in ModelManager spreads calls across models.
os.environ["OPENROUTER_PAID"] = "false"

# Keep moderate E2E runs moving: cap research stage/runtime budgets so
# failures surface quickly and the fix loop can iterate faster.
os.environ.setdefault("AUTOGIT_RESEARCH_HARD_TIMEOUT_S", "300")
os.environ.setdefault("AUTOGIT_RESEARCH_SOFT_BUDGET_S", "90")
os.environ.setdefault("AUTOGIT_SOTA_TIMEOUT_S", "120")
os.environ.setdefault("AUTOGIT_MAX_FIX_ATTEMPTS_CAP", "8")

IDEA = (
    "Build a Python command-line Todo application with a REST API backend. "
    "Use Flask for the API server with SQLite storage. "
    "Features: add/remove/list/complete todos, priority levels (high/medium/low), "
    "due dates, and a simple CLI client that talks to the API. "
    "Include proper error handling and input validation."
)

async def main():
    from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline

    print(f"\n{'='*70}")
    print(f"  E2E TEST: Moderate Case — Todo App with REST API")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    start = time.time()

    result = await run_auto_git_pipeline(
        idea=IDEA,
        max_debate_rounds=2,
        use_web_search=True,
        auto_publish=False,       # Don't push to GitHub
        output_dir="output/e2e_todo_app",
        thread_id=f"e2e_moderate_{int(time.time())}",
        interactive=False,
        resume=False,             # Fresh run
    )

    elapsed = time.time() - start
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    # ── Collect results ─────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  E2E TEST RESULTS")
    print(f"{'='*70}")
    print(f"  Duration       : {minutes}m {seconds}s")
    print(f"  Final stage    : {result.get('current_stage', 'unknown')}")

    # Code generation
    gen_code = result.get("generated_code", {})
    if isinstance(gen_code, dict):
        files = gen_code.get("files", gen_code)
        print(f"  Files generated : {len(files)}")
        for fname in sorted(files.keys()) if isinstance(files, dict) else []:
            loc = len(str(files[fname]).splitlines())
            print(f"    - {fname} ({loc} lines)")
    else:
        print(f"  Files generated : N/A")

    # Tests
    tests_passed = result.get("tests_passed", None)
    print(f"  Tests passed   : {tests_passed}")

    # Fix loop
    fix_attempts = result.get("fix_attempts", 0)
    max_fix = result.get("max_fix_attempts", 8)
    print(f"  Fix attempts   : {fix_attempts}/{max_fix}")

    # Feature verification
    test_results = result.get("test_results", {}) or {}
    fv = test_results.get("feature_verification", {})
    fv_summary = fv.get("summary", {})
    if fv_summary:
        print(f"  Feature verify : {fv_summary.get('passed',0)}/{fv_summary.get('total',0)} ({fv_summary.get('pass_rate',0):.0f}%)")

    # Self-eval
    se_score = result.get("self_eval_score", -1)
    print(f"  Self-eval score: {se_score if se_score >= 0 else 'N/A'}")

    # Goal achievement
    ga_score = result.get("goal_achievement_score", -1)
    print(f"  Goal eval score: {ga_score if ga_score >= 0 else 'N/A'}")

    # GitHub
    gh_url = result.get("github_url") or result.get("github_repo")
    print(f"  GitHub URL     : {gh_url or 'not published'}")

    # Errors
    errors = result.get("errors", [])
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors[:10]:
            print(f"    ⚠ {str(e)[:120]}")

    print(f"\n{'='*70}")

    # Save full result to JSON
    out_path = "output/e2e_todo_app/e2e_result.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        serializable = {}
        for k, v in result.items():
            try:
                json.dumps(v)
                serializable[k] = v
            except (TypeError, ValueError):
                serializable[k] = str(v)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, default=str)
        print(f"  Full result saved to: {out_path}")
    except Exception as ex:
        print(f"  Could not save result JSON: {ex}")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
