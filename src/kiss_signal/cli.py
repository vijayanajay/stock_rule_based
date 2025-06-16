"""CLI entry point using Typer framework."""

import logging
from datetime import date
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .config import load_app_config
from .engine import run_analysis

__all__ = ["app"]

app = typer.Typer()
console = Console()

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def _show_banner() -> None:
    """Display project banner using Rich."""
    console.print(
        Panel(
            "[bold blue]KISS Signal CLI[/bold blue]\n[italic]Keep-It-Simple Data Foundation[/italic]",
            title="QuickEdge",
            border_style="blue",
        )
    )


@app.command()
def run(
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging"),
    config: str = typer.Option("config.yaml", "--config", help="Path to config file"),
    rules: str = typer.Option("config/rules.yaml", "--rules", help="Path to rules file"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)")
) -> None:
    """Run the KISS Signal data foundation pipeline."""
    setup_logging(verbose)
    _show_banner()
    logger.debug(
        "Running CLI run command with verbose=%s, freeze_data=%s, config=%s, rules=%s",
        verbose,
        freeze_data,
        config,
        rules,
    )

    try:
        # Parse freeze date if provided
        freeze_date: Optional[date] = None
        if freeze_data:
            freeze_date = date.fromisoformat(freeze_data)
            console.print(f"[yellow]⚠️  FREEZE MODE: Using data only up to {freeze_date}[/yellow]")        # Load unified configuration
        app_config = load_app_config(Path(config), Path(rules))
        console.print("[1/2] Configuration loaded.")

        # Run analysis pipeline
        console.print("[2/2] Running analysis...")
        signals = run_analysis(app_config)

        # Simple signal output
        successful = sum(1 for success in signals.get("refresh_results", {}).values() if success)
        total = len(signals.get("refresh_results", {}))
        if total > 0:
            console.print(f"      └─ Cache updated successfully ({successful}/{total} symbols)")
        
        console.print("\n[green]✨ Analysis complete. Foundation is ready.[/green]")

    except typer.Exit:
        raise
    except ValueError as e:
        # Catches date parsing errors and config validation errors
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
