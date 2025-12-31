"""
Solution Generator Agent
Proposes novel solutions to research problems.
"""

import json
from typing import List

from src.models.schemas import ProblemStatement, SolutionProposal
from src.utils.logger import get_logger
from src.utils.ollama_client import get_ollama_client
from src.utils.json_parser import safe_parse_solutions
from src.agents.tier2_debate.prompts import get_solution_generator_prompt
from src.pipeline.state import AgentState, add_warning

logger = get_logger("solution_generator")


async def generate_solutions(
    problem: ProblemStatement,
    iteration: int = 1,
    previous_critique: str = None
) -> List[SolutionProposal]:
    """
    Generate novel solutions to a problem.
    
    Args:
        problem: Problem statement
        iteration: Which iteration (1, 2, 3)
        previous_critique: Feedback from critic (if any)
    
    Returns:
        List of solution proposals
    """
    logger.info(f"💡 Generating solutions (iteration {iteration})...")
    
    client = get_ollama_client()
    
    # Use centralized prompt
    prompt = get_solution_generator_prompt(problem, iteration, previous_critique)

    try:
        response = await client.generate(
            model="qwen3:4b",  # 262K context for debate history
            prompt=prompt,
            temperature=0.8  # Higher for creativity
        )
        
        content = response.get("content", "")  # ollama_client uses "content" not "response"
        
        # Log what we got for debugging
        logger.info("="*60)
        logger.info(f"RAW OUTPUT FROM QWEN3:4B ({len(content)} chars):")
        logger.info(content[:500] if len(content) > 500 else content)
        logger.info("="*60)
        
        # Use robust parser
        solutions_data = safe_parse_solutions(content, iteration)
        
        if not solutions_data:
            logger.error("No valid solutions parsed from response")
            return []
        
        # Create SolutionProposal objects
        solutions = []
        for i, sol_data in enumerate(solutions_data[:3], 1):  # Max 3
            try:
                solution = SolutionProposal(**sol_data)
                solutions.append(solution)
                logger.info(f"  {i}. {solution.approach_name}")
            except Exception as e:
                logger.warning(f"Failed to create solution {i}: {e}")
                continue
        
        logger.info(f"✅ Generated {len(solutions)} solutions")
        return solutions
        
    except Exception as e:
        logger.error(f"Solution generation failed: {e}")
        return []


async def solution_generator_node(state: AgentState) -> AgentState:
    """
    LangGraph node for solution generation.
    
    Args:
        state: Pipeline state
    
    Returns:
        Updated state with solution_proposals
    """
    problem = state.get("problem_statement")
    if not problem:
        logger.error("No problem statement in state")
        return state
    
    iteration = state.get("debate_iteration", 1)
    previous_critique = state.get("latest_critique")
    
    solutions = await generate_solutions(problem, iteration, previous_critique)
    
    if solutions:
        state["solution_proposals"] = solutions
        logger.info(f"✅ Proposed {len(solutions)} solutions")
    else:
        state = add_warning(state, "Solution generation failed", tier=2)
    
    return state
