"""Enhanced CLI module for MEQSAP with comprehensive error handling and user experience features."""

import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Optional, Tuple
import importlib.metadata

import pandas as pd
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

# Core application modules - import actual functions
from src.meqsap import __version__
from src.meqsap.config import (
    load_yaml_config,
    validate_config,
    StrategyConfig,
)
from src.meqsap.data import fetch_market_data
from src.meqsap.backtest import run_complete_backtest, BacktestAnalysisResult
from src.meqsap.reporting import generate_complete_report
from src.meqsap.exceptions import (
    MEQSAPError,
    ConfigurationError,
    DataError, # For catching from data module
    DataAcquisitionError,
    BacktestError, # For catching from backtest module
    BacktestExecutionError,
    ReportingError, # For catching from reporting module
    ReportGenerationError,
)

# Create the main app with proper command structure
app = typer.Typer(
    name="meqsap",
    help="MEQSAP - Market Equity Quantitative Strategy Analysis Platform\n\n"
         "A comprehensive tool for backtesting and analyzing quantitative trading strategies.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Global console instance - will be reconfigured based on CLI options
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


@app.command("analyze")
def analyze_command(
    config_file: Path = typer.Argument(
        ...,
        help="Path to the YAML configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    validate_only: bool = typer.Option(
        False,
        "--validate-only",
        help="Only validate the configuration, don't run backtest",
    ),
    report: bool = typer.Option(
        False,
        "--report",
        help="Generate PDF report after analysis",
    ),
    output_dir: Optional[Path] = typer.Option(
        "./reports",
        "--output-dir",
        help="Directory for output reports",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output with detailed logging and diagnostics",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q", 
        help="Suppress non-essential output (minimal output mode)",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output",
    ),
) -> None:
    """
    Analyze a trading strategy with MEQSAP using a YAML configuration file.

    This command loads the configuration, fetches market data, runs a backtest, 
    and generates comprehensive analysis reports for the MEQSAP platform.

    Examples:
        meqsap analyze config.yaml
        meqsap analyze config.yaml --report --verbose
        meqsap analyze config.yaml --validate-only
        meqsap analyze config.yaml --output-dir ./custom_reports --report
    """
    # Validate mutually exclusive options
    if verbose and quiet:
        console.print("[bold red]Error:[/bold red] --verbose and --quiet flags cannot be used together")
        raise typer.Exit(code=1)
    
    # Configure global console and logging based on options
    _configure_application_context(verbose=verbose, quiet=quiet, no_color=no_color)
    
    try:
        exit_code = _main_pipeline(
            config_file=config_file,
            report=report,
            verbose=verbose,
            quiet=quiet,
            dry_run=validate_only,
            output_dir=output_dir,
            no_color=no_color,
        )
        raise typer.Exit(code=exit_code)
    except typer.Exit:
        raise  # Re-raise typer.Exit as-is
    except Exception as e:
        error_msg = _generate_error_message(e, verbose=verbose, no_color=no_color) # type: ignore
        console.print(error_msg)
        raise typer.Exit(code=10)  # Use distinct exit code for unexpected errors


def _configure_application_context(verbose: bool, quiet: bool, no_color: bool) -> None:
    """Configure logging and console settings based on CLI options."""
    global console
    
    # Configure console
    if no_color:
        console = Console(color_system=None)
    else:
        console = Console()
    
    # Configure logging
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("src.meqsap").setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)
    else:
        logging.getLogger().setLevel(logging.INFO)


def _main_pipeline(
    config_file: Path,
    report: bool,
    verbose: bool, 
    quiet: bool,
    dry_run: bool,
    output_dir: Optional[Path],
    no_color: bool,
) -> int:
    """
    Main pipeline execution function with comprehensive error handling.
    
    Returns:
        int: Exit code (0 for success, non-zero for various error conditions)
    """
    start_time = time.time()
    
    try:
        # Step 1: Validate and load configuration
        config = _validate_and_load_config(config_file, verbose, quiet)
        
        # Step 2: Handle dry-run mode
        if dry_run:
            return _handle_dry_run_mode(config, quiet)
        
        # Step 3: Execute data acquisition pipeline
        market_data = _handle_data_acquisition(config, verbose, quiet)
        
        # Step 4: Execute backtest and analysis pipeline
        analysis_result = _execute_backtest_pipeline(market_data, config, verbose, quiet)
          # Step 5: Generate output and reports
        _generate_output(
            analysis_result=analysis_result,
            config=config,
            report=report,
            output_dir=output_dir,
            quiet=quiet,
            no_color=no_color,
            verbose=verbose,
        )
        
        # Step 6: Report success and timing
        if not quiet:
            elapsed_time = time.time() - start_time
            console.print(f"\n[bold green]✓ MEQSAP analysis completed successfully in {elapsed_time:.2f} seconds[/bold green]")
        return 0
        
    except ConfigurationError as e:
        error_msg = _generate_error_message(e, verbose=verbose, no_color=no_color)
        console.print(error_msg)
        return 1  # Configuration errors
    except DataAcquisitionError as e:
        error_msg = _generate_error_message(e, verbose=verbose, no_color=no_color)
        console.print(error_msg)
        return 2  # Data acquisition failures
    except BacktestExecutionError as e:
        error_msg = _generate_error_message(e, verbose=verbose, no_color=no_color)
        console.print(error_msg)
        return 3  # Computation failures  
    except ReportGenerationError as e:
        error_msg = _generate_error_message(e, verbose=verbose, no_color=no_color)
        console.print(error_msg)
        return 4  # Output generation failures
    except Exception as e:
        # Log the unexpected error for debugging
        logging.exception("An unexpected error occurred in main pipeline")
        
        error_msg = _generate_error_message(e, verbose=verbose, no_color=no_color)
        console.print(error_msg)
        return 10  # Distinct exit code for unexpected errors


def _validate_and_load_config(config_file: Path, verbose: bool, quiet: bool) -> StrategyConfig:
    """
    Enhanced configuration loading with detailed validation error reporting.
    
    Args:
        config_file: Path to configuration file
        verbose: Enable verbose output
        quiet: Enable quiet mode
        
    Returns:
        StrategyConfig: Validated configuration object
        
    Raises:
        ConfigurationError: For any configuration validation failures
    """
    if not quiet:
        console.print(f"📋 Loading configuration from: [cyan]{config_file}[/cyan]")
    
    try:
        # File system validation
        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_file}")
        
        if not config_file.is_file():
            raise ConfigurationError(f"Path is not a file: {config_file}")
        
        if not config_file.suffix.lower() in ['.yaml', '.yml']:
            raise ConfigurationError(f"Configuration file must have .yaml or .yml extension: {config_file}")
        
        # YAML syntax validation and schema validation using existing functions
        try:
            # Use load_yaml_config from the config module
            raw_config_data = load_yaml_config(config_file) # Will raise exceptions.ConfigurationError
            config = validate_config(raw_config_data) # Will raise exceptions.ConfigurationError
            strategy_params = config.validate_strategy_params() # Will raise exceptions.ConfigurationError
        except ConfigurationError as e: # Catch the centralized ConfigurationError
            raise ConfigurationError(f"Configuration error: {e}")
        except Exception as e:
            raise ConfigurationError(f"Unexpected error processing configuration file {config_file}: {e}")
        
        if not quiet:
            console.print(
                Panel(
                    f"[bold green]✓ Configuration valid![/bold green]\n\n"
                    f"Strategy: [bold]{config.strategy_type}[/bold]\n"
                    f"Ticker: [bold]{config.ticker}[/bold]\n"
                    f"Date Range: [bold]{config.start_date}[/bold] to [bold]{config.end_date}[/bold]",
                    title="📊 MEQSAP Configuration",
                    expand=False,
                    border_style="green"
                )
            )
        
        if verbose and not quiet:
            console.print("\n[bold underline]Strategy Parameters:[/bold underline]")
            for key, value in strategy_params.model_dump().items():
                console.print(f"  [bold cyan]{key.replace('_', ' ').title()}[/bold cyan]: {value}")
            console.print()
        
        return config
        
    except ConfigurationError as e: # Catch the centralized ConfigurationError
        raise ConfigurationError(f"Configuration validation failed: {e}")
    except Exception as e:
        raise ConfigurationError(f"Unexpected error loading configuration: {e}")


def _handle_dry_run_mode(config: StrategyConfig, quiet: bool) -> int:
    """
    Handle dry-run mode - validate configuration without executing backtest.
    
    Args:
        config: Validated configuration
        quiet: Enable quiet mode
        
    Returns:
        int: Exit code (0 for valid config, 1 for issues)
    """
    if not quiet:
        console.print("\n[bold blue]🔍 Dry-run mode - Configuration validation only[/bold blue]")
        
        # Show what operations would be performed
        operations_table = Table(title="Planned Operations", show_header=True, header_style="bold magenta")
        operations_table.add_column("Operation", style="cyan")
        operations_table.add_column("Details", style="white")
        
        operations_table.add_row("Data Acquisition", f"Fetch {config.ticker} from {config.start_date} to {config.end_date}")
        operations_table.add_row("Strategy", f"Execute {config.strategy_type} strategy")
        operations_table.add_row("Backtesting", "Run complete backtest with vibe checks")
        operations_table.add_row("Output", "Generate terminal report")
        
        console.print(operations_table)
        console.print("\n[green]✓ Configuration is valid. Ready for execution.[/green]")
        console.print("[dim]Use without --dry-run to execute the backtest.[/dim]")
    
    return 0


def _handle_data_acquisition(config: StrategyConfig, verbose: bool, quiet: bool) -> pd.DataFrame:
    """
    Wrapper for data acquisition with progress indicators and error handling.
    
    Args:
        config: Strategy configuration
        verbose: Enable verbose output
        quiet: Enable quiet mode
        
    Returns:
        pd.DataFrame: Validated market data
        
    Raises:
        DataAcquisitionError: For any data acquisition failures
    """
    try:
        if not quiet:
            console.print(f"\n📈 Fetching market data for [bold cyan]{config.ticker}[/bold cyan] "
                         f"from [bold]{config.start_date}[/bold] to [bold]{config.end_date}[/bold]...")
        
        # Use progress indicator for data acquisition
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=quiet,
        ) as progress:
            task = progress.add_task("Downloading market data...", total=None)
            market_data = fetch_market_data(config.ticker, config.start_date, config.end_date)
            progress.update(task, completed=100)
        
        if not quiet:
            console.print(f"[green]✓[/green] Market data received: [bold]{len(market_data)}[/bold] bars")
            
            if verbose:
                console.print("\n[bold underline]Data Sample (first 3 rows):[/bold underline]")
                console.print(market_data.head(3))
                console.print()
        
        return market_data
        
    except DataError as e: # Catch DataError from data.py
        raise DataAcquisitionError(f"Failed to acquire market data: {e}")
    except Exception as e:
        raise DataAcquisitionError(f"Unexpected error during data acquisition: {e}")


def _execute_backtest_pipeline(
    data: pd.DataFrame, 
    config: StrategyConfig, 
    verbose: bool, 
    quiet: bool
) -> BacktestAnalysisResult:
    """
    Orchestrate signal generation, backtesting, and validation checks.
    
    Args:
        data: Market data
        config: Strategy configuration  
        verbose: Enable verbose output
        quiet: Enable quiet mode
        
    Returns:
        BacktestAnalysisResult: Complete analysis results
        
    Raises:
        BacktestExecutionError: For any computation failures
    """
    try:
        if not quiet:
            console.print("\n🔄 Running backtest analysis...")
        
        # Use progress indicator for backtest execution
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            disable=quiet,
        ) as progress:
            task = progress.add_task("Executing backtest and analysis...", total=None)
            analysis_result = run_complete_backtest(config, data)
            progress.update(task, completed=100)
        
        if not quiet:
            console.print("[green]✓[/green] Backtest analysis complete")
        
        return analysis_result
        
    except BacktestError as e: # Catch BacktestError from backtest.py
        raise BacktestExecutionError(f"Backtest execution failed: {e}")
    except Exception as e:
        raise BacktestExecutionError(f"Unexpected error during backtest execution: {e}")


def _generate_output(
    analysis_result: BacktestAnalysisResult,
    config: StrategyConfig,
    report: bool,
    output_dir: Optional[Path],
    quiet: bool,
    no_color: bool,
    verbose: bool = False,
) -> None:
    """
    Orchestrate all output generation (terminal and PDF reports).
    
    Args:
        analysis_result: Backtest results
        config: Strategy configuration
        report: Generate PDF report
        output_dir: Custom output directory
        quiet: Enable quiet mode
        no_color: Disable colored output
        verbose: Enable verbose output
        
    Raises:
        ReportGenerationError: For any output generation failures
    """
    try:
        # Determine output directory
        output_directory_str = str(output_dir) if output_dir else "./reports"
        
        if not quiet:
            if report:
                console.print(f"\n📄 Generating reports (PDF: Yes, Output Dir: [cyan]{output_directory_str}[/cyan])...")
            else:
                console.print("\n📄 Generating terminal report...")
        
        # Generate reports with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=quiet,
        ) as progress:
            task = progress.add_task("Generating reports...", total=None)
            
            pdf_path = generate_complete_report(
                analysis_result=analysis_result,
                include_pdf=report,
                output_directory=output_directory_str,
                no_color=no_color,
                quiet=quiet,
            )
            
            progress.update(task, completed=100)
        
        # Report PDF generation success
        if report and pdf_path and not quiet:
            resolved_pdf_path = Path(pdf_path).resolve()
            console.print(f"[green]✓[/green] PDF report generated: [link=file://{resolved_pdf_path}]{resolved_pdf_path}[/link]")
        elif report and not pdf_path and not quiet:
            console.print("[yellow]⚠[/yellow] PDF report was requested but generation failed (check logs)")
        
        # Show trade details in verbose mode
        if verbose and not quiet:
            _display_trade_details(analysis_result)
            
    except ReportingError as e:
        raise ReportGenerationError(f"Report generation failed: {e}")
    except Exception as e:
        raise ReportGenerationError(f"Unexpected error during report generation: {e}")


def _display_trade_details(analysis_result: BacktestAnalysisResult) -> None:
    """Display detailed trade information in verbose mode."""
    primary_result = analysis_result.primary_result
    if primary_result and primary_result.total_trades > 0 and hasattr(primary_result, 'trade_details') and primary_result.trade_details:
        console.print("\n[bold underline]Trade Details (first 5):[/bold underline]")
        for i, trade_detail in enumerate(primary_result.trade_details[:5]):
            console.print(
                f"  [bold]Trade {i+1}:[/bold] "
                f"Entry: {trade_detail.get('entry_date', 'N/A')} @ ${trade_detail.get('entry_price', 0.0):.2f}, "
                f"Exit: {trade_detail.get('exit_date', 'N/A')} @ ${trade_detail.get('exit_price', 0.0):.2f}, "
                f"PnL: ${trade_detail.get('pnl', 0.0):.2f} ({trade_detail.get('return_pct', 0.0):.2f}%)"
            )
        if len(primary_result.trade_details) > 5:
            console.print(f"  ... and {len(primary_result.trade_details) - 5} more trades not shown.")
        console.print()
    elif primary_result and primary_result.total_trades == 0:
        console.print("\n[yellow]⚠ No trades were executed during the backtest.[/yellow]")


def _generate_error_message(exception: Exception, verbose: bool = False, no_color: bool = False) -> str:
    """
    Generate user-friendly error messages with recovery suggestions.
    
    Args:
        exception: The exception that occurred
        verbose: Include detailed debug information
        no_color: Disable colored output
        
    Returns:
        str: Formatted error message with suggestions
    """
    error_type = type(exception).__name__
    error_msg = str(exception)
    
    # Base error message
    if no_color:
        message_parts = [f"{error_type}: {error_msg}"]
    else:
        message_parts = [f"[bold red]{error_type}:[/bold red] {error_msg}"]
    
    # Add recovery suggestions based on error type
    suggestions = _get_recovery_suggestions(exception)
    if suggestions:
        message_parts.append("\n[bold yellow]Suggested Solutions:[/bold yellow]")
        for suggestion in suggestions:
            message_parts.append(f"  • {suggestion}")
    
    # Add debug information in verbose mode
    if verbose:
        message_parts.append("\n[bold underline]Debug Information:[/bold underline]")
        if no_color:
            message_parts.append(traceback.format_exc())
        else:
            message_parts.append(f"[dim]{traceback.format_exc()}[/dim]")
    
    return "\n".join(message_parts)


def _get_recovery_suggestions(exception: Exception) -> list[str]:
    """Get specific recovery suggestions based on exception type."""
    suggestions = []
    
    if isinstance(exception, ConfigurationError):
        suggestions.extend([
            "Verify the YAML file syntax is correct",
            "Check that all required fields are present",
            "Ensure date ranges are valid (start < end, not in future)",
            "Validate ticker symbol format",
            "Try using --dry-run to validate configuration without execution",
            "Check examples in documentation for proper YAML structure"
        ])
    elif isinstance(exception, DataAcquisitionError):
        suggestions.extend([
            "Check your internet connection",
            "Verify the ticker symbol exists and is correctly spelled",
            "Try a different date range (some tickers have limited historical data)",
            "Wait a moment and try again (rate limiting)",
            "Check if yfinance service is experiencing issues",
            "Try using a more common ticker symbol to test connectivity"
        ])
    elif isinstance(exception, BacktestExecutionError):
        suggestions.extend([
            "Verify your strategy parameters are reasonable",
            "Check that your data has sufficient history for the strategy",
            "Ensure moving average periods are less than data length",
            "Try reducing the complexity of your strategy parameters",
            "Check for data quality issues in your date range",
            "Consider using --verbose for more detailed error information"
        ])
    elif isinstance(exception, ReportGenerationError):
        suggestions.extend([
            "Check that the output directory exists and is writable",
            "Ensure you have sufficient disk space",
            "Try running without --report flag to skip PDF generation",
            "Verify all required dependencies for PDF generation are installed",
            "Check file permissions in the output directory",
            "Try specifying a different output directory with --output-dir"
        ])
    else:
        suggestions.extend([
            "Try running with --verbose for more details",
            "Check the documentation for troubleshooting guides",
            "Verify all dependencies are properly installed",
            "Try running --version to check dependency status",
            "Consider using --dry-run to isolate configuration issues",
            "Check if this is a known issue in the project documentation"
        ])
    
    return suggestions


@app.command("version")
def version_command():
    """Display version information."""
    console.print(f"MEQSAP version: {__version__}")


def cli_main():
    """
    Main entry point for the CLI application.
    This function is called when the script is executed directly or via console script.
    """
    app()


if __name__ == "__main__":
    cli_main()