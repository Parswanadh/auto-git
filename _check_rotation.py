"""Verify model configuration with proper dotenv loading (same as pipeline does)."""
from dotenv import load_dotenv
load_dotenv()

from src.utils.model_manager import get_model_manager

mgr = get_model_manager()

for profile, candidates in mgr.CLOUD_CONFIGS.items():
    free = [c for c in candidates if "free" in c[1].lower() or c[0].startswith("groq") or c[1] == "openrouter/hunter-alpha"]
    paid = [c for c in candidates if c not in free]
    print(f"\n{profile}: {len(candidates)} candidates ({len(free)} free, {len(paid)} paid)")
    for i, (p, m, t) in enumerate(candidates):
        tag = "FREE" if (p, m, t) in free else "PAID"
        print(f"  {i:2d}: [{tag:4s}] {p}/{m}")

print(f"\nGroq pool size: {len(mgr._rotation_counter)} (counter)")
from src.utils.model_manager import _GROQ_KEY_POOL
print(f"Groq keys in pool: {len(_GROQ_KEY_POOL)}")

# Test rotation
print("\n--- Round-robin test (balanced, 5 calls) ---")
for i in range(5):
    model = mgr.get_model("balanced")
    resolved = mgr._active_provider
    from src.utils.model_manager import RESOLVED_MODELS
    print(f"  Call {i+1}: {RESOLVED_MODELS.get('balanced', '?')}")
