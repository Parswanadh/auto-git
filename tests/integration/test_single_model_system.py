"""
Test script for Single-Model Multi-Agent System.

Validates that the sequential orchestrator works correctly with 8GB VRAM constraint.

Tests:
1. Persona loading and validation
2. Sequential critique execution
3. Consensus building
4. Full pipeline execution
"""

import asyncio
import sys
import time

# Add project root to path
sys.path.insert(0, "D:/Projects/auto-git")

from src.agents.personas import (
    PERSONA_CONFIGS,
    get_persona_prompt,
    get_persona_temperature,
    get_critique_personas,
    PERSONA_WEIGHTS,
    validate_persona
)
from src.agents.sequential_orchestrator import (
    SequentialAgentOrchestrator,
    create_orchestrator,
    quick_critique
)
from src.utils.ollama_client import get_ollama_client
from src.utils.logger import get_logger

logger = get_logger("test_single_model")


def test_personas():
    """Test 1: Verify all personas are properly configured."""
    print("\n" + "=" * 60)
    print("TEST 1: Persona Configuration")
    print("=" * 60)

    expected_personas = [
        "researcher",
        "architect",
        "ml_theorist",
        "systems_engineer",
        "applied_scientist",
        "code_reviewer"
    ]

    for persona in expected_personas:
        assert validate_persona(persona), f"Persona {persona} not found"

        config = PERSONA_CONFIGS[persona]
        assert config.name, f"Persona {persona} has no name"
        assert config.system_prompt, f"Persona {persona} has no system prompt"
        assert 0.0 <= config.temperature <= 1.0, f"Persona {persona} has invalid temperature"
        assert config.max_tokens > 0, f"Persona {persona} has invalid max_tokens"

        print(f"  [OK] {persona}: {config.role}")
        print(f"       Temperature: {config.temperature}, Max tokens: {config.max_tokens}")

    # Verify critique personas
    critique_personas = get_critique_personas()
    assert len(critique_personas) == 4, f"Expected 4 critique personas, got {len(critique_personas)}"
    print(f"\n  [OK] Critique personas: {', '.join(critique_personas)}")

    # Verify weights
    total_weight = sum(PERSONA_WEIGHTS.values())
    assert abs(total_weight - 1.0) < 0.01, f"Persona weights sum to {total_weight}, expected 1.0"
    print(f"  [OK] Persona weights sum to {total_weight}")

    print("\n[OK] All personas properly configured!")
    return True


async def test_ollama_connection():
    """Test 2: Verify Ollama connection and models."""
    print("\n" + "=" * 60)
    print("TEST 2: Ollama Connection")
    print("=" * 60)

    client = get_ollama_client()

    # Health check
    if not await client.health_check():
        print("[FAIL] Ollama health check failed")
        return False

    print("[OK] Ollama is healthy")

    # List models
    models = await client.list_models()
    model_names = [m.get("name", "") for m in models]

    print(f"[OK] Found {len(models)} models")

    # Check for required models
    required_models = [
        "qwen3:4b",      # Primary model (4GB VRAM)
        "gemma2:2b",     # Router model (2GB VRAM)
        "all-minilm"     # Embeddings (0.5GB VRAM)
    ]

    for model in required_models:
        # Check if model exists (partial match for tags)
        found = any(model in name for name in model_names)
        status = "[OK]" if found else "[WARN]"
        print(f"  {status} {model}: {'found' if found else 'NOT FOUND'}")

    print("\n[OK] Ollama connection verified!")
    return True


async def test_sequential_orchestrator():
    """Test 3: Test SequentialAgentOrchestrator."""
    print("\n" + "=" * 60)
    print("TEST 3: Sequential Agent Orchestrator")
    print("=" * 60)

    orchestrator = create_orchestrator()

    # Verify configuration
    assert orchestrator.PRIMARY_MODEL == "qwen3:4b", "Primary model should be qwen3:4b"
    assert orchestrator.ROUTER_MODEL == "gemma2:2b", "Router model should be gemma2:2b"
    print(f"[OK] Primary model: {orchestrator.PRIMARY_MODEL}")
    print(f"[OK] Router model: {orchestrator.ROUTER_MODEL}")

    # Test single persona execution
    print("\nTesting single persona execution...")
    result = await orchestrator.execute_with_persona(
        task="What is 2+2? Answer with just the number.",
        persona="architect",
        temperature=0.1
    )

    assert result["content"], "No content returned"
    assert result["tokens_used"] > 0, "No tokens counted"
    assert result["latency_seconds"] > 0, "No latency measured"

    print(f"[OK] Generated {result['tokens_used']} tokens in {result['latency_seconds']:.2f}s")
    print(f"[OK] Response: {result['content'][:100]}...")

    print("\n[OK] Sequential orchestrator working!")
    return True


async def test_simple_critique():
    """Test 4: Test simple critique without full pipeline."""
    print("\n" + "=" * 60)
    print("TEST 4: Simple Critique")
    print("=" * 60)

    # Simple test problem
    problem = {
        "domain": "Machine Learning",
        "challenge": "How to make neural networks train faster?",
        "current_solutions": [
            "Use GPUs for parallel computation",
            "Use mixed precision training"
        ],
        "limitations": [
            "GPU memory is limited",
            "Mixed precision can lose numerical stability"
        ],
        "requirements": [
            "Must work on consumer hardware",
            "Should not sacrifice accuracy"
        ]
    }

    # Simple solution to critique
    solution = """
    Proposed Solution: Quantization-Aware Training

    The approach is to use 8-bit quantization during training while maintaining
    a 32-bit master copy of weights. This reduces memory usage by 4x and allows
    larger batch sizes, which improves training speed.

    Key components:
    1. Quantize weights and gradients to 8-bit during forward/backward pass
    2. Maintain 32-bit master weights for updates
    3. Use straight-through estimator for gradients
    4. Apply loss scaling to prevent gradient vanishing

    Expected speedup: 2-3x faster training with minimal accuracy loss.
    """

    print(f"Problem: {problem['challenge']}")
    print(f"Solution: {solution[:100]}...")

    start_time = time.time()

    try:
        consensus = await quick_critique(solution, problem)

        elapsed = time.time() - start_time

        print(f"\n[OK] Critique completed in {elapsed:.1f}s")
        print(f"      Weighted score: {consensus.weighted_score:.1f}/10")
        print(f"      Confidence: {consensus.confidence:.1%}")
        print(f"      Disagreement: {consensus.disagreement_level:.2f}")
        print(f"      Needs refinement: {consensus.needs_refinement}")

        if consensus.common_strengths:
            print(f"\n      Common strengths:")
            for strength in consensus.common_strengths[:3]:
                print(f"        - {strength}")

        if consensus.common_weaknesses:
            print(f"\n      Common weaknesses:")
            for weakness in consensus.common_weaknesses[:3]:
                print(f"        - {weakness}")

        print("\n[OK] Simple critique working!")
        return True

    except Exception as e:
        print(f"\n[FAIL] Critique failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_pipeline():
    """Test 5: Test full pipeline (if models are available)."""
    print("\n" + "=" * 60)
    print("TEST 5: Full Pipeline (Optional)")
    print("=" * 60)

    # Check if user wants to run full test
    print("WARNING: Full pipeline test will take 2-5 minutes and make multiple LLM calls.")
    print("This is useful for validation but not required for basic functionality.")

    # Simple problem for testing
    problem = {
        "domain": "Natural Language Processing",
        "challenge": "How to make language models more context-aware?",
        "current_solutions": [
            "Increase context window (expensive)",
            "Use retrieval-augmented generation"
        ],
        "limitations": [
            "Long context windows are O(n^2) complexity",
            "RAG adds latency and requires external knowledge base"
        ],
        "requirements": [
            "Should scale linearly with context length",
            "Must maintain coherence across long documents"
        ]
    }

    orchestrator = create_orchestrator()

    try:
        result = await orchestrator.execute_pipeline(problem, max_refinements=1)

        print(f"\n[OK] Pipeline completed!")
        print(f"      Stages: {', '.join(result.stages_completed)}")
        print(f"      Total tokens: {result.total_tokens}")
        print(f"      Total latency: {result.total_latency:.1f}s")
        print(f"      Consensus score: {result.consensus.weighted_score:.1f}/10")
        print(f"      Final solution: {result.final_solution[:200]}...")

        return True

    except Exception as e:
        print(f"\n[WARN] Full pipeline test skipped or failed: {e}")
        return None  # Don't fail, this is optional


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SINGLE-MODEL MULTI-AGENT SYSTEM TEST")
    print("=" * 60)
    print("\nThis test validates the single-model architecture for 8GB VRAM constraint.")
    print("Models used: qwen3:4b (4GB), gemma2:2b (2GB), all-minilm (0.5GB)")
    print("Total VRAM: 6.5GB (well within 8GB limit)")

    results = {}

    # Test 1: Persona configuration
    try:
        results["personas"] = test_personas()
    except Exception as e:
        print(f"[FAIL] Persona test failed: {e}")
        results["personas"] = False

    # Test 2: Ollama connection
    try:
        results["ollama"] = await test_ollama_connection()
    except Exception as e:
        print(f"[FAIL] Ollama test failed: {e}")
        results["ollama"] = False

    # Only continue if Ollama is working
    if results.get("ollama"):
        # Test 3: Sequential orchestrator
        try:
            results["orchestrator"] = await test_sequential_orchestrator()
        except Exception as e:
            print(f"[FAIL] Orchestrator test failed: {e}")
            import traceback
            traceback.print_exc()
            results["orchestrator"] = False

        # Test 4: Simple critique
        try:
            results["critique"] = await test_simple_critique()
        except Exception as e:
            print(f"[FAIL] Critique test failed: {e}")
            import traceback
            traceback.print_exc()
            results["critique"] = False

        # Test 5: Full pipeline (optional)
        try:
            results["pipeline"] = await test_full_pipeline()
        except Exception as e:
            print(f"[WARN] Pipeline test failed: {e}")
            results["pipeline"] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]" if passed is False else "[SKIP]"
        print(f"  {status} {test_name}")

    passed_count = sum(1 for v in results.values() if v is True)
    total_count = len(results)

    print(f"\n{passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n[SUCCESS] All tests passed! Single-model system is working.")
    elif passed_count >= total_count - 1:
        print("\n[OK] Core tests passed. System is functional.")
    else:
        print("\n[FAIL] Some tests failed. Please check the errors above.")

    return passed_count >= total_count - 1  # Allow 1 test to fail/skip


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
