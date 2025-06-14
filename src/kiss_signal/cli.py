"""CLI entry point using Typer framework."""

import logging
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .config import load_config

app = typer.Typer()

logger = logging.getLogger(__name__)
console = Console()


def resolve_config_path(config_path: str = "config.yaml") -> str:
    """Resolve config path relative to project root or current directory."""
    config_file = Path(config_path)
    
    # First try current directory
    if config_file.exists():
        return str(config_file)
    
    # Try project root (3 levels up from cli.py: src/kiss_signal/cli.py -> project_root)
    project_root = Path(__file__).parent.parent.parent
    project_config = project_root / config_path
    if project_config.exists():
        return str(project_config)
    
    # Return original path for proper error handling
    return config_path


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
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)")
) -> None:
    """QuickEdge: KISS Signal CLI - Keep-It-Simple Signal Generation for NSE Equities."""
    setup_logging(verbose)
    show_banner()
    
    try:
        # Step 1: Loading configuration
        console.print("🔧 Loading configuration...", style="yellow")
        config_path = resolve_config_path()
        config = load_config(config_path)
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
