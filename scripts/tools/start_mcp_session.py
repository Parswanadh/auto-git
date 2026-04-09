#!/usr/bin/env python3
"""Start VS Code with MCP-ready environment and preflight checks.

Usage:
  python scripts/tools/start_mcp_session.py
  python scripts/tools/start_mcp_session.py --workspace D:/Projects/auto-git
  python scripts/tools/start_mcp_session.py --check-only
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple


def parse_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def run_quick_check(command: List[str], timeout: int = 20) -> Tuple[bool, str]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out.strip()
    except Exception as exc:
        return False, str(exc)


def preflight(workspace: Path, env: Dict[str, str]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    venv = workspace / ".venv" / "Scripts"

    git_exe = venv / "mcp-server-git.exe"
    sqlite_exe = venv / "mcp-server-sqlite.exe"

    if not git_exe.exists():
        errors.append(f"Missing executable: {git_exe}")
    else:
        ok, msg = run_quick_check([str(git_exe), "--help"])
        if not ok:
            errors.append(f"Git MCP check failed: {msg}")

    if not sqlite_exe.exists():
        errors.append(f"Missing executable: {sqlite_exe}")
    else:
        ok, msg = run_quick_check([str(sqlite_exe), "--help"])
        if not ok:
            errors.append(f"SQLite MCP check failed: {msg}")

    if shutil.which("npx") is None:
        errors.append("`npx` is not available on PATH")

    required = ["CONTEXT7_API_KEY", "TAVILY_API_KEY", "POSTGRES_DSN"]
    missing = [k for k in required if not (env.get(k) or os.environ.get(k))]
    if missing:
        warnings.append(
            "Missing MCP environment variables (API-backed MCPs may stay stopped): "
            + ", ".join(missing)
        )

    return errors, warnings


def launch_vscode(workspace: Path, env: Dict[str, str], trigger_autostart: bool = True) -> int:
    code_cmd = shutil.which("code")
    if code_cmd is None:
        print("ERROR: VS Code CLI `code` was not found on PATH.")
        print("Open Command Palette in VS Code and run: Shell Command: Install 'code' command in PATH")
        return 1

    child_env = os.environ.copy()
    child_env.update(env)

    proc = subprocess.run([code_cmd, str(workspace), "--reuse-window"], env=child_env, check=False)

    # VS Code MCP autostart is triggered by configuration changes.
    # Touch the workspace mcp.json after launch to force a change event.
    if trigger_autostart:
        mcp_config = workspace / ".vscode" / "mcp.json"
        if mcp_config.exists():
            time.sleep(2)
            mcp_config.touch()

    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Start VS Code with MCP auto-start preflight")
    parser.add_argument("--workspace", default=str(Path.cwd()), help="Workspace folder")
    parser.add_argument("--check-only", action="store_true", help="Only run preflight checks")
    parser.add_argument(
        "--no-trigger-autostart",
        action="store_true",
        help="Do not touch .vscode/mcp.json after launching VS Code",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    env_file = workspace / ".vscode" / "mcp.env"
    env_template = workspace / ".vscode" / "mcp.env.example"
    if not env_file.exists() and env_template.exists():
        env_file.write_text(env_template.read_text(encoding="utf-8"), encoding="utf-8")

    env = parse_env_file(env_file)

    errors, warnings = preflight(workspace, env)
    print("MCP preflight report")
    print("===================")
    print(f"Workspace: {workspace}")
    print(f"Env file: {env_file} ({'found' if env_file.exists() else 'missing'})")

    if errors:
        print("\nErrors found:")
        for item in errors:
            print(f"- {item}")
    if warnings:
        print("\nWarnings:")
        for item in warnings:
            print(f"- {item}")
    if not errors and not warnings:
        print("\nAll checks passed.")

    if args.check_only:
        return 0 if not errors else 2

    if errors:
        print("\nBlocking errors detected. Not launching VS Code.")
        return 2

    print("\nLaunching VS Code with MCP environment...")
    return launch_vscode(workspace, env, trigger_autostart=not args.no_trigger_autostart)


if __name__ == "__main__":
    sys.exit(main())
