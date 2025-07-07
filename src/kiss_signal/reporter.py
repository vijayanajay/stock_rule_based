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

from . import data, rules, persistence
from .config import Config

__all__ = ["generate_daily_report", "analyze_rule_performance", "format_rule_analysis_as_md", "_identify_new_signals", "analyze_strategy_performance", "format_strategy_analysis_as_md"]

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

        # Start with the first rule's signals, then AND subsequent rules
        first_rule = rule_stack_defs[0]
        rule_func = getattr(rules, first_rule['type'])
        combined_signals = rule_func(price_data, **first_rule.get('params', {}))

        for rule_def in rule_stack_defs[1:]:
            rule_func = getattr(rules, rule_def['type'])
            combined_signals &= rule_func(price_data, **rule_def.get('params', {}))

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
                refresh_days=config.cache_refresh_days,
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
            start_date_filter = (date.today() - timedelta(days=config.hold_period)) if hasattr(config, 'hold_period') and config.hold_period else date.today()
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
        run_date = config.freeze_date or date.today()

        positions_to_hold: List[Dict[str, Any]] = []
        positions_to_close: List[Dict[str, Any]] = []

        # 2. Process each open position with dynamic exit checking
        for pos in open_positions:
            entry_date = date.fromisoformat(pos["entry_date"])
            days_held = (run_date - entry_date).days

            try:
                price_data = data.get_price_data(symbol=pos["symbol"], cache_dir=Path(config.cache_dir), start_date=entry_date, end_date=run_date, freeze_date=config.freeze_date, years=config.historical_data_years)
                nifty_data = data.get_price_data(symbol="^NSEI", cache_dir=Path(config.cache_dir), start_date=entry_date, end_date=run_date, freeze_date=config.freeze_date, years=config.historical_data_years)

                current_price = price_data['close'].iloc[-1] if not price_data.empty else pos['entry_price']
                current_low = price_data['low'].iloc[-1] if not price_data.empty else current_price
                current_high = price_data['high'].iloc[-1] if not price_data.empty else current_price
                return_pct = (current_price - pos['entry_price']) / pos['entry_price'] * 100 if pos['entry_price'] > 0 else 0.0
                nifty_return_pct = ((nifty_data['close'].iloc[-1] - nifty_data['close'].iloc[0]) / nifty_data['close'].iloc[0] * 100) if nifty_data is not None and not nifty_data.empty and nifty_data['close'].iloc[0] > 0 else 0.0

                pos.update({'current_price': current_price, 'return_pct': return_pct, 'nifty_return_pct': nifty_return_pct, 'days_held': days_held})

                # Check for dynamic exit conditions
                exit_reason = _check_exit_conditions(pos, price_data, current_low, current_high, rules_config.get('sell_conditions', []), days_held, config.hold_period) # type: ignore
                if exit_reason:
                    pos.update({'exit_date': run_date.isoformat(), 'exit_price': current_price, 'final_return_pct': return_pct, 'final_nifty_return_pct': nifty_return_pct, 'exit_reason': exit_reason})
                    positions_to_close.append(pos)
                else:
                    positions_to_hold.append(pos)
            except Exception as e:
                logger.warning(f"Could not process position for {pos['symbol']}: {e}")
                pos.update({'current_price': None, 'return_pct': None, 'nifty_return_pct': None, 'days_held': days_held})
                positions_to_hold.append(pos)

        # 3. Persist changes (close positions)
        if positions_to_close:
            persistence.close_positions_batch(db_path, positions_to_close)
        
        # 4. Identify and persist new signals
        new_signals = _identify_new_signals(db_path, run_timestamp, config)
        if new_signals:
            persistence.add_new_positions_from_signals(db_path, new_signals)
            logger.info(f"Added {len(new_signals)} new positions to the database.")

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

# impure
def analyze_rule_performance(db_path: Path) -> List[Dict[str, Any]]:
    """Analyzes the entire history of strategies to rank individual rule performance."""
    rule_stats: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: {'metrics': [], 'symbols': []})

    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT rule_stack, edge_score, win_pct, sharpe, symbol FROM strategies")
            strategies = cursor.fetchall()

        for strategy in strategies:
            try:
                rules_in_stack = json.loads(strategy['rule_stack'])
                if not isinstance(rules_in_stack, list): # Check if it's a list
                    logger.debug(f"Skipping malformed rule_stack (not a list) for strategy on symbol {strategy['symbol']}")
                    continue
                for rule_def in rules_in_stack:
                    if not isinstance(rule_def, dict): # Check if rule_def is a dict
                        logger.debug(f"Skipping malformed rule_def (not a dict) in rule_stack for symbol {strategy['symbol']}")
                        continue
                    rule_name = rule_def.get('name')
                    if not rule_name:
                        continue
                    
                    metrics = {
                        'edge_score': strategy['edge_score'],
                        'win_pct': strategy['win_pct'],
                        'sharpe': strategy['sharpe']
                    }
                    rule_stats[rule_name]['metrics'].append(metrics)
                    rule_stats[rule_name]['symbols'].append(strategy['symbol'])
            except (json.JSONDecodeError, TypeError):
                continue  # Skip malformed rule stacks

        analysis = []
        for name, data in rule_stats.items():
            freq = len(data['metrics'])
            avg_edge = sum(m['edge_score'] for m in data['metrics']) / freq
            avg_win = sum(m['win_pct'] for m in data['metrics']) / freq
            avg_sharpe = sum(m['sharpe'] for m in data['metrics']) / freq
            top_symbols_list = [s for s, count in Counter(data['symbols']).most_common(3)]
            
            analysis.append({
                'rule_name': name,
                'frequency': freq,
                'avg_edge_score': avg_edge,
                'avg_win_pct': avg_win,
                'avg_sharpe': avg_sharpe,
                'top_symbols': ", ".join(top_symbols_list),
            })

        return sorted(analysis, key=lambda x: x['avg_edge_score'], reverse=True)
    except sqlite3.Error as e:
        logger.error(f"Database error during rule analysis: {e}")
        return []


# pure
def format_rule_analysis_as_md(analysis: List[Dict[str, Any]]) -> str:
    """Formats the rule performance analysis into a markdown table."""
    title = "# Rule Performance Analysis\n\n"
    description = "This report analyzes all optimal strategies ever found to rank individual rule performance.\n\n"
    header = "| Rule Name | Frequency | Avg Edge Score | Avg Win % | Avg Sharpe | Top Symbols |\n"
    separator = "|:---|---:|---:|---:|---:|:---|\n"
    
    rows = []
    for stats in analysis:
        row = (
            f"| {stats['rule_name']} "
            f"| {stats['frequency']} "
            f"| {stats['avg_edge_score']:.2f} "
            f"| {stats['avg_win_pct']:.1%} "
            f"| {stats['avg_sharpe']:.2f} "
            f"| {stats['top_symbols']} |"
        )
        rows.append(row)
    
    return title + description + header + separator + "\n".join(rows)

def _check_exit_conditions(
    position: Dict[str, Any],
    price_data: pd.DataFrame,
    current_low: float,
    current_high: float,
    sell_conditions: List[Dict[str, Any]],
    days_held: int,
    hold_period: int
) -> Optional[str]:
    """Check exit conditions for an open position in priority order."""
    entry_price = position['entry_price']

    for condition in sell_conditions:
        rule_type = condition.get('type')
        params = condition.get('params', {})

        if rule_type == 'stop_loss_pct':
            percentage = params.get('percentage', 0)
            if current_low <= entry_price * (1 - percentage):
                return f"Stop-loss at -{percentage:.1%}"
        elif rule_type == 'take_profit_pct':
            percentage = params.get('percentage', 0)
            if current_high >= entry_price * (1 + percentage):
                return f"Take-profit at +{percentage:.1%}"
        else:
            try:
                rule_func = getattr(rules, rule_type, None)
                if rule_func and rule_func(price_data, **params).iloc[-1]:
                    return f"Rule: {condition.get('name', rule_type)}"
            except Exception as e:
                logger.warning(f"Error checking exit rule {rule_type}: {e}")

    if days_held >= hold_period:
        return f"Exit: End of {hold_period}-day holding period."
    return None

def analyze_strategy_performance(db_path: Path) -> List[Dict[str, Any]]:
    """Analyzes the entire history of strategies to rank strategy combinations."""
    # Use a defaultdict to easily aggregate data for each unique strategy.
    # The key will be the string representation of the rule stack.
    stats = defaultdict(lambda: {'metrics': [], 'symbols': []})

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        # Select all the data we need from every strategy ever saved.
        cursor = conn.execute("SELECT symbol, rule_stack, edge_score, win_pct, sharpe, total_trades, avg_return FROM strategies")
        strategies = cursor.fetchall()

    for strategy in strategies:
        try:
            rules_in_stack = json.loads(strategy['rule_stack'])
            # Ensure we have a list of rules
            if isinstance(rules_in_stack, list):
                # Create a consistent, readable key for the strategy combination.
                # e.g., "baseline_rule + rsi_filter + volume_filter"
                strategy_key = " + ".join(r.get('name', 'N/A') for r in rules_in_stack if isinstance(r, dict))
                if not strategy_key:
                    continue
            else:
                logger.warning(f"Invalid rule_stack format for {strategy['symbol']}: expected list, got {type(rules_in_stack)}")
                continue
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Malformed rule_stack JSON for {strategy['symbol']}: {strategy['rule_stack']}")
            continue

        # Append the metrics and symbol for later aggregation.
        stats[strategy_key]['metrics'].append(dict(strategy))
        stats[strategy_key]['symbols'].append(strategy['symbol'])

    # Now, process the aggregated data to calculate averages.
    analysis = []
    for key, strategy_data in stats.items():
        freq = len(strategy_data['metrics'])

        # Safely sum total_trades, as it might be corrupted in the DB
        total_trades_sum = 0
        for m in strategy_data['metrics']:
            try:
                total_trades_sum += int(m['total_trades'])
            except (ValueError, TypeError):
                logger.warning(
                    f"Could not parse total_trades '{m['total_trades']!r}' for strategy '{key}' "
                    f"on symbol '{m.get('symbol', 'N/A')}'. Treating as 0."
                )

        analysis.append({
            'strategy_name': key,
            'frequency': freq,
            'avg_edge_score': sum(float(m['edge_score']) for m in strategy_data['metrics']) / freq,
            'avg_win_pct': sum(float(m['win_pct']) for m in strategy_data['metrics']) / freq,
            'avg_sharpe': sum(float(m['sharpe']) for m in strategy_data['metrics']) / freq,
            'avg_trades': total_trades_sum / freq if freq > 0 else 0.0,
            'avg_return': sum(float(m['avg_return']) for m in strategy_data['metrics']) / freq,
            'top_symbols': ", ".join(s for s, _ in Counter(strategy_data['symbols']).most_common(3)),
        })

    # Sort by the primary performance metric.
    return sorted(analysis, key=lambda x: x['avg_edge_score'], reverse=True)


def format_strategy_analysis_as_md(analysis: List[Dict[str, Any]]) -> str:
    """Formats the strategy performance analysis into a markdown table."""
    header = "| Strategy (Rule Stack) | Freq. | Avg Edge | Avg Win % | Avg Sharpe | Avg Return | Avg Trades | Top Symbols |\n"
    separator = "|:---|---:|---:|---:|---:|---:|---:|:---|\n"
    
    rows = []
    for stats in analysis:
        row = (
            f"| `{stats['strategy_name']}` "
            f"| {stats['frequency']} "
            f"| {stats['avg_edge_score']:.2f} "
            f"| {stats['avg_win_pct']:.1%} "
            f"| {stats['avg_sharpe']:.2f} "
            f"| {stats['avg_return']:.1%} "
            f"| {stats['avg_trades']:.1f} "
            f"| {stats['top_symbols']} |"
        )
        rows.append(row)
    
    return f"# Strategy Performance Report\n\n{header}{separator}" + "\n".join(rows)
