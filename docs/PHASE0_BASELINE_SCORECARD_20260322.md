# Phase 0 Baseline Scorecard (2026-03-22)

Purpose: Baseline reliability and correctness metrics before Phase 1 fail-closed routing changes.
Source run: output/e2e_complex_perplexica/complex_run_result_20260322_021714.json and logs/pipeline_trace_20260322_021716.jsonl

## Baseline Snapshot

- Run result file: output/e2e_complex_perplexica/complex_run_result_20260322_021714.json
- Trace file: logs/pipeline_trace_20260322_021716.jsonl
- Summary file: output/e2e_complex_perplexica/complex_run_summary_20260322_021714.txt

## Gate Metrics (Current Baseline)

- current_stage: saved_locally_tests_failed
- tests_passed: false
- correctness_passed: false
- final_status: needs_attention
- self_eval_score: 4.0
- hard_failures_count: 11
- execution_error_count: 11
- publish_eligible: false
- contradiction_detected: false
- verification_state: runtime_failed

## Loop Intensity (from trace/node frequency)

- code_testing: 13
- feature_verification: 13
- strategy_reasoner: 12
- code_fixing: 12
- smoke_test: 5
- pipeline_self_eval: 5

Interpretation: loop controls prevent crash but convergence remains weak in verification/fix path.

## Top Failure Signatures

1. GENERATED_TEST_FAILURE: 8/8 generated tests failed.
2. SMOKE_TEST NameError: mapper is not defined in worker.py standardize_icu_data path.
3. GOAL-EVAL partial requirement failures (incident simulation, retraining/rollback completeness, async/runtime reliability).

## Resource/Cost Snapshot

- total_tokens: 1,251,002
- model_calls: 158
- estimated_cost_usd: 0.22124573

Interpretation: high compute spend relative to failed correctness outcome.

## Confirmed Structural Gap Baseline

1. model_failover_profile appears normalized in workflow state but not consistently used in node-level model selection calls.
2. Undefined-symbol failures are still discovered late via runtime smoke/testing rather than blocked earlier by deterministic guards.

## Phase 0 Exit Conditions

This baseline is accepted for Phase 1 kickoff only after:
- Baseline artifact files are archived.
- Metrics above are referenced in PROGRESS entry.
- Phase 1 target checks are explicitly linked to these baseline values.
