# Story 020: Fix Strategy Performance Report Massive Duplication

## Status: 🔴 Ready (Critical Data Quality Issue)

**Priority:** CRITICAL (2,300+ rows should be ~100 unique results - 21x duplication)
**Estimated Story Points:** 2 (Simple SQL fix + database constraints)
**Prerequisites:** None (Critical bugfix)
**Created:** 2025-07-19
**Reviewed:** 2025-07-19 (Kailash Nadh - Technical Architecture - CRITICAL KISS FIX)

## User Story
As a trader analyzing strategy performance, I want the `analyze-strategies` command to generate a clean, deduplicated CSV report so that I can see actual strategy performance without 21 identical copies of the same results cluttering my analysis.

## Context & Rationale

**CRITICAL BUG DISCOVERED**: The `strategy_performance_report.csv` contains massive duplication with 2,326 lines when it should contain ~100 unique strategy-symbol combinations. Analysis reveals:

- Same strategy results repeated 21+ times with identical metrics but different timestamps
- Example: `HDFCBANK, bullish_engulfing_reversal, 75bf44fe` appears 21 times with identical edge_score/win_rate/pnl
- Root cause: `reporter.py::analyze_strategy_performance()` pulls ALL rows without deduplication
- Storage system allows unlimited duplicate entries without constraints

**Business Impact:**
- CSV files are 21x larger than necessary (2.3MB vs 100KB)
- Analysis is impossible with thousands of duplicate rows
- Performance degradation from processing 21x more data
- Loss of confidence in system data quality

**KISS Fix Approach**: 
1. Fix the broken SQL query to return only latest results per strategy-symbol
2. Add database constraints to prevent future duplicates
3. Clean existing duplicate data

This violates the fundamental data principle: **"One source of truth per strategy result."**

## Architectural Deep Dive

### Current Broken System Analysis
The existing system follows a modular monolith pattern but has a critical data quality flaw:

**Current Broken Flow:**
1. `cli.py::analyze_strategies()` calls `reporter.analyze_strategy_performance()`
2. `reporter.py` executes: `SELECT * FROM strategies ORDER BY symbol, edge_score DESC`
3. This pulls EVERY duplicate row for each strategy-symbol combination
4. CSV writer dumps all 2,326 duplicated rows to file

**Current Database Schema (BROKEN):**
```sql
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    strategy_name TEXT NOT NULL, 
    edge_score REAL NOT NULL,
    win_rate REAL NOT NULL,
    avg_return REAL NOT NULL,
    total_pnl REAL NOT NULL,
    num_trades INTEGER NOT NULL,
    config_hash TEXT NOT NULL,
    backtest_date TEXT NOT NULL,
    params_json TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- NO UNIQUE CONSTRAINTS = UNLIMITED DUPLICATES!
```

### Proposed KISS Fix

#### 1. Fix Reporter Query (Immediate Relief)
Replace the broken `SELECT *` with intelligent deduplication using CTE:

```sql
WITH latest_results AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY symbol, strategy_name, config_hash 
               ORDER BY timestamp DESC
           ) as rn
    FROM strategies
)
SELECT symbol, strategy_name, edge_score, win_rate, avg_return, 
       total_pnl, num_trades, config_hash, backtest_date, params_json
FROM latest_results 
WHERE rn = 1
ORDER BY symbol, edge_score DESC;
```

#### 2. Add Database Constraints (Prevent Future Duplicates)
```sql
CREATE UNIQUE INDEX idx_strategies_unique 
ON strategies(symbol, strategy_name, config_hash);
```

#### 3. Clean Existing Data (One-time Cleanup)
```sql
DELETE FROM strategies WHERE id NOT IN (
    SELECT MAX(id) FROM strategies 
    GROUP BY symbol, strategy_name, config_hash
);
```

**Result:** 2,326 rows → ~110 unique strategy results (21x reduction)

## Technical Implementation Goals

### Phase 1: Immediate Relief (Story 020)
1. **Fix Reporter Query**: Replace broken `SELECT *` with CTE-based deduplication
2. **Add Database Migration**: Create unique constraint to prevent future duplicates  
3. **Clean Existing Data**: Remove 21x duplicates from current database
4. **Validate Fix**: Confirm CSV reports now contain ~100 rows instead of 2,300+

**Immediate Business Value**: 
- Clean, usable CSV reports for strategy analysis
- 21x faster report generation and file sizes
- Restored confidence in data quality
- Prevention of future duplicates

## Detailed Acceptance Criteria

### AC-1: Fix Reporter SQL Query (Immediate Relief)
**File**: `src/kiss_signal/reporter.py`
**Function**: `analyze_strategy_performance()`

**Implementation Requirements**:
- [ ] **Replace Broken Query**: Remove `SELECT * FROM strategies ORDER BY symbol, edge_score DESC`
- [ ] **Intelligent Deduplication**: Use CTE with ROW_NUMBER() to get latest result per strategy-symbol-config
- [ ] **Preserve Column Order**: Maintain exact same CSV output format for backward compatibility
- [ ] **Performance Optimization**: Query should execute faster despite CTE (fewer rows returned)
- [ ] **Clear Logging**: Log number of unique strategies found vs total rows in database

**Critical Implementation**:
```python
def analyze_strategy_performance(output_file: str = "strategy_performance_report.csv") -> None:
    """Generate strategy performance report with proper deduplication.
    
    FIXED: Now returns only the latest result for each unique strategy-symbol-config
    combination instead of all historical duplicates.
    """
    from .database import get_db_connection
    
    with get_db_connection() as conn:
        # NEW: Intelligent deduplication query using CTE
        query = """
        WITH latest_results AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY symbol, strategy_name, config_hash 
                       ORDER BY timestamp DESC
                   ) as rn
            FROM strategies
        )
        SELECT symbol, strategy_name, edge_score, win_rate, avg_return, 
               total_pnl, num_trades, config_hash, backtest_date, params_json
        FROM latest_results 
        WHERE rn = 1
        ORDER BY symbol, edge_score DESC
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Log deduplication impact
        total_rows_query = "SELECT COUNT(*) as total FROM strategies"
        total_rows = pd.read_sql_query(total_rows_query, conn)['total'].iloc[0]
        unique_strategies = len(df)
        
        logger.info(f"Strategy performance deduplication: {unique_strategies} unique strategies "
                   f"from {total_rows} total database rows "
                   f"(eliminated {total_rows - unique_strategies} duplicates)")
        
        if df.empty:
            logger.warning("No strategy results found in database")
            # Create empty CSV with headers
            pd.DataFrame(columns=["symbol", "strategy_name", "edge_score", "win_rate", 
                                "avg_return", "total_pnl", "num_trades", "config_hash", 
                                "backtest_date", "params_json"]).to_csv(output_file, index=False)
        else:
            df.to_csv(output_file, index=False)
            logger.info(f"Strategy performance report written to {output_file} "
                       f"({unique_strategies} unique strategies)")
```

**Unit Tests Required**:
- [ ] Test with duplicate data (verify only latest results returned)
- [ ] Test with single strategy (verify correct result selected)
- [ ] Test with multiple configs for same strategy-symbol (verify all configs included)
- [ ] Test with empty database (verify graceful handling)
- [ ] Test ordering (verify symbol ordering and edge_score DESC within symbol)
- [ ] Performance test (verify faster execution with large duplicate datasets)

### AC-2: Database Migration for Unique Constraints
**File**: `src/kiss_signal/database.py`

**New Function**: `migrate_add_unique_constraints()`
```python
def migrate_add_unique_constraints() -> None:
    """Add unique constraints to prevent strategy result duplicates.
    
    This migration prevents the same strategy-symbol-config combination
    from being stored multiple times, fixing the root cause of the 
    duplication issue.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if unique index already exists
        index_check = cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_strategies_unique'
        """).fetchone()
        
        if index_check:
            logger.info("Unique constraint already exists, skipping migration")
            return
        
        logger.info("Adding unique constraint to prevent strategy duplicates")
        
        try:
            # Step 1: Clean existing duplicates first
            logger.info("Cleaning existing duplicate strategies...")
            delete_query = """
            DELETE FROM strategies WHERE id NOT IN (
                SELECT MAX(id) FROM strategies 
                GROUP BY symbol, strategy_name, config_hash
            )
            """
            deleted_rows = cursor.execute(delete_query).rowcount
            logger.info(f"Removed {deleted_rows} duplicate strategy entries")
            
            # Step 2: Add unique constraint
            cursor.execute("""
                CREATE UNIQUE INDEX idx_strategies_unique 
                ON strategies(symbol, strategy_name, config_hash)
            """)
            
            conn.commit()
            logger.info("Successfully added unique constraint to strategies table")
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Failed to add unique constraint: {e}")
            raise
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            conn.rollback()
            raise

def run_migrations() -> None:
    """Run all pending database migrations."""
    migrate_add_unique_constraints()
```

**Integration Requirements**:
- [ ] Call `run_migrations()` in application startup
- [ ] Add migration to CLI command for manual execution
- [ ] Handle existing duplicate data gracefully
- [ ] Log migration progress and results

### AC-3: Fix Strategy Storage to Respect Unique Constraints  
**File**: `src/kiss_signal/backtester.py` (or wherever strategies are stored)

**Implementation Requirements**:
- [ ] **Modify Storage Logic**: Change INSERT to INSERT OR REPLACE for duplicate handling
- [ ] **Conflict Resolution**: When duplicate detected, update with latest results
- [ ] **Error Handling**: Graceful handling of constraint violations
- [ ] **Performance**: Minimize impact on backtesting performance

**Storage Fix Example**:
```python
def store_strategy_result(self, result: Dict[str, Any]) -> None:
    """Store strategy result with duplicate prevention.
    
    Uses INSERT OR REPLACE to handle duplicates gracefully instead
    of creating multiple entries for the same strategy-symbol-config.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Use INSERT OR REPLACE to handle duplicates
        query = """
        INSERT OR REPLACE INTO strategies 
        (symbol, strategy_name, edge_score, win_rate, avg_return, 
         total_pnl, num_trades, config_hash, backtest_date, params_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        cursor.execute(query, (
            result['symbol'],
            result['strategy_name'], 
            result['edge_score'],
            result['win_rate'],
            result['avg_return'],
            result['total_pnl'],
            result['num_trades'],
            result['config_hash'],
            result['backtest_date'],
            result['params_json']
        ))
        
        logger.debug(f"Stored strategy result: {result['symbol']} - {result['strategy_name']} "
                    f"(edge_score: {result['edge_score']:.4f})")
```

### AC-4: CLI Command for Manual Deduplication
**File**: `src/kiss_signal/cli.py`

**New Command**: `deduplicate-strategies`
```python
@app.command()
def deduplicate_strategies(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted without actually deleting")
) -> None:
    """Remove duplicate strategy entries from database.
    
    Fixes databases with duplicate strategy results by keeping only the
    latest entry for each unique strategy-symbol-config combination.
    """
    from .database import get_db_connection, run_migrations
    
    logger.info("Starting strategy deduplication process")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Count current duplicates
        duplicate_count_query = """
        SELECT COUNT(*) - COUNT(DISTINCT symbol, strategy_name, config_hash) as duplicates
        FROM strategies
        """
        duplicate_count = cursor.execute(duplicate_count_query).fetchone()[0]
        
        if duplicate_count == 0:
            logger.info("No duplicate strategies found")
            return
        
        logger.info(f"Found {duplicate_count} duplicate strategy entries")
        
        if dry_run:
            # Show what would be deleted
            preview_query = """
            SELECT symbol, strategy_name, config_hash, COUNT(*) as count,
                   MIN(timestamp) as oldest, MAX(timestamp) as newest
            FROM strategies 
            GROUP BY symbol, strategy_name, config_hash
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            """
            duplicates_df = pd.read_sql_query(preview_query, conn)
            
            console.print("\n[bold]Duplicate Strategy Entries (would keep newest):[/bold]")
            for _, row in duplicates_df.iterrows():
                console.print(f"  {row['symbol']} - {row['strategy_name']} - {row['config_hash'][:8]}: "
                             f"{row['count']} entries ({row['oldest']} to {row['newest']})")
            
            console.print(f"\n[bold red]Total duplicates to remove: {duplicate_count}[/bold red]")
            console.print("[dim]Run without --dry-run to perform actual deduplication[/dim]")
        else:
            # Perform actual deduplication
            run_migrations()  # This includes the deduplication logic
            console.print(f"[bold green]✅ Removed {duplicate_count} duplicate strategy entries[/bold green]")
```

## Simple Success Metrics

### SM-1: Data Quality Validation  
- [ ] **CSV Size Reduction**: `strategy_performance_report.csv` reduced from 2,300+ to ~100 rows
- [ ] **File Size Reduction**: CSV file size reduced by ~95% (from 2.3MB to ~100KB)
- [ ] **Unique Strategy Count**: Verify exact count matches expected unique strategy-symbol combinations
- [ ] **Data Integrity**: All unique strategies preserved, no data loss during deduplication

### SM-2: Performance Impact Validation
- [ ] **Report Generation Speed**: CSV generation 20x faster (fewer rows to process)
- [ ] **Database Query Performance**: Deduplication query executes in <100ms
- [ ] **Storage Prevention**: New strategy results cannot create duplicates (constraint violation)
- [ ] **Backtesting Impact**: <1% performance impact from INSERT OR REPLACE logic

### SM-3: Technical Quality
- [ ] **Backward Compatibility**: CSV format unchanged, existing analysis scripts work
- [ ] **Error Handling**: Graceful degradation if migration fails
- [ ] **Logging**: Clear visibility into deduplication process and results
- [ ] **Data Consistency**: No orphaned or corrupted data after cleanup

## Implementation Task Breakdown

### Task 020.1: Fix Reporter SQL Query (1 story point)
**Owner**: Backend Developer  
**Dependencies**: None (Critical bugfix)
**Deliverables**:
- [ ] Replace broken `SELECT *` with CTE-based deduplication query
- [ ] Add logging for deduplication metrics
- [ ] Unit tests for deduplication logic

**Files Modified**:
- `src/kiss_signal/reporter.py` (~20 LOC changed)
- `tests/test_reporter.py` (+40 LOC)

### Task 020.2: Database Migration and Constraints (1 story point)  
**Owner**: Backend Developer
**Dependencies**: None
**Deliverables**:
- [ ] Add unique constraint migration
- [ ] Clean existing duplicate data
- [ ] Add CLI command for manual deduplication
- [ ] Integration tests

**Files Modified**:
- `src/kiss_signal/database.py` (+50 LOC) 
- `src/kiss_signal/cli.py` (+40 LOC)
- `tests/test_database.py` (+60 LOC)

### Task 020.3: Fix Strategy Storage Logic (0.5 story points)
**Owner**: Backend Developer
**Dependencies**: Task 020.2
**Deliverables**:
- [ ] Change INSERT to INSERT OR REPLACE 
- [ ] Test constraint violation handling
- [ ] Performance validation

**Files Modified**:
- `src/kiss_signal/backtester.py` (~10 LOC changed)
- `tests/test_backtester.py` (+20 LOC)

### Task 020.4: End-to-End Validation (0.5 story points)
**Owner**: QA/Backend Developer
**Dependencies**: Tasks 020.1, 020.2, 020.3
**Deliverables**:
- [ ] Full system test with duplicate cleanup
- [ ] CSV report validation 
- [ ] Performance regression test
- [ ] Documentation update

**Files Modified**:
- `tests/test_integration.py` (+30 LOC)
- `README.md` (updated with deduplication info)

## Risk Assessment & Mitigation

### Low Risks (Critical Bugfix)
1. **Data Loss During Cleanup**: Accidental deletion of unique strategies
   - *Mitigation*: Comprehensive testing, dry-run option, database backup before migration
   
2. **Performance Regression**: CTE query slower than simple SELECT
   - *Mitigation*: Query performance testing, index optimization if needed

3. **Constraint Violations**: Existing code breaks with new unique constraints
   - *Mitigation*: INSERT OR REPLACE pattern, comprehensive error handling

### Minimal Risks  
1. **Migration Failure**: Unique constraint creation fails on some systems
   - *Mitigation*: Rollback logic, clear error messages, manual recovery steps

## Post-Implementation Monitoring

### Key Metrics to Track
1. **CSV Report Size**: Sustained reduction from 2,300+ to ~100 rows
2. **Database Growth**: Linear growth instead of 21x duplication  
3. **Report Generation Time**: 20x improvement in CSV generation speed
4. **Error Rates**: Monitor constraint violation frequency

### Success Criteria (1 day post-deployment)
- [ ] CSV reports consistently contain ~100 rows instead of 2,300+
- [ ] No duplicate strategy entries in new backtest runs
- [ ] Report generation performance improved by 20x
- [ ] Zero data quality complaints from users

## Next Possible Stories

### Story 021: Strategy Performance Trend Analysis (3 story points)
**Description**: Add historical tracking of strategy performance changes over time
**Justification**: Now that we have clean data, we can build meaningful trend analysis

### Story 022: Strategy Performance Dashboard (5 story points)  
**Description**: Web dashboard for interactive strategy performance analysis
**Justification**: Clean data enables rich visualization and filtering

### Story 023: Automated Strategy Performance Alerts (2 story points)
**Description**: Alert when strategy performance significantly changes
**Justification**: Clean baseline data enables meaningful change detection

## KISS Principle Compliance Check

✅ **Tiny Diffs**: Total changes <150 LOC across all files  
✅ **Critical Bugfix**: Addresses fundamental data quality issue
✅ **Simple Solution**: CTE query + unique constraint, no complex frameworks
✅ **Immediate Business Value**: 21x reduction in report size and generation time
✅ **Backward Compatible**: CSV format unchanged, existing scripts work
✅ **Testable**: Clear before/after validation with concrete metrics
✅ **Debuggable**: Clear logging of deduplication process
✅ **Minimal Dependencies**: No new external libraries
✅ **Data Integrity**: Preserves all unique data while removing duplicates
✅ **Performance Improvement**: 20x faster report generation

**ARCHITECTURAL BENEFITS**:
- **Data Quality Restoration**: One source of truth per strategy result  
- **Performance Optimization**: 21x reduction in data processing
- **Storage Efficiency**: Prevents unlimited duplicate accumulation
- **Analysis Enablement**: Clean data enables meaningful business analysis
- **Future-Proof**: Unique constraints prevent regression of this issue

## Definition of Done (Critical Fix)

### Code Quality
- [ ] **Implementation Complete**: Reporter query fixed, database constraints added
- [ ] **Test Coverage**: >95% line coverage for modified functions
- [ ] **Type Safety**: Full type hints with mypy validation passing  
- [ ] **Simple Documentation**: Clear docstrings and migration notes
- [ ] **Code Review**: Peer review completed, focusing on data integrity

### Integration & Testing
- [ ] **Unit Tests**: All deduplication logic comprehensively tested
- [ ] **Integration Test**: End-to-end testing with duplicate data cleanup
- [ ] **Performance Test**: 20x improvement in report generation verified
- [ ] **Data Migration Test**: Safe cleanup of existing duplicates validated
- [ ] **Regression Testing**: All existing functionality continues to work

### Data Quality & Business Value
- [ ] **CSV Deduplication**: Reports reduced from 2,300+ to ~100 rows
- [ ] **Database Constraints**: New duplicates prevented by unique constraints
- [ ] **Data Integrity**: All unique strategies preserved during cleanup
- [ ] **Performance Improvement**: Report generation 20x faster

### Production Readiness
- [ ] **Safe Migration**: Database migration tested with rollback capability
- [ ] **Error Handling**: Graceful degradation when constraints violated
- [ ] **Clear Logging**: Comprehensive logging of deduplication process and results
- [ ] **Monitoring**: Metrics in place to track ongoing data quality

---

**Story Estimation Rationale**:
Estimated at 2 points for critical bugfix:
- **SQL Query Fix** (0.5 points): Simple CTE replacement for broken SELECT *
- **Database Migration** (1 point): Unique constraint + duplicate cleanup logic
- **Storage Logic Update** (0.5 points): INSERT OR REPLACE pattern

**KISS Compliance**:
- **Critical Business Need**: 21x duplication breaks basic analysis functionality
- **Simple Technical Solution**: CTE query + unique constraint, no complex architecture
- **Immediate Measurable Impact**: 2,300 rows → 100 rows, 20x performance improvement
- **Data Integrity Focus**: Preserve all unique data while eliminating waste
- **Prevention-Oriented**: Fix root cause, not just symptoms

**Critical Priority Justification**:
This is not a feature request but a **critical data quality bug** that makes the system's primary output (strategy performance reports) completely unusable for analysis. The 21x duplication transforms a 100-row analytical dataset into an incomprehensible 2,300-row mess, destroying the core value proposition of the trading analysis system.
