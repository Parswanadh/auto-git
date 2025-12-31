#!/usr/bin/env python
"""
Entry point for auto-git command
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from auto_git_interactive import interactive_session
from rich.console import Console

console = Console()

def main():
    """Main entry point for auto-git command"""
    try:
        asyncio.run(interactive_session())
    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Goodbye![/cyan]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
