"""
S22 Pipeline Test: Smoke-test fix loop validation

Complex idea that exercises:
- Multi-file project structure (models, services, API routes, tests)
- Database operations (SQLite) — previous failure class
- Config management — previous failure class (truncated config.py)
- CLI + REST API interface
- Background task processing

The smoke test node should now catch runtime crashes (import errors,
missing attributes, DB schema mismatches) and feed them back to the
fix loop BEFORE self-eval/publishing.
"""
import asyncio
import sys
import os

# Ensure project root on path
sys.path.insert(0, os.path.dirname(__file__))

from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline


IDEA = """
Build a Task Queue Manager with REST API and CLI:

1. SQLite-backed persistent task queue with priority levels (critical/high/medium/low)
2. REST API (Flask or FastAPI):
   - POST /tasks — submit a task with name, priority, payload JSON
   - GET /tasks — list tasks with filtering by status and priority
   - GET /tasks/<id> — get task details with execution history
   - POST /tasks/<id>/retry — retry a failed task
   - DELETE /tasks/<id> — cancel a pending task
3. Worker system:
   - Concurrent worker pool (configurable size)
   - Workers pick highest-priority tasks first
   - Automatic retry with exponential backoff (max 3 retries)
   - Dead-letter queue for permanently failed tasks
4. CLI interface:
   - `taskq submit "task name" --priority high --payload '{"key":"val"}'`
   - `taskq list --status pending --limit 20`
   - `taskq worker start --concurrency 4`
   - `taskq stats` — show queue depth, success/fail rates, avg latency
5. Health monitoring:
   - /health endpoint returning queue depth and worker status
   - Prometheus-compatible metrics endpoint
   - Configurable alerting thresholds
6. Config via YAML file with sensible defaults
7. Comprehensive pytest test suite covering queue CRUD, worker lifecycle, retry logic
"""


async def main():
    print("=" * 70)
    print("  S22 PIPELINE TEST: Task Queue Manager")
    print("  Testing: smoke_test_node → fix loop integration")
    print("=" * 70)
    
    result = await run_auto_git_pipeline(
        idea=IDEA,
        auto_publish=False,
        output_dir="output",
        max_debate_rounds=2,
        min_consensus_score=0.7,
        interactive=True,
        thread_id="s22-smoke-test-validation",
    )
    
    # Report
    print("\n" + "=" * 70)
    print("  PIPELINE RESULT SUMMARY")
    print("=" * 70)
    stage = result.get("current_stage", "unknown")
    tests = result.get("tests_passed", False)
    smoke = result.get("smoke_test", {})
    self_eval = result.get("self_eval_score")
    goal = result.get("goal_achievement")
    fix_attempts = result.get("fix_attempts", 0)
    output_path = result.get("output_path", "N/A")
    
    print(f"  Stage:          {stage}")
    print(f"  Tests passed:   {tests}")
    print(f"  Smoke test:     {'PASS' if smoke.get('passed') else 'FAIL'}")
    print(f"  Self-eval:      {self_eval}")
    print(f"  Goal achieve:   {goal}")
    print(f"  Fix attempts:   {fix_attempts}")
    print(f"  Output:         {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
