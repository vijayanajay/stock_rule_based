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

## Test Coverage Enhancement Patterns (Issue #4 - Reporter.py Coverage >88%)

### Key Patterns for Achieving High Test Coverage

1. **Exit Condition Testing**:
   - Always test invalid entry prices (0, negative, None, missing fields)
   - Test all condition types: stop_loss_pct, take_profit_pct, ATR-based conditions
   - Test both dict-style and object-style conditions
   - Mock external dependencies (rules module) for isolation
   - Test exception handling in condition calculations

2. **Database Function Testing**:
   - Test with non-existent database paths
   - Test with None database paths
   - Test with malformed JSON data in database
   - Test with empty result sets
   - Test connection errors and SQL errors separately

3. **Formatting Function Edge Cases**:
   - Test with None/missing values in all fields
   - Test with extreme numeric values (inf, -inf, nan)
   - Test with special characters requiring CSV escaping
   - Test with empty input data
   - Test with malformed input structures

4. **Position Processing Coverage**:
   - Test successful scenarios first
   - Test data unavailability scenarios
   - Test calculation errors and exceptions
   - Test with various date formats and invalid dates
   - Test benchmark data integration errors

5. **Error Handling Patterns**:
   - Use `patch` to simulate specific exceptions
   - Test both expected errors and unexpected errors
   - Verify functions return appropriate defaults (None, empty list, etc.)
   - Test logging behavior where applicable

### Common AI Testing Pitfalls to Avoid

- **Don't assume dependencies are available**: Mock external functions and modules
- **Test error paths thoroughly**: Exception handling often has low coverage
- **Cover all conditional branches**: Use both positive and negative test cases
- **Test with realistic malformed data**: Real-world data often has unexpected formats
- **Verify edge cases in calculations**: Division by zero, None values, extreme numbers