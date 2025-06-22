# Story 008: Implement Reporting Module

## Status: 📋 READY FOR DEVELOPMENT

**Priority:** HIGH  
**Estimated Story Points:** 5  
**Prerequisites:** Story 007 (Implement SQLite Persistence Layer) ✅ Complete  
**Created:** 2025-06-22  
**Last Updated:** 2025-06-29 (Incorporating review feedback)

## User Story
As a technical trader, I want the CLI to generate a clean, actionable daily markdown report (`signals_YYYY-MM-DD.md`) that summarizes new buy signals, open positions, and positions to sell so that I can quickly understand what actions to take each day.

## Context & Rationale
This story implements the core reporting functionality that transforms database-stored strategies and signals into the actionable markdown reports specified in the PRD. The report format is explicitly defined in the PRD with specific tables and columns.

**Current State:**
- ✅ Data layer complete (Stories 002-004)
- ✅ Rule functions complete (Story 003)  
- ✅ Backtesting engine complete (Story 005)
- ✅ Persistence layer complete (Story 007) - all strategies stored in SQLite
- 🔄 **Missing:** Daily markdown report generation as specified in PRD
- 🔄 **Missing:** Position tracking and trade lifecycle management (deferred)
- 🔄 **Missing:** NIFTY benchmark comparison for alpha calculation (deferred)

**Architecture Requirements from PRD:**
- Generate `signals_YYYY-MM-DD.md` files with specific table format.
- Include summary line: "Summary: X New Buy Signals, Y Open Positions, Z Positions to Sell".
- Track position lifecycle (entry → holding → exit conditions).
- Compare returns against NIFTY benchmark for alpha calculation.
- Integrate as the final step in the CLI workflow.

## Problem Analysis

### Business Requirements (PRD)
- **Daily Report Format:** Specific markdown tables for NEW BUYS, OPEN POSITIONS, POSITIONS TO SELL.
- **Alpha Tracking:** "For a trade to be considered successful, its backtested return must be greater than the return of the NIFTY 50 index over the identical holding period" (deferred to a future story).
- **Holding Period:** Default 20-day holding period with exit conditions (deferred to a future story).
- **Actionable Output:** Clear recommendations for what to buy, hold, or sell.

### Technical Requirements
- **Read Optimal Strategies:** Query the SQLite database for the best-performing strategy for each symbol from the latest run.
- **Identify New Signals:** For each optimal strategy, apply it to the latest price data to check if a "BUY" signal is active *today*. This is not re-backtesting; it's applying a known-good rule to current data.
- **Track Open Positions (Placeholder):** The report will include sections for open/sell positions, but the logic will be implemented in a future story.
- **Generate Markdown Report:** Create a formatted markdown file using simple string manipulation.
- **CLI Integration:** Integrate the reporting step into the main `run` command's workflow.

## Acceptance Criteria

### Core Functionality
- **AC1:** `generate_daily_report()` function creates a markdown report with the specified format.
  - AC1.1: Creates a file named `signals_YYYY-MM-DD.md` in a configurable output directory.
  - AC1.2: Includes a summary line with counts of new buys, open positions, and positions to sell.
  - AC1.3: Formats the NEW BUYS table with columns: `Ticker`, `Recommended Buy Date`, `Entry Price`, `Rule Stack`, `Edge Score`.
  - AC1.4: Implements placeholder tables for OPEN POSITIONS and POSITIONS TO SELL, clearly stating that full tracking is a future feature.
  - AC1.5: Generates clean, standard markdown using string formatting (not `rich`).

- **AC2:** `identify_new_signals()` function determines buy signals for the current date.
  - AC2.1: Reads the optimal strategies from the database for the current run.
  - AC2.2: For each optimal strategy, applies its rule(s) to the latest price data to check for an entry signal on the most recent day.
  - AC2.3: Filters signals based on a configurable `edge_score_threshold`.
  - AC2.4: Returns structured data (e.g., a list of dictionaries) ready for report generation.

### Integration & Quality
- **AC3:** CLI integration provides a seamless reporting workflow.
  - AC3.1: Adds a `[5/5] Generating report...` step after persistence in the CLI.
  - AC3.2: The report generation process uses the output directory from the `Config` object.
  - AC3.3: Handles report generation failures gracefully (logs the error but does not crash the CLI).
  - AC3.4: On success, prints a message to the console with the path to the generated report file.

- **AC4:** Configuration support for reporting parameters is implemented.
  - AC4.1: Adds a `reports_output_dir` field to the `Config` model (default: `"reports/"`).
  - AC4.2: Adds an `edge_score_threshold` for signal filtering (default: `0.50`).
  - AC4.3: The main `config.yaml` is updated with the new reporting configuration section.

- **AC5:** Test coverage and code quality standards are met.
  - AC5.1: ≥90% test coverage on the `reporter.py` module.
  - AC5.2: Unit tests for report generation with mocked data and database interactions.
  - AC5.3: Integration tests for the CLI workflow including the report generation step.
  - AC5.4: MyPy strict mode compliance with full type hints.

## Technical Design

### Core Functions (`src/kiss_signal/reporter.py`)
The implementation will favor pure functions and avoid a `Reporter` class, in line with H-16.

```python
# src/kiss_signal/reporter.py
from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional
import logging
import json
import sqlite3

from . import data, rules
from .config import Config

__all__ = ["generate_daily_report"]

logger = logging.getLogger(__name__)

# impure
def _fetch_best_strategies(db_path: Path, run_timestamp: str, threshold: float) -> List[Dict[str, Any]]:
    """Private helper to fetch the best strategy for each symbol from a run."""
    # Connects to DB, queries for the top strategy per symbol above threshold.
    # Returns a list of strategy records.

# pure
def _check_for_signal(price_data: pd.DataFrame, rule_def: Dict[str, Any]) -> bool:
    """Private helper to check if a rule triggers on the last day of data."""
    # Gets rule function from rules module, calls it with params.
    # Returns True if signal is active on the last row, False otherwise.

# impure
def _identify_new_signals(
    db_path: Path,
    run_timestamp: str,
    config: Config,
    rules_config: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Identifies new buy signals by applying optimal strategies to latest data."""
    # 1. Fetch best strategies using _fetch_best_strategies.
    # 2. Create a lookup map from rule name to rule definition from rules_config.
    # 3. For each strategy, get latest price data using data.get_price_data.
    # 4. Look up the full rule definition using the name from the DB.
    # 5. Use _check_for_signal to see if the rule is active today.
    # 6. If active, construct a signal dict with Ticker, Date, Entry Price (last close), etc.
    # 7. Return list of new signals.

# impure
def generate_daily_report(
    db_path: Path,
    run_timestamp: str,
    config: Config,
    rules_config: List[Dict[str, Any]]
) -> Optional[Path]:
    """Generates the main daily markdown report."""
    # 1. Call _identify_new_signals to get new buy signals.
    # 2. Create markdown content using string formatting.
    # 3. Write the report to a file in config.reports_output_dir.
    # 4. Return the path to the generated file, or None on failure.
```

### Report Template Format
The generated markdown will strictly follow this format.

```markdown
# Signal Report: 2025-06-29

**Summary:** 2 New Buy Signals, 0 Open Positions, 0 Positions to Sell.

## NEW BUYS
| Ticker | Recommended Buy Date | Entry Price | Rule Stack | Edge Score |
|:-------|:---------------------|:------------|:-----------|:-----------|
| RELIANCE | 2025-06-29 | 2950.75 | sma_10_20_crossover | 0.68 |
| INFY | 2025-06-29 | 1520.25 | rsi_oversold_30 | 0.55 |

## OPEN POSITIONS
*Full position tracking will be implemented in a future story.*

## POSITIONS TO SELL
*Full position tracking will be implemented in a future story.*

---
*Report generated by KISS Signal CLI v1.4 on 2025-06-29*
```

### Configuration Integration
**`config.yaml` additions:**
```yaml
# ... existing configuration ...

# Reporting configuration
reports_output_dir: "reports/"
edge_score_threshold: 0.50
```

**`src/kiss_signal/config.py` addition:**
```python
class Config(BaseModel):
    # ... existing fields ...
    reports_output_dir: str = Field(default="reports/")
    edge_score_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
```

## Implementation Plan

### Files to Create/Modify
1.  **`src/kiss_signal/reporter.py`** (new implementation, ~150 LOC)
    - Implement the functions and helpers as designed above.
2.  **`src/kiss_signal/config.py`** (minimal addition, +2 LOC)
    - Add `reports_output_dir` and `edge_score_threshold` fields.
3.  **`src/kiss_signal/cli.py`** (minimal addition, ~25 LOC)
    - Add a new `[5/5] Generating report...` step.
    - Call `reporter.generate_daily_report` with proper error handling.
4.  **`tests/test_reporter.py`** (new file, ~180 LOC)
    - Comprehensive tests for the public and private functions.
    - Mock database interactions and file system I/O.
5.  **`config.yaml`** (minimal addition, +3 lines)
    - Add the `reporting` configuration section.

### Development Approach
- **Start with data flow:** Implement `_fetch_best_strategies` and its tests first.
- **Implement rule evaluation:** Create `_check_for_signal` and test it with sample data.
- **Orchestrate signal identification:** Implement the main `_identify_new_signals` function.
- **Focus on formatting:** Implement `generate_daily_report` and validate the markdown output against the template.
- **Integrate last:** Add the CLI step after all core functions are tested and working.
- **Follow hard rules:** Use explicit paths, proper error handling, and no silent failures.

## Risk Analysis & Mitigation

### Technical Risks
- **Database query complexity:** Mitigated by using a simple `GROUP BY` and `MAX()` query to find the best strategy per symbol, which is efficient with the existing index.
- **Markdown formatting:** Mitigated by using a simple f-string based template approach.
- **File I/O errors:** Mitigated by wrapping file writes in `try...except` blocks and ensuring the output directory is created with `path.parent.mkdir(parents=True, exist_ok=True)`.

### Business Risks
- **Report format mismatch:** Mitigated by creating a golden file test that compares the generated report against a known-good template.
- **Missing signals:** Mitigated by clear threshold configuration and logging any strategies that are filtered out.

## Definition of Done Checklist

- [ ] All acceptance criteria are met and have been tested.
- [ ] `reporter.py` module is implemented with all core functions.
- [ ] The generated report format exactly matches the PRD specification.
- [ ] CLI integration adds the reporting step without disrupting the existing workflow.
- [ ] Configuration is updated to support reporting parameters.
- [ ] A comprehensive test suite with ≥90% coverage is implemented.
- [ ] All tests are passing, including integration tests.
- [ ] MyPy strict mode compliance is achieved.
- [ ] Error handling covers edge cases like directory permissions.
- [ ] Manual testing of the full CLI workflow with report generation is complete.
- [ ] The generated reports are human-readable and actionable.
- [ ] Code review is completed, focusing on adherence to hard rules.

## Future Stories Planned
This story lays the groundwork for full trade lifecycle management.

- **Story 009: Implement Position Tracking:** Add `trades` and `positions` tables to the database. Implement logic to track open positions, calculate P&L, and evaluate exit conditions. This will populate the `OPEN POSITIONS` and `POSITIONS TO SELL` sections of the report.
- **Story 010: Implement NIFTY Benchmark Integration:** Add NIFTY 50 data fetching and use it to calculate alpha for each trade, fulfilling a key PRD requirement.