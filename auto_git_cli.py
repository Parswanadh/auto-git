#!/usr/bin/env python3
"""
AUTO-GIT CLI - Professional Research-to-Code-to-GitHub Pipeline
Author: Auto-GIT Team
License: MIT
"""

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box
import asyncio

app = typer.Typer(
    name="auto-git",
    help="🚀 Autonomous Research-to-GitHub Pipeline powered by LangGraph",
    add_completion=False
)
console = Console()

# ASCII Art Logo
LOGO = """
   ___         __           _______ ______
  / _ | __ __ / /_ ___     / ___/  /  ___/
 / __ |/ // // __// _ \   / (_ / / / /    
/_/ |_|\_,_/ \__/ \___/   \___//_/ /_/     
                                           
 Autonomous Research → Code → GitHub Pipeline
 Powered by LangGraph | Built with ❤️
"""

def show_banner():
    """Display the Auto-GIT banner"""
    console.print(Panel(
        LOGO,
        style="bold cyan",
        border_style="bright_blue",
        box=box.DOUBLE
    ))


def show_main_menu():
    """Display the main menu options"""
    table = Table(
        title="🎯 Available Commands",
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
        box=box.ROUNDED
    )
    
    table.add_column("Command", style="cyan", width=20)
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")
    
    table.add_row(
        "generate",
        "Generate code from research idea or paper",
        "✅ Ready"
    )
    table.add_row(
        "research",
        "Research-only mode (no code generation)",
        "✅ Ready"
    )
    table.add_row(
        "debate",
        "Run multi-perspective debate on idea",
        "✅ Ready"
    )
    table.add_row(
        "publish",
        "Publish existing code to GitHub",
        "🚧 Beta"
    )
    table.add_row(
        "status",
        "Check system health & configuration",
        "✅ Ready"
    )
    table.add_row(
        "config",
        "Configure API keys and settings",
        "✅ Ready"
    )
    
    console.print(table)
    console.print("\n💡 [dim]Use --help with any command for more options[/dim]\n")


@app.command()
def menu():
    """
    🎮 Interactive menu mode - browse all features
    """
    show_banner()
    show_main_menu()


@app.command()
def generate(
    idea: str = typer.Argument(..., help="Research idea or arXiv paper ID"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for generated code"),
    github: bool = typer.Option(False, "--github", "-g", help="Automatically publish to GitHub"),
    max_rounds: int = typer.Option(2, "--rounds", "-r", help="Maximum debate rounds"),
    web_search: bool = typer.Option(True, "--search/--no-search", help="Enable web search"),
):
    """
    🚀 Generate code from research idea using LangGraph pipeline
    
    This runs the full pipeline:
    1. Research (arXiv + web search)
    2. Problem extraction
    3. Multi-perspective debate
    4. Solution selection
    5. Code generation (DeepSeek Coder)
    6. GitHub publishing (if --github flag)
    
    Example:
        auto-git generate "Efficient transformer attention for long sequences"
        auto-git generate "2301.12345" --github
    """
    show_banner()
    
    console.print(f"\n[bold green]🚀 Starting Auto-GIT Pipeline[/bold green]")
    console.print(f"[cyan]Research Idea:[/cyan] {idea}")
    console.print(f"[cyan]Max Debate Rounds:[/cyan] {max_rounds}")
    console.print(f"[cyan]Web Search:[/cyan] {'✅ Enabled' if web_search else '❌ Disabled'}")
    console.print(f"[cyan]Auto-Publish:[/cyan] {'✅ Yes' if github else '❌ No'}\n")
    
    if not Confirm.ask("🤔 Ready to start?", default=True):
        console.print("[yellow]Pipeline cancelled[/yellow]")
        raise typer.Exit()
    
    # Run the pipeline
    from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline
    
    try:
        console.print("\n[bold cyan]⚙️  Initializing LangGraph workflow...[/bold cyan]\n")
        
        result = asyncio.run(run_auto_git_pipeline(
            idea=idea,
            max_debate_rounds=max_rounds,
            use_web_search=web_search,
            auto_publish=github,
            output_dir=output_dir
        ))
        
        # Display results
        console.print("\n" + "="*80)
        console.print(Panel(
            "[bold green]✅ Pipeline Completed Successfully![/bold green]",
            style="green",
            border_style="bright_green"
        ))
        
        # Show final solution
        if result.get("final_solution"):
            console.print(f"\n[bold cyan]🏆 Selected Solution:[/bold cyan]")
            console.print(f"  [green]{result['final_solution'].get('approach_name', 'N/A')}[/green]")
        
        # Show GitHub URL if published
        if result.get("github_url"):
            console.print(f"\n[bold cyan]📦 GitHub Repository:[/bold cyan]")
            console.print(f"  [link={result['github_url']}]{result['github_url']}[/link]")
        
        console.print("\n" + "="*80 + "\n")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Pipeline interrupted by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[bold red]❌ Pipeline failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def research(
    idea: str = typer.Argument(..., help="Research topic or question"),
    max_results: int = typer.Option(5, "--max", "-m", help="Maximum papers to find"),
):
    """
    🔍 Research-only mode - find papers and implementations
    
    Searches arXiv and GitHub without code generation.
    """
    show_banner()
    console.print(f"\n[bold cyan]🔍 Searching for:[/bold cyan] {idea}\n")
    
    from src.utils.web_search import ResearchSearcher
    
    searcher = ResearchSearcher()
    papers, web_results, implementations = searcher.search_comprehensive(idea, max_results=max_results)
    
    # Display papers
    if papers:
        console.print(Panel(f"[bold green]📚 Found {len(papers)} papers on arXiv[/bold green]", style="green"))
        for i, paper in enumerate(papers[:max_results], 1):
            console.print(f"\n{i}. [cyan]{paper['title']}[/cyan]")
            console.print(f"   [dim]{paper['authors']}[/dim]")
            console.print(f"   [link={paper['pdf_url']}]PDF Link[/link]")
    
    # Display implementations
    if implementations:
        console.print(f"\n[bold green]💻 Found {len(implementations)} implementations[/bold green]")
        for i, impl in enumerate(implementations[:3], 1):
            console.print(f"\n{i}. {impl.get('title', 'N/A')}")
            console.print(f"   [link={impl.get('href', '#')}]{impl.get('href', '#')}[/link]")
    
    console.print()


@app.command()
def debate(
    idea: str = typer.Argument(..., help="Research problem to debate"),
    rounds: int = typer.Option(2, "--rounds", "-r", help="Number of debate rounds"),
):
    """
    🗣️  Multi-perspective debate on research problem
    
    Runs the debate system with 3 expert perspectives:
    - ML Researcher
    - Systems Engineer
    - Applied Scientist
    """
    show_banner()
    console.print(f"\n[bold cyan]🗣️  Starting multi-perspective debate[/bold cyan]")
    console.print(f"[cyan]Topic:[/cyan] {idea}")
    console.print(f"[cyan]Rounds:[/cyan] {rounds}\n")
    
    from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline
    
    result = asyncio.run(run_auto_git_pipeline(
        idea=idea,
        max_debate_rounds=rounds,
        use_web_search=True,
        stop_after="solution_selection"  # Don't generate code
    ))
    
    console.print("\n[bold green]✅ Debate complete![/bold green]\n")


@app.command()
def status():
    """
    📊 Check system status and configuration
    
    Verifies:
    - Ollama connection
    - Available models
    - GitHub token
    - Directory structure
    """
    show_banner()
    
    console.print("[bold cyan]🔍 System Status Check[/bold cyan]\n")
    
    # Check Ollama
    console.print("[cyan]Checking Ollama...[/cyan]")
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            console.print(f"  [green]✅ Ollama running ({len(models)} models available)[/green]")
            
            # Check for required models
            model_names = [m["name"] for m in models]
            required_models = ["qwen3:4b", "deepseek-coder-v2:16b"]
            for model in required_models:
                if any(model in name for name in model_names):
                    console.print(f"  [green]✅ {model} available[/green]")
                else:
                    console.print(f"  [yellow]⚠️  {model} not found[/yellow]")
        else:
            console.print("  [red]❌ Ollama not responding[/red]")
    except Exception as e:
        console.print(f"  [red]❌ Ollama connection failed: {e}[/red]")
    
    # Check GitHub token
    console.print("\n[cyan]Checking GitHub...[/cyan]")
    import os
    if os.getenv("GITHUB_TOKEN"):
        console.print("  [green]✅ GitHub token configured[/green]")
    else:
        console.print("  [yellow]⚠️  GitHub token not set (use: export GITHUB_TOKEN=...)[/yellow]")
    
    # Check directories
    console.print("\n[cyan]Checking directories...[/cyan]")
    dirs = ["src/langraph_pipeline", "src/utils", "output"]
    for dir_path in dirs:
        import os
        if os.path.exists(dir_path):
            console.print(f"  [green]✅ {dir_path}/[/green]")
        else:
            console.print(f"  [yellow]⚠️  {dir_path}/ missing[/yellow]")
    
    console.print("\n[bold green]System check complete![/bold green]\n")


@app.command()
def config(
    github_token: Optional[str] = typer.Option(None, "--github-token", help="Set GitHub personal access token"),
    ollama_url: Optional[str] = typer.Option(None, "--ollama-url", help="Set Ollama server URL"),
):
    """
    ⚙️  Configure Auto-GIT settings
    
    Set API keys and configuration options.
    """
    show_banner()
    
    if github_token:
        # Save to .env file
        env_path = ".env"
        with open(env_path, "a") as f:
            f.write(f"\nGITHUB_TOKEN={github_token}\n")
        console.print("[green]✅ GitHub token saved to .env[/green]")
    
    if ollama_url:
        with open(".env", "a") as f:
            f.write(f"\nOLLAMA_BASE_URL={ollama_url}\n")
        console.print(f"[green]✅ Ollama URL set to {ollama_url}[/green]")
    
    if not github_token and not ollama_url:
        console.print("[yellow]No configuration changes made. Use --help for options.[/yellow]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    🚀 AUTO-GIT - Autonomous Research-to-GitHub Pipeline
    
    Transforms research ideas into working code and published GitHub repositories.
    
    Powered by LangGraph, Ollama, and Multi-Agent Debate Systems.
    """
    if ctx.invoked_subcommand is None:
        # No command specified, show menu
        menu()


if __name__ == "__main__":
    app()
