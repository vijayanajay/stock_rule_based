"""
Reporting and Presentation Module for MEQSAP.

This module provides formatted terminal output and PDF report generation
functionality using rich for terminal formatting and pyfolio for PDF reports.
"""

import os
import warnings
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

try:
    # For direct imports when used as a package
    from .backtest import BacktestResult, VibeCheckResults, RobustnessResults, BacktestAnalysisResult
    from .exceptions import ReportingError
except ImportError:
    # For imports when running tests or if structure changes
    from src.meqsap.backtest import BacktestResult, VibeCheckResults, RobustnessResults, BacktestAnalysisResult  # type: ignore
    from src.meqsap.exceptions import ReportingError  # type: ignore
from .config import StrategyConfig  # This import should be fine as it's a sibling module

# Optional pyfolio import with graceful degradation
try:
    import pyfolio as pf
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    PYFOLIO_AVAILABLE = True
except ImportError:
    PYFOLIO_AVAILABLE = False
    pf = None

logger = logging.getLogger(__name__)


class ReportConfig(BaseModel):
    """Configuration for report generation."""
    
    include_pdf: bool = Field(False, description="Whether to generate PDF report")
    output_directory: str = Field("./reports", description="Directory for report output")
    filename_prefix: str = Field("meqsap_report", description="Prefix for report filenames")
    include_plots: bool = Field(True, description="Whether to include plots in PDF")
    decimal_places: int = Field(2, ge=0, le=6, description="Decimal places for formatting")
    color_output: bool = Field(True, description="Whether to use colored terminal output")


class ExecutiveVerdictData(BaseModel):
    """Formatted data for executive verdict display."""
    
    strategy_name: str = Field(..., description="Name of the strategy")
    ticker: str = Field(..., description="Stock ticker symbol")
    date_range: str = Field(..., description="Formatted date range")
    total_return: str = Field(..., description="Formatted total return")
    annual_return: str = Field(..., description="Formatted annualized return")
    sharpe_ratio: str = Field(..., description="Formatted Sharpe ratio")
    max_drawdown: str = Field(..., description="Formatted maximum drawdown")
    win_rate: str = Field(..., description="Formatted win rate")
    total_trades: int = Field(..., description="Total number of trades")
    vibe_check_status: str = Field(..., description="Overall vibe check status")
    robustness_score: str = Field(..., description="Formatted robustness assessment")
    overall_verdict: str = Field(..., description="Overall strategy verdict")


def format_percentage(value: float, decimal_places: int = 2, include_sign: bool = True) -> str:
    """Format a decimal value as a percentage."""
    if pd.isna(value) or not np.isfinite(value):
        return "N/A"
    
    formatted = f"{value:.{decimal_places}f}%"
    if include_sign and value > 0:
        formatted = "+" + formatted
    return formatted


def format_currency(value: float, decimal_places: int = 2) -> str:
    """Format a value as currency."""
    if pd.isna(value) or not np.isfinite(value):
        return "N/A"
    
    return f"${value:,.{decimal_places}f}"


def format_number(value: float, decimal_places: int = 2) -> str:
    """Format a numeric value with specified decimal places."""
    if pd.isna(value) or not np.isfinite(value):
        return "N/A"
    
    return f"{value:.{decimal_places}f}"


def get_performance_color(metric_name: str, value: float) -> str:
    """Get color code for performance metrics based on thresholds."""
    if pd.isna(value) or not np.isfinite(value):
        return "white"
    
    color_rules = {
        "total_return": {"good": 10.0, "bad": -5.0},  # Thresholds in percentage
        "annual_return": {"good": 15.0, "bad": 0.0},
        "sharpe_ratio": {"good": 1.0, "bad": 0.0},
        "max_drawdown": {"good": -10.0, "bad": -25.0},  # Note: negative values
        "win_rate": {"good": 55.0, "bad": 45.0},
    }
    
    if metric_name not in color_rules:
        return "white"
    
    thresholds = color_rules[metric_name]
    
    if metric_name == "max_drawdown":
        # For drawdown, positive values are invalid (should always be <= 0)
        if value > 0:
            return "red"
        # For valid negative drawdown values, better is less negative (closer to 0)
        if value >= thresholds["good"]:
            return "green"
        elif value <= thresholds["bad"]:
            return "red"
        else:
            return "yellow"
    else:
        # For other metrics, higher is better
        if value >= thresholds["good"]:
            return "green"
        elif value <= thresholds["bad"]:
            return "red"
        else:
            return "yellow"


def format_performance_metrics(backtest_result: BacktestResult, decimal_places: int = 2) -> Dict[str, str]:
    """Format raw performance metrics for display."""
    
    metrics = {
        "total_return": format_percentage(backtest_result.total_return, decimal_places),
        "annual_return": format_percentage(backtest_result.annualized_return, decimal_places),
        "sharpe_ratio": format_number(backtest_result.sharpe_ratio, decimal_places + 1),
        "max_drawdown": format_percentage(backtest_result.max_drawdown, decimal_places),
        "win_rate": format_percentage(backtest_result.win_rate, decimal_places),
        "volatility": format_percentage(backtest_result.volatility, decimal_places),
        "calmar_ratio": format_number(backtest_result.calmar_ratio, decimal_places + 1),
        "final_value": format_currency(backtest_result.final_value, 0),
        "profit_factor": format_number(backtest_result.profit_factor, decimal_places + 1),
    }
    
    return metrics


def determine_overall_verdict(
    vibe_checks: VibeCheckResults, 
    robustness_checks: RobustnessResults, 
    backtest_result: BacktestResult
) -> tuple[str, List[str]]:
    """Determine overall strategy verdict and recommendations."""
    
    recommendations = []
    
    # Critical failure conditions
    if not vibe_checks.overall_pass:
        return "FAIL", ["Strategy failed basic validation checks - review vibe check results"]
    
    if backtest_result.total_trades == 0:
        return "FAIL", ["Strategy generated no trades - inactive or misconfigured"]
    
    # Performance-based evaluation
    performance_issues = []
    
    if backtest_result.sharpe_ratio < 0.5:
        performance_issues.append("Low Sharpe ratio indicates poor risk-adjusted returns")
    
    if backtest_result.max_drawdown < -30:  # More than 30% drawdown
        performance_issues.append(f"High maximum drawdown ({backtest_result.max_drawdown:.1f}%)")
    
    if robustness_checks.sharpe_degradation > 75:
        performance_issues.append("Strategy highly sensitive to transaction costs")
    
    if robustness_checks.turnover_rate > 50:
        performance_issues.append("Very high turnover rate may not be practical")
    
    # Determine verdict
    if len(performance_issues) >= 3:
        return "FAIL", performance_issues
    elif len(performance_issues) >= 1:
        return "WARNING", performance_issues + robustness_checks.recommendations
    else:
        return "PASS", robustness_checks.recommendations or ["Strategy shows good performance characteristics"]


def create_strategy_summary_table(
    strategy_config: StrategyConfig, 
    backtest_result: BacktestResult,
    color_output: bool = True
) -> Table:
    """Create a summary table with strategy information."""
    
    table = Table(
        title="Strategy Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold blue",
        title_style="bold magenta"
    )
    
    table.add_column("Parameter", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    
    # Add strategy information
    table.add_row("Strategy Type", strategy_config.strategy_type)
    table.add_row("Ticker", strategy_config.ticker.upper())
    table.add_row("Date Range", f"{strategy_config.start_date} to {strategy_config.end_date}")
    
    # Add strategy parameters
    strategy_params = strategy_config.validate_strategy_params()
    for key, value in strategy_params.model_dump().items():
        table.add_row(f"  {key.replace('_', ' ').title()}", str(value))
    
    # Add basic performance info
    table.add_row("", "")  # Separator
    table.add_row("Total Trades", str(backtest_result.total_trades))
    table.add_row("Final Portfolio Value", format_currency(backtest_result.final_value, 0))
    
    return table


def create_performance_table(
    backtest_result: BacktestResult, 
    decimal_places: int = 2,
    color_output: bool = True
) -> Table:
    """Create a performance metrics table."""
    
    table = Table(
        title="Performance Metrics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold green",
        title_style="bold magenta"
    )
    
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", justify="right")
    
    formatted_metrics = format_performance_metrics(backtest_result, decimal_places)
    
    # Define metric display order and labels
    metric_labels = {
        "total_return": "Total Return",
        "annual_return": "Annualized Return", 
        "sharpe_ratio": "Sharpe Ratio",
        "max_drawdown": "Maximum Drawdown",
        "volatility": "Volatility",
        "calmar_ratio": "Calmar Ratio",
        "win_rate": "Win Rate",
        "profit_factor": "Profit Factor",
        "final_value": "Final Value"
    }
    
    for metric_key, label in metric_labels.items():
        value = formatted_metrics[metric_key]
        
        if color_output and metric_key in ["total_return", "annual_return", "sharpe_ratio", "max_drawdown", "win_rate"]:
            # Get raw value for color determination
            raw_value = getattr(backtest_result, metric_key, 0)
            color = get_performance_color(metric_key, raw_value)
            value = f"[{color}]{value}[/{color}]"
        
        table.add_row(label, value)
    
    return table


def create_vibe_check_table(vibe_checks: VibeCheckResults, color_output: bool = True) -> Table:
    """Create a vibe check results table."""
    
    table = Table(
        title="Strategy Validation (Vibe Checks)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold yellow",
        title_style="bold magenta"
    )
    
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center", style="bold")
    table.add_column("Details", style="white")
    
    # Individual check results
    checks = [
        ("Minimum Trades", vibe_checks.minimum_trades_check),
        ("Signal Quality", vibe_checks.signal_quality_check),
        ("Data Coverage", vibe_checks.data_coverage_check),
    ]
    
    for check_name, passed in checks:
        if color_output:
            status = "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]"
        else:
            status = "✅ PASS" if passed else "❌ FAIL"
        
        # Find relevant message
        relevant_messages = [msg for msg in vibe_checks.check_messages if check_name.lower() in msg.lower()]
        details = relevant_messages[0] if relevant_messages else "No details available"
        
        table.add_row(check_name, status, details)
    
    # Overall status
    table.add_row("", "", "")  # Separator
    if color_output:
        overall_status = "[green]✅ OVERALL PASS[/green]" if vibe_checks.overall_pass else "[red]❌ OVERALL FAIL[/red]"
    else:
        overall_status = "✅ OVERALL PASS" if vibe_checks.overall_pass else "❌ OVERALL FAIL"
    
    table.add_row("OVERALL", overall_status, "All validation checks combined")
    
    return table


def create_robustness_table(robustness_checks: RobustnessResults, color_output: bool = True) -> Table:
    """Create a robustness analysis table."""
    
    table = Table(
        title="Robustness Analysis",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold red",
        title_style="bold magenta"
    )
    
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_column("Assessment", style="white")
    
    # Robustness metrics
    table.add_row(
        "Baseline Sharpe Ratio",
        format_number(robustness_checks.baseline_sharpe, 2),
        "Normal trading conditions"
    )
    
    table.add_row(
        "High Fees Sharpe Ratio",
        format_number(robustness_checks.high_fees_sharpe, 2),
        "With elevated transaction costs"
    )
    
    degradation_color = "red" if robustness_checks.sharpe_degradation > 50 else "yellow" if robustness_checks.sharpe_degradation > 25 else "green"
    degradation_text = format_percentage(robustness_checks.sharpe_degradation, 1)
    if color_output:
        degradation_text = f"[{degradation_color}]{degradation_text}[/{degradation_color}]"
    
    table.add_row(
        "Sharpe Degradation",
        degradation_text,
        "Impact of higher fees"
    )
    
    turnover_color = "red" if robustness_checks.turnover_rate > 50 else "yellow" if robustness_checks.turnover_rate > 20 else "green"
    turnover_text = format_percentage(robustness_checks.turnover_rate, 1)
    if color_output:
        turnover_text = f"[{turnover_color}]{turnover_text}[/{turnover_color}]"
    
    table.add_row(
        "Turnover Rate",
        turnover_text,
        "Portfolio turnover frequency"
    )
    
    return table


def create_recommendations_panel(recommendations: List[str], color_output: bool = True) -> Panel:
    """Create a panel with strategy recommendations."""
    
    if not recommendations:
        recommendations = ["No specific recommendations at this time."]
    
    recommendation_text = "\n".join([f"• {rec}" for rec in recommendations])
    
    return Panel(
        recommendation_text,
        title="Recommendations",
        title_align="left",
        border_style="blue",
        padding=(1, 2)
    )


def generate_executive_verdict(
    analysis_result: BacktestAnalysisResult,
    report_config: ReportConfig = None
) -> None:
    """Generate and display the executive verdict in the terminal."""
    
    if report_config is None:
        report_config = ReportConfig()
    
    console = Console(force_terminal=report_config.color_output)
    
    # Extract components
    backtest_result = analysis_result.primary_result
    vibe_checks = analysis_result.vibe_checks
    robustness_checks = analysis_result.robustness_checks
    strategy_config = StrategyConfig(**analysis_result.strategy_config)
    
    # Determine overall verdict
    overall_verdict, recommendations = determine_overall_verdict(
        vibe_checks, robustness_checks, backtest_result
    )
    
    # Display header
    console.print()
    console.print(Panel(
        f"[bold]MEQSAP Strategy Analysis Report[/bold]\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        title="📊 Market Equity Quantitative Strategy Analysis Platform",
        title_align="center",
        border_style="magenta",
        padding=(1, 2)
    ))
    
    # Create and display tables
    console.print()
    console.print(create_strategy_summary_table(strategy_config, backtest_result, report_config.color_output))
    
    console.print()
    console.print(create_performance_table(backtest_result, report_config.decimal_places, report_config.color_output))
    
    console.print()
    console.print(create_vibe_check_table(vibe_checks, report_config.color_output))
    
    console.print()
    console.print(create_robustness_table(robustness_checks, report_config.color_output))
    
    console.print()
    console.print(create_recommendations_panel(recommendations, report_config.color_output))
    
    # Overall verdict
    console.print()
    verdict_color = {
        "PASS": "green",
        "WARNING": "yellow", 
        "FAIL": "red"
    }.get(overall_verdict, "white")
    
    if report_config.color_output:
        verdict_text = f"[bold {verdict_color}]{overall_verdict}[/bold {verdict_color}]"
    else:
        verdict_text = f"**{overall_verdict}**"
    
    console.print(Panel(
        f"Overall Strategy Verdict: {verdict_text}",
        title="🎯 Final Assessment",
        title_align="center",
        border_style=verdict_color,
        padding=(1, 2)
    ))
    console.print()


def prepare_returns_for_pyfolio(backtest_result: BacktestResult) -> pd.Series:
    """Convert backtest results to pyfolio-compatible returns series."""
    
    if not backtest_result.portfolio_value_series:
        raise ReportingError("No portfolio value series available for pyfolio conversion")
    
    # Convert portfolio values to returns
    portfolio_values = pd.Series(backtest_result.portfolio_value_series)
    portfolio_values.index = pd.to_datetime(portfolio_values.index)
    
    # Calculate daily returns
    returns = portfolio_values.pct_change().dropna()
    
    if returns.empty:
        raise ReportingError("Unable to calculate returns from portfolio values")
    
    # Check for degenerate cases where returns are meaningless for analysis
    if (returns.abs() < 1e-10).all():
        raise ReportingError("Unable to calculate returns: portfolio values are constant (zero returns)")
    
    return returns


def generate_pdf_report(
    analysis_result: BacktestAnalysisResult,
    output_path: Optional[str] = None,
    report_config: ReportConfig = None
) -> str:
    """Generate a comprehensive PDF report using pyfolio."""
    
    if not PYFOLIO_AVAILABLE:
        raise ReportingError(
            "PDF report generation requires pyfolio. Install with: pip install pyfolio"
        )
    
    if report_config is None:
        report_config = ReportConfig(include_pdf=True)
    
    # Prepare output path
    if output_path is None:
        os.makedirs(report_config.output_directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_config = StrategyConfig(**analysis_result.strategy_config)
        filename = f"{report_config.filename_prefix}_{strategy_config.ticker}_{timestamp}.pdf"
        output_path = os.path.join(report_config.output_directory, filename)
    else:
        # Ensure parent directory exists for explicit output_path
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Prepare data for pyfolio
        returns = prepare_returns_for_pyfolio(analysis_result.primary_result)
        
        # Suppress warnings during PDF generation
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Create the tear sheet
            with plt.style.context('seaborn-v0_8'):
                fig = pf.create_full_tear_sheet(
                    returns,
                    live_start_date=None,
                    return_fig=True
                )
                
                # Save to PDF
                fig.savefig(output_path, format='pdf', bbox_inches='tight', dpi=300)
                plt.close(fig)
        
        return output_path
        
    except Exception as e:
        raise ReportingError(f"PDF report generation failed: {str(e)}") from e


def generate_complete_report(
    analysis_result: BacktestAnalysisResult,
    include_pdf: bool = False,
    output_directory: str = "./reports",
    no_color: bool = False,
    quiet: bool = False
) -> Optional[str]:
    """Generate complete report output with optional PDF."""
    
    report_config = ReportConfig(
        include_pdf=include_pdf,
        output_directory=output_directory,
        color_output=not no_color
    )
    
    pdf_path = None
    
    try:
        # Generate terminal output unless quiet mode
        if not quiet:
            generate_executive_verdict(analysis_result, report_config)
        
        # Generate PDF if requested
        if include_pdf:
            if not quiet:
                console = Console()
                with console.status("[bold blue]Generating PDF report...[/bold blue]"):
                    pdf_path = generate_pdf_report(analysis_result, report_config=report_config)
                console.print(f"[green]✓[/green] PDF report generated: [bold]{pdf_path}[/bold]")
            else:
                pdf_path = generate_pdf_report(analysis_result, report_config=report_config)
        
        return pdf_path
        
    except ReportingError as e:
        console = Console()
        console.print(f"[bold red]Report Generation Error:[/bold red] {str(e)}")
        return None
    except Exception as e:
        console = Console()
        console.print(f"[bold red]Unexpected Error in Report Generation:[/bold red] {str(e)}")
        return None
