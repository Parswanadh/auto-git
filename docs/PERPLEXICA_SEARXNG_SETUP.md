# Perplexica + SearxNG + Tor Infrastructure Setup Guide

**Purpose**: Reusable guide for setting up a self-hosted AI-powered research stack  
**Stack**: Perplexica (AI search) → SearxNG (meta-search) → Tor (IP rotation) + Redis (caching)  
**Last Tested**: March 11, 2026

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                       YOUR APPLICATION                           │
│            (Python async client → HTTP POST to API)              │
└──────────────────────┬───────────────────────────────────────────┘
                       │ http://localhost:9123/api/search
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PERPLEXICA (Port 9123)                         │
│  • Next.js standalone app (Node.js)                              │
│  • LLM-powered RAG: synthesizes search results with citations    │
│  • Swarm mode: 6 parallel specialized agents                     │
│  • Uses Ollama for chat + embeddings (local, free)               │
│  • Connects to SearxNG for raw search results                    │
└──────────────────────┬───────────────────────────────────────────┘
                       │ http://localhost:8080/search?format=json
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    SEARXNG (Port 8080)                            │
│  • Meta-search engine (aggregates 20+ engines)                   │
│  • JSON API for programmatic access                              │
│  • Rate-limit bypass via Tor proxy                               │
│  • Redis for result caching                                      │
└──────────┬───────────────────────────────────┬───────────────────┘
           │ socks5h://127.0.0.1:9050          │ redis://localhost:6379
           ▼                                   ▼
┌─────────────────────┐              ┌──────────────────┐
│   TOR PROXY (9050)  │              │  REDIS (6379)    │
│   Docker container  │              │  Docker container│
│   dperson/torproxy  │              │  redis:alpine    │
│   IP rotation       │              │  Result caching  │
└─────────────────────┘              └──────────────────┘
```

---

## Prerequisites

- **Docker Desktop** (for Tor + Redis containers)
- **Python 3.10+** with a conda or venv environment
- **Ollama** installed and running (port 11434)
- **Node.js 18+** (for Perplexica)
- **Git** (to clone repos)

---

## Step 1: Docker Containers (Tor + Redis)

### Start Tor Proxy (IP rotation for SearxNG)

```powershell
docker run -d --name searxng-tor --restart unless-stopped -p 9050:9050 dperson/torproxy
```

### Start Redis (SearxNG result caching)

```powershell
docker run -d --name searxng-redis --restart unless-stopped -p 6379:6379 redis:alpine
```

### Verify containers

```powershell
docker ps --format "{{.Names}} | {{.Ports}} | {{.Status}}"
# Expected:
# searxng-tor   | 0.0.0.0:9050->9050/tcp | Up X minutes
# searxng-redis | 0.0.0.0:6379->6379/tcp | Up X minutes
```

---

## Step 2: Ollama Models

Perplexica needs a **chat model** and an **embedding model** running in Ollama.

```powershell
# Chat model (small, fast — Perplexica only uses it for result synthesis)
ollama pull qwen3.5:2b

# Embedding model (for semantic search within Perplexica)
ollama pull embeddinggemma:300m

# Verify
ollama list
```

**Model choices** (adjust based on your VRAM):

| VRAM   | Chat Model     | Embedding Model      |
|--------|----------------|----------------------|
| 4 GB   | qwen3.5:2b     | embeddinggemma:300m  |
| 8 GB   | qwen3.5:9b     | embeddinggemma:300m  |
| 16 GB+ | qwen3:14b      | nomic-embed-text     |

---

## Step 3: SearxNG Setup

### Clone and create config directory

```powershell
cd D:\Projects  # or wherever you want it
git clone https://github.com/searxng/searxng.git
cd searxng
mkdir data
```

### Create `data/settings.yml`

This is the key config file. Save this as `D:\Projects\searxng\data\settings.yml`:

```yaml
use_default_settings: true

general:
  instance_name: 'My-SearxNG'
  debug: false

search:
  autocomplete: 'google'
  formats:
    - html
    - json            # REQUIRED for API access
  default_lang: 'en'

server:
  port: 8080
  bind_address: '127.0.0.1'
  secret_key: 'GENERATE_A_RANDOM_KEY_HERE'  # python -c "import secrets; print(secrets.token_hex(32))"
  limiter: false       # Disable rate limiting for localhost
  public_instance: false
  request_timeout: 15

# Redis caching (requires Docker redis container)
valkey:
  url: "redis://localhost:6379/0"

# Tor proxy for all outgoing requests (prevents IP bans)
outgoing:
  request_timeout: 12
  max_request_timeout: 25
  pool_connections: 50
  pool_maxsize: 15
  enable_http2: true
  proxies:
    all://:
      - socks5h://127.0.0.1:9050    # Tor SOCKS5 proxy
  using_tor_proxy: true
  extra_proxy_timeout: 10

ui:
  static_use_hash: true

# Engine configuration — enable reliable + academic engines
engines:
  # --- GENERAL (reliable through Tor) ---
  - name: google
    disabled: false
    shortcut: g
    timeout: 10
  - name: bing
    disabled: false
    shortcut: bi
    timeout: 10
  - name: duckduckgo
    disabled: false
    shortcut: ddg
    timeout: 15
  - name: brave
    disabled: false
    shortcut: br
    timeout: 15
  - name: startpage
    disabled: false
    shortcut: sp
    timeout: 15
  - name: qwant
    disabled: false
    shortcut: qw
    timeout: 10
  - name: mojeek
    disabled: false
    shortcut: mjk
    timeout: 10
  - name: yahoo
    disabled: false
    shortcut: yh
    timeout: 10
  - name: wikipedia
    disabled: false
    shortcut: wp
  - name: wikidata
    disabled: false
    shortcut: wd

  # --- ACADEMIC/SCIENCE ---
  - name: arxiv
    disabled: false
    shortcut: arx
  - name: google scholar
    disabled: false
    shortcut: gs
    timeout: 10
  - name: semantic scholar
    disabled: false
    shortcut: se
    timeout: 10
  - name: crossref
    disabled: false
    shortcut: cr
  - name: openairedatasets
    disabled: false
    shortcut: oad
  - name: openairepublications
    disabled: false
    shortcut: oap
  - name: pubmed
    disabled: false
    shortcut: pub

  # --- CODE/TECH ---
  - name: github
    disabled: false
    shortcut: gh
  - name: stackoverflow
    disabled: false
    shortcut: st
  - name: npm
    disabled: false
    shortcut: npm
  - name: pypi
    disabled: false
    shortcut: pypi
  - name: hackernews
    disabled: false
    shortcut: hn
  - name: mdn
    disabled: false
    shortcut: mdn
```

### Create a conda environment for SearxNG

```powershell
conda create -n searxng python=3.12 -y
conda activate searxng
cd D:\Projects\searxng
pip install -e .
```

### Generate a secret key

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
# Copy the output and replace 'GENERATE_A_RANDOM_KEY_HERE' in settings.yml
```

### Start SearxNG

```powershell
conda activate searxng
cd D:\Projects\searxng
$env:SEARXNG_SETTINGS_PATH = "D:\Projects\searxng\data\settings.yml"
python -m searx.webapp
```

**Expected output:**
```
[INFO] searx.webapp - SearXNG is running on http://127.0.0.1:8080
```

### Verify SearxNG

```powershell
# Browser: http://localhost:8080
# API test:
Invoke-RestMethod "http://localhost:8080/search?q=python+asyncio&format=json" | Select-Object -ExpandProperty results | Select-Object -First 3
```

---

## Step 4: Perplexica Setup

### Clone and build

```powershell
cd D:\Projects
git clone https://github.com/ItzCrazyKns/Perplexica.git perplexica
cd perplexica

# Install dependencies and build
npm install
npm run build
```

### Configure `data/config.json`

After first run, Perplexica creates `data/config.json`. You can also create it manually.
The key settings are:

```json
{
  "version": 1,
  "setupComplete": true,
  "preferences": {
    "theme": "dark"
  },
  "modelProviders": [
    {
      "id": "ollama-provider",
      "name": "Ollama",
      "type": "ollama",
      "config": {
        "baseURL": "http://localhost:11434"
      },
      "chatModels": [
        {
          "name": "qwen3.5:2b",
          "key": "qwen3.5:2b"
        }
      ],
      "embeddingModels": [
        {
          "name": "embeddinggemma:300m",
          "key": "embeddinggemma:300m"
        }
      ]
    }
  ],
  "search": {
    "searxngURL": "http://localhost:8080"
  }
}
```

**Important**: The `search.searxngURL` tells Perplexica where to find SearxNG. Make sure SearxNG is running before starting Perplexica.

#### Optional: Add cloud providers for better synthesis quality

You can add OpenRouter, Groq, or Anthropic for Perplexica's LLM synthesis:

```json
{
  "id": "openrouter-provider",
  "name": "OpenRouter",
  "type": "openai",
  "chatModels": [
    {
      "name": "grok-4.1-fast",
      "key": "x-ai/grok-4.1-fast"
    }
  ],
  "embeddingModels": [],
  "config": {
    "apiKey": "sk-or-v1-YOUR_KEY_HERE",
    "baseURL": "https://openrouter.ai/api/v1"
  }
}
```

### Start Perplexica

```powershell
cd D:\Projects\perplexica\.next\standalone

# Copy config to standalone directory
Copy-Item -Force D:\Projects\perplexica\data\config.json D:\Projects\perplexica\.next\standalone\data\config.json

# Set port (default 3000, we use 9123 to avoid conflicts)
$env:PORT = "9123"

# Start
node server.js
```

**Expected output:**
```
▲ Next.js 14.x.x
- Local:        http://localhost:9123
✓ Ready in Xms
```

### Verify Perplexica

```powershell
# Browser: http://localhost:9123
# API test:
Invoke-RestMethod "http://localhost:9123/api/models"
```

---

## Step 5: Full Startup Sequence

Run these in order (each in a separate terminal):

### Terminal 1: Docker containers

```powershell
docker start searxng-tor searxng-redis
# Or if first time:
# docker run -d --name searxng-tor --restart unless-stopped -p 9050:9050 dperson/torproxy
# docker run -d --name searxng-redis --restart unless-stopped -p 6379:6379 redis:alpine
```

### Terminal 2: Ollama (usually auto-starts)

```powershell
ollama serve
# Usually already running as a service
```

### Terminal 3: SearxNG

```powershell
conda activate searxng
cd D:\Projects\searxng
$env:SEARXNG_SETTINGS_PATH = "D:\Projects\searxng\data\settings.yml"
python -m searx.webapp
```

### Terminal 4: Perplexica

```powershell
cd D:\Projects\perplexica\.next\standalone
Copy-Item -Force D:\Projects\perplexica\data\config.json D:\Projects\perplexica\.next\standalone\data\config.json
$env:PORT = "9123"
node server.js
```

### Verification (in any terminal)

```powershell
# Test Tor proxy
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip

# Test Redis
redis-cli -h localhost -p 6379 ping
# Expected: PONG

# Test SearxNG
Invoke-RestMethod "http://localhost:8080/search?q=test&format=json" | Select-Object -ExpandProperty results | Measure-Object
# Expected: Count > 0

# Test Perplexica
Invoke-RestMethod "http://localhost:9123/api/models"
# Expected: JSON with model providers

# Test Perplexica search
$body = @{
    query = "Python asyncio best practices"
    chatModel = @{ providerId = "ollama-provider"; key = "qwen3.5:2b" }
    embeddingModel = @{ providerId = "ollama-provider"; key = "embeddinggemma:300m" }
    optimizationMode = "balanced"
    sources = @("web")
    history = @()
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:9123/api/search" -Method POST -Body $body -ContentType "application/json"
```

---

## Step 6: Python Client Integration

### Environment Variables

Add to your `.env` file:

```bash
# Perplexica
PERPLEXICA_URL=http://localhost:9123
PERPLEXICA_CHAT_PROVIDER=Ollama
PERPLEXICA_CHAT_MODEL=qwen3.5:2b
PERPLEXICA_EMBEDDING_PROVIDER=Ollama
PERPLEXICA_EMBEDDING_MODEL=embeddinggemma:300m
PERPLEXICA_MODE=quality          # speed | balanced | quality
PERPLEXICA_TIMEOUT=300           # seconds (swarm mode needs 2-5 min)
PERPLEXICA_SWARM=true            # enable 6-agent parallel research
```

### Minimal Python Client

```python
"""Minimal Perplexica client — copy this for any project."""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp


@dataclass
class SearchResult:
    title: str
    url: str
    content: str


class PerplexicaClient:
    def __init__(self, base_url: str = "http://localhost:9123", timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._chat_model: Optional[dict] = None
        self._embedding_model: Optional[dict] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def discover_models(self) -> bool:
        """Auto-discover available models from Perplexica."""
        session = await self._get_session()
        try:
            async with session.get(f"{self.base_url}/api/models") as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                providers = data if isinstance(data, list) else data.get("providers", [])
                for p in providers:
                    if not self._chat_model and p.get("chatModels"):
                        self._chat_model = {
                            "providerId": p["id"],
                            "key": p["chatModels"][0]["key"],
                        }
                    if not self._embedding_model and p.get("embeddingModels"):
                        self._embedding_model = {
                            "providerId": p["id"],
                            "key": p["embeddingModels"][0]["key"],
                        }
                return bool(self._chat_model and self._embedding_model)
        except Exception:
            return False

    async def search(
        self,
        query: str,
        mode: str = "balanced",
        sources: list[str] | None = None,
    ) -> Dict[str, Any]:
        """Run a single search query."""
        if not self._chat_model:
            await self.discover_models()

        session = await self._get_session()
        body = {
            "chatModel": self._chat_model,
            "embeddingModel": self._embedding_model,
            "optimizationMode": mode,
            "sources": sources or ["web"],
            "query": query,
            "history": [],
        }

        async with session.post(f"{self.base_url}/api/search", json=body) as resp:
            data = await resp.json()
            return data

    async def swarm_search(self, query: str, mode: str = "quality") -> Dict[str, Any]:
        """
        Swarm mode: 6 specialized agents search in parallel.
        
        Agents:
          1. Core Researcher — main overview
          2. Technical Analyst — implementation details
          3. News Tracker — latest developments
          4. Comparison Analyst — alternatives
          5. Applications Expert — real-world use cases
          6. Community Analyst — opinions & experiences
        
        Returns synthesized results via SSE stream.
        """
        if not self._chat_model:
            await self.discover_models()

        session = await self._get_session()
        body = {
            "chatModel": self._chat_model,
            "embeddingModel": self._embedding_model,
            "optimizationMode": mode,
            "sources": ["web", "academic", "discussions"],
            "query": query,
            "history": [],
            "stream": True,
            "swarmMode": True,
        }

        t0 = time.monotonic()
        message_parts = []
        sources_data = []

        async with session.post(
            f"{self.base_url}/api/search",
            json=body,
            timeout=aiohttp.ClientTimeout(total=max(self.timeout.total or 300, 300)),
        ) as resp:
            buffer = ""
            async for chunk in resp.content.iter_any():
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    evt_type = event.get("type", "")
                    if evt_type == "response":
                        message_parts.append(event.get("data", ""))
                    elif evt_type in ("sources", "searchResults"):
                        raw = event.get("data", [])
                        if isinstance(raw, list):
                            sources_data.extend(raw)
                    elif evt_type == "swarmAgentResult":
                        agent = event.get("data", {})
                        if agent.get("message"):
                            name = agent.get("agentName", "Agent")
                            message_parts.append(f"\n\n### {name}\n{agent['message']}")
                        if isinstance(agent.get("sources"), list):
                            sources_data.extend(agent["sources"])

        # Parse sources
        results = []
        seen = set()
        for src in sources_data:
            meta = src.get("metadata", {}) if isinstance(src, dict) else {}
            url = meta.get("url", "") or src.get("url", "")
            if url and url not in seen:
                seen.add(url)
                results.append(SearchResult(
                    title=meta.get("title", "") or src.get("title", ""),
                    url=url,
                    content=src.get("content", ""),
                ))

        return {
            "message": "".join(message_parts),
            "sources": results,
            "elapsed_s": round(time.monotonic() - t0, 2),
        }

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ── Usage Example ──────────────────────────────────────────────

async def main():
    client = PerplexicaClient("http://localhost:9123")

    # Simple search
    result = await client.search("Python async task queue patterns", mode="balanced")
    print(f"Answer: {result.get('message', '')[:500]}")

    # Swarm search (6 agents, comprehensive)
    deep = await client.swarm_search("distributed task queue architecture production-grade")
    print(f"\nSwarm result: {len(deep['sources'])} sources in {deep['elapsed_s']}s")
    print(f"Message preview: {deep['message'][:500]}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Requirements

```
aiohttp>=3.9
```

---

## API Reference

### Perplexica REST API

#### `GET /api/models`
Returns available model providers with their chat and embedding models.

#### `POST /api/search`
Main search endpoint. Accepts JSON body:

```json
{
  "chatModel": {
    "providerId": "provider-uuid",
    "key": "model-name"
  },
  "embeddingModel": {
    "providerId": "provider-uuid",
    "key": "embedding-model-name"
  },
  "optimizationMode": "speed|balanced|quality",
  "sources": ["web", "academic", "discussions"],
  "query": "your search query",
  "history": [],
  "stream": false,
  "swarmMode": false,
  "systemInstructions": "optional custom instructions"
}
```

**Response** (non-streaming):
```json
{
  "message": "synthesized answer with citations",
  "sources": [
    {
      "metadata": { "title": "...", "url": "..." },
      "content": "snippet..."
    }
  ]
}
```

**Response** (streaming / swarm mode): NDJSON stream with events:
- `{"type": "response", "data": "text chunk"}`
- `{"type": "sources", "data": [...]}`
- `{"type": "swarmAgentResult", "data": {"agentName": "...", "message": "...", "sources": [...]}}`

### SearxNG JSON API

#### `GET /search?q=query&format=json`

Query parameters:
- `q` — search query (required)
- `format` — `json` for API access (required)
- `categories` — comma-separated: `general`, `it`, `science`, `files`
- `engines` — comma-separated: `google`, `bing`, `arxiv`, `github`
- `language` — `en`, `de`, `fr`, etc.
- `time_range` — `day`, `week`, `month`, `year`
- `safesearch` — `0` (off), `1` (moderate), `2` (strict)

---

## Swarm Mode Details

When `swarmMode: true` is set in the search request, Perplexica launches **6 specialized agents** that each search and analyze the topic from a different angle:

| Agent | Role | What it finds |
|-------|------|---------------|
| Core Researcher | Main overview | Key concepts, definitions, primary sources |
| Technical Analyst | How it works | Implementation details, APIs, architecture |
| News Tracker | Latest developments | Recent articles, announcements, updates |
| Comparison Analyst | Alternatives | Competing solutions, pros/cons, benchmarks |
| Applications Expert | Real-world use | Case studies, production deployments |
| Community Analyst | User opinions | Forum posts, reviews, community insights |

All 6 agents run **in parallel**, and results are streamed back as `swarmAgentResult` events. The combined output typically contains 20-50 unique sources and a synthesized answer of 5,000-15,000 characters.

**Performance**: Swarm mode takes 2-5 minutes depending on the topic complexity and LLM speed.

---

## Troubleshooting

### SearxNG: "No results" or timeouts

1. **Check Tor**: `curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip`
2. **Check Redis**: `redis-cli -h localhost -p 6379 ping` → should return `PONG`
3. **Restart Tor container**: `docker restart searxng-tor`
4. **Check engine availability**: Visit `http://localhost:8080/stats` for engine health

### Perplexica: "Models not found"

1. **Check Ollama**: `ollama list` — models must be downloaded
2. **Check config.json**: Ensure `chatModels` and `embeddingModels` match what Ollama has
3. **Restart**: Copy config and restart Perplexica

### Perplexica: Search hangs or times out

1. **SearxNG must be running** before Perplexica starts
2. **Increase timeout**: Set `PERPLEXICA_TIMEOUT=300` (5 minutes for swarm mode)
3. **Check SearxNG directly**: `http://localhost:8080/search?q=test&format=json`

### CAPTCHA / Rate Limiting

The Tor proxy rotates IP addresses automatically. If you still get blocked:
1. Restart Tor: `docker restart searxng-tor`
2. Disable the blocking engine in `settings.yml` (`disabled: true`)
3. Wait 5-10 minutes (IP rotation)

### Port Conflicts

| Service    | Default Port | Change via |
|------------|-------------|------------|
| SearxNG    | 8080        | `settings.yml → server.port` |
| Perplexica | 9123        | `$env:PORT = "XXXX"` |
| Ollama     | 11434       | `$env:OLLAMA_HOST = "0.0.0.0:XXXX"` |
| Tor        | 9050        | Docker port mapping `-p XXXX:9050` |
| Redis      | 6379        | Docker port mapping `-p XXXX:6379` |

---

## Directory Structure

```
D:\Projects\
├── perplexica\                    # Perplexica repo
│   ├── .next\standalone\          # Built Next.js app
│   │   ├── server.js              # Entry point
│   │   └── data\config.json       # Runtime config (copied from parent)
│   └── data\config.json           # Source config
│
├── searxng\                       # SearxNG repo
│   └── data\
│       └── settings.yml           # SearxNG configuration
│
└── your-project\                  # Your application
    ├── .env                       # Environment variables
    └── perplexica_client.py       # Python client (copy from above)
```

---

## Quick Copy-Paste: Full Startup Script

Save as `start_research_stack.ps1`:

```powershell
# Start Docker containers
Write-Host "Starting Docker containers..."
docker start searxng-tor searxng-redis 2>$null
if ($LASTEXITCODE -ne 0) {
    docker run -d --name searxng-tor --restart unless-stopped -p 9050:9050 dperson/torproxy
    docker run -d --name searxng-redis --restart unless-stopped -p 6379:6379 redis:alpine
}

# Wait for containers
Start-Sleep 3

# Start SearxNG in background
Write-Host "Starting SearxNG on port 8080..."
$searxng = Start-Process -FilePath "cmd" -ArgumentList "/c cd D:\Projects\searxng && conda activate searxng && set SEARXNG_SETTINGS_PATH=D:\Projects\searxng\data\settings.yml && python -m searx.webapp" -PassThru -WindowStyle Minimized

Start-Sleep 5

# Start Perplexica in background
Write-Host "Starting Perplexica on port 9123..."
$perplexica = Start-Process -FilePath "cmd" -ArgumentList "/c cd D:\Projects\perplexica\.next\standalone && copy /Y D:\Projects\perplexica\data\config.json D:\Projects\perplexica\.next\standalone\data\config.json && set PORT=9123 && node server.js" -PassThru -WindowStyle Minimized

Start-Sleep 5

# Verify
Write-Host "`nVerifying services..."
try { $r = Invoke-RestMethod "http://localhost:8080/search?q=test&format=json"; Write-Host "  SearxNG: OK ($($r.results.Count) results)" } catch { Write-Host "  SearxNG: FAILED" }
try { $r = Invoke-RestMethod "http://localhost:9123/api/models"; Write-Host "  Perplexica: OK" } catch { Write-Host "  Perplexica: FAILED" }

Write-Host "`nResearch stack ready!"
```

---

## Cost

**$0.00** — entirely self-hosted:
- Ollama models run locally (free)
- SearxNG queries search engines directly (free)
- Tor proxy is free open-source software
- Redis is free open-source software
- Perplexica is free open-source software

Only cost is electricity + your hardware. Optional: add a cloud LLM provider (OpenRouter, Groq) for better synthesis quality.
