"""
Pure reporting module for generating daily markdown reports from pre-calculated data.

This module is a read-only component that only formats data passed to it from 
the CLI orchestrator. It contains no business logic for signal generation or 
position management.
"""

from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional
import logging
import sqlite3
import json
import pandas as pd
from collections import defaultdict
from io import StringIO

from .config import Config

logger = logging.getLogger(__name__)


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
        strategy_name = " + ".join([r.get("name", r.get("type", "unknown")) for r in rule_stack])
        
        report = StringIO()
        report.write("WALK-FORWARD ANALYSIS RESULTS (Out-of-Sample Only)\n")
        report.write("=" * 60 + "\n\n")
        report.write(f"Symbol: {symbol}\n")
        report.write(f"Strategy: [{strategy_name}]\n\n")
        
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
        report.write(f"- Average Return: {metrics['avg_return']:.2f} (realistic expectation)\n")
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