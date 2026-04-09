# Borrowed Features Integration Plan (DeepAgents + DeerFlow + OpenClaw)

Date: 2026-03-16
Scope: Auto-GIT reliability, quality, and production hardening using proven patterns from DeepAgents, DeerFlow, and OpenClaw.
Status: In progress. This document now includes live implementation status notes.

## Implementation Status Snapshot (2026-03-16)

Legend: complete = implemented and test-covered, partial = implemented but not fully productized or still quality-limited.

| Area | Status | Notes |
|---|---|---|
| Structured error envelope | complete | Implemented in workflow wrapper with error_code/root_cause/remediation/retryable payloads. |
| Global loop guard | complete | Workflow-level loop fingerprints, hard limits, loop events, and route forcing implemented. |
| Telemetry parity checks | complete | Trace/status parity validator and strict/warn policy in workflow + CLI. |
| Context offload + pointer substitution | complete | Offload refs and pointer-based compaction in workflow middleware. |
| Explicit summarize trigger | complete | summarize_now trigger compacts state deterministically in heavy loop phases. |
| Todo context restoration | complete | todo_context_pointer restoration notes + tests implemented. |
| Fan-out governance | complete | Stage caps for perspectives and policy events implemented. |
| Trust/allowlist policy gating | complete | constrained/untrusted block high-risk paths and strict allowlist gate publishing. |
| HITL approvals | complete | Added CLI-productized HITL flow for risky publish operations (`--hitl-git-publishing`, `--hitl-interactive`) and wired decisions into generate/replay pipeline execution. |
| Checkpointer provider abstraction | complete | memory/sqlite/local/redis abstraction + load helpers implemented. |
| Replay/doctor ops tooling | complete | CLI replay/doctor implemented with resumability diagnostics. |
| Model failover profile controls | complete | profile-driven failover chain and selection implemented. |
| Throughput optimization (SOTA-style reuse) | complete | Added artifact-fingerprint-based reuse for expensive code_testing/feature_verification/smoke_test node outputs when artifacts unchanged. |
| Runtime-aware cache invalidation | complete | Added runtime-relevance fingerprint mode so documentation-only changes do not invalidate expensive runtime verification caches. |
| State shape stability | complete | Added runtime list-shape coercion for errors/warnings to prevent type drift in long runs. |

### Latest delta in this session

1. Workflow-level normalization added for trust mode, allowlist mode, failover profile, and telemetry parity mode.
2. Fixed parity_mode runtime regression during parity bookkeeping.
3. Added artifact fingerprint reuse cache for code_testing and smoke_test to reduce repeated heavy work.
4. Hardened runtime state merge/finalization to coerce errors/warnings to list shape.
5. Expanded unit tests in tests/unit/test_phase_d_ops_tools.py and tests/unit/test_integration_plan_controls.py.
6. Extended reusable-node cache to include feature_verification and added runtime-aware fingerprinting to avoid invalidating cache on docs-only changes.
7. Added cloud-only runtime guardrails: global local-model disable switch + Perplexica gating in model manager, workflow, SOTA researcher, and CLI.
8. Added CLI cloud-only mode toggle for generate/replay runs to enforce AUTOGIT_DISABLE_LOCAL_MODELS=true and PERPLEXICA_ENABLED=false at runtime.
9. Added workflow preflight fail-fast for cloud-only runs with no cloud keys configured (prevents late pipeline collapse).
10. Added fix-loop stagnation escape hatch: repeated unchanged code_fixing artifacts route back to code_generation instead of repeated retests.
11. Added bounded deduplicated append-only state merging to prevent errors/warnings/resource log bloat in long runs.
12. Added pre-node payload trimming for strategy_reasoner/code_fixing to reduce provider 413 request-too-large failures.
13. Hardened code-review parse reliability in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py): added multi-pass JSON salvage plus deterministic static fallback checks (entry point, relative imports, stubs, encoding) so review no longer silently skips when LLM output is malformed.
14. Ran bounded cloud-only benchmark attempts: early/mid pipeline stages completed, but architecture/codegen remained provider-latency bound under 429/timeout conditions; this confirms cloud-only control paths are active while exposing remaining provider resilience bottlenecks.
15. Fixed architect-spec robustness in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py): normalized non-string fields from LLM JSON (including list/dict pseudocode and purpose fields) to prevent list.splitlines crashes and unnecessary fallback.
16. Added timeout-driven health/circuit behavior in [src/utils/model_manager.py](src/utils/model_manager.py): timed-out model routes now enter temporary cooldown and contribute to provider circuit-tripping, reducing repeated long stalls on degraded endpoints.
17. Hardened eval parser reliability in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py): `pipeline_self_eval_node` and `goal_achievement_eval_node` now use multi-pass JSON parsing with deterministic fallback payloads and explicit warning markers (`SELF_EVAL_JSON_FALLBACK_USED`, `GOAL_EVAL_JSON_FALLBACK_USED`).
18. Added Phase 1 regression coverage in [tests/unit/test_nodes_zero_cost.py](tests/unit/test_nodes_zero_cost.py) for malformed self-eval/goal-eval outputs to verify safe fallback behavior and warning emission.
19. Added Phase 2 regression coverage in [tests/unit/test_model_manager_large_prompt_controls.py](tests/unit/test_model_manager_large_prompt_controls.py) for large-prompt attempt-budget enforcement and same-call provider-family timeout suppression.
20. Completed post-phase SOTA validation runs:
	- Phase 1 pack: `tests/unit/test_nodes_zero_cost.py::TestEvalParserFallback` + `tests/unit/test_state_contracts.py` -> 20 passed.
	- Phase 2 pack: `tests/unit/test_model_manager_large_prompt_controls.py` + `tests/unit/test_integration_plan_controls.py` -> 23 passed.
21. Ran a combined cross-phase gate pack (`TestEvalParserFallback` + `test_state_contracts` + `test_model_manager_large_prompt_controls` + `test_integration_plan_controls`) -> 43 passed, confirming no interaction regressions between Phase 1 and Phase 2 hardening.
22. Executed bounded cloud-only runtime smoke (`stop_after=requirements_extraction`) and found a runtime dependency gap (`ModuleNotFoundError: langchain_openai`), then fixed by installing `langchain-openai` and re-ran successfully -> `current_stage=requirements_extracted`, `errors=0`, `warnings=0`.
23. Completed HITL UX productization for risky operations in [auto_git_cli.py](auto_git_cli.py): added explicit and interactive publish decisions (`--hitl-git-publishing`, `--hitl-interactive`) for both `generate` and `replay --resume-run`, then passed decisions via `hitl_decisions` to workflow policy enforcement.
24. Added/ran HITL CLI regression tests in [tests/unit/test_phase_d_ops_tools.py](tests/unit/test_phase_d_ops_tools.py) validating pass-through and interactive decision capture -> 18 passed.
25. Expanded combined regression gate to include HITL ops tooling coverage (`TestEvalParserFallback` + `test_state_contracts` + `test_model_manager_large_prompt_controls` + `test_integration_plan_controls` + `test_phase_d_ops_tools`) -> 61 passed.
26. Ran deeper cloud-only bounded runtime smoke to `stop_after=code_generation` and reached `current_stage=code_generated` with `errors=0`, confirming end-to-end progression through generation under cloud-only constraints; observed expected provider-latency/429 pressure in free-tier model endpoints.
27. Closed additional runtime dependency gap discovered during deeper smoke by installing `langchain-groq`; validated with follow-up bounded cloud-only run to `stop_after=architect_spec` -> `current_stage=architect_spec_complete`, `errors=0`, `warnings=0`.
28. Fixed Python 3.14 AST compatibility regression in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py) by removing direct `ast.Str` assumptions in three code/testing paths and switching to compatibility-safe docstring node handling.
29. Added regression coverage in [tests/unit/test_nodes_zero_cost.py](tests/unit/test_nodes_zero_cost.py) (`test_handles_missing_ast_str_node`) to validate behavior when `ast.Str` is absent.
30. Re-ran bounded complex verification with increased per-case timeout (`AUTOGIT_COMPLEX_CASE_TIMEOUT_S=900`) using [scripts/run_complex_verification_bounded.py](scripts/run_complex_verification_bounded.py): `ok=3/3`, `timeouts=0`, `exceptions=0`; all cases reached `current_stage=testing_complete` (summary: [logs/complex_verification_bounded_20260317_232416.json](logs/complex_verification_bounded_20260317_232416.json)).

## 1) Parallel Pipeline Observation (Single Subagent)

Observation source: one read-only Explore subagent run over the live workspace.

### Runtime finding
- Current pipeline run was not active at inspection time.
- Latest observed run failed early at requirements extraction stage.
- Trace indicated requirements extraction ended in requirements_extraction_failed after about 81 seconds.
- Status artifacts were inconsistent with trace (status report showed no effective progress while trace showed node execution).

### Reliability implication
- Early-stage failure visibility is weak.
- Telemetry consistency between trace and status snapshots needs hardening.
- Recovery and diagnosis paths should be made deterministic.

## 2) Current Auto-GIT Weak Points (Code-Grounded)

| Weak point | Why it matters | Current location(s) | Borrow candidate |
|---|---|---|---|
| Broad exception swallowing across nodes | Failures become non-actionable; root cause can be hidden | src/langraph_pipeline/nodes.py | DeerFlow ToolErrorHandlingMiddleware style normalization + structured error envelopes |
| Missing global repetitive-loop guard (beyond local oscillation logic) | Pipeline may revisit unproductive cycles under edge cases | src/langraph_pipeline/nodes.py, src/langraph_pipeline/workflow_enhanced.py | DeerFlow loop detection middleware pattern |
| Trace/status mismatch risk | Production observability confidence drops | logs status + trace artifacts, workflow reporting paths | OpenClaw ops-style health/doctor contracts + stricter event schema |
| Context growth in long runs still expensive | Degrades quality in deep fix loops | src/langraph_pipeline/nodes.py, workflow prompt assembly | DeepAgents pointer-based offloading + summarization control |
| Subagent/task fan-out governance is limited | Resource spikes and noisy delegation can reduce quality | strategy/debate delegation paths | DeerFlow SubagentLimitMiddleware + DeepAgents subagent contracts |
| Human safety gates are optional/limited for risky actions | Risky publish/exec paths can proceed without policy review | publish/exec flow in workflow and nodes | DeepAgents interrupt_on approvals + OpenClaw policy defaults |
| Checkpoint lifecycle and replay ergonomics can improve | Slower incident recovery and harder postmortems | workflow checkpointer setup and run scripts | DeepAgents/LangGraph persistence patterns |
| Tool policy is not centrally allowlisted by trust level | Harder to enforce least-privilege at runtime | tool usage spread across nodes | OpenClaw explicit allowlist/denylist runtime policy model |

## 3) Borrow Catalog: What to Integrate

## 3.1 From DeepAgents

| Feature | Keep as-is from source? | Auto-GIT adaptation |
|---|---|---|
| Context offload with file-pointer substitution for large tool inputs/results | Pattern only | Add context-offload service that persists large intermediate payloads and injects compact pointers in prompts |
| Summarization triggers plus optional tool-triggered summarization | Pattern only | Add deterministic summarize_now control in fix loop + keep automatic threshold summarization |
| interrupt_on per-tool HITL decisions (approve/edit/reject) | Pattern only | Gate publish, destructive shell, and high-risk edits via policy-driven approvals |
| Strong subagent contract schema | Pattern only | Define explicit subagent spec object with tool/model/context constraints |
| Composite backend memory routing | Pattern only | Route short-term run state vs long-term memory to separate stores |
| CLI safe non-interactive shell policy | Pattern only | Add shell allowlist mode for unattended runs |

## 3.2 From DeerFlow

| Feature | Keep as-is from source? | Auto-GIT adaptation |
|---|---|---|
| LoopDetectionMiddleware (hash repeated call sets, warn then hard-stop) | Pattern only | Add workflow-level loop detector across node transitions and strategy cycles |
| SubagentLimitMiddleware (truncate excess parallel calls) | Pattern only | Enforce max fan-out per stage and per turn |
| ToolErrorHandlingMiddleware (normalize exceptions) | Pattern only | Convert tool/node exceptions into structured state errors with codes and remediation hints |
| ThreadData path isolation contract | Pattern only | Strengthen per-run workspace/uploads/outputs contracts for run artifacts |
| Todo context-loss reminder | Pattern only | Re-inject todo summary when compaction/summarization removes earlier todo context |
| Checkpointer provider abstraction | Pattern only | Standardize memory/sqlite/postgres checkpointer provider entrypoint |

## 3.3 From OpenClaw

| Feature | Keep as-is from source? | Auto-GIT adaptation |
|---|---|---|
| Allowlist-first trust policy for untrusted surfaces | Pattern only | Enforce least-privilege tool policy by execution context |
| Doctor-style ops diagnostics | Pattern only | Add autogit doctor command validating env, model keys, checkpoints, sandbox health |
| Explicit runtime safety defaults and channel/policy separation | Pattern only | Separate trusted local run mode vs constrained automation mode |
| Model failover profile controls | Pattern only | Add model routing profiles with deterministic failover order and health scoring |
| Operational runbook depth | Pattern only | Add failure class runbooks and self-heal actions in CLI output |

## 4) Full Integration Plan (Phased)

## Phase A: Reliability Foundation (2-4 days)
Goal: eliminate silent failures and improve diagnosis fidelity.

1. Structured error envelope
- Add canonical error schema: error_code, stage, source, root_cause, remediation, retryable.
- Touch points: src/langraph_pipeline/nodes.py, src/langraph_pipeline/state.py.

2. Global loop guard
- Add node-transition fingerprinting and hard-stop policy.
- Touch points: src/langraph_pipeline/workflow_enhanced.py, src/utils/middleware.py.

3. Telemetry contract hardening
- Enforce parity between trace events and status snapshots.
- Touch points: src/utils/pipeline_tracer.py, workflow progress reporting paths.

Acceptance checks:
- Any node failure emits structured error with root cause class.
- No run can loop indefinitely without explicit terminal state.
- Trace/status consistency checker passes for synthetic failure scenarios.

## Phase B: Context and Quality Stability (3-6 days)
Goal: preserve reasoning quality in long runs and fix loops.

1. Context offload service
- Persist large intermediate content and replace with path pointers + previews.

2. Dual summarization strategy
- Automatic threshold summarization + explicit summarize command in fix loops.

3. Todo context restoration
- Re-inject active todo state after context compaction.

Touch points:
- src/langraph_pipeline/nodes.py
- src/langraph_pipeline/workflow_enhanced.py
- src/langraph_pipeline/state.py
- new helper module under src/utils for offload index and retrieval.

Acceptance checks:
- Prompt token load reduced on long fix loops.
- Quality regression tests unchanged or improved.
- No missing todo state after compaction in test harness.

## Phase C: Delegation and Safety Controls (3-5 days)
Goal: controlled parallelism and safer execution.

1. Subagent/task fan-out caps per stage.
2. Tool allowlist policy by trust mode.
3. Optional HITL approvals for high-risk operations.

Touch points:
- src/langraph_pipeline/workflow_enhanced.py
- src/langraph_pipeline/nodes.py
- cli config and policy loading path.

Acceptance checks:
- Fan-out never exceeds configured limits.
- High-risk tool calls blocked or gated in constrained mode.
- HITL flow tested with approve/reject/edit cases.

## Phase D: Production Ops and Recovery (3-5 days)
Goal: shorten MTTR and improve unattended reliability.

1. Checkpointer provider abstraction and replay helpers.
2. autogit doctor diagnostics command.
3. Model failover profile with health-aware fallback.

Touch points:
- checkpointer setup in workflow and CLI entry paths
- new diagnostics command in CLI module
- model router/fallback manager modules.

Acceptance checks:
- Replay from checkpoint works after injected failures.
- doctor detects known env/config breakages.
- failover switches provider without pipeline crash.

## 5) Rough Estimate Table: Expected Improvements

Baseline assumptions use current observed behavior and existing internal docs.
Ranges are conservative and confidence-tagged.

| Improvement area | Feature source | Baseline pain | Expected delta after implementation | Confidence |
|---|---|---|---|---|
| Silent failure diagnosability | DeerFlow + OpenClaw | Early-stage failures can be under-specified | 60-80% faster root-cause identification time | Medium-High |
| Infinite/near-infinite loop risk | DeerFlow | Oscillation still possible in edge paths | 70-90% reduction in pathological repeat loops | High |
| Long-run prompt bloat | DeepAgents | Context pressure in long fix cycles | 25-40% reduction in prompt token footprint on long runs | Medium |
| Output quality consistency in long tasks | DeepAgents + DeerFlow | Late-loop quality degradation risk | 10-20% improvement in self-eval and goal-eval stability | Medium |
| Production safety for risky actions | DeepAgents + OpenClaw | Risk controls are not uniformly policy-driven | 50-70% reduction in unsafe unattended actions | Medium |
| Resource spikes from uncontrolled delegation | DeerFlow + DeepAgents | Fan-out variance impacts reliability | 20-35% improvement in run-to-run latency variance | Medium |
| Incident recovery speed (MTTR) | OpenClaw + LangGraph persistence patterns | Manual triage and restart steps | 30-50% faster recovery from failed runs | Medium |
| Observability trustworthiness | OpenClaw ops discipline | Trace/status inconsistencies possible | 70-90% improvement in report consistency confidence | Medium-High |

## 6) Rough Estimate Table: Quality and Production Outcomes

| Outcome class | Metric | Current (qualitative) | Post-integration target (rough) |
|---|---|---|---|
| Quality | Goal-eval implementation coverage | Moderate variance by task complexity | +8 to +15 points on moderate-complexity tasks |
| Quality | Fix-loop effectiveness | Good but with occasional oscillation | 15-30% fewer fix attempts to convergence |
| Quality | End-to-end determinism | Medium | Medium-High with policy gates and replay support |
| Production | Failure observability | Medium-Low in some edge cases | High with structured errors + doctor + parity checks |
| Production | Recovery workflow | Manual-heavy | Semi-automated restart/replay with diagnostics |
| Production | Safety posture | Mixed by mode | Explicit trust modes and risk-gated actions |

## 7) Code Difference Blueprint (Planned, Not Implemented)

| Change type | Estimated files touched | Notes |
|---|---|---|
| Modify existing workflow/state/node modules | 5-9 files | Mainly workflow_enhanced.py, state.py, nodes.py, model/router modules |
| Add new utility modules (loop guard, context offload, policy) | 3-6 files | Isolated helpers for maintainability |
| Add/upgrade tests | 6-12 test files | Unit + integration for loop, policy, replay, telemetry parity |
| CLI diagnostics additions | 1-3 files | doctor command and related health checks |
| Docs/runbooks updates | 3-6 files | setup, safety, failover, replay, troubleshooting |

## 8) Rational Constraints and Non-Hallucination Notes

1. Estimates are ranges, not guarantees.
2. Gains depend on model quality, API stability, and workload mix.
3. Some DeepAgents/OpenClaw capabilities are product-surface features; only architecture patterns are proposed for Auto-GIT.
4. No assumption is made that all external design choices are universally better; integration is selective and pipeline-goal aligned.

## 9) Recommended Execution Order

1. Phase A first (reliability and telemetry correctness).
2. Then Phase B (context quality stabilization).
3. Then Phase C (safety and controlled delegation).
4. Then Phase D (ops tooling and recovery acceleration).

This order minimizes risk and produces measurable wins earliest.

## 10) SOTA Testing Program (Added 2026-03-18)

Goal: move from stage-completion validation to correctness-truth validation with modern test strategy layering.

### 10.1 Test pyramid for Auto-GIT pipeline

1. Deterministic unit tests (fast, zero cost)
- Routing semantics: verify publish/fix transitions against correctness gates.
- State contracts: required fields, defaults, and merge-shape invariants.
- Parser hardening: malformed model outputs map to deterministic fallback payloads.

2. Property-based tests (Hypothesis-style)
- Generate random state permutations to validate invariants:
	- publish is blocked when hard_failures is non-empty.
	- correctness_passed implies tests_passed and hard_failures is empty.
	- loop detector eventually enters hard_limit under repeated signatures.

3. Mutation testing (mutmut-style, incremental)
- Mutate routing predicates and gate logic to ensure tests kill semantic regressions.
- Focus mutation targets on:
	- should_fix_code
	- should_regen_or_publish
	- goal-eval routing and publish gates
- Execution note: mutmut requires fork support; on Windows run via WSL.

4. Metamorphic and differential checks
- Re-run same generated artifact set with docs-only changes; runtime verification cache behavior must remain stable.
- Inject equivalent error payload shapes (string/list/dict forms) and assert identical correctness classification.

5. Benchmark harness and leaderboard discipline
- Keep bounded 3-case benchmark as the release gate.
- Track two separate success metrics:
	- stage_complete_rate
	- correctness_pass_rate
- Treat false-green as a blocker regardless of stage completion.

### 10.2 Release quality gates

1. Required green suites
- routing/contract unit suite
- eval-parser fallback suite
- model failover/large-prompt control suite
- bounded complex verification suite

2. Required thresholds
- false-green rate = 0%
- publish-with-hard-failure rate = 0%
- correctness_pass_rate non-regressive against baseline

3. Stop-the-line conditions
- any run with `current_stage` indicating success while `correctness_passed=false`
- any publish path entered with non-empty `hard_failures`

### 10.3 Current execution delta

1. Implemented in this pass:
- correctness-aware routing updates in workflow helpers.
- correctness-aware publish blocking in git publishing node.
- new regression module for routing + publish gate semantics.

2. Next SOTA test additions:
- add Hypothesis state-invariant tests.
- add mutation-testing config and CI-only nightly target.
- add benchmark summary dashboard artifact from bounded runs (implemented: scripts/tools/compare_bounded_runs.py).
- command: d:/Projects/auto-git/.venv/Scripts/python.exe scripts/tools/compare_bounded_runs.py --log-dir logs --write-md logs/bounded_dashboard_latest.md

### 10.4 Baseline capture (2026-03-18 bounded run)

Source artifact: logs/complex_verification_bounded_20260318_233702.json

1. Aggregate metrics
- total_cases = 3
- ok_cases = 3 (runner-level execution)
- correctness_passed = 0/3
- mean hard_failures_count = 4.67
- mean soft_warnings_count = 0.33

2. Observed mismatch signal
- All three cases reached `stage=testing_complete` while `correctness_passed=false`.
- This confirms stage completion alone is not a valid success signal and supports correctness-first gating.

3. Immediate interpretation
- Routing and publish gates must continue to consume correctness/hard-failure truth fields.
- Benchmark reporting should keep runner health and correctness quality as two distinct KPIs.
