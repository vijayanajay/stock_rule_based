"""CLI entry point using Typer framework."""

import logging
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .config import Config, load_config

app = typer.Typer()

logger = logging.getLogger(__name__)
console = Console()


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
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)"),
    config_file: str = typer.Option(
        "config.yaml", "--config", help="Path to the configuration file."
    ),
) -> None:
    """Run the KISS Signal pipeline: load config and print a success message."""
    # Initialize logging first
    setup_logging(verbose)
    
    # Create a local logger instance
    local_logger = logging.getLogger(__name__)
    
    # Show banner
    show_banner()
    
    local_logger.debug(
        "Running CLI run command with verbose=%s, freeze_data=%s, config_file=%s",
        verbose,
        freeze_data,
        config_file,
    )

    try:
        config_path = Path(config_file)
        if not config_path.exists():
            console.print(f"❌ Error: Configuration file not found: {config_file}", style="bold red")
            local_logger.error(f"Configuration file not found: {config_file}")
            raise typer.Exit(1)
        console.print(f"🔧 Loading configuration from [cyan]{config_file}[/cyan]...", style="yellow")
        config: Config = load_config(config_path)
        local_logger.info("Configuration and rules loaded successfully")
        console.print("🎉 Foundation setup complete!", style="bold green")
        local_logger.info("Pipeline completed successfully")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="bold red")
        local_logger.error(f"Pipeline failed: {e}", exc_info=verbose)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
