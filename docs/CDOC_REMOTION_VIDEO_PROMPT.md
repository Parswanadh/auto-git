# CDOC: Auto-GIT Improvement Blueprint + Exact Claude Code Prompt for Remotion

Date: 2026-03-17
Owner: Auto-GIT
Status: Ready to use

## 1) Critical Pipeline Improvement Blueprint

This is prioritized for maximum reduction in noisy errors and maximum improvement in true pass rate.

### A. Correctness Gates (highest ROI)
1. Split hard failures vs soft failures in testing.
- Hard fail only on: syntax invalid, import crash, main entry crash, true runtime exceptions.
- Soft fail (warning) for low-trust generated test failures if failures are only inside generated tests.
- Outcome: fewer false-negative pipeline failures.

2. Add error taxonomy with weighted severity.
- Category examples: DEPENDENCY, API_MISMATCH, CONTRACT_VIOLATION, TEST_FLAKE, INFRA_TIMEOUT, PROVIDER_RATE_LIMIT.
- Use weighted score to decide retry, deterministic fix, or LLM escalation.
- Outcome: targeted fixes instead of noisy generic loops.

3. Add deterministic first, LLM second policy everywhere.
- Keep deterministic fixers first for imports, requirements cleanup, shadow file deletion, known syntax transforms.
- Only send residual errors to LLM.
- Outcome: lower latency and less oscillation.

### B. Fix Loop Stability
4. Introduce anti-oscillation circuit per error fingerprint.
- If same fingerprint repeats 3+ times, require strategy switch (not same prompt family).
- Force action switch: patch -> regenerate file-level -> fallback template.
- Outcome: fewer infinite loops.

5. Add file-level rollback, not full rollback.
- If one file fix worsens syntax, rollback only that file and keep other good fixes.
- Outcome: preserves progress per iteration.

6. Add confidence-driven model routing.
- Simple dependency/syntax fixes use fast model.
- Multi-file architecture/API mismatch routes to powerful model once, not many fast retries.
- Outcome: cheaper and faster convergence.

### C. Dependency Reliability
7. Add dependency preflight before full install.
- Validate requirements lines, normalize specifiers, remove stdlib/internal modules, detect impossible pins.
- Outcome: fewer pip dead-ends.

8. Add build backend guardrail.
- Bootstrap packaging toolchain before install: pip, setuptools, wheel.
- Then attempt requirements install.
- Outcome: lower build backend failure rate.

9. Add two-tier install strategy.
- Tier 1: strict requirements install.
- Tier 2 fallback: install minimal inferred imports for runtime sanity when strict install fails.
- Outcome: more projects become executable for evaluation.

### D. Runtime and Evaluation Quality
10. Enforce executable acceptance contract.
- A run is "good" only if: stage complete AND tests_passed true AND no hard errors.
- Keep separate metric for stage completion vs correctness completion.
- Outcome: less misleading green states.

11. Add generated-test trust scoring.
- Parse provenance header and classify tests as low/medium/high trust.
- Low-trust tests contribute warning score; medium/high can fail pipeline.
- Outcome: better signal quality.

12. Add richer benchmark outputs.
- Persist per case: hard_errors, soft_errors, recovered_errors, unresolved_errors, root-cause family.
- Outcome: measurable improvement over time.

### E. Throughput and Cost
13. Parallelize independent validation steps.
- Syntax, type, lint, security checks in bounded parallel workers.
- Outcome: lower wall time.

14. Add adaptive timeout budgets.
- Increase timeout only for identified long-tail nodes, not globally.
- Outcome: fewer wasteful long waits.

15. Add provider health-aware routing.
- If 429 or timeout trend detected, switch provider family for next N calls.
- Outcome: lower transient provider failure impact.

### F. Recommended sequence for implementation
Phase 1: A1, A2, B4, B5
Phase 2: C7, C8, C9
Phase 3: D10, D11, D12
Phase 4: E13, E14, E15

## 2) Exact Prompt for Claude Code to Build a Remotion Video

Use this prompt exactly in Claude Code.

---

You are a senior Remotion engineer and technical storyteller. Build a production-quality video project that explains Auto-GIT: what it does, what was fixed, current reliability status, and next improvements.

Goal:
Create a complete Remotion video codebase that renders a polished 16:9 1080p video (30fps) with voiceover-ready captions and motion graphics. The video should feel premium and technical, not generic.

Primary audience:
AI engineers, infra engineers, and technical founders.

Output requirements:
1. Create a Remotion project in the current workspace folder.
2. Produce all source files needed to render final video.
3. Include a single command to render MP4.
4. Include a short README section with run steps.
5. Use deterministic structure and reusable scene components.

Video constraints:
- Duration target: 2m 30s to 3m 30s.
- Resolution: 1920x1080.
- FPS: 30.
- Visual style: modern technical documentary.
- Color direction: deep slate + cyan + amber accents, no purple bias.
- Typography: avoid default system look; choose strong readable web-safe pair.
- Motion: purposeful transitions, timeline bars, node-flow diagrams, metric counters.
- Accessibility: high contrast and clear text spacing.

Narrative structure (must implement all scenes):
Scene 1: Hook (8-12s)
- Problem: autonomous code generation often "looks done" but fails in runtime.
- Show mismatch between "stage complete" and "tests passed".

Scene 2: What Auto-GIT is (15-25s)
- Show 19-node pipeline from requirements extraction to git publishing.
- Explain research -> debate -> codegen -> testing -> fixing loop.

Scene 3: What was fixed recently (35-50s)
- AST compatibility fix for Python 3.14 (no ast.Str assumption).
- Execution policy wrapping across all nodes.
- Resource monitor integration.
- Dependency bootstrap hardening.

Scene 4: Verification evidence (25-40s)
- Show bounded complex suite outcomes.
- Contrast old run vs improved run (timeouts and completion deltas).
- Keep claims factual and conservative.

Scene 5: Why many errors still appear (30-45s)
- Explain error classes:
  - Historical/noise logs.
  - Soft warnings vs hard execution errors.
  - Generated low-trust test failures.
- Show how this inflates perceived failure volume.

Scene 6: Critical improvements roadmap (40-60s)
- Show prioritized roadmap:
  - Correctness gates.
  - Fix-loop anti-oscillation.
  - Dependency preflight and fallback.
  - Provider-health routing.
  - Better benchmark metrics.

Scene 7: Closing (10-20s)
- "From stage-complete to correctness-complete".
- Show concrete next-step checklist.

Data handling instructions:
- Use placeholder-safe structured data objects in code for metrics and milestones.
- Build scenes from data arrays, not hardcoded duplicated JSX.
- If real log parsing is uncertain, use clearly labeled "example metric" entries.
- Do not fabricate unverifiable numeric claims.

Technical implementation requirements:
- Use TypeScript.
- Use composition-based architecture:
  - src/Root.tsx
  - src/Video.tsx
  - src/scenes/*
  - src/components/*
  - src/data/storyData.ts
  - src/styles/theme.ts
- Build reusable components:
  - AnimatedTitle
  - PipelineDiagram
  - MetricCard
  - TimelineRow
  - SplitComparison
  - ChecklistPanel
- Build smooth transitions between scenes.
- Add subtle background motion (grid/parallax/glow) without clutter.

Audio and captions:
- Generate a narration script file in plain text.
- Generate subtitle cues as data (start/end/frame + text).
- Include a captions overlay component synced to frame ranges.
- Do not require external paid assets.

Engineering quality bar:
- Clean, modular code.
- No dead files.
- No repeated magic numbers; centralize constants.
- Add comments only where logic is non-obvious.

Acceptance checklist (must satisfy before finishing):
1. npm install succeeds.
2. Remotion preview runs.
3. MP4 render command is provided.
4. All scenes compile without TypeScript errors.
5. README includes exact commands:
   - install
   - preview
   - render

Now do the following in order:
1. Scaffold project and files.
2. Implement theme and shared components.
3. Implement all scenes and scene timing.
4. Implement subtitle data and overlay.
5. Wire full composition.
6. Provide final commands and a concise summary of what was created.

---

## 3) Optional Enhanced Prompt Mode (if you want more cinematic output)

Add this single line at the top of the prompt:
"Bias toward cinematic pacing, stronger visual metaphors, and fewer words per frame; maximize clarity through motion and composition over text density."

## 4) Quick Validation Script (manual)

After Claude Code generates the project, run:
1. npm install
2. npm run dev
3. npm run build (if available)
4. npx remotion render src/index.ts AutoGitReliability out/auto-git-reliability.mp4

If render fails, ask Claude Code:
"Fix all TypeScript and Remotion composition errors, keep scene timings unchanged, and re-validate render command."
