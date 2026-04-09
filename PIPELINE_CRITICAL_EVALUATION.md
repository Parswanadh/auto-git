# Pipeline Critical Evaluation — Calculator E2E Test (March 12, 2026)

## Executive Summary

**Overall Score: 5.5 / 10**

The pipeline produced working code in Run 1, but a second run with the identical idea exposed catastrophic instability. The same input (`"Create a simple command-line calculator"`) produced a clean 17-minute run AND a 46-minute nightmare with 11 fix cycles that ultimately **failed to save its output**. This non-determinism is the pipeline's most serious problem.

---

## Two Runs, Same Idea — Wildly Different Results

| Metric | Run 1 (`000503`) | Run 2 (`003233`) | Delta |
|--------|-----------------|-----------------|-------|
| Duration | 17.5 min | 46 min | **2.6x slower** |
| LLM calls | 33 | 82 | **2.5x more** |
| Total tokens | 184K | 643K | **3.5x more** |
| Est. cost | $0.064 | ~$0.22 | **3.4x more** |
| Fix cycles | 2 | 11 | **5.5x more** |
| Smoke test attempts | 1 (pass) | 7 (6 fail, 1 pass) | — |
| Self-eval attempts | 1 (pass) | 4 (3 reject, 1 pass) | — |
| Output saved | ✅ Yes | ❌ **No** (2 bugs) | — |
| Strategy reasoner % | ~5% | **31.7%** | — |

**Run 2 consumed 3.5x the tokens and failed to save any output.** A complete waste.

---

## Scoring Breakdown

### 1. Code Quality: 7.5 / 10

**What's good:**
- `exceptions.py` — Clean, well-documented exception hierarchy (100/100)
- `core.py` — Solid validation pipeline with range and near-zero checks (100/100)
- `main.py` — Working argparse + REPL + demo mode (90/100)
- Code review agent caught 6 API mismatches in test file (infix→prefix notation) — impressive

**What's bad:**
- `feature_tests.py` tests 8–10 reference `InvalidInputError` and `DivisionByZeroError` without importing them → NameError. Feature verification reported 7/10 (70%) because of this, but the generated report still claims 100%.
- `test_main.py` scored only 82/100 quality, 50/100 security, 66/100 lint
- `requirements.txt` line 1 is literally `txt` (invalid package name — the requirements rebuilder cleaned the file incorrectly and wrote `['invalid']` → `txt`)

### 2. Research Quality: 2 / 10

**Critical failure.** The SOTA researcher crashes with `No module named 'utils'` (a broken import in `src/research/sota_researcher.py`). The research report's Section 2 ("State of the Art") says *"Web search not available — see papers below"* and Section 3 ("Literature Review") says *"No papers found in research context."*

The Perplexica fallback returned 6,693 chars of context, but the final research report has two entirely empty sections. The remaining sections (Methodology, Implementation, Evaluation) are reasonable — they come from the LLM synthesizing Perplexica results. But two empty sections in the report that's supposed to ground the entire debate is a serious quality issue.

### 3. Debate & Selection: 4 / 10

- Consensus score: **0.50** (below 0.70 threshold) with only 1 debate round
- Selection was **forced** — the system picked "Security Expert's Validation-Centric Safe Arithmetic CLI Calculator" because it couldn't achieve consensus
- The forced selection happened to produce decent code, but this was luck
- The architect estimated 815 lines; actual output was ~295 lines (**2.8x overestimate**) — the spec has no grounding in reality

### 4. Self-Healing Loop: 3 / 10

**This is the pipeline's worst subsystem.**

**Run 1** (good case): 
- Fix 1: Added `pytest` to requirements.txt (correct fix)
- Fix 2: Added positional args to argparse (correct fix)
- Both were real bugs caught by real test failures

**Run 2** (catastrophic case):
- The `SELF_METHOD_MISSING` static checker flagged `self.assertEqual()`, `self.assertIn()`, etc. as "missing methods" — but these are **inherited from `unittest.TestCase`** and work perfectly fine
- The checker doesn't understand class inheritance, so every `unittest.TestCase` subclass triggers false positives
- The strategy reasoner treated these false positives as real bugs and web-searched "python Resolve SELF_METHOD_MISSING by replacing inherited unittest fix example" — googling our internal bug label as if it were a Python concept
- The code fixer would rewrite the test file, the checker would flag it again, the strategy reasoner would try again → **infinite loop** until budget exhaustion
- 11 fix cycles, 14.6 minutes of strategy reasoning, all to "fix" something that was never broken

**Root cause**: `nodes.py` lines 5853–5869 — the intra-class `self.method()` checker walks the AST for `self.X()` calls and checks if `X` exists in the class body, but **never checks base classes**. Any method inherited from a parent class (like `unittest.TestCase.assertEqual`) is flagged as missing.

### 5. Output Persistence: 1 / 10

**Run 2 failed to save ANY output.** Two bugs combined:

1. `git_publishing_node` imports `Github` and `datetime` in the same try block:
   ```python
   try:
       from github import Github     # ← Fails (PyGithub not installed)
       from datetime import datetime  # ← Never executed
   ```
   When `github` import fails, `datetime` is undefined.

2. The fallback save path uses `datetime.now()` — but `datetime` was never imported because it was after the failing import. Result: `cannot access local variable 'datetime'`.

This means: **if PyGithub isn't installed AND auto_publish is True, the pipeline loses all generated code.** Run 1 avoided this because its routing hit the early save path (auto_publish=False). Run 2 somehow hit the publishing path despite auto_publish being False (likely a checkpoint resume issue).

### 6. Pipeline Efficiency: 5 / 10

Run 1 was reasonably efficient (17.5 min, $0.064 for a calculator). But Run 2's profile reveals massive waste:

| Component (Run 2) | Time | % of Total |
|-------------------|------|------------|
| Strategy reasoner | 14.6 min | 31.7% |
| Code fixing | 6.2 min | 13.6% |
| Research | 5.0 min | 10.9% |
| Code generation | 3.3 min | 7.2% |
| Code testing (×11) | 2.7 min | 5.8% |
| Self-eval (×4) | 1.7 min | 3.7% |
| **All other nodes** | **12.5 min** | **27.1%** |

45% of total time was strategy_reasoner + code_fixing — **all wasted on false positives**.

### 7. Reproducibility: 2 / 10

Same idea, same model, same config → one run succeeds cleanly, the other burns 3.5x tokens and fails to save. The non-determinism comes from:
- LLM temperature causing different code structures (pytest parametrize in Run 1 vs unittest.TestCase in Run 2)
- The validator having landmines (SELF_METHOD_MISSING) that only trigger on certain code structures
- No circuit breaker to detect "same error repeating N times = probably a false positive"

---

## Identified Bugs (Priority Order)

### P0 — CRITICAL (cause pipeline failure)

| # | Bug | Location | Impact |
|---|-----|----------|--------|
| 1 | **SELF_METHOD_MISSING doesn't check parent classes** | `nodes.py:5853–5869` | 11 fix loops in Run 2, 460K wasted tokens |
| 2 | **`datetime` imported after failing `github` import** | `nodes.py:10222–10225` | Run 2 output permanently lost |
| 3 | **SOTA researcher broken import** | `sota_researcher.py` → `No module named 'utils'` | Empty research report sections |

### P1 — HIGH (cause incorrect output)

| # | Bug | Location | Impact |
|---|-----|----------|--------|
| 4 | **Feature test generator doesn't import project exceptions** | Feature verifier template | 3/10 feature tests always NameError |
| 5 | **requirements.txt corruption** — cleaned to `txt` on line 1 | Requirements rebuilder logic | Invalid pip install |
| 6 | **No circuit breaker for repeated identical errors** | Fix loop routing | Endless loops on false positives |

### P2 — MEDIUM (cause waste or confusion)

| # | Bug | Location | Impact |
|---|-----|----------|--------|
| 7 | **Strategy reasoner web-searches internal bug labels** | Strategy reasoner node | Googles "SELF_METHOD_MISSING" as if it's real Python |
| 8 | **Architect line estimate wildly wrong** (815 vs 295) | Architect spec node | No practical impact but suggests poor calibration |
| 9 | **Feature verification reports 100% in goal report** despite 7/10 actual | Goal eval logic | Misleading metrics |
| 10 | **Checkpoint resume may bypass auto_publish=False routing** | Workflow routing | Run 2 hit publishing path unexpectedly |

---

## Improvement Recommendations (Priority Order)

### 1. Fix SELF_METHOD_MISSING Inheritance (P0 — immediate)

Add parent class awareness to the intra-class method checker. At minimum:
- Skip the check entirely for classes inheriting from known frameworks (`unittest.TestCase`, `abc.ABC`, etc.)
- Or: resolve base classes and collect their methods too
- Or: only flag `self.X()` if the method name doesn't exist in ANY class in the file's inheritance chain

### 2. Fix Import Ordering in git_publishing_node (P0 — 2 lines)

Move `from datetime import datetime` before `from github import Github`, or import it outside the try block entirely.

### 3. Add Fix Loop Circuit Breaker (P1 — critical for stability)

If the same error (same type + same file + same line range) persists across 3 consecutive fix cycles:
- Mark it as a **suspected false positive**
- Skip it and proceed
- Log a warning for human review

This alone would have prevented Run 2's entire 11-cycle nightmare.

### 4. Fix SOTA Researcher Import (P0 — unblock research)

Fix the `No module named 'utils'` error in `sota_researcher.py`. This will restore the research report's two empty sections and give the debate system actual grounding.

### 5. Feature Test Template: Add Imports (P1 — template fix)

The feature test generator creates tests that reference project custom exceptions but doesn't add the necessary imports. Either:
- Add dynamic imports based on the project's exception hierarchy
- Or wrap exception-testing code in try/except ImportError

### 6. Requirements Rebuilder Validation (P1)

Add validation that re-built requirements.txt entries are valid PyPI package names (not `txt`, `invalid`, etc.). Simple regex check: `/^[a-zA-Z0-9_-]+/`.

### 7. Strategy Reasoner: Don't Web-Search Internal Labels (P2)

The strategy reasoner should never web-search for error types that start with our internal prefixes (`SELF_METHOD_MISSING`, `API_MISMATCH`, `STUB_BODY`, etc.). These are internal classification labels, not Python concepts.

### 8. Add Smoke Test Error Detail to Logs (P2)

The smoke test currently logs "❌ Smoke test failed: 1 error(s)" but doesn't log what the actual error was. The error details are critical for debugging and should be in the main log, not just buried in the state object.

---

## What the Pipeline Does Well

Despite the harsh score, several things work impressively:

1. **Code review agent is excellent** — caught 6 real API mismatches between test code and implementation in Run 1
2. **LLM-as-Judge is well-calibrated** — scored 3.0/10 when main.py only showed --help, 9.0/10 after argparse fix
3. **Multi-perspective debate produces good solutions** — the Security Expert's validation-centric approach was genuinely well-designed
4. **Incremental compilation works** — 3/3 files validated during generation
5. **The fix loop concept is sound** — Run 1's 2-cycle fix (pytest + argparse) was exactly the right behavior

The core architecture is solid. The problems are in the validators and edge cases, not the fundamental design.

---

*Generated from analysis of traces `000503` and `003233`, agent status reports, checkpoint data, and full pipeline logs (94KB stdout, 259KB e2e log, 165KB progress log).*
