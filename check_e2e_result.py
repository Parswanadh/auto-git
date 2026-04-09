"""Quick script to read and summarize E2E result JSON."""
import json, sys

with open("output/e2e_todo_app/e2e_result.json") as f:
    r = json.load(f)

print("=== E2E PIPELINE RESULT SUMMARY ===")
dur = r.get("duration_seconds", 0)
print(f"Duration: {dur:.0f}s ({dur/60:.1f} min)")
print(f"Files generated: {r.get('files_generated', '?')}")
print(f"Tests passed: {r.get('tests_passed', '?')}")
print(f"Fix attempts: {r.get('fix_attempts', '?')}")
print(f"Self-eval score: {r.get('self_eval_score', '?')}")
print(f"Goal eval score: {r.get('goal_eval_score', '?')}")
print(f"Final stage: {r.get('final_stage', '?')}")
print(f"Published: {r.get('github_repo', 'not published')}")
print(f"Errors count: {len(r.get('errors', []))}")

code = r.get("generated_code", {})
files = code.get("files", {})
print(f"\nGenerated files ({len(files)}):")
for fn in sorted(files.keys()):
    print(f"  {fn} ({len(files[fn])} chars)")

# Smoke test
smoke = r.get("smoke_test_results", r.get("smoke_test", {}))
if smoke:
    print(f"\nSmoke test: {smoke}")

# Test results
tr = r.get("test_results", {})
if isinstance(tr, dict):
    errs = tr.get("execution_errors", [])
    print(f"\nExecution errors ({len(errs)}):")
    for e in errs[:5]:
        print(f"  - {str(e)[:120]}")

# Self eval 
se_score = r.get("self_eval_score", None)
se_att = r.get("self_eval_attempts", None)
print(f"\nSelf-eval: score={se_score}, attempts={se_att}")

# Goal eval
ge = r.get("goal_achievement", r.get("goal_eval", {}))
if isinstance(ge, dict):
    print(f"\nGoal eval:")
    for k, v in ge.items():
        if k not in ("raw", "per_goal", "details") and not isinstance(v, (list, dict)):
            print(f"  {k}: {v}")

# Current stage
print(f"\nFinal stage: {r.get('current_stage', '?')}")
