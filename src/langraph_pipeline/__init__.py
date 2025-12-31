"""
LangGraph Pipeline for Auto-GIT

Production-grade orchestration using LangGraph with:
- Multi-perspective debate system
- Web search integration
- State persistence
- Ollama LLM integration
"""

from .state import (
    AutoGITState,
    create_initial_state,
    EXPERT_PERSPECTIVES,
    PerspectiveConfig,
    SolutionProposal,
    Critique,
    DebateRound
)

from .workflow import (
    build_workflow,
    compile_workflow,
    run_auto_git_pipeline,
    print_workflow_structure
)

from .nodes import (
    research_node,
    problem_extraction_node,
    solution_generation_node,
    critique_node,
    consensus_check_node,
    solution_selection_node,
    code_generation_node,
    git_publishing_node
)

from .integrated_workflow import (
    build_integrated_workflow,
    compile_integrated_workflow,
    run_integrated_pipeline,
    print_integrated_workflow_structure
)

from .integrated_nodes import (
    enhanced_research_node,
    memory_retrieval_node,
    persona_solution_generation_node,
    persona_critique_node,
    weighted_consensus_node,
    store_experience_node
)

__all__ = [
    # State
    "AutoGITState",
    "create_initial_state",
    "EXPERT_PERSPECTIVES",
    "PerspectiveConfig",
    "SolutionProposal",
    "Critique",
    "DebateRound",
    
    # Workflow
    "build_workflow",
    "compile_workflow",
    "run_auto_git_pipeline",
    "print_workflow_structure",
    
    # Nodes
    "research_node",
    "problem_extraction_node",
    "solution_generation_node",
    "critique_node",
    "consensus_check_node",
    "solution_selection_node",
    "code_generation_node",
    "git_publishing_node",

    # Integrated Workflow (Single-Model Multi-Agent)
    "build_integrated_workflow",
    "compile_integrated_workflow",
    "run_integrated_pipeline",
    "print_integrated_workflow_structure",

    # Integrated Nodes
    "enhanced_research_node",
    "memory_retrieval_node",
    "persona_solution_generation_node",
    "persona_critique_node",
    "weighted_consensus_node",
    "store_experience_node",
]
