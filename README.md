# KISS Signal CLI – Keep-It-Simple Signal Generation for NSE Equities

A streamlined tool for backtesting and generating trading signals for Indian equities. Provides robust data acquisition, rule-based signal generation, backtesting, and reporting via a simple CLI.

## Quick Start

1. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Run the analysis:**
    ```cmd
    python run.py run
    ```

3. **View results:**
    ```cmd
    python run.py analyze-strategies
    ```

## CLI Commands

### Main Commands
- `run`: Run the full backtesting pipeline
- `analyze-strategies`: Generate CSV report of strategy performance
- `analyze-rules`: Generate markdown report of individual rule performance
- `clear-and-recalculate`: Clear database and recalculate all strategies

### Options
- `--verbose, -v`: Detailed logs
- `--help, -h`: Show help
- `--config`: Path to config file (default: config.yaml)
- `--rules`: Path to rules config file (default: config/rules.yaml)
- `--freeze-date`: Use historical date for testing (YYYY-MM-DD)
- `--force`: Skip confirmation prompts

## Strategy Performance Analysis

The CLI provides detailed analysis of strategy performance:

### Strategy Performance Report
```cmd
# Generate per-stock strategy analysis (default)
python run.py analyze-strategies --output strategy_performance_report.csv

# Include strategies with fewer trades using --min-trades option
python run.py analyze-strategies --min-trades 5 --output low_threshold_report.csv

# Show ALL strategies, even those with very few trades
python run.py analyze-strategies --min-trades 0 --output complete_analysis.csv

# Generate aggregated strategy performance summary
python run.py analyze-strategies --aggregate --output aggregated_summary.csv
```

#### New --min-trades Feature
The `--min-trades` parameter controls which strategies are included in the analysis:
- **Default (10)**: Only includes strategies with 10+ trades for statistical significance
- **Custom value**: Set your own threshold (e.g., `--min-trades 5`)
- **Show all (0)**: Include ALL strategies regardless of trade count (`--min-trades 0`)

This addresses the common issue where strategies are filtered out due to insufficient trades, allowing you to:
- See the complete picture of rule performance
- Identify highly selective but profitable strategies
- Make informed decisions about rule effectiveness

#### Report Metrics
Generates a CSV report with the following metrics:
- **strategy_rule_stack**: The combination of rules (e.g., "bullish_engulfing_reversal + filter_with_rsi_oversold")
- **frequency**: Number of symbols where this strategy was optimal
- **avg_edge_score**: Average edge score (weighted combination of win rate and Sharpe ratio)
- **avg_win_pct**: Average win percentage (decimal, e.g., 0.65 = 65%)
- **avg_sharpe**: Average Sharpe ratio
- **avg_pnl_per_trade**: Average profit/loss per trade in currency units
- **avg_return_pct**: Average return percentage per trade
- **avg_trades**: Average number of trades per symbol
- **top_symbols**: Most frequently appearing symbols for this strategy

### Individual Rule Performance
```cmd
python run.py analyze-rules --output rule_performance_analysis.md
```
Analyzes performance of individual rules across all strategies.

### Database Management
```cmd
python run.py clear-and-recalculate --force
```
Clears all existing strategies from the database and recalculates them with current parameters. Useful when:
- Rule parameters have been modified
- Strategy logic has been updated
- You want to test different configurations

## Technical Analysis Rules

The system supports various technical analysis rules:

### Entry Rules
- **engulfing_pattern**: Bullish engulfing candlestick pattern
- **sma_crossover**: Simple moving average crossover
- **rsi_oversold**: RSI-based oversold signals
- **volume_spike**: Volume spike detection
- **hammer_pattern**: Hammer candlestick pattern
- **macd_crossover**: MACD signal line crossover

### Filter Rules
- **price_above_sma**: Price above moving average filter
- **rsi_oversold**: RSI momentum confirmation
- **volume_spike**: Volume confirmation

### Exit Rules
- **stop_loss_pct**: Percentage-based stop loss
- **take_profit_pct**: Percentage-based take profit
- **sma_cross_under**: Moving average exit signal

## Configuration

### Main Configuration (config.yaml)
```yaml
database_path: "data/kiss_signal.db"
cache_dir: "data"
cache_refresh_days: 1
historical_data_years: 2
edge_score_threshold: 0.1
hold_period: 20
min_trades_threshold: 10
initial_capital: 100000.0
symbols_path: "data/nifty_large_mid.csv"
rules_config_path: "config/rules.yaml"
```

### Rules Configuration (config/rules.yaml)
Defines the baseline rule and filter layers:
```yaml
baseline:
  name: "bullish_engulfing_reversal"
  type: "engulfing_pattern"
  params:
    min_body_ratio: 1.2

layers:
  - name: "filter_with_rsi_oversold"
    type: "rsi_oversold"
    params:
      period: 14
      oversold_threshold: 30.0
```

## Data & Caching
- Auto-fetches NSE data from Yahoo Finance
- Caches data in `data/` directory
- Refresh controlled by `cache_refresh_days` setting
- Supports freeze dates for deterministic testing

## Troubleshooting

### Common Issues
- **Low win rates (< 5%)**: Check rule parameters, consider loosening filters
- **No strategies found**: Lower `edge_score_threshold` or `min_trades_threshold`
- **Database errors**: Delete `data/kiss_signal.db` and run `clear-and-recalculate`
- **Data issues**: Check symbol file and internet connection

### Performance Issues
- **Slow backtesting**: Reduce `historical_data_years` or number of symbols
- **Memory usage**: Process symbols in batches (modify CLI if needed)

### Debugging
- Use `--verbose` flag for detailed logs
- Check `analyze_strategies_log.txt` for strategy analysis execution details
- Check `clear_and_recalculate_log.md` for database recalculation details
- Monitor database size growth in `data/kiss_signal.db`

## Development

### Requirements
- Python 3.9+
- Required packages: pandas, numpy, vectorbt, typer, rich, pydantic, yfinance

### Setup
```bash
pip install -e .
```

### Testing
```bash
pytest tests/
mypy src/
```

### Code Quality
- Type hints required for all functions
- Pydantic models for configuration
- Comprehensive docstrings
- Follow KISS principles (Keep-It-Simple)

## Project Structure
```
src/kiss_signal/
├── __init__.py
├── cli.py              # CLI entry point
├── config.py           # Configuration management
├── data.py             # Data acquisition
├── backtester.py       # Backtesting engine
├── rules.py            # Technical analysis rules
├── persistence.py      # Database operations
├── reporter.py         # Report generation
└── performance.py      # Performance monitoring

config/
├── rules.yaml          # Rules configuration
tests/                  # Test suite
data/                   # Data cache and database
```

## Architecture

The system follows a modular monolith pattern:
- **CLI Layer**: User interface and command orchestration
- **Data Layer**: Market data acquisition and caching
- **Rules Layer**: Technical analysis implementations
- **Backtesting Layer**: Strategy evaluation using vectorbt
- **Persistence Layer**: SQLite database operations
- **Reporting Layer**: Analysis and report generation

## License
MIT License
