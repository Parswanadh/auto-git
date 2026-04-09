# Auto-GIT Canonical Context Recovery Brief

Date: 2026-04-01  
Scope: single source for rapid session recovery and operator alignment

## Purpose

This brief consolidates live runtime evidence, current code truth, and phase-locked governance so new sessions can recover context quickly without re-reading the full repository.

Companion execution plan: [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md#L1)  
Companion handoff log: [HANDOFF.md](HANDOFF.md#L1)

## Fast Recovery Flow

1. Start from this brief.
2. Validate latest run outcome from run_result and run_lineage artifacts.
3. Confirm routing and quality gate behavior in workflow code.
4. Execute only the next phase-locked items from the updated plan.

## Source-Of-Truth Priority

1. Latest runtime artifacts in logs and output.
2. Core orchestrator and node code.
3. Active phase plan and latest handoff deltas.
4. Secondary status docs.
5. Historical docs only for background.

## Current Verified Runtime Snapshot

As of latest verified artifacts in this workspace:

- Moderate E2E terminal state is saved_locally_tests_failed in [logs/run_result_e2e_moderate_1774978952_20260331_231232.json](logs/run_result_e2e_moderate_1774978952_20260331_231232.json#L4).
- Moderate E2E quality gate reason is correctness_gate_failed in [logs/run_result_e2e_moderate_1774978952_20260331_231232.json](logs/run_result_e2e_moderate_1774978952_20260331_231232.json#L18).
- Complex E2E terminal state is saved_locally_tests_failed in [logs/run_result_complex_perplexica_20260331_233931_20260331_233934.json](logs/run_result_complex_perplexica_20260331_233931_20260331_233934.json#L4).
- Complex E2E reports hard failures in [logs/run_result_complex_perplexica_20260331_233931_20260331_233934.json](logs/run_result_complex_perplexica_20260331_233931_20260331_233934.json#L11).
- Moderate trace shows expensive fix-loop churn in [logs/pipeline_trace_20260331_231232.jsonl](logs/pipeline_trace_20260331_231232.jsonl#L55).
- Complex status report shows code_fixing dominated wall time in [logs/agent_status_20260331_233934.md](logs/agent_status_20260331_233934.md#L26).

Interpretation:

- Pipeline reliability controls are active.
- Publish remains fail-closed on correctness failures.
- Primary unresolved frontier is convergence and correctness on moderate and complex workloads.

## Code-Level Truth Map

Core orchestrator and contract logic:

- Pipeline entry and run orchestration in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L3246).
- Quality contract application in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1621).
- Run artifact finalization and lineage fail-close in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L429).
- Self-eval routing in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L772).
- Goal-eval routing in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L907).
- Fix routing in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1077).
- Execution policy map in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L1185).
- Post-fix router in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L3011).
- Post-smoke router in [src/langraph_pipeline/workflow_enhanced.py](src/langraph_pipeline/workflow_enhanced.py#L3041).

Core node surfaces:

- Requirements extraction in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L2426).
- Problem extraction in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L3392).
- Code generation in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L4984).
- Code testing in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L7565).
- Feature verification in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L9309).
- Code fixing in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L9977).
- Git publishing in [src/langraph_pipeline/nodes.py](src/langraph_pipeline/nodes.py#L13314).

Model failover and cache stack:

- Client cache in [src/utils/model_manager.py](src/utils/model_manager.py#L656).
- Fallback runtime wrapper in [src/utils/model_manager.py](src/utils/model_manager.py#L1022).
- Public fallback accessor in [src/utils/model_manager.py](src/utils/model_manager.py#L1349).

State contract for phase lock telemetry:

- Phase fields in [src/langraph_pipeline/state.py](src/langraph_pipeline/state.py#L179).
- Default initialization in [src/langraph_pipeline/state.py](src/langraph_pipeline/state.py#L399).

## Governance And Plan Alignment

Active phase execution source is [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md#L6).

Critical findings table and phase mapping are in:

- [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md#L30)
- [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md#L71)
- [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md#L275)

Latest enforcement and deltas are in:

- [HANDOFF.md](HANDOFF.md#L7)
- [HANDOFF.md](HANDOFF.md#L74)
- [HANDOFF.md](HANDOFF.md#L132)

## Known Drift And Reliability Notes

- README architecture is historical and does not represent current 19-node control flow: [README.md](README.md#L21).
- BUG_TRACKER unresolved list may lag real code and must be re-verified before triage planning: [BUG_TRACKER.md](BUG_TRACKER.md#L138).
- Build status percentages are useful for broad direction but not a substitute for latest run artifacts: [BUILD_STATUS_TODO.md](BUILD_STATUS_TODO.md#L265).

## Synthetic Artifact Caution

Some thread-01 run999 artifacts are unit-test fixtures for fail-closed lineage behavior and not production E2E evidence:

- Fixture-style result in [logs/run_result_thread-01_run999.json](logs/run_result_thread-01_run999.json#L4).
- Corresponding unit test in [tests/unit/test_run_lineage_manifest.py](tests/unit/test_run_lineage_manifest.py#L192).

## Immediate Next Session Checklist

1. Execute only Phase 0 and Phase 1 remaining work from the updated plan.
2. Re-run deterministic gates and moderate gate with fresh artifacts.
3. Re-check convergence metrics from trace node_calls and quality gate reasons.
4. Update handoff and this brief after each completed gate.

## Canonical Artifact Pointers

- [logs/run_result_e2e_moderate_1774978952_20260331_231232.json](logs/run_result_e2e_moderate_1774978952_20260331_231232.json)
- [logs/run_lineage_e2e_moderate_1774978952.json](logs/run_lineage_e2e_moderate_1774978952.json)
- [logs/pipeline_trace_20260331_231232.jsonl](logs/pipeline_trace_20260331_231232.jsonl)
- [logs/run_result_complex_perplexica_20260331_233931_20260331_233934.json](logs/run_result_complex_perplexica_20260331_233931_20260331_233934.json)
- [logs/run_lineage_complex_perplexica_20260331_233931.json](logs/run_lineage_complex_perplexica_20260331_233931.json)
- [logs/agent_status_20260331_233934.md](logs/agent_status_20260331_233934.md)

