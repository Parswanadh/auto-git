"""Quick pipeline test runner — non-interactive, research-heavy idea."""
import asyncio
import sys
import os
import time

# Ensure src is importable
sys.path.insert(0, os.path.dirname(__file__))


async def main():
    from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline
    from src.utils.model_manager import print_token_summary, get_model_health_report

    idea = (
        "Build a Graph-based Retrieval Augmented Generation (GraphRAG) engine that "
        "constructs a knowledge graph from unstructured documents using entity extraction "
        "and relation linking, then uses graph neural network embeddings for hybrid "
        "retrieval (combining BM25 sparse search with GNN-based dense search). "
        "The system should support incremental graph updates, community detection for "
        "automatic topic clustering, and multi-hop reasoning over the knowledge graph "
        "to answer complex questions that require synthesizing information across "
        "multiple documents."
    )

    print(f"\n{'='*80}")
    print(f"  AUTO-GIT PIPELINE TEST — Complex Research-Heavy Idea")
    print(f"{'='*80}")
    print(f"\nIdea: {idea[:120]}...")
    print(f"Started: {time.strftime('%H:%M:%S')}\n")

    t0 = time.time()
    result = await run_auto_git_pipeline(
        idea=idea,
        max_debate_rounds=2,
        use_web_search=True,
        auto_publish=False,
        output_dir="output/graphrag_test",
        interactive=False,
        resume=True,
    )
    elapsed = time.time() - t0

    print(f"\n{'='*80}")
    print(f"  PIPELINE COMPLETE — {elapsed:.1f}s elapsed")
    print(f"{'='*80}")

    # Summary
    stage = result.get("current_stage", "unknown")
    errors = result.get("errors", [])
    files = result.get("generated_code", {}).get("files", {}) if isinstance(result.get("generated_code"), dict) else {}
    tests_passed = result.get("tests_passed", False)
    self_eval = result.get("self_eval_score", "N/A")
    goal_pct = result.get("goal_achievement_pct", "N/A")

    print(f"\n  Stage:         {stage}")
    print(f"  Files:         {len(files)}")
    print(f"  Tests passed:  {tests_passed}")
    print(f"  Self-eval:     {self_eval}")
    print(f"  Goal %:        {goal_pct}")
    print(f"  Errors:        {len(errors)}")

    if files:
        print(f"\n  Generated files:")
        for fname, code in sorted(files.items()):
            lines = len(code.splitlines()) if isinstance(code, str) else 0
            chars = len(code) if isinstance(code, str) else 0
            print(f"    {fname}: {lines} lines, {chars:,} chars")

    if errors:
        print(f"\n  Last 5 errors:")
        for e in errors[-5:]:
            print(f"    - {str(e)[:120]}")

    # Print token and cost summary
    print()
    print_token_summary()

    # Print model health
    health = get_model_health_report()
    if health.get("dead"):
        print(f"\n  Dead models: {health['dead']}")
    if health.get("resolved"):
        print(f"\n  Resolved models:")
        for profile, model in health["resolved"].items():
            print(f"    {profile}: {model}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
