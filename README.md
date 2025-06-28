# Signal CLI – Simple Signal Generation for NSE Equities

A streamlined tool for backtesting and generating trading signals for Indian equities. Provides robust data acquisition, signal generation, backtesting, and reporting via a simple CLI.

## Quick Start

1. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Run the app:**
    ```cmd
    quickedge run
    # or
    python run.py run
    ```

3. **Example config:**
    ```yaml
    ticker: AAPL
    start_date: 2022-01-01
    end_date: 2022-12-31
    strategy_type: MovingAverageCrossover
    strategy_params:
      fast_ma: 10
      slow_ma: 30
    ```

4. **Analyze:**
    ```cmd
    python run.py analyze my_strategy.yaml
    python run.py analyze my_strategy.yaml --report --verbose
    ```

## CLI Options
- `--report`: Generate PDF report
- `--validate-only`: Only validate config
- `--output-dir DIR`: Output directory
- `--verbose, -v`: Detailed logs
- `--quiet, -q`: Minimal output
- `--help, -h`: Show help

## Strategy: MovingAverageCrossover
- `fast_ma`: Fast MA period (>0)
- `slow_ma`: Slow MA period (>fast_ma)
- Entry: fast MA crosses above slow MA
- Exit: fast MA crosses below slow MA

## Output
- Console: summary stats, trade analysis, risk metrics
- PDF/CSV: in `reports/` directory

## Data & Caching
- Auto-fetches/caches Yahoo Finance data in `data/cache/`
- Use `from meqsap.data import clear_cache` to clear cache

## Troubleshooting
- **slow_ma > fast_ma**: Fix config
- **Insufficient data**: Extend date range or reduce MA
- **No data**: Check ticker
- **Import errors**: Run from project root

For help: `python run.py --help`

## Development
- Python 3.9+
- Install dev deps: `pip install -e .[dev]`
- Run tests: `pytest`
- Code: type hints, Pydantic, docstrings

## Project Structure
- `src/` – main code
- `tests/` – tests
- `docs/` – docs
- `run.py` – entry point

## License
MIT License
