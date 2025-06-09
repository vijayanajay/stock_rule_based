# MEQSAP Technical Debt Log

This document tracks identified technical debt items, their context, impact, and proposed rectification.

**Last Updated:** 2025-06-01

---
**-- TECHNICAL DEBT ITEM (NEW/UPDATED) --**
**Debt Title:** Ambiguity in `run_backtest` Data/Signal Input Handling
**Unique Identifier:** TD-20250601-001
**Origin/Context:** Audit finding (2025-06-01). The `run_backtest` function in `src/meqsap/backtest.py` has a complex way of determining `prices_data` and `signals` when its `data` argument is a dictionary. If `run_complete_backtest` passes a dictionary to `run_backtest` that contains `'prices'` but omits `'signals'`, `run_backtest` will fail. The docstring is also slightly ambiguous about precedence.
**Status (if updating existing):** NOT STARTED
**Detailed Description:**
    Current: The `run_backtest` function allows `data` to be a dict or DataFrame. If dict, it expects `prices` and optionally `signals`. If the `signals` parameter to `run_backtest` is `None` (as it is when called by `run_complete_backtest`), it then tries to get `signals` from `data.get('signals')`. If `data` (the dict) doesn't have a `'signals'` key, it raises an error. This specific failure path for `run_complete_backtest` (if it were to pass a dict with only prices) is not explicitly documented or guarded against in `run_complete_backtest`.
    Ideal: The interaction between `run_complete_backtest` and `run_backtest` regarding data and signal passing should be crystal clear and robust. `run_backtest`'s docstring should precisely define behavior for all input combinations. `run_complete_backtest` should ensure it always calls `run_backtest` with valid arguments.
    Why Debt: Current logic is slightly convoluted and could lead to unexpected `BacktestError` if `run_backtest` is used in new ways or if `run_complete_backtest` internals change.
**Impact/Consequences:** Potential for runtime errors if `run_backtest` is used in new ways or if `run_complete_backtest` internals change. Reduced code clarity for developers trying to understand data flow.
**Proposed Rectification (Task/Feature):**
    * Goal: Clarify and simplify data/signal passing between `run_complete_backtest` and `run_backtest`.
    * Specific Actionable Steps:
        1.  Refactor `run_backtest` to have a more straightforward way of accepting price and signal data (e.g., dedicated parameters for price DataFrame and signal DataFrame, removing the dict option or making its contract stricter).
        2.  Update `run_complete_backtest` to align with the refactored `run_backtest` signature.
        3.  Improve docstrings in both functions to leave no ambiguity about input expectations.
        4.  Add specific unit tests for different input combinations to `run_backtest`.
    * Acceptance Criteria / Definition of Done:
        1.  `run_backtest` signature is clear and less prone to ambiguous input combinations.
        2.  `run_complete_backtest` correctly prepares data for `run_backtest`.
        3.  Docstrings are updated and unambiguous.
        4.  New unit tests pass.
**Estimated Effort/Priority:** Medium / Medium

---
**-- TECHNICAL DEBT ITEM (NEW/UPDATED) --**
**Debt Title:** Overly Permissive `safe_float` Conversion
**Unique Identifier:** TD-20250601-002
**Origin/Context:** Audit finding (2025-06-01). The `safe_float` function in `src/meqsap/backtest.py` defaults to 0.0 and logs a warning for many types of conversion errors, including `None`, `NaN`, `inf`, `ValueError`, `TypeError`.
**Status (if updating existing):** NOT STARTED
**Detailed Description:**
    Current: `safe_float` converts various non-float inputs (or problematic floats like NaN/inf) to a default value (0.0) and logs a warning. This is used when parsing portfolio statistics from `vectorbt` and trade details.
    Ideal: While robust, this behavior might mask underlying data issues or changes in `vectorbt`'s output. For critical metrics, a failure to convert might indicate a more severe problem that should halt execution or be handled more explicitly than just defaulting to 0.0.
    Why Debt: Suppressing potential errors by defaulting can lead to silent failures or incorrect metrics being reported without clear indication of the root data problem. The skipped test `tests/test_float_handling.py :: TestFloatConversions.test_mock_stats_with_non_numeric` suggests this area needs more thought.
**Impact/Consequences:** Potentially misleading backtest results if underlying data from `vectorbt` is corrupted or in an unexpected format. Makes debugging harder if errors are silently converted to defaults.
**Proposed Rectification (Task/Feature):**
    * Goal: Make float conversion more explicit about failure for critical metrics while retaining robustness for non-critical ones.
    * Specific Actionable Steps:
        1.  Identify which metrics parsed by `safe_float` are absolutely critical (e.g., final portfolio value, core returns) versus less critical or optional.
        2.  For critical metrics, modify the parsing logic: instead of `safe_float` with a default, attempt direct conversion and raise a `BacktestError` if conversion fails for unexpected reasons (e.g., string value where number is expected). `None` or `NaN` from `vectorbt` might still be handled by defaulting, but unexpected types should be errors.
        3.  For non-critical/optional metrics, `safe_float` might still be appropriate, but ensure warnings are prominent.
        4.  Re-evaluate and implement the skipped test `test_mock_stats_with_non_numeric` to cover various scenarios.
    * Acceptance Criteria / Definition of Done:
        1.  Conversion of critical backtest metrics is strict; unexpected non-numeric data causes a `BacktestError`.
        2.  Non-critical metrics are handled robustly, with clear warnings if defaults are used.
        3.  The skipped test is implemented and passes.
        4.  Logging for conversion issues is clear and actionable.
**Estimated Effort/Priority:** Medium / Medium

---
**-- TECHNICAL DEBT ITEM (NEW/UPDATED) --**
**Debt Title:** Fragile Close Price Column Discovery
**Unique Identifier:** TD-20250601-003
**Origin/Context:** Audit finding (2025-06-01). Both `src/meqsap/backtest.py::StrategySignalGenerator._generate_ma_crossover_signals` and `src/meqsap/backtest.py::run_backtest` use a multi-step `if/elif/else` logic to find the 'Close' price column.
**Status (if updating existing):** NOT STARTED
**Detailed Description:**
    Current: The logic `[col for col in data.columns if col.lower() == 'close']` and `[col for col in aligned_data.columns if 'price' in col.lower() or 'close' in col.lower()]` can be fragile. For example, 'Adjusted Close' would not be found by `col.lower() == 'close'`, and if there are multiple columns with 'price' (e.g. 'entry_price', 'exit_price', 'close_price'), it picks the first one found.
    Ideal: Data column names should be normalized early in the data ingestion pipeline (e.g., in `src/meqsap/data.py` after fetching from yfinance) to a consistent format (e.g., all lowercase: 'open', 'high', 'low', 'close', 'volume'). Downstream modules would then expect these consistent names.
    Why Debt: Increases the chance of `BacktestError` if input data columns don't exactly match expected patterns. Makes the code in `backtest.py` more complex.
**Impact/Consequences:** Reduced robustness to variations in input data column naming. Potential for using the wrong price column in calculations.
**Proposed Rectification (Task/Feature):**
    * Goal: Standardize price column names at the data ingestion phase.
    * Specific Actionable Steps:
        1.  In `src/meqsap/data.py`, after `yf.download()`, add a step to normalize OHLCV column names to a consistent format (e.g., lowercase 'open', 'high', 'low', 'close', 'volume').
        2.  Update `src/meqsap/backtest.py` (and any other modules consuming this data) to expect these standardized column names, simplifying the column access logic.
        3.  Ensure ADR-002 or another relevant ADR documents this column naming convention if it's not already covered.
        4.  Update unit tests to reflect this change.
    * Acceptance Criteria / Definition of Done:
        1.  `data.py` normalizes OHLCV column names upon fetching.
        2.  `backtest.py` (and other consumers) use standardized column names.
        3.  Code for column discovery in `backtest.py` is simplified.
        4.  Relevant ADRs updated if necessary.
**Estimated Effort/Priority:** Low / Medium
