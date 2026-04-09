import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.langraph_pipeline import nodes


class _FakeExecutor:
    def __init__(self, project_dir: Path, venv_dir: Path | None = None):
        self.project_dir = Path(project_dir)
        self.venv_dir = Path(venv_dir) if venv_dir else self.project_dir / ".venv"
        self.test_results = {"execution_errors": []}

    def create_environment(self) -> bool:
        return True

    def install_dependencies(self) -> bool:
        return True

    def get_python_executable(self) -> Path:
        return Path(sys.executable)


def _fake_build_cached_venv_dir(cache_root: Path, requirements_text: str) -> Path:
    return cache_root / "py-test-cached"


def _fake_subprocess_run(*args, **kwargs):
    return SimpleNamespace(returncode=0, stdout="ok", stderr="")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_save_smoke_reuses_cached_env_without_pip_step():
    with tempfile.TemporaryDirectory(prefix="autogit-smoke-test-") as tmpdir:
        project_dir = Path(tmpdir)
        (project_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (project_dir / "requirements.txt").write_text("requests\n", encoding="utf-8")

        with patch("src.utils.code_executor.CodeExecutor", _FakeExecutor), patch(
            "src.utils.code_executor.build_cached_venv_dir", _fake_build_cached_venv_dir
        ), patch("subprocess.run", side_effect=_fake_subprocess_run):
            result = await nodes._post_save_smoke_test(str(project_dir))

    assert result["passed"] is True
    steps = result.get("steps", [])
    assert any(s.get("step") == "create/reuse cached venv" and s.get("passed") for s in steps)
    assert any(s.get("step") == "install dependencies" and s.get("passed") for s in steps)
    assert not any(s.get("step") == "pip install -r requirements.txt" for s in steps)
