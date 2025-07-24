"""
Reporting module for generating daily markdown reports from backtesting results.

This module reads optimal strategies from the SQLite database and generates
actionable markdown reports showing new buy signals, open positions, and
positions to sell.
"""

from pathlib import Path
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import logging
import json  # Standard library
import sqlite3
import pandas as pd
from collections import Counter, defaultdict
from io import StringIO

from . import data, rules, persistence
from .config import Config

# Import config functions from persistence for convenience
from .persistence import generate_config_hash, create_config_snapshot

__all__ = ["generate_daily_report", "_identify_new_signals", "analyze_strategy_performance", "analyze_strategy_performance_aggregated", "format_strategy_analysis_as_csv", "generate_config_hash", "create_config_snapshot"]

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


def _find_signals_in_window(price_data: pd.DataFrame, rule_stack_defs: List[Dict[str, Any]]) -> pd.Series:
    """
    Private helper to apply a full rule stack and find all signal triggers.
    
    Args:
        price_data: DataFrame with OHLCV data.
        rule_stack_defs: A list of rule definitions to apply.
        
    Returns:
        A boolean Series with True for any day a signal triggered.
    """
    try:
        if not rule_stack_defs or price_data.empty:
            return pd.Series(False, index=price_data.index)

        # Correctly initialize with the first rule's signals, then AND subsequent rules.
        # This fixes a critical bug where signals were being improperly combined.
        combined_signals: Optional[pd.Series] = None

        for rule_def in rule_stack_defs:
            rule_func = getattr(rules, rule_def['type'])
            
            # Convert string parameters to appropriate types (defensive programming)
            rule_params = rule_def.get('params', {})
            converted_rule_params = {}
            for key, value in rule_params.items():
                if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                    converted_rule_params[key] = float(value) if '.' in value else int(value)
                else:
                    converted_rule_params[key] = value
            
            rule_signals = rule_func(price_data, **converted_rule_params)

            if combined_signals is None:
                combined_signals = rule_signals.copy()
            else:
                combined_signals &= rule_signals

        return combined_signals.fillna(False)
    except Exception as e:
        logger.error(f"Error finding signals for rule stack: {e}")
        return pd.Series(False, index=price_data.index)


def _identify_new_signals(
    db_path: Path,
    run_timestamp: str,
    config: Config,
) -> List[Dict[str, Any]]:
    """
    Identifies buy signals from the last `hold_period` days.
    
    Args:
        db_path: Path to SQLite database.
        run_timestamp: Timestamp of the backtesting run.
        config: Config object
    Returns:
        List of dicts with new signal info
    """
    strategies = _fetch_best_strategies(db_path, run_timestamp, config.edge_score_threshold)
    if not strategies:
        logger.info("No strategies found above threshold, no signals to generate")
        return []

    signals = []
    for strategy in strategies:
        try:
            symbol = strategy['symbol']
            rule_stack_defs = json.loads(strategy['rule_stack'])
            price_data = data.get_price_data(
                symbol=symbol,
                cache_dir=Path(config.cache_dir),
                years=config.historical_data_years,
                freeze_date=config.freeze_date,
            )
            if not isinstance(rule_stack_defs, list):
                logger.warning(f"Rule stack for {symbol} is not a list, skipping.")
                continue
            if price_data.empty:
                continue

            # Find all signals for the given strategy
            all_signals = _find_signals_in_window(price_data, rule_stack_defs)
            
            # Determine the start date for recent signals
            run_date = config.freeze_date or date.today()
            start_date_filter = (run_date - timedelta(days=config.hold_period)) if hasattr(config, 'hold_period') and config.hold_period else run_date
            # Filter for signals within the last `hold_period` days
            recent_signals = all_signals[all_signals.index.date >= start_date_filter]

            for signal_date, is_signal_active in recent_signals.items():
                if not is_signal_active:
                    continue
                
                entry_price = price_data.loc[signal_date]['close']
                rule_stack_str = " + ".join([(r.get("name") or r.get("type") or "") for r in rule_stack_defs if isinstance(r, dict)])
                signals.append({
                    'ticker': symbol,
                    'date': signal_date.strftime('%Y-%m-%d'),
                    'entry_price': entry_price,
                    'rule_stack': rule_stack_str,
                    'edge_score': strategy['edge_score']
                })
                logger.info(f"Found recent signal for {symbol} on {signal_date.date()} at {entry_price:.2f}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse rule stack for {symbol}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing strategy for {symbol}: {e}")
            continue
    return signals


def _format_new_buys_table(new_signals: List[Dict[str, Any]]) -> str:
    """Formats the markdown table for new buy signals."""
    if not new_signals:
        return "*No new buy signals found.*"

    header = "| Ticker | Recommended Buy Date | Entry Price | Rule Stack | Edge Score |\n"
    separator = "|:-------|:---------------------|:------------|:-----------|:-----------|\n"
    rows = [
        f"| {s['ticker']} | {s['date']} | {s['entry_price']:.2f} | {s['rule_stack']} | {s['edge_score']:.2f} |"
        for s in new_signals
    ]
    return header + separator + "\n".join(rows)


def _format_open_positions_table(
    open_positions: List[Dict[str, Any]], hold_period: int
) -> str:
    """Formats the markdown table for open positions."""
    if not open_positions:
        return "*No open positions.*"

    header = "| Ticker | Entry Date | Entry Price | Current Price | Return % | NIFTY Period Return % | Day in Trade |\n"
    separator = "|:-------|:-----------|:------------|:--------------|:---------|:----------------------|:-------------|\n"
    rows = []
    for pos in open_positions:
        current_price_str = f"{pos['current_price']:.2f}" if pos.get('current_price') is not None else "N/A"
        return_pct_str = f"{pos['return_pct']:+.2f}%" if pos.get('return_pct') is not None else "N/A"
        nifty_return_pct_str = f"{pos['nifty_return_pct']:+.2f}%" if pos.get('nifty_return_pct') is not None else "N/A"
        rows.append(
            f"| {pos['symbol']} | {pos['entry_date']} | {pos['entry_price']:.2f} | "
            f"{current_price_str} | {return_pct_str} | "
            f"{nifty_return_pct_str} | {pos['days_held']} / {hold_period} |"
        )
    return header + separator + "\n".join(rows)


def _format_sell_positions_table(
    closed_positions: List[Dict[str, Any]]
) -> str:
    """Formats the markdown table for positions to sell."""
    if not closed_positions:
        return "*No positions to sell.*"

    header = "| Ticker | Status | Reason |\n"
    separator = "|:-------|:-------|:-------|\n"
    rows = [
        f"| {pos['symbol']} | SELL | {pos.get('exit_reason', 'Unknown')} |"
        for pos in closed_positions
    ]
    return header + separator + "\n".join(rows)


def _build_report_content(
    report_date_str: str,
    new_signals: List[Dict[str, Any]],
    open_positions: List[Dict[str, Any]],
    closed_positions: List[Dict[str, Any]],
    config: Config,
) -> str:
    """Builds the full markdown report content."""
    summary_line = (
        f"**Summary:** {len(new_signals)} New Buy Signals, "
        f"{len(open_positions)} Open Positions, "
        f"{len(closed_positions)} Positions to Sell."
    )
    new_buys_table = _format_new_buys_table(new_signals)
    open_pos_table = _format_open_positions_table(open_positions, config.hold_period)
    sell_pos_table = _format_sell_positions_table(closed_positions)

    return f"""# Signal Report: {report_date_str}

{summary_line}

## NEW BUYS
{new_buys_table}

## OPEN POSITIONS
{open_pos_table}

## POSITIONS TO SELL
{sell_pos_table}

---
*Report generated by KISS Signal CLI v1.4 on {report_date_str}*
"""

# impure
def generate_daily_report(
    db_path: Path,
    run_timestamp: str,
    config: Config,
    rules_config: Dict[str, Any],
) -> Optional[Path]:
    """
    Generates the main daily markdown report with consolidated position logic.
    
    Returns the path to the generated report file, or None if failed.
    """
    try:
        # 1. Fetch all existing open positions
        open_positions = persistence.get_open_positions(db_path)

        # 2. Process each open position with dynamic exit checking
        positions_to_hold, positions_to_close = _process_open_positions(open_positions, config, rules_config)

        # 3. Persist changes (close positions)
        if positions_to_close:
            persistence.close_positions_batch(db_path, positions_to_close)
        
        # 4. Identify and persist new signals
        new_signals = _identify_new_signals(db_path, run_timestamp, config)
        if new_signals:
            added_count = persistence.add_new_positions_from_signals(db_path, new_signals)
            logger.info(f"Added {added_count} new positions to the database.")

        # 5. Build and save the report
        report_date_str = (config.freeze_date or date.today()).strftime("%Y-%m-%d")
        report_content = _build_report_content(
            report_date_str, new_signals, positions_to_hold, positions_to_close, config
        )
        
        output_dir = Path(config.reports_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = output_dir / f"signals_{report_date_str}.md"
        report_file.write_text(report_content, encoding='utf-8')
        logger.info(f"Report generated: {report_file}")
        return report_file
    except (Exception, KeyError) as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        return None

def _process_open_positions(
    open_positions: List[Dict[str, Any]], 
    config: Config, 
    rules_config: Dict[str, Any]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Process open positions to determine which to hold and which to close.
    
    This function processes each open position to:
    1. Calculate current price and return percentage
    2. Calculate Nifty index return for the same period (for benchmark comparison)
    3. Check exit conditions to determine if positions should be closed
    
    The Nifty period return calculation ensures accurate comparison between stock
    and market performance by using the exact same date range for both calculations.
    
    Args:
        open_positions: List of open position records from database
        config: Application configuration
        rules_config: Rules configuration dictionary
        
    Returns:
        Tuple of (positions_to_hold, positions_to_close)
    """
    run_date = config.freeze_date or date.today()
    positions_to_hold: List[Dict[str, Any]] = []
    positions_to_close: List[Dict[str, Any]] = []

    for pos in open_positions:
        entry_date = date.fromisoformat(pos["entry_date"])
        days_held = (run_date - entry_date).days

        try:
            # Ignore freeze_date to get latest data for live position tracking
            price_data = data.get_price_data(
                symbol=pos["symbol"], 
                cache_dir=Path(config.cache_dir), 
                start_date=entry_date, 
                end_date=run_date, 
                freeze_date=None,
                years=config.historical_data_years
            )

            if price_data.empty:
                logger.warning(f"No price data available for {pos['symbol']} from {entry_date} to {run_date}")
                current_price = float(pos['entry_price'])
                current_low = current_high = current_price
                return_pct = 0.0
                nifty_return_pct = 0.0
            else:
                # Use the latest available price (which may be older than run_date)
                current_price = float(price_data['close'].iloc[-1])
                current_low = float(price_data['low'].iloc[-1])  
                current_high = float(price_data['high'].iloc[-1])
                return_pct = (current_price - pos['entry_price']) / pos['entry_price'] * 100 if pos['entry_price'] > 0 else 0.0
                
                # Log if data is stale (last date != run_date)
                last_data_date = price_data.index[-1].date()
                if last_data_date < run_date:
                    days_behind = (run_date - last_data_date).days
                    logger.info(f"Using stale data for {pos['symbol']}: last available {last_data_date}, current {run_date} ({days_behind} day{'s' if days_behind != 1 else ''} behind)")
                
                # Calculate NIFTY return for the same period as available stock data
                # This is important for comparing stock performance against the market benchmark
                actual_end_date = last_data_date if last_data_date < run_date else run_date
                try:
                    # Ignore freeze_date to get latest data for live position tracking
                    nifty_data = data.get_price_data(
                        symbol="^NSEI", 
                        cache_dir=Path(config.cache_dir), 
                        start_date=entry_date,  # Use the same entry date as the stock position
                        end_date=actual_end_date,  # Use the same end date as available for the stock
                        freeze_date=None,
                        years=config.historical_data_years
                    )
                    
                    # Log the retrieved Nifty data details for debugging and verification
                    if nifty_data is not None and not nifty_data.empty:
                        logger.info(f"NIFTY data retrieved: {len(nifty_data)} rows, date range: {nifty_data.index[0].date()} to {nifty_data.index[-1].date()}")
                        logger.debug(f"NIFTY first value: {nifty_data['close'].iloc[0]}, last value: {nifty_data['close'].iloc[-1]}")
                    
                    # Handle cases where Nifty data is missing or invalid
                    if nifty_data is None or nifty_data.empty or len(nifty_data) == 0:
                        logger.warning(f"No NIFTY data available for period {entry_date} to {actual_end_date}")
                        nifty_return_pct = 0.0
                    elif nifty_data['close'].iloc[0] <= 0:
                        logger.warning(f"Invalid NIFTY entry price for period {entry_date} to {actual_end_date}: {nifty_data['close'].iloc[0]}")
                        nifty_return_pct = 0.0
                    else:
                        # Calculate Nifty return with proper start and end values
                        # This calculation mirrors how stock returns are calculated for consistency
                        try:
                            # Ensure we have data points to calculate with - need at least 2 points for a valid return calculation
                            # (one for the starting value and one for the ending value)
                            if len(nifty_data) >= 2:
                                nifty_start = nifty_data['close'].iloc[0]  # First day's closing price (position entry date)
                                nifty_end = nifty_data['close'].iloc[-1]   # Last day's closing price (current date)
                                
                                # Validate the values to prevent calculation errors
                                # Both start and end values must be positive for a valid percentage calculation
                                if nifty_start > 0 and nifty_end > 0:
                                    # Calculate percentage return using the standard formula:
                                    # ((end_price - start_price) / start_price) * 100
                                    # This gives us the percentage change in the Nifty index over the same period
                                    # that the position has been held, allowing for direct comparison
                                    nifty_return_pct = (nifty_end - nifty_start) / nifty_start * 100
                                    logger.info(f"NIFTY return calculation for {pos['symbol']}: {nifty_start:.2f} to {nifty_end:.2f} = {nifty_return_pct:.2f}%")
                                else:
                                    logger.warning(f"Invalid NIFTY values for {pos['symbol']}: start={nifty_start}, end={nifty_end}")
                                    nifty_return_pct = 0.0
                            else:
                                # For very new positions (e.g., entered today), we might only have one data point
                                # In this case, we can't calculate a return, so we default to 0.0%
                                logger.warning(f"Insufficient NIFTY data points for {pos['symbol']}: {len(nifty_data)} rows")
                                nifty_return_pct = 0.0
                        except (IndexError, ZeroDivisionError) as e:
                            # Handle specific calculation errors gracefully
                            logger.warning(f"Error calculating NIFTY return for {pos['symbol']}: {e}")
                            nifty_return_pct = 0.0
                except ValueError as e:
                    # Handle specific data retrieval errors
                    logger.warning(f"Failed to get NIFTY data for {pos['symbol']} comparison: {e}")
                    nifty_return_pct = 0.0
                except Exception as e:
                    # Catch-all for unexpected errors
                    logger.error(f"Unexpected error calculating NIFTY return for {pos['symbol']}: {e}", exc_info=True)
                    nifty_return_pct = 0.0

            pos.update({
                'current_price': current_price, 
                'return_pct': return_pct, 
                'nifty_return_pct': nifty_return_pct, 
                'days_held': days_held
            })

            # Check for dynamic exit conditions
            sell_conditions = getattr(rules_config, 'sell_conditions', None) if hasattr(rules_config, 'sell_conditions') else rules_config.get('sell_conditions', [])
            # Ensure sell_conditions is a list
            if sell_conditions is None:
                sell_conditions = []
            exit_reason = _check_exit_conditions(pos, price_data, current_low, current_high, sell_conditions, days_held, config.hold_period)
            if exit_reason:
                pos.update({
                    'exit_date': run_date.isoformat(), 
                    'exit_price': current_price, 
                    'final_return_pct': return_pct, 
                    'final_nifty_return_pct': nifty_return_pct, 
                    'exit_reason': exit_reason
                })
                positions_to_close.append(pos)
            else:
                positions_to_hold.append(pos)
        except Exception as e:
            logger.error(f"Failed to process position for {pos['symbol']}: {e}")
            # Fall back to N/A values when everything fails
            pos.update({
                'current_price': None, 
                'return_pct': None, 
                'nifty_return_pct': None, 
                'days_held': days_held
            })
            positions_to_hold.append(pos)

    return positions_to_hold, positions_to_close


def format_strategy_analysis_as_csv(analysis: List[Dict[str, Any]], aggregate: bool = False) -> str:
    """Formats the strategy performance analysis into a CSV string.
    
    Args:
        analysis: List of strategy performance records (per-stock or aggregated)
        aggregate: If True, formats aggregated data; if False, formats per-stock data
        
    Returns:
        CSV string with proper formatting
    """
    if not analysis:
        if aggregate:
            return "strategy_rule_stack,frequency,avg_edge_score,avg_win_pct,avg_sharpe,avg_return,avg_trades,top_symbols,config_hash,run_date,config_details\n"
        else:
            return "symbol,strategy_rule_stack,edge_score,win_pct,sharpe,total_return,total_trades,config_hash,run_date,config_details\n"

    output = StringIO()
    
    if aggregate:
        # Write header for aggregated format (Story 16 + config tracking)
        output.write("strategy_rule_stack,frequency,avg_edge_score,avg_win_pct,avg_sharpe,avg_return,avg_trades,top_symbols,config_hash,run_date,config_details\n")
        
        # Write data rows with proper CSV escaping
        for record in analysis:
            # Format numeric values to 4 decimal places
            avg_edge_score = f"{record['avg_edge_score']:.4f}" if record['avg_edge_score'] is not None else "0.0000"
            avg_win_pct = f"{record['avg_win_pct']:.4f}" if record['avg_win_pct'] is not None else "0.0000"
            avg_sharpe = f"{record['avg_sharpe']:.4f}" if record['avg_sharpe'] is not None else "0.0000"
            avg_return = f"{record['avg_return']:.4f}" if record['avg_return'] is not None else "0.0000"
            avg_trades = f"{record['avg_trades']:.1f}" if record['avg_trades'] is not None else "0.0"
            
            # Escape CSV values
            strategy_rule_stack = str(record['strategy_rule_stack']).replace('"', '""')
            top_symbols = str(record['top_symbols']).replace('"', '""')
            config_hash = str(record['config_hash']).replace('"', '""')
            run_date = str(record['run_date']).replace('"', '""')
            config_details = str(record['config_details']).replace('"', '""')
            
            output.write(f'"{strategy_rule_stack}",{record["frequency"]},{avg_edge_score},{avg_win_pct},{avg_sharpe},{avg_return},{avg_trades},"{top_symbols}","{config_hash}","{run_date}","{config_details}"\n')
    else:
        # Write header for per-stock format (Story 17)
        output.write("symbol,strategy_rule_stack,edge_score,win_pct,sharpe,total_return,total_trades,config_hash,run_date,config_details\n")
        
        # Write data rows with proper CSV escaping
        for record in analysis:
            # Format numeric values to 4 decimal places
            edge_score = f"{record['edge_score']:.4f}" if record['edge_score'] is not None else "0.0000"
            win_pct = f"{record['win_pct']:.4f}" if record['win_pct'] is not None else "0.0000"
            sharpe = f"{record['sharpe']:.4f}" if record['sharpe'] is not None else "0.0000"
            total_return = f"{record['total_return']:.4f}" if record['total_return'] is not None else "0.0000"
            
            # Escape CSV values
            symbol = str(record['symbol']).replace('"', '""')
            strategy_rule_stack = str(record['strategy_rule_stack']).replace('"', '""')
            config_hash = str(record['config_hash']).replace('"', '""')
            run_date = str(record['run_date']).replace('"', '""')
            config_details = str(record['config_details']).replace('"', '""')
            
            output.write(f'"{symbol}","{strategy_rule_stack}",{edge_score},{win_pct},{sharpe},{total_return},{record["total_trades"]},"{config_hash}","{run_date}","{config_details}"\n')
    
    return output.getvalue()

def _check_exit_conditions(
    position: Dict[str, Any],
    price_data: pd.DataFrame,
    current_low: float,
    current_high: float,
    sell_conditions: List[Any],  # Can be RuleDef objects or dicts
    days_held: int,
    hold_period: int
) -> Optional[str]:
    """Check exit conditions for an open position in priority order."""
    entry_price = position['entry_price']

    for condition in sell_conditions:
        # Handle both RuleDef objects and dictionaries
        if hasattr(condition, 'type'):  # RuleDef object
            rule_type = condition.type
            params = condition.params if hasattr(condition, 'params') and condition.params else {}
            condition_name = getattr(condition, 'name', rule_type)
        else:  # Dictionary
            rule_type = condition.get('type')
            params = condition.get('params', {})
            condition_name = condition.get('name', rule_type)

        if rule_type == 'stop_loss_pct':
            percentage = params.get('percentage', 0) if isinstance(params, dict) else getattr(params, 'percentage', 0)
            if current_low <= entry_price * (1 - percentage):
                return f"Stop-loss at -{percentage:.1%}"
        elif rule_type == 'take_profit_pct':
            percentage = params.get('percentage', 0) if isinstance(params, dict) else getattr(params, 'percentage', 0)
            if current_high >= entry_price * (1 + percentage):
                return f"Take-profit at +{percentage:.1%}"
        else:
            try:
                rule_func = getattr(rules, rule_type, None)
                if rule_func:
                    # Convert string parameters to appropriate types (defensive programming)
                    converted_params = {}
                    for key, value in params.items():
                        if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                            converted_params[key] = float(value) if '.' in value else int(value)
                        else:
                            converted_params[key] = value
                    
                    # Special handling for ATR-based exit functions that require entry_price
                    if rule_type in ['stop_loss_atr', 'take_profit_atr']:
                        if rule_func(price_data, entry_price, **converted_params):
                            return f"Rule: {condition_name}"
                    else:
                        if rule_func(price_data, **converted_params).iloc[-1]:
                            return f"Rule: {condition_name}"
            except Exception as e:
                logger.warning(f"Error checking exit rule {rule_type}: {e}")

    if days_held >= hold_period:
        return f"Exit: End of {hold_period}-day holding period."
    return None

def analyze_strategy_performance(db_path: Path, min_trades: int = 10) -> List[Dict[str, Any]]:
    """Analyze strategy performance with comprehensive per-stock breakdown.
    
    Args:
        db_path: Path to SQLite database
        min_trades: Minimum trades required for analysis (0 = show all)
        
    Returns:
        List of individual strategy performance records (deduplicated)
    """
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build WHERE clause for min_trades filtering
            where_clause = "WHERE total_trades >= ?" if min_trades > 0 else ""
            params = [min_trades] if min_trades > 0 else []
            
            # Deduplication query: get latest strategy per symbol-rule_stack combination
            cursor = conn.execute(f"""
                SELECT s.symbol, s.rule_stack, s.edge_score, s.win_pct, s.sharpe,
                       s.avg_return as total_return, s.total_trades, s.config_hash, s.run_timestamp,
                       s.config_snapshot
                FROM strategies s
                INNER JOIN (
                    SELECT symbol, rule_stack, MAX(id) as max_id
                    FROM strategies 
                    {where_clause}
                    GROUP BY symbol, rule_stack
                ) latest ON s.id = latest.max_id
                ORDER BY s.symbol, s.edge_score DESC
            """, params)
            
            results = []
            for row in cursor.fetchall():
                try:
                    rules = json.loads(row['rule_stack'])
                    strategy_name = " + ".join(str(r.get('name') or r.get('type') or 'N/A') for r in rules if isinstance(r, dict)) if isinstance(rules, list) else "Unknown Strategy"
                    config_details = json.loads(row['config_snapshot'] or '{}')
                    results.append(dict(row) | {'strategy_rule_stack': strategy_name, 'config_details': str(config_details), 'run_date': row['run_timestamp'][:10] if row['run_timestamp'] else 'unknown'})
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning(f"Skipping malformed strategy record: {e}")
                    continue
            return results
            
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Failed to read strategies from database: {e}")
        return []


def analyze_strategy_performance_aggregated(db_path: Path, min_trades: int = 10) -> List[Dict[str, Any]]:
    """Analyze strategy performance aggregated by rule stack combinations (Story 16 format).
    
    Groups strategies by rule_stack and calculates aggregated metrics:
    frequency, average scores, and top performing symbols.
    
    Args:
        db_path: Path to SQLite database
        min_trades: Minimum trades required for analysis (0 = show all)
        
    Returns:
        List of aggregated strategy performance records with config tracking
    """
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build WHERE clause for min_trades filtering
            where_clause = "WHERE total_trades >= ?" if min_trades > 0 else ""
            params = [min_trades] if min_trades > 0 else []
            
            cursor = conn.execute(f"""
                SELECT symbol, rule_stack, edge_score, win_pct, sharpe,
                       avg_return, total_trades, config_hash, run_timestamp,
                       config_snapshot
                FROM strategies 
                {where_clause}
                ORDER BY symbol, edge_score DESC
            """, params)
            
            # Group by strategy (rule_stack) AND config_hash for tracking
            strategy_groups = {}
            for row in cursor.fetchall():
                try:
                    # Parse rule stack to create human-readable strategy name
                    rules = json.loads(row['rule_stack'])
                    if isinstance(rules, list) and rules:
                        strategy_name = " + ".join(str(r.get('name') or r.get('type') or 'N/A') for r in rules if isinstance(r, dict))
                    else:
                        strategy_name = "Unknown Strategy"
                    
                    # Group by strategy name + config hash to track different configurations
                    group_key = f"{strategy_name}|{row['config_hash'] or 'legacy'}"
                    
                    if group_key not in strategy_groups:
                        strategy_groups[group_key] = {
                            'strategy_name': strategy_name,
                            'config_hash': row['config_hash'] or 'legacy',
                            'run_date': row['run_timestamp'][:10] if row['run_timestamp'] else 'unknown',
                            'config_snapshot': row['config_snapshot'],
                            'records': []
                        }
                    
                    strategy_groups[group_key]['records'].append({
                        'symbol': row['symbol'],
                        'edge_score': row['edge_score'],
                        'win_pct': row['win_pct'],
                        'sharpe': row['sharpe'],
                        'avg_return': row['avg_return'],
                        'total_trades': row['total_trades']
                    })
                    
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning(f"Skipping malformed strategy record: {e}")
                    continue
            
            # Calculate aggregated metrics for each strategy+config combination
            results = []
            for group_key, group_data in strategy_groups.items():
                records = group_data['records']
                if not records:
                    continue
                
                # Calculate averages
                avg_edge_score = sum(r['edge_score'] or 0 for r in records) / len(records)
                avg_win_pct = sum(r['win_pct'] or 0 for r in records) / len(records)
                avg_sharpe = sum(r['sharpe'] or 0 for r in records) / len(records)
                avg_return = sum(r['avg_return'] or 0 for r in records) / len(records) / 100000  # Convert to percentage
                avg_trades = sum(r['total_trades'] or 0 for r in records) / len(records)
                
                # Find top symbols by frequency
                symbol_counts: Dict[str, int] = {}
                for r in records:
                    symbol = r['symbol']
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
                
                top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                top_symbols_str = ", ".join([f"{symbol} ({count})" for symbol, count in top_symbols])
                
                # Parse config details
                try:
                    config_details = json.loads(group_data['config_snapshot'] or '{}')
                except (json.JSONDecodeError, TypeError):
                    config_details = {}
                
                results.append({
                    'strategy_rule_stack': group_data['strategy_name'],
                    'frequency': len(records),
                    'avg_edge_score': avg_edge_score,
                    'avg_win_pct': avg_win_pct,
                    'avg_sharpe': avg_sharpe,
                    'avg_return': avg_return,
                    'avg_trades': avg_trades,
                    'top_symbols': top_symbols_str,
                    'config_hash': group_data['config_hash'],
                    'run_date': group_data['run_date'],
                    'config_details': str(config_details)
                })
            
            # Sort by average edge score descending
            results.sort(key=lambda x: x['avg_edge_score'], reverse=True)
            
            logger.info(f"Analyzed {len(results)} unique strategy+config combinations from {sum(len(group['records']) for group in strategy_groups.values())} individual records")
            return results
            
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Failed to read strategies from database: {e}")
        return []


def format_strategy_analysis_as_md(analysis: List[Dict[str, Any]]) -> str:
    """Formats the strategy performance analysis into a markdown table."""
    header = "| Strategy (Rule Stack) | Freq. | Avg Edge | Avg Win % | Avg Sharpe | Avg PnL/Trade | Avg Trades | Top Symbols |\n"
    separator = "|:---|---:|---:|---:|---:|---:|---:|:---|\n"
    
    rows = []
    for stats in analysis:
        row = (
            f"| `{stats['strategy_name']}` "
            f"| {stats['frequency']} "
            f"| {stats['avg_edge_score']:.2f} "
            f"| {stats['avg_win_pct']:.1%} "
            f"| {stats['avg_sharpe']:.2f} "
            f"| {stats['avg_return']:.2f} "  # PnL in currency units
            f"| {stats['avg_trades']:.1f} "
            f"| {stats['top_symbols']} |"
        )
        rows.append(row)
    
    return f"# Strategy Performance Report\n\n{header}{separator}" + "\n".join(rows)



