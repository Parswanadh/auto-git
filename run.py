#!/usr/bin/env python3
"""
AUTO-GIT PUBLISHER - Main Entry Point
Production-grade LangGraph pipeline with local Ollama models.
"""

import asyncio
from typing import Optional, List
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.utils.config import get_config, load_config
from src.utils.logger import setup_logging, get_logger
from src.utils.ollama_client import get_ollama_client, test_ollama_connection
from src.pipeline.graph import compile_pipeline, create_initial_state
from src.pipeline.state import AgentState
from src.agents.tier0_supervisor.supervisor import PipelineSupervisor


console = Console()
logger = get_logger()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    🚀 AUTO-GIT PUBLISHER
    
    Production-grade autonomous research-to-GitHub pipeline.
    Built with LangGraph + Local Ollama (No rate limits!)
    """
    pass


@cli.command()
@click.option('--papers', '-n', default=5, help='Max papers to process')
@click.option('--dry-run', is_flag=True, help='Don\'t publish to GitHub')
@click.option('--tier', type=click.Choice(['1', 'all']), default='1', help='Tier to run')
def run(papers: int, dry_run: bool, tier: str):
    """Run the LangGraph pipeline (discover papers automatically)."""
    asyncio.run(_run_async(papers, dry_run, tier, user_ideas=None))


@cli.command()
@click.option('--idea', '-i', help='Single research idea/problem statement')
@click.option('--ideas-file', '-f', type=click.Path(exists=True), help='File with multiple ideas (one per line)')
@click.option('--interactive', is_flag=True, help='Enter ideas interactively')
@click.option('--dry-run', is_flag=True, help='Don\'t publish to GitHub')
def generate(idea: str, ideas_file: str, interactive: bool, dry_run: bool):
    """Generate solutions from YOUR research ideas (no paper discovery)."""
    
    ideas = []
    
    if idea:
        ideas.append(idea)
    
    if ideas_file:
        with open(ideas_file, 'r', encoding='utf-8') as f:
            file_ideas = [
                line.strip() for line in f 
                if line.strip() and not line.strip().startswith('#')
            ]
            ideas.extend(file_ideas)
    
    if interactive:
        console.print("[cyan]💡 Enter your research ideas (one per line, empty line to finish):[/cyan]")
        while True:
            user_input = input("> ")
            if not user_input.strip():
                break
            ideas.append(user_input.strip())
    
    if not ideas:
        console.print("[red]ERROR: No ideas provided. Use --idea, --ideas-file, or --interactive[/red]")
        return
    
    console.print(f"[green]Loaded {len(ideas)} idea(s)[/green]")
    for idx, idea_text in enumerate(ideas, 1):
        console.print(f"  {idx}. {idea_text[:80]}..." if len(idea_text) > 80 else f"  {idx}. {idea_text}")
    
    asyncio.run(_run_async(papers=len(ideas), dry_run=dry_run, tier='ideas', user_ideas=ideas))


async def _run_async(papers: int, dry_run: bool, tier: str, user_ideas: Optional[List[str]] = None):
    """Async implementation of run command."""
    from src.models.schemas import ProblemStatement
    
    config = get_config()
    setup_logging(log_level=config.log_level)
    
    # Initialize supervisor
    supervisor = PipelineSupervisor(
        checkpoint_dir="./data/checkpoints",
        checkpoint_interval_seconds=300,  # 5 minutes
        max_consecutive_errors=5
    )
    
    mode_text = "USER IDEAS" if user_ideas else "PAPER DISCOVERY"
    console.print(Panel.fit(
        "[bold cyan]AUTO-GIT PUBLISHER[/bold cyan]\\n"
        f"Mode: {mode_text}\\n"
        f"Processing: {len(user_ideas) if user_ideas else papers} {'ideas' if user_ideas else 'papers'}\\n"
        f"Publish: {'DRY RUN' if dry_run else 'LIVE'}\\n"
        f"Supervisor: [green]ACTIVE[/green]",
        title="LangGraph Pipeline",
        border_style="cyan"
    ))
    
    try:
        # Start supervisor
        supervisor.start()
        
        # Test Ollama with supervision
        console.print("\n[yellow]Testing Ollama...[/yellow]")
        if not await test_ollama_connection():
            console.print("[red]❌ Start Ollama: ollama serve[/red]")
            supervisor.shutdown()
            return
        
        # Compile pipeline
        console.print("[yellow]Compiling pipeline...[/yellow]")
        app = compile_pipeline(checkpointer=True)
        
        # Create initial state
        if user_ideas:
            # User-provided ideas mode: skip discovery, go straight to debate
            state = create_initial_state()
            state["config_snapshot"] = load_config()
            
            console.print("[green]✅ Ready!\n[/green]")
            console.print("[bold yellow]💡 Processing Your Ideas[/bold yellow]\n")
            
            # Process each idea sequentially
            for idx, idea_text in enumerate(user_ideas, 1):
                console.print(f"\n[cyan]{'='*60}[/cyan]")
                console.print(f"[bold cyan]💡 IDEA {idx}/{len(user_ideas)}[/bold cyan]")
                console.print(f"[cyan]{'='*60}[/cyan]")
                console.print(f"[yellow]{idea_text}[/yellow]\n")
                
                # Create problem statement from user idea
                problem = ProblemStatement(
                    domain="User-Specified",
                    challenge=idea_text,
                    current_solutions=[],
                    limitations=["To be determined through debate"],
                    datasets=[],
                    metrics=[],
                    requirements=[],
                    paper_solution="N/A - User-provided idea"
                )
                
                # Set state for this idea
                state["problem_statement"] = problem
                state["debate_iteration"] = 1
                state["solution_proposals"] = []
                state["solution_critiques"] = []
                state["final_solution"] = None
                state["passes_validation"] = False
                
                # Run debate directly (skip discovery)
                from src.agents.tier2_debate.debate_moderator import debate_moderator_node
                state = await debate_moderator_node(state)
                
                # Check validation
                if state.get("passes_validation"):
                    console.print(f"[green]✅ Idea {idx} validated! Ready for code generation.[/green]")
                else:
                    console.print(f"[yellow]⚠️  Idea {idx} needs refinement or may not be feasible.[/yellow]")
                
                # Save checkpoint after each idea
                supervisor.save_checkpoint(state)
            
            console.print(f"\n[bold green]✅ Processed {len(user_ideas)} idea(s)[/bold green]")
            supervisor.shutdown()
            return
        
        # Normal discovery mode
        state = create_initial_state()
        state["config_snapshot"] = load_config()
        
        console.print("[green]✅ Ready!\n[/green]")
        
        # Run with supervision
        console.print("[bold yellow]Tier 1: Discovery[/bold yellow]\n")
        
        async for event in app.astream(state, config={"configurable": {"thread_id": state["pipeline_id"]}}):
            # Check for shutdown request
            if supervisor.check_shutdown():
                console.print("\n[yellow]⚠️  Graceful shutdown requested...[/yellow]")
                supervisor.save_checkpoint(state)
                break
            
            # Check if should checkpoint
            if supervisor.should_checkpoint():
                supervisor.save_checkpoint(state)
            
            for node_name, node_state in event.items():
                console.print(f"[cyan]{node_name}[/cyan]")
                
                if node_state.get("current_paper"):
                    paper = node_state["current_paper"]
                    console.print(f"  📄 {paper.title[:70]}...")
                
                if node_state.get("novelty_result") and node_name == "novelty_classifier":
                    result = node_state["novelty_result"]
                    icon = "✅" if result.threshold_pass else "❌"
                    console.print(f"  {icon} Novelty: {result.score:.1f}/10")
                
                if node_state.get("priority_result") and node_name == "priority_router":
                    result = node_state["priority_result"]
                    icon = "✅" if result.should_proceed else "⏳"
                    console.print(f"  {icon} Priority: {result.priority:.2f}\n")
        
        console.print("[bold green]Complete![/bold green]")
        
        # Show final status
        status = supervisor.get_status()
        console.print(f"\n[dim]Agents executed: {status['agents_executed']}[/dim]")
        console.print(f"[dim]Errors: {status['error_count']} | Warnings: {status['warnings_count']}[/dim]")
        
        supervisor.shutdown(state)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupt received[/yellow]")
        supervisor.save_checkpoint(state)
        supervisor.shutdown(state)
    except Exception as e:
        console.print(f"[red]❌ {str(e)}[/red]")
        logger.error("Pipeline failed", exc_info=True)
        supervisor.record_error(e, "pipeline")
        supervisor.save_error_report()
        supervisor.shutdown(state)


@cli.command()
@click.argument('paper_id')
def process(paper_id: str):
    """Process a single paper by arXiv ID."""
    config = get_config()
    setup_logging(log_level=config.log_level)
    
    console.print(f"[cyan]Processing paper: {paper_id}[/cyan]")
    
    # TODO: Implement single paper processing
    console.print("[yellow]Single paper processing coming soon...[/yellow]")


@cli.command()
def test():
    """Run system tests."""
    asyncio.run(_test_async())


async def _test_async():
    """Async implementation of test command."""
    config = get_config()
    setup_logging(log_level='INFO')
    
    console.print(Panel.fit("[bold yellow]SYSTEM TEST[/bold yellow]", border_style="yellow"))
    
    tests = [
        ("Configuration", test_config),
        ("Ollama Connection", test_ollama_test),
        ("Ollama Models", test_models),
    ]
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        for name, test_func in tests:
            task = progress.add_task(f"Testing {name}...", total=None)
            try:
                await test_func(config)
                progress.update(task, description=f"✅ {name}")
            except Exception as e:
                progress.update(task, description=f"❌ {name}: {str(e)}")


async def test_config(config):
    """Test configuration."""
    assert config.github_token, "GITHUB_TOKEN not set"
    assert config.github_username, "GITHUB_USERNAME not set"


async def test_ollama_test(config):
    """Test Ollama."""
    client = get_ollama_client()
    if not await client.health_check():
        raise Exception("Ollama not responding")


async def test_models(config):
    """Test models."""
    client = get_ollama_client()
    models = await client.list_models()
    # Handle both dict with 'name' key and dict with 'model' key
    model_names = [m.get("name") or m.get("model", "") for m in models]
    required = ["qwen3:8b", "gemma2:2b", "deepseek-coder-v2:16b"]
    missing = [m for m in required if m not in model_names]
    if missing:
        raise Exception(f"Missing: {', '.join(missing)}")


@cli.command()
def status():
    """Show pipeline status and checkpoints."""
    from pathlib import Path
    import json
    from datetime import datetime
    
    supervisor = PipelineSupervisor()
    status = supervisor.get_status()
    
    # Create status table
    table = Table(title="📊 Pipeline Status", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("State", status['state'])
    table.add_row("Agents Executed", str(status['agents_executed']))
    table.add_row("Errors", str(status['error_count']))
    table.add_row("Warnings", str(status['warnings_count']))
    table.add_row("Uptime", f"{status['uptime_seconds']:.1f}s")
    
    console.print(table)
    
    # List checkpoints
    checkpoints = supervisor.list_checkpoints()
    if checkpoints:
        console.print("\n[bold cyan]📂 Available Checkpoints:[/bold cyan]")
        for cp in checkpoints[:5]:  # Show last 5
            cp_path = Path(cp)
            try:
                with open(cp_path) as f:
                    data = json.load(f)
                    timestamp = data.get('timestamp', 'unknown')
                    agents = data.get('agents_executed', 0)
                    console.print(f"  [green]•[/green] {cp_path.name}")
                    console.print(f"    {timestamp} | {agents} agents executed")
            except:
                console.print(f"  [yellow]•[/yellow] {cp_path.name}")
    else:
        console.print("\n[dim]No checkpoints found[/dim]")


@cli.command()
@click.argument('checkpoint_path', required=False)
@click.option('--list', 'list_checkpoints', is_flag=True, help='List available checkpoints')
def resume(checkpoint_path: str, list_checkpoints: bool):
    """Resume from checkpoint."""
    supervisor = PipelineSupervisor()
    
    if list_checkpoints:
        checkpoints = supervisor.list_checkpoints()
        if not checkpoints:
            console.print("[yellow]No checkpoints found[/yellow]")
            return
        
        console.print("[bold cyan]📂 Available Checkpoints:[/bold cyan]\n")
        for i, cp in enumerate(checkpoints[:10], 1):
            console.print(f"  {i}. {Path(cp).name}")
        
        console.print("\n[dim]Usage: python run.py resume <checkpoint_path>[/dim]")
        return
    
    if not checkpoint_path:
        # Use most recent checkpoint
        checkpoints = supervisor.list_checkpoints()
        if not checkpoints:
            console.print("[red]No checkpoints found[/red]")
            return
        checkpoint_path = checkpoints[0]
        console.print(f"[cyan]Using most recent: {Path(checkpoint_path).name}[/cyan]")
    
    console.print(f"\n[yellow]Resuming from checkpoint...[/yellow]")
    
    # Load checkpoint
    state_data = supervisor.load_checkpoint(checkpoint_path)
    if not state_data:
        console.print("[red]Failed to load checkpoint[/red]")
        return
    
    console.print("[green]✅ Checkpoint loaded[/green]")
    console.print("[yellow]⚠️  Resume execution not yet fully implemented[/yellow]")
    console.print("[dim]Will be available after Phase 1 completion[/dim]")


@cli.command()
def old_status():
    """Show pipeline status."""
    console.print(Panel.fit(
        "[bold cyan]Status[/bold cyan]\n\n"
        "Tier 1: ✅ Implemented\n"
        "Tier 2-4: 🔄 Coming Soon",
        title="📊 Dashboard",
        border_style="cyan"
    ))


@cli.command()
def init():
    """Initialize databases and directories."""
    from pathlib import Path
    
    console.print("[cyan]Initializing...[/cyan]")
    
    dirs = ["./data", "./data/vector_db", "./logs", "./generated_repos"]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] {dir_path}")
    
    console.print("\n[green]✅ Complete![/green]")
    console.print("\n[yellow]Next:[/yellow]")
    console.print("1. [cyan]ollama serve[/cyan]")
    console.print("2. [cyan]python run.py test[/cyan]")
    console.print("3. [cyan]python run.py run --tier 1[/cyan]")


if __name__ == "__main__":
    cli()
