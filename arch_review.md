# Architectural Review - 2025-07-09

**Audit Scope:** Baseline audit of the `stock_rule_based` repository.
**Prior `arch_review.md`:** Not found. This audit establishes the baseline.
**Prior `resolved_issues.md`:** Not found. Created empty.

---

## Part 1: Audit of Prior Architectural Mandates & Identification of New Critical Flaws

### A. Compliance Audit of `arch_review.md` Directives

Not applicable. This is the initial audit.

### B. New Critical Architectural Flaws

**-- NEW CRITICAL ARCHITECTURAL FLAW --**
**Category:** Architectural Degeneration / Code Hygiene Failure
**Location:** `src/kiss_signal/adapters/yfinance_adapter.py`
**Description:** The module `yfinance_adapter.py` is a complete duplicate of data fetching logic that is also present and used in `src/kiss_signal/data.py`. The version in `data.py` is more robust, including a retry mechanism. The `yfinance_adapter.py` module is not imported or used anywhere, making it dead code.
**Consequences:** Increased maintenance overhead, confusion for new developers, risk of being used by mistake, and bloating the codebase.
**Justification for Criticality:** Violates the DRY (Don't Repeat Yourself) principle and indicates a lack of code hygiene. It is a structural flaw that should be rectified to maintain a clean and understandable architecture.
**Root Cause Analysis:** An incomplete refactoring where data-fetching logic was moved or consolidated into `data.py`, but the original adapter file was not deleted.
**Systemic Prevention Mandate:** Implement a pre-commit hook or CI step that uses a tool like `vulture` to detect and flag unused code, preventing dead code from being merged into the main branch.

---

**-- NEW CRITICAL ARCHITECTURAL FLAW --**
**Category:** Critical Feature Discrepancy
**Location:** `src/kiss_signal/backtester.py` (implementation) vs. `docs/prd.md` (requirement)
**Description:** The Product Requirements Document (`docs/prd.md`) explicitly describes a core feature for strategy discovery: testing rule `layers` on top of a `baseline` rule to find optimal combinations. The current implementation in `backtester.py` does not support this layering. It only tests each rule from `rules.yaml` in isolation.
**Consequences:** The system fails to deliver on a key promised feature. The core value proposition of discovering synergistic rule combinations is missing, making the backtester fundamentally simpler and less powerful than designed.
**Justification for Criticality:** This is a failure to meet documented core product requirements. The main purpose of the backtester, as specified in the PRD, is not being fulfilled.
**Root Cause Analysis:** The implementation likely simplified the initial approach, and the documentation was never updated to reflect this reduced scope, or the feature was planned but never completed. Evidence in `docs/memory.md` suggests the `baseline` concept existed previously but was lost during refactoring.
**Systemic Prevention Mandate:** Enforce a stricter "Definition of Done" for user stories, requiring that implementation be explicitly verified against all related documentation (PRD, architecture docs) before closure. Add a mandatory item to the Pull Request template checklist: "Confirm implementation matches documented requirements in PRD and architecture.md."

---

**-- NEW CRITICAL ARCHITECTURAL FLAW --**
**Category:** Documentation Veracity Failure
**Location:** `docs/architecture.md`
**Description:** The primary architecture document is dangerously out of sync with the actual implementation. Key discrepancies include:
1.  **Component Diagram & Project Structure:** References non-existent modules like `SignalGenerator` and `DataManager`.
2.  **Database Schema:** Describes a normalized schema with `rule_stack` and `trades` tables using foreign keys. The implementation in `persistence.py` uses a different, denormalized schema with `strategies` and `positions` tables, storing rule definitions as JSON.
**Consequences:** The document is actively misleading, causing severe onboarding friction and creating a false understanding of the system's structure. It undermines all future architectural decisions and maintenance efforts.
**Justification for Criticality:** The single source of truth for the system's architecture is incorrect and unreliable.
**Root Cause Analysis:** A failure in process. Documentation was not updated in lock-step with significant architectural refactoring (e.g., deleting modules, changing the persistence strategy).
**Systemic Prevention Mandate:** Mandate that any Pull Request involving architectural changes (module deletion/addition, database schema changes) MUST include corresponding updates to `docs/architecture.md`. This must be a required, non-negotiable item on the PR template checklist.

---

**-- NEW CRITICAL ARCHITECTURAL FLAW --**
**Category:** Dependency Hygiene Failure
**Location:** `pyproject.toml`, `requirements.txt`
**Description:** The project has two competing dependency lists. `pyproject.toml` should be the single source of truth, but `requirements.txt` contains additional, apparently unused dependencies (`python-telegram-bot`, `pandas-ta`, `matplotlib`, `seaborn`).
**Consequences:** Bloats the development and production environments, increases the security surface area, creates confusion about the project's true dependencies, and can lead to version conflicts.
**Justification for Criticality:** Poor dependency management is a sign of a poorly maintained project. It violates the principle of having a single source of truth and complicates the development environment setup.
**Root Cause Analysis:** `requirements.txt` was likely used for experimentation or for features that were later removed, but it was never cleaned up. The project has not standardized on using `pyproject.toml` for all dependency management.
**Systemic Prevention Mandate:**
1.  Standardize on `pyproject.toml` as the single source of truth for all dependencies (main and dev).
2.  Remove the `requirements.txt` file entirely after ensuring any necessary dependencies are migrated to `pyproject.toml`.
3.  Add a CI check that fails if a `requirements.txt` file is added to the repository.
4.  The standard development workflow must be `pip install -e .[dev]`.

---

## Part 2: Strategic Architectural Imperatives

Not applicable for this baseline audit. The focus must be on rectifying the critical flaws identified above.

---

## Part 3: Actionable Technical Debt Rectification

No new technical debt is being logged. The identified flaws are considered bugs/errors that must be fixed, not accepted as debt. A `technical_debt.md` file will be created but left empty.

---

## Part 4: Audit Conclusion & Next Steps Mandate

1.  **Critical Path to Compliance:**
    1.  **Highest Priority:** Resolve the **Feature Discrepancy** by either implementing the `baseline` + `layer` strategy in the backtester or updating the PRD to reflect the current, simpler implementation. This decision is critical to aligning the product with its documented goals.
    2.  **Second Priority:** Correct the **Stale Architecture Document** to reflect the current state of the codebase, particularly the database schema and component structure.

2.  **System Integrity Verdict:** **DEGRADED**. The system's architectural integrity is compromised due to significant drift between documentation, requirements, and implementation. The presence of dead code and inconsistent dependency management further indicates a need for improved engineering discipline. While the code that is used appears to be of reasonable quality and is well-tested, the architectural and documentary foundations are unsound.

3.  **`arch_review.md` Update Instruction:** This document serves as the `arch_review.md` for the next audit cycle. All four identified flaws are now considered open directives.

4.  **`resolved_issues.md` Maintenance Confirmation:** An empty `resolved_issues.md` has been created. It will be populated as issues from this review are resolved in subsequent cycles.
