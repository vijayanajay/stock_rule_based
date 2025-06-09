# Resolved Architectural Issues Log

This file tracks issues that have been resolved, including their re-open history.

**Last Updated:** 2025-06-02

---
**Issue ID:** FLAW-20250601-001
**Status:** RESOLVED
**Resolution Date:** 2025-06-02
**Summary of Resolution:**
The local `ConfigError` definition was removed from `src/meqsap/config.py`. The `src/meqsap/cli.py` module was verified to exclusively import and use `ConfigurationError` from `src/meqsap/exceptions.py`, adhering to `docs/adr/004-error-handling-policy.md`.

---
**Issue ID:** FLAW-20250601-002
**Status:** RESOLVED
**Resolution Date:** 2025-06-02
**Summary of Resolution:**
The exception hierarchy diagram in `docs/adr/004-error-handling-policy.md` and the "Exception Mapping" table in `docs/policies/error-handling-policy.md` were verified to include the CLI-specific exceptions (`DataAcquisitionError`, `BacktestExecutionError`, `ReportGenerationError`) as subclasses of `CLIError`, aligning documentation with the implemented error handling.

---
**Issue ID:** FLAW-20250601-003
**Status:** RESOLVED
**Resolution Date:** 2025-06-02
**Summary of Resolution:**
The "Project Structure" diagram in `docs/architecture.md` was verified to include `src/meqsap/exceptions.py`, the `examples/` directory, and details of the `docs/` subdirectories (e.g., `adr/`, `policies/`), accurately reflecting the current project structure.

---
**Issue ID:** FLAW-20250601-004
**Status:** RESOLVED
**Resolution Date:** 2025-06-02
**Summary of Resolution:**
Corrected the example validation logic in `docs/adr/adr-002-date-range-handling.md` (section "Internal Implementation") to reflect the actual correct check, ensuring data for the inclusive `end_date` is present after yfinance fetching and adjustment.

---
**Issue ID:** FLAW-20250602-001
**Original Description (Concise):** Incorrect error handling and exit code (5 instead of 10) for unexpected exceptions in `cli.py`. Type hint violation for error handling utility functions.
**Initial Resolution Summary (Concise):** Corrected exit codes to 10 in `_main_pipeline` and `analyze_command` for generic exceptions. Fixed `_generate_error_message` call in `_main_pipeline`. Updated type hints for `_generate_error_message` and `_get_recovery_suggestions` to accept `Exception`.
**Date First Resolved:** 2025-06-02
**Reopen Count:** 0
**Last Reopened Date:**
**Last Resolution Summary (Concise):** Corrected exit codes to 10 in `_main_pipeline` and `analyze_command` for generic exceptions. Fixed `_generate_error_message` call in `_main_pipeline`. Updated type hints for `_generate_error_message` and `_get_recovery_suggestions` to accept `Exception`.
**Date Last Resolved:** 2025-06-02
