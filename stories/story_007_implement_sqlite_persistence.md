# Story 007: Implement SQLite Persistence Layer

## Status: 📝 READY FOR DEVELOPMENT (REVISED)

**Priority:** HIGH  
**Estimated Story Points:** 3 (Revised from 5)  
**Prerequisites:** Story 005 (Implement Backtesting Engine) ✅ Complete  
**Created:** 2025-06-21  
**Revised:** 2025-06-24

## User Story
As a technical trader, I want all backtesting results and trading signals to be persistently stored in a local SQLite database so that I can maintain a complete historical record of all recommendations and their performance outcomes.

## Context & Rationale
This story implements the persistence layer that stores backtesting results in SQLite, as explicitly required by the PRD: "All trade signals are persisted in a local SQLite database, ensuring a full and transparent history of every recommendation."

**Current State:**
- ✅ Data layer complete (Stories 002-004)
- ✅ Rule functions complete (Story 003)  
- ✅ Backtesting engine complete, producing a `List[Dict[str, Any]]` of ranked strategies.
- ✅ CLI pipeline functional but results only displayed in console
- ❌ No persistence layer - `persistence.py` is empty
- ❌ No historical tracking of recommendations and outcomes

**Architecture Impact:**
- Completes core workflow: Data → Strategy Discovery → Signal Generation → **Persistence** → Reporting
- Enables future historical analysis and performance tracking
- Provides foundation for upcoming reporting module (Story 008)
- Maintains single source of truth for all trading recommendations

## Problem Analysis

### Business Requirements (PRD)
- **SQLite Database:** "single-file SQLite database for all persistence" 
- **Signal History:** "full and transparent history of every recommendation"
- **Performance Tracking:** Enable analysis of recommendation outcomes over time
- **WAL Mode:** Architecture specifies "sqlite3 stdlib (WAL mode)" for concurrent access

### Technical Requirements
- Store the strategy result dictionaries produced by the `backtester` module.
- Support efficient queries for reporting and analysis.  
- Handle database schema creation and migration.
- Integrate seamlessly with existing CLI workflow.
- Follow KISS principles: simple, focused, minimal LOC.

### Current Integration Points
- **Input:** `List[Dict[str, Any]]` from `backtester.find_optimal_strategies()`
- **CLI Integration:** Results from `_run_backtests()` in `cli.py`
- **Future Consumer:** Reporting module will query historical data

## Acceptance Criteria

### Core Functionality
- **AC1:** `create_database()` function creates SQLite database with proper schema.
  - AC1.1: Creates `strategies` table with columns matching the backtester's output dictionary.
  - AC1.2: Enables WAL mode for concurrent access as per architecture.
  - AC1.3: Handles database file creation in the location specified in `config.yaml`.
  - AC1.4: Includes proper indexing for future query performance.

- **AC2:** `save_strategies_batch()` function efficiently stores multiple strategy results.
  - AC2.1: Accepts `List[Dict[str, Any]]` and stores all relevant fields.
  - AC2.2: Uses a transaction for atomicity (all or nothing).
  - AC2.3: Includes a `run_timestamp` for historical tracking.
  - AC2.4: Handles `rule_stack` list serialization to a JSON string.
  - AC2.5: Logs persistence activity and handles errors with transaction rollback.

### Integration & Quality
- **AC3:** CLI integration stores results automatically after a successful run.
  - AC3.1: `cli.py` calls persistence functions after backtesting is complete.
  - AC3.2: Database location is read from the main `Config` object.
  - AC3.3: Graceful handling of persistence failures (log but do not crash the CLI).

- **AC4:** Error handling and edge cases are covered.
  - AC4.1: Database file permissions issues are handled gracefully.
  - AC4.2: Concurrent access is handled correctly with WAL mode.

- **AC5:** Test coverage and code quality standards are met.
  - AC5.1: ≥90% test coverage on the `persistence.py` module.
  - AC5.2: Each function has comprehensive unit tests using an isolated in-memory database.
  - AC5.3: MyPy strict mode compliance with full type hints.
  - AC5.4: All code adheres to the project's hard rules.

## Technical Design

### Database Schema (Simplified)
This schema directly maps to the output of `backtester.find_optimal_strategies`.

```sql
-- Stores the best strategies found for each symbol in a given run.
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,           -- ISO 8601 timestamp of the analysis run
    symbol TEXT NOT NULL,                  -- Stock symbol (e.g., 'RELIANCE')
    rule_stack TEXT NOT NULL,              -- JSON array of rule names (e.g., '["sma_10_20_crossover"]')
    edge_score REAL NOT NULL,              -- The calculated edge score for the strategy
    win_pct REAL NOT NULL,                 -- Win percentage from the backtest
    sharpe REAL NOT NULL,                  -- Sharpe ratio from the backtest
    total_trades INTEGER NOT NULL,         -- Total trades in the backtest period
    avg_return REAL NOT NULL,              -- Average return per trade
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_strategies_symbol_timestamp ON strategies(symbol, run_timestamp);
```

### Core Functions (`src/kiss_signal/persistence.py`)
The API is minimal, focusing only on what is needed now.

```python
# src/kiss_signal/persistence.py
from pathlib import Path
from typing import List, Dict, Any
import sqlite3
import json
import logging

__all__ = ["create_database", "save_strategies_batch"]

logger = logging.getLogger(__name__)

# impure
def create_database(db_path: Path) -> None:
    """Create SQLite database with the strategies schema and enables WAL mode."""

# impure
def save_strategies_batch(db_path: Path, strategies: List[Dict[str, Any]], run_timestamp: str) -> bool:
    """Save a batch of strategy results in a single transaction."""
```

### Configuration Integration
A simple, top-level key will be added to `config.yaml` and the `Config` model.

**`config.yaml` addition:**
```yaml
# ... existing configuration ...

# Path to the SQLite database file
database_path: "data/kiss_signal.db"
```

**`src/kiss_signal/config.py` addition:**
```python
class Config(BaseModel):
    # ... existing fields ...
    database_path: str = Field(default="data/kiss_signal.db")
```

## Implementation Plan

### Files to Create/Modify
1.  **`src/kiss_signal/persistence.py`** (new implementation, ~80 LOC)
    - Implement `create_database` and `save_strategies_batch`.
2.  **`src/kiss_signal/config.py`** (minimal addition, +1 LOC)
    - Add `database_path` field to the `Config` model.
3.  **`src/kiss_signal/cli.py`** (minimal addition, ~15 LOC)
    - Add calls to `create_database` and `save_strategies_batch` in the `run` command.
4.  **`tests/test_persistence.py`** (new file, ~100 LOC)
    - Comprehensive tests for the two public functions.
5.  **`config.yaml`** (minimal addition, +2 lines)
    - Add the `database_path` key.

### Development Approach
- **Start with schema:** Define and test database creation first.
- **Implement batch save:** Create the `save_strategies_batch` function.
- **Test isolation:** Each test uses a temporary or in-memory database file.
- **Integration last:** Add CLI integration after core functions are tested and working.
- **Follow hard rules:** Explicit paths, proper error handling, no silent failures.

## Risk Analysis & Mitigation

### Technical Risks
- **Database corruption:** Mitigated by WAL mode and using atomic transactions for batch writes.
- **Performance with large datasets:** Mitigated by proper indexing and batch operations.
- **Schema Evolution:** Not in scope. The current schema is simple. Future changes will require a separate migration story.

### Business Risks  
- **Data loss:** Mitigated by atomic transactions and proper error handling.
- **CLI workflow disruption:** Mitigated by graceful failure handling (log errors but continue without crashing).

## Definition of Done Checklist

- [ ] All acceptance criteria are met and have been tested.
- [ ] `persistence.py` module is implemented with full functionality.
- [ ] Database schema is created and documented.  
- [ ] CLI integration is working without disrupting the existing workflow.
- [ ] Configuration is updated to support the database location.
- [ ] A comprehensive test suite with ≥90% coverage is implemented.
- [ ] All tests are passing, including integration tests.
- [ ] MyPy strict mode compliance is achieved.
- [ ] Performance is acceptable for expected data volumes.
- [ ] Error handling covers edge cases like file permissions.
- [ ] Documentation is updated for persistence functions.
- [ ] Manual testing of the full CLI workflow with persistence is complete.
- [ ] Code review is completed, focusing on adherence to hard rules.

## Validation Approach

### Unit Testing
- Database creation and schema validation.
- Batch save operations with mocked data.  
- Error handling for database connection and transaction failures.
- Performance testing for batch operations.

### Integration Testing  
- End-to-end workflow: backtesting → persistence.
- CLI integration with real configuration files.
- Concurrent access simulation with WAL mode.

### Manual Validation
- Run `python run.py run` and verify database file creation.
- Inspect database contents with an SQLite browser to confirm data integrity.
- Verify results persist across multiple CLI runs.
- Test behavior with a missing/corrupted database file.

---

**Ready for Development:** This story is fully specified and ready for implementation. All dependencies are satisfied and acceptance criteria are clearly defined.

---

## Detailed Task Breakdown

### Phase 1: Database Schema & Core Functions (2 Tasks)

#### Task 1.1: Implement Database Schema Creation
**File:** `src/kiss_signal/persistence.py`  
**Estimated LOC:** ~35  
**Dependencies:** None  

**Specific Requirements:**
- Create `create_database()` function that accepts an explicit `Path` object.
- Implement the SQL schema exactly as specified in the Technical Design section.
- Use `CREATE TABLE IF NOT EXISTS` for idempotency.
- Enable WAL mode using `PRAGMA journal_mode=WAL`.
- Use context managers for database connection handling to ensure it's closed properly.

**Antipattern Prevention:**
- ✅ Use explicit path handling; no magic file resolution.
- ✅ Catch specific `sqlite3` exceptions, not bare `except:`.
- ✅ Log all operations; no silent failures.

**Test Requirements:**
- Test that `create_database` works correctly in a temporary directory.
- Verify the created schema matches the expected structure (table name, columns, types).
- Test that WAL mode is successfully enabled on the connection.
- Test error handling for scenarios like directory permission issues.

---

#### Task 1.2: Implement Batch Save Operation
**File:** `src/kiss_signal/persistence.py`  
**Estimated LOC:** ~45  
**Dependencies:** Task 1.1 complete  

**Specific Requirements:**
- Implement `save_strategies_batch()` for persisting multiple results.
- The function must accept `List[Dict[str, Any]]` to match the backtester's output.
- Use a single transaction (`BEGIN`, `COMMIT`, `ROLLBACK`) for atomicity.
- Convert the `rule_stack` list within each dictionary to a JSON string for storage.
- Return a boolean indicating success or failure.
- Add comprehensive logging for debugging and monitoring.

**Transaction Pattern:**
```python
def save_strategies_batch(...) -> bool:
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        for strategy in strategies:
            # Prepare data and execute INSERT
            ...
        cursor.execute("COMMIT")
        return True
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Batch save failed: {e}")
        return False
    finally:
        if conn:
            conn.close()
```

**Test Requirements:**
- Test a successful batch save with multiple strategy dictionaries.
- Test the rollback behavior by forcing an error mid-transaction.
- Test performance improvement over simulated individual saves.
- Test handling of an empty list of strategies (should succeed with no changes).

---

### Phase 2: Configuration & CLI Integration (2 Tasks)

#### Task 2.1: Add Database Configuration Support
**Files:** `src/kiss_signal/config.py`, `config.yaml`  
**Estimated LOC:** ~5 total  
**Dependencies:** None (can be done in parallel)  

**`config.py` Changes:**
```python
class Config(BaseModel):
    # ...existing fields...
    database_path: str = Field(default="data/kiss_signal.db")
```

**`config.yaml` Addition:**
```yaml
# ... existing configuration ...

# Path to the SQLite database file
database_path: "data/kiss_signal.db"
```

**Test Requirements:**
- Update `test_config.py` to ensure the new `database_path` field is loaded and validated correctly.

---

#### Task 2.2: Integrate Persistence into CLI Workflow
**File:** `src/kiss_signal/cli.py`  
**Estimated LOC:** ~15  
**Dependencies:** Phase 1 complete  

**Specific Requirements:**
- In the `run` command, after `_run_backtests` successfully returns results:
    1. Get the `database_path` from the loaded `app_config`.
    2. Call `persistence.create_database()` to ensure the DB and table exist.
    3. Call `persistence.save_strategies_batch()` with the results.
    4. Add a new progress step to the console output, e.g., `[5/5] Saving results...`.
    5. Wrap persistence calls in a `try...except` block to handle failures gracefully.

**Test Requirements:**
- Update `test_cli.py` to mock the persistence functions.
- Verify that `create_database` and `save_strategies_batch` are called with the correct arguments after a successful backtest run.
- Test that the CLI does not crash if the mocked persistence functions raise an exception.

---

### Phase 3: Testing and Validation (1 Task)

#### Task 3.1: Create Comprehensive Persistence Test Suite
**File:** `tests/test_persistence.py`  
**Estimated LOC:** ~100  
**Dependencies:** Phase 1 complete  

**Specific Requirements:**
- Create a new test file `tests/test_persistence.py`.
- Use `pytest` fixtures to provide sample strategy data (`List[Dict[str, Any]]`).
- Use an in-memory SQLite database (`:memory:`) or a temporary file for test isolation.
- **Test `create_database`:**
    - Verify table and indexes are created correctly.
- **Test `save_strategies_batch`:**
    - Verify data is inserted correctly.
    - Verify `rule_stack` is stored as a valid JSON string.
    - Test transaction rollback on error.
- Achieve ≥90% test coverage for `src/kiss_signal/persistence.py`.

**Test Fixture Example:**
```python
@pytest.fixture
def sample_strategies() -> List[Dict[str, Any]]:
    return [
        {'symbol': 'RELIANCE', 'rule_stack': ['sma_crossover'], 'edge_score': 0.75, ...},
        {'symbol': 'INFY', 'rule_stack': ['rsi_oversold'], 'edge_score': 0.68, ...},
    ]
```