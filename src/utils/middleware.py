"""
Pipeline Middleware System — Inspired by Deep Agents (LangChain)

Provides pre/post node hooks for the LangGraph pipeline, enabling:
- Loop detection (tracks per-file edit counts across fix cycles)
- Pre-completion checklist (validates outputs before publishing)
- Context compaction (trims bloated state to prevent context rot)
- Tool output offloading (large outputs → file, head/tail in state)

Architecture:
    Each middleware is a callable that wraps a node function.
    Middleware can inspect/modify state before and after node execution.
    Multiple middleware are composed via `compose_middleware()`.

Reference: https://docs.langchain.com/oss/python/langchain/middleware/overview

Session 14: Extracted from Deep Agents harness engineering patterns.
"""

import os
import re
import json
import time
import hashlib
import logging
import difflib
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1. LOOP DETECTION MIDDLEWARE
#    Tracks per-file edit counts across fix cycles.
#    After N edits to the same file, injects guidance to
#    reconsider approach (prevents "doom loops").
#    Inspired by Deep Agents' LoopDetectionMiddleware.
# ─────────────────────────────────────────────────────────────

@dataclass
class LoopDetector:
    """Detects oscillating fix patterns and doom loops.
    
    Tracks:
    - Per-file edit count across fix iterations
    - Error fingerprint recurrence (same error appearing 3+ times)
    - Cross-node cycle detection (code_testing → code_fixing → code_testing N times)
    - Strategy repetition (same fix approach tried multiple times)
    """
    max_edits_per_file: int = 5
    max_error_recurrence: int = 3
    max_node_cycles: int = 12  # Max times through the fix loop before escalating

    # Internal tracking
    file_edit_counts: Dict[str, int] = field(default_factory=dict)
    error_fingerprints: Dict[str, int] = field(default_factory=dict)
    node_visit_counts: Dict[str, int] = field(default_factory=dict)
    strategy_hashes: Dict[str, int] = field(default_factory=dict)
    
    # Escalation history
    escalations: List[Dict[str, Any]] = field(default_factory=list)
    
    def record_file_edit(self, filename: str) -> Optional[str]:
        """Record a file edit. Returns warning message if doom loop detected."""
        self.file_edit_counts[filename] = self.file_edit_counts.get(filename, 0) + 1
        count = self.file_edit_counts[filename]
        
        if count >= self.max_edits_per_file:
            warning = (
                f"⚠️ LOOP DETECTED: '{filename}' has been edited {count} times. "
                f"Consider a fundamentally different approach instead of patching the same file. "
                f"Options: (1) Rewrite the file from scratch, (2) Split into smaller modules, "
                f"(3) Simplify the implementation, (4) Remove this file if non-essential."
            )
            self.escalations.append({
                "type": "file_doom_loop",
                "file": filename,
                "edit_count": count,
                "timestamp": datetime.now().isoformat(),
            })
            return warning
        return None
    
    def record_error(self, error_fingerprint: str) -> Optional[str]:
        """Record an error occurrence. Returns warning if oscillating."""
        self.error_fingerprints[error_fingerprint] = (
            self.error_fingerprints.get(error_fingerprint, 0) + 1
        )
        count = self.error_fingerprints[error_fingerprint]
        
        if count >= self.max_error_recurrence:
            warning = (
                f"⚠️ OSCILLATION DETECTED: Error '{error_fingerprint[:80]}...' has appeared "
                f"{count} times. The current fix strategy is not working. "
                f"SKIP this error and focus on other issues, or try a completely different approach."
            )
            self.escalations.append({
                "type": "error_oscillation",
                "fingerprint": error_fingerprint[:120],
                "count": count,
                "timestamp": datetime.now().isoformat(),
            })
            return warning
        return None
    
    def record_node_visit(self, node_name: str) -> Optional[str]:
        """Record a node visit. Returns warning if cycling too much."""
        self.node_visit_counts[node_name] = (
            self.node_visit_counts.get(node_name, 0) + 1
        )
        count = self.node_visit_counts[node_name]
        
        if count >= self.max_node_cycles:
            warning = (
                f"⚠️ CYCLE LIMIT: Node '{node_name}' has been visited {count} times. "
                f"The pipeline is not making progress. Consider: "
                f"(1) Accepting current output, (2) Reducing scope, (3) Using simpler implementation."
            )
            self.escalations.append({
                "type": "node_cycle_limit",
                "node": node_name,
                "visit_count": count,
                "timestamp": datetime.now().isoformat(),
            })
            return warning
        return None
    
    def record_strategy(self, strategy_description: str) -> Optional[str]:
        """Record a fix strategy. Returns warning if repeating."""
        h = hashlib.md5(strategy_description.lower().strip().encode()).hexdigest()[:12]
        self.strategy_hashes[h] = self.strategy_hashes.get(h, 0) + 1
        count = self.strategy_hashes[h]
        
        if count >= 2:
            warning = (
                f"⚠️ STRATEGY REPEAT: A similar fix strategy has been tried {count} times. "
                f"Try a fundamentally different approach."
            )
            self.escalations.append({
                "type": "strategy_repeat",
                "hash": h,
                "count": count,
                "timestamp": datetime.now().isoformat(),
            })
            return warning
        return None
    
    def get_context_injection(self) -> str:
        """Generate context injection for LLM prompts based on current state."""
        lines = []
        
        # Files edited many times
        hot_files = {f: c for f, c in self.file_edit_counts.items() if c >= 3}
        if hot_files:
            lines.append("FILES REQUIRING CAUTION (edited multiple times):")
            for f, c in sorted(hot_files.items(), key=lambda x: -x[1]):
                lines.append(f"  - {f}: {c} edits — consider rewriting from scratch")
        
        # Recurring errors to skip
        stuck_errors = {fp: c for fp, c in self.error_fingerprints.items() if c >= self.max_error_recurrence}
        if stuck_errors:
            lines.append("\nERRORS TO SKIP (unfixable with current approach):")
            for fp, c in stuck_errors.items():
                lines.append(f"  - [{c}x] {fp[:100]}")
        
        # Overall cycle count
        fix_cycles = self.node_visit_counts.get("code_fixing", 0)
        if fix_cycles >= 4:
            lines.append(f"\n⚠️ FIX CYCLE {fix_cycles}/{self.max_node_cycles} — focus on highest-impact issues only.")
        
        return "\n".join(lines) if lines else ""
    
    def get_report(self) -> Dict[str, Any]:
        """Get a summary report of loop detection state."""
        return {
            "file_edit_counts": dict(self.file_edit_counts),
            "error_recurrence": {k: v for k, v in self.error_fingerprints.items() if v >= 2},
            "node_visits": dict(self.node_visit_counts),
            "escalations": self.escalations[-10:],  # Last 10
            "total_escalations": len(self.escalations),
        }


# Global loop detector instance (persists across pipeline nodes)
_loop_detector: Optional[LoopDetector] = None

def get_loop_detector() -> LoopDetector:
    """Get or create the global loop detector."""
    global _loop_detector
    if _loop_detector is None:
        _loop_detector = LoopDetector()
    return _loop_detector

def reset_loop_detector():
    """Reset for a new pipeline run."""
    global _loop_detector
    _loop_detector = LoopDetector()


# ─────────────────────────────────────────────────────────────
# 2. PRE-COMPLETION CHECKLIST
#    Validates pipeline outputs before publishing.
#    Intercepts before git_publishing to catch:
#    - Missing files that were planned
#    - Empty/stub implementations
#    - Broken imports between generated files
#    - Missing entry point (main.py / __init__.py)
#    - Missing requirements.txt
#    Inspired by Deep Agents' PreCompletionChecklistMiddleware.
# ─────────────────────────────────────────────────────────────

@dataclass
class ChecklistItem:
    name: str
    passed: bool
    details: str
    severity: str = "error"  # "error" | "warning" | "info"


def run_pre_completion_checklist(state: Dict[str, Any]) -> List[ChecklistItem]:
    """Run comprehensive pre-completion checks before publishing.
    
    Returns list of ChecklistItems. If any have severity="error" and passed=False,
    the code should not be published without fixing.
    """
    results = []
    generated_code = state.get("generated_code", {})
    files = generated_code.get("files", {}) if isinstance(generated_code, dict) else {}
    requirements = state.get("requirements", {})
    
    # ── Check 1: Files exist ──
    if not files:
        results.append(ChecklistItem(
            name="files_generated",
            passed=False,
            details="No files were generated! Cannot publish empty repository.",
            severity="error"
        ))
        return results  # No point checking further
    
    results.append(ChecklistItem(
        name="files_generated",
        passed=True,
        details=f"{len(files)} files generated",
        severity="info"
    ))
    
    # ── Check 2: Entry point exists ──
    has_entry = any(
        f in files for f in ["main.py", "__main__.py", "app.py", "cli.py", "run.py", "setup.py"]
    )
    has_init = "__init__.py" in files
    results.append(ChecklistItem(
        name="entry_point",
        passed=has_entry or has_init,
        details=f"Entry point found: {has_entry}, __init__.py: {has_init}",
        severity="warning" if not has_entry else "info"
    ))
    
    # ── Check 3: Requirements.txt exists ──
    has_reqs = "requirements.txt" in files
    results.append(ChecklistItem(
        name="requirements_txt",
        passed=has_reqs,
        details="requirements.txt present" if has_reqs else "Missing requirements.txt",
        severity="warning"
    ))
    
    # ── Check 4: No empty files ──
    empty_files = [f for f, content in files.items() 
                   if not content or len(content.strip()) < 10]
    results.append(ChecklistItem(
        name="no_empty_files",
        passed=len(empty_files) == 0,
        details=f"Empty files: {empty_files}" if empty_files else "All files have content",
        severity="error" if empty_files else "info"
    ))
    
    # ── Check 5: No placeholder TODO stubs ──
    stub_patterns = [
        r'raise\s+NotImplementedError',
        r'pass\s*#\s*TODO',
        r'\.\.\..*#\s*TODO',
        r'#\s*TODO:\s*implement',
    ]
    stub_files = []
    for filename, content in files.items():
        if not isinstance(content, str):
            continue
        for pattern in stub_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                stub_files.append(filename)
                break
    
    results.append(ChecklistItem(
        name="no_stubs",
        passed=len(stub_files) == 0,
        details=f"Stub/TODO files: {stub_files}" if stub_files else "No placeholder stubs detected",
        severity="warning" if stub_files else "info"
    ))
    
    # ── Check 6: Python syntax valid ──
    import ast
    syntax_errors = []
    for filename, content in files.items():
        if not filename.endswith('.py') or not isinstance(content, str):
            continue
        try:
            ast.parse(content)
        except SyntaxError as e:
            syntax_errors.append(f"{filename}:{e.lineno}: {e.msg}")
    
    results.append(ChecklistItem(
        name="syntax_valid",
        passed=len(syntax_errors) == 0,
        details=f"Syntax errors: {syntax_errors[:5]}" if syntax_errors else "All Python files parse correctly",
        severity="error" if syntax_errors else "info"
    ))
    
    # ── Check 7: Cross-file imports resolve ──
    local_modules = set()
    for filename in files:
        if filename.endswith('.py'):
            mod_name = filename.replace('.py', '').replace('/', '.').replace('\\', '.')
            local_modules.add(mod_name)
            # Also add just the filename stem
            local_modules.add(os.path.splitext(os.path.basename(filename))[0])
    
    broken_imports = []
    for filename, content in files.items():
        if not filename.endswith('.py') or not isinstance(content, str):
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                # Check if it's a local import that doesn't resolve
                mod_parts = node.module.split('.')
                base_module = mod_parts[0]
                if base_module in local_modules and node.module not in local_modules:
                    # Nested import to local module that doesn't exist
                    broken_imports.append(f"{filename}: from {node.module} import ...")
    
    results.append(ChecklistItem(
        name="imports_resolve",
        passed=len(broken_imports) == 0,
        details=f"Broken local imports: {broken_imports[:5]}" if broken_imports else "Local imports resolve",
        severity="warning" if broken_imports else "info"
    ))
    
    # ── Check 8: README exists ──
    has_readme = any(f.lower() in ("readme.md", "readme.txt", "readme.rst") for f in files)
    results.append(ChecklistItem(
        name="readme_exists",
        passed=has_readme,
        details="README found" if has_readme else "No README file — documentation is missing",
        severity="warning"
    ))
    
    # ── Check 9: Tests passed or at least exist ──
    tests_passed = state.get("tests_passed", False)
    smoke_test = state.get("smoke_test", {}) or {}
    smoke_passed = smoke_test.get("passed", False) if isinstance(smoke_test, dict) else False
    
    results.append(ChecklistItem(
        name="tests_status",
        passed=tests_passed,
        details=f"Tests passed: {tests_passed}, Smoke test: {smoke_passed}",
        severity="warning" if not tests_passed else "info"
    ))
    
    # ── Check 10: Self-eval score acceptable ──
    self_eval_score = state.get("self_eval_score", -1.0)
    results.append(ChecklistItem(
        name="self_eval_score",
        passed=self_eval_score >= 6.0 or self_eval_score < 0,
        details=f"Self-eval score: {self_eval_score:.1f}/10" if self_eval_score >= 0 else "Self-eval not run",
        severity="warning" if 0 <= self_eval_score < 6.0 else "info"
    ))
    
    return results


def format_checklist_report(items: List[ChecklistItem]) -> str:
    """Format checklist items as a human-readable report."""
    lines = ["=" * 60, "📋 PRE-COMPLETION CHECKLIST", "=" * 60]
    
    errors = [i for i in items if not i.passed and i.severity == "error"]
    warnings = [i for i in items if not i.passed and i.severity == "warning"]
    passed = [i for i in items if i.passed]
    
    for item in items:
        icon = "✅" if item.passed else ("❌" if item.severity == "error" else "⚠️")
        lines.append(f"  {icon} {item.name}: {item.details}")
    
    lines.append("")
    lines.append(f"Result: {len(passed)} passed, {len(errors)} errors, {len(warnings)} warnings")
    
    if errors:
        lines.append("\n🚫 BLOCKING ISSUES — must fix before publishing:")
        for e in errors:
            lines.append(f"  - {e.name}: {e.details}")
    
    if warnings:
        lines.append("\n⚠️ WARNINGS — should fix if possible:")
        for w in warnings:
            lines.append(f"  - {w.name}: {w.details}")
    
    lines.append("=" * 60)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 3. CONTEXT COMPACTION
#    Prevents context rot by trimming bloated state fields.
#    Keeps head/tail of large lists, summarizes old errors,
#    and offloads large tool outputs to files.
#    Inspired by Deep Agents' SummarizationMiddleware and
#    ContextEditingMiddleware.
# ─────────────────────────────────────────────────────────────

def compact_state_errors(state: Dict[str, Any], max_recent: int = 15) -> Dict[str, Any]:
    """Compact the errors list to prevent context bloat.
    
    Keeps the last `max_recent` errors and summarizes older ones.
    This prevents the state from growing unboundedly across fix iterations.
    """
    errors = state.get("errors", [])
    if len(errors) <= max_recent:
        return {}  # Nothing to compact
    
    # Keep last N errors verbatim
    recent = errors[-max_recent:]
    old_count = len(errors) - max_recent
    
    # Summarize old errors by type
    old_errors = errors[:old_count]
    error_types: Dict[str, int] = {}
    for err in old_errors:
        if isinstance(err, str):
            # Extract error type from string
            match = re.match(r'(\w+Error|\w+Exception|SyntaxError|ImportError)', err)
            err_type = match.group(1) if match else "Other"
            error_types[err_type] = error_types.get(err_type, 0) + 1
    
    summary = f"[COMPACTED: {old_count} older errors — " + ", ".join(
        f"{t}:{c}" for t, c in sorted(error_types.items(), key=lambda x: -x[1])
    ) + "]"
    
    return {"errors": [summary] + recent}


def compact_state_warnings(state: Dict[str, Any], max_recent: int = 10) -> Dict[str, Any]:
    """Compact the warnings list."""
    warnings = state.get("warnings", [])
    if len(warnings) <= max_recent:
        return {}
    
    recent = warnings[-max_recent:]
    old_count = len(warnings) - max_recent
    summary = f"[COMPACTED: {old_count} older warnings trimmed]"
    return {"warnings": [summary] + recent}


def compact_fix_diffs(state: Dict[str, Any], max_keep: int = 3) -> Dict[str, Any]:
    """Keep only the last N fix diffs to prevent bloat."""
    diffs = state.get("fix_diffs", [])
    if len(diffs) <= max_keep:
        return {}
    return {"fix_diffs": diffs[-max_keep:]}


def compact_resource_events(state: Dict[str, Any], max_keep: int = 10) -> Dict[str, Any]:
    """Keep only recent resource events."""
    events = state.get("resource_events", [])
    if len(events) <= max_keep:
        return {}
    return {"resource_events": events[-max_keep:]}


def run_state_compaction(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run all compaction strategies on state. Returns partial state update dict."""
    updates = {}
    
    for compactor in [compact_state_errors, compact_state_warnings, 
                      compact_fix_diffs, compact_resource_events]:
        result = compactor(state)
        if result:
            updates.update(result)
    
    if updates:
        logger.info(f"State compaction: trimmed {len(updates)} field(s)")
    
    return updates


# ─────────────────────────────────────────────────────────────
# 4. TOOL OUTPUT OFFLOADING
#    Large tool/node outputs are written to files and replaced
#    with a summary + file path in state.
#    Prevents context window overflow.
#    Inspired by Deep Agents' file offloading in tool outputs.
# ─────────────────────────────────────────────────────────────

def offload_large_output(
    content: str,
    label: str,
    output_dir: str = "logs/offloaded",
    max_inline_chars: int = 2000,
) -> str:
    """If content exceeds max_inline_chars, offload to file and return summary.
    
    Returns the original content if small enough, or a head/tail summary with
    a file path reference if too large.
    """
    if len(content) <= max_inline_chars:
        return content
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{label}_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        logger.warning(f"Failed to offload output to {filepath}: {e}")
        # Fallback: just truncate
        return content[:max_inline_chars] + f"\n... [TRUNCATED {len(content) - max_inline_chars} chars]"
    
    # Keep head and tail
    head_chars = max_inline_chars // 2
    tail_chars = max_inline_chars // 2
    head = content[:head_chars]
    tail = content[-tail_chars:]
    
    return (
        f"{head}\n"
        f"\n... [{len(content) - head_chars - tail_chars} chars offloaded to {filepath}] ...\n\n"
        f"{tail}"
    )


def offload_test_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """Offload large test result fields to files."""
    test_results = state.get("test_results", {})
    if not isinstance(test_results, dict):
        return {}
    
    updates = {}
    output_dir = os.path.join(state.get("output_dir", "output"), "offloaded")
    
    # Offload large execution_errors
    exec_errors = test_results.get("execution_errors", [])
    if isinstance(exec_errors, list) and len(exec_errors) > 20:
        offloaded = offload_large_output(
            "\n".join(str(e) for e in exec_errors),
            "execution_errors",
            output_dir=output_dir
        )
        test_results = dict(test_results)
        test_results["execution_errors"] = [offloaded]
        test_results["_errors_offloaded"] = True
        updates["test_results"] = test_results
    
    return updates


# ─────────────────────────────────────────────────────────────
# 5. DIFF-BASED FIXING HELPER
#    Instead of regenerating entire files, extract only the
#    changed functions/regions and create minimal patches.
#    Reduces LLM confusion and preserves working code.
#    Inspired by Deep Agents' speculative diff-based editing.
# ─────────────────────────────────────────────────────────────

def generate_minimal_diff(old_content: str, new_content: str, filename: str = "file.py") -> str:
    """Generate a unified diff between old and new content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    return "\n".join(diff)


def extract_error_context(
    code: str, 
    error_line: int, 
    context_lines: int = 15
) -> Tuple[str, int, int]:
    """Extract the function/class containing the error line.
    
    Returns (context_code, start_line, end_line) — the smallest
    function or class enclosing the error, plus context.
    """
    lines = code.splitlines()
    if error_line < 1 or error_line > len(lines):
        # Fallback: return surrounding lines
        start = max(0, error_line - context_lines - 1)
        end = min(len(lines), error_line + context_lines)
        return "\n".join(lines[start:end]), start + 1, end
    
    import ast
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Can't parse — return raw context
        start = max(0, error_line - context_lines - 1)
        end = min(len(lines), error_line + context_lines)
        return "\n".join(lines[start:end]), start + 1, end
    
    # Find the smallest enclosing function/class
    best_node = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                if node.lineno <= error_line <= (node.end_lineno or error_line):
                    if best_node is None or (node.end_lineno - node.lineno) < (best_node.end_lineno - best_node.lineno):
                        best_node = node
    
    if best_node:
        start = max(0, best_node.lineno - 2)  # 1 line before function def
        end = min(len(lines), (best_node.end_lineno or best_node.lineno) + 1)
        return "\n".join(lines[start:end]), start + 1, end
    
    # No enclosing function — return surrounding context
    start = max(0, error_line - context_lines - 1)
    end = min(len(lines), error_line + context_lines)
    return "\n".join(lines[start:end]), start + 1, end


def build_focused_fix_prompt(
    filename: str,
    code: str,
    errors: List[Dict[str, Any]],
    max_context_chars: int = 4000,
) -> str:
    """Build an LLM prompt focused on just the error regions.
    
    Instead of sending the entire file, extracts only the
    functions that need fixing and their error context.
    """
    sections = []
    seen_ranges = set()
    
    for error in errors[:5]:  # Limit to 5 errors per file
        line = error.get("line", 0)
        if not line:
            continue
        
        context, start, end = extract_error_context(code, line)
        range_key = (start, end)
        if range_key in seen_ranges:
            continue
        seen_ranges.add(range_key)
        
        sections.append(
            f"### Error at line {line}: {error.get('message', 'unknown')}\n"
            f"```python\n"
            f"# Lines {start}-{end} of {filename}:\n"
            f"{context}\n"
            f"```\n"
        )
    
    if not sections:
        # No specific line info — send first N chars of file
        truncated = code[:max_context_chars]
        return (
            f"### Full file: {filename}\n"
            f"```python\n{truncated}\n```\n"
            f"{'[TRUNCATED]' if len(code) > max_context_chars else ''}\n"
        )
    
    return "\n".join(sections)


# ─────────────────────────────────────────────────────────────
# 6. MIDDLEWARE COMPOSITION
#    Compose multiple middleware into a single wrapper.
#    Each middleware can modify state before/after node execution.
# ─────────────────────────────────────────────────────────────

def compose_middleware(
    node_fn: Callable,
    *middleware: Callable
) -> Callable:
    """Compose multiple middleware around a node function.
    
    Each middleware should be a function that takes (node_fn, state) and
    returns a modified result dict. Middleware are applied in order
    (first middleware is outermost).
    
    Example:
        wrapped = compose_middleware(
            code_fixing_node,
            loop_detection_middleware,
            compaction_middleware,
        )
    """
    result = node_fn
    for mw in reversed(middleware):
        prev = result
        def make_wrapper(mw_fn, inner_fn):
            async def wrapped(state):
                return await mw_fn(inner_fn, state)
            return wrapped
        result = make_wrapper(mw, prev)
    return result
