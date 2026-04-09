"""
Direct GLM API test script - bypasses factory health check.
"""

import asyncio
import os
import sys
import time

# Add project root to path
sys.path.insert(0, "D:/Projects/auto-git")

from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.llm_providers.example", override=False)
load_dotenv(".env", override=True)


async def test_direct_api():
    """Test GLM API directly using httpx."""
    import httpx

    api_key = os.getenv("GLM_API_KEY")
    api_provider = os.getenv("GLM_API_PROVIDER", "z.ai")
    model = os.getenv("GLM_MODEL", "glm-4.5")

    if not api_key:
        print("[FAIL] GLM_API_KEY not set")
        return

    print("=" * 60)
    print("Direct GLM API Test")
    print("=" * 60)
    print(f"API Provider: {api_provider}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:20]}...{api_key[-10:]}")

    # Generate JWT token if using Z.ai
    try:
        import jwt
        if "." in api_key:
            id_part, secret = api_key.split(".", 1)
            exp_seconds = 3600
            payload = {
                "api_key": id_part,
                "exp": int(round(time.time() * 1000)) + exp_seconds * 1000,
                "timestamp": int(round(time.time() * 1000)),
            }
            token = jwt.encode(
                payload,
                secret,
                algorithm="HS256",
                headers={"alg": "HS256", "sign_type": "SIGN"},
            )
            print(f"[OK] JWT token generated: {token[:50]}...")
            auth_token = token
        else:
            auth_token = api_key
    except ImportError:
        print("[WARN] PyJWT not installed, using direct API key")
        auth_token = api_key

    base_url = "https://api.z.ai/api/paas/v4/"

    async with httpx.AsyncClient(timeout=30) as client:
        # Test health check
        print("\n--- Testing Health Check ---")
        try:
            response = await client.post(
                f"{base_url}chat/completions",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")

        # Test actual generation
        print("\n--- Testing Generation ---")
        try:
            response = await client.post(
                f"{base_url}chat/completions",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say 'Hello from GLM!'"}],
                    "max_tokens": 50,
                    "temperature": 0.7
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"[OK] Response: {content}")
            else:
                print(f"[FAIL] Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_direct_api())
