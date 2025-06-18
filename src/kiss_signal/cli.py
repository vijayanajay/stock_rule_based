"""CLI entry point using Typer framework."""

import logging
from datetime import date
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config, load_rules
from . import data, backtester

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
    config_path_str: str = typer.Option("config.yaml", "--config", help="Path to config file"),
    rules_path_str: str = typer.Option("config/rules.yaml", "--rules", help="Path to rules file"),
    freeze_date_str: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)")
) -> None:
    """Run the KISS Signal analysis pipeline."""
    setup_logging(verbose)
    _show_banner()

    config_path = Path(config_path_str)
    rules_path = Path(rules_path_str)

    logger.debug(
        "Running CLI run command with verbose=%s, freeze_date=%s, config=%s, rules=%s",
        verbose,
        freeze_date_str,
        config_path,
        rules_path,
    )

    try:
        # Parse freeze date if provided
        freeze_date = date.fromisoformat(freeze_date_str) if freeze_date_str else None
        if freeze_date:
            console.print(f"[yellow]⚠️  FREEZE MODE: Using data only up to {freeze_date}[/yellow]")
        
        # Load configuration - check if files exist before loading
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
            
        # Load configuration
        app_config = load_config(config_path)
        rules_config = load_rules(rules_path)
        console.print("[1/4] Configuration loaded.")

        # Step 2: Refresh market data if needed
        if freeze_date:
            logger.debug(f"Freeze mode active: {freeze_date}")
            console.print("[2/4] Skipping data refresh (freeze mode).")
        else:
            logger.debug("Refreshing market data")
            console.print("[2/4] Refreshing market data...")
            data.refresh_market_data(
                universe_path=app_config.universe_path,
                cache_dir=app_config.cache_dir,
                refresh_days=app_config.cache_refresh_days,
                years=app_config.historical_data_years,
                freeze_date=freeze_date
            )

        # Step 3: Analyze strategies for each ticker
        console.print("[3/4] Analyzing strategies for each ticker...")
        symbols = data.load_universe(app_config.universe_path)
        all_results = []

        # Initialize backtester
        bt = backtester.Backtester(
            hold_period=getattr(app_config, 'hold_period', 20),
            min_trades_threshold=getattr(app_config, 'min_trades_threshold', 10)
        )

        with console.status("[bold green]Running backtests...") as status:
            for i, symbol in enumerate(symbols):
                status.update(f"Analyzing {symbol} ({i+1}/{len(symbols)})...")
                try:
                    # Get price data for this symbol
                    price_data = data.get_price_data(
                        symbol=symbol,
                        cache_dir=Path(app_config.cache_dir),
                        refresh_days=app_config.cache_refresh_days,
                        years=app_config.historical_data_years,
                        freeze_date=freeze_date,
                    )
                    
                    if price_data is None or len(price_data) < 100:
                        logger.warning(f"Insufficient data for {symbol}, skipping")
                        continue

                    # Run backtester on this symbol
                    strategies = bt.find_optimal_strategies(
                        rule_combinations=rules_config,
                        price_data=price_data,
                        freeze_date=freeze_date
                    )

                    # Add symbol info to each strategy
                    for strategy in strategies:
                        strategy['symbol'] = symbol
                        all_results.append(strategy)

                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")
                    continue

        # Step 4: Display results summary
        console.print("[4/4] Analysis complete. Results summary:")
        
        if all_results:
            # Create summary table
            table = Table(title="Top Strategies by Edge Score")
            table.add_column("Symbol", style="cyan")
            table.add_column("Rule Stack", style="green")
            table.add_column("Edge Score", justify="right", style="yellow")
            table.add_column("Win %", justify="right", style="blue")
            table.add_column("Sharpe", justify="right", style="magenta")
            table.add_column("Trades", justify="right", style="white")

            # Sort all results by edge score and show top 10
            top_strategies = sorted(all_results, key=lambda x: x['edge_score'], reverse=True)[:10]
            
            for strategy in top_strategies:
                rule_stack_str = " + ".join(strategy['rule_stack'])
                table.add_row(
                    strategy['symbol'],
                    rule_stack_str,
                    f"{strategy['edge_score']:.3f}",
                    f"{strategy['win_pct']:.1%}",
                    f"{strategy['sharpe']:.2f}",
                    str(strategy['total_trades'])
                )

            console.print(table)
            console.print(f"\n[green]✨ Analysis complete. Found {len(all_results)} valid strategies across {len(set(s['symbol'] for s in all_results))} symbols.[/green]")
        else:
            console.print("[red]No valid strategies found. Check data quality and rule configurations.[/red]")
    
    except typer.Exit:
        raise
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
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
