"""
SOTA Research Engine — Auto-GIT
================================

A STORM/GPT-Researcher-inspired research system that combines:

1. **Multi-Perspective Decomposition** (STORM):
   - Discover N relevant perspectives on the topic
   - Simulate expert conversations from each angle
   - Generate deep follow-up questions per perspective

2. **Plan-and-Solve Parallel Execution** (GPT-Researcher):
   - Decompose topic into sub-questions
   - Execute all searches in parallel
   - Aggregate with Reciprocal Rank Fusion

3. **Iterative Gap Analysis**:
   - After each research round, identify coverage gaps
   - Generate targeted queries to fill gaps
   - Continue until completeness threshold met

4. **Compound Multi-Engine Search**:
   - Perplexica (swarm + follow-up)
   - SearXNG (meta-search across Google/Bing/DDG/arXiv/GitHub)
   - arXiv direct API
   - compound-beta LLM (web-grounded)
   - All engines searched in parallel, results fused

5. **Persistent Research Memory** (ChromaDB):
   - Store all findings as embeddings
   - Before new research, recall related prior knowledge
   - Only research the gaps (saves 40-60% search time)
   - Cross-session knowledge accumulation

6. **Hierarchical Mind Map**:
   - Organize findings into a concept tree
   - Track coverage per branch
   - Detect and fill blind spots

Architecture:
    SOTAResearcher
    ├── PerspectiveEngine      — STORM-style perspective discovery + conversations
    ├── QueryPlanner           — Decomposes topic into sub-questions
    ├── CompoundSearcher       — Parallel multi-engine search
    ├── ResultFuser            — Reciprocal Rank Fusion + dedup
    ├── GapAnalyzer            — Identifies missing coverage
    ├── ResearchMemory         — ChromaDB persistent memory
    └── MindMapBuilder         — Hierarchical concept organization
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def _env_flag_enabled(value: str, default: bool = False) -> bool:
    raw = (value or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def _local_models_enabled() -> bool:
    if _env_flag_enabled(os.environ.get("AUTOGIT_DISABLE_LOCAL_MODELS", ""), default=False):
        return False
    override = os.environ.get("AUTOGIT_LOCAL_MODELS_ENABLED", "")
    if override.strip():
        return _env_flag_enabled(override, default=True)
    # Safety default: cloud-only unless explicitly enabled.
    return False


def _perplexica_enabled() -> bool:
    if not _env_flag_enabled(os.environ.get("PERPLEXICA_ENABLED", "true"), default=True):
        return False
    # If local models are disabled and Perplexica is configured with Ollama, skip it.
    chat_provider = os.environ.get("PERPLEXICA_CHAT_PROVIDER", "").strip().lower()
    embedding_provider = os.environ.get("PERPLEXICA_EMBEDDING_PROVIDER", "").strip().lower()
    if not _local_models_enabled() and (
        chat_provider in ("", "ollama") or embedding_provider in ("", "ollama")
    ):
        return False
    return True

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA STRUCTURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Source:
    """A single research source (paper, web page, repo, etc.)."""
    title: str
    url: str
    content: str  # snippet or summary
    source_type: str = "web"  # "academic", "web", "code", "discussion"
    engine: str = ""  # which search engine found it
    relevance_score: float = 0.0
    quality_score: float = 0.0
    fused_rank: float = 0.0
    citation_verified: Optional[bool] = None
    perspective: str = ""  # which perspective discovered it

    @property
    def content_hash(self) -> str:
        return hashlib.md5(self.content[:500].encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "title": self.title, "url": self.url,
            "content": self.content[:2000],
            "source_type": self.source_type, "engine": self.engine,
            "relevance_score": round(self.relevance_score, 3),
            "quality_score": round(self.quality_score, 3),
            "fused_rank": round(self.fused_rank, 3),
            "citation_verified": self.citation_verified,
            "perspective": self.perspective,
        }


@dataclass
class Perspective:
    """A research perspective (STORM-style)."""
    name: str
    description: str
    questions: List[str] = field(default_factory=list)
    findings: List[Source] = field(default_factory=list)
    conversation: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class MindMapNode:
    """A node in the hierarchical research mind map."""
    concept: str
    facts: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)  # URLs
    coverage_score: float = 0.0  # 0-1, how well this concept is covered
    children: List["MindMapNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "facts": self.facts[:10],
            "sources": self.sources[:5],
            "coverage": round(self.coverage_score, 2),
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class ResearchReport:
    """The final output of a SOTA research session."""
    topic: str
    perspectives: List[Perspective]
    mind_map: MindMapNode
    all_sources: List[Source]
    summary: str
    key_findings: List[str]
    open_problems: List[str]
    implementations: List[Dict[str, str]]
    benchmarks: List[Dict[str, str]]
    gaps_remaining: List[str]
    iterations: int
    total_queries: int
    total_sources: int
    unique_sources: int
    elapsed_s: float
    memory_hits: int = 0  # how many results came from prior memory

    def to_research_context(self) -> Dict[str, Any]:
        """Convert to the research_context format expected by the pipeline."""
        papers = []
        web_results = []
        impls = []
        for s in self.all_sources:
            entry = s.to_dict()
            if s.source_type == "academic":
                papers.append({
                    "title": s.title, "url": s.url,
                    "summary": s.content[:1500],
                    "relevance_score": s.relevance_score,
                    "citation_verified": s.citation_verified,
                })
            elif s.source_type == "code":
                impls.append({
                    "title": s.title, "url": s.url,
                    "description": s.content[:600],
                    "source": s.engine,
                })
            else:
                web_results.append({
                    "title": s.title, "url": s.url,
                    "snippet": s.content[:800],
                    "relevance_score": s.relevance_score,
                })

        return {
            "papers": papers,
            "web_results": web_results,
            "implementations": impls + self.implementations,
            "search_timestamp": datetime.now().isoformat(),
            "sota_research": {
                "summary": self.summary[:8000],
                "key_findings": self.key_findings,
                "open_problems": self.open_problems,
                "benchmarks": self.benchmarks,
                "mind_map": self.mind_map.to_dict(),
                "perspectives_used": [p.name for p in self.perspectives],
                "iterations": self.iterations,
                "total_queries": self.total_queries,
                "unique_sources": self.unique_sources,
                "memory_hits": self.memory_hits,
                "gaps_remaining": self.gaps_remaining,
                "elapsed_s": self.elapsed_s,
            },
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PERSISTENT RESEARCH MEMORY (ChromaDB)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ResearchMemory:
    """
    Persistent vector-based research memory.

    Stores findings across sessions so the system can:
    - Recall related prior research before starting
    - Avoid re-searching topics already covered
    - Build cumulative knowledge over time
    """

    def __init__(self, db_path: str = "data/research_memory"):
        self._db_path = Path(db_path)
        self._db_path.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None
        self._ready = False

    def _ensure_ready(self):
        if self._ready:
            return True
        try:
            import chromadb
            from chromadb.config import Settings
            self._client = chromadb.PersistentClient(
                path=str(self._db_path),
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="research_findings",
                metadata={"hnsw:space": "cosine"},
            )
            self._ready = True
            logger.info(f"Research memory ready: {self._collection.count()} stored findings")
            return True
        except ImportError:
            logger.warning("chromadb not installed — research memory disabled")
            return False
        except Exception as e:
            logger.warning(f"Research memory init failed: {e}")
            return False

    def recall(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Recall related prior findings."""
        if not self._ensure_ready():
            return []
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, self._collection.count() or 1),
            )
            findings = []
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 1.0
                findings.append({
                    "id": doc_id,
                    "content": results["documents"][0][i],
                    "relevance": round(1.0 - dist, 3),  # cosine distance → similarity
                    "topic": meta.get("topic", ""),
                    "source_url": meta.get("source_url", ""),
                    "source_type": meta.get("source_type", ""),
                    "stored_at": meta.get("stored_at", ""),
                })
            return [f for f in findings if f["relevance"] > 0.3]
        except Exception as e:
            logger.warning(f"Memory recall failed: {e}")
            return []

    def store(self, sources: List[Source], topic: str):
        """Store new research findings for future recall."""
        if not self._ensure_ready():
            return
        try:
            docs, ids, metas = [], [], []
            for s in sources:
                if not s.content or len(s.content) < 20:
                    continue
                doc_id = hashlib.md5(f"{s.url}:{s.content[:200]}".encode()).hexdigest()
                docs.append(f"{s.title}\n{s.content[:1500]}")
                ids.append(doc_id)
                metas.append({
                    "topic": topic[:200],
                    "source_url": s.url[:500],
                    "source_type": s.source_type,
                    "engine": s.engine,
                    "relevance_score": s.relevance_score,
                    "stored_at": datetime.now().isoformat(),
                })
            if docs:
                # Upsert to avoid duplicates
                self._collection.upsert(documents=docs, ids=ids, metadatas=metas)
                logger.info(f"Stored {len(docs)} findings to research memory (total: {self._collection.count()})")
        except Exception as e:
            logger.warning(f"Memory store failed: {e}")

    @property
    def count(self) -> int:
        if not self._ensure_ready():
            return 0
        return self._collection.count()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESULT FUSION (Reciprocal Rank Fusion)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def reciprocal_rank_fusion(
    ranked_lists: List[List[Source]],
    k: int = 60,
) -> List[Source]:
    """
    Merge multiple ranked result lists into one using RRF.

    RRF(d) = Σ 1/(k + rank(d)) for each list containing d.

    This is the standard technique for fusing results from multiple
    search engines (used by Elasticsearch, Pinecone, etc.).
    """
    scores: Dict[str, float] = defaultdict(float)
    source_map: Dict[str, Source] = {}

    for ranked_list in ranked_lists:
        for rank, source in enumerate(ranked_list):
            key = source.url or source.content_hash
            scores[key] += 1.0 / (k + rank + 1)
            # Keep the version with highest individual relevance
            if key not in source_map or source.relevance_score > source_map[key].relevance_score:
                source_map[key] = source

    # Sort by fused score descending
    sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    result = []
    for key in sorted_keys:
        src = source_map[key]
        src.fused_rank = scores[key]
        result.append(src)
    return result


def deduplicate_sources(sources: List[Source]) -> List[Source]:
    """Remove duplicates by URL and content hash."""
    seen_urls: Set[str] = set()
    seen_hashes: Set[str] = set()
    unique = []
    for s in sources:
        if s.url and s.url in seen_urls:
            continue
        ch = s.content_hash
        if ch in seen_hashes:
            continue
        if s.url:
            seen_urls.add(s.url)
        seen_hashes.add(ch)
        unique.append(s)
    return unique


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUALITY SCORING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_REPUTABLE_DOMAINS = {
    "arxiv.org", "github.com", "gitlab.com", "scholar.google.com",
    "semanticscholar.org", "openreview.net", "huggingface.co",
    "pytorch.org", "tensorflow.org", "proceedings.mlr.press",
    "aclanthology.org", "neurips.cc", "icml.cc",
}


def score_source_quality(source: Source) -> float:
    """Score a source 0-1 based on domain reputation, content length, etc."""
    score = 0.0
    # Domain reputation (0.4 weight)
    url_lower = source.url.lower() if source.url else ""
    for domain in _REPUTABLE_DOMAINS:
        if domain in url_lower:
            score += 0.4
            break
    else:
        if any(tld in url_lower for tld in (".edu", ".gov", ".ac.")):
            score += 0.3

    # Content length (0.3 weight)
    content_len = len(source.content)
    if content_len > 500:
        score += 0.3
    elif content_len > 200:
        score += 0.2
    elif content_len > 50:
        score += 0.1

    # Title quality (0.2 weight)
    if source.title and len(source.title) > 10:
        score += 0.2
    elif source.title:
        score += 0.1

    # Has URL (0.1 weight)
    if source.url:
        score += 0.1

    return min(score, 1.0)


def classify_source_type(url: str) -> str:
    """Classify a URL into source type."""
    url_lower = (url or "").lower()
    if any(d in url_lower for d in ("arxiv.org", "scholar.google", "semanticscholar",
                                      "openreview.net", "proceedings.mlr", "aclanthology",
                                      "pubmed", "ieee.org", "acm.org")):
        return "academic"
    if any(d in url_lower for d in ("github.com", "gitlab.com", "huggingface.co",
                                      "pypi.org", "npmjs.com")):
        return "code"
    if any(d in url_lower for d in ("reddit.com", "stackoverflow.com", "news.ycombinator",
                                      "discord.com", "forum")):
        return "discussion"
    return "web"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN RESEARCHER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SOTAResearcher:
    """
    SOTA-level research engine inspired by STORM + GPT-Researcher.

    Pipeline:
    1. Recall prior knowledge from memory
    2. Discover perspectives (STORM)
    3. Plan sub-questions (GPT-Researcher)
    4. Parallel compound search (all engines)
    5. Fuse results (Reciprocal Rank Fusion)
    6. Gap analysis → loop if needed
    7. Build mind map
    8. Synthesize final report
    9. Store new findings to memory
    """

    def __init__(
        self,
        *,
        max_iterations: int = 3,
        max_perspectives: int = 4,
        max_sub_questions: int = 8,
        max_sources_per_engine: int = 20,
        completeness_threshold: float = 0.75,
        memory_path: str = "data/research_memory",
        llm_getter=None,
    ):
        self.max_iterations = max_iterations
        self.max_perspectives = max_perspectives
        self.max_sub_questions = max_sub_questions
        self.max_sources_per_engine = max_sources_per_engine
        self.completeness_threshold = completeness_threshold
        self._llm_getter = llm_getter  # callable returning LLM instance
        self.memory = ResearchMemory(db_path=memory_path)

        # Engine availability (lazy-checked)
        self._perplexica = None
        self._searxng = None
        self._engines_checked = False

    # ── LLM access ────────────────────────────────────────────

    def _get_llm(self, profile: str = "research"):
        """Get an LLM instance. Uses the pipeline's model manager if available."""
        if self._llm_getter:
            return self._llm_getter(profile)
        # Fallback: import through the package path so the researcher works
        # both from the repo root and when imported as part of src.*.
        try:
            from src.utils.model_manager import get_llm
            return get_llm(profile)
        except Exception:
            from ..utils.model_manager import get_llm
            return get_llm(profile)

    # ── Ollama model pre-warming ─────────────────────────────

    async def _ensure_ollama_models(self) -> bool:
        """
        Pre-warm Ollama models needed by Perplexica.
        Reads PERPLEXICA_CHAT_MODEL and PERPLEXICA_EMBEDDING_MODEL from env,
        checks `ollama ps`, and loads any that aren't running.
        Returns True if all needed models are loaded.
        """
        import subprocess

        chat_model = os.environ.get("PERPLEXICA_CHAT_MODEL", "").strip()
        embed_model = os.environ.get("PERPLEXICA_EMBEDDING_MODEL", "").strip()
        needed = [m for m in [chat_model, embed_model] if m]
        if not needed:
            return True

        # Check which models are already loaded
        try:
            result = subprocess.run(
                ["ollama", "ps"], capture_output=True, text=True, timeout=10
            )
            loaded_output = result.stdout.lower()
        except Exception as e:
            logger.warning(f"Cannot check ollama ps: {e}")
            return False

        models_to_load = []
        for model in needed:
            # ollama ps output has model name in first column
            if model.lower().split(":")[0] in loaded_output:
                logger.info(f"Ollama model already loaded: {model}")
            else:
                models_to_load.append(model)

        if not models_to_load:
            return True

        # Check that models are available locally (ollama list)
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
            available = result.stdout.lower()
        except Exception:
            available = ""

        for model in models_to_load:
            model_base = model.lower().split(":")[0]
            if model_base not in available:
                logger.warning(f"Ollama model not installed: {model} — run 'ollama pull {model}'")
                continue

            logger.info(f"Pre-warming Ollama model: {model}")
            try:
                # Send a tiny prompt to force the model into VRAM
                proc = await asyncio.create_subprocess_exec(
                    "ollama", "run", model, "--keepalive", "30m",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                # Send empty input to just load the model and exit
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=b"hi\n"), timeout=120
                )
                if proc.returncode == 0:
                    logger.info(f"Model loaded: {model}")
                else:
                    logger.warning(f"Model load failed ({model}): {stderr.decode()[:200]}")
            except asyncio.TimeoutError:
                logger.warning(f"Model load timed out: {model}")
            except Exception as e:
                logger.warning(f"Model load error ({model}): {e}")

        return True

    # ── Perplexica auto-launch ────────────────────────────────

    async def _ensure_perplexica(self) -> bool:
        """
        Check if Perplexica is running; if not, try to launch it.
        Looks for the Perplexica project in common locations and starts it.
        Returns True if Perplexica is reachable after this call.
        """
        import subprocess
        import aiohttp

        url = os.environ.get("PERPLEXICA_URL", "http://localhost:9123")

        # Quick health check
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{url}/api/providers", timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Perplexica already running at {url}")
                        return True
        except Exception:
            pass

        logger.info("Perplexica not running — attempting auto-launch...")

        # Find Perplexica installation
        perplexica_dir = os.environ.get("PERPLEXICA_DIR", "")
        if not perplexica_dir or not os.path.isdir(perplexica_dir):
            # Search common locations
            candidates = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))))), "perplexica"),
                os.path.expanduser("~/Projects/perplexica"),
                "D:/Projects/perplexica",
            ]
            for c in candidates:
                if os.path.isdir(c) and os.path.isfile(os.path.join(c, "package.json")):
                    perplexica_dir = c
                    break

        if not perplexica_dir:
            logger.warning("Perplexica directory not found — cannot auto-launch")
            return False

        # Launch Perplexica (npm start in background)
        try:
            logger.info(f"Starting Perplexica from {perplexica_dir}...")
            # Use npm start which runs "next start -p 9123"
            proc = subprocess.Popen(
                ["npm", "start"],
                cwd=perplexica_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            logger.info(f"Perplexica launch initiated (PID {proc.pid})")
        except Exception as e:
            logger.warning(f"Failed to start Perplexica: {e}")
            return False

        # Wait for it to become available (up to 45 seconds)
        for attempt in range(15):
            await asyncio.sleep(3)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{url}/api/providers",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status == 200:
                            logger.info(f"Perplexica is ready at {url} (took ~{(attempt + 1) * 3}s)")
                            return True
            except Exception:
                continue

        logger.warning("Perplexica did not start within 45 seconds")
        return False

    # ── Engine discovery ──────────────────────────────────────

    async def _check_engines(self):
        """
        Discover which search engines are available.
        Auto-warms Ollama models and auto-launches Perplexica if needed.
        """
        if self._engines_checked:
            return
        self._engines_checked = True

        if _perplexica_enabled():
            # Step 1: Ensure Ollama models are loaded (needed by Perplexica)
            await self._ensure_ollama_models()

            # Step 2: Ensure Perplexica is running (auto-launch if needed)
            await self._ensure_perplexica()

            # Step 3: Connect to Perplexica
            try:
                from src.research.perplexica_client import PerplexicaClient
                url = os.environ.get("PERPLEXICA_URL", "http://localhost:9123")
                client = PerplexicaClient(
                    url,
                    chat_provider_name=os.environ.get("PERPLEXICA_CHAT_PROVIDER"),
                    chat_model_key=os.environ.get("PERPLEXICA_CHAT_MODEL"),
                    embedding_provider_name=os.environ.get("PERPLEXICA_EMBEDDING_PROVIDER"),
                    embedding_model_key=os.environ.get("PERPLEXICA_EMBEDDING_MODEL"),
                    default_mode=os.environ.get("PERPLEXICA_MODE", "quality"),
                    timeout_s=int(os.environ.get("PERPLEXICA_TIMEOUT", "180")),
                )
                if await client.is_available():
                    self._perplexica = client
                    logger.info(f"Perplexica available at {url}")
                else:
                    await client.close()
                    logger.info("Perplexica not available (even after auto-launch attempt)")
            except Exception as e:
                logger.info(f"Perplexica not available: {e}")
        else:
            logger.info("Perplexica disabled by environment; skipping local engine warmup and launch")

        # Step 4: SearXNG
        try:
            from src.research.searxng_client import SearXNGClient
            client = SearXNGClient()
            if client.is_available():
                self._searxng = client
                logger.info("SearXNG available")
            else:
                logger.info("SearXNG not available")
        except Exception as e:
            logger.info(f"SearXNG not available: {e}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: DISCOVER PERSPECTIVES (STORM-style)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _discover_perspectives(
        self, topic: str, prior_knowledge: str = ""
    ) -> List[Perspective]:
        """
        STORM-style: discover N relevant expert perspectives on the topic.
        Each perspective will generate unique questions and search queries.
        """
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
        except ImportError:
            from langchain.schema import SystemMessage, HumanMessage

        llm = self._get_llm("research")
        prompt = f"""Given this research topic: "{topic}"

{f"We already know some things about this: {prior_knowledge[:2000]}" if prior_knowledge else ""}

Identify {self.max_perspectives} distinct expert perspectives that would provide
the most comprehensive and deep understanding of this topic.

For each perspective, also generate 3-5 specific, deep research questions
that ONLY this expert would ask (not generic questions).

Return ONLY valid JSON:
{{
  "perspectives": [
    {{
      "name": "Role name (e.g., Systems Architect)",
      "description": "Why this perspective is essential for this topic",
      "questions": [
        "Highly specific question from this expert's viewpoint",
        "Another deep question only this expert would ask"
      ]
    }}
  ]
}}"""

        try:
            resp = await llm.ainvoke([
                SystemMessage(content=(
                    "You are a research planning expert. You decompose topics into "
                    "the most insightful expert perspectives. Each perspective should "
                    "cover a DIFFERENT dimension of the topic — avoid overlap."
                )),
                HumanMessage(content=prompt),
            ])
            raw = resp.content or ""
            parsed = _extract_json(raw)
            if isinstance(parsed, dict):
                perspectives = []
                for p in parsed.get("perspectives", [])[:self.max_perspectives]:
                    perspectives.append(Perspective(
                        name=p.get("name", "Expert"),
                        description=p.get("description", ""),
                        questions=p.get("questions", [])[:5],
                    ))
                if perspectives:
                    logger.info(f"Discovered {len(perspectives)} perspectives: {[p.name for p in perspectives]}")
                    return perspectives
        except Exception as e:
            logger.warning(f"Perspective discovery failed: {e}")

        # Fallback: hardcoded perspectives
        return [
            Perspective("Research Scientist", "Theoretical foundations, SOTA papers, benchmarks",
                        [f"What are the latest papers on {topic}?",
                         f"What benchmarks measure progress in {topic}?"]),
            Perspective("Systems Engineer", "Architecture, scalability, production readiness",
                        [f"What are the best open-source implementations of {topic}?",
                         f"What hardware requirements does {topic} have?"]),
            Perspective("Applied Practitioner", "Real-world use cases, trade-offs, lessons learned",
                        [f"What are common pitfalls when implementing {topic}?",
                         f"What is the recommended approach for {topic} in production?"]),
        ]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: PLAN SUB-QUESTIONS (GPT-Researcher-style)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _plan_sub_questions(
        self, topic: str, perspectives: List[Perspective], prior_knowledge: str = ""
    ) -> List[str]:
        """
        Generate a comprehensive list of sub-questions that together
        cover all aspects of the topic. Based on GPT-Researcher's
        Plan-and-Solve pattern.
        """
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
        except ImportError:
            from langchain.schema import SystemMessage, HumanMessage

        perspective_text = "\n".join(
            f"- {p.name}: {', '.join(p.questions[:3])}"
            for p in perspectives
        )

        llm = self._get_llm("research")
        prompt = f"""Research topic: "{topic}"

Expert perspectives and their questions:
{perspective_text}

{f"Prior knowledge: {prior_knowledge[:1500]}" if prior_knowledge else ""}

Generate {self.max_sub_questions} search-engine-optimized sub-questions that:
1. Together provide comprehensive coverage of the topic
2. Include questions from EVERY perspective above
3. Are specific enough for a search engine (not too broad)
4. Cover: theory, implementation, benchmarks, tools, limitations, recent advances
5. Do NOT overlap — each question must target a unique aspect

Return ONLY valid JSON:
{{
  "sub_questions": [
    "First specific search query...",
    "Second specific search query..."
  ]
}}"""

        try:
            resp = await llm.ainvoke([
                SystemMessage(content=(
                    "You are a research planner. Generate precise, search-engine-optimized "
                    "queries that collectively provide comprehensive topic coverage. "
                    "Each query should be concise (5-15 words) and target a specific aspect."
                )),
                HumanMessage(content=prompt),
            ])
            parsed = _extract_json(resp.content or "")
            if isinstance(parsed, dict):
                questions = parsed.get("sub_questions", [])[:self.max_sub_questions]
                if questions:
                    return questions
        except Exception as e:
            logger.warning(f"Sub-question planning failed: {e}")

        # Fallback: basic queries
        return [
            f"{topic} state of the art 2025 2026",
            f"{topic} best implementations github",
            f"{topic} benchmark comparison",
            f"{topic} architecture design",
            f"{topic} limitations challenges",
            f"{topic} recent advances papers arxiv",
        ]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: COMPOUND PARALLEL SEARCH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _search_perplexica(
        self, queries: List[str], perspective: str = ""
    ) -> List[Source]:
        """Search via Perplexica (swarm + targeted queries)."""
        if not self._perplexica:
            return []

        sources = []
        try:
            # Use swarm search for the main topic (first query)
            main_query = queries[0] if queries else ""
            if main_query:
                swarm_result = await self._perplexica.swarm_search(
                    main_query,
                    sources=["web", "academic"],
                    mode=os.environ.get("PERPLEXICA_MODE", "quality"),
                )
                for s in swarm_result.sources:
                    sources.append(Source(
                        title=s.title, url=s.url, content=s.content,
                        source_type=classify_source_type(s.url),
                        engine="perplexica_swarm",
                        relevance_score=0.85,
                        perspective=perspective,
                    ))

            # Targeted queries for the rest (semaphore-limited)
            sem = asyncio.Semaphore(4)

            async def _search_one(q: str):
                async with sem:
                    await asyncio.sleep(0.5)  # throttle
                    return await self._perplexica.search(
                        q, sources=["web", "academic"],
                        mode="speed",
                    )

            tasks = [_search_one(q) for q in queries[1:6]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    continue
                for s in r.sources:
                    sources.append(Source(
                        title=s.title, url=s.url, content=s.content,
                        source_type=classify_source_type(s.url),
                        engine="perplexica",
                        relevance_score=0.8,
                        perspective=perspective,
                    ))
        except Exception as e:
            logger.warning(f"Perplexica search error: {e}")

        return sources[:self.max_sources_per_engine]

    async def _search_searxng(
        self, queries: List[str], perspective: str = ""
    ) -> List[Source]:
        """Search via SearXNG meta-search engine."""
        if not self._searxng:
            return []

        sources = []
        try:
            for q in queries[:6]:
                try:
                    # General web search
                    results = self._searxng.search(q, categories="general", max_results=10)
                    for r in (results or []):
                        sources.append(Source(
                            title=r.get("title", ""), url=r.get("url", ""),
                            content=r.get("content", r.get("snippet", "")),
                            source_type=classify_source_type(r.get("url", "")),
                            engine="searxng",
                            relevance_score=0.75,
                            perspective=perspective,
                        ))
                except Exception:
                    pass

                try:
                    # Academic search
                    results = self._searxng.search_papers(q, max_results=8)
                    for r in (results or []):
                        sources.append(Source(
                            title=r.get("title", ""), url=r.get("url", ""),
                            content=r.get("content", r.get("snippet", "")),
                            source_type="academic",
                            engine="searxng_academic",
                            relevance_score=0.8,
                            perspective=perspective,
                        ))
                except Exception:
                    pass

                try:
                    # Code search
                    results = self._searxng.search_code(q, max_results=5)
                    for r in (results or []):
                        sources.append(Source(
                            title=r.get("title", ""), url=r.get("url", ""),
                            content=r.get("content", r.get("snippet", "")),
                            source_type="code",
                            engine="searxng_code",
                            relevance_score=0.8,
                            perspective=perspective,
                        ))
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"SearXNG search error: {e}")

        return sources[:self.max_sources_per_engine]

    async def _search_arxiv(
        self, queries: List[str], perspective: str = ""
    ) -> List[Source]:
        """Direct arXiv API search."""
        sources = []
        try:
            from src.utils.web_search import ArxivSearcher
            searcher = ArxivSearcher(max_results=8)
            for q in queries[:4]:
                try:
                    results = searcher.search(q)
                    for r in (results or []):
                        sources.append(Source(
                            title=r.get("title", ""), url=r.get("url", ""),
                            content=r.get("summary", r.get("abstract", "")),
                            source_type="academic",
                            engine="arxiv",
                            relevance_score=0.85,
                            perspective=perspective,
                        ))
                except Exception:
                    pass
        except ImportError:
            logger.debug("ArxivSearcher not available")
        return sources[:self.max_sources_per_engine]

    async def _search_compound_beta(
        self, topic: str, sub_questions: List[str], perspective: str = ""
    ) -> Tuple[List[Source], Dict[str, Any]]:
        """
        Use compound-beta (Groq web-search LLM) for a structured research pass.
        Returns both raw sources and structured insights.
        """
        sources = []
        structured = {}
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
        except ImportError:
            from langchain.schema import SystemMessage, HumanMessage

        try:
            llm = self._get_llm("research")
            questions_text = "\n".join(f"- {q}" for q in sub_questions[:6])
            resp = await llm.ainvoke([
                SystemMessage(content=(
                    "You are a world-class research analyst with real-time web search. "
                    "Search for recent papers, benchmarks, open-source implementations, and SOTA results. "
                    "Cite specific sources. Return ONLY valid JSON."
                )),
                HumanMessage(content=f"""Research: {topic}
Sub-questions to address:
{questions_text}

Return JSON:
{{
  "sota_summary": "3-5 sentence state of the art summary",
  "key_papers": [{{"title": "...", "url": "arxiv link", "contribution": "..."}}],
  "open_problems": ["Problem 1...", "Problem 2..."],
  "implementations": [{{"name": "...", "url": "github link", "description": "..."}}],
  "benchmarks": [{{"name": "...", "metric": "...", "best_result": "...", "model": "..."}}],
  "key_insights": ["Insight 1...", "Insight 2..."]
}}"""),
            ])

            parsed = _extract_json(resp.content or "")
            if isinstance(parsed, dict):
                structured = parsed
                for p in parsed.get("key_papers", []):
                    sources.append(Source(
                        title=p.get("title", ""), url=p.get("url", ""),
                        content=p.get("contribution", ""),
                        source_type="academic", engine="compound_beta",
                        relevance_score=0.9, perspective=perspective,
                    ))
                for imp in parsed.get("implementations", []):
                    sources.append(Source(
                        title=imp.get("name", ""), url=imp.get("url", ""),
                        content=imp.get("description", ""),
                        source_type="code", engine="compound_beta",
                        relevance_score=0.85, perspective=perspective,
                    ))
        except Exception as e:
            logger.warning(f"compound-beta search failed: {e}")

        return sources, structured

    async def _parallel_search(
        self, queries: List[str], topic: str, perspective: str = ""
    ) -> List[List[Source]]:
        """
        Run ALL available search engines in parallel and return separate
        ranked lists (for Reciprocal Rank Fusion).
        """
        tasks = []
        task_names = []

        # Perplexica
        if self._perplexica:
            tasks.append(self._search_perplexica(queries, perspective))
            task_names.append("perplexica")

        # SearXNG
        if self._searxng:
            tasks.append(self._search_searxng(queries, perspective))
            task_names.append("searxng")

        # arXiv
        tasks.append(self._search_arxiv(queries, perspective))
        task_names.append("arxiv")

        # compound-beta (returns tuple, we need just the sources)
        async def _cb_sources():
            srcs, _ = await self._search_compound_beta(topic, queries, perspective)
            return srcs
        tasks.append(_cb_sources())
        task_names.append("compound_beta")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        ranked_lists = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Search engine {task_names[i]} failed: {result}")
                continue
            if result:
                # Score quality for each source
                for src in result:
                    src.quality_score = score_source_quality(src)
                # Sort by quality within this engine's results
                result.sort(key=lambda s: s.quality_score, reverse=True)
                ranked_lists.append(result)
                logger.info(f"  {task_names[i]}: {len(result)} results")

        return ranked_lists

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: GAP ANALYSIS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _analyze_gaps(
        self, topic: str, current_sources: List[Source], perspectives: List[Perspective]
    ) -> Tuple[List[str], float]:
        """
        Analyze what's missing from current research.
        Returns (gap_queries, completeness_score).
        """
        # Check structural coverage
        has_academic = any(s.source_type == "academic" for s in current_sources)
        has_code = any(s.source_type == "code" for s in current_sources)
        has_discussion = any(s.source_type == "discussion" for s in current_sources)
        has_web = any(s.source_type == "web" for s in current_sources)

        # Count per perspective
        perspective_coverage = {}
        for p in perspectives:
            count = sum(1 for s in current_sources if s.perspective == p.name)
            perspective_coverage[p.name] = count

        # Calculate structural completeness
        type_score = sum([
            0.3 if has_academic else 0,
            0.25 if has_code else 0,
            0.15 if has_discussion else 0,
            0.15 if has_web else 0,
        ])
        # Source quantity bonus
        quantity_score = min(0.15, len(current_sources) / 100 * 0.15)
        completeness = type_score + quantity_score

        # Use LLM to identify specific gaps
        gaps = []
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
        except ImportError:
            from langchain.schema import SystemMessage, HumanMessage

        try:
            llm = self._get_llm("fast")
            source_summary = "\n".join(
                f"- [{s.source_type}] {s.title}: {s.content[:100]}"
                for s in current_sources[:30]
            )
            resp = await llm.ainvoke([
                SystemMessage(content="You identify gaps in research coverage. Return ONLY JSON."),
                HumanMessage(content=f"""Topic: {topic}
Current sources ({len(current_sources)} total):
{source_summary}

What important aspects are NOT yet covered? Generate 3-5 specific search queries
to fill the gaps. Focus on:
- Missing theoretical foundations
- Missing practical implementations
- Missing benchmarks or comparisons
- Missing recent developments (2025-2026)

Return JSON: {{"gaps": ["gap query 1", "gap query 2", ...]}}"""),
            ])
            parsed = _extract_json(resp.content or "")
            if isinstance(parsed, dict):
                gaps = parsed.get("gaps", [])[:5]
        except Exception as e:
            logger.warning(f"Gap analysis LLM failed: {e}")

        # Structural gaps as fallback
        if not has_academic:
            gaps.append(f"{topic} research papers arxiv 2025 2026")
        if not has_code:
            gaps.append(f"{topic} implementation github open source")
        if not has_discussion:
            gaps.append(f"{topic} community discussion reddit hackernews")

        return gaps, completeness

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 5: BUILD MIND MAP
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _build_mind_map(
        self, topic: str, sources: List[Source]
    ) -> MindMapNode:
        """Build a hierarchical mind map from research findings."""
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
        except ImportError:
            from langchain.schema import SystemMessage, HumanMessage

        try:
            llm = self._get_llm("balanced")
            source_text = "\n".join(
                f"[{s.source_type}] {s.title}: {s.content[:200]}"
                for s in sources[:40]
            )
            resp = await llm.ainvoke([
                SystemMessage(content=(
                    "You organize research findings into a hierarchical concept map. "
                    "Return ONLY valid JSON."
                )),
                HumanMessage(content=f"""Topic: {topic}
Sources:
{source_text}

Create a hierarchical mind map. Return JSON:
{{
  "concept": "{topic}",
  "facts": ["Key fact 1", "Key fact 2"],
  "children": [
    {{
      "concept": "Sub-topic 1",
      "facts": ["Fact about sub-topic"],
      "children": []
    }}
  ]
}}"""),
            ])
            parsed = _extract_json(resp.content or "")
            if isinstance(parsed, dict):
                return _parse_mind_map(parsed)
        except Exception as e:
            logger.warning(f"Mind map generation failed: {e}")

        # Fallback: organize by source type
        root = MindMapNode(concept=topic)
        by_type = defaultdict(list)
        for s in sources:
            by_type[s.source_type].append(s)
        for stype, srcs in by_type.items():
            child = MindMapNode(
                concept=stype.title(),
                facts=[s.title for s in srcs[:5]],
                sources=[s.url for s in srcs[:5]],
                coverage_score=min(1.0, len(srcs) / 10),
            )
            root.children.append(child)
        return root

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 6: SYNTHESIZE REPORT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _synthesize(
        self, topic: str, sources: List[Source], structured_data: Dict[str, Any]
    ) -> Tuple[str, List[str], List[str], List[Dict], List[Dict]]:
        """
        Synthesize all findings into a coherent summary.
        Returns (summary, key_findings, open_problems, implementations, benchmarks).
        """
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
        except ImportError:
            from langchain.schema import SystemMessage, HumanMessage

        # If compound-beta gave us structured data, use it directly
        key_findings = structured_data.get("key_insights", [])
        open_problems = structured_data.get("open_problems", [])
        implementations = structured_data.get("implementations", [])
        benchmarks = structured_data.get("benchmarks", [])

        try:
            llm = self._get_llm("balanced")
            source_summary = "\n".join(
                f"- [{s.source_type}] {s.title}: {s.content[:300]}"
                for s in sources[:50]
            )
            resp = await llm.ainvoke([
                SystemMessage(content=(
                    "You are an expert research synthesizer. Create a comprehensive "
                    "but concise summary of research findings. Be specific — cite "
                    "numbers, paper names, and concrete results. Return ONLY JSON."
                )),
                HumanMessage(content=f"""Topic: {topic}
Sources ({len(sources)} total):
{source_summary}

Synthesize into JSON:
{{
  "summary": "Comprehensive 5-10 sentence summary with specific findings, numbers, and citations",
  "key_findings": ["Finding 1 with specifics", "Finding 2..."],
  "open_problems": ["Problem 1 with detail", "Problem 2..."],
  "implementations": [{{"name": "...", "url": "...", "description": "..."}}],
  "benchmarks": [{{"name": "...", "metric": "...", "best_result": "...", "model": "..."}}]
}}"""),
            ])
            parsed = _extract_json(resp.content or "")
            if isinstance(parsed, dict):
                summary = parsed.get("summary", "")
                key_findings = parsed.get("key_findings", key_findings) or key_findings
                open_problems = parsed.get("open_problems", open_problems) or open_problems
                impls = parsed.get("implementations", [])
                if impls:
                    implementations = impls
                bms = parsed.get("benchmarks", [])
                if bms:
                    benchmarks = bms
                return summary, key_findings, open_problems, implementations, benchmarks
        except Exception as e:
            logger.warning(f"Synthesis failed: {e}")

        # Fallback summary
        summary = (
            f"Research on '{topic}' found {len(sources)} sources "
            f"({sum(1 for s in sources if s.source_type == 'academic')} academic, "
            f"{sum(1 for s in sources if s.source_type == 'code')} code repos, "
            f"{sum(1 for s in sources if s.source_type == 'web')} web pages)."
        )
        return summary, key_findings, open_problems, implementations, benchmarks

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN ENTRY POINT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def research(self, topic: str) -> ResearchReport:
        """
        Run a full SOTA research session on a topic.

        This is the main entry point. Orchestrates:
        1. Memory recall
        2. Perspective discovery
        3. Sub-question planning
        4. Iterative compound search
        5. Result fusion + dedup
        6. Gap analysis + loop
        7. Mind map construction
        8. Synthesis
        9. Memory storage
        """
        t0 = time.monotonic()
        logger.info(f"SOTA Research starting: '{topic}'")

        # Check available engines
        await self._check_engines()
        engines = []
        if self._perplexica:
            engines.append("Perplexica")
        if self._searxng:
            engines.append("SearXNG")
        engines.extend(["arXiv", "compound-beta"])
        logger.info(f"Available engines: {engines}")

        # ── 1. Recall prior knowledge ────────────────────────
        prior_findings = self.memory.recall(topic, top_k=20)
        memory_hits = len(prior_findings)
        prior_knowledge = ""
        if prior_findings:
            prior_knowledge = "\n".join(
                f"- {f['content'][:200]}" for f in prior_findings[:10]
            )
            logger.info(f"Recalled {memory_hits} prior findings from memory")

        # ── 2. Discover perspectives (STORM) ──────────────────
        perspectives = await self._discover_perspectives(topic, prior_knowledge)

        # ── 3. Plan sub-questions (GPT-Researcher) ────────────
        sub_questions = await self._plan_sub_questions(topic, perspectives, prior_knowledge)
        logger.info(f"Planned {len(sub_questions)} sub-questions")

        # ── 4. Iterative search loop ─────────────────────────
        all_sources: List[Source] = []
        total_queries = 0
        structured_data: Dict[str, Any] = {}

        for iteration in range(self.max_iterations):
            logger.info(f"Research iteration {iteration + 1}/{self.max_iterations}")

            if iteration == 0:
                queries = sub_questions
            else:
                # Use gap queries from previous iteration
                gaps, completeness = await self._analyze_gaps(topic, all_sources, perspectives)
                logger.info(f"Completeness: {completeness:.2f}, gaps: {len(gaps)}")
                if completeness >= self.completeness_threshold or not gaps:
                    logger.info("Completeness threshold met — stopping research")
                    break
                queries = gaps

            # Search with perspective rotation
            perspective_name = perspectives[iteration % len(perspectives)].name

            # Run parallel compound search
            ranked_lists = await self._parallel_search(queries, topic, perspective_name)
            total_queries += len(queries)

            # Also get structured data on first iteration
            if iteration == 0:
                _, cb_data = await self._search_compound_beta(topic, queries)
                structured_data.update(cb_data)

            # Fuse results
            if ranked_lists:
                fused = reciprocal_rank_fusion(ranked_lists)
                new_sources = deduplicate_sources(fused)
                all_sources.extend(new_sources)
                logger.info(f"  Iteration {iteration + 1}: +{len(new_sources)} sources (total: {len(all_sources)})")

        # Final dedup across all iterations
        all_sources = deduplicate_sources(all_sources)

        # ── 5. Build mind map ─────────────────────────────────
        mind_map = await self._build_mind_map(topic, all_sources)

        # ── 6. Synthesize report ──────────────────────────────
        summary, key_findings, open_problems, implementations, benchmarks = \
            await self._synthesize(topic, all_sources, structured_data)

        # ── 7. Final gap check ────────────────────────────────
        _, final_completeness = await self._analyze_gaps(topic, all_sources, perspectives)
        gaps_remaining = []
        if final_completeness < self.completeness_threshold:
            # Record remaining gaps
            gaps_remaining, _ = await self._analyze_gaps(topic, all_sources, perspectives)

        # ── 8. Store to memory ────────────────────────────────
        self.memory.store(all_sources, topic)

        # ── 9. Cleanup ────────────────────────────────────────
        if self._perplexica:
            try:
                await self._perplexica.close()
            except Exception:
                pass

        elapsed = time.monotonic() - t0
        logger.info(
            f"SOTA Research complete: {len(all_sources)} unique sources, "
            f"{total_queries} queries, {elapsed:.1f}s"
        )

        return ResearchReport(
            topic=topic,
            perspectives=perspectives,
            mind_map=mind_map,
            all_sources=all_sources,
            summary=summary,
            key_findings=key_findings,
            open_problems=open_problems,
            implementations=implementations if isinstance(implementations, list) else [],
            benchmarks=benchmarks if isinstance(benchmarks, list) else [],
            gaps_remaining=gaps_remaining,
            iterations=min(iteration + 1, self.max_iterations),
            total_queries=total_queries,
            total_sources=len(all_sources),
            unique_sources=len(all_sources),
            elapsed_s=round(elapsed, 2),
            memory_hits=memory_hits,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _extract_json(text: str) -> Any:
    """Extract JSON from text that may contain markdown code fences or prose."""
    import re
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code fences
    m = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try finding first { ... } block
    brace_start = text.find('{')
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start:i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _parse_mind_map(data: dict) -> MindMapNode:
    """Recursively parse a mind map dict into MindMapNode tree."""
    node = MindMapNode(
        concept=data.get("concept", "Unknown"),
        facts=data.get("facts", [])[:10],
        sources=data.get("sources", [])[:5],
        coverage_score=data.get("coverage", 0.0),
    )
    for child_data in data.get("children", [])[:8]:
        if isinstance(child_data, dict):
            node.children.append(_parse_mind_map(child_data))
    return node
