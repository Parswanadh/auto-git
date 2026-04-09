# Auto-GIT Handoff (March 22, 2026)

Status: Active handoff for next implementation session
Owner: Pipeline Reliability Track
Prepared by: GitHub Copilot
Canonical recovery brief: [docs/CONTEXT_RECOVERY_BRIEF_2026_04_01.md](docs/CONTEXT_RECOVERY_BRIEF_2026_04_01.md)

## 0) Latest Delta (March 25, 2026, 13:53-14:26)

Moderate E2E monitoring has been completed for the latest restarted run.

Run artifacts:
- Trace: `logs/pipeline_trace_20260325_135345.jsonl`
- Main log: `logs/e2e_moderate_latest.log`
- Status: `logs/agent_status_20260325_135345.md`
- Model health: `logs/model_health_20260325_135345.json`
- Output: `output/e2e_todo_app/secure-flask-authentication-with-jwt--argon2/20260325_142635`

Observed terminal outcome:
- Final stage: `saved_locally_tests_failed`
- Duration: `32m 52s`
- Fix attempts: `12/12` (budget exhausted)
- Self-eval score: `6.0/10`
- Correctness gate: fail-closed (publish blocked)
- Smoke signal: `tests_status` warning persisted (`Tests passed: False, Smoke test: True`)

Most actionable frontier from this run:
1. The run no longer stalls in research (timeout budgeting patch effective), but still converges to local-save terminal due correctness failures.
2. Requirements extraction still intermittently fails JSON parsing (`requirements_extraction_failed:JSONDecodeError`), reducing structured grounding quality early.
3. Generated auth/API project remains partially implemented versus requirement checklist, and fix loop exhausts before crossing correctness gate.

Control-loop note:
- A no-op self-eval loop breaker was added in `should_regen_or_publish(...)` for repeated smoke-pass/no-hard-failure cycles.
- This latest run still ended with hard-failure count > 0 at terminal gate, so publish remained correctly blocked.

Immediate next implementation targets:
1. Add deterministic requirements-extraction JSON hardening fallback to reduce repeated `JSONDecodeError` degradation.
2. Add deterministic auth/API compatibility fixer(s) for generated Flask/JWT scaffold mismatches seen in this output family.
3. Add focused routing tests for terminal gate behavior when `tests_passed=False` and smoke passes, to prevent budget waste while preserving fail-closed publishing.

## 0.1) New Delta (March 25, 2026, 15:59 onward)

SOTA testing expansion and deterministic parsing hardening were implemented after the previous run.

Code changes:
1. Requirements extraction parser hardening
- File: `src/langraph_pipeline/nodes.py`
- `requirements_extraction_node(...)` now uses robust fallback extraction (`extract_json_from_text(..., expected_type="object")`) when direct `json.loads(...)` fails.

2. Routing correctness precedence fix
- File: `src/langraph_pipeline/workflow_enhanced.py`
- In `should_fix_code(...)`, `artifact_incomplete` is now checked before `correctness_passed` publish short-circuit.
- This enforces fix-loop entry for incomplete placeholder artifacts even when other signals look clean.

3. New unit tests (zero-cost)
- File: `tests/unit/test_nodes_zero_cost.py`
	- noisy JSON fallback extraction cases (trailing noise, think-tag payloads)
- File: `tests/unit/test_correctness_routing.py`
	- artifact_incomplete routing assertions
	- no-op self-eval loop escape assertion
	- no-files-generated publish assertion

Validation results:
- `tests/unit/test_nodes_zero_cost.py -k RequirementsExtractionNode` → pass
- `tests/unit/test_correctness_routing.py tests/unit/test_workflow_loop_guard.py` → pass
- targeted combined requirements/routing slice → pass

Live run status (current):
- Trace: `logs/pipeline_trace_20260325_155920.jsonl`
- Log: `logs/e2e_moderate_latest.log`
- Confirmed early-stage improvement:
	- `requirements_extraction` completed as `requirements_extracted` in ~59s with `error_count=0`.
	- this is the exact prior recurring frontier (`requirements_extraction_failed:JSONDecodeError`) now mitigated in this run.

## 0.2) Plan Enforcement Decision (March 25, 2026, critical review)

This section locks execution back to the approved phase plan and addresses strategic drift.

### Critical evaluation of current strategy

What is valid:
1. Enforcing fail-closed correctness gates is the right direction.
2. Deterministic-first repair remains the correct lever for reliability/cost.
3. Structured artifacts and telemetry are already strong assets.

What is strategically wrong (must be corrected):
1. Over-optimizing coordination infrastructure before code-generation correctness converges.
2. Expanding MCP integration breadth before immediate runtime frontier is stabilized.
3. Running long moderate loops without strict phase-lock acceptance criteria.

Conclusion:
- Current bottleneck is still incomplete/fragile generated code convergence, not lack of orchestration breadth.
- MCP usage should be expanded selectively, not indiscriminately.

### Enforced phase-lock policy (effective immediately)

1. No phase rollover without gate pass evidence.
2. If a phase gate fails, only fixes mapped to that phase are allowed.
3. Contradiction state (`tests_passed` mismatch with hard failures/correctness) is stop-the-line.
4. Publish path remains blocked unless correctness gate is fully clean.

### Coordinated workstreams (from parallel subagent synthesis)

Workstream A (active now):
- Deterministic parse and early-stage hardening (already in progress and validated).

Workstream B (next):
- Deterministic runtime/frontier fixers for current moderate loop signatures:
	- Flask app-context runtime path
	- generated CLI signature mismatch path

Workstream C (gated after B):
- Failure taxonomy + anti-thrash policy strengthening for repeated signatures.

Workstream D (deferred, not blocked):
- MCP expansion with strict ROI filter.
	- Immediate MCP priority is narrow, high-impact usage only.
	- Broad MCP rollout is explicitly deferred until moderate correctness improves.

### MCP maximization policy (corrected)

Use MCPs to maximum useful extent, not maximum surface extent.

Immediate MCP priorities:
1. Policy/routing integration hooks where they reduce manual branching cost.
2. Git/publishing or deterministic tooling paths with clear audit benefits.
3. Security/testing MCP lanes only after core moderate correctness converges.

Deferred MCP priorities:
1. Large-scale research/security sandbox MCP expansion before core convergence.
2. Multi-server orchestration that introduces more failure surface than reliability gain in the current phase.

## 0.3) New Delta (March 25, 2026, phase-lock implemented in code)

Plan enforcement moved from documentation policy to runtime routing code.

Implemented:
1. Strict phase-lock telemetry helpers in workflow routing
- File: [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py)
- Added `_phase_lock_current(...)` and `_record_phase_gate_event(...)`
- All self-eval/goal-eval route outcomes now record `phase_gate_history` with allow/deny reason and phase transition metadata.

2. Goal-eval publish gate hardened
- File: [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py)
- Added `should_publish_after_goal_eval(...)` and routed `_goal_eval_route(...)` through it.
- Enforces: no publish transition without valid phase-lock preconditions.
- Supports phase inference from `goal_eval_*` stages, then applies strict checks.

3. State contract extended for phase-lock persistence
- File: [src/langraph_pipeline/state.py](src/langraph_pipeline/state.py)
- Added fields:
	- `phase_lock_current_phase`
	- `phase_gate_history`
	- `phase_lock_policy_version`
- Added defaults in `create_initial_state(...)`.

4. Regression coverage added
- File: [tests/unit/test_correctness_routing.py](tests/unit/test_correctness_routing.py)
	- self-eval publish phase advancement assertions
	- goal-eval publish block on missing phase
	- goal-stage phase inference + publish allow
- File: [tests/unit/test_state_contracts.py](tests/unit/test_state_contracts.py)
	- new phase-lock default-field assertions

Validation:
1. `pytest tests/unit/test_correctness_routing.py -q` → pass
2. `pytest tests/unit/test_state_contracts.py -q` → pass
3. `pytest tests/unit/test_pipeline_todo_tracking.py tests/unit/test_state_contracts.py tests/unit/test_mcp_server_manager.py -q` → pass (18)

Operational note:
- VS Code task `pytest-autogit-direct-python` currently fails due PowerShell invocation/path quoting (`D:\.conda\envs\auto-git\python.exe` not resolved by task shell). Direct-python invocation is currently reliable.

## 0.4) New Delta (March 25, 2026, publish fallback fixed)

Issue resolved from latest moderate run:
- previous terminal stage was `saved_locally_after_error` only because `PyGithub` was not installed (`No module named 'github'`).

Implemented fix:
1. `git_publishing_node(...)` now imports GitHub SDK lazily and handles missing dependency as non-fatal.
- File: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py)
- Behavior change:

## 0.5) New Delta (March 25, 2026, deterministic frontier shift)

Implemented this session:
1. Deterministic SQLAlchemy `create_all(bind=...)` repair
- File: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py)
- Added `_auto_fix_sqlalchemy_create_all_bind(...)`
- Trigger signature: `MetaData.create_all() missing 1 required positional argument: 'bind'`
- Behavior: rewrites `*.metadata.create_all()` to include `bind=engine` (when `engine` exists) or `bind=db.engine` (when Flask-SQLAlchemy `db` exists).

2. Deterministic dateutil dependency repair
- File: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py)
- Added `_auto_fix_dateutil_requirements(...)`
- Trigger signature: `MISSING_CUSTOM_MODULE` with `dateutil`
- Behavior: ensures `python-dateutil` is present in `requirements.txt`.

3. Missing-custom-module detector alias correction
- File: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py)
- Added `dateutil` to known third-party module set.
- Added alias bridge: if requirements contain `python_dateutil`, detector now treats `dateutil` imports as satisfied.

4. Deterministic pre-fix chain integration
- File: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py)
- Wired both new fixers into `code_fixing_node(...)` before LLM patching.

5. Regression tests added and passing
- File: [tests/unit/test_nodes_zero_cost.py](tests/unit/test_nodes_zero_cost.py)
- Added:
	- `TestSqlAlchemyCreateAllBindAutoFix`
	- `TestDateutilRequirementsAutoFix`
- Focused validation:
	- `pytest tests/unit/test_nodes_zero_cost.py -k "SqlAlchemyCreateAllBindAutoFix or DateutilRequirementsAutoFix or FlaskJsonifyContextAutoFix or SqliteTodoContractAutoFix" -q`
	- Result: pass (`8` tests).

Current operational note:
- A fresh moderate E2E launch started and recorded `requirements_extraction` completion in trace `logs/pipeline_trace_20260325_232248.jsonl`, but did not produce a completed terminal artifact set; prior completed moderate terminal remains `saved_locally_tests_failed` at `output/e2e_todo_app/zero-trust-shielded-todo-stack/20260325_215601`.
	- if `auto_publish=true` but `github` module is unavailable, pipeline now saves locally with:
		- `current_stage = "saved_locally"`
		- warning message (instead of error terminal state)

2. Regression test added:
- File: [tests/unit/test_correctness_routing.py](tests/unit/test_correctness_routing.py)
- `test_git_publishing_missing_pygithub_falls_back_to_saved_locally`

Validation:
1. `pytest tests/unit/test_correctness_routing.py -q` → pass
2. `nodes.py` static error check → clean

## 1) Executive Summary

Auto-GIT has strong reliability scaffolding in place, but still fails on end-to-end correctness in complex runs. The system is close to production-grade architecture-wise, but enforcement at terminal decision boundaries is still insufficient.

Key fact:
- The latest deep complex run reached late stages but ended in a tests-failed state, not a publish-ready state.

Bottom line:
- This is not primarily a "need better model" problem.
- This is primarily a "need stricter control-loop and correctness enforcement" problem.

## 1.1 Latest Delta (March 22, 2026, post-13:46)

New deterministic hardening landed:
- File: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py)
- Added `_auto_fix_fastapi_jsonresponse_import(files)`
- Integrated pre-fix trigger for:
	- `cannot import name 'JSONResponse' from 'fastapi'`
	- Rewrites generated imports to `from fastapi.responses import JSONResponse`

Regression coverage:
- File: [tests/unit/test_nodes_zero_cost.py](tests/unit/test_nodes_zero_cost.py)
- Added tests for rewrite and no-op cases.
- `python -m pytest tests/unit/test_nodes_zero_cost.py -q` passes.

Live complex run status:
- Background terminal id: `587c0f19-f95e-4537-a964-fb5163672e9b`
- Still running during this handoff update.
- Latest observed dominant signatures in run logs:
	- FastAPI JSONResponse import mismatch (now deterministically handled in codebase)
	- DP epsilon range validation failure in generated runtime path
	- ModelRegistry API mismatch in generated CLI path

## 2) What Research Found (and Why It Matters)

## 2.1 Claude Code-inspired findings

What we found:
- Strong lifecycle gating (before/after hooks), permission boundaries, and completion discipline are central to reliability.

Why it matters here:
- Auto-GIT must never declare success on narrative quality when runtime correctness fails.
- Completion must be evidence-backed, not confidence-backed.

Adopted direction:
- Fail-closed terminal gates.
- Strong stop-the-line contradiction checks.

## 2.2 Deep Agents-inspired findings

What we found:
- Checklist as explicit state + planner/executor/evaluator loops outperform prose-only control.

Why it matters here:
- Requirements currently can pass through as partial without strict evidence links.

Adopted direction:
- Checklist/evidence state model.
- Replanner triggers on repeated failure and confidence drop.

## 2.3 DeerFlow-inspired findings

What we found:
- Middleware patterns for loop detection, fan-out control, and normalized error handling reduce thrash.

Why it matters here:
- Repeated signature retries are still costly and often unproductive.

Adopted direction:
- Failure bucketing taxonomy.
- Deterministic policy routing per bucket.
- Signature-streak rollback/switch mechanism.

## 2.4 OpenClaw-inspired findings

What we found:
- Trust-mode and allowlist policy hardening + doctor-grade diagnostics are operational multipliers.

Why it matters here:
- Policy normalization exists, but operational confidence depends on enforceable runtime behavior and observability.

Adopted direction:
- Strict trust/allowlist enforcement in high-risk paths.
- Better doctor/replay recommendations.

## 2.5 SWE-Agent-inspired findings

What we found:
- Trajectory artifacts and reproducible evaluation are core to improving reliability over time.

Why it matters here:
- Without per-attempt evidence, recurring failures are hard to diagnose and tune.

Adopted direction:
- Persist attempt-level trajectory bundles.
- Strengthen replay and benchmark discipline.

## 2.6 Aider-inspired findings

What we found:
- Diff-first edits + deterministic checks + rollback ergonomics reduce collateral regressions.

Why it matters here:
- Large, unconstrained fixes increase cross-file breakage risk.

Adopted direction:
- Prefer constrained repair strategy and deterministic validation ordering.

## 3) Confirmed Pipeline Loopholes and Bugs

## 3.1 Confirmed from complex run artifacts

Observed in the latest deep run result:
- Final stage reached tests-failed terminal path (not publish-ready).
- Smoke test failed with runtime NameError on undefined mapper symbol.
- Generated tests failed heavily (8/8 failure class observed in error summary).
- Goal-achievement checks remained partial for multiple requirements.

Interpretation:
- Static quality signals are insufficient.
- Runtime truth and requirement evidence still not tightly enforced.

## 3.2 Structural loopholes (systemic)

1. Late correctness truth
- Pipeline can progress deeply before hard correctness contradictions block outcome.

2. Control-plane vs data-plane mismatch
- Failover profile is normalized and passed, but runtime enforcement in all node-level model paths is not fully guaranteed.

3. Retry thrashing
- Similar failure signatures can loop with costly retries and weak strategy switching.

4. Provider instability amplification
- 429/timeout/degraded endpoints can consume excessive attempts without sufficiently deterministic escape logic.

5. Requirement evidence gap
- Requirement completion is not always anchored to explicit runtime verification evidence.

## 4) Current Strengths (Do Not Break These)

- Workflow-level loop and policy scaffolding exists.
- Telemetry parity checks exist.
- Context offload + pointer compaction exists.
- Checkpointer provider abstraction exists.
- Replay and doctor CLI commands exist.
- Artifact fingerprint reuse exists for expensive verification nodes.

Constraint for next work:
- Preserve all existing strength areas while tightening correctness enforcement.

## 5) Planned Work Program

Canonical execution plan document:
- docs/PERFECT_UPDATED_PLAN_31_03.md

Canonical benchmark showcase document:
- docs/SOTA_SHOWCASE_BENCHMARK_PROGRAM_31_03.md

Baseline architecture plan document:
- docs/PERFECT_PLAN_22_03.md

Execution model:
- 6 phases with SOTA test gates after each phase.

## Phase 0 (Baseline Contract)
- Freeze baseline artifacts and define strict pass/fail contract.
- Add contradiction stop-the-line policy.

## Phase 1 (Fail-Closed Terminal Gates)
- Enforce no-success if tests/smoke/hard-failures disagree with success state.
- Add route invariants and terminal diagnostics.

## Phase 2 (Deterministic Repair + Anti-Thrash)
- Add failure taxonomy and per-bucket deterministic first-action policy.
- Add signature streak rollback + strategy switch.

## Phase 3 (Failover Profile Runtime Enforcement)
- Ensure model_failover_profile drives actual node-level model selection behavior.
- Add profile behavior tracing.

## Phase 4 (Checklist State + Replanner + Tool Scope)
- Introduce requirement evidence state model.
- Add replanner triggers and per-stage tool scoping.

## Phase 5 (Trajectory Evidence + Release Governance)
- Persist attempt trajectories.
- Upgrade doctor/replay remediation guidance.
- Add release scorecard and trend gating.

## 6) SOTA Test Program (Mandatory After Every Phase)

## 6.1 Deterministic unit gate
- python -m pytest tests/unit/test_pipeline_todo_tracking.py tests/unit/test_state_contracts.py tests/unit/test_mcp_server_manager.py -q
- python -m pytest tests/unit/test_integration_plan_controls.py tests/unit/test_nodes_zero_cost.py tests/unit/test_phase_d_ops_tools.py tests/unit/test_model_manager_large_prompt_controls.py -q

## 6.2 Moderate E2E gate
- python run_e2e_moderate.py

## 6.3 Complex one-shot gate
- python tests/e2e/run_e2e_complex_perplexica_once.py

## 6.4 Complex bounded pack gate
- python scripts/run_complex_verification_bounded.py

Promotion rule:
- No phase promotion unless all four gates pass and artifacts are archived.

## 7) Priority Implementation Queue (Next Session)

1. Implement Phase 0 contract enforcement and baseline scorecard.
2. Implement Phase 1 terminal fail-closed routing.
3. Add and run phase-specific route-invariant tests.
4. Run full SOTA gate stack.
5. Archive results and only then open Phase 2.

## 8) Key Risks and Mitigations

Risk 1: Over-gating slows iteration.
- Mitigation: strict gates for promotion/release, faster local dev mode for iteration.

Risk 2: Provider instability masks regressions.
- Mitigation: report deterministic failures separately from provider-surface failures.

Risk 3: Scope creep across phases.
- Mitigation: no cross-phase work until current phase gate is passed.

Risk 4: Flaky long-run tests.
- Mitigation: bounded rerun policy, stable env settings, strict artifact capture.

## 9) Non-Negotiable Acceptance Criteria

- False-green rate must be zero.
- Publish-with-hard-failure must be zero.
- Complex-run contradiction states must be zero.
- KPI trend must be non-regressive for two consecutive cycles before release certification.

## 10) Open Questions for Next Agent

1. Which node-level LLM acquisition paths still bypass runtime failover-profile enforcement?
2. Which contradiction states are still possible in terminal routing under edge merges?
3. Are there any deterministic checks that can move earlier to reduce expensive late retries?

## 11) Quick Start for Next Session

1. Read docs/PERFECT_UPDATED_PLAN_31_03.md (execution plan) and docs/PERFECT_PLAN_22_03.md (baseline architecture rationale).
2. Implement Phase 0 and Phase 1 only.
3. Run all four SOTA gates.
4. Update PROGRESS.md with gate results and artifact links.

End of handoff.

---

## 12) Latest Delta: Severity-Ranked Critical Review (March 22, 2026 @ ~13:46)

Scope of this delta:
- Incorporates the latest completed moderate and complex E2E runs after Phase 1 hardening work.
- Captures what improved, what still fails, and what to implement next without reopening broad scope.

Primary evidence artifacts:
- `output/e2e_todo_app/e2e_result.json`
- `output/e2e_complex_perplexica/complex_run_result_20260322_130113.json`
- `output/e2e_complex_perplexica/complex_run_summary_20260322_130113.txt`

### CRITICAL Findings

1. Complex E2E still terminates in correctness-failed state
- Final metrics (complex):
	- `current_stage=saved_locally_tests_failed`
	- `tests_passed=False`
	- `correctness_passed=False`
	- `hard_failures_count=14`
	- `publish_eligible=False`
- Top failure signature remains runtime-grounded, not cosmetic:
	- Tensor scalar conversion crash in generated `main.py` (`RuntimeError: a Tensor with 2 elements cannot be converted to Scalar`).

2. Fix-loop exhaustion still occurs before convergence
- Complex run consumed full fix budget (`fix_attempts=12`) and remained failing.
- This confirms persistent late-loop inefficiency for shape/signature class errors.

### HIGH Findings

3. Moderate E2E also remains non-promotable
- Final metrics (moderate):
	- `current_stage=saved_locally_tests_failed`
	- `tests_passed=False`
	- `hard_failures_count=16`
	- `publish_eligible=False`
- Indicates reliability gains are present but not yet sufficient for phase promotion.

4. Telemetry parity mismatch warnings remain noisy in moderate artifact
- Multiple warning entries indicate parity mismatch across nodes.
- This does not explain the primary runtime failures, but it reduces signal clarity during triage.

### MEDIUM Findings

5. Research-path quality still degrades under constrained provider surfaces
- Moderate artifact recorded synthesized-analysis fallback with no external sources captured.
- This is likely quality-impacting but secondary to runtime correctness blockers.

### What Improved in This Session (Already Landed)

1. Deterministic Unicode hardening
- Sanitizer now handles heavy-check variants (`✔`, `✔️`), strips U+FE0F/U+200D residues, and removes any remaining non-ASCII in `.py` files.

2. Deterministic Flask app-context repair
- Added pre-fix auto-remediation that wraps bare `create_all()` calls in `with app.app_context():`.

3. Regression coverage
- Added unit tests for both improvements in `tests/unit/test_nodes_zero_cost.py`.

### Immediate Implementation Queue (next 1-2 focused steps)

1. Add deterministic tensor-shape/singleton prediction repair rule
- Target the exact recurring crash class in generated `main.py`:
	- when `.argmax(...).item()` is called on non-singleton tensors.
- Introduce pre-fix normalization pattern (or error-pattern DB rule) to enforce scalar-safe reduction before `.item()`.

2. Add deterministic signature-arity patch for known generated callsites
- For recurring `SIGNATURE_MISMATCH` patterns, inject argument adapters before LLM patch attempts.
- Goal: reduce costly oscillation and preserve fix budget for non-deterministic issues.

Phase promotion status after this delta:
- **NOT READY** for Phase 2 promotion.
- Continue Phase 1 hardening until both moderate and complex one-shot gates satisfy tests/correctness/publish eligibility criteria.
