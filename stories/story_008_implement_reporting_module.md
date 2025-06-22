# Story 008: Implement Reporting Module

## Status: 📋 READY FOR DEVELOPMENT

**Priority:** HIGH  
**Estimated Story Points:** 5  
**Prerequisites:** Story 007 (Implement SQLite Persistence Layer) ✅ Complete  
**Created:** 2025-06-22  

## User Story
As a technical trader, I want the CLI to generate a clean, actionable daily markdown report (`signals_YYYY-MM-DD.md`) that summarizes new buy signals, open positions, and positions to sell so that I can quickly understand what actions to take each day.

## Context & Rationale
This story implements the core reporting functionality that transforms database-stored strategies and signals into the actionable markdown reports specified in the PRD. The report format is explicitly defined in the PRD with specific tables and columns.

**Current State:**
- ✅ Data layer complete (Stories 002-004)
- ✅ Rule functions complete (Story 003)  
- ✅ Backtesting engine complete (Story 005)
- ✅ Signal generation functional (Story 006)
- ✅ Persistence layer complete (Story 007) - all strategies stored in SQLite
- 🔄 **Missing:** Daily markdown report generation as specified in PRD
- 🔄 **Missing:** Position tracking and trade lifecycle management
- 🔄 **Missing:** NIFTY benchmark comparison for alpha calculation

**Architecture Requirements from PRD:**
- Generate `signals_YYYY-MM-DD.md` files with specific table format
- Include summary line: "Summary: X New Buy Signals, Y Open Positions, Z Positions to Sell"
- Track position lifecycle (entry → holding → exit conditions)
- Compare returns against NIFTY benchmark for alpha calculation
- Integrate as step [4/5] in CLI workflow after persistence

## Problem Analysis

### Business Requirements (PRD)
- **Daily Report Format:** Specific markdown tables for NEW BUYS, OPEN POSITIONS, POSITIONS TO SELL
- **Alpha Tracking:** "For a trade to be considered successful, its backtested return must be greater than the return of the NIFTY 50 index over the identical holding period"
- **Holding Period:** Default 20-day holding period with exit conditions
- **Actionable Output:** Clear recommendations for what to buy, hold, or sell

### Technical Requirements
- Read optimal strategies from SQLite database (persisted by Story 007)
- Generate signals for current date based on latest price data
- Track open positions and calculate current returns vs NIFTY
- Determine exit conditions (20-day limit, strategy change, stop-loss)
- Output formatted markdown with rich tables
- Integrate into CLI as final step after persistence

### Current Integration Points
- **Input:** Strategies in SQLite database from `persistence.save_strategies_batch()`
- **CLI Integration:** Add as step [4/5] after `_save_results()` in `cli.py`
- **Data Sources:** Latest price data from `data` module, stored strategies from database
- **Future Enhancement:** Position tracking will require additional database tables in future stories

## Acceptance Criteria

### Core Functionality
- **AC1:** `generate_daily_report()` function creates markdown report with specified format
  - AC1.1: Creates file named `signals_YYYY-MM-DD.md` in configurable output directory
  - AC1.2: Includes summary line with counts of new buys, open positions, positions to sell
  - AC1.3: Formats NEW BUYS table with columns: Ticker, Recommended Buy Date, Entry Price, Rule Stack, Edge Score
  - AC1.4: Implements placeholder tables for OPEN POSITIONS and POSITIONS TO SELL (full tracking in future story)
  - AC1.5: Uses Rich formatting for clean table output in markdown

- **AC2:** `identify_new_signals()` function determines buy signals for current date
  - AC2.1: Reads optimal strategies from database for current run
  - AC2.2: Applies strategies to latest price data to generate entry signals
  - AC2.3: Filters signals based on edge score threshold from config
  - AC2.4: Returns structured data for report generation

### Integration & Quality
- **AC3:** CLI integration provides seamless reporting workflow
  - AC3.1: Add `[4/5] Generating report...` step after persistence in CLI
  - AC3.2: Report generation uses output directory from config
  - AC3.3: Graceful error handling if report generation fails
  - AC3.4: Success message shows path to generated report file

- **AC4:** Configuration support for reporting parameters
  - AC4.1: Add `reports_output_dir` field to Config model (default: "reports/")
  - AC4.2: Add `edge_score_threshold` for signal filtering (default: 0.50)
  - AC4.3: Update `config.yaml` with reporting configuration

- **AC5:** Test coverage and code quality standards are met
  - AC5.1: ≥90% test coverage on the `reporter.py` module
  - AC5.2: Unit tests for report generation with mocked data
  - AC5.3: Integration tests for CLI workflow with report generation
  - AC5.4: MyPy strict mode compliance with full type hints

## Technical Design

### Core Functions (`src/kiss_signal/reporter.py`)
```python
# src/kiss_signal/reporter.py
from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional
import logging

__all__ = ["generate_daily_report", "identify_new_signals"]

logger = logging.getLogger(__name__)

def identify_new_signals(
    db_path: Path, 
    run_timestamp: str,
    edge_score_threshold: float = 0.50
) -> List[Dict[str, Any]]:
    """Identify new buy signals from latest strategy run."""
    # Read strategies from database for given run_timestamp
    # Filter by edge_score_threshold
    # Return list of signal dictionaries

def generate_daily_report(
    signals: List[Dict[str, Any]],
    report_date: date,
    output_dir: Path
) -> Path:
    """Generate daily markdown report with buy signals."""
    # Create markdown content with specified format
    # Include summary line and NEW BUYS table
    # Add placeholder sections for future position tracking
    # Write to signals_YYYY-MM-DD.md file
    # Return path to generated file
```

### Report Template Format
```markdown
# Signal Report: 2025-06-22

**Summary:** 2 New Buy Signals, 0 Open Positions, 0 Positions to Sell.

## NEW BUYS
| Ticker | Recommended Buy Date | Entry Price | Rule Stack | Edge Score |
|:-------|:---------------------|:------------|:-----------|:-----------|
| RELIANCE | 2025-06-22 | 2950.75 | sma_crossover | 0.68 |
| INFY | 2025-06-22 | 1520.25 | rsi_oversold + bull_regime | 0.55 |

## OPEN POSITIONS
*Position tracking will be implemented in a future story.*

## POSITIONS TO SELL
*Position tracking will be implemented in a future story.*

---
*Report generated by KISS Signal CLI v1.4 on 2025-06-22*
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
1. **`src/kiss_signal/reporter.py`** (new implementation, ~120 LOC)
   - Implement `identify_new_signals` and `generate_daily_report` functions
   - Add markdown formatting utilities
   - Database query functions for reading strategies

2. **`src/kiss_signal/config.py`** (minimal addition, +2 LOC)
   - Add `reports_output_dir` and `edge_score_threshold` fields

3. **`src/kiss_signal/cli.py`** (minimal addition, ~20 LOC)
   - Add `[4/5] Generating report...` step after persistence
   - Call reporting functions with proper error handling
   - Display success message with report path

4. **`tests/test_reporter.py`** (new file, ~150 LOC)
   - Comprehensive tests for both core functions
   - Mock database interactions
   - Test markdown format validation

5. **`config.yaml`** (minimal addition, +3 lines)
   - Add reporting configuration keys

### Development Approach
- **Start with data flow:** Implement database reading for strategies first
- **Mock position tracking:** Add placeholder sections for future stories
- **Test markdown format:** Ensure output matches PRD specification exactly
- **CLI integration last:** Add reporting step after core functions work
- **Follow KISS principles:** Simple, focused implementation with clear error handling

## Risk Analysis & Mitigation

### Technical Risks
- **Database query complexity:** Mitigated by simple SELECT queries on existing schema
- **Markdown formatting:** Mitigated by using Python f-strings and template approach
- **File I/O errors:** Mitigated by proper error handling and directory creation

### Business Risks
- **Report format mismatch:** Mitigated by exact template matching PRD specification
- **Missing signals:** Mitigated by clear threshold configuration and logging

## Definition of Done Checklist

- [ ] All acceptance criteria are met and have been tested
- [ ] `reporter.py` module is implemented with both core functions
- [ ] Report format exactly matches PRD specification
- [ ] CLI integration adds reporting step without disrupting workflow
- [ ] Configuration is updated to support reporting parameters
- [ ] Comprehensive test suite with ≥90% coverage is implemented
- [ ] All tests are passing, including integration tests
- [ ] MyPy strict mode compliance is achieved
- [ ] Error handling covers edge cases like directory permissions
- [ ] Manual testing of full CLI workflow with report generation
- [ ] Generated reports are human-readable and actionable
- [ ] Code review completed, focusing on KISS principles

## Validation Approach

### Unit Testing
- Report generation with sample signal data
- Database query functions with mocked database
- Markdown formatting validation
- Configuration integration testing

### Integration Testing
- End-to-end workflow: persistence → reporting
- CLI integration with real configuration files
- File system operations with temporary directories

### Manual Validation
- Run `python run.py run` and verify report file creation
- Inspect generated markdown for correct format and content
- Verify report directory creation and file permissions
- Test with various edge score thresholds and signal counts

---

## Future Stories Planned

After Story 008 (Reporting Module) is complete, the following stories are planned to complete the KISS Signal CLI v1.4:

### Story 009: Implement Position Tracking and Trade Lifecycle Management
**Priority:** HIGH | **Story Points:** 8  
**Dependencies:** Story 008 (Reporting Module)

**Scope:** Implement full position tracking with entry/exit logic, stop-loss conditions, and 20-day holding period management. Add database tables for `trades` and `positions`. Complete the OPEN POSITIONS and POSITIONS TO SELL sections in daily reports.

**Key Features:**
- Database schema extension with `trades` and `positions` tables
- Position entry logic when buy signals are generated
- Exit condition evaluation (20-day limit, strategy change, stop-loss)
- Current position P&L calculation with NIFTY benchmark comparison
- Complete OPEN POSITIONS and POSITIONS TO SELL report sections

### Story 010: Implement NIFTY Benchmark Integration
**Priority:** MEDIUM | **Story Points:** 3  
**Dependencies:** Story 009 (Position Tracking)

**Scope:** Add NIFTY 50 index data fetching and benchmark comparison for alpha calculation. Implement the PRD requirement that "trade success" requires beating NIFTY returns over identical holding periods.

**Key Features:**
- NIFTY 50 price data integration via yfinance
- Benchmark return calculation for position periods
- Alpha calculation (position return - NIFTY return)
- Enhanced reporting with alpha metrics in position tables

### Story 011: Enhanced CLI Features and Data Management
**Priority:** MEDIUM | **Story Points:** 5  
**Dependencies:** Story 010 (NIFTY Benchmark)

**Scope:** Implement additional CLI commands for data management, historical report viewing, and performance analysis. Add cache management and data validation features.

**Key Features:**
- `quickedge history` command for viewing past reports
- `quickedge performance` command for portfolio analysis
- `quickedge cache --refresh` for data management
- Data validation and error recovery features
- Enhanced logging and debugging capabilities

### Story 012: Configuration Enhancement and Rule Validation
**Priority:** LOW | **Story Points:** 3  
**Dependencies:** Story 011 (Enhanced CLI)

**Scope:** Add advanced configuration features, rule validation, and parameter optimization capabilities. Implement configurable edge score weights and strategy selection criteria.

**Key Features:**
- Configurable EdgeScore weights (win_pct vs sharpe ratio)
- Rule stack validation and dependency checking
- Parameter range validation for technical indicators
- Configuration file validation and error reporting

### Story 013: Performance Optimization and Production Readiness
**Priority:** LOW | **Story Points:** 4  
**Dependencies:** Story 012 (Configuration Enhancement)

**Scope:** Optimize performance for larger datasets, implement caching strategies, and add production-ready features like concurrent processing and memory management.

**Key Features:**
- Concurrent strategy analysis for multiple symbols
- Improved caching strategies for historical data
- Memory optimization for large datasets
- Database performance optimization and indexing
- Error recovery and retry logic for API failures

---

## Implementation Progress Log

### 📋 Status: Ready for Development
This story is prepared and ready for implementation. All prerequisites are complete and requirements are clearly defined.

**Next Steps:**
1. Create `src/kiss_signal/reporter.py` with core functions
2. Update configuration to support reporting parameters
3. Implement CLI integration for report generation
4. Create comprehensive test suite
5. Validate end-to-end workflow with manual testing

---

**Current Status:** Story 008 is **READY FOR DEVELOPMENT** - all prerequisites complete, requirements defined.

**Dependencies Met:**
- ✅ Story 007 (Persistence) - SQLite database operations functional
- ✅ Strategy data available in database for report generation
- ✅ CLI framework ready for additional workflow steps

**Expected Delivery:**
- Daily markdown reports matching PRD specification
- Integration into existing CLI workflow as step [4/5]
- Foundation for future position tracking and trade management
- Clear, actionable output for daily trading decisions
