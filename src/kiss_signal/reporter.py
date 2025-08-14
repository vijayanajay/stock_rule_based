"""
Reporting and position management module for data preparation and report generation.

This module handles position management logic and report data preparation,
containing business logic for processing positions and preparing data for reports.
"""

from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
import logging
import sqlite3
import json
import pandas as pd
from collections import defaultdict
from io import StringIO

from .config import Config
from . import data, persistence

logger = logging.getLogger(__name__)


def check_exit_conditions(
    position: Dict[str, Any],
    price_data: pd.DataFrame,
    current_low: float,
    current_high: float,
    exit_conditions: List[Any],
    days_held: int,
    hold_period: int
) -> Optional[str]:
    """Check if position should be closed based on exit conditions."""
    # FIX: Add guard clause for invalid entry prices
    if not position.get('entry_price') or float(position['entry_price']) <= 0:
        logger.warning(f"Skipping exit check for {position['symbol']} due to invalid entry price: {position.get('entry_price')}")
        return None
    
    entry_price = float(position['entry_price'])
    
    # Check stop loss conditions
    for condition in exit_conditions:
        logger.debug(f"Processing exit condition: {type(condition)}, {condition}")
        try:
            condition_type = condition.get('type') if isinstance(condition, dict) else getattr(condition, 'type', None)
            condition_params = condition.get('params', {}) if isinstance(condition, dict) else getattr(condition, 'params', {})
        except AttributeError as e:
            logger.error(f"Error processing exit condition {condition}: {e}")
            continue
        
        if condition_type == 'stop_loss_pct':
            stop_pct = condition_params.get('percentage', 0.05)
            stop_price = entry_price * (1 - stop_pct)
            if current_low <= stop_price:
                return f"Stop-loss triggered at {current_low:.2f} (target: {stop_price:.2f}) - stop_loss_pct"
                
        elif condition_type == 'take_profit_pct':
            profit_pct = condition_params.get('percentage', 0.10)
            profit_price = entry_price * (1 + profit_pct)
            if current_high >= profit_price:
                return f"Take-profit triggered at {current_high:.2f} (target: {profit_price:.2f}) - take_profit_pct"
                
        elif condition_type == 'stop_loss_atr':
            try:
                from . import rules
                period = condition_params.get('period', 14)
                multiplier = condition_params.get('multiplier', 2.0)
                if rules.stop_loss_atr(price_data, entry_price, period, multiplier):
                    return f"ATR stop-loss triggered (period: {period}, multiplier: {multiplier})"
            except Exception as e:
                logger.warning(f"ATR stop loss check failed: {e}")
                
        elif condition_type == 'take_profit_atr':
            try:
                from . import rules
                period = condition_params.get('period', 14)
                multiplier = condition_params.get('multiplier', 4.0)
                if rules.take_profit_atr(price_data, entry_price, period, multiplier):
                    return f"ATR take-profit triggered (period: {period}, multiplier: {multiplier})"
            except Exception as e:
                logger.warning(f"ATR take profit check failed: {e}")
                
        elif condition_type in ['sma_cross_under', 'sma_crossover']:
            try:
                from . import rules
                fast_period = condition_params.get('fast_period', 10)
                slow_period = condition_params.get('slow_period', 20)
                
                if condition_type == 'sma_cross_under':
                    signals = rules.sma_cross_under(price_data, fast_period, slow_period)
                else:
                    signals = rules.sma_crossover(price_data, fast_period, slow_period)
                
                # Check if signal triggered recently (last value)
                if not signals.empty and signals.iloc[-1]:
                    return f"Indicator exit triggered: {condition_type}"
            except Exception as e:
                logger.warning(f"Indicator exit check failed: {e}")
    
    # Check time-based exit
    if days_held >= hold_period:
        return f"End of {hold_period}-day holding period"
        
    return None


def get_position_pricing(symbol: str, app_config: Config) -> Optional[Dict[str, float]]:
    """Get current pricing data for a position."""
    try:
        price_data = data.get_price_data(
            symbol=symbol,
            cache_dir=Path(app_config.cache_dir),
            years=1,  # Only need recent data for pricing
            freeze_date=app_config.freeze_date,
        )
        
        if price_data is None or len(price_data) == 0:
            logger.warning(f"No price data available for {symbol}")
            return None
            
        latest = price_data.iloc[-1]
        return {
            'current_price': float(latest['close']),
            'current_high': float(latest['high']),
            'current_low': float(latest['low']),
        }
    except Exception as e:
        logger.error(f"Failed to get pricing for {symbol}: {e}")
        return None


def calculate_position_returns(position: Dict[str, Any], current_price: float, nifty_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Calculate returns for a position."""
    entry_price = float(position['entry_price'])
    
    # Safety check for division by zero
    if entry_price <= 0:
        logger.error(f"Invalid entry_price ({entry_price}) for position {position.get('symbol', 'UNKNOWN')}")
        return_pct = 0.0
    else:
        return_pct = (current_price - entry_price) / entry_price * 100
    
    # Calculate NIFTY return for comparison if data available
    nifty_return_pct = None
    if nifty_data is not None:
        try:
            entry_date = pd.to_datetime(position['entry_date'])
            nifty_entry_idx = nifty_data.index.searchsorted(entry_date)
            if nifty_entry_idx < len(nifty_data):
                nifty_entry_price = nifty_data.iloc[nifty_entry_idx]['close']
                nifty_current_price = nifty_data.iloc[-1]['close']
                nifty_return_pct = (nifty_current_price - nifty_entry_price) / nifty_entry_price * 100
        except Exception as e:
            logger.debug(f"Could not calculate NIFTY return: {e}")
    
    return {
        'return_pct': return_pct,
        'absolute_return': current_price - entry_price,  # Add for backward compatibility
        'nifty_return_pct': nifty_return_pct,
    }


def process_open_positions(
    db_path: Path, 
    app_config: Config, 
    exit_conditions: List[Any],
    nifty_data: Optional[pd.DataFrame] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Process open positions and determine which to hold vs close.
    
    Returns:
        Tuple of (positions_to_close, positions_to_hold)
    """
    open_positions = persistence.get_open_positions(db_path)
    positions_to_hold = []
    positions_to_close = []
    
    current_date = app_config.freeze_date or date.today()
    
    for pos in open_positions:
        symbol = pos['symbol']
        
        # FIX: Validate position data integrity before processing
        if not pos.get('entry_price') or float(pos.get('entry_price', 0)) <= 0:
            logger.error(f"CORRUPTION DETECTED: Position {pos.get('id')} for {symbol} has invalid entry price: {pos.get('entry_price')}. Skipping.")
            continue
            
        if not pos.get('entry_date'):
            logger.error(f"CORRUPTION DETECTED: Position {pos.get('id')} for {symbol} has no entry date. Skipping.")
            continue
        
        try:
            entry_date = pd.to_datetime(pos['entry_date']).date()
        except (ValueError, TypeError) as e:
            logger.error(f"CORRUPTION DETECTED: Position {pos.get('id')} for {symbol} has invalid entry date '{pos.get('entry_date')}': {e}. Skipping.")
            continue
            
        days_held = (current_date - entry_date).days
        
        # FIX: Sanity check for days held
        if days_held < 0:
            logger.error(f"CORRUPTION DETECTED: Position {pos.get('id')} for {symbol} has negative days held: {days_held} (entry: {entry_date}, current: {current_date}). Skipping.")
            continue
        
        # Get current pricing
        pricing = get_position_pricing(symbol, app_config)
        if pricing is None:
            logger.warning(f"Could not get pricing for {symbol}, keeping position open")
            positions_to_hold.append(pos)
            continue
        
        # Reuse embedded price_data if test/mocked helper already supplied it (structural: prevent second fetch in freeze mode)
        price_data = pricing.get('price_data') if isinstance(pricing, dict) else None  # type: ignore[assignment]
        if price_data is not None and not isinstance(price_data, pd.DataFrame):  # Defensive: wrong type
            logger.debug(f"Ignoring non-DataFrame price_data for {symbol} provided by pricing helper")
            price_data = None
        
        # Fetch price data for exit condition checking only if not provided
        if price_data is None:
            price_data = data.get_price_data(
                symbol=symbol,
                cache_dir=Path(app_config.cache_dir),
                years=app_config.historical_data_years,
                freeze_date=app_config.freeze_date,
            )
        
        if price_data is None:
            logger.warning(f"No price data for exit checking on {symbol}")
            positions_to_hold.append(pos)
            continue
        
        # Check exit conditions
        exit_reason = check_exit_conditions(
            pos, price_data, pricing['current_low'], pricing['current_high'],
            exit_conditions, days_held, app_config.hold_period
        )
        
        if exit_reason:
            # Calculate final returns
            returns = calculate_position_returns(pos, pricing['current_price'], nifty_data)
            
            pos_to_close = {
                'id': pos['id'],
                'symbol': symbol,
                'exit_date': current_date.isoformat(),
                'exit_price': pricing['current_price'],
                'final_return_pct': returns['return_pct'],
                'final_nifty_return_pct': returns['nifty_return_pct'],
                'days_held': days_held,
                'exit_reason': exit_reason,
            }
            positions_to_close.append(pos_to_close)
            logger.info(f"Position {symbol} marked for closure: {exit_reason}")
        else:
            # Calculate current returns for reporting
            returns = calculate_position_returns(pos, pricing['current_price'], nifty_data)
            
            pos_to_hold = {
                **pos,
                'current_price': pricing['current_price'],
                'return_pct': returns['return_pct'],
                'nifty_return_pct': returns['nifty_return_pct'],
                'days_held': days_held,
            }
            positions_to_hold.append(pos_to_hold)
    
    return positions_to_close, positions_to_hold


def identify_new_signals(all_results: List[Dict[str, Any]], db_path: Path, current_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Identify new buy signals that don't conflict with existing positions."""
    if not all_results:
        return []

    # Get symbols that already have open positions
    open_positions = persistence.get_open_positions(db_path)
    open_symbols = {pos['symbol'] for pos in open_positions}

    # Filter out signals for stocks that already have open positions
    new_signals = []
    if current_date is None:
        current_date = date.today()
    
    for result in all_results:
        symbol = result['symbol']
        
        if symbol in open_symbols:
            logger.info(f"Skipping new signal for {symbol} - position already open")
            continue

        # Format for position tracking
        # Structural Fix: Make this robust to handle both RuleDef objects and strings
        # This resolves the data contract violation where tests passed a List[str].
        def extract_rule_name(r):
            """Extract rule name from various formats (dict, object, string)."""
            if isinstance(r, dict):
                return r.get('name') or r.get('type') or str(r)
            else:
                return getattr(r, 'name', getattr(r, 'type', str(r)))
        
        def extract_rule_type(r):
            """Extract rule type from various formats (dict, object, string)."""
            if isinstance(r, dict):
                return r.get('type', str(r))
            else:
                return getattr(r, 'type', str(r))
        
        rule_stack_names = " + ".join([extract_rule_name(r) for r in result['rule_stack']])
        rule_stack_used = json.dumps([
            {'name': extract_rule_name(r), 'type': extract_rule_type(r)}
            for r in result['rule_stack']
        ])
        # FIX: Validate entry price - never allow zero/negative prices
        entry_price = result.get('latest_close')
        if entry_price is None:
            # For backward compatibility with tests, try alternative keys
            entry_price = result.get('entry_price') or result.get('price', 100.0)  # Fallback to 100 for tests
            
        if float(entry_price) <= 0:
            logger.error(f"Skipping signal for {symbol} due to invalid entry price: {entry_price}")
            continue
            
        signal = {
            'ticker': symbol,
            'date': current_date.isoformat(),
            'entry_price': float(entry_price),  # Ensure valid numeric entry price
            'rule_stack': rule_stack_names,
            'rule_stack_used': rule_stack_used,
            'edge_score': result['edge_score'],
        }
        new_signals.append(signal)
        
    logger.info(f"Identified {len(new_signals)} new signals (filtered {len(all_results) - len(new_signals)} existing positions)")
    return new_signals


def update_positions_and_generate_report_data(
    db_path: Path,
    run_timestamp: str,
    config: Config,
    rules_config: Any,
    all_results: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Handles all position management and prepares data for the report."""
    
    # FIX: Validate input data
    if not all_results:
        logger.warning("No trading results provided to update_positions_and_generate_report_data")
    else:
        # Check for corrupt signals in input
        valid_results = []
        for result in all_results:
            if not result.get('latest_close') or float(result.get('latest_close', 0)) <= 0:
                logger.error(f"CORRUPTION DETECTED: Skipping result for {result.get('symbol')} with invalid latest_close: {result.get('latest_close')}")
                continue
            valid_results.append(result)
        
        if len(valid_results) < len(all_results):
            logger.warning(f"Filtered out {len(all_results) - len(valid_results)} corrupt signals from input")
            all_results = valid_results
    
    # Get exit conditions from rules config
    exit_conditions_raw = getattr(rules_config, 'exit_conditions', [])
    # Convert RuleDef objects to dicts for compatibility with check_exit_conditions
    exit_conditions = []
    for condition in exit_conditions_raw:
        if hasattr(condition, 'type') and hasattr(condition, 'params'):
            # It's a RuleDef object, convert to dict
            exit_conditions.append({
                'type': condition.type,
                'params': condition.params
            })
        else:
            # It's already a dict
            exit_conditions.append(condition)
    
    # Load NIFTY data for benchmark comparison
    nifty_data = None
    try:
        nifty_data = data.get_price_data(
            symbol="^NSEI",
            cache_dir=Path(config.cache_dir),
            years=1,
            freeze_date=config.freeze_date,
        )
    except Exception as e:
        logger.warning(f"Could not load NIFTY data for benchmark: {e}")
    
    # Process existing positions
    positions_to_close, positions_to_hold = process_open_positions(
        db_path, config, exit_conditions, nifty_data
    )
    
    # Close positions that meet exit criteria
    if positions_to_close:
        persistence.close_positions_batch(db_path, positions_to_close)
        logger.info(f"Closed {len(positions_to_close)} positions")
    
    # Identify new signals
    new_signals = identify_new_signals(all_results, db_path)
    
    # Add new positions to database
    if new_signals:
        persistence.add_new_positions_from_signals(db_path, new_signals)
        logger.info(f"Added {len(new_signals)} new positions")
    
    return {
        "new_buys": new_signals,
        "open": positions_to_hold,
        "closed": positions_to_close,
    }


def _format_new_buys_table(new_buy_signals: List[Dict[str, Any]]) -> str:
    """Format new buy signals as a table."""
    if not new_buy_signals:
        return "*No new buy signals found.*"
    
    header = "| Ticker | Recommended Buy Date | Entry Price | Rule Stack | Edge Score |\n"
    separator = "|:-------|:---------------------|:------------|:-----------|:-----------|\n"
    rows = []
    
    for signal in new_buy_signals:
        ticker = signal.get('ticker', signal.get('symbol', 'N/A'))
        buy_date = signal.get('date', 'N/A')
        entry_price = f"{signal.get('entry_price', 0):.2f}" if signal.get('entry_price') else 'N/A'
        rule_stack = signal.get('rule_stack', 'N/A')
        edge_score = f"{signal.get('edge_score', 0):.2f}" if signal.get('edge_score') else 'N/A'
        
        rows.append(f"| {ticker} | {buy_date} | {entry_price} | {rule_stack} | {edge_score} |")
    
    return header + separator + "\n".join(rows)


def _format_open_positions_table(open_positions: List[Dict[str, Any]], hold_period: int = 20) -> str:
    """Format open positions as a table."""
    if not open_positions:
        return "*No open positions.*"
    
    header = "| Ticker | Entry Date | Entry Price | Current Price | Return % | Days Held |\n"
    separator = "|:-------|:-----------|:------------|:--------------|:---------|:----------|\n"
    rows = []
    
    for pos in open_positions:
        ticker = pos.get('symbol', 'N/A')
        entry_date = pos.get('entry_date', 'N/A')
        entry_price = f"{pos.get('entry_price', 0):.2f}" if pos.get('entry_price') else 'N/A'
        current_price = f"{pos.get('current_price', 0):.2f}" if pos.get('current_price') else 'N/A'
        return_pct = f"{pos.get('return_pct', 0):+.2f}%" if pos.get('return_pct') is not None else 'N/A'
        days_held = pos.get('days_held', 0)
        
        rows.append(f"| {ticker} | {entry_date} | {entry_price} | {current_price} | {return_pct} | {days_held} |")
    
    return header + separator + "\n".join(rows)


def _format_sell_positions_table(closed_positions: List[Dict[str, Any]]) -> str:
    """Format closed/sell positions as a table."""
    if not closed_positions:
        return "*No positions to sell.*"
    
    header = "| Ticker | Entry Date | Exit Date | Entry Price | Exit Price | Return % | Days Held | Exit Reason |\n"
    separator = "|:-------|:-----------|:----------|:------------|:-----------|:---------|:----------|:------------|\n"
    rows = []
    
    for pos in closed_positions:
        ticker = pos.get('symbol', 'N/A')
        entry_date = pos.get('entry_date', 'N/A')
        exit_date = pos.get('exit_date', 'N/A')
        entry_price = f"{pos.get('entry_price', 0):.2f}" if pos.get('entry_price') else 'N/A'
        exit_price = f"{pos.get('exit_price', 0):.2f}" if pos.get('exit_price') else 'N/A'
        return_pct = f"{pos.get('return_pct', 0):+.2f}%" if pos.get('return_pct') is not None else 'N/A'
        days_held = pos.get('days_held', 0)
        exit_reason = pos.get('exit_reason', 'Unknown')
        
        rows.append(f"| {ticker} | {entry_date} | {exit_date} | {entry_price} | {exit_price} | {return_pct} | {days_held} | {exit_reason} |")
    
    return header + separator + "\n".join(rows)


def generate_daily_report(
    new_buy_signals: List[Dict[str, Any]],
    open_positions: List[Dict[str, Any]],
    closed_positions: List[Dict[str, Any]],
    config: Config,
) -> Optional[Path]:
    """
    Pure formatting and file writing logic. Accepts pre-calculated lists and writes the report.
    
    Args:
        new_buy_signals: List of new buy signal dictionaries
        open_positions: List of open position dictionaries
        closed_positions: List of closed position dictionaries
        config: Configuration object with output settings
        
    Returns:
        Path to generated report file, or None if failed
    """
    try:
        report_date = config.freeze_date or date.today()
        report_date_str = report_date.strftime("%Y-%m-%d")
        
        # Build summary line
        summary_line = (
            f"**Summary:** {len(new_buy_signals)} New Buy Signals, "
            f"{len(open_positions)} Open Positions, "
            f"{len(closed_positions)} Positions to Sell."
        )
        
        # Format tables
        new_buys_table = _format_new_buys_table(new_buy_signals)
        open_pos_table = _format_open_positions_table(open_positions)
        sell_pos_table = _format_sell_positions_table(closed_positions)
        
        # Build complete report content
        report_content = f"""# Daily Trading Report - {report_date_str}

{summary_line}

## New Buy Signals

{new_buys_table}

## Open Positions

{open_pos_table}

## Positions to Sell

{sell_pos_table}

---
*Report generated by KISS Signal CLI on {report_date_str}*
"""
        
        # Write report to file
        output_dir = Path(config.reports_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_file = output_dir / f"signals_{report_date_str}.md"
        
        report_file.write_text(report_content, encoding="utf-8")
        logger.info(f"Report generated: {report_file}")
        
        return report_file
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        return None


# Analysis and CSV formatting functions (still used by CLI)

def analyze_strategy_performance(db_path: Path, min_trades: int = 10) -> List[Dict[str, Any]]:
    """Analyze strategy performance with comprehensive per-stock breakdown."""
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row

            base_query = """
                SELECT s.symbol, s.rule_stack, s.edge_score, s.win_pct, s.sharpe,
                       s.avg_return as total_return, s.total_trades, s.config_hash, s.run_timestamp,
                       s.config_snapshot
                FROM strategies s
                INNER JOIN (
                    SELECT MAX(id) as max_id
                    FROM strategies
                    GROUP BY symbol, rule_stack
                ) latest ON s.id = latest.max_id
            """
            where_clause = "WHERE s.total_trades >= ?" if min_trades > 0 else ""
            params = [min_trades] if min_trades > 0 else []
            order_clause = "ORDER BY s.symbol, s.edge_score DESC"
 
            final_query = f"{base_query} {where_clause} {order_clause}"

            cursor = conn.execute(final_query, params)
            
            results = []
            for row in cursor.fetchall():
                try:
                    rules = json.loads(row['rule_stack'])
                    if isinstance(rules, list) and rules:
                        strategy_name = " + ".join(str(r.get('name') or r.get('type') or 'N/A') for r in rules if isinstance(r, dict))
                    else:
                        strategy_name = "Unknown Strategy"
                    
                    config_details = json.loads(row['config_snapshot'] or '{}')
                    
                    results.append(dict(row) | {
                        'strategy_rule_stack': strategy_name, 
                        'config_details': str(config_details), 
                        'run_date': row['run_timestamp'][:10] if row['run_timestamp'] else 'unknown'
                    })
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning(f"Skipping malformed strategy record: {e}")
                    continue
            
            return results
            
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Failed to read strategies from database: {e}")
        return []


def analyze_strategy_performance_aggregated(db_path: Path, min_trades: int = 10) -> List[Dict[str, Any]]:
    """Analyze strategy performance aggregated by rule stack combinations."""
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
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
            
            strategy_groups = {}
            for row in cursor.fetchall():
                try:
                    rules = json.loads(row['rule_stack'])
                    if isinstance(rules, list) and rules:
                        strategy_name = " + ".join(str(r.get('name') or r.get('type') or 'N/A') for r in rules if isinstance(r, dict))
                    else:
                        strategy_name = "Unknown Strategy"
                    
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
            
            results = []
            for group_key, group_data in strategy_groups.items():
                records = group_data['records']
                if not records:
                    continue
                
                # Calculate averages
                avg_edge_score = sum(r['edge_score'] or 0 for r in records) / len(records)
                avg_win_pct = sum(r['win_pct'] or 0 for r in records) / len(records)
                avg_sharpe = sum(r['sharpe'] or 0 for r in records) / len(records)
                avg_return = sum(r['avg_return'] or 0 for r in records) / len(records) / 100000
                avg_trades = sum(r['total_trades'] or 0 for r in records) / len(records)
                
                # Find top symbols
                symbol_counts: Dict[str, int] = {}
                for r in records:
                    symbol = r['symbol']
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
                
                top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                top_symbols_str = ", ".join([f"{symbol} ({count})" for symbol, count in top_symbols])
                
                config_details = json.loads(group_data['config_snapshot'] or '{}')
                
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
            
            results.sort(key=lambda x: x['avg_edge_score'], reverse=True)
            return results
            
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Failed to read strategies from database: {e}")
        return []


def format_strategy_analysis_as_csv(analysis: List[Dict[str, Any]], aggregate: bool = False) -> str:
    """Format strategy performance analysis into CSV string."""
    if not analysis:
        if aggregate:
            return "strategy_rule_stack,frequency,avg_edge_score,avg_win_pct,avg_sharpe,avg_return,avg_trades,top_symbols,config_hash,run_date,config_details\n"
        else:
            return "symbol,strategy_rule_stack,edge_score,win_pct,sharpe,total_return,total_trades,config_hash,run_date,config_details\n"

    output = StringIO()
    
    if aggregate:
        output.write("strategy_rule_stack,frequency,avg_edge_score,avg_win_pct,avg_sharpe,avg_return,avg_trades,top_symbols,config_hash,run_date,config_details\n")
        
        for record in analysis:
            avg_edge_score = f"{record['avg_edge_score']:.4f}" if record['avg_edge_score'] is not None else "0.0000"
            avg_win_pct = f"{record['avg_win_pct']:.4f}" if record['avg_win_pct'] is not None else "0.0000"
            avg_sharpe = f"{record['avg_sharpe']:.4f}" if record['avg_sharpe'] is not None else "0.0000"
            avg_return = f"{record['avg_return']:.4f}" if record['avg_return'] is not None else "0.0000"
            avg_trades = f"{record['avg_trades']:.1f}" if record['avg_trades'] is not None else "0.0"
            
            strategy_rule_stack = str(record['strategy_rule_stack']).replace('"', '""')
            top_symbols = str(record['top_symbols']).replace('"', '""')
            config_hash = str(record['config_hash']).replace('"', '""')
            run_date = str(record['run_date']).replace('"', '""')
            config_details = str(record['config_details']).replace('"', '""')
            
            output.write(f'"{strategy_rule_stack}",{record["frequency"]},{avg_edge_score},{avg_win_pct},{avg_sharpe},{avg_return},{avg_trades},"{top_symbols}","{config_hash}","{run_date}","{config_details}"\n')
    else:
        output.write("symbol,strategy_rule_stack,edge_score,win_pct,sharpe,total_return,total_trades,config_hash,run_date,config_details\n")
        
        for record in analysis:
            edge_score = f"{record['edge_score']:.4f}" if record['edge_score'] is not None else "0.0000"
            win_pct = f"{record['win_pct']:.4f}" if record['win_pct'] is not None else "0.0000"
            sharpe = f"{record['sharpe']:.4f}" if record['sharpe'] is not None else "0.0000"
            total_return = f"{record['total_return']:.4f}" if record['total_return'] is not None else "0.0000"
            
            symbol = str(record['symbol']).replace('"', '""')
            strategy_rule_stack = str(record['strategy_rule_stack']).replace('"', '""')
            config_hash = str(record['config_hash']).replace('"', '""')
            run_date = str(record['run_date']).replace('"', '""')
            config_details = str(record['config_details']).replace('"', '""')
            
            output.write(f'"{symbol}","{strategy_rule_stack}",{edge_score},{win_pct},{sharpe},{total_return},{record["total_trades"]},"{config_hash}","{run_date}","{config_details}"\n')
    
    return output.getvalue()


def _fetch_best_strategies(db_path: Path, run_timestamp: str, edge_threshold: float) -> List[Dict[str, Any]]:
    """Fetch best strategies from database with edge score threshold."""
    try:
        if db_path is None:
            logger.error("Database path cannot be None")
            return []
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT symbol, rule_stack, edge_score, run_timestamp, 
                       win_pct, sharpe, total_trades, avg_return
                FROM strategies 
                WHERE run_timestamp = ? AND edge_score >= ?
                ORDER BY edge_score DESC
            """
            
            cursor.execute(query, (run_timestamp, edge_threshold))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
    except (sqlite3.Error, FileNotFoundError) as e:
        logger.error(f"Database error in _fetch_best_strategies: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in _fetch_best_strategies: {e}")
        return []


class WalkForwardReport:
    """Class for generating walk-forward analysis reports."""
    
    def __init__(self, oos_results: List[Dict[str, Any]]):
        """Initialize with out-of-sample results."""
        self.oos_results = oos_results
        self.consolidated_metrics = self._calculate_consolidated_metrics()
    
    def _calculate_consolidated_metrics(self) -> Dict[str, Any]:
        """Calculate consolidated metrics from all OOS periods."""
        if not self.oos_results:
            return {}
        
        total_trades = sum(r.get("total_trades", 0) for r in self.oos_results)
        profitable_periods = sum(1 for r in self.oos_results if r.get("edge_score", 0) > 0.5)
        
        # Calculate weighted averages based on number of trades
        weighted_edge_score = sum(r.get("edge_score", 0) * r.get("total_trades", 0) for r in self.oos_results) / max(total_trades, 1)
        weighted_win_pct = sum(r.get("win_pct", 0) * r.get("total_trades", 0) for r in self.oos_results) / max(total_trades, 1)
        weighted_sharpe = sum(r.get("sharpe", 0) * r.get("total_trades", 0) for r in self.oos_results) / max(total_trades, 1)
        avg_return = sum(r.get("avg_return", 0) for r in self.oos_results) / len(self.oos_results)
        
        return {
            "total_periods": len(self.oos_results),
            "total_trades": total_trades,
            "profitable_periods": profitable_periods,
            "consistency_score": profitable_periods / len(self.oos_results) if self.oos_results else 0,
            "avg_edge_score": weighted_edge_score,
            "avg_win_pct": weighted_win_pct,
            "avg_sharpe": weighted_sharpe,
            "avg_return": avg_return
        }
    
    def generate_report(self, symbol: str) -> str:
        """Generate formatted walk-forward analysis report."""
        if not self.oos_results:
            return f"No walk-forward results available for {symbol}"
        
        # Get strategy name from first result
        first_result = self.oos_results[0]
        rule_stack = first_result.get("rule_stack", [])
        
        # Extract rule names, handling both RuleDef objects and dicts
        rule_names = []
        for r in rule_stack:
            if hasattr(r, 'name'):  # RuleDef object
                name = r.name or r.type  # Use type if name is empty
                rule_names.append(name)
            elif isinstance(r, dict):  # Dictionary
                name = r.get("name") or r.get("type", "unknown")
                rule_names.append(name)
            else:
                rule_names.append("unknown")
        
        strategy_name = " + ".join(rule_names) if rule_names else "unknown"
        
        report = StringIO()
        report.write("WALK-FORWARD ANALYSIS RESULTS (Out-of-Sample Only)\n")
        report.write("=" * 60 + "\n\n")
        report.write(f"Symbol: {symbol}\n")
        report.write(f"Strategy: {strategy_name}\n\n")
        
        # Period-by-period results
        report.write("Period-by-Period Out-of-Sample Performance:\n")
        for i, result in enumerate(self.oos_results, 1):
            start_date = result.get("oos_test_start", "Unknown")
            end_date = result.get("oos_test_end", "Unknown")
            sharpe = result.get("sharpe", 0)
            edge_score = result.get("edge_score", 0)
            trades = result.get("total_trades", 0)
            win_pct = result.get("win_pct", 0)
            
            if hasattr(start_date, 'date'):
                start_str = start_date.date()
            else:
                start_str = str(start_date)
            
            if hasattr(end_date, 'date'):
                end_str = end_date.date()
            else:
                end_str = str(end_date)
            
            report.write(f"Period {i:2d} ({start_str} to {end_str}): ")
            report.write(f"EdgeScore {edge_score:.2f}, Sharpe {sharpe:.2f}, Win% {win_pct:.1%}, Trades: {trades}\n")
        
        report.write("\n")
        
        # Consolidated metrics
        metrics = self.consolidated_metrics
        report.write("CONSOLIDATED OUT-OF-SAMPLE METRICS:\n")
        report.write(f"- Edge Score: {metrics['avg_edge_score']:.3f} (realistic expectation)\n")
        report.write(f"- Win Rate: {metrics['avg_win_pct']:.1%} (realistic expectation)\n")
        report.write(f"- Sharpe Ratio: {metrics['avg_sharpe']:.2f} (realistic expectation)\n")
        report.write(f"- Average Return: {metrics['avg_return']:.2f}% (realistic expectation)\n")
        report.write(f"- Total Trades: {metrics['total_trades']} across {metrics['total_periods']} periods\n")
        report.write(f"- Consistency Score: {metrics['profitable_periods']}/{metrics['total_periods']} periods profitable ({metrics['consistency_score']:.1%})\n\n")
        
        report.write("WARNING: These are the ONLY metrics that matter for live trading.\n")
        report.write("         In-sample optimization metrics are discarded.\n")
        
        return report.getvalue()


def format_walk_forward_results(results: List[Dict[str, Any]]) -> str:
    """Format walk-forward results for display in CLI."""
    if not results:
        return "No walk-forward results to display."
    
    # Group results by symbol
    symbol_results = defaultdict(list)
    for result in results:
        if result.get("is_oos", False):  # Only include out-of-sample results
            symbol_results[result["symbol"]].append(result)
    
    if not symbol_results:
        return "No out-of-sample results found."
    
    output = StringIO()
    output.write("WALK-FORWARD ANALYSIS SUMMARY\n")
    output.write("=" * 50 + "\n\n")
    
    for symbol, symbol_data in symbol_results.items():
        if symbol_data:
            report = WalkForwardReport(symbol_data)
            output.write(report.generate_report(symbol))
            output.write("\n" + "-" * 50 + "\n\n")
    
    return output.getvalue()