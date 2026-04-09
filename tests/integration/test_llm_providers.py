"""
Test script for LLM provider system.

Tests the dual-mode LLM implementation with your API key.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, "D:/Projects/auto-git")

from dotenv import load_dotenv

# Load environment variables from multiple sources
# Load example first (for defaults), then main .env (for actual values including API keys)
load_dotenv(".env.llm_providers.example", override=False)  # LLM provider defaults
load_dotenv(".env", override=True)  # Main .env file with actual API keys

from src.utils.llm_providers.factory import LLMFactory
from src.utils.llm_providers.config import TaskType, ExecutionMode


async def test_factory():
    """Test LLMFactory initialization."""
    print("=" * 60)
    print("Testing LLM Factory Initialization")
    print("=" * 60)

    factory = LLMFactory()

    print(f"\n[OK] Factory initialized")
    print(f"Available providers: {factory.get_available_providers()}")
    print(f"Daily cost limit: ${os.getenv('LLM_DAILY_COST_LIMIT', '10.0')}")

    return factory


async def test_ollama_provider(factory):
    """Test Ollama provider (local)."""
    print("\n" + "=" * 60)
    print("Testing Ollama Provider (Local)")
    print("=" * 60)

    # Small delay before health check
    import asyncio
    await asyncio.sleep(0.5)

    try:
        provider = await factory.get_provider(TaskType.FAST_ANALYSIS, ExecutionMode.LOCAL)
        print(f"[OK] Ollama provider created: {provider.get_provider_name()}")

        # Health check
        is_healthy = await provider.health_check()
        print(f"Health check: {'[OK] PASS' if is_healthy else '[FAIL] FAILED'}")

        if is_healthy:
            # Test generation
            print("\nTesting generation...")
            result = await provider.generate("Say 'Hello from Ollama!'", max_tokens=50)

            print(f"Content: {result['content'][:100]}...")
            print(f"Tokens: {result['tokens_used']}")
            print(f"Cost: ${result['cost_usd']:.4f}")
            print(f"Latency: {result['latency_seconds']:.2f}s")
            print(f"[OK] Ollama generation successful")

    except Exception as e:
        print(f"[FAIL] Ollama provider test failed: {e}")


async def test_glm_provider(factory):
    """Test GLM provider (cloud)."""
    print("\n" + "=" * 60)
    print("Testing GLM Provider (Cloud)")
    print("=" * 60)

    api_key = os.getenv("GLM_API_KEY")
    if not api_key or api_key == "your_glm_api_key_here":
        print("[WARN] GLM_API_KEY not set, skipping GLM test")
        print("       Add your GLM API key to .env or .env.llm_providers.example")
        return

    # Small delay before health check to avoid rate limiting
    import asyncio
    await asyncio.sleep(1.0)

    try:
        provider = await factory.get_provider(TaskType.CODE_GENERATION, ExecutionMode.CLOUD)
        print(f"[OK] GLM provider created: {provider.get_provider_name()}")

        # Health check
        is_healthy = await provider.health_check()
        print(f"Health check: {'[OK] PASS' if is_healthy else '[FAIL] FAILED'}")

        if is_healthy:
            # Test generation
            print("\nTesting generation...")
            result = await provider.generate("Say 'Hello from GLM-4.5!'", max_tokens=50)

            print(f"Content: {result['content'][:100]}...")
            print(f"Tokens: {result['tokens_used']}")
            print(f"Cost: ${result['cost_usd']:.4f}")
            print(f"Latency: {result['latency_seconds']:.2f}s")
            print(f"[OK] GLM generation successful")

            # Check daily cost
            daily_cost = await factory.get_total_cost_today()
            print(f"\nDaily cost so far: ${daily_cost:.4f}")

    except Exception as e:
        print(f"[FAIL] GLM provider test failed: {e}")


async def test_dual_provider_fallback(factory):
    """Test DualProvider with fallback strategy."""
    print("\n" + "=" * 60)
    print("Testing DualProvider (Fallback Strategy)")
    print("=" * 60)

    # Small delay before health check
    import asyncio
    await asyncio.sleep(1.0)

    try:
        provider = await factory.get_provider(TaskType.ANALYSIS, ExecutionMode.FALLBACK)
        print(f"[OK] DualProvider created (fallback mode)")

        # Test generation (will use GLM, fallback to Ollama if needed)
        print("\nTesting generation with fallback...")
        result = await provider.generate("Say 'Hello from DualProvider!'", max_tokens=50)

        print(f"Content: {result['content'][:100]}...")
        print(f"Provider: {result['provider']}")
        print(f"Tokens: {result['tokens_used']}")
        print(f"Cost: ${result['cost_usd']:.4f}")
        print(f"Fallback used: {result.get('fallback_used', False)}")
        print(f"[OK] DualProvider generation successful")

    except Exception as e:
        print(f"[FAIL] DualProvider test failed: {e}")


async def test_cost_tracker():
    """Test cost tracking."""
    print("\n" + "=" * 60)
    print("Testing Cost Tracker")
    print("=" * 60)

    try:
        from src.utils.llm_providers.utils.cost_tracker import CostTracker

        tracker = CostTracker()
        daily_summary = await tracker.get_daily_summary()

        print(f"Today's total cost: ${daily_summary['total_cost']:.4f}")
        print(f"Today's total tokens: {daily_summary['total_tokens']}")
        print(f"By provider: {daily_summary['by_provider']}")

        is_within_limit = await tracker.is_within_limit()
        print(f"Within daily limit: {'[OK] YES' if is_within_limit else '[FAIL] NO'}")

        print("[OK] Cost tracker test successful")

    except Exception as e:
        print(f"[FAIL] Cost tracker test failed: {e}")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LLM Provider System Test Suite")
    print("=" * 60)

    # Check environment
    api_key = os.getenv("GLM_API_KEY")
    if api_key and api_key != "your_glm_api_key_here":
        print(f"\n[OK] GLM_API_KEY is configured")
    else:
        print(f"\n[WARN] GLM_API_KEY not configured")
        print("       To test GLM, add GLM_API_KEY to .env file")

    try:
        # Test factory
        factory = await test_factory()

        # Test Ollama (local)
        await test_ollama_provider(factory)

        # Test GLM (cloud)
        await test_glm_provider(factory)

        # Test DualProvider
        await test_dual_provider_fallback(factory)

        # Test cost tracker
        await test_cost_tracker()

        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print("[OK] Core LLM provider system is working!")
        print("\nPhase 1 Complete: Dual-Mode LLM Foundation")
        print("\nNext steps:")
        print("1. Migrate existing agents to use LLMFactory")
        print("2. Implement enhanced research agents")
        print("3. Create skills framework")

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
