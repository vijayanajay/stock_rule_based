# Resolved Architectural Issues

This file serves as a historical log of architectural issues that have been addressed.
When an issue from `arch_review.md` is resolved, its entry is moved here.

---
**Issue ID:** DEAD-CODE-20250709
**Original Description (Concise):** The module `src/kiss_signal/adapters/yfinance_adapter.py` was unused dead code, duplicating logic from `data.py`.
**Initial Resolution Summary (Concise):** The obsolete `yfinance_adapter.py` module and its parent `adapters` directory were deleted from the codebase.
**Date First Resolved:** 2025-07-16
**Reopen Count:** 0
**Last Reopened Date:** 
**Last Resolution Summary (Concise):** The obsolete `yfinance_adapter.py` module and its parent `adapters` directory were deleted from the codebase.
**Date Last Resolved:** 2025-07-16
---
**Issue ID:** FEATURE-DISCREPANCY-20250709
**Original Description (Concise):** The backtester did not implement the `baseline` + `layers` strategy discovery mechanism specified in the PRD.
**Initial Resolution Summary (Concise):** The `backtester.py` module was updated to correctly implement the `baseline` + `layers` logic. It now tests the baseline rule alone, and then the baseline combined with each layer, ranking the results.
**Date First Resolved:** 2025-07-16
**Reopen Count:** 0
**Last Reopened Date:** 
**Last Resolution Summary (Concise):** The `backtester.py` module was updated to correctly implement the `baseline` + `layers` logic. It now tests the baseline rule alone, and then the baseline combined with each layer, ranking the results.
**Date Last Resolved:** 2025-07-16
---
**Issue ID:** DEP-HYGIENE-20250709
**Original Description (Concise):** The project had two competing dependency lists (`pyproject.toml` and `requirements.txt`).
**Initial Resolution Summary (Concise):** The `requirements.txt` file was deleted, standardizing on `pyproject.toml` as the single source of truth for all project dependencies.
**Date First Resolved:** 2025-07-16
**Reopen Count:** 0
**Last Reopened Date:** 
**Last Resolution Summary (Concise):** The `requirements.txt` file was deleted, standardizing on `pyproject.toml` as the single source of truth for all project dependencies.
**Date Last Resolved:** 2025-07-16
---
**Issue ID:** DOC-VERACITY-20250709
**Original Description (Concise):** `docs/architecture.md` was out of sync with the codebase, referencing non-existent modules and an incorrect project structure.
**Initial Resolution Summary (Concise):** The "Project Structure" section in `docs/architecture.md` was updated to remove all references to obsolete files and add missing modules, bringing the document into full alignment with the codebase.
**Date First Resolved:** 2025-07-17
**Reopen Count:** 0
**Last Reopened Date:** 
**Last Resolution Summary (Concise):** The "Project Structure" section in `docs/architecture.md` was updated to remove all references to obsolete files and add missing modules, bringing the document into full alignment with the codebase.
**Date Last Resolved:** 2025-07-17
---
**Issue ID:** TEST-HARNESS-INTEGRITY-20250713
**Original Description (Concise):** Two CLI tests were structurally flawed: `test_run_command_backtest_generic_exception_verbose` used incorrect argument order (`--verbose` after `run` command), and `test_run_command_help` was not self-contained, failing due to main callback dependencies on configuration files.
**Initial Resolution Summary (Concise):** Fixed argument order in `test_run_command_backtest_generic_exception_verbose` to place `--verbose` before the `run` command. Modified `test_run_command_help` to test main application help (`--help`) instead of subcommand help, eliminating configuration file dependencies.
**Date First Resolved:** 2025-07-13
**Reopen Count:** 0
**Last Reopened Date:** 
**Last Resolution Summary (Concise):** Fixed argument order in `test_run_command_backtest_generic_exception_verbose` to place `--verbose` before the `run` command. Modified `test_run_command_help` to test main application help (`--help`) instead of subcommand help, eliminating configuration file dependencies.
**Date Last Resolved:** 2025-07-13
