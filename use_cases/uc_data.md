| KISS | Version: 1.0 |
|---|---|
| Use Case Specification KS_DATA_BS_UC004 – Get Market Price Data | Date: 08/07/24 |

# KS_DATA_BS_UC004 – Get Market Price Data

**1. Brief Description**

This use case allows an actor to retrieve historical Open, High, Low, Close, and Volume (OHLCV) price data for a given stock symbol. It intelligently utilizes a local file-based cache to minimize redundant network requests to the data provider.

The use case can be called:
- By the Backtester module to get historical data for strategy evaluation.
- By the Reporter module to get the latest price for open positions.

**2. Actors**

**2.1 Primary Actors**
1. **Backtester Module** – Requires long-term historical data for backtesting.
2. **Reporter Module** – Requires recent price data for performance calculation.

**2.2 Secondary Actors**
- yfinance API
- File System Cache

**3. Conditions**

**3.1 Pre-Condition**
- The stock symbol is valid.
- A cache directory is available for reading and writing.

**3.2 Post Conditions on success**
1. A pandas DataFrame containing the requested price data is returned.
2. The DataFrame is indexed by date and contains lowercase columns: `open`, `high`, `low`, `close`, `volume`.
3. The local cache for the symbol is created or updated if necessary.

**3.3 Post Conditions on Failure**
1. An exception (`FileNotFoundError`, `ValueError`) is raised.
2. No data is returned.

**4. Trigger**

1. A request for price data is issued by a Primary Actor. This request must contain:
    a. The stock `symbol`.
    b. The path to the `cache_dir`.
    c. Optional parameters like `years` of history or a `freeze_date`.

**5. Main Flow: KS_DATA_BS_UC004.MF – Get Market Price Data (Cache Hit)**

10. The system checks if the cache file for the symbol needs to be refreshed based on its modification time and the `refresh_days` configuration.
    <<_needs_refresh(symbol, cache_dir, refresh_days) = False>>
    *See Alternative Flow 1: KS_DATA_BS_UC004.AF01 – Cache Miss or Stale Data*

20. The system loads the price data from the existing CSV cache file.
    <<data = _load_symbol_cache(symbol, cache_dir)>>

30. The system applies any date filtering based on `start_date`, `end_date`, or `freeze_date`.
    <<data = data[data.index <= pd.to_datetime(freeze_date)]>>

40. The system returns the pandas DataFrame to the primary actor.

99. The use case ends.

**6. Flows (Exception/Alternative/Extension)**

**6.1 Alternative Flow 1: KS_DATA_BS_UC004.AF01 – Cache Miss or Stale Data**

10. At **step 10 of the main flow**, the system determines the cache file is missing or stale.
    10.10. The system checks if cache file exists using Path.exists().
    <<cache_file = cache_dir / f"{symbol}.NS.csv"; cache_file.exists() = False>>
    10.20. If file exists, the system compares modification time with refresh threshold.
    <<file_modified = datetime.fromtimestamp(cache_file.stat().st_mtime)>>
    <<cutoff = datetime.now() - timedelta(days=refresh_days)>>
    <<file_modified < cutoff = True>>
    10.30. In freeze mode, the system raises FileNotFoundError if cache doesn't exist.
    <<if freeze_date and not cache_file.exists(): raise FileNotFoundError(f"Cached data not found for {symbol} (freeze mode)")>>

20. The system downloads fresh data from the `yfinance` API with retry logic.
    20.10. The system imports yfinance locally to avoid startup cost and reduce cold-start time.
    <<import yfinance as yf>>
    20.20. The system adds .NS suffix to symbol for yfinance compatibility, handling indices like ^NSEI.
    <<symbol_with_suffix = f"{symbol}.NS" if not symbol.endswith('.NS') and not symbol.startswith('^') else symbol>>
    20.30. NSE symbols require .NS suffix while indices like ^NSEI are used as-is for Yahoo Finance API.
    20.40. The system calculates date range based on years parameter and freeze_date.
    <<end_date = freeze_date or date.today(); start_date = end_date - timedelta(days=years * 365)>>
    20.50. The freeze_date parameter enables deterministic backtesting by fixing the data cutoff point.
    20.60. The system attempts download with up to 3 retries and exponential backoff (2^attempt seconds).
    <<for attempt in range(3): data = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True); if data is not None: break; time.sleep(2 ** attempt)>>
    20.70. The auto_adjust=True parameter applies stock splits and dividend adjustments automatically.
    20.80. Exponential backoff handles temporary network issues and API rate limiting gracefully.
    20.90. The system resets index to get 'Date' column and standardizes column names to lowercase.
    <<data = data.reset_index(); data.columns = [col[0].lower() if isinstance(col, tuple) else str(col).lower() for col in data.columns]>>
    20.100. MultiIndex columns from yfinance are flattened to simple lowercase names for consistency.
    20.110. The system ensures required columns exist: date, open, high, low, close, volume.
    <<required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']; if not all(col in data.columns for col in required_columns): return None>>
    20.120. The system converts data types: datetime for date, numeric for OHLC, Int64 for volume.
    <<data['date'] = pd.to_datetime(data['date']); data['volume'] = pd.to_numeric(data['volume'], errors='coerce').astype('Int64')>>
    20.130. Int64 type handles NaN values in volume data properly unlike standard int64.
    *See Exception Flow 1: KS_DATA_BS_UC004.XF01 – Data Download Failed*

30. The system validates the quality of the downloaded data using _validate_data_quality function.
    30.10. The system checks for empty data to prevent processing invalid datasets.
    <<if data.empty: logger.warning(f"Empty data for {symbol}"); return False>>
    30.20. The system checks for negative prices in OHLC columns which indicate data corruption.
    <<price_cols = ['open', 'high', 'low', 'close']; negative_prices = (data[price_cols] < 0).any().any()>>
    <<if negative_prices: logger.warning(f"Negative prices detected for {symbol}"); return False>>
    30.30. The any().any() pattern checks if any negative value exists across all price columns.
    30.40. The system checks for excessive zero-volume days (>10% of data) indicating illiquid or delisted stocks.
    <<if (data['volume'] == 0).sum() > len(data) * 0.1: logger.warning(f"High zero-volume days for {symbol}"); return False>>
    30.50. Zero-volume threshold of 10% filters out stocks with insufficient trading activity.
    30.60. The system checks for large data gaps (>5 consecutive days) that could affect technical analysis.
    <<max_gap_days = data.sort_values('date')['date'].diff().dt.days.max()>>
    <<if pd.notna(max_gap_days) and max_gap_days > 5: logger.warning(f"Large data gap detected for {symbol}: {max_gap_days} days"); return False>>
    30.70. The diff().dt.days calculation finds the maximum gap between consecutive trading days.
    30.80. Data gaps larger than 5 days suggest missing data that could skew backtesting results.
    30.90. The pd.notna() check handles edge cases where diff() returns NaN values.
    *See Exception Flow 2: KS_DATA_BS_UC004.XF02 – Data Quality Validation Failed*

40. The system saves the validated, fresh data to the cache file using _save_symbol_cache function.
    40.10. The system writes data to CSV format without index to preserve date column.
    <<cache_file = cache_dir / f"{symbol}.NS.csv"; data.to_csv(cache_file, index=False)>>
    40.20. The system handles save errors gracefully and logs failures.
    <<try: data.to_csv(cache_file, index=False); return True except Exception as e: logger.error(f"Failed to save cache for {symbol}: {e}"); return False>>

50. The flow continues from **step 30 of the main flow**.

**6.2 Exception Flow 1: KS_DATA_BS_UC004.XF01 – Data Download Failed**

10. At **step 20 of the alternative flow**, the `yfinance` API call fails or returns no data.
    <<_fetch_symbol_data(...) = None>>
20. The system raises a `ValueError` indicating the data fetch failed.
99. The use case ends.

**6.3 Exception Flow 2: KS_DATA_BS_UC004.XF02 – Data Quality Validation Failed**

10. At **step 30 of the alternative flow**, the downloaded data does not pass quality checks.
    <<_validate_data_quality(...) = False>>
20. The system raises a `ValueError` indicating the data is invalid.
99. The use case ends.

**7. Notes / Assumptions**

- The use case assumes network connectivity is available when a cache refresh is needed.
- yfinance import is deferred using local import to avoid startup cost when cache hits occur.
- Data standardization ensures consistent lowercase column names across all cached files.
- Cache files use CSV format with date column (not index) for easier manual inspection and debugging.
- Retry logic with exponential backoff (2^attempt seconds) handles temporary network issues and API rate limits.
- Quality validation prevents corrupted data from entering the cache and affecting backtests.
- In freeze mode, no network requests are made to ensure deterministic backtesting results.
- The _load_symbol_cache function handles both date column and date index formats for backward compatibility.
- MultiIndex columns from yfinance are flattened to simple lowercase column names.
- Volume data uses Int64 type to handle NaN values properly.
- Date filtering is applied after cache loading to support various date range requirements.
- The system logs warnings for limited data (< 50 rows) but continues processing.
- NSE symbols automatically get .NS suffix while indices like ^NSEI are handled specially.

**8. Issues**

| No: | Description: | Date | Action: | Status |
|---|---|---|---|---|
| 1. | | | | |

**9. Revision History**

| Date | Rev | Who | Description | Reference |
|---|---|---|---|---|
| 08/07/24 | 1.0 | AI | Initial document creation. | |

**10. Reference Documentation**

| Document Name | Version | Description | Location |
|---|---|---|---|
| `src/kiss_signal/data.py` | | Source code for the data module with yfinance integration and caching logic. | Git Repository |
| `yfinance` | | Third-party library for downloading Yahoo Finance data. | PyPI |
| `pandas` | | Data manipulation library for DataFrame operations. | PyPI |
