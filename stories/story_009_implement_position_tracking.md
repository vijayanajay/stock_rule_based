# Story 009: Implement Position Tracking and Lifecycle Management

## Status: 🔄 READY FOR DEVELOPMENT (REVISED)

**Priority:** HIGH  
**Estimated Story Points:** 8  
**Prerequisites:** Story 008 (Implement Reporting Module) ✅ Complete  
**Created:** 2025-06-23  
**Last Updated:** 2025-06-23 (Incorporated review feedback)

### Reviewer Comments (Kailash Nadh)
- **R-1 (No New Module):** All new logic will be housed in `persistence.py` and `reporter.py`. No new `position_manager.py` module will be created to keep the structure simple (H-4).
- **R-2 (Simplified Exit Logic):** This story will implement the time-based exit (`days_held >= hold_period`) **only**. The more complex "strategy change" exit condition is deferred to a future story to reduce complexity (H-3, H-9).
- **R-3 (Calculate Dynamic Data):** For `OPEN` positions, performance metrics (`return_%`, `nifty_%`, `days_held`) will be calculated on-the-fly in the reporter. These values will only be persisted in the database when a position is `CLOSED` (H-3).
- **R-4 (No Feature Flag):** The `position_tracking_enabled` flag has been removed. The feature will be implemented directly without a conditional configuration flag (H-3, H-4).
- **R-5 (Refined Persistence API):** The `persistence.py` API will be focused on data I/O. Business logic for determining which positions to close will reside in `reporter.py` (H-4).
- **R-6 (NIFTY Data Handling):** NIFTY 50 index data will be fetched and cached via a new function in `data.py` to keep the core reporting logic offline-safe (H-21).

## User Story
As a technical trader, I want the system to track open positions (entry → holding → exit) and automatically identify when positions should be sold based on holding period limits, so that I can see my complete portfolio status and follow disciplined exit rules in my daily reports.

## Context & Rationale
The current system generates new buy signals but doesn't track what happens after purchase. According to the PRD, the system needs complete position lifecycle management with a default 20-day holding period. This is crucial for risk management and portfolio discipline.

**Current State:**
- ✅ Signal generation working (finds new BUY opportunities)
- ✅ Database persistence for strategies and runs
- ✅ Daily markdown reports with NEW BUYS section
- ❌ **Missing:** `positions` table in database
- ❌ **Missing:** Trade lifecycle management (entry → exit)
- ❌ **Missing:** OPEN POSITIONS report section with real data
- ❌ **Missing:** POSITIONS TO SELL report section with real data

**Architecture Requirements from PRD:**
- Track position lifecycle: entry → holding → exit conditions
- Default 20-day holding period
- Calculate position returns vs NIFTY benchmark for alpha measurement
- Include OPEN POSITIONS and POSITIONS TO SELL sections in daily reports
- Persist trade events in SQLite for full audit trail

## Problem Analysis

### Business Requirements (PRD)
- **Position Lifecycle:** "Track position lifecycle (entry → holding → exit conditions)"
- **Holding Period:** "Default 20-day holding period"
- **Alpha Tracking:** "For a trade to be considered successful, its backtested return must be greater than the return of the NIFTY 50 index over the identical holding period"
- **Exit Conditions:** Automatic exit after `hold_period` days.
- **Portfolio View:** Clear view of all open positions with current performance

### Technical Requirements
- **Database Schema:** Add `positions` table to track individual trade lifecycles.
- **Position States:** `OPEN`, `CLOSED`.
- **Entry Tracking:** Record new positions when buy signals are generated.
- **Exit Logic:** Identify positions that should be closed based on the time-based `hold_period`.
- **Performance Calculation:** Calculate position returns and compare vs NIFTY.
- **Report Integration:** Populate OPEN POSITIONS and POSITIONS TO SELL sections.

## Acceptance Criteria

### ✅ Database Schema Enhancement
- [ ] **AC-1:** Add `positions` table to the SQLite schema in `persistence.py` with these columns:
  - `id` (INTEGER PRIMARY KEY)
  - `symbol` (TEXT NOT NULL)
  - `entry_date` (TEXT NOT NULL)
  - `entry_price` (REAL NOT NULL)
  - `exit_date` (TEXT, nullable)
  - `exit_price` (REAL, nullable)
  - `status` (TEXT NOT NULL, 'OPEN' or 'CLOSED')
  - `rule_stack_used` (TEXT NOT NULL, JSON of the strategy definition)
  - `final_return_pct` (REAL, nullable, stored only on close)
  - `final_nifty_return_pct` (REAL, nullable, stored only on close)
  - `days_held` (INTEGER, nullable, stored only on close)
  - `created_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

### ✅ Position Entry Logic
- [ ] **AC-2:** Create `add_positions_batch()` in `persistence.py` that:
  - Records new positions from a list of new buy signals.
  - Sets status to 'OPEN'.
  - Records entry date, price, and the full strategy definition used.
  - Prevents adding a new position for a symbol that already has an `OPEN` position.

### ✅ Position Exit Logic  
- [ ] **AC-3:** Implement position exit detection in `reporter.py`:
  - Fetch all `OPEN` positions from the database.
  - For each position, identify if `(today - entry_date).days >= config.hold_period`.
  - Positions meeting this condition are marked for the "POSITIONS TO SELL" report section.

### ✅ Performance Calculation
- [ ] **AC-4:** Implement performance calculation logic in `reporter.py`:
  - For each `OPEN` position, calculate the current return: `(current_price - entry_price) / entry_price`.
  - Fetch NIFTY 50 data for the same period (via `data.py`) and calculate the benchmark return.
  - These calculated values are used for the report but **not** saved back to the DB for open positions.

### ✅ Report Integration
- [ ] **AC-5:** Update `generate_daily_report()` in `reporter.py` to populate:
  - **OPEN POSITIONS table** with: Ticker | Entry Date | Entry Price | Current Price | Return % | NIFTY Period Return % | Day in Trade
  - **POSITIONS TO SELL table** with: Ticker | Status | Reason (e.g., "Time limit: 20 days held")
  - Update the report's summary line with accurate counts.

### ✅ Configuration Support
- [ ] **AC-6:** The existing `hold_period: 20` in `config.yaml` will be used to drive the time-based exit logic. No new configuration is needed.

### ✅ Integration & Testing
- [ ] **AC-7:** The end-to-end workflow is tested:
  - Run analysis → generate signals → add new positions to DB → update reports with open/sell positions.
  - Test the full lifecycle of a position from entry through a time-based exit.
  - Verify database integrity and report accuracy.

## Detailed Implementation Tasks

### Task 1: Database Schema Update
- **File:** `src/kiss_signal/persistence.py`
- **Action:** Add the `CREATE TABLE IF NOT EXISTS positions (...)` SQL statement to the `create_database` function. Add an index on `(symbol, status)`.
```sql
-- Add to persistence.create_database()
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_date TEXT,
    exit_price REAL,
    status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
    rule_stack_used TEXT NOT NULL,
    final_return_pct REAL,
    final_nifty_return_pct REAL,
    days_held INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_positions_status_symbol ON positions(status, symbol);
```

### Task 2: Persistence Layer Functions
- **File:** `src/kiss_signal/persistence.py`
- **Action:** Implement the following functions:
  - `add_positions_batch(db_path, new_signals)`: Adds new signals to the `positions` table with `status='OPEN'`. Must be transactional.
  - `get_open_positions(db_path)`: Fetches all records from the `positions` table where `status='OPEN'`.
  - `update_closed_positions_batch(db_path, closed_positions)`: Updates records to `status='CLOSED'` and populates final metrics (`exit_date`, `exit_price`, `final_return_pct`, etc.).

### Task 3: NIFTY Data Fetching
- **File:** `src/kiss_signal/data.py`
- **Action:** Add a new function `get_nifty_data(start_date, end_date, cache_dir)` that fetches and caches NIFTY 50 index data (`^NSEI`) for a given date range. This keeps network I/O isolated.

### Task 4: Reporter Module Logic
- **File:** `src/kiss_signal/reporter.py`
- **Action:** This is the core of the story.
  1.  In `generate_daily_report`, first call `_identify_new_signals` as before.
  2.  Call `persistence.add_positions_batch` to save these new signals as `OPEN` positions.
  3.  Call `persistence.get_open_positions` to get a list of all currently open positions.
  4.  Create two lists: `positions_to_hold` and `positions_to_close`.
  5.  Iterate through open positions:
      - Fetch current price and NIFTY data for the holding period.
      - Calculate `days_held`, `current_return_pct`, and `nifty_return_pct`.
      - If `days_held >= config.hold_period`, add it to `positions_to_close` with the reason.
      - Otherwise, add it to `positions_to_hold`.
  6.  Call `persistence.update_closed_positions_batch` to update the status of closed positions in the DB.
  7.  Use the `positions_to_hold` and `positions_to_close` lists to generate the `OPEN POSITIONS` and `POSITIONS TO SELL` tables in the markdown report.

### Task 5: Testing
- **File:** `tests/test_reporter.py`, `tests/test_persistence.py`
- **Action:**
  - Add tests for the new `positions` table schema and persistence functions.
  - Add tests for the NIFTY data fetching function in `test_data.py`.
  - Heavily test the logic in `reporter.py`:
    - Test that new signals become open positions.
    - Test that open positions appear correctly in the report.
    - Test that a position held for longer than `hold_period` is correctly identified for selling.
    - Test the on-the-fly performance calculations.

## Technical Considerations

### Database Design
- The `positions` table is the single source of truth for the portfolio.
- Indexes on `(symbol, status)` will be critical for efficiently fetching open positions.

### Performance & Caching
- Caching NIFTY data is essential to avoid hitting the `yfinance` API for every open position, every day.
- Batching database writes (`add_positions_batch`, `update_closed_positions_batch`) is crucial for performance.

### Error Handling
- Gracefully handle failures in fetching NIFTY data (e.g., log a warning and show "N/A" in the report for the benchmark return).
- All database operations must be transactional to prevent data corruption.

## Directory Structure Impact

This story will primarily modify existing modules to incorporate position tracking logic, keeping the project structure lean.

- **`src/kiss_signal/persistence.py`**: **MODIFIED**
  - Add `positions` table to `create_database()`.
  - Implement `add_positions_batch()`, `get_open_positions()`, `update_closed_positions_batch()`.

- **`src/kiss_signal/reporter.py`**: **MODIFIED**
  - Add logic to fetch open positions, calculate performance, and identify positions to close.
  - Update report generation to populate all three tables (`NEW BUYS`, `OPEN POSITIONS`, `POSITIONS TO SELL`).

- **`src/kiss_signal/data.py`**: **MODIFIED**
  - Add `get_nifty_data()` to fetch and cache NIFTY 50 index data, keeping network I/O isolated.

- **`src/kiss_signal/cli.py`**: **MODIFIED**
  - Update the `run` command to orchestrate the new position tracking and reporting steps.

- **`tests/test_persistence.py`**: **MODIFIED**
  - Add tests for the new `positions` table and its related functions.

- **`tests/test_reporter.py`**: **MODIFIED**
  - Add tests for the complete reporting lifecycle, including open and closed positions.

- **`docs/architecture.md`**: **MODIFIED**
  - Update the database schema section to include the new `positions` table.

## Out of Scope (Future Stories)

This story is strictly focused on implementing basic position tracking with a time-based exit. The following related features are explicitly out of scope and will be handled in subsequent stories:

- **Advanced Exit Strategies:** Implementing exit conditions based on strategy signal changes, stop-losses, or trailing stops.
- **Portfolio-level Analytics:** Calculating and reporting on total portfolio value, overall risk metrics, or diversification.
- **Position Sizing:** The system will continue to assume a fixed, notional amount per trade. Volatility-based or risk-parity position sizing is a future enhancement.
- **Tax-lot Accounting:** No tracking of cost basis for tax purposes.
- **Brokerage Integration:** No direct interaction with any brokerage APIs.

## Definition of Done
- [ ] All acceptance criteria implemented and tested.
- [ ] The `positions` table is added to the database schema correctly.
- [ ] The CLI workflow correctly identifies new signals, adds them as open positions, and updates the daily report to show all open and to-be-sold positions.
- [ ] The time-based exit logic (`hold_period`) is working correctly.
- [ ] Test coverage for new logic in `persistence.py` and `reporter.py` is ≥ 85%.
- [ ] All existing tests continue to pass.
- [ ] MyPy strict mode passes with no errors.
- [ ] The implementation adheres to all project hard rules.
- [ ] The architecture documentation is updated to reflect the new `positions` table and logic.

## Next Set of Stories (Roadmap)

### Story 010: Implement Advanced Exit Strategies  
**Priority:** MEDIUM | **Points:** 5  
**Goal:** Add configurable exit conditions beyond time-based exits, such as when the entry strategy no longer signals a buy, or a basic stop-loss is hit. This makes the exit logic more sophisticated and risk-aware.

### Story 011: Add Portfolio Analytics and Risk Metrics
**Priority:** MEDIUM | **Points:** 6  
**Goal:** Implement portfolio-level reporting: total portfolio value, diversification metrics, risk exposure, drawdown analysis, and overall performance vs benchmark.

### Story 012: Implement Position Sizing Strategy
**Priority:** LOW | **Points:** 4  
**Goal:** Add intelligent position sizing based on volatility (e.g., ATR-based) or portfolio allocation rules, rather than assuming a fixed amount per trade.

### Story 013: Add Trade Journal and Historical Analysis
**Priority:** LOW | **Points:** 5  
**Goal:** Create a comprehensive trade journal with detailed historical analysis, strategy performance over time, and learning insights for strategy refinement.