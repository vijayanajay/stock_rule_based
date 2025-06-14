## Structural Issue Identified

Data from `data.py` was assumed to always have a `DateTimeIndex`, but edge cases in `yfinance` responses sometimes yielded a `RangeIndex` under certain error conditions, breaking `vectorbt` assumptions in `run_backtest`.

### Proposed Fix

1. **File**: `data_manager.py`
   - **Line**: Add validation for index type before processing data.
   ```python
   if not isinstance(df.index, pd.DateTimeIndex):
       raise ValueError("DataFrame index must be a DateTimeIndex")
   ```

### Memory Entry

- **Issue**: Assumed `DateTimeIndex` in `data.py` led to failures in `run_backtest`.
- **Fix**: Added index validation to ensure compatibility with `vectorbt` assumptions.
- **Lesson**: Always validate data integrity across module boundaries to prevent structural issues.