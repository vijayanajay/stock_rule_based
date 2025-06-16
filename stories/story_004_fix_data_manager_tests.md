# Story 004: Fix DataManager Test Failures & Complete Data Layer Transition

## Status: READY FOR DEVELOPMENT

## Story Summary
Fix 12 failing tests in `test_data_manager.py` by completing the transition from class-based to function-based data operations. The DataManager class was deprecated in favor of direct function calls from `kiss_signal.data`, but the tests weren't updated to match this architectural change.

## Priority: HIGH
**Rationale**: Failing tests block further development and violate the quality gate requirement that "pytest passes" before commits.

## Story Details

### Problem Analysis
Based on pytest results showing 12 failures in `test_data_manager.py`:

1. **Missing Private Methods**: Tests expect private methods (`_fetch_symbol_data`, `_needs_refresh`, etc.) that exist in `data.py` but aren't exposed through the DataManager compatibility shim
2. **Function Signature Mismatch**: `get_price_data()` function signature changed, causing TypeError
3. **Incomplete Deprecation**: DataManager class exists as compatibility shim but doesn't fully support the old interface that tests depend on

### Memory Bank Learnings Applied
- ✅ **Function-Based Design**: Continue transition from class to simple functions (per `data_module_refactoring_learnings.md`)
- ✅ **No Over-Engineering**: Don't add complex compatibility layers
- ✅ **KISS Compliance**: Use direct function calls instead of wrapper classes

### Acceptance Criteria

#### 1. All Tests Pass
- [ ] All 12 failing tests in `test_data_manager.py` pass
- [ ] Total test suite: 77/77 tests passing
- [ ] No new test failures introduced

#### 2. Choose Implementation Strategy
**Option A: Complete Deprecation (RECOMMENDED)**
- [ ] Update failing tests to use `kiss_signal.data` functions directly
- [ ] Remove or simplify DataManager compatibility shim
- [ ] Follow established pattern from memory bank

**Option B: Full Compatibility Shim**
- [ ] Add missing private methods to DataManager class
- [ ] Delegate to corresponding `data.py` functions

#### 3. Maintain API Consistency
- [ ] `get_price_data()` signature matches between DataManager and data module
- [ ] All function calls use consistent parameter ordering
- [ ] Type hints preserved throughout

#### 4. Quality Gates
- [ ] `pytest` passes (77/77 tests)
- [ ] `mypy` passes with strict typing
- [ ] No deprecation warnings in test output
- [ ] All changes < 25 LOC per file (KISS principle)

### Implementation Constraints

#### Must Preserve
- ✅ All existing functionality
- ✅ Backward compatibility for CLI and engine modules
- ✅ Type safety with mypy --strict
- ✅ Existing file structure

#### Must NOT
- ❌ Add new external dependencies
- ❌ Change public API of data functions
- ❌ Break existing CLI commands
- ❌ Introduce complex error handling

### Files to Modify

#### Primary
- `tests/test_data_manager.py` - Update tests to use data functions directly
- `src/kiss_signal/data_manager.py` - Fix compatibility shim or remove

#### Secondary (if needed)
- `src/kiss_signal/data.py` - Minor signature adjustments if required

### Technical Approach

Based on memory bank guidance and KISS principles:

1. **Analyze Current Usage**: Check which modules still use DataManager
2. **Update Tests**: Modify `test_data_manager.py` to call `data` functions directly
3. **Fix Signatures**: Ensure `get_price_data` has consistent parameters
4. **Validate Integration**: Ensure CLI still works with updated data layer
5. **Clean Up**: Remove unnecessary DataManager methods

## Detailed Task Breakdown

### Phase 1: Analysis & Planning (30 minutes)
- [ ] **Task 1.1**: Run failing tests to confirm exact error messages
  ```bash
  pytest tests/test_data_manager.py -v --tb=short
  ```
- [ ] **Task 1.2**: Audit current DataManager usage across codebase
  ```bash
  grep -r "DataManager" src/ --include="*.py"
  ```
- [ ] **Task 1.3**: Compare function signatures between `data.py` and `data_manager.py`
- [ ] **Task 1.4**: Document which tests need Option A (direct functions) vs Option B (shim methods)

### Phase 2: Fix Function Signature Mismatches (45 minutes)
- [ ] **Task 2.1**: Fix `get_price_data()` signature mismatch in DataManager.get_price_data()
  - Current issue: `TypeError: get_price_data() missing 2 required positional arguments`
  - Expected: Match data.py function signature exactly
- [ ] **Task 2.2**: Update any other method signatures in DataManager class
- [ ] **Task 2.3**: Run specific failing test to validate signature fix:
  ```bash
  pytest tests/test_data_manager.py::TestDataManager::test_get_price_data_missing_cache -v
  ```

### Phase 3: Implement Missing Private Methods (60 minutes)
Choose ONE approach:

#### Option A: Update Tests (RECOMMENDED - follows KISS)
- [ ] **Task 3.1**: Update `test_cache_metadata_operations` to use data functions directly
- [ ] **Task 3.2**: Update `test_needs_refresh` to call `data._needs_refresh()` directly  
- [ ] **Task 3.3**: Update `test_add_ns_suffix` to call `data._add_ns_suffix()` directly
- [ ] **Task 3.4**: Update `test_validate_data_quality` to call `data._validate_data_quality()` directly
- [ ] **Task 3.5**: Update `test_fetch_symbol_data_*` to call `data._fetch_symbol_data()` directly
- [ ] **Task 3.6**: Update `test_save_and_load_symbol_cache` to call data functions directly

#### Option B: Add Compatibility Methods (if Option A blocked)
- [ ] **Task 3.1**: Add DataManager._needs_refresh() method delegating to data._needs_refresh()
- [ ] **Task 3.2**: Add DataManager._add_ns_suffix() method delegating to data._add_ns_suffix()  
- [ ] **Task 3.3**: Add DataManager._validate_data_quality() method delegating to data._validate_data_quality()
- [ ] **Task 3.4**: Add DataManager._fetch_symbol_data() method delegating to data._fetch_symbol_data()
- [ ] **Task 3.5**: Add DataManager._save_symbol_cache() method delegating to data._save_symbol_cache()
- [ ] **Task 3.6**: Add DataManager._load_cache_metadata() method (or remove test if no longer needed)

### Phase 4: Test Validation & Integration (30 minutes)
- [ ] **Task 4.1**: Run all DataManager tests to confirm fixes
  ```bash
  pytest tests/test_data_manager.py -v
  ```
- [ ] **Task 4.2**: Run full test suite to ensure no regressions
  ```bash
  pytest -x
  ```
- [ ] **Task 4.3**: Validate mypy compliance
  ```bash
  mypy src/kiss_signal/
  ```
- [ ] **Task 4.4**: Test CLI integration still works
  ```bash
  python -m kiss_signal.cli run --freeze-date 2025-01-01 --verbose
  ```

### Phase 5: Cleanup & Documentation (15 minutes)  
- [ ] **Task 5.1**: Remove any unused imports in modified files
- [ ] **Task 5.2**: Update docstrings if function signatures changed
- [ ] **Task 5.3**: Ensure no deprecation warnings in test output
- [ ] **Task 5.4**: Update memory bank with lessons learned

## Troubleshooting Guide

### Common Issues & Solutions
1. **Import Errors**: Ensure `from kiss_signal import data` is used in tests
2. **Signature Mismatches**: Check parameter order matches exactly between modules  
3. **Mock Setup**: Update test mocks to match new function call patterns
4. **Path Objects**: Ensure Path vs string consistency in function calls

### Rollback Plan
If Option A causes excessive test changes:
1. Revert test changes: `git checkout -- tests/test_data_manager.py`
2. Implement Option B with minimal compatibility methods
3. Focus only on fixing the 12 specific failing tests

## Validation Commands
```bash
# Primary validation
pytest tests/test_data_manager.py -v

# Full test suite  
pytest

# Type checking
mypy src/

# Integration test
python -m kiss_signal.cli run --freeze-date 2025-01-01
```
