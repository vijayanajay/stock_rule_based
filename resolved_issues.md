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
