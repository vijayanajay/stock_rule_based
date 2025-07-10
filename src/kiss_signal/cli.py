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


def _save_results(
    db_connection: persistence.Connection,
    results: List[Dict[str, Any]],
    run_timestamp: str,
) -> None:
    """Save analysis results to the database using an existing connection."""
    if not results:
        return

    console.print("[5/5] Saving results...", style="blue")
    try:
        success = persistence.save_strategies_batch(db_connection, results, run_timestamp)

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
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data to specific date (YYYY-MM-DD)")
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
                    refresh_days=app_config.cache_refresh_days,
                    years=app_config.historical_data_years,
                    freeze_date=app_config.freeze_date,
                )

            console.print("[3/4] Analyzing strategies for each ticker...")
            symbols = data.load_universe(app_config.universe_path)
            all_results = _run_backtests(app_config, rules_config, symbols, app_config.freeze_date)

            console.print("[4/4] Analysis complete. Results summary:")
            run_timestamp = datetime.now().isoformat()
            _display_results(all_results)
            _save_results(db_connection, all_results, run_timestamp)
            _generate_and_save_report(app_config, rules_config, run_timestamp)

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
        if db_connection:
            db_connection.close()
            logger.info("Database connection closed.")


@app.command(name="analyze-rules")
def analyze_rules(
    ctx: typer.Context,
    output_file: Path = typer.Option(
        "rule_performance_analysis.md",
        "--output",
        "-o",
        help="Path to save the markdown analysis report.",
    ),
) -> None:
    """Analyze and report on the historical performance of individual rules."""
    console.print("[bold blue]Analyzing historical rule performance...[/bold blue]")
    app_config = ctx.obj["config"]
    db_path = Path(app_config.database_path)

    if not db_path.exists():
        console.print(f"[red]Error: Database file not found at {db_path}[/red]")
        raise typer.Exit(1)

    try:
        rule_performance = reporter.analyze_rule_performance(db_path)
        if not rule_performance:
            console.print("[yellow]No historical strategies found in the database to analyze.[/yellow]")
            return

        report_content = reporter.format_rule_analysis_as_md(rule_performance)
        output_file.write_text(report_content, encoding="utf-8")
        console.print(f"✅ Rule performance analysis saved to: [cyan]{output_file}[/cyan]")

    except Exception as e:
        console.print(f"[red]An unexpected error occurred during analysis: {e}[/red]")
        if ctx.obj and ctx.obj.get("verbose", False):
            console.print_exception()
        raise typer.Exit(1)


@app.command(name="analyze-strategies")
def analyze_strategies(
    ctx: typer.Context,
    output_file: Path = typer.Option(
        "strategy_performance_report.csv",
        "--output", "-o",
        help="Path to save the strategy performance report as a CSV file.",
    ),
) -> None:
    """Analyze and report on the historical performance of all strategy combinations."""
    console.print("[bold blue]Analyzing historical strategy performance...[/bold blue]")
    app_config = ctx.obj["config"]
    db_path = Path(app_config.database_path)

    if not db_path.exists():
        console.print(f"[red]Error: Database file not found at {db_path}[/red]")
        raise typer.Exit(1)

    try:
        strategy_performance = reporter.analyze_strategy_performance(db_path)
        if not strategy_performance:
            console.print("[yellow]No historical strategies found to analyze.[/yellow]")
            return

        report_content = reporter.format_strategy_analysis_as_csv(strategy_performance)
        output_file.write_text(report_content, encoding="utf-8")
        console.print(f"✅ Strategy performance report saved to: [cyan]{output_file}[/cyan]")

        # Save log before completing
        try:
            log_path = Path("analyze_strategies_log.txt")
            log_path.write_text(console.export_text(clear=False), encoding="utf-8")
            logger.info(f"Log file saved to {log_path}")
        except OSError as log_e:
            error_msg = f"Critical error: Could not save log file to {log_path}. Reason: {log_e}"
            logger.error(error_msg, exc_info=True)
            console.print(f"[red]{error_msg}[/red]")

    except Exception as e:
        console.print(f"[red]An unexpected error occurred during analysis: {e}[/red]")
        if ctx.obj and ctx.obj.get("verbose", False):
            console.print_exception()
        # Save log before exiting
        try:
            log_path = Path("analyze_strategies_log.txt")
            log_path.write_text(console.export_text(clear=False), encoding="utf-8")
            logger.info(f"Log file saved to {log_path}")
        except OSError as log_e:
            error_msg = f"Critical error: Could not save log file to {log_path}. Reason: {log_e}"
            logger.error(error_msg, exc_info=True)
            console.print(f"[red]{error_msg}[/red]")
        raise typer.Exit(1)


@app.command(name="clear-and-recalculate")
def clear_and_recalculate(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data at this date (YYYY-MM-DD format)"),
) -> None:
    """Clear all strategies from database and recalculate them with current parameters."""
    app_config = ctx.obj["config"]
    rules_config = ctx.obj["rules"]
    db_path = Path(app_config.database_path)

    if not db_path.exists():
        console.print(f"[red]Error: Database file not found at {db_path}[/red]")
        raise typer.Exit(1)

    if not force and not typer.confirm(f"⚠️ This will permanently delete all strategies from {db_path}. Continue?"):
        console.print("[blue]Operation cancelled.[/blue]")
        raise typer.Exit(0)

    try:
        with persistence.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM strategies")
            deleted_count = cursor.rowcount
            conn.commit()
            console.print(f"✅ Deleted {deleted_count} strategy records.")

            # Reuse the existing backtesting logic from the `run` command
            console.print("[bold blue]Starting fresh backtesting run...[/bold blue]")
            symbols = data.load_universe(app_config.universe_path)
            freeze_date_obj = date.fromisoformat(freeze_data) if freeze_data else None
            all_results = _run_backtests(app_config, rules_config, symbols, freeze_date_obj)

            console.print("[bold blue]Saving new strategies...[/bold blue]")
            run_timestamp = datetime.now().isoformat()
            _save_results(conn, all_results, run_timestamp)

            console.print(f"✅ [bold green]Recalculation complete! Found {len(all_results)} new strategies.[/bold green]")

    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        if ctx.obj.get("verbose"):
            console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
