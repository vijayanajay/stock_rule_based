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
import json
import sqlite3
import pandas as pd

from . import data, rules, persistence
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

        # Start with a Series of all True, then AND with each rule's signals
        combined_signals = pd.Series(True, index=price_data.index)
        for rule_def in rule_stack_defs:
            rule_type = rule_def['type']
            rule_params = rule_def.get('params', {})
            rule_func = getattr(rules, rule_type)
            
            # AND the signals together
            combined_signals &= rule_func(price_data, **rule_params)

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


def _calculate_open_position_metrics(
    open_positions: List[Dict[str, Any]], config: Config
) -> List[Dict[str, Any]]:
    """Calculate metrics for open positions for reporting."""
    if not open_positions:
        return []

    augmented_positions = []
    run_date = config.freeze_date or date.today()

    for pos in open_positions:
        entry_date = date.fromisoformat(pos["entry_date"])
        days_held = (run_date - entry_date).days
        try:
            price_data = data.get_price_data(
                symbol=pos["symbol"],
                cache_dir=Path(config.cache_dir),
                refresh_days=config.cache_refresh_days,
                start_date=entry_date,
                end_date=run_date,
                freeze_date=config.freeze_date,
            )
            if price_data is None or price_data.empty:
                logger.warning(f"Could not get price data for open position {pos['symbol']}. Reporting with N/A.")
                pos.update({
                    "current_price": None, "return_pct": None,
                    "nifty_return_pct": None, "days_held": days_held,
                })
            else:
                current_price = price_data['close'].iloc[-1]
                return_pct = (current_price - pos["entry_price"]) / pos["entry_price"] * 100

                nifty_data = data.get_price_data(
                    symbol="^NSEI",
                    cache_dir=Path(config.cache_dir),
                    refresh_days=config.cache_refresh_days,
                    start_date=entry_date,
                    end_date=run_date,
                    freeze_date=config.freeze_date,
                )
                
                nifty_return_pct = 0.0
                if nifty_data is not None and not nifty_data.empty:
                    nifty_start_price = nifty_data['close'].iloc[0]
                    nifty_end_price = nifty_data['close'].iloc[-1]
                    if nifty_start_price > 0:
                        nifty_return_pct = (nifty_end_price - nifty_start_price) / nifty_start_price * 100

                pos.update({
                    "current_price": current_price, "return_pct": return_pct,
                    "nifty_return_pct": nifty_return_pct, "days_held": days_held,
                })

        except Exception as e:
            logger.error(f"Error calculating metrics for position {pos['symbol']}: {e}")
            pos.update({
                "current_price": None, "return_pct": None,
                "nifty_return_pct": None,
                "days_held": days_held,
            })
        augmented_positions.append(pos)
            
    return augmented_positions


def _manage_open_positions(
    open_positions: List[Dict[str, Any]], config: Config
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separates open positions into 'hold' and 'close' lists and calculates metrics."""
    positions_to_hold: List[Dict[str, Any]] = []
    positions_to_close: List[Dict[str, Any]] = []
    run_date = config.freeze_date or date.today()

    for pos in open_positions:
        entry_date = date.fromisoformat(pos["entry_date"])
        days_held = (run_date - entry_date).days
        if days_held >= config.hold_period:
            try:
                price_data = data.get_price_data(
                    symbol=pos["symbol"], cache_dir=Path(config.cache_dir),
                    refresh_days=config.cache_refresh_days,
                    start_date=entry_date, end_date=run_date,
                    freeze_date=config.freeze_date
                )
                if price_data is not None and not price_data.empty:
                    pos['exit_price'] = price_data['close'].iloc[-1]
                    pos['exit_date'] = run_date.strftime('%Y-%m-%d')
                    pos['days_held'] = days_held
                    pos['final_return_pct'] = (pos['exit_price'] - pos['entry_price']) / pos['entry_price'] * 100
                    nifty_data = data.get_price_data(
                        symbol="^NSEI", cache_dir=Path(config.cache_dir),
                        start_date=entry_date, end_date=run_date,
                        freeze_date=config.freeze_date
                    )
                    pos['final_nifty_return_pct'] = 0.0
                    if nifty_data is not None and not nifty_data.empty:
                        nifty_start = nifty_data['close'].iloc[0]
                        nifty_end = nifty_data['close'].iloc[-1]
                        if nifty_start > 0:
                            pos['final_nifty_return_pct'] = (nifty_end - nifty_start) / nifty_start * 100
                else:
                    logger.warning(f"Could not get exit price for closing position {pos['symbol']}: No data.")
                    pos['exit_price'] = None
                    pos['exit_date'] = run_date.strftime('%Y-%m-%d')
                    pos['days_held'] = days_held
                    pos['final_return_pct'] = None
                    pos['final_nifty_return_pct'] = None
            except Exception as e:
                logger.warning(f"Could not get exit price for closing position {pos['symbol']}: {e}")
                pos['exit_price'] = None
                pos['exit_date'] = run_date.strftime('%Y-%m-%d')
                pos['days_held'] = days_held
                pos['final_return_pct'] = None
                pos['final_nifty_return_pct'] = None
            positions_to_close.append(pos)
        else:
            positions_to_hold.append(pos)
    return positions_to_hold, positions_to_close


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
    closed_positions: List[Dict[str, Any]], hold_period: int
) -> str:
    """Formats the markdown table for positions to sell."""
    if not closed_positions:
        return "*No positions to sell.*"

    header = "| Ticker | Status | Reason |\n"
    separator = "|:-------|:-------|:-------|\n"
    rows = [
        f"| {pos['symbol']} | SELL | Exit: End of {hold_period}-day holding period. |"
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
    sell_pos_table = _format_sell_positions_table(closed_positions, config.hold_period)

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
) -> Optional[Path]:
    """
    Generates the main daily markdown report.
    
    Returns the path to the generated report file, or None if failed.
    """
    try:
        # 1. Fetch all existing open positions and determine their status FIRST
        open_positions = persistence.get_open_positions(db_path)
        positions_to_hold, positions_to_close = _manage_open_positions(open_positions, config)

        # 2. Calculate metrics for reporting (on-the-fly for open positions to be held)
        reportable_open_positions = _calculate_open_position_metrics(positions_to_hold, config)

        # 3. Close positions that have met their exit criteria
        if positions_to_close:
            persistence.close_positions_batch(db_path, positions_to_close)
            logger.info(f"Closed {len(positions_to_close)} positions.")

        # 4. Identify and save new buy signals
        new_signals = _identify_new_signals(db_path, run_timestamp, config)
        if new_signals:
            strategies = _fetch_best_strategies(db_path, run_timestamp, 0.0)
            strategy_map = {s['symbol']: s['rule_stack'] for s in strategies}
            for signal in new_signals:
                signal['rule_stack_used'] = strategy_map.get(signal['ticker'], "[]")
            persistence.add_new_positions_from_signals(db_path, new_signals)
            logger.info(f"Added {len(new_signals)} new positions to the database.")

        # 5. Generate the report content using the separated lists
        report_date_str = date.today().strftime("%Y-%m-%d")
        report_content = _build_report_content(
            report_date_str, new_signals, reportable_open_positions, positions_to_close, config
        )
        
        # 6. Write the report to a file
        output_dir = Path(config.reports_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = output_dir / f"signals_{report_date_str}.md"
        report_file.write_text(report_content, encoding='utf-8')
        logger.info(f"Report generated: {report_file}")
        return report_file
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        return None
