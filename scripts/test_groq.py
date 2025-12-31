"""
Test Groq API connection.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from groq import Groq
from rich.console import Console
from rich.panel import Panel

from src.utils.config import get_config
from src.utils.logger import setup_logging, get_logger


console = Console()


async def test_groq():
    """Test Groq API connection and models."""
    config = get_config()
    logger = setup_logging(log_level='INFO')
    
    if not config.groq_api_key:
        console.print("[red]❌ GROQ_API_KEY not set in .env[/red]")
        return False
    
    console.print(Panel.fit(
        "[bold cyan]Testing Groq API Connection[/bold cyan]",
        border_style="cyan"
    ))
    
    try:
        # Initialize client
        client = Groq(api_key=config.groq_api_key)
        
        # Test gpt-oss-20b (analysis model)
        console.print("\n[yellow]Testing gpt-oss-20b...[/yellow]")
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{
                "role": "user",
                "content": "Say 'Hello from AUTO-GIT Publisher!' in exactly 5 words."
            }],
            max_tokens=50,
            temperature=0.5
        )
        
        result = response.choices[0].message.content
        console.print(f"[green]✓[/green] Response: {result}")
        console.print(f"[dim]Tokens used: {response.usage.total_tokens}[/dim]")
        
        # Test gpt-oss-120b (code generation model)
        console.print("\n[yellow]Testing gpt-oss-120b...[/yellow]")
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{
                "role": "user",
                "content": "Write a Python function that returns 'Hello World'"
            }],
            max_tokens=100,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        console.print(f"[green]✓[/green] Generated code:")
        console.print(f"[dim]{result[:200]}...[/dim]")
        console.print(f"[dim]Tokens used: {response.usage.total_tokens}[/dim]")
        
        console.print("\n[bold green]✅ All Groq API tests passed![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Groq API test failed: {str(e)}[/red]")
        logger.error("Groq API test failed", exc_info=True)
        return False


if __name__ == "__main__":
    print("🧪 Testing Groq API...")
    success = asyncio.run(test_groq())
    sys.exit(0 if success else 1)
