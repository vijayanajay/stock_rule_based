<!-- Status: Completed -->
# Story: Data Acquisition and Caching Module Implementation

## Description
Implement the data module for MEQSAP. This module will acquire historical OHLCV market data for a specified ticker using yfinance, implement a file-based caching system, and perform data integrity checks. It must be fully independent and follow the modular monolith pattern.

## Acceptance Criteria
1. Data module can download historical OHLCV data for a ticker and date range using yfinance
2. Data is cached locally (e.g., Parquet or Feather format) to avoid redundant downloads
3. On cache miss, data is fetched from yfinance and stored in the cache
4. On cache hit, data is loaded from the cache without calling yfinance
5. Data integrity checks are performed: no NaN values, correct date range, and data freshness
6. Clear error handling for bad tickers, missing data, or API issues
7. Unit tests cover all core and edge cases
8. Documentation is added for module usage and configuration

## Implementation Details

### Data Module
- Create `src/meqsap/data.py` as a new module
- Implement a function to fetch data for a given ticker, start_date, and end_date
- Use yfinance to download data if not cached
- Store and load cached data using Parquet or Feather (choose one, document rationale)
- Implement data integrity checks:
  - Ensure no missing (NaN) values in the returned DataFrame
  - Ensure the data covers the requested date range
  - Optionally, check that the most recent data is not stale (e.g., within 2 days of today for non-weekends)
- Raise clear, user-friendly errors for all failure modes
- Ensure the module is independent and does not import from other MEQSAP modules except config for the validated config object

### Caching
- Use a dedicated cache directory (e.g., `data/cache/` under project root)
- Cache key should be based on ticker and date range
- On repeated requests for the same ticker and range, load from cache
- Provide a function to clear the cache (for testing and user diagnostics)

### Unit Testing
- Add tests in `tests/test_data.py`
- Test cache hit, cache miss, data integrity failures, and error handling

### Documentation
- Add docstrings to all public functions and classes
- Update README.md with a section on data acquisition and caching

## Tasks
- [ ] Create `src/meqsap/data.py` and implement data acquisition logic:
    - Define `fetch_market_data(ticker: str, start_date: date, end_date: date) -> pandas.DataFrame`
    - Import `yfinance` and `pandas`
    - Implement date parsing and DataFrame normalization
- [ ] Implement file-based caching:
    - Define cache directory constant (`data/cache/`) and ensure it exists
    - Implement `cache_key(ticker, start_date, end_date) -> str` generation
    - Implement `load_from_cache(key: str) -> pandas.DataFrame` and `save_to_cache(df: pandas.DataFrame, key: str)` using Parquet
- [ ] Implement data integrity checks:
    - Verify no NaN values in the DataFrame; raise `DataError` if found
    - Confirm DataFrame covers the full requested date range; raise error on gaps
    - Check data freshness: last available date >= end_date and within 2 days of today
- [ ] Add error handling for all failure modes:
    - Handle `yfinance` download errors and wrap them in `DataError`
    - Handle invalid ticker symbols and missing data scenarios with clear messages
    - Provide suggestions for retry or checking ticker format
- [ ] Add unit tests in `tests/test_data.py`:
    - Test cache miss: fetch data from yfinance and save to cache
    - Test cache hit: load data from cache without calling yfinance (use mocking)
    - Test NaN detection and incomplete date range errors
    - Test stale data freshness error
    - Test `clear_cache()` function removes cached files
- [ ] Add/Update documentation:
    - Add docstrings for all public functions (`fetch_market_data`, `clear_cache`, etc.)
    - Update `README.md` with a "Data Acquisition & Caching" section and usage examples

## Definition of Done
1. Data module is implemented and fully tested
2. Caching works as specified
3. Data integrity checks are enforced
4. All tests pass
5. Documentation is complete
6. Code follows project standards and is independent

### Pseudocode

**Component:** `Data Module`
**Function:** `fetch_market_data`

**Inputs:**
* `ticker` (str): The stock ticker symbol to download data for.
* `start_date` (date): The start of the desired data range.
* `end_date` (date): The end of the desired data range.

**Output:**
* A `pandas.DataFrame` containing OHLCV data for `ticker` from `start_date` to `end_date`.

**Steps:**
1. **Generate cache key.**
   * Call `cache_key(ticker, start_date, end_date)` to create a unique identifier.
2. **Attempt cache load.**
   * If `load_from_cache(key)` succeeds, return the cached DataFrame immediately.
3. **Download data from yfinance.**
   * Use `yfinance.download(ticker, start=start_date, end=end_date)`.
   * If download fails, raise `DataError` with details.
4. **Normalize DataFrame.**
   * Reset index and rename columns to standard OHLCV names.
5. **Perform integrity checks.**
   * Verify no NaN values; if found, raise `DataError("Missing data points detected")`.
   * Ensure DataFrame covers every date in the range; if gaps exist, raise `DataError("Data gaps detected")`.
6. **Save to cache.**
   * Call `save_to_cache(normalized_df, key)` to write Parquet file.
7. **Return the DataFrame.**
   * Return `normalized_df` to the caller.
