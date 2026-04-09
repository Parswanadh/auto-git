# Auto-GIT Testing Strategy

## Overview

The Auto-GIT pipeline has **66 test/script files** that have been organized into a clean directory structure, plus a new **zero-cost testing framework** that tests pipeline nodes without burning API credits.

---

## Directory Structure

```
tests/
├── conftest.py              # Shared fixtures: FakeLLM, make_state(), patch_get_llm
├── __init__.py
├── unit/                    # 18 files — ZERO cost, no LLM/API needed
│   ├── test_nodes_zero_cost.py    # NEW: 41 tests for node functions & utilities
│   ├── test_state_contracts.py    # NEW: 14 tests for state shape validation
│   ├── test_middleware.py         # Middleware component tests
│   ├── test_workspace_and_cli.py  # 191 CLI regression tests
│   └── ... (14 more legacy unit tests)
├── integration/             # 20 files — Need live LLM/API
│   ├── test_pipeline_run.py
│   ├── test_openrouter.py
│   └── ... (requires API keys)
├── e2e/                     # 6 files — Full pipeline runs (slow, costly)
│   ├── run_e2e_test.py
│   ├── test_pipeline_comprehensive.py
│   └── ...
├── diagnostics/             # 5 files — Health checks & debugging
│   ├── test_engine_warmup.py
│   ├── test_minimal.py
│   └── ...
├── benchmarks/              # 1 file — Performance/reliability tests
│   └── test_phase2_baby_dragon.py
├── agents/                  # Empty (future)
├── fixtures/                # Empty (future: golden files, cassettes)
└── validation/              # Empty (future)

scripts/
├── runners/                 # 6 files — Pipeline launcher scripts
│   ├── run_pipeline.py
│   ├── run_baby_dragon.py
│   └── ...
├── tools/                   # 10 files — Utility scripts
│   ├── check_keys.py
│   ├── seed_error_memory.py
│   ├── dashboard.py
│   └── ...
├── build_global_index.py
├── init_db.py
├── setup_searxng.bat
└── setup_searxng.sh
```

---

## How to Run Tests

### Zero-Cost (Default) — `pytest`
```bash
# Default: only runs @pytest.mark.unit tests ($0.00)
pytest

# Verbose with individual test names
pytest -v

# Run specific test file
pytest tests/unit/test_nodes_zero_cost.py -v
```

### Integration Tests — Need API Keys
```bash
# Run integration tests (costs money!)
pytest -m "integration" -v

# Run specific integration test
pytest tests/integration/test_openrouter.py -v
```

### E2E Tests — Full Pipeline
```bash
# Run end-to-end tests (slow, expensive)
pytest -m "e2e" -v
```

### All Tests
```bash
# Run everything (unit + integration + e2e)
pytest -m "unit or integration or e2e" -v
```

---

## Zero-Cost Testing Framework

### The Problem
- Pipeline has 19 nodes, each calling LLM APIs
- A single pipeline run costs $0.05-$0.50 and takes 5-20 minutes
- 30 silent failure patterns identified where errors are swallowed
- No way to iterate quickly on fixes without burning money

### The Solution: FakeLLM + State Contracts

#### 1. FakeLLM (in `tests/conftest.py`)
A drop-in mock for `FallbackLLM` / `ChatOllama` that:
- Returns canned responses (single, sequential, or dynamic)
- Tracks call count and message history
- Has both `ainvoke()` and `invoke()` methods
- Costs $0.00

```python
from tests.conftest import FakeLLM

# Single response (reused forever)
llm = FakeLLM("hello world")

# Sequential responses
llm = FakeLLM(["first", "second", "third"])

# Dynamic (based on input)
llm = FakeLLM(response_fn=lambda msgs: f"got {len(msgs)} messages")
```

#### 2. State Factory (in `tests/conftest.py`)
Creates properly initialized `AutoGITState` dicts with all ~45 fields:

```python
def test_my_node(make_state, patch_get_llm):
    state = make_state(idea="Build a calculator", fix_attempts=3)
    # All fields have safe defaults — no NoneType crashes
```

#### 3. LLM Patching Fixture
Auto-patches all LLM entry points so tests can't accidentally call real APIs:

```python
@pytest.fixture
def patch_get_llm(fake_llm):
    # Patches: get_llm(), get_fallback_llm() in nodes.py and model_manager.py
    # Returns the FakeLLM so tests can configure responses
    yield fake_llm
```

---

## Test Categories

| Category | Marker | Cost | Files | Tests | Purpose |
|----------|--------|------|-------|-------|---------|
| Unit | `@pytest.mark.unit` | $0.00 | 18+ | 55+ | Pure functions, mocked LLM, state contracts |
| Integration | `@pytest.mark.integration` | $0.01-0.10/test | 20 | ~100 | Real LLM calls, API connectivity |
| E2E | `@pytest.mark.e2e` | $0.05-0.50/run | 6 | ~10 | Full pipeline runs |
| Diagnostic | `@pytest.mark.diagnostic` | $0.00 | 5 | ~20 | Health checks, warmup |
| Benchmark | `@pytest.mark.benchmark` | $0.10+/run | 1 | ~5 | Performance measurement |

---

## What the New Unit Tests Cover

### `test_nodes_zero_cost.py` (41 tests)
1. **State Contracts** — All required fields exist, defaults are safe, no shared mutable refs
2. **_clean_requirements_txt** — Stdlib filtering, alias mapping, import-aware filtering, edge cases
3. **_build_requirements_from_imports** — AST scanning, local module exclusion, deterministic output
4. **requirements_extraction_node** — Empty idea skip, valid JSON parsing, malformed JSON fallback, markdown fence stripping
5. **Silent Failure Prevention** — Error list appendable, empty code detectable, tests_passed=False default
6. **Incomplete Artifact Detection** — Skeleton markers, NotImplementedError, TODO pass
7. **FakeLLM Infrastructure** — Sequential responses, history tracking, sync/async invoke
8. **Emoji Sanitization** — Map completeness, ASCII-only replacements
9. **Import-to-Package Map** — Known aliases correct, valid Python identifiers

### `test_state_contracts.py` (14 tests)
1. **AutoGITState creation** — Minimal creation, safe defaults, custom params
2. **Type safety** — Lists are actual lists, dicts are actual dicts, no None traps
3. **S22 regression** — tests_passed=False, fix_attempts=0
4. **Perspective configs** — Expert perspectives exist and have names

---

## Future Expansion Plan

### Phase 2: VCR.py Cassette Recording ($0.00 after first run)
Record real API responses once, replay forever:
```python
@vcr.use_cassette('fixtures/research_node.yaml')
async def test_research_node_with_real_data(make_state):
    # First run: records real API response
    # Subsequent runs: replays from cassette ($0.00)
```

### Phase 3: Property-Based Testing (Hypothesis)
Test with randomly generated inputs:
```python
@given(idea=st.text(min_size=1, max_size=1000))
def test_requirements_extraction_never_crashes(idea, make_state, patch_get_llm):
    state = make_state(idea=idea)
    result = asyncio.run(requirements_extraction_node(state))
    assert "current_stage" in result
```

### Phase 4: Fault Injection
Test resilience with deliberately broken LLMs:
```python
class FaultyLLM(FakeLLM):
    def ainvoke(self, messages, **kwargs):
        if random.random() < 0.3:
            raise TimeoutError("simulated timeout")
        return super().ainvoke(messages, **kwargs)
```

### Phase 5: Free-Tier LLM Testing
Use free LLM APIs for realistic integration tests:
- **Groq**: 14,400 requests/day free tier
- **Google AI Studio**: Free Gemini API
- **Ollama**: Local qwen3:0.6b (522MB, runs on any machine)

---

## Silent Failure Patterns to Test

The audit found **30 silent failure patterns**. Priority ones to add tests for:

| # | Pattern | Severity | Test Strategy |
|---|---------|----------|---------------|
| 1 | Empty research looks like valid research | CRITICAL | Assert research_context has papers/web lists |
| 2 | Resource gate defaults to "safe" (=skip) | CRITICAL | FaultInjection: test with low VRAM |
| 3 | Placeholder code passes syntax validation | CRITICAL | Assert no `NotImplementedError` in output |
| 4 | JSON parse failure → empty dict (not error) | HIGH | FakeLLM returning garbage, check errors[] |
| 5 | Missing state keys silently dropped by LangGraph | HIGH | State contract tests (DONE) |
| 6 | 3+ fix cycles on same error (wasted tokens) | HIGH | Circuit breaker unit test |
| 7 | Web search query contains internal labels | HIGH | Assert no `[STRATEGY]` in search queries |
