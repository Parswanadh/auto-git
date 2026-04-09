"""
Refine Node — Enhance an existing project through the pipeline.

Two modes:
  1. **User-directed**: user gives specific instructions ("add auth", "improve perf")
  2. **Auto-enhance**: pipeline researches best practices and applies them

Works on any directory — reads files via Workspace, produces a dict of
{filename: new_content} patches that can be written back.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

# ── Lazy LLM import ─────────────────────────────────────────────────────

def _get_llm(profile: str = "powerful"):
    """Get a cached LLM instance from model_manager (or fallback)."""
    try:
        from src.utils.model_manager import get_llm
        return get_llm(profile)
    except Exception:
        pass
    # Cloud fallback
    try:
        from src.llm.hybrid_router import get_llm as get_llm_router
        return get_llm_router(profile)
    except Exception:
        pass
    # Absolute fallback — raw OpenRouter via langchain
    _api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not _api_key:
        raise ValueError("No LLM API key available. Set OPENROUTER_API_KEY, GROQ_API_KEY, or configure Ollama.")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model="x-ai/grok-4.1-fast",
        api_key=_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.3,
    )


# ── Analysis functions ──────────────────────────────────────────────────

async def analyse_project(
    repo_map: str,
    full_context: str,
    user_request: str = "",
) -> Dict[str, Any]:
    """
    Use an LLM to produce a structured analysis of the project.
    Returns a dict with keys: strengths, weaknesses, suggestions, priority_files.
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = _get_llm("reasoning")

    system = (
        "You are a senior software architect performing a code review.\n"
        "Given a project's file map and source code, produce a JSON analysis:\n"
        '{"strengths": ["..."], "weaknesses": ["..."], "suggestions": ["..."], '
        '"priority_files": ["file.py", ...], "estimated_effort": "low|medium|high"}\n'
        "Focus on: correctness, performance, security, code quality, missing tests, "
        "documentation gaps, dependency issues.\n"
        "Reply with ONLY valid JSON, no markdown fences."
    )

    user_msg = f"PROJECT FILES:\n{repo_map}\n\n"
    if user_request:
        user_msg += f"USER REQUEST: {user_request}\n\n"
    user_msg += f"SOURCE CODE:\n{full_context[:80000]}"

    messages = [SystemMessage(content=system), HumanMessage(content=user_msg)]
    response = await llm.ainvoke(messages, timeout=120)
    text = response.content.strip()

    # Parse JSON
    import json
    try:
        # Strip markdown fences if present
        clean = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        clean = re.sub(r"```\s*$", "", clean, flags=re.MULTILINE)
        return json.loads(clean)
    except json.JSONDecodeError:
        return {
            "strengths": [],
            "weaknesses": [],
            "suggestions": [text[:500]],
            "priority_files": [],
            "estimated_effort": "unknown",
        }


async def plan_refinements(
    analysis: Dict[str, Any],
    repo_map: str,
    user_request: str = "",
) -> List[Dict[str, str]]:
    """
    Given analysis, produce a concrete list of file-level changes.

    Returns list of:
      {"file": "path.py", "action": "modify|create|delete", "description": "..."}
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    import json

    llm = _get_llm("reasoning")

    system = (
        "You are a senior developer planning code refinements.\n"
        "Given a project analysis and optionally a user request, produce a JSON "
        "array of planned changes:\n"
        '[{"file": "path/file.py", "action": "modify", "description": "Add input validation to handle_request()"}, ...]\n'
        "Actions: modify, create, delete.\n"
        "Order by priority (most impactful first). Max 15 changes.\n"
        "Reply with ONLY valid JSON array, no markdown fences."
    )

    user_msg = f"ANALYSIS:\n{json.dumps(analysis, indent=2)}\n\nFILES:\n{repo_map}\n"
    if user_request:
        user_msg += f"\nUSER REQUEST (high priority): {user_request}\n"

    messages = [SystemMessage(content=system), HumanMessage(content=user_msg)]
    response = await llm.ainvoke(messages, timeout=90)
    text = response.content.strip()

    try:
        clean = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        clean = re.sub(r"```\s*$", "", clean, flags=re.MULTILINE)
        plan = json.loads(clean)
        if isinstance(plan, list):
            return plan[:15]
    except json.JSONDecodeError:
        pass

    return [{"file": "unknown", "action": "modify", "description": text[:300]}]


async def generate_refined_file(
    file_path: str,
    original_content: str,
    change_description: str,
    repo_map: str,
    user_request: str = "",
    related_files: Dict[str, str] | None = None,
) -> str:
    """
    Generate the refined version of a single file.

    Returns the complete new file content.
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = _get_llm("powerful")

    system = (
        "You are an expert developer refining existing code.\n"
        "Given a file and a description of changes needed, produce the COMPLETE "
        "updated file content.\n\n"
        "Rules:\n"
        "- Output ONLY the file content, no markdown fences, no explanation.\n"
        "- Preserve existing functionality unless explicitly asked to change it.\n"
        "- Keep the same coding style and conventions.\n"
        "- Add docstrings/comments only where genuinely helpful.\n"
        "- Ensure all imports are correct.\n"
        "- Do not add unnecessary dependencies."
    )

    user_msg = f"FILE: {file_path}\n"
    user_msg += f"CHANGE NEEDED: {change_description}\n"
    if user_request:
        user_msg += f"USER REQUEST: {user_request}\n"
    user_msg += f"\nPROJECT STRUCTURE:\n{repo_map[:4000]}\n"

    if related_files:
        user_msg += "\nRELATED FILES (for cross-reference):\n"
        for rpath, rcontent in list(related_files.items())[:3]:
            user_msg += f"\n--- {rpath} ---\n{rcontent[:3000]}\n"

    user_msg += f"\nORIGINAL FILE CONTENT:\n{original_content}\n"

    messages = [SystemMessage(content=system), HumanMessage(content=user_msg)]
    response = await llm.ainvoke(messages, timeout=180)
    code = response.content.strip()

    # Strip markdown fences if the LLM wrapped them
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    return code


async def generate_new_file(
    file_path: str,
    description: str,
    repo_map: str,
    user_request: str = "",
    related_files: Dict[str, str] | None = None,
) -> str:
    """Generate a brand new file for the project."""
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = _get_llm("powerful")

    system = (
        "You are an expert developer creating a new file for an existing project.\n"
        "Generate the COMPLETE file content based on the description.\n\n"
        "Rules:\n"
        "- Output ONLY the file content, no markdown fences, no explanation.\n"
        "- Follow the project's existing coding style.\n"
        "- Import from project modules correctly.\n"
        "- Include proper docstrings."
    )

    user_msg = f"NEW FILE: {file_path}\nDESCRIPTION: {description}\n"
    if user_request:
        user_msg += f"USER REQUEST: {user_request}\n"
    user_msg += f"\nPROJECT STRUCTURE:\n{repo_map[:4000]}\n"

    if related_files:
        user_msg += "\nEXISTING FILES (for reference):\n"
        for rpath, rcontent in list(related_files.items())[:3]:
            user_msg += f"\n--- {rpath} ---\n{rcontent[:3000]}\n"

    messages = [SystemMessage(content=system), HumanMessage(content=user_msg)]
    response = await llm.ainvoke(messages, timeout=180)
    code = response.content.strip()

    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    return code


# ── Main refine orchestrator ────────────────────────────────────────────

async def refine_project(
    workspace_root: str | Path,
    user_request: str = "",
    *,
    auto_apply: bool = False,
    max_files: int = 15,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    End-to-end project refinement.

    Args:
        workspace_root: Path to the project directory.
        user_request: What the user wants improved (empty = auto-enhance).
        auto_apply: If True, write changes directly to disk.
        max_files: Max files to refine in one pass.
        dry_run: If True, analyse only — don't generate code.

    Returns:
        {
            "analysis": {...},
            "plan": [...],
            "changes": {filepath: new_content, ...},
            "applied": bool,
            "stats": {"files_analysed": N, "files_changed": N, "time_s": N}
        }
    """
    from src.utils.workspace import Workspace

    start = time.monotonic()
    root = Path(workspace_root).resolve()

    # 1. Scan workspace
    ws = Workspace.scan(root)
    repo_map = ws.build_repo_map(max_tokens=6000, focus_query=user_request)

    summary = ws.get_summary()
    logger.info(
        f"Scanned workspace: {summary['total_files']} files, "
        f"{summary['total_lines']} lines, type={summary['project_type']}"
    )

    # 2. Build context (prioritised file contents for the LLM)
    full_context = ws.build_full_context(max_chars=100_000)

    # 3. Analyse
    console.print("[cyan]Analysing project...[/]")
    analysis = await analyse_project(repo_map, full_context, user_request)

    if dry_run:
        elapsed = time.monotonic() - start
        return {
            "analysis": analysis,
            "plan": [],
            "changes": {},
            "applied": False,
            "stats": {
                "files_analysed": summary["total_files"],
                "files_changed": 0,
                "time_s": round(elapsed, 1),
            },
        }

    # 4. Plan
    console.print("[cyan]Planning refinements...[/]")
    plan = await plan_refinements(analysis, repo_map, user_request)

    # 5. Execute changes
    changes: Dict[str, str] = {}
    for step in plan[:max_files]:
        fpath = step.get("file", "")
        action = step.get("action", "modify")
        desc = step.get("description", "")

        if not fpath or fpath == "unknown":
            continue

        console.print(f"  [yellow]{action}[/] {fpath}: {desc[:60]}...")

        # Gather related files for cross-reference
        related: Dict[str, str] = {}
        for other_step in plan:
            other_f = other_step.get("file", "")
            if other_f and other_f != fpath and other_f in ws.files:
                content = ws.read_file(other_f)
                if content:
                    related[other_f] = content
                if len(related) >= 3:
                    break

        if action == "modify":
            original = ws.read_file(fpath)
            if original is None:
                logger.warning(f"Cannot read {fpath} for modification, skipping")
                continue
            new_content = await generate_refined_file(
                fpath, original, desc, repo_map, user_request, related,
            )
            if new_content and new_content != original:
                changes[fpath] = new_content

        elif action == "create":
            new_content = await generate_new_file(
                fpath, desc, repo_map, user_request, related,
            )
            if new_content:
                changes[fpath] = new_content

        elif action == "delete":
            changes[fpath] = "__DELETE__"

    # 6. Apply if requested
    applied = False
    if auto_apply and changes:
        for fpath, content in changes.items():
            if content == "__DELETE__":
                ws.delete_file(fpath)
            else:
                ws.write_file(fpath, content)
        applied = True

    elapsed = time.monotonic() - start
    return {
        "analysis": analysis,
        "plan": plan,
        "changes": changes,
        "applied": applied,
        "stats": {
            "files_analysed": summary["total_files"],
            "files_changed": len(changes),
            "time_s": round(elapsed, 1),
        },
    }
