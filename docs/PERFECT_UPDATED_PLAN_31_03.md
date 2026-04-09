# Perfect Updated Integration Plan 31-03 (Reliability Closure + SOTA Gate Discipline)

Date: 2026-03-31  
Owner: Auto-GIT Core Pipeline Team  
Status: Ready for implementation  
Supersedes for execution ordering: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md)  
Companion governance source: [HANDOFF.md](HANDOFF.md#L380)  
Companion benchmark program: [docs/SOTA_SHOWCASE_BENCHMARK_PROGRAM_31_03.md](docs/SOTA_SHOWCASE_BENCHMARK_PROGRAM_31_03.md)
Canonical recovery brief: [docs/CONTEXT_RECOVERY_BRIEF_2026_04_01.md](docs/CONTEXT_RECOVERY_BRIEF_2026_04_01.md)

## 1. Purpose and Relationship to the 22_03 Baseline

This document is a strict execution update that keeps the architecture and intent of the March 22 plan, while integrating all currently verified findings from latest runtime and artifact evidence.

Baseline references preserved in this update:
- Mission and trust objective: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L7)
- Program principles: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L31)
- Phase model 0-5: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L67)
- SOTA test protocol and promotion policy: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L298)
- Timeline and KPI frame: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L345)

Additional enforcement source retained:
- Current handoff phase lock and non-negotiable acceptance criteria: [HANDOFF.md](HANDOFF.md#L388), [HANDOFF.md](HANDOFF.md#L453)

## 2. Integrated Findings (Complete Set)

This section integrates each confirmed finding into the plan with direct evidence.

| ID | Severity | Finding | Evidence | Baseline section impacted |
|---|---|---|---|---|
| F1 | Critical | Quality contract can report contradiction_detected true and final_success true simultaneously | [output/e2e_todo_app/e2e_result.json](output/e2e_todo_app/e2e_result.json#L2606), [output/e2e_todo_app/e2e_result.json](output/e2e_todo_app/e2e_result.json#L2608), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1258), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1297) | Phase 1 fail-closed gates |
| F2 | Critical | Latest run lineage is incomplete; newest trace is not the same run reflected by summary log/result bundle | [logs/pipeline_trace_20260326_001108.jsonl](logs/pipeline_trace_20260326_001108.jsonl#L15), [logs/pipeline_trace_20260326_001108.jsonl](logs/pipeline_trace_20260326_001108.jsonl#L17), [logs/e2e_moderate_latest.txt](logs/e2e_moderate_latest.txt#L1259), [logs/e2e_moderate_latest.txt](logs/e2e_moderate_latest.txt#L1287) | Phase 0 baseline contract |
| F3 | High | code_review_agent exceeded expected timeout envelope (observed ~11810s despite policy hard timeout 600s) | [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L868), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2270), [logs/pipeline_trace_20260326_001108.jsonl](logs/pipeline_trace_20260326_001108.jsonl#L15) | Phase 1 and Phase 2 control-loop fidelity |
| F4 | High | Private control-loop routers remain untested directly (_after_fixing, _after_smoke_test, _goal_eval_route) | [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2519), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2557), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2606), [tests/unit/test_correctness_routing.py](tests/unit/test_correctness_routing.py#L21), [tests/unit/test_workflow_loop_guard.py](tests/unit/test_workflow_loop_guard.py#L15) | Phase 1 route invariants |
| F5 | High | Telemetry parity mismatches are noisy due to asymmetric error_count calculations | [src/utils/pipeline_tracer.py](src/utils/pipeline_tracer.py#L53), [src/utils/pipeline_tracer.py](src/utils/pipeline_tracer.py#L102), [src/utils/pipeline_tracer.py](src/utils/pipeline_tracer.py#L230), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2931), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2940), [output/e2e_todo_app/e2e_result.json](output/e2e_todo_app/e2e_result.json#L5) | Phase 0 observability contract |
| F6 | Medium | VS Code task runner for target pytest set is broken in current shell invocation | [HANDOFF.md](HANDOFF.md#L170), [PROGRESS.md](PROGRESS.md#L216) | Phase 0 operations readiness |
| F7 | Medium | Complex-gate evidence is stale relative to current date and cannot certify current phase progression | [output/e2e_complex_perplexica/complex_run_result_20260322_143632.json](output/e2e_complex_perplexica/complex_run_result_20260322_143632.json), [output/e2e_complex_perplexica/complex_run_summary_20260322_143632.txt](output/e2e_complex_perplexica/complex_run_summary_20260322_143632.txt) | SOTA gates and promotion policy |

## 2.1 Cross-Check Completeness Review (Critical)

This updated plan was cross-checked against the full verified finding set and baseline 22_03 obligations.

Coverage result:
- All previously confirmed operational findings (F1-F7) are represented in the integrated findings table.
- Each finding is mapped to implementation and tests in the traceability matrix (Section 5).
- Baseline phase architecture and SOTA promotion model remain aligned with [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L67) and [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L298).

Residual execution caveat (must be closed during implementation):
- `tests/unit/test_control_loop_routing.py` is a planned Phase 1 addition and is intentionally absent in baseline state; Phase 1 cannot be certified complete until this module exists and passes with the routing suite.

## 3. Updated Program Principles (Delta on Top of 22_03)

Baseline principles from [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L31) remain valid. The following additions are now mandatory:

1. Contradiction-dominance principle:
- If contradiction_detected is true, final_success must be false and publish_eligible must be false.

2. Run-lineage integrity principle:
- A run is certifiable only when trace, status, and result artifacts share one run identity and one terminal outcome.

3. Timeout-fidelity principle:
- Node elapsed time must not exceed effective hard timeout without explicit timeout fallback evidence.

4. Router-closure test completeness principle:
- Every private post-node router that can alter convergence (_after_fixing, _after_smoke_test, _goal_eval_route) must have direct unit coverage.

5. Parity-signal quality principle:
- Parity warnings are reliability signals, not noise. Error-count formulas must be symmetrical between tracer and workflow status snapshots.

## 4. Updated Phase Plan (Mapped to 22_03)

### Phase 0 (Trust Repair and Contract Normalization) - 0 to 24 hours

Baseline mapping:
- Phase 0 baseline contract: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L69)
- Deterministic gate requirements: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L308)

Objectives:
- Remove contradiction-success coexistence.
- Align parity error counting.
- Restore local operator test command reliability.
- Create run-lineage manifest discipline.

Work package P0.1 - Quality contract invariant repair:
- Files:
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1258)
- Changes:
  - Force publish_eligible false when contradiction_detected true.
  - Force final_success false when contradiction_detected true.
  - Add explicit quality_gate_reason field for deterministic postmortem context.
- Tests:
  - Extend [tests/unit/test_correctness_routing.py](tests/unit/test_correctness_routing.py#L325)
  - Add contradiction-dominance tests covering stale-warning carry-forward cases.

Work package P0.2 - Parity symmetry fix:
- Files:
  - [src/utils/pipeline_tracer.py](src/utils/pipeline_tracer.py#L230)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2931)
- Changes:
  - Unify error_count derivation logic in one shared helper.
  - Reduce false mismatch emissions without suppressing real mismatches.
- Tests:
  - Add parity unit tests under tests/unit to validate trace/status symmetry.

Work package P0.3 - Task runner reliability correction:
- Scope:
  - Fix VS Code task command invocation for pytest target currently failing.
- Changes:
  - Use a shell-safe invocation path or command wrapper that executes correctly in pwsh.
- Validation:
  - task shell: pytest-autogit-direct-python must pass from task runner, not only direct terminal.

Work package P0.4 - Run-lineage manifest:
- Output requirement:
  - For each E2E execution, emit `logs/run_lineage_<thread_id>.json`.
  - Required schema fields: run_id, thread_id, trace_file, status_file, result_file, started_at, ended_at, terminal_stage.
  - Required consistency checks: all referenced files exist; terminal_stage matches in trace tail/status/result.
- Validation:
  - Certify only if lineage files exist, schema validation passes, and stage values agree.
  - Add deterministic checker command in implementation phase: `D:\Projects\auto-git\.venv\Scripts\python.exe scripts\tools\check_run_lineage.py --latest`.

Phase 0 acceptance gate:
- No artifact with contradiction_detected true and final_success true.
- No parity mismatch warnings generated by asymmetry defects in a passing deterministic test run.
- Task runner command for core unit bundle is functional.

### Phase 1 (Fail-Closed Terminal Gates + Router Closure Tests) - 24 to 72 hours

Baseline mapping:
- Phase 1 fail-closed intent: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L102)
- Route invariant requirement: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L126)

Objectives:
- Harden terminal routing semantics.
- Close private router test gap.

Work package P1.1 - Terminal gate harmonization:
- Files:
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L434)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L569)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L739)
- Changes:
  - Ensure publish path decisions cannot bypass contradiction or correctness failures due to stale fields.
  - Ensure no-files-generated path does not incorrectly inflate publish-like success semantics.

Work package P1.2 - Private router direct tests:
- Files:
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2519)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2557)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2606)
- New test module to add:
  - tests/unit/test_control_loop_routing.py
- Required test groups:
  - _after_fixing branch matrix
  - _after_smoke_test branch matrix
  - _goal_eval_route branch matrix
  - convergence budget boundary cases

Work package P1.3 - Goal-eval and phase-lock regression reinforcement:
- Expand [tests/unit/test_correctness_routing.py](tests/unit/test_correctness_routing.py#L99) with explicit contradictory-state combinations at phase boundaries.

Phase 1 acceptance gate:
- All routing suites pass with closure test module included.
- No publish-like terminal state accepted when correctness gate is false.

### Phase 2 (Timeout Fidelity + Anti-Thrash Stabilization) - Days 3 to 5

Baseline mapping:
- Anti-thrash and deterministic policy: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L131)
- Provider/runtime enforcement context: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L170)

Objectives:
- Resolve code_review timeout behavior mismatch.
- Prevent silent multi-hour stall windows.

Work package P2.1 - Timeout diagnosis and instrumentation:
- Files:
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L866)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2270)
  - [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L12699)
- Changes:
  - Annotate timeout source in node result (policy hard-timeout, node-internal timeout, provider stall, cancellation delay).
  - Record effective timeout values used at runtime in trace context.

Work package P2.2 - Deterministic fallback on overrun:
- Ensure any node elapsed > effective hard timeout emits timeout fallback patch and warning deterministically.

Work package P2.3 - Anti-thrash loop tuning:
- Tie signature-streak logic to timeout categories so repeated timeout signatures switch strategy earlier.

Phase 2 acceptance gate:
- code_review_agent runtime must satisfy one of the following:
  - `elapsed_s <= effective_hard_timeout_s + 5s` for completed calls, or
  - timeout fallback emitted with explicit `timeout_source` classification and preserved warning artifact.

### Phase 3 (Runtime Failover Profile Enforcement Completion) - Days 5 to 7

Baseline mapping:
- Phase 3 profile enforcement: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L170)

Objectives:
- Close remaining control-plane vs data-plane failover gaps.

Work package P3.1:
- Audit all node model acquisition points for profile enforcement consistency.

Work package P3.2:
- Add trace markers proving profile and provider-family selection decisions at each node.

Work package P3.3:
- Add regression tests for provider cooldown and family suppression interaction.

Phase 3 acceptance gate:
- Every LLM node emits profile and provider-family decision trace metadata.

### Phase 4 (Checklist State, Replanner, Tool Scope) - Week 2

Baseline mapping:
- Phase 4 details: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L200)

Objectives:
- Make requirement completion proof-bearing.
- Enable bounded replanning triggers.

Work package P4.1:
- Requirement evidence model with pointers to test and runtime artifacts.

Work package P4.2:
- Replanner triggers for confidence collapse, repeated same-signature failures, and timeout streaks.

Work package P4.3:
- Stage-level tool allowlist enforcement and audit logs.

Phase 4 acceptance gate:
- Every requirement has a machine-checkable evidence record before final publish path.

### Phase 5 (Trajectory Evidence and Release Governance) - Week 3

Baseline mapping:
- Phase 5 details: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L230)
- Definition of done alignment: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L408)

Objectives:
- Ensure repeatable diagnosis and release certification.

Work package P5.1:
- Persist trajectory bundles for each attempt (decision, patch summary, tests, failure signature, rollback action).

Work package P5.2:
- Extend doctor/replay with ranked remediation guidance from observed bucket history.

Work package P5.3:
- Release scorecard with trend gating and freshness checks.

Phase 5 acceptance gate:
- Two consecutive cycles pass all gate requirements with zero contradiction states.

## 5. Finding-to-Action Traceability Matrix

| Finding | Actions | Tests | Completion evidence |
|---|---|---|---|
| F1 | P0.1, P1.1 | contradiction-dominance routing tests | quality_gate has contradiction false for all success states |
| F2 | P0.4 | run-lineage integrity checker tests | trace/status/result manifest shows single coherent run |
| F3 | P2.1, P2.2 | timeout-overrun regression tests | no unclassified > hard_timeout elapsed nodes |
| F4 | P1.2 | new router closure unit suite | complete branch coverage for closure routers |
| F5 | P0.2 | parity symmetry tests | parity mismatch warnings reduced to genuine mismatches only |
| F6 | P0.3 | task execution smoke test | VS Code task command runs green |
| F7 | Gate execution schedule | complex gate runs refreshed | complex artifacts updated and timestamp-fresh |

## 6. Updated SOTA Test Protocol and Promotion Rules

Baseline reference:
- [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md#L298)
- [HANDOFF.md](HANDOFF.md#L413)

Mandatory gate order after each completed phase:
1. Deterministic unit gate
2. Moderate E2E gate
3. Complex one-shot gate
4. Complex bounded pack gate

Execution preflight (mandatory before gates):
- Confirm interpreter:
  - D:\Projects\auto-git\.venv\Scripts\python.exe -c "print('AUTO_GIT_VENV_OK')"
- Confirm task path if using VS Code tasks:
  - task shell: pytest-autogit-direct-python
  - If task fails in pwsh path resolution, run gate commands directly with the .venv interpreter and log this in run artifacts.

Deterministic gate commands (canonical):
- D:\Projects\auto-git\.venv\Scripts\python.exe -m pytest tests/unit/test_pipeline_todo_tracking.py tests/unit/test_state_contracts.py tests/unit/test_mcp_server_manager.py -q
- D:\Projects\auto-git\.venv\Scripts\python.exe -m pytest tests/unit/test_integration_plan_controls.py tests/unit/test_nodes_zero_cost.py tests/unit/test_phase_d_ops_tools.py tests/unit/test_model_manager_large_prompt_controls.py -q

Deterministic gate commands (alternative when .venv is unavailable):
- conda run -n auto-git python -m pytest tests/unit/test_pipeline_todo_tracking.py tests/unit/test_state_contracts.py tests/unit/test_mcp_server_manager.py -q
- conda run -n auto-git python -m pytest tests/unit/test_integration_plan_controls.py tests/unit/test_nodes_zero_cost.py tests/unit/test_phase_d_ops_tools.py tests/unit/test_model_manager_large_prompt_controls.py -q

Moderate gate command:
- D:\Projects\auto-git\.venv\Scripts\python.exe run_e2e_moderate.py

Complex one-shot gate command:
- D:\Projects\auto-git\.venv\Scripts\python.exe tests/e2e/run_e2e_complex_perplexica_once.py

Complex bounded pack gate command:
- D:\Projects\auto-git\.venv\Scripts\python.exe scripts/run_complex_verification_bounded.py

Additional promotion blockers (new):
- Block promotion if any artifact reports contradiction_detected true.
- Block promotion if run-lineage manifest is missing or inconsistent.
- Block promotion if latest complex gate artifacts are older than 72 hours.

## 7. 24h / 72h / 7-Day Execution Schedule

### First 24 hours
- Complete Phase 0 packages P0.1 to P0.4.
- Run deterministic gate set.
- Produce baseline-corrected scorecard.

### Within 72 hours
- Complete Phase 1 packages P1.1 to P1.3.
- Run deterministic + moderate gates.
- Confirm no contradiction-success coexistence and no untested closure routers.

### Within 7 days
- Complete Phase 2 and Phase 3 packages.
- Run full four-gate SOTA protocol.
- Archive and publish updated readiness matrix.

## 8. Risks, Controls, and Rollback

R1 - Over-correction on fail-closed gating blocks legitimate success:
- Control: route-level tests for clean success path and contradiction path.
- Rollback: revert only gating delta commit, keep test additions.

R2 - Timeout fix introduces false positives:
- Control: classify timeout source and assert only hard timeout envelope breaches trigger fallback.
- Rollback: keep instrumentation, disable strict enforcement via config flag while retaining logs.

R3 - Parity fix hides real mismatches:
- Control: keep mismatch emission but unify formulas; do not suppress mismatch category.
- Rollback: compare old/new parity outputs using replay traces before full rollout.

R4 - Task runner changes become shell-specific:
- Control: validate in pwsh and cmd contexts.
- Rollback: retain direct .venv fallback documented in runbook.

## 9. Definition of Done for This Updated Plan

This updated plan is considered complete only when all conditions below are true:

1. No certifiable run contains contradiction_detected true with final_success true.
2. All private control-loop closure routers have direct unit test coverage.
3. code_review timeout behavior is classified and bounded by effective policy or explicit fallback reason.
4. Parity mismatches represent genuine divergence, not formula asymmetry.
5. Task runner path is operational for core deterministic suite.
6. Complex gate artifacts are refreshed and pass promotion criteria.
7. Promotion only proceeds with all SOTA gates passing and artifacts archived.

## 10. Immediate Implementation Queue (Actionable)

1. Implement P0.1 and P0.2 first in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1258) and [src/utils/pipeline_tracer.py](src/utils/pipeline_tracer.py#L230).
2. Fix task runner command path and validate task execution (P0.3).
3. Implement run-lineage manifest output and checker (P0.4).
4. Add private router closure tests (P1.2) and run deterministic suite.
5. Implement timeout-fidelity instrumentation and fallback verification (P2.1/P2.2).
6. Execute full SOTA four-gate protocol and archive fresh artifacts.

## 11. Notes on Scope Discipline

In alignment with [HANDOFF.md](HANDOFF.md#L388), this plan does not introduce broad roadmap expansion before current trust and convergence defects are resolved. The immediate priority is correctness and certifiability, not feature breadth.

## 12. Swarm Panel Addendum (Session 41)

This addendum captures a three-perspective critical panel review to maximize score lift from current output quality.

Score objective:
- Raise operational output score from approximately 4.2/10 to 8.0-8.3/10 within 7 days, contingent on passing phase gates.

### 12.1 Panel Perspectives (Critical, Non-Overlapping)

1. Perspective A - Fail-Closed Reliability (control-loop correctness)
- Primary concern:
  - false-green outcomes (publish-like semantics without certifiable correctness)
- Priority actions:
  - hard enforce contradiction-dominance in quality contract
  - close router branch-matrix gaps for post-fix and post-smoke routing
  - enforce lineage consistency as a fail-closed condition in finalization

2. Perspective B - Runtime SRE and Provider Resilience (time-budget fidelity)
- Primary concern:
  - long stalls and provider-thrash degrade completion reliability in complex runs
- Priority actions:
  - classify timeout source deterministically for every timeout event
  - introduce per-call timeout guards in high-cost nodes (not only node-level wrapper)
  - split free/paid provider lanes and trip provider-family fail-fast on auth/quota failures

3. Perspective C - Verification and Benchmark Governance (certification discipline)
- Primary concern:
  - incomplete evidence or stale artifacts reduce promotion trust even when partial runs succeed
- Priority actions:
  - enforce trace/status/result coherence as promotion prerequisite
  - add parity symmetry contract for error_count across tracer and workflow status
  - require fresh complex evidence within SLA before promotion

### 12.2 Delta Work Packages (Added to Existing Phase Plan)

Work package P0.5 - Lineage strictness enforcement:
- Files:
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L291)
  - [scripts/tools/check_run_lineage.py](scripts/tools/check_run_lineage.py)
  - [tests/unit/test_run_lineage_manifest.py](tests/unit/test_run_lineage_manifest.py)
- Changes:
  - treat missing or empty status terminal stage as inconsistency
  - fail closed in finalization if trace/status/result stage agreement is not proven
- Validation:
  - add deterministic tests for missing file, empty stage, and stage mismatch

Work package P1.4 - Router closure matrix and contradiction dominance:
- Files:
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1258)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2519)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2557)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2606)
- Tests:
  - add [tests/unit/test_control_loop_routing_extended.py](tests/unit/test_control_loop_routing_extended.py)
  - expand [tests/unit/test_correctness_routing.py](tests/unit/test_correctness_routing.py)
- Changes:
  - enforce contradiction_detected => final_success false and publish_eligible false
  - cover boundary states for _after_fixing, _after_smoke_test, and _goal_eval_route behavior

Work package P1.5 - Telemetry parity symmetry contract:
- Files:
  - [src/utils/pipeline_tracer.py](src/utils/pipeline_tracer.py#L230)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2931)
- Changes:
  - compute error_count through one shared helper used by tracer and workflow status
- Tests:
  - add [tests/unit/test_parity_symmetry.py](tests/unit/test_parity_symmetry.py)

Work package P2.4 - Timeout-source fidelity and deterministic overrun fallback:
- Files:
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L866)
  - [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2270)
  - [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L12699)
- Changes:
  - annotate timeout_source as one of: policy_hard_timeout, node_internal_timeout, provider_stall, cancellation_delay
  - if elapsed exceeds effective hard timeout, emit deterministic timeout fallback artifact
- Validation:
  - extend timeout regression tests in routing and node suites

Work package P3.4 - Provider lane split and fail-fast family trip:
- Files:
  - [src/utils/model_manager.py](src/utils/model_manager.py)
  - [config/model_backends.yaml](config/model_backends.yaml)
- Changes:
  - explicit free-lane and paid-lane routing with bounded retries per lane
  - auth/quota failures trip provider family and route immediately to next provider
- Validation:
  - provider failfast regression tests and complex run recovery telemetry

### 12.3 Mandatory KPI Targets (Swarm Panel)

1. Trust and certifiability:
- contradiction and final_success co-occurrence: 0
- lineage inconsistencies in certifiable runs: 0

2. Runtime stability:
- unclassified timeout events: 0
- provider-thrash loops per complex run: <= 1

3. Test closure:
- router closure branch coverage: >= 95%
- parity mismatch false-positive rate: < 1%

4. Operations:
- deterministic task runner success rate in pwsh and cmd: >= 99%

### 12.4 Score Lift Forecast (If Executed in Order)

1. Phase 0 plus Phase 1 delta (P0.5, P1.4, P1.5):
- expected lift: +3.2 to +4.1 points

2. Phase 2 plus Phase 3 delta (P2.4, P3.4):
- expected lift: +1.0 to +1.8 points

3. Net expected range after full addendum execution:
- projected score: 8.0 to 8.3/10

### 12.5 Execution Order Constraint

Do not reorder these deltas:
1. P0.5
2. P1.4
3. P1.5
4. P2.4
5. P3.4

Rationale:
- certifiability and correctness controls must become trustworthy before runtime acceleration is considered score-bearing.

## 13. Swarm Debate Synthesis 01-04 (OpenClaw, Deep Agents, Leaked-Harness Patterns)

This section records a four-stream swarm analysis plus sequential-thinking debate to decide what should be integrated next.

Evidence streams used:
1. OpenClaw and leaked-harness clean-room runtime pattern audit from [external/claw-code/README.md](external/claw-code/README.md#L28), [external/claw-code/src/runtime.py](external/claw-code/src/runtime.py#L90), [external/claw-code/src/query_engine.py](external/claw-code/src/query_engine.py#L61), [external/claw-code/src/tools.py](external/claw-code/src/tools.py#L62), [external/claw-code/src/session_store.py](external/claw-code/src/session_store.py#L19).
2. Deep Agents pattern/status audit against current implementation in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2945), [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L9528), [src/utils/middleware.py](src/utils/middleware.py).
3. Borrowed-features status audit from [PIPELINE_IMPROVEMENT_PLAN.md](PIPELINE_IMPROVEMENT_PLAN.md#L42), [docs/BORROWED_FEATURES_INTEGRATION_PLAN_2026.md](docs/BORROWED_FEATURES_INTEGRATION_PLAN_2026.md#L5), [PROGRESS.md](PROGRESS.md).
4. External best-practice cross-check for checkpointing, context isolation, policy hooks, and HITL discipline.

Debate method:
1. Integrate-aggressively position: finish highest-ROI unfinished improvements from ranked backlog.
2. Conservative-hardening position: borrow architecture patterns only, avoid snapshot-mirror execution surfaces.
3. Operations-cost position: stage changes by measurable KPI improvement and retain deterministic fallbacks.

### 13.1 Decision Verdict

Integrate now (Phase A, immediate):
1. Semgrep SAST gate in code testing path.
- Target: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py) in code_testing_node.
- Reason: closes known security blind spot and is already rank 10 candidate in [PIPELINE_IMPROVEMENT_PLAN.md](PIPELINE_IMPROVEMENT_PLAN.md#L51).
2. Speculative diff-based fixing in fix loop.
- Target: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L9528) and [src/utils/middleware.py](src/utils/middleware.py).
- Reason: strongest remaining Aider-style gap; expected reduction in oscillation/churn.
3. Repo map and code graph consistency checks.
- Target: [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L299), [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L4747).
- Reason: directly improves cross-file correctness for regeneration cycles.
4. TDD loop insertion around feature verification and fixing.
- Target: [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2999), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L3011), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L3022).
- Reason: converts test feedback into first-class generation constraints.
5. Runtime manifest plus transcript compaction standardization.
- Target: [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L3100), [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L2830).
- Reason: improves reproducibility and long-run context stability.

Integrate next (Phase B, after Phase A gate passes):
1. Pipeline-native MCP routing layer for selected nodes only.
- Start with research, code_testing, and git_publishing.
2. Playwright browser verification path for web projects.
3. Provider-lane ensemble voting for high-risk generation decisions only.

Reject for integration (do not adopt):
1. Snapshot-mirror command/tool execution architecture from claw-code.
2. Stubbed deferred-init or remote runtime modes that do not execute real work.
3. Token-overlap prompt routing as primary control-plane router for this DAG.

### 13.2 Status Cross-Check Against Current Implementation

Already strong and should be preserved:
1. Phase-lock gating and correctness contract in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1511).
2. Loop detection, compaction, and offload primitives in [src/utils/middleware.py](src/utils/middleware.py) and [src/utils/context_offload.py](src/utils/context_offload.py).
3. Deep fix-loop controls and prompt-budget tracking in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L4749) and [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L9528).

Still incomplete relative to borrowed-roadmap intent:
1. Ranked items 6-10 are not fully closed in [PIPELINE_IMPROVEMENT_PLAN.md](PIPELINE_IMPROVEMENT_PLAN.md#L47).
2. MCP manager exists but pipeline-native usage remains partial: [src/cli/claude_code_cli.py](src/cli/claude_code_cli.py#L133).
3. Aider-style diff-first editing is not yet the default fix strategy.

### 13.3 Phase A Acceptance Gate (Required Before Advancing)

All of the following must pass in one fresh moderate run:
1. No contradiction state: contradiction_detected must never coexist with final_success true.
2. Fix-loop efficiency improves versus current baseline:
- target: at least 20 percent reduction in average fix iterations for moderate run set.
3. Security gate active:
- Semgrep findings captured into test results and used in route decisions.
4. Cross-file consistency improves:
- reduction in import/signature mismatch regressions after regeneration cycles.
5. Runtime artifact discipline:
- lineage manifest and runtime manifest both emitted and coherent.

### 13.4 Execution Order Constraint for Section 13

Do not reorder this section's implementation sequence:
1. Semgrep SAST wiring.
2. Diff-based fixing path.
3. Repo map and code graph consistency checks.
4. TDD loop integration.
5. Runtime manifest standardization.

Rationale:
- This sequence maximizes correctness and safety first, then raises consistency and development speed without weakening fail-closed behavior.
