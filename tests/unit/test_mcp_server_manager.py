"""Unit tests for MCP transport behavior in claude_code_cli MCPServerManager."""

import asyncio
import io
import json
import os
from pathlib import Path

from src.cli.claude_code_cli import MCPServerManager


class _FakeProc:
    def __init__(self, stdout_text: str = ""):
        self.stdin = io.StringIO()
        self.stdout = io.StringIO(stdout_text)
        self.stderr = io.StringIO("")

    def poll(self):
        return None


def _framed_response(payload: dict) -> str:
    body = json.dumps(payload)
    return f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"


def test_frame_message_uses_content_length():
    mgr = MCPServerManager()
    framed = mgr._frame_message({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}})
    assert framed.startswith("Content-Length:")
    assert "\r\n\r\n" in framed


def test_send_request_reads_correlated_response():
    async def _run():
        mgr = MCPServerManager()
        response = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        proc = _FakeProc(_framed_response(response))
        out = await mgr._send_request(proc, "ping", {}, timeout=2, retries=1)
        assert out is not None
        assert out.get("id") == 1
        assert out.get("result", {}).get("ok") is True

    asyncio.run(_run())


def test_send_request_rejects_mismatched_id():
    async def _run():
        mgr = MCPServerManager()
        response = {"jsonrpc": "2.0", "id": 999, "result": {"ok": True}}
        proc = _FakeProc(_framed_response(response))
        out = await mgr._send_request(proc, "ping", {}, timeout=1, retries=1)
        assert out is None

    asyncio.run(_run())


def test_builtin_read_file_blocks_path_traversal():
    async def _run():
        mgr = MCPServerManager()
        parent = Path(os.getcwd()).parent
        blocked = await mgr._execute_builtin("read_file", {"path": str(parent / "outside.txt")})
        assert blocked.get("status") == "error"
        assert "Path traversal blocked" in blocked.get("error", "")

    asyncio.run(_run())


def test_builtin_write_and_read_within_workspace():
    async def _run():
        mgr = MCPServerManager()
        target = Path(os.getcwd()) / "tmp_mcp_test_file.txt"
        try:
            write = await mgr._execute_builtin("write_file", {"path": str(target), "content": "hello"})
            assert write.get("status") == "success"
            read = await mgr._execute_builtin("read_file", {"path": str(target)})
            assert read.get("status") == "success"
            assert read.get("result") == "hello"
        finally:
            if target.exists():
                target.unlink()

    asyncio.run(_run())
