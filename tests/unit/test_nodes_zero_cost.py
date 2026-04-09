"""
Zero-cost unit tests for Auto-GIT pipeline nodes and utilities.

These tests NEVER call real LLM APIs — all LLM interactions are mocked
with FakeLLM from conftest.py. They validate:

1. State contracts — nodes accept/return correct state shapes
2. Pure functions — _clean_requirements_txt, _build_requirements_from_imports, etc.
3. Edge cases — empty inputs, None values, malformed JSON
4. Silent failure prevention — nodes must report errors, not swallow them
5. Node behavior — correct routing, fallback logic, error accumulation

Run with: pytest tests/unit/test_nodes_zero_cost.py -v
Cost: $0.00 (no API calls)
"""

import pytest
import sys
import os
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 1: State Contract Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestStateContracts:
    """Verify state factory produces valid state dicts."""

    def test_make_state_has_all_required_fields(self, make_state):
        """State must have all fields that nodes read via state.get()."""
        state = make_state()
        required_keys = [
            "idea", "requirements", "research_context", "problems",
            "generated_code", "test_results", "tests_passed", "fix_attempts",
            "max_fix_attempts", "errors", "warnings", "current_stage",
            "debate_rounds", "final_solution", "published",
            "_prev_fix_strategies", "_persistent_error_tracker",
        ]
        for key in required_keys:
            assert key in state, f"Missing required state key: {key}"

    def test_make_state_overrides(self, make_state):
        """Overrides must replace default values."""
        state = make_state(idea="Build a web scraper", fix_attempts=3)
        assert state["idea"] == "Build a web scraper"
        assert state["fix_attempts"] == 3

    def test_make_state_defaults_are_safe(self, make_state):
        """Default state should not trigger None errors in any node."""
        state = make_state()
        assert state["errors"] == []
        assert state["warnings"] == []
        assert state["debate_rounds"] == []
        assert state["generated_code"] == {}
        assert state["tests_passed"] is False
        assert state["fix_attempts"] == 0

    def test_make_state_list_fields_are_mutable(self, make_state):
        """List fields must be independent copies, not shared references."""
        s1 = make_state()
        s2 = make_state()
        s1["errors"].append("test error")
        assert s2["errors"] == [], "States must not share mutable references"


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 2: _clean_requirements_txt (pure function, zero cost)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestCleanRequirementsTxt:
    """Test the requirements.txt cleaner — a pure function with no LLM calls."""

    @pytest.fixture(autouse=True)
    def import_function(self):
        from src.langraph_pipeline.nodes import _clean_requirements_txt
        self.clean = _clean_requirements_txt

    def test_empty_input(self):
        assert self.clean("") == ""
        assert self.clean(None) is None

    def test_strips_stdlib_modules(self):
        req = "os\nsys\njson\nrequests\n"
        result = self.clean(req)
        assert "os" not in result.split("\n")
        assert "sys" not in result.split("\n")
        assert "json" not in result.split("\n")
        assert "requests" in result

    def test_keeps_third_party_packages(self):
        req = "flask>=2.0\nnumpy\npandas==1.5.3\n"
        result = self.clean(req)
        assert "flask>=2.0" in result
        assert "numpy" in result
        assert "pandas==1.5.3" in result

    def test_strips_editable_installs(self):
        req = "flask\n-e git+https://github.com/user/repo.git\nrequests\n"
        result = self.clean(req)
        assert "-e" not in result
        assert "flask" in result

    def test_strips_internal_modules(self):
        req = "_thread\n_collections_abc\nrequests\n"
        result = self.clean(req)
        assert "_thread" not in result
        assert "_collections_abc" not in result
        assert "requests" in result

    def test_strips_non_installable_placeholder_package(self):
        req = "flask\ndatabase\nrequests\n"
        result = self.clean(req)
        lines = [l.strip() for l in result.split("\n") if l.strip() and not l.startswith("#")]
        assert "database" not in lines
        assert "flask" in lines
        assert "requests" in lines

    def test_strips_non_installable_lockingmiddleware_package(self):
        req = "flask\nLockingMiddleware\nrequests\n"
        result = self.clean(req)
        lines = [l.strip().lower() for l in result.split("\n") if l.strip() and not l.startswith("#")]
        assert "lockingmiddleware" not in lines
        assert "flask" in lines
        assert "requests" in lines

    def test_strips_local_class_name_from_requirements_when_sources_available(self):
        req = "flask\nLockingMiddleware\nrequests\n"
        py = {
            "main.py": "import flask\nimport requests\n",
            "middleware.py": "class LockingMiddleware:\n    pass\n",
        }
        result = self.clean(req, py_sources=py)
        lines = [l.strip().lower() for l in result.split("\n") if l.strip() and not l.startswith("#")]
        assert "lockingmiddleware" not in lines
        assert "flask" in lines
        assert "requests" in lines

    def test_preserves_comments(self):
        req = "# Core dependencies\nflask\n# Utils\nrequests\n"
        result = self.clean(req)
        assert "# Core dependencies" in result
        assert "# Utils" in result

    def test_renames_import_aliases(self):
        """sklearn -> scikit-learn, yaml -> pyyaml, etc."""
        req = "sklearn>=1.2\nyaml\ncv2\nnacl\n"
        result = self.clean(req)
        assert "scikit-learn" in result
        assert "pyyaml" in result
        assert "opencv-python" in result
        assert "pynacl" in result

    def test_strips_multi_word_invalid_lines(self):
        """Lines like 'torch schedulers' are not valid pip specifiers."""
        req = "flask\ntorch schedulers\nrequests\n"
        result = self.clean(req)
        assert "torch schedulers" not in result

    def test_with_py_sources_filters_unused(self):
        """When py_sources provided, only keep packages actually imported."""
        req = "flask\nnumpy\npandas\nrequests\n"
        py = {"main.py": "import flask\nimport requests\n"}
        result = self.clean(req, py_sources=py)
        assert "flask" in result
        assert "requests" in result
        # numpy and pandas are NOT imported → should be filtered
        lines = [l.strip() for l in result.split("\n") if l.strip() and not l.startswith("#")]
        assert "numpy" not in lines
        assert "pandas" not in lines


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 3: _build_requirements_from_imports (pure function)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBuildRequirementsFromImports:
    """Test deterministic requirements builder — no LLM needed."""

    @pytest.fixture(autouse=True)
    def import_function(self):
        from src.langraph_pipeline.nodes import _build_requirements_from_imports
        self.build = _build_requirements_from_imports

    def test_empty_sources(self):
        assert self.build({}) == ""
        assert self.build(None) == ""

    def test_detects_third_party_imports(self):
        sources = {"main.py": "import flask\nimport numpy\nfrom requests import get\n"}
        result = self.build(sources)
        assert "flask" in result
        assert "numpy" in result
        assert "requests" in result

    def test_excludes_stdlib(self):
        sources = {"main.py": "import os\nimport sys\nimport json\nimport flask\n"}
        result = self.build(sources)
        lines = result.strip().split("\n")
        assert "os" not in lines
        assert "sys" not in lines
        assert "flask" in lines

    def test_excludes_local_project_modules(self):
        """Files in the project should not appear in requirements."""
        sources = {
            "main.py": "import flask\nfrom utils import helper\n",
            "utils.py": "def helper(): pass\n",
        }
        result = self.build(sources)
        assert "utils" not in result.split("\n")
        assert "flask" in result

    def test_maps_aliases_to_pip_names(self):
        sources = {"main.py": "import cv2\nfrom PIL import Image\nimport sklearn\n"}
        result = self.build(sources)
        assert "opencv-python" in result
        assert "pillow" in result
        assert "scikit-learn" in result

    def test_deterministic_output(self):
        """Output should be sorted and stable across calls."""
        sources = {"main.py": "import numpy\nimport flask\nimport requests\n"}
        r1 = self.build(sources)
        r2 = self.build(sources)
        assert r1 == r2
        lines = r1.strip().split("\n")
        assert lines == sorted(lines, key=str.lower)


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 3b: _ensure_requirements_complete (pure function, rollback-proof)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestEnsureRequirementsComplete:
    """Test deterministic requirements completeness checker — no LLM needed."""

    @pytest.fixture(autouse=True)
    def import_function(self):
        from src.langraph_pipeline.nodes import _ensure_requirements_complete
        self.ensure = _ensure_requirements_complete

    def test_no_py_files_returns_unchanged(self):
        files = {"requirements.txt": "flask\n", "README.md": "# Hello"}
        result = self.ensure(files)
        assert result["requirements.txt"] == "flask\n"

    def test_adds_missing_packages(self):
        """If code imports flask, sqlalchemy, typer but requirements.txt only has flask."""
        files = {
            "main.py": "import flask\nimport sqlalchemy\nimport typer\n",
            "requirements.txt": "flask>=3.0\n",
        }
        result = self.ensure(files)
        req = result["requirements.txt"]
        assert "sqlalchemy" in req
        assert "typer" in req
        assert "flask" in req  # original preserved

    def test_does_not_duplicate_existing(self):
        """Should not add packages that already exist in requirements.txt."""
        files = {
            "main.py": "import flask\nimport requests\n",
            "requirements.txt": "flask>=3.0\nrequests>=2.32\n",
        }
        result = self.ensure(files)
        req = result["requirements.txt"]
        assert req.count("flask") == 1
        assert req.count("requests") == 1

    def test_handles_alias_mapping(self):
        """PIL -> pillow, cv2 -> opencv-python, etc."""
        files = {
            "main.py": "from PIL import Image\nimport cv2\nimport sklearn\nfrom argon2 import PasswordHasher\n",
            "requirements.txt": "",
        }
        result = self.ensure(files)
        req = result["requirements.txt"]
        assert "pillow" in req
        assert "opencv-python" in req
        assert "scikit-learn" in req
        assert "argon2-cffi" in req

    def test_excludes_stdlib_modules(self):
        """os, sys, json, etc. should never be added to requirements.txt."""
        files = {
            "main.py": "import os\nimport sys\nimport json\nimport flask\n",
            "requirements.txt": "",
        }
        result = self.ensure(files)
        req = result["requirements.txt"]
        assert "os" not in req.split("\n")
        assert "sys" not in req.split("\n")
        assert "flask" in req

    def test_excludes_local_project_modules(self):
        """Imports from other project files should not appear in requirements."""
        files = {
            "main.py": "import flask\nfrom utils import helper\nfrom config import Config\n",
            "utils.py": "def helper(): pass\n",
            "config.py": "class Config: pass\n",
            "requirements.txt": "",
        }
        result = self.ensure(files)
        req = result["requirements.txt"]
        assert "utils" not in req.split("\n")
        assert "config" not in req.split("\n")
        assert "flask" in req

    def test_does_not_mutate_input(self):
        """Must not modify the caller's dictionary."""
        files = {
            "main.py": "import flask\nimport typer\n",
            "requirements.txt": "flask\n",
        }
        original_req = files["requirements.txt"]
        self.ensure(files)
        assert files["requirements.txt"] == original_req

    def test_creates_requirements_if_missing(self):
        """If no requirements.txt exists, should create one."""
        files = {
            "main.py": "import flask\nimport requests\n",
        }
        result = self.ensure(files)
        assert "requirements.txt" in result
        assert "flask" in result["requirements.txt"]
        assert "requests" in result["requirements.txt"]

    def test_handles_version_specifiers_in_existing(self):
        """Should recognize 'flask>=3.0' as 'flask' already present."""
        files = {
            "main.py": "import flask\nimport sqlalchemy\n",
            "requirements.txt": "flask>=3.0.0\nrich>=13.7.0\n",
        }
        result = self.ensure(files)
        req = result["requirements.txt"]
        # flask should not be duplicated
        assert req.count("flask") == 1
        # sqlalchemy should be added
        assert "sqlalchemy" in req

    def test_handles_hyphenated_vs_underscored_names(self):
        """python-dateutil vs python_dateutil should be treated as same."""
        files = {
            "main.py": "import dateutil\n",
            "requirements.txt": "python-dateutil>=2.8\n",
        }
        result = self.ensure(files)
        req = result["requirements.txt"]
        # Should NOT add python-dateutil again since it's already there
        assert req.count("dateutil") == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 4: Requirements Extraction Node (mocked LLM)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestRequirementsExtractionNode:
    """Test requirements_extraction_node with FakeLLM — zero API calls."""

    @pytest.fixture(autouse=True)
    def setup_patches(self):
        """Patch all LLM calls and Rich console output."""
        from tests.conftest import FakeLLM
        self.fake_llm = FakeLLM()
        self.patches = [
            patch("src.langraph_pipeline.nodes.get_fallback_llm", return_value=self.fake_llm),
            patch("src.langraph_pipeline.nodes.Console"),
        ]
        for p in self.patches:
            p.start()
        yield
        for p in self.patches:
            p.stop()

    @pytest.mark.asyncio
    async def test_empty_idea_skips(self, make_state):
        from src.langraph_pipeline.nodes import requirements_extraction_node
        state = make_state(idea="")
        result = await requirements_extraction_node(state)
        assert result["current_stage"] == "requirements_skipped"
        assert self.fake_llm.call_count == 0, "Should NOT call LLM when idea is empty"

    @pytest.mark.asyncio
    async def test_valid_json_response_extracts_requirements(self, make_state):
        from src.langraph_pipeline.nodes import requirements_extraction_node
        self.fake_llm._responses = [json.dumps({
            "project_type": "cli_tool",
            "complexity": "simple",
            "core_components": ["calculator", "CLI parser"],
            "key_features": ["add", "subtract", "multiply", "divide"],
            "data_flow": "user input -> parse -> compute -> display",
            "external_deps": [],
            "test_scenarios": [{"name": "add test", "input": "1 + 2", "expected": "3"}],
            "success_criteria": "Correct arithmetic for all operations",
            "risk_areas": ["division by zero"],
        })]
        state = make_state(idea="Build a calculator")
        result = await requirements_extraction_node(state)
        assert result["current_stage"] == "requirements_extracted"
        assert result["requirements"]["project_type"] == "cli_tool"
        assert result["requirements"]["complexity"] == "simple"

    @pytest.mark.asyncio
    async def test_malformed_json_graceful_fallback(self, make_state):
        from src.langraph_pipeline.nodes import requirements_extraction_node
        self.fake_llm._responses = ["This is not JSON at all"]
        state = make_state(idea="Build something")
        result = await requirements_extraction_node(state)
        # Should not crash — should return failure stage
        assert "fail" in result["current_stage"].lower() or "skip" in result["current_stage"].lower()

    @pytest.mark.asyncio
    async def test_json_with_markdown_fences(self, make_state):
        from src.langraph_pipeline.nodes import requirements_extraction_node
        self.fake_llm._responses = ['```json\n{"project_type":"web_api","complexity":"moderate",'
                                     '"core_components":["api"],"key_features":["REST"],'
                                     '"data_flow":"req->resp","external_deps":["flask"],'
                                     '"test_scenarios":[],"success_criteria":"works",'
                                     '"risk_areas":[]}\n```']
        state = make_state(idea="Build an API")
        result = await requirements_extraction_node(state)
        assert result["current_stage"] == "requirements_extracted"

    @pytest.mark.asyncio
    async def test_json_with_trailing_noise_uses_fallback_extractor(self, make_state):
        from src.langraph_pipeline.nodes import requirements_extraction_node
        self.fake_llm._responses = [
            '{"project_type":"cli_tool","complexity":"simple",'
            '"core_components":["calculator"],"key_features":["add"],'
            '"data_flow":"input->compute->output","external_deps":[],"test_scenarios":[],'
            '"success_criteria":"works","risk_areas":[]} trailing non-json text'
        ]
        state = make_state(idea="Build a calculator")
        result = await requirements_extraction_node(state)
        assert result["current_stage"] == "requirements_extracted"
        assert result["requirements"].get("project_type") == "cli_tool"

    @pytest.mark.asyncio
    async def test_json_after_thinking_tag_uses_fallback_extractor(self, make_state):
        from src.langraph_pipeline.nodes import requirements_extraction_node
        self.fake_llm._responses = [
            '<think>reasoning omitted</think>{"project_type":"web_api","complexity":"moderate",'
            '"core_components":["api"],"key_features":["crud"],'
            '"data_flow":"req->db->resp","external_deps":["flask"],"test_scenarios":[],'
            '"success_criteria":"crud works","risk_areas":[]}'
        ]
        state = make_state(idea="Build an API")
        result = await requirements_extraction_node(state)
        assert result["current_stage"] == "requirements_extracted"
        assert result["requirements"].get("project_type") == "web_api"

    @pytest.mark.asyncio
    async def test_exception_returns_structured_failure_payload(self, make_state):
        from src.langraph_pipeline.nodes import requirements_extraction_node

        state = make_state(idea="Build a calculator")
        with patch("src.langraph_pipeline.nodes.get_fallback_llm", side_effect=RuntimeError("llm unavailable")):
            result = await requirements_extraction_node(state)

        assert result["current_stage"] == "requirements_extraction_failed"
        assert any("requirements_extraction_failed:RuntimeError:llm unavailable" in e for e in result.get("errors", []))
        assert any("Requirements extraction failed; continuing with raw idea" in w for w in result.get("warnings", []))

        err = result.get("requirements_extraction_error", {})
        assert err.get("node") == "requirements_extraction"
        assert err.get("exception_type") == "RuntimeError"
        assert err.get("message") == "llm unavailable"
        assert err.get("retryable") is True
        assert isinstance(err.get("timestamp"), str)


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 5: Silent Failure Detection
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestSilentFailurePrevention:
    """Ensure nodes don't silently swallow errors."""

    def test_state_errors_list_is_appendable(self, make_state):
        """Errors list must support append (some nodes do state['errors'].append())."""
        state = make_state()
        state["errors"].append("test error")
        assert len(state["errors"]) == 1

    def test_empty_generated_code_is_detectable(self, make_state):
        """Code generation returning {} should be distinguishable from success."""
        state = make_state()
        assert state["generated_code"] == {}
        # After successful code gen, it should have 'files' key
        state["generated_code"] = {"files": {"main.py": "print('hello')"}}
        assert "files" in state["generated_code"]

    def test_tests_passed_defaults_false(self, make_state):
        """tests_passed must default to False — S22 bug was it defaulting to True."""
        state = make_state()
        assert state["tests_passed"] is False, \
            "tests_passed must default to False (S22 bug: was True, causing publish of broken code)"


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 6: Incomplete Artifact Detection (pure function)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestIncompleteArtifactDetection:
    """Test _find_incomplete_artifacts — detects placeholder/skeleton code."""

    @pytest.fixture(autouse=True)
    def import_function(self):
        from src.langraph_pipeline.nodes import _find_incomplete_artifacts
        self.find = _find_incomplete_artifacts

    def test_clean_code_returns_empty(self):
        files = {"main.py": "def add(a, b): return a + b\n"}
        assert self.find(files) == []

    def test_detects_skeleton_markers(self):
        files = {"main.py": "# AUTO-GENERATED SKELETON\ndef foo(): pass\n"}
        result = self.find(files)
        assert len(result) > 0
        assert "main.py" in result[0]

    def test_detects_not_implemented(self):
        files = {"engine.py": "def compute():\n    raise NotImplementedError\n"}
        result = self.find(files)
        assert len(result) > 0

    def test_detects_todo_pass(self):
        files = {"handler.py": "def handle():\n    pass  # TODO: implement\n"}
        result = self.find(files)
        assert len(result) > 0

    def test_handles_missing_ast_str_node(self, monkeypatch):
        import ast as _ast

        if hasattr(_ast, "Str"):
            monkeypatch.delattr(_ast, "Str")

        files = {"main.py": "\"\"\"Doc\"\"\"\n\ndef run():\n    return 0\n"}
        result = self.find(files)
        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 7: FakeLLM fixture tests (verify our test infrastructure works)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFakeLLM:
    """Verify FakeLLM works correctly — meta-tests for test infrastructure."""

    @pytest.mark.asyncio
    async def test_single_response_reused(self):
        from tests.conftest import FakeLLM
        llm = FakeLLM("hello")
        r1 = await llm.ainvoke([])
        r2 = await llm.ainvoke([])
        assert r1.content == "hello"
        assert r2.content == "hello"
        assert llm.call_count == 2

    @pytest.mark.asyncio
    async def test_sequential_responses(self):
        from tests.conftest import FakeLLM
        llm = FakeLLM(["first", "second", "third"])
        r1 = await llm.ainvoke([])
        r2 = await llm.ainvoke([])
        r3 = await llm.ainvoke([])
        assert r1.content == "first"
        assert r2.content == "second"
        assert r3.content == "third"

    @pytest.mark.asyncio
    async def test_response_fn(self):
        from tests.conftest import FakeLLM
        llm = FakeLLM(response_fn=lambda msgs: f"echo: {len(msgs)} messages")
        r = await llm.ainvoke(["a", "b", "c"])
        assert r.content == "echo: 3 messages"

    @pytest.mark.asyncio
    async def test_call_history_tracking(self):
        from tests.conftest import FakeLLM
        llm = FakeLLM("ok")
        await llm.ainvoke(["msg1"])
        await llm.ainvoke(["msg2"])
        assert len(llm.call_history) == 2
        assert llm.call_history[0] == ["msg1"]

    def test_sync_invoke(self):
        from tests.conftest import FakeLLM
        llm = FakeLLM("sync response")
        r = llm.invoke([])
        assert r.content == "sync response"


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 8: Emoji/Artifact Sanitization (pure data)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestEmojiSanitization:
    """Test emoji-to-ASCII replacement map completeness."""

    @pytest.fixture(autouse=True)
    def import_map(self):
        from src.langraph_pipeline.nodes import _EMOJI_TO_ASCII
        self.emoji_map = _EMOJI_TO_ASCII

    def test_map_is_nonempty(self):
        assert len(self.emoji_map) > 30, "Emoji map should cover 30+ emojis"

    def test_common_emojis_covered(self):
        for emoji in ["✅", "❌", "⚠️", "🔄", "🔍", "💡", "🚀", "✔", "✔️"]:
            assert emoji in self.emoji_map, f"Missing common emoji: {emoji}"

    def test_replacements_are_ascii(self):
        for emoji, replacement in self.emoji_map.items():
            assert all(ord(c) < 128 for c in replacement), \
                f"Replacement for {emoji} contains non-ASCII: {replacement}"

    def test_sanitize_emoji_removes_variation_selector(self):
        from src.langraph_pipeline.nodes import _sanitize_emoji

        files = {
            "cli.py": "def show(todo):\n    status = '✔️' if todo['done'] else '❌'\n    return status\n"
        }
        changed = _sanitize_emoji(files, "unit-test")

        assert changed == 1
        sanitized = files["cli.py"]
        assert "✔" not in sanitized
        assert "❌" not in sanitized
        assert "\ufe0f" not in sanitized
        assert "[OK]" in sanitized
        assert "[FAIL]" in sanitized

    def test_sanitize_emoji_strips_remaining_non_ascii(self):
        from src.langraph_pipeline.nodes import _sanitize_emoji

        files = {
            "main.py": "def main():\n    print('ok')\n    note = 'naive cafe\u2014test'\n    return note\n"
        }
        changed = _sanitize_emoji(files, "unit-test")

        assert changed == 1
        assert all(ord(ch) < 128 for ch in files["main.py"])


@pytest.mark.unit
class TestFlaskAppContextAutoFix:
    """Validate deterministic fix for Flask-SQLAlchemy app context errors."""

    def test_wraps_create_all_with_app_context(self):
        from src.langraph_pipeline.nodes import _auto_fix_flask_app_context

        files = {
            "main.py": (
                "from flask import Flask\n"
                "from flask_sqlalchemy import SQLAlchemy\n\n"
                "app = Flask(__name__)\n"
                "db = SQLAlchemy(app)\n"
                "db.create_all()\n"
            )
        }

        changed = _auto_fix_flask_app_context(files)

        assert changed == ["main.py"]
        assert "with app.app_context():" in files["main.py"]
        assert "    db.create_all()" in files["main.py"]

    def test_skips_when_already_wrapped(self):
        from src.langraph_pipeline.nodes import _auto_fix_flask_app_context

        code = (
            "from flask import Flask\n"
            "app = Flask(__name__)\n"
            "with app.app_context():\n"
            "    db.create_all()\n"
        )
        files = {"main.py": code}

        changed = _auto_fix_flask_app_context(files)

        assert changed == []
        assert files["main.py"] == code


@pytest.mark.unit
class TestFlaskJsonifyContextAutoFix:
    """Validate deterministic app-context bootstrap for direct jsonify() calls."""

    def test_injects_has_app_context_and_pushes_context(self):
        from src.langraph_pipeline.nodes import _auto_fix_flask_jsonify_context

        files = {
            "api.py": (
                "from flask import Flask, jsonify\n"
                "app = Flask(__name__)\n\n"
                "def health():\n"
                "    return jsonify({'ok': True}), 200\n"
            )
        }

        changed = _auto_fix_flask_jsonify_context(files)

        assert changed == ["api.py"]
        fixed = files["api.py"]
        assert "has_app_context" in fixed
        assert "if not has_app_context():" in fixed
        assert "app.app_context().push()" in fixed

    def test_skips_when_context_push_already_exists(self):
        from src.langraph_pipeline.nodes import _auto_fix_flask_jsonify_context

        code = (
            "from flask import Flask, jsonify, has_app_context\n"
            "app = Flask(__name__)\n"
            "if not has_app_context():\n"
            "    app.app_context().push()\n\n"
            "def health():\n"
            "    return jsonify({'ok': True}), 200\n"
        )
        files = {"api.py": code}

        changed = _auto_fix_flask_jsonify_context(files)

        assert changed == []
        assert files["api.py"] == code


@pytest.mark.unit
class TestSqliteTodoContractAutoFix:
    """Validate deterministic SQLite Todo model/API contract repair."""

    def test_adds_get_by_id_and_constructor_compat(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlite_todo_contract

        files = {
            "models.py": (
                "import sqlite3\n\n"
                "DATABASE_PATH = 'todos.db'\n\n"
                "class Todo:\n"
                "    def __init__(self, title: str, priority: str, due_date: str) -> None:\n"
                "        self.id = None\n"
                "        self.title = title\n"
                "        self.priority = priority\n"
                "        self.due_date = due_date\n"
                "        self.status = 'pending'\n\n"
                "    def save(self):\n"
                "        pass\n"
            )
        }
        errors = ["AttributeError: type object 'Todo' has no attribute 'get_by_id'"]

        changed = _auto_fix_sqlite_todo_contract(files, errors)

        assert changed == ["models.py"]
        fixed = files["models.py"]
        assert "def __init__(self, title: str, priority: str, due_date: str, todo_id=None, status: str = 'pending', **kwargs):" in fixed
        assert "self.id = todo_id if todo_id is not None else kwargs.get(" in fixed
        assert "self.status = kwargs.get(" in fixed
        assert "def get_by_id(cls, todo_id: int):" in fixed

    def test_skips_when_error_does_not_match(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlite_todo_contract

        code = (
            "import sqlite3\n\n"
            "class Todo:\n"
            "    def __init__(self, title, priority, due_date):\n"
            "        self.title = title\n"
        )
        files = {"models.py": code}

        changed = _auto_fix_sqlite_todo_contract(files, ["some unrelated error"])

        assert changed == []
        assert files["models.py"] == code


@pytest.mark.unit
class TestFlaskTodoRouteAutoFix:
    """Validate deterministic fix for missing Flask Todo route bindings."""

    def test_injects_routes_when_todo_api_exists_without_routes(self):
        from src.langraph_pipeline.nodes import _auto_fix_flask_todo_routes

        files = {
            "app.py": (
                "from flask import Flask, request, jsonify\n"
                "app = Flask(__name__)\n\n"
                "class TodoModel:\n"
                "    @staticmethod\n"
                "    def query():\n"
                "        return None\n\n"
                "class TodoAPI:\n"
                "    def add_todo(self, data):\n"
                "        return jsonify({'id': 1}), 201\n"
                "    def list_todos(self):\n"
                "        return jsonify([]), 200\n"
                "    def remove_todo(self, todo_id):\n"
                "        return jsonify({'message': 'ok'}), 200\n"
                "    def complete_todo(self, todo_id):\n"
                "        return jsonify({'message': 'ok'}), 200\n"
            )
        }

        changed = _auto_fix_flask_todo_routes(files)

        assert changed == ["app.py"]
        fixed = files["app.py"]
        assert "@app.route('/todos', methods=['POST'])" in fixed
        assert "@app.route('/todos', methods=['GET'])" in fixed
        assert "@app.route('/todos/<int:todo_id>', methods=['DELETE'])" in fixed
        assert "@app.route('/todos/<int:todo_id>/complete', methods=['PUT'])" in fixed

    def test_skips_when_routes_already_exist(self):
        from src.langraph_pipeline.nodes import _auto_fix_flask_todo_routes

        code = (
            "from flask import Flask\n"
            "app = Flask(__name__)\n"
            "@app.route('/todos')\n"
            "def list_todos():\n"
            "    return []\n"
            "class TodoAPI:\n"
            "    def add_todo(self, data):\n"
            "        return {}, 201\n"
            "    def remove_todo(self, todo_id):\n"
            "        return {}, 200\n"
        )
        files = {"app.py": code}

        changed = _auto_fix_flask_todo_routes(files)

        assert changed == []
        assert files["app.py"] == code


@pytest.mark.unit
class TestTensorScalarAutoFix:
    """Validate deterministic fix for non-singleton tensor scalar conversion."""

    def test_rewrites_argmax_item_chain(self):
        from src.langraph_pipeline.nodes import _auto_fix_tensor_scalar_item

        files = {
            "main.py": (
                "def run(pred):\n"
                "    value = pred.argmax(-1).item()\n"
                "    return value\n"
            )
        }

        changed = _auto_fix_tensor_scalar_item(files)

        assert changed == ["main.py"]
        assert ".argmax(-1).reshape(-1)[0].item()" in files["main.py"]

    def test_no_change_when_pattern_absent(self):
        from src.langraph_pipeline.nodes import _auto_fix_tensor_scalar_item

        code = (
            "def run(pred):\n"
            "    return pred.argmax(-1)\n"
        )
        files = {"main.py": code}

        changed = _auto_fix_tensor_scalar_item(files)

        assert changed == []
        assert files["main.py"] == code


@pytest.mark.unit
class TestFastApiJsonResponseAutoFix:
    """Validate deterministic import-path repair for FastAPI JSONResponse."""

    def test_rewrites_fastapi_import_and_adds_responses_import(self):
        from src.langraph_pipeline.nodes import _auto_fix_fastapi_jsonresponse_import

        files = {
            "control_plane.py": (
                "from fastapi import FastAPI, APIRouter, JSONResponse\n\n"
                "app = FastAPI()\n"
            )
        }

        changed = _auto_fix_fastapi_jsonresponse_import(files)

        assert changed == ["control_plane.py"]
        fixed = files["control_plane.py"]
        assert "from fastapi import FastAPI, APIRouter" in fixed
        assert "from fastapi.responses import JSONResponse" in fixed

    def test_no_change_when_already_imported_from_fastapi_responses(self):
        from src.langraph_pipeline.nodes import _auto_fix_fastapi_jsonresponse_import

        code = (
            "from fastapi import FastAPI\n"
            "from fastapi.responses import JSONResponse\n\n"
            "app = FastAPI()\n"
        )
        files = {"control_plane.py": code}

        changed = _auto_fix_fastapi_jsonresponse_import(files)

        assert changed == []
        assert files["control_plane.py"] == code


@pytest.mark.unit
class TestCryptographySigningImportAutoFix:
    """Validate deterministic repair for invalid cryptography signing imports."""

    def test_rewrites_signing_import_to_pynacl(self):
        from src.langraph_pipeline.nodes import _auto_fix_cryptography_signing_import

        files = {
            "crypto.py": (
                "from cryptography.hazmat.primitives.asymmetric import signing\n\n"
                "def build_key():\n"
                "    return signing.SigningKey.generate()\n"
            )
        }

        changed = _auto_fix_cryptography_signing_import(files)

        assert changed == ["crypto.py"]
        fixed = files["crypto.py"]
        assert "from nacl import signing" in fixed
        assert "from cryptography.hazmat.primitives.asymmetric import signing" not in fixed


@pytest.mark.unit
class TestSignatureMismatchAutoFix:
    """Validate deterministic call-shape normalization for SIGNATURE_MISMATCH."""

    def test_adds_missing_arguments_when_minimum_required(self):
        from src.langraph_pipeline.nodes import _auto_fix_signature_mismatch_calls

        files = {
            "main.py": (
                "def create_todo(title, done, owner):\n"
                "    return {\"title\": title}\n\n"
                "item = create_todo(\"x\", False)\n"
            )
        }
        errors = [
            "SIGNATURE_MISMATCH: main.py:4 - `create_todo()` called with 2 argument(s) but requires at least 3."
        ]

        changed = _auto_fix_signature_mismatch_calls(files, errors)

        assert changed == ["main.py"]
        assert "item = create_todo(\"x\", False, None)" in files["main.py"]

    def test_removes_extra_arguments_when_maximum_allowed(self):
        from src.langraph_pipeline.nodes import _auto_fix_signature_mismatch_calls

        files = {
            "main.py": (
                "def create_todo(title, done):\n"
                "    return {\"title\": title}\n\n"
                "item = create_todo(\"x\", False, 123)\n"
            )
        }
        errors = [
            "SIGNATURE_MISMATCH: main.py:4 - `create_todo()` called with 3 argument(s) but accepts at most 2."
        ]

        changed = _auto_fix_signature_mismatch_calls(files, errors)

        assert changed == ["main.py"]
        assert "item = create_todo(\"x\", False)" in files["main.py"]


@pytest.mark.unit
class TestMarshmallowFieldKwargAutoFix:
    """Validate deterministic repair for Marshmallow field kwarg mismatches."""

    def test_rewrites_default_and_missing_to_load_default(self):
        from src.langraph_pipeline.nodes import _auto_fix_marshmallow_field_kwargs

        files = {
            "api.py": (
                "from marshmallow import Schema, fields\n\n"
                "class TodoSchema(Schema):\n"
                "    completed = fields.Bool(default=False)\n"
                "    title = fields.Str(missing='untitled')\n"
            )
        }
        errors = [
            "Import error in api.py: Field.__init__() got an unexpected keyword argument 'default'"
        ]

        changed = _auto_fix_marshmallow_field_kwargs(files, errors)

        assert changed == ["api.py"]
        fixed = files["api.py"]
        assert "fields.Bool(load_default=False)" in fixed
        assert "fields.Str(load_default='untitled')" in fixed
        assert "fields.Bool(default=" not in fixed
        assert "fields.Str(missing=" not in fixed

    def test_no_change_when_no_error_signal(self):
        from src.langraph_pipeline.nodes import _auto_fix_marshmallow_field_kwargs

        code = (
            "from marshmallow import Schema, fields\n\n"
            "class TodoSchema(Schema):\n"
            "    completed = fields.Bool(default=False)\n"
        )
        files = {"api.py": code}

        changed = _auto_fix_marshmallow_field_kwargs(files, ["some other error"])

        assert changed == []
        assert files["api.py"] == code


@pytest.mark.unit
class TestSqlAlchemyDbNameErrorAutoFix:
    """Validate deterministic repair for `name 'db' is not defined`."""

    def test_injects_sqlalchemy_db_assignment_when_import_exists(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_db_nameerror

        files = {
            "api.py": (
                "from flask import Flask\n"
                "from flask_sqlalchemy import SQLAlchemy\n\n"
                "class TodoModel(db.Model):\n"
                "    pass\n"
            )
        }

        changed = _auto_fix_sqlalchemy_db_nameerror(files)

        assert changed == ["api.py"]
        assert "db = SQLAlchemy()" in files["api.py"]

    def test_injects_db_shim_when_sqlalchemy_import_missing(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_db_nameerror

        files = {
            "api.py": (
                "from flask import Flask\n\n"
                "class TodoModel(db.Model):\n"
                "    pass\n"
            )
        }

        changed = _auto_fix_sqlalchemy_db_nameerror(files)

        assert changed == ["api.py"]
        assert "class _AutoGitDbShim:" in files["api.py"]
        assert "db = _AutoGitDbShim()" in files["api.py"]

    def test_no_change_when_db_assignment_already_present(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_db_nameerror

        code = (
            "from flask_sqlalchemy import SQLAlchemy\n"
            "db = SQLAlchemy()\n\n"
            "class TodoModel(db.Model):\n"
            "    pass\n"
        )
        files = {"api.py": code}

        changed = _auto_fix_sqlalchemy_db_nameerror(files)

        assert changed == []
        assert files["api.py"] == code

    def test_injects_sqlalchemy_import_when_symbol_used_without_import(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_db_nameerror

        files = {
            "app.py": (
                "from flask import Flask\n\n"
                "app = Flask(__name__)\n"
                "db = SQLAlchemy(app)\n"
            )
        }

        changed = _auto_fix_sqlalchemy_db_nameerror(files)

        assert changed == ["app.py"]
        assert "from flask_sqlalchemy import SQLAlchemy" in files["app.py"]


@pytest.mark.unit
class TestSqlAlchemyDatabaseSessionAttrAutoFix:
    """Validate deterministic repair when db is incorrectly assigned to Database()."""

    def test_rewrites_database_assignment_when_session_is_used(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_database_session_attr

        files = {
            "api.py": (
                "from flask import Flask\n\n"
                "app = Flask(__name__)\n"
                "db = Database(app)\n\n"
                "def save(todo):\n"
                "    db.session.add(todo)\n"
                "    db.session.commit()\n"
            )
        }
        errors = [
            "AttributeError: 'Database' object has no attribute 'session'"
        ]

        changed = _auto_fix_sqlalchemy_database_session_attr(files, errors)

        assert changed == ["api.py"]
        fixed = files["api.py"]
        assert "from flask_sqlalchemy import SQLAlchemy" in fixed
        assert "db = SQLAlchemy()" in fixed
        assert "db = Database(app)" not in fixed

    def test_no_change_without_matching_error(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_database_session_attr

        code = (
            "from flask_sqlalchemy import SQLAlchemy\n"
            "db = SQLAlchemy()\n"
            "def save(todo):\n"
            "    db.session.add(todo)\n"
        )
        files = {"api.py": code}

        changed = _auto_fix_sqlalchemy_database_session_attr(files, ["different error"])

        assert changed == []
        assert files["api.py"] == code


@pytest.mark.unit
class TestSqlAlchemyPaginateKwargAutoFix:
    """Validate deterministic conversion of Query.paginate positional args."""

    def test_rewrites_paginate_positional_args_to_keywords(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_paginate_kwargs

        files = {
            "main.py": (
                "def list_todos(query):\n"
                "    return query.paginate(page_num, per_page, False)\n"
            )
        }
        errors = [
            "TypeError: Query.paginate() takes 1 positional argument but 4 were given"
        ]

        changed = _auto_fix_sqlalchemy_paginate_kwargs(files, errors)

        assert changed == ["main.py"]
        assert "query.paginate(page=page_num, per_page=per_page, error_out=False)" in files["main.py"]

    def test_no_change_when_paginate_already_uses_keywords(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_paginate_kwargs

        code = (
            "def list_todos(query):\n"
            "    return query.paginate(page=1, per_page=10, error_out=False)\n"
        )
        files = {"main.py": code}

        changed = _auto_fix_sqlalchemy_paginate_kwargs(
            files,
            ["TypeError: Query.paginate() takes 1 positional argument but 4 were given"],
        )

        assert changed == []
        assert files["main.py"] == code


@pytest.mark.unit
class TestSqlAlchemyDoubleRegistrationAutoFix:
    """Validate deterministic fix for SQLAlchemy app registration mismatch."""

    def test_rewrites_sqlalchemy_app_constructor_binding(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_double_registration

        files = {
            "api.py": (
                "from flask import Flask\n"
                "from flask_sqlalchemy import SQLAlchemy\n\n"
                "app = Flask(__name__)\n"
                "db = SQLAlchemy(app)\n"
            )
        }
        errors = [
            "RuntimeError: A 'SQLAlchemy' instance has already been registered on this Flask app"
        ]

        changed = _auto_fix_sqlalchemy_double_registration(files, errors)

        assert changed == ["api.py"]
        fixed = files["api.py"]
        assert "db = SQLAlchemy()" in fixed
        assert "db.init_app(app)" in fixed
        assert "db = SQLAlchemy(app)" not in fixed

    def test_adds_missing_init_app_for_plain_sqlalchemy_instance(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_double_registration

        files = {
            "api.py": (
                "from flask import Flask\n"
                "from flask_sqlalchemy import SQLAlchemy\n\n"
                "app = Flask(__name__)\n"
                "db = SQLAlchemy()\n"
            )
        }
        errors = [
            "RuntimeError: The current Flask app is not registered with this 'SQLAlchemy' instance"
        ]

        changed = _auto_fix_sqlalchemy_double_registration(files, errors)

        assert changed == ["api.py"]
        assert "db.init_app(app)" in files["api.py"]


@pytest.mark.unit
class TestSqlAlchemyCreateAllBindAutoFix:
    """Validate deterministic fix for MetaData.create_all bind errors."""

    def test_rewrites_metadata_create_all_with_engine_bind(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_create_all_bind

        files = {
            "models.py": (
                "from sqlalchemy import create_engine\n"
                "engine = create_engine('sqlite:///todos.db')\n\n"
                "def create_db():\n"
                "    Base.metadata.create_all()\n"
            )
        }
        errors = ["TypeError: MetaData.create_all() missing 1 required positional argument: 'bind'"]

        changed = _auto_fix_sqlalchemy_create_all_bind(files, errors)

        assert changed == ["models.py"]
        assert "Base.metadata.create_all(bind=engine)" in files["models.py"]

    def test_rewrites_metadata_create_all_with_db_engine_bind(self):
        from src.langraph_pipeline.nodes import _auto_fix_sqlalchemy_create_all_bind

        files = {
            "models.py": (
                "from flask_sqlalchemy import SQLAlchemy\n"
                "db = SQLAlchemy()\n\n"
                "def create_db():\n"
                "    Base.metadata.create_all()\n"
            )
        }
        errors = ["TypeError: MetaData.create_all() missing 1 required positional argument: 'bind'"]

        changed = _auto_fix_sqlalchemy_create_all_bind(files, errors)

        assert changed == ["models.py"]
        assert "Base.metadata.create_all(bind=db.engine)" in files["models.py"]


@pytest.mark.unit
class TestDateutilRequirementsAutoFix:
    """Validate deterministic dependency repair for dateutil missing-module loops."""

    def test_adds_python_dateutil_when_missing_custom_module_error_present(self):
        from src.langraph_pipeline.nodes import _auto_fix_dateutil_requirements

        files = {
            "requirements.txt": "flask\n",
            "main.py": "from dateutil import parser\n",
        }
        errors = [
            "MISSING_CUSTOM_MODULE: main.py:1 - from dateutil import ...",
        ]

        changed = _auto_fix_dateutil_requirements(files, errors)

        assert changed == ["requirements.txt"]
        assert "python-dateutil" in files["requirements.txt"]

    def test_no_change_when_python_dateutil_already_present(self):
        from src.langraph_pipeline.nodes import _auto_fix_dateutil_requirements

        files = {
            "requirements.txt": "flask\npython-dateutil>=2.9\n",
            "main.py": "from dateutil import parser\n",
        }
        errors = [
            "MISSING_CUSTOM_MODULE: main.py:1 - from dateutil import ...",
        ]

        changed = _auto_fix_dateutil_requirements(files, errors)

        assert changed == []
        assert files["requirements.txt"].count("python-dateutil") == 1


@pytest.mark.unit
class TestPydanticPrioritySchemaAutoFix:
    """Validate deterministic repair for Pydantic Priority schema generation errors."""

    def test_normalizes_plain_priority_class_and_adds_model_config(self):
        from src.langraph_pipeline.nodes import _auto_fix_pydantic_priority_schema

        files = {
            "schemas.py": (
                "from pydantic import BaseModel\n\n"
                "class Priority:\n"
                "    LOW = 'low'\n"
                "    HIGH = 'high'\n\n"
                "class TodoIn(BaseModel):\n"
                "    priority: Priority\n"
            )
        }

        changed = _auto_fix_pydantic_priority_schema(files)

        assert changed == ["schemas.py"]
        fixed = files["schemas.py"]
        assert "from enum import Enum" in fixed
        assert "from pydantic import ConfigDict" in fixed
        assert "class Priority(str, Enum):" in fixed
        assert "model_config = ConfigDict(arbitrary_types_allowed=True)" in fixed

    def test_no_change_when_priority_enum_and_model_config_already_valid(self):
        from src.langraph_pipeline.nodes import _auto_fix_pydantic_priority_schema

        code = (
            "from enum import Enum\n"
            "from pydantic import BaseModel, ConfigDict\n\n"
            "class Priority(str, Enum):\n"
            "    LOW = 'low'\n"
            "    HIGH = 'high'\n\n"
            "class TodoIn(BaseModel):\n"
            "    model_config = ConfigDict(arbitrary_types_allowed=True)\n"
            "    priority: Priority\n"
        )
        files = {"schemas.py": code}

        changed = _auto_fix_pydantic_priority_schema(files)

        assert changed == []
        assert files["schemas.py"] == code


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 9: Import-to-Package Alias Map
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestImportToPkgMap:
    """Validate the _IMPORT_TO_PKG alias mapping."""

    @pytest.fixture(autouse=True)
    def import_map(self):
        from src.langraph_pipeline.nodes import _IMPORT_TO_PKG
        self.alias_map = _IMPORT_TO_PKG

    def test_known_aliases(self):
        assert self.alias_map["cv2"] == "opencv-python"
        assert self.alias_map["PIL"] == "pillow"
        assert self.alias_map["sklearn"] == "scikit-learn"
        assert self.alias_map["yaml"] == "pyyaml"
        assert self.alias_map["bs4"] == "beautifulsoup4"
        assert self.alias_map["flask_sqlalchemy"] == "Flask-SQLAlchemy"
        assert self.alias_map["neo4j"] == "neo4j"
        assert self.alias_map["argon2"] == "argon2-cffi"

    def test_keys_are_import_names(self):
        """Keys should be valid Python import names."""
        for key in self.alias_map:
            assert key.isidentifier() or "." not in key, \
                f"Invalid import name in alias map: {key}"

    def test_values_are_nonempty(self):
        for key, val in self.alias_map.items():
            assert val and val.strip(), f"Empty package name for {key}"


# ─────────────────────────────────────────────────────────────────────────────
# Test Group 10: Code Review Fallback (invalid JSON -> deterministic checks)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestCodeReviewFallback:
    """Ensure code_review_agent_node still reviews code when LLM JSON is malformed."""

    @pytest.mark.asyncio
    async def test_code_review_uses_deterministic_fallback_on_unparseable_json(self, make_state):
        from tests.conftest import FakeLLM
        from src.langraph_pipeline.nodes import code_review_agent_node

        # Reviewer returns unparseable text; fixer returns corrected main.py.
        review_llm = FakeLLM("not-json")
        fixed_main = (
            "def main():\n"
            "    print('ok')\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )
        fix_llm = FakeLLM(fixed_main)

        state = make_state(
            generated_code={
                "files": {
                    "main.py": "def main():\n    print('ok')\n",
                    "utils.py": "def helper():\n    return 1\n",
                }
            }
        )

        with patch(
            "src.langraph_pipeline.nodes.get_fallback_llm",
            side_effect=[review_llm, fix_llm],
        ), patch("src.langraph_pipeline.nodes.Console"):
            result = await code_review_agent_node(state)

        assert result.get("current_stage") == "code_reviewed"
        out_files = result.get("generated_code", {}).get("files", {})
        assert "main.py" in out_files
        assert "if __name__ == '__main__':" in out_files["main.py"]


@pytest.mark.unit
class TestArchitectSpecHardening:
    """Ensure architect_spec_node tolerates non-string fields in model JSON."""

    @pytest.mark.asyncio
    async def test_architect_spec_handles_list_pseudocode_without_splitlines_crash(self, make_state):
        from tests.conftest import FakeLLM
        from src.langraph_pipeline.nodes import architect_spec_node

        spec_payload = {
            "project_name": "ttl_lru_cache",
            "one_line_description": "In-memory cache",
            "files": [
                {
                    "name": "main.py",
                    "purpose": ["entrypoint", "demo"],
                    "estimated_lines": 40,
                    "key_classes": [],
                    "key_functions": ["main() -> None"],
                    "imports_from_project": ["cache.TTLCache"],
                    "external_deps": [],
                }
            ],
            "data_flow": ["main -> cache"],
            "key_algorithms": [
                {
                    "name": "Eviction loop",
                    "file": "cache.py",
                    "pseudocode": ["if expired: drop", "if over_capacity: evict_lru"],
                }
            ],
            "entry_point_behavior": ["parse args", "run demo"],
            "expected_output": "ok",
            "test_scenarios": ["python main.py"],
            "total_estimated_lines": 120,
        }

        fake_llm = FakeLLM(json.dumps(spec_payload))
        state = make_state(
            idea="Build a cache",
            final_solution={
                "approach_name": "TTL-LRU",
                "key_innovation": "hybrid wheel",
                "architecture_design": ["hash map", "linked list"],
                "implementation_plan": ["step1", "step2"],
            },
            research_summary=["finding A", "finding B"],
        )

        with patch("src.langraph_pipeline.nodes.get_fallback_llm", return_value=fake_llm), patch(
            "src.langraph_pipeline.nodes.Console"
        ):
            result = await architect_spec_node(state)

        assert result.get("current_stage") == "architect_spec_complete"
        spec_text = result.get("_architecture_spec_text", "")
        assert "Eviction loop" in spec_text
        assert "if expired: drop" in spec_text


@pytest.mark.unit
class TestEvalParserFallback:
    """Phase 1: ensure eval nodes degrade safely on malformed LLM JSON."""

    @pytest.mark.asyncio
    async def test_self_eval_malformed_json_uses_fallback_and_flags_warning(self, make_state):
        from tests.conftest import FakeLLM
        from src.langraph_pipeline.nodes import pipeline_self_eval_node

        fake_llm = FakeLLM("this is not json")
        state = make_state(
            generated_code={"files": {"main.py": "def main():\n    print('ok')\n"}},
            tests_passed=True,
            self_eval_attempts=0,
        )

        with patch("src.langraph_pipeline.nodes.get_fallback_llm", return_value=fake_llm), patch(
            "src.langraph_pipeline.nodes.Console"
        ):
            result = await pipeline_self_eval_node(state)

        assert result.get("current_stage") in {"self_eval_needs_regen", "self_eval_approved"}
        assert any("SELF_EVAL_JSON_FALLBACK_USED" in w for w in result.get("warnings", []))

    @pytest.mark.asyncio
    async def test_goal_eval_malformed_json_uses_fallback_and_flags_warning(self, make_state):
        from tests.conftest import FakeLLM
        from src.langraph_pipeline.nodes import goal_achievement_eval_node

        fake_llm = FakeLLM("still not json")
        state = make_state(
            generated_code={"files": {"main.py": "def main():\n    print('ok')\n"}},
            goal_eval_attempts=0,
            tests_passed=False,
            smoke_test={"passed": False, "errors": ["runtime crash"]},
        )

        with patch("src.langraph_pipeline.nodes.get_fallback_llm", return_value=fake_llm), patch(
            "src.langraph_pipeline.nodes.Console"
        ):
            result = await goal_achievement_eval_node(state)

        assert result.get("current_stage") in {"goal_eval_needs_work", "goal_eval_approved"}
        assert any("GOAL_EVAL_JSON_FALLBACK_USED" in w for w in result.get("warnings", []))
        report = result.get("goal_eval_report", {})
        assert isinstance(report, dict)

    @pytest.mark.asyncio
    async def test_self_eval_respects_env_fix_attempt_cap(self, make_state):
        from tests.conftest import FakeLLM
        from src.langraph_pipeline.nodes import pipeline_self_eval_node

        fake_llm = FakeLLM("this is not json")
        state = make_state(
            generated_code={"files": {"main.py": "def main():\n    print('ok')\n"}},
            tests_passed=True,
            self_eval_attempts=0,
            max_fix_attempts=7,
        )

        with patch.dict("os.environ", {"AUTOGIT_MAX_FIX_ATTEMPTS_CAP": "8"}, clear=False), patch(
            "src.langraph_pipeline.nodes.get_fallback_llm", return_value=fake_llm
        ), patch("src.langraph_pipeline.nodes.Console"):
            result = await pipeline_self_eval_node(state)

        assert result.get("current_stage") == "self_eval_needs_regen"
        assert result.get("max_fix_attempts") == 8

    @pytest.mark.asyncio
    async def test_goal_eval_respects_env_fix_attempt_cap(self, make_state):
        from tests.conftest import FakeLLM
        from src.langraph_pipeline.nodes import goal_achievement_eval_node

        fake_llm = FakeLLM("still not json")
        state = make_state(
            generated_code={"files": {"main.py": "def main():\n    print('ok')\n"}},
            goal_eval_attempts=0,
            tests_passed=False,
            smoke_test={"passed": False, "errors": ["runtime crash"]},
            max_fix_attempts=7,
        )

        with patch.dict("os.environ", {"AUTOGIT_MAX_FIX_ATTEMPTS_CAP": "8"}, clear=False), patch(
            "src.langraph_pipeline.nodes.get_fallback_llm", return_value=fake_llm
        ), patch("src.langraph_pipeline.nodes.Console"):
            result = await goal_achievement_eval_node(state)

        assert result.get("current_stage") == "goal_eval_needs_work"
        assert result.get("max_fix_attempts") == 8

    @pytest.mark.asyncio
    async def test_eval_fix_attempt_cap_defaults_when_env_invalid(self, make_state):
        from tests.conftest import FakeLLM
        from src.langraph_pipeline.nodes import pipeline_self_eval_node, goal_achievement_eval_node

        fake_llm = FakeLLM("this is not json")
        state_self = make_state(
            generated_code={"files": {"main.py": "def main():\n    print('ok')\n"}},
            tests_passed=True,
            self_eval_attempts=0,
            max_fix_attempts=11,
        )
        state_goal = make_state(
            generated_code={"files": {"main.py": "def main():\n    print('ok')\n"}},
            goal_eval_attempts=0,
            tests_passed=False,
            smoke_test={"passed": False, "errors": ["runtime crash"]},
            max_fix_attempts=11,
        )

        with patch.dict("os.environ", {"AUTOGIT_MAX_FIX_ATTEMPTS_CAP": "not_an_int"}, clear=False), patch(
            "src.langraph_pipeline.nodes.get_fallback_llm", return_value=fake_llm
        ), patch("src.langraph_pipeline.nodes.Console"):
            self_result = await pipeline_self_eval_node(state_self)
            goal_result = await goal_achievement_eval_node(state_goal)

        assert self_result.get("max_fix_attempts") == 12
        assert goal_result.get("max_fix_attempts") == 12
