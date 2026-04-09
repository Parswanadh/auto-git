import textwrap
from pathlib import Path

import pytest

from src.utils.workspace import Workspace


pytestmark = pytest.mark.unit


def _top_repo_map_entry(repo_map: str) -> str:
    for line in repo_map.splitlines():
        if line and not line.startswith("  ") and "  (" in line:
            return line.split("  (", 1)[0].strip()
    return ""


def test_repo_map_focus_query_prioritizes_relevant_module(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        textwrap.dedent(
            """
            from auth_service import AuthService
            from calc_utils import add

            def main():
                svc = AuthService()
                print(svc.login('u', 'p'))
                print(add(1, 2))
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "auth_service.py").write_text(
        textwrap.dedent(
            """
            class AuthService:
                def login(self, username: str, password: str) -> bool:
                    return bool(username and password)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "calc_utils.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n",
        encoding="utf-8",
    )

    ws = Workspace.scan(tmp_path)
    focused = ws.build_repo_map(max_tokens=300, focus_query="implement auth login token flow")

    assert "auth_service.py" in focused
    assert _top_repo_map_entry(focused) in {"main.py", "auth_service.py"}


def test_repo_map_shows_truncation_marker_when_budget_small(tmp_path: Path) -> None:
    for i in range(25):
        (tmp_path / f"m{i}.py").write_text(f"def fn_{i}():\n    return {i}\n", encoding="utf-8")

    ws = Workspace.scan(tmp_path)
    repo_map = ws.build_repo_map(max_tokens=20)

    assert "... and" in repo_map
