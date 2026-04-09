# SOTA Pipeline Reliability Blueprint

## Objective

Build an Auto-GIT pipeline that can:
- understand a problem statement or paper
- generate strong SOTA-style implementations
- minimize runtime and structural errors
- always test, validate, and evaluate outputs before publication

## Research Method

This blueprint combines:
- parallel best-practice investigations on LangGraph orchestration
- Python sandbox and validation optimization research
- prompt/context efficiency research
- direct inspection of the Auto-GIT codebase

## Best-Practice Findings

### 1. Resource-aware orchestration
Heavy nodes should not start blindly. They should check RAM/VRAM/CPU headroom, wait briefly under pressure, and degrade gracefully rather than crash.

### 2. Budgeted nodes
Long-running nodes need soft budgets for observability and hard timeouts for recovery. Timeouts must return safe fallback state, not hang the graph.

### 3. Prompt-efficiency without functional loss
Large codegen pipelines perform better when prompts are symbol-first, file-targeted, and repo-aware instead of repeatedly injecting broad cross-file dumps.

### 4. Deterministic gates before expensive review
Placeholder files, missing APIs, and obvious structural failures should be caught before expensive LLM review and runtime testing.

### 5. Cached infrastructure, fresh execution results
Reuse environments, model clients, and dependency caches. Do not reuse prior pass/fail outcomes across changed code.

### 6. Validation must remain layered
A high-quality pipeline should combine:
- syntax validation
- import/runtime validation
- type checking
- security scanning
- linting
- feature verification
- self-evaluation
- goal/requirement evaluation

## Implemented Improvements

### Orchestration and stability
- integrated resource-aware gating into heavy workflow nodes
- added soft-budget reporting and hard-timeout fallback behavior
- started/stopped live resource monitoring during pipeline runs
- added operational telemetry fields to state

### Code generation efficiency
- added a compact `repo_map` generated from architecture spec
- switched file prompts to targeted architecture context instead of only global architecture text
- reduced cross-file prompt bloat using symbol summaries for reference files
- added prompt budget tracking for planning, code generation, and fixing

### Testing and validation efficiency
- capped validator concurrency based on available RAM
- preserved cached test environments and cached dependency installs
- kept explicit verification states so static-only timeout never looks like a runtime pass

### Sandbox efficiency
- enabled persistent Docker pip cache keyed by image + requirements
- removed Docker `--no-cache-dir`
- fixed Docker timeout cleanup to target the actual container
- aligned memory-swap settings for predictable limits

### Quality protection
- preserved incomplete-artifact fail-fast checks
- preserved deterministic review skipping only when safe
- preserved separate strategy-hash and error-hash tracking

## Validation Performed

### Static validation
- no editor errors in modified workflow/state/resource-monitor/docker/codegen files

### Smoke validation
A lightweight import/build smoke test succeeded for:
- workflow graph construction
- state initialization with new telemetry fields
- resource monitor evaluation logic

## What This Improves Toward the Goal

These changes move the pipeline closer to:
- fewer crashes under local resource pressure
- lower prompt/token waste
- faster code generation and fixing cycles
- more consistent tested/evaluated outputs
- better observability when a run is slow or degraded

## Remaining Work to Reach the Strongest Reliability Target

### High priority
1. add project-level validation reuse across fix cycles
2. add targeted runtime test selection by changed files
3. add stronger final publish gate requiring non-placeholder, runtime-verified output
4. build paper/problem ingestion scoring so research quality is measured before codegen
5. add repo-map usage to review/eval prompts, not only codegen/fixing

### Medium priority
1. add wheelhouse/prebuilt dependency layers for repeated generated dependency sets
2. add public API diff detection to gate deep review even more safely
3. add requirement-to-test traceability in goal evaluation
4. add trusted vs generated test provenance scoring

## Practical Truth

The target is a pipeline that behaves like a high-reliability autonomous engineer.

Absolute "0 errors" cannot be honestly guaranteed for all unseen problem statements or papers, but the system can be pushed toward:
- deterministic prechecks
- strong runtime validation
- explicit failure states
- aggressive auto-fixing
- publish only after tested and evaluated success

That is the correct engineering path to near-zero error output while preserving functionality.
