#!/usr/bin/env python3
"""
Session 20 — Pipeline test run with moderately complex idea.
Tests the S20 optimizations: guarded file planner, contract derivation,
error-scoped strategy reasoner, few-shot examples, CoT, raised threshold, etc.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel

console = Console()

IDEA = (
    "Build a real-time anomaly detection system for time-series sensor data. "
    "Use a sliding-window isolation forest for streaming anomaly scoring, "
    "with an SQLite database for historical storage, a configurable alerting "
    "threshold system, and a CLI dashboard that displays live stats "
    "(anomalies detected, current score, data rate). "
    "Include data ingestion from CSV files and a synthetic data generator for testing."
)

async def main():
    console.print(Panel(
        f"[bold cyan]Session 20 Pipeline Test[/bold cyan]\n\n"
        f"[yellow]Idea:[/yellow] {IDEA[:120]}...\n\n"
        f"Testing: guarded file planner, contract derivation from spec,\n"
        f"error-scoped strategy, few-shot, CoT, raised threshold (7), prompt budget",
        title="S20 Test Run",
        border_style="cyan",
    ))

    from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline

    t0 = time.time()
    result = await run_auto_git_pipeline(
        idea=IDEA,
        use_web_search=True,
        max_debate_rounds=2,
        auto_publish=False,
        output_dir="output/s20_test",
        thread_id="s20_test_run",
        resume=False,  # Force fresh run
    )
    elapsed = time.time() - t0

    # ── Print summary ───────────────────────────────────────────
    stage = result.get("current_stage", "unknown")
    score = result.get("self_eval_score", -1)
    fix_attempts = result.get("fix_attempts", 0)
    goal_report = result.get("goal_eval_report") or {}
    pct = goal_report.get("overall_pct_implemented", "?")
    files = result.get("generated_code", {})
    if isinstance(files, dict):
        files = files.get("files", files)
    n_files = len(files) if isinstance(files, dict) else 0
    errors = result.get("errors", [])
    github_url = result.get("github_url", "")

    console.print("\n" + "=" * 70)
    console.print(Panel(
        f"[bold]Stage:[/bold]         {stage}\n"
        f"[bold]Self-eval:[/bold]     {score}/10\n"
        f"[bold]Goal %:[/bold]        {pct}%\n"
        f"[bold]Fix attempts:[/bold]  {fix_attempts}\n"
        f"[bold]Files:[/bold]         {n_files}\n"
        f"[bold]Errors:[/bold]        {len(errors)}\n"
        f"[bold]Time:[/bold]          {elapsed:.0f}s ({elapsed/60:.1f}min)\n"
        f"[bold]GitHub:[/bold]        {github_url or 'not published'}",
        title="Pipeline Result",
        border_style="green" if score >= 7 else "yellow" if score >= 5 else "red",
    ))

    # Show files generated
    if isinstance(files, dict):
        console.print("\n[bold]Generated files:[/bold]")
        for fname, fcode in sorted(files.items()):
            lines = len(fcode.splitlines()) if isinstance(fcode, str) else 0
            console.print(f"  {fname}: {lines} lines")

    if errors:
        console.print(f"\n[red]Pipeline errors ({len(errors)}):[/red]")
        for e in errors[:5]:
            console.print(f"  - {str(e)[:120]}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
