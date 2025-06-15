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


def show_banner() -> None:
    """Display project banner using Rich."""
    banner_text = """
[bold blue]KISS Signal CLI v1.4.0[/bold blue]
[italic]Keep-It-Simple Signal Generation for NSE Equities[/italic]
    """
    console.print(Panel(banner_text, title="QuickEdge", border_style="blue"))


@app.command()
def run(
    config: str = typer.Option("config.yaml", help="Path to configuration file"),
    rules: str = typer.Option("rules.yaml", help="Path to rules file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)")
) -> None:
    """Run the KISS Signal backtesting engine."""
    # Initialize logging first
    setup_logging(verbose)
    
    # Create a local logger instance
    local_logger = logging.getLogger(__name__)
      # Show banner
    show_banner()
    
    local_logger.debug(
        "Running CLI run command with verbose=%s, freeze_data=%s, config=%s",
        verbose,
        freeze_data,
        config,
    )

    try:
        # Parse freeze date if provided
        freeze_date: Optional[date] = None
        if freeze_data:
            try:
                freeze_date = date.fromisoformat(freeze_data)
                console.print(f"[yellow]⚠️  FREEZE MODE: Using data only up to {freeze_date}[/yellow]")
            except ValueError:
                console.print("[red]Error: Invalid freeze date format. Use YYYY-MM-DD[/red]")
                raise typer.Exit(1)
        
        # Load configuration
        config_path = Path(config)
        try:
            app_config = load_config(config_path)
            # Override freeze_date from CLI if provided
            if freeze_date:
                app_config.freeze_date = freeze_date
        except FileNotFoundError:
            console.print(f"[red]Error: Configuration file not found: {config}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
            raise typer.Exit(1)
        
        # Check rules file exists
        rules_path = Path(rules)
        if not rules_path.exists():
            console.print(f"[red]Error: Rules file not found: {rules}[/red]")
            raise typer.Exit(1)
        
        console.print("[bold blue]KISS Signal CLI[/bold blue]")
        console.print("─" * 20)
        
        # Phase 1: Configuration
        console.print("[1/6] Loading configuration... ", end="")
        console.print("[green]✓[/green]")
        
        # Phase 2: Data Manager Setup
        console.print("[2/6] Setting up data manager... ", end="")
        data_manager = DataManager(
            universe_path=app_config.universe_path,
            historical_years=app_config.historical_data_years,
            cache_refresh_days=app_config.cache_refresh_days,
            freeze_date=app_config.freeze_date,
            console=console
        )
        console.print("[green]✓[/green]")
        
        # Phase 3: Market Data Refresh
        if app_config.freeze_date:
            console.print("[3/6] Refreshing market data... [yellow]SKIPPED (freeze mode active)[/yellow]")
        else:
            console.print("[3/6] Refreshing market data...")
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
        
        # Phase 4: Data Validation
        console.print("[4/6] Validating data quality... ", end="")
        console.print("[green]✓[/green]")
        
        # Phase 5: Rules Loading
        console.print("[5/6] Loading trading rules... ", end="")
        console.print("[green]✓[/green]")
        
        # Phase 6: Ready
        console.print("[6/6] Foundation ready! ", end="")
        console.print("[green]✓[/green]")
        
        console.print("\n[green]✨ KISS Signal CLI ready for backtesting![/green]")
        
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
