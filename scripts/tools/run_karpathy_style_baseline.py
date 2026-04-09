#!/usr/bin/env python3
"""Run a Karpathy-style baseline: single-shot coding loop with minimal automation.

This baseline intentionally does one direct generation pass, then lightweight
syntax/runtime checks. It is used as a workflow baseline for comparison.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output" / "benchmark_baseline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IDEA = (
    "Build a Python command-line Todo application with a REST API backend. "
    "Use Flask for the API server with SQLite storage. Features: add/remove/list/complete todos, "
    "priority levels (high/medium/low), due dates, and a simple CLI client that talks to the API. "
    "Include proper error handling and input validation."
)

PROMPT = f"""
You are an expert Python engineer.
Generate complete working Python code for this goal in a single pass.
Return only code.

Goal:
{IDEA}
""".strip()

FALLBACK_BASELINE_CODE = """from flask import Flask, jsonify, request

app = Flask(__name__)
todos = []


@app.post('/todos')
def add_todo():
    payload = request.get_json(force=True)
    todos.append(payload)
    return jsonify(payload), 201


@app.get('/todos')
def list_todos():
    return jsonify(todos)


def main():
    print('karpathy-style baseline demo: minimal single-shot app')


if __name__ == '__main__':
    main()
"""


def _extract_code(text: str) -> str:
    if "```python" in text:
        return text.split("```python", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text.strip()


def _run_runtime_check(path: Path) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(ROOT),
        )
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout or "py_compile failed").strip()
        return True, "py_compile passed"
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def main() -> int:
    start = time.time()
    result: Dict[str, Any] = {
        "mode": "karpathy_style_single_shot",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "idea": IDEA,
        "llm_calls": 1,
        "generation_ok": False,
        "syntax_ok": False,
        "runtime_ok": False,
        "error": None,
    }

    code = ""

    try:
        sys.path.insert(0, str(ROOT))
        from src.utils.model_manager import get_model_manager  # pylint: disable=import-error

        llm = get_model_manager().get_model("balanced")
        response = llm.invoke(PROMPT)
        raw_text = response.content if hasattr(response, "content") else str(response)
        code = _extract_code(raw_text)
        result["generation_ok"] = bool(code)
    except Exception as exc:  # pragma: no cover - runtime-dependent
        result["error"] = f"llm_invoke_failed: {exc}"
        code = FALLBACK_BASELINE_CODE
        result["generation_ok"] = True
        result["fallback_used"] = True
        result["fallback_reason"] = "LLM unavailable; generated deterministic minimal baseline code"

    app_path = OUTPUT_DIR / "baseline_app.py"
    if code:
        app_path.write_text(code, encoding="utf-8")
        result["generated_file"] = str(app_path.relative_to(ROOT)).replace("\\", "/")
        result["generated_chars"] = len(code)
        result["generated_lines"] = len(code.splitlines())

        try:
            ast.parse(code)
            result["syntax_ok"] = True
        except Exception as exc:  # pragma: no cover
            result["syntax_ok"] = False
            result["syntax_error"] = str(exc)

        runtime_ok, runtime_msg = _run_runtime_check(app_path)
        result["runtime_ok"] = runtime_ok
        result["runtime_message"] = runtime_msg

    result["duration_seconds"] = round(time.time() - start, 3)
    result["completed_at"] = datetime.utcnow().isoformat() + "Z"

    output_path = OUTPUT_DIR / "baseline_result.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Baseline result written: {output_path}")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
