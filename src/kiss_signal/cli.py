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
        datefmt="[%Y-%m-%d %H:%M:%S]",
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


def _analyze_symbol(
    symbol: str, 
    app_config: Config, 
    rules_config: Any, 
    freeze_date: Optional[date], 
    bt: backtester.Backtester
) -> List[Dict[str, Any]]:
    """Helper to run backtest analysis for a single symbol."""
    try:
        price_data = data.get_price_data(
            symbol=symbol,
            cache_dir=Path(app_config.cache_dir),
            years=app_config.historical_data_years,
            freeze_date=freeze_date,
        )
        
        if price_data is None or len(price_data) < 100:
            logger.warning(f"Insufficient data for {symbol}, skipping")
            return []

        strategies = bt.find_optimal_strategies(
            rules_config=rules_config,
            price_data=price_data,
            symbol=symbol,
            freeze_date=freeze_date,
        )
        
        result = []
        for strategy in strategies:
            strategy["symbol"] = symbol
            result.append(strategy)
        return result

    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return []


def _run_backtests(
    app_config: Config,
    rules_config: Dict[str, Any],
    symbols: List[str],
    freeze_date: Optional[date],
    min_trades_threshold: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Run backtester for all symbols and return combined results."""
    # Use provided min_trades_threshold, or fall back to config, or default to 0
    threshold = min_trades_threshold if min_trades_threshold is not None else getattr(app_config, "min_trades_threshold", 0)
    
    bt = backtester.Backtester(
        hold_period=getattr(app_config, "hold_period", 20),
        min_trades_threshold=threshold,
    )
    
    all_results = []
    with console.status("[bold green]Running backtests...") as status:
        for i, symbol in enumerate(symbols):
            status.update(f"Analyzing {symbol} ({i+1}/{len(symbols)})...")
            all_results.extend(_analyze_symbol(symbol, app_config, rules_config, freeze_date, bt))
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


def _save_results(
    db_connection: persistence.Connection,
    results: List[Dict[str, Any]],
    run_timestamp: str,
    config_snapshot: Optional[Dict[str, Any]] = None,
    config_hash: Optional[str] = None
) -> None:
    """Save analysis results to the database using an existing connection."""
    if not results:
        return

    console.print("[5/5] Saving results...", style="blue")
    try:
        success = persistence.save_strategies_batch(
            db_connection, results, run_timestamp, config_snapshot, config_hash
        )

        if success:
            logger.info(f"Saved {len(results)} strategies to the database.")
        else:
            console.print("⚠️  Failed to save results to database.", style="yellow")
            logger.warning("Persistence failed but continuing execution.")

    except Exception as e:
        console.print(f"⚠️  Database error: {e}", style="yellow")
        logger.error(f"Persistence error: {e}", exc_info=True)


def _generate_and_save_report(
    app_config: Config, rules_config: Dict[str, Any], run_timestamp: str
) -> None:
    """Generate and save the daily report, handling errors gracefully."""
    console.print("[5/5] Generating report...", style="blue")
    try:
        report_path = reporter.generate_daily_report(
            db_path=Path(app_config.database_path),
            run_timestamp=run_timestamp,
            config=app_config,
            rules_config=rules_config,
        )
        if report_path: # Only print if report was generated
            console.print(f"* Report generated: {report_path}", style="green")
        else:
            console.print("(WARN) Report generation failed", style="yellow")
    except Exception as e:
        console.print(f"(WARN) Report error: {e}", style="yellow")
        logger.error(f"Report generation error: {e}", exc_info=True)


def _process_and_save_results(
    db_connection: persistence.Connection, 
    all_results: List[Dict[str, Any]], 
    app_config: Config, 
    rules_config: Any
) -> None:
    """Helper to display, save, and report results."""
    run_timestamp = datetime.now().isoformat()
    rules_dict = rules_config.model_dump() if hasattr(rules_config, 'model_dump') else dict(rules_config)
    config_snapshot = persistence.create_config_snapshot(rules_dict, app_config, app_config.freeze_date.isoformat() if app_config.freeze_date else None)
    config_hash = persistence.generate_config_hash(rules_dict, app_config)
    
    _display_results(all_results)
    _save_results(db_connection, all_results, run_timestamp, config_snapshot, config_hash)
    _generate_and_save_report(app_config, rules_config, run_timestamp)


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
    # This prevents the main callback from running for --help or completion scripts
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
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)"),
    min_trades: Optional[int] = typer.Option(None, "--min-trades", help="Minimum trades required during backtesting (None = use config default)")
) -> None:
    """Run the KISS Signal analysis pipeline."""
    _show_banner()

    app_config = ctx.obj["config"]
    rules_config = ctx.obj["rules"]
    verbose = ctx.obj["verbose"]
    db_connection = None

    freeze_date_obj: Optional[date] = None
    if freeze_data:
        try:
            freeze_date_obj = date.fromisoformat(freeze_data)
            app_config.freeze_date = freeze_date_obj
        except ValueError:
            console.print(f"[red]Error: Invalid isoformat string for freeze_date: '{freeze_data}'[/red]")
            raise typer.Exit(1)

    try:
        db_path = Path(app_config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        persistence.create_database(db_path)
        db_connection = persistence.get_connection(db_path)

        with performance_monitor.monitor_execution("full_backtest"):
            console.print("[1/4] Configuration loaded.")
            if app_config.freeze_date:
                if verbose: logger.info(f"Freeze mode active: {app_config.freeze_date}")
                console.print("[2/4] Skipping data refresh (freeze mode).")
            else:
                if verbose: logger.info("Refreshing market data")
                console.print("[2/4] Refreshing market data...")
                data.refresh_market_data(
                    universe_path=app_config.universe_path,
                    cache_dir=app_config.cache_dir,
                    years=app_config.historical_data_years,
                    freeze_date=app_config.freeze_date,
                )

            console.print("[3/4] Analyzing strategies for each ticker...")
            symbols = data.load_universe(app_config.universe_path)
            all_results = _run_backtests(app_config, rules_config, symbols, app_config.freeze_date, min_trades)

            console.print("[4/4] Analysis complete. Results summary:")
            
            _process_and_save_results(db_connection, all_results, app_config, rules_config)

        if verbose:
            perf_summary = performance_monitor.get_summary()
            if perf_summary:
                console.print("\n[bold blue]Performance Summary:[/bold blue]")
                console.print(f"Total Duration: {perf_summary['total_duration']:.2f}s")
                console.print(f"Slowest Function: {perf_summary['slowest_function']}")

    except (typer.Exit, FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
    finally:
        # Save log regardless of success or failure
        try:
            log_path = Path("run_log.txt")
            log_path.write_text(console.export_text(clear=False), encoding="utf-8")
            logger.info(f"Log file saved to {log_path}")
        except OSError as log_e:
            error_msg = f"Critical error: Could not save log file to run_log.txt. Reason: {log_e}"
            logger.error(error_msg, exc_info=True)
            console.print(f"[red]{error_msg}[/red]")
        
        if db_connection:
            db_connection.close()
            logger.info("Database connection closed.")


@app.command(name="analyze-strategies")
def analyze_strategies(
    ctx: typer.Context,
    output_file: Path = typer.Option(
        "strategy_performance_report.csv",
        "--output", "-o",
        help="Path to save the strategy performance report as a CSV file.",
    ),
    per_stock: bool = typer.Option(
        False,
        "--per-stock",
        help="Generate detailed per-stock strategy report instead of the aggregated leaderboard.",
    ),
    min_trades: Optional[int] = typer.Option(
        None,
        "--min-trades",
        help="Minimum trades required for analysis (None = use default threshold)",
    ),
) -> None:
    """Analyze and report on the comprehensive performance of all strategies."""
    format_desc = "per-stock strategy" if per_stock else "aggregated strategy"
    console.print(f"[bold blue]Analyzing {format_desc} performance...[/bold blue]")
    app_config = ctx.obj["config"]
    db_path = Path(app_config.database_path)

    if not db_path.exists():
        console.print(f"[red]Error: Database file not found at {db_path}[/red]")
        raise typer.Exit(1)

    try:
        # Use provided min_trades or fall back to default of 10
        min_trades_value = min_trades if min_trades is not None else 10
        
        if per_stock:
            strategy_performance = reporter.analyze_strategy_performance(db_path, min_trades=min_trades_value)
        else:
            strategy_performance = reporter.analyze_strategy_performance_aggregated(db_path, min_trades=min_trades_value)
            
        if not strategy_performance:
            console.print("[yellow]No historical strategies found to analyze.[/yellow]")
            return

        report_content = reporter.format_strategy_analysis_as_csv(strategy_performance, aggregate=not per_stock)
        output_file.write_text(report_content, encoding="utf-8")
        console.print(f"✅ Strategy performance analysis saved to: [cyan]{output_file}[/cyan]")

    except Exception as e:
        console.print(f"[red]An unexpected error occurred during analysis: {e}[/red]")
        if ctx.obj and isinstance(ctx.obj, dict) and ctx.obj.get("verbose", False):
            console.print_exception()
        raise typer.Exit(1)
    finally:
        # Save log regardless of success or failure
        try:
            log_path = Path("analyze_strategies_log.txt")
            log_path.write_text(console.export_text(clear=False), encoding="utf-8")
            logger.info(f"Log file saved to {log_path}")
        except OSError as log_e:
            error_msg = f"Critical error: Could not save log file to {log_path}. Reason: {log_e}"
            logger.error(error_msg, exc_info=True)
            console.print(f"[red]{error_msg}[/red]")


@app.command(name="clear-and-recalculate")
def clear_and_recalculate(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
    preserve_all: bool = typer.Option(False, "--preserve-all", help="Skip clearing, analysis only"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data at this date (YYYY-MM-DD format)"),
) -> None:
    """Intelligently clear current strategies and recalculate with preservation of historical data."""
    app_config = ctx.obj["config"]
    rules_config = ctx.obj["rules"]
    db_path = Path(app_config.database_path)

    if not db_path.exists():
        console.print(f"[red]Error: Database file not found at {db_path}[/red]")
        raise typer.Exit(1)

    db_connection = None
    try:
        freeze_date_obj = freeze_data  # Keep as string for persistence layer compatibility
        
        if not preserve_all and not force:
            # Show preview information before confirmation
            from .config import get_active_strategy_combinations
            import json
            
            with persistence.get_connection(db_path) as conn:
                rules_dict = rules_config.model_dump()
                current_config_hash = persistence.generate_config_hash(rules_dict, app_config)
                
                active_strategies = get_active_strategy_combinations(rules_config)

                total_count = conn.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
                
                delete_count_query = f"""
                    SELECT COUNT(*) FROM strategies
                    WHERE config_hash = ? AND rule_stack IN ({','.join(['?'] * len(active_strategies))})
                """
                will_delete = conn.execute(delete_count_query, [current_config_hash] + active_strategies).fetchone()[0]
                preserved_count = total_count - will_delete

                console.print(f"[blue]Current database contains {total_count} strategies[/blue]")
                console.print(f"[green]Will preserve {preserved_count} historical strategies[/green]")
                console.print(f"[yellow]Will clear {will_delete} current strategy records[/yellow]")

                if not force and will_delete > 0:
                    if not typer.confirm("Continue with intelligent clearing?"):
                        console.print("[blue]Operation cancelled.[/blue]")
                        raise typer.Exit(0)

        # Use the extracted business logic function
        result = persistence.clear_and_recalculate_strategies(
            db_path, app_config, rules_config, 
            force=force, preserve_all=preserve_all, freeze_date=freeze_date_obj
        )

        console.print(f"✅ [bold green]Operation complete![/bold green]")
        console.print(f"[green]Cleared: {result['cleared_count']} strategies[/green]")
        console.print(f"[green]Preserved: {result['preserved_count']} historical strategies[/green]")
        console.print(f"[green]New strategies found: {result['new_strategies']}[/green]")

    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        if ctx.obj and isinstance(ctx.obj, dict) and ctx.obj.get("verbose"):
            console.print_exception()
        raise typer.Exit(1)
    finally:
        # Save log regardless of success or failure
        try:
            log_path = Path("clear_and_recalculate_log.txt")
            log_path.write_text(console.export_text(clear=False), encoding="utf-8")
            logger.info(f"Log file saved to {log_path}")
        except OSError as log_e:
            error_msg = f"Critical error: Could not save log file to {log_path}. Reason: {log_e}"
            logger.error(error_msg, exc_info=True)
            console.print(f"[red]{error_msg}[/red]")
