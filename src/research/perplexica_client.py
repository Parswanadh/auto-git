"""
Perplexica Search Client for Auto-GIT

Async client for Perplexica's REST API — an open-source AI-powered search engine
(https://github.com/ItzCrazyKns/Perplexica).  Perplexica runs locally via Docker,
combines SearxNG meta-search with LLM-powered RAG to return synthesised answers
with cited sources.

Key features for Auto-GIT:
  • Web + academic + discussion search modes
  • quality / balanced / speed optimisation
  • Parallel queries via asyncio.gather
  • Automatic provider/model discovery
  • Structured source extraction (title + URL + snippet)

Usage:
    client = PerplexicaClient("http://localhost:3000")
    results = await client.research("multi-tenant SQLAlchemy patterns")

Docker quick-start:
    docker run -d -p 3000:3000 \\
      -v perplexica-data:/home/perplexica/data \\
      --name perplexica itzcrazykns1337/perplexica:latest
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PerplexicaSource:
    """A single search-result source returned by Perplexica."""
    title: str
    url: str
    content: str  # snippet

    def to_dict(self) -> dict:
        return {"title": self.title, "url": self.url, "content": self.content}


@dataclass
class PerplexicaResult:
    """The full result of a Perplexica search query."""
    query: str
    message: str                          # synthesised answer
    sources: List[PerplexicaSource]       # cited sources
    mode: str = "quality"                 # speed | balanced | quality
    source_types: List[str] = field(default_factory=lambda: ["web"])
    elapsed_s: float = 0.0

    @property
    def source_count(self) -> int:
        return len(self.sources)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "message": self.message,
            "sources": [s.to_dict() for s in self.sources],
            "mode": self.mode,
            "source_types": self.source_types,
            "elapsed_s": round(self.elapsed_s, 2),
        }


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class PerplexicaClient:
    """
    Async HTTP client for a self-hosted Perplexica instance.

    Lifecycle:
        client = PerplexicaClient(base_url)
        await client.ensure_ready()          # discover providers & models
        result = await client.search(...)    # run a single search
        results = await client.research(...) # run parallel multi-source search
        await client.close()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9123",
        *,
        chat_provider_name: str | None = None,
        chat_model_key: str | None = None,
        embedding_provider_name: str | None = None,
        embedding_model_key: str | None = None,
        default_mode: str = "quality",
        timeout_s: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout_s)
        self._session: Optional[aiohttp.ClientSession] = None

        # Provider/model overrides (resolved lazily)
        self._chat_provider_name = chat_provider_name
        self._chat_model_key = chat_model_key
        self._embedding_provider_name = embedding_provider_name
        self._embedding_model_key = embedding_model_key
        self.default_mode = default_mode

        # Resolved after ensure_ready()
        self._chat_model: Optional[Dict[str, str]] = None    # {providerId, key}
        self._embedding_model: Optional[Dict[str, str]] = None
        self._providers: List[dict] = []
        self._ready = False

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Health / readiness
    # ------------------------------------------------------------------

    async def is_available(self) -> bool:
        """Check if Perplexica is reachable."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/providers", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def ensure_ready(self) -> bool:
        """
        Discover providers and pick the best chat + embedding model.
        Call once before making search requests.
        Returns True if ready.
        """
        if self._ready:
            return True

        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/providers") as resp:
                if resp.status != 200:
                    logger.warning(f"Perplexica /api/providers returned {resp.status}")
                    return False
                data = await resp.json()
                self._providers = data.get("providers", [])
        except Exception as e:
            logger.warning(f"Perplexica not available at {self.base_url}: {e}")
            return False

        if not self._providers:
            logger.warning("Perplexica returned zero providers")
            return False

        # Resolve chat model
        self._chat_model = self._resolve_model(
            self._providers,
            self._chat_provider_name,
            self._chat_model_key,
            model_type="chat",
        )
        # Resolve embedding model
        self._embedding_model = self._resolve_model(
            self._providers,
            self._embedding_provider_name,
            self._embedding_model_key,
            model_type="embedding",
        )

        if not self._chat_model:
            logger.warning("Perplexica: no suitable chat model found")
            return False
        if not self._embedding_model:
            logger.warning("Perplexica: no suitable embedding model found")
            return False

        logger.info(
            f"Perplexica ready — chat: {self._chat_model}, "
            f"embedding: {self._embedding_model}, "
            f"providers: {len(self._providers)}"
        )
        self._ready = True
        return True

    # ------------------------------------------------------------------
    # Model resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_model(
        providers: List[dict],
        preferred_provider: str | None,
        preferred_key: str | None,
        model_type: str = "chat",
    ) -> Optional[Dict[str, str]]:
        """Find the best matching provider+model from the providers list."""
        models_field = "chatModels" if model_type == "chat" else "embeddingModels"

        # 1. Try exact match if both specified
        if preferred_provider and preferred_key:
            for p in providers:
                if p["name"].lower() == preferred_provider.lower():
                    for m in p.get(models_field, []):
                        if m["key"] == preferred_key:
                            return {"providerId": p["id"], "key": m["key"]}

        # 2. Try matching just the model key across all providers
        if preferred_key:
            for p in providers:
                for m in p.get(models_field, []):
                    if m["key"] == preferred_key:
                        return {"providerId": p["id"], "key": m["key"]}

        # 3. Try matching by provider name, pick first model
        if preferred_provider:
            for p in providers:
                if p["name"].lower() == preferred_provider.lower():
                    models = p.get(models_field, [])
                    if models:
                        return {"providerId": p["id"], "key": models[0]["key"]}

        # 4. Fallback: first provider with any model of this type
        # Prefer Ollama (free, local) > Groq > OpenAI
        priority = ["ollama", "groq", "openai", "gemini", "anthropic"]
        for pref_name in priority:
            for p in providers:
                if pref_name in p["name"].lower():
                    models = p.get(models_field, [])
                    if models:
                        return {"providerId": p["id"], "key": models[0]["key"]}

        # 5. True fallback: literally any provider
        for p in providers:
            models = p.get(models_field, [])
            if models:
                return {"providerId": p["id"], "key": models[0]["key"]}

        return None

    # ------------------------------------------------------------------
    # Core search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        sources: List[str] | None = None,
        mode: str | None = None,
        history: List[Tuple[str, str]] | None = None,
        system_instructions: str | None = None,
        stream: bool = False,
    ) -> PerplexicaResult:
        """
        Run a single Perplexica search query.

        Args:
            query: The search query.
            sources: List of source types — "web", "academic", "discussions".
            mode: Optimisation mode — "speed", "balanced", "quality".
            history: Conversation history as [(role, message), ...].
            system_instructions: Custom instructions for the AI.
            stream: Whether to use streaming (not supported yet, reserved).

        Returns:
            PerplexicaResult with synthesised answer and sources.
        """
        if not self._ready:
            ready = await self.ensure_ready()
            if not ready:
                raise RuntimeError(
                    f"Perplexica not ready at {self.base_url}. "
                    "Is the Docker container running?"
                )

        sources = sources or ["web"]
        mode = mode or self.default_mode
        history = history or []

        body = {
            "chatModel": self._chat_model,
            "embeddingModel": self._embedding_model,
            "optimizationMode": mode,
            "sources": sources,
            "query": query,
            "history": [list(pair) for pair in history],
            "stream": False,  # we'll parse non-streaming response
        }
        if system_instructions:
            body["systemInstructions"] = system_instructions

        t0 = time.monotonic()
        session = await self._get_session()

        try:
            async with session.post(
                f"{self.base_url}/api/search",
                json=body,
                timeout=aiohttp.ClientTimeout(total=max(self._timeout.total or 120, 120)),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning(f"Perplexica search failed ({resp.status}): {text[:500]}")
                    return PerplexicaResult(
                        query=query,
                        message=f"[Perplexica error {resp.status}]",
                        sources=[],
                        mode=mode,
                        source_types=sources,
                        elapsed_s=time.monotonic() - t0,
                    )

                data = await resp.json()
        except asyncio.TimeoutError:
            logger.warning(f"Perplexica search timed out for: {query[:80]}")
            return PerplexicaResult(
                query=query, message="[timeout]", sources=[],
                mode=mode, source_types=sources,
                elapsed_s=time.monotonic() - t0,
            )
        except Exception as e:
            logger.warning(f"Perplexica search error: {e}")
            return PerplexicaResult(
                query=query, message=f"[error: {e}]", sources=[],
                mode=mode, source_types=sources,
                elapsed_s=time.monotonic() - t0,
            )

        elapsed = time.monotonic() - t0

        # Parse sources
        raw_sources = data.get("sources", [])
        parsed_sources = []
        for src in raw_sources:
            meta = src.get("metadata", {})
            parsed_sources.append(PerplexicaSource(
                title=meta.get("title", ""),
                url=meta.get("url", ""),
                content=src.get("content", ""),
            ))

        return PerplexicaResult(
            query=query,
            message=data.get("message", ""),
            sources=parsed_sources,
            mode=mode,
            source_types=sources,
            elapsed_s=elapsed,
        )

    # ------------------------------------------------------------------
    # High-level: parallel multi-source research
    # ------------------------------------------------------------------

    async def research(
        self,
        topic: str,
        *,
        queries: List[str] | None = None,
        mode: str = "quality",
        include_academic: bool = True,
        include_discussions: bool = False,
        system_instructions: str | None = None,
        max_parallel: int = 8,
    ) -> Dict[str, Any]:
        """
        Run a comprehensive research session on a topic.

        Generates multiple search queries from the topic and runs them
        in parallel across web + academic sources.

        Args:
            topic: The research topic / project idea.
            queries: Optional list of pre-generated search queries.
                     If None, auto-generates from the topic.
            mode: "quality" (deeper) or "speed" (faster).
            include_academic: Also search academic sources.
            include_discussions: Also search discussion forums.
            system_instructions: Custom instructions.
            max_parallel: Max concurrent searches.

        Returns:
            Dict with keys: summary, web_results, academic_results,
            all_sources, query_count, elapsed_s
        """
        if not self._ready:
            ready = await self.ensure_ready()
            if not ready:
                return {
                    "summary": "[Perplexica not available]",
                    "web_results": [],
                    "academic_results": [],
                    "all_sources": [],
                    "query_count": 0,
                    "elapsed_s": 0,
                    "error": f"Perplexica not reachable at {self.base_url}",
                }

        t0 = time.monotonic()

        # Build query list
        if not queries:
            queries = self._generate_research_queries(topic)

        # Build search tasks
        tasks = []
        for q in queries:
            # Web search for each query
            tasks.append(self.search(
                q, sources=["web"], mode=mode,
                system_instructions=system_instructions or self._research_instructions(),
            ))
            # Academic search (if enabled) — for first 4 queries
            if include_academic and len(tasks) < max_parallel * 4:
                tasks.append(self.search(
                    q, sources=["academic"], mode=mode,
                    system_instructions=system_instructions or self._research_instructions(),
                ))
            # Discussion search
            if include_discussions and len(tasks) < max_parallel * 5:
                tasks.append(self.search(
                    q, sources=["discussions"], mode=mode,
                    system_instructions=system_instructions or self._research_instructions(),
                ))

        # Run with concurrency limit
        semaphore = asyncio.Semaphore(max_parallel)

        async def _limited(task):
            async with semaphore:
                return await task

        results: List[PerplexicaResult] = await asyncio.gather(
            *[_limited(t) for t in tasks],
            return_exceptions=True,
        )

        # Process results
        web_results = []
        academic_results = []
        discussion_results = []
        all_sources: List[dict] = []
        seen_urls: set = set()

        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Perplexica parallel search error: {r}")
                continue
            if not isinstance(r, PerplexicaResult):
                continue

            entry = {
                "query": r.query,
                "answer": r.message,
                "source_count": r.source_count,
                "elapsed_s": r.elapsed_s,
                "sources": [s.to_dict() for s in r.sources],
            }

            if "academic" in r.source_types:
                academic_results.append(entry)
            elif "discussions" in r.source_types:
                discussion_results.append(entry)
            else:
                web_results.append(entry)

            # Deduplicate sources by URL
            for s in r.sources:
                if s.url and s.url not in seen_urls:
                    seen_urls.add(s.url)
                    all_sources.append(s.to_dict())

        elapsed = time.monotonic() - t0

        # Build combined summary
        summaries = []
        for r in results:
            if isinstance(r, PerplexicaResult) and r.message and not r.message.startswith("["):
                summaries.append(r.message)
        combined_summary = "\n\n---\n\n".join(summaries) if summaries else "[No results]"

        return {
            "summary": combined_summary,
            "web_results": web_results,
            "academic_results": academic_results,
            "discussion_results": discussion_results,
            "all_sources": all_sources,
            "unique_source_count": len(all_sources),
            "query_count": len(queries),
            "search_count": len(tasks),
            "elapsed_s": round(elapsed, 2),
        }

    # ------------------------------------------------------------------
    # Swarm mode: 6-agent parallel research
    # ------------------------------------------------------------------

    async def swarm_search(
        self,
        query: str,
        *,
        sources: List[str] | None = None,
        mode: str | None = None,
        system_instructions: str | None = None,
    ) -> PerplexicaResult:
        """
        Run a swarm-mode search with 6 specialized agents in parallel.

        Perplexica's swarm launches these agents concurrently:
          1. Core Researcher — main overview
          2. Technical Analyst — how it works, implementation
          3. News Tracker — latest developments
          4. Comparison Analyst — alternatives & comparisons
          5. Applications Expert — real-world use cases
          6. Community Analyst — user opinions & experiences

        Results are synthesized into a single comprehensive answer.
        Swarm mode uses streaming internally, so we parse the SSE stream.
        """
        if not self._ready:
            ready = await self.ensure_ready()
            if not ready:
                raise RuntimeError(f"Perplexica not ready at {self.base_url}")

        sources = sources or ["web", "academic", "discussions"]
        mode = mode or self.default_mode

        body = {
            "chatModel": self._chat_model,
            "embeddingModel": self._embedding_model,
            "optimizationMode": mode,
            "sources": sources,
            "query": query,
            "history": [],
            "stream": True,  # Swarm mode requires streaming
            "swarmMode": True,
        }
        if system_instructions:
            body["systemInstructions"] = system_instructions

        t0 = time.monotonic()
        session = await self._get_session()
        message_parts = []
        sources_data = []

        try:
            async with session.post(
                f"{self.base_url}/api/search",
                json=body,
                timeout=aiohttp.ClientTimeout(total=max(self._timeout.total or 300, 300)),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning(f"Perplexica swarm failed ({resp.status}): {text[:500]}")
                    return PerplexicaResult(
                        query=query, message=f"[Perplexica swarm error {resp.status}]",
                        sources=[], mode=mode, source_types=sources,
                        elapsed_s=time.monotonic() - t0,
                    )

                # Parse SSE/NDJSON stream
                buffer = ""
                async for chunk_bytes in resp.content.iter_any():
                    buffer += chunk_bytes.decode("utf-8", errors="replace")
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
                        elif evt_type == "sources" or evt_type == "searchResults":
                            raw = event.get("data", [])
                            if isinstance(raw, list):
                                sources_data.extend(raw)
                        elif evt_type == "swarmAgentResult":
                            # Individual agent results
                            agent_data = event.get("data", {})
                            agent_msg = agent_data.get("message", "")
                            if agent_msg:
                                agent_name = agent_data.get("agentName", "Agent")
                                message_parts.append(f"\n\n### {agent_name}\n{agent_msg}")
                            agent_sources = agent_data.get("sources", [])
                            if isinstance(agent_sources, list):
                                sources_data.extend(agent_sources)

        except asyncio.TimeoutError:
            logger.warning(f"Perplexica swarm timed out for: {query[:80]}")
            # Return whatever we collected so far
        except Exception as e:
            logger.warning(f"Perplexica swarm error: {e}")

        elapsed = time.monotonic() - t0
        full_message = "".join(message_parts)

        # Parse sources
        parsed_sources = []
        seen_urls = set()
        for src in sources_data:
            meta = src.get("metadata", {}) if isinstance(src, dict) else {}
            url = meta.get("url", "") or src.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                parsed_sources.append(PerplexicaSource(
                    title=meta.get("title", "") or src.get("title", ""),
                    url=url,
                    content=src.get("content", ""),
                ))

        logger.info(
            f"Perplexica swarm complete: {len(parsed_sources)} sources, "
            f"{len(full_message)} chars, {elapsed:.1f}s"
        )

        return PerplexicaResult(
            query=query,
            message=full_message,
            sources=parsed_sources,
            mode=mode,
            source_types=sources,
            elapsed_s=elapsed,
        )

    # ------------------------------------------------------------------
    # High-level: swarm + parallel research (best quality)
    # ------------------------------------------------------------------

    async def deep_research(
        self,
        topic: str,
        *,
        mode: str = "quality",
        system_instructions: str | None = None,
    ) -> Dict[str, Any]:
        """
        Maximum-depth research using swarm mode + supplementary queries.

        1. Runs swarm search (6 agents in parallel) for comprehensive coverage
        2. Runs targeted follow-up queries for academic papers and implementations

        This is the recommended method for Auto-GIT pipeline research.
        """
        if not self._ready:
            ready = await self.ensure_ready()
            if not ready:
                return {
                    "summary": "[Perplexica not available]",
                    "web_results": [], "academic_results": [],
                    "all_sources": [], "query_count": 0, "elapsed_s": 0,
                    "error": f"Perplexica not reachable at {self.base_url}",
                }

        t0 = time.monotonic()
        instructions = system_instructions or self._research_instructions()

        # 1. Swarm search — 6 agents cover the topic broadly
        swarm_result = await self.swarm_search(
            topic,
            sources=["web", "academic", "discussions"],
            mode=mode,
            system_instructions=instructions,
        )

        # 2. Targeted follow-ups — dynamically generated queries
        #    Run sequentially with delays to avoid rate-limiting SearxNG engines
        follow_up_queries = self._generate_research_queries(topic)
        follow_ups: List[PerplexicaResult] = []

        # Use queries [1:7] (skip original, take up to 6 dynamic queries)
        for q in follow_up_queries[1:7]:
            try:
                await asyncio.sleep(1)  # Throttle: 1s between queries (Tor handles rate limits)
                r = await self.search(
                    q, sources=["web"], mode="speed",
                    system_instructions=instructions,
                )
                follow_ups.append(r)
            except Exception as e:
                logger.warning(f"Follow-up query failed: {e}")
                continue

        # Add 3 academic-specific queries
        for aq in follow_up_queries[1:4]:
            try:
                await asyncio.sleep(1)
                r = await self.search(
                    aq, sources=["academic"], mode="speed",
                    system_instructions=instructions,
                )
                follow_ups.append(r)
            except Exception as e:
                logger.warning(f"Academic follow-up failed: {e}")

        # 3. Merge everything
        all_sources: List[dict] = []
        seen_urls: set = set()

        # Add swarm sources
        for s in swarm_result.sources:
            if s.url and s.url not in seen_urls:
                seen_urls.add(s.url)
                all_sources.append(s.to_dict())

        # Categorize
        web_results = []
        academic_results = []
        implementations = []

        # Process swarm result
        for s in swarm_result.sources:
            entry = s.to_dict()
            url_lower = s.url.lower()
            if "arxiv" in url_lower or "scholar" in url_lower or "pubmed" in url_lower:
                academic_results.append({
                    "title": s.title, "url": s.url,
                    "summary": s.content[:1500], "relevance_score": 0.9,
                })
            elif "github.com" in url_lower or "gitlab.com" in url_lower:
                implementations.append({
                    "title": s.title, "url": s.url,
                    "description": s.content[:600], "source": "perplexica_swarm",
                })
            else:
                web_results.append({
                    "title": s.title, "url": s.url,
                    "snippet": s.content[:800], "relevance_score": 0.85,
                })

        # Process follow-up results
        for r in follow_ups:
            if not isinstance(r, PerplexicaResult):
                continue
            for s in r.sources:
                if s.url and s.url not in seen_urls:
                    seen_urls.add(s.url)
                    all_sources.append(s.to_dict())
                    url_lower = s.url.lower()
                    if "arxiv" in url_lower or "scholar" in url_lower:
                        academic_results.append({
                            "title": s.title, "url": s.url,
                            "summary": s.content[:1500], "relevance_score": 0.85,
                        })
                    elif "github.com" in url_lower or "gitlab.com" in url_lower:
                        implementations.append({
                            "title": s.title, "url": s.url,
                            "description": s.content[:600], "source": "perplexica_followup",
                        })

        # Build insights from swarm + follow-ups
        insights = []
        if swarm_result.message and not swarm_result.message.startswith("["):
            # Split swarm message into chunks per agent
            for chunk in swarm_result.message.split("### "):
                chunk = chunk.strip()
                if chunk:
                    insights.append(chunk[:2000])
        for r in follow_ups:
            if isinstance(r, PerplexicaResult) and r.message and not r.message.startswith("["):
                insights.append(r.message[:1500])

        elapsed = time.monotonic() - t0

        return {
            "summary": swarm_result.message[:10000] if swarm_result.message else "[No results]",
            "web_results": web_results,
            "academic_results": academic_results,
            "discussion_results": [],
            "implementations": implementations,
            "all_sources": all_sources,
            "insights": insights[:30],
            "unique_source_count": len(all_sources),
            "query_count": 1 + len(follow_ups),
            "search_count": 1 + len(follow_ups),
            "swarm_agents": 6,
            "elapsed_s": round(elapsed, 2),
        }

    # ------------------------------------------------------------------
    # Query generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_research_queries(topic: str) -> List[str]:
        """
        Dynamically generate diverse search queries from a topic.
        Extracts key concepts and creates targeted queries for different
        research dimensions: architecture, implementation, comparison,
        academic papers, and community discussion.
        """
        topic_clean = topic.strip()
        if len(topic_clean) > 300:
            topic_clean = topic_clean[:300]

        # Extract first meaningful line as the core subject
        first_line = topic_clean.split("\n")[0].strip()[:120]

        # Extract significant words (3+ chars, not common stop words)
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "are",
            "was", "will", "can", "has", "have", "been", "but", "not",
            "you", "all", "they", "into", "also", "each", "use", "using",
            "build", "create", "make", "how", "what", "when", "where",
            "should", "would", "could", "need", "want", "like",
        }
        words = [
            w for w in topic_clean.lower().split()
            if len(w) >= 3 and w not in stop_words
        ]
        # Deduplicate while preserving order
        seen = set()
        key_terms = []
        for w in words:
            clean = w.strip(".,;:!?()[]{}\"'`")
            if clean and clean not in seen:
                seen.add(clean)
                key_terms.append(clean)

        # Build dynamic queries based on extracted concepts
        queries = [topic_clean]  # original always first

        # Architecture & best practices
        if key_terms:
            arch_terms = " ".join(key_terms[:5])
            queries.append(f"{arch_terms} architecture best practices production 2025 2026")

        # How-to / tutorial
        queries.append(f"how to implement {first_line}")

        # GitHub implementations
        queries.append(f"github open source {first_line}")

        # Academic / research papers
        if len(key_terms) >= 2:
            academic_terms = " ".join(key_terms[:4])
            queries.append(f"{academic_terms} research paper arxiv 2024 2025")

        # Common pitfalls / troubleshooting
        queries.append(f"{first_line} common mistakes pitfalls solutions")

        # Comparison / alternatives
        if len(key_terms) >= 2:
            queries.append(f"{key_terms[0]} vs alternatives comparison {key_terms[1]}")

        return queries[:7]

    @staticmethod
    def _research_instructions() -> str:
        """System instructions optimised for Auto-GIT research."""
        return (
            "You are a research assistant for a code generation system. "
            "Your goal is to find implementation patterns, best practices, "
            "architecture designs, and open-source examples. "
            "Focus on: 1) Production-ready patterns, 2) Common pitfalls, "
            "3) Library/framework recommendations with version info, "
            "4) GitHub repos with working code. "
            "Be specific — cite exact package names, versions, and URLs. "
            "Prefer results from 2024-2026."
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self):
        await self.ensure_ready()
        return self

    async def __aexit__(self, *args):
        await self.close()


# ---------------------------------------------------------------------------
# Convenience function for one-shot research
# ---------------------------------------------------------------------------

async def perplexica_research(
    topic: str,
    base_url: str = "http://localhost:9123",
    mode: str = "quality",
    **kwargs,
) -> Dict[str, Any]:
    """
    One-shot research using Perplexica.

    >>> results = await perplexica_research("multi-tenant SQLAlchemy patterns")
    >>> print(results["summary"])
    """
    async with PerplexicaClient(base_url) as client:
        return await client.research(topic, mode=mode, **kwargs)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    async def _test():
        url = os.environ.get("PERPLEXICA_URL", "http://localhost:3000")
        topic = " ".join(sys.argv[1:]) or "production-grade Telegram bot with aiogram and SQLAlchemy"

        print(f"Testing Perplexica at {url}")
        print(f"Topic: {topic}\n")

        client = PerplexicaClient(url)
        available = await client.is_available()
        print(f"Available: {available}")

        if not available:
            print("Perplexica is not running. Start it with:")
            print("  docker run -d -p 3000:3000 -v perplexica-data:/home/perplexica/data --name perplexica itzcrazykns1337/perplexica:latest")
            return

        results = await client.research(topic)
        print(f"\nQueries: {results['query_count']}")
        print(f"Sources: {results['unique_source_count']}")
        print(f"Elapsed: {results['elapsed_s']}s")
        print(f"\n{'='*60}")
        print("SUMMARY (first 1000 chars):")
        print(results["summary"][:1000])
        print(f"\n{'='*60}")
        print("SOURCES:")
        for s in results["all_sources"][:10]:
            print(f"  - {s['title'][:80]}")
            print(f"    {s['url']}")

        await client.close()

    asyncio.run(_test())
