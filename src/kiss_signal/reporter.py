"""
Reporting module for generating daily markdown reports from backtesting results.

This module reads optimal strategies from the SQLite database and generates
actionable markdown reports showing new buy signals, open positions, and
positions to sell.
"""

from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional
import logging
import json
import sqlite3
import pandas as pd

from . import data, rules
from .config import Config

__all__ = ["generate_daily_report"]

logger = logging.getLogger(__name__)


def _fetch_best_strategies(db_path: Path, run_timestamp: str, threshold: float) -> List[Dict[str, Any]]:
    """
    Fetches the single best strategy for each symbol from a specific run,
    using a SQL window function for efficiency.
    
    Args:
        db_path: Path to SQLite database.
        run_timestamp: Timestamp of the backtesting run.
        threshold: Minimum edge score to consider.
        
    Returns:
        A list of strategy records, one for each symbol.
    """
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row  # To get dict-like rows
            query = """
            WITH ranked_strategies AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER(PARTITION BY symbol ORDER BY edge_score DESC) as rn
                FROM strategies
                WHERE run_timestamp = ? AND edge_score >= ?
            )
            SELECT symbol, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return
            FROM ranked_strategies
            WHERE rn = 1
            ORDER BY symbol;
            """
            cursor = conn.execute(query, (run_timestamp, threshold))
            strategies = [dict(row) for row in cursor.fetchall()]
            
            if not strategies:
                logger.warning(f"No strategies found for timestamp {run_timestamp} above threshold {threshold}")
            else:
                logger.info(f"Found {len(strategies)} optimal strategies above threshold {threshold}")
            return strategies
            
    except sqlite3.Error as e:
        logger.error(f"Database error fetching strategies: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching strategies: {e}")
        return []


def _check_for_signal(price_data: pd.DataFrame, rule_def: Dict[str, Any]) -> bool:
    """
    Private helper to check if a rule triggers BUY signal on the last trading day.
    
    Args:
        price_data: DataFrame with OHLCV data
        rule_def: Rule definition with type and parameters
        
    Returns:
        True if signal is active on last day, False otherwise
    """
    try:
        if len(price_data) == 0:
            return False
            
        rule_type = rule_def['type']
        rule_params = rule_def.get('params', {})
        
        # Get rule function from rules module
        if not hasattr(rules, rule_type):
            logger.error(f"Unknown rule type: {rule_type}")
            return False
            
        rule_func = getattr(rules, rule_type)
        
        # Apply rule to price data
        signals = rule_func(price_data, **rule_params)
        
        if len(signals) == 0:
            return False
            
        # Check if signal is active on the last day
        return bool(signals.iloc[-1]) if len(signals) > 0 else False
        
    except Exception as e:
        logger.error(f"Error checking signal for rule {rule_def.get('type', 'unknown')}: {e}")
        return False


def _identify_new_signals(
    db_path: Path,
    run_timestamp: str,
    config: Config,
) -> List[Dict[str, Any]]:
    """
    Identifies new buy signals by applying optimal strategies to latest data.
    
    Args:
        db_path: Path to SQLite database
        run_timestamp: Timestamp of the backtesting run
        config: Application configuration
        
    Returns:
        List of signal dictionaries ready for report generation
    """
    # 1. Fetch best strategies using _fetch_best_strategies
    strategies = _fetch_best_strategies(db_path, run_timestamp, config.edge_score_threshold)
    
    if not strategies:
        logger.info("No strategies found above threshold, no signals to generate")
        return []
        
    signals = []
    
    # 3. For each strategy, check for active signals
    for strategy in strategies:
        symbol = strategy['symbol']
        rule_stack_json = strategy['rule_stack']
        try:
            # Parse rule stack from JSON
            # It's a list of rule definition dictionaries.
            rule_stack_defs = json.loads(rule_stack_json)
            
            if not rule_stack_defs:
                continue
                
            # For now, handle single rule per strategy (as per current design)
            # The full rule definition is now self-contained in the persisted record.
            rule_def = rule_stack_defs[0]
            
            # Ensure rule_def is a dictionary
            if isinstance(rule_def, str):
                logger.warning(f"Expected rule definition dictionary but got string for {symbol}: {rule_def}")
                continue
                        
            # 5. Get latest price data
            try:
                price_data = data.get_price_data(
                    symbol=symbol,
                    cache_dir=Path(config.cache_dir),
                    refresh_days=config.cache_refresh_days,
                    years=config.historical_data_years,
                    freeze_date=config.freeze_date,
                )
            except Exception as e:
                logger.warning(f"Failed to load price data for {symbol}: {e}")
                continue
            # 6. Check for entry signal on latest date
            if price_data.empty:
                continue
            latest_date = price_data.index[-1]
            
            if _check_for_signal(price_data, rule_def):
                entry_price = price_data['close'].iloc[-1]
                signal_date = latest_date.strftime('%Y-%m-%d')
                signals.append({
                    'ticker': symbol,
                    'date': signal_date,
                    'entry_price': entry_price,
                    'rule_stack': rule_def.get('name', rule_def['type']),
                    'edge_score': strategy['edge_score']
                })
                
                logger.info(f"New signal: {symbol} at {entry_price} using {rule_def.get('name', rule_def['type'])}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse rule stack for {symbol}: {e}")
            continue
    return signals


def generate_daily_report(
    db_path: Path,
    run_timestamp: str,
    config: Config,
) -> Optional[Path]:
    """
    Generates the main daily markdown report.
    
    Args:
        db_path: Path to SQLite database
        run_timestamp: Timestamp of the backtesting run
        config: Application configuration
        
    Returns:
        Path to generated report file, or None on failure
    """
    try:
        # 1. Call _identify_new_signals to get new buy signals
        signals = _identify_new_signals(db_path, run_timestamp, config)
        
        # 2. Create markdown content using string formatting
        report_date = date.today().strftime('%Y-%m-%d')
        
        # Format NEW BUYS table
        if signals:
            new_buys_table = "| Ticker | Recommended Buy Date | Entry Price | Rule Stack | Edge Score |\n"
            new_buys_table += "|:-------|:---------------------|:------------|:-----------|:-----------|\n"
            
            for signal in signals:
                new_buys_table += f"| {signal['ticker']} | {signal['date']} | {signal['entry_price']:.2f} | {signal['rule_stack']} | {signal['edge_score']:.2f} |\n"
        else:
            new_buys_table = "*No new buy signals found.*"
        
        # Create full report content
        report_content = f"""# Signal Report: {report_date}

**Summary:** {len(signals)} New Buy Signals, 0 Open Positions, 0 Positions to Sell.

## NEW BUYS
{new_buys_table}

## OPEN POSITIONS
*Full position tracking will be implemented in a future story.*

## POSITIONS TO SELL
*Full position tracking will be implemented in a future story.*

---
*Report generated by KISS Signal CLI v1.4 on {report_date}*
"""
        
        # 3. Write the report to a file
        output_dir = Path(config.reports_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = output_dir / f"signals_{report_date}.md"
        report_file.write_text(report_content, encoding='utf-8')
        
        logger.info(f"Report generated: {report_file}")
        return report_file
        
    except OSError as e:
        logger.error(f"Failed to write report: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error generating report: {e}")
        return None
