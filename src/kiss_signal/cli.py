"""CLI entry point using Typer framework."""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

import typer
import rich.progress as progress
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from .config import Config, load_config, load_rules
from . import data, backtester, persistence, reporter
from .performance import performance_monitor

__all__ = ["app"]

app = typer.Typer(help="KISS Signal CLI - Keep-It-Simple Signal Generation")
console = Console(record=True)

logger = logging.getLogger(__name__)


# impure
def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO

    # Configure logging to use RichHandler. `force=True` removes existing handlers.
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False)],
        force=True,
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


def _create_progress_context() -> progress.Progress:
    """Create progress context for long-running operations."""
    return progress.Progress(
        progress.SpinnerColumn(),
        progress.TextColumn("[progress.description]{task.description}"),
        progress.BarColumn(),
        progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        progress.TimeElapsedColumn(),
        console=console,
    )


def _run_backtests(
    app_config: Config,
    rules_config: Dict[str, Any],
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
                    rules_config=rules_config,
                    price_data=price_data,
                    symbol=symbol,
                    freeze_date=freeze_date,
                )
                
                for strategy in strategies:
                    strategy["symbol"] = symbol
                    all_results.append(strategy)

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
    return all_results


def _display_results(results: List[Dict[str, Any]]) -> None:
    """Build and display a Rich Table of top strategies."""
    if not results:
        console.print("[red]No valid strategies found. Check data quality and rule configurations.[/red]")
        return

    table = Table(title="Top Strategies by Edge Score")
    table.add_column("Symbol", style="cyan")
    table.add_column("Rule Stack", style="green")
    table.add_column("Edge Score", justify="right", style="yellow")
    table.add_column("Win %", justify="right", style="blue")
    table.add_column("Sharpe", justify="right", style="magenta")
    table.add_column("Trades", justify="right", style="white")
 
    top_strategies = sorted(results, key=lambda x: x["edge_score"], reverse=True)[:10]
 
    for strategy in top_strategies:
        # The rule_stack now contains RuleDef Pydantic models.
        # We extract the name for display purposes.
        rule_stack_str = " + ".join([getattr(r, 'name', r.type) for r in strategy["rule_stack"]])
        table.add_row(
            strategy["symbol"],
            rule_stack_str,
            f"{strategy['edge_score']:.3f}",
            f"{strategy['win_pct']:.1%}",
            f"{strategy['sharpe']:.2f}",
            str(strategy["total_trades"]),
        )
 
    console.print(table)
    console.print(
        f"\n[green]* Analysis complete. Found {len(results)} valid strategies "
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


def _generate_and_save_report(
    app_config: Config, run_timestamp: str
) -> None:
    """Generate and save the daily report, handling errors gracefully."""
    console.print("[5/5] Generating report...", style="blue")
    try:
        report_path = reporter.generate_daily_report(
            db_path=Path(app_config.database_path),
            run_timestamp=run_timestamp,
            config=app_config,
        )
        if report_path:
            console.print(f"* Report generated: {report_path}", style="green")
        else:
            console.print("(WARN) Report generation failed", style="yellow")
    except Exception as e:
        console.print(f"(WARN) Report error: {e}", style="yellow")
        logger.error(f"Report generation error: {e}", exc_info=True)


@app.callback()
def main(
    ctx: typer.Context,
    config_path: str = typer.Option("config.yaml", "--config", help="Path to config YAML file."),
    rules_path: str = typer.Option("config/rules.yaml", "--rules", help="Path to rules YAML file."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """
    KISS Signal CLI.
    """
    if ctx.resilient_parsing:
        return

    setup_logging(verbose)
    
    # Store loaded configs in the context
    try:
        ctx.obj = {
            "config": load_config(Path(config_path)),
            "rules": load_rules(Path(rules_path)),
            "verbose": verbose,
        }
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="run")
def run(
    ctx: typer.Context,
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)")
) -> None:
    """Run the KISS Signal analysis pipeline."""
    _show_banner()

    app_config = ctx.obj["config"]
    rules_config = ctx.obj["rules"]
    verbose = ctx.obj["verbose"]

    freeze_date_obj: Optional[date] = None
    if freeze_data:
        try:
            freeze_date_obj = date.fromisoformat(freeze_data)
            # Override config's freeze_date with CLI flag if provided
            app_config.freeze_date = freeze_date_obj
        except ValueError:
            console.print(f"[red]Error: Invalid isoformat string for freeze_date: '{freeze_data}'[/red]")
            raise typer.Exit(1)

    try:
        with performance_monitor.monitor_execution("full_backtest"):
            console.print("[1/4] Configuration loaded.")

            # Step 2: Refresh market data if needed
            if app_config.freeze_date:
                if verbose:
                    logger.info(f"Freeze mode active: {app_config.freeze_date}")
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
                    freeze_date=app_config.freeze_date,
                )

            # Step 3: Analyze strategies for each ticker
            console.print("[3/4] Analyzing strategies for each ticker...")
            symbols = data.load_universe(app_config.universe_path)
            all_results = _run_backtests(app_config, rules_config, symbols, app_config.freeze_date)

            # Step 4: Display results summary and save
            console.print("[4/4] Analysis complete. Results summary:")
            run_timestamp = datetime.now().isoformat()
            _display_results(all_results)
            _save_results(app_config, all_results, run_timestamp)
            _generate_and_save_report(app_config, run_timestamp)

        # Show performance summary if verbose
        if verbose:
            perf_summary = performance_monitor.get_summary()
            if perf_summary:
                console.print("\n[bold blue]Performance Summary:[/bold blue]")
                console.print(f"Total Duration: {perf_summary['total_duration']:.2f}s")
                console.print(f"Slowest Function: {perf_summary['slowest_function']}")

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
            try:
                console.print_exception()
            except Exception as pe_e: # pe_e for print_exception_error
                # Log this internal error to stderr, as console might be problematic
                print(f"Error during console.print_exception(): {pe_e}", file=sys.stderr)
        raise typer.Exit(1)
    finally:
        # Always save the log, even if errors occurred
        try:
            # Use console.export_text() and standard file I/O for robustness.
            # console.save_text() can be brittle in some environments (e.g., CI/CD).
            Path("run_log.txt").write_text(console.export_text(clear=False), encoding="utf-8")
            # This message will be on console but not in the saved file.
            print("\nLog file saved to run_log.txt", file=sys.stderr)
        except Exception as e:
            # Fallback to standard print if console is broken
            print(f"\nCritical error: Could not save log file: {e}", file=sys.stderr)


if __name__ == "__main__":
    app()