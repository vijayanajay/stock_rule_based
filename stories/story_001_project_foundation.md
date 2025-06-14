# Story 001: Project Foundation Setup

**Status:** Ready for Development  
**Estimated Story Points:** 5  
**Priority:** Critical (Blocks all other work)  
**Created:** 2025-01-06  

## User Story
As a technical trader, I want the basic project structure and entry point established so that I can run the `quickedge run` command and see initial progress feedback.

## Acceptance Criteria

### AC1: Basic Package Structure
- [ ] Create `src/kiss_signal/` package with `__init__.py`
- [ ] Create basic module stubs: `cli.py`, `config.py`, `data_manager.py`
- [ ] Ensure `pyproject.toml` is updated to match architecture (entry point: `quickedge`)
- [ ] All modules have proper type hints and minimal docstrings

### AC2: CLI Entry Point
- [ ] Implement basic `quickedge run` command using Typer
- [ ] Support `--verbose` and `--freeze-data YYYY-MM-DD` flags
- [ ] Display project banner and placeholder progress steps
- [ ] Command exits cleanly with status 0 for success

### AC3: Configuration Foundation
- [ ] Create basic Pydantic models for `EdgeScoreWeights` 
- [ ] Implement `config.py` module to load and validate `config.yaml`
- [ ] Add schema validation with clear error messages
- [ ] Support `win_pct` and `sharpe` weights that sum to 1.0

### AC4: Quality Gates
- [ ] `pytest` runs and passes (even with placeholder tests)
- [ ] `mypy` passes with no errors
- [ ] `quickedge run --freeze-data 2025-01-01` completes without crashes
- [ ] All files follow the coding instructions (≤25 LOC changes per component)

## Technical Requirements

### Dependencies (Already in requirements.txt)
- `typer` for CLI framework
- `pydantic>=2.0.0` for config validation
- `pyyaml>=6.0` for YAML parsing
- `rich` for terminal output (mandatory per architecture)

### File Structure to Create
```
src/
└── kiss_signal/
    ├── __init__.py
    ├── cli.py          # Typer-based CLI entry point
    ├── config.py       # Pydantic models + YAML loading
    └── data_manager.py # Placeholder for future data handling
```

### Key Design Constraints
- **Modular Monolith:** All code in single package, clear module boundaries
- **KISS Principle:** Minimal, boring code - no premature optimization
- **Rich Output:** All terminal feedback through `rich` helpers
- **Type Safety:** Full type hints on every function signature
- **No New Dependencies:** Stick to blessed stack only

## Definition of Done
1. ✅ `quickedge run` command executes and shows progress steps
2. ✅ `quickedge --help` displays command options correctly  
3. ✅ Basic config validation works (can detect malformed YAML)
4. ✅ `pytest` and `mypy` both pass
5. ✅ Code follows architecture patterns (logging, error handling)
6. ✅ All new code is ≤25 LOC per module for this story

## Out of Scope
- Actual data fetching or signal generation
- Database setup or backtesting logic
- Complex error handling or recovery
- Any GUI or web interface components

## Notes for Implementation
- Start with `cli.py` as the entry point
- Use placeholder methods that print their intended actions
- Focus on the "happy path" - basic structure working end-to-end
- Remember: this is the foundation for all subsequent stories

## Related Stories
- Story 002: Data Manager & NSE Data Fetching (depends on this)
- Story 003: SQLite Persistence Layer (depends on this)
- Story 004: Basic Backtesting Framework (depends on stories 002, 003)
