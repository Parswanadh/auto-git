"""
Enhanced LangGraph Workflow with Progress Monitoring

Adds Rich progress bars, live updates, and inter-stage output display.
"""

import logging
import asyncio
from typing import Literal, Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import box

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
    code_fixing_node,
    git_publishing_node
)

logger = logging.getLogger(__name__)
console = Console()


def display_research_results(state: AutoGITState):
    """Display research results in a formatted panel"""
    # Get research context
    research_context = state.get("research_context", {})
    papers = research_context.get("papers", []) if research_context else []
    web_results = research_context.get("web_results", []) if research_context else []
    implementations = research_context.get("implementations", []) if research_context else []
    
    table = Table(title="📚 Research Results", box=box.ROUNDED, border_style="cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Details", style="white")
    
    # Display paper info
    if papers:
        first_paper = papers[0].get('title', 'N/A')[:50]
        table.add_row("arXiv Papers", str(len(papers)), f"{first_paper}...")
    else:
        table.add_row("arXiv Papers", "0", "None found")
    
    # Display web results
    if web_results:
        first_result = web_results[0].get('title', 'N/A')[:50]
        table.add_row("Web Results", str(len(web_results)), f"{first_result}...")
    else:
        table.add_row("Web Results", "0", "None found")
    
    # Display implementations
    if implementations:
        table.add_row("Implementations", str(len(implementations)), f"{len(implementations)} found on GitHub")
    else:
        table.add_row("Implementations", "0", "None found")
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def display_problems(state: AutoGITState):
    """Display extracted problems"""
    problems = state.get("problems", [])
    selected = state.get("selected_problem")
    
    console.print("\n")
    console.print(Panel(
        f"[bold cyan]🎯 Extracted {len(problems)} Research Problems[/bold cyan]",
        border_style="cyan"
    ))
    
    for i, problem in enumerate(problems[:3], 1):
        if isinstance(problem, dict):
            console.print(f"\n{i}. [yellow]{problem.get('title', 'Problem ' + str(i))}[/yellow]")
            console.print(f"   [dim]{problem.get('description', 'N/A')[:100]}...[/dim]")
        else:
            # Problem is a string
            console.print(f"\n{i}. [yellow]{str(problem)[:100]}...[/yellow]")
    
    if selected:
        if isinstance(selected, dict):
            console.print(f"\n[bold green]✓ Selected:[/bold green] {selected.get('title', 'Problem 1')}")
        else:
            console.print(f"\n[bold green]✓ Selected:[/bold green] {str(selected)[:50]}...")
    console.print("\n")


def display_debate_round(state: AutoGITState):
    """Display debate round results"""
    rounds = state.get("debate_rounds", [])
    if not rounds:
        return
    
    current_round = rounds[-1]
    proposals = current_round.get("proposals", [])
    critiques = current_round.get("critiques", [])
    
    console.print("\n")
    console.print(Panel(
        f"[bold magenta]💡 Round {current_round.get('round_number', '?')} - {len(proposals)} Proposals, {len(critiques)} Critiques[/bold magenta]",
        border_style="magenta"
    ))
    
    # Show proposals
    for i, proposal in enumerate(proposals, 1):
        console.print(f"\n{i}. [cyan]{proposal.get('approach_name', 'Unnamed')}[/cyan]")
        console.print(f"   [green]Perspective:[/green] {proposal.get('perspective', 'N/A')}")
        console.print(f"   [dim]{proposal.get('key_innovation', 'N/A')[:80]}...[/dim]")
        console.print(f"   [yellow]Novelty: {proposal.get('novelty_score', 0):.2f}[/yellow] | [blue]Feasibility: {proposal.get('feasibility_score', 0):.2f}[/blue]")
    
    console.print("\n")


def display_final_solution(state: AutoGITState):
    """Display the selected final solution"""
    solution = state.get("final_solution")
    if not solution:
        return
    
    console.print("\n")
    console.print(Panel(
        f"[bold green]🏆 SELECTED SOLUTION[/bold green]\n\n"
        f"[cyan]{solution.get('approach_name', 'N/A')}[/cyan]\n\n"
        f"[white]{solution.get('key_innovation', 'N/A')}[/white]\n\n"
        f"[dim]Architecture: {solution.get('architecture_design', 'N/A')[:100]}...[/dim]",
        border_style="bright_green",
        box=box.DOUBLE
    ))
    console.print("\n")


def display_generated_code(state: AutoGITState):
    """Display generated code summary"""
    generated = state.get("generated_code", {})
    if not generated:
        return
    
    files = generated.get("files", {})
    
    console.print("\n")
    console.print(Panel(
        f"[bold cyan]💻 Generated Code[/bold cyan]",
        border_style="cyan"
    ))
    
    for filename, content in files.items():
        lines = len(content.split('\n')) if isinstance(content, str) else 0
        console.print(f"  [green]✓[/green] {filename} [dim]({lines} lines)[/dim]")
    
    console.print("\n")


def display_github_result(state: AutoGITState):
    """Display GitHub publishing result"""
    github_url = state.get("github_url")
    repo_name = state.get("repo_name")
    
    if github_url:
        console.print("\n")
        console.print(Panel(
            f"[bold green]🚀 Published to GitHub![/bold green]\n\n"
            f"[cyan]Repository:[/cyan] {repo_name}\n"
            f"[cyan]URL:[/cyan] [link={github_url}]{github_url}[/link]",
            border_style="bright_green",
            box=box.DOUBLE
        ))
        console.print("\n")


def display_test_results(state: AutoGITState):
    """Display code testing results"""
    test_results = state.get("test_results")
    tests_passed = state.get("tests_passed", False)
    
    if not test_results:
        return
    
    console.print("\n")
    
    # Create status table
    table = Table(title="🧪 Code Testing Results", box=box.ROUNDED, show_header=True)
    table.add_column("Test", style="cyan", width=30)
    table.add_column("Status", width=15)
    table.add_column("Details", style="dim", width=50)
    
    # Environment creation
    env_status = "✅ Pass" if test_results.get("environment_created") else "❌ Fail"
    table.add_row("Environment Creation", env_status, "Virtual environment setup")
    
    # Dependencies installation
    deps_status = "✅ Pass" if test_results.get("dependencies_installed") else "❌ Fail"
    table.add_row("Dependencies", deps_status, "Package installation")
    
    # Syntax validation
    syntax_status = "✅ Pass" if test_results.get("syntax_valid") else "❌ Fail"
    table.add_row("Syntax Check", syntax_status, "Python syntax validation")
    
    # Import testing
    import_status = "✅ Pass" if test_results.get("import_successful") else "❌ Fail"
    table.add_row("Import Test", import_status, "Module import validation")
    
    console.print(table)
    
    # Display errors if any
    errors = test_results.get("execution_errors", [])
    if errors:
        console.print("\n[bold red]⚠️ Errors Detected:[/bold red]")
        for error in errors[:5]:  # Limit to 5 errors
            console.print(f"  [red]•[/red] [dim]{error}[/dim]")
    
    # Display warnings if any
    warnings = test_results.get("warnings", [])
    if warnings:
        console.print("\n[bold yellow]⚠️ Warnings:[/bold yellow]")
        for warning in warnings[:3]:  # Limit to 3 warnings
            console.print(f"  [yellow]•[/yellow] [dim]{warning}[/dim]")
    
    # Overall status
    if tests_passed:
        console.print("\n[bold green]✅ All tests passed! Code is ready for publishing.[/bold green]")
    else:
        console.print("\n[bold red]❌ Tests failed! Auto-fixing will be attempted.[/bold red]")
        console.print("[yellow]Review errors above. You can choose to stop, continue fixing, or publish anyway.[/yellow]")
    
    console.print("\n")
    
    # Return whether user wants to continue
    return tests_passed


def should_continue_debate(state: AutoGITState) -> Literal["continue", "select"]:
    """Routing function: Decide whether to continue debate or select solution"""
    current_stage = state.get("current_stage", "")
    
    if current_stage == "consensus_reached":
        return "select"
    elif current_stage == "max_rounds_reached":
        return "select"
    else:
        return "continue"


def should_fix_code(state: AutoGITState) -> Literal["fix", "publish"]:
    """Routing function: Decide whether to fix code or proceed to publishing"""
    tests_passed = state.get("tests_passed", True)
    fix_attempts = state.get("fix_attempts", 0)
    max_attempts = state.get("max_fix_attempts", 6)
    
    # If tests passed, go to publishing
    if tests_passed:
        return "publish"
    
    # If we haven't exceeded max attempts, try to fix
    if fix_attempts < max_attempts:
        return "fix"
    
    # Otherwise, give up and go to publishing (will save locally)
    return "publish"


def build_workflow() -> StateGraph:
    """Build the LangGraph StateGraph workflow with all nodes"""
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
    workflow.add_node("code_fixing", code_fixing_node)
    workflow.add_node("git_publishing", git_publishing_node)
    
    # Define the flow
    workflow.set_entry_point("research")
    workflow.add_edge("research", "problem_extraction")
    workflow.add_edge("problem_extraction", "solution_generation")
    workflow.add_edge("solution_generation", "critique")
    workflow.add_edge("critique", "consensus_check")
    
    # Conditional routing from consensus_check
    workflow.add_conditional_edges(
        "consensus_check",
        should_continue_debate,
        {
            "continue": "solution_generation",
            "select": "solution_selection"
        }
    )
    
    # Final flow with self-healing loop
    workflow.add_edge("solution_selection", "code_generation")
    workflow.add_edge("code_generation", "code_testing")
    
    # Conditional: if tests fail, try to fix; if pass, publish
    workflow.add_conditional_edges(
        "code_testing",
        should_fix_code,
        {
            "fix": "code_fixing",
            "publish": "git_publishing"
        }
    )
    
    # After fixing, test again (creates the self-healing loop)
    workflow.add_edge("code_fixing", "code_testing")
    
    workflow.add_edge("git_publishing", END)
    
    return workflow


def compile_workflow() -> StateGraph:
    """Compile the workflow with memory persistence"""
    workflow = build_workflow()
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


async def run_auto_git_pipeline(
    idea: str,
    user_requirements: str = None,
    requirements: Dict[str, Any] = None,  # Structured requirements from conversation
    use_web_search: bool = True,
    max_debate_rounds: int = 2,
    min_consensus_score: float = 0.5,
    auto_publish: bool = False,
    output_dir: Optional[str] = None,
    stop_after: Optional[str] = None,
    thread_id: str = "default"
) -> AutoGITState:
    """
    Run the complete Auto-GIT pipeline with progress monitoring
    
    Args:
        idea: Research idea or topic
        user_requirements: Optional additional requirements
        requirements: Structured requirements from conversation agent (IMPORTANT!)
        use_web_search: Enable web search
        max_debate_rounds: Maximum debate rounds
        min_consensus_score: Minimum consensus score (0-1)
        auto_publish: Automatically publish to GitHub
        output_dir: Output directory for generated code
        stop_after: Stop after this node (for testing)
        thread_id: Thread ID for checkpointing
        
    Returns:
        Final state after pipeline execution
    """
    
    # Create initial state
    initial_state = create_initial_state(
        idea=idea,
        user_requirements=user_requirements,
        requirements=requirements,  # Pass requirements to state
        use_web_search=use_web_search,
        max_rounds=max_debate_rounds,
        min_consensus=min_consensus_score
    )
    
    # Add flags to state
    initial_state["auto_publish"] = auto_publish
    initial_state["output_dir"] = output_dir or "output"
    
    # Compile workflow
    workflow = compile_workflow()
    
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    # Pipeline stages for progress tracking
    stages = [
        ("research", "🔍 Searching arXiv and web..."),
        ("problem_extraction", "🎯 Extracting research problems..."),
        ("solution_generation", "💡 Generating solutions (Round {})..."),
        ("critique", "🔍 Cross-perspective review..."),
        ("consensus_check", "⚖️  Checking consensus..."),
        ("solution_selection", "🏆 Selecting best solution..."),
        ("code_generation", "💻 Generating code with DeepSeek..."),
        ("code_testing", "🧪 Testing code in isolated environment..."),
        ("code_fixing", "🔧 Auto-fixing issues..."),
        ("git_publishing", "📤 Publishing to GitHub..."),
    ]
    
    # Progress bar setup
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        main_task = progress.add_task("[cyan]Pipeline Progress", total=len(stages))
        
        final_state = None
        current_round = 1
        visited_nodes = set()
        
        try:
            async for state in workflow.astream(initial_state, config):
                for node_name, node_state in state.items():
                    
                    # Update progress
                    current_stage = node_state.get("current_stage", "")
                    
                    # Track rounds
                    if node_name == "solution_generation" and node_name in visited_nodes:
                        current_round += 1
                    
                    visited_nodes.add(node_name)
                    
                    # Find matching stage
                    for stage_name, stage_desc in stages:
                        if stage_name == node_name:
                            desc = stage_desc.format(current_round) if '{}' in stage_desc else stage_desc
                            progress.update(main_task, description=f"[cyan]{desc}")
                            progress.advance(main_task, 0.5)
                            break
                    
                    # Display inter-stage results
                    if node_name == "research" and current_stage == "research_complete":
                        display_research_results(node_state)
                    
                    elif node_name == "problem_extraction" and current_stage == "problems_extracted":
                        display_problems(node_state)
                    
                    elif node_name == "critique" and current_stage == "critiques_complete":
                        display_debate_round(node_state)
                    
                    elif node_name == "solution_selection" and current_stage == "solution_selected":
                        display_final_solution(node_state)
                    
                    elif node_name == "code_generation" and current_stage == "code_generated":
                        display_generated_code(node_state)
                    
                    elif node_name == "code_testing" and current_stage == "testing_complete":
                        tests_passed = display_test_results(node_state)
                        
                        # Give user control if tests failed
                        if not tests_passed:
                            from rich.prompt import Prompt
                            fix_attempts = node_state.get("fix_attempts", 0)
                            max_attempts = node_state.get("max_fix_attempts", 6)
                            
                            console.print(f"[dim]Fix attempt {fix_attempts}/{max_attempts}[/dim]\n")
                            
                            choice = Prompt.ask(
                                "[cyan]What would you like to do?[/cyan]",
                                choices=["continue", "stop", "publish"],
                                default="continue"
                            )
                            
                            if choice == "stop":
                                console.print("\n[yellow]⏹️ Stopping pipeline. Saving code locally...[/yellow]\n")
                                # Force local save
                                node_state["tests_passed"] = False
                                node_state["fix_attempts"] = max_attempts  # Force max to skip fixing
                                progress.update(main_task, completed=len(stages))
                                return node_state
                            
                            elif choice == "publish":
                                console.print("\n[yellow]⚠️ Publishing despite test failures...[/yellow]\n")
                                # Force publishing
                                node_state["tests_passed"] = True
                                node_state["fix_attempts"] = max_attempts  # Skip fixing
                            
                            # If "continue", let it proceed to fixing automatically
                    
                    elif node_name == "code_fixing" and current_stage == "code_fixed":
                        # Show fix progress
                        fix_attempts = node_state.get("fix_attempts", 0)
                        max_attempts = node_state.get("max_fix_attempts", 6)
                        console.print(f"\n[green]✅ Fix attempt {fix_attempts}/{max_attempts} completed. Re-testing...[/green]\n")
                        
                        # Give user option to stop if multiple fixes attempted
                        if fix_attempts >= 2:  # After 2 fix attempts, ask user
                            from rich.prompt import Prompt
                            
                            choice = Prompt.ask(
                                "[cyan]Continue auto-fixing?[/cyan]",
                                choices=["yes", "stop", "publish"],
                                default="yes"
                            )
                            
                            if choice == "stop":
                                console.print("\n[yellow]⏹️ Stopping. Saving current state...[/yellow]\n")
                                node_state["fix_attempts"] = max_attempts  # Force stop
                                progress.update(main_task, completed=len(stages))
                                return node_state
                            
                            elif choice == "publish":
                                console.print("\n[yellow]⚠️ Publishing current state...[/yellow]\n")
                                node_state["tests_passed"] = True
                                node_state["fix_attempts"] = max_attempts
                    
                    elif node_name == "git_publishing" and current_stage == "published":
                        display_github_result(node_state)
                    
                    final_state = node_state
                    
                    # Stop if requested
                    if stop_after and node_name == stop_after:
                        progress.update(main_task, completed=len(stages))
                        return final_state
            
            progress.update(main_task, completed=len(stages))
            return final_state
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Pipeline failed: {e}[/bold red]")
            raise
