"""
Dynamic Agent Spawner — Kimi K2.5-Style Adaptive Multi-Agent System
=====================================================================

Instead of a fixed set of 3 perspectives, the spawner:
  1. Analyses the task and determines HOW MANY and WHAT KIND of agents are needed.
  2. Spawns specialised agents with unique roles, prompts, temperatures and
     model profiles — all determined by an LLM "planner" call.
  3. Coordinates execution (fan-out/fan-in, hierarchical, sequential, or
     supervisor-worker).
  4. Aggregates results via weighted voting, synthesis, or merge.

Design principles (research-backed):
  • Persona diversity ≈ model diversity (Multi-Agent Debate, 2024).
  • Resource-aware: spawns fewer agents when RAM/VRAM is tight.
  • Idempotent: safe to call multiple times — agents are stateless.
  • Cheap: uses the "fast" LLM profile for planning, heavier profiles
    only for the spawned workers that need them.

Integration points in Auto-GIT pipeline:
  • ``generate_perspectives_node`` → replaced by ``spawn_debate_agents``
  • ``code_generation_node`` → spawn per-file specialist writers
  • ``code_review_agent_node`` → spawn review specialists
  • ``code_testing_node`` → spawn test specialists (unit, integration, security)

Usage
-----
::

    spawner = AgentSpawner()

    # --- simple fan-out ---
    pool = await spawner.spawn_for_task(
        task="Design a privacy-preserving federated learning system",
        context={"research": ..., "requirements": ...},
        phase="debate",          # debate | codegen | review | test
        max_agents=6,
    )
    results = await pool.run_all(
        prompt="Propose a solution from your expert viewpoint.",
        coordination="parallel",
    )

    # --- supervisor pattern ---
    results = await pool.run_supervised(
        goal="Generate and validate a complete implementation",
        supervisor_profile="powerful",
    )
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

CoordinationMode = Literal["parallel", "sequential", "hierarchical", "round_robin"]
PhaseHint = Literal["debate", "codegen", "review", "test", "research", "general"]


@dataclass
class AgentRole:
    """Blueprint for a dynamically-created agent."""

    name: str
    role_description: str
    expertise: str
    focus_areas: list[str] = field(default_factory=list)
    evaluation_criteria: list[str] = field(default_factory=list)
    system_prompt: str = ""
    temperature: float = 0.7
    model_profile: str = "balanced"  # fast | balanced | powerful | reasoning
    weight: float = 1.0  # voting weight in aggregation


@dataclass
class AgentResult:
    """Structured output from a single spawned agent."""

    agent_id: str
    agent_name: str
    role: AgentRole
    output: Any  # parsed JSON or raw text
    raw_text: str = ""
    latency_s: float = 0.0
    success: bool = True
    error: str = ""


@dataclass
class PoolResult:
    """Aggregated results from a whole agent pool."""

    results: list[AgentResult] = field(default_factory=list)
    coordination: str = "parallel"
    total_latency_s: float = 0.0
    successful: int = 0
    failed: int = 0
    synthesis: str = ""  # Supervisor / aggregation summary
    consensus_score: float = 0.0


# ---------------------------------------------------------------------------
# Spawned Agent — lightweight callable wrapper
# ---------------------------------------------------------------------------

class SpawnedAgent:
    """
    A dynamically-created agent instance.

    Wraps an LLM with a specific system prompt / role.
    Stateless — call ``execute()`` as many times as you like.
    """

    def __init__(self, role: AgentRole, llm: Any):
        self.id = f"agent-{uuid.uuid4().hex[:8]}"
        self.role = role
        self.llm = llm
        self.call_count = 0

    async def execute(
        self,
        task: str,
        context: str = "",
        output_format: str = "",
    ) -> AgentResult:
        """
        Execute a task and return structured result.

        Parameters
        ----------
        task : str
            The main instruction / question.
        context : str
            Optional background info to prepend.
        output_format : str
            Optional format hint appended to the user prompt
            (e.g. "Return ONLY valid JSON").
        """
        t0 = time.perf_counter()
        self.call_count += 1

        system = self.role.system_prompt or self._build_system_prompt()
        user = task
        if context:
            user = f"{context}\n\n---\n\n{task}"
        if output_format:
            user = f"{user}\n\n{output_format}"

        messages = [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            raw = response.content or ""
            # Attempt JSON extraction
            parsed = _try_parse_json(raw)
            return AgentResult(
                agent_id=self.id,
                agent_name=self.role.name,
                role=self.role,
                output=parsed if parsed is not None else raw,
                raw_text=raw,
                latency_s=round(time.perf_counter() - t0, 2),
            )
        except Exception as exc:
            logger.warning(f"Agent {self.role.name} failed: {exc}")
            return AgentResult(
                agent_id=self.id,
                agent_name=self.role.name,
                role=self.role,
                output=None,
                raw_text="",
                latency_s=round(time.perf_counter() - t0, 2),
                success=False,
                error=str(exc),
            )

    # -- helpers --

    def _build_system_prompt(self) -> str:
        """Build a system prompt from role metadata."""
        parts = [
            f"You are a {self.role.role_description}.",
            f"\nYour expertise: {self.role.expertise}",
        ]
        if self.role.focus_areas:
            parts.append(f"Focus areas: {', '.join(self.role.focus_areas)}")
        if self.role.evaluation_criteria:
            parts.append(
                "Evaluation criteria you apply:\n"
                + "\n".join(f"  - {c}" for c in self.role.evaluation_criteria)
            )
        return "\n".join(parts)

    def __repr__(self) -> str:
        return (
            f"<SpawnedAgent {self.id} name={self.role.name!r} "
            f"profile={self.role.model_profile}>"
        )


# ---------------------------------------------------------------------------
# Agent Pool — manages a group of spawned agents
# ---------------------------------------------------------------------------

class AgentPool:
    """
    Manages execution of a group of :class:`SpawnedAgent` instances.

    Supports multiple coordination modes:
      - **parallel**: all agents run concurrently (fastest, default)
      - **sequential**: one after another, each sees previous outputs
      - **round_robin**: agents take turns refining a shared artefact
      - **hierarchical**: supervisor distributes sub-tasks, workers execute
    """

    def __init__(
        self,
        agents: list[SpawnedAgent],
        phase: PhaseHint = "general",
    ):
        self.agents = agents
        self.phase = phase

    @property
    def size(self) -> int:
        return len(self.agents)

    # ── parallel (fan-out / fan-in) ──────────────────────────────────────

    async def run_parallel(
        self,
        task: str,
        context: str = "",
        output_format: str = "",
    ) -> PoolResult:
        """Execute all agents concurrently and collect results."""
        t0 = time.perf_counter()
        coros = [
            a.execute(task, context=context, output_format=output_format)
            for a in self.agents
        ]
        raw = await asyncio.gather(*coros, return_exceptions=True)
        results = []
        for r in raw:
            if isinstance(r, Exception):
                results.append(
                    AgentResult(
                        agent_id="?",
                        agent_name="?",
                        role=AgentRole(name="?", role_description="", expertise=""),
                        output=None,
                        success=False,
                        error=str(r),
                    )
                )
            else:
                results.append(r)

        return PoolResult(
            results=results,
            coordination="parallel",
            total_latency_s=round(time.perf_counter() - t0, 2),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
        )

    # ── sequential (pipeline / chain) ────────────────────────────────────

    async def run_sequential(
        self,
        task: str,
        context: str = "",
        output_format: str = "",
    ) -> PoolResult:
        """
        Execute agents one-by-one.  Each agent sees the previous agent's output
        appended to the context, enabling iterative refinement.
        """
        t0 = time.perf_counter()
        results: list[AgentResult] = []
        accumulated_context = context

        for agent in self.agents:
            result = await agent.execute(
                task,
                context=accumulated_context,
                output_format=output_format,
            )
            results.append(result)
            if result.success and result.raw_text:
                accumulated_context += (
                    f"\n\n--- Output from {agent.role.name} ---\n{result.raw_text[:2000]}"
                )

        return PoolResult(
            results=results,
            coordination="sequential",
            total_latency_s=round(time.perf_counter() - t0, 2),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
        )

    # ── round-robin refinement ───────────────────────────────────────────

    async def run_round_robin(
        self,
        task: str,
        context: str = "",
        output_format: str = "",
        rounds: int = 2,
    ) -> PoolResult:
        """
        Agents take turns refining a shared artefact.
        Each round, every agent gets the latest artefact and improves it.
        """
        t0 = time.perf_counter()
        results: list[AgentResult] = []
        artefact = ""

        for rnd in range(rounds):
            for agent in self.agents:
                round_ctx = context
                if artefact:
                    round_ctx += (
                        f"\n\n--- Current artefact (round {rnd + 1}) ---\n{artefact}"
                    )
                round_task = (
                    f"[Round {rnd + 1}] {task}\n\n"
                    "Improve the current artefact. Keep what's good, fix what isn't."
                )
                result = await agent.execute(
                    round_task,
                    context=round_ctx,
                    output_format=output_format,
                )
                results.append(result)
                if result.success and result.raw_text:
                    artefact = result.raw_text

        return PoolResult(
            results=results,
            coordination="round_robin",
            total_latency_s=round(time.perf_counter() - t0, 2),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
        )

    # ── hierarchical (supervisor ↔ workers) ──────────────────────────────

    async def run_supervised(
        self,
        goal: str,
        context: str = "",
        output_format: str = "",
        supervisor_llm: Any = None,
    ) -> PoolResult:
        """
        A supervisor agent decomposes the goal into sub-tasks, assigns each
        to the most appropriate worker, then synthesises the results.

        If no ``supervisor_llm`` is provided, the first agent in the pool
        acts as supervisor and the rest are workers.
        """
        t0 = time.perf_counter()

        # --- determine supervisor and workers ---
        if supervisor_llm is not None:
            supervisor = SpawnedAgent(
                role=AgentRole(
                    name="Supervisor",
                    role_description="Project coordinator and synthesiser",
                    expertise="Task decomposition, delegation, result synthesis",
                    model_profile="powerful",
                ),
                llm=supervisor_llm,
            )
            workers = list(self.agents)
        else:
            supervisor = self.agents[0]
            workers = self.agents[1:] if len(self.agents) > 1 else self.agents

        # --- Step 1: supervisor decomposes ---
        worker_list = "\n".join(
            f"  {i + 1}. {w.role.name} — {w.role.expertise}"
            for i, w in enumerate(workers)
        )
        decompose_prompt = (
            f"Goal: {goal}\n\n"
            f"Available workers:\n{worker_list}\n\n"
            "Decompose this goal into sub-tasks.  Assign each sub-task to the "
            "best-suited worker by number.  Return JSON:\n"
            '{"subtasks": [{"worker_index": 0, "task": "..."}, ...]}'
        )
        plan_result = await supervisor.execute(
            decompose_prompt, context=context, output_format="Return ONLY valid JSON."
        )

        subtasks: list[dict] = []
        if plan_result.success and isinstance(plan_result.output, dict):
            subtasks = plan_result.output.get("subtasks", [])
        if not subtasks:
            # Fallback: broadcast goal to all workers
            subtasks = [
                {"worker_index": i, "task": goal} for i in range(len(workers))
            ]

        # --- Step 2: workers execute their sub-tasks in parallel ---
        worker_coros = []
        for st in subtasks:
            idx = int(st.get("worker_index", 0)) % len(workers)
            worker_coros.append(
                workers[idx].execute(
                    st.get("task", goal),
                    context=context,
                    output_format=output_format,
                )
            )
        worker_results = await asyncio.gather(*worker_coros, return_exceptions=True)
        clean_results = []
        for r in worker_results:
            if isinstance(r, Exception):
                clean_results.append(
                    AgentResult(
                        agent_id="?", agent_name="?",
                        role=AgentRole(name="?", role_description="", expertise=""),
                        output=None, success=False, error=str(r),
                    )
                )
            else:
                clean_results.append(r)

        # --- Step 3: supervisor synthesises ---
        synth_ctx = "\n\n".join(
            f"--- {r.agent_name} ---\n{r.raw_text[:2000]}"
            for r in clean_results
            if r.success
        )
        synth_result = await supervisor.execute(
            "Synthesise the following worker outputs into a single coherent result.",
            context=f"{context}\n\n{synth_ctx}",
            output_format=output_format,
        )

        all_results = [plan_result] + clean_results + [synth_result]
        return PoolResult(
            results=all_results,
            coordination="hierarchical",
            total_latency_s=round(time.perf_counter() - t0, 2),
            successful=sum(1 for r in all_results if r.success),
            failed=sum(1 for r in all_results if not r.success),
            synthesis=synth_result.raw_text if synth_result.success else "",
        )

    # ── convenience dispatcher ───────────────────────────────────────────

    async def run(
        self,
        task: str,
        context: str = "",
        output_format: str = "",
        coordination: CoordinationMode = "parallel",
        **kwargs: Any,
    ) -> PoolResult:
        """
        Dispatch to the requested coordination mode.
        """
        if coordination == "parallel":
            return await self.run_parallel(task, context, output_format)
        if coordination == "sequential":
            return await self.run_sequential(task, context, output_format)
        if coordination == "round_robin":
            return await self.run_round_robin(task, context, output_format, **kwargs)
        if coordination == "hierarchical":
            return await self.run_supervised(task, context, output_format, **kwargs)
        raise ValueError(f"Unknown coordination mode: {coordination}")


# ---------------------------------------------------------------------------
# Agent Spawner — the main factory
# ---------------------------------------------------------------------------

# Phase-specific defaults for agent count and profiles
_PHASE_DEFAULTS: dict[PhaseHint, dict[str, Any]] = {
    "debate": {
        "min_agents": 3,
        "max_agents": 7,
        "default_profile": "balanced",
        "coordination": "parallel",
    },
    "codegen": {
        "min_agents": 2,
        "max_agents": 5,
        "default_profile": "powerful",
        "coordination": "sequential",
    },
    "review": {
        "min_agents": 2,
        "max_agents": 5,
        "default_profile": "reasoning",
        "coordination": "parallel",
    },
    "test": {
        "min_agents": 2,
        "max_agents": 4,
        "default_profile": "balanced",
        "coordination": "parallel",
    },
    "research": {
        "min_agents": 2,
        "max_agents": 4,
        "default_profile": "balanced",
        "coordination": "parallel",
    },
    "general": {
        "min_agents": 2,
        "max_agents": 5,
        "default_profile": "balanced",
        "coordination": "parallel",
    },
}


class AgentSpawner:
    """
    Dynamic agent factory — analyses a task and spawns the right number and
    kind of specialised agents.

    Inspired by Kimi K2.5, AutoGen, CrewAI.  Key differences:
      1. **Adaptive count** — LLM decides how many agents are needed (2-N)
         based on task complexity and available resources.
      2. **Resource-aware** — checks free RAM/VRAM before spawning and
         degrades gracefully (fewer agents, smaller models).
      3. **Phase-aware** — different pipeline phases get different defaults
         (debate → 3-7 agents, codegen → 2-5, review → 2-5).
      4. **Heterogeneous profiles** — each agent can use a different model
         profile (fast/balanced/powerful/reasoning).
    """

    def __init__(self, resource_monitor: Any = None):
        self._resource_monitor = resource_monitor

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def spawn_for_task(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        phase: PhaseHint = "general",
        min_agents: int | None = None,
        max_agents: int | None = None,
        coordination: CoordinationMode | None = None,
        fixed_roles: list[AgentRole] | None = None,
    ) -> AgentPool:
        """
        Analyse the task and spawn an appropriate team of agents.

        Parameters
        ----------
        task : str
            Natural language task description.
        context : dict, optional
            Additional context (research, requirements, code, etc.).
        phase : str
            Pipeline phase hint — affects defaults.
        min_agents, max_agents : int, optional
            Override phase defaults.
        coordination : str, optional
            Override default coordination mode.
        fixed_roles : list[AgentRole], optional
            If provided, skip LLM planning and use these roles directly.

        Returns
        -------
        AgentPool
            Ready-to-execute pool of SpawnedAgent instances.
        """
        defaults = _PHASE_DEFAULTS.get(phase, _PHASE_DEFAULTS["general"])
        _min = min_agents or defaults["min_agents"]
        _max = max_agents or defaults["max_agents"]

        # Adjust max down if resources are tight
        _max = self._resource_adjusted_max(_max)

        if fixed_roles:
            roles = fixed_roles
        else:
            roles = await self._plan_agents(task, context or {}, phase, _min, _max)

        agents = self._instantiate_agents(roles)

        logger.info(
            f"🤖 Spawned {len(agents)} agents for phase={phase}: "
            + ", ".join(a.role.name for a in agents)
        )

        return AgentPool(agents, phase=phase)

    # ------------------------------------------------------------------
    # LLM-based agent planning
    # ------------------------------------------------------------------

    async def _plan_agents(
        self,
        task: str,
        context: dict[str, Any],
        phase: PhaseHint,
        min_agents: int,
        max_agents: int,
    ) -> list[AgentRole]:
        """
        Use an LLM to determine what agents are needed.
        """
        try:
            from src.utils.model_manager import get_fallback_llm
        except ImportError:
            from utils.model_manager import get_fallback_llm  # type: ignore

        llm = get_fallback_llm("fast")

        phase_guidance = _PHASE_GUIDANCE.get(phase, "")

        system = (
            "You are an expert meta-agent planner.  Given a task description and "
            "pipeline phase, determine the optimal team of AI agents to accomplish "
            "the task.  Each agent should have a DISTINCT, NON-OVERLAPPING role.\n\n"
            "Consider:\n"
            "  1. Task complexity — simple tasks need fewer agents\n"
            "  2. Required expertise diversity — cover all critical angles\n"
            "  3. Coordination efficiency — too many agents add overhead\n\n"
            f"Phase: {phase}\n"
            f"{phase_guidance}\n\n"
            "Return ONLY valid JSON in EXACTLY this format — no prose outside JSON."
        )

        # Build concise context summary
        ctx_summary = ""
        if context:
            for key in ("idea", "selected_problem", "requirements"):
                if context.get(key):
                    val = context[key]
                    if isinstance(val, str):
                        ctx_summary += f"\n{key}: {val[:300]}"
                    elif isinstance(val, dict):
                        ctx_summary += f"\n{key}: {str(val)[:300]}"

        user = f"""Task: {task}
{ctx_summary}

Decide how many agents are needed (between {min_agents} and {max_agents}) and define each one.

Return this EXACT JSON:
{{
  "agent_count": <int>,
  "reasoning": "Why this many agents with these roles",
  "agents": [
    {{
      "name": "Short Agent Title (2-4 words)",
      "role_description": "Full professional role (1 sentence)",
      "expertise": "Core technical expertise",
      "focus_areas": ["area1", "area2", "area3"],
      "temperature": 0.7,
      "model_profile": "balanced",
      "weight": 1.0
    }}
  ]
}}

model_profile options: "fast" (simple tasks), "balanced" (default), "powerful" (complex code), "reasoning" (analysis/critique).
weight: importance in voting (0.5-1.5, default 1.0)."""

        messages = [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]

        try:
            response = await llm.ainvoke(messages)
            parsed = _try_parse_json(response.content or "")

            if isinstance(parsed, dict) and parsed.get("agents"):
                agents_raw = parsed["agents"]
                if isinstance(agents_raw, list) and len(agents_raw) >= min_agents:
                    roles = []
                    for a in agents_raw[:max_agents]:
                        roles.append(
                            AgentRole(
                                name=str(a.get("name", "Agent"))[:50],
                                role_description=str(
                                    a.get("role_description", "Domain expert")
                                ),
                                expertise=str(a.get("expertise", "")),
                                focus_areas=list(a.get("focus_areas", [])),
                                temperature=float(a.get("temperature", 0.7)),
                                model_profile=str(
                                    a.get("model_profile", "balanced")
                                ),
                                weight=float(a.get("weight", 1.0)),
                            )
                        )
                    logger.info(
                        f"LLM planned {len(roles)} agents: "
                        + ", ".join(r.name for r in roles)
                    )
                    if parsed.get("reasoning"):
                        logger.info(f"  Reasoning: {parsed['reasoning']}")
                    return roles

            raise ValueError(f"Invalid planner output: {type(parsed)}")

        except Exception as exc:
            logger.warning(
                f"Agent planning failed ({exc}); using phase defaults for {phase}"
            )
            return self._default_roles_for_phase(phase, min_agents)

    # ------------------------------------------------------------------
    # Resource-aware scaling
    # ------------------------------------------------------------------

    def _resource_adjusted_max(self, desired_max: int) -> int:
        """
        Reduce max agent count if system resources are low.
        """
        if self._resource_monitor is None:
            return desired_max

        try:
            result = self._resource_monitor.evaluate_resources(
                max_ram_percent=80.0,
                max_vram_percent=80.0,
            )
            if not result["safe"]:
                reduced = max(2, desired_max // 2)
                logger.info(
                    f"Resource pressure detected — reducing max agents "
                    f"{desired_max}→{reduced}: {result['reasons']}"
                )
                return reduced
            # Even if "safe", scale by available headroom
            ram_free = result.get("ram_free_gb", 8.0)
            if ram_free < 2.0:
                return max(2, desired_max - 2)
            if ram_free < 4.0:
                return max(2, desired_max - 1)
        except Exception:
            pass
        return desired_max

    # ------------------------------------------------------------------
    # Agent instantiation
    # ------------------------------------------------------------------

    def _instantiate_agents(self, roles: Sequence[AgentRole]) -> list[SpawnedAgent]:
        """Create SpawnedAgent instances with the appropriate LLM."""
        try:
            from src.utils.model_manager import get_fallback_llm
        except ImportError:
            from utils.model_manager import get_fallback_llm  # type: ignore

        agents = []
        for role in roles:
            profile = role.model_profile
            if profile not in ("fast", "balanced", "powerful", "reasoning"):
                profile = "balanced"
            llm = get_fallback_llm(profile)
            agents.append(SpawnedAgent(role=role, llm=llm))
        return agents

    # ------------------------------------------------------------------
    # Phase-specific defaults (fallback when LLM planning fails)
    # ------------------------------------------------------------------

    @staticmethod
    def _default_roles_for_phase(
        phase: PhaseHint, count: int
    ) -> list[AgentRole]:
        """Hand-crafted fallback roles per phase."""
        if phase == "debate":
            return _DEFAULT_DEBATE_ROLES[:count]
        if phase == "codegen":
            return _DEFAULT_CODEGEN_ROLES[:count]
        if phase == "review":
            return _DEFAULT_REVIEW_ROLES[:count]
        if phase == "test":
            return _DEFAULT_TEST_ROLES[:count]
        if phase == "research":
            return _DEFAULT_RESEARCH_ROLES[:count]
        return _DEFAULT_GENERAL_ROLES[:count]


# ---------------------------------------------------------------------------
# Result aggregation helpers
# ---------------------------------------------------------------------------

def aggregate_votes(
    results: list[AgentResult],
    key: str = "recommendation",
) -> dict[str, float]:
    """
    Weighted voting across agent results.

    Each agent's ``output[key]`` is treated as a vote, weighted by
    ``role.weight``.  Returns {option: weighted_score}.
    """
    votes: dict[str, float] = {}
    for r in results:
        if not r.success or not isinstance(r.output, dict):
            continue
        vote = r.output.get(key, "")
        if vote:
            votes[vote] = votes.get(vote, 0.0) + r.role.weight
    return votes


def synthesise_outputs(
    results: list[AgentResult],
    max_chars_per_agent: int = 2000,
) -> str:
    """Combine successful agent outputs into a single context string."""
    parts = []
    for r in results:
        if r.success and r.raw_text:
            parts.append(
                f"--- {r.agent_name} ({r.role.expertise}) ---\n"
                f"{r.raw_text[:max_chars_per_agent]}"
            )
    return "\n\n".join(parts)


def best_result_by_score(
    results: list[AgentResult],
    score_key: str = "quality_score",
) -> AgentResult | None:
    """
    Return the result with the highest ``output[score_key]``,
    weighted by the agent's role weight.
    """
    best, best_score = None, -1.0
    for r in results:
        if not r.success or not isinstance(r.output, dict):
            continue
        raw_score = float(r.output.get(score_key, 0))
        weighted = raw_score * r.role.weight
        if weighted > best_score:
            best_score = weighted
            best = r
    return best


# ---------------------------------------------------------------------------
# Phase guidance prompts (injected into the planner)
# ---------------------------------------------------------------------------

_PHASE_GUIDANCE: dict[PhaseHint, str] = {
    "debate": (
        "This is the DEBATE phase.  Agents should represent diverse expert "
        "perspectives that can critique solutions from non-overlapping angles.\n"
        "Good roles: Domain Researcher, Systems Architect, Security Expert, "
        "Performance Engineer, UX/Practical Engineer, Theorist.\n"
        "Each agent proposes AND critiques — diversity of viewpoint is key."
    ),
    "codegen": (
        "This is the CODE GENERATION phase.  Agents should be specialised "
        "code writers for different aspects of the project.\n"
        "Good roles: Core Algorithm Developer, API/Interface Designer, "
        "Data Pipeline Engineer, Test Writer, DevOps/Config Specialist.\n"
        "Each agent writes code for their area of expertise."
    ),
    "review": (
        "This is the CODE REVIEW phase.  Agents should catch different kinds "
        "of problems.\n"
        "Good roles: Security Reviewer, Performance Analyser, API Contract "
        "Checker, Code Style/Maintainability Reviewer, Correctness Verifier.\n"
        "Each agent reviews from their specialist angle."
    ),
    "test": (
        "This is the TESTING phase.  Agents should design tests covering "
        "different dimensions.\n"
        "Good roles: Unit Test Designer, Integration Test Designer, Edge Case "
        "Hunter, Security Test Engineer, Performance Benchmarker.\n"
        "Each agent generates tests for their speciality."
    ),
    "research": (
        "This is the RESEARCH phase.  Agents should search for and synthesise "
        "information from different sources and angles.\n"
        "Good roles: Academic Paper Analyst, Industry Practice Surveyor, "
        "Competitive Landscape Analyst, Dataset/Benchmark Scout.\n"
        "Each agent researches their angle and reports findings."
    ),
    "general": (
        "General-purpose task.  Assign agents that cover the most critical "
        "aspects of the task."
    ),
}


# ---------------------------------------------------------------------------
# Default roles (fallback when LLM planning fails)
# ---------------------------------------------------------------------------

_DEFAULT_DEBATE_ROLES: list[AgentRole] = [
    AgentRole(
        name="Domain Researcher",
        role_description="Expert researcher in the task's domain",
        expertise="Literature review, SOTA analysis, theoretical foundations",
        focus_areas=["novelty", "theoretical soundness", "related work"],
        temperature=0.6,
        model_profile="balanced",
        weight=1.0,
    ),
    AgentRole(
        name="Systems Architect",
        role_description="Production systems architect",
        expertise="System design, scalability, deployment, infrastructure",
        focus_areas=["architecture", "scalability", "production readiness"],
        temperature=0.5,
        model_profile="balanced",
        weight=1.2,
    ),
    AgentRole(
        name="Security Engineer",
        role_description="Security and reliability expert",
        expertise="Vulnerability analysis, threat modeling, secure coding",
        focus_areas=["security", "privacy", "input validation", "error handling"],
        temperature=0.4,
        model_profile="reasoning",
        weight=1.3,
    ),
    AgentRole(
        name="Applied Scientist",
        role_description="Applied ML scientist focused on practical impact",
        expertise="Real-world deployment, user impact, practical constraints",
        focus_areas=["feasibility", "user impact", "deployment"],
        temperature=0.6,
        model_profile="balanced",
        weight=1.1,
    ),
    AgentRole(
        name="Performance Engineer",
        role_description="Performance and optimisation specialist",
        expertise="Algorithmic complexity, memory efficiency, benchmarking",
        focus_areas=["performance", "efficiency", "optimization"],
        temperature=0.5,
        model_profile="balanced",
        weight=1.0,
    ),
    AgentRole(
        name="UX Strategist",
        role_description="User experience and developer experience analyst",
        expertise="API ergonomics, documentation, developer workflows",
        focus_areas=["usability", "documentation", "developer experience"],
        temperature=0.6,
        model_profile="fast",
        weight=0.8,
    ),
    AgentRole(
        name="ML Theorist",
        role_description="Machine learning theory and formal methods expert",
        expertise="Convergence proofs, generalization bounds, complexity analysis",
        focus_areas=["theoretical guarantees", "mathematical rigor", "generalization"],
        temperature=0.4,
        model_profile="reasoning",
        weight=1.1,
    ),
]

_DEFAULT_CODEGEN_ROLES: list[AgentRole] = [
    AgentRole(
        name="Core Developer",
        role_description="Senior software engineer implementing core logic",
        expertise="Algorithm implementation, data structures, clean code",
        focus_areas=["core logic", "algorithms", "data structures"],
        temperature=0.3,
        model_profile="powerful",
        weight=1.3,
    ),
    AgentRole(
        name="API Designer",
        role_description="API and interface design specialist",
        expertise="REST APIs, CLI interfaces, type systems, contracts",
        focus_areas=["interfaces", "contracts", "ergonomics"],
        temperature=0.4,
        model_profile="balanced",
        weight=1.0,
    ),
    AgentRole(
        name="Test Writer",
        role_description="Test-driven development specialist",
        expertise="pytest, property-based testing, edge cases, mocking",
        focus_areas=["unit tests", "integration tests", "coverage"],
        temperature=0.3,
        model_profile="balanced",
        weight=1.1,
    ),
    AgentRole(
        name="DevOps Engineer",
        role_description="Build, deploy, and configuration specialist",
        expertise="Docker, CI/CD, requirements, packaging, env config",
        focus_areas=["deployment", "configuration", "dependencies"],
        temperature=0.3,
        model_profile="fast",
        weight=0.8,
    ),
    AgentRole(
        name="Data Engineer",
        role_description="Data pipeline and storage specialist",
        expertise="ETL, databases, data validation, serialization",
        focus_areas=["data flow", "storage", "validation"],
        temperature=0.4,
        model_profile="balanced",
        weight=0.9,
    ),
]

_DEFAULT_REVIEW_ROLES: list[AgentRole] = [
    AgentRole(
        name="Security Reviewer",
        role_description="Application security reviewer",
        expertise="OWASP, injection, auth, crypto, input validation",
        focus_areas=["vulnerabilities", "auth", "input sanitization"],
        temperature=0.3,
        model_profile="reasoning",
        weight=1.3,
    ),
    AgentRole(
        name="Correctness Verifier",
        role_description="Logic and correctness verification specialist",
        expertise="Edge cases, off-by-one, null safety, concurrency bugs",
        focus_areas=["logic errors", "edge cases", "correctness"],
        temperature=0.3,
        model_profile="reasoning",
        weight=1.2,
    ),
    AgentRole(
        name="Performance Analyst",
        role_description="Code performance analysis and profiling expert",
        expertise="Big-O, memory leaks, I/O bottlenecks, caching",
        focus_areas=["performance", "memory", "scalability"],
        temperature=0.4,
        model_profile="balanced",
        weight=1.0,
    ),
    AgentRole(
        name="Maintainability Reviewer",
        role_description="Code quality and maintainability expert",
        expertise="SOLID, DRY, readability, documentation, naming",
        focus_areas=["readability", "documentation", "code structure"],
        temperature=0.4,
        model_profile="fast",
        weight=0.8,
    ),
    AgentRole(
        name="API Contract Checker",
        role_description="Interface contract and type safety reviewer",
        expertise="Type annotations, API contracts, schema validation",
        focus_areas=["types", "contracts", "schema consistency"],
        temperature=0.3,
        model_profile="balanced",
        weight=1.0,
    ),
]

_DEFAULT_TEST_ROLES: list[AgentRole] = [
    AgentRole(
        name="Unit Test Designer",
        role_description="Unit testing specialist",
        expertise="pytest, fixtures, parametrize, mocking, assertions",
        focus_areas=["function-level tests", "isolation", "coverage"],
        temperature=0.3,
        model_profile="balanced",
        weight=1.2,
    ),
    AgentRole(
        name="Integration Tester",
        role_description="Integration and system testing specialist",
        expertise="End-to-end flows, API testing, database testing",
        focus_areas=["whole-system tests", "API flows", "data integrity"],
        temperature=0.4,
        model_profile="balanced",
        weight=1.1,
    ),
    AgentRole(
        name="Edge Case Hunter",
        role_description="Adversarial testing and edge case specialist",
        expertise="Boundary values, null inputs, concurrency, large inputs",
        focus_areas=["edge cases", "error paths", "adversarial inputs"],
        temperature=0.5,
        model_profile="reasoning",
        weight=1.0,
    ),
    AgentRole(
        name="Security Tester",
        role_description="Security testing and penetration testing specialist",
        expertise="Fuzzing, injection testing, auth bypass, privilege escalation",
        focus_areas=["security tests", "fuzzing", "privilege checks"],
        temperature=0.4,
        model_profile="reasoning",
        weight=1.3,
    ),
]

_DEFAULT_RESEARCH_ROLES: list[AgentRole] = [
    AgentRole(
        name="Paper Analyst",
        role_description="Academic literature analysis expert",
        expertise="arXiv, citation networks, methodology assessment",
        focus_areas=["papers", "methods", "results", "limitations"],
        temperature=0.5,
        model_profile="balanced",
        weight=1.0,
    ),
    AgentRole(
        name="Industry Surveyor",
        role_description="Industry practice and deployment analyst",
        expertise="Production systems, industry trends, best practices",
        focus_areas=["deployments", "industry trends", "tooling"],
        temperature=0.6,
        model_profile="balanced",
        weight=0.9,
    ),
    AgentRole(
        name="Benchmark Scout",
        role_description="Dataset and benchmark assessment specialist",
        expertise="Evaluation metrics, benchmark suites, data quality",
        focus_areas=["benchmarks", "metrics", "datasets"],
        temperature=0.5,
        model_profile="fast",
        weight=0.8,
    ),
    AgentRole(
        name="Competitive Analyst",
        role_description="Competitive landscape and patent analyst",
        expertise="Competitor analysis, patent search, IP landscape",
        focus_areas=["competitors", "patents", "market gaps"],
        temperature=0.6,
        model_profile="fast",
        weight=0.7,
    ),
]

_DEFAULT_GENERAL_ROLES: list[AgentRole] = [
    AgentRole(
        name="Generalist",
        role_description="Versatile problem solver",
        expertise="Broad engineering knowledge, problem decomposition",
        focus_areas=["problem solving", "design", "implementation"],
        temperature=0.5,
        model_profile="balanced",
        weight=1.0,
    ),
    AgentRole(
        name="Critic",
        role_description="Quality and correctness reviewer",
        expertise="Code review, logical reasoning, edge case analysis",
        focus_areas=["correctness", "quality", "edge cases"],
        temperature=0.4,
        model_profile="reasoning",
        weight=1.1,
    ),
]


# ---------------------------------------------------------------------------
# JSON helper
# ---------------------------------------------------------------------------

def _try_parse_json(text: str) -> Any:
    """Try to extract JSON from text.  Returns parsed object or None."""
    import json
    import re

    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)

    # Try direct parse
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to find JSON object/array in text
    for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except (json.JSONDecodeError, ValueError):
                continue

    return None
