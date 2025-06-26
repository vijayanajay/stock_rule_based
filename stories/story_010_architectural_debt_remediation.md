# Story 010: Architectural Debt Remediation and Core Infrastructure Cleanup

## Status: ✅ COMPLETE

**Priority:** CRITICAL  
**Estimated Story Points:** 13  
**Prerequisites:** Story 009 (Implement Position Tracking) ✅ Complete  
**Created:** 2025-06-26  
**Last Updated:** 2025-06-26  

### Critical Architectural Review Context
This story addresses **four critical architectural flaws** identified in the 2025-07-09 baseline architectural audit (`arch_review.md`). These flaws represent fundamental integrity issues that must be resolved to maintain the project's architectural health and prevent further technical debt accumulation.

### Implementation Summary
- **Dead Code Removed:** Deleted `src/kiss_signal/adapters/yfinance_adapter.py` and its tests, as it was a duplicate of logic in `data.py`.
- **Backtester Feature Implemented:** The backtester now correctly implements the `baseline` + `layers` strategy discovery mechanism as specified in the PRD. It tests the baseline rule alone, then tests the baseline combined with each layer, and ranks the results.
- **Architecture Documentation Corrected:** `docs/architecture.md` has been updated to reflect the actual codebase. References to non-existent modules (`DataManager`, `SignalGenerator`) have been removed, and the database schema has been corrected to show the `strategies` and `positions` tables with JSON storage for rule definitions.
- **Dependencies Standardized:** The `requirements.txt` file has been deleted, establishing `pyproject.toml` as the single source of truth for all project dependencies.
- **Use Cases Updated:** All relevant use cases (`uc_cli.md`, `uc_backtester.md`) have been updated to reflect the new `baseline` + `layers` logic, ensuring documentation-to-code traceability.
- **Test Suite Aligned:** The test suite has been updated to pass with the new architectural changes, ensuring no regressions were introduced.

**Final Status:** All four critical architectural flaws have been resolved. The codebase, documentation, and dependency management are now consistent and aligned.

**Architectural Audit Verdict:** **SYSTEM INTEGRITY DEGRADED** - Critical drift between documentation, requirements, and implementation detected.

## User Story
As a maintainer of the KISS Signal CLI codebase, I want to resolve all critical architectural flaws identified in the baseline audit so that the system has consistent documentation, clean code hygiene, proper dependency management, and feature parity with documented requirements, ensuring long-term maintainability and developer onboarding success.

## Context & Rationale

### Current Architectural Integrity Issues
The baseline architectural audit identified four critical flaws that fundamentally compromise the system's integrity:

1. **🔴 CRITICAL: Dead Code Pollution** - `yfinance_adapter.py` is duplicate, unused code violating DRY principles
2. **🔴 CRITICAL: Feature Discrepancy** - Backtester missing core `baseline` + `layers` functionality described in PRD
3. **🔴 CRITICAL: Documentation Veracity Failure** - `architecture.md` describes non-existent components and wrong database schema
4. **🔴 CRITICAL: Dependency Hygiene Failure** - Competing dependency lists in `pyproject.toml` vs `requirements.txt`

### Impact on Development Workflow
- **Developer Onboarding:** New developers receive misleading information from `architecture.md`
- **Feature Development:** Core PRD requirements are unimplemented, blocking strategy optimization
- **Code Quality:** Dead code and dependency confusion creates maintenance overhead
- **System Reliability:** Inconsistent dependency management increases security and version conflict risks

### KISS Principles Compliance
This remediation aligns with KISS principles by:
- **Minimalism:** Removing dead code and unnecessary dependencies
- **Single Source of Truth:** Eliminating competing documentation and dependency lists  
- **Transparency:** Making documentation accurately reflect implementation
- **Modularity:** Ensuring backtester implements documented modular strategy testing

## Problem Analysis

### Critical Flaw #1: Architectural Degeneration / Code Hygiene Failure
**Location:** `src/kiss_signal/adapters/yfinance_adapter.py`
**Issue:** Complete duplicate of data fetching logic present in `src/kiss_signal/data.py`
**Evidence:** Module not imported anywhere, `data.py` version has retry logic making it more robust
**Impact:** Violates DRY principle, confuses developers, bloats codebase

### Critical Flaw #2: Critical Feature Discrepancy  
**Location:** `src/kiss_signal/backtester.py` vs `docs/prd.md`
**Issue:** PRD specifies testing rule `layers` on top of `baseline` rule to find optimal combinations
**Evidence:** Current implementation only tests rules in isolation, missing core strategy discovery feature
**Impact:** System fails to deliver key promised functionality, reduces backtester value proposition

### Critical Flaw #3: Documentation Veracity Failure
**Location:** `docs/architecture.md`
**Issue:** Architecture document describes non-existent components and wrong database schema
**Evidence:**
- References non-existent modules like `SignalGenerator` and `DataManager`
- Describes normalized schema with `rule_stack` and `trades` tables using foreign keys
- Actual implementation uses denormalized schema with `strategies` and `positions` tables storing rule definitions as JSON
**Impact:** Actively misleading documentation causes onboarding friction and wrong architectural decisions

### Critical Flaw #4: Dependency Hygiene Failure
**Location:** `pyproject.toml` vs `requirements.txt`
**Issue:** Two competing dependency lists with unused dependencies in `requirements.txt`
**Evidence:** `requirements.txt` contains `python-telegram-bot`, `pandas-ta`, `matplotlib`, `seaborn` not in `pyproject.toml`
**Impact:** Bloated environments, security surface area increase, version conflict risks

## Acceptance Criteria

### ✅ AC-1: Dead Code Elimination
- [ ] **AC-1.1:** Remove `src/kiss_signal/adapters/yfinance_adapter.py` file completely
- [ ] **AC-1.2:** Verify no imports reference the deleted module anywhere in codebase
- [ ] **AC-1.3:** Remove empty `src/kiss_signal/adapters/` directory if it becomes empty
- [ ] **AC-1.4:** Add entry to `docs/memory.md` documenting the dead code removal and rationale

### ✅ AC-2: Backtester Feature Parity Implementation
- [ ] **AC-2.1:** Implement `baseline` + `layers` strategy testing in `backtester.py`
- [ ] **AC-2.2:** Update `find_optimal_strategies()` to test `baseline` rule alone first
- [ ] **AC-2.3:** Iterate through each `layer` from `config/rules.yaml`, testing `baseline + layer` combinations
- [ ] **AC-2.4:** Return strategies ranked by edge score with rule stack combinations (e.g., "baseline,rsi14_confirm")
- [ ] **AC-2.5:** Maintain backward compatibility with existing strategy format in database
- [ ] **AC-2.6:** Add warning messages for strategies generating fewer trades than `min_trades_threshold`

### ✅ AC-3: Architecture Documentation Accuracy
- [ ] **AC-3.1:** Update `docs/architecture.md` Component Diagram to reflect actual modules:
  - Replace references to `SignalGenerator` with `rules.py` and `backtester.py`
  - Replace references to `DataManager` with `data.py`
  - Ensure all referenced modules actually exist in `src/kiss_signal/`
- [ ] **AC-3.2:** Update Database Schema section to match actual `persistence.py` implementation:
  - Replace `rule_stack` and `trades` tables with `strategies` and `positions` tables
  - Remove foreign key references (denormalized schema)
  - Show JSON storage of rule definitions in `strategies.rule_stack` column
- [ ] **AC-3.3:** Update module descriptions to match actual functionality in codebase
- [ ] **AC-3.4:** Add verification checklist to ensure documentation stays synchronized

### ✅ AC-4: Dependency Management Standardization  
- [ ] **AC-4.1:** Remove `requirements.txt` file completely
- [ ] **AC-4.2:** Migrate any necessary dependencies from `requirements.txt` to `pyproject.toml`
- [ ] **AC-4.3:** Verify all dependencies in `pyproject.toml` are actually used in the codebase
- [ ] **AC-4.4:** Update installation instructions in `README.md` to use `pip install -e .[dev]`
- [ ] **AC-4.5:** Document in `docs/memory.md` that `pyproject.toml` is the single source of truth for dependencies

### ✅ AC-5: Integration & Validation
- [ ] **AC-5.1:** All existing tests pass after changes
- [ ] **AC-5.2:** `mypy` type checking passes with zero errors
- [ ] **AC-5.3:** `python run.py run --freeze-data 2025-01-01` completes successfully
- [ ] **AC-5.4:** Generated reports show rule stack combinations (e.g., "baseline,rsi14_confirm") in NEW BUYS table
- [ ] **AC-5.5:** Database queries work correctly with updated schema documentation alignment

## Detailed Implementation Tasks

### Task 1: Dead Code Elimination
- **File:** `src/kiss_signal/adapters/yfinance_adapter.py`
- **Action:** Delete the entire file and directory if empty
- **Verification:** 
  ```bash
  grep -r "yfinance_adapter" src/ tests/
  # Should return no results
  ```

### Task 2: Baseline + Layers Strategy Implementation
- **File:** `src/kiss_signal/backtester.py`
- **Action:** Enhance `find_optimal_strategies()` method to implement layered strategy testing
- **Core Logic:**
  ```python
  # 1. Test baseline strategy alone
  baseline_result = self._backtest_strategy(baseline_rules, price_data)
  
  # 2. Test baseline + each layer
  for layer_name, layer_rules in layers.items():
      combined_strategy = {**baseline_rules, **layer_rules}
      layer_result = self._backtest_strategy(combined_strategy, price_data)
      # Store with rule_stack like "baseline,rsi14_confirm"
  
  # 3. Return best performing combination by edge score
  ```

### Task 3: Rule Configuration Support
- **File:** `config/rules.yaml`
- **Action:** Ensure structure supports `baseline` and `layers` sections as described in PRD
- **Expected Structure:**
  ```yaml
  baseline:
    # Core entry/exit rules
    
  layers:
    rsi14_confirm:
      # Additional conditions
    bull_regime:
      # Market regime filters
  ```

### Task 4: Architecture Documentation Update
- **File:** `docs/architecture.md`
- **Action:** Replace inaccurate sections with current implementation reality
- **Key Updates:**
  - Component diagram showing actual `src/kiss_signal/` modules
  - Database schema matching `persistence.py` CREATE TABLE statements
  - Remove references to non-existent modules
  - Add note about JSON storage in denormalized schema

### Task 5: Dependency Standardization
- **Files:** `requirements.txt` (delete), `pyproject.toml` (update), `README.md` (update)
- **Actions:**
  1. Review `requirements.txt` for any dependencies not in `pyproject.toml`
  2. Add necessary dependencies to `pyproject.toml` [dev] section if needed
  3. Delete `requirements.txt`
  4. Update README installation instructions

### Task 6: Memory Documentation
- **File:** `docs/memory.md`
- **Action:** Add entries documenting architectural decisions and lessons learned
- **Content:**
  ```markdown
  ## Architectural Debt Remediation (2025-06-26)
  
  ### Dead Code Removed
  - Deleted `src/kiss_signal/adapters/yfinance_adapter.py` - duplicate of data.py functionality
  - Lesson: Always remove unused modules during refactoring to prevent confusion
  
  ### Dependency Management 
  - Standardized on `pyproject.toml` as single source of truth
  - Removed `requirements.txt` to eliminate competing dependency lists
  - Installation: `pip install -e .[dev]`
  
  ### Baseline + Layers Implementation
  - Implemented PRD-specified strategy layering in backtester
  - Rule stacks now show combinations like "baseline,rsi14_confirm"
  - Maintains backward compatibility with existing database schema
  ```

## Definition of Done Checklist

- [ ] **Code Quality:**
  - [ ] All dead code removed from codebase
  - [ ] `mypy` passes with zero errors
  - [ ] All existing tests pass
  - [ ] New strategy layering functionality tested

- [ ] **Documentation:**
  - [ ] `docs/architecture.md` accurately reflects current implementation
  - [ ] Database schema documentation matches `persistence.py`
  - [ ] Component references match actual module structure
  - [ ] `docs/memory.md` updated with architectural decisions

- [ ] **Dependencies:**
  - [ ] Single source of truth: `pyproject.toml` only
  - [ ] No unused dependencies in project
  - [ ] Installation instructions updated in README
  - [ ] Development workflow uses `pip install -e .[dev]`

- [ ] **Feature Compliance:**
  - [ ] Backtester implements `baseline` + `layers` as specified in PRD
  - [ ] Strategy combinations tested and ranked by edge score
  - [ ] Rule stack names show layer combinations (e.g., "baseline,rsi14_confirm")
  - [ ] Warning messages for low-trade strategies implemented

- [ ] **Integration:**
  - [ ] `python run.py run --freeze-data 2025-01-01` completes successfully
  - [ ] Generated reports show proper rule stack combinations
  - [ ] Database operations work correctly
  - [ ] No regression in existing functionality

## Risk Assessment & Mitigation

### High Risk: Breaking Changes in Backtester
- **Risk:** Changing strategy testing logic could break existing database data
- **Mitigation:** Maintain backward compatibility in database schema, test with existing data

### Medium Risk: Documentation Sync Drift
- **Risk:** Documentation could become stale again after fixes
- **Mitigation:** Add verification checklist and process mandate in architecture document

### Low Risk: Dependency Conflicts
- **Risk:** Removing `requirements.txt` could affect deployment scripts
- **Mitigation:** Update all installation documentation and verify development setup

## Success Metrics

1. **Architectural Integrity:** All four critical flaws from audit resolved
2. **Developer Experience:** New developers can onboard using accurate documentation
3. **Feature Completeness:** Backtester delivers PRD-specified baseline + layers functionality
4. **Code Hygiene:** Zero dead code, single dependency source, clean module structure
5. **System Reliability:** No regression in existing functionality, all tests pass

## Related Stories & Dependencies

- **Prerequisite:** Story 009 (Position Tracking) - Provides database schema context
- **Follow-up:** Future story for rule layering optimization and performance tuning
- **Reference:** PRD Section 6 (Functional Requirements) for baseline + layers specification

---

**Technical Debt Note:** This story eliminates technical debt rather than accepting it. All identified issues are treated as bugs/errors requiring immediate resolution rather than conscious debt acceptance.
