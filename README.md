# MEQSAP - Market Equity Quantitative Strategy Analysis Platform

A comprehensive platform for backtesting quantitative trading strategies using historical market data. MEQSAP provides robust data acquisition, signal generation, backtesting, and reporting capabilities with a user-friendly command-line interface.

## Installation

### Option 1: Development Installation (Recommended)
```bash
pip install -e .
```

### Option 2: Direct Usage (No Installation Required)
You can run MEQSAP directly from the project root using the provided `run.py` script:
```bash
python run.py --help
```

## Quick Start

### 1. Create a Configuration File

Create a YAML configuration file (e.g., `my_strategy.yaml`):

```yaml
# Basic Moving Average Crossover Strategy
ticker: AAPL                    # Stock ticker symbol
start_date: 2022-01-01          # Analysis start date (inclusive)
end_date: 2022-12-31            # Analysis end date (inclusive)
strategy_type: MovingAverageCrossover
strategy_params:
  fast_ma: 10                   # Fast moving average period (days)
  slow_ma: 30                   # Slow moving average period (days)
```

### 2. Run the Analysis

#### Using the run.py script (no installation required):
```bash
# Basic analysis
python run.py analyze my_strategy.yaml

# With detailed reporting
python run.py analyze my_strategy.yaml --report --verbose

# Validate configuration only
python run.py analyze my_strategy.yaml --validate-only
```

#### Using the installed CLI:
```bash
# Basic analysis
meqsap analyze my_strategy.yaml

# With detailed reporting  
meqsap analyze my_strategy.yaml --report --verbose
```

### 3. View Results

MEQSAP will output:
- **Summary Statistics**: Key performance metrics (returns, Sharpe ratio, max drawdown)
- **Trade Analysis**: Entry/exit points and individual trade performance
- **Risk Metrics**: Volatility, drawdown analysis, and risk-adjusted returns
- **Optional PDF Report**: Comprehensive analysis with charts (when using `--report`)

## Available Strategy Types

### MovingAverageCrossover
Implements a trading strategy based on the crossover of two moving averages.

**Required Parameters:**
- `fast_ma`: Fast moving average period in days (must be > 0)
- `slow_ma`: Slow moving average period in days (must be > fast_ma)

**Trading Logic:**
- **Entry Signal**: When fast MA crosses above slow MA (bullish crossover)
- **Exit Signal**: When fast MA crosses below slow MA (bearish crossover)

**Example Configuration:**
```yaml
strategy_type: MovingAverageCrossover
strategy_params:
  fast_ma: 10      # 10-day moving average
  slow_ma: 30      # 30-day moving average
```

## CLI Commands and Options

### `analyze` - Run Strategy Analysis

**Syntax:**
```bash
python run.py analyze CONFIG_FILE [OPTIONS]
# or
meqsap analyze CONFIG_FILE [OPTIONS]
```

**Arguments:**
- `CONFIG_FILE`: Path to YAML configuration file (required)

**Options:**
- `--report`: Generate a comprehensive PDF report after analysis
- `--validate-only`: Only validate the configuration, don't run backtest
- `--output-dir DIR`: Directory for output reports (default: `./reports`)
- `--verbose, -v`: Enable detailed logging and diagnostics
- `--quiet, -q`: Suppress non-essential output (minimal mode)
- `--no-color`: Disable colored terminal output
- `--help, -h`: Show help message

**Examples:**
```bash
# Basic analysis
python run.py analyze config.yaml

# Generate PDF report with verbose output
python run.py analyze config.yaml --report --verbose

# Validate configuration only
python run.py analyze config.yaml --validate-only

# Custom output directory
python run.py analyze config.yaml --report --output-dir ./my_reports

# Quiet mode for scripting
python run.py analyze config.yaml --quiet
```

### `version` - Show Version Information

**Syntax:**
```bash
python run.py version
# or  
meqsap version
```

Shows the current version of MEQSAP.

### Global Help

**Syntax:**
```bash
python run.py --help
# or
meqsap --help
```

Shows available commands and global options.

## Configuration File Format

MEQSAP uses YAML configuration files to define strategy parameters and analysis settings.

### Required Fields

```yaml
ticker: SYMBOL                  # Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)
start_date: YYYY-MM-DD         # Analysis start date (inclusive)
end_date: YYYY-MM-DD           # Analysis end date (inclusive)  
strategy_type: STRATEGY_NAME   # Strategy to backtest
strategy_params:               # Strategy-specific parameters
  param1: value1
  param2: value2
```

### Field Details

**`ticker`**: Stock symbol to analyze
- Format: Alphanumeric with dots and hyphens allowed
- Examples: `AAPL`, `BRK.B`, `BTC-USD`

**`start_date` / `end_date`**: Date range for analysis
- Format: `YYYY-MM-DD` (ISO format)
- **Important**: Both dates are INCLUSIVE
- Example: `start_date: 2022-01-01` and `end_date: 2022-12-31` includes both January 1st and December 31st
- Minimum range: Must provide enough data for the strategy (e.g., 30+ days for a 30-day moving average)

**`strategy_type`**: Currently supported strategies
- `MovingAverageCrossover`: Moving average crossover strategy

**`strategy_params`**: Strategy-specific configuration
- See "Available Strategy Types" section for required parameters per strategy

### Example Configurations

#### Short-term Trading (5-day vs 15-day MA)
```yaml
ticker: TSLA
start_date: 2023-01-01
end_date: 2023-12-31
strategy_type: MovingAverageCrossover
strategy_params:
  fast_ma: 5
  slow_ma: 15
```

#### Long-term Investing (50-day vs 200-day MA)
```yaml
ticker: SPY
start_date: 2020-01-01
end_date: 2023-12-31
strategy_type: MovingAverageCrossover
strategy_params:
  fast_ma: 50
  slow_ma: 200
```

#### Cryptocurrency Analysis
```yaml
ticker: BTC-USD
start_date: 2022-06-01
end_date: 2023-06-01
strategy_type: MovingAverageCrossover
strategy_params:
  fast_ma: 10
  slow_ma: 30
```

## Output and Reporting

### Console Output

MEQSAP provides rich, formatted output in the terminal:

#### Default Mode
- Strategy configuration summary
- Data acquisition progress
- Backtest execution status  
- Key performance metrics
- Trade summary statistics

#### Verbose Mode (`--verbose`)
- Detailed logging of all operations
- Data validation steps
- Signal generation diagnostics
- Extended performance metrics
- Error details and stack traces

#### Quiet Mode (`--quiet`)
- Minimal output for scripting
- Only essential results and errors
- No progress indicators or detailed logs

### PDF Reports (`--report`)

When using the `--report` option, MEQSAP generates comprehensive PDF reports including:

- **Executive Summary**: Key performance metrics and conclusions
- **Strategy Details**: Configuration and parameters used
- **Performance Charts**: Price charts with entry/exit signals
- **Risk Analysis**: Drawdown charts and risk metrics
- **Trade Analysis**: Detailed trade-by-trade breakdown
- **Statistical Summary**: Complete performance statistics

Reports are saved to the output directory (default: `./reports/`) with timestamps.

### Output Directory Structure

```
reports/
├── AAPL_MovingAverageCrossover_20231215_143022.pdf
├── AAPL_MovingAverageCrossover_20231215_143022_trades.csv
└── summary_stats.json
```

## Data Acquisition & Caching

MEQSAP handles market data acquisition automatically with intelligent caching.

### Features
- **Automatic Data Fetching**: Uses Yahoo Finance (yfinance) for market data
- **Local Caching**: Stores data in Parquet format to avoid redundant downloads
- **Data Integrity Checks**:
  - Validates no missing/NaN values
  - Ensures complete date range coverage
  - Checks data freshness (within 2 days for recent data)
- **Error Handling**: Clear messages for invalid tickers, missing data, or API issues

### Cache Location
Data is cached in: `data/cache/` directory

### Manual Cache Management
```python
from meqsap.data import clear_cache
clear_cache()  # Clear all cached data
```

## Error Handling and Troubleshooting

MEQSAP provides comprehensive error handling with helpful recovery suggestions.

### Common Issues and Solutions

#### Configuration Errors
```bash
Error: Invalid parameters for strategy MovingAverageCrossover: slow_ma must be greater than fast_ma
```
**Solution**: Ensure `slow_ma > fast_ma` in your configuration

#### Data Issues
```bash
Error: No data found for ticker 'INVALID_SYMBOL'
```
**Solution**: Check ticker symbol spelling and ensure it exists on Yahoo Finance

#### Insufficient Data
```bash
Error: Insufficient data: need at least 30 bars, got 20
```
**Solution**: Extend your date range or reduce the moving average periods

### Debug Mode
Use `--verbose` flag for detailed error information and troubleshooting steps.

## Examples and Use Cases

### 1. Quick Strategy Test
```bash
# Test a simple strategy with minimal output
python run.py analyze examples/ma_crossover.yaml --quiet
```

### 2. Comprehensive Analysis
```bash
# Full analysis with PDF report and detailed logging
python run.py analyze my_config.yaml --report --verbose --output-dir ./analysis_results
```

### 3. Configuration Validation
```bash
# Check if your configuration is valid before running
python run.py analyze my_config.yaml --validate-only
```

### 4. Batch Analysis (Scripting)
```bash
# Run multiple analyses in quiet mode for automation
for config in configs/*.yaml; do
    python run.py analyze "$config" --quiet --report
done
```

## Development

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Setup Development Environment

1. **Clone the repository** (if applicable):
```bash
git clone <repository-url>
cd meqsap
```

2. **Install in development mode**:
```bash
pip install -e .
```

3. **Install development dependencies**:
```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_config.py
pytest tests/test_backtest.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src/meqsap
```

### Code Quality

The project uses:
- **Type Hints**: All code includes comprehensive type annotations
- **Pydantic**: For configuration validation and data models
- **Error Handling**: Comprehensive exception handling with custom error types
- **Documentation**: Extensive docstrings and inline comments

### Project Structure

```
meqsap/
├── src/meqsap/           # Main package
│   ├── __init__.py       # Package initialization
│   ├── cli.py           # Command-line interface
│   ├── config.py        # Configuration handling
│   ├── data.py          # Data acquisition and caching
│   ├── backtest.py      # Strategy backtesting engine
│   ├── reporting.py     # Report generation
│   └── exceptions.py    # Custom exception classes
├── tests/               # Test suite
├── examples/            # Example configurations
├── docs/               # Documentation
├── run.py              # Convenient entry point
└── README.md           # This file
```

## API Reference

For detailed API documentation, see the docstrings in the source code:

- `config.py`: Configuration loading and validation
- `data.py`: Market data acquisition and caching
- `backtest.py`: Strategy implementation and backtesting
- `reporting.py`: Report generation and formatting
- `cli.py`: Command-line interface

## Support and Contributing

### Getting Help

1. **Check the examples**: Look at `examples/` directory for sample configurations
2. **Use verbose mode**: Run with `--verbose` for detailed diagnostics
3. **Check documentation**: Review this README and inline code documentation

### Reporting Issues

When reporting issues, please include:
- Your configuration file
- Complete error messages (use `--verbose`)
- Python version and operating system
- Steps to reproduce the issue

### Contributing

1. Follow the existing code style and patterns
2. Add tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

MIT License - see LICENSE file for details.

---

## Quick Reference Card

### Essential Commands
```bash
# Basic usage
python run.py analyze config.yaml

# With reporting
python run.py analyze config.yaml --report --verbose

# Validation only  
python run.py analyze config.yaml --validate-only

# Get help
python run.py --help
python run.py analyze --help
```

### Sample Configuration
```yaml
ticker: AAPL
start_date: 2022-01-01
end_date: 2022-12-31
strategy_type: MovingAverageCrossover
strategy_params:
  fast_ma: 10
  slow_ma: 30
```

### Common Issues
- **slow_ma must be greater than fast_ma**: Fix parameter ordering
- **Insufficient data**: Extend date range or reduce MA periods
- **No data found**: Check ticker symbol validity
- **Import errors**: Ensure you're in project root directory

For more help: `python run.py --help`
