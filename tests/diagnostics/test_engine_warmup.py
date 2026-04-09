"""Quick test: Ollama model pre-warming + Perplexica auto-launch."""
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from dotenv import load_dotenv
load_dotenv()

from src.research.sota_researcher import SOTAResearcher


async def test():
    r = SOTAResearcher(max_iterations=1, max_perspectives=2, max_sub_questions=3)

    # Step 1: Test engine discovery (includes model warming + Perplexica launch)
    print("=" * 60)
    print("Testing engine warm-up and auto-launch...")
    print("=" * 60)
    await r._check_engines()

    perplexica_ok = r._perplexica is not None
    searxng_ok = r._searxng is not None
    print(f"\nPerplexica: {'YES' if perplexica_ok else 'NO'}")
    print(f"SearXNG: {'YES' if searxng_ok else 'NO'}")

    # Step 2: Check ollama ps
    import subprocess
    result = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=10)
    print(f"\nOllama models loaded:\n{result.stdout}")

    # Cleanup
    if r._perplexica:
        await r._perplexica.close()


if __name__ == "__main__":
    asyncio.run(test())
