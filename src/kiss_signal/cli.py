"""CLI entry point using Typer framework."""

import logging
from datetime import date
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .data_manager import DataManager

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
        "Running CLI run command with verbose=%s, freeze_data=%s, config=%s",
        verbose,
        freeze_data,
        config,
    )

    try:
        # Parse freeze date if provided
        freeze_date: Optional[date] = None
        if freeze_data:
            freeze_date = date.fromisoformat(freeze_data)
            console.print(f"[yellow]⚠️  FREEZE MODE: Using data only up to {freeze_date}[/yellow]")
        # Load configuration
        config_path = Path(config)
        try:
            app_config = load_config(config_path)
        except FileNotFoundError:
            console.print(f"[red]Error: Configuration file not found: {config}[/red]")
            raise typer.Exit(1)
        # Check rules file exists
        rules_path = Path(rules)
        if not rules_path.exists():
            console.print(f"[red]Error: Rules file not found: {rules}[/red]")
            raise typer.Exit(1)
        console.print("\n[bold blue]Pipeline Stages[/bold blue]")
        console.print("─" * 20)
        console.print("[1/3] Loading configuration... ", end="")
        console.print("[green]✓[/green]")
        # Phase 2: Data Manager Setup
        console.print("[2/3] Setting up data manager... ", end="")
        data_manager = DataManager(
            universe_path=app_config.universe_path,
            historical_years=app_config.historical_data_years,
            cache_dir=app_config.cache_dir,
            cache_refresh_days=app_config.cache_refresh_days,
            freeze_date=freeze_date,
            console=console
        )
        console.print("[green]✓[/green]")
        # Phase 3: Market Data Refresh
        console.print("[3/3] Refreshing market data...")
        if freeze_date or app_config.freeze_date:
            console.print("      └─ [yellow]SKIPPED (freeze mode active)[/yellow]")
        else:
            try:
                results = data_manager.refresh_market_data()
                successful = sum(1 for success in results.values() if success)
                total = len(results)
                console.print(f"      └─ Cache updated successfully ({successful}/{total} symbols)")
            except Exception as e:
                console.print(f"[red]Error refreshing market data: {e}[/red]")
                if verbose:
                    console.print_exception()
                raise typer.Exit(1)
        console.print("\n[green]✨ Data refresh complete. Foundation is ready.[/green]")
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
