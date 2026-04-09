# Pipeline Correctness Execution Checklist

Date: 2026-03-18
Purpose: Implement and verify the reliability plan with direct file-level mapping.

## Success Criteria

A run is successful only when all are true:
- `correctness_passed == true`
- `tests_passed == true`
- `hard_failures_count == 0`

Secondary metrics:
- `soft_warnings_count` tracked separately (non-blocking)
- `stage` used for orchestration tracking only

## Phase 1: Correctness Contract + Telemetry Truth

### 1.1 Add canonical correctness fields to pipeline state
- File: `src/langraph_pipeline/state.py`
- Done when:
  - `AutoGITState` defines: `correctness_passed`, `hard_failures`, `soft_warnings`
  - `create_initial_state()` initializes these fields

### 1.2 Derive correctness truth snapshot at workflow merge points
- File: `src/langraph_pipeline/workflow_enhanced.py`
- Done when:
  - helper computes hard failures from `test_results.execution_errors`
  - helper computes soft warnings from `test_results.warnings` + state warnings
  - helper computes `correctness_passed = tests_passed and hard_failures == 0`
  - per-node merged state always includes these fields

### 1.3 Surface hard/soft correctness in verification harness
- Files:
  - `scripts/run_complex_verification_suite.py`
  - `scripts/run_complex_verification_bounded.py`
- Done when:
  - output JSON includes: `correctness_passed`, `hard_failures_count`, `soft_warnings_count`
  - CLI output prints correctness + hard/soft counts

## Phase 2: Fix-Loop Stability

### 2.1 Fingerprint loop breaker
- File: `src/langraph_pipeline/nodes.py` (inside `code_fixing_node`)
- Tasks:
  - detect repeated error fingerprints >= 3 attempts
  - force strategy switch (not same prompt family)
  - record forced switch reason in warnings
- Done when:
  - recurring fingerprints drop in bounded runs

### 2.2 File-level rollback only
- File: `src/langraph_pipeline/nodes.py`
- Tasks:
  - rollback only files whose patch increased syntax/runtime failures
  - preserve unrelated good fixes in same iteration
- Done when:
  - fewer regressions per fix attempt

## Phase 3: Dependency Reliability

### 3.1 Strict dependency preflight
- Files:
  - `src/langraph_pipeline/nodes.py`
  - `src/utils/code_executor.py`
- Tasks:
  - sanitize requirements
  - strip stdlib/internal entries
  - normalize invalid specifiers
- Done when:
  - install fatal rate decreases

### 3.2 Two-tier install strategy
- File: `src/utils/code_executor.py`
- Tasks:
  - Tier 1 strict install from requirements
  - Tier 2 minimal inferred runtime dependencies fallback
- Done when:
  - more cases reach runtime execution

## Phase 4: Provider Resilience

### 4.1 Health-aware model routing
- File: `src/utils/model_manager.py`
- Tasks:
  - provider health score and cooldown
  - route by task class and current provider health
- Done when:
  - lower timeout/429 cascade impact

### 4.2 Budget-aware node tuning
- File: `src/langraph_pipeline/workflow_enhanced.py`
- Tasks:
  - adaptive soft/hard budget by historical node runtime
- Done when:
  - reduced false budget breaches without runtime blowups

## Verification Protocol

Run after each phase:
1. `d:/Projects/auto-git/.venv/Scripts/python.exe -m py_compile src/langraph_pipeline/state.py src/langraph_pipeline/workflow_enhanced.py scripts/run_complex_verification_suite.py scripts/run_complex_verification_bounded.py`
2. `d:/Projects/auto-git/.venv/Scripts/python.exe scripts/run_complex_verification_bounded.py`
3. Inspect latest summary JSON under `logs/` and record:
   - `correctness_passed`
   - `hard_failures_count`
   - `soft_warnings_count`
   - `tests_passed`

## Reporting Template (per run)

- Run ID:
- Cases:
- Stage-complete rate:
- Correctness-pass rate:
- Mean hard failures per case:
- Mean soft warnings per case:
- Top recurring fingerprint:
- Top dependency failure class:
- Next patch target:
