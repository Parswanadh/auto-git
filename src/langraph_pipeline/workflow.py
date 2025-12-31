"""
LangGraph Workflow for Auto-GIT

Defines the state graph that orchestrates the entire pipeline.
Uses LangGraph's StateGraph for production-grade orchestration.
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AutoGITState, create_initial_state
from .nodes import (
    research_node,
    problem_extraction_node,
    solution_generation_node,
    critique_node,
    consensus_check_node,
    solution_selection_node,
    code_generation_node,
    code_testing_node,
    git_publishing_node
)

logger = logging.getLogger(__name__)


def should_continue_debate(state: AutoGITState) -> Literal["continue", "select"]:
    """
    Routing function: Decide whether to continue debate or select solution
    
    Returns:
        "continue": Go back to solution generation for another round
        "select": Move to solution selection
    """
    current_stage = state.get("current_stage", "")
    
    if current_stage == "consensus_reached":
        logger.info("  → Routing to: solution_selection")
        return "select"
    elif current_stage == "max_rounds_reached":
        logger.info("  → Routing to: solution_selection (max rounds)")
        return "select"
    else:  # continue_debate
        logger.info("  → Routing to: solution_generation (next round)")
        return "continue"


def build_workflow() -> StateGraph:
    """
    Build the LangGraph StateGraph workflow
    
    Flow:
    1. Research (web search)
    2. Problem Extraction
    3. Solution Generation → Critique → Consensus Check
       └─ (loop back to 3 if no consensus)
    4. Solution Selection
    5. Code Generation
    6. Git Publishing
    
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("🏗️  Building LangGraph workflow...")
    
    # Create the graph
    workflow = StateGraph(AutoGITState)
    
    # Add nodes
    workflow.add_node("research", research_node)
    workflow.add_node("problem_extraction", problem_extraction_node)
    workflow.add_node("solution_generation", solution_generation_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("consensus_check", consensus_check_node)
    workflow.add_node("solution_selection", solution_selection_node)
    workflow.add_node("code_generation", code_generation_node)
    workflow.add_node("code_testing", code_testing_node)
    workflow.add_node("git_publishing", git_publishing_node)
    
    # Define the flow
    workflow.set_entry_point("research")
    
    # Linear flow through research and problem extraction
    workflow.add_edge("research", "problem_extraction")
    workflow.add_edge("problem_extraction", "solution_generation")
    
    # Debate loop
    workflow.add_edge("solution_generation", "critique")
    workflow.add_edge("critique", "consensus_check")
    
    # Conditional routing from consensus_check
    workflow.add_conditional_edges(
        "consensus_check",
        should_continue_debate,
        {
            "continue": "solution_generation",  # Loop back for another round
            "select": "solution_selection"      # Move to selection
        }
    )
    
    # Final flow
    workflow.add_edge("solution_selection", "code_generation")
    workflow.add_edge("code_generation", "code_testing")
    workflow.add_edge("code_testing", "git_publishing")
    workflow.add_edge("git_publishing", END)
    
    logger.info("✅ LangGraph workflow built successfully")
    
    return workflow


def compile_workflow() -> StateGraph:
    """
    Compile the workflow with memory persistence
    
    Returns:
        Compiled workflow ready for execution
    """
    workflow = build_workflow()
    
    # Add memory saver for checkpointing
    memory = MemorySaver()
    compiled_workflow = workflow.compile(checkpointer=memory)
    
    logger.info("✅ Workflow compiled with memory checkpointing")
    
    return compiled_workflow


async def run_auto_git_pipeline(
    idea: str,
    user_requirements: str = None,
    use_web_search: bool = True,
    max_rounds: int = 3,
    min_consensus: float = 0.7,
    thread_id: str = "default"
) -> AutoGITState:
    """
    Run the complete Auto-GIT pipeline
    
    Args:
        idea: Research idea or topic
        user_requirements: Optional additional requirements
        use_web_search: Enable web search
        max_rounds: Maximum debate rounds
        min_consensus: Minimum consensus score
        thread_id: Thread ID for checkpointing
        
    Returns:
        Final state after pipeline execution
    """
    logger.info(f"🚀 Starting Auto-GIT pipeline for: {idea}")
    
    # Create initial state
    initial_state = create_initial_state(
        idea=idea,
        user_requirements=user_requirements,
        use_web_search=use_web_search,
        max_rounds=max_rounds,
        min_consensus=min_consensus
    )
    
    # Compile workflow
    workflow = compile_workflow()
    
    # Configure execution
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    # Run the pipeline
    logger.info("▶️  Executing pipeline...")
    
    try:
        final_state = None
        async for state in workflow.astream(initial_state, config):
            # state is a dict with node names as keys
            # Get the last state update
            for node_name, node_state in state.items():
                current_stage = node_state.get("current_stage", "unknown")
                logger.info(f"  📍 Node: {node_name} | Stage: {current_stage}")
                final_state = node_state
        
        logger.info("✅ Pipeline execution complete!")
        
        return final_state
        
    except Exception as e:
        logger.error(f"❌ Pipeline execution failed: {e}")
        raise


# ============================================
# Visualization & Debugging
# ============================================

def visualize_workflow():
    """
    Generate a visualization of the workflow graph
    
    Requires: pip install pygraphviz
    """
    try:
        from IPython.display import Image, display
        
        workflow = build_workflow()
        compiled = workflow.compile()
        
        # Generate graph image
        img = compiled.get_graph().draw_mermaid_png()
        
        with open("workflow_graph.png", "wb") as f:
            f.write(img)
        
        logger.info("✅ Workflow visualization saved to workflow_graph.png")
        
        return img
        
    except ImportError:
        logger.warning("pygraphviz not installed. Cannot visualize workflow.")
        logger.info("Install with: pip install pygraphviz")
        return None


def print_workflow_structure():
    """Print the workflow structure as text"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    Auto-GIT LangGraph Pipeline                ║
╚══════════════════════════════════════════════════════════════╝

    START
      │
      ▼
┌─────────────────┐
│   1. Research   │  🔍 Web search (arXiv + DuckDuckGo)
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ 2. Problem Extract  │  🎯 Identify novel problems
└─────────┬───────────┘
          │
          ▼
    ╔═══════════════════╗
    ║   DEBATE LOOP     ║
    ╠═══════════════════╣
    ║ 3. Solution Gen   ║  💡 Multi-perspective proposals
    ║        │          ║     (ML Researcher, Systems Engineer,
    ║        ▼          ║      Applied Scientist)
    ║ 4. Critique       ║  🔍 Cross-perspective review
    ║        │          ║
    ║        ▼          ║
    ║ 5. Consensus?     ║  ⚖️  Check agreement
    ║        │          ║
    ║    ┌───┴───┐      ║
    ║    No      Yes    ║
    ║    │       │      ║
    ║    └───────┘      ║
    ╚═══════════════════╝
          │
          ▼
┌──────────────────────┐
│ 6. Solution Select   │  🏆 Pick best proposal
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 7. Code Generation   │  💻 Implement with DeepSeek
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 8. Git Publishing    │  📤 Push to GitHub
└──────────┬───────────┘
           │
           ▼
          END

═══════════════════════════════════════════════════════════════

Key Features:
✓ Multi-perspective debate (STORM-inspired)
✓ Web search integration (DuckDuckGo + arXiv)
✓ Production-grade orchestration (LangGraph)
✓ State persistence & checkpointing
✓ Conditional routing & loops

""")


if __name__ == "__main__":
    # Print workflow structure
    print_workflow_structure()
    
    # Build and validate workflow
    logging.basicConfig(level=logging.INFO)
    workflow = build_workflow()
    compiled = compile_workflow()
    
    print("✅ Workflow compilation successful!")
    print("\nTo run the pipeline:")
    print("  from src.langraph_pipeline.workflow import run_auto_git_pipeline")
    print("  await run_auto_git_pipeline('Your research idea')")
