"""CLI entry point using Typer framework."""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

import pandas as pd
import typer
import rich.progress as progress
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from .config import Config, load_config, load_rules
from . import data, backtester, persistence
from .backtester import Backtester  # For test compatibility
from .reporter import (
    generate_daily_report,
    format_walk_forward_results,
    analyze_strategy_performance,
    analyze_strategy_performance_aggregated,
    format_strategy_analysis_as_csv,
    update_positions_and_generate_report_data,
    get_position_pricing as _reporter_get_position_pricing,
)

# Public wrappers with explicit type hints to maintain stable CLI-facing API
def get_position_pricing(symbol: str, app_config: Config) -> Optional[Dict[str, float]]:  # pragma: no cover thin wrapper
    return _reporter_get_position_pricing(symbol, app_config)

# Backwards compatibility shim for tests (deleted function)


from .performance import performance_monitor
from .exceptions import DataMismatchError

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



def _create_progress_context() -> progress.Progress:  # pragma: no cover - test stub
    """Create progress context for long-running operations."""
    return progress.Progress(console=console)



def _analyze_symbol(
    symbol: str, 
    app_config: Config, 
    rules_config: Any, 
    freeze_date: Optional[date], 
    bt: backtester.Backtester,
    market_data: Optional[pd.DataFrame] = None,
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

        latest_close = price_data['close'].iloc[-1]

        strategies = bt.find_optimal_strategies(
            price_data=price_data,
            rules_config=rules_config,
            market_data=market_data,
            symbol=symbol,
            freeze_date=freeze_date,
            edge_score_weights=app_config.edge_score_weights,
            config=app_config,  # Add config parameter
        )
        
        result = []
        for strategy in strategies:
            strategy["symbol"] = symbol
            strategy["latest_close"] = latest_close  # Attach the latest close price
            result.append(strategy)
        return result

    except DataMismatchError as e:
        logger.error(f"CRITICAL: Market data for ^NSEI does not cover the full history for {symbol}. Run data refresh.")
        return []
    except FileNotFoundError as e:
        logger.error(f"Data file not found for {symbol}: {e}")
        return []
    except ValueError as e:
        logger.error(f"Configuration error for {symbol}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return []



def display_results(results: List[Dict[str, Any]]) -> None:
    """Build and display a Rich Table of top strategies."""
    if not results:
        console.print("[red]No valid strategies found. Check data quality and rule configurations.[/red]")
        return

    # Check if we have walk-forward results
    oos_results = [r for r in results if r.get("is_oos", False)]
    
    if oos_results:
        # Display walk-forward specific summary
        console.print("[bold blue]Walk-Forward Analysis Results (Out-of-Sample Only)[/bold blue]")
        walk_forward_summary = format_walk_forward_results(oos_results)
        console.print(walk_forward_summary)
    else:
        # Display traditional table for in-sample results
        console.print("[bold yellow]In-Sample Results (NOT reliable for live trading)[/bold yellow]")
        
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
            # Handle both dict (from tests) and object formats
            def extract_rule_name(r: Any) -> str:
                if isinstance(r, dict):
                    return r.get('name') or r.get('type') or str(r)
                else:
                    return getattr(r, 'name', getattr(r, 'type', str(r)))
            
            rule_stack_str = " + ".join([extract_rule_name(r) for r in strategy["rule_stack"]])
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


# Back-compat: legacy tests import _display_results (removed during refactor).
# Provide alias to preserve external observable contract without duplication.
_display_results = display_results  # pragma: no cover


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


def _parse_freeze_date(freeze_data: Optional[str]) -> Optional[date]:
    """Parse and validate freeze date parameter."""
    if not freeze_data:
        return None
    
    try:
        return date.fromisoformat(freeze_data)
    except ValueError:
        console.print(f"[red]Error: Invalid isoformat string for freeze_date: '{freeze_data}'[/red]")
        raise typer.Exit(1)


def _save_command_log(log_filename: Optional[str]) -> None:
    """Save command log to file with error handling."""
    if not log_filename:
        logger.debug("No log filename provided, skipping log file save.")
        return

    try:
        log_path = Path(log_filename)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(console.export_text(clear=False), encoding="utf-8")
        logger.info(f"Log file saved to {log_path}")
    except OSError as log_e:
        error_msg = f"Critical error: Could not save log file to {log_filename}. Reason: {log_e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")


def _handle_command_exception(e: Exception, verbose: bool, context: str = "") -> None:
    """Handle command exceptions with appropriate logging."""
    # Preserve typer.Exit exceptions with their original exit codes
    if isinstance(e, typer.Exit):
        raise e
    
    if isinstance(e, (FileNotFoundError, ValueError)):
        error_msg = str(e)
    else:
        error_msg = f"An unexpected error occurred {context}: {e}" if context else f"An unexpected error occurred: {e}"
    
    console.print(f"[red]{'Error: ' if isinstance(e, (FileNotFoundError, ValueError)) else ''}{error_msg}[/red]")
    
    if verbose and not isinstance(e, (FileNotFoundError, ValueError)):
        console.print_exception()
    
    raise typer.Exit(1)




def _process_and_save_results(
    db_connection: persistence.Connection, 
    all_results: List[Dict[str, Any]], 
    app_config: Config, 
    rules_config: Any
) -> None:
    """Helper to display, save, update positions, and report results."""
    run_timestamp = datetime.now().isoformat()
    rules_dict = rules_config.model_dump() if hasattr(rules_config, 'model_dump') else dict(rules_config)
    config_snapshot = persistence.create_config_snapshot(rules_dict, app_config, app_config.freeze_date.isoformat() if app_config.freeze_date else None)
    config_hash = persistence.generate_config_hash(rules_dict, app_config)
    
    display_results(all_results)
    _save_results(db_connection, all_results, run_timestamp, config_snapshot, config_hash)

    # New pipeline step: update positions and get report data
    console.print("[5/5] Generating report...", style="blue")
    try:
        report_data = update_positions_and_generate_report_data(
            Path(app_config.database_path), run_timestamp, app_config, rules_config
        )

        # Call the new, simpler reporter
        report_path = generate_daily_report(
            new_buy_signals=report_data["new_buys"],
            open_positions=report_data["open"],
            closed_positions=report_data["closed"],
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


def _execute_analysis_pipeline(
    ctx: typer.Context,
    log_file: str,
    output_file: Path,
    per_stock: bool,
    min_trades: Optional[int],
) -> None:
    """Executes the analysis-only command pipeline."""
    app_config = ctx.obj["config"]
    
    db_path = Path(app_config.database_path)
    if not db_path.exists():
        console.print("[yellow]No historical strategies found to analyze.[/yellow]")
        _save_command_log(log_file)
        return
    
    format_desc = "per-stock strategy" if per_stock else "aggregated strategy"
    console.print(f"[bold blue]Analyzing {format_desc} performance...[/bold blue]")
    
    try:
        min_trades_value = min_trades if min_trades is not None else 10
        strategy_performance = (analyze_strategy_performance if per_stock else analyze_strategy_performance_aggregated)(db_path, min_trades=min_trades_value)
        
        if not strategy_performance:
            console.print("[yellow]No strategy data found.[/yellow]")
            return
        
        report_content = format_strategy_analysis_as_csv(strategy_performance, aggregate=not per_stock)
        if output_file is not None:
            output_file.write_text(report_content, encoding="utf-8")
            console.print(f"✅ Strategy performance analysis saved to: [cyan]{output_file}[/cyan]")
    except (OSError, PermissionError) as write_error:
        raise ValueError(f"Cannot write to output path: {output_file}") from write_error
    except Exception as e:
        verbose = ctx.obj["verbose"]
        _handle_command_exception(e, verbose, "during analysis")
    finally:
        _save_command_log(log_file)


def _execute_backtest_pipeline(
    ctx: typer.Context,
    freeze_data: Optional[str],
    log_file: str,
    clear_strategies: bool,
    min_trades: Optional[int],
    force: bool,
    preserve_all: bool,
) -> None:
    """Executes the backtesting and reporting pipeline for run/clear commands."""
    app_config = ctx.obj["config"]
    rules_config = ctx.obj["rules"]
    verbose = ctx.obj["verbose"]
    
    app_config.freeze_date = _parse_freeze_date(freeze_data)
    
    if not clear_strategies:  # Only show banner for run command
        _show_banner()
    
    db_connection = None
    
    try:
        # Database setup
        db_path = Path(app_config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        persistence.create_database(db_path)
        db_connection = persistence.get_connection(db_path)

        # Strategy clearing (clear-and-recalculate only)
        if clear_strategies and not preserve_all:
            if not force:
                from .config import get_active_strategy_combinations
                
                rules_dict = rules_config.model_dump()
                current_config_hash = persistence.generate_config_hash(rules_dict, app_config)
                active_strategies = get_active_strategy_combinations(rules_config)

                total_count = db_connection.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
                delete_count_query = f"""
                    SELECT COUNT(*) FROM strategies
                    WHERE config_hash = ? AND rule_stack IN ({','.join(['?'] * len(active_strategies))})
                """
                will_delete = db_connection.execute(delete_count_query, [current_config_hash] + active_strategies).fetchone()[0]
                preserved_count = total_count - will_delete

                console.print(f"[blue]Current database contains {total_count} strategies[/blue]")
                console.print(f"[green]Will preserve {preserved_count} historical strategies[/green]")
                console.print(f"[yellow]Will clear {will_delete} current strategy records[/yellow]")

                if not typer.confirm("Are you sure you want to continue with intelligent clearing?"):
                    console.print("[blue]Operation cancelled.[/blue]")
                    raise typer.Exit(0)

            clear_result = persistence.clear_strategies_for_config(db_connection, app_config, rules_config)
            console.print(f"✅ Cleared: {clear_result['cleared_count']} strategies")
            console.print(f"✅ Preserved: {clear_result['preserved_count']} historical strategies")

        # Core workflow - inline backtesting workflow
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
            threshold = min_trades if min_trades is not None else getattr(app_config, "min_trades_threshold", 0)
            
            # Inline backtester logic
            bt = backtester.Backtester(
                hold_period=getattr(app_config, "hold_period", 20),
                min_trades_threshold=threshold,
                initial_capital=getattr(app_config, "portfolio_initial_capital", 100000.0),
            )
            
            # Fetch market data once if context filters are present
            market_data = None
            context_filters = getattr(rules_config, 'context_filters', [])
            if context_filters:
                for filter_def in context_filters:
                    if hasattr(filter_def, 'type') and filter_def.type == "market_above_sma":
                        index_symbol = filter_def.params.get("index_symbol", "^NSEI")
                        try:
                            market_data = data.get_price_data(
                                symbol=index_symbol,
                                cache_dir=Path(app_config.cache_dir),
                                years=app_config.historical_data_years,
                                freeze_date=app_config.freeze_date,
                            )
                            logger.info(f"Loaded market data for {index_symbol}")
                            break  # Only need to load once
                        except Exception as e:
                            logger.warning(f"Could not load market data for {index_symbol}: {e}")
            
            all_results = []
            with console.status("[bold green]Running backtests...") as status:
                for i, symbol in enumerate(symbols):
                    status.update(f"Analyzing {symbol} ({i+1}/{len(symbols)})...")
                    all_results.extend(_analyze_symbol(symbol, app_config, rules_config, app_config.freeze_date, bt, market_data))
            
            console.print("[4/4] Analysis complete. Results summary:")
            _process_and_save_results(db_connection, all_results, app_config, rules_config)
            
            if clear_strategies:
                console.print(f"✅ New strategies found: {len(all_results)}")

        # Performance summary
        if verbose:
            perf_summary = performance_monitor.get_summary()
            if perf_summary:
                console.print("\n[bold blue]Performance Summary:[/bold blue]")
                console.print(f"Total Duration: {perf_summary['total_duration']:.2f}s")
                console.print(f"Slowest Function: {perf_summary['slowest_function']}")

    except Exception as e:
        context = "during clearing and recalculation" if clear_strategies else "during run pipeline"
        _handle_command_exception(e, verbose, context)
    finally:
        if db_connection:
            db_connection.close()
            logger.info("Database connection closed.")
        _save_command_log(log_file)


@app.command(name="run")
def run(
    ctx: typer.Context,
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)"),
    min_trades: Optional[int] = typer.Option(None, "--min-trades", help="Minimum trades required during backtesting (None = use config default)"),
) -> None:
    """Run the KISS Signal analysis pipeline with professional walk-forward validation."""
    _execute_backtest_pipeline(ctx, freeze_data, "run_log.txt", clear_strategies=False, min_trades=min_trades, force=False, preserve_all=False)


@app.command(name="analyze-strategies")
def analyze_strategies(
    ctx: typer.Context,
    output_file: Path = typer.Option("strategy_performance_report.csv", "--output", "-o", help="Path to save the strategy performance report as a CSV file."),
    per_stock: bool = typer.Option(False, "--per-stock", help="Generate detailed per-stock strategy report instead of the aggregated leaderboard."),
    min_trades: Optional[int] = typer.Option(None, "--min-trades", help="Minimum trades required for analysis (None = use default threshold)"),
) -> None:
    """Analyze and report on the comprehensive performance of all strategies."""
    _execute_analysis_pipeline(ctx, "analyze_strategies_log.txt", output_file, per_stock, min_trades)


@app.command(name="clear-and-recalculate")
def clear_and_recalculate(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
    preserve_all: bool = typer.Option(False, "--preserve-all", help="Skip clearing, analysis only"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data at this date (YYYY-MM-DD format)"),
) -> None:
    """Intelligently clear current strategies and recalculate with preservation of historical data."""
    _execute_backtest_pipeline(ctx, freeze_data, "clear_and_recalculate_log.txt", clear_strategies=True, min_trades=None, force=force, preserve_all=preserve_all)
