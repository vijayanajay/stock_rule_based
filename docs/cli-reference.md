# KISS Signal CLI Reference

**Version:** 1.0  
**Framework:** Typer  
**Philosophy:** Keep-It-Simple Signal generation for NSE stock trading

---

## Overview

The KISS Signal CLI provides a command-line interface for backtesting trading strategies, analyzing performance, and generating reports. All commands support verbose logging and use configuration files for flexibility.

## Global Options

These options are available for all commands:

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--config` | | `config.yaml` | Path to the main conf### Version History

### Current (Story 22: CLI Simplification)
- ✅ Simplified CLI with single analysis command
- ✅ Aggregated strategy leaderboard as default (most useful view)
- ✅ Per-stock detailed analysis via `--per-stock` flag
- ✅ Configuration tracking and snapshots for both modes
- ✅ Percentage conversion for aggregated returns
- ✅ Intelligent clearing with historical preservation
- ✅ Enhanced CLI commands with proper error handling
- ✅ Dual output format support (aggregated vs. detailed)

### Previous Versions
- Story 17: Per-stock analysis with configuration tracking
- Story 16: Aggregated strategy performance leaderboard
- Story 14: Rule performance analysis
- Basic backtesting and reporting
- SQLite persistence layer
- Configuration-driven approachL file |
| `--rules` | | `config/rules.yaml` | Path to trading rules configuration YAML file |
| `--verbose` | `-v` | `false` | Enable verbose logging with debug information |
| `--help` | | | Show help information for any command |

---

## Commands

### 1. `run` - Execute Backtesting

**Purpose:** Run backtesting analysis for all symbols in the universe and generate reports.

```bash
python -m kiss_signal run [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--freeze-data` | `str` | `None` | Freeze historical data to a specific date (YYYY-MM-DD format) for reproducible backtesting |

#### Behavior

1. **Data Loading:** Loads symbol universe from configuration file
2. **Price Data:** Fetches historical price data with caching support
3. **Backtesting:** Runs strategy analysis using configured rules
4. **Persistence:** Saves results to SQLite database with configuration tracking
5. **Reporting:** Generates daily report with new signals and position updates

#### Example Usage

```bash
# Run with current data
python -m kiss_signal run --config config.yaml --verbose

# Run with frozen historical data for reproducible results
python -m kiss_signal run --freeze-data 2025-01-01

# Run with custom configuration files
python -m kiss_signal run --config my_config.yaml --rules my_rules.yaml
```

#### Output Files

- Database updated with new strategies
- Daily report in Markdown format (location: `reports_output_dir` from config)
- Console output with progress and summary statistics

---

### 2. `analyze-strategies` - Strategy Performance Analysis

**Purpose:** Analyze comprehensive strategy performance with aggregated leaderboard as default.

```bash
python -m kiss_signal analyze-strategies [OPTIONS]
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | `Path` | `strategy_performance_report.csv` | Output file path for the CSV report |
| `--per-stock` | | `bool` | `false` | Generate detailed per-stock strategy report instead of the aggregated leaderboard |

#### Behavior

**Default Mode (Aggregated Strategy Leaderboard):**
1. **Data Grouping:** Groups strategies by rule stack combinations and configuration
2. **Aggregated Metrics:** Calculates frequency, averages, and top symbols per strategy
3. **Configuration Tracking:** Preserves config information for each strategy group
4. **CSV Export:** Generates summary CSV with aggregated performance metrics

**Per-Stock Mode (`--per-stock` flag):**
1. **Data Retrieval:** Extracts all strategy records from database
2. **Per-Stock Analysis:** Returns individual records for each symbol-strategy combination
3. **Configuration Tracking:** Includes config hash and snapshot for each record
4. **CSV Export:** Generates detailed CSV with all strategy metrics

#### Report Formats

**Aggregated Format (Default - CSV)**

| Column | Description |
|--------|-------------|
| `strategy_rule_stack` | Human-readable rule combination |
| `frequency` | Number of times strategy was optimal |
| `avg_edge_score` | Average edge score across all uses |
| `avg_win_pct` | Average win percentage |
| `avg_sharpe` | Average Sharpe ratio |
| `avg_return` | Average return percentage (converted from PnL) |
| `avg_trades` | Average number of trades per use |
| `top_symbols` | Top 3 symbols where strategy performed best |
| `config_hash` | Configuration fingerprint for tracking |
| `run_date` | Date of strategy calculation |
| `config_details` | JSON snapshot of configuration used |

**Per-Stock Format (`--per-stock` flag - CSV)**

| Column | Description |
|--------|-------------|
| `symbol` | Stock symbol (e.g., RELIANCE, TCS) |
| `strategy_rule_stack` | Human-readable rule combination |
| `edge_score` | Strategy edge score (0-1) |
| `win_pct` | Win percentage (0-1) |
| `sharpe` | Sharpe ratio |
| `total_return` | Average return per trade |
| `total_trades` | Number of trades executed |
| `config_hash` | Configuration fingerprint for tracking |
| `run_date` | Date of strategy calculation |
| `config_details` | JSON snapshot of configuration used |

#### Features

- **Sensible Defaults:** Aggregated leaderboard by default (most useful view)
- **Dual Output Modes:** Choose between aggregated summaries or detailed per-stock records
- **Configuration Tracking:** Both modes include config hash and snapshot for historical context
- **Percentage Returns:** Aggregated mode converts raw PnL to meaningful percentages
- **Historical Preservation:** All past runs maintained with their configurations
- **Automatic Logging:** Saves execution log to `analyze_strategies_log.txt`

#### Example Usage

```bash
# Default: Aggregated leaderboard (most common use case)
python -m kiss_signal analyze-strategies

# Detailed per-stock analysis
python -m kiss_signal analyze-strategies --per-stock

# Custom output with aggregated summary
python -m kiss_signal analyze-strategies --output reports/strategy_summary_2025.csv

# Per-stock analysis with custom output
python -m kiss_signal analyze-strategies --per-stock --output reports/detailed_strategies_2025.csv

# With verbose logging for debugging
python -m kiss_signal analyze-strategies --per-stock --verbose
```

#### When to Use Each Mode

| Use Case | Command | Best For |
|----------|---------|----------|
| **Strategy Research** | Default | Understanding which rule combinations work best overall |
| **Stock-Specific Analysis** | `--per-stock` | Analyzing how strategies perform on individual stocks |
| **Performance Comparison** | Default | Comparing strategy effectiveness across configurations |
| **Detailed Investigation** | `--per-stock` | Debugging strategy performance on specific symbols |
| **Historical Tracking** | Both | Both modes preserve configuration history |

---

### 4. `clear-and-recalculate` - Intelligent Data Management

**Purpose:** Intelligently clear current strategies and recalculate with preservation of historical data (Story 17 implementation).

```bash
python -m kiss_signal clear-and-recalculate [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--force` | `bool` | `false` | Skip confirmation prompt before clearing data |
| `--preserve-all` | `bool` | `false` | Skip clearing phase, run analysis only (useful for adding new data) |
| `--freeze-data` | `str` | `None` | Freeze data at specific date for recalculation (YYYY-MM-DD format) |

#### Intelligent Clearing Logic

1. **Configuration Analysis:** Generates hash of current configuration
2. **Strategy Identification:** Identifies which rule combinations are currently active
3. **Selective Deletion:** Only removes strategies matching current config and active rules
4. **Historical Preservation:** Keeps all strategies from different configurations or rule sets
5. **Fresh Calculation:** Runs new backtest with current configuration

#### Process Flow

1. **Pre-clearing Analysis:**
   - Count total strategies in database
   - Identify strategies matching current configuration
   - Display preservation vs. deletion counts
   - Request confirmation (unless `--force` used)

2. **Intelligent Clearing:**
   - Delete only current-config strategies
   - Preserve all historical data
   - Log detailed operation results

3. **Recalculation:**
   - Run fresh backtesting with current rules
   - Save with new configuration tracking
   - Generate summary statistics

#### Example Usage

```bash
# Interactive clearing with confirmation
python -m kiss_signal clear-and-recalculate

# Automatic clearing without prompts
python -m kiss_signal clear-and-recalculate --force

# Analysis only, no clearing
python -m kiss_signal clear-and-recalculate --preserve-all

# Recalculate with historical data freeze
python -m kiss_signal clear-and-recalculate --freeze-data 2025-01-01

# Verbose logging for troubleshooting
python -m kiss_signal clear-and-recalculate --verbose --force
```

#### Safety Features

- **Configuration Validation:** Ensures config files are valid before clearing
- **Confirmation Prompts:** Requires user confirmation unless `--force` used
- **Detailed Logging:** Shows exactly what will be preserved vs. deleted
- **Error Recovery:** Saves logs even if operation fails
- **Rollback Safety:** Historical data never deleted accidentally

---

## Database Reset and Clean Start

### 5. `reset-database` - Complete Database Reset

**Purpose:** Reset the database to initial state and optionally clean analysis files for a completely fresh start.

#### Manual Reset Steps

Since database reset is a destructive operation, it's implemented as manual steps to prevent accidental data loss:

```bash
# Step 1: Stop any running KISS Signal processes
# (Check task manager if needed)

# Step 2: Backup current database (optional but recommended)
copy data\kiss_signal.db data\kiss_signal.db.backup

# Step 3: Delete the database file
del data\kiss_signal.db

# Step 4: Delete analysis output files (optional)
del test_analysis.csv
del strategy_performance_report.csv
del analyze_strategies_log.txt

# Step 5: Run fresh backtesting to recreate database
python run.py run --verbose

# Step 6: Generate fresh analysis
python run.py analyze-strategies
```

#### Complete Reset with Scripts

For convenience, you can create batch scripts for common reset scenarios:

**Full Reset (Windows batch file - `reset_full.bat`):**
```batch
@echo off
echo WARNING: This will delete all historical data!
set /p confirm="Are you sure? Type 'yes' to continue: "
if /i "%confirm%" NEQ "yes" (
    echo Reset cancelled.
    exit /b 1
)

echo Creating backup...
copy data\kiss_signal.db data\kiss_signal.db.backup > nul 2>&1

echo Deleting database...
del data\kiss_signal.db

echo Deleting analysis files...
del test_analysis.csv > nul 2>&1
del strategy_performance_report.csv > nul 2>&1
del analyze_strategies_log.txt > nul 2>&1
del clear_and_recalculate_log.txt > nul 2>&1

echo Running fresh backtesting...
python run.py run --verbose

echo Generating fresh analysis...
python run.py analyze-strategies

echo Reset complete!
```

**Database Only Reset (Windows batch file - `reset_db_only.bat`):**
```batch
@echo off
echo WARNING: This will delete the database but preserve analysis files!
set /p confirm="Are you sure? Type 'yes' to continue: "
if /i "%confirm%" NEQ "yes" (
    echo Reset cancelled.
    exit /b 1
)

echo Creating backup...
copy data\kiss_signal.db data\kiss_signal.db.backup > nul 2>&1

echo Deleting database...
del data\kiss_signal.db

echo Running fresh backtesting...
python run.py run --verbose

echo Database reset complete!
```

#### When to Use Reset vs. Clear-and-Recalculate

| Use Case | Command | Behavior |
|----------|---------|----------|
| **Configuration changed** | `clear-and-recalculate` | Preserves historical data, clears current config only |
| **Database corruption** | **Reset Database** | Complete fresh start, all data lost |
| **Testing/Development** | `clear-and-recalculate --preserve-all` | No clearing, just fresh calculations |
| **Clean slate needed** | **Reset Database** | Remove all legacy data and start over |
| **Performance issues** | **Reset Database** | Clean database can improve performance |

#### Reset Safety Checklist

Before resetting the database:

- [ ] **Backup Important Data:** Copy `kiss_signal.db` if you might need historical results
- [ ] **Export Current Analysis:** Run `analyze-strategies` to save CSV before reset
- [ ] **Document Configuration:** Note current config settings for reference
- [ ] **Check Dependencies:** Ensure no other processes are accessing the database
- [ ] **Test Configuration:** Verify `config.yaml` and `rules.yaml` are valid

#### Post-Reset Validation

After reset, verify everything works:

```bash
# 1. Check database was recreated
dir data\kiss_signal.db

# 2. Verify strategies were generated
python run.py analyze-strategies --output validation.csv

# 3. Check record count (should have new strategies)
python -c "import sqlite3; conn = sqlite3.connect('data/kiss_signal.db'); print(f'Total strategies: {conn.execute(\"SELECT COUNT(*) FROM strategies\").fetchone()[0]}'); conn.close()"

# 4. Verify configuration tracking (should not be 'legacy')
python -c "import sqlite3; conn = sqlite3.connect('data/kiss_signal.db'); configs = conn.execute(\"SELECT DISTINCT config_hash FROM strategies\").fetchall(); print(f'Config hashes: {[c[0] for c in configs]}'); conn.close()"
```

#### Troubleshooting Reset Issues

**Database file locked:**
```bash
# Check for running processes
tasklist | findstr python

# Force kill if needed (use PID from tasklist)
taskkill /F /PID <process_id>
```

**Permission errors:**
```bash
# Run command prompt as Administrator, or
# Check file permissions on data folder
```

**Configuration errors after reset:**
```bash
# Validate configuration files
python -c "import yaml; yaml.safe_load(open('config.yaml')); yaml.safe_load(open('config/rules.yaml')); print('Config files valid')"
```

---

## Configuration Files

### Main Configuration (`config.yaml`)

Required settings for all CLI operations:

```yaml
universe_path: "data/nifty_large_mid.csv"
historical_data_years: 3
cache_dir: "data/"
cache_refresh_days: 7
hold_period: 20
database_path: "data/kiss_signal.db"
min_trades_threshold: 10
edge_score_weights:
  win_pct: 0.6
  sharpe: 0.4
reports_output_dir: "reports/"
edge_score_threshold: 0.50
```

### Rules Configuration (`config/rules.yaml`)

Defines trading rules and their parameters:

```yaml
signal_rules:
  - name: "bullish_engulfing"
    type: "candlestick"
    # ... rule parameters
  - name: "rsi_oversold"
    type: "momentum"
    # ... rule parameters

filter_rules:
  - name: "volume_filter"
    type: "volume"
    # ... filter parameters
```

---

## Common Usage Patterns

### Daily Workflow

```bash
# 1. Run daily analysis
python -m kiss_signal run --verbose

# 2. Generate monthly strategy summary (aggregated - default)
python -m kiss_signal analyze-strategies --output monthly_strategies.csv

# 3. Generate detailed stock analysis (per-stock)
python -m kiss_signal analyze-strategies --per-stock --output detailed_monthly_strategies.csv
python -m kiss_signal analyze-strategies --output detailed_monthly_strategies.csv
```

### Configuration Changes

```bash
# After updating rules configuration
python -m kiss_signal clear-and-recalculate --force

# For testing new parameters
python -m kiss_signal clear-and-recalculate --preserve-all --freeze-data 2025-01-01
```

### Research and Backtesting

```bash
# Historical analysis with frozen data
python -m kiss_signal run --freeze-data 2024-12-31

# Compare configurations (aggregated view - default)
python -m kiss_signal analyze-strategies --output config_v1_summary.csv
# ... update configuration ...
python -m kiss_signal clear-and-recalculate --force
python -m kiss_signal analyze-strategies --output config_v2_summary.csv

# Compare configurations (detailed view)
python -m kiss_signal analyze-strategies --per-stock --output config_v1_detailed.csv
# ... update configuration ...
python -m kiss_signal clear-and-recalculate --force
python -m kiss_signal analyze-strategies --output config_v2_detailed.csv
```

---

## Error Handling

### Common Exit Codes

- `0`: Success
- `1`: General error (configuration, file access, etc.)

### Error Recovery

All commands include:
- **Graceful Error Handling:** Commands continue where possible
- **Detailed Error Messages:** Clear indication of what went wrong
- **Log Preservation:** Console output saved to log files even on failure
- **Database Safety:** Transactions used to prevent data corruption

### Troubleshooting

1. **Use `--verbose` flag** for detailed debugging information
2. **Check log files** automatically saved by analysis commands
3. **Verify configuration files** are valid YAML format
4. **Ensure database permissions** allow read/write access

---

## Performance Considerations

### Data Caching

- Price data cached based on `cache_refresh_days` setting
- Cache directory configurable via `cache_dir` parameter
- Manual cache clearing may be needed after configuration changes

### Database Optimization

- SQLite database automatically optimized for query performance
- Regular `analyze-strategies` runs help maintain query performance
- Consider backup strategies for production databases

### Memory Usage

- Process symbols sequentially to minimize memory footprint
- Large universes (>500 symbols) may require extended runtime
- Use `--freeze-data` for faster repeated analysis during development

---

## Integration Notes

### Automation

All commands designed for automation:
- Return appropriate exit codes
- Support non-interactive operation with `--force`
- Generate machine-readable output formats (CSV)
- Include comprehensive logging

### CI/CD Integration

```bash
# Example GitHub Actions workflow step
- name: Run KISS Signal Analysis
  run: |
    python -m kiss_signal run --freeze-data 2025-01-01
    python -m kiss_signal analyze-strategies --output results.csv
```

### External Tool Integration

- **CSV exports** compatible with Excel, Python pandas, R
- **Markdown reports** integrate with documentation systems
- **Database format** accessible via standard SQLite tools
- **Log files** compatible with log aggregation systems

---

## Version History

### Current (Story 17)
- ✅ Per-stock strategy analysis
- ✅ Configuration tracking and snapshots
- ✅ Intelligent clearing with historical preservation
- ✅ Enhanced CLI commands with proper error handling

### Previous Versions
- Rule performance analysis
- Basic backtesting and reporting
- SQLite persistence layer
- Configuration-driven approach
