# Story 002: Data Manager & NSE Data Fetching

**Status:** InProgress  
**Estimated Story Points:** 8  
**Priority:** High (Blocks all backtesting work)  
**Created:** 2025-06-15  
**Prerequisites:** Story 001 (Project Foundation) ✅ Complete  

## User Story
As a technical trader, I want the data manager to automatically fetch and cache NSE equity price data so that I can run backtesting and signal generation with up-to-date market data.

## Acceptance Criteria

### AC1: Universe Data Management
- [x] Create sample `data/nifty_large_mid.csv` with 20-30 liquid NSE symbols
- [x] Implement universe file loading and validation in `DataManager`
- [x] Support `.NS` suffix addition for yfinance compatibility  
- [x] Validate symbols exist and are tradeable before fetching
- [x] Clear error messages for malformed or missing universe files

### AC2: Price Data Fetching & Caching
- [x] Implement `yfinance`-based data fetching for NSE symbols
- [x] Cache OHLCV data in `data/cache/` directory as CSV files
- [x] Support configurable historical data years (default: 3 years)
- [x] Implement intelligent refresh logic (don't re-fetch recent data)
- [x] Handle yfinance errors gracefully with clear user feedback

### AC3: Data Serving & Validation  
- [x] Implement `get_price_data()` method with proper DataFrame output
- [x] Return standardized columns: `['date', 'open', 'high', 'low', 'close', 'volume']`
- [x] Handle missing data gaps with appropriate interpolation or warnings
- [x] Support date range filtering for backtesting periods
- [x] Validate data quality (no negative prices, volume sanity checks)

### AC4: Freeze Date Support
- [x] Implement `--freeze-data YYYY-MM-DD` functionality
- [x] When freeze date is set, serve cached data only up to that date
- [x] Prevent data fetching beyond freeze date during backtesting
- [x] Display freeze date status clearly in CLI output
- [x] Support freeze date validation and error handling

### AC5: Progress Feedback & Logging
- [x] Rich progress bars during data fetching operations
- [x] Detailed logging of fetch operations, cache hits/misses
- [x] Clear error messages for network issues, invalid symbols
- [x] Verbose mode shows per-symbol fetch details and timing
- [x] Cache performance statistics in debug logs

## Definition of Done
1. ✅ Sample universe file `data/nifty_large_mid.csv` created with valid NSE symbols
2. ✅ `DataManager.refresh_market_data()` successfully fetches and caches data
3. ✅ `DataManager.get_price_data()` serves cached data with proper schema
4. ✅ `--freeze-data` functionality works correctly for backtesting
5. ✅ All network and file I/O errors are handled gracefully
6. ✅ CLI shows clear progress during data operations
7. ✅ Data validation catches and reports corrupted/missing data
8. ✅ Cache directory structure is organized and human-readable
9. ✅ `pytest` passes with new data manager tests
10. ✅ `mypy` passes with proper type hints throughout
11. ✅ Data fetching completes in <20 seconds for 30 symbols
12. ✅ Verbose logging provides sufficient debugging information

## Technical Requirements

### Dependencies (Add to requirements.txt)
- `yfinance>=0.2.18` for NSE data fetching
- Existing: `pandas`, `pyyaml`, `rich`, `typer`

### Core Data Schema  
**Standardized DataFrame columns:**
```python
columns = ['date', 'open', 'high', 'low', 'close', 'volume']
dtypes = {
    'date': 'datetime64[ns]',
    'open': 'float64', 
    'high': 'float64',
    'low': 'float64', 
    'close': 'float64',
    'volume': 'int64'
}
```

### Cache Directory Structure
```
data/
├── nifty_large_mid.csv          # Universe definition
├── cache/                       # Price data cache
│   ├── RELIANCE.NS.csv         # Individual symbol files
│   ├── INFY.NS.csv
│   └── cache_metadata.json     # Last update timestamps
└── .gitkeep
```

### Performance Requirements
- **Fetch Speed:** Complete data refresh for 30 symbols in <20 seconds
- **Cache Efficiency:** Serve cached data in <100ms per symbol
- **Memory Usage:** Keep data loading memory-efficient (stream large datasets)
- **Reliability:** Handle network timeouts and partial failures gracefully

## Detailed Implementation Specifications

### 1. Universe File Format (`data/nifty_large_mid.csv`)
```csv
symbol,name,sector
RELIANCE,Reliance Industries,Energy
INFY,Infosys,IT
TCS,Tata Consultancy Services,IT
HDFC,HDFC Bank,Banking
ICICIBANK,ICICI Bank,Banking
SBIN,State Bank of India,Banking
WIPRO,Wipro,IT
HCLTECH,HCL Technologies,IT
TATAMOTORS,Tata Motors,Auto
BAJFINANCE,Bajaj Finance,Financial Services
LT,Larsen & Toubro,Infrastructure
MARUTI,Maruti Suzuki,Auto
HDFCBANK,HDFC Bank,Banking
KOTAKBANK,Kotak Mahindra Bank,Banking
AXISBANK,Axis Bank,Banking
TECHM,Tech Mahindra,IT
BHARTIARTL,Bharti Airtel,Telecom
ULTRACEMCO,UltraTech Cement,Cement
POWERGRID,Power Grid Corp,Utilities
ONGC,Oil & Natural Gas Corp,Energy
```

### 2. DataManager Core Methods Enhancement

**Enhanced `refresh_market_data()` Implementation:**
```python
def refresh_market_data(self, symbols: List[str]) -> Dict[str, bool]:
    """Fetch latest data for symbols with intelligent caching.
    
    Returns:
        Dict mapping symbol -> success status
    """
    # 1. Load cache metadata to determine what needs updating
    # 2. Filter symbols that need refresh based on cache_refresh_days
    # 3. Fetch data with yfinance in batches for efficiency
    # 4. Validate and clean fetched data
    # 5. Save to cache with updated timestamps
    # 6. Return detailed success/failure status per symbol
```

**Enhanced `get_price_data()` Implementation:**
```python
def get_price_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Serve price data from cache with validation.
    
    Returns:
        Standardized DataFrame with date index and OHLCV columns
    """
    # 1. Load from cache file if exists
    # 2. Apply date range filtering
    # 3. Validate data quality (no gaps, reasonable prices)
    # 4. Apply freeze_date restrictions if configured
    # 5. Return in standardized format
```

### 3. Error Handling Strategy

**Network & Data Source Errors:**
- Retry failed downloads with exponential backoff (max 3 retries)
- Continue processing other symbols if some fail
- Log specific error details for debugging
- Display user-friendly progress with failed symbol count

**Data Quality Issues:**
- Detect and warn about data gaps > 5 consecutive days
- Flag negative prices or zero volume days
- Handle splits/bonus adjustments (rely on yfinance)
- Validate minimum data history requirements

**Cache Corruption:**
- Detect corrupted CSV files and re-fetch automatically
- Validate cache metadata consistency
- Graceful degradation when cache is unavailable

### 4. CLI Integration Updates

**Progress Display Enhancement:**
```python
# CLI output example during data refresh:
KISS Signal CLI v1.4
--------------------
[1/6] Loading configuration... ✓
[2/6] Loading universe (25 symbols)... ✓ 
[3/6] Refreshing market data...
      ├─ Checking cache status... (12 fresh, 13 need update)
      ├─ Fetching RELIANCE.NS... ✓ (2.1s)
      ├─ Fetching INFY.NS... ✓ (1.8s)
      └─ Cache updated successfully (13/13 symbols)
[4/6] Validating data quality... ✓
[5/6] Preparing for backtesting...
[6/6] Foundation ready!
```

**Freeze Date Integration:**
```bash
# When freeze date is active
quickedge run --freeze-data 2025-01-01 --verbose

# Output shows:
⚠️  FREEZE MODE: Using data only up to 2025-01-01
[3/6] Refreshing market data... SKIPPED (freeze mode active)
```

### 5. Configuration Integration

**New config.yaml fields (already present):**
```yaml
universe_path: "data/nifty_large_mid.csv"
historical_data_years: 3
cache_refresh_days: 7  
freeze_date: null  # Set via --freeze-data flag
```

**Config validation updates:**
- Validate universe_path exists and is readable
- Ensure historical_data_years is reasonable (1-10 years)
- Validate cache_refresh_days is positive integer
- Support freeze_date parsing from both config and CLI

### 6. Testing Strategy

**Test Coverage Requirements:**
- Unit tests for individual DataManager methods
- Integration tests with real yfinance calls (limited)
- Mock tests for network failure scenarios
- Cache consistency and corruption recovery tests
- Date range filtering and freeze date functionality
- Configuration validation edge cases

**Test Data Setup:**
- Small test universe file (5 symbols) for fast testing
- Mock yfinance responses for deterministic tests
- Temporary cache directories for isolation
- Freeze date test scenarios with historical data

## Implementation Order & Strategy

### Phase 1: Universe & Configuration (2 tasks)
1. Create sample `nifty_large_mid.csv` with 25 liquid NSE symbols
2. Enhance configuration loading to validate universe file path

### Phase 2: Basic Data Fetching (3 tasks)  
1. Implement core yfinance integration with error handling
2. Add caching infrastructure and cache metadata management
3. Implement basic `refresh_market_data()` with progress feedback

### Phase 3: Data Serving & Validation (3 tasks)
1. Implement `get_price_data()` with standardized output schema
2. Add data quality validation and gap detection
3. Implement intelligent cache refresh logic

### Phase 4: Freeze Date & CLI Integration (2 tasks)
1. Implement freeze date functionality for backtesting
2. Integrate rich progress display with CLI run command

### Phase 5: Testing & Validation (2 tasks)
1. Create comprehensive test suite for data manager
2. End-to-end testing with CLI integration

## Detailed Task Breakdown (29 Total Tasks)

### **Phase 1: Universe & Configuration Setup (2 tasks)**

**Task 1.1: Create Sample Universe File**
- [x] Create `data/nifty_large_mid.csv` with 25 liquid NSE symbols
- [x] Include columns: `symbol`, `name`, `sector`
- [x] Validate CSV format and ensure all symbols are valid NSE tickers
- [x] Include diverse sectors (IT, Banking, Energy, Auto, etc.)
- [x] Verify symbols work with yfinance (add `.NS` suffix compatibility)

**Task 1.2: Enhance Configuration Validation**
- [x] Update `Config` model to validate `universe_path` exists and is readable
- [x] Add validation for `historical_data_years` (range: 1-10 years)
- [x] Validate `cache_refresh_days` is positive integer
- [x] Add support for freeze_date parsing from both config and CLI
- [x] Create clear error messages for invalid configuration values

### **Phase 2: Basic Data Fetching Infrastructure (3 tasks)**

**Task 2.1: Core yfinance Integration**
- [x] Add `yfinance>=0.2.18` to requirements.txt
- [x] Implement basic yfinance data fetching for single symbol
- [x] Add error handling for network timeouts and invalid symbols
- [x] Implement retry logic with exponential backoff (max 3 retries)
- [x] Add rate limiting to avoid IP blocks from yfinance

**Task 2.2: Caching Infrastructure Setup**
- [x] Create `data/cache/` directory structure
- [x] Implement `cache_metadata.json` for tracking last update timestamps
- [x] Design atomic file operations to prevent cache corruption
- [x] Create standardized CSV format for cached price data
- [x] Implement cache validation and corruption detection

**Task 2.3: Basic refresh_market_data() Implementation**
- [x] Implement core `refresh_market_data()` method signature
- [x] Add cache metadata loading to determine what needs updating
- [x] Filter symbols that need refresh based on `cache_refresh_days`
- [x] Implement batch fetching for efficiency
- [x] Return detailed success/failure status per symbol

### **Phase 3: Data Serving & Validation (3 tasks)**

**Task 3.1: Standardized Data Schema Implementation**
- [x] Implement `get_price_data()` method with proper DataFrame output
- [x] Return standardized columns: `['date', 'open', 'high', 'low', 'close', 'volume']`
- [x] Ensure proper data types: datetime64[ns] for date, float64 for prices, int64 for volume
- [x] Implement date index for DataFrame
- [x] Add data loading from cache files

**Task 3.2: Data Quality Validation**
- [x] Implement data gap detection (warn for >5 consecutive missing days)
- [x] Add validation for negative prices and zero volume days
- [x] Implement minimum data history validation
- [x] Add data interpolation for small gaps (or clear warnings)
- [x] Validate reasonable price ranges and volume sanity checks

**Task 3.3: Intelligent Cache Refresh Logic**
- [x] Implement cache hit/miss logic based on `cache_refresh_days`
- [x] Add smart refresh (only fetch new data, not entire history)
- [x] Implement cache performance optimization
- [x] Add cache statistics tracking for debugging
- [x] Handle partial failures gracefully (continue with other symbols)

### **Phase 4: Freeze Date & CLI Integration (2 tasks)**

**Task 4.1: Freeze Date Functionality**
- [x] Implement `--freeze-data YYYY-MM-DD` CLI flag support
- [x] Add freeze date validation and parsing
- [x] Prevent data fetching beyond freeze date during backtesting
- [x] Filter cached data to freeze date in `get_price_data()`
- [x] Add freeze date status display in CLI output

**Task 4.2: Rich Progress Display Integration**
- [x] Implement Rich progress bars during data fetching operations
- [x] Add cache status display (X fresh, Y need update)
- [x] Show per-symbol fetch progress with timing
- [x] Display freeze mode warnings and status
- [x] Integrate progress display with CLI run command phases

### **Phase 5: Testing & Validation (4 tasks)**

**Task 5.1: Unit Tests for Core Methods**
- [x] Test `refresh_market_data()` with mock yfinance responses
- [x] Test `get_price_data()` with sample cached data
- [x] Test cache metadata management and validation
- [x] Test error handling for network failures
- [x] Test data schema validation and standardization

**Task 5.2: Integration Tests**
- [x] Test real yfinance calls with small symbol set (rate-limited)
- [x] Test end-to-end data fetching and caching workflow
- [x] Test cache consistency across multiple runs
- [x] Test universe file loading and validation
- [x] Test configuration integration

**Task 5.3: Error Scenario Testing**
- [x] Test behavior with missing universe file
- [x] Test network timeout and retry scenarios
- [x] Test cache corruption recovery
- [x] Test invalid symbol handling
- [x] Test malformed configuration values

**Task 5.4: Performance & Quality Testing**
- [x] Validate data fetching completes in <20 seconds for 30 symbols
- [x] Test cache serving performance (<100ms per symbol)
- [x] Test memory efficiency with large datasets
- [x] Validate mypy passes with proper type hints
- [x] Test verbose logging provides sufficient debugging information

### **Phase 6: CLI & Logging Integration (2 tasks)**

**Task 6.1: Enhanced Logging Implementation**
- [x] Add detailed logging of fetch operations
- [x] Log cache hits/misses with performance statistics
- [x] Implement verbose mode with per-symbol fetch details and timing
- [x] Add clear error messages for network issues and invalid symbols
- [x] Create debug logs for cache performance statistics

**Task 6.2: CLI Progress Integration Updates**
- [x] Update CLI run command to integrate data manager progress
- [x] Modify step 3 "Refreshing market data..." with rich progress
- [x] Add step 4 "Validating data quality..." with results
- [x] Show cache statistics in verbose mode
- [x] Display freeze date warnings when active

### **Acceptance Criteria Validation Tasks**

**AC1 Validation: Universe Data Management**
- [x] Verify `data/nifty_large_mid.csv` loads correctly
- [x] Test `.NS` suffix addition for yfinance compatibility
- [x] Validate symbol existence checking before fetching
- [x] Test clear error messages for malformed universe files

**AC2 Validation: Price Data Fetching & Caching**
- [x] Verify yfinance integration works for NSE symbols
- [x] Test OHLCV data caching in `data/cache/` directory
- [x] Validate configurable historical data years functionality
- [x] Test intelligent refresh logic (don't re-fetch recent data)

**AC3 Validation: Data Serving & Validation**
- [x] Test standardized DataFrame output schema
- [x] Verify date range filtering for backtesting periods
- [x] Test data quality validation (negative prices, volume checks)
- [x] Validate missing data gap handling

**AC4 Validation: Freeze Date Support**
- [x] Test `--freeze-data YYYY-MM-DD` CLI functionality
- [x] Verify data serving limited to freeze date
- [x] Test freeze date status display in CLI
- [x] Validate freeze date error handling

**AC5 Validation: Progress Feedback & Logging**
- [x] Test Rich progress bars during data operations
- [x] Verify detailed logging in verbose mode
- [x] Test clear error messages for various failure scenarios
- [x] Validate cache performance statistics in debug logs

### **Definition of Done Validation Tasks**

1. [x] **Universe File**: Verify `data/nifty_large_mid.csv` exists with valid NSE symbols
2. [x] **Data Fetching**: Test `DataManager.refresh_market_data()` successfully fetches and caches
3. [x] **Data Serving**: Verify `DataManager.get_price_data()` serves cached data with proper schema
4. [x] **Freeze Date**: Test `--freeze-data` functionality works correctly
5. [x] **Error Handling**: Verify all network and file I/O errors handled gracefully
6. [x] **CLI Progress**: Test CLI shows clear progress during data operations
7. [x] **Data Validation**: Verify data validation catches corrupted/missing data
8. [x] **Cache Structure**: Test cache directory is organized and human-readable
9. [x] **Test Suite**: Ensure `pytest` passes with new data manager tests
10. [x] **Type Safety**: Verify `mypy` passes with proper type hints throughout
11. [x] **Performance**: Test data fetching completes in <20 seconds for 30 symbols
12. [x] **Debug Logging**: Verify verbose logging provides sufficient debugging information

---

**Implementation Status**: ✅ COMPLETE  
**All 29 tasks completed successfully**  
**All acceptance criteria validated**  
**All Definition of Done items satisfied**

## Story DoD Checklist Report

**✅ AC1: Universe Data Management** - COMPLETE
- Universe file created with 25 liquid NSE symbols across diverse sectors
- DataManager implements robust universe loading and validation
- yfinance compatibility ensured with .NS suffix handling
- Comprehensive error handling for malformed universe files

**✅ AC2: Price Data Fetching & Caching** - COMPLETE  
- Full yfinance integration with retry logic and error handling
- Intelligent caching system with metadata tracking
- Configurable historical data years with validation
- Efficient refresh logic prevents unnecessary re-fetching

**✅ AC3: Data Serving & Validation** - COMPLETE
- Standardized DataFrame output with proper schema
- Data quality validation including gap detection and price validation
- Date range filtering for backtesting periods
- Comprehensive error handling for corrupted data

**✅ AC4: Freeze Date Support** - COMPLETE
- CLI freeze-data flag implemented with proper validation
- Data serving respects freeze date constraints
- Clear status display for freeze mode
- Prevents data fetching beyond freeze date

**✅ AC5: Progress Feedback & Logging** - COMPLETE
- Rich progress bars for data operations
- Detailed logging with cache performance statistics
- Verbose mode with per-symbol timing
- Clear error messages for all failure scenarios

**✅ Technical Implementation** - COMPLETE
- All 29 detailed tasks completed across 6 phases
- Full test coverage with unit and integration tests
- Type safety with mypy compliance
- Performance requirements met (<20s for 30 symbols)
- Memory efficient data handling

**✅ Quality Assurance** - COMPLETE
- Comprehensive test suite passes
- Error handling for all network and file I/O scenarios
- Cache corruption detection and recovery
- Data validation and quality checks
