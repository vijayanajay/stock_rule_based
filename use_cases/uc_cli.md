| KISS | Version: 1.0 |
|---|---|
| Use Case Specification KS_CLI_BS_UC002 – Run Full Signal Analysis Pipeline | Date: 08/07/24 |

# KS_CLI_BS_UC002 – Run Full Signal Analysis Pipeline

**1. Brief Description**

This use case allows a user to execute the entire signal analysis pipeline via a single command. This includes refreshing data, finding optimal strategies for each stock, persisting the results, and generating a daily report.

The use case can be called:
- By a trader at the end of the trading day to get signals for the next day.
- During development or research to test the end-to-end workflow.

**2. Actors**

**2.1 Primary Actors**
1. **User/Trader** – The person who initiates the analysis to get trading signals.

**2.2 Secondary Actors**
- Config Module
- Data Module
- Backtester Module
- Persistence Module
- Reporter Module

**3. Conditions**

**3.1 Pre-Condition**
- The user has access to a command line interface.
- Valid `config.yaml` and `rules.yaml` files exist at specified paths.

**3.2 Post Conditions on success**
1. Historical price data cache is updated (if not in freeze mode).
2. Optimal strategies are identified and saved to the SQLite database.
3. A daily markdown report (`signals_YYYY-MM-DD.md`) is generated in the reports directory.
4. A summary of the run is displayed on the console.

**3.3 Post Conditions on Failure**
1. The application exits with a non-zero status code.
2. A specific error message is displayed on the console.
3. A `run_log.txt` file is created with detailed error information.

**4. Trigger**

1. The User executes the `run` command from the command line. This request must contain:
    a. The `--config` argument with a path to `config.yaml`.
    b. The `--rules` argument with a path to `rules.yaml`.
    c. Optional flags like `--verbose` or `--freeze-data`.

**5. Main Flow: KS_CLI_BS_UC002.MF – Run Full Signal Analysis Pipeline**

10. The system loads and validates the application configuration and trading rules from the provided file paths.
    <<app_config = load_config(config_path)>>
    <<rules_config = load_rules(rules_path)>>
    *See Exception Flow 1: KS_CLI_BS_UC002.XF01 – Invalid or Missing Configuration*

20. The system refreshes the market data cache for all symbols in the universe, unless in freeze mode.
    20.10. The system loads the universe symbols from the CSV file.
    <<symbols = data.load_universe(app_config.universe_path)>>
    20.20. If freeze_date is provided, the system skips data refresh to maintain deterministic results.
    <<if freeze_date: logger.info(f"Freeze mode active: {freeze_date}")>>
    20.30. Otherwise, the system calls the data module to refresh market data for all symbols.
    <<data.refresh_market_data(universe_path, cache_dir, refresh_days, years, freeze_date)>>
    20.40. The data module filters symbols needing refresh using _needs_refresh() function.
    <<symbols_to_fetch = [symbol for symbol in symbols if _needs_refresh(symbol, cache_path, refresh_days)]>>
    20.50. For each stale symbol, the data module downloads fresh data using yfinance API with 3-retry exponential backoff.
    <<data = _fetch_symbol_data(symbol_with_suffix, years, freeze_date)>>
    20.60. Downloaded data undergoes quality validation: negative prices, >10% zero volume days, >5 day gaps.
    <<_validate_data_quality(data, symbol)>>
    20.70. Valid data is saved to cache files in CSV format with standardized lowercase OHLCV columns.
    <<_save_symbol_cache(symbol, data, cache_path)>>
    *See Use Case KS_DATA_BS_UC004 – Get Market Price Data for complete data refresh implementation including cache management, yfinance integration, and quality validation*
    *See Exception Flow 2: KS_CLI_BS_UC002.XF02 – Data Refresh Failure*

30. The system runs backtests for all symbols to find the optimal trading strategies.
    30.10. The system creates a Backtester instance with configured parameters.
    <<bt = backtester.Backtester(hold_period=getattr(app_config, "hold_period", 20), min_trades_threshold=getattr(app_config, "min_trades_threshold", 10))>>
    30.20. The system displays progress using Rich console status indicator.
    <<with console.status("[bold green]Running backtests...") as status:>>
    30.30. For each symbol in the universe, the system loads price data using the data module.
    <<price_data = data.get_price_data(symbol, cache_dir, refresh_days, years, freeze_date)>>
    30.40. The system validates that sufficient data exists (minimum 100 rows) for backtesting.
    <<if price_data is None or len(price_data) < 100: logger.warning(f"Insufficient data for {symbol}, skipping")>>
    30.50. The system calls the backtester to find optimal strategies for the current symbol.
    <<strategies = bt.find_optimal_strategies(rule_combinations, price_data, freeze_date)>>
    30.60. The backtester generates entry signals using _generate_signals() method for each rule combination.
    <<entry_signals = self._generate_signals(rule_combo, price_data)>>
    30.70. Time-based exit signals are generated using vectorbt's forward shift.
    <<exit_signals = entry_signals.vbt.fshift(hold_period)>>
    30.80. Portfolio simulation is created with realistic trading costs (0.1% fees, 0.05% slippage).
    <<portfolio = vbt.Portfolio.from_signals(close=price_data['close'], entries=entry_signals, exits=exit_signals, fees=0.001, slippage=0.0005, init_cash=100000)>>
    30.90. Strategies with insufficient trades (< min_trades_threshold) are filtered out.
    <<if total_trades < self.min_trades_threshold: continue>>
    30.100. Valid strategies are ranked by calculated edge score using default weights (60% win_pct + 40% sharpe).
    <<edge_score = (win_pct * 0.6) + (sharpe * 0.4)>>
    30.110. The symbol is added to each strategy result and complete rule definition is preserved in rule_stack.
    <<strategy["symbol"] = symbol; strategy['rule_stack'] = [rule_combo]>>
    *See Use Case KS_BACKTESTER_BS_UC001 – Find Optimal Trading Strategies for complete backtesting implementation including signal generation, portfolio simulation, and performance metrics calculation*

40. The system displays a summary of the top-performing strategies on the console using Rich table formatting.
    40.10. The system creates a Rich Table with columns for Symbol, Rule Stack, Edge Score, Win %, Sharpe, and Trades.
    <<table = Table(title="Top Strategies by Edge Score")>>
    40.20. The system sorts all results by edge score in descending order and selects top 10.
    <<top_strategies = sorted(results, key=lambda x: x["edge_score"], reverse=True)[:10]>>
    40.30. For each strategy, the system extracts rule names for display.
    <<rule_stack_str = " + ".join([r.get('name', r.get('type', '')) for r in strategy["rule_stack"]])>>
    40.40. The system displays the formatted table and summary statistics.
    <<console.print(table); console.print(f"Found {len(results)} valid strategies across {len(set(s['symbol'] for s in results))} symbols")>>

50. The system saves the optimal strategies to the SQLite database.
    50.10. The system ensures the database directory exists.
    <<db_path.parent.mkdir(parents=True, exist_ok=True)>>
    50.20. The system creates the database with proper schema if it doesn't exist.
    <<persistence.create_database(db_path)>>
    50.30. The system generates an ISO 8601 timestamp for the current run.
    <<run_timestamp = datetime.now().isoformat()>>
    50.40. The system saves all strategies in a single atomic transaction.
    <<success = persistence.save_strategies_batch(db_path, results, run_timestamp)>>
    50.50. The system logs success or failure but continues execution on persistence failure.
    <<if success: logger.info(f"Saved {len(results)} strategies to database") else: logger.warning("Persistence failed but continuing execution")>>
    *See Use Case KS_PERSISTENCE_BS_UC005 – Persist and Retrieve Trading Data for complete database operations including schema creation, batch inserts, and transaction management*
    *See Exception Flow 3: KS_CLI_BS_UC002.XF03 – Database Persistence Failure*

60. The system generates the daily markdown report based on the latest signals and open positions.
    60.10. The system calls the reporter module to generate the complete daily report.
    <<report_path = reporter.generate_daily_report(db_path=Path(app_config.database_path), run_timestamp=run_timestamp, config=app_config)>>
    60.20. The reporter identifies new buy signals by fetching best strategies above edge_score_threshold.
    <<strategies = _fetch_best_strategies(db_path, run_timestamp, config.edge_score_threshold)>>
    60.30. For each strategy, the reporter checks if rule triggers BUY signal on latest trading day.
    <<signal_active = _check_for_signal(price_data, rule_def)>>
    60.40. New signals are saved as 'OPEN' positions in the database.
    <<persistence.add_new_positions_from_signals(db_path, new_signals)>>
    60.50. The system fetches all currently 'OPEN' positions and separates them into hold/close lists.
    <<positions_to_hold, positions_to_close = _manage_open_positions(open_positions, config)>>
    60.60. Current metrics are calculated for open positions (price, return %, NIFTY comparison).
    <<reportable_open_positions = _calculate_open_position_metrics(positions_to_hold, config)>>
    60.70. Positions meeting the hold_period criteria are marked as 'CLOSED' in database.
    <<persistence.close_positions_batch(db_path, positions_to_close)>>
    60.80. The system formats markdown tables for NEW BUYS, OPEN POSITIONS, and POSITIONS TO SELL.
    60.90. The complete report is written to a timestamped markdown file in the reports directory.
    <<report_file.write_text(report_content, encoding='utf-8')>>
    60.100. The system displays success message or warning on report generation failure.
    <<if report_path: console.print(f"✨ Report generated: {report_path}") else: console.print("⚠️ Report generation failed")>>
    *See Use Case KS_REPORTER_BS_UC006 – Generate Daily Signal Report for complete report generation including signal identification, position management, and markdown formatting*
    *See Exception Flow 4: KS_CLI_BS_UC002.XF04 – Report Generation Failure*

99. The use case ends.

**6. Flows (Exception/Alternative/Extension)**

**6.1 Exception Flow 1: KS_CLI_BS_UC002.XF01 – Invalid or Missing Configuration**

10. At **step 10 of the main flow**, the system determines that a configuration file is missing or contains invalid data.
    <<FileNotFoundError>> or <<pydantic.ValidationError>>
20. The system prints a specific error message to the console.
30. The system exits with a non-zero status code.
99. The use case ends.

**6.2 Exception Flow 2: KS_CLI_BS_UC002.XF02 – Data Refresh Failure**

10. At **step 20 of the main flow**, the system fails to download or validate data for a significant number of symbols.
20. The system logs the errors and may continue with cached data or abort if data is insufficient.
30. If aborting, the system prints an error message and exits.
99. The use case ends.

**6.3 Exception Flow 3: KS_CLI_BS_UC002.XF03 – Database Persistence Failure**

10. At **step 50 of the main flow**, the system fails to connect to or write to the SQLite database.
    <<sqlite3.Error>>
20. The system prints a warning message to the console but continues execution to generate the report.
30. The flow continues from **step 60 of the main flow**.

**6.4 Exception Flow 4: KS_CLI_BS_UC002.XF04 – Report Generation Failure**

10. At **step 60 of the main flow**, the system fails to write the markdown report file.
    <<OSError>>
20. The system prints a warning message to the console.
99. The use case ends.

**7. Notes / Assumptions**

- The CLI uses Typer framework for command-line interface with Rich for enhanced console output.
- Logging is configured with RichHandler and noisy third-party loggers (numba, vectorbt) are silenced.
- The system displays a project banner using Rich Panel before execution.
- Progress is shown using Rich console status indicators during long-running operations.
- All console output is recorded and saved to run_log.txt file for debugging.
- Error handling is graceful - persistence or report failures don't crash the CLI.
- The system validates file existence before attempting to load configuration files.
- Freeze mode prevents data downloads to ensure deterministic backtesting results.
- The user is expected to have Python and the required dependencies (typer, rich, pydantic, pyyaml) installed.

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
| `src/kiss_signal/cli.py` | | Source code for the CLI module with Typer framework implementation. | Git Repository |
| `src/kiss_signal/data.py` | | Data module for market data fetching and caching. | Git Repository |
| `src/kiss_signal/backtester.py` | | Backtesting engine using vectorbt library. | Git Repository |
| `src/kiss_signal/persistence.py` | | SQLite persistence layer for strategies and positions. | Git Repository |
| `src/kiss_signal/reporter.py` | | Daily report generation module. | Git Repository |
