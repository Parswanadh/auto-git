"""Context offload helpers for long-running pipeline loops.

Stores large text/list payloads to disk and returns compact inline previews with
stable pointer metadata. Used to reduce prompt/state bloat while preserving
recoverability.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _safe_label(label: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", (label or "payload").strip())
    return cleaned[:80] or "payload"


def _write_payload_file(content: str, label: str, output_dir: str) -> Optional[str]:
    try:
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{_safe_label(label)}_{ts}.txt"
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
    except Exception:
        return None


def offload_text(
    text: str,
    *,
    label: str,
    output_dir: str,
    threshold_chars: int = 12000,
    preview_chars: int = 1400,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Offload long text and return preview + pointer metadata."""
    content = str(text or "")
    if len(content) <= threshold_chars:
        return content, None

    path = _write_payload_file(content, label=label, output_dir=output_dir)
    if not path:
        trimmed = content[:preview_chars] + f"\n... [TRUNCATED {len(content) - preview_chars} chars]"
        return trimmed, None

    head = content[: preview_chars // 2]
    tail = content[-(preview_chars // 2) :]
    preview = (
        f"{head}\n\n"
        f"... [OFFLOADED {len(content)} chars to {path}] ...\n\n"
        f"{tail}"
    )
    ref = {
        "label": label,
        "path": path,
        "chars": len(content),
        "offloaded_at": datetime.now().isoformat(),
    }
    return preview, ref


def offload_state_fields(
    state_patch: Dict[str, Any],
    *,
    node_name: str,
    output_dir: str = "logs/offloaded_context",
    fields: Optional[List[str]] = None,
    threshold_chars: int = 12000,
) -> Dict[str, Any]:
    """Offload selected large fields from a node patch.

    Adds/extends state_patch['context_offload_refs'] when offloading occurs.
    """
    if not isinstance(state_patch, dict):
        return {}

    selected_fields = fields or ["research_summary", "implementation_notes", "todo_generation_notes"]
    updates: Dict[str, Any] = {}
    refs: List[Dict[str, Any]] = list(state_patch.get("context_offload_refs", []))

    for field in selected_fields:
        value = state_patch.get(field)
        if isinstance(value, str) and len(value) > threshold_chars:
            preview, ref = offload_text(
                value,
                label=f"{node_name}_{field}",
                output_dir=output_dir,
                threshold_chars=threshold_chars,
            )
            updates[field] = preview
            if ref:
                refs.append(ref)

    if refs:
        updates["context_offload_refs"] = refs

    return updates


def compact_todos_with_pointer(
    todos: List[Dict[str, Any]],
    *,
    output_dir: str = "logs/offloaded_context",
    max_inline_items: int = 80,
) -> Dict[str, Any]:
    """If todo list is very large, persist the full list and keep a compact inline copy."""
    if not isinstance(todos, list) or len(todos) <= max_inline_items:
        return {}

    content = json.dumps(todos, ensure_ascii=True, indent=2)
    path = _write_payload_file(content, label="pipeline_todos", output_dir=output_dir)
    if not path:
        return {}

    return {
        "pipeline_todos": todos[:max_inline_items],
        "todo_context_pointer": path,
        "todo_generation_notes": (
            f"Large todo list compacted to first {max_inline_items} items. "
            f"Full list persisted at: {path}"
        ),
        "context_offload_refs": [{
            "label": "pipeline_todos",
            "path": path,
            "items": len(todos),
            "offloaded_at": datetime.now().isoformat(),
        }],
    }


def restore_todo_context_if_missing(state: Dict[str, Any]) -> Dict[str, Any]:
    """Restore minimal todo context note when compaction removed inline todos."""
    todos = state.get("pipeline_todos")
    pointer = state.get("todo_context_pointer")
    if isinstance(todos, list) and todos:
        return {}
    if not pointer or not isinstance(pointer, str):
        return {}

    note = (
        f"Todo context restored from pointer: {pointer}. "
        "Inline todo list was compacted; keep verification focused on gate completion and critical items."
    )
    updates = {
        "todo_generation_notes": note,
    }
    if not isinstance(state.get("warnings"), list):
        updates["warnings"] = [note]
    else:
        updates["warnings"] = list(state.get("warnings", [])) + [note]
    return updates
