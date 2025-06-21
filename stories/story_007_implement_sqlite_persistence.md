# Story 007: Implement SQLite Persistence Layer

## Status: 📝 READY FOR DEVELOPMENT

**Priority:** HIGH  
**Estimated Story Points:** 5  
**Prerequisites:** Story 005 (Implement Backtesting Engine) ✅ Complete  
**Created:** 2025-06-21  

## User Story
As a technical trader, I want all backtesting results and trading signals to be persistently stored in a local SQLite database so that I can maintain a complete historical record of all recommendations and their performance outcomes.

## Context & Rationale
This story implements the persistence layer that stores backtesting results in SQLite, as explicitly required by the PRD: "All trade signals are persisted in a local SQLite database, ensuring a full and transparent history of every recommendation."

**Current State:**
- ✅ Data layer complete (Stories 002-004)
- ✅ Rule functions complete (Story 003)  
- ✅ Backtesting engine complete with `BacktestResult` dataclass (Story 005)
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
- Store `BacktestResult` objects from backtesting engine
- Support efficient queries for reporting and analysis  
- Handle database schema creation and migration
- Integrate seamlessly with existing CLI workflow
- Follow KISS principles: simple, focused, minimal LOC

### Current Integration Points
- **Input:** `BacktestResult` objects from `backtester.analyze_stock()`
- **CLI Integration:** Results from `_run_backtests()` in `cli.py`
- **Future Consumer:** Reporting module will query historical data

## Acceptance Criteria

### Core Functionality
- **AC1:** `create_database()` function creates SQLite database with proper schema
  - AC1.1: Creates `results` table with columns matching `BacktestResult` fields
  - AC1.2: Enables WAL mode for concurrent access as per architecture
  - AC1.3: Handles database file creation in configurable location
  - AC1.4: Includes proper indexing for query performance
  - AC1.5: Schema supports all `BacktestResult` fields with correct types

- **AC2:** `save_backtest_result()` function persists individual results
  - AC2.1: Accepts `BacktestResult` dataclass and stores all fields
  - AC2.2: Includes timestamp of analysis run for historical tracking
  - AC2.3: Handles duplicate symbol/date combinations gracefully
  - AC2.4: Returns success/failure status for error handling
  - AC2.5: Logs persistence activity for debugging

- **AC3:** `save_backtest_batch()` function efficiently stores multiple results
  - AC3.1: Accepts list of `BacktestResult` objects for batch processing
  - AC3.2: Uses transaction for atomicity (all or nothing)
  - AC3.3: Provides better performance than individual saves
  - AC3.4: Includes run metadata (analysis date, configuration used)
  - AC3.5: Proper error handling with rollback on failure

### Query & Retrieval
- **AC4:** `get_historical_results()` function retrieves stored data
  - AC4.1: Supports filtering by symbol, date range, rule combinations
  - AC4.2: Returns results in consistent format for reporting consumption
  - AC4.3: Handles empty result sets gracefully
  - AC4.4: Supports pagination for large datasets
  - AC4.5: Efficient query execution with proper indexing

- **AC5:** `get_latest_results()` function gets most recent analysis
  - AC5.1: Returns latest run results for all symbols
  - AC5.2: Handles case where no results exist
  - AC5.3: Supports filtering by symbol subset
  - AC5.4: Optimized query performance for common use case

### Integration & Quality
- **AC6:** CLI integration stores results automatically
  - AC6.1: `cli.py` calls persistence functions after backtesting
  - AC6.2: Database location configurable via `config.yaml`
  - AC6.3: Graceful handling of persistence failures (log but continue)
  - AC6.4: No impact on existing CLI behavior for non-persistence features
  - AC6.5: Progress indication for persistence operations

- **AC7:** Error handling and edge cases covered
  - AC7.1: Database file permissions issues handled gracefully
  - AC7.2: Disk space exhaustion handled with clear error messages
  - AC7.3: Database corruption detection and recovery guidance
  - AC7.4: Concurrent access handled correctly with WAL mode
  - AC7.5: Schema migration support for future enhancements

- **AC8:** Test coverage and code quality standards met
  - AC8.1: ≥85% test coverage on persistence module
  - AC8.2: Each function has comprehensive unit tests with isolated databases
  - AC8.3: Integration tests with real `BacktestResult` objects
  - AC8.4: MyPy strict mode compliance with full type hints
  - AC8.5: Performance tests for batch operations

## Technical Design

### Database Schema
```sql
-- Main results table storing all backtest outcomes
CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,           -- When analysis was performed
    symbol TEXT NOT NULL,                  -- NSE symbol (e.g., 'RELIANCE.NS')
    rule_stack TEXT NOT NULL,              -- JSON array of rules used
    total_signals INTEGER NOT NULL,        -- Number of buy signals generated
    profitable_signals INTEGER NOT NULL,   -- Number of profitable trades
    win_rate REAL NOT NULL,                -- Success percentage
    avg_return REAL NOT NULL,              -- Average return per trade
    total_return REAL NOT NULL,            -- Cumulative return
    max_drawdown REAL NOT NULL,            -- Maximum loss percentage
    sharpe_ratio REAL NOT NULL,            -- Risk-adjusted return
    edge_score REAL NOT NULL,              -- Combined performance metric
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX idx_results_symbol ON results(symbol);
CREATE INDEX idx_results_timestamp ON results(run_timestamp);
CREATE INDEX idx_results_edge_score ON results(edge_score DESC);
CREATE UNIQUE INDEX idx_results_unique ON results(symbol, run_timestamp);
```

### Core Functions
```python
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict
import sqlite3
import json
import logging
from datetime import datetime

from .backtester import BacktestResult

logger = logging.getLogger(__name__)

def create_database(db_path: Path) -> None:
    """Create SQLite database with proper schema and WAL mode."""

def save_backtest_result(db_path: Path, result: BacktestResult, 
                        run_timestamp: str) -> bool:
    """Save single backtest result to database."""

def save_backtest_batch(db_path: Path, results: List[BacktestResult], 
                       run_timestamp: str) -> bool:
    """Save multiple backtest results in single transaction."""

def get_historical_results(db_path: Path, symbol: Optional[str] = None,
                          days_back: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve historical results with optional filtering."""

def get_latest_results(db_path: Path, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Get most recent analysis results."""
```

### Configuration Integration
```yaml
# Addition to config.yaml
database:
  path: "data/kiss_signal.db"
  wal_mode: true
  backup_enabled: true
```

## Implementation Plan

### Files to Create/Modify
1. **`src/kiss_signal/persistence.py`** (new implementation, ~150 LOC)
   - Replace empty placeholder with full persistence implementation
   - All database operations and schema management

2. **`src/kiss_signal/config.py`** (minimal addition, ~5 LOC)
   - Add database configuration fields to `Config` class

3. **`src/kiss_signal/cli.py`** (minimal addition, ~10 LOC)  
   - Integrate persistence calls in `run()` function after backtesting
   - Add database location from config

4. **`tests/test_persistence.py`** (new file, ~200 LOC)
   - Comprehensive test suite with isolated database instances
   - Unit tests for all functions
   - Integration tests with real `BacktestResult` objects

5. **`config.yaml`** (minimal addition, ~3 lines)
   - Add database configuration section

### Development Approach
- **Start with schema:** Define and test database creation first
- **Build incrementally:** Implement save functions before query functions  
- **Test isolation:** Each test uses temporary database file
- **Integration last:** Add CLI integration after core functions work
- **Follow antipatterns guide:** Explicit paths, proper error handling, defensive coding

## Risk Analysis & Mitigation

### Technical Risks
- **Database corruption:** Mitigated by WAL mode and transaction usage
- **Performance with large datasets:** Mitigated by proper indexing and batch operations
- **Integration complexity:** Mitigated by minimal CLI changes and thorough testing

### Business Risks  
- **Data loss:** Mitigated by atomic transactions and proper error handling
- **CLI workflow disruption:** Mitigated by graceful failure handling (log errors but continue)

## Definition of Done Checklist

- [ ] All acceptance criteria verified and tested
- [ ] `persistence.py` module implemented with full functionality
- [ ] Database schema created and documented  
- [ ] CLI integration working without disrupting existing workflow
- [ ] Configuration updated to support database location
- [ ] Comprehensive test suite with ≥85% coverage
- [ ] All tests passing including integration tests
- [ ] MyPy strict mode compliance
- [ ] Performance acceptable for expected data volumes
- [ ] Error handling covers edge cases
- [ ] Documentation updated for persistence functions
- [ ] Manual testing of full CLI workflow with persistence
- [ ] Code review completed focusing on antipattern avoidance

## Validation Approach

### Unit Testing
- Database creation and schema validation
- Individual save/query operations with mocked data  
- Error handling for various failure scenarios
- Performance testing for batch operations

### Integration Testing  
- End-to-end workflow: backtesting → persistence → retrieval
- CLI integration with real configuration files
- Concurrent access simulation with WAL mode

### Manual Validation
- Run `quickedge run` and verify database file creation
- Inspect database contents with SQLite browser
- Verify results persist across multiple CLI runs
- Test behavior with missing/corrupted database file

---

**Ready for Development:** This story is fully specified and ready for implementation. All dependencies are satisfied and acceptance criteria are clearly defined. The implementation should follow KISS principles and avoid antipatterns documented in the memory bank.

---

## Detailed Task Breakdown

### Phase 1: Database Schema & Core Infrastructure (Tasks 1-3)

#### Task 1: Implement Database Schema Creation
**File:** `src/kiss_signal/persistence.py`  
**Estimated LOC:** ~40  
**Dependencies:** None  

**Specific Requirements:**
- Create `create_database()` function with explicit Path parameter
- Implement SQL schema exactly as specified in Technical Design
- Enable WAL mode: `PRAGMA journal_mode=WAL`
- Add all required indexes for query performance
- Handle database file creation with proper error messages
- Use context managers for connection handling

**Antipattern Prevention:**
- ✅ Explicit path handling - no magic file resolution
- ✅ Proper error handling - specific SQLite exceptions
- ✅ No silent failures - log all operations

**Test Requirements:**
- Test database creation in temporary directory
- Verify schema matches expected structure
- Test WAL mode is enabled
- Test proper error handling for permission issues

---

#### Task 2: Implement Basic Save Operations
**File:** `src/kiss_signal/persistence.py`  
**Estimated LOC:** ~50  
**Dependencies:** Task 1 complete  

**Specific Requirements:**
- Implement `save_backtest_result()` for single result persistence
- Convert `BacktestResult` dataclass to database row format
- Handle `rule_stack` list serialization to JSON
- Include run_timestamp parameter for historical tracking
- Return boolean success/failure status
- Add comprehensive logging for debugging

**Data Conversion Logic:**
```python
# Convert BacktestResult to database row
def _result_to_row(result: BacktestResult, run_timestamp: str) -> Dict[str, Any]:
    return {
        'run_timestamp': run_timestamp,
        'symbol': result.symbol,
        'rule_stack': json.dumps(result.rule_stack),  # Serialize list
        'total_signals': result.total_signals,
        'profitable_signals': result.profitable_signals,
        'win_rate': result.win_rate,
        'avg_return': result.avg_return,
        'total_return': result.total_return,
        'max_drawdown': result.max_drawdown,
        'sharpe_ratio': result.sharpe_ratio,
        'edge_score': result.edge_score
    }
```

**Test Requirements:**
- Test saving valid `BacktestResult` object
- Test duplicate symbol/timestamp handling
- Test JSON serialization of rule_stack
- Test error handling for invalid data

---

#### Task 3: Implement Batch Save Operations  
**File:** `src/kiss_signal/persistence.py`  
**Estimated LOC:** ~30  
**Dependencies:** Task 2 complete  

**Specific Requirements:**
- Implement `save_backtest_batch()` for multiple results
- Use single transaction for atomicity (all-or-nothing)
- Provide better performance than individual saves
- Include rollback on any failure
- Add batch operation logging

**Transaction Pattern:**
```python
def save_backtest_batch(db_path: Path, results: List[BacktestResult], 
                       run_timestamp: str) -> bool:
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("BEGIN TRANSACTION")
            for result in results:
                # Insert each result
                pass
            conn.execute("COMMIT")
            return True
    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"Batch save failed: {e}")
        return False
```

**Test Requirements:**
- Test successful batch save with multiple results
- Test rollback behavior on failure
- Test performance improvement over individual saves
- Test empty list handling

---

### Phase 2: Query & Retrieval Functions (Tasks 4-5)

#### Task 4: Implement Historical Data Retrieval
**File:** `src/kiss_signal/persistence.py`  
**Estimated LOC:** ~40  
**Dependencies:** Task 1-3 complete  

**Specific Requirements:**
- Implement `get_historical_results()` with optional filtering
- Support symbol filtering (optional parameter)
- Support date range filtering with `days_back` parameter
- Return consistent data format for reporting consumption
- Handle empty result sets gracefully
- Deserialize JSON rule_stack back to list

**Query Logic:**
```python
def get_historical_results(db_path: Path, symbol: Optional[str] = None,
                          days_back: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Build dynamic WHERE clause based on parameters:
    - symbol: WHERE symbol = ?
    - days_back: WHERE run_timestamp >= date('now', '-N days')
    """
```

**Test Requirements:**
- Test retrieval with no filters (all data)
- Test symbol filtering 
- Test date range filtering
- Test empty result handling
- Test JSON deserialization of rule_stack

---

#### Task 5: Implement Latest Results Query
**File:** `src/kiss_signal/persistence.py`  
**Estimated LOC:** ~25  
**Dependencies:** Task 4 complete  

**Specific Requirements:**
- Implement `get_latest_results()` for most recent analysis
- Return latest run for all symbols or filtered subset
- Optimize query performance for common use case
- Handle case where no results exist
- Use efficient SQL with proper indexing

**Optimized Query:**
```sql
-- Get latest results per symbol
SELECT * FROM results r1
WHERE r1.run_timestamp = (
    SELECT MAX(r2.run_timestamp) 
    FROM results r2 
    WHERE r2.symbol = r1.symbol
)
```

**Test Requirements:**
- Test getting latest results for all symbols
- Test filtering by symbol subset
- Test behavior with no data
- Test query performance

---

### Phase 3: Configuration Integration (Task 6)

#### Task 6: Add Database Configuration Support
**Files:** `src/kiss_signal/config.py`, `config.yaml`  
**Estimated LOC:** ~10 total  
**Dependencies:** None (can be done in parallel)  

**Config.py Changes:**
```python
class Config(BaseModel):
    # ...existing fields...
    
    # New database configuration
    database_path: str = Field(default="data/kiss_signal.db", 
                              description="Path to SQLite database file")
```

**Config.yaml Addition:**
```yaml
# Existing configuration...

# Database settings
database_path: "data/kiss_signal.db"
```
