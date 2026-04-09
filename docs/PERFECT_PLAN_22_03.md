# Perfect Integration Plan 22-03 (Production + SOTA Testing)

Date: 2026-03-22
Owner: Auto-GIT Core Pipeline Team
Status: Approved for execution

## 1. Mission

Build a fail-closed, production-grade Auto-GIT pipeline that:
- Stops false-green outcomes.
- Converges faster under real provider instability.
- Preserves correctness under long fix loops.
- Proves quality after each phase using SOTA testing gates.

## 2. Critical Review (Current State)

## 2.1 What is strong right now
- Workflow-level reliability scaffolding is substantial (loop guards, parity checks, policy normalization, context offload, checkpointer abstraction).
- Unit coverage for integration controls already exists and is useful.
- Replay and doctor operations tooling is present and operational.

## 2.2 What is still blocking production trust
- Runtime correctness can still fail late (smoke/test failures after extensive pipeline work).
- Completion semantics are not strict enough in edge scenarios; progress can look good while the artifact is still broken.
- Failover profile is mostly plumbed but not fully enforced across live node-level model selection paths.
- Fix loops still spend expensive retries on repeated signature patterns.

## 2.3 Root cause theme
The architecture is mostly there. Enforcement at decision boundaries is the remaining gap.

## 3. Program Principles

1. Fail closed, never optimistic-close.
2. Deterministic checks before expensive retries.
3. Strict separation of deterministic failures vs provider-variability failures.
4. Every phase ends with a SOTA test gate.
5. No phase rollover without explicit pass criteria.

## 4. Inspiration Map (What We Borrow and Why)

This plan is intentionally not "generic best practice." Every major control is inspired by observed patterns in top agent systems and adapted to Auto-GIT.

1. Claude Code (Anthropic)
- Why borrowed: strongest policy/hook mindset for fail-closed behavior.
- Borrowed patterns: lifecycle gating, approval/safety boundaries, completion discipline.

2. LangGraph Deep Agents
- Why borrowed: best-practice stateful orchestration for planner-executor-evaluator loops.
- Borrowed patterns: middleware guard bands, checklist/state discipline, bounded refinement loops.

3. DeerFlow
- Why borrowed: practical middleware patterns for loop/fan-out/tool error normalization.
- Borrowed patterns: loop detection, subagent limits, structured exception handling.

4. OpenClaw
- Why borrowed: operations-first trust/allowlist and diagnostics model.
- Borrowed patterns: trust modes, least-privilege posture, doctor/runbook style ops checks.

5. SWE-Agent
- Why borrowed: trajectory rigor and reproducible benchmark discipline.
- Borrowed patterns: artifacted run traces, explicit evaluation/replay workflows.

6. Aider
- Why borrowed: practical coding-loop reliability and rollback ergonomics.
- Borrowed patterns: diff-first edits, frequent deterministic checks, rapid undo safety.

## 5. Phase Plan (Step-by-Step, Why, and Inspiration)

## Phase 0 - Baseline Freeze and Contract (2 days)
Goal: lock baseline metrics and formal pass/fail contract.

Why this phase exists:
- Without a baseline contract, every later result is subjective and hard to compare.
- This prevents moving goalposts and creates a production-grade decision policy.

Inspired by:
- SWE-Agent trajectory/evaluation rigor.
- OpenClaw doctor/runbook operational discipline.

Steps:
1. Freeze baseline run artifacts and metrics in logs/output.
   - Why: creates a stable reference point for regression detection.
   - Inspired by: SWE-Agent run artifact discipline.
2. Define release gate contract:
   - tests_passed == true
   - smoke_test.passed == true
   - hard_failures_count == 0
   - correctness_passed == true
   - Why: enforces truth-over-appearance; no "looks done" acceptance.
   - Inspired by: Claude Code completion discipline, Deep Agents evaluator gate pattern.
3. Add stop-the-line rules for contradiction states.
   - Why: contradiction states are high-risk false greens and must fail immediately.
   - Inspired by: fail-closed policy patterns in Claude-style safety controls.
4. Publish baseline scorecard template.
   - Why: standard reporting accelerates reviews and reduces interpretation drift.
   - Inspired by: OpenClaw operational reporting style.

Deliverables:
- Baseline scorecard table.
- Gate contract section in docs.

## Phase 1 - Fail-Closed Correctness Gates (4 days)
Goal: prevent false terminal success.

Why this phase exists:
- Current pipeline can still appear successful before runtime truth is fully proven.
- This phase converts terminal routing into strict correctness enforcement.

Inspired by:
- Claude Code: completion must satisfy checks before done.
- Deep Agents: evaluator-optimizer loop with hard stop criteria.

Steps:
1. Tighten workflow terminal routing and publish gating.
   - Why: terminal routing is the last line of defense against incorrect outputs.
   - Inspired by: Claude-style completion gating.
2. Enforce no-success if hard failures or smoke/test failures exist.
   - Why: removes optimistic-success ambiguity.
   - Inspired by: safety-first fail-closed policy design.
3. Add explicit warning/error reason propagation at terminal decision points.
   - Why: improves diagnosability and shortens MTTR.
   - Inspired by: OpenClaw doctor-style operational transparency.
4. Add route-level invariants in unit tests.
   - Why: route regressions are subtle and must be caught deterministically.
   - Inspired by: SWE-Agent benchmark discipline + Deep Agents state invariants.

Deliverables:
- Updated terminal routing behavior.
- Regression tests for contradiction blocking.

## Phase 2 - Deterministic Repair and Anti-Thrash (5 days)
Goal: reduce repeated blind retries.

Why this phase exists:
- Blind retries inflate cost and latency while repeating identical failure signatures.
- Deterministic first-response policies reduce entropy and improve convergence.

Inspired by:
- DeerFlow loop detection middleware.
- Aider-style deterministic check/fix cadence.
- SWE-Agent trajectory-based failure analysis.

Steps:
1. Add failure bucketing taxonomy:
   - undefined_symbol
   - import_mismatch
   - type_call_mismatch
   - dependency_runtime
   - provider_timeout
   - provider_rate_limit
   - Why: explicit classes enable targeted, reliable remediation.
   - Inspired by: structured error normalization patterns from DeerFlow/OpenClaw.
2. Bind deterministic first-action policy per bucket.
   - Why: prevents random strategy switching and fixes easier root causes first.
   - Inspired by: Aider practical coding-loop discipline.
3. Add repeated-signature streak breaker:
   - auto rollback to last stable checkpoint
   - force strategy switch
   - Why: repeated signatures prove current strategy is non-productive.
   - Inspired by: loop-guard and rollback patterns across DeerFlow + Aider.
4. Log bucket decisions into telemetry artifacts.
   - Why: enables explainability and later policy tuning.
   - Inspired by: SWE-Agent trajectory logging and ops observability practices.

Deliverables:
- Failure bucket router.
- Anti-thrashing rollback/strategy switch logic.
- Per-attempt bucket telemetry.

## Phase 3 - End-to-End Failover Profile Enforcement (4 days)
Goal: make failover profiles actively control node-level LLM pathing.

Why this phase exists:
- Profile normalization without runtime enforcement causes policy illusions.
- Provider instability needs deterministic profile behavior under pressure.

Inspired by:
- OpenClaw trust/policy posture.
- Deep Agents middleware enforcement.
- Existing model-router profile logic adapted to live node calls.

Steps:
1. Thread model_failover_profile into all node model acquisition points.
   - Why: policy must reach the execution path, not just config parsing.
   - Inspired by: policy propagation principles in production orchestration.
2. Enforce profile chain at runtime, not only normalization.
   - Why: closes control-plane vs data-plane mismatch.
   - Inspired by: OpenClaw-like policy enforcement boundaries.
3. Respect provider-family cooldown/suppression in same-call retries.
   - Why: avoids repeated stalls on degraded families.
   - Inspired by: resilient fallback chain design.
4. Add profile behavior trace markers.
   - Why: without trace markers, enforcement cannot be audited.
   - Inspired by: SWE-Agent/OpenClaw observability standards.

Deliverables:
- Runtime profile enforcement in active nodes.
- Profile-based routing telemetry.

## Phase 4 - Checklist State + Replanner + Tool Scoping (6 days)
Goal: convert requirement completion into machine-checkable evidence.

Why this phase exists:
- Requirement text alone is insufficient; proof-bearing state is needed.
- Replanner logic is required when confidence drops or repeated failure occurs.

Inspired by:
- Deep Agents checklist-as-state and middleware orchestration.
- Claude context engineering patterns for scoped tool use.

Steps:
1. Add checklist state object with required evidence pointers.
   - Why: final acceptance must be evidence-backed, not narrative-backed.
   - Inspired by: Deep Agents state discipline.
2. Add replanner triggers on confidence drop and repeated failures.
   - Why: bounded replanning prevents endless ineffective local loops.
   - Inspired by: planner-executor-evaluator loop patterns.
3. Apply dynamic tool allowlists per stage intent.
   - Why: reduced tool surface lowers wrong-tool and noisy-action risks.
   - Inspired by: Claude/OpenClaw least-privilege policy model.
4. Ensure requirement-to-verification traceability for final gate.
   - Why: every requirement should map to explicit verification evidence.
   - Inspired by: SWE-bench style verification rigor.

Deliverables:
- Checklist/evidence model in state.
- Replanner join logic.
- Stage-level tool scoping policy.

## Phase 5 - Trajectory Evidence + Release Governance (5 days)
Goal: production repeatability and fast postmortems.

Why this phase exists:
- Fixing once is not enough; we need repeatable diagnosis and governance.
- Production releases require historical evidence and trend-aware confidence.

Inspired by:
- SWE-Agent trajectory artifacts.
- OpenClaw doctor/runbook model.
- Aider practical iteration traceability.

Steps:
1. Persist per-attempt trajectory bundles:
   - decisions
   - patch summary
   - tests
   - failure signature
   - rollback action
   - Why: captures decision provenance for replay and regression analysis.
   - Inspired by: SWE-Agent trajectory design.
2. Enrich replay/doctor with recommended remediation actions.
   - Why: operators need direct, actionable next steps.
   - Inspired by: OpenClaw diagnostics ergonomics.
3. Add release scorecard generation and trend tracking.
   - Why: release confidence should be trend-based, not anecdotal.
   - Inspired by: benchmark leaderboard and operational SLO thinking.
4. Lock release gate to evidence-backed checks only.
   - Why: prevents subjective override in high-pressure release moments.
   - Inspired by: fail-closed governance discipline.

Deliverables:
- Attempt trajectory artifacts.
- Enhanced doctor/replay reports.
- Release governance scorecard.

## 6. Detailed Checklist

## 6.1 Engineering checklist
- [ ] Baseline contract published.
- [ ] Contradiction-state blocker implemented.
- [ ] Deterministic failure taxonomy implemented.
- [ ] Bucket-to-policy remediator wired.
- [ ] Signature streak rollback implemented.
- [ ] Runtime failover profile fully enforced.
- [ ] Profile telemetry markers added.
- [ ] Checklist evidence schema added to state.
- [ ] Replanner threshold policy implemented.
- [ ] Stage-level tool scoping enforced.
- [ ] Trajectory artifacts persisted per attempt.
- [ ] Release scorecard auto-generated.

## 6.2 Test engineering checklist
- [ ] Unit routing invariants updated.
- [ ] Failure taxonomy unit tests added.
- [ ] Profile-routing tests added.
- [ ] Checklist-state invariants added.
- [ ] Replanner trigger tests added.
- [ ] Replay/doctor output tests expanded.
- [ ] Metamorphic docs-only fingerprint tests retained.
- [ ] Complex-run assertion parser added for gate enforcement.

## 6.3 Operations checklist
- [ ] SOTA gate report stored for each phase.
- [ ] Rollback protocol documented.
- [ ] On-call runbook updated.
- [ ] CI phase-gate workflow updated.

## 7. SOTA Testing Protocol (Required After Each Phase)

Why this protocol is mandatory:
- SOTA quality requires layered validation, not single-test confidence.
- Deterministic + moderate + complex testing catches different failure classes.

Inspired by:
- SWE-bench and SWE-Agent evaluation rigor.
- Deep Agents multi-layer validation philosophy.

## 7.1 Deterministic unit gate
Run:
- python -m pytest tests/unit/test_pipeline_todo_tracking.py tests/unit/test_state_contracts.py tests/unit/test_mcp_server_manager.py -q
- python -m pytest tests/unit/test_integration_plan_controls.py tests/unit/test_nodes_zero_cost.py tests/unit/test_phase_d_ops_tools.py tests/unit/test_model_manager_large_prompt_controls.py -q

Pass criteria:
- 100% pass.
- No new flaky failures allowed.

## 7.2 Moderate E2E gate
Run:
- python run_e2e_moderate.py

Pass criteria:
- Pipeline reaches expected terminal stage with no contradiction state.

## 7.3 Complex E2E gate (single long case)
Run:
- python tests/e2e/run_e2e_complex_perplexica_once.py

Pass criteria:
- No hard crash.
- No false-success terminal state.
- Failure (if any) must be classified into defined taxonomy.

## 7.4 Complex bounded pack gate
Run:
- python scripts/run_complex_verification_bounded.py

Pass criteria:
- No exceptions.
- Timeout count non-regressive versus prior phase baseline.
- Correctness indicators non-regressive.

## 7.5 Phase promotion policy
A phase is promoted only if all four gates pass and gate artifacts are archived.

## 8. Timeline (Production Program)

Why this timeline shape:
- Early phases focus on correctness enforcement because that has highest ROI.
- Mid phases enforce runtime resilience and policy fidelity.
- Final phases prioritize governance, reproducibility, and release safety.

Inspired by:
- Incremental hardening programs used in production agent systems.

Week 1:
- Phase 0 complete.
- Phase 1 complete.

Week 2:
- Phase 2 complete.

Week 3:
- Phase 3 complete.

Week 4:
- Phase 4 complete.

Week 5:
- Phase 5 complete.

Week 6 (buffer and hardening):
- Regression-only hardening.
- Documentation freeze.
- Release candidate certification.

## 9. KPI Targets

Why these KPIs:
- They directly track trust failures (false-green, unsafe publish) and convergence efficiency.
- They separate reliability outcomes from model/provider variability noise.

Primary KPIs:
- False-green rate: 0%.
- Publish-with-hard-failure rate: 0%.
- Median fix attempts: reduce by >= 25% from baseline.
- Repeated-signature streak incidents: reduce by >= 50% from baseline.
- Complex-run timeout rate: non-regressive first, then reduce >= 20%.

Secondary KPIs:
- Mean time to diagnose failed run.
- Replay success rate from checkpoints.
- Variance in run duration under same input class.

## 10. Risk Register and Mitigations

1. Over-gating slows feature velocity.
- Mitigation: keep strict gating on phase exits and release branches; allow dev-fast mode locally.

2. Provider instability masks real code regressions.
- Mitigation: split deterministic gate failures from provider-surface failures in reports.

3. Scope creep across phases.
- Mitigation: no cross-phase additions before phase gate close.

4. Test flakiness in long complex runs.
- Mitigation: bounded rerun policy, stable seed/config, strict artifact logging.

## 11. Definition of Done

Production readiness is achieved only when:
- All 6 phases are closed with SOTA gate evidence.
- KPI targets are met for two consecutive weekly cycles.
- Release candidate passes full deterministic + moderate + complex test program with no contradiction states.

## 12. Immediate Next 72 Hours

1. Implement Phase 0 contract and baseline scorecard.
2. Implement Phase 1 fail-closed terminal gating.
3. Run full SOTA test protocol and archive artifacts.
4. Open Phase 2 branch only after documented gate pass.
