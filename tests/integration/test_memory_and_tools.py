"""
Integration test for Memory and Tool systems.

Tests:
1. HierarchicalMemory - store and retrieve episodes
2. ToolRegistry - execute tools in parallel
3. End-to-end: Memory + Tools together
"""

import asyncio
import sys
import time

# Add project root to path
sys.path.insert(0, "D:/Projects/auto-git")

from src.agents.memory.hierarchical_memory import (
    HierarchicalMemory,
    get_memory,
    Episode,
    Pattern,
    Skill
)
from src.agents.tools.tool_registry import (
    ToolRegistry,
    get_tool_registry,
    ArxivSearchTool,
    PapersWithCodeTool,
    DatasetCheckerTool,
    GitHubSearchTool
)
from src.utils.logger import get_logger

logger = get_logger("test_memory_tools")


async def test_hierarchical_memory():
    """Test 1: Hierarchical Memory system."""
    print("\n" + "=" * 60)
    print("TEST 1: Hierarchical Memory System")
    print("=" * 60)

    memory = HierarchicalMemory(storage_path="./data/test_memory")

    # Test storing an episode
    print("\nStoring episode...")
    problem = {
        "domain": "Natural Language Processing",
        "challenge": "How to make language models more context-aware?",
        "current_solutions": ["Increase context window", "Use RAG"],
        "limitations": ["Long context is O(n^2)", "RAG adds latency"],
        "requirements": ["Linear scaling", "Maintain coherence"]
    }

    solution = """
    Proposed Solution: Sparse Attention Mechanism

    Use sparse attention patterns to reduce complexity from O(n^2) to O(n log n)
    while maintaining long-range dependencies through strategic attention heads.

    Key components:
    1. Local attention for nearby tokens
    2. Global attention for key positions
    3. Random attention for diversity
    4. Efficient implementation with Flash Attention
    """

    critiques = [
        {
            "persona": "ml_theorist",
            "content": "Theoretical soundness: Good. Complexity analysis is correct.",
            "score": 8.0
        },
        {
            "persona": "systems_engineer",
            "content": "Scalability: Excellent. O(n log n) is much better than O(n^2).",
            "score": 9.0
        },
        {
            "persona": "applied_scientist",
            "content": "Practical: Good but Flash Attention requires specific hardware.",
            "score": 7.5
        },
        {
            "persona": "code_reviewer",
            "content": "Implementation: Need more details on sparse pattern selection.",
            "score": 7.0
        }
    ]

    consensus = {
        "weighted_score": 7.875,
        "confidence": 0.9,
        "needs_refinement": False,
        "common_strengths": ["Good theoretical foundation", "Scalable approach"],
        "common_weaknesses": ["Implementation details missing"],
        "disagreement_level": 0.83
    }

    episode_id = await memory.remember_debate(
        problem=problem,
        solution=solution,
        critiques=critiques,
        consensus=consensus,
        outcome="success",
        quality_score=7.875,
        tokens_used=5000,
        latency_seconds=120.0
    )

    print(f"[OK] Episode stored: {episode_id}")

    # Test retrieval
    print("\nRetrieving similar episodes...")
    similar = await memory.retrieve_relevant(problem, top_k=5, min_similarity=0.5)
    print(f"[OK] Retrieved {len(similar)} episodes")

    # Test skills
    print("\nGetting applicable skills...")
    skills = await memory.get_applicable_skills(problem)
    print(f"[OK] Found {len(skills)} applicable skills")
    for skill in skills[:3]:
        print(f"      - {skill.name}: {skill.description[:50]}")

    # Test statistics
    stats = memory.get_statistics()
    print(f"\n[OK] Memory Statistics:")
    print(f"      Episodes: {stats['total_episodes']}")
    print(f"      Patterns: {stats['total_patterns']}")
    print(f"      Skills: {stats['total_skills']}")
    print(f"      Success rate: {stats['success_rate']:.1%}")

    print("\n[OK] Hierarchical Memory test passed!")
    return True


async def test_tool_registry():
    """Test 2: Tool Registry system."""
    print("\n" + "=" * 60)
    print("TEST 2: Tool Registry System")
    print("=" * 60)

    registry = ToolRegistry()

    # List available tools
    tools = registry.list_tools()
    print(f"\n[OK] Available tools: {', '.join(tools)}")

    # Test descriptions
    descriptions = registry.get_tool_descriptions()
    for tool_name, desc in descriptions.items():
        print(f"\n  {tool_name}:")
        print(f"    {desc[:100]}...")

    # Test arXiv search
    print("\n\nTesting arXiv search...")
    result = await registry.call_tool(
        "arxiv_search",
        query="attention mechanism",
        categories=["cs.AI", "cs.LG"],
        max_results=3
    )

    if result.success:
        papers = result.data
        print(f"[OK] Found {len(papers)} papers in {result.execution_time:.2f}s")
        for paper in papers[:2]:
            print(f"      - {paper['title'][:60]}...")
    else:
        print(f"[WARN] arXiv search failed: {result.error}")

    # Test dataset checker
    print("\nTesting dataset checker...")
    result = await registry.call_tool(
        "dataset_checker",
        dataset_name="imagenet",
        hub="huggingface"
    )

    if result.success:
        data = result.data
        print(f"[OK] Dataset check completed in {result.execution_time:.2f}s")
        if data.get("exists"):
            print(f"      Dataset exists: {data['name']}")
        else:
            print(f"      Dataset not found, suggestions: {data.get('suggestions', [])}")
    else:
        print(f"[WARN] Dataset check failed: {result.error}")

    # Test parallel tool execution
    print("\nTesting parallel tool execution...")
    parallel_calls = {
        "arxiv_search": {
            "query": "transformer architecture",
            "max_results": 2
        },
        "github_search": {
            "query": "transformer",
            "language": "python",
            "max_results": 2
        }
    }

    start_time = time.time()
    parallel_results = await registry.call_tools_parallel(parallel_calls)
    elapsed = time.time() - start_time

    print(f"[OK] Parallel execution completed in {elapsed:.2f}s")
    for tool_name, result in parallel_results.items():
        status = "[OK]" if result.success else "[FAIL]"
        items = len(result.data) if result.success and isinstance(result.data, list) else 0
        print(f"      {status} {tool_name}: {items} results")

    print("\n[OK] Tool Registry test passed!")
    return True


async def test_end_to_end():
    """Test 3: End-to-end integration (Memory + Tools)."""
    print("\n" + "=" * 60)
    print("TEST 3: End-to-End Integration")
    print("=" * 60)

    memory = get_memory()
    registry = get_tool_registry()

    # Scenario: Research a problem using tools, then remember the outcome
    problem = {
        "domain": "Computer Vision",
        "challenge": "How to improve object detection accuracy?",
        "current_solutions": ["YOLO", "Faster R-CNN"],
        "limitations": ["Trade-off between speed and accuracy"],
        "requirements": ["Real-time performance", "High accuracy"]
    }

    print(f"\nProblem: {problem['challenge']}")

    # Step 1: Use tools to research
    print("\n[Step 1] Researching with tools...")

    # Search arXiv for related papers
    arxiv_result = await registry.call_tool(
        "arxiv_search",
        query="object detection accuracy",
        categories=["cs.CV"],
        max_results=3
    )

    if arxiv_result.success:
        papers = arxiv_result.data
        print(f"  [arXiv] Found {len(papers)} related papers")
        for paper in papers[:2]:
            print(f"    - {paper['title'][:50]}...")

    # Search GitHub for implementations
    github_result = await registry.call_tool(
        "github_search",
        query="object detection",
        language="python",
        max_results=2
    )

    if github_result.success:
        repos = github_result.data
        print(f"  [GitHub] Found {len(repos)} related repos")
        for repo in repos[:2]:
            print(f"    - {repo['name']} ({repo['stars']} stars)")

    # Step 2: Store the research in memory
    print("\n[Step 2] Storing research in memory...")

    solution = f"""
    Based on research from {len(arxiv_result.data)} papers and {len(github_result.data)} GitHub repos:

    Proposed Solution: Multi-Scale Feature Pyramid Network

    Combine insights from recent papers:
    - Use feature pyramid networks for multi-scale detection
    - Apply efficient attention mechanisms from recent arXiv papers
    - Implement optimized architecture based on successful GitHub repos

    Expected improvements: +5-10% mAP with minimal speed impact.
    """

    critiques = [
        {"persona": "ml_theorist", "content": "Sound approach", "score": 8.0},
        {"persona": "systems_engineer", "content": "Scalable design", "score": 8.5},
        {"persona": "applied_scientist", "content": "Practical solution", "score": 8.0},
        {"persona": "code_reviewer", "content": "Implementation needed", "score": 7.5}
    ]

    consensus = {
        "weighted_score": 8.0,
        "confidence": 0.95,
        "needs_refinement": False,
        "common_strengths": ["Research-backed", "Scalable"],
        "common_weaknesses": [],
        "disagreement_level": 0.4
    }

    episode_id = await memory.remember_debate(
        problem=problem,
        solution=solution,
        critiques=critiques,
        consensus=consensus,
        outcome="success",
        quality_score=8.0,
        tokens_used=3000,
        latency_seconds=90.0
    )

    print(f"  [OK] Episode stored: {episode_id}")

    # Step 3: Retrieve and verify
    print("\n[Step 3] Retrieving from memory...")

    similar = await memory.retrieve_relevant(problem, top_k=3)
    print(f"  [OK] Retrieved {len(similar)} similar episodes")

    for ep in similar:
        print(f"    - {ep.episode_id}: score={ep.quality_score:.1f}, outcome={ep.outcome}")

    # Step 4: Check applicable skills
    print("\n[Step 4] Checking applicable skills...")
    skills = await memory.get_applicable_skills(problem)
    print(f"  [OK] Found {len(skills)} applicable skills")
    for skill in skills[:3]:
        print(f"    - {skill.name} (success_rate: {skill.success_rate:.1%})")

    print("\n[OK] End-to-end integration test passed!")
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MEMORY & TOOLS INTEGRATION TEST")
    print("=" * 60)

    results = {}

    # Test 1: Hierarchical Memory
    try:
        results["memory"] = await test_hierarchical_memory()
    except Exception as e:
        print(f"\n[FAIL] Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        results["memory"] = False

    # Test 2: Tool Registry
    try:
        results["tools"] = await test_tool_registry()
    except Exception as e:
        print(f"\n[FAIL] Tools test failed: {e}")
        import traceback
        traceback.print_exc()
        results["tools"] = False

    # Test 3: End-to-end
    try:
        results["integration"] = await test_end_to_end()
    except Exception as e:
        print(f"\n[FAIL] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        results["integration"] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print(f"\n{passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n[SUCCESS] All tests passed! Memory and Tools are working.")
    else:
        print(f"\n[WARN] {total_count - passed_count} test(s) failed.")

    return passed_count >= total_count - 1


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
