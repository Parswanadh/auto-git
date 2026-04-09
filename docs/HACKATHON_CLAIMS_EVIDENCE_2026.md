# Hackathon Claims Evidence Pack (2026)

This document defines claim-safe talking points for Auto-GIT with source-backed evidence.

## Claim Rules
- Only claim what is measured in this repo or directly sourced from public docs.
- Distinguish benchmark methodology claims from model-score ownership claims.
- For any numeric claim, include a source URL and date context.

## Evidence Sources
- SWE-bench official site: https://www.swebench.com/
- SWE-bench Verified overview: https://www.swebench.com/verified.html
- SWE-bench GitHub docs and harness details: https://github.com/SWE-bench/SWE-bench
- OpenAI SWE-bench Verified methodology write-up: https://openai.com/index/introducing-swe-bench-verified/
- LangGraph overview and production features: https://docs.langchain.com/oss/python/langgraph/overview
- Claude Code docs (agentic coding workflows and MCP integration): https://code.claude.com/docs
- Aider docs/repo (repo map, lint+test loop, git integration): https://github.com/Aider-AI/aider

## Defensible Claims (Use As-Is)
1. "Auto-GIT uses a multi-stage autonomous software loop: requirement extraction, research, debate, generation, validation, repair, and publish."
- Evidence: internal pipeline implementation in src/langraph_pipeline.

2. "Our evaluation strategy mirrors modern coding-agent benchmark principles: issue-fix verification plus regression protection."
- Evidence: SWE-bench FAIL_TO_PASS and PASS_TO_PASS framing in OpenAI/SWE-bench docs.

3. "We prioritize reproducible runtime validation with isolated environments and trace artifacts."
- Evidence: SWE-bench containerized harness emphasis, plus Auto-GIT logs and cached test environments.

4. "Auto-GIT is built on a stateful orchestration approach suitable for long-running agents."
- Evidence: LangGraph core benefits: durable execution, memory, and debugging instrumentation.

5. "We explicitly separate product failures from harness-generation failures to reduce false iteration churn."
- Evidence: feature verification fallback handling and taxonomy in the current pipeline code.

## Numeric Claims We Can Make Now
1. "Current pipeline has 19 orchestrated nodes."
- Source: project architecture docs and workflow implementation.

2. "SWE-bench Verified is a human-validated subset of 500 instances."
- Source: https://www.swebench.com/verified.html

3. "SWE-bench evaluations use pass/fail style test validation for fix correctness and regression checks."
- Source: https://openai.com/index/introducing-swe-bench-verified/

## Claims To Avoid Unless We Run Supporting Experiments
- "State-of-the-art on SWE-bench"
- "Best-in-class coding agent"
- "X% better than competitor Y"
- "Production-ready at enterprise scale" (unless reliability and security gates are demonstrated and documented)

## Fast Demo Script (Hackathon Pitch)
1. "We run an end-to-end autonomous coding pipeline, not a single prompt."
2. "Our loop includes runtime validation and iterative repair with failure memory."
3. "Our testing philosophy follows benchmark-grade principles: solve the target issue and prove no collateral regressions."
4. "Every run emits traceable artifacts and measurable quality metrics."

## Next Evidence Upgrades
1. Publish N=5 repeated moderate E2E runs with min/median/max reliability metrics.
2. Add a public benchmark-style report with FAIL_TO_PASS and PASS_TO_PASS summaries.
3. Add a reproducibility appendix: exact env, command lines, seed policy, and artifact paths.
