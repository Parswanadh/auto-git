"""Checkpointer provider factory for Auto-GIT workflows.

Provides a single entrypoint to create a checkpoint saver with optional
provider selection (sqlite, memory, local, redis). This keeps workflow code
agnostic to the concrete persistence backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import os
import sqlite3

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver


class AsyncSqliteSaver(SqliteSaver):
    """Async adapter for SqliteSaver used by workflow.astream()."""

    async def aget_tuple(self, config):
        return self.get_tuple(config)

    async def alist(self, config, *, filter=None, before=None, limit=None):
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(self, config, checkpoint, metadata, new_versions):
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id):
        return self.put_writes(config, writes, task_id)


@dataclass
class CheckpointerBundle:
    provider: str
    checkpointer: Any
    close: Optional[Callable[[], None]] = None
    location: str = ""


def create_checkpointer(provider: Optional[str] = None, logs_dir: str = "logs") -> CheckpointerBundle:
    """Create a checkpointer bundle from provider name.

    Supported providers:
    - sqlite (default): disk-backed local sqlite db
    - memory: in-memory checkpointer
    - local: local file checkpointer
    - redis: redis checkpointer
    """
    selected = (provider or os.getenv("AUTOGIT_CHECKPOINTER_PROVIDER", "sqlite")).strip().lower()

    if selected == "memory":
        return CheckpointerBundle(provider="memory", checkpointer=MemorySaver(), location="in-memory")

    if selected == "local":
        from .local_checkpointer import LocalFileCheckpointer

        checkpoint_dir = os.path.join(logs_dir, "checkpoints_local")
        cp = LocalFileCheckpointer(checkpoint_dir=checkpoint_dir)
        return CheckpointerBundle(provider="local", checkpointer=cp, location=checkpoint_dir)

    if selected == "redis":
        from .redis_checkpointer import RedisCheckpointSaver

        redis_url = os.getenv("AUTOGIT_REDIS_URL", "redis://localhost:6379")
        cp = RedisCheckpointSaver(redis_url=redis_url)
        return CheckpointerBundle(provider="redis", checkpointer=cp, location=redis_url)

    # default: sqlite
    os.makedirs(logs_dir, exist_ok=True)
    checkpoint_db = os.path.join(logs_dir, "pipeline_checkpoints.db")
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    cp = AsyncSqliteSaver(conn)
    return CheckpointerBundle(
        provider="sqlite",
        checkpointer=cp,
        close=conn.close,
        location=checkpoint_db,
    )


def load_existing_checkpoint(checkpointer: Any, config: dict) -> Any:
    """Fetch existing checkpoint from provider when available."""
    try:
        if hasattr(checkpointer, "get"):
            return checkpointer.get(config)
    except Exception:
        return None
    return None
