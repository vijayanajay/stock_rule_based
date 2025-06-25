| KISS | Version: 1.0 |
|---|---|
| Use Case Specification KS_BACKTESTER_BS_UC001 – Find Optimal Trading Strategies | Date: 08/07/24 |

# KS_BACKTESTER_BS_UC001 – Find Optimal Trading Strategies

**1. Brief Description**

This use case allows an actor to backtest a list of trading rule combinations against historical price data to find the most optimal strategies based on a calculated edge score.

The use case can be called:
- As part of the main analysis pipeline to discover the best strategy for each stock in the universe.
- During a research phase to evaluate the performance of new or modified trading rules.

**2. Actors**

**2.1 Primary Actors**
1. **CLI Orchestrator** – The main application component that orchestrates the analysis pipeline and requires optimal strategies for signal generation.

**2.2 Secondary Actors**
- Rules Module
- vectorbt Library

**3. Conditions**

**3.1 Pre-Condition**
- A list of valid rule combinations to be tested is available.
- A pandas DataFrame containing historical OHLCV price data is available.

**3.2 Post Conditions on success**
1. A list of validated strategies, ranked by their edge score, is returned to the actor.
2. Each strategy in the list contains performance metrics (win percentage, Sharpe ratio, total trades, etc.).

**3.3 Post Conditions on Failure**
1. An empty list of strategies is returned.
2. Errors encountered during the backtesting of any single rule combination are logged, but the process continues with the next combination.

**4. Trigger**

1. A request to find optimal strategies is issued by the Primary Actor. This request must contain:
    a. A list of rule combination dictionaries (`rule_combinations`).
    b. A pandas DataFrame of historical price data (`price_data`).
    c. An optional set of weights for the edge score calculation (`edge_score_weights`).

**5. Main Flow: KS_BACKTESTER_BS_UC001.MF – Find Optimal Trading Strategies**

10. The system receives the list of rule combinations and the price data.
    10.10. The system validates that rule_combinations is not empty.
    <<len(rule_combinations) > 0>>
    10.20. If freeze_date is provided, the system filters price data up to that date.
    <<price_data = price_data[price_data.index.date <= freeze_date]>>
    10.30. The system sets default edge score weights if not provided.
    <<edge_score_weights = {'win_pct': 0.6, 'sharpe': 0.4}>>

20. The system iterates through each `rule_combo` in the `rule_combinations` list.
    20.10. The system logs progress every 5th strategy to reduce verbosity.
    20.20. The system extracts rule name for logging purposes.
    <<rule_name = rule_combo.get('name', rule_combo.get('rule_stack', ['unknown']))>>

30. For the current `rule_combo`, the system generates entry signals using the _generate_signals method.
    30.10. The system validates that the rule_combo contains required 'type' field.
    <<rule_type = rule_combo.get('type'); if not rule_type: raise ValueError(f"Rule combination missing 'type' field: {rule_combo}")>>
    30.20. The system retrieves the rule function from the rules module using getattr.
    <<rule_func = getattr(rules, rule_type, None); if rule_func is None: raise ValueError(f"Rule function '{rule_type}' not found in rules module")>>
    30.30. The system validates that rule parameters are provided and not empty.
    <<rule_params = rule_combo.get('params', {}); if not rule_params: raise ValueError(f"Missing parameters for rule '{rule_type}'")>>
    30.40. The system calls the rule function with price data and parameters, handling exceptions.
    <<try: entry_signals = rule_func(price_data, **rule_params) except Exception as e: raise ValueError(f"Rule '{rule_type}' failed execution") from e>>
    30.50. The _generate_signals method supports multiple rule types: sma_crossover, ema_crossover, rsi_oversold.
    30.60. For sma_crossover: validates fast_period < slow_period, calculates rolling means, detects crossover using shift(1).
    30.70. For ema_crossover: validates fast_period < slow_period, calculates exponential means using ewm(), detects crossover.
    30.80. For rsi_oversold: calculates RSI using Wilder's exponential smoothing, detects recovery signals when RSI crosses below threshold.
    30.90. All rule functions return boolean pandas Series with same index as price_data, NaN values filled with False.
    30.100. The system logs debug information about signal count if debug logging is enabled.
    <<if logger.isEnabledFor(logging.DEBUG): logger.debug(f"Generated {entry_signals.sum()} entry signals for rule '{rule_type}'")>>
    *See Use Case KS_RULES_BS_UC007 – Evaluate Technical Indicator Rule for detailed signal generation implementation*

40. The system generates time-based exit signals using the _generate_time_based_exits method.
    40.10. The _generate_time_based_exits method takes entry_signals Series and hold_period integer as parameters.
    40.20. The system uses vectorbt's forward shift (fshift) to create exit signals after hold_period days.
    <<exit_signals = self._generate_time_based_exits(entry_signals, self.hold_period)>>
    40.30. The _generate_time_based_exits method applies vectorbt's clean vectorized forward shift operation.
    <<return entry_signals.vbt.fshift(hold_period)>>
    40.40. This creates exit signals exactly hold_period days after each entry signal, implementing time-based exit strategy.
    40.50. The resulting exit_signals Series has same index as entry_signals but values shifted forward by hold_period.

50. The system creates a portfolio simulation using vectorbt's from_signals method.
    50.10. The system configures realistic portfolio parameters: 0.1% fees, 0.05% slippage, 100K initial cash.
    50.20. The system uses daily frequency ('D') to match the price data time series.
    50.30. The system sets size=np.inf for percentage-based position sizing (uses all available capital).
    50.40. The system creates the portfolio with complete parameter specification.
    <<portfolio = vbt.Portfolio.from_signals(close=price_data['close'], entries=entry_signals, exits=exit_signals, freq='D', fees=0.001, slippage=0.0005, init_cash=100000, size=np.inf)>>
    50.50. The portfolio object contains all trade records, performance metrics, and statistical methods for analysis.

60. The system determines if the number of trades generated by the strategy is greater than or equal to the `min_trades_threshold`.
    <<total_trades = portfolio.trades.count()>>
    <<total_trades >= min_trades_threshold>>
    *See Exception Flow 1: KS_BACKTESTER_BS_UC001.XF01 – Insufficient Trades for Strategy*

70. The system calculates the strategy's performance metrics using vectorbt methods.
    70.10. The system checks if trades exist before calculating metrics to avoid division by zero.
    <<if total_trades > 0: # Calculate metrics else: win_pct = 0.0; sharpe = 0.0; avg_return = 0.0>>
    70.20. The system calculates win percentage using vectorbt's win_rate method (returns 0-100, converted to 0-1).
    <<win_pct = portfolio.trades.win_rate() / 100.0>>
    70.30. The win_rate method analyzes all completed trades and calculates percentage of profitable trades.
    70.40. The system calculates Sharpe ratio using vectorbt's sharpe_ratio method on portfolio returns.
    <<sharpe = portfolio.sharpe_ratio()>>
    70.50. The sharpe_ratio method calculates risk-adjusted returns using portfolio's daily return series.
    70.60. The system calculates average return from trades records with comprehensive error handling.
    <<try: trades_df = portfolio.trades.records_readable; avg_return = trades_df['Return [%]'].mean() / 100.0 if 'Return [%]' in trades_df.columns else 0.0 except Exception: avg_return = 0.0>>
    70.70. The records_readable method provides human-readable DataFrame with trade details including entry/exit prices and returns.
    70.80. The system handles NaN values from vectorbt calculations by defaulting to 0.0 for edge score calculation.
    <<win_pct = 0.0 if pd.isna(win_pct) else win_pct; sharpe = 0.0 if pd.isna(sharpe) else sharpe>>
    70.90. NaN handling ensures edge score calculation always receives valid numeric inputs.

80. The system calculates the `edge_score` for the strategy using the provided weights.
    <<edge_score = (win_pct * weights['win_pct']) + (sharpe * weights['sharpe'])>>

90. The system stores the complete strategy definition and its calculated metrics in a list of results.
    90.10. The system creates a strategy dictionary with rule_stack containing the full rule definition for self-contained persistence.
    <<strategy = {'rule_stack': [rule_combo], 'edge_score': edge_score, 'win_pct': win_pct, 'sharpe': sharpe, 'total_trades': total_trades, 'avg_return': avg_return}>>
    90.20. The system appends the strategy to the results list for later sorting and ranking.
    <<strategies.append(strategy)>>

100. After all combinations are tested, the system sorts the list of valid strategies in descending order by `edge_score`.
    <<strategies.sort(key=lambda x: x['edge_score'], reverse=True)>>

110. The system returns the ranked list of strategies to the primary actor.
    110.10. The system logs the total number of valid strategies found.
    <<logger.info(f"Found {len(strategies)} valid strategies (>= {min_trades_threshold} trades)")>>

99. The use case ends.

**6. Flows (Exception/Alternative/Extension)**

**6.1 Exception Flow 1: KS_BACKTESTER_BS_UC001.XF01 – Insufficient Trades for Strategy**

10. At **step 60 of the main flow**, the system determines that the number of trades is below the minimum threshold.
    <<portfolio.trades.count() < min_trades_threshold>>
20. The system logs that the strategy is being skipped due to an insufficient number of trades.
30. The system discards the current rule combination and proceeds to the next one in the list, returning to **step 20 of the main flow**.

**7. Notes / Assumptions**

- The `_generate_signals` method validates rule types and parameters, raising ValueError for invalid configurations.
- The `_generate_time_based_exits` method uses vectorbt's vbt.fshift() for clean vectorized exit signal generation.
- The use case assumes that the input price data has already been cleaned and validated by the data module.
- Portfolio simulation uses realistic trading costs: 0.1% fees and 0.05% slippage with 100K initial cash.
- Edge score calculation uses default weights of 60% win percentage and 40% Sharpe ratio if not provided.
- The complete rule definition is persisted in rule_stack to make database records self-contained.
- Exception handling continues processing remaining rule combinations if individual rules fail.
- Progress logging occurs every 5th strategy to reduce verbosity during backtesting.
- The calc_edge_score method implements weighted scoring: edge_score = (win_pct * weights['win_pct']) + (sharpe * weights['sharpe']).
- Vectorbt's from_signals method handles complex portfolio mechanics including position sizing, fees, and slippage automatically.
- The min_trades_threshold filter ensures only statistically significant strategies are considered (default 10 trades).
- Rule functions from the rules module are dynamically loaded using getattr() for flexible rule type support.
- All rule functions return boolean pandas Series with same index as input price data for consistent signal alignment.
- Time-based exits are the only exit strategy currently implemented (no stop-loss or take-profit exits).
- The hold_period parameter defines the exact number of days to hold positions after entry signals.
- Portfolio simulation assumes infinite capital (size=np.inf) for percentage-based position sizing.
- Error handling logs individual rule failures but continues processing to maximize strategy discovery. 5th strategy to reduce verbosity during large backtests.
- The system handles freeze_date by filtering price data up to that date for deterministic testing.
- Vectorbt methods (win_rate, sharpe_ratio) are called as methods, not properties.
- NaN handling ensures metrics default to 0.0 when vectorbt calculations are not applicable.
- The backtester logs initialization parameters and final strategy count for debugging.
- Rule function lookup uses getattr with None default to detect missing rule implementations.

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
| `src/kiss_signal/backtester.py` | | Source code for the backtesting module using vectorbt library. | Git Repository |
| `src/kiss_signal/rules.py` | | Rule functions module containing technical indicator implementations. | Git Repository |
| `vectorbt` | | High-performance backtesting library for portfolio simulation. | PyPI |
| `numpy` | | Numerical computing library used for array operations. | PyPI |
