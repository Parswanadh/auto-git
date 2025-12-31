#!/usr/bin/env python3
"""
Auto-GIT Simple Runner - Uses SequentialAgentOrchestrator directly
Solves: "integrating a text llm to understand images in 4 gb vram constraint"
"""

import asyncio
import sys
import time
sys.path.insert(0, "D:/Projects/auto-git")

from src.agents.sequential_orchestrator import create_orchestrator
from src.agents.tools.tool_registry import get_tool_registry
from src.utils.logger import get_logger

logger = get_logger("auto_git")


async def main():
    IDEA = "integrating a text llm to understand images in 4 gb vram constraint"

    print("=" * 70)
    print("AUTO-GIT: Single-Model Multi-Agent Research System")
    print("=" * 70)
    print(f"\nProblem: {IDEA}\n")

    # Create orchestrator
    print("Initializing agents (qwen3:4b, 6 personas)...")
    orchestrator = create_orchestrator()

    # Run tools first for research
    print("\n[Research Phase] Searching arXiv and GitHub...")
    registry = get_tool_registry()

    # Parallel tool search
    results = await registry.call_tools_parallel({
        "arxiv_search": {"query": "vision language model small vram", "max_results": 5},
        "github_search": {"query": "vision language model", "max_results": 3}
    })

    papers = results.get("arxiv_search").data if results.get("arxiv_search") else []
    repos = results.get("github_search").data if results.get("github_search") else []

    print(f"  Found {len(papers)} papers, {len(repos)} repos")

    # Build problem context
    problem = {
        "domain": "Computer Vision / NLP",
        "challenge": IDEA,
        "current_solutions": [p.get("title", "")[:80] for p in papers[:3]],
        "limitations": [
            "Large VLMs require 16GB+ VRAM",
            "Current models like LLaVA need too much memory",
            "Edge deployment impossible with existing solutions"
        ],
        "requirements": [
            "Must work in 4GB VRAM",
            "Text LLM + Image understanding",
            "Maintain reasonable quality"
        ],
        "tool_context": {
            "related_papers": [p.get("title", "") for p in papers[:3]],
            "github_repos": [r.get("name", "") for r in repos]
        }
    }

    # Run the pipeline
    print("\n[Debate Phase] Running 6-persona analysis pipeline...")
    start = time.time()

    result = await orchestrator.execute_pipeline(
        problem=problem,
        max_refinements=1
    )

    elapsed = time.time() - start

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nTime: {elapsed:.1f}s | Tokens: {result.total_tokens:,}")

    print(f"\nStages: {', '.join(result.stages_completed)}")

    print(f"\nConsensus Score: {result.consensus.weighted_score:.1f}/10")
    print(f"Confidence: {result.consensus.confidence:.1%}")
    print(f"Disagreement: {result.consensus.disagreement_level:.2f}")

    print("\n" + "-" * 70)
    print("FINAL SOLUTION")
    print("-" * 70)
    print(result.final_solution[:2000] + "..." if len(result.final_solution) > 2000 else result.final_solution)

    print("\n" + "-" * 70)
    print("CRITIQUE BREAKDOWN")
    print("-" * 70)
    for critique in result.consensus.all_critiques[:4]:
        print(f"\n[{critique.persona.upper()}]")
        print(f"  Score: {critique.score}/10")
        if critique.strengths:
            print(f"  Strengths: {', '.join(critique.strengths[:2])}")
        if critique.weaknesses:
            print(f"  Weaknesses: {', '.join(critique.weaknesses[:2])}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Auto-GIT analysis complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
