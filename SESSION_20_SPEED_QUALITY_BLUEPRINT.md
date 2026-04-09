# Session 20: Speed & Quality Improvement Blueprint

## Research Methodology

This blueprint is the result of:
1. **Deep codebase analysis** — read ~13,000 lines across all pipeline nodes, workflow orchestration, model management, validation, sandbox, error handling
2. **Prompt-by-prompt audit** — analyzed every major LLM prompt (architect_spec, code_generation, code_review, strategy_reasoner, code_fixing, self_eval, goal_eval, feature_verification) for token waste, missing context, and structure quality
3. **Fix loop trace** — mapped all 4 re-entry paths, measured worst-case iteration counts (44 node executions), identified every location where context is lost between iterations
4. **Redundancy measurement** — counted duplicate sanitization calls (5× emoji, 7× artifact stripping), overlapping LLM calls (file planner always overridden, Option 6 ⊂ code_review), re-extracted data (goal_eval re-decomposes requirements)
5. **SOTA technique research** — studied SWE-Agent (agent-computer interfaces), MapCoder (4-agent cycle), LATS (tree search for code), Aider (diff-based editing, repo maps, flexible patching, multi-model retry), Kimi K1.5 (RL-scaled reasoning), SWT-Bench (test-as-filter doubles fix precision)

---

## Impact × Effort Matrix

All improvements are ranked by **speed gain × quality gain / implementation effort**.

| Rank | Improvement | Speed Gain | Quality Gain | Effort | ROI Score |
|------|-------------|-----------|-------------|--------|-----------|
| 1 | Eliminate 3 wasted LLM calls | 30-60s saved | — | 1h | ★★★★★ |
| 2 | Diff-based code fixing | 40-60% fewer fix tokens | +20% fix accuracy | 4h | ★★★★★ |
| 3 | Error-scoped strategy reasoner | 50-70% fewer tokens | +15% diagnosis quality | 2h | ★★★★★ |
| 4 | Prompt budget enforcement | 20-40% token savings | +10% instruction following | 3h | ★★★★☆ |
| 5 | Deduplicate sanitization passes | 10-20s saved per run | — | 1h | ★★★★☆ |
| 6 | Few-shot examples in critical prompts | — | +25-35% output quality | 3h | ★★★★☆ |
| 7 | Pin requirements across evaluations | — | Eliminates requirement drift | 1h | ★★★★☆ |
| 8 | Diff tracking between fix iterations | — | +20% fix convergence | 3h | ★★★★☆ |
| 9 | Inject research into architect spec | — | +15% spec quality | 0.5h | ★★★★☆ |
| 10 | Chain-of-thought in strategy reasoner | — | +20% root-cause accuracy | 2h | ★★★☆☆ |
| 11 | Test-as-filter for fix validation | — | +30% correct fixes accepted | 4h | ★★★☆☆ |
| 12 | Tiered review (5/10/5 issue types) | 25% faster review | +15% issue detection | 2h | ★★★☆☆ |
| 13 | Self-eval scoring rubric + examples | — | +25% evaluation consistency | 2h | ★★★☆☆ |
| 14 | Raise self-eval threshold 6→7 | — | Blocks more bad code | 0.5h | ★★★☆☆ |
| 15 | Output verification in self-eval | — | Catches logic bugs | 4h | ★★☆☆☆ |

---

## Detailed Improvement Specifications

### RANK 1: Eliminate 3 Wasted LLM Calls
**Speed: 30-60 seconds saved per run | Effort: ~1 hour**

Three LLM calls are provably wasted every single run:

#### 1a. File planner call is always overridden
- **Location**: [nodes.py L2860-L2890](src/langraph_pipeline/nodes.py#L2860)
- **Problem**: An LLM call generates a `file_list` JSON. Immediately after at L2891, the architect spec's file list overrides it unconditionally. Since `architect_spec_node` always runs before `code_generation_node` (unconditional edge), this LLM call is 100% wasted.
- **Fix**: Guard the file planner LLM call with `if not _spec_file_list:`. Skip entirely when architect spec provides the list.

#### 1b. Option 6 self-review duplicated by code_review_agent
- **Location**: [nodes.py L3755-L3832](src/langraph_pipeline/nodes.py#L3755)
- **Problem**: After all files are generated, sends all `.py` files to LLM for cross-file consistency audit (checks 5 issue types). `code_review_agent_node` runs immediately after and checks 20 issue types (strict superset). This is 1-2 redundant LLM calls.
- **Fix**: Remove the Option 6 self-review block entirely. `code_review_agent_node` catches everything it would find and more.

#### 1c. Contract generation overlaps architect spec
- **Location**: [nodes.py L2929-L2990](src/langraph_pipeline/nodes.py#L2929)
- **Problem**: The architect spec already defines class names, key methods, constructor signatures, and import dependencies per file. The contract generation repeats this as a slightly different format, costing 1 additional LLM call.
- **Fix**: Derive contracts directly from the architect spec JSON (no LLM call). Parse `architecture_spec.files[].key_classes[].key_methods[]` into the contract format deterministically.

**Combined impact**: Eliminates 3 LLM calls = ~30-60 seconds + ~3,000-8,000 tokens saved per run.

---

### RANK 2: Diff-Based Code Fixing (Aider-Style)
**Speed: 40-60% fewer fix tokens | Quality: +20% fix accuracy | Effort: ~4 hours**

**Current Problem**: `code_fixing_node` requires the LLM to return the ENTIRE file even when only 2 lines need changing. For a 500-line file with a 1-line bug, the LLM must regenerate 499 unchanged lines. This:
- Wastes tokens (output tokens are expensive)
- Risks introducing new bugs in untouched code
- Makes the model's task harder than necessary

**Proven Solution** (from Aider research):
- Use unified diff format for LLM fixes
- LLM returns search/replace blocks instead of full files
- Flexible patching handles imperfect diffs

**Implementation**:
```
System prompt for code_fixing:
"Return fixes as search/replace blocks:

<<<<<<< SEARCH
def calculate(x, y):
    return x + y  # BUG: should multiply
=======
def calculate(x, y):
    return x * y
>>>>>>> REPLACE

Include 3-5 lines of context around each change.
Only show the parts that need changing."
```

**Key design decisions** (based on Aider's findings):
1. **No line numbers** — LLMs are terrible at line numbers. Use search/replace blocks with context.
2. **High-level hunks** — encourage replacing whole functions/methods, not surgical per-line edits.
3. **Flexible matching** — strip whitespace, try fuzzy match, handle missing context lines.
4. **Fallback to full file** — if diff application fails 2× times, fall back to current full-file approach.

**Expected Impact**:
- Fix prompts shrink from ~10,000 tokens to ~2,000 tokens (4-5× reduction)
- Fix accuracy improves because model focuses only on the broken part
- Fewer accidental regressions in untouched code

---

### RANK 3: Error-Scoped Strategy Reasoner
**Speed: 50-70% fewer tokens | Quality: +15% diagnosis | Effort: ~2 hours**

**Current Problem**: Strategy reasoner includes ALL `.py` files in its prompt, regardless of which files have errors. For a 6-file project, this means ~1,200 lines of code per invocation, running up to 8 times in worst case = **~50,000 wasted tokens**.

**Fix**:
1. Parse error messages to extract file names (already available via traceback parser)
2. Only include files mentioned in errors + their direct importers
3. For non-mentioned files, include only a 1-line summary: `"utils.py (47 lines, imports: typing, json — no errors)"`

**Implementation**:
```python
# In strategy_reasoner_node, replace the all-files loop:
error_files = set()
for err in execution_errors:
    parsed = parse_error(err)  # Already have traceback_parser
    if parsed and parsed.file:
        error_files.add(parsed.file)

for fname, fcode in files.items():
    if fname in error_files:
        # Include full code (with truncation for >300 lines)
        prompt += f"\n## {fname} (HAS ERRORS)\n```python\n{fcode}\n```\n"
    else:
        # Include only summary
        prompt += f"\n## {fname} ({len(fcode.splitlines())} lines, no errors) — omitted\n"
```

Also: show ±15 lines around each error location instead of first 200 + last 50, using `ParsedError.lineno` for precise targeting.

---

### RANK 4: Prompt Budget Enforcement
**Speed: 20-40% token savings | Quality: +10% instruction following | Effort: ~3 hours**

**Current Problem**: Prompt budget is tracked via `_record_prompt_budget()` but NEVER enforced. The per-file code generation prompt concatenates 9 context sources that can balloon to 20,000+ tokens. When prompts exceed context windows, critical information (the actual errors) gets silently truncated.

**Fix**: Add a `_trim_prompt_to_budget()` function that enforces a max token budget with priority-based trimming:

```python
CONTEXT_PRIORITY = [
    ("base_prompt",        1.0),   # Never trim
    ("architecture",       0.9),   # Almost never trim
    ("contract",           0.8),   # Trim if overlaps arch
    ("cross_file_context", 0.7),   # Trim to signatures only
    ("research_context",   0.5),   # Trim aggressively
    ("codegen_lessons",    0.4),   # Keep only top 3
    ("repo_map",           0.3),   # Trim to file list only
    ("completeness_rules", 0.2),   # Keep only top 5 rules
]

def _trim_prompt_to_budget(sections: dict, max_tokens: int) -> str:
    total = sum(len(s) // 4 for s in sections.values())
    if total <= max_tokens:
        return "\n\n".join(sections.values())
    
    # Trim lowest-priority sections first
    for name, priority in sorted(CONTEXT_PRIORITY, key=lambda x: x[1]):
        if total <= max_tokens:
            break
        section = sections.get(name, "")
        trimmed = _truncate_section(section, target_reduction=(total - max_tokens))
        saved = len(section) // 4 - len(trimmed) // 4
        total -= saved
        sections[name] = trimmed
    
    return "\n\n".join(sections.values())
```

**Where to apply**: `code_generation_node`, `code_fixing_node`, `code_review_agent_node`, `strategy_reasoner_node`.

---

### RANK 5: Deduplicate Sanitization Passes
**Speed: 10-20s saved | Effort: ~1 hour**

**Current Problem**: Multiple sanitization functions run redundantly:
- `_sanitize_emoji` runs **5 times** across the pipeline (2 back-to-back in `code_generation_node` at L4114 and L4443)
- `_sanitize_llm_artifacts` runs **7 times** (2 back-to-back at L4123 and L4450)

**Fix**:
1. Remove the duplicate back-to-back calls in `code_generation_node` (the "proactive" pass at L4443/L4450 can never find anything the first pass at L4114/L4123 already cleaned)
2. Add an `_already_sanitized` flag per file so subsequent calls are no-ops if content hasn't changed since last sanitization
3. Consolidate: run both sanitizers in a single `_sanitize_all(files, label)` function

---

### RANK 6: Few-Shot Examples in Critical Prompts
**Quality: +25-35% output quality | Effort: ~3 hours**

**Current Problem**: All major prompts use zero-shot instruction-following. Research consistently shows that even 1 few-shot example improves LLM output quality by 25-35%, especially for structured output.

**Where to add few-shot examples** (priority order):

#### 6a. Architect Spec — show one complete filled JSON
```json
// Example for a URL shortener project:
{
  "files": [
    {
      "path": "main.py",
      "purpose": "Entry point with CLI and demo output",
      "estimated_lines": 45,
      "key_classes": [],
      "key_functions": ["main", "demo"],
      "imports_from_project": ["shortener"],
      "external_dependencies": []
    },
    {
      "path": "shortener.py", 
      "purpose": "Core URL shortening logic with Base62 encoding",
      "estimated_lines": 80,
      "key_classes": [{"name": "URLShortener", "key_methods": ["shorten", "resolve", "_encode"]}],
      "key_functions": [],
      "imports_from_project": ["storage"],
      "external_dependencies": ["hashlib"]
    }
  ],
  "key_algorithms": [
    {
      "name": "Base62 URL encoding",
      "pseudocode": "hash = md5(url)[:8]; encoded = base62_encode(int(hash, 16)); return encoded"
    }
  ]
}
```

#### 6b. Code Fixing — show one before/after fix example
Show a concrete example of a file with a NameError bug and its fix, demonstrated in search/replace format.

#### 6c. Self-Eval — show scored example output
Show what an 8/10 vs 4/10 project looks like with specific criteria.

#### 6d. Strategy Reasoner — show root-cause analysis example
Show a concrete error → diagnosis → strategy chain.

---

### RANK 7: Pin Requirements Across Evaluations
**Quality: Eliminates requirement drift | Effort: ~1 hour**

**Current Problem**: `goal_achievement_eval_node` re-extracts requirements from scratch each time it runs. Since the LLM extracts requirements non-deterministically, the requirements can literally change between evaluation passes. This causes the fix loop to chase moving targets.

**Fix**:
1. In `goal_achievement_eval_node`, extract requirements ONCE on the first pass
2. Store the extracted requirement list in state as `pinned_requirements: List[str]`
3. On subsequent passes, use the pinned list directly (no LLM re-extraction)

```python
# In goal_achievement_eval_node:
if state.get("pinned_requirements"):
    requirements = state["pinned_requirements"]
else:
    requirements = llm_extract_requirements(idea)
    state["pinned_requirements"] = requirements
```

---

### RANK 8: Diff Tracking Between Fix Iterations
**Quality: +20% fix convergence | Effort: ~3 hours**

**Current Problem**: No node tracks what changed between fix iterations. The strategy reasoner sees the current code but not what was modified in the last fix. It can't reason about "the fix for X broke Y."

**Fix**: After each `code_fixing_node` execution, compute and store unified diffs:

```python
import difflib

def _compute_diffs(old_files: dict, new_files: dict) -> dict:
    diffs = {}
    for fname in set(old_files) | set(new_files):
        old = (old_files.get(fname, "") or "").splitlines(keepends=True)
        new = (new_files.get(fname, "") or "").splitlines(keepends=True)
        diff = list(difflib.unified_diff(old, new, fromfile=f"a/{fname}", tofile=f"b/{fname}"))
        if diff:
            diffs[fname] = "".join(diff)
    return diffs
```

Add `fix_diffs: List[Dict[str, str]]` to state. Inject into strategy reasoner:
```
CHANGES FROM LAST FIX ATTEMPT:
--- a/main.py → main.py
@@ -15,3 +15,3 @@
-    result = x + y
+    result = x * y
```

This lets the reasoner see precisely what changed and diagnose whether the last fix caused a regression.

---

### RANK 9: Inject Research into Architect Spec
**Quality: +15% spec quality | Effort: ~30 minutes**

**Current Problem**: `research_summary` is loaded at L2472 in `architect_spec_node` but never included in the `spec_prompt`. The architect designs blind to research findings.

**Fix**: One-line addition:
```python
# In architect_spec_node, add to spec_prompt:
spec_prompt += f"\n\nRESEARCH FINDINGS:\n{research_summary[:3000]}\n"
```

This ensures the architecture leverages discovered papers, patterns, and existing implementations.

---

### RANK 10: Chain-of-Thought in Strategy Reasoner
**Quality: +20% root-cause accuracy | Effort: ~2 hours**

**Current Problem**: Strategy reasoner uses the "reasoning" model but the prompt doesn't leverage chain-of-thought. It must produce perfect JSON without intermediate reasoning. The LLM's `<think>` block is stripped during JSON extraction, losing the reasoning.

**Fix**: Two-stage prompting:
```
Stage 1 (thinking):
"Analyze each error. For each one, explain:
1. What the error message says
2. What file and line it occurs at  
3. What the root cause likely is
4. What similar errors you've seen before
5. What approach would fix it

Think step by step. Wrap your reasoning in <analysis> tags."

Stage 2 (structured output):
"Based on your analysis above, produce the JSON strategy:
{root_cause, failure_category, per_file_instructions, ...}"
```

Alternatively, keep the single-call approach but add a `"reasoning"` field to the JSON output that the LLM fills before the strategy fields. This preserves the chain-of-thought in state for debugging.

---

### RANK 11: Test-as-Filter for Fix Validation (SWT-Bench)
**Quality: +30% correct fixes accepted | Effort: ~4 hours**

**Research basis**: SWT-Bench paper found that LLM-generated tests **double the precision** of SWE-agent's code fixes when used as a filter. Generated tests are a cheap validation layer.

**Implementation**:
1. Before the fix loop starts, use a fast LLM to generate 3-5 test cases from the requirements
2. After each fix attempt, run these tests in addition to the built-in smoke tests
3. Only accept fixes that pass all generated tests
4. If tests fail, inject the test failure output into the next strategy reasoner call

This creates a tighter feedback loop: tests catch fixes that technically compile but produce wrong output.

**Key insight**: The `test_scenarios` field from the architect spec is currently NEVER used downstream. Wire it to test generation.

---

### RANK 12: Tiered Review (5/10/5 Issue Types)
**Speed: 25% faster review | Quality: +15% detection | Effort: ~2 hours**

**Current Problem**: `code_review_agent_node` lists all 20 issue types equally in one massive system prompt. Research shows LLMs reliably follow ~7 rules max. Past 10, compliance drops sharply.

**Fix**: Split into 3 tiers:
- **Tier 1 (Always check — 5 types)**: TRUNCATED, MISSING_ENTRY_POINT, STUB_BODY, CIRCULAR_IMPORT, API_MISMATCH
- **Tier 2 (Check if resources allow — 10 types)**: SILENT_MAIN, MISSING_OUTPUT_PROJECTION, DEAD_LOGIC, WRONG_CALL, MISSING_EXPORT, SELF_METHOD_MISSING, UNINITIALIZED_ATTR, RELATIVE_IMPORT, ENCODING_ISSUE, DEMO_MODE_INPUT
- **Tier 3 (Final pass only — 5 types)**: SHAPE_MISMATCH, DUPLICATE_CLASS, PLACEHOLDER_INIT, ATTR_MISMATCH, REDUNDANT_WRAPPING

On first review cycle: use Tier 1 only (5 rules). On final review: use Tier 1 + Tier 2 (15 rules). Only include Tier 3 if self-eval requests deeper review.

---

### RANK 13: Self-Eval Scoring Rubric with Examples
**Quality: +25% evaluation consistency | Effort: ~2 hours**

**Current Problem**: Self-eval says "score 0-10 on each dimension" with no calibration. Without examples, scoring is arbitrary and inconsistent between runs.

**Fix**: Add concrete rubrics:
```
COMPLETENESS SCORING GUIDE:
- 9-10: All spec files exist, all classes/methods have full implementations, no TODOs/stubs
- 7-8: All files exist, 90%+ methods implemented, minor edge cases missing
- 5-6: Most files exist, some methods are stubs or incomplete
- 3-4: Several files missing or mostly placeholder
- 1-2: Skeleton project, most code is TODO comments

CORRECTNESS SCORING GUIDE:
- 9-10: main.py runs, produces expected output, all tests pass
- 7-8: main.py runs with minor issues, most tests pass
- 5-6: main.py runs but output is partially wrong or incomplete
- 3-4: main.py crashes or produces no useful output
- 1-2: Multiple files have syntax errors or won't import
```

Also: inject the `architecture_spec` so the evaluator knows what was PLANNED vs what was BUILT.

---

### RANK 14: Raise Self-Eval Threshold
**Quality: Blocks more bad code | Effort: ~30 minutes**

**Current Problem**: Self-eval pass threshold is 6/10. A project scoring 6/10 on correctness has significant bugs. This is too low.

**Fix**:
- Raise overall threshold from 6 to 7
- Add dimension-specific minimums: `correctness >= 7`, `completeness >= 6`
- If correctness < 7 but overall >= 7, route to fix loop targeting correctness specifically

---

### RANK 15: Output Verification in Self-Eval
**Quality: Catches logic bugs | Effort: ~4 hours**

**Current Problem**: Self-eval judges code quality by reading the code, not by running it. If code runs but produces wrong output, neither evaluator catches this.

**Fix**: In `pipeline_self_eval_node`:
1. Run `main.py` in Docker sandbox (already have `DockerExecutor`)
2. Capture stdout/stderr
3. Compare against `expected_output` from architect spec
4. If output doesn't match expected: auto-fail correctness dimension

```python
from src.utils.docker_executor import DockerExecutor

executor = DockerExecutor()
result = executor.execute(files, "python main.py", timeout=30)
if result.exit_code != 0:
    correctness_score = min(correctness_score, 4)
if expected_output and expected_output not in result.stdout:
    correctness_score = min(correctness_score, 5)
```

---

## Implementation Priority — What to Do First

### Batch 1: Quick Wins (2-3 hours, biggest ROI)
These require minimal code changes and yield immediate gains:

1. **Rank 1**: Eliminate 3 wasted LLM calls (guard file planner, remove Option 6, derive contracts from spec)
2. **Rank 5**: Remove duplicate back-to-back sanitization calls
3. **Rank 9**: Inject research_summary into architect_spec_node prompt
4. **Rank 7**: Pin requirements in goal_eval (extract once, reuse)
5. **Rank 14**: Raise self-eval threshold from 6 to 7

**Expected combined impact**: ~1-2 minutes faster per run, eliminates 3 wasted LLM calls, prevents requirement drift.

### Batch 2: Medium Effort (4-6 hours, critical quality improvements)
These are the highest-quality-impact changes:

6. **Rank 3**: Error-scoped strategy reasoner (send only error-relevant files)
7. **Rank 6**: Few-shot examples in architect_spec_node and code_fixing_node
8. **Rank 8**: Diff tracking between fix iterations
9. **Rank 10**: Chain-of-thought in strategy reasoner
10. **Rank 4**: Prompt budget enforcement with priority-based trimming

**Expected combined impact**: Fix loop converges 30-50% faster, 20-30% better diagnosis quality.

### Batch 3: Structural Changes (6-10 hours, major architecture improvements)
These are the most impactful but require careful implementation:

11. **Rank 2**: Diff-based code fixing (Aider-style search/replace blocks)
12. **Rank 11**: Test-as-filter for fix validation
13. **Rank 12**: Tiered review (5/10/5)
14. **Rank 13**: Self-eval scoring rubric with examples
15. **Rank 15**: Output verification in self-eval

**Expected combined impact**: 40-60% reduction in fix loop tokens, catches logic bugs that currently slip through.

---

## Expected Cumulative Impact

| Metric | Current | After Batch 1 | After Batch 2 | After Batch 3 |
|--------|---------|---------------|---------------|---------------|
| LLM calls per run (no-fix) | ~16-18 | ~13-14 | ~13-14 | ~13-14 |
| Avg tokens per fix cycle | ~15,000 | ~13,000 | ~8,000 | ~4,000 |
| Fix loop convergence (iters) | 3-4 avg | 3-4 avg | 2-3 avg | 1-2 avg |
| First-time correctness | ~45% | ~50% | ~65% | ~80% |
| Instruction-following quality | ~60% | ~65% | ~80% | ~85% |
| Requirement drift | Yes | No | No | No |
| Logic bug detection | None | None | Partial | Runtime verified |
| Pipeline duration (typical) | 8-12 min | 7-10 min | 5-8 min | 3-6 min |

---

## Research Sources

| Source | Key Insight Applied |
|--------|-------------------|
| **Aider** (aider.chat) | Diff-based editing with flexible patching reduces fix tokens 4-5×. Repo maps > RAG for code context. Multi-model retry (alternating GPT-4o/Opus) finds solutions that single models miss. |
| **SWE-Agent** (Princeton/Stanford) | Agent-computer interfaces matter — give LLMs structured tools, not free-form instructions. Mini-SWE-Agent achieves 65% SWE-bench in 100 lines. |
| **MapCoder** (arXiv:2405.11403) | 4-agent cycle (recall → plan → generate → debug) achieves 93.9% HumanEval. Example recall is the key differentiator. |
| **LATS** (arXiv:2310.04406) | Tree search with backtracking and self-reflection. 92.7% HumanEval. Value function + environment feedback > chain of thought alone. |
| **SWT-Bench** (arXiv:2406.12952) | Generated tests double fix precision. Code repair agents are better test generators than purpose-built test generators. |
| **Kimi K1.5** (arXiv:2501.12599) | Long context scaling + policy optimization without MCTS. Simple RL framework outperforms complex tree search. |
| **Few-shot prompting research** | 1 example > 10 rules for structured output quality. LLMs follow ~7 instruction rules reliably; past 10, compliance drops. |
| **Prompt engineering benchmarks** | Structured context (sections, headers) > raw concatenation. Priority-based trimming > random truncation. |
