"""
Enhanced LangGraph Workflow with Progress Monitoring

Adds Rich progress bars, live updates, and inter-stage output display.
"""

import os
import sys
import logging
import asyncio
import time
import re
import hashlib
import json
from typing import Literal, Optional, Dict, Any, List

# Fix Windows cp1252 codec crashing on emoji in Rich console output
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from ..utils.model_manager import print_token_summary
from ..utils.pipeline_tracer import PipelineTracer, compute_error_count
from ..utils.resource_monitor import get_monitor
from ..utils.context_offload import (
    offload_state_fields,
    compact_todos_with_pointer,
    restore_todo_context_if_missing,
)
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import box

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver


class _AsyncSqliteSaver(SqliteSaver):
    """SqliteSaver subclass that satisfies LangGraph's async astream() interface
    by delegating every async method to its synchronous counterpart.
    All state reads/writes are lightweight dict operations, so running them on
    the event-loop thread is fine for this single-threaded async pipeline."""

    async def aget_tuple(self, config):
        return self.get_tuple(config)

    async def alist(self, config, *, filter=None, before=None, limit=None):
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(self, config, checkpoint, metadata, new_versions):
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id):
        return self.put_writes(config, writes, task_id)

from .state import AutoGITState, create_initial_state
from .checkpointer_factory import create_checkpointer, load_existing_checkpoint
from .nodes import (
    requirements_extraction_node,
    research_node,
    generate_perspectives_node,
    problem_extraction_node,
    solution_generation_node,
    critique_node,
    consensus_check_node,
    solution_selection_node,
    architect_spec_node,
    code_generation_node,
    code_review_agent_node,
    code_testing_node,
    feature_verification_node,
    strategy_reasoner_node,
    code_fixing_node,
    smoke_test_node,
    pipeline_self_eval_node,
    goal_achievement_eval_node,
    git_publishing_node,
    set_runtime_failover_profile,
    reset_runtime_failover_profile,
)

logger = logging.getLogger(__name__)
console = Console()


_PHASE_LOCK_POLICY_VERSION = "v1"
_PHASE_LOCK_FINAL_PHASE = 4


def _phase_lock_current(state: Dict[str, Any]) -> int:
    """Return normalized phase-lock position for this run."""
    try:
        value = int(state.get("phase_lock_current_phase", 0) or 0)
    except Exception:
        value = 0
    return max(0, min(_PHASE_LOCK_FINAL_PHASE, value))


def _record_phase_gate_event(
    state: Dict[str, Any],
    *,
    gate: str,
    decision: str,
    from_phase: int,
    to_phase: int,
    allowed: bool,
    reason: str,
) -> None:
    """Persist compact phase-lock events for post-run diagnostics and tests."""
    if not isinstance(state, dict):
        return

    history = state.get("phase_gate_history")
    if not isinstance(history, list):
        history = []

    history.append(
        {
            "gate": str(gate),
            "decision": str(decision),
            "from_phase": int(from_phase),
            "to_phase": int(to_phase),
            "allowed": bool(allowed),
            "reason": str(reason),
            "policy_version": _PHASE_LOCK_POLICY_VERSION,
            "timestamp": int(time.time()),
        }
    )
    if len(history) > 200:
        history = history[-200:]

    state["phase_gate_history"] = history
    state["phase_lock_policy_version"] = _PHASE_LOCK_POLICY_VERSION
    state["phase_lock_current_phase"] = max(_phase_lock_current(state), int(to_phase if allowed else from_phase))


def _append_phase_gate_rejection(state: Dict[str, Any], node: str, route_decision: str, reason: str) -> None:
    """Track structured phase-gate rejection reasons for post-run diagnostics."""
    if not isinstance(state, dict):
        return
    rejections = state.get("phase_gate_rejections")
    if not isinstance(rejections, list):
        rejections = []
    rejections.append(
        {
            "node": str(node),
            "route_decision": str(route_decision),
            "reason": str(reason),
            "timestamp": int(time.time()),
        }
    )
    if len(rejections) > 200:
        rejections = rejections[-200:]
    state["phase_gate_rejections"] = rejections


def _persist_phase_gate_scorecard(state: Dict[str, Any]) -> Optional[str]:
    """Persist a compact phase-gate scorecard artifact for run tracking."""
    if not isinstance(state, dict):
        return None

    quality_gate = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}
    smoke = state.get("smoke_test") if isinstance(state.get("smoke_test"), dict) else {}
    scorecard = {
        "phase": 1,
        "current_stage": state.get("current_stage", ""),
        "tests_passed": bool(state.get("tests_passed", False)),
        "smoke_test_passed": bool(smoke.get("passed", False)),
        "hard_failures_count": int(quality_gate.get("hard_failures_count", 0) or 0),
        "correctness_passed": bool(quality_gate.get("correctness_passed", False)),
        "contradiction_detected": bool(quality_gate.get("contradiction_detected", False)),
        "publish_eligible": bool(quality_gate.get("publish_eligible", False)),
        "final_success": bool(state.get("final_success", False)),
        "phase_gate_rejections": state.get("phase_gate_rejections", []),
        "timestamp": int(time.time()),
    }

    output_root = str(state.get("output_dir") or "output")
    scorecard_path = os.path.join(output_root, "phase_gate_scorecard.json")
    os.makedirs(output_root, exist_ok=True)
    with open(scorecard_path, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)
    return scorecard_path


def _safe_filename_token(value: str) -> str:
    """Convert arbitrary labels (thread IDs) into filesystem-safe tokens."""
    token = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "default")).strip("._")
    return token or "default"


def _extract_trace_terminal_stage(trace_path: str) -> str:
    """Best-effort terminal stage extraction from pipeline trace JSONL."""
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
    """Extract terminal stage from agent status markdown report."""
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
    """Extract terminal stage from the persisted run-result snapshot."""
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


def _persist_run_result_snapshot(
    state: Dict[str, Any],
    *,
    logs_dir: str,
    run_id: str,
    thread_id: str,
) -> str:
    """Persist a compact result payload used by lineage validation."""
    os.makedirs(logs_dir, exist_ok=True)
    safe_thread = _safe_filename_token(thread_id)
    safe_run = _safe_filename_token(run_id)
    result_path = os.path.abspath(os.path.join(logs_dir, f"run_result_{safe_thread}_{safe_run}.json"))

    quality_gate = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}
    payload = {
        "run_id": str(run_id),
        "thread_id": str(thread_id),
        "current_stage": str(state.get("current_stage", "") or ""),
        "final_status": str(state.get("final_status", "") or ""),
        "final_success": bool(state.get("final_success", False)),
        "tests_passed": bool(state.get("tests_passed", False)),
        "quality_gate": quality_gate,
        "quality_gate_reason": str(state.get("quality_gate_reason", "") or ""),
        "output_path": str(state.get("output_path", "") or ""),
        "github_url": str(state.get("github_url", "") or ""),
        "updated_at": __import__("datetime").datetime.now().isoformat(),
    }
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return result_path


def _persist_run_lineage_manifest(
    *,
    logs_dir: str,
    run_id: str,
    thread_id: str,
    trace_file: str,
    status_file: str,
    result_file: str,
    started_at: str,
    ended_at: str,
    terminal_stage: str,
) -> str:
    """Persist run-lineage manifest and inline consistency checks."""
    os.makedirs(logs_dir, exist_ok=True)
    safe_thread = _safe_filename_token(thread_id)
    manifest_path = os.path.abspath(os.path.join(logs_dir, f"run_lineage_{safe_thread}.json"))

    trace_file = os.path.abspath(trace_file)
    status_file = os.path.abspath(status_file)
    result_file = os.path.abspath(result_file)

    trace_stage = _extract_trace_terminal_stage(trace_file)
    status_stage = _extract_status_terminal_stage(status_file)
    result_stage = _extract_result_terminal_stage(result_file)

    stage_values = {
        "manifest_terminal_stage": str(terminal_stage or "").strip(),
        "trace_terminal_stage": str(trace_stage or "").strip(),
        "status_terminal_stage": str(status_stage or "").strip(),
        "result_terminal_stage": str(result_stage or "").strip(),
    }
    missing_stage_fields = [k for k, v in stage_values.items() if not v]
    all_stage_fields_present = len(missing_stage_fields) == 0
    stages_match = all_stage_fields_present and len(set(stage_values.values())) == 1

    manifest = {
        "run_id": str(run_id),
        "thread_id": str(thread_id),
        "trace_file": trace_file,
        "status_file": status_file,
        "result_file": result_file,
        "started_at": str(started_at),
        "ended_at": str(ended_at),
        "terminal_stage": str(terminal_stage or ""),
        "trace_terminal_stage": str(trace_stage or ""),
        "status_terminal_stage": str(status_stage or ""),
        "result_terminal_stage": str(result_stage or ""),
        "consistency": {
            "files_exist": bool(
                os.path.exists(trace_file)
                and os.path.exists(status_file)
                and os.path.exists(result_file)
            ),
            "all_stage_fields_present": bool(all_stage_fields_present),
            "missing_stage_fields": missing_stage_fields,
            "stages_match": bool(stages_match),
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest_path


def _persist_runtime_manifest(
    *,
    state: Dict[str, Any],
    logs_dir: str,
    run_id: str,
    thread_id: str,
    lineage_path: str,
    result_path: str,
) -> str:
    """Persist runtime manifest with artifact fingerprints and compaction metadata."""
    os.makedirs(logs_dir, exist_ok=True)
    safe_thread = _safe_filename_token(thread_id)
    safe_run = _safe_filename_token(run_id)
    runtime_manifest_path = os.path.abspath(
        os.path.join(logs_dir, f"runtime_manifest_{safe_thread}_{safe_run}.json")
    )

    generated_code = state.get("generated_code") if isinstance(state.get("generated_code"), dict) else {}
    files = generated_code.get("files", {}) if isinstance(generated_code, dict) else {}
    files = files if isinstance(files, dict) else {}

    runtime_files = []
    for name in sorted(files.keys()):
        if not _is_runtime_relevant_file(str(name)):
            continue
        content = str(files.get(name, "") or "")
        runtime_files.append(
            {
                "name": str(name),
                "chars": len(content),
                "sha256": hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest(),
            }
        )

    context_refs = state.get("context_offload_refs", [])
    if not isinstance(context_refs, list):
        context_refs = [context_refs] if context_refs else []

    payload = {
        "run_id": str(run_id),
        "thread_id": str(thread_id),
        "current_stage": str(state.get("current_stage", "") or ""),
        "tests_passed": bool(state.get("tests_passed", False)),
        "quality_gate_reason": str(state.get("quality_gate_reason", "") or ""),
        "artifact_fingerprints": {
            "full": _compute_generated_artifact_fingerprint(state, mode="full"),
            "runtime": _compute_generated_artifact_fingerprint(state, mode="runtime"),
        },
        "runtime_files": runtime_files,
        "runtime_file_count": len(runtime_files),
        "transcript_compaction": {
            "context_offload_ref_count": len(context_refs),
            "todo_context_pointer": str(state.get("todo_context_pointer", "") or ""),
            "summarize_now": bool(state.get("summarize_now", False)),
        },
        "artifacts": {
            "lineage_manifest": os.path.abspath(lineage_path) if lineage_path else "",
            "result_snapshot": os.path.abspath(result_path) if result_path else "",
        },
        "consistency": {
            "lineage_manifest_exists": bool(lineage_path and os.path.exists(lineage_path)),
            "result_snapshot_exists": bool(result_path and os.path.exists(result_path)),
            "runtime_fingerprint_present": bool(
                _compute_generated_artifact_fingerprint(state, mode="runtime")
            ),
        },
        "updated_at": __import__("datetime").datetime.now().isoformat(),
    }

    with open(runtime_manifest_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return runtime_manifest_path


def _finalize_run_artifacts(
    state: Dict[str, Any],
    *,
    tracer: PipelineTracer,
    thread_id: str,
    started_at: str,
    persist_scorecard: bool,
) -> Dict[str, Optional[str]]:
    """Persist scorecard + run result + run lineage and close tracer."""
    scorecard_path = _persist_phase_gate_scorecard(state) if persist_scorecard else None
    tracer.finish(state)

    ended_at = __import__("datetime").datetime.now().isoformat()
    run_id = str(getattr(tracer, "ts", _safe_filename_token(thread_id)))
    result_path = _persist_run_result_snapshot(
        state,
        logs_dir="logs",
        run_id=run_id,
        thread_id=thread_id,
    )
    lineage_path = _persist_run_lineage_manifest(
        logs_dir="logs",
        run_id=run_id,
        thread_id=thread_id,
        trace_file=str(getattr(tracer, "trace_path", "")),
        status_file=str(getattr(tracer, "status_path", "")),
        result_file=result_path,
        started_at=started_at,
        ended_at=ended_at,
        terminal_stage=str(state.get("current_stage", "") or ""),
    )

    # Fail closed if trace/status/result lineage agreement is not proven.
    lineage_consistency_ok = True
    try:
        manifest_payload = json.loads(open(lineage_path, "r", encoding="utf-8").read())
        consistency = manifest_payload.get("consistency") if isinstance(manifest_payload.get("consistency"), dict) else {}
        files_exist = bool(consistency.get("files_exist", False))
        stages_match = bool(consistency.get("stages_match", False))
        status_terminal_stage = str(manifest_payload.get("status_terminal_stage", "") or "").strip()
        lineage_consistency_ok = files_exist and stages_match and bool(status_terminal_stage)
    except Exception:
        lineage_consistency_ok = False

    if not lineage_consistency_ok:
        reason = "RUN_LINEAGE_INCONSISTENT: trace/status/result terminal-stage agreement not proven"
        warnings = state.get("warnings", [])
        if not isinstance(warnings, list):
            warnings = [str(warnings)] if warnings else []
        if reason not in warnings:
            warnings.append(reason)
        state["warnings"] = warnings
        state["quality_gate_reason"] = "lineage_inconsistent"
        state["final_success"] = False
        state["final_status"] = "needs_attention"

        qg = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}
        qg = dict(qg)
        qg["publish_eligible"] = False
        qg["final_success"] = False
        qg["lineage_consistent"] = False
        qg["reason"] = "lineage_inconsistent"
        state["quality_gate"] = qg

        # Re-persist snapshots so artifacts reflect fail-closed finalization state.
        result_path = _persist_run_result_snapshot(
            state,
            logs_dir="logs",
            run_id=run_id,
            thread_id=thread_id,
        )
        lineage_path = _persist_run_lineage_manifest(
            logs_dir="logs",
            run_id=run_id,
            thread_id=thread_id,
            trace_file=str(getattr(tracer, "trace_path", "")),
            status_file=str(getattr(tracer, "status_path", "")),
            result_file=result_path,
            started_at=started_at,
            ended_at=ended_at,
            terminal_stage=str(state.get("current_stage", "") or ""),
        )

    runtime_manifest_path = _persist_runtime_manifest(
        state=state,
        logs_dir="logs",
        run_id=run_id,
        thread_id=thread_id,
        lineage_path=lineage_path,
        result_path=result_path,
    )
    state["runtime_manifest"] = runtime_manifest_path

    return {
        "scorecard_path": scorecard_path,
        "result_path": result_path,
        "lineage_path": lineage_path,
        "runtime_manifest_path": runtime_manifest_path,
        "run_id": run_id,
    }


def display_research_results(state: AutoGITState):
    """Display research results in a formatted panel"""
    # Get research context
    research_context = state.get("research_context", {})
    papers = research_context.get("papers", []) if research_context else []
    web_results = research_context.get("web_results", []) if research_context else []
    implementations = research_context.get("implementations", []) if research_context else []
    
    table = Table(title="📚 Research Results", box=box.ROUNDED, border_style="cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Details", style="white")
    
    # Display paper info
    if papers:
        first_paper = str(papers[0].get('title', 'N/A'))[:50]
        table.add_row("arXiv Papers", str(len(papers)), f"{first_paper}...")
    else:
        table.add_row("arXiv Papers", "0", "None found")
    
    # Display web results
    if web_results:
        first_result = str(web_results[0].get('title', 'N/A'))[:50]
        table.add_row("Web Results", str(len(web_results)), f"{first_result}...")
    else:
        table.add_row("Web Results", "0", "None found")
    
    # Display implementations
    if implementations:
        table.add_row("Implementations", str(len(implementations)), f"{len(implementations)} found on GitHub")
    else:
        table.add_row("Implementations", "0", "None found")
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def display_problems(state: AutoGITState):
    """Display extracted problems"""
    problems = state.get("problems", [])
    selected = state.get("selected_problem")
    
    console.print("\n")
    console.print(Panel(
        f"[bold cyan]🎯 Extracted {len(problems)} Research Problems[/bold cyan]",
        border_style="cyan"
    ))
    
    for i, problem in enumerate(problems[:3], 1):
        if isinstance(problem, dict):
            console.print(f"\n{i}. [yellow]{problem.get('title', 'Problem ' + str(i))}[/yellow]")
            console.print(f"   [dim]{str(problem.get('description', 'N/A'))[:100]}...[/dim]")
        else:
            # Problem is a string
            console.print(f"\n{i}. [yellow]{str(problem)[:100]}...[/yellow]")
    
    if selected:
        if isinstance(selected, dict):
            console.print(f"\n[bold green]✓ Selected:[/bold green] {selected.get('title', 'Problem 1')}")
        else:
            console.print(f"\n[bold green]✓ Selected:[/bold green] {str(selected)[:50]}...")
    console.print("\n")


def display_debate_round(state: AutoGITState):
    """Display debate round results"""
    rounds = state.get("debate_rounds", [])
    if not rounds:
        return
    
    current_round = rounds[-1]
    proposals = current_round.get("proposals", [])
    critiques = current_round.get("critiques", [])
    
    console.print("\n")
    console.print(Panel(
        f"[bold magenta]💡 Round {current_round.get('round_number', '?')} - {len(proposals)} Proposals, {len(critiques)} Critiques[/bold magenta]",
        border_style="magenta"
    ))
    
    # Show proposals
    for i, proposal in enumerate(proposals, 1):
        console.print(f"\n{i}. [cyan]{proposal.get('approach_name', 'Unnamed')}[/cyan]")
        console.print(f"   [green]Perspective:[/green] {proposal.get('perspective', 'N/A')}")
        console.print(f"   [dim]{str(proposal.get('key_innovation', 'N/A'))[:80]}...[/dim]")
        console.print(f"   [yellow]Novelty: {proposal.get('novelty_score', 0):.2f}[/yellow] | [blue]Feasibility: {proposal.get('feasibility_score', 0):.2f}[/blue]")
    
    console.print("\n")


def display_final_solution(state: AutoGITState):
    """Display the selected final solution"""
    solution = state.get("final_solution")
    if not solution:
        return
    
    console.print("\n")
    console.print(Panel(
        f"[bold green]🏆 SELECTED SOLUTION[/bold green]\n\n"
        f"[cyan]{solution.get('approach_name', 'N/A')}[/cyan]\n\n"
        f"[white]{solution.get('key_innovation', 'N/A')}[/white]\n\n"
        f"[dim]Architecture: {str(solution.get('architecture_design', 'N/A'))[:100]}...[/dim]",
        border_style="bright_green",
        box=box.DOUBLE
    ))
    console.print("\n")


def display_generated_code(state: AutoGITState):
    """Display generated code summary"""
    generated = state.get("generated_code", {})
    if not generated:
        return
    
    files = generated.get("files", {})
    
    console.print("\n")
    console.print(Panel(
        f"[bold cyan]💻 Generated Code[/bold cyan]",
        border_style="cyan"
    ))
    
    for filename, content in files.items():
        lines = len(content.split('\n')) if isinstance(content, str) else 0
        console.print(f"  [green]✓[/green] {filename} [dim]({lines} lines)[/dim]")
    
    console.print("\n")


def display_github_result(state: AutoGITState):
    """Display GitHub publishing result"""
    github_url = state.get("github_url")
    repo_name = state.get("repo_name")
    
    if github_url:
        console.print("\n")
        console.print(Panel(
            f"[bold green]🚀 Published to GitHub![/bold green]\n\n"
            f"[cyan]Repository:[/cyan] {repo_name}\n"
            f"[cyan]URL:[/cyan] [link={github_url}]{github_url}[/link]",
            border_style="bright_green",
            box=box.DOUBLE
        ))
        console.print("\n")


def display_test_results(state: AutoGITState):
    """Display code testing results"""
    test_results = state.get("test_results")
    tests_passed = state.get("tests_passed", False)
    
    if not test_results:
        return
    
    console.print("\n")
    
    # Create status table
    table = Table(title="🧪 Code Testing Results", box=box.ROUNDED, show_header=True)
    table.add_column("Test", style="cyan", width=30)
    table.add_column("Status", width=15)
    table.add_column("Details", style="dim", width=50)
    
    # Environment creation
    env_status = "✅ Pass" if test_results.get("environment_created") else "❌ Fail"
    table.add_row("Environment Creation", env_status, "Virtual environment setup")
    
    # Dependencies installation
    deps_status = "✅ Pass" if test_results.get("dependencies_installed") else "❌ Fail"
    table.add_row("Dependencies", deps_status, "Package installation")
    
    # Syntax validation
    syntax_status = "✅ Pass" if test_results.get("syntax_valid") else "❌ Fail"
    table.add_row("Syntax Check", syntax_status, "Python syntax validation")
    
    # Import testing
    import_status = "✅ Pass" if test_results.get("import_successful") else "❌ Fail"
    table.add_row("Import Test", import_status, "Module import validation")
    
    console.print(table)
    
    # Display errors if any
    errors = test_results.get("execution_errors", [])
    if errors:
        console.print("\n[bold red]⚠️ Errors Detected:[/bold red]")
        for error in errors[:5]:  # Limit to 5 errors
            console.print(f"  [red]•[/red] [dim]{error}[/dim]")
    
    # Display warnings if any
    warnings = test_results.get("warnings", [])
    if warnings:
        console.print("\n[bold yellow]⚠️ Warnings:[/bold yellow]")
        for warning in warnings[:3]:  # Limit to 3 warnings
            console.print(f"  [yellow]•[/yellow] [dim]{warning}[/dim]")
    
    # Overall status
    if tests_passed:
        console.print("\n[bold green]✅ All tests passed! Code is ready for publishing.[/bold green]")
    else:
        console.print("\n[bold red]❌ Tests failed! Auto-fixing will be attempted.[/bold red]")
        console.print("[yellow]Review errors above. You can choose to stop, continue fixing, or publish anyway.[/yellow]")
    
    console.print("\n")
    
    # Return whether user wants to continue
    return tests_passed


def should_continue_debate(state: AutoGITState) -> Literal["continue", "select"]:
    """Routing function: Decide whether to continue debate or select solution"""
    if state.get("_loop_detection_state") == "hard_limit":
        logger.warning("Loop detector in hard_limit state during debate; forcing solution selection")
        return "select"

    current_stage = state.get("current_stage", "")

    # Always proceed to selection on terminal/success stages
    if current_stage in ("consensus_reached", "max_rounds_reached"):
        return "select"

    # Proceed to selection on failure stages – prevents infinite retry loop
    if current_stage in (
        "solution_generation_failed",
        "critique_failed",
        "no_debate_rounds",
    ):
        logger.warning(f"Debate stage failed ({current_stage}), proceeding to solution selection")
        return "select"

    # If no proposals were generated at all, don't loop forever
    debate_rounds = state.get("debate_rounds") or []
    if not debate_rounds:
        return "select"
    last_round = debate_rounds[-1] if debate_rounds else {}
    if not last_round.get("proposals"):
        return "select"

    # Still in debate – keep going
    return "continue"


def should_regen_or_publish(state: AutoGITState) -> Literal["fix", "publish"]:
    """Routing from pipeline_self_eval: low score → code_fixing, approved → git_publishing"""
    stage = state.get("current_stage", "")
    fix_attempts = state.get("fix_attempts", 0)
    max_attempts = state.get("max_fix_attempts", 8)
    test_results = state.get("test_results", {}) if isinstance(state.get("test_results"), dict) else {}
    verification_state = test_results.get("verification_state", "")
    correctness_snapshot = _derive_correctness_snapshot(dict(state))
    correctness_passed = bool(state.get("correctness_passed", correctness_snapshot["correctness_passed"]))
    quality_gate = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}
    if bool(quality_gate.get("contradiction_detected", False)):
        reason = "quality_gate contradiction_detected=True during self-eval routing"
        logger.error("PHASE_LOCK_VIOLATION: %s", reason)
        _append_phase_gate_rejection(state, "should_regen_or_publish", "fix", reason)
        _record_phase_gate_event(
            state,
            gate="self_eval_to_goal_eval",
            decision="fix",
            from_phase=_phase_lock_current(state),
            to_phase=_phase_lock_current(state),
            allowed=False,
            reason=reason,
        )
        return "fix"
    if state.get("_loop_detection_state") == "hard_limit":
        if correctness_passed:
            logger.warning("Loop detector in hard_limit state during self-eval; correctness passed, allowing publish path")
            return "publish"
        logger.warning("Loop detector hard_limit during self-eval with failing correctness gate; forcing fix path")
        return "fix" if fix_attempts < max_attempts else "publish"
    if stage == "self_eval_needs_regen":
        # Don't send back for more fixing if we've already exhausted attempts
        if fix_attempts >= max_attempts:
            logger.warning(f"   self_eval wants regen but fix_attempts={fix_attempts} >= max={max_attempts} — publishing anyway")
            _append_phase_gate_rejection(
                state,
                "should_regen_or_publish",
                "publish",
                f"fix budget exhausted ({fix_attempts}/{max_attempts}) while self_eval_needs_regen",
            )
            _record_phase_gate_event(
                state,
                gate="self_eval_to_goal_eval",
                decision="publish",
                from_phase=_phase_lock_current(state),
                to_phase=3,
                allowed=True,
                reason="self_eval_needs_regen but fix budget exhausted",
            )
            return "publish"
        _record_phase_gate_event(
            state,
            gate="self_eval_to_goal_eval",
            decision="fix",
            from_phase=_phase_lock_current(state),
            to_phase=_phase_lock_current(state),
            allowed=False,
            reason="self_eval requested regeneration",
        )
        return "fix"
    if verification_state == "artifact_incomplete":
        logger.warning("   Incomplete artifacts detected after self-eval — forcing fix path")
        _append_phase_gate_rejection(
            state,
            "should_regen_or_publish",
            "fix",
            "artifact_incomplete detected after self-eval",
        )
        _record_phase_gate_event(
            state,
            gate="self_eval_to_goal_eval",
            decision="fix",
            from_phase=_phase_lock_current(state),
            to_phase=_phase_lock_current(state),
            allowed=False,
            reason="artifact_incomplete detected after self-eval",
        )
        return "fix"
    if not correctness_passed and fix_attempts < max_attempts:
        hard_failures = correctness_snapshot.get("hard_failures", [])
        smoke = state.get("smoke_test") or {}
        smoke_passed = bool(smoke.get("passed", False))
        node_calls = state.get("_node_exec_frequency") if isinstance(state.get("_node_exec_frequency"), dict) else {}
        self_eval_calls = int(node_calls.get("pipeline_self_eval", 0) or 0)
        if not hard_failures and smoke_passed and self_eval_calls >= 2:
            logger.warning(
                "   Correctness mismatch has no hard failures after repeated smoke-pass cycles — allowing publish to break no-op fix loop"
            )
            _append_phase_gate_rejection(
                state,
                "should_regen_or_publish",
                "publish",
                "no-op loop break after repeated smoke passes without hard failures",
            )
            _record_phase_gate_event(
                state,
                gate="self_eval_to_goal_eval",
                decision="publish",
                from_phase=_phase_lock_current(state),
                to_phase=3,
                allowed=True,
                reason="no-op loop break after repeated smoke passes",
            )
            return "publish"
        logger.warning(
            "   Correctness gate failed after self-eval (tests/hard-fail mismatch) — forcing fix path"
        )
        _append_phase_gate_rejection(
            state,
            "should_regen_or_publish",
            "fix",
            "correctness gate failed after self-eval",
        )
        _record_phase_gate_event(
            state,
            gate="self_eval_to_goal_eval",
            decision="fix",
            from_phase=_phase_lock_current(state),
            to_phase=_phase_lock_current(state),
            allowed=False,
            reason="correctness gate failed after self-eval",
        )
        return "fix"
    _record_phase_gate_event(
        state,
        gate="self_eval_to_goal_eval",
        decision="publish",
        from_phase=_phase_lock_current(state),
        to_phase=3,
        allowed=True,
        reason="self-eval approved",
    )
    return "publish"


def should_publish_after_goal_eval(state: AutoGITState) -> Literal["fix", "publish"]:
    """Route from goal-eval to publish with strict phase-lock assertions."""
    fix_attempts = state.get("fix_attempts", 0)
    max_attempts = state.get("max_fix_attempts", 8)
    correctness_snapshot = _derive_correctness_snapshot(dict(state))
    correctness_passed = bool(state.get("correctness_passed", correctness_snapshot["correctness_passed"]))
    quality_gate = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}

    phase_before = _phase_lock_current(state)
    stage = str(state.get("current_stage", "") or "")
    if stage.startswith("goal_eval_") and phase_before < 3:
        _record_phase_gate_event(
            state,
            gate="phase_inference",
            decision="advance",
            from_phase=phase_before,
            to_phase=3,
            allowed=True,
            reason=f"inferred from stage={stage}",
        )
        phase_before = _phase_lock_current(state)

    if bool(quality_gate.get("contradiction_detected", False)):
        reason = "quality_gate contradiction_detected=True during goal evaluation routing"
        logger.error("PHASE_LOCK_VIOLATION: %s", reason)
        _append_phase_gate_rejection(state, "_goal_eval_route", "fix", reason)
        _record_phase_gate_event(
            state,
            gate="goal_eval_to_publish",
            decision="fix",
            from_phase=phase_before,
            to_phase=phase_before,
            allowed=False,
            reason=reason,
        )
        return "fix"

    if phase_before < 3:
        reason = f"phase_lock blocked goal publish transition: current_phase={phase_before}"
        logger.warning("%s", reason)
        _append_phase_gate_rejection(state, "_goal_eval_route", "fix", reason)
        _record_phase_gate_event(
            state,
            gate="goal_eval_to_publish",
            decision="fix",
            from_phase=phase_before,
            to_phase=phase_before,
            allowed=False,
            reason=reason,
        )
        return "fix"

    if state.get("_loop_detection_state") == "hard_limit":
        if correctness_passed:
            logger.warning("Loop detector in hard_limit state during goal-eval; correctness passed, allowing publish path")
            _record_phase_gate_event(
                state,
                gate="goal_eval_to_publish",
                decision="publish",
                from_phase=phase_before,
                to_phase=4,
                allowed=True,
                reason="hard_limit with correctness passed",
            )
            return "publish"
        logger.warning("Loop detector hard_limit during goal-eval with failing correctness gate; forcing fix path")
        _record_phase_gate_event(
            state,
            gate="goal_eval_to_publish",
            decision="fix",
            from_phase=phase_before,
            to_phase=phase_before,
            allowed=False,
            reason="hard_limit with failing correctness gate",
        )
        return "fix" if fix_attempts < max_attempts else "publish"

    if fix_attempts >= max_attempts:
        _append_phase_gate_rejection(
            state,
            "_goal_eval_route",
            "publish",
            f"fix budget exhausted ({fix_attempts}/{max_attempts}) during goal evaluation",
        )
        _record_phase_gate_event(
            state,
            gate="goal_eval_to_publish",
            decision="publish",
            from_phase=phase_before,
            to_phase=4,
            allowed=True,
            reason=f"fix budget exhausted ({fix_attempts}/{max_attempts})",
        )
        return "publish"

    # Guard against post-approval no-op loops: goal evaluation can be approved
    # while tests_passed remains stale/False even though runtime is healthy.
    # If smoke passed and there are no hard failures, allow publish path.
    hard_failures = correctness_snapshot.get("hard_failures", [])
    smoke = state.get("smoke_test") or {}
    smoke_passed = bool(smoke.get("passed", False))
    node_calls = state.get("_node_exec_frequency") if isinstance(state.get("_node_exec_frequency"), dict) else {}
    goal_eval_calls = int(node_calls.get("goal_achievement_eval", 0) or 0)
    if (
        stage == "goal_eval_approved"
        and not correctness_passed
        and not hard_failures
        and smoke_passed
        and goal_eval_calls >= 1
    ):
        _append_phase_gate_rejection(
            state,
            "_goal_eval_route",
            "publish",
            "goal_eval_approved with smoke_passed and no hard failures; overriding stale correctness flag",
        )
        _record_phase_gate_event(
            state,
            gate="goal_eval_to_publish",
            decision="publish",
            from_phase=phase_before,
            to_phase=4,
            allowed=True,
            reason="goal_eval_approved + smoke_passed + no hard failures",
        )
        return "publish"

    if not correctness_passed:
        logger.warning("Goal-eval route blocked by correctness gate; returning to fix loop")
        _append_phase_gate_rejection(
            state,
            "_goal_eval_route",
            "fix",
            "correctness gate failed during goal evaluation",
        )
        _record_phase_gate_event(
            state,
            gate="goal_eval_to_publish",
            decision="fix",
            from_phase=phase_before,
            to_phase=phase_before,
            allowed=False,
            reason="correctness gate failed during goal evaluation",
        )
        return "fix"

    if stage == "goal_eval_needs_work":
        _record_phase_gate_event(
            state,
            gate="goal_eval_to_publish",
            decision="fix",
            from_phase=phase_before,
            to_phase=phase_before,
            allowed=False,
            reason="goal_eval_needs_work",
        )
        return "fix"

    _record_phase_gate_event(
        state,
        gate="goal_eval_to_publish",
        decision="publish",
        from_phase=phase_before,
        to_phase=4,
        allowed=True,
        reason="goal evaluation approved",
    )
    return "publish"


def should_fix_code(state: AutoGITState) -> Literal["fix", "publish"]:
    """Routing function: Decide whether to fix code or proceed to publishing"""
    tests_passed = state.get("tests_passed", False)  # Fail-safe: default to False (never auto-publish untested code)
    fix_attempts = state.get("fix_attempts", 0)
    max_attempts = state.get("max_fix_attempts", 8)  # 8 max — generous for complex projects
    current_stage = state.get("current_stage", "")
    test_results = state.get("test_results", {}) if isinstance(state.get("test_results"), dict) else {}
    verification_state = test_results.get("verification_state", "")
    correctness_snapshot = _derive_correctness_snapshot(dict(state))
    correctness_passed = bool(state.get("correctness_passed", correctness_snapshot["correctness_passed"]))
    quality_gate = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}
    if bool(quality_gate.get("contradiction_detected", False)):
        reason = "quality_gate contradiction_detected=True during fix routing"
        logger.error("PHASE_LOCK_VIOLATION: %s", reason)
        _append_phase_gate_rejection(state, "should_fix_code", "fix", reason)
        return "fix"
    if state.get("_loop_detection_state") == "hard_limit":
        if correctness_passed:
            logger.warning("Loop detector in hard_limit state during fix routing; correctness passed, allowing publish path")
            return "publish"
        logger.warning("Loop detector hard_limit during fix routing with failing correctness gate; forcing fix path if budget remains")
        return "fix" if fix_attempts < max_attempts else "publish"
    
    # CRITICAL: If no files were generated, skip fixing entirely
    generated_code = state.get("generated_code", {})
    files = generated_code.get("files", {})
    if not files or current_stage == "code_generation_skipped":
        logger.info("   No code to fix, routing to publish")
        _append_phase_gate_rejection(
            state,
            "should_fix_code",
            "publish",
            "no generated files available for fixing",
        )
        return "publish"
    
    if verification_state == "artifact_incomplete":
        logger.info("   Placeholder/skeleton artifacts detected → fix attempt required")
        _append_phase_gate_rejection(
            state,
            "should_fix_code",
            "fix",
            "artifact_incomplete detected in verification_state",
        )
        return "fix"

    security_gate_failed = bool(test_results.get("security_gate_failed", False))
    if security_gate_failed:
        if fix_attempts >= max_attempts:
            logger.warning(
                f"   Security gate failed but fix budget exhausted ({fix_attempts}/{max_attempts})"
            )
            _append_phase_gate_rejection(
                state,
                "should_fix_code",
                "publish",
                f"security gate failed with exhausted fix budget ({fix_attempts}/{max_attempts})",
            )
            return "publish"

        logger.info(
            f"   Security gate failed (Semgrep findings) → fix attempt {fix_attempts + 1}/{max_attempts}"
        )
        _append_phase_gate_rejection(
            state,
            "should_fix_code",
            "fix",
            "security_gate_failed",
        )
        return "fix"

    # If truth-first correctness passed, go to smoke-test/self-eval path.
    # tests_passed alone is insufficient when hard_failures are present.
    if correctness_passed:
        return "publish"
    
    # --- From here: correctness_passed is False ---
    
    # If fixing already failed or errored (avoid infinite loops)
    if current_stage in ["fixing_failed", "fixing_error"]:
        logger.info(f"   Stage {current_stage} (fix already attempted), routing to publish")
        _append_phase_gate_rejection(
            state,
            "should_fix_code",
            "publish",
            f"stage={current_stage} after failed fix attempt",
        )
        return "publish"

    # HARD CAP: never exceed max attempts regardless of reason
    if fix_attempts >= max_attempts:
        logger.warning(f"   Max fix attempts reached ({fix_attempts}/{max_attempts}) — giving up")
        _append_phase_gate_rejection(
            state,
            "should_fix_code",
            "publish",
            f"fix budget exhausted ({fix_attempts}/{max_attempts})",
        )
        return "publish"
    
    # Correctness failed and we have fix budget — try to fix
    logger.info(
        f"   Correctness gate failed (tests_passed={tests_passed}, hard_failures={len(correctness_snapshot['hard_failures'])}) "
        f"→ fix attempt {fix_attempts + 1}/{max_attempts}"
    )
    return "fix"


_NODE_EXECUTION_POLICY: Dict[str, Dict[str, Any]] = {
    # S21: Relaxed resource gates — cloud LLMs don't need local VRAM,
    # reduced wait_timeout (gate is advisory; long waits just waste time),
    # raised RAM% thresholds (typical dev machines run 60-80% RAM normally).
    "research": {
        "soft_budget_s": 120,
        "hard_timeout_s": 900,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 98.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    "solution_generation": {
        "soft_budget_s": 180,
        "hard_timeout_s": 360,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 98.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    "architect_spec": {
        "soft_budget_s": 90,
        "hard_timeout_s": 420,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 98.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    "code_generation": {
        "soft_budget_s": 480,
        "hard_timeout_s": 1500,
        "resource_gate": {
            "wait_timeout": 10,
            "max_cpu_percent": 98.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.5,
        },
    },
    "code_review_agent": {
        "soft_budget_s": 240,
        "hard_timeout_s": 600,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 98.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    "code_testing": {
        "soft_budget_s": 360,
        "hard_timeout_s": 900,
        "resource_gate": {
            "wait_timeout": 10,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.5,
        },
    },
    "feature_verification": {
        "soft_budget_s": 180,
        "hard_timeout_s": 420,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    # S22: Previously unwrapped nodes — now have timeout protection
    "strategy_reasoner": {
        "soft_budget_s": 120,
        "hard_timeout_s": 300,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    "code_fixing": {
        "soft_budget_s": 360,
        "hard_timeout_s": 900,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    "goal_achievement_eval": {
        "soft_budget_s": 120,
        "hard_timeout_s": 300,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    # S22: Smoke test — runs generated code in isolated venv before eval
    "smoke_test": {
        "soft_budget_s": 120,
        "hard_timeout_s": 300,
        "resource_gate": {
            "wait_timeout": 5,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 1.0,
        },
    },
    # S26: Lightweight nodes — short timeouts to prevent silent hangs
    "requirements_extraction": {
        "soft_budget_s": 60,
        "hard_timeout_s": 180,
        "resource_gate": {
            "wait_timeout": 3,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 0.5,
        },
    },
    "generate_perspectives": {
        "soft_budget_s": 60,
        "hard_timeout_s": 180,
        "resource_gate": {
            "wait_timeout": 3,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 0.5,
        },
    },
    "problem_extraction": {
        "soft_budget_s": 60,
        "hard_timeout_s": 180,
        "resource_gate": {
            "wait_timeout": 3,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 0.5,
        },
    },
    "critique": {
        "soft_budget_s": 90,
        "hard_timeout_s": 240,
        "resource_gate": {
            "wait_timeout": 3,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 0.5,
        },
    },
    "consensus_check": {
        "soft_budget_s": 45,
        "hard_timeout_s": 120,
        "resource_gate": {
            "wait_timeout": 3,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 0.5,
        },
    },
    "solution_selection": {
        "soft_budget_s": 60,
        "hard_timeout_s": 180,
        "resource_gate": {
            "wait_timeout": 3,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 0.5,
        },
    },
    "pipeline_self_eval": {
        "soft_budget_s": 90,
        "hard_timeout_s": 240,
        "resource_gate": {
            "wait_timeout": 3,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 0.5,
        },
    },
    "git_publishing": {
        "soft_budget_s": 60,
        "hard_timeout_s": 180,
        "resource_gate": {
            "wait_timeout": 3,
            "max_cpu_percent": 99.0,
            "max_ram_percent": 95.0,
            "min_free_ram_gb": 0.5,
        },
    },
}


_LOOP_NODE_HARD_LIMITS: Dict[str, int] = {
    # Debate loop
    "solution_generation": 8,
    "critique": 8,
    "consensus_check": 10,
    # Fix loop
    "code_testing": 14,
    "feature_verification": 14,
    "strategy_reasoner": 14,
    "code_fixing": 14,
    "smoke_test": 10,
    # Eval loop
    "pipeline_self_eval": 8,
    "goal_achievement_eval": 8,
}


_STAGE_FANOUT_CAPS: Dict[str, int] = {
    "generate_perspectives": 6,
    "solution_generation": 6,
    "critique": 6,
}

_HIGH_RISK_NODES = {"git_publishing"}


def _structured_error_envelope(
    *,
    node_name: str,
    stage: str,
    error_code: str,
    root_cause: str,
    remediation: str,
    retryable: bool,
    source: str = "workflow_wrapper",
) -> Dict[str, Any]:
    return {
        "error_code": error_code,
        "stage": stage,
        "source": source,
        "root_cause": root_cause,
        "remediation": remediation,
        "retryable": retryable,
        "node": node_name,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }


def _apply_stage_fanout_caps(state: AutoGITState, node_name: str) -> Dict[str, Any]:
    """Clamp fan-out inputs to keep delegation bounded per stage."""
    cap = int(_STAGE_FANOUT_CAPS.get(node_name, 0) or 0)
    if cap <= 0:
        return {}

    updates: Dict[str, Any] = {}
    events: List[Dict[str, Any]] = []

    perspectives = state.get("perspectives")
    if isinstance(perspectives, list) and len(perspectives) > cap:
        updates["perspectives"] = perspectives[:cap]
        events.append({
            "event": "fanout_capped",
            "node": node_name,
            "field": "perspectives",
            "original": len(perspectives),
            "cap": cap,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

    dyn = state.get("dynamic_perspective_configs")
    if isinstance(dyn, list) and len(dyn) > cap:
        updates["dynamic_perspective_configs"] = dyn[:cap]
        events.append({
            "event": "fanout_capped",
            "node": node_name,
            "field": "dynamic_perspective_configs",
            "original": len(dyn),
            "cap": cap,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

    spawned = state.get("spawned_agent_roles")
    if isinstance(spawned, list) and len(spawned) > cap:
        updates["spawned_agent_roles"] = spawned[:cap]
        events.append({
            "event": "fanout_capped",
            "node": node_name,
            "field": "spawned_agent_roles",
            "original": len(spawned),
            "cap": cap,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

    if events:
        updates["policy_events"] = events
        updates["warnings"] = [
            f"Fan-out cap applied at {node_name}: max {cap} parallel delegates"
        ]

    return updates


def _evaluate_execution_policy(state: AutoGITState, node_name: str) -> Dict[str, Any]:
    """Apply trust-mode allowlist and optional HITL gate for high-risk nodes."""
    trust_mode = str(state.get("trust_mode") or "trusted").lower().strip()
    allowlist_mode = str(state.get("tool_allowlist_mode") or "permissive").lower().strip()
    hitl = state.get("hitl_decisions") if isinstance(state.get("hitl_decisions"), dict) else {}

    if trust_mode in {"constrained", "untrusted"} and node_name in _HIGH_RISK_NODES:
        decision = str(hitl.get(node_name, "pending")).lower().strip()
        if decision not in {"approve", "edit"}:
            stage = "publish_blocked_policy" if node_name == "git_publishing" else f"{node_name}_blocked_policy"
            reason = (
                f"Policy blocked {node_name}: trust_mode={trust_mode}, decision={decision or 'pending'}"
            )
            return {
                "blocked": True,
                "result": {
                    "current_stage": stage,
                    "warnings": [reason],
                    "policy_events": [{
                        "event": "blocked_by_policy",
                        "node": node_name,
                        "trust_mode": trust_mode,
                        "allowlist_mode": allowlist_mode,
                        "decision": decision or "pending",
                        "timestamp": __import__("datetime").datetime.now().isoformat(),
                    }],
                },
            }

    if allowlist_mode == "strict" and node_name == "git_publishing" and trust_mode != "trusted":
        reason = f"Strict allowlist prevents publishing in {trust_mode} mode"
        return {
            "blocked": True,
            "result": {
                "current_stage": "publish_blocked_policy",
                "warnings": [reason],
                "policy_events": [{
                    "event": "blocked_by_allowlist",
                    "node": node_name,
                    "trust_mode": trust_mode,
                    "allowlist_mode": allowlist_mode,
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                }],
            },
        }

    return {"blocked": False}


def _get_loop_node_limit(node_name: str) -> int:
    return int(_LOOP_NODE_HARD_LIMITS.get(node_name, 20))


def _coerce_list(value: Any) -> list:
    """Normalize optional state/result fields to list form.

    This prevents malformed checkpoint or node outputs (e.g. string/dict)
    from corrupting loop telemetry updates.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    return [value]


def _coerce_dict(value: Any) -> dict:
    """Normalize optional mapping fields to dict form."""
    return dict(value) if isinstance(value, dict) else {}


def _derive_correctness_snapshot(merged_state: Dict[str, Any]) -> Dict[str, Any]:
    """Build a truth-first correctness snapshot from test_results/state fields.

    Hard failures are sourced from execution/runtime failures, while soft warnings
    are informational and should not alone mark a run as failed.
    """
    test_results = merged_state.get("test_results") if isinstance(merged_state.get("test_results"), dict) else {}

    hard_failures = []
    if isinstance(test_results, dict):
        exec_errors = test_results.get("execution_errors", [])
        if isinstance(exec_errors, list):
            hard_failures.extend([str(e) for e in exec_errors if str(e).strip()])
        elif exec_errors:
            hard_failures.append(str(exec_errors))

    # Fallback to top-level errors if test_results had nothing explicit.
    if not hard_failures:
        state_errors = merged_state.get("errors", [])
        if isinstance(state_errors, list):
            hard_failures.extend([str(e) for e in state_errors if str(e).strip()])
        elif state_errors:
            hard_failures.append(str(state_errors))

    soft_warnings = []
    if isinstance(test_results, dict):
        tr_warnings = test_results.get("warnings", [])
        if isinstance(tr_warnings, list):
            soft_warnings.extend([str(w) for w in tr_warnings if str(w).strip()])
        elif tr_warnings:
            soft_warnings.append(str(tr_warnings))

    state_warnings = merged_state.get("warnings", [])
    if isinstance(state_warnings, list):
        soft_warnings.extend([str(w) for w in state_warnings if str(w).strip()])
    elif state_warnings:
        soft_warnings.append(str(state_warnings))

    # Deduplicate while preserving order.
    dedup_hard = []
    seen_hard = set()
    for item in hard_failures:
        if item not in seen_hard:
            dedup_hard.append(item)
            seen_hard.add(item)

    dedup_soft = []
    seen_soft = set()
    for item in soft_warnings:
        if item not in seen_soft:
            dedup_soft.append(item)
            seen_soft.add(item)

    tests_passed = bool(merged_state.get("tests_passed", False))
    correctness_passed = tests_passed and len(dedup_hard) == 0

    return {
        "correctness_passed": correctness_passed,
        "hard_failures": dedup_hard,
        "soft_warnings": dedup_soft,
    }


def _apply_quality_contract(state_patch: Dict[str, Any], *, terminal: bool = False) -> Dict[str, Any]:
    """Normalize correctness fields and derive final success semantics.

    This keeps a single truth source across routing, summaries, and benchmark scripts.
    """
    normalized = dict(state_patch)
    snapshot = _derive_correctness_snapshot(normalized)
    normalized.update(snapshot)

    tests_passed = bool(normalized.get("tests_passed", False))
    correctness_passed = bool(snapshot["correctness_passed"])
    hard_failures = snapshot["hard_failures"]
    soft_warnings = snapshot["soft_warnings"]
    stage = str(normalized.get("current_stage", "") or "")
    terminal_publish_stages = {"published", "saved_locally"}

    # Contradiction is broader than tests-pass mismatch:
    # any publish-like terminal stage with failing correctness semantics is contradictory.
    prior_quality_gate = normalized.get("quality_gate") if isinstance(normalized.get("quality_gate"), dict) else {}
    prior_contradiction = bool(prior_quality_gate.get("contradiction_detected", False))
    prior_warning_contradiction = any(
        "QUALITY_GATE_CONTRADICTION" in str(w)
        for w in (normalized.get("warnings", []) if isinstance(normalized.get("warnings"), list) else [])
    )

    contradiction_reasons: List[str] = []
    if tests_passed and not correctness_passed:
        contradiction_reasons.append("tests_passed_but_correctness_failed")
    if stage in terminal_publish_stages and not correctness_passed:
        contradiction_reasons.append("publish_stage_without_correctness")
    if prior_contradiction:
        contradiction_reasons.append("prior_quality_gate_contradiction")
    if prior_warning_contradiction:
        contradiction_reasons.append("prior_warning_contradiction")

    contradiction = bool(contradiction_reasons)

    publish_eligible = (
        correctness_passed
        and not bool(normalized.get("self_eval_unverified", False))
        and not bool(normalized.get("goal_eval_unverified", False))
    )

    quality_gate_reason = str(normalized.get("quality_gate_reason", "") or "").strip()
    if contradiction:
        # Contradiction-dominance: contradiction always blocks publish/final success.
        publish_eligible = False
        quality_gate_reason = "contradiction_detected:" + ",".join(contradiction_reasons)
    elif not quality_gate_reason:
        quality_gate_reason = "quality_gate_passed" if publish_eligible else "correctness_gate_failed"

    terminal_success_stages = {"published", "saved_locally"}
    final_success = bool(terminal and stage in terminal_success_stages and publish_eligible)

    if contradiction:
        warning = (
            "QUALITY_GATE_CONTRADICTION: publish-like stage reached while correctness gate is failing "
            f"(stage={stage}, tests_passed={tests_passed}, hard_failures={len(hard_failures)})."
        )
        warnings = normalized.get("warnings", [])
        if isinstance(warnings, list):
            if warning not in warnings:
                warnings.append(warning)
            normalized["warnings"] = warnings
        elif warnings:
            normalized["warnings"] = [str(warnings), warning]
        else:
            normalized["warnings"] = [warning]

    normalized["quality_gate"] = {
        "tests_passed": tests_passed,
        "correctness_passed": correctness_passed,
        "hard_failures_count": len(hard_failures),
        "soft_warnings_count": len(soft_warnings),
        "contradiction_detected": contradiction,
        "publish_eligible": publish_eligible,
        "final_success": final_success,
        "reason": quality_gate_reason,
    }
    normalized["quality_gate_reason"] = quality_gate_reason
    normalized["final_success"] = final_success
    normalized["final_status"] = "success" if final_success else "needs_attention"
    return normalized


def _compute_workflow_fingerprint(merged_state: Dict[str, Any], node_name: str, stage: str) -> str:
    """Create a compact deterministic signature for oscillation detection."""
    test_results = merged_state.get("test_results") if isinstance(merged_state.get("test_results"), dict) else {}
    exec_errors = test_results.get("execution_errors", []) if isinstance(test_results, dict) else []
    exec_errors = [str(e)[:200] for e in exec_errors[:3]] if isinstance(exec_errors, list) else []

    files_summary = []
    generated_code = merged_state.get("generated_code") if isinstance(merged_state.get("generated_code"), dict) else {}
    files = generated_code.get("files", {}) if isinstance(generated_code, dict) else {}
    if isinstance(files, dict):
        for fname in sorted(files.keys())[:20]:
            content = files.get(fname)
            files_summary.append(f"{fname}:{len(str(content or ''))}")

    payload = {
        "node": node_name,
        "stage": stage,
        "tests_passed": bool(merged_state.get("tests_passed", False)),
        "fix_attempts": int(merged_state.get("fix_attempts", 0) or 0),
        "errors": exec_errors,
        "files": files_summary,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()[:16]


def _update_loop_detection_state(state: AutoGITState, node_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Update workflow-level loop telemetry and trip hard limit when oscillation repeats."""
    merged_state: Dict[str, Any] = dict(state)
    merged_state.update(result)
    stage = str(merged_state.get("current_stage", ""))

    counts = _coerce_dict(state.get("_node_exec_frequency"))
    notes = _coerce_list(state.get("_loop_detection_notes"))
    path = _coerce_list(state.get("_current_node_path"))
    history = _coerce_list(state.get("_node_paths_history"))
    fingerprints = _coerce_list(state.get("_workflow_state_fingerprints"))
    loop_state = str(state.get("_loop_detection_state") or "clean")

    counts[node_name] = int(counts.get(node_name, 0) or 0) + 1
    node_count = counts[node_name]
    node_limit = _get_loop_node_limit(node_name)

    path.append(node_name)
    if len(path) > 80:
        path = path[-80:]
    history.append(">".join(path[-25:]))
    if len(history) > 30:
        history = history[-30:]

    fp = _compute_workflow_fingerprint(merged_state, node_name, stage)
    fingerprints.append(fp)
    if len(fingerprints) > 20:
        fingerprints = fingerprints[-20:]

    recent = fingerprints[-10:]
    repeat_count = recent.count(fp)
    oscillation_candidate_nodes = {
        "code_testing",
        "feature_verification",
        "strategy_reasoner",
        "code_fixing",
        "smoke_test",
        "pipeline_self_eval",
        "goal_achievement_eval",
    }
    oscillating = node_name in oscillation_candidate_nodes and repeat_count >= 4

    if node_count > node_limit or oscillating:
        loop_state = "hard_limit"
        reason = (
            f"Loop detector hard limit at node '{node_name}': "
            f"count={node_count}/{node_limit}, repeat_signature={repeat_count}"
        )
        notes.append(reason)
        notes = notes[-30:]
        result["warnings"] = _coerce_list(result.get("warnings")) + [reason]
        result["resource_events"] = _coerce_list(result.get("resource_events")) + [{
            "node": node_name,
            "event": "loop_hard_limit",
            "count": node_count,
            "limit": node_limit,
            "repeat_signature": repeat_count,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }]

    result["_node_exec_frequency"] = counts
    result["_current_node_path"] = path
    result["_node_paths_history"] = history
    result["_workflow_state_fingerprints"] = fingerprints
    result["_loop_detection_state"] = loop_state
    result["_loop_detection_notes"] = notes
    return result


def _build_timeout_fallback(node_name: str, warning: str) -> Dict[str, Any]:
    """Return a safe fallback state for wrapped node timeouts."""
    base: Dict[str, Any] = {
        "warnings": [warning],
        "structured_errors": [
            _structured_error_envelope(
                node_name=node_name,
                stage=f"{node_name}_timeout",
                error_code="NODE_TIMEOUT",
                root_cause=warning,
                remediation="Increase node timeout or reduce workload for this stage.",
                retryable=True,
            )
        ],
        "resource_events": [{
            "node": node_name,
            "event": "hard_timeout",
            "warning": warning,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }],
    }
    if node_name == "research":
        base.update({
            "current_stage": "research_timeout",
            "research_context": {
                "papers": [],
                "web_results": [],
                "implementations": [],
                "search_timestamp": __import__("datetime").datetime.now().isoformat(),
            },
            "research_summary": "",
            "research_report": None,
        })
    elif node_name == "architect_spec":
        base.update({
            "current_stage": "architect_spec_failed",
            "architecture_spec": None,
            "_architecture_spec_text": "",
        })
    elif node_name == "code_generation":
        base.update({
            "current_stage": "code_generation_timeout",
            "generated_code": {},
        })
    elif node_name == "code_review_agent":
        base.update({
            "current_stage": "code_review_timeout",
        })
    elif node_name == "feature_verification":
        base.update({
            "current_stage": "feature_verification_skipped",
            "tests_passed": False,
            "test_results": {
                "execution_errors": ["FEATURE_VERIFICATION_TIMEOUT: Node exceeded hard timeout"],
                "verification_state": "feature_verification_timeout",
            },
        })
    else:
        base.update({
            "current_stage": f"{node_name}_timeout",
        })
    return base


def _append_budget_report(
    state: AutoGITState,
    node_name: str,
    elapsed_s: float,
    policy: Dict[str, Any],
    resource_snapshot: Optional[Dict[str, Any]] = None,
    waited_s: float = 0.0,
    timed_out: bool = False,
    timeout_source: str = "none",
) -> Dict[str, Any]:
    report = dict(state.get("node_budget_report") or {})
    report[node_name] = {
        "elapsed_s": round(elapsed_s, 3),
        "soft_budget_s": policy.get("soft_budget_s"),
        "hard_timeout_s": policy.get("hard_timeout_s"),
        "effective_soft_budget_s": policy.get("soft_budget_s"),
        "effective_hard_timeout_s": policy.get("hard_timeout_s"),
        "waited_for_resources_s": round(waited_s, 3),
        "timed_out": timed_out,
        "timeout_source": str(timeout_source or "none"),
        "resource_snapshot": resource_snapshot,
        "updated_at": __import__("datetime").datetime.now().isoformat(),
    }
    return report


def _collect_timeout_markers(result: Dict[str, Any]) -> List[str]:
    """Collect timeout-like markers emitted by node internals/providers."""
    markers: List[str] = []
    if not isinstance(result, dict):
        return markers

    stage = str(result.get("current_stage", "") or "")
    if "timeout" in stage.lower():
        markers.append(f"stage:{stage}")

    for key in ("errors", "warnings"):
        values = result.get(key, [])
        if isinstance(values, list):
            for item in values:
                text = str(item or "")
                if "timeout" in text.lower():
                    markers.append(f"{key}:{text[:200]}")
        elif values:
            text = str(values)
            if "timeout" in text.lower():
                markers.append(f"{key}:{text[:200]}")

    test_results = result.get("test_results") if isinstance(result.get("test_results"), dict) else {}
    exec_errors = test_results.get("execution_errors", []) if isinstance(test_results, dict) else []
    if isinstance(exec_errors, list):
        for item in exec_errors:
            text = str(item or "")
            if "timeout" in text.lower():
                markers.append(f"execution_errors:{text[:200]}")
    elif exec_errors:
        text = str(exec_errors)
        if "timeout" in text.lower():
            markers.append(f"execution_errors:{text[:200]}")

    deduped: List[str] = []
    seen = set()
    for marker in markers:
        if marker not in seen:
            seen.add(marker)
            deduped.append(marker)
    return deduped


def _collect_provider_stall_markers(result: Dict[str, Any]) -> List[str]:
    """Collect provider-throttle/stall hints to classify timeout source precisely."""
    if not isinstance(result, dict):
        return []

    markers: List[str] = []
    keywords = (
        "rate limit",
        "429",
        "cooldown",
        "provider",
        "throttle",
        "quota",
    )

    def _scan_value(prefix: str, value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                text = str(item or "")
                lower = text.lower()
                if any(k in lower for k in keywords):
                    markers.append(f"{prefix}:{text[:200]}")
        elif value:
            text = str(value)
            lower = text.lower()
            if any(k in lower for k in keywords):
                markers.append(f"{prefix}:{text[:200]}")

    _scan_value("errors", result.get("errors"))
    _scan_value("warnings", result.get("warnings"))

    test_results = result.get("test_results") if isinstance(result.get("test_results"), dict) else {}
    _scan_value("execution_errors", test_results.get("execution_errors"))

    deduped: List[str] = []
    seen = set()
    for marker in markers:
        if marker not in seen:
            seen.add(marker)
            deduped.append(marker)
    return deduped


def _classify_timeout_source(
    result: Dict[str, Any],
    elapsed_s: float,
    policy: Dict[str, Any],
    *,
    timed_out: bool,
) -> str:
    """Classify timeout source for observability and acceptance-gate auditing."""
    if timed_out:
        return "policy_hard_timeout"

    hard_timeout_s = float(policy.get("hard_timeout_s") or 0)
    soft_budget_s = float(policy.get("soft_budget_s") or 0)
    if hard_timeout_s > 0 and elapsed_s > hard_timeout_s + 5:
        return "cancellation_delay"

    markers = _collect_timeout_markers(result)
    provider_markers = _collect_provider_stall_markers(result)
    if markers and provider_markers:
        return "provider_stall"
    if markers:
        return "node_internal_timeout"

    if soft_budget_s > 0 and elapsed_s > soft_budget_s:
        return "soft_budget_exceeded"

    return "none"


def _normalize_todo_key(text: str) -> str:
    """Normalize requirement text into a stable lookup key."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def _split_user_requirements(user_reqs: str) -> list[str]:
    if not user_reqs:
        return []
    parts = [p.strip() for p in re.split(r"[;,\n]", user_reqs) if p.strip()]
    deduped = []
    seen = set()
    for p in parts:
        k = _normalize_todo_key(p)
        if k and k not in seen:
            seen.add(k)
            deduped.append(p)
    return deduped


def _make_todo(
    todo_id: str,
    title: str,
    detail: str,
    category: str,
    priority: str,
    acceptance_criteria: list[str],
    verification_nodes: list[str],
    requirement_key: str = "",
) -> Dict[str, Any]:
    return {
        "id": todo_id,
        "title": title,
        "detail": detail,
        "category": category,
        "priority": priority,
        "status": "pending",
        "acceptance_criteria": acceptance_criteria,
        "verification_nodes": verification_nodes,
        "requirement_key": requirement_key,
        "evidence": "",
        "updated_stage": "initialized",
    }


def _build_initial_pipeline_todos(state: AutoGITState, requirements: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Build detailed todos from extracted requirements and pipeline gates."""
    reqs = requirements if isinstance(requirements, dict) else {}
    components = [c for c in reqs.get("core_components", []) if isinstance(c, str) and c.strip()]
    features = [f for f in reqs.get("key_features", []) if isinstance(f, str) and f.strip()]
    scenarios = [s for s in reqs.get("test_scenarios", []) if isinstance(s, dict)]
    user_items = _split_user_requirements(state.get("user_requirements", "") or "")

    todos: list[Dict[str, Any]] = []
    todos.append(_make_todo(
        todo_id="GATE-REQUIREMENTS",
        title="Finalize requirement baseline",
        detail="Create a canonical project scope from idea + user constraints + extracted structure before downstream generation.",
        category="gate",
        priority="critical",
        acceptance_criteria=[
            "Structured requirements JSON exists and is non-empty",
            "Complexity/project type are identified",
            "Core components and key features are enumerated",
        ],
        verification_nodes=["requirements_extraction"],
    ))
    todos.append(_make_todo(
        todo_id="GATE-RESEARCH",
        title="Assemble validated research context",
        detail="Collect evidence-backed references and implementation patterns to ground architecture and code generation.",
        category="gate",
        priority="high",
        acceptance_criteria=[
            "Research stage completes with non-empty context or explicit fallback rationale",
            "Research summary is available for prompt grounding",
        ],
        verification_nodes=["research"],
    ))
    todos.append(_make_todo(
        todo_id="GATE-ARCH",
        title="Produce architecture specification",
        detail="Create a concrete architecture blueprint (modules, data flow, interfaces, and implementation constraints).",
        category="gate",
        priority="critical",
        acceptance_criteria=[
            "Architecture spec is produced",
            "Spec includes file/module strategy and data flow",
            "Spec can be injected into code generation prompt",
        ],
        verification_nodes=["architect_spec"],
    ))
    todos.append(_make_todo(
        todo_id="GATE-CODEGEN",
        title="Generate implementation artifacts",
        detail="Generate complete runnable files with requirements and README aligned to requested capabilities.",
        category="gate",
        priority="critical",
        acceptance_criteria=[
            "generated_code.files is non-empty",
            "main entrypoint and dependency manifest exist",
            "No placeholder-only artifact set",
        ],
        verification_nodes=["code_generation"],
    ))
    todos.append(_make_todo(
        todo_id="GATE-TEST-RUNTIME",
        title="Pass runtime validation",
        detail="Ensure generated code passes core testing/validation and resolves executable failures.",
        category="quality_gate",
        priority="critical",
        acceptance_criteria=[
            "code_testing reports tests_passed=true",
            "No blocking execution_errors remain",
        ],
        verification_nodes=["code_testing", "code_fixing"],
    ))
    todos.append(_make_todo(
        todo_id="GATE-FEATURE",
        title="Verify requested features",
        detail="Run feature verification against required behavior and enforce fix-loop until acceptable pass rate.",
        category="quality_gate",
        priority="critical",
        acceptance_criteria=[
            "feature_verification completes",
            "Feature pass rate reaches target threshold",
        ],
        verification_nodes=["feature_verification", "goal_achievement_eval"],
    ))
    todos.append(_make_todo(
        todo_id="GATE-SMOKE",
        title="Pass isolated smoke run",
        detail="Install and execute generated project in isolated environment to prove end-to-end runnable output.",
        category="quality_gate",
        priority="high",
        acceptance_criteria=[
            "smoke_test.passed is true",
            "Main entrypoint runs without fatal error",
        ],
        verification_nodes=["smoke_test"],
    ))
    todos.append(_make_todo(
        todo_id="GATE-GOAL",
        title="Satisfy user goal coverage",
        detail="Reach high requirement implementation coverage with concrete evidence per requested capability.",
        category="quality_gate",
        priority="critical",
        acceptance_criteria=[
            "Goal evaluation report exists",
            "Overall implemented percentage reaches acceptance threshold",
        ],
        verification_nodes=["goal_achievement_eval"],
    ))
    todos.append(_make_todo(
        todo_id="GATE-PUBLISH",
        title="Publish or save verified deliverable",
        detail="Publish to GitHub when quality gates pass, otherwise save locally with traceable reports.",
        category="delivery_gate",
        priority="high",
        acceptance_criteria=[
            "Published URL exists OR local output directory is created",
            "Final state includes clear completion status",
        ],
        verification_nodes=["git_publishing"],
    ))

    for idx, comp in enumerate(components, start=1):
        todos.append(_make_todo(
            todo_id=f"COMP-{idx:02d}",
            title=f"Implement component: {comp}",
            detail=f"Build and integrate the '{comp}' module with stable interfaces and production-oriented behavior.",
            category="component",
            priority="high",
            acceptance_criteria=[
                f"Component '{comp}' has concrete implementation code",
                f"Component '{comp}' is wired into overall project flow",
                "No TODO/stub placeholders for core logic",
            ],
            verification_nodes=["code_generation", "goal_achievement_eval", "code_testing"],
            requirement_key=_normalize_todo_key(comp),
        ))

    for idx, feat in enumerate(features, start=1):
        todos.append(_make_todo(
            todo_id=f"FEAT-{idx:02d}",
            title=f"Deliver feature: {feat}",
            detail=f"Implement full user-visible behavior for '{feat}' with robust runtime handling.",
            category="feature",
            priority="critical",
            acceptance_criteria=[
                f"Feature '{feat}' has runnable implementation",
                f"Feature '{feat}' appears in goal-eval evidence",
                "Feature behavior survives test and fix cycles",
            ],
            verification_nodes=["feature_verification", "goal_achievement_eval", "smoke_test"],
            requirement_key=_normalize_todo_key(feat),
        ))

    for idx, scen in enumerate(scenarios, start=1):
        name = str(scen.get("name", f"Scenario {idx}")).strip()
        expected = str(scen.get("expected", "Expected behavior should be met")).strip()
        todos.append(_make_todo(
            todo_id=f"TEST-{idx:02d}",
            title=f"Satisfy scenario: {name}",
            detail=f"Ensure scenario '{name}' passes with expected result: {expected}",
            category="test_scenario",
            priority="high",
            acceptance_criteria=[
                f"Scenario '{name}' is represented by runnable logic",
                "Execution output aligns with expected result",
            ],
            verification_nodes=["code_testing", "feature_verification", "goal_achievement_eval"],
            requirement_key=_normalize_todo_key(name),
        ))

    for idx, item in enumerate(user_items, start=1):
        todos.append(_make_todo(
            todo_id=f"USER-{idx:02d}",
            title=f"Honor user constraint: {item}",
            detail=f"Apply explicit user-provided requirement: '{item}' across architecture, code, and verification.",
            category="user_requirement",
            priority="critical",
            acceptance_criteria=[
                "Constraint is visible in implementation",
                "Constraint is validated by final goal-eval evidence",
            ],
            verification_nodes=["architect_spec", "code_generation", "goal_achievement_eval"],
            requirement_key=_normalize_todo_key(item),
        ))

    return todos


def _set_todo_status(task: Dict[str, Any], status: str, stage: str, evidence: str = "") -> None:
    task["status"] = status
    task["updated_stage"] = stage
    if evidence:
        task["evidence"] = evidence


def _update_todo_summary(todos: list[Dict[str, Any]], stage: str) -> Dict[str, Any]:
    counts = {
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "blocked": 0,
    }
    for task in todos:
        status = task.get("status", "pending")
        if status not in counts:
            status = "pending"
        counts[status] += 1

    total = max(len(todos), 1)
    completion_pct = round((counts["completed"] / total) * 100.0, 1)
    critical_open = [
        t.get("title", "")
        for t in todos
        if t.get("priority") == "critical" and t.get("status") != "completed"
    ]
    return {
        "total": len(todos),
        "pending": counts["pending"],
        "in_progress": counts["in_progress"],
        "completed": counts["completed"],
        "blocked": counts["blocked"],
        "completion_pct": completion_pct,
        "critical_open": critical_open[:15],
        "last_updated_stage": stage,
    }


def _update_pipeline_todos(state: AutoGITState, node_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Generate/update detailed pipeline todos based on stage outcomes."""
    merged_state: Dict[str, Any] = dict(state)
    merged_state.update(result)
    stage = str(merged_state.get("current_stage", ""))

    todos = result.get("pipeline_todos")
    if not isinstance(todos, list):
        todos = state.get("pipeline_todos", [])
    todos = [dict(t) for t in todos if isinstance(t, dict)]

    if node_name == "requirements_extraction" and not todos:
        reqs = merged_state.get("requirements") or {}
        todos = _build_initial_pipeline_todos(merged_state, reqs)
        result["todo_generation_notes"] = (
            "Detailed todos generated from structured requirements and pipeline quality gates."
        )

    if not todos:
        return result

    by_id = {t.get("id"): t for t in todos if t.get("id")}

    if stage == "requirements_extracted":
        if "GATE-REQUIREMENTS" in by_id:
            _set_todo_status(by_id["GATE-REQUIREMENTS"], "completed", stage, "Structured requirements extracted.")
    elif stage == "requirements_extraction_failed":
        if "GATE-REQUIREMENTS" in by_id:
            _set_todo_status(by_id["GATE-REQUIREMENTS"], "blocked", stage, "Requirements extraction failed.")

    if node_name == "research":
        if "GATE-RESEARCH" in by_id:
            if stage == "research_complete":
                _set_todo_status(by_id["GATE-RESEARCH"], "completed", stage, "Research context assembled.")
            elif "failed" in stage or "timeout" in stage:
                _set_todo_status(by_id["GATE-RESEARCH"], "blocked", stage, f"Research stage ended with '{stage}'.")
            else:
                _set_todo_status(by_id["GATE-RESEARCH"], "in_progress", stage, f"Research stage '{stage}'.")

    if node_name == "architect_spec" and "GATE-ARCH" in by_id:
        if stage == "architect_spec_complete":
            _set_todo_status(by_id["GATE-ARCH"], "completed", stage, "Architecture specification generated.")
        elif "failed" in stage or "timeout" in stage:
            _set_todo_status(by_id["GATE-ARCH"], "blocked", stage, f"Architecture stage ended with '{stage}'.")

    if node_name == "code_generation":
        if "GATE-CODEGEN" in by_id:
            if stage == "code_generated":
                _set_todo_status(by_id["GATE-CODEGEN"], "completed", stage, "Code artifacts generated.")
                for t in todos:
                    if t.get("category") in {"component", "feature", "user_requirement", "test_scenario"} and t.get("status") == "pending":
                        _set_todo_status(t, "in_progress", stage, "Code generated; awaiting verification evidence.")
            elif "failed" in stage or "timeout" in stage:
                _set_todo_status(by_id["GATE-CODEGEN"], "blocked", stage, f"Code generation ended with '{stage}'.")

    if node_name == "code_testing" and "GATE-TEST-RUNTIME" in by_id:
        correctness_snapshot = _derive_correctness_snapshot(merged_state)
        correctness_passed = bool(merged_state.get("correctness_passed", correctness_snapshot["correctness_passed"]))
        if stage == "testing_complete" and correctness_passed:
            _set_todo_status(by_id["GATE-TEST-RUNTIME"], "completed", stage, "Core runtime tests passed.")
        elif stage in {"testing_complete", "testing_failed"}:
            _set_todo_status(by_id["GATE-TEST-RUNTIME"], "blocked", stage, "Runtime tests still failing.")

    if node_name == "feature_verification" and "GATE-FEATURE" in by_id:
        fv = ((merged_state.get("test_results") or {}).get("feature_verification") or {})
        rate = float(((fv.get("summary") or {}).get("pass_rate", 0.0)) or 0.0)
        if stage == "feature_verification_complete" and rate >= 80:
            _set_todo_status(by_id["GATE-FEATURE"], "completed", stage, f"Feature pass rate {rate:.0f}%.")
        elif stage == "feature_verification_complete":
            _set_todo_status(by_id["GATE-FEATURE"], "in_progress", stage, f"Feature pass rate {rate:.0f}% (needs improvement).")
        elif "failed" in stage or "skipped" in stage:
            _set_todo_status(by_id["GATE-FEATURE"], "blocked", stage, f"Feature verification ended with '{stage}'.")

    if node_name == "smoke_test" and "GATE-SMOKE" in by_id:
        smoke = merged_state.get("smoke_test") or {}
        smoke_ok = bool(smoke.get("passed", False))
        if stage == "smoke_test_passed" and smoke_ok:
            _set_todo_status(by_id["GATE-SMOKE"], "completed", stage, "Smoke run succeeded in isolated environment.")
        elif stage in {"smoke_test_failed", "smoke_test_error"}:
            _set_todo_status(by_id["GATE-SMOKE"], "blocked", stage, "Smoke run failed.")

    if node_name == "goal_achievement_eval":
        report = merged_state.get("goal_eval_report") or {}
        req_reports = report.get("requirements", []) if isinstance(report, dict) else []
        req_map: Dict[str, Dict[str, Any]] = {}
        for rr in req_reports:
            if not isinstance(rr, dict):
                continue
            key = _normalize_todo_key(str(rr.get("name", "")))
            if key:
                req_map[key] = rr

        for t in todos:
            category = t.get("category")
            if category not in {"component", "feature", "user_requirement", "test_scenario"}:
                continue
            key = t.get("requirement_key", "")
            rr = req_map.get(key)
            if not rr:
                continue
            status = str(rr.get("status", "missing"))
            evidence = str(rr.get("evidence", ""))
            if status == "implemented":
                _set_todo_status(t, "completed", stage, evidence)
            elif status == "partial":
                _set_todo_status(t, "in_progress", stage, evidence)
            else:
                _set_todo_status(t, "pending", stage, evidence)

        if "GATE-GOAL" in by_id:
            pct = float(report.get("overall_pct_implemented", 0.0)) if isinstance(report, dict) else 0.0
            if stage == "goal_eval_approved" and pct >= 80:
                _set_todo_status(by_id["GATE-GOAL"], "completed", stage, f"Goal coverage {pct:.0f}%.")
            elif stage == "goal_eval_approved":
                _set_todo_status(by_id["GATE-GOAL"], "in_progress", stage, f"Approved with {pct:.0f}% coverage.")
            else:
                _set_todo_status(by_id["GATE-GOAL"], "in_progress", stage, "Goal eval requested further work.")

    if node_name == "git_publishing" and "GATE-PUBLISH" in by_id:
        if stage == "published":
            _set_todo_status(by_id["GATE-PUBLISH"], "completed", stage, "Project published successfully.")
        elif stage == "saved_locally_tests_failed":
            _set_todo_status(by_id["GATE-PUBLISH"], "blocked", stage, "Correctness gate failed; saved locally only.")
        elif stage.startswith("saved_locally"):
            _set_todo_status(by_id["GATE-PUBLISH"], "completed", stage, "Saved locally with reports/artifacts.")
        elif "failed" in stage:
            _set_todo_status(by_id["GATE-PUBLISH"], "blocked", stage, "Publishing failed.")

    result["pipeline_todos"] = todos
    result["todo_progress"] = _update_todo_summary(todos, stage)
    return result


def _is_runtime_relevant_file(name: str) -> bool:
    """Return True for files likely to affect runtime execution and verification."""
    normalized = str(name or "").replace("\\", "/").strip().lower()
    base = normalized.rsplit("/", 1)[-1]

    if not normalized:
        return False

    # Dependency/build metadata should invalidate runtime verification caches.
    runtime_manifest_files = {
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "pipfile",
        "pipfile.lock",
        "poetry.lock",
    }
    if base in runtime_manifest_files:
        return True

    # Ignore documentation-only artifacts for runtime checks.
    if base in {"readme.md", "license", "license.txt", "changelog.md"}:
        return False

    runtime_exts = {".py", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".txt"}
    for ext in runtime_exts:
        if normalized.endswith(ext):
            return True
    return False


def _compute_generated_artifact_fingerprint(state: Dict[str, Any], mode: str = "full") -> str:
    """Build deterministic fingerprint for generated code artifacts.

    Modes:
    - full: include all generated files (strict invalidation)
    - runtime: include only runtime-relevant files (faster reuse)
    """
    generated_code = state.get("generated_code") if isinstance(state.get("generated_code"), dict) else {}
    files = generated_code.get("files", {}) if isinstance(generated_code, dict) else {}
    if not isinstance(files, dict) or not files:
        return ""

    hasher = hashlib.sha256()
    included = 0
    for name in sorted(files.keys()):
        if mode == "runtime" and not _is_runtime_relevant_file(str(name)):
            continue
        included += 1
        hasher.update(str(name).encode("utf-8", errors="replace"))
        hasher.update(b"\x00")
        hasher.update(str(files.get(name, "")).encode("utf-8", errors="replace"))
        hasher.update(b"\x00")
    if included == 0:
        return ""
    return hasher.hexdigest()


def _coerce_list_shape(state_patch: Dict[str, Any], keys: tuple[str, ...] = ("errors", "warnings")) -> Dict[str, Any]:
    """Normalize list-like fields to avoid type drift in long runs."""
    for key in keys:
        value = state_patch.get(key, [])
        if isinstance(value, list):
            state_patch[key] = value
            continue
        if value in (None, ""):
            state_patch[key] = []
        else:
            state_patch[key] = [str(value)]
    return state_patch


def _append_unique_capped(
    existing: Any,
    new_items: Any,
    *,
    cap: int = 600,
) -> List[Any]:
    """Merge append-only list fields with dedup + bounded growth."""
    combined: List[Any] = []
    seen: set[str] = set()

    def _iter_items(value: Any) -> List[Any]:
        if isinstance(value, list):
            return value
        if value in (None, ""):
            return []
        return [value]

    for item in _iter_items(existing) + _iter_items(new_items):
        key = json.dumps(item, sort_keys=True, default=str) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            continue
        seen.add(key)
        combined.append(item)

    if cap > 0 and len(combined) > cap:
        return combined[-cap:]
    return combined


def _trim_reasoning_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """Trim high-entropy failure payloads before reason/fix nodes to avoid 413s."""
    trimmed = dict(state)
    test_results = dict(trimmed.get("test_results") or {}) if isinstance(trimmed.get("test_results"), dict) else {}

    def _trim_list(values: Any, max_items: int = 24, max_chars: int = 500) -> List[str]:
        items = values if isinstance(values, list) else ([values] if values else [])
        out: List[str] = []
        for item in items[:max_items]:
            text = str(item).strip()
            if len(text) > max_chars:
                text = text[:max_chars] + " ...[truncated]"
            out.append(text)
        return out

    if test_results:
        test_results["execution_errors"] = _trim_list(test_results.get("execution_errors", []), max_items=20, max_chars=420)
        test_results["smoke_test_errors"] = _trim_list(test_results.get("smoke_test_errors", []), max_items=12, max_chars=420)
        test_results["tracebacks"] = _trim_list(test_results.get("tracebacks", []), max_items=8, max_chars=700)
        trimmed["test_results"] = test_results

    trimmed["errors"] = _trim_list(trimmed.get("errors", []), max_items=40, max_chars=380)
    trimmed["warnings"] = _trim_list(trimmed.get("warnings", []), max_items=30, max_chars=320)
    return trimmed


def _cloud_provider_available() -> bool:
    """Return True when at least one cloud LLM provider is configured."""
    cloud_keys = [
        os.getenv("OPENROUTER_API_KEY", ""),
        os.getenv("OPENAI_API_KEY", ""),
        os.getenv("GROQ_API_KEY", ""),
        os.getenv("GLM_API_KEY", ""),
    ]
    if any(str(v or "").strip() for v in cloud_keys):
        return True

    for i in range(1, 8):
        if str(os.getenv(f"GROQ_API_KEY_{i}", "") or "").strip():
            return True
    return False


def _compute_failure_signature(state_patch: Dict[str, Any]) -> str:
    """Create a stable signature for failed runtime/test outcomes."""
    tests_passed = bool(state_patch.get("tests_passed", False))
    if tests_passed:
        return ""

    test_results = state_patch.get("test_results", {}) if isinstance(state_patch.get("test_results"), dict) else {}
    exec_errors = test_results.get("execution_errors", [])
    if not isinstance(exec_errors, list):
        exec_errors = [str(exec_errors)] if exec_errors else []

    smoke_errors = test_results.get("smoke_test_errors", [])
    if not isinstance(smoke_errors, list):
        smoke_errors = [str(smoke_errors)] if smoke_errors else []

    feature_summary = (test_results.get("feature_verification", {}) or {}).get("summary", {})
    feature_pass_rate = feature_summary.get("pass_rate", 0)

    payload = {
        "stage": str(state_patch.get("current_stage", "")),
        "verification_state": str(test_results.get("verification_state", "")),
        "exec_errors": [str(e).strip()[:240] for e in exec_errors[:10]],
        "smoke_errors": [str(e).strip()[:240] for e in smoke_errors[:10]],
        "feature_pass_rate": float(feature_pass_rate or 0),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8", errors="replace")).hexdigest()


def _update_failure_signature_tracking(
    previous_state: Dict[str, Any],
    node_state: Dict[str, Any],
    node_name: str,
) -> Dict[str, Any]:
    """Track repeated failures and trigger summarize_now when loop stagnates."""
    tracked_nodes = {"code_testing", "feature_verification", "smoke_test"}
    if node_name not in tracked_nodes:
        return node_state

    signature = _compute_failure_signature(node_state)
    prev_signature = str(previous_state.get("_last_failure_signature", "") or "")
    prev_streak = int(previous_state.get("_failure_signature_streak", 0) or 0)

    if not signature:
        node_state["_last_failure_signature"] = ""
        node_state["_failure_signature_streak"] = 0
        return node_state

    streak = prev_streak + 1 if signature == prev_signature else 1
    node_state["_last_failure_signature"] = signature
    node_state["_failure_signature_streak"] = streak

    if streak >= 2:
        node_state["summarize_now"] = True
        node_state["warnings"] = list(node_state.get("warnings", [])) + [
            f"Repeated failure signature detected at {node_name} (streak={streak}); forcing summarize_now compaction."
        ]
    return node_state


def _with_execution_policy(node_name: str, node_fn):
    """Wrap heavy nodes with resource gating and budget tracking."""

    def _resolve_effective_policy(base_policy: Dict[str, Any]) -> Dict[str, Any]:
        """Allow per-run policy overrides via environment variables.

        Research-heavy runs can raise budgets without editing code:
          AUTOGIT_RESEARCH_HARD_TIMEOUT_S
          AUTOGIT_RESEARCH_SOFT_BUDGET_S
          AUTOGIT_RESEARCH_RESOURCE_WAIT_TIMEOUT_S
        """
        effective = dict(base_policy or {})
        gate = dict(effective.get("resource_gate") or {})

        if node_name == "research":
            hard_override = str(os.environ.get("AUTOGIT_RESEARCH_HARD_TIMEOUT_S", "")).strip()
            soft_override = str(os.environ.get("AUTOGIT_RESEARCH_SOFT_BUDGET_S", "")).strip()
            wait_override = str(os.environ.get("AUTOGIT_RESEARCH_RESOURCE_WAIT_TIMEOUT_S", "")).strip()

            if hard_override.isdigit() and int(hard_override) > 0:
                effective["hard_timeout_s"] = int(hard_override)
            if soft_override.isdigit() and int(soft_override) > 0:
                effective["soft_budget_s"] = int(soft_override)
            if wait_override.isdigit() and int(wait_override) >= 0:
                gate["wait_timeout"] = int(wait_override)

        if gate:
            effective["resource_gate"] = gate
        return effective

    async def _wrapped(state: AutoGITState) -> Dict[str, Any]:
        policy = _resolve_effective_policy(_NODE_EXECUTION_POLICY.get(node_name, {}))
        monitor = get_monitor()
        resource_gate = policy.get("resource_gate") or {}
        resource_events = []
        warnings = []
        policy_events: List[Dict[str, Any]] = []
        resource_snapshot = None
        waited_s = 0.0
        working_state: AutoGITState = dict(state)
        reusable_nodes = {
            "code_testing": "full",
            "feature_verification": "runtime",
            "smoke_test": "runtime",
        }
        fp_mode = reusable_nodes.get(node_name)
        artifact_fp = _compute_generated_artifact_fingerprint(working_state, mode=fp_mode) if fp_mode else ""

        # Pre-node governance: cap fan-out and enforce trust policy/HITL rules.
        fanout_updates = _apply_stage_fanout_caps(state, node_name)
        if fanout_updates:
            working_state.update({k: v for k, v in fanout_updates.items() if k not in {"warnings", "policy_events"}})
            warnings.extend(fanout_updates.get("warnings", []))
            policy_events.extend(fanout_updates.get("policy_events", []))

        # Pre-node payload compaction for reasoning/fix nodes to prevent
        # request-size failures on cloud providers.
        if node_name in {"strategy_reasoner", "code_fixing"}:
            working_state = _trim_reasoning_payload(working_state)

        policy_eval = _evaluate_execution_policy(working_state, node_name)
        if policy_eval.get("blocked"):
            blocked_result = dict(policy_eval.get("result") or {})
            blocked_result["node_budget_report"] = _append_budget_report(
                state,
                node_name,
                0.0,
                policy,
                resource_snapshot=resource_snapshot,
                waited_s=waited_s,
                timed_out=False,
                timeout_source="none",
            )
            blocked_result = _update_loop_detection_state(state, node_name, blocked_result)
            blocked_result = _update_pipeline_todos(state, node_name, blocked_result)
            return blocked_result

        # SOTA throughput optimization: skip expensive validation/smoke nodes when
        # generated artifacts are unchanged and prior node result is reusable.
        node_cache = state.get("_node_result_cache") if isinstance(state.get("_node_result_cache"), dict) else {}
        cached_entry = node_cache.get(node_name) if isinstance(node_cache, dict) else None
        if fp_mode and artifact_fp and isinstance(cached_entry, dict):
            if cached_entry.get("artifact_fp") == artifact_fp and isinstance(cached_entry.get("result"), dict):
                reused = dict(cached_entry.get("result") or {})
                reused.pop("node_budget_report", None)
                reused["node_budget_report"] = _append_budget_report(
                    state,
                    node_name,
                    0.0,
                    policy,
                    resource_snapshot=resource_snapshot,
                    waited_s=waited_s,
                    timed_out=False,
                    timeout_source="none",
                )
                reused["warnings"] = list(reused.get("warnings", [])) + [
                    f"{node_name} reused cached result (generated artifacts unchanged)."
                ]
                reused = _update_loop_detection_state(state, node_name, reused)
                reused = _update_pipeline_todos(state, node_name, reused)
                reused = _coerce_list_shape(reused)
                return reused

        if resource_gate:
            try:
                resource_eval = monitor.evaluate_resources(
                    max_cpu_percent=resource_gate.get("max_cpu_percent", 90.0),
                    max_ram_percent=resource_gate.get("max_ram_percent", 85.0),
                    max_vram_percent=resource_gate.get("max_vram_percent", 85.0),
                    min_free_ram_gb=resource_gate.get("min_free_ram_gb", 0.0),
                    min_free_vram_mb=resource_gate.get("min_free_vram_mb", 0.0),
                )
            except Exception:
                resource_eval = {"safe": True, "reasons": [], "stats": {}}
            resource_snapshot = resource_eval.get("stats")
            if not resource_eval.get("safe", True):
                wait_timeout = int(resource_gate.get("wait_timeout", 0) or 0)
                if wait_timeout > 0:
                    wait_start = time.monotonic()
                    monitor.wait_for_resources(
                        timeout=wait_timeout,
                        poll_interval=2.0,
                        max_cpu_percent=resource_gate.get("max_cpu_percent", 90.0),
                        max_ram_percent=resource_gate.get("max_ram_percent", 85.0),
                        max_vram_percent=resource_gate.get("max_vram_percent", 85.0),
                        min_free_ram_gb=resource_gate.get("min_free_ram_gb", 0.0),
                        min_free_vram_mb=resource_gate.get("min_free_vram_mb", 0.0),
                        quiet=True,
                    )
                    waited_s = time.monotonic() - wait_start
                    resource_snapshot = monitor.get_stats_snapshot()
                wait_msg = (
                    f"Resource gate activated before {node_name}: "
                    f"{'; '.join(resource_eval.get('reasons', [])) or 'resource pressure detected'}"
                )
                warnings.append(wait_msg)
                resource_events.append({
                    "node": node_name,
                    "event": "resource_gate",
                    "waited_s": round(waited_s, 3),
                    "reasons": resource_eval.get("reasons", []),
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                })

        start = time.monotonic()
        failover_token = None
        try:
            failover_token = set_runtime_failover_profile(working_state.get("model_failover_profile", "balanced"))
            result = node_fn(working_state)
            if asyncio.iscoroutine(result):
                hard_timeout_s = policy.get("hard_timeout_s")
                if hard_timeout_s:
                    result = await asyncio.wait_for(result, timeout=hard_timeout_s)
                else:
                    result = await result
            reset_runtime_failover_profile(failover_token)
        except asyncio.TimeoutError:
            reset_runtime_failover_profile(failover_token)
            hard_timeout_s = policy.get("hard_timeout_s")
            warning = f"{node_name} exceeded hard timeout of {hard_timeout_s}s; using fallback path"
            fallback = _build_timeout_fallback(node_name, warning)
            timeout_source = "policy_hard_timeout"
            fallback["timeout_source"] = timeout_source
            fallback["node_budget_report"] = _append_budget_report(
                state,
                node_name,
                float(hard_timeout_s or 0),
                policy,
                resource_snapshot=resource_snapshot,
                waited_s=waited_s,
                timed_out=True,
                timeout_source=timeout_source,
            )
            fallback = _update_loop_detection_state(state, node_name, fallback)
            fallback = _update_pipeline_todos(state, node_name, fallback)
            return fallback
        except Exception as exc:
            reset_runtime_failover_profile(failover_token)
            err_msg = f"{type(exc).__name__}: {exc}"
            remediation = "Inspect structured_errors payload and stage logs, then retry with reduced scope."
            fallback = {
                "current_stage": f"{node_name}_failed",
                "errors": [f"{node_name} failed: {err_msg}"],
                "warnings": [f"Unhandled exception in {node_name}; emitted structured error envelope"],
                "timeout_source": "node_exception",
                "structured_errors": [
                    _structured_error_envelope(
                        node_name=node_name,
                        stage=f"{node_name}_failed",
                        error_code="NODE_EXECUTION_ERROR",
                        root_cause=err_msg,
                        remediation=remediation,
                        retryable=node_name not in {"git_publishing"},
                    )
                ],
            }
            fallback["node_budget_report"] = _append_budget_report(
                state,
                node_name,
                time.monotonic() - start,
                policy,
                resource_snapshot=resource_snapshot,
                waited_s=waited_s,
                timed_out=False,
                timeout_source="node_exception",
            )
            fallback = _update_loop_detection_state(state, node_name, fallback)
            fallback = _update_pipeline_todos(state, node_name, fallback)
            return fallback

        elapsed_s = time.monotonic() - start
        result = dict(result or {})
        timeout_source = _classify_timeout_source(result, elapsed_s, policy, timed_out=False)
        result["timeout_source"] = timeout_source
        result["node_budget_report"] = _append_budget_report(
            state,
            node_name,
            elapsed_s,
            policy,
            resource_snapshot=resource_snapshot,
            waited_s=waited_s,
            timed_out=False,
            timeout_source=timeout_source,
        )

        hard_timeout_s = float(policy.get("hard_timeout_s") or 0)
        if hard_timeout_s > 0 and elapsed_s > hard_timeout_s + 5:
            overrun_warning = (
                f"{node_name} elapsed {elapsed_s:.1f}s exceeded hard timeout envelope {hard_timeout_s}s by >5s"
            )
            warnings.append(overrun_warning)
            resource_events.append({
                "node": node_name,
                "event": "hard_timeout_overrun",
                "elapsed_s": round(elapsed_s, 3),
                "hard_timeout_s": hard_timeout_s,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            })
            structured_errors = result.get("structured_errors")
            if not isinstance(structured_errors, list):
                structured_errors = []
            structured_errors.append(
                _structured_error_envelope(
                    node_name=node_name,
                    stage=f"{node_name}_timeout_overrun",
                    error_code="NODE_TIMEOUT_OVERRUN",
                    root_cause=overrun_warning,
                    remediation="Inspect node-internal await points and provider latency; preserve timeout_source metadata.",
                    retryable=True,
                )
            )
            result["structured_errors"] = structured_errors
            result["timeout_source"] = "cancellation_delay"
            result["timeout_fallback"] = {
                "applied": True,
                "source": "cancellation_delay",
                "elapsed_s": round(elapsed_s, 3),
                "effective_hard_timeout_s": hard_timeout_s,
            }

        soft_budget_s = policy.get("soft_budget_s")
        if soft_budget_s and elapsed_s > soft_budget_s:
            slow_msg = f"{node_name} exceeded soft budget ({elapsed_s:.1f}s > {soft_budget_s}s)"
            warnings.append(slow_msg)
            resource_events.append({
                "node": node_name,
                "event": "soft_budget_exceeded",
                "elapsed_s": round(elapsed_s, 3),
                "soft_budget_s": soft_budget_s,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            })

        if warnings:
            result["warnings"] = list(result.get("warnings", [])) + warnings
        if resource_events:
            result["resource_events"] = resource_events
        if policy_events:
            result["policy_events"] = list(result.get("policy_events", [])) + policy_events

        result = _update_loop_detection_state(state, node_name, result)

        result = _update_pipeline_todos(state, node_name, result)

        # Explicit summarize trigger for long fix loops.
        if bool(state.get("summarize_now", False)):
            try:
                from ..utils.middleware import run_state_compaction
                compacted = run_state_compaction({**state, **result})
                if compacted:
                    result.update(compacted)
                result["summarize_now"] = False
                result["warnings"] = list(result.get("warnings", [])) + [
                    "Explicit summarize_now trigger applied; context was compacted."
                ]
            except Exception:
                pass

        # ── Middleware: Context Compaction (post-node) ────────────────
        # After certain heavy nodes, trim bloated append-only state fields
        # to prevent context rot. Only runs on nodes that produce lots of
        # accumulated errors/warnings/diffs.
        # Inspired by Deep Agents' SummarizationMiddleware + ContextEditingMiddleware.
        _COMPACTION_NODES = {"code_fixing", "code_testing", "feature_verification", "smoke_test"}
        if node_name in _COMPACTION_NODES:
            try:
                from ..utils.middleware import run_state_compaction
            except ImportError:
                try:
                    from src.utils.middleware import run_state_compaction
                except ImportError:
                    run_state_compaction = None  # type: ignore
            if run_state_compaction is not None:
                # Merge current node result with existing state for compaction analysis
                _merged_for_compact = dict(state)
                _merged_for_compact.update(result)
                compacted = run_state_compaction(_merged_for_compact)
                if compacted:
                    result.update(compacted)
                    logger.info(f"  📦 Context compaction after {node_name}: trimmed {list(compacted.keys())}")
        # ── End Context Compaction ────────────────────────────────────

        # Context offload + todo restoration middleware.
        try:
            offload_updates = offload_state_fields(result, node_name=node_name)
            if offload_updates:
                result.update(offload_updates)

            compacted_todos = compact_todos_with_pointer(result.get("pipeline_todos", []))
            if compacted_todos:
                result.update(compacted_todos)

            restored = restore_todo_context_if_missing({**state, **result})
            if restored:
                result.update(restored)
        except Exception:
            # Offload must be best-effort and never affect node outcomes.
            pass

        # Persist reusable node outputs keyed by generated artifact fingerprint.
        if fp_mode and artifact_fp:
            cache_store = dict(node_cache) if isinstance(node_cache, dict) else {}
            cache_result = dict(result)
            cache_result.pop("node_budget_report", None)
            cache_result.pop("resource_events", None)
            cache_result.pop("policy_events", None)
            cache_store[node_name] = {
                "artifact_fp": artifact_fp,
                "result": cache_result,
            }
            result["_node_result_cache"] = cache_store

        # Detect fix-loop stagnation: unchanged generated artifacts across repeated
        # code_fixing passes while tests are still failing. Escalate to regeneration.
        if node_name == "code_fixing":
            merged_for_fp = dict(state)
            merged_for_fp.update(result)
            fix_fp = _compute_generated_artifact_fingerprint(merged_for_fp, mode="runtime")
            prev_fix_fp = str(state.get("_last_fix_artifact_fp", "") or "")
            prev_fix_streak = int(state.get("_fix_stagnation_streak", 0) or 0)
            same_fp = bool(fix_fp and prev_fix_fp and fix_fp == prev_fix_fp)
            fix_streak = prev_fix_streak + 1 if same_fp else 0
            result["_last_fix_artifact_fp"] = fix_fp
            result["_fix_stagnation_streak"] = fix_streak

            if fix_streak >= 2 and not bool(merged_for_fp.get("tests_passed", False)):
                result["current_stage"] = "fix_stagnated"
                result["warnings"] = list(result.get("warnings", [])) + [
                    "Code fixing stagnated (artifacts unchanged across retries); routing to regeneration."
                ]

        result = _coerce_list_shape(result)
        return result

    return _wrapped


def _route_after_code_testing(state: AutoGITState) -> Literal["verify", "fix"]:
    """Route after code_testing to avoid unnecessary verification hops when base tests fail."""
    tests_passed = bool(state.get("tests_passed", False))
    stage = str(state.get("current_stage", "") or "")
    generated_code = state.get("generated_code") if isinstance(state.get("generated_code"), dict) else {}
    files = generated_code.get("files", {}) if isinstance(generated_code, dict) else {}

    # Preserve existing no-file behavior: let downstream should_fix_code handle it.
    if not isinstance(files, dict) or not files or stage == "testing_skipped":
        return "verify"

    if tests_passed:
        return "verify"

    logger.info("   code_testing failed base checks — routing directly to strategy_reasoner")
    return "fix"


def _route_after_fixing(state: AutoGITState) -> Literal["review", "retest", "smoke", "regenerate"]:
    """Route after code_fixing; extracted for direct unit coverage."""
    stage = state.get("current_stage", "")
    quality_gate = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}
    if bool(quality_gate.get("contradiction_detected", False)):
        reason = "quality_gate contradiction_detected=True after code_fixing"
        logger.error("PHASE_LOCK_VIOLATION: %s", reason)
        _append_phase_gate_rejection(state, "_after_fixing", "retest", reason)
        return "retest"

    if stage == "fix_stagnated":
        logger.warning("   code_fixing stagnated (no artifact change) — routing to code_generation")
        _append_phase_gate_rejection(state, "_after_fixing", "regenerate", "fix_stagnated")
        return "regenerate"

    if stage in ("no_errors_to_fix", "fixing_failed", "fixing_error"):
        logger.info(f"   code_fixing returned '{stage}' — nothing fixed, routing to smoke_test for runtime check")
        _append_phase_gate_rejection(state, "_after_fixing", "smoke", f"stage={stage}")
        return "smoke"

    fix_attempts = state.get("fix_attempts", 0)
    if fix_attempts <= 1 and state.get("fix_review_required", False):
        logger.info("   First fix cycle → routing through code_review_agent")
        return "review"

    if fix_attempts <= 1:
        logger.info("   First fix cycle but only deterministic/local fixes applied → skipping deep review")
    return "retest"


def _route_after_smoke_test(state: AutoGITState) -> Literal["fix", "eval"]:
    """Route after smoke_test; extracted for direct unit coverage."""
    smoke = state.get("smoke_test") or {}
    stage = state.get("current_stage", "")
    fix_attempts = state.get("fix_attempts", 0)
    max_attempts = state.get("max_fix_attempts", 8)
    quality_gate = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}

    if bool(quality_gate.get("contradiction_detected", False)):
        reason = "quality_gate contradiction_detected=True after smoke_test"
        logger.error("PHASE_LOCK_VIOLATION: %s", reason)
        _append_phase_gate_rejection(state, "_after_smoke_test", "fix", reason)
        return "fix"

    if smoke.get("passed", False) or stage == "smoke_test_passed":
        return "eval"

    if fix_attempts < max_attempts:
        logger.info(f"   🔬 Smoke test FAILED → routing to fix loop (attempt {fix_attempts+1}/{max_attempts})")
        _append_phase_gate_rejection(state, "_after_smoke_test", "fix", "smoke test failed")
        return "fix"

    logger.warning(f"   🔬 Smoke test failed but fix budget exhausted ({fix_attempts}/{max_attempts}) — proceeding to eval")
    _append_phase_gate_rejection(
        state,
        "_after_smoke_test",
        "eval",
        f"smoke test failed with exhausted fix budget ({fix_attempts}/{max_attempts})",
    )
    return "eval"


def build_workflow() -> StateGraph:
    """Build the LangGraph StateGraph workflow with all nodes"""
    workflow = StateGraph(AutoGITState)
    
    # Add nodes — S26: ALL nodes now wrapped with execution policy (timeout + resource gate)
    workflow.add_node("requirements_extraction", _with_execution_policy("requirements_extraction", requirements_extraction_node))
    workflow.add_node("research", _with_execution_policy("research", research_node))
    workflow.add_node("generate_perspectives", _with_execution_policy("generate_perspectives", generate_perspectives_node))
    workflow.add_node("problem_extraction", _with_execution_policy("problem_extraction", problem_extraction_node))
    workflow.add_node("solution_generation", _with_execution_policy("solution_generation", solution_generation_node))
    workflow.add_node("critique", _with_execution_policy("critique", critique_node))
    workflow.add_node("consensus_check", _with_execution_policy("consensus_check", consensus_check_node))
    workflow.add_node("solution_selection", _with_execution_policy("solution_selection", solution_selection_node))
    workflow.add_node("architect_spec", _with_execution_policy("architect_spec", architect_spec_node))
    workflow.add_node("code_generation", _with_execution_policy("code_generation", code_generation_node))
    workflow.add_node("code_review_agent", _with_execution_policy("code_review_agent", code_review_agent_node))
    workflow.add_node("code_testing", _with_execution_policy("code_testing", code_testing_node))
    workflow.add_node("feature_verification", _with_execution_policy("feature_verification", feature_verification_node))
    workflow.add_node("strategy_reasoner", _with_execution_policy("strategy_reasoner", strategy_reasoner_node))
    workflow.add_node("code_fixing", _with_execution_policy("code_fixing", code_fixing_node))
    workflow.add_node("smoke_test", _with_execution_policy("smoke_test", smoke_test_node))
    workflow.add_node("pipeline_self_eval", _with_execution_policy("pipeline_self_eval", pipeline_self_eval_node))
    workflow.add_node("goal_achievement_eval", _with_execution_policy("goal_achievement_eval", goal_achievement_eval_node))
    workflow.add_node("git_publishing", _with_execution_policy("git_publishing", git_publishing_node))
    
    # Define the flow
    workflow.set_entry_point("requirements_extraction")
    workflow.add_edge("requirements_extraction", "research")
    workflow.add_edge("research", "generate_perspectives")
    workflow.add_edge("generate_perspectives", "problem_extraction")
    workflow.add_edge("problem_extraction", "solution_generation")
    workflow.add_edge("solution_generation", "critique")
    workflow.add_edge("critique", "consensus_check")
    
    # Conditional routing from consensus_check
    workflow.add_conditional_edges(
        "consensus_check",
        should_continue_debate,
        {
            "continue": "solution_generation",
            "select": "solution_selection"
        }
    )
    
    # Final flow with self-healing loop
    workflow.add_edge("solution_selection", "architect_spec")
    workflow.add_edge("architect_spec", "code_generation")
    workflow.add_edge("code_generation", "code_review_agent")
    workflow.add_edge("code_review_agent", "code_testing")
    
    # TDD loop gate: if base tests fail, route directly to strategy/fix loop;
    # only run feature verification on a passing baseline.
    workflow.add_conditional_edges(
        "code_testing",
        _route_after_code_testing,
        {
            "verify": "feature_verification",
            "fix": "strategy_reasoner",
        }
    )
    
    # Conditional: if tests/features fail, reason about WHY then fix; if pass, go to smoke test
    workflow.add_conditional_edges(
        "feature_verification",
        should_fix_code,
        {
            "fix": "strategy_reasoner",    # reason first, then fix
            "publish": "smoke_test"        # S22: smoke test before eval
        }
    )

    # Strategy reasoner always flows into code_fixing
    workflow.add_edge("strategy_reasoner", "code_fixing")

    workflow.add_conditional_edges(
        "code_fixing",
        _route_after_fixing,
        {
            "review": "code_review_agent",   # first fix cycle: review for fix-introduced bugs
            "retest": "code_testing",         # subsequent cycles: skip review for speed
            "smoke": "smoke_test",            # S23: nothing to fix → still runtime-verify
            "regenerate": "code_generation",  # stagnation escape hatch
        }
    )

    workflow.add_conditional_edges(
        "smoke_test",
        _route_after_smoke_test,
        {
            "fix": "strategy_reasoner",
            "eval": "pipeline_self_eval",
        }
    )

    # Self-eval: approved → goal eval; needs_work → reason + fix again
    workflow.add_conditional_edges(
        "pipeline_self_eval",
        should_regen_or_publish,
        {
            "fix": "strategy_reasoner",   # reason before fixing on self-eval too
            "publish": "goal_achievement_eval",
        }
    )

    workflow.add_conditional_edges(
        "goal_achievement_eval",
        should_publish_after_goal_eval,
        {
            "fix": "strategy_reasoner",
            "publish": "git_publishing",
        }
    )
    
    workflow.add_edge("git_publishing", END)
    
    return workflow


def compile_workflow() -> StateGraph:
    """Compile the workflow with memory persistence"""
    workflow = build_workflow()
    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        debug=False
    )


def _enforce_telemetry_parity(parity: Dict[str, Any], node_name: str, mode: str) -> Optional[str]:
    """Apply parity policy; return warning text or raise in strict mode."""
    if parity.get("ok", True):
        return None

    mismatch_preview = "; ".join((parity.get("mismatches") or [])[:3]) or "unknown mismatch"
    message = f"Telemetry parity mismatch at {node_name}: {mismatch_preview}"

    if mode == "strict":
        raise RuntimeError(message)
    return message


def _normalize_trust_mode(mode: str) -> str:
    """Normalize trust mode to trusted|constrained|untrusted with safe fallback."""
    normalized = str(mode or "trusted").strip().lower()
    if normalized not in {"trusted", "constrained", "untrusted"}:
        return "trusted"
    return normalized


def _normalize_allowlist_mode(mode: str) -> str:
    """Normalize allowlist mode to permissive|strict with safe fallback."""
    normalized = str(mode or "permissive").strip().lower()
    if normalized not in {"permissive", "strict"}:
        return "permissive"
    return normalized


def _normalize_failover_profile(profile: str) -> str:
    """Normalize failover profile to supported values with safe fallback."""
    normalized = str(profile or "balanced").strip().lower()
    if normalized not in {"balanced", "resilient", "cost_saver"}:
        return "balanced"
    return normalized


def _normalize_telemetry_parity_mode(mode: str) -> str:
    """Normalize telemetry parity mode to warn|strict with safe fallback."""
    normalized = str(mode or "warn").strip().lower()
    if normalized not in {"warn", "strict"}:
        return "warn"
    return normalized


async def run_auto_git_pipeline(
    idea: str,
    user_requirements: str = None,
    requirements: Dict[str, Any] = None,  # Structured requirements from conversation
    use_web_search: bool = True,
    max_debate_rounds: int = 5,
    min_consensus_score: float = 0.7,
    auto_publish: bool = False,
    output_dir: Optional[str] = None,
    stop_after: Optional[str] = None,
    thread_id: str = "default",
    interactive: bool = True,
    resume: bool = True,
    checkpointer_provider: Optional[str] = None,
    trust_mode: str = "trusted",
    tool_allowlist_mode: str = "permissive",
    hitl_decisions: Optional[Dict[str, str]] = None,
    model_failover_profile: str = "balanced",
    telemetry_parity_mode: str = "warn",
) -> AutoGITState:
    """
    Run the complete Auto-GIT pipeline with progress monitoring
    
    Args:
        idea: Research idea or topic
        user_requirements: Optional additional requirements
        requirements: Structured requirements from conversation agent (IMPORTANT!)
        use_web_search: Enable web search
        max_debate_rounds: Maximum debate rounds
        min_consensus_score: Minimum consensus score (0-1)
        auto_publish: Automatically publish to GitHub
        output_dir: Output directory for generated code
        stop_after: Stop after this node (for testing)
        thread_id: Thread ID for checkpointing
        resume: If True (default) and a prior checkpoint exists for thread_id,
                resume from the last completed node instead of starting fresh.
                Set to False to force a clean run (existing checkpoint is kept
                but ignored; new checkpoints overwrite it for this thread_id).
        
    Returns:
        Final state after pipeline execution
    """
    monitor = get_monitor()
    if not monitor.monitoring:
        monitor.start()
    run_started_at = __import__("datetime").datetime.now().isoformat()
    
    # Create initial state
    initial_state = create_initial_state(
        idea=idea,
        user_requirements=user_requirements,
        requirements=requirements,  # Pass requirements to state
        use_web_search=use_web_search,
        max_rounds=max_debate_rounds,
        min_consensus=min_consensus_score
    )
    
    # Add flags to state
    initial_state["auto_publish"] = auto_publish
    initial_state["output_dir"] = output_dir or "output"
    initial_state["trust_mode"] = _normalize_trust_mode(trust_mode)
    initial_state["tool_allowlist_mode"] = _normalize_allowlist_mode(tool_allowlist_mode)
    initial_state["hitl_decisions"] = dict(hitl_decisions or {})
    initial_state["checkpointer_provider"] = str(checkpointer_provider or os.getenv("AUTOGIT_CHECKPOINTER_PROVIDER", "sqlite"))
    initial_state["model_failover_profile"] = _normalize_failover_profile(model_failover_profile)
    initial_state["telemetry_parity_mode"] = _normalize_telemetry_parity_mode(telemetry_parity_mode)
    parity_mode = initial_state["telemetry_parity_mode"]

    local_models_disabled = str(os.getenv("AUTOGIT_DISABLE_LOCAL_MODELS", "")).strip().lower() in {"1", "true", "yes", "on"}
    if local_models_disabled and not _cloud_provider_available():
        raise RuntimeError(
            "Cloud-only mode is enabled (AUTOGIT_DISABLE_LOCAL_MODELS=true) but no cloud LLM keys are configured. "
            "Set at least one of OPENROUTER_API_KEY, GROQ_API_KEY, GROQ_API_KEY_1..7, OPENAI_API_KEY, or GLM_API_KEY."
        )
    
    # ── Checkpointer provider abstraction (sqlite/memory/local/redis) ────────
    bundle = create_checkpointer(provider=checkpointer_provider, logs_dir="logs")
    checkpointer = bundle.checkpointer

    config = {
        "configurable": {
            "thread_id": thread_id
        },
        "recursion_limit": 200,  # Raised for max-quality run
    }

    # Build workflow with disk-persistent checkpointer
    workflow = build_workflow().compile(checkpointer=checkpointer, debug=False)

    # Detect prior checkpoint for this thread → resume vs fresh start
    existing_checkpoint = load_existing_checkpoint(checkpointer, config)
    if resume and existing_checkpoint is not None:
        console.print(Panel(
            f"[bold green]\u267b\ufe0f  Resuming from last checkpoint[/bold green]\n"
            f"Thread : [cyan]{thread_id}[/cyan]\n"
            f"Provider: [cyan]{bundle.provider}[/cyan]\n"
            f"Store   : [dim]{bundle.location}[/dim]\n\n"
            f"[dim]Pass resume=False to force a fresh run.[/dim]",
            title="Resume Mode", border_style="green",
        ))
        astream_input: Optional[AutoGITState] = None  # LangGraph resumes from saved state
    else:
        if resume:
            console.print(f"[dim]No checkpoint found for thread '{thread_id}' — starting fresh.[/dim]")
        astream_input = initial_state
    
    # Pipeline stages for progress tracking
    stages = [
        ("requirements_extraction", "📋 Extracting requirements..."),
        ("research", "🔍 SOTA research (compound-beta web search)..."),
        ("generate_perspectives", "🧠 Generating domain-specific experts..."),
        ("problem_extraction", "🎯 Extracting research problems..."),
        ("solution_generation", "💡 Generating solutions (Round {})..."),
        ("critique", "🔍 Cross-perspective review..."),
        ("consensus_check", "⚖️  Checking consensus..."),
        ("solution_selection", "🏆 Selecting best solution..."),
        ("architect_spec",    "📐 Designing technical architecture..."),
        ("code_generation",   "💻 Generating implementation code..."),
        ("code_review_agent", "🔍 Deep code review..."),
        ("code_testing",      "🧪 Testing code..."),
        ("feature_verification", "🔍 Verifying features in sandbox..."),
        ("strategy_reasoner", "🧠 Reasoning about failures..."),
        ("code_fixing",       "🔧 Auto-fixing issues..."),
        ("smoke_test",        "🔬 Smoke testing in isolated venv..."),
        ("pipeline_self_eval","🔬 Self-evaluating quality..."),
        ("goal_achievement_eval", "🎯 Evaluating goal achievement..."),
        ("git_publishing",    "📤 Publishing to GitHub..."),
    ]
    
    try:
        # Progress bar setup
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            main_task = progress.add_task("[cyan]Pipeline Progress", total=len(stages))
            
            final_state = None
            accumulated_state = {}  # Track full state across all node outputs
            current_round = 1
            visited_nodes = set()

            # ── Observability tracer (writes logs/pipeline_trace_*.jsonl + agent_status_*.md) ──
            tracer = PipelineTracer(logs_dir="logs", idea=idea, thread_id=thread_id)

            # ── Lightweight progress heartbeat (survives terminal deletion) ──
            _progress_path = os.path.join("logs", "pipeline_progress.txt")
            def _write_progress(msg: str):
                import time as _t
                line = f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] {msg}\n"
                try:
                    with open(_progress_path, "a", encoding="utf-8") as _f:
                        _f.write(line)
                except Exception:
                    pass
            _write_progress("workflow astream starting…")

            async for state in workflow.astream(astream_input, config):
                for node_name, node_state in state.items():
                    if isinstance(node_state, dict):
                        node_state = _coerce_list_shape(dict(node_state))
                    
                    # Update progress
                    current_stage = node_state.get("current_stage", "")
                    
                    # Track rounds
                    if node_name == "solution_generation" and node_name in visited_nodes:
                        current_round += 1
                    
                    visited_nodes.add(node_name)

                    # Truth-first correctness snapshot for every node emission.
                    node_state = _apply_quality_contract(node_state, terminal=False)
                    
                    # Find matching stage
                    for stage_name, stage_desc in stages:
                        if stage_name == node_name:
                            desc = stage_desc.format(current_round) if '{}' in stage_desc else stage_desc
                            progress.update(main_task, description=f"[cyan]{desc}")
                            progress.advance(main_task, 0.5)
                            break
                    
                    # Display inter-stage results
                    if node_name == "research" and current_stage == "research_complete":
                        display_research_results(node_state)
                    
                    elif node_name == "problem_extraction" and current_stage == "problems_extracted":
                        display_problems(node_state)
                    
                    elif node_name == "critique" and current_stage == "critiques_complete":
                        display_debate_round(node_state)
                    
                    elif node_name == "solution_selection" and current_stage == "solution_selected":
                        display_final_solution(node_state)
                    
                    elif node_name == "code_generation" and current_stage == "code_generated":
                        display_generated_code(node_state)
                    
                    elif node_name == "code_testing" and current_stage == "testing_complete":
                        tests_passed = display_test_results(node_state)

                        if not tests_passed:
                            fix_attempts = node_state.get("fix_attempts", 0)
                            max_attempts = node_state.get("max_fix_attempts", 8)
                            console.print(f"[dim]Fix attempt {fix_attempts}/{max_attempts} — auto-continuing...[/dim]\n")
                    
                    elif node_name == "feature_verification":
                        fv_stage = node_state.get("current_stage", "")
                        if fv_stage == "feature_verification_complete":
                            fv_report = (node_state.get("test_results") or {}).get("feature_verification", {})
                            fv_summary = fv_report.get("summary", {})
                            fv_total = fv_summary.get("total", 0)
                            fv_passed = fv_summary.get("passed", 0)
                            fv_rate = fv_summary.get("pass_rate", 0)
                            if fv_rate >= 80:
                                console.print(f"[green]✅ Feature verification: {fv_passed}/{fv_total} passed ({fv_rate:.0f}%)[/green]")
                            elif fv_rate >= 50:
                                console.print(f"[yellow]⚠️  Feature verification: {fv_passed}/{fv_total} passed ({fv_rate:.0f}%)[/yellow]")
                            else:
                                console.print(f"[red]❌ Feature verification: {fv_passed}/{fv_total} passed ({fv_rate:.0f}%) — routing to fix[/red]")
                        elif fv_stage == "feature_verification_skipped":
                            console.print("[dim]Feature verification skipped[/dim]")
                    
                    elif node_name == "code_fixing" and current_stage == "code_fixed":
                        fix_attempts = node_state.get("fix_attempts", 0)
                        max_attempts = node_state.get("max_fix_attempts", 8)
                        console.print(f"\n[green]\u2705 Fix attempt {fix_attempts}/{max_attempts} completed. Re-testing...[/green]\n")
                        # No interactive prompt — max_fix_attempts cap stops the loop automatically.
                    
                    elif node_name == "pipeline_self_eval":
                        se_score = node_state.get("self_eval_score", -1)
                        se_stage = node_state.get("current_stage", "")
                        if se_stage == "self_eval_approved":
                            score_label = f"{se_score:.1f}/10" if se_score >= 0 else "skipped"
                            console.print(f"[bold green]\n\u2705 Self-eval approved (score {score_label})[/bold green]")
                        elif se_stage == "self_eval_needs_regen":
                            console.print(f"[bold yellow]\n⚠️  Self-eval score {se_score:.1f}/10 — triggering fix loop[/bold yellow]")

                    elif node_name == "git_publishing" and current_stage == "published":
                        display_github_result(node_state)
                    
                    # ── Trace this node completion ──────────────────────
                    tracer.on_node_complete(node_name, node_state)
                    _write_progress(f"NODE DONE: {node_name} → stage={current_stage}")

                    # Telemetry contract hardening: trace/status parity check.
                    _parity_state = dict(accumulated_state)
                    _parity_state.update(node_state)
                    _parity_state = _coerce_list_shape(_parity_state)
                    _status_correctness = _derive_correctness_snapshot(_parity_state)
                    _status_errors = _parity_state.get("errors", [])
                    if not isinstance(_status_errors, list):
                        _status_errors = []
                    _status_qg = _parity_state.get("quality_gate") if isinstance(_parity_state.get("quality_gate"), dict) else {}
                    _status_qg_hard = int(_status_qg.get("hard_failures_count", 0) or 0)
                    _status_node_calls = _parity_state.get("_node_exec_frequency", {})
                    if not isinstance(_status_node_calls, dict) or not _status_node_calls:
                        _status_node_calls = tracer.get_runtime_snapshot().get("node_calls", {})
                    _status_error_count = int(compute_error_count(_parity_state) or 0)
                    status_snapshot = {
                        "node_calls": _status_node_calls,
                        "current_stage": _parity_state.get("current_stage", ""),
                        "error_count": _status_error_count,
                    }
                    parity = tracer.validate_status_snapshot(status_snapshot)
                    parity["mode"] = parity_mode
                    parity_warning = _enforce_telemetry_parity(parity, node_name, parity_mode)
                    if parity_warning:
                        node_state.setdefault("warnings", [])
                        if isinstance(node_state["warnings"], list):
                            node_state["warnings"].append(parity_warning)
                    node_state["telemetry_parity"] = parity

                    node_state = _update_failure_signature_tracking(accumulated_state, node_state, node_name)

                    final_state = node_state
                    for _append_key in ("errors", "warnings", "debate_rounds", "resource_events", "agent_pool_log"):
                        _existing = accumulated_state.get(_append_key, [])
                        _new_items = node_state.pop(_append_key, [])
                        _cap = 800 if _append_key in {"errors", "warnings"} else 400
                        accumulated_state[_append_key] = _append_unique_capped(_existing, _new_items, cap=_cap)
                    accumulated_state.update(node_state)  # Merge remaining fields
                    accumulated_state = _coerce_list_shape(accumulated_state)

                    # Stop if requested
                    if stop_after and node_name == stop_after:
                        progress.update(main_task, completed=len(stages))
                        accumulated_state = _coerce_list_shape(accumulated_state)
                        accumulated_state = _apply_quality_contract(accumulated_state, terminal=False)
                        artifacts = _finalize_run_artifacts(
                            accumulated_state,
                            tracer=tracer,
                            thread_id=thread_id,
                            started_at=run_started_at,
                            persist_scorecard=False,
                        )
                        if artifacts.get("result_path"):
                            accumulated_state["run_result_path"] = artifacts["result_path"]
                        if artifacts.get("lineage_path"):
                            accumulated_state["run_lineage_manifest"] = artifacts["lineage_path"]
                        if artifacts.get("runtime_manifest_path"):
                            accumulated_state["run_runtime_manifest"] = artifacts["runtime_manifest_path"]
                        return accumulated_state

            progress.update(main_task, completed=len(stages))
            print_token_summary()
            accumulated_state = _coerce_list_shape(accumulated_state)
            accumulated_state = _apply_quality_contract(accumulated_state, terminal=True)
            artifacts = _finalize_run_artifacts(
                accumulated_state,
                tracer=tracer,
                thread_id=thread_id,
                started_at=run_started_at,
                persist_scorecard=True,
            )
            if artifacts.get("scorecard_path"):
                logger.info("Phase-gate scorecard saved to %s", artifacts["scorecard_path"])
            if artifacts.get("result_path"):
                logger.info("Run result snapshot saved to %s", artifacts["result_path"])
                accumulated_state["run_result_path"] = artifacts["result_path"]
            if artifacts.get("lineage_path"):
                logger.info("Run lineage manifest saved to %s", artifacts["lineage_path"])
                accumulated_state["run_lineage_manifest"] = artifacts["lineage_path"]
            if artifacts.get("runtime_manifest_path"):
                logger.info("Runtime manifest saved to %s", artifacts["runtime_manifest_path"])
                accumulated_state["run_runtime_manifest"] = artifacts["runtime_manifest_path"]
            _write_progress("PIPELINE COMPLETE ✅")
            return accumulated_state

    except Exception as e:
        console.print(f"\n[bold red]❌ Pipeline failed: {e}[/bold red]")
        print_token_summary()
        if 'tracer' in locals():
            failure_state = _coerce_list_shape(dict(locals().get('accumulated_state', {})))
            try:
                artifacts = _finalize_run_artifacts(
                    failure_state,
                    tracer=tracer,
                    thread_id=thread_id,
                    started_at=run_started_at,
                    persist_scorecard=False,
                )
                if artifacts.get("result_path"):
                    failure_state["run_result_path"] = artifacts["result_path"]
                if artifacts.get("lineage_path"):
                    failure_state["run_lineage_manifest"] = artifacts["lineage_path"]
                if artifacts.get("runtime_manifest_path"):
                    failure_state["run_runtime_manifest"] = artifacts["runtime_manifest_path"]
            except Exception:
                tracer.finish(failure_state)
        if '_write_progress' in locals():
            _write_progress(f"PIPELINE FAILED ❌: {type(e).__name__}: {e}")
        raise
    finally:
        if 'bundle' in locals() and getattr(bundle, "close", None):
            try:
                bundle.close()
            except Exception:
                pass
        if monitor.monitoring:
            monitor.stop()
