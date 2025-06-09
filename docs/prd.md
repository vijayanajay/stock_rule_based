# MEQSAP Product Requirements Document (PRD) - v2.0

## 1. Goal, Objective, and Context

* **Goal:** To build a command-line tool, the Minimum Viable Quantitative Strategy Analysis Pipeline (MEQSAP), that can take a simple strategy configuration file, run a complete backtest, perform robustness checks, and present a clear, actionable verdict.
* **Objective:** The core principle is to rapidly develop this end-to-end "happy path" by orchestrating powerful, existing Python libraries (`vectorbt`, `pyfolio`, `pydantic`, etc.). The focus is on high-level integration and logic validation ("Vibe Checks") rather than writing low-level, boilerplate code.
* **Context:** This project is for a user who wants to quickly and reliably analyze quantitative trading strategies using a simple, configuration-driven CLI tool. The MVP must prove the viability of the orchestration-first approach.

## 2. User Stories (MVP)

1.  **As a strategist, I want to** define a trading strategy (e.g., a moving average crossover) in a simple `.yaml` file **so that** I can configure a backtest without writing any Python code.
2.  **As a strategist, I want the tool to** validate my `.yaml` configuration against a predefined schema **so that** I am immediately alerted to typos or invalid parameter combinations (e.g., `slow_ma` < `fast_ma`).
3.  **As a strategist, I want the tool to** automatically download the necessary historical price data for a given ticker **so that** I don't have to manage data files manually.
4.  **As a strategist, I want the tool to** cache downloaded data **so that** subsequent runs on the same data are fast and don't repeatedly call the data provider's API.
5.  **As a strategist, I want the tool to** run a complete backtest on my defined strategy using a single command **so that** I can see its performance statistics.
6.  **As a strategist, I want to** see a clean, formatted "Executive Verdict" table in my terminal **so that** I can quickly assess the strategy's performance and the results of all validation checks.
7.  **As a strategist, I want the tool to** automatically perform "Vibe Checks" (e.g., ensuring at least one trade occurred) **so that** I can instantly spot obviously flawed or inactive strategies.
8.  **As a strategist, I want the tool to** run automated robustness checks (e.g., re-running with high fees) **so that** I can understand how sensitive my strategy is to real-world costs.
9.  **As a strategist, I want the option to** generate a comprehensive, institutional-grade PDF report using a command-line flag (`--report`) **so that** I can perform a deeper analysis or share the results.
10. **As a developer, I want the tool to** provide clear, user-friendly error messages (e.g., for a bad ticker or malformed config file) **so that** users can self-diagnose and fix problems easily.

## 3. Functional Requirements (MVP)

The system must be able to:

* **Strategy Configuration:**
    1.  Load a backtest strategy from a `.yaml` configuration file using `yaml.safe_load()` for security.
    2.  Validate the loaded configuration against a predefined Pydantic schema.
* **Data Handling:**
    3.  Acquire historical OHLCV data for a specified ticker from `yfinance`.
    4.  Implement a file-based caching system for downloaded data (e.g., using Parquet or Feather format) to improve performance on subsequent runs.
    5.  Perform data integrity "Vibe Checks" post-download to validate data for completeness (no NaN values) and freshness.
* **Backtesting Core:**
    6.  Generate entry and exit signals based on the strategy's rules by leveraging a library like `pandas-ta`.
    7.  Execute a full backtest using the generated signals with a single command from the `vectorbt` library.
* **Results & Reporting:**
    8.  Print the core performance statistics from the backtest result.
    9.  Perform a "Vibe Check" to ensure the strategy generated at least one trade.
    10. Conduct an automated robustness "Vibe Check" by re-running the simulation with high fees and by reporting the strategy's turnover rate.
    11. Display a formatted "Executive Verdict" in the terminal using the `rich` library, presenting key metrics and the pass/fail status (e.g., ✅/❌) of all "Vibe Checks".
    12. Generate a comprehensive PDF report ("tear sheet") using `pyfolio` when the `--report` flag is used.
* **CLI & Diagnostics:**
    13. Provide a `--verbose` flag to print detailed logs for debugging user-reported issues.
    14. Provide a `--version` flag that outputs the tool's version and the versions of its key dependencies.

## 4. Non-Functional Requirements (MVP)

* **Reliability:** The pipeline must be reliable and produce consistent, reproducible results, achieved by leveraging battle-tested libraries for core operations.
* **Modularity & Maintainability:** The codebase will be highly maintainable by strictly adhering to the "orchestration-first" principle and being structured into distinct modules with clear separation of concerns (e.g., `cli`, `config`, `data`, `backtest`, `reporting`).
* **Code Quality:** Pydantic must be used heavily for all data validation. The entire codebase must use Python's native type hints.
* **Dependency Management:** Project dependencies **must** be explicitly defined and frozen `requirements.txt` to ensure a completely reproducible environment.
* **Performance:** The backtesting process should be fast enough for iterative testing, aided by the required data caching mechanism.
* **Packaging:** The application should be packaged for distribution via PyPI to ensure easy installation for end-users (`pip install meqsap`).

## 5. Technical Assumptions

* **Repository & Service Architecture:** The application will be a **Monolith** contained within a **single repository (Monorepo)**.
* **Core Libraries:** The project is an orchestration of the following key Python libraries: `yfinance`, `vectorbt`, `pyyaml`, `pydantic`, `pandas`, `pandas-ta`, `rich`, and `pyfolio`.
* **Language:** Python 3.9+.
* **Platform:** A command-line tool for standard terminal environments (Linux, macOS, Windows).

## 6. Epic Overview

**Epic 1: Core Backtesting Pipeline**
* **Goal:** Build a functional, end-to-end pipeline runnable from the command line. This involves setting up the reproducible Python environment, creating the logic to load and validate a strategy from YAML, implementing data acquisition with caching, and executing a backtest using `vectorbt`. The epic is complete when the pipeline can output basic performance results to the terminal.

**Epic 2: Analysis, Reporting & UX**
* **Goal:** Enhance the core pipeline with an analysis and presentation layer. This includes implementing the automated "Vibe Checks" (e.g., for fees, turnover, and trade count). The key deliverable is the formatted "Executive Verdict" table using the `rich` library. This epic is complete when the `pyfolio` report generation is functional via the `--report` flag and user-friendly error handling is in place.

---

## 7. Explicitly Out of Scope for MVP

To ensure a focused and rapid development cycle, the following are **not** part of the MVP.

* **Automated Intelligence:**
    * **No Automated Feature Engineering:** The system will not automatically generate or select trading features (`tsfresh`, `scikit-learn`). Strategies must use a small, pre-defined set of indicators (e.g., SMA, EMA, RSI).
    * **No Automated Strategy Suggestions:** The tool will not diagnose strategy weaknesses or automatically generate a modified `.yaml` file. It only reports the metrics.
    * **No A/B Testing:** The tool will not perform comparative tests between different strategies.

* **Advanced Backtesting Features:**
    * **No Walk-Forward Optimization:** All backtests are simple in-sample runs.
    * **No Advanced `vectorbt` Features:** Use of custom event handlers, parameter optimization grids (`run_combs`), or other advanced `vectorbt` functionalities is not included.
    * **No Complex Fee Models:** The tool will only support a simple, fixed percentage fee model.

* **Scope of Analysis:**
    * **No Batch Testing:** The tool will process one strategy at a time. It will not support running a directory of strategies to produce a leaderboard.
    * **Single-Instrument Only:** The tool will only analyze a single ticker at a time. Multi-asset backtesting is not supported.

* **User Interface:**
    * **No Interactive Prompts:** The tool is non-interactive. All control is through the YAML file and command-line flags.
    * **No Interactive Plots:** The tool will not serve or display interactive plots in a browser.

* **Data Sources:**
    * **`yfinance` Only:** The only supported data source is `yfinance`. Support for other data providers or local CSV files is not included.