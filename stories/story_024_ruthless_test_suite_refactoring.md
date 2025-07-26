# Story 024: Kill Test File Fragmentation

## Status: 📋 Ready for Development

**Priority:** CRITICAL (Technical Debt)
**Estimated Story Points:** 3
**Prerequisites:** All prior stories complete (Stories 001-023) ✅
**Created:** 2025-07-27
**Reviewed:** 2025-07-27 (Kailash Nadh - RUTHLESS SIMPLIFICATION)

## User Story

As a developer, I want to merge fragmented test files so the test suite is fast and maintainable.

## Problem

**Current:** 31 test files, 11,364 lines of test code
**Problem:** Fragmented into single-purpose files (`test_cli_basic.py`, `test_cli_advanced.py`, etc.)
**Impact:** Slow, hard to navigate, expensive to maintain

## Solution

**Merge files by module.** One test file per source module. Delete the rest.

**Target:** 12 test files, ~8,000 lines (30% reduction)

## The Work

### 1. Merge Files by Module

**CLI Tests** (5 files → 1):
- `test_cli_basic.py` + `test_cli_advanced.py` + `test_cli_coverage.py` + `test_cli_min_trades.py` + `test_cli_clear_*.py` → `test_cli.py`

**Reporter Tests** (6 files → 1):
- `test_reporter_core.py` + `test_reporter_advanced.py` + `test_reporter_coverage.py` + `test_reporter_data_issues.py` + `test_reporter_index_symbol_bug.py` → `test_reporter.py`

**Data Tests** (3 files → 1):
- `test_data_basic.py` + `test_data_advanced.py` + `test_market_alignment.py` → `test_data.py`

**Backtester Tests** (+3 files):
- `test_context_filters.py` + `test_pandas_downcasting_fix.py` + `test_complete_rule_stack.py` → merge into `test_backtester.py`

**Rules Tests** (+1 file):
- `test_atr_fix.py` → merge into `test_rule_funcs.py` → rename to `test_rules.py`

**Persistence Tests** (+1 file):
- `test_story_020_deduplication.py` → merge into `test_persistence.py`

**Adapters** (rename):
- `test_yfinance_adapter.py` → `test_adapters.py`

### 2. Use Parameterization to Kill Redundancy

Replace duplicate test functions with `@pytest.mark.parametrize`. Example:

```python
# BEFORE: 4 functions, 60 lines
def test_cli_run_basic(): ...
def test_cli_run_verbose(): ...
def test_cli_run_freeze(): ...
def test_cli_run_error(): ...

# AFTER: 1 function, 15 lines  
@pytest.mark.parametrize("args,expected", [
    (["run"], {"success": True}),
    (["run", "--verbose"], {"success": True}),
    (["run", "--freeze-data", "2025-01-01"], {"success": True}),
    (["run", "--invalid"], {"success": False}),
])
def test_cli_variations(args, expected): ...
```

### 3. Centralize Setup in conftest.py

Add fixtures to eliminate duplicated setup:

```python
@pytest.fixture(scope="session")
def test_env():
    """Temp dir with config.yaml and rules.yaml"""
    
@pytest.fixture(scope="session") 
def sample_db():
    """SQLite DB with test data"""
```

## Detailed Task List

### Phase 1: CLI Tests Consolidation
1. **Create `test_cli.py`** - New consolidated file with module docstring
2. **Copy tests from:**
   - `test_cli_basic.py` → `test_cli_run_*` functions
   - `test_cli_advanced.py` → `test_cli_analyze_*` functions  
   - `test_cli_coverage.py` → `test_cli_edge_cases_*` functions
   - `test_cli_min_trades.py` → `test_cli_min_trades_*` functions
   - `test_cli_clear_and_recalculate_new.py` → `test_cli_clear_*` functions
3. **Parameterize duplicates:** Merge `test_cli_run_basic` + `test_cli_run_verbose` → `test_cli_run_variations`
4. **Delete source files:** Remove all 5 original CLI test files
5. **Test:** `pytest tests/test_cli.py -v` passes

### Phase 2: Reporter Tests Consolidation  
1. **Create `test_reporter.py`** - New consolidated file
2. **Copy tests from:**
   - `test_reporter_core.py` → Core reporter functionality
   - `test_reporter_advanced.py` → Strategy analysis features
   - `test_reporter_coverage.py` → Edge cases and error handling
   - `test_reporter_data_issues.py` → Data validation tests
   - `test_reporter_index_symbol_bug.py` → Bug fix regression tests
3. **Parameterize CSV output tests:** Multiple format variations → single parameterized test
4. **Delete source files:** Remove all 5 original reporter test files
5. **Test:** `pytest tests/test_reporter.py -v` passes

### Phase 3: Data Tests Consolidation
1. **Create `test_data.py`** - New consolidated file  
2. **Copy tests from:**
   - `test_data_basic.py` → Basic data loading/validation
   - `test_data_advanced.py` → Advanced data operations
   - `test_market_alignment.py` → Market data alignment logic
   - `test_timestamp_comparison_fix.py` → Timestamp handling bug fixes
3. **Merge duplicate yfinance tests:** Single parameterized test for multiple symbols
4. **Delete source files:** Remove all 4 original data test files
5. **Test:** `pytest tests/test_data.py -v` passes

### Phase 4: Backtester Enhancement
1. **Enhance existing `test_backtester.py`**
2. **Merge content from:**
   - `test_context_filters.py` → Context filter tests
   - `test_pandas_downcasting_fix.py` → Pandas dtype handling  
   - `test_complete_rule_stack.py` → End-to-end rule combinations
3. **Organize by feature:** Group tests by backtester functionality (signals, exits, context)
4. **Delete source files:** Remove 3 merged files
5. **Test:** `pytest tests/test_backtester.py -v` passes

### Phase 5: Rules and Misc Consolidation
1. **Rename:** `test_rule_funcs.py` → `test_rules.py`
2. **Merge `test_atr_fix.py`** → Add ATR tests to rules file
3. **Merge `test_story_020_deduplication.py`** → Add to `test_persistence.py`
4. **Rename:** `test_yfinance_adapter.py` → `test_adapters.py` 
5. **Delete merged files:** Remove 2 source files
6. **Test:** All affected files pass individually

### Phase 6: Fixture Centralization
1. **Enhance `conftest.py`** with shared fixtures:
   - `test_environment` → Temp directory with config files
   - `sample_db` → Pre-populated SQLite database
   - `stock_data_samples` → Standard OHLCV test data
2. **Replace setup code** in all test files with fixture usage
3. **Remove duplicated setup** from individual test files
4. **Test:** `pytest tests/ -v` passes with new fixtures

## Acceptance Criteria

### File Structure
- [ ] **CLI Tests**: 5 files → 1 file (`test_cli.py`)
- [ ] **Reporter Tests**: 5 files → 1 file (`test_reporter.py`)  
- [ ] **Data Tests**: 4 files → 1 file (`test_data.py`)
- [ ] **Backtester Tests**: 3 additional files merged into existing `test_backtester.py`
- [ ] **Rules Tests**: 1 file renamed + 1 merged → `test_rules.py`
- [ ] **Persistence Tests**: 1 file merged into existing `test_persistence.py`
- [ ] **Adapters**: 1 file renamed → `test_adapters.py`
- [ ] **Total Count**: 31 files → 12 files (19 files deleted)

### Code Quality
- [ ] **Line Reduction**: 11,364 lines → ~8,000 lines (≥30% reduction)
- [ ] **Parameterization**: CLI tests use `@pytest.mark.parametrize` for variations
- [ ] **Fixture Usage**: Setup code centralized in `conftest.py`
- [ ] **Import Cleanup**: No unused imports in consolidated files
- [ ] **Docstrings**: Each consolidated file has clear module docstring explaining scope

### Functionality  
- [ ] **All Tests Pass**: 100% pass rate after consolidation
- [ ] **Coverage Maintained**: >92% coverage on `backtester`, `cli`, `reporter`, `rules` modules
- [ ] **Test Isolation**: Tests can run in any order (`pytest --random-order`)
- [ ] **Performance**: Test suite runs faster (fewer file discovery overhead)
- [ ] **Parallel Execution**: Compatible with `pytest -n auto`

### Technical Validation
- [ ] **mypy**: All test files pass type checking
- [ ] **pytest**: No warnings about deprecated features
- [ ] **Imports**: All relative imports work correctly in consolidated files
- [ ] **Fixtures**: Shared fixtures work across all test files
- [ ] **CI Compatibility**: Existing GitHub Actions workflow still works

## Architectural Considerations

### Test File Organization
**Principle**: One test file per source module. No exceptions.

**Import Strategy**: 
```python
# Consolidated files import the module they test
import src.kiss_signal.cli as cli_module
import src.kiss_signal.reporter as reporter_module
```

**Fixture Scope**:
- `session`: Read-only data (config files, sample data)  
- `function`: Mutable state (databases, temp files)

### Parameterization Strategy
**When to Parameterize**:
- Multiple similar test functions testing variations of same logic
- Different input/output combinations for same function
- Error handling tests with different error types

**When NOT to Parameterize**:
- Tests with fundamentally different setup requirements
- Tests validating completely different behaviors
- Tests that would become unclear when parameterized

### Fixture Design
**Central Fixtures** (`conftest.py`):
```python
@pytest.fixture(scope="session")
def test_environment():
    """Isolated filesystem with standard config.yaml and rules.yaml"""
    
@pytest.fixture(scope="session") 
def sample_db():
    """SQLite database pre-populated with test strategies and positions"""
    
@pytest.fixture(scope="function")
def temp_db():
    """Empty SQLite database for tests that modify data"""
```

**File-Specific Fixtures**: Only when needed for that specific module's tests.

### Migration Safety
**Import Path Validation**: After each merge, verify all imports resolve correctly.
**Test Isolation**: Ensure consolidated tests don't share mutable state.
**Coverage Tracking**: Run coverage before/after each merge to catch regressions.

## Definition of Done

## Definition of Done

### Quantitative Metrics
- [ ] **File Count**: Exactly 12 test files in `tests/` directory
- [ ] **Line Count**: ≤8,000 total lines of test code (measured via `wc -l tests/*.py`)
- [ ] **Test Count**: All original test functions preserved (no test logic lost)
- [ ] **Coverage**: ≥92% on critical modules (`backtester.py`, `cli.py`, `reporter.py`, `rules.py`)
- [ ] **Performance**: Test suite runs ≤80% of original execution time

### Functional Validation  
- [ ] **Test Execution**: `pytest tests/ -v` shows 100% pass rate
- [ ] **Parallel Execution**: `pytest tests/ -n 4` works without race conditions
- [ ] **Random Order**: `pytest tests/ --random-order` passes consistently
- [ ] **Type Checking**: `mypy tests/` shows zero type errors
- [ ] **Import Validation**: No circular imports or missing dependencies

### Quality Gates
- [ ] **Documentation**: Each consolidated file has clear docstring explaining scope
- [ ] **Code Style**: No unused imports, consistent formatting  
- [ ] **Fixture Usage**: Shared setup centralized, no duplicate initialization code
- [ ] **Parameterization**: Appropriate use of `@pytest.mark.parametrize` for test variations
- [ ] **Test Names**: Clear, descriptive test function names in consolidated files

### Integration Validation
- [ ] **CI Pipeline**: Existing GitHub Actions workflow passes unchanged
- [ ] **Coverage Reports**: Coverage reporting tools work with new file structure  
- [ ] **IDE Support**: VS Code test discovery works with consolidated files
- [ ] **Developer Workflow**: `pytest tests/test_cli.py::test_specific_function` works
- [ ] **Debug Support**: Individual tests can be debugged in isolation

**Ship Criteria**: All checkboxes above must be ✅ before story is marked complete.

**Success Signal**: Developer adds new test with <5 lines of setup code and it runs immediately.

**Failure Signal**: Test suite takes longer to run or has lower coverage than before consolidation.

## Final File List

```
tests/
├── test_adapters.py      
├── test_backtester.py    
├── test_cli.py           
├── test_config.py        
├── test_data.py          
├── test_integration_backtester.py
├── test_integration_cli.py
├── test_mathematical_accuracy.py
├── test_performance.py   
├── test_persistence.py   
├── test_reporter.py      
└── test_rules.py         
```

**Result**: Clean, fast test suite. One file per module. No ceremony.
