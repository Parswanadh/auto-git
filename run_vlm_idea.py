#!/usr/bin/env python3
"""
Auto-GIT Runner - Single-Model Multi-Agent System
Solves: "integrating a text llm to understand images in 4 gb vram constraint"
"""

import asyncio
import sys
import time
from datetime import datetime

sys.path.insert(0, "D:/Projects/auto-git")

from src.langraph_pipeline.integrated_workflow import run_integrated_pipeline


async def main():
    IDEA = "integrating a text llm to understand images in 4 gb vram constraint"

    print("=" * 70)
    print("AUTO-GIT: Single-Model Multi-Agent System")
    print("=" * 70)
    print(f"\nProblem: {IDEA}\n")
    print("System Components:")
    print("  - 6 specialized personas (qwen3:4b)")
    print("  - HierarchicalMemory (learn from past)")
    print("  - ToolRegistry (arXiv + GitHub)")
    print("  - Weighted consensus (4 critique perspectives)")
    print("  - Sequential execution (8GB VRAM optimized)")
    print("\n" + "-" * 70)

    start_time = time.time()

    result = await run_integrated_pipeline(
        idea=IDEA,
        max_rounds=2,
        min_consensus=0.7,
        thread_id="vlm_problem"
    )

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nTime: {elapsed:.1f}s | Stage: {result.get('current_stage')}")

    if result.get("weighted_consensus"):
        wc = result["weighted_consensus"]
        print(f"\nConsensus: {wc.get('score', 0):.1f}/10 (confidence: {wc.get('confidence', 0):.0%})")

    if result.get("final_solution"):
        sol = result["final_solution"]
        print(f"\nSolution: {sol.get('approach_name', 'N/A')}")
        print(f"Innovation: {sol.get('key_innovation', 'N/A')[:100]}...")

    if result.get("generated_code"):
        print(f"\nCode: {result['generated_code'].get('total_files', 0)} files generated")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
