"""
LangGraph State Management for Auto-GIT

Defines the state schema that flows through the entire pipeline.
Uses TypedDict for type safety and clarity.
"""

from typing import TypedDict, List, Dict, Optional, Annotated, Literal, Any
from datetime import datetime
import operator


class PaperMetadata(TypedDict):
    """Metadata for a research paper"""
    title: str
    authors: List[str]
    summary: str
    pdf_url: str
    published: str
    categories: List[str]


class WebResult(TypedDict):
    """Web search result"""
    title: str
    href: str
    body: str


class ResearchContext(TypedDict):
    """Research context from web searches"""
    papers: List[PaperMetadata]
    web_results: List[WebResult]
    implementations: List[WebResult]
    search_timestamp: str


class SolutionProposal(TypedDict):
    """A proposed solution from one perspective"""
    approach_name: str
    perspective: str  # ML Researcher, Systems Engineer, etc.
    key_innovation: str
    architecture_design: str
    implementation_plan: List[str]
    expected_advantages: List[str]
    potential_challenges: List[str]
    novelty_score: float
    feasibility_score: float


class Critique(TypedDict):
    """Critique of a solution proposal"""
    solution_id: str
    reviewer_perspective: str
    overall_assessment: Literal["promising", "needs-work", "flawed"]
    strengths: List[str]
    weaknesses: List[str]
    specific_concerns: List[str]
    improvement_suggestions: List[str]
    feasibility_score: float
    recommendation: Literal["accept", "revise", "reject"]


class DebateRound(TypedDict):
    """One round of debate"""
    round_number: int
    proposals: List[SolutionProposal]
    critiques: List[Critique]
    consensus_reached: bool
    round_summary: str


class GeneratedCode(TypedDict):
    """Generated implementation code"""
    file_name: str
    code: str
    language: str
    description: str
    dependencies: List[str]


class AutoGITState(TypedDict):
    """
    Main state that flows through the LangGraph pipeline
    
    This is the central data structure that each node reads from and writes to.
    LangGraph automatically manages state updates and persistence.
    """
    
    # Input
    idea: str
    user_requirements: Optional[str]
    requirements: Optional[Dict[str, Any]]  # Structured requirements from conversation agent
    
    # Research Context
    research_context: Optional[ResearchContext]
    related_work_summary: Optional[str]
    
    # Problem Extraction
    problems: List[str]
    selected_problem: Optional[str]
    
    # Multi-Perspective Debate
    debate_rounds: Annotated[List[DebateRound], operator.add]  # Append-only
    current_round: int
    max_rounds: int
    perspectives: List[str]  # Active expert perspectives
    
    # Solution Selection
    final_solution: Optional[SolutionProposal]
    selection_reasoning: Optional[str]
    
    # Code Generation
    generated_code: List[GeneratedCode]
    implementation_notes: Optional[str]
    
    # Code Testing
    test_results: Optional[Dict[str, Any]]
    tests_passed: bool
    fix_attempts: int  # Number of times we've tried to fix code
    max_fix_attempts: int  # Maximum fix attempts before giving up
    
    # Git Publishing
    repo_name: Optional[str]
    commit_message: Optional[str]
    published: bool
    publication_url: Optional[str]
    
    # Metadata
    pipeline_start_time: str
    current_stage: str
    errors: Annotated[List[str], operator.add]  # Append-only error log
    warnings: Annotated[List[str], operator.add]  # Append-only warning log
    
    # Configuration
    use_web_search: bool
    max_debate_rounds: int
    min_consensus_score: float


class PerspectiveConfig(TypedDict):
    """Configuration for expert perspectives"""
    name: str
    role: str
    expertise: str
    focus_areas: List[str]
    evaluation_criteria: List[str]


# Expert Perspectives (from STORM paper)
EXPERT_PERSPECTIVES: List[PerspectiveConfig] = [
    {
        "name": "ML Researcher",
        "role": "Machine Learning Research Scientist",
        "expertise": "Deep learning architectures, training methodologies, theoretical foundations",
        "focus_areas": ["novelty", "theoretical soundness", "empirical validation", "scalability"],
        "evaluation_criteria": [
            "Is the approach theoretically grounded?",
            "Does it advance the state-of-the-art?",
            "Are the claims supported by evidence?",
            "How does it compare to existing methods?"
        ]
    },
    {
        "name": "Systems Engineer",
        "role": "ML Systems Engineer",
        "expertise": "Production ML systems, optimization, deployment, infrastructure",
        "focus_areas": ["implementation feasibility", "computational efficiency", "production readiness", "maintainability"],
        "evaluation_criteria": [
            "Can this be implemented efficiently?",
            "What are the computational costs?",
            "Is it production-ready?",
            "How maintainable is the system?"
        ]
    },
    {
        "name": "Applied Scientist",
        "role": "Applied ML Scientist",
        "expertise": "Real-world applications, practical constraints, user impact",
        "focus_areas": ["practical utility", "real-world applicability", "user impact", "deployment challenges"],
        "evaluation_criteria": [
            "Does it solve a real problem?",
            "What are the practical limitations?",
            "How easy is it to adopt?",
            "What's the impact on end-users?"
        ]
    }
]


def create_initial_state(
    idea: str,
    user_requirements: Optional[str] = None,
    requirements: Optional[Dict[str, Any]] = None,
    use_web_search: bool = True,
    max_rounds: int = 3,
    min_consensus: float = 0.7
) -> AutoGITState:
    """
    Create initial state for the LangGraph pipeline
    
    Args:
        idea: The research idea or topic
        user_requirements: Optional additional requirements
        requirements: Structured requirements from conversation agent (IMPORTANT!)
        use_web_search: Whether to use web search
        max_rounds: Maximum debate rounds
        min_consensus: Minimum consensus score to stop debate
        
    Returns:
        Initial AutoGITState
    """
    return AutoGITState(
        # Input
        idea=idea,
        user_requirements=user_requirements,
        requirements=requirements,  # Pass structured requirements
        
        # Research Context
        research_context=None,
        related_work_summary=None,
        
        # Problem Extraction
        problems=[],
        selected_problem=None,
        
        # Multi-Perspective Debate
        debate_rounds=[],
        current_round=0,
        max_rounds=max_rounds,
        perspectives=[p["name"] for p in EXPERT_PERSPECTIVES],
        
        # Solution Selection
        final_solution=None,
        selection_reasoning=None,
        
        # Code Generation
        generated_code=[],
        implementation_notes=None,
        
        # Code Testing
        test_results=None,
        tests_passed=True,
        fix_attempts=0,
        max_fix_attempts=6,  # Try to fix up to 6 times  # Default to True
        
        # Git Publishing
        repo_name=None,
        commit_message=None,
        published=False,
        publication_url=None,
        
        # Metadata
        pipeline_start_time=datetime.now().isoformat(),
        current_stage="initialized",
        errors=[],
        warnings=[],
        
        # Configuration
        use_web_search=use_web_search,
        max_debate_rounds=max_rounds,
        min_consensus_score=min_consensus
    )


def get_perspective_by_name(name: str) -> Optional[PerspectiveConfig]:
    """Get perspective configuration by name"""
    for perspective in EXPERT_PERSPECTIVES:
        if perspective["name"] == name:
            return perspective
    return None
