# Story 17: Implement Per-Stock Strategy Performance Analysis with Config Tracking

## Status: ✅ COMPLETE

**Priority:** High (Enables granular strategy analysis and historical data preservation)
**Estimated Story Points:** 8
**Prerequisites:** Story 016 (Strategy Performance Leaderboard) ✅ Complete
**Created:** 2025-07-13
**Completed:** 2025-07-13

## User Story
As a trader, I want to generate detailed per-stock strategy performance reports with config tracking, so I can understand which strategies work best for specific stocks under different market conditions, while preserving valuable historical learning when refreshing current strategies.

## Context & Rationale
Story 016 successfully implemented aggregated strategy performance analysis across all stocks. However, this aggregated view masks important stock-specific insights. Different strategies may work better for different stocks based on their volatility, sector, market cap, or trading patterns.

Additionally, the current system lacks historical context about what configurations produced successful strategies. When rules change or markets evolve, we lose the ability to understand why certain strategies worked in the past.

The current `clear-and-recalculate` command also blindly deletes ALL strategies, destroying potentially valuable historical data from previous configurations that might still be relevant.

This story addresses the need for:
- **Granular Analysis**: Per-stock strategy performance to identify stock-specific patterns
- **Historical Preservation**: Smart clearing that maintains historical learning
- **Config Context**: Tracking what configurations produced successful strategies
- **Evolutionary Learning**: Understanding strategy effectiveness across different market conditions

## Acceptance Criteria

### AC-1: Database Schema Enhancement
**Database Migration Implementation:**
- [x] Create `migrate_strategies_table_v2()` function in `src/kiss_signal/persistence.py`
- [x] Function checks for existing columns using `PRAGMA table_info(strategies)` before migration
- [x] Adds `config_snapshot` TEXT column to store JSON configuration data including:
  - `rules_hash`: SHA256 hash of the rules.yaml file content
  - `app_config_hash`: Hash of key app configuration parameters
  - `run_parameters`: Freeze date, universe file path, date range
  - `timestamp`: When the config was captured
- [x] Adds `config_hash` TEXT column as primary identifier for configuration groups
- [x] Safely backfills existing records with placeholder values: `{"legacy": true}` and `config_hash = "legacy"`
- [x] Migration is idempotent - can be run multiple times safely
- [x] Preserves all existing strategy data during migration
- [x] Migration completes in < 60 seconds for databases up to 100K records

**Database Integration:**
- [x] Migration runs automatically on first database connection after upgrade
- [x] Creates database backup before migration (kiss_signal.db.backup)
- [x] Logs migration progress and results
- [x] Handles SQLite locking gracefully during migration

### AC-2: Enhanced Strategy Persistence
**Config Snapshot Generation:**
- [x] Implement `generate_config_hash(rules_config: Dict, app_config: Config) -> str` function
- [x] Config hash includes: rules file content hash, universe path, key parameters, freeze date
- [x] Hash is deterministic - same config always produces same hash
- [x] Hash is collision-resistant using SHA256

**Config Snapshot Creation:**
- [x] Implement `create_config_snapshot(rules_config: Dict, app_config: Config) -> Dict[str, Any]` function
- [x] Snapshot includes complete context needed to understand strategy performance:
  - Rules file hash and key rule parameters
  - Universe file path and modification time
  - Date range used for backtesting
  - Freeze date if applicable
  - App version/commit hash
- [x] Snapshot is JSON serializable and < 1KB per record

**Enhanced Persistence:**
- [x] Modify `save_strategies_batch()` to accept and store config context
- [x] Update all calls to strategy saving to include current config snapshot
- [x] Ensure backward compatibility - function works with or without config parameters
- [x] Strategy saving performance impact < 5% compared to current implementation

### AC-3: Enhanced Strategy Analysis Command
**Command Interface:**
- [x] Existing `analyze-strategies` command interface remains unchanged
- [x] Command accepts only `--output` parameter (maintains simplicity)
- [x] Default output file remains `strategy_performance_report.csv`
- [x] Command help text updated to reflect comprehensive analysis capability

**Analysis Behavior:**
- [x] Always generates per-stock breakdown showing individual strategy performance for each symbol
- [x] Always includes config tracking columns in output for historical context
- [x] Analyzes ALL strategies in database regardless of config or date
- [x] Results sorted by symbol (ascending), then edge_score (descending)
- [x] Handles empty database gracefully with informative message

**Output Format:**
- [x] CSV contains exactly these columns in this order:
  - `symbol`, `strategy_rule_stack`, `edge_score`, `win_pct`, `sharpe`, `total_return`, `total_trades`, `config_hash`, `run_date`, `config_details`
- [x] `strategy_rule_stack` shows human-readable rule combination (e.g., "sma_10_20_crossover + rsi_oversold")
- [x] `run_date` extracts date portion from run_timestamp (YYYY-MM-DD format)
- [x] `config_details` shows key config information in readable format
- [x] All numeric values formatted to 4 decimal places
- [x] File encoding is UTF-8 with proper CSV escaping

### AC-4: Intelligent Clearing Logic
**Active Strategy Detection:**
- [x] Implement `get_active_strategy_combinations(rules_config: Dict) -> List[str]` function
- [x] Function parses current rules.yaml to extract all possible strategy combinations
- [x] Returns list of JSON-serialized rule stacks that match current configuration
- [x] Handles nested rule configurations and combinations correctly

**Smart Deletion Logic:**
- [x] `clear-and-recalculate` command generates current config hash before deletion
- [x] Deletion query: `DELETE FROM strategies WHERE config_hash = ? AND rule_stack IN (?)`
- [x] Only deletes strategies that match BOTH current config hash AND current active rules
- [x] Preserves strategies from different configs or deprecated rule combinations
- [x] Preserves strategies with `config_hash = "legacy"` (pre-migration data)

**User Interface:**
- [x] Add `--preserve-all` flag that skips deletion entirely (analysis-only mode)
- [x] Before deletion, show count of strategies to be preserved vs deleted
- [x] Require user confirmation unless `--force` flag is used
- [x] Display progress: "✅ Preserved X historical strategies" and "✅ Cleared Y current strategy records"
- [x] Complete clearing and recalculation in same database transaction

**Data Integrity:**
- [x] Clearing operation is atomic - either all strategies cleared or none
- [x] Database constraints prevent orphaned or corrupted records
- [x] Clearing performance scales linearly with database size

### AC-5: Enhanced Reporting Functions
**Core Analysis Function:**
- [x] Enhance `analyze_strategy_performance(db_path: Path) -> List[Dict[str, Any]]` to remove aggregation
- [x] Function returns individual strategy records with all required fields
- [x] Handles malformed JSON in rule_stack or config_snapshot gracefully (skip record)
- [x] Function completes in < 30 seconds for databases with 1M+ records
- [x] Returns empty list for empty database (no exceptions)

**CSV Formatting:**
- [x] Enhance `format_strategy_analysis_as_csv(analysis_data: List[Dict]) -> str` 
- [x] Function handles the new comprehensive format with config columns
- [x] Proper CSV escaping for rule names containing commas or quotes
- [x] Consistent number formatting (4 decimal places for floats)
- [x] Function is pure (no side effects) and deterministic

**Helper Functions:**
- [x] `generate_config_hash()` produces 8-character hash prefix for readability
- [x] Config hashing is fast (< 10ms) and memory efficient
- [x] All functions have comprehensive docstrings with parameter and return type documentation

### AC-6: Code Quality and Compliance
**Type Safety:**
- [x] All new functions have complete type hints including Optional, List, Dict types
- [x] All functions pass `mypy --strict` without warnings
- [x] Type hints are accurate and enforceable at runtime where applicable

**Testing Coverage:**
- [x] Unit tests for all new functions with 100% line coverage
- [x] Integration tests for CLI commands using temporary test databases
- [x] Migration tests ensuring data safety with various database states
- [x] Performance tests validating analysis completes within time limits
- [x] Edge case tests for empty databases, malformed JSON, large datasets

**KISS Compliance:**
- [x] No new external dependencies added to project
- [x] Functions are single-purpose with clear responsibilities
- [x] Code complexity remains low (cyclomatic complexity < 10 per function)
- [x] Total new code < 200 lines across all modified files
- [x] Function interfaces are simple and intuitive

**Backward Compatibility:**
- [x] Existing CLI commands work unchanged for current users
- [x] Existing database schemas are preserved and enhanced
- [x] No breaking changes to public function signatures
- [x] Migration handles all existing database states gracefully
- [x] Legacy data is preserved and clearly marked in outputs

## Technical Design (KISS Approach)

### 1. Database Migration (`src/kiss_signal/persistence.py`)
```python
def migrate_strategies_table_v2(db_path: Path) -> None:
    """Safely migrate strategies table to include config tracking."""
    with sqlite3.connect(str(db_path)) as conn:
        # Check if migration needed
        cursor = conn.execute("PRAGMA table_info(strategies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'config_snapshot' not in columns:
            conn.execute("ALTER TABLE strategies ADD COLUMN config_snapshot TEXT")
            conn.execute("ALTER TABLE strategies ADD COLUMN config_hash TEXT")
            # Backfill existing records with placeholder values
            conn.execute("""
                UPDATE strategies 
                SET config_snapshot = '{"legacy": true}', 
                    config_hash = 'legacy' 
                WHERE config_snapshot IS NULL
            """)
            conn.commit()
```

### 2. Enhanced Strategy Saving (`src/kiss_signal/persistence.py`)
```python
def save_strategy_with_config(
    db_connection: Connection,
    strategy_result: Dict[str, Any],
    config_snapshot: Dict[str, Any],
    config_hash: str,
    run_timestamp: str
) -> bool:
    """Save strategy result with configuration context."""
    try:
        db_connection.execute("""
            INSERT INTO strategies (
                symbol, rule_stack, edge_score, win_pct, sharpe, 
                total_return, total_trades, run_timestamp,
                config_snapshot, config_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy_result['symbol'],
            json.dumps(strategy_result['rule_stack']),
            strategy_result['edge_score'],
            strategy_result['win_pct'], 
            strategy_result['sharpe'],
            strategy_result['total_return'],
            strategy_result['total_trades'],
            run_timestamp,
            json.dumps(config_snapshot),
            config_hash
        ))
        return True
    except sqlite3.Error:
        return False
```

### 3. Simplified Analysis Function (`src/kiss_signal/reporter.py`)
```python
def analyze_strategy_performance(db_path: Path) -> List[Dict[str, Any]]:
    """Analyze strategy performance with comprehensive per-stock breakdown."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT symbol, rule_stack, edge_score, win_pct, sharpe,
                   total_return, total_trades, config_hash, run_timestamp,
                   config_snapshot
            FROM strategies 
            ORDER BY symbol, edge_score DESC
        """)
        
        results = []
        for row in cursor.fetchall():
            try:
                rules = json.loads(row['rule_stack'])
                strategy_name = " + ".join(r.get('name', 'N/A') for r in rules)
                config_details = json.loads(row['config_snapshot'] or '{}')
                
                results.append({
                    'symbol': row['symbol'],
                    'strategy_rule_stack': strategy_name,
                    'edge_score': row['edge_score'],
                    'win_pct': row['win_pct'],
                    'sharpe': row['sharpe'],
                    'total_return': row['total_return'],
                    'total_trades': row['total_trades'],
                    'config_hash': row['config_hash'],
                    'run_date': row['run_timestamp'][:10],  # Extract date part
                    'config_details': str(config_details)
                })
            except (json.JSONDecodeError, TypeError):
                continue
                
        return results
```

### 4. Simplified CLI Command (`src/kiss_signal/cli.py`)
```python
@app.command(name="analyze-strategies")
def analyze_strategies(
    ctx: typer.Context,
    output_file: Path = typer.Option(
        "strategy_performance_report.csv",
        "--output", "-o",
        help="Path to save the strategy performance report as a CSV file.",
    ),
) -> None:
    """Analyze and report on the comprehensive performance of all strategies."""
    console.print("[bold blue]Analyzing strategy performance...[/bold blue]")
    app_config = ctx.obj["config"]
    db_path = Path(app_config.database_path)

    if not db_path.exists():
        console.print(f"[red]Error: Database file not found at {db_path}[/red]")
        raise typer.Exit(1)

    try:
        strategy_performance = reporter.analyze_strategy_performance(db_path)
        if not strategy_performance:
            console.print("[yellow]No historical strategies found to analyze.[/yellow]")
            return

        report_content = reporter.format_strategy_analysis_as_csv(strategy_performance)
        output_file.write_text(report_content, encoding="utf-8")
        console.print(f"✅ Strategy performance analysis saved to: [cyan]{output_file}[/cyan]")

    except Exception as e:
        console.print(f"[red]An unexpected error occurred during analysis: {e}[/red]")
        if ctx.obj and ctx.obj.get("verbose", False):
            console.print_exception()
        raise typer.Exit(1)
```

### 4. Intelligent Clearing (`src/kiss_signal/cli.py`)
```python
@app.command(name="clear-and-recalculate")
def clear_and_recalculate(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
    preserve_all: bool = typer.Option(False, "--preserve-all", help="Skip clearing, analysis only"),
    freeze_data: Optional[str] = typer.Option(None, "--freeze-data", help="Freeze data at this date"),
) -> None:
    """Intelligently clear current strategies and recalculate with preservation of historical data."""
    app_config = ctx.obj["config"]
    rules_config = ctx.obj["rules"]
    
    if not preserve_all:
        # Generate current config context
        current_config_hash = reporter.generate_config_hash(rules_config, app_config)
        active_strategies = reporter.get_active_strategy_combinations(rules_config)
        
        # Smart deletion query
        with persistence.get_connection(db_path) as conn:
            # Count what will be preserved vs deleted
            preserved_count = conn.execute("""
                SELECT COUNT(*) FROM strategies 
                WHERE config_hash != ? OR rule_stack NOT IN ({})
            """.format(','.join(['?'] * len(active_strategies))), 
            [current_config_hash] + active_strategies).fetchone()[0]
            
            if not force:
                console.print(f"Will preserve {preserved_count} historical strategies")
                if not typer.confirm("Continue with intelligent clearing?"):
                    return
            
            # Perform intelligent deletion
            cursor = conn.execute("""
                DELETE FROM strategies 
                WHERE config_hash = ? AND rule_stack IN ({})
            """.format(','.join(['?'] * len(active_strategies))),
            [current_config_hash] + active_strategies)
            
            deleted_count = cursor.rowcount
            console.print(f"✅ Preserved {preserved_count} historical strategies")
            console.print(f"✅ Cleared {deleted_count} current strategy records")
```

### 5. Sample Comprehensive CSV Output (`strategy_performance_report.csv`)
```csv
symbol,strategy_rule_stack,edge_score,win_pct,sharpe,total_return,total_trades,config_hash,run_date,config_details
RELIANCE,sma_10_20_crossover + rsi_oversold,0.75,0.68,1.45,0.12,23,abc123,2025-07-13,"{'rules_hash': 'def456', 'market_conditions': 'bullish'}"
RELIANCE,bollinger_breakout,0.72,0.65,1.38,0.11,18,abc123,2025-07-13,"{'rules_hash': 'def456', 'market_conditions': 'bullish'}"
INFY,macd_momentum + volume_filter,0.69,0.72,1.33,0.08,15,abc123,2025-07-13,"{'rules_hash': 'def456', 'market_conditions': 'bullish'}"
INFY,sma_10_20_crossover + rsi_oversold,0.65,0.60,1.25,0.07,20,abc123,2025-07-13,"{'rules_hash': 'def456', 'market_conditions': 'bullish'}"
TCS,bollinger_breakout,0.71,0.68,1.40,0.09,16,abc123,2025-07-13,"{'rules_hash': 'def456', 'market_conditions': 'bullish'}"
```

## Architectural Considerations

### Database Design
- **Config Snapshot**: JSON field storing complete configuration context for historical analysis
- **Config Hash**: Efficient indexing and querying of configuration groups
- **Backward Compatibility**: Existing strategies get placeholder values during migration

### Performance
- **Indexed Queries**: Config hash enables efficient filtering without JSON parsing
- **Selective Analysis**: Symbol filtering reduces query overhead for focused analysis
- **Batch Operations**: Intelligent clearing uses efficient SQL operations

### Data Preservation Strategy
- **Historical Value**: Preserve strategies from different configs as learning data
- **Smart Clearing**: Only remove strategies that will be recalculated
- **Context Tracking**: Maintain configuration context for each strategy run

## Out of Scope

### Immediate Exclusions
- **Complex Market Analysis**: Advanced market condition detection and correlation
- **Automated Recommendations**: AI-driven strategy suggestions based on historical data
- **Real-time Updates**: Live updating of strategy performance during market hours
- **GUI Components**: Graphical visualization of per-stock performance
- **Strategy Optimization**: Automatic parameter tuning based on historical analysis

### Future Considerations (Not This Story)
- **Performance Correlation Analysis**: Cross-stock strategy performance patterns
- **Market Regime Detection**: Automatic identification of market conditions
- **Strategy Evolution Tracking**: Visual timeline of strategy effectiveness
- **Automated Backtesting Triggers**: Scheduled recalculation based on market events

## Definition of Done

- [x] All acceptance criteria are met and tested
- [x] Database migration script successfully updates existing data
- [x] `analyze-strategies` command provides comprehensive analysis with config tracking
- [x] `clear-and-recalculate` intelligently preserves historical strategies
- [x] All new functions pass `mypy --strict` type checking
- [x] Comprehensive test coverage including edge cases
- [x] Integration tests verify end-to-end functionality
- [x] Performance is acceptable for typical database sizes (< 1M records)
- [x] Documentation is updated with new command usage examples

## Detailed Task List

### Task 1: Database Schema Migration
- [x] Create `migrate_strategies_table_v2()` function in `persistence.py`
- [x] Add config snapshot and hash columns to strategies table
- [x] Implement safe migration with backward compatibility
- [x] Add unit tests for migration logic

### Task 2: Enhanced Strategy Persistence
- [x] Modify `save_strategies_batch()` to include config context
- [x] Implement `generate_config_hash()` function for consistent hashing
- [x] Create `create_config_snapshot()` function to capture current state
- [x] Update strategy saving calls throughout the application

### Task 3: Simplified Analysis Enhancement
- [x] Enhance existing `analyze_strategy_performance()` function to always provide comprehensive analysis
- [x] Remove complex conditional logic - always show per-stock breakdown with config
- [x] Update CSV formatting to handle the comprehensive format
- [x] Maintain same simple CLI interface with enhanced output

### Task 4: Intelligent Clearing Logic
- [x] Implement `get_active_strategy_combinations()` to parse current rules
- [x] Modify `clear_and_recalculate` command with intelligent deletion
- [x] Add `--preserve-all` flag for analysis-only mode
- [x] Include progress reporting and confirmation prompts

### Task 5: Comprehensive Testing
- [x] Unit tests for all new functions with mock data
- [x] Integration tests for CLI commands with temporary databases
- [x] Migration tests ensuring data safety and correctness
- [x] Edge case tests for malformed data and empty databases

### Task 6: Documentation and Examples
- [x] Update README with new command usage examples
- [x] Add sample CSV outputs to documentation
- [x] Create migration guide for existing users
- [x] Document configuration hash methodology

## User Acceptance Testing Scenarios

### Scenario 1: Fresh Installation
1. User runs system for first time
2. Database created with new schema
3. Strategies saved with config tracking
4. Per-stock analysis generates correct reports

### Scenario 2: Existing Database Migration
1. User has existing strategies database
2. Migration runs automatically on first use
3. Existing strategies preserved with legacy markers
4. New strategies include full config context

### Scenario 3: Rule Changes and Clearing
1. User modifies rules.yaml configuration
2. Runs `clear-and-recalculate` command
3. Historical strategies from old configs preserved
4. Only current config strategies recalculated

### Scenario 4: Comprehensive Analysis
1. User runs `analyze-strategies` (simple command)
2. Receives detailed CSV with per-stock performance AND config tracking
3. Can see all strategies for all symbols with historical context
4. Single command provides complete view of strategy performance

## Risk Assessment

### Technical Risks
- **Migration Complexity**: Database migration could fail on large datasets
- **Performance Impact**: Additional columns might slow queries
- **Storage Growth**: Config snapshots increase database size

### Mitigation Strategies
- **Staged Migration**: Test migration on backup databases first
- **Indexed Queries**: Use config_hash for efficient filtering
- **JSON Compression**: Store only essential config details

### Success Metrics
- **Migration Success**: 100% of existing strategies preserved during migration
- **Query Performance**: Per-stock analysis completes in < 30 seconds for typical datasets
- **Data Integrity**: No loss of historical strategy data during intelligent clearing
- **User Adoption**: Clear improvement in strategy analysis capabilities

---

**Story Priority Justification:**
This story directly addresses the user's need for granular, stock-specific strategy analysis while implementing sophisticated data preservation strategies. It builds naturally on Story 016's foundation while adding the historical context and intelligent data management that enables continuous learning and improvement of trading strategies.

**Implementation Summary:**
- ✅ Database migration V2 implemented with `config_snapshot` and `config_hash` columns
- ✅ Enhanced strategy persistence with configuration tracking
- ✅ Migration function handles existing data safely with legacy placeholders
- ✅ Config hash generation and snapshot creation implemented
- ✅ Database schema versioning implemented (PRAGMA user_version = 2)
- ✅ Full test coverage including migration, config functions, and edge cases
- ✅ Backward compatibility maintained for existing installations
