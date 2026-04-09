# Pipeline Readiness Matrix and Critical Workflow Analysis

Last updated: 2026-03-14

## Readiness Scale
- production-ready: reliable defaults, explicit failure semantics, and clear quality gates
- needs-hardening: core behavior is implemented but has failure-path or determinism gaps
- scaffold: architecture exists but protocol/runtime behavior is incomplete

## Subsystem Matrix

| Subsystem | Status | Strong Evidence | Key Gap | Immediate Hardening Action |
|---|---|---|---|---|
| Requirements extraction | needs-hardening | Structured decomposition JSON + complexity routing in early pipeline | Uses global complexity override path in addition to state | Remove global override reads/writes and rely strictly on state |
| Research | needs-hardening | Multi-source fallback chain is implemented | Can return research_complete despite weak/empty evidence | Add minimum evidence threshold before allowing downstream stage |
| Debate/consensus | needs-hardening | Multi-perspective generation + critique + consensus loop | no_debate_rounds can still route forward | Require minimum debate artifacts before selection |
| Architecture spec | needs-hardening | Dedicated architect node with spec payload for codegen | Failure/timeout can degrade to proceed-without-spec | Build deterministic fallback mini-spec instead of empty plan |
| Code generation | needs-hardening | Prompt guardrails, sanitization, and post-processing are substantial | Timeout and JSON robustness still uneven at call-sites | Enforce wait_for-style hard timeout wrapper at each critical LLM call |
| Testing/verification | needs-hardening | Code testing + feature verification + smoke testing exist | Feature verification can be skipped in some failure paths | Run reduced requirement probes even when core tests fail |
| Fix loop | needs-hardening | Strategy reasoner + deterministic and LLM fix flows are implemented | Large monolithic path complicates deterministic behavior | Split into smaller fix phases with direct unit tests |
| Self/goal evaluation | needs-hardening | Runtime-aware goal eval with requirement-level report | "approved" fallback can appear under evaluator failures | Add explicit unverified terminal stage and block publish from it |
| Publishing | needs-hardening | Safe local-save fallback exists and publish gates are present | No strict final release-gate object with all pass flags | Require one final release gate object before remote publish |
| MCP integration | scaffold | CLI manager starts servers and lists/calls tools | Transport protocol framing and full pipeline wiring not complete | Implement spec-correct framing lifecycle and node-level MCP usage |

## MCP Readiness Matrix

| MCP Area | Current State | Readiness | Blocking Item |
|---|---|---|---|
| Sequential thinking MCP | available and usable | production-ready for analysis support | none |
| CLI MCP manager | implemented with server lifecycle scaffolding | needs-hardening | full spec-compliant transport framing + retries |
| Pipeline-level MCP execution | partial/planned | scaffold | no direct node integration for deterministic pipeline operations |
| Security/quality MCPs (Semgrep/pip-audit plan) | planned in roadmap docs | scaffold | integration and policy enforcement not yet wired |
| Sandbox-oriented MCP strategy (E2B/Daytona plan) | documented in roadmap | scaffold | runtime integration and fallback policy not implemented |

## Critical Workflow Analysis

1. The workflow is strong in breadth (19-node lifecycle) but still relies on permissive fallback semantics in a few high-impact paths.
2. The highest-leverage stabilization is tightening fail-closed behavior at research sufficiency, architecture fallback quality, and eval approval semantics.
3. MCP capability exists at the CLI surface but is not yet a first-class execution primitive inside pipeline nodes.
4. The fix loop is feature-rich but large enough that regressions are difficult to localize quickly without more granular tests.
5. Release correctness should be controlled by one explicit final gate object, not inferred from dispersed stage fields.

## New Pipeline Todo System (Implemented)

The pipeline now generates and tracks a detailed TODO list from requirements at startup, then updates progress after each node using middleware.

Generated TODO categories:
- gate: requirements, research, architecture, codegen, publish
- quality_gate: runtime test, feature verification, smoke run, goal coverage
- component: each core component from requirements
- feature: each key feature from requirements
- test_scenario: each named test scenario
- user_requirement: each explicit user-provided requirement

Each TODO includes:
- title and detailed description
- priority
- acceptance criteria
- verification nodes
- status lifecycle (pending, in_progress, completed, blocked)
- evidence and updated stage

State keys added:
- pipeline_todos
- todo_progress
- todo_generation_notes

Runtime behavior:
- Todos are generated at requirements extraction.
- Every wrapped node updates todo status through workflow middleware.
- Goal-eval evidence maps requirement outcomes back to matching component/feature/user/test todos.
- todo_progress maintains completion percentage and remaining critical items.

## Recommended Next Hardening Steps

1. Add a final release gate object that explicitly requires tests_passed, smoke_test.passed, and verified goal-eval status.
2. Convert MCP CLI transport handling to spec-compliant framing and then expose deterministic MCP calls in selected pipeline nodes.
3. Add targeted unit tests for todo lifecycle updates across stage transitions (requirements, codegen, testing, feature verification, goal eval, publishing).
4. Add evidence-threshold routing to prevent weak research context from being marked complete.
