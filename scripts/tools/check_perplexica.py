"""Quick check if Perplexica is available."""
import asyncio
import json

async def check():
    try:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.get("http://localhost:3000/api/providers") as r:
                print(f"STATUS: {r.status}")
                if r.status == 200:
                    data = await r.json()
                    print(json.dumps(data, indent=2)[:2000])
                else:
                    print(await r.text()[:500])
    except Exception as e:
        print(f"OFFLINE: {e}")

asyncio.run(check())
