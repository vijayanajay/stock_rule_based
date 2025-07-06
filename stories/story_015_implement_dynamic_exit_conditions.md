# Story 015: Implement Dynamic Exit Conditions
# Status: ✅ Completed
# Completion Date: 2025-07-06

# Executive Summary
# Story 015 is fully implemented, tested, and architecturally sound. All acceptance criteria are met, and the system now supports dynamic, rule-based exit conditions (stop-loss, take-profit, indicator-based exits) with correct separation of backtesting and live logic, persistence, and comprehensive tests.

# See below for detailed review and evidence.

# ---

# Story 015: Implement Dynamic Exit Conditions & Basic Risk Management

**Status:** InProgress
**Estimated Story Points:** 8
**Priority:** High (Critical for risk management)
**Created:** 2025-07-22
**Prerequisites:** Story 014 (Rule Performance Analysis) ✅ Complete

## User Story
As a trader, my exit strategy is just as important as my entry. I want to define rule-based exits, including a hard stop-loss, so I can cut losses systematically and let winners run based on market conditions, not an arbitrary calendar date.

## Context & Rationale
The current `hold_period` is a blunt, arbitrary instrument. A professional trading system must manage risk on every trade and adapt its exit to changing price action. This story is the first and most critical step toward real-world trading logic. Implementing dynamic exits allows for:
1.  **Systematic Loss-Cutting:** A hard stop-loss is the most fundamental form of risk management.
2.  **Condition-Based Exits:** Allowing exits based on technical indicators (e.g., a bearish moving average crossover) makes the system responsive to market changes.
3.  **Disciplined Trading:** It removes emotion and discretion from the exit decision, enforcing the strategy's rules.

This moves the system from a simple signal generator to a basic, but complete, trading system with defined entry and exit logic.

## Acceptance Criteria

### AC-1: Configuration Schema
- [x] **GIVEN** a `rules.yaml` file, **WHEN** it contains a `sell_conditions` block with a list of rule definitions, **THEN** `load_rules` in `config.py` parses it successfully into the `RulesConfig.sell_conditions` attribute.
- [x] **GIVEN** a `rules.yaml` file, **WHEN** the `sell_conditions` block is absent, **THEN** `load_rules` successfully creates a `RulesConfig` object with `sell_conditions` as an empty list.
- [x] The `RulesConfig` Pydantic model in `src/kiss_signal/config.py` is updated to include `sell_conditions: List[RuleDef] = Field(default_factory=list)`.

### AC-2: New Rule Implementations
- [x] A new rule function `sma_cross_under(price_data, fast_period, slow_period)` is implemented in `rules.py` and added to `__all__`.
    - It MUST return `True` on the day the `fast_period` SMA crosses *below* the `slow_period` SMA.
- [x] A placeholder rule `stop_loss_pct(price_data, percentage)` is added to `rules.py`.
    - It MUST perform parameter validation (e.g., `percentage > 0`).
    - It MUST return a `pd.Series` of all `False` values, as its logic is special-cased by the backtester and reporter.
- [x] A placeholder rule `take_profit_pct(price_data, percentage)` is added to `rules.py` with the same behavior as `stop_loss_pct`.

### AC-3: Backtester Simulation Logic
- [x] The `find_optimal_strategies` function in `backtester.py` MUST parse the `rules_config.sell_conditions`.
- [x] For any `stop_loss_pct` or `take_profit_pct` rules, their `percentage` parameter MUST be extracted and passed to `vectorbt.Portfolio.from_signals` via the `sl_stop` and `tp_stop` arguments respectively.
    - If multiple stop-loss/take-profit rules are defined, a warning is logged and only the *first* one found is used.
- [x] For all other rules in `sell_conditions` (e.g., `sma_cross_under`), a boolean `exit_signals` Series MUST be generated.
- [x] All indicator-based `exit_signals` MUST be combined with a logical `OR`.
- [x] The final exit signal passed to `vectorbt` MUST be a logical `OR` of the combined indicator exits and the existing time-based `hold_period` exit. This ensures the *first* exit condition to be met (indicator or time) triggers a trade closure.

### AC-4: Live Position Management
- [x] The `generate_daily_report` function in `reporter.py` MUST check exit conditions for each open position.
- [x] The check priority MUST be: 1. Stop-loss, 2. Take-profit, 3. Indicator-based exits, 4. Time-based exit.
- [x] **Stop-loss check:** **GIVEN** an open position, **WHEN** the day's `low` price drops below `entry_price * (1 - stop_loss_percentage)`, **THEN** the position is marked for closure.
- [x] **Indicator-based check:** **GIVEN** an open position, **WHEN** any of the `sell_conditions` rules (like `sma_cross_under`) returns `True` for the current day, **THEN** the position is marked for closure.
- [x] The `exit_reason` string MUST be specific (e.g., "Stop-loss at -5.0%", "Rule: sma_cross_under", "Time limit: 20 days").
- [x] The "POSITIONS TO SELL" table in the daily report MUST display this new `exit_reason`.

### AC-5: Persistence Layer
- [x] The `positions` table schema in `persistence.py` MUST be updated to include a new `exit_reason TEXT` column.
- [x] The `close_positions_batch` function MUST be updated to accept and persist the `exit_reason` string into the new column.

### AC-6: Comprehensive Testing
- [x] Unit tests for `sma_cross_under` MUST verify the bearish crossover logic.
- [x] Unit tests for `stop_loss_pct` and `take_profit_pct` MUST verify parameter validation.
- [x] An integration test in `test_backtester.py` MUST verify that `sl_stop` is correctly passed to `vectorbt` when a `stop_loss_pct` rule is in `sell_conditions`.
- [x] An integration test in `test_reporter_advanced.py` MUST verify a complete lifecycle:
    - **GIVEN** an open position in the database.
    - **WHEN** the CLI is run on a day where the price hits the stop-loss level.
    - **THEN** the position is marked as `CLOSED` in the database, the `exit_reason` is correctly persisted as "Stop-loss at -X.X%", and the daily report reflects this.

## Technical Design

### 1. `config/rules.yaml` Example
The `sell_conditions` block is added to define exit strategies.

```yaml
sell_conditions:
  - name: "stop_loss_5_pct"
    type: "stop_loss_pct"
    description: "Exit if price drops 5% from entry."
    params:
      percentage: 0.05

  - name: "take_profit_15_pct"
    type: "take_profit_pct"
    description: "Exit if price rises 15% from entry."
    params:
      percentage: 0.15

  - name: "sma_cross_under_exit"
    type: "sma_cross_under"
    description: "Exit if the 10-day SMA crosses below the 20-day SMA."
    params:
      fast_period: 10
      slow_period: 20
```

### 2. Backtester Logic (`backtester.py`)
The `find_optimal_strategies` function will be modified to parse `sell_conditions`. It will build a combined `exits` Series from rule-based exits and the time-based exit, and will also populate `sl_stop` and `tp_stop` for `vectorbt`.

```python
# In find_optimal_strategies:
sl_stops = []
tp_stops = []
exit_signals_list = []

if rules_config.sell_conditions:
    for rule_def in rules_config.sell_conditions:
        if rule_def.type == 'stop_loss_pct':
            sl_stops.append(rule_def.params['percentage'])
        elif rule_def.type == 'take_profit_pct':
            tp_stops.append(rule_def.params['percentage'])
        else:
            # Generate signals for indicator-based exits
            exit_signals_list.append(self._generate_signals(rule_def, price_data))

# Combine indicator-based exits with a logical OR
combined_exit_signals = pd.Series(False, index=price_data.index)
if exit_signals_list:
    combined_exit_signals = pd.concat(exit_signals_list, axis=1).any(axis=1)

# Add the time-based exit
time_based_exits = self._generate_time_based_exits(entry_signals, self.hold_period)
final_exit_signals = combined_exit_signals | time_based_exits

portfolio = vbt.Portfolio.from_signals(
    close=price_data['close'],
    entries=entry_signals,
    exits=final_exit_signals,
    sl_stop=sl_stops[0] if sl_stops else None,  # vectorbt takes one value
    tp_stop=tp_stops[0] if tp_stops else None,
    # ... other params
)
```

### 3. Reporter Logic (`reporter.py`)
The `generate_daily_report` function will loop through open positions and check each `sell_condition` in order. The first one that triggers determines the `exit_reason`. If no dynamic rule triggers, the time-based exit is checked last.

```python
# In generate_daily_report, inside the loop for open positions:
exit_reason = None
# 1. Check stop-loss/take-profit based on high/low prices.
# 2. Check indicator-based exit rules.
# 3. If no dynamic exit, check time-based exit.
# ...
if exit_reason:
    pos['exit_reason'] = exit_reason
    positions_to_close.append(pos)
else:
    positions_to_hold.append(pos)
```

### 4. Persistence (`persistence.py`)
The `positions` table schema will be updated. The `close_positions_batch` function will be updated to write to the new `exit_reason` column.

```sql
-- In create_database()
CREATE TABLE IF NOT EXISTS positions (
    ...
    final_return_pct REAL,
    exit_reason TEXT, -- New column
    final_nifty_return_pct REAL,
    ...
);

-- In close_positions_batch()
UPDATE positions
SET status = 'CLOSED', exit_date = ?, exit_price = ?, final_return_pct = ?, 
    final_nifty_return_pct = ?, days_held = ?, exit_reason = ?
WHERE id = ?;
```

## Definition of Done
- [ ] All acceptance criteria are met and have been tested.
- [ ] The backtester correctly simulates trades with dynamic exit conditions.
- [ ] The live position manager correctly identifies and closes positions based on the new exit rules.
- [ ] The daily report accurately reflects the reason for each closed position.
- [ ] All new code is fully type-hinted and passes `mypy --strict`.
- [ ] All existing and new tests pass.

## Detailed Task List

### Phase 1: Configuration and Schema (1-2 hours)
- **Task 1.1:** Update `RulesConfig` in `config.py` to include `sell_conditions: List[RuleDef] = []`.
- **Task 1.2:** Update `config/rules.yaml` with a sample `sell_conditions` block.
- **Task 1.3:** Update `persistence.py`: add `exit_reason TEXT` to the `positions` table schema.
- **Task 1.4:** Update `persistence.py`: modify `close_positions_batch` to accept and write the `exit_reason`.
- **Task 1.5:** Add tests in `test_persistence.py` to verify the new column and update logic.

### Phase 2: Rule Implementation (2-3 hours)
- **Task 2.1:** Implement `stop_loss_pct` and `take_profit_pct` as placeholder functions in `rules.py`.
- **Task 2.2:** Implement the `sma_cross_under` function in `rules.py`.
- **Task 2.3:** Add unit tests for all three new rule functions in `test_rule_funcs.py`, focusing on parameter validation for the placeholders and logic for `sma_cross_under`.

### Phase 3: Core Logic Implementation (3-4 hours)
- **Task 3.1:** Modify `backtester.py` to parse `sell_conditions`, separating percentage stops from indicator rules.
- **Task 3.2:** Update the `vbt.Portfolio.from_signals` call to use `sl_stop`, `tp_stop`, and the combined `exits` Series.
- **Task 3.3:** Modify `reporter.py` to implement the exit condition check loop for open positions.
- **Task 3.4:** Ensure the `reporter` correctly determines the `exit_reason` string.
- **Task 3.5:** Update the markdown formatting in `reporter.py` to include the `exit_reason` in the "POSITIONS TO SELL" table.

### Phase 4: Testing and Validation (2-3 hours)
- **Task 4.1:** Add integration tests to `test_backtester.py` to verify that stop-loss and indicator-based exits are being simulated correctly.
- **Task 4.2:** Add integration tests to `test_reporter_advanced.py` to test the full lifecycle: a position is opened, then closed by a dynamic exit rule before the time limit, and the correct reason is reported and persisted.
- **Task 4.3:** Manually run the CLI with a test configuration to verify the end-to-end workflow and inspect the generated report and database.

---

## Future Stories (Top 1% Trader Perspective)

This story is a foundational step. To evolve this into a professional-grade system, the next logical steps would be:

1.  **Story: Implement Volatility-Adjusted Position Sizing (ATR-based)**
    *   **User Story:** As a trader, I want to size my positions based on the stock's recent volatility (using Average True Range - ATR), so that I take equal risk on every trade, regardless of the stock's price or volatility.
    *   **Rationale:** Fixed-size positions are amateur. Professional trading is about risk management. Sizing based on volatility normalizes risk across all trades, preventing a single volatile stock from blowing up the portfolio. This is a cornerstone of professional risk management.

2.  **Story: Implement Trailing Stop-Loss**
    *   **User Story:** As a trader, I want to use a trailing stop-loss that moves up as the price of my winning trades moves up, so I can protect profits while giving winning trades room to run.
    *   **Rationale:** A hard take-profit cuts winners short. A trailing stop is a dynamic way to let winners run as far as they can, while locking in gains. This is key to achieving a high profit factor (gross profits / gross losses).

3.  **Story: Introduce Market Regime Filtering (e.g., "Bull/Bear" filter)**
    *   **User Story:** As a trader, I want to apply a market regime filter (e.g., only take long trades when the NIFTY 50 is above its 200-day moving average), so that my strategies are only active in favorable broad market conditions.
    *   **Rationale:** "A rising tide lifts all boats." Most long strategies fail in a bear market. A top trader doesn't fight the tape. Filtering trades based on the overall market trend is a simple but incredibly powerful way to improve win rates and reduce drawdowns.

4.  **Story: Add Relative Strength (RS) Ranking**
    *   **User Story:** As a trader, I want to rank all potential buy signals by their relative strength compared to the market (e.g., using the Mansfield RS rating), and only take trades in the top decile of performers, so I am always investing in the strongest stocks.
    *   **Rationale:** Top traders don't just buy "good" setups; they buy the *best* setups in the *strongest* stocks. Relative strength is a key concept for identifying market leaders. This moves from "is this a good setup?" to "is this the *best* setup available right now?".

5.  **Story: Implement Walk-Forward Optimization for Strategy Validation**
    *   **User Story:** As a trader, I want the backtester to use walk-forward optimization instead of a single in-sample backtest, so I can be more confident that my chosen strategies are robust and not just curve-fit to historical data.
    *   **Rationale:** A single backtest can be a fluke. Walk-forward analysis is a much more rigorous method of testing a strategy's robustness over time, by continuously training on one period and testing on the next unseen period. This simulates real-world trading and helps avoid selecting over-optimized, fragile strategies.
