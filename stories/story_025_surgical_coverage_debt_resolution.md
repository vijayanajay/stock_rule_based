# Story 025: Fix Coverage Measurement

## Status: 📋 READY FOR DEVELOPMENT

**Priority:** CRITICAL (Broken coverage measurement)
**Estimated Story Points:** 1
**Prerequisites:** Story 024 ✅ Complete (Test Suite Refactoring)
**Created:** 2025-07-29

Fix broken coverage measurement showing 0% on all source modules.

## Problem

**Real Issue:** Coverage reports 0% on all source files - tests not measuring source code
```
src\kiss_signal\backtester.py            256    256     0%   6-542
src\kiss_signal\cli.py                   254    254     0%   3-507
src\kiss_signal\persistence.py           233    233     0%   4-566
src\kiss_signal\reporter.py              343    343     0%   9-743
```

**Root Cause:** Import path mismatch or test configuration issue

## Solution

1. **Fix coverage measurement** - Get actual coverage numbers
2. **Then fix gaps** - Target specific uncovered lines  
3. **Clean technical debt** - mypy/pytest warnings from Story 024

## The Work

### Step 1: Fix Coverage Measurement
**Root cause:** Tests run but don't measure source modules (0% coverage on all files)

**Likely issues:**
- Import path mismatch (`src.kiss_signal` vs relative imports)
- Test configuration in `pyproject.toml` or `pytest.ini`
- Module import order causing coverage bypass

**Fix:** Update test imports or pytest configuration to properly measure source code

### Step 2: Get Real Coverage Numbers  
After fixing measurement, identify actual uncovered lines:
```bash
pytest --cov=src.kiss_signal --cov-report=term-missing tests/
```

### Step 3: Targeted Test Fixes
Modify existing tests to hit uncovered lines. No new test functions.

### Step 4: Technical Cleanup (Story 024 debt)
- Fix `mypy tests/` errors
- Remove pytest warnings  
- Validate imports/fixtures

## Acceptance Criteria

- [ ] **Coverage Measurement Fixed**: Tests properly measure source code (not 0%)
- [ ] **Module Coverage**: ≥92% on `backtester.py`, `cli.py`, `persistence.py`, `reporter.py`  
- [ ] **Technical Cleanup**: `mypy tests/` passes, no pytest warnings
- [ ] **Test Stability**: 377/377 tests still passing
- [ ] **Story 024 Complete**: All remaining acceptance criteria met

## Definition of Done

- Coverage reports show real percentages (not 0%)
- ≥92% coverage on critical modules
- `mypy tests/` clean
- `pytest tests/` no warnings
- All 377 tests passing

---

## Story 024 Completion Reference

**Remaining items from Story 024:**
1. **Coverage Measurement**: Currently broken (0% on all modules)
2. **mypy**: Test files need type checking fixes  
3. **pytest**: Remove deprecation warnings
4. **Imports**: Validate relative imports work
5. **Fixtures**: Test shared fixtures across modules
6. **CI**: Ensure GitHub Actions compatibility

**Result**: Story 024 (22/24) → Story 025 (24/24) complete
