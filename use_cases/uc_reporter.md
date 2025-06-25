| KISS | Version: 1.0 |
|---|---|
| Use Case Specification KS_REPORTER_BS_UC006 – Generate Daily Signal Report | Date: 08/07/24 |

# KS_REPORTER_BS_UC006 – Generate Daily Signal Report

**1. Brief Description**

This use case allows an actor to generate a daily markdown report that summarizes new buy signals, tracks the status of currently open positions, and identifies positions that should be sold based on exit criteria.

The use case can be called:
- As the final step in the main CLI `run` command to produce the daily actionable output.

**2. Actors**

**2.1 Primary Actors**
1. **CLI Orchestrator** – The main application component that initiates the report generation at the end of an analysis run.

**2.2 Secondary Actors**
- Persistence Module
- Data Module
- Rules Module

**3. Conditions**

**3.1 Pre-Condition**
- The database contains optimal strategies from a recent backtesting run.
- The database may contain existing 'OPEN' positions from previous runs.
- The price data cache is up-to-date.

**3.2 Post Conditions on success**
1. A markdown file (`signals_YYYY-MM-DD.md`) is created in the reports directory.
2. New buy signals are added to the `positions` table in the database with 'OPEN' status.
3. Positions that have met their exit criteria are updated to 'CLOSED' status in the database.

**3.3 Post Conditions on Failure**
1. The report file may not be created or may be incomplete.
2. An error is logged, but the application does not crash.

**4. Trigger**

1. A request to generate the daily report is issued by the Primary Actor. This request must contain:
    a. The path to the SQLite database (`db_path`).
    b. The timestamp of the current analysis run (`run_timestamp`).
    c. The application `config` object.

**5. Main Flow: KS_REPORTER_BS_UC006.MF – Generate Daily Signal Report**

10. The system identifies new buy signals using the _identify_new_signals function.
    10.10. The system fetches the single best strategy for each symbol using SQL window function with ROW_NUMBER().
    <<strategies = _fetch_best_strategies(db_path, run_timestamp, config.edge_score_threshold)>>
    10.20. The _fetch_best_strategies function uses ranked CTE to get top strategy per symbol above threshold.
    <<WITH ranked_strategies AS (SELECT *, ROW_NUMBER() OVER(PARTITION BY symbol ORDER BY edge_score DESC) as rn FROM strategies WHERE run_timestamp = ? AND edge_score >= ?) SELECT * FROM ranked_strategies WHERE rn = 1>>
    10.30. The ROW_NUMBER() window function ranks strategies by edge_score within each symbol partition.
    10.40. Only strategies meeting the edge_score_threshold are considered for signal generation.
    10.50. For each strategy, the system parses the rule_stack JSON to get rule definitions.
    <<rule_stack_defs = json.loads(rule_stack_json); rule_def = rule_stack_defs[0]>>
    10.60. JSON parsing reconstructs the complete rule definition including type and parameters.
    10.70. The system loads latest price data for each symbol with comprehensive error handling.
    <<try: price_data = data.get_price_data(symbol, cache_dir, refresh_days, years, freeze_date) except Exception: continue>>
    10.80. Error handling ensures individual symbol failures don't abort the entire signal identification process.
    *See Use Case KS_DATA_BS_UC004 – Get Market Price Data for price data retrieval including cache management and validation*
    10.90. The system checks if rule triggers a BUY signal on the last trading day using _check_for_signal.
    <<if _check_for_signal(price_data, rule_def): # Create signal record>>
    10.100. The _check_for_signal function applies rule to price data and checks last day signal.
    <<rule_func = getattr(rules, rule_type); signals = rule_func(price_data, **rule_params); return bool(signals.iloc[-1])>>
    10.110. The iloc[-1] operation checks the signal status on the most recent trading day.
    10.120. Dynamic rule loading using getattr() supports all rule types defined in the rules module.
    *See Use Case KS_RULES_BS_UC007 – Evaluate Technical Indicator Rule for rule execution details*
    10.130. For active signals, the system creates signal records with entry price and date.
    <<signals.append({'ticker': symbol, 'date': signal_date, 'entry_price': entry_price, 'rule_stack': rule_def.get('name', rule_def['type']), 'edge_score': strategy['edge_score']})>>
    10.140. Signal records include all necessary information for position tracking and reporting.

20. The system saves these new signals as 'OPEN' positions in the database.
    20.10. The system maps strategy rule_stacks for each signal to preserve complete rule definitions.
    <<strategies = _fetch_best_strategies(db_path, run_timestamp, 0.0); strategy_map = {s['symbol']: s['rule_stack'] for s in strategies}>>
    20.20. The system adds rule_stack_used field to each signal for database storage.
    <<for signal in new_signals: signal['rule_stack_used'] = strategy_map.get(signal['ticker'], "[]")>>
    20.30. The system calls persistence module to add new positions, preventing duplicates.
    <<persistence.add_new_positions_from_signals(db_path, new_signals)>>
    20.40. The add_new_positions_from_signals function checks for existing open positions before inserting.
    <<open_symbols = {row[0] for row in cursor.execute("SELECT symbol FROM positions WHERE status = 'OPEN'").fetchall()}; if symbol in open_symbols: continue>>
    *See Use Case KS_PERSISTENCE_BS_UC005 – Persist and Retrieve Trading Data for database operations*

30. The system fetches all currently 'OPEN' positions from the database.
    <<open_positions = persistence.get_open_positions(db_path)>>
    *See Use Case KS_PERSISTENCE_BS_UC005 – Persist and Retrieve Trading Data for position retrieval*

40. The system separates open positions into hold and close lists using _manage_open_positions function.
    40.10. For each position, the system calculates days held since entry using date arithmetic.
    <<entry_date = date.fromisoformat(pos["entry_date"]); days_held = (today - entry_date).days>>
    40.20. The fromisoformat() method parses ISO 8601 date strings stored in the database.
    40.30. The system checks if the holding period has been met for time-based exit strategy.
    <<if days_held >= config.hold_period: # Add to positions_to_close else: # Add to positions_to_hold>>
    40.40. The hold_period configuration defines the exact number of days to hold each position.
    40.50. For positions to close, the system loads current price data and calculates exit metrics.
    <<price_data = data.get_price_data(symbol, cache_dir, years=1); pos['exit_price'] = price_data['close'].iloc[-1]>>
    40.60. The iloc[-1] operation gets the most recent closing price for exit calculations.
    40.70. The system calculates final return percentage using standard return formula.
    <<pos['final_return_pct'] = (pos['exit_price'] - pos['entry_price']) / pos['entry_price'] * 100>>
    40.80. Return calculation uses percentage format for easy interpretation in reports.

50. The system separates the positions into two lists: `positions_to_hold` and `positions_to_close`.
    50.10. For positions to close, the system loads current price data and calculates exit metrics.
    50.20. The system calculates final return percentage and NIFTY benchmark comparison.
    <<final_return_pct = (exit_price - entry_price) / entry_price * 100>>

60. For positions to be held, the system calculates on-the-fly performance metrics using _calculate_open_position_metrics.
    60.10. The system loads current price data for each open position with error handling.
    <<try: price_data = data.get_price_data(symbol, cache_dir, years=1) except Exception: continue>>
    60.20. The system calculates current return percentage using latest close price.
    <<current_price = price_data['close'].iloc[-1]; return_pct = (current_price - pos["entry_price"]) / pos["entry_price"] * 100>>
    60.30. The system loads NIFTY data for benchmark comparison using ^NSEI symbol.
    <<nifty_data = data.get_price_data(symbol="^NSEI", cache_dir, start_date=entry_date, end_date=today)>>
    60.40. The system calculates NIFTY return for the same holding period with zero default.
    <<nifty_return_pct = 0.0; if nifty_data is not None and not nifty_data.empty: nifty_return_pct = (nifty_end_price - nifty_start_price) / nifty_start_price * 100>>
    60.50. The system updates position dictionary with calculated metrics.
    <<pos.update({"current_price": current_price, "return_pct": return_pct, "nifty_return_pct": nifty_return_pct, "days_held": days_held})>>

70. The system updates the database to mark the `positions_to_close` as 'CLOSED' and records their final exit details.
    <<persistence.close_positions_batch(db_path, positions_to_close)>>
    *See Use Case KS_PERSISTENCE_BS_UC005 – Persist and Retrieve Trading Data for position closure*

80. The system formats the markdown report content, including tables for NEW BUYS, OPEN POSITIONS, and POSITIONS TO SELL.
    80.10. The system creates summary line with counts of each position type.
    <<summary_line = f"**Summary:** {len(new_signals)} New Buy Signals, {len(reportable_open_positions)} Open Positions, {len(positions_to_close)} Positions to Sell.">>
    80.20. The system formats NEW BUYS table with ticker, date, entry price, rule stack, and edge score.
    <<new_buys_table = "| Ticker | Recommended Buy Date | Entry Price | Rule Stack | Edge Score |\n"; for signal in new_signals: new_buys_table += f"| {signal['ticker']} | {signal['date']} | {signal['entry_price']:.2f} | {signal['rule_stack']} | {signal['edge_score']:.2f} |\n">>
    80.30. The system formats OPEN POSITIONS table with current metrics and benchmark comparison.
    <<open_pos_table = "| Ticker | Entry Date | Entry Price | Current Price | Return % | NIFTY Period Return % | Day in Trade |\n"; for pos in reportable_open_positions: open_pos_table += f"| {pos['symbol']} | {pos['entry_date']} | {pos['entry_price']:.2f} | {pos['current_price']:.2f} | {pos['return_pct']:+.2f}% | {pos['nifty_return_pct']:+.2f}% | {pos['days_held']} / {config.hold_period} |\n">>
    80.40. The system formats POSITIONS TO SELL table with exit reasons.
    <<sell_pos_table = "| Ticker | Status | Reason |\n"; for pos in positions_to_close: sell_pos_table += f"| {pos['symbol']} | SELL | Exit: End of {config.hold_period}-day holding period. |\n">>
    80.50. The system combines all sections into complete markdown report content with header and footer.
    <<report_content = f"# Signal Report: {report_date_str}\n\n{summary_line}\n\n## NEW BUYS\n{new_buys_table}\n\n## OPEN POSITIONS\n{open_pos_table}\n\n## POSITIONS TO SELL\n{sell_pos_table}\n\n---\n*Report generated by KISS Signal CLI v1.4 on {report_date_str}*">>

90. The system writes the formatted content to a markdown file in the configured reports directory.
    90.10. The system creates output directory if it doesn't exist using Path operations.
    <<output_dir = Path(config.reports_output_dir); output_dir.mkdir(parents=True, exist_ok=True)>>
    90.20. The system creates timestamped filename using today's date.
    <<report_date_str = date.today().strftime("%Y-%m-%d"); report_file = output_dir / f"signals_{report_date_str}.md">>
    90.30. The system writes content to file with UTF-8 encoding and logs success.
    <<report_file.write_text(report_content, encoding='utf-8'); logger.info(f"Report generated: {report_file}")>>
    90.40. The system returns the report file path for confirmation.
    <<return report_file>>
    *See Exception Flow 1: KS_REPORTER_BS_UC006.XF01 – Report File Write Failed*

99. The use case ends.

**6. Flows (Exception/Alternative/Extension)**

**6.1 Exception Flow 1: KS_REPORTER_BS_UC006.XF01 – Report File Write Failed**

10. At **step 90 of the main flow**, the system encounters an error while trying to write the report file.
    <<OSError>>
20. The system logs the error.
30. The system returns a failure status (e.g., `None`) to the primary actor.
99. The use case ends.

**7. Notes / Assumptions**

- This use case orchestrates logic from multiple other modules (data, persistence, rules) to achieve its goal.
- The _fetch_best_strategies function uses SQL window functions (ROW_NUMBER) for efficient top-N-per-group queries.
- The _check_for_signal function applies rule functions to latest price data to detect active signals.
- Signal detection uses the last trading day in the price data to determine entry timing.
- Position management separates concerns: identification, metric calculation, and database updates.
- The _manage_open_positions function separates positions into hold/close lists based on hold_period.
- NIFTY benchmark (^NSEI) is used for performance comparison against market index.
- The exit condition is currently limited to a fixed holding period (time-based exits only).
- Report format includes markdown tables for easy readability and potential automation.
- Error handling continues report generation even if individual position calculations fail.
- UTF-8 encoding ensures proper handling of special characters in report content.
- The system prevents duplicate open positions for the same symbol using database checks.
- Rule stack definitions are preserved in JSON format for complete signal traceability.
- The report includes summary statistics and is timestamped with generation date.
- Database operations use row_factory = sqlite3.Row for dict-like access to query results.

**8. Issues**

| No: | Description: | Date | Action: | Status |
|---|---|---|---|---|
| 1. | | | | |

**9. Revision History**

| Date | Rev | Who | Description | Reference |
|---|---|---|---|---|
| 08/07/24 | 1.0 | AI | Initial document creation. | |

**10. Reference Documentation**

| Document Name | Version | Description | Location |
|---|---|---|---|
| `src/kiss_signal/reporter.py` | | Source code for the reporting module with signal detection and report generation. | Git Repository |
| `src/kiss_signal/data.py` | | Data module for price data retrieval. | Git Repository |
| `src/kiss_signal/rules.py` | | Rules module for signal detection. | Git Repository |
| `src/kiss_signal/persistence.py` | | Persistence module for database operations. | Git Repository |
| `docs/prd.md` | 1.4 | Product Requirements Document defining the report format. | Git Repository |
