"""CLI entry point using Typer framework."""

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from .config import load_config

logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(name="quickedge", help="KISS Signal CLI - Keep-It-Simple Signal Generation")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def show_banner() -> None:
    """Display project banner using Rich."""
    banner_text = """
[bold blue]KISS Signal CLI v1.4.0[/bold blue]
[italic]Keep-It-Simple Signal Generation for NSE Equities[/italic]
    """
    console.print(Panel(banner_text, title="QuickEdge", border_style="blue"))


@app.command()
def run(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)")
) -> None:
    """Run the signal generation pipeline."""
    setup_logging(verbose)
    show_banner()
    
    try:
        # Step 1: Loading configuration
        console.print("🔧 Loading configuration...", style="yellow")
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Step 2-6: Placeholder steps
        console.print("✅ Validating universe data...", style="green")
        console.print("🚀 Initializing data manager...", style="blue")
        console.print("📊 Setting up backtester...", style="cyan")
        console.print("🎯 Preparing signal generator...", style="magenta")
        console.print("🎉 Foundation setup complete!", style="bold green")
        
        logger.info("Pipeline completed successfully")
        
    except Exception as e:
        console.print(f"❌ Error: {e}", style="bold red")
        logger.error(f"Pipeline failed: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
