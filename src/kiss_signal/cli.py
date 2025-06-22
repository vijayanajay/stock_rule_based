"""CLI entry point using Typer framework."""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from .config import Config, load_config, load_rules
from . import data, backtester, persistence, reporter

__all__ = ["app"]

app = typer.Typer(help="KISS Signal CLI - Keep-It-Simple Signal Generation")
console = Console(record=True)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO

    # Close and remove any existing handlers
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)

    # Configure logging to use RichHandler, which prints to our console object
    # This will show logs on screen. The console object records them.
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False)]
    )

    # Silence noisy third-party loggers
    logging.getLogger('numba.core.ssa').setLevel(logging.WARNING)
    logging.getLogger('numba.core').setLevel(logging.WARNING)
    logging.getLogger('numba').setLevel(logging.WARNING)
    logging.getLogger('vectorbt').setLevel(logging.WARNING)

    # Log the start of the run
    logger = logging.getLogger(__name__)
    logger.info("=== KISS Signal CLI Run Started ===")


def _show_banner() -> None:
    """Display project banner using Rich."""
    console.print(
        Panel(
            "[bold blue]KISS Signal CLI[/bold blue]\n[italic]Keep-It-Simple Data Foundation[/italic]",
            title="QuickEdge",
            border_style="blue",
        )
    )


def _run_backtests(
    app_config: Config,
    rules_config: List[Dict[str, Any]],
    symbols: List[str],
    freeze_date: Optional[date],
) -> List[Dict[str, Any]]:
    """Run backtester for all symbols and return combined results."""
    all_results = []
    bt = backtester.Backtester(
        hold_period=getattr(app_config, "hold_period", 20),
        min_trades_threshold=getattr(app_config, "min_trades_threshold", 10),
    )

    with console.status("[bold green]Running backtests...") as status:
        for i, symbol in enumerate(symbols):
            status.update(f"Analyzing {symbol} ({i+1}/{len(symbols)})...")
            try:
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

                strategies = bt.find_optimal_strategies(
                    rule_combinations=rules_config,
                    price_data=price_data,
                    freeze_date=freeze_date,
                )
                
                for strategy in strategies:
                    strategy["symbol"] = symbol
                    all_results.append(strategy)

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
    return all_results


def _build_results_table(results: List[Dict[str, Any]]) -> Table:
    """Build a Rich Table to display top strategies."""
    table = Table(title="Top Strategies by Edge Score")
    table.add_column("Symbol", style="cyan")
    table.add_column("Rule Stack", style="green")
    table.add_column("Edge Score", justify="right", style="yellow")
    table.add_column("Win %", justify="right", style="blue")
    table.add_column("Sharpe", justify="right", style="magenta")
    table.add_column("Trades", justify="right", style="white")

    top_strategies = sorted(results, key=lambda x: x["edge_score"], reverse=True)[:10]

    for strategy in top_strategies:
        # The rule_stack now contains full rule definition dicts.
        # We extract the name for display purposes.
        rule_stack_str = " + ".join([r.get('name', r.get('type', '')) for r in strategy["rule_stack"]])
        table.add_row(
            strategy["symbol"],
            rule_stack_str,
            f"{strategy['edge_score']:.3f}",
            f"{strategy['win_pct']:.1%}",
            f"{strategy['sharpe']:.2f}",
            str(strategy["total_trades"]),
        )
    return table


def _print_results(results: List[Dict[str, Any]]) -> None:
    """Print the results summary table."""
    if not results:
        console.print("[red]No valid strategies found. Check data quality and rule configurations.[/red]")
        return

    table = _build_results_table(results)
    console.print(table)
    console.print(
        f"\n[green]✨ Analysis complete. Found {len(results)} valid strategies "
        f"across {len(set(s['symbol'] for s in results))} symbols.[/green]"
    )


def _save_results(app_config: Config, results: List[Dict[str, Any]], run_timestamp: str) -> None:
    """Save analysis results to the database."""
    if not results:
        return

    console.print("[5/5] Saving results...", style="blue")
    try:
        db_path = Path(app_config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        persistence.create_database(db_path)
        success = persistence.save_strategies_batch(db_path, results, run_timestamp)

        if success:
            logger.info(f"Saved {len(results)} strategies to database at {db_path}")
        else:
            console.print("⚠️  Failed to save results to database.", style="yellow")
            logger.warning("Persistence failed but continuing execution.")

    except Exception as e:
        console.print(f"⚠️  Database error: {e}", style="yellow")
        logger.error(f"Persistence error: {e}", exc_info=True)
        # Continue execution - don't crash CLI on persistence failure


@app.command(name="run")
def run(
    config_path: str = typer.Option(..., help="Path to config YAML file"),
    rules_path: str = typer.Option(..., help="Path to rules YAML file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)")
) -> None:
    """Run the KISS Signal analysis pipeline."""
    setup_logging(verbose)
    _show_banner()

    config_path = Path(config_path)
    rules_path = Path(rules_path)

    freeze_date: Optional[date] = None
    if freeze_data:
        try:
            freeze_date = date.fromisoformat(freeze_data)
        except ValueError:
            console.print(f"[red]Error: Invalid isoformat string for freeze_date: '{freeze_data}'[/red]")
            raise typer.Exit(1)

    try:
        # Load configuration - check if files exist before loading
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        app_config = load_config(config_path)
        rules_config = load_rules(rules_path)
        console.print("[1/4] Configuration loaded.")
        # Step 2: Refresh market data if needed
        if freeze_date:
            if verbose:
                logger.info(f"Freeze mode active: {freeze_date}")
            console.print("[2/4] Skipping data refresh (freeze mode).")
        else:
            if verbose:
                logger.info("Refreshing market data")
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
        all_results = _run_backtests(app_config, rules_config, symbols, freeze_date)        # Step 4: Display results summary
        console.print("[4/4] Analysis complete. Results summary:")
        _print_results(all_results)
        # Step 5: Save results
        run_timestamp = datetime.now().isoformat()
        _save_results(app_config, all_results, run_timestamp)

        console.print("[5/5] Generating report...", style="blue")
        try:
            report_path = reporter.generate_daily_report(
                db_path=Path(app_config.database_path),
                run_timestamp=run_timestamp,
                config=app_config,
            )
            
            if report_path:
                console.print(f"✨ Report generated: {report_path}", style="green")
            else:
                console.print("⚠️  Report generation failed", style="yellow")
                
        except Exception as e:
            console.print(f"⚠️  Report error: {e}", style="yellow")
            logger.error(f"Report generation error: {e}", exc_info=True)

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
    finally:
        # Always save the log, even if errors occurred
        try:
            console.save_text("run_log.txt")
            # This message will be on console but not in the saved file.
            console.print("\n[green]Log file saved to [bold]run_log.txt[/bold][/green]")
        except Exception as e:
            # Fallback to standard print if console is broken
            import sys
            print(f"\nCritical error: Could not save log file: {e}", file=sys.stderr)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit")
) -> None:
    """KISS Signal CLI - Keep-It-Simple Signal Generation for NSE stocks."""
    if version:
        console.print("KISS Signal CLI v1.4")
        raise typer.Exit()
    
    # If no command provided, show help
    if ctx.invoked_subcommand is None:
        console.print("No command specified. Use 'run' to execute the signal analysis.")
        console.print("Try 'python run.py --help' for help.")
        raise typer.Exit()


if __name__ == "__main__":
    app()
