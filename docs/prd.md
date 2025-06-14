### **Product Requirements Document (PRD)**
**Project Name:** KISS Signal CLI v1.4
**Last Updated:** 2025-06-14

---

#### 1. Introduction / Problem Statement
[cite_start]Retail technical traders require a personalized, automated tool to identify high-performance trading strategies[cite: 1]. [cite_start]They need daily, actionable BUY/SELL signals that are quick to produce, transparent in their logic, and lightweight enough to run from a command-line interface[cite: 1].

[cite_start]Current market solutions are polarized between time-consuming manual analysis and resource-intensive, opaque "AI" platforms[cite: 1]. [cite_start]This creates a critical gap for the sophisticated personal trader who values transparency, control, and efficiency[cite: 1]. [cite_start]They need a tool that can automatically discover and validate what works, discard what doesn't, and present the results clearly, emulating a disciplined analyst while being tailored to their specific performance goals[cite: 1].

---

#### 2. Vision, Goals, & Success Metrics
* [cite_start]**Vision:** "One command, actionable signals." [cite: 1]
* **MVP Goals:**
    1.  [cite_start]The `quickedge run` command will perform all necessary actions—data refresh, strategy analysis, and signal generation—and produce a daily markdown report[cite: 1].
    2.  [cite_start]The strategy engine will automatically test predefined rule layers on top of a baseline to discover and select the optimal strategy for each stock based on backtested performance[cite: 1].
    3.  [cite_start]All trade signals are persisted in a local SQLite database, ensuring a full and transparent history of every recommendation[cite: 1].
* **Success Metrics for v1.4:**
    1.  [cite_start]**Performance Target:** The backtesting engine must identify strategies that historically yield a `2%` or greater return within a `3-30` day holding period[cite: 1].
    2.  [cite_start]**Alpha Generation:** For a trade to be considered successful, its backtested return must be greater than the return of the NIFTY 50 index over the identical holding period[cite: 1].
    3.  [cite_start]**Personal Utility:** The tool is to be used as a personal trader, successfully replacing a prior manual workflow[cite: 1].
    4.  [cite_start]**Edge Score Definition:** The `EdgeScore`, a key performance metric for selecting a strategy, is explicitly defined as: `EdgeScore = (win_pct * 0.6) + (sharpe * 0.4)`[cite: 1]. [cite_start]The weights will be configurable in `config.yaml`[cite: 1].

---

#### 3. Target User & Pain Points
* [cite_start]**Persona:** A self-sufficient retail trader in Indian equities who is comfortable with command-line tools and wants to automate the discovery and execution of personalized, high-performance trading strategies[cite: 1].
* **Key Pain Points:**
    * [cite_start]**Strategy Discovery:** The manual process of finding indicators and patterns that consistently work is time-consuming and prone to biases[cite: 1].
    * [cite_start]**Lack of Automation:** A need for a tool that can automatically vet strategies against performance criteria without manual intervention[cite: 1].
    * [cite_start]**Performance Benchmarking:** Difficulty in consistently measuring if a strategy is genuinely outperforming the market (e.g., NIFTY) on a trade-by-trade basis[cite: 1].
    * [cite_start]**Silent Failures:** Not knowing if a lack of signals is due to market conditions or overly restrictive, poorly configured rules[cite: 1].

---

#### 4. User Interaction and Design Goals
[cite_start]As a CLI-first tool, the user experience centers on providing clear progress feedback and a highly informative, actionable output report[cite: 1].

* **CLI Interaction:**
    * [cite_start]The `quickedge run` command will display the current activity to the user, showing progress through the main stages of execution[cite: 1].
        ```
        KISS Signal CLI v1.4
        ---------------------
        [1/4] Refreshing price data... Done.
        [2/4] Analyzing strategies for 60 tickers... In Progress...
        [3/4] Generating signals from latest data...
        [4/4] Writing report...

        Signal generation complete.
        Report written to: signals_2025-06-14.md
        ```
    * [cite_start]In case of any errors, clear and specific messages will be displayed to the user[cite: 1].

* **Markdown Report (`signals_<date>.md`):**
    * [cite_start]The daily report will be a clean, well-formatted markdown table with the specific columns requested[cite: 1].

        **Signal Report: 2025-06-14**

        **NEW BUYS**
        | Ticker | Recommended Buy Date | Entry Price | Rule Stack | Edge Score |
        | :--- | :--- | :--- | :--- | :--- |
        | TATAMOTORS | 2025-06-14 | 950.25 | baseline,rsi14_confirm | 0.62 |
        | INFY | 2025-06-14 | 1500.00 | baseline,bull_regime | 0.55 |

        **OPEN POSITIONS**
        | Ticker | Entry Date | Entry Price | Current Price | Return % | NIFTY Period Return % | Day in Trade |
        | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
        | RELIANCE | 2025-06-09 | 2900.50 | 2958.50 | +2.00% | +0.50% | 5 / 20 |
        | HDFCBANK | 2025-05-29 | 1650.75 | 1620.00 | -1.86% | -2.50% | 12 / 20 |

        **POSITIONS TO SELL (Rule Change / Exit Condition Met)**
        | Ticker | Status | Reason |
        | :--- | :--- | :--- |
        | WIPRO | SELL | Exit: End of 20-day holding period. |

**Recommendation:**
* [cite_start]**Add Summary to Report:** To improve clarity, the first line of the markdown report should be a high-level summary, e.g., `Summary: 2 New Buy Signals, 2 Open Positions, 1 Position to Sell.` [cite: 1]

---

#### 5. Technical Assumptions
* [cite_start]**Architecture:** The system is a self-contained, monolithic CLI application[cite: 1]. [cite_start]It has no external service dependencies beyond the data source[cite: 1].
* [cite_start]**Language & Runtime:** Python 3.11+ [cite: 1]
* [cite_start]**Core Libraries:** `vectorbt` for backtesting and indicators, `yfinance` for EOD data[cite: 1].
* [cite_start]**Data Store:** A single-file SQLite database for all persistence[cite: 1].
* [cite_start]**Interfaces:** No GUI or cloud services[cite: 1]. [cite_start]Interaction is purely via the command line and configuration files[cite: 1].
* [cite_start]**Data Quality:** Price data adjustments for corporate actions (splits, dividends) are handled by a pre-existing, external user library and are not within the scope of this project[cite: 1].
* [cite_start]**Code Structure:** The codebase will be organized into distinct, modular Python files (e.g., `data_manager.py`, `backtester.py`, `rules.py`, `reporter.py`) to ensure clarity and maintainability, even within the strict LoC limit[cite: 1].

---

#### 6. Functional Requirements (Epics & Stories)

**Recommendation on Story Granularity:**
* While user stories are present, they lack specific, granular Acceptance Criteria (ACs). The document has a high-level "Acceptance Criteria" section (13), but individual stories should have their own distinct ACs to be truly "done." This level of detail is typically fleshed out by a Product Owner (PO) or Scrum Master (SM) before development begins on a story, but it is a key consideration for the next phase of planning.

##### Epic 1 – Data Layer
[cite_start]*Goal: To ensure the application has a reliable and up-to-date source of market data, managed via a single command.* [cite: 1]
* [cite_start]**Story 1.1:** As a system, I want `quickedge run` to automatically trigger an intelligent refresh of the local price data cache, ensuring efficiency and up-to-date analysis within a single command[cite: 1].
* [cite_start]**Story 1.2:** As a system, I want to handle failures from the data source gracefully, alerting the user that data could not be refreshed and aborting the run cleanly[cite: 1].

##### Epic 2 – Strategy Construction
[cite_start]*Goal: To automatically discover, backtest, and validate effective rule-based strategies for each stock against specific performance benchmarks.* [cite: 1]
* [cite_start]**Story 2.1 (Revised):** As a system, I want to automatically test pre-defined rule `layers` from `rules.yaml` by iteratively adding one layer at a time to the `baseline` rule, finding the optimal combination for each stock[cite: 1].
* [cite_start]**Story 2.2:** As a system, I want to use walk-forward validation to ensure strategies are robust over a 2-3 year historical period[cite: 1]. *(Refer to Appendix A for methodology options)._
* [cite_start]**Story 2.3:** As a system, during backtesting, I want to validate that a strategy achieves at least a 2% return within a 3-30 day window to be considered successful[cite: 1].
* [cite_start]**Story 2.4:** As a system, I want to calculate the return of the NIFTY 50 index over the identical holding period for each trade to ensure the algorithm generates true alpha[cite: 1].
* [cite_start]**Story 2.5 (New):** As a user, I want to be warned in the verbose log when a tested strategy results in a very low number of trades during backtesting, so I can identify if my rules are too restrictive[cite: 1].

##### Epic 3 – Rule-Engine Module
[cite_start]*Goal: To allow for the definition of trading rules using a simple, transparent, and text-based configuration.* [cite: 1]
* [cite_start]**Story 3.1 (Revised):** As a user, I want to author trading strategies in a simple, declarative `rules.yaml` file so that I can easily create and manage my strategies without writing complex code[cite: 1].
* [cite_start]**Story 3.2:** As a user, I want the application to validate `rules.yaml` on startup and provide clear, human-readable error messages if the syntax is incorrect[cite: 1].

##### Epic 4 – Signal Generation & Lifecycle Tracking
[cite_start]*Goal: To evaluate the best strategies against the latest market data to produce daily signals and track their lifecycle in a clear report.* [cite: 1]
* [cite_start]**Story 4.1:** As a user, I want `quickedge run` to evaluate the optimal rule stacks against the latest closing prices to generate signals[cite: 1].
* [cite_start]**Story 4.2:** As a system, I want to generate a daily markdown report with sections for `NEW_BUY`, `OPEN`, and `SELL` signals, containing all specified data columns for clear, actionable insights[cite: 1].
* [cite_start]**Story 4.3:** As a system, I want to persist every signal in the `trades` table to maintain a full audit trail[cite: 1].

##### Epic 5 – CLI & Configuration
[cite_start]*Goal: To provide the user with simple commands and a clear configuration file to control the application.* [cite: 1]
* [cite_start]**Story 5.1:** As a user, I want a single primary command, `quickedge run`, for all operational activities[cite: 1].
* [cite_start]**Story 5.2:** As a user, I want to control key parameters by editing a simple `config.yaml` file[cite: 1].
* [cite_start]**Story 5.3:** As a user, I want to be able to use a `--verbose` flag to generate a detailed debug log for troubleshooting and validation[cite: 1].

---

#### 7. Non-Functional Requirements
* [cite_start]**NFR-1 (Performance):** A full run for 60 stocks must complete in under 30 seconds[cite: 1].
* [cite_start]**NFR-2 (Determinism):** Given an identical database and config, the output must be 100% reproducible[cite: 1].
* [cite_start]**NFR-3 (Simplicity):** The entire Python codebase must not exceed 1,000 lines of code (excluding dependencies)[cite: 1].
* [cite_start]**NFR-4 (Scope):** There will be no web UIs, dashboards, or external database dependencies[cite: 1].

---

#### 8. SQLite Schema
```sql
CREATE TABLE price ( ticker TEXT, date DATE, open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (ticker, date) );
CREATE TABLE rule_stack ( ticker TEXT PRIMARY KEY, layers TEXT, win_pct REAL, sharpe REAL, edge_score REAL, updated_at DATE );
CREATE TABLE trades ( id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date DATE, ticker TEXT, entry_price REAL, rule_stack TEXT, win_pct REAL, sharpe REAL, edge_score REAL, prob_20d_up REAL, status TEXT, day_in_trade INTEGER, close_price REAL, exit_date DATE );
```

**Recommendation:**
* [cite_start]**Data Normalization:** To improve data integrity, the `trades` table should not store `win_pct`, `sharpe`, etc[cite: 1]. [cite_start]These are properties of the strategy[cite: 1]. [cite_start]Instead, the report generator should `JOIN` the `trades` and `rule_stack` tables to fetch this information on the fly[cite: 1]. [cite_start]This is a best practice, though optional for a personal tool[cite: 1].

---

#### 9. Rule-Engine and Configuration

##### 9.1 Core Concepts
[cite_start]The strategy is defined across two files: `config.yaml` for general parameters and `rules.yaml` for the logic[cite: 1]. [cite_start]This approach separates the logic (Python code), the rule composition (YAML), and high-level parameters (config)[cite: 1].

* [cite_start]**Rules as Functions:** A rule is a call to a pre-coded Python function (e.g., an indicator or a pattern)[cite: 1]. [cite_start]`rules.yaml` specifies which functions to call with which parameters[cite: 1].
* [cite_start]**Structure:** `rules.yaml` has sections for `principles` (master filters), `baseline` (mandatory entry/exit criteria), and `layers` (optional conditions)[cite: 1].
* [cite_start]**Thresholds:** `config.yaml` will hold key operational parameters, including the `min_trades_threshold` to warn against overly stringent rules[cite: 1].

##### 9.2 `rules.yaml` File Structure & Syntax
[cite_start]The syntax is `function_name: [param1, param2, ...]`[cite: 1]. [cite_start]The Python backend will parse this and call the corresponding function[cite: 1].
```yaml
# rules.yaml

# General principles that act as a master filter.
principles:
  - "is_liquid: [20, 50000000]"
  - "is_not_penny_stock: [20]"

# The baseline strategy.
baseline:
  BUY:
    - "cross_over: ['close', 'sma(close, 20)']"
  SELL:
    - "fixed_exit: ['days_in_trade', 20]"

# Optional layers to test.
layers:
  rsi_confirm:
    BUY:
      - "rsi: ['close', 14, '>', 55]"
  bull_regime:
    FILTER:
      - "is_bull_market: ['index_close', 50]"
  volume_spike:
    FILTER:
      - "volume_above_avg: ['volume', 20, 1.5]"
  early_exit_on_rsi_weakness:
    SELL:
      - "rsi: ['close', 14, '<', 40]"
```

##### 9.3 `config.yaml` File Example
[cite_start]This file controls the high-level behavior of the application[cite: 1].
```yaml
# config.yaml

# Path to the list of tickers to analyze.
universe_path: "data/nifty60.csv"

# Default holding period if not specified in rules.
hold_period: 20

# NEW: Warn if a backtested strategy yields fewer trades than this over the entire historical period.
min_trades_threshold: 10

# Weights for calculating the EdgeScore.
edge_score_weights:
  win_pct: 0.6
  sharpe: 0.4
```

##### 9.4 Evaluation Logic
1.  [cite_start]**Parsing:** `config.yaml` and `rules.yaml` are parsed[cite: 1]. [cite_start]Errors in syntax or calls to non-existent Python functions are reported[cite: 1].
2.  [cite_start]**Principle Filtering:** If the `principles` block exists, it is evaluated first for each stock[cite: 1]. [cite_start]If any principle fails, that stock is skipped[cite: 1].
3.  **Iterative Backtesting:** For each stock that passes:
    a. [cite_start]The `baseline` strategy is backtested[cite: 1]. [cite_start]Its performance metrics, including total number of trades, are calculated[cite: 1].
    b. [cite_start]The engine then iterates through each `layer` defined in `rules.yaml`, creates a new temporary strategy (`baseline` + `layer`), and runs a full backtest[cite: 1].
    c. [cite_start]**Feedback Check:** After each backtest, the system checks if the total number of trades is below the `min_trades_threshold` from `config.yaml`[cite: 1]. [cite_start]If it is, a warning is recorded for the verbose log[cite: 1].
    d. [cite_start]The `EdgeScore` for each tested combination is recorded[cite: 1].
4.  [cite_start]**Optimal Strategy Selection:** The combination that produced the highest `EdgeScore` (and meets other criteria) is saved in the `rule_stack` table[cite: 1].

---

#### 10. Monitoring, Observability & Maintenance
[cite_start]To ensure transparency and aid in debugging, the application will support detailed logging[cite: 1].
* [cite_start]**Verbose Logging:** A `--verbose` flag on the `quickedge run` command will generate a `run_log_<date>.txt` file[cite: 1].
* **Log Content:** This log will detail the step-by-step execution for each ticker, including:
    * [cite_start]Which principles were checked and if they passed[cite: 1].
    * [cite_start]The backtest performance (`EdgeScore`, `win_pct`, `sharpe`, total trades) for the `baseline` strategy[cite: 1].
    * [cite_start]The backtest performance for each `baseline` + `layer` combination that was tested[cite: 1].
    * **A `WARNING` message if a tested strategy combination generates fewer trades than the `min_trades_threshold`. [cite_start]E.g., `WARNING: Strategy 'baseline,rsi_confirm' on 'RELIANCE' generated only 4 trades, which is below the threshold of 10.`** [cite: 1]
    * [cite_start]A final statement indicating which rule stack was chosen as optimal for the ticker[cite: 1].

---

#### 11. Roadmap – Post-MVP Features
* [cite_start]**AI Strategy Improver:** An engine that analyzes why an algorithm did not work and suggests how to improve it by modifying rules[cite: 1].
* [cite_start]**Dynamic Exit Conditions:** Implement sell triggers based on changing market dynamics (e.g., trend reversal, volatility spike) rather than a fixed time-based stop[cite: 1].
* [cite_start]Equal-risk ATR position sizing [cite: 1]
* [cite_start]Short-side rule stacks [cite: 1]
* [cite_start]Sector rotation overlay [cite: 1]
* [cite_start]Adaptive exit optimisation [cite: 1]
* [cite_start]Opt-in e-mail / Telegram alerts [cite: 1]

---

#### 12. What *Not* To Do (Scope Boundaries)
* [cite_start]No intraday, options, or futures trading[cite: 1].
* [cite_start]No deep-learning or "black box" models[cite: 1].
* [cite_start]No external database engines[cite: 1].
* [cite_start]No GUI[cite: 1].
* [cite_start]No complex, implicit "auto-magic" strategy discovery beyond the explicit rules defined in `rules.yaml`[cite: 1]. [cite_start]The system's logic must remain transparent[cite: 1].
* [cite_start]No public-facing security hardening[cite: 1]. [cite_start]This tool is for personal, local use only[cite: 1].
* [cite_start]No packaging for public distribution (e.g., PyPI)[cite: 1]. [cite_start]Execution will be done by manually running the Python script[cite: 1].

---

#### 13. Acceptance Criteria
1.  [cite_start]After a fresh install, `quickedge run` completes successfully and produces a `signals_<date>.md` file[cite: 1].
2.  [cite_start]The format of the generated `.md` file matches the specification, including all required columns[cite: 1].
3.  [cite_start]Backtested strategies that are selected as `NEW_BUY` signals meet the minimum performance criteria[cite: 1].
4.  [cite_start]Re-running the tool correctly retains `OPEN` trades and updates their status[cite: 1].
5.  [cite_start]A trade held for the full period is correctly moved to the `SELL` category[cite: 1].
6.  [cite_start]The application exits with a clear error message if the `config.yaml` or `rules.yaml` file contains a syntax error[cite: 1].
7.  [cite_start]Running `quickedge run --verbose` generates a detailed `run_log_<date>.txt` file that includes warnings for strategies that fall below the `min_trades_threshold`[cite: 1].

---

#### 14. Change Log
| Version | Date | Author | Description |
| :--- | :--- | :--- | :--- |
| 1.4 | 2025-06-14 | BMAD | Added recommendation to Section 6 to emphasize the need for granular, story-level Acceptance Criteria. |
| 1.3 | 2025-06-14 | K. Nadh | Added feedback mechanism to warn users of overly stringent rules that result in too few trades, configured via `config.yaml`. |
| 1.2 | 2025-06-14 | K. Nadh | Revised PRD based on feedback. Replaced rule-engine with a simpler YAML-based spec. Added logging, backtesting appendix, and clarified scope. |
| 1.1 | 2025-06-14 | John, PM | Integrated user feedback on success metrics, validation, CLI/report format, and single-command execution. |
| 1.0 | 2025-06-14 | User | Initial draft and concept. |

---

### **Appendix A: Backtesting Methodology Options**

[cite_start]For the MVP, the **Simple In-Sample / Out-of-Sample Split** is recommended for its simplicity and alignment with the project's KISS philosophy[cite: 1].

1.  **Simple In-Sample / Out-of-Sample (IS/OOS) Split (Recommended for MVP):**
    * [cite_start]**Concept:** The historical data (e.g., 3 years) is split into two periods[cite: 1]. [cite_start]The first 80% (the "in-sample" period) is used to find the best-performing rule stack[cite: 1]. [cite_start]The remaining 20% (the "out-of-sample" period) is used to verify that the chosen strategy still performs well on data it has never seen[cite: 1].
    * [cite_start]**Pros:** Simple to implement, computationally fast, provides a basic check against overfitting[cite: 1].
    * [cite_start]**Cons:** The results can be sensitive to the specific period chosen for the split[cite: 1].

2.  **Rolling Walk-Forward Validation:**
    * [cite_start]**Concept:** This is a more robust method[cite: 1]. [cite_start]The data is divided into many overlapping windows[cite: 1]. [cite_start]For each window, you train on a period of data and test on the period immediately following it[cite: 1]. [cite_start](e.g., Train on Year 1, Test on Q1 of Year 2. Then, roll forward: Train on Q1/Y1-Q1/Y2, Test on Q2/Y2)[cite: 1].
    * [cite_start]**Pros:** More accurately simulates real-world trading where you would periodically update your strategy[cite: 1]. [cite_start]Less sensitive to any single time period[cite: 1].
    * [cite_start]**Cons:** Far more computationally intensive, more complex to implement correctly[cite: 1].

3.  **Anchored (or Expanding) Walk-Forward Validation:**
    * [cite_start]**Concept:** Similar to rolling, but the training period always starts from the beginning of the dataset and expands[cite: 1]. [cite_start](e.g., Train on Y1, Test Q1/Y2. Then Train on Y1+Q1/Y2, Test Q2/Y2)[cite: 1].
    * [cite_start]**Pros:** Uses all available data for training each step[cite: 1].
    * [cite_start]**Cons:** Gives more weight to older data over time, may be slow to adapt to changing market regimes[cite: 1]. [cite_start]Computationally heavy[cite: 1].