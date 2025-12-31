"""
Test script for LangGraph-based Auto-GIT pipeline

Usage:
    python test_langgraph_pipeline.py
"""

import asyncio
import logging
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.langraph_pipeline import (
    run_auto_git_pipeline,
    print_workflow_structure,
    EXPERT_PERSPECTIVES
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

console = Console()


def print_expert_perspectives():
    """Display configured expert perspectives"""
    console.print("\n[bold cyan]📋 Expert Perspectives Configured:[/bold cyan]\n")
    
    for perspective in EXPERT_PERSPECTIVES:
        console.print(f"[bold]{perspective['name']}[/bold]")
        console.print(f"  Role: {perspective['role']}")
        console.print(f"  Expertise: {perspective['expertise']}")
        console.print(f"  Focus: {', '.join(perspective['focus_areas'])}")
        console.print()


def display_results(state):
    """Display pipeline results in a nice format"""
    console.print("\n" + "="*80 + "\n")
    console.print("[bold green]🎉 PIPELINE EXECUTION COMPLETE![/bold green]\n")
    
    # Display research context
    if state.get("research_context"):
        research = state["research_context"]
        console.print(Panel(
            f"[cyan]Papers Found:[/cyan] {len(research.get('papers', []))}\n"
            f"[cyan]Web Results:[/cyan] {len(research.get('web_results', []))}\n"
            f"[cyan]Implementations:[/cyan] {len(research.get('implementations', []))}",
            title="🔍 Research Context",
            border_style="cyan"
        ))
    
    # Display problems
    if state.get("problems"):
        console.print("\n[bold yellow]🎯 Problems Extracted:[/bold yellow]")
        for i, problem in enumerate(state["problems"], 1):
            console.print(f"  {i}. {problem}")
        console.print(f"\n[bold]Selected Problem:[/bold] {state.get('selected_problem', 'None')}\n")
    
    # Display debate summary
    if state.get("debate_rounds"):
        console.print(f"[bold magenta]🎭 Debate Rounds:[/bold magenta] {len(state['debate_rounds'])}")
        
        for round_data in state["debate_rounds"]:
            console.print(f"\n[bold]Round {round_data['round_number']}:[/bold]")
            console.print(f"  Proposals: {len(round_data['proposals'])}")
            console.print(f"  Critiques: {len(round_data['critiques'])}")
            
            # Show proposals
            for proposal in round_data["proposals"]:
                console.print(f"\n  📝 [cyan]{proposal['approach_name']}[/cyan]")
                console.print(f"     Perspective: {proposal['perspective']}")
                console.print(f"     Novelty: {proposal['novelty_score']:.2f}, Feasibility: {proposal['feasibility_score']:.2f}")
            
            # Show critiques summary
            if round_data["critiques"]:
                accept_count = sum(1 for c in round_data["critiques"] if c["recommendation"] == "accept")
                revise_count = sum(1 for c in round_data["critiques"] if c["recommendation"] == "revise")
                reject_count = sum(1 for c in round_data["critiques"] if c["recommendation"] == "reject")
                console.print(f"\n  Critique Summary: ✅ {accept_count} accept | 🔄 {revise_count} revise | ❌ {reject_count} reject")
    
    # Display final solution
    if state.get("final_solution"):
        solution = state["final_solution"]
        console.print("\n" + Panel(
            f"[bold green]{solution['approach_name']}[/bold green]\n\n"
            f"[yellow]Perspective:[/yellow] {solution['perspective']}\n"
            f"[yellow]Innovation:[/yellow] {solution['key_innovation']}\n\n"
            f"[yellow]Architecture:[/yellow] {solution['architecture_design']}\n\n"
            f"[yellow]Scores:[/yellow] Novelty: {solution['novelty_score']:.2f}, Feasibility: {solution['feasibility_score']:.2f}",
            title="🏆 Selected Solution",
            border_style="green"
        ))
        
        if state.get("selection_reasoning"):
            console.print(f"\n[dim]Reasoning: {state['selection_reasoning']}[/dim]")
    
    # Display errors and warnings
    if state.get("errors"):
        console.print("\n[bold red]❌ Errors:[/bold red]")
        for error in state["errors"]:
            console.print(f"  - {error}")
    
    if state.get("warnings"):
        console.print("\n[bold yellow]⚠️  Warnings:[/bold yellow]")
        for warning in state["warnings"]:
            console.print(f"  - {warning}")
    
    console.print("\n" + "="*80 + "\n")


async def main():
    """Main test function"""
    console.print("\n[bold blue]╔══════════════════════════════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║         LangGraph-Based Auto-GIT Pipeline Test              ║[/bold blue]")
    console.print("[bold blue]╚══════════════════════════════════════════════════════════════╝[/bold blue]\n")
    
    # Show workflow structure
    print_workflow_structure()
    
    # Show expert perspectives
    print_expert_perspectives()
    
    # Get test idea from user or use default
    console.print("[bold cyan]Enter research idea (or press Enter for default):[/bold cyan]")
    idea = input("> ").strip()
    
    if not idea:
        idea = "Efficient transformer attention mechanisms for long sequences"
        console.print(f"[dim]Using default: {idea}[/dim]\n")
    
    # Configuration
    use_web_search = True
    max_rounds = 2  # Reduced for faster testing
    min_consensus = 0.5
    
    console.print(f"\n[bold]Configuration:[/bold]")
    console.print(f"  Web Search: {'✅ Enabled' if use_web_search else '❌ Disabled'}")
    console.print(f"  Max Rounds: {max_rounds}")
    console.print(f"  Min Consensus: {min_consensus}")
    console.print(f"  Perspectives: {len(EXPERT_PERSPECTIVES)}")
    console.print()
    
    # Run pipeline
    try:
        console.print("[bold green]🚀 Starting pipeline execution...[/bold green]\n")
        
        final_state = await run_auto_git_pipeline(
            idea=idea,
            use_web_search=use_web_search,
            max_rounds=max_rounds,
            min_consensus=min_consensus,
            thread_id="test_run"
        )
        
        # Display results
        display_results(final_state)
        
        console.print("[bold green]✅ Test completed successfully![/bold green]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Pipeline failed with error:[/bold red]")
        console.print(f"[red]{str(e)}[/red]")
        import traceback
        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
