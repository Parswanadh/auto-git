"""
LangGraph Pipeline Nodes for Auto-GIT

Each node is a function that takes the current state and returns updates.
LangGraph handles the orchestration and state management.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from rich.console import Console

# Load environment variables from .env file
load_dotenv()

from ..utils.web_search import ResearchSearcher
from .state import (
    AutoGITState,
    ResearchContext,
    SolutionProposal,
    Critique,
    DebateRound,
    EXPERT_PERSPECTIVES,
    get_perspective_by_name
)
from ..utils.json_parser import extract_json_from_text, safe_parse_solutions

logger = logging.getLogger(__name__)


# ============================================
# Node 1: Research & Context Gathering
# ============================================

async def research_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 1: Gather research context using web search
    
    Searches arXiv and web for related papers and implementations.
    This enriches the context before problem extraction.
    """
    idea = state['idea']
    logger.info(f"🔍 Research Node: Searching for '{idea}'")
    
    # Show to user what we're searching for
    console = Console()
    console.print(f"\n[cyan]🔍 Searching for:[/cyan] [bold]{idea}[/bold]")
    
    if not state.get("use_web_search", True):
        logger.info("Web search disabled, skipping research")
        return {
            "current_stage": "research_skipped",
            "research_context": None
        }
    
    try:
        # Search using ResearchSearcher
        console.print(f"[dim]  • Searching arXiv papers...[/dim]")
        console.print(f"[dim]  • Searching web resources...[/dim]")
        console.print(f"[dim]  • Finding implementations...[/dim]\\n")
        
        searcher = ResearchSearcher(max_arxiv=5, max_web=5)
        results = searcher.search_comprehensive(idea)
        
        # Create research context
        research_context: ResearchContext = {
            "papers": results["papers"],
            "web_results": results["web_results"],
            "implementations": results["implementations"],
            "search_timestamp": datetime.now().isoformat()
        }
        
        # Generate summary
        summary = f"""
        Found {len(results['papers'])} research papers
        Found {len(results['web_results'])} web results
        Found {len(results['implementations'])} implementation examples
        """
        
        logger.info(f"✅ Research complete: {len(results['papers'])} papers, {len(results['web_results'])} web results")
        
        # Show summary to user
        if len(results['papers']) == 0 and len(results['web_results']) == 0:
            console.print(f"[yellow]⚠️  No results found. This may be due to:[/yellow]")
            console.print(f"[dim]  • Network connectivity issues[/dim]")
            console.print(f"[dim]  • Search query too specific[/dim]")
            console.print(f"[dim]  • Rate limiting from search providers[/dim]")
            console.print(f"[dim]Continuing with pipeline anyway...\\n[/dim]")
        else:
            console.print(f"[green]✅ Found:[/green] [bold]{len(results['papers'])}[/bold] papers, [bold]{len(results['web_results'])}[/bold] web results\\n")
        
        return {
            "current_stage": "research_complete",
            "research_context": research_context,
            "related_work_summary": summary.strip()
        }
        
    except Exception as e:
        logger.error(f"Research node failed: {e}")
        return {
            "current_stage": "research_failed",
            "errors": [f"Research failed: {str(e)}"],
            "research_context": None
        }


# ============================================
# Node 2: Problem Extraction
# ============================================

async def problem_extraction_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 2: Extract research problems from the idea + research context
    
    IMPORTANT: Uses the user's ACTUAL requirements from conversation agent
    """
    logger.info("🎯 Problem Extraction Node")
    
    try:
        # Get requirements from conversation agent (if available)
        requirements = state.get("requirements", {})
        core_idea = requirements.get("core_idea", state['idea'])
        target_task = requirements.get("target_task", "")
        model_type = requirements.get("model_type", "")
        approach = requirements.get("approach", "")
        
        # Build problem statement from actual user requirements
        if requirements:
            problem_statement = f"Build {core_idea}"
            if target_task:
                problem_statement = f"{target_task}: {core_idea}"
            
            problems = [problem_statement]
            selected_problem = problem_statement
            
            logger.info(f"✅ Using user's actual requirement: {selected_problem}")
            
            return {
                "current_stage": "problems_extracted",
                "problems": problems,
                "selected_problem": selected_problem
            }
        
        # Fallback: Use LLM extraction if no requirements
        llm = ChatOllama(
            model="qwen3:4b",
            temperature=0.7,
            base_url="http://localhost:11434"
        )
        
        # Build context from research
        context = ""
        if state.get("research_context"):
            searcher = ResearchSearcher()
            context = searcher.format_papers_for_prompt(state["research_context"]["papers"])
            context += "\n\n" + searcher.format_web_results_for_prompt(state["research_context"]["implementations"])
        
        # Create prompt
        system_prompt = """You are a research problem extraction expert. Your task is to identify novel, 
interesting research problems based on an idea and existing work.

Focus on:
1. Gaps in current research
2. Practical limitations of existing methods
3. Emerging opportunities
4. Unsolved challenges

Output format (JSON array):
[
  "Problem 1: Clear, specific problem statement",
  "Problem 2: Another distinct problem",
  "Problem 3: ..."
]"""
        
        user_prompt = f"""Idea: {state['idea']}

{context}

Based on the idea and related work above, identify 3-5 novel research problems worth solving.
Each problem should be specific, well-scoped, and not already solved by existing work.

Return ONLY a JSON array of problem statements."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await llm.ainvoke(messages)
        
        # Parse response
        problems_text = response.content
        problems_json = extract_json_from_text(problems_text)
        
        if isinstance(problems_json, list):
            problems = problems_json
        else:
            problems = [problems_json.get("problems", [])]
        
        logger.info(f"✅ Extracted {len(problems)} problems")
        
        # Select first problem for now (could be enhanced with ranking)
        selected_problem = problems[0] if problems else None
        
        return {
            "current_stage": "problems_extracted",
            "problems": problems,
            "selected_problem": selected_problem
        }
        
    except Exception as e:
        logger.error(f"Problem extraction failed: {e}")
        return {
            "current_stage": "problem_extraction_failed",
            "errors": [f"Problem extraction failed: {str(e)}"],
            "problems": [],
            "selected_problem": None
        }


# ============================================
# Node 3: Multi-Perspective Solution Generation
# ============================================

async def solution_generation_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 3: Generate solutions from multiple expert perspectives
    
    Each perspective (ML Researcher, Systems Engineer, Applied Scientist)
    proposes solutions based on their expertise.
    """
    logger.info(f"💡 Solution Generation Node (Round {state['current_round'] + 1})")
    
    try:
        llm = ChatOllama(
            model="qwen3:4b",
            temperature=0.8,
            base_url="http://localhost:11434"
        )
        
        problem = state["selected_problem"]
        proposals: List[SolutionProposal] = []
        
        # Create console for user feedback
        console = Console()
        
        # Generate solutions from each perspective
        for perspective_name in state["perspectives"]:
            perspective = get_perspective_by_name(perspective_name)
            if not perspective:
                continue
            
            # Show to user which agent is working
            console.print(f"  [cyan]🧠 {perspective['name']}:[/cyan] [dim]Proposing solution...[/dim]")
            
            logger.info(f"  📝 Generating solution from: {perspective['name']}")
            
            system_prompt = f"""You are a {perspective['role']}.

Your expertise: {perspective['expertise']}
Your focus areas: {', '.join(perspective['focus_areas'])}

Propose a solution to the research problem from your expert perspective.
Consider your specific focus areas and evaluation criteria.

Output format (JSON):
{{
  "approach_name": "Descriptive name for your approach",
  "key_innovation": "Core novel contribution",
  "architecture_design": "High-level architecture description",
  "implementation_plan": ["Step 1", "Step 2", "..."],
  "expected_advantages": ["Advantage 1", "..."],
  "potential_challenges": ["Challenge 1", "..."],
  "novelty_score": 0.0-1.0,
  "feasibility_score": 0.0-1.0
}}"""
            
            user_prompt = f"""Problem: {problem}

Propose a solution from your perspective as a {perspective['role']}.
Focus on: {', '.join(perspective['focus_areas'])}

Return ONLY valid JSON."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await llm.ainvoke(messages)
            
            # Parse solution
            solution_json = extract_json_from_text(response.content)
            
            if solution_json and isinstance(solution_json, dict):
                solution: SolutionProposal = {
                    "approach_name": solution_json.get("approach_name", "Unnamed Approach"),
                    "perspective": perspective_name,
                    "key_innovation": solution_json.get("key_innovation", ""),
                    "architecture_design": solution_json.get("architecture_design", ""),
                    "implementation_plan": solution_json.get("implementation_plan", []),
                    "expected_advantages": solution_json.get("expected_advantages", []),
                    "potential_challenges": solution_json.get("potential_challenges", []),
                    "novelty_score": float(solution_json.get("novelty_score", 0.5)),
                    "feasibility_score": float(solution_json.get("feasibility_score", 0.5))
                }
                proposals.append(solution)
                # Show generated solution to user
                console.print(f"    [green]✓[/green] [bold]{solution['approach_name']}[/bold]")
                console.print(f"       [dim]{solution['key_innovation'][:80]}...[/dim]")
                logger.info(f"    ✅ Generated: {solution['approach_name']}")
        
        logger.info(f"✅ Generated {len(proposals)} solutions from {len(state['perspectives'])} perspectives")
        
        return {
            "current_stage": "solutions_generated",
            "current_round": state["current_round"] + 1,
            "debate_rounds": [{
                "round_number": state["current_round"] + 1,
                "proposals": proposals,
                "critiques": [],
                "consensus_reached": False,
                "round_summary": f"Generated {len(proposals)} proposals"
            }]
        }
        
    except Exception as e:
        logger.error(f"Solution generation failed: {e}")
        return {
            "current_stage": "solution_generation_failed",
            "errors": [f"Solution generation failed: {str(e)}"]
        }


# ============================================
# Node 4: Multi-Perspective Critique
# ============================================

async def critique_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 4: Each perspective critiques all proposals
    
    Cross-perspective review to identify strengths and weaknesses.
    """
    logger.info("🔍 Critique Node: Multi-perspective review")
    
    try:
        llm = ChatOllama(
            model="qwen3:4b",
            temperature=0.3,  # Lower temperature for more objective critique
            base_url="http://localhost:11434"
        )
        
        # Get current round's proposals
        current_round = state["debate_rounds"][-1]
        proposals = current_round["proposals"]
        all_critiques: List[Critique] = []
        
        # Create console for user feedback
        console = Console()
        
        # Each perspective reviews ALL proposals (including their own)
        for reviewer_perspective_name in state["perspectives"]:
            reviewer = get_perspective_by_name(reviewer_perspective_name)
            if not reviewer:
                continue
            
            # Show which agent is reviewing
            console.print(f"\n  [magenta]🔍 {reviewer['name']}:[/magenta] [dim]Reviewing {len(proposals)} proposals...[/dim]")
            logger.info(f"  🔍 {reviewer['name']} reviewing {len(proposals)} proposals")
            
            for proposal in proposals:
                # Skip self-review (or enable for self-critique?)
                if proposal["perspective"] == reviewer_perspective_name:
                    continue
                
                system_prompt = f"""You are a {reviewer['role']} reviewing a proposed solution.

Your expertise: {reviewer['expertise']}
Evaluation criteria: {', '.join(reviewer['evaluation_criteria'])}

Provide constructive critique focusing on:
- Technical feasibility
- Potential issues
- Improvement suggestions

Output format (JSON):
{{
  "overall_assessment": "promising" | "needs-work" | "flawed",
  "strengths": ["Strength 1", "..."],
  "weaknesses": ["Weakness 1", "..."],
  "specific_concerns": ["Concern 1", "..."],
  "improvement_suggestions": ["Suggestion 1", "..."],
  "feasibility_score": 0.0-1.0,
  "recommendation": "accept" | "revise" | "reject"
}}"""
                
                user_prompt = f"""Review this proposal:

Approach: {proposal['approach_name']}
Innovation: {proposal['key_innovation']}
Architecture: {proposal['architecture_design']}
Implementation: {', '.join(proposal['implementation_plan'][:3])}...

From your perspective as {reviewer['role']}, provide a detailed critique.
Return ONLY valid JSON."""
                
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                response = await llm.ainvoke(messages)
                critique_json = extract_json_from_text(response.content)
                
                if critique_json and isinstance(critique_json, dict):
                    critique: Critique = {
                        "solution_id": proposal["approach_name"],
                        "reviewer_perspective": reviewer_perspective_name,
                        "overall_assessment": critique_json.get("overall_assessment", "needs-work"),
                        "strengths": critique_json.get("strengths", []),
                        "weaknesses": critique_json.get("weaknesses", []),
                        "specific_concerns": critique_json.get("specific_concerns", []),
                        "improvement_suggestions": critique_json.get("improvement_suggestions", []),
                        "feasibility_score": float(critique_json.get("feasibility_score", 0.5)),
                        "recommendation": critique_json.get("recommendation", "revise")
                    }
                    all_critiques.append(critique)
                    
                    # Show critique assessment to user
                    recommendation = critique["recommendation"]
                    if recommendation == "accept":
                        console.print(f"    [green]✓[/green] [bold]{proposal['approach_name'][:50]}[/bold]: [green]Accept[/green]")
                    elif recommendation == "revise":
                        console.print(f"    [yellow]⚠[/yellow] [bold]{proposal['approach_name'][:50]}[/bold]: [yellow]Revise[/yellow]")
                    else:
                        console.print(f"    [red]×[/red] [bold]{proposal['approach_name'][:50]}[/bold]: [red]Reject[/red]")
                    
                    logger.info(f"    ✅ {reviewer['name']}: {critique['overall_assessment']} ({critique['recommendation']})")
        
        # Update current round with critiques
        updated_round = current_round.copy()
        updated_round["critiques"] = all_critiques
        updated_round["round_summary"] = f"{len(proposals)} proposals, {len(all_critiques)} critiques"
        
        # Update state (replace last round)
        updated_rounds = state["debate_rounds"][:-1] + [updated_round]
        
        logger.info(f"✅ Generated {len(all_critiques)} critiques")
        
        return {
            "current_stage": "critiques_complete",
            "debate_rounds": [updated_round]  # LangGraph will append this
        }
        
    except Exception as e:
        logger.error(f"Critique node failed: {e}")
        return {
            "current_stage": "critique_failed",
            "errors": [f"Critique failed: {str(e)}"]
        }


# ============================================
# Node 5: Consensus Check
# ============================================

def consensus_check_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 5: Check if consensus is reached
    
    Determines if we should continue debating or select the best solution.
    """
    logger.info("⚖️  Consensus Check Node")
    
    current_round = state["debate_rounds"][-1]
    critiques = current_round["critiques"]
    
    # Calculate consensus score (percentage of "accept" recommendations)
    if not critiques:
        consensus_score = 0.0
    else:
        accept_count = sum(1 for c in critiques if c["recommendation"] == "accept")
        consensus_score = accept_count / len(critiques)
    
    consensus_reached = consensus_score >= state["min_consensus_score"]
    max_rounds_reached = state["current_round"] >= state["max_debate_rounds"]
    
    logger.info(f"  Consensus score: {consensus_score:.2f} (threshold: {state['min_consensus_score']})")
    logger.info(f"  Round: {state['current_round']}/{state['max_debate_rounds']}")
    
    if consensus_reached:
        logger.info("✅ Consensus reached!")
        return {
            "current_stage": "consensus_reached"
        }
    elif max_rounds_reached:
        logger.info("⚠️  Max rounds reached, forcing selection")
        return {
            "current_stage": "max_rounds_reached"
        }
    else:
        logger.info("🔄 Continue debate")
        return {
            "current_stage": "continue_debate"
        }


# ============================================
# Node 6: Solution Selection
# ============================================

async def solution_selection_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 6: Select the best solution based on all debate rounds
    
    Analyzes all proposals and critiques to pick the winner.
    """
    logger.info("🏆 Solution Selection Node")
    
    try:
        llm = ChatOllama(
            model="qwen3:4b",
            temperature=0.2,
            base_url="http://localhost:11434"
        )
        
        # Collect all proposals and critiques
        all_proposals = []
        all_critiques = []
        for round_data in state["debate_rounds"]:
            all_proposals.extend(round_data["proposals"])
            all_critiques.extend(round_data["critiques"])
        
        # Build summary
        summary = "# Debate Summary\n\n"
        for i, proposal in enumerate(all_proposals, 1):
            summary += f"\n## Proposal {i}: {proposal['approach_name']}\n"
            summary += f"Perspective: {proposal['perspective']}\n"
            summary += f"Innovation: {proposal['key_innovation']}\n"
            summary += f"Novelty: {proposal['novelty_score']}, Feasibility: {proposal['feasibility_score']}\n"
            
            # Find critiques for this proposal
            proposal_critiques = [c for c in all_critiques if c["solution_id"] == proposal["approach_name"]]
            if proposal_critiques:
                summary += f"Critiques ({len(proposal_critiques)}):\n"
                for critique in proposal_critiques:
                    summary += f"  - {critique['reviewer_perspective']}: {critique['overall_assessment']} ({critique['recommendation']})\n"
        
        system_prompt = """You are an expert research evaluator. Review all proposals and critiques to select the best solution.

Consider:
- Technical merit and novelty
- Feasibility and practicality
- Consensus across perspectives
- Balance of innovation and implementability

Output format (JSON):
{
  "selected_approach": "Name of selected approach",
  "reasoning": "Detailed explanation of selection",
  "confidence": 0.0-1.0
}"""
        
        user_prompt = f"""{summary}

Based on the debate above, select the BEST solution and explain your reasoning.
Return ONLY valid JSON."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await llm.ainvoke(messages)
        selection_json = extract_json_from_text(response.content)
        
        # Handle JSON extraction failure
        if selection_json is None:
            logger.warning(f"Failed to extract JSON from text (length: {len(response.content)})")
            logger.debug(f"Response content: {response.content[:500]}")
            
            # Fallback: select highest scoring proposal
            if all_proposals:
                final_solution = max(all_proposals, key=lambda p: p["novelty_score"] + p["feasibility_score"])
                reasoning = f"Auto-selected highest scoring proposal (JSON parsing failed)"
                logger.info(f"✅ Fallback Selected: {final_solution['approach_name']}")
                
                return {
                    "current_stage": "solution_selected",
                    "final_solution": final_solution,
                    "selection_reasoning": reasoning
                }
            else:
                logger.error("No proposals available for fallback selection")
                return {
                    "current_stage": "selection_failed",
                    "errors": ["JSON extraction failed and no proposals available"]
                }
        
        selected_name = selection_json.get("selected_approach", "")
        reasoning = selection_json.get("reasoning", "")
        
        # Find the selected proposal
        final_solution = None
        for proposal in all_proposals:
            if proposal["approach_name"] == selected_name or selected_name in proposal["approach_name"]:
                final_solution = proposal
                break
        
        if not final_solution and all_proposals:
            # Fallback: select highest scoring proposal
            final_solution = max(all_proposals, key=lambda p: p["novelty_score"] + p["feasibility_score"])
            reasoning += f"\n(Fallback: Selected highest scoring proposal)"
        
        logger.info(f"✅ Selected: {final_solution['approach_name'] if final_solution else 'None'}")
        
        return {
            "current_stage": "solution_selected",
            "final_solution": final_solution,
            "selection_reasoning": reasoning
        }
        
    except Exception as e:
        logger.error(f"Solution selection failed: {e}")
        
        # Try to salvage by selecting highest scoring proposal
        try:
            all_proposals = []
            for round_data in state.get("debate_rounds", []):
                all_proposals.extend(round_data.get("proposals", []))
            
            if all_proposals:
                final_solution = max(all_proposals, key=lambda p: p.get("novelty_score", 0) + p.get("feasibility_score", 0))
                logger.info(f"✅ Emergency Fallback Selected: {final_solution['approach_name']}")
                return {
                    "current_stage": "solution_selected",
                    "final_solution": final_solution,
                    "selection_reasoning": f"Emergency selection due to error: {str(e)}"
                }
        except Exception as fallback_error:
            logger.error(f"Fallback selection also failed: {fallback_error}")
        
        return {
            "current_stage": "selection_failed",
            "errors": [f"Selection failed: {str(e)}"]
        }


# ============================================
# Node 7: Code Generation
# ============================================

async def code_generation_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 7: Generate implementation code using DeepSeek Coder
    
    Generates:
    - model.py: Core model implementation
    - train.py: Training loop
    - evaluate.py: Evaluation metrics
    - data_loader.py: Data handling
    - utils.py: Helper functions
    - README.md: Documentation
    - requirements.txt: Dependencies
    """
    logger.info("💻 Code Generation Node")
    
    try:
        from langchain_ollama import ChatOllama
        
        # Use DeepSeek Coder V2:16b for code generation
        llm = ChatOllama(
            model="deepseek-coder-v2:16b",
            temperature=0.2,  # Lower temperature for more deterministic code
            base_url="http://localhost:11434"
        )
        
        solution = state.get("final_solution")
        if not solution:
            logger.warning("No solution found, skipping code generation")
            return {
                "current_stage": "code_generation_skipped",
                "generated_code": {}
            }
        
        idea = state["idea"]
        approach = solution["approach_name"]
        innovation = solution["key_innovation"]
        architecture = solution["architecture_design"]
        implementation_plan = solution.get("implementation_plan", [])
        
        # Files to generate
        files_to_generate = {
            "model.py": f"""You are an expert PyTorch developer. Generate a production-ready model implementation.

Research Idea: {idea}
Approach: {approach}
Innovation: {innovation}
Architecture: {architecture}

Generate ONLY the model.py file with:
- Complete model class inheriting from nn.Module
- Proper initialization
- Forward pass implementation
- Docstrings for all methods
- Type hints

Return ONLY valid Python code, no explanations.""",
            
            "train.py": f"""Generate a training script for: {approach}

Include:
- Training loop with progress bars
- Loss calculation
- Optimizer setup (AdamW)
- Learning rate scheduling
- Checkpointing
- Logging with tensorboard
- Command-line arguments

Return ONLY valid Python code.""",
            
            "evaluate.py": f"""Generate evaluation script for: {approach}

Include:
- Model loading from checkpoint
- Evaluation metrics calculation
- Results visualization
- Performance reporting

Return ONLY valid Python code.""",
            
            "data_loader.py": f"""Generate data loading utilities for: {approach}

Include:
- Dataset class
- DataLoader setup
- Data preprocessing
- Augmentation if needed

Return ONLY valid Python code.""",
            
            "utils.py": f"""Generate utility functions for: {approach}

Include:
- Helper functions
- Logging setup
- Configuration management
- Common operations

Return ONLY valid Python code.""",
            
            "README.md": f"""Generate a comprehensive README for: {approach}

Include:
- Project description
- Installation instructions
- Usage examples
- Architecture overview
- Citation information

Return ONLY valid Markdown.""",
            
            "requirements.txt": """Generate requirements.txt with:
torch>=2.0.0
numpy>=1.24.0
tqdm>=4.65.0
tensorboard>=2.13.0

Return ONLY package names with versions."""
        }
        
        generated_files = {}
        
        logger.info(f"  Generating {len(files_to_generate)} files...")
        
        for filename, prompt in files_to_generate.items():
            logger.info(f"  📝 Generating {filename}...")
            
            messages = [
                SystemMessage(content="You are an expert code generator. Generate clean, production-ready code."),
                HumanMessage(content=prompt)
            ]
            
            response = await llm.ainvoke(messages)
            code = response.content
            
            # Clean up code (remove markdown code blocks if present)
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code and filename.endswith(".py"):
                code = code.split("```")[1].split("```")[0].strip()
            elif "```markdown" in code:
                code = code.split("```markdown")[1].split("```")[0].strip()
            elif "```" in code and filename == "requirements.txt":
                # Clean requirements.txt from markdown blocks
                code = code.split("```")[1].split("```")[0].strip()
                # Remove language tags like 'plaintext' or 'txt'
                if code.startswith(("plaintext", "txt", "text")):
                    code = "\n".join(code.split("\n")[1:]).strip()
            
            generated_files[filename] = code
            logger.info(f"  ✅ Generated {filename} ({len(code)} chars)")
        
        logger.info(f"✅ Generated {len(generated_files)} files")
        
        return {
            "current_stage": "code_generated",
            "generated_code": {
                "files": generated_files,
                "approach": approach,
                "total_files": len(generated_files)
            }
        }
        
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        return {
            "current_stage": "code_generation_failed",
            "errors": [f"Code generation failed: {str(e)}"],
            "generated_code": {}
        }


# ============================================
# Node 8: Code Testing and Validation
# ============================================

async def code_testing_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 8: Test generated code in isolated environment
    
    Creates virtual environment, installs dependencies,
    validates syntax, tests imports, and runs basic execution tests.
    """
    logger.info("🧪 Code Testing Node")
    
    try:
        from pathlib import Path
        from ..utils.code_executor import CodeExecutor
        import tempfile
        import shutil
        
        generated_code = state.get("generated_code", {})
        files = generated_code.get("files", {})
        
        if not files:
            logger.warning("No files to test")
            return {
                "current_stage": "testing_skipped",
                "test_results": {"error": "No files generated"}
            }
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test_project"
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # Write all files to test directory
            for filename, content in files.items():
                file_path = test_dir / filename
                file_path.write_text(content, encoding="utf-8")
                logger.info(f"  📝 Wrote {filename} for testing")
            
            # Run test suite
            logger.info(f"🔬 Testing code in: {test_dir}")
            executor = CodeExecutor(test_dir)
            test_results = executor.run_full_test_suite(cleanup_after=True)
            
            # Analyze results
            passed = (
                test_results.get("environment_created", False) and
                test_results.get("dependencies_installed", False) and
                test_results.get("syntax_valid", True) and
                test_results.get("import_successful", True)
            )
            
            if passed:
                logger.info("✅ All tests passed!")
            else:
                logger.warning("⚠️  Some tests failed")
                for error in test_results.get("execution_errors", []):
                    logger.error(f"  ❌ {error}")
            
            # Log warnings
            for warning in test_results.get("warnings", []):
                logger.warning(f"  ⚠️  {warning}")
            
            return {
                "current_stage": "testing_complete",
                "test_results": test_results,
                "tests_passed": passed
            }
    
    except Exception as e:
        logger.error(f"Code testing failed: {e}")
        return {
            "current_stage": "testing_failed",
            "errors": [f"Testing failed: {str(e)}"],
            "test_results": {"error": str(e)},
            "tests_passed": False
        }


# ============================================
# Node 8.5: Code Fixing (Self-Healing)
# ============================================

async def code_fixing_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 8.5: Automatically fix code issues based on test failures
    
    Analyzes test errors and generates fixes for:
    - Syntax errors
    - Import errors
    - Missing dependencies
    - Runtime errors
    """
    logger.info("🔧 Code Fixing Node: Auto-healing code issues")
    
    console = Console()
    console.print("\n[yellow]🔧 Analyzing test failures and generating fixes...[/yellow]")
    
    try:
        test_results = state.get("test_results", {})
        fix_attempts = state.get("fix_attempts", 0)
        
        if fix_attempts >= state.get("max_fix_attempts", 6):
            logger.error(f"Max fix attempts ({fix_attempts}) reached. Giving up.")
            console.print(f"\n[red]❌ Max fix attempts reached. Cannot auto-fix code.[/red]\n")
            return {
                "current_stage": "fixing_failed",
                "fix_attempts": fix_attempts,
                "errors": [f"Max fix attempts ({fix_attempts}) reached"]
            }
        
        # Get error details
        execution_errors = test_results.get("execution_errors", [])
        warnings = test_results.get("warnings", [])
        
        if not execution_errors:
            logger.info("No errors to fix")
            return {
                "current_stage": "no_errors_to_fix",
                "fix_attempts": fix_attempts
            }
        
        console.print(f"\n[cyan]Found {len(execution_errors)} errors. Attempt {fix_attempts + 1}/{state.get('max_fix_attempts', 6)}[/cyan]")
        
        # Use DeepSeek Coder to fix issues
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model="deepseek-coder-v2:16b",
            temperature=0.2,
            base_url="http://localhost:11434"
        )
        
        generated_code = state.get("generated_code", {})
        files = generated_code.get("files", {})
        
        # Build error context
        error_summary = "\n".join([f"- {error}" for error in execution_errors[:5]])
        
        system_prompt = """You are an expert Python debugger. Fix code issues based on test errors.

Your job:
1. Analyze the error messages
2. Identify the root cause
3. Generate fixed code
4. Ensure all imports and dependencies are correct

Return ONLY valid Python code for each file, no explanations."""
        
        fixed_files = {}
        
        # Fix each file that has errors
        for filename, content in files.items():
            if not filename.endswith('.py'):
                fixed_files[filename] = content
                continue
            
            console.print(f"  [dim]Fixing {filename}...[/dim]")
            
            user_prompt = f"""Fix this Python file based on the test errors:

Errors:
{error_summary}

File: {filename}
```python
{content}
```

Return the FIXED code for {filename}. Fix:
- Syntax errors
- Import errors  
- Missing dependencies
- Type errors
- Runtime errors

Return ONLY the complete fixed Python code, no explanations."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await llm.ainvoke(messages)
            
            # Extract code from response
            fixed_code = response.content
            if "```python" in fixed_code:
                fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
            elif "```" in fixed_code:
                fixed_code = fixed_code.split("```")[1].split("```")[0].strip()
            
            fixed_files[filename] = fixed_code
            console.print(f"  [green]✓[/green] Fixed {filename}")
        
        # Update requirements.txt if there are import errors
        if any("import" in str(e).lower() or "modulenotfound" in str(e).lower() for e in execution_errors):
            console.print(f"  [dim]Updating requirements.txt...[/dim]")
            
            # Extract missing modules from errors
            missing_modules = []
            for error in execution_errors:
                if "No module named" in str(error):
                    # Extract module name from "No module named 'xxx'"
                    import re
                    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", str(error))
                    if match:
                        missing_modules.append(match.group(1))
            
            if missing_modules:
                current_reqs = fixed_files.get("requirements.txt", "")
                new_reqs = current_reqs.strip()
                for module in missing_modules:
                    if module not in new_reqs:
                        new_reqs += f"\n{module}"
                fixed_files["requirements.txt"] = new_reqs.strip()
                console.print(f"  [green]✓[/green] Added missing dependencies: {', '.join(missing_modules)}")
        
        logger.info(f"✅ Fixed {len(fixed_files)} files")
        console.print(f"\n[green]✅ Code fixes generated. Re-testing...[/green]\n")
        
        return {
            "current_stage": "code_fixed",
            "generated_code": {"files": fixed_files},
            "fix_attempts": fix_attempts + 1
        }
    
    except Exception as e:
        logger.error(f"Code fixing failed: {e}")
        console.print(f"\n[red]❌ Fixing failed: {e}[/red]\n")
        return {
            "current_stage": "fixing_error",
            "errors": [f"Fixing failed: {str(e)}"],
            "fix_attempts": state.get("fix_attempts", 0) + 1
        }


# ============================================
# Node 9: Git Publishing
# ============================================

async def git_publishing_node(state: AutoGITState) -> Dict[str, Any]:
    """
    Node 9: Publish generated code to GitHub
    
    Creates a new repository and pushes all generated code.
    Only publishes if tests passed (or if testing was skipped).
    """
    logger.info("📤 Git Publishing Node")
    
    # Check test results before publishing
    test_results = state.get("test_results", {})
    tests_passed = state.get("tests_passed", True)  # Default to True if testing was skipped
    
    console = Console()
    
    if not tests_passed:
        logger.warning("⚠️  Tests failed! Skipping GitHub publishing.")
        console.print("\n[yellow]⚠️  Tests failed! Code will be saved locally only (not published to GitHub).[/yellow]")
        
        # Force local save when tests fail
        try:
            from pathlib import Path
            from datetime import datetime
            
            output_dir = Path(state.get("output_dir", "output"))
            solution = state.get("final_solution") or {}
            repo_name = solution.get("approach_name", "auto-git-project").replace(" ", "-").lower()
            project_dir = output_dir / repo_name / datetime.now().strftime("%Y%m%d_%H%M%S")
            project_dir.mkdir(parents=True, exist_ok=True)
            
            generated_code = state.get("generated_code") or {}
            files = generated_code.get("files", {})
            
            if files:
                for filename, content in files.items():
                    file_path = project_dir / filename
                    file_path.write_text(content, encoding="utf-8")
                    logger.info(f"  ✅ Saved {filename}")
                
                console.print(f"\n[green]✅ Code saved to:[/green] [bold cyan]{project_dir}[/bold cyan]\n")
                console.print(f"[dim]Review the code, fix any issues, then use the publish script to upload to GitHub.[/dim]\n")
                
                return {
                    "current_stage": "saved_locally_tests_failed",
                    "output_path": str(project_dir),
                    "github_url": None,
                    "tests_passed": False
                }
            else:
                logger.error("No files to save")
                return {
                    "current_stage": "no_files",
                    "errors": ["No generated files to save"]
                }
        except Exception as e:
            logger.error(f"Failed to save locally: {e}")
            return {
                "current_stage": "save_failed",
                "errors": [f"Local save failed: {str(e)}"]
            }
    
    try:
        import os
        from pathlib import Path
        from github import Github
        from datetime import datetime
        
        # Check if auto-publish is enabled
        if not state.get("auto_publish", False):
            logger.info("Auto-publish disabled, saving locally only")
            
            # Save files locally
            output_dir = Path(state.get("output_dir", "output"))
            solution = state.get("final_solution") or {}
            repo_name = solution.get("approach_name", "auto-git-project").replace(" ", "-").lower()
            project_dir = output_dir / repo_name / datetime.now().strftime("%Y%m%d_%H%M%S")
            project_dir.mkdir(parents=True, exist_ok=True)
            
            generated_code = state.get("generated_code") or {}
            files = generated_code.get("files", {})
            
            for filename, content in files.items():
                file_path = project_dir / filename
                file_path.write_text(content, encoding="utf-8")
                logger.info(f"  ✅ Saved {filename}")
            
            logger.info(f"✅ Code saved to: {project_dir}")
            
            return {
                "current_stage": "saved_locally",
                "output_path": str(project_dir),
                "github_url": None
            }
        
        # GitHub publishing
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.error("GITHUB_TOKEN not found in environment")
            return {
                "current_stage": "publishing_failed",
                "errors": ["GITHUB_TOKEN not set. Use: export GITHUB_TOKEN=your_token"]
            }
        
        solution = state.get("final_solution") or {}
        generated_code = state.get("generated_code") or {}
        files = generated_code.get("files", {})
        
        if not files:
            logger.warning("No files to publish")
            return {
                "current_stage": "no_files",
                "errors": ["No generated files to publish"]
            }
        
        # Create GitHub client
        g = Github(github_token)
        user = g.get_user()
        
        # Create repository name
        repo_name = solution.get("approach_name", "auto-git-project").replace(" ", "-").lower()
        repo_name = f"autogit-{repo_name}-{datetime.now().strftime('%Y%m%d')}"
        
        logger.info(f"  Creating repository: {repo_name}")
        
        # Create repository
        repo = user.create_repo(
            name=repo_name,
            description=f"Auto-generated implementation: {solution.get('approach_name', 'N/A')}",
            private=False,
            auto_init=False
        )
        
        logger.info(f"  ✅ Repository created: {repo.html_url}")
        
        # Create files
        for filename, content in files.items():
            logger.info(f"  📤 Uploading {filename}...")
            repo.create_file(
                path=filename,
                message=f"Add {filename}",
                content=content
            )
        
        logger.info(f"✅ Published to GitHub: {repo.html_url}")
        
        return {
            "current_stage": "published",
            "github_url": repo.html_url,
            "repo_name": repo_name
        }
        
    except Exception as e:
        logger.error(f"Git publishing failed: {e}")
        
        # Fallback: save locally
        try:
            output_dir = Path(state.get("output_dir", "output"))
            solution = state.get("final_solution") or {}
            repo_name = solution.get("approach_name", "auto-git-project").replace(" ", "-").lower()
            project_dir = output_dir / repo_name / datetime.now().strftime("%Y%m%d_%H%M%S")
            project_dir.mkdir(parents=True, exist_ok=True)
            
            generated_code = state.get("generated_code") or {}
            files = generated_code.get("files", {})
            
            for filename, content in files.items():
                file_path = project_dir / filename
                file_path.write_text(content, encoding="utf-8")
            
            logger.info(f"✅ Saved locally to: {project_dir} (GitHub push failed)")
            
            return {
                "current_stage": "saved_locally_after_error",
                "output_path": str(project_dir),
                "errors": [f"GitHub publishing failed: {str(e)}"]
            }
        except Exception as save_error:
            logger.error(f"Failed to save locally: {save_error}")
            return {
                "current_stage": "publishing_failed",
                "errors": [f"Publishing failed: {str(e)}", f"Local save failed: {str(save_error)}"]
            }

