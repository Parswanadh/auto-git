# BUG TRACKER — Auto-GIT Pipeline
> Generated: 2026-03-11 | Method: Code audit + actual code verification
> Total: 85 bugs catalogued | Verified against real code

## Methodology (What We're Doing Differently This Time)

Based on engineering best practices (Google SRE, Microsoft SDFC, NASA JPL):

1. **Reproduce First** — Run the pipeline. See what ACTUALLY crashes.
2. **Fix What Matters** — Only bugs hit during real execution get fixed first.
3. **Test Each Fix** — Every fix gets a regression test BEFORE marking "done".
4. **One At A Time** — Fix → test → commit cycle per bug. No shotgun approach.
5. **Measure Impact** — Does the pipeline produce better output after fixes?

---

## STATUS LEGEND
- ✅ VERIFIED FIXED — Code reviewed, fix confirmed correct
- 🔧 NEEDS FIX — Bug confirmed still exists in code
- ⚪ NOT A BUG — False positive or not applicable
- 🟡 PARTIAL — Fix exists but incomplete
- ❓ UNCHECKED — Not yet verified

---

## CRITICAL (10)

| # | File | Bug | Status | Notes |
|---|------|-----|--------|-------|
| 1 | cli_entry.py | Double `main()` call | ✅ VERIFIED FIXED | |
| 2 | auto_git_cli.py | `search_comprehensive` tuple unpack crash | ✅ VERIFIED FIXED | |
| 3 | auto_git_interactive.py | Same tuple unpack crash | ✅ VERIFIED FIXED | |
| 4 | nodes.py ~L1644 | `extract_json_from_text` returns None → `.get()` crash | 🔧 NEEDS FIX | `problems_json` can be None, then `problems_json.get()` crashes |
| 5 | nodes.py ~L5596 | `passed` computed before static analysis runs | ✅ VERIFIED FIXED | |
| 6 | extensive_researcher.py | API mismatch (prompt= vs messages=) | ✅ VERIFIED FIXED | |
| 7 | multi_critic_consensus.py | Logger used before defined | ✅ VERIFIED FIXED | |
| 8 | paper_scout.py | END constant never imported | ✅ VERIFIED FIXED | |
| 9 | supervisor.py | `asyncio.run()` inside async context | ✅ VERIFIED FIXED | |
| 10 | web_search.py | Brave engine registered but no dispatch | ✅ VERIFIED FIXED | |

## HIGH (23)

| # | File | Bug | Status | Notes |
|---|------|-----|--------|-------|
| 11 | nodes.py ~L1645 | Nested list wrapping `[["p1","p2"]]` | 🔧 NEEDS FIX | When `problems_json` is dict, `[problems_json.get("problems", [])]` wraps in extra list |
| 12 | nodes.py ~L1926 | debate_rounds duplication via operator.add | ✅ VERIFIED FIXED | |
| 13 | nodes.py ~L3301 | Case-sensitivity in shadow-file detection | 🔧 NEEDS FIX | `_KNOWN_PKG_STEMS` has "PIL" but `.lower()` comparison makes it match |
| 14 | nodes.py ~L4641 | Import wiring regex corrupts strings/comments | ✅ VERIFIED FIXED | Uses `\b` + `re.escape()` now |
| 15 | workflow_enhanced.py | `accumulated_state.update()` overwrites lists | ✅ VERIFIED FIXED | Append-keys popped before update |
| 16 | app.py | Command injection via `os.system` | ✅ VERIFIED FIXED | Uses `subprocess.Popen` now |
| 17 | web_search.py | Wrong dict keys for results | ✅ VERIFIED FIXED | |
| 18 | code_validator.py | Pattern strip breaks on `**/` prefix | ✅ VERIFIED FIXED | |
| 19 | code_validator.py | `IndentationError` unreachable after `SyntaxError` | ⚪ NOT A BUG | Order doesn't matter for distinct error types |
| 20 | docker_executor.py | Hardcoded `network=bridge` | ✅ VERIFIED FIXED | |
| 21 | ollama_client.py | Stream type mismatch | ✅ VERIFIED FIXED | |
| 22 | code_executor.py | `test_imports` wrong signature | ✅ VERIFIED FIXED | |
| 23 | auto_git_interactive.py | `parse_intent` doesn't lowercase | ✅ VERIFIED FIXED | |
| 24 | publish_to_github.py | Missing module reference | ✅ VERIFIED FIXED | |
| 25 | auto_git_cli.py | Debate cmd missing try-except | ✅ VERIFIED FIXED | Has try/except/KeyboardInterrupt |
| 26 | auto_git_cli.py | `.env` duplicate appends | ✅ VERIFIED FIXED | `_upsert_env_var` deduplicates |
| 27 | config.yaml | 16B model on 8GB VRAM | ✅ VERIFIED FIXED | Removed |
| 28 | claude_code_cli.py | MCP newline framing | ✅ VERIFIED FIXED | |
| 29 | debate_moderator.py | Infinite loop risk | ✅ VERIFIED FIXED | |
| 30 | realworld_validator.py | Wrong dict key | ✅ VERIFIED FIXED | |
| 31 | problem_extractor.py | Wrong dict key | ✅ VERIFIED FIXED | |
| 32 | hybrid_router.py | `asyncio.wait` misuse | ✅ VERIFIED FIXED | |
| 33 | config.py | Env overrides hardcoded | ✅ VERIFIED FIXED | |

## MEDIUM (35)

| # | File | Bug | Status | Notes |
|---|------|-----|--------|-------|
| 34 | nodes.py ~L368 | `len(content)` on None | ✅ VERIFIED FIXED | Type contract ensures non-None |
| 35 | nodes.py ~L2284 | `round_data["proposals"]` without `.get()` | 🔧 NEEDS FIX | Bare dict access, will KeyError |
| 36 | nodes.py | Round number extraction ValueError | ⚪ NOT A BUG | Rounds are dicts, not parsed strings |
| 37 | nodes.py ~L2285 | `round_data["critiques"]` inconsistent | 🔧 NEEDS FIX | Line 2618 uses `.get()`, 2285 doesn't |
| 38 | nodes.py | Thread-unsafe `_error_memory` global | ✅ VERIFIED FIXED | Moved to state dict |
| 39 | nodes.py ~L4738 | SQL regex fragile | ✅ VERIFIED FIXED | Robust DOTALL regex + column parsing |
| 40 | nodes.py ~L4498 | Contract stubs are placeholders | ✅ VERIFIED FIXED | Real stubs with NotImplementedError |
| 41 | nodes.py ~L4113 | One incomplete file blocks all testing | ✅ VERIFIED FIXED | Retry loop + skeleton fallback |
| 42 | nodes.py ~L4144 | Fallback skeleton unreachable | ✅ VERIFIED FIXED | Reachable via retry failure path |
| 43 | nodes.py | Docstring mismatch | ⚪ NOT A BUG | Docstrings match signatures |
| 44 | nodes.py ~L6020 | Parent class detection string matching | ✅ VERIFIED FIXED | Uses AST |
| 45 | nodes.py ~L5975 | Stale `var_class` post-scope | ✅ VERIFIED FIXED | Properly scoped |
| 46 | nodes.py | Error filter too aggressive | ⚪ NOT A BUG | Errors properly forwarded |
| 47 | nodes.py ~L9742 | GOAL-EVAL errors accumulate | 🟡 PARTIAL | Fresh copy per iteration, but extend could duplicate if state reused |
| 48 | nodes.py | Smoke test uses host Python | ⚪ NOT A BUG | Dedicated venv created |
| 49 | nodes.py ~L5589 | `write_text(None)` crash | ✅ VERIFIED FIXED | Content from dict iteration, never None |
| 50 | nodes.py ~L2821 | Unbound `_console` | ✅ VERIFIED FIXED | `_RCAS()` called at scope entry |
| 51 | nodes.py ~L5988 | `_var_name` None from regex | ✅ VERIFIED FIXED | Null check before use |
| 52 | workflow_enhanced.py | SQLite connection never closed | ✅ VERIFIED FIXED | |
| 53 | workflow_enhanced.py | Goal eval route no fix_attempts guard | ✅ VERIFIED FIXED | |
| 54 | workflow_enhanced.py | Resume returns empty dict | ✅ VERIFIED FIXED | |
| 55 | state.py | Missing field inits | ✅ VERIFIED FIXED | |
| 56 | global_novelty.py | Novelty score unbounded | ✅ VERIFIED FIXED | |
| 57 | enhanced_validator.py | Security raw dict format | ✅ VERIFIED FIXED | |
| 58 | enhanced_validator.py | Bare `ruff` call | ✅ VERIFIED FIXED | Uses `_find_executable` |
| 59 | error_pattern_db.py | `missing_fstring` broad regex | ✅ VERIFIED FIXED | |
| 60 | error_pattern_db.py | Classmethod gets self not cls | ✅ VERIFIED FIXED | |
| 61 | config.py | `load_config` no error handling | ✅ VERIFIED FIXED | |
| 62 | resource_monitor.py | Unconditional `import psutil` | ✅ VERIFIED FIXED | |
| 63 | resource_monitor.py | Temp file leak | ✅ VERIFIED FIXED | |
| 64 | cache.py | SQL injection in table name | ✅ VERIFIED FIXED | |
| 65 | semantic_cache.py | Dimension mismatch | ✅ VERIFIED FIXED | |
| 66 | hybrid_router.py | Empty response check | ✅ VERIFIED FIXED | |
| 67 | claude_code_cli.py | Path traversal in write_file | ✅ VERIFIED FIXED | |
| 68 | refine_node.py | Empty API key fallback | ✅ VERIFIED FIXED | |

## LOW (17)

| # | File | Bug | Status | Notes |
|---|------|-----|--------|-------|
| 69 | nodes.py | alias_map rebuilt every iteration | ⚪ NOT A BUG | Built once per function call, not in loop |
| 70 | nodes.py ~L4405 | AnnAssign not tracked | ✅ VERIFIED FIXED | Explicit AnnAssign handler |
| 71 | nodes.py | Hardcoded thresholds | 🟡 PARTIAL | Some configurable via state, some hardcoded |
| 72 | nodes.py | Dead `tests_passed` check | ⚪ NOT A BUG | Actually used in state propagation |
| 73 | nodes.py | Display defaults mismatch | ⚪ NOT A BUG | No mismatch found |
| 74 | nodes.py | Inconsistent constants | ⚪ NOT A BUG | Constants are centralized |
| 75 | nodes.py | Windows temp cleanup | ✅ VERIFIED FIXED | `ignore_errors=True` |
| 76 | nodes.py ~L3280 | Shadow set duplicated | 🟡 PARTIAL | Two similar sets exist intentionally |
| 77 | nodes.py ~L4633 | Fragile ast.alias handling | ✅ VERIFIED FIXED | Proper AST + difflib fuzzy matching |
| 78 | resource_monitor.py | Progress bar > 100% | ✅ VERIFIED FIXED | |
| 79 | workflow_enhanced.py | `compile_workflow` dead code | ⚪ NOT A BUG | |
| 80 | resource_monitor.py | `monitor.stop()` asymmetry | ✅ VERIFIED FIXED | |
| 81 | nodes.py | `_research_only` None crash | ✅ VERIFIED FIXED | |
| 82 | model_manager.py | Logger defined twice | ✅ VERIFIED FIXED | |
| 83 | pipeline_tracer.py | File handle never closed | ✅ VERIFIED FIXED | |
| 84 | rate_limiter.py | Rate limiter math error | ✅ VERIFIED FIXED | |
| 85 | config.yaml | `python_version: "3.8"` | ✅ VERIFIED FIXED | |

---

## SUMMARY

| Status | Count |
|--------|-------|
| ✅ VERIFIED FIXED | 62 |
| 🔧 NEEDS FIX | 5 (#4, #11, #13, #35, #37) |
| 🟡 PARTIAL | 3 (#47, #71, #76) |
| ⚪ NOT A BUG | 15 |
| **Total** | **85** |

## ACTION PLAN

### Step 1: Fix the 5 confirmed bugs (all in nodes.py)
- Bug #4/#11: `extract_json_from_text` None handling + nested list fix (~L1640-1645)
- Bug #13: Case-sensitivity in `_KNOWN_PKG_STEMS` (~L3301)
- Bug #35/#37: Unsafe `round_data["proposals"]` and `["critiques"]` (~L2284-2285)

### Step 2: Run the full pipeline with a simple idea
- `python auto_git_cli.py generate "Create a simple calculator CLI"`
- Record every error, crash, and unexpected output

### Step 3: Fix what breaks in practice
- Only fix bugs that cause actual pipeline failures
- Write a test for each fix

### Step 4: Evaluate output quality
- Does generated code compile?
- Does it run?
- Does it match the idea?
- Quality score vs expectation
