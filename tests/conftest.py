"""
Shared test fixtures for Auto-GIT pipeline testing.

This conftest provides zero-cost mocks and fixtures that allow testing
pipeline nodes WITHOUT any LLM API calls or network access.

Key fixtures:
    fake_llm          - Drop-in replacement for FallbackLLM (canned responses)
    make_state        - Factory for AutoGITState with sensible defaults
    patch_get_llm     - Auto-patches get_llm/get_fallback_llm globally
    sample_code       - Example generated code for testing validators
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Exclude script-style "test" files that call sys.exit() at module level ──
# These crash pytest collection. They should be run standalone, not via pytest.
collect_ignore = [
    os.path.join(os.path.dirname(__file__), "diagnostics"),
    os.path.join(os.path.dirname(__file__), "benchmarks"),
    os.path.join(os.path.dirname(__file__), "e2e"),
    os.path.join(os.path.dirname(__file__), "integration"),
    os.path.join(os.path.dirname(__file__), "agents"),
    os.path.join(os.path.dirname(__file__), "unit", "test_integration_verify.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_enhanced_validation_integration.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_model_setup.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_analytics.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_integrated_quick.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_integration_13_validation.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_integration_14_monitoring.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_model_router.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_multi_agent.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_tracing.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_validator_direct.py"),
    os.path.join(os.path.dirname(__file__), "unit", "test_workspace_and_cli.py"),
]


# ─────────────────────────────────────────────────────────────────────────────
# FakeLLM: Zero-cost mock that replaces FallbackLLM/ChatOllama
# ─────────────────────────────────────────────────────────────────────────────

class FakeResponse:
    """Mimics langchain AIMessage response."""
    def __init__(self, content: str):
        self.content = content
        self.response_metadata = {"model": "fake-llm", "finish_reason": "stop"}
        self.usage_metadata = {"input_tokens": 10, "output_tokens": 50}


class FakeLLM:
    """
    Zero-cost mock for FallbackLLM / ChatOllama.
    
    Usage:
        # Sequential responses (pops from front):
        llm = FakeLLM(["first response", "second response"])
        
        # Single response (reused every time):
        llm = FakeLLM("always this")
        
        # Dynamic response based on prompt content:
        llm = FakeLLM(response_fn=lambda msgs: "computed response")
    """
    
    def __init__(self, responses=None, response_fn=None):
        if responses is None and response_fn is None:
            responses = ['{"result": "mocked response"}']
        
        if isinstance(responses, str):
            responses = [responses]
        
        self._responses = list(responses) if responses else []
        self._response_fn = response_fn
        self.call_count = 0
        self.call_history: List[Any] = []
    
    def _get_response(self, messages) -> str:
        self.call_count += 1
        self.call_history.append(messages)
        
        if self._response_fn:
            return self._response_fn(messages)
        
        if self._responses:
            # Pop from front, but keep last one for reuse
            if len(self._responses) > 1:
                return self._responses.pop(0)
            return self._responses[0]
        
        return '{"result": "default mock response"}'
    
    async def ainvoke(self, messages, **kwargs):
        content = self._get_response(messages)
        return FakeResponse(content)
    
    def invoke(self, messages, **kwargs):
        content = self._get_response(messages)
        return FakeResponse(content)


# ─────────────────────────────────────────────────────────────────────────────
# State factory
# ─────────────────────────────────────────────────────────────────────────────

def _make_state(**overrides) -> Dict[str, Any]:
    """
    Create a minimal AutoGITState dict with all required fields.
    Pass overrides to customize specific fields.
    """
    base = {
        # Input
        "idea": "Build a simple calculator CLI",
        "user_requirements": None,
        "requirements": None,
        
        # Research
        "research_context": None,
        "related_work_summary": None,
        "research_report": None,
        "research_summary": None,
        
        # Problem Extraction
        "problems": [],
        "selected_problem": None,
        
        # Debate
        "debate_rounds": [],
        "current_round": 0,
        "max_rounds": 2,
        "perspectives": ["ML Researcher", "Systems Engineer", "Applied Scientist"],
        "dynamic_perspective_configs": None,
        
        # Solution
        "final_solution": None,
        "selection_reasoning": None,
        
        # Code Generation
        "generated_code": {},
        "implementation_notes": None,
        
        # Code Testing
        "test_results": None,
        "tests_passed": False,
        "fix_attempts": 0,
        "max_fix_attempts": 8,
        
        # Self-Evaluation
        "self_eval_attempts": 0,
        "self_eval_score": -1.0,
        "self_eval_unverified": False,
        
        # Goal Achievement
        "goal_eval_attempts": 0,
        "goal_eval_report": None,
        "goal_eval_unverified": False,
        
        # Architecture
        "architecture_spec": None,
        "_architecture_spec_text": "",
        "repo_map": "",
        "context_budget_report": {},
        
        # Strategy Reasoner
        "_prev_fix_strategies": [],
        "_prev_strategy_hashes": [],
        "_prev_error_hashes": [],
        "_auto_fixed_errors": [],
        "_persistent_error_tracker": {},
        "_error_fingerprints_history": [],
        
        # S20
        "pinned_requirements": None,
        "fix_diffs": [],
        
        # Dynamic Agent Spawner
        "spawned_agent_roles": None,
        "agent_pool_log": [],
        "spawn_coordination_mode": None,
        
        # Telemetry
        "node_budget_report": {},
        "resource_events": [],
        "pipeline_todos": [],
        "todo_progress": {},
        "todo_generation_notes": "",
        
        # Git Publishing
        "repo_name": None,
        "commit_message": None,
        "published": False,
        "github_url": None,
        
        # Metadata
        "pipeline_start_time": datetime.now().isoformat(),
        "current_stage": "initialized",
        "errors": [],
        "warnings": [],
        
        # S22 fixes
        "should_continue_debate": False,
        "fix_review_required": False,
        "auto_publish": False,
        "output_dir": None,
        "output_path": None,
        "smoke_test": None,
        
        # Configuration
        "use_web_search": False,
        "max_debate_rounds": 2,
        "min_consensus_score": 0.7,
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Pytest fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_llm():
    """A FakeLLM instance that returns a default JSON response."""
    return FakeLLM()


@pytest.fixture
def make_state():
    """Factory fixture — call make_state(idea="...", ...) to create state dicts."""
    return _make_state


@pytest.fixture
def patch_get_llm(fake_llm):
    """
    Auto-patches all LLM entry points so no node can accidentally call a real API.
    Returns the FakeLLM instance so tests can configure responses.
    
    Usage:
        def test_my_node(patch_get_llm, make_state):
            patch_get_llm._responses = ["my custom response"]
            state = make_state(idea="test")
            result = await my_node(state)
    """
    with patch("src.langraph_pipeline.nodes.get_llm", return_value=fake_llm), \
         patch("src.langraph_pipeline.nodes.get_fallback_llm", return_value=fake_llm), \
         patch("src.utils.model_manager.get_fallback_llm", return_value=fake_llm):
        yield fake_llm


@pytest.fixture
def sample_generated_code():
    """Example generated code dict for testing validators and code_testing_node."""
    return {
        "files": {
            "main.py": '''"""Simple Calculator CLI"""
import sys

def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b

def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def main():
    if len(sys.argv) != 4:
        print("Usage: python main.py <a> <op> <b>")
        sys.exit(1)
    a, op, b = float(sys.argv[1]), sys.argv[2], float(sys.argv[3])
    ops = {"+": add, "-": subtract, "*": multiply, "/": divide}
    if op not in ops:
        print(f"Unknown operator: {op}")
        sys.exit(1)
    print(ops[op](a, b))

if __name__ == "__main__":
    main()
''',
            "requirements.txt": "# No external dependencies\n",
            "README.md": "# Calculator CLI\nA simple calculator.\n",
        },
        "approach": "Simple procedural calculator with CLI interface",
    }


@pytest.fixture
def sample_bad_code():
    """Code with deliberate errors for testing fix loops."""
    return {
        "files": {
            "main.py": '''"""Broken Calculator"""
import nonexistent_module

def add(a, b)  # missing colon
    return a + b

class Calculator:
    def divide(self, a, b):
        return a / b  # no zero check
''',
            "requirements.txt": "nonexistent_package==99.99\n",
        },
        "approach": "Broken calculator for testing",
    }
