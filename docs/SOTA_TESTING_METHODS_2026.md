# SOTA Testing Methods (2026) for Auto-GIT

This note summarizes modern testing methods researched from public docs and maps them to Auto-GIT pipeline hardening.

## Sources
- Hypothesis/property-based testing: https://hypothesis.works/articles/what-is-property-based-testing/
- Hypothesis docs: https://hypothesis.readthedocs.io/en/latest/
- OSS-Fuzz/coverage-guided fuzzing: https://google.github.io/oss-fuzz/
- Pytest flaky-test guidance: https://docs.pytest.org/en/stable/explanation/flaky.html
- Pact contract testing: https://docs.pact.io/
- Chaos principles: https://principlesofchaos.org/
- Mutation testing overview: https://en.wikipedia.org/wiki/Mutation_testing
- Metamorphic testing overview: https://en.wikipedia.org/wiki/Metamorphic_testing

## Methods to Prioritize
1. Property-based tests
- Validate invariants over many generated inputs.
- Best for state transforms, scoring logic, parsers, and routing guards.

2. Metamorphic tests
- Validate relations between multiple executions when a perfect oracle is hard.
- Example: fingerprint should be invariant under key-order permutations.

3. Mutation-inspired tests
- Ensure tests fail when core behavior changes.
- Example: signature should change when semantic fields change.

4. Fault-injection/chaos tests
- Inject malformed or partial state to prove graceful degradation.
- Example: node output fields with wrong types should not crash loop guard.

5. Contract tests for interfaces
- Enforce producer/consumer schema for node result payloads.
- Example: requirements extraction failure envelope fields and types.

6. Flaky-resistance discipline
- Deterministic assertions, isolated state, no hidden ordering dependence.
- Use random-order/rerun tooling only for diagnosis, not as a permanent crutch.

7. Fuzzing (incremental adoption)
- Start with parser and serializer boundaries.
- Later: continuous fuzzing for high-risk components.

## Applied in This Session
- Added SOTA-inspired tests in tests/unit/test_sota_testing_methods.py:
  - Property/metamorphic checks for workflow fingerprint determinism.
  - Mutation-style checks for semantic-change sensitivity.
  - Fault-injection checks for malformed warnings/resource_events.

- Hardened loop detector normalization in src/langraph_pipeline/workflow_enhanced.py:
  - Coerces malformed list/dict fields to safe shapes before appending telemetry.

## Recommended Next Wave
1. Add contract tests for all node error envelopes (not just requirements extraction).
2. Add random-order CI lane for unit tests to detect hidden coupling.
3. Add optional Hypothesis-based suites for parser and state-merging utilities.
4. Add lightweight mutation-testing gate (target changed files only).
5. Add fuzz targets for traceback parser and error pattern matcher.

## Benchmark-Aligned Acceptance Criteria (SWE-bench Style)
Use this section to keep Auto-GIT evaluation aligned with current coding-agent
benchmark practices, while avoiding unsupported marketing claims.

1. Separate fix-validation from regression-validation
- Mirror FAIL_TO_PASS and PASS_TO_PASS style checks from SWE-bench methodology.
- For each generated patch candidate:
  - FAIL_TO_PASS lane: tests that prove the reported issue is fixed.
  - PASS_TO_PASS lane: tests that prove unrelated behavior did not regress.

2. Use reproducible, isolated environments
- Run evaluation in containerized or isolated environments (cached venv or Docker)
  with explicit dependency install logs.
- Preserve full run artifacts: test logs, trace, patch diff, environment metadata.

3. Track quality with verifiable metrics, not anecdotes
- Record per-run metrics:
  - Feature pass rate
  - Fix-loop iterations
  - Time-to-first-pass
  - Regression count after fix
- Publish only claims tied to logged artifacts.

4. Grade reliability by repeated trials
- For moderate tasks, run at least N=5 seeds before claiming stability.
- Report min/median/max rather than one best run.

5. Explicitly classify non-product failures
- Separate failures into:
  - Product correctness failures
  - Test-harness generation failures
  - Infra/environment failures
- Prevent harness-only failures from being misreported as product regressions.

## Auto-GIT Mapping
- FAIL_TO_PASS lane: feature verification and targeted runtime checks.
- PASS_TO_PASS lane: smoke test and execution error regression checks.
- Isolated runtime: cached test env and sandbox execution path.
- Traceability: pipeline trace JSONL + run log files in logs/.
- Failure taxonomy: strategy_reasoner categories + execution error memory.
