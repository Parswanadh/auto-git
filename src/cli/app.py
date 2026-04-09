#!/usr/bin/env python3
"""
Auto-GIT — Unified CLI
Launch with: auto-git

Inspired by Claude Code / Deep Agents / Gemini CLI.
Consolidates all prior CLI entry points into one polished experience.
"""

import asyncio
import os
import subprocess
import sys
import time
import json
import signal
from pathlib import Path
from typing import Optional, Dict, Any, List

# ── Force UTF-8 on Windows so Unicode banner renders correctly ─
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # older Python or non-file stream

# ── Rich imports ──────────────────────────────────────────────
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich import box
from rich.tree import Tree
import itertools

# ── Add project root to path ─────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

console = Console()

# ──────────────────────────────────────────────────────────────
# BANNER & ANIMATIONS
# ──────────────────────────────────────────────────────────────

# Gradient lines (cyan -> blue -> magenta)
BANNER_LINES_UNICODE = [
    "    \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557   \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557        \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "   \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u255a\u2550\u2550\u2588\u2588\u2554\u2550\u2550\u255d\u2588\u2588\u2554\u2550\u2550\u2550\u2588\u2588\u2557      \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d \u2588\u2588\u2551\u255a\u2550\u2550\u2588\u2588\u2554\u2550\u2550\u255d",
    "   \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551   ",
    "   \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551\u255a\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551   ",
    "   \u2588\u2588\u2551  \u2588\u2588\u2551\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d   \u2588\u2588\u2551   \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d      \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551   \u2588\u2588\u2551   ",
    "   \u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d    \u255a\u2550\u255d    \u255a\u2550\u2550\u2550\u2550\u2550\u255d        \u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d   \u255a\u2550\u255d   ",
]

BANNER_LINES_ASCII = [
    r"      _   _   _ _____ ___        ____ ___ _____ ",
    r"     / \ | | | |_   _/ _ \      / ___|_ _|_   _|",
    r"    / _ \| | | | | || | | |____| |  _ | |  | |  ",
    r"   / ___ \ |_| | | || |_| |____| |_| || |  | |  ",
    r"  /_/   \_\___/  |_| \___/      \____|___| |_|  ",
    r"                                                 ",
]


def _can_render_unicode() -> bool:
    """Check if the current terminal can render Unicode box-drawing chars."""
    try:
        "\u2588".encode(sys.stdout.encoding or "utf-8")
        return True
    except (UnicodeEncodeError, LookupError):
        return False


BANNER_LINES = BANNER_LINES_UNICODE if _can_render_unicode() else BANNER_LINES_ASCII

GRADIENT_COLORS = [
    "bright_cyan",
    "cyan",
    "blue",
    "bright_blue",
    "magenta",
    "bright_magenta",
]

TAGLINE = "Autonomous Research -> Code -> GitHub Pipeline"
VERSION = "2.0.0"


def _gradient_banner() -> Text:
    """Build the banner with per-line gradient colours."""
    txt = Text()
    for i, line in enumerate(BANNER_LINES):
        color = GRADIENT_COLORS[i % len(GRADIENT_COLORS)]
        txt.append(line + "\n", style=f"bold {color}")
    return txt


def animate_startup():
    """Play a short typewriter-style startup animation."""
    try:
        console.clear()
    except Exception:
        pass  # clear may fail on some terminals

    # 1. Print banner line-by-line with tiny delay
    for i, line in enumerate(BANNER_LINES):
        color = GRADIENT_COLORS[i % len(GRADIENT_COLORS)]
        try:
            console.print(f"[bold {color}]{line}[/]")
        except UnicodeEncodeError:
            # Last-resort: strip Rich markup and print plain
            print(line)
        time.sleep(0.06)

    # 2. Tagline
    console.print()
    tag = Text()
    tag.append("   > ", style="bright_yellow")
    tag.append(TAGLINE, style="dim bold")
    tag.append(f"  v{VERSION}", style="dim")
    console.print(tag)
    console.print()


def print_status_bar(checks: Dict[str, str]):
    """Compact one-line status indicators."""
    dot = "*" if not _can_render_unicode() else "\u25cf"
    parts = []
    for label, state in checks.items():
        if state == "ok":
            parts.append(f"[green]{dot}[/] {label}")
        elif state == "warn":
            parts.append(f"[yellow]{dot}[/] {label}")
        else:
            parts.append(f"[red]{dot}[/] {label}")
    console.print("   " + "   ".join(parts))
    console.print()


# ──────────────────────────────────────────────────────────────
# QUICK SYSTEM CHECKS (non-blocking)
# ──────────────────────────────────────────────────────────────

def _check_ollama() -> str:
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return "ok" if r.status_code == 200 else "fail"
    except Exception:
        return "warn"


def _check_github_token() -> str:
    return "ok" if os.getenv("GITHUB_TOKEN") else "warn"


def _check_env_keys() -> str:
    """Check that at least one LLM provider key is set."""
    for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        if os.getenv(key):
            return "ok"
    return "warn"


def quick_health_check() -> Dict[str, str]:
    """Run fast, non-blocking health checks."""
    # Load .env if present
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            pass

    return {
        "LLM Keys": _check_env_keys(),
        "Ollama": _check_ollama(),
        "GitHub": _check_github_token(),
    }


# ──────────────────────────────────────────────────────────────
# MODEL SELECTOR
# ──────────────────────────────────────────────────────────────

PROFILES_INFO = {
    "fast":      ("⚡ Fast",      "Quick extraction & validation",      "0.3-0.4"),
    "balanced":  ("⚖️  Balanced",  "Problem extraction, solutions",      "0.7"),
    "powerful":  ("🔥 Powerful",  "Code generation, architecture",      "0.3"),
    "reasoning": ("🧠 Reasoning", "Critique, debate, consensus",        "0.8"),
    "research":  ("🔍 Research",  "Web-grounded SOTA research",         "0.3-0.5"),
}


def show_model_profiles():
    """Display available model profiles from model_manager."""
    table = Table(
        title="🤖 Model Profiles",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Profile", style="bold cyan", width=14)
    table.add_column("Description", style="white", width=36)
    table.add_column("Temp", style="yellow", width=8)

    for key, (label, desc, temp) in PROFILES_INFO.items():
        table.add_row(label, desc, temp)

    console.print()
    console.print(table)
    console.print()


def interactive_model_select() -> Optional[str]:
    """Let the user pick a profile; returns profile name or None."""
    show_model_profiles()
    profiles = list(PROFILES_INFO.keys())
    choice = Prompt.ask(
        "Select a profile",
        choices=profiles + ["back"],
        default="balanced",
    )
    return None if choice == "back" else choice


def show_ollama_models():
    """List models currently pulled in Ollama."""
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=5)
        models = r.json().get("models", [])
    except Exception:
        console.print("[red]  Could not reach Ollama.[/]")
        return

    if not models:
        console.print("[yellow]  No models found in Ollama.[/]")
        return

    table = Table(title="Ollama Models", box=box.SIMPLE, border_style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Size", style="yellow")
    table.add_column("Modified", style="dim")
    for m in models:
        size_gb = m.get("size", 0) / (1024**3)
        table.add_row(
            m.get("name", "?"),
            f"{size_gb:.1f} GB",
            m.get("modified_at", "?")[:19],
        )
    console.print()
    console.print(table)
    console.print()


# ──────────────────────────────────────────────────────────────
# PIPELINE RUNNER  (live node-by-node progress)
# ──────────────────────────────────────────────────────────────

PIPELINE_NODES = [
    ("requirements_extraction",  "📋 Extracting requirements"),
    ("research",                 "🔍 Researching papers & code"),
    ("problem_extraction",       "🧩 Extracting problems"),
    ("solution_generation",      "💡 Generating solutions"),
    ("critique",                 "🗣️  Expert critique"),
    ("consensus_check",          "🤝 Checking consensus"),
    ("solution_selection",       "🏆 Selecting best solution"),
    ("architecture",             "🏗️  Designing architecture"),
    ("code_generation",          "💻 Generating code"),
    ("code_testing",             "🧪 Testing code"),
    ("code_fixing",              "🔧 Fixing issues"),
    ("self_evaluation",          "📊 Self-evaluation"),
    ("feature_verification",     "✅ Verifying features"),
    ("smoke_test",               "🔥 Smoke testing"),
    ("goal_evaluation",          "🎯 Evaluating goals"),
    ("git_publishing",           "📤 Publishing to GitHub"),
]


async def run_pipeline_with_progress(
    idea: str,
    *,
    auto_publish: bool = False,
    output_dir: Optional[str] = None,
    max_rounds: int = 5,
    profile: str = "balanced",
    user_requirements: Optional[str] = None,
):
    """
    Run the full Auto-GIT pipeline with a Rich live-progress display.
    """
    from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline

    console.print()
    _launch_body = f"[bold bright_cyan]Idea:[/] {idea}"
    if user_requirements:
        _launch_body += f"\n[bold bright_yellow]Requirements:[/] {user_requirements}"
    console.print(Panel.fit(
        _launch_body,
        title="🚀 Pipeline Launch",
        border_style="bright_cyan",
    ))
    console.print()

    # Progress bar for visual feedback
    progress = Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[cyan]{task.completed}/{task.total}[/]"),
        TimeElapsedColumn(),
        console=console,
    )

    task_id = progress.add_task("Pipeline progress", total=len(PIPELINE_NODES))

    # Callback to update progress from inside the pipeline
    stage_index = {"current": 0}

    def _stage_callback(stage_name: str):
        """Called by workflow when each node starts."""
        for idx, (node_name, label) in enumerate(PIPELINE_NODES):
            if node_name in stage_name:
                stage_index["current"] = idx
                progress.update(task_id, completed=idx, description=label)
                break

    with progress:
        try:
            result = await run_auto_git_pipeline(
                idea=idea,
                user_requirements=user_requirements,
                max_debate_rounds=max_rounds,
                use_web_search=True,
                auto_publish=auto_publish,
                output_dir=output_dir,
                interactive=False,
                resume=False,  # Fresh run — use 'resume' command for checkpoint resume
            )
            progress.update(task_id, completed=len(PIPELINE_NODES), description="✅ Done!")
        except KeyboardInterrupt:
            console.print("\n[yellow]Pipeline interrupted.[/]")
            return None
        except Exception as exc:
            progress.update(task_id, description=f"[red]❌ {exc}[/]")
            console.print(f"\n[bold red]Pipeline error:[/] {exc}\n")
            return None

    # ── Results summary ──
    _show_pipeline_results(result)
    return result


def _show_pipeline_results(state: Dict[str, Any]):
    """Pretty-print pipeline results."""
    console.print()
    console.rule("[bold green]Pipeline Complete[/]")
    console.print()

    # Score
    score = state.get("self_eval_score", 0)
    score_color = "green" if score >= 7 else "yellow" if score >= 5 else "red"
    console.print(f"  [bold]Self-Eval Score:[/] [{score_color}]{score}/10[/]")

    # Tests
    tests = state.get("tests_passed", False)
    console.print(f"  [bold]Tests Passed:[/]   {'[green]Yes[/]' if tests else '[red]No[/]'}")

    # Files
    files_dict = (state.get("generated_code") or {}).get("files", {})
    console.print(f"  [bold]Files Generated:[/] [cyan]{len(files_dict)}[/]")

    # Output
    out_path = state.get("output_path")
    if out_path:
        console.print(f"  [bold]Output:[/]          [link=file://{out_path}]{out_path}[/]")

    # GitHub
    gh_url = state.get("github_url")
    if gh_url:
        console.print(f"  [bold]GitHub:[/]          [link={gh_url}]{gh_url}[/]")

    console.print()

    # File listing
    if files_dict:
        file_table = Table(box=box.SIMPLE, border_style="dim", show_header=False)
        file_table.add_column("File", style="cyan")
        file_table.add_column("Lines", style="yellow", justify="right")
        for fname, content in sorted(files_dict.items()):
            lines = content.count("\n") + 1 if content else 0
            file_table.add_row(fname, str(lines))
        console.print(file_table)
        console.print()


# ──────────────────────────────────────────────────────────────
# CONFIG VIEWER / EDITOR
# ──────────────────────────────────────────────────────────────

def show_config():
    """Display current config.yaml highlights."""
    cfg_path = PROJECT_ROOT / "config.yaml"
    if not cfg_path.exists():
        console.print("[yellow]config.yaml not found.[/]")
        return
    try:
        import yaml
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]Failed to load config: {e}[/]")
        return

    table = Table(title="⚙️  Configuration", box=box.ROUNDED, border_style="cyan")
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", style="white")

    # Pipeline settings
    pipe = cfg.get("pipeline", {})
    table.add_row("Pipeline Version", str(pipe.get("version", "?")))
    table.add_row("Dry Run", str(pipe.get("dry_run", "?")))
    table.add_row("Novelty Threshold", str(pipe.get("novelty_threshold", "?")))

    # Models
    m = cfg.get("models", {}).get("primary", {})
    table.add_row("Code Generation Model", str(m.get("code_generation", "?")))
    table.add_row("Analysis Model", str(m.get("analysis", "?")))

    # Single-model arch
    sma = cfg.get("single_model_architecture", {})
    table.add_row("Primary Model", str(sma.get("primary_model", "?")))
    table.add_row("Router Model", str(sma.get("router_model", "?")))

    console.print()
    console.print(table)
    console.print()


def full_status():
    """Detailed system health + config dump."""
    console.print()
    console.rule("[bold cyan]System Status[/]")
    console.print()

    # Health
    checks = quick_health_check()
    print_status_bar(checks)

    # Ollama details
    show_ollama_models()

    # Config
    show_config()

    # Directories
    dirs = ["src/langraph_pipeline", "src/utils", "output", "logs"]
    for d in dirs:
        p = PROJECT_ROOT / d
        marker = "[green]✓[/]" if p.exists() else "[red]✗[/]"
        console.print(f"  {marker} {d}/")
    console.print()


# ──────────────────────────────────────────────────────────────
# HELP
# ──────────────────────────────────────────────────────────────

def show_help():
    """Print the interactive help table."""
    table = Table(
        title="📚 Commands",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Command", style="bold cyan", width=28)
    table.add_column("Description", style="white")

    cmds = [
        ("run <idea>",               "Run full pipeline on an idea"),
        ("run --idea <id>",          "Run pipeline with arXiv paper ID"),
        ("resume",                   "Resume last interrupted pipeline"),
        ("refine [instructions]",    "Refine/enhance current project"),
        ("fix <project>",            "Test & fix existing project"),
        ("research <topic>",         "Research-only mode"),
        ("", ""),
        ("ls [pattern]",             "List files in workspace"),
        ("tree",                     "Show directory tree"),
        ("cat <file>",              "View a file's contents"),
        ("edit <file>",             "Open a file for editing"),
        ("search <query>",          "Search across all files"),
        ("", ""),
        ("models",                   "Show & select model profiles"),
        ("models ollama",            "List Ollama models"),
        ("status",                   "Full system health check"),
        ("config",                   "View configuration"),
        ("help",                     "This help screen"),
        ("clear",                    "Clear the terminal"),
        ("exit / quit / Ctrl+C",     "Exit Auto-GIT"),
    ]

    for cmd, desc in cmds:
        if not cmd and not desc:
            table.add_row("", "")  # separator row
        else:
            table.add_row(cmd, desc)

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]  Or just type naturally: 'generate a sparse attention library'[/]")
    console.print("[dim]  Refine: open auto-git in a project folder, then type 'refine add auth'[/]")
    console.print()


# ──────────────────────────────────────────────────────────────
# INTENT ROUTING
# ──────────────────────────────────────────────────────────────

# Words that signal the user has a project idea (even if short)
_IDEA_VERBS = {"implement", "make", "design", "develop", "write", "code", "prototype", "add", "port"}

# ── Workspace state (lazily initialised) ─────────────────────
_workspace = None  # type: ignore
_workspace_cwd: Optional[str] = None


def _get_workspace():
    """Return the current Workspace, scanning cwd on first call."""
    global _workspace, _workspace_cwd
    cwd = os.getcwd()
    if _workspace is None or _workspace_cwd != cwd:
        from src.utils.workspace import Workspace
        _workspace = Workspace.scan(cwd)
        _workspace_cwd = cwd
    return _workspace


def _refresh_workspace():
    """Force a re-scan of the current directory."""
    global _workspace, _workspace_cwd
    _workspace = None
    _workspace_cwd = None
    return _get_workspace()


def route_input(raw: str):
    """
    Classify user input into (action, payload).
    Supports both slash-commands and natural language.
    """
    stripped = raw.strip()
    lower = stripped.lower()

    # Empty
    if not stripped:
        return ("noop", "")

    # Exact commands
    if lower in ("help", "/help", "h", "?"):
        return ("help", "")
    if lower in ("exit", "quit", "q", "/exit", "/quit"):
        return ("exit", "")
    if lower in ("clear", "/clear", "cls"):
        return ("clear", "")
    if lower in ("status", "/status", "health"):
        return ("status", "")
    if lower in ("config", "/config", "settings"):
        return ("config", "")
    if lower in ("models", "/models"):
        return ("models", "")
    if lower == "models ollama":
        return ("models_ollama", "")
    if lower in ("resume", "/resume"):
        return ("resume", "")

    # Bare commands (no payload) — will prompt interactively
    if lower in ("run", "/run", "generate", "create", "build"):
        return ("run", "")
    if lower in ("research", "/research"):
        return ("research", "")
    if lower in ("fix", "/fix"):
        return ("fix", "")
    if lower in ("debate", "/debate"):
        return ("debate", "")
    if lower in ("refine", "/refine", "improve", "enhance"):
        return ("refine", "")

    # Workspace / directory-awareness commands
    if lower in ("ls", "files", "/ls", "dir"):
        return ("ls", "")
    if lower in ("tree", "/tree"):
        return ("tree", "")
    if lower.startswith("ls ") or lower.startswith("files "):
        return ("ls", stripped.split(None, 1)[1] if " " in stripped else "")
    if lower.startswith("cat ") or lower.startswith("show ") or lower.startswith("read "):
        return ("cat", stripped.split(None, 1)[1] if " " in stripped else "")
    if lower.startswith("edit "):
        return ("edit", stripped[5:].strip())
    if lower.startswith("search ") or lower.startswith("grep "):
        return ("search", stripped.split(None, 1)[1] if " " in stripped else "")

    # Command prefixes
    if lower.startswith("run "):
        return ("run", stripped[4:].strip())
    if lower.startswith("generate "):
        return ("run", stripped[9:].strip())
    if lower.startswith("create "):
        return ("run", stripped[7:].strip())
    if lower.startswith("build "):
        return ("run", stripped[6:].strip())
    if lower.startswith("fix "):
        return ("fix", stripped[4:].strip())
    if lower.startswith("research "):
        return ("research", stripped[9:].strip())
    if lower.startswith("debate "):
        return ("debate", stripped[7:].strip())
    if lower.startswith("refine ") or lower.startswith("improve ") or lower.startswith("enhance "):
        return ("refine", stripped.split(None, 1)[1] if " " in stripped else "")

    # Natural-language fallback: treat as idea if long enough or starts with an idea verb
    first_word = lower.split()[0] if lower.split() else ""
    if len(stripped) > 15 or first_word in _IDEA_VERBS:
        return ("run", stripped)

    # Short non-command text → conversational / unknown
    return ("chat", stripped)


# ──────────────────────────────────────────────────────────────
# WORKSPACE COMMANDS (directory awareness)
# ──────────────────────────────────────────────────────────────

def show_workspace_banner():
    """Show a compact workspace awareness banner on startup."""
    cwd = os.getcwd()
    try:
        from src.utils.workspace import Workspace
        ws = Workspace.scan(cwd, max_files=2000)
        summary = ws.get_summary()
        ptype = summary["project_type"]
        ptype_colors = {
            "python": "yellow", "node": "green", "rust": "red",
            "go": "cyan", "java": "bright_red",
        }
        color = ptype_colors.get(ptype, "dim")

        info = Text()
        info.append("   📂 ", style="dim")
        info.append(cwd, style="bold white")
        info.append("  ", style="dim")
        info.append(f"[{ptype}]", style=f"bold {color}")
        info.append(f"  {summary['total_files']} files", style="dim")
        info.append(f"  {summary['total_lines']:,} lines", style="dim")
        if ws.project and ws.project.entrypoints:
            info.append(f"  entry: {', '.join(ws.project.entrypoints[:2])}", style="dim cyan")
        console.print(info)
        console.print()
    except Exception:
        console.print(f"   [dim]📂 {cwd}[/]")
        console.print()


def handle_ls(pattern: str):
    """List files in the workspace."""
    ws = _get_workspace()
    pat = pattern if pattern else "*"
    files = ws.list_files(pattern=pat)
    if not files:
        console.print(f"[yellow]No files matching '{pat}'[/]")
        return

    table = Table(box=box.SIMPLE, border_style="dim", show_header=True)
    table.add_column("File", style="cyan")
    table.add_column("Lines", style="yellow", justify="right", width=8)
    table.add_column("Size", style="dim", justify="right", width=10)

    for rel in files[:100]:
        fi = ws.files[rel]
        size_str = _human_size(fi.size)
        table.add_row(rel, str(fi.lines) if fi.lines else "-", size_str)

    console.print(table)
    if len(files) > 100:
        console.print(f"[dim]  ... and {len(files) - 100} more files[/]")
    console.print()


def handle_tree():
    """Show a directory tree."""
    ws = _get_workspace()
    # Build a Rich tree
    rich_tree = Tree(f"📂 [bold]{ws.root.name}[/]")
    _build_rich_tree(rich_tree, ws)
    console.print(rich_tree)
    console.print()


def handle_cat(file_path: str):
    """Display a file's contents with syntax highlighting."""
    if not file_path:
        console.print("[yellow]Usage: cat <file>[/]")
        return
    ws = _get_workspace()
    content = ws.read_file(file_path)
    if content is None:
        console.print(f"[red]File not found or binary: {file_path}[/]")
        return

    ext = os.path.splitext(file_path)[1].lstrip(".")
    lexer_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "rs": "rust", "go": "go", "java": "java",
        "json": "json", "yaml": "yaml", "yml": "yaml",
        "md": "markdown", "toml": "toml", "sh": "bash",
        "html": "html", "css": "css", "sql": "sql",
    }
    lexer = lexer_map.get(ext, "text")
    console.print(Syntax(content, lexer, line_numbers=True, theme="monokai"))
    console.print()


def handle_edit(file_path: str):
    """Open a file in the user's editor (or display it if no editor found)."""
    if not file_path:
        console.print("[yellow]Usage: edit <file>[/]")
        return
    ws = _get_workspace()
    abs_p = ws.root / file_path
    if not abs_p.exists():
        console.print(f"[red]File not found: {file_path}[/]")
        return
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", ""))
    if not editor:
        # Fallback: try code, then notepad
        import shutil
        for candidate in ("code", "notepad"):
            if shutil.which(candidate):
                editor = candidate
                break
    if editor:
        subprocess.Popen([editor, str(abs_p)])
    else:
        handle_cat(file_path)


def handle_search(query: str):
    """Search across all workspace files."""
    if not query:
        console.print("[yellow]Usage: search <query>[/]")
        return
    ws = _get_workspace()
    results = ws.search_content(query, max_results=30)
    if not results:
        console.print(f"[yellow]No matches for '{query}'[/]")
        return

    current_file = ""
    for fpath, line_no, line_text in results:
        if fpath != current_file:
            console.print(f"\n[bold cyan]{fpath}[/]")
            current_file = fpath
        # Highlight the match
        console.print(f"  [dim]{line_no:>4}[/]  {line_text[:120]}")
    console.print(f"\n[dim]{len(results)} matches[/]\n")


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def _build_rich_tree(tree: Tree, ws, *, max_depth: int = 4):
    """Populate a Rich Tree from the workspace file index."""
    # Group files by directory
    dirs: Dict[str, List[str]] = {}
    for rel in sorted(ws.files):
        parent = os.path.dirname(rel) or "."
        dirs.setdefault(parent, []).append(os.path.basename(rel))

    _rich_tree_recurse(tree, dirs, ".", depth=0, max_depth=max_depth)


def _rich_tree_recurse(tree, dirs, current, depth, max_depth):
    if depth >= max_depth:
        sub_count = sum(1 for d in dirs if d.startswith(current + "/"))
        if sub_count:
            tree.add(f"[dim]... {sub_count} more subdirectories[/]")
        return

    # Sub-directories of current
    sub_dirs = sorted(
        d for d in dirs
        if d != current and (os.path.dirname(d) or ".") == current
    )
    files_here = dirs.get(current, [])

    for sd in sub_dirs:
        branch = tree.add(f"📁 [bold]{os.path.basename(sd)}[/]")
        _rich_tree_recurse(branch, dirs, sd, depth + 1, max_depth)

    for fname in files_here[:50]:
        ext_icons = {
            ".py": "🐍", ".js": "📜", ".ts": "📘", ".json": "📋",
            ".yaml": "⚙️", ".yml": "⚙️", ".md": "📝", ".toml": "⚙️",
            ".rs": "🦀", ".go": "🐹",
        }
        ext = os.path.splitext(fname)[1].lower()
        icon = ext_icons.get(ext, "📄")
        tree.add(f"{icon} {fname}")
    if len(files_here) > 50:
        tree.add(f"[dim]... and {len(files_here) - 50} more files[/]")


# ──────────────────────────────────────────────────────────────
# REFINE EXISTING PROJECT
# ──────────────────────────────────────────────────────────────

async def handle_refine(user_request: str):
    """Refine/enhance the project in the current directory."""
    cwd = os.getcwd()
    ws = _get_workspace()
    summary = ws.get_summary()

    if summary["total_files"] == 0:
        console.print("[yellow]No files found in current directory. cd into a project first.[/]")
        return

    console.print()
    console.print(Panel.fit(
        f"[bold bright_cyan]Refine Mode[/]\n"
        f"Directory: [cyan]{cwd}[/]\n"
        f"Files: {summary['total_files']}  Lines: {summary['total_lines']:,}  Type: {summary['project_type']}\n"
        f"Request: [yellow]{user_request or '(auto-enhance)'}[/]",
        title="🔄 Project Refinement",
        border_style="bright_cyan",
    ))
    console.print()

    # Confirm before proceeding
    if not user_request:
        user_request = Prompt.ask(
            "[cyan]What would you like to improve?[/] (empty = auto-enhance)",
            default="",
        )

    apply = Confirm.ask("Apply changes directly to files?", default=False)

    from src.langraph_pipeline.refine_node import refine_project

    progress = Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    )
    task_id = progress.add_task("Analysing & refining...", total=None)

    with progress:
        try:
            result = await refine_project(
                workspace_root=cwd,
                user_request=user_request,
                auto_apply=apply,
            )
            progress.update(task_id, description="✅ Done!")
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]Refine cancelled.[/]")
            return
        except Exception as exc:
            console.print(f"\n[red]Refine failed: {exc}[/]")
            return

    # Show results
    analysis = result.get("analysis", {})
    plan = result.get("plan", [])
    changes = result.get("changes", {})
    stats = result.get("stats", {})

    # Analysis panel
    if analysis:
        strengths = analysis.get("strengths", [])
        weaknesses = analysis.get("weaknesses", [])
        suggestions = analysis.get("suggestions", [])

        analysis_parts = []
        if strengths:
            analysis_parts.append("[green]Strengths:[/]\n" + "\n".join(f"  + {s}" for s in strengths[:5]))
        if weaknesses:
            analysis_parts.append("[red]Weaknesses:[/]\n" + "\n".join(f"  - {w}" for w in weaknesses[:5]))
        if suggestions:
            analysis_parts.append("[yellow]Suggestions:[/]\n" + "\n".join(f"  * {s}" for s in suggestions[:5]))

        if analysis_parts:
            console.print(Panel(
                "\n\n".join(analysis_parts),
                title="📊 Analysis",
                border_style="cyan",
            ))

    # Plan table
    if plan:
        plan_table = Table(title="📋 Refinement Plan", box=box.ROUNDED, border_style="cyan")
        plan_table.add_column("#", style="dim", width=3)
        plan_table.add_column("Action", style="yellow", width=8)
        plan_table.add_column("File", style="cyan", width=30)
        plan_table.add_column("Description", style="white")
        for i, step in enumerate(plan, 1):
            plan_table.add_row(
                str(i), step.get("action", "?"),
                step.get("file", "?"), step.get("description", "")[:60],
            )
        console.print(plan_table)

    # Changes summary
    if changes:
        console.print(f"\n  [bold]Files changed:[/] [cyan]{len(changes)}[/]")
        for fpath in sorted(changes):
            tag = "[red]DELETE[/]" if changes[fpath] == "__DELETE__" else "[green]WRITE[/]"
            console.print(f"    {tag} {fpath}")

        if result.get("applied"):
            console.print("\n  [bold green]Changes applied to disk.[/]")
        else:
            # Offer to apply now
            if Confirm.ask("\n  Apply these changes now?", default=True):
                ws = _get_workspace()
                for fpath, content in changes.items():
                    if content == "__DELETE__":
                        ws.delete_file(fpath)
                    else:
                        ws.write_file(fpath, content)
                console.print("  [bold green]Changes applied.[/]")
                _refresh_workspace()
            else:
                console.print("  [dim]Changes discarded.[/]")

    console.print(f"\n  [dim]Time: {stats.get('time_s', '?')}s | "
                  f"Files analysed: {stats.get('files_analysed', '?')} | "
                  f"Files changed: {stats.get('files_changed', '?')}[/]")
    console.print()


# ──────────────────────────────────────────────────────────────
# FIX EXISTING PROJECT
# ──────────────────────────────────────────────────────────────

async def handle_fix(project_hint: str):
    """Re-test & fix an existing generated project."""
    out_dir = PROJECT_ROOT / "output"
    if not out_dir.exists():
        console.print("[yellow]No output/ directory found.[/]")
        return

    projects = sorted([d for d in out_dir.iterdir() if d.is_dir()])
    if not projects:
        console.print("[yellow]No projects in output/.[/]")
        return

    # Match
    match = None
    for p in projects:
        if project_hint and project_hint.lower() in p.name.lower():
            match = p
            break

    if not match:
        console.print("[bold cyan]Available projects:[/]")
        for i, p in enumerate(projects, 1):
            console.print(f"  {i}. [cyan]{p.name}[/]")
        console.print("\n[dim]Usage: fix <name>[/]")
        return

    console.print(f"\n[bold green]🔧 Fixing:[/] [cyan]{match.name}[/]\n")

    # Delegate to existing fix logic
    try:
        from auto_git_interactive import handle_fix_project
        await handle_fix_project(match.name)
    except ImportError:
        console.print("[red]Could not import fix handler.[/]")


# ──────────────────────────────────────────────────────────────
# REPL (Interactive Loop)
# ──────────────────────────────────────────────────────────────

async def repl():
    """Main interactive read-eval-print loop."""
    while True:
        try:
            raw = Prompt.ask("[bold bright_cyan]auto-git[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]👋 Goodbye![/]")
            break

        action, payload = route_input(raw)

        if action == "noop":
            continue

        elif action == "help":
            show_help()

        elif action == "exit":
            console.print("[cyan]👋 Goodbye![/]")
            break

        elif action == "clear":
            console.clear()

        elif action == "status":
            full_status()

        elif action == "config":
            show_config()

        elif action == "models":
            profile = interactive_model_select()
            if profile:
                console.print(f"[green]Selected profile:[/] [bold]{profile}[/]")

        elif action == "models_ollama":
            show_ollama_models()

        elif action == "run":
            if not payload:
                payload = Prompt.ask("[cyan]Enter your idea[/]")
            if payload:
                # Ask for user-defined goals/requirements
                _extra_reqs = Prompt.ask(
                    "[cyan]Additional requirements/goals? (comma or newline separated, Enter to skip)[/]",
                    default="",
                )
                pub = Confirm.ask("Auto-publish to GitHub?", default=False)
                try:
                    await run_pipeline_with_progress(
                        payload,
                        auto_publish=pub,
                        user_requirements=_extra_reqs or None,
                    )
                except (KeyboardInterrupt, asyncio.CancelledError):
                    console.print("\n[yellow]Pipeline cancelled.[/]")

        elif action == "fix":
            if not payload:
                payload = Prompt.ask("[cyan]Project name to fix[/]")
            if payload:
                try:
                    await handle_fix(payload)
                except (KeyboardInterrupt, asyncio.CancelledError):
                    console.print("\n[yellow]Fix cancelled.[/]")

        elif action == "research":
            if not payload:
                payload = Prompt.ask("[cyan]Research topic[/]")
            if payload:
                try:
                    await _research_only(payload)
                except (KeyboardInterrupt, asyncio.CancelledError):
                    console.print("\n[yellow]Research cancelled.[/]")

        elif action == "debate":
            if not payload:
                payload = Prompt.ask("[cyan]Debate topic[/]")
            if payload:
                try:
                    await _debate_only(payload)
                except (KeyboardInterrupt, asyncio.CancelledError):
                    console.print("\n[yellow]Debate cancelled.[/]")

        elif action == "refine":
            try:
                await handle_refine(payload)
            except (KeyboardInterrupt, asyncio.CancelledError):
                console.print("\n[yellow]Refine cancelled.[/]")

        elif action == "ls":
            handle_ls(payload)

        elif action == "tree":
            handle_tree()

        elif action == "cat":
            handle_cat(payload)

        elif action == "edit":
            handle_edit(payload)

        elif action == "search":
            handle_search(payload)

        elif action == "resume":
            console.print("[yellow]Resume not yet implemented — run a fresh pipeline.[/]")

        elif action == "chat":
            console.print(
                "[dim]I'm Auto-GIT — an autonomous research-to-code pipeline.\n"
                "Type [bold]help[/bold] to see commands, or describe a project idea to get started.[/dim]"
            )

        else:
            console.print(f"[dim]Unknown command: '{payload}'. Type 'help' for options.[/]")


async def _research_only(topic: str):
    """Research mode: search arXiv + web without code gen."""
    console.print(f"\n[bold cyan]🔍 Researching:[/] {topic}\n")
    try:
        from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline
        result = await run_auto_git_pipeline(
            idea=topic,
            use_web_search=True,
            stop_after="problem_extraction",
            interactive=False,
            resume=False,  # Always fresh for research
        )
        if not result:
            console.print("[yellow]Research returned no results.[/]")
            return
        # Try multiple keys — research_summary may not be set by the early stop
        summary = (
            result.get("research_summary")
            or result.get("research_context", {}).get("summary")
            or result.get("research_context", {}).get("synthesis")
            or ""
        )
        if not summary:
            # Build a quick summary from whatever research data exists
            ctx = result.get("research_context") or {}
            papers = ctx.get("papers") or ctx.get("arxiv_results") or []
            web = ctx.get("web_results") or ctx.get("web") or []
            problems = result.get("problems") or []
            parts = []
            if papers:
                parts.append(f"**{len(papers)} papers** found")
            if web:
                parts.append(f"**{len(web)} web results**")
            if problems:
                parts.append("\n**Extracted problems:**\n" + "\n".join(f"- {p}" for p in problems[:5]))
            summary = "\n\n".join(parts) if parts else "No research results found. Try a more specific topic."
        console.print(Panel(Markdown(summary), title="Research Summary", border_style="cyan"))
    except Exception as e:
        console.print(f"[red]Research failed: {e}[/]")
    console.print()


async def _debate_only(topic: str):
    """Debate mode: run through solution selection, no code gen."""
    console.print(f"\n[bold cyan]🗣️  Debating:[/] {topic}\n")
    try:
        from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline
        result = await run_auto_git_pipeline(
            idea=topic,
            use_web_search=True,
            stop_after="solution_selection",
            interactive=False,
            resume=False,  # Always fresh for debate
        )
        sol = result.get("final_solution")
        if sol:
            console.print(Panel(
                f"[bold]{sol.get('approach_name', 'N/A')}[/]\n\n{sol.get('description', '')}",
                title="🏆 Selected Solution",
                border_style="green",
            ))
    except Exception as e:
        console.print(f"[red]Debate failed: {e}[/]")
    console.print()


# ──────────────────────────────────────────────────────────────
# DIRECT CLI COMMANDS  (auto-git run "...", auto-git status, etc.)
# ──────────────────────────────────────────────────────────────

def cli_direct():
    """
    Handle direct command-line invocations:
      auto-git run "idea"
      auto-git status
      auto-git models
    Falls back to interactive REPL when no args given.
    """
    args = sys.argv[1:]

    if not args:
        # No args → interactive mode
        return None  # signal: run interactive

    cmd = args[0].lower()

    if cmd in ("run", "generate", "create"):
        idea = " ".join(args[1:])
        if not idea:
            console.print("[red]Usage: auto-git run <idea>[/]")
            sys.exit(1)
        animate_startup()
        checks = quick_health_check()
        print_status_bar(checks)
        asyncio.run(run_pipeline_with_progress(idea))
        sys.exit(0)

    if cmd == "status":
        animate_startup()
        full_status()
        sys.exit(0)

    if cmd == "models":
        animate_startup()
        show_model_profiles()
        show_ollama_models()
        sys.exit(0)

    if cmd in ("help", "--help", "-h"):
        animate_startup()
        show_help()
        sys.exit(0)

    if cmd == "config":
        animate_startup()
        show_config()
        sys.exit(0)

    if cmd in ("refine", "improve", "enhance"):
        instructions = " ".join(args[1:])
        animate_startup()
        asyncio.run(handle_refine(instructions))
        sys.exit(0)

    if cmd == "tree":
        handle_tree()
        sys.exit(0)

    if cmd in ("ls", "files"):
        handle_ls(" ".join(args[1:]))
        sys.exit(0)

    if cmd in ("cat", "show", "read"):
        handle_cat(" ".join(args[1:]))
        sys.exit(0)

    if cmd in ("search", "grep"):
        handle_search(" ".join(args[1:]))
        sys.exit(0)

    # Unknown → treat as idea
    idea = " ".join(args)
    animate_startup()
    checks = quick_health_check()
    print_status_bar(checks)
    asyncio.run(run_pipeline_with_progress(idea))
    sys.exit(0)


# ──────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────────────

def main():
    """
    Single entry point: `auto-git`

    - With arguments → direct command execution
    - Without arguments → animated banner + interactive REPL
    """
    # Handle direct CLI commands first
    result = cli_direct()
    if result is not None:
        return  # cli_direct handled it and exited

    # Interactive mode
    try:
        animate_startup()
        checks = quick_health_check()
        print_status_bar(checks)
        show_workspace_banner()
        show_help()
        asyncio.run(repl())
    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Goodbye![/]")
    except Exception as e:
        console.print(f"\n[bold red]Fatal error: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
