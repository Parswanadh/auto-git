# SOTA Showcase Benchmark Program 31-03 (Execution Ready)

Date: 2026-03-31  
Owner: Auto-GIT Core Pipeline Team  
Status: Ready for rollout  
Primary execution anchor: [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md)  
Baseline reference: [docs/PERFECT_PLAN_22_03.md](docs/PERFECT_PLAN_22_03.md)

## 1. Objective

Run a benchmark program that can be shown publicly without trust gaps:
- reproducible
- statistically meaningful
- resistant to cherry-picked runs
- aligned with modern coding-agent benchmarks
- mapped to security/compliance expectations

This document converts research into an actionable benchmark system for Auto-GIT.

## 2. Benchmark Stack (Four Levels)

## Level A: Internal Deterministic Reliability Gate

Purpose:
- verify routing correctness, state contracts, and no-regression invariants

Primary assets:
- [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md#L285)
- [tests/unit/test_correctness_routing.py](tests/unit/test_correctness_routing.py)
- [tests/unit/test_workflow_loop_guard.py](tests/unit/test_workflow_loop_guard.py)
- [tests/unit/test_sota_testing_methods.py](tests/unit/test_sota_testing_methods.py)

Required pass condition:
- 100 percent pass on required deterministic suites
- zero contradiction success artifacts
- zero missing run-lineage manifests

## Level B: Internal E2E Reliability and Convergence

Purpose:
- measure real pipeline convergence on moderate and complex tasks

Primary assets:
- [run_e2e_moderate.py](run_e2e_moderate.py)
- [scripts/run_complex_verification_bounded.py](scripts/run_complex_verification_bounded.py)
- [scripts/run_complex_verification_suite.py](scripts/run_complex_verification_suite.py)

Required pass condition:
- moderate lane success rate at or above 80 percent over repeated runs
- bounded complex lane correctness trend improving week over week
- no stale artifacts used for promotion

## Level C: External Coding Benchmark Alignment

Purpose:
- anchor claims against public benchmark ecosystems

Target benchmark families:
1. SWE-bench Verified (issue-resolution benchmark with human-filtered subset and dockerized harness)
2. LiveCodeBench (contamination-aware rolling contest benchmark)
3. EvalPlus HumanEval+/MBPP+ (stronger test coverage than original HumanEval/MBPP)

Required pass condition:
- publish external scores with run metadata, harness version, and exact date window
- never compare across incompatible benchmark variants without explicit disclaimer

## Level D: Security and Compliance Benchmarking

Purpose:
- prove generated outputs are not only correct but also safer by default

Security benchmark components:
1. dependency vulnerability scanning for Python environments
2. static application security checks where applicable
3. dynamic web scanning for generated web projects
4. requirement mapping to ASVS and SSDF controls

Reference standards and tools:
- OWASP ASVS v5.0.0
- NIST SSDF SP 800-218
- pip-audit
- OWASP ZAP

Required pass condition:
- security gate pass rate at or above 95 percent on benchmarked projects
- all critical vulnerabilities blocked from promotion

## 3. Metric System (Scorecard Contract)

Each benchmark run must emit these metrics.

Core reliability metrics:
1. task_success_rate = successful_runs / total_runs
2. contradiction_rate = runs_with_contradiction_true / total_runs
3. lineage_integrity_rate = runs_with_valid_lineage / total_runs
4. timeout_fidelity_rate = classified_timeout_events / timeout_events
5. deterministic_pass_rate = passed_required_tests / total_required_tests

Convergence and performance metrics:
1. median_time_to_first_pass_seconds
2. median_fix_iterations_until_pass
3. fix_loop_overrun_rate = runs_exceeding_fix_budget / total_runs
4. median_total_tokens_per_run
5. median_estimated_cost_usd_per_successful_run

Quality metrics:
1. feature_pass_rate
2. regression_rate = regressions_detected / total_success_claims
3. publish_precision = truly_publishable_runs / publish_attempted_runs

Security metrics:
1. dependency_vuln_count_by_severity
2. security_gate_pass_rate
3. critical_vuln_block_rate

## 4. Promotion Thresholds (Bronze/Silver/Gold)

Use these as public showcase tiers.

Bronze:
- task_success_rate >= 0.70
- contradiction_rate = 0.00
- lineage_integrity_rate >= 0.95
- deterministic_pass_rate = 1.00
- security_gate_pass_rate >= 0.90

Silver:
- task_success_rate >= 0.80
- contradiction_rate = 0.00
- lineage_integrity_rate = 1.00
- timeout_fidelity_rate >= 0.95
- security_gate_pass_rate >= 0.95

Gold:
- task_success_rate >= 0.88
- contradiction_rate = 0.00
- lineage_integrity_rate = 1.00
- timeout_fidelity_rate = 1.00
- security_gate_pass_rate >= 0.98

Non-negotiable blocker:
- any contradiction_detected true blocks promotion regardless of average score.

## 5. Statistical Rigor Rules

Minimum run counts:
1. deterministic lane: every commit affecting routing or terminal logic
2. moderate lane: at least 10 runs per checkpoint
3. complex bounded lane: at least 5 runs per checkpoint

Reporting rules:
1. report median, p25, p75 for latency/cost metrics
2. report point estimate plus 95 percent confidence interval for success rate
3. include failure taxonomy split:
- product correctness failure
- test harness generation failure
- infrastructure failure

Anti-gaming rules:
1. no best-of-N single-run claims
2. no stale artifact evidence older than 72 hours for promotion
3. no mixing benchmark versions in one headline metric without explicit split

## 6. Execution Plan (14 Days)

Days 1-2:
1. enforce Level A and Level B artifact discipline from [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md)
2. run deterministic suites plus moderate baseline pack
3. publish baseline scorecard snapshot

Days 3-5:
1. run complex bounded pack and close timeout/lineage gaps
2. produce first trend view for convergence and cost
3. verify promotion blockers trigger correctly

Days 6-9:
1. run external benchmark pilot for SWE-bench Verified subset and one contamination-aware LiveCodeBench slice
2. archive benchmark config, run ids, harness versions, and environment metadata

Days 10-12:
1. run security benchmark pack on generated web/api outputs
2. map detected findings to ASVS and SSDF categories
3. update release blocker rules from findings

Days 13-14:
1. generate showcase report with Bronze/Silver/Gold placement
2. include confidence intervals, caveats, and reproducibility appendix
3. publish only if all blockers clear

## 7. Canonical Command Set

Local deterministic gate:
- D:\Projects\auto-git\.venv\Scripts\python.exe -m pytest tests/unit/test_pipeline_todo_tracking.py tests/unit/test_state_contracts.py tests/unit/test_mcp_server_manager.py -q
- D:\Projects\auto-git\.venv\Scripts\python.exe -m pytest tests/unit/test_integration_plan_controls.py tests/unit/test_nodes_zero_cost.py tests/unit/test_phase_d_ops_tools.py tests/unit/test_model_manager_large_prompt_controls.py -q

Moderate gate:
- D:\Projects\auto-git\.venv\Scripts\python.exe run_e2e_moderate.py

Complex bounded gate:
- D:\Projects\auto-git\.venv\Scripts\python.exe scripts/run_complex_verification_bounded.py

Complex suite gate:
- D:\Projects\auto-git\.venv\Scripts\python.exe scripts/run_complex_verification_suite.py

Dependency security gate:
- D:\Projects\auto-git\.venv\Scripts\python.exe -m pip_audit -r requirements.txt

Note:
- if VS Code task shell resolution fails, use direct interpreter commands and record that fallback in run artifacts.

## 8. Artifact Package Required for Any Public Claim

Each published benchmark checkpoint must include:
1. run manifest and lineage references
2. benchmark configuration and command lines
3. raw logs and summarized scorecard
4. benchmark version and date window
5. confidence intervals and sample sizes
6. failure taxonomy table

Recommended storage anchors:
- [logs](logs)
- [output](output)
- [docs/PHASE0_BASELINE_SCORECARD_20260322.md](docs/PHASE0_BASELINE_SCORECARD_20260322.md)

## 9. How This Integrates with Current Plan

This benchmark program is an execution layer on top of [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md):
1. Phase 0-1 corrections remove invalid success signals
2. Phase 2-3 fixes stabilize timing/failover behavior
3. this document defines how to measure and present those improvements credibly

In short:
- [docs/PERFECT_UPDATED_PLAN_31_03.md](docs/PERFECT_UPDATED_PLAN_31_03.md) answers what to fix.
- this document answers how to prove and showcase results.

## 10. External References (Research Anchors)

Benchmark references:
- SWE-bench Verified: https://www.swebench.com/verified.html
- SWE-bench evaluation guide: https://www.swebench.com/SWE-bench/guides/evaluation/
- LiveCodeBench: https://livecodebench.github.io/
- LiveCodeBench paper: https://arxiv.org/abs/2403.07974
- EvalPlus: https://evalplus.github.io/
- HumanEval paper: https://arxiv.org/abs/2107.03374
- MBPP paper: https://arxiv.org/abs/2108.07732

Security/compliance references:
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- NIST SSDF SP 800-218: https://csrc.nist.gov/pubs/sp/800/218/final
- pip-audit: https://github.com/pypa/pip-audit
- OWASP ZAP: https://www.zaproxy.org/
