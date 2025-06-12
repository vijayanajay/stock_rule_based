Excellent. I'm glad that plan works for you. By focusing on a robust V1 and clearly defining our V2 goals, we're setting the project up for both immediate success and future growth.

I have now updated the Product Requirements Document to reflect our discussion. This version incorporates the more sophisticated market regime analysis, the flexible process timing, and the enhanced reporting, while officially moving the stateful learning and predictive analytics to the Post-MVP roadmap.

Here is the finalized PRD for the **Automated Technical Analyst Assistant v1.0**.

***

# Product Requirements Document (PRD) - Automated Technical Analyst Assistant v1.0

## 1. Introduction / Problem Statement

Retail traders and investors often rely on discretionary technical analysis or overly complex "black box" AI solutions. This creates a gap in the market for a tool that is both systematic and transparent. Traders need a reliable way to discover, validate, and apply rule-based trading strategies at scale, but they lack the tools to do so efficiently without significant manual effort or trusting opaque algorithms. The core problem is the inability to systematically learn from historical market data in a transparent, repeatable, and automated fashion.

## 2. Vision & Goals

* **Vision:** To empower a retail trader with an automated technical analyst that provides transparent, data-driven, and continuously improving trading signals, enabling access to systematic trading.
* **Primary Goals (MVP):**
    1.  **Develop a Core Strategy Engine:** Build a system capable of backtesting predefined trading strategies against a universe of 150+ Indian stocks to identify the top-performing strategy for each stock on a weekly basis, contextualized by the current market regime.
    2.  **Deliver Actionable Daily Signals:** Ensure the system can generate and deliver daily "Buy," "Sell," and "Hold" signals with over 99% uptime and reliability.
    3.  **Validate System Efficacy:** Achieve a positive backtested cumulative return for the system's aggregate signals over a 2-year historical data period to prove the model's fundamental viability.

## 3. Target Audience / Users

The primary user is a single, tech-savvy retail trader in the Indian stock market. They are knowledgeable about technical analysis concepts but want to move beyond discretionary chart-reading. They are systematic in their thinking, appreciate data-driven decisions, and value transparency and understanding the logic behind the signals they receive.

## 4. Technical Assumptions

* [cite_start]**Service Architecture:** The system will be built as a **monolithic application with a modular design**. [cite: 1450] [cite_start]Key modules will include, but are not limited to: `Data Ingestion`, `Strategy Engine`, `Backtesting`, `Signal Generation`, and `Reporting`. [cite: 1452]
* **Data Source:** The system will exclusively use the `yfinance` library to source all historical end-of-day (EOD) stock data. This is a fixed requirement.
* [cite_start]**Security:** As the application is for personal use by a single user and does not handle live trading credentials, user accounts, or sensitive personal data, security requirements are considered minimal. [cite: 1481]

## 5. Epics and Functional Requirements (MVP Scope)

### **Epic 1: Foundational Backtesting Engine**
*Goal: To build the core engine that can ingest market data and evaluate a library of trading strategies against a universe of stocks to find the best performer for each stock, contextualized by the current market regime.*

* [cite_start]**FR-1.1 (Stock Universe):** The system must support a configurable universe of at least 150 large-cap and mid-cap stocks from the Indian market (e.g., Nifty 200). [cite: 423]
* [cite_start]**FR-1.2 (Strategy Definition):** The system must include a predefined library of transparent, human-readable trading strategies. [cite: 423] The canonical list of these strategies and candlestick patterns will be maintained in a separate `strategies.md` document.
* **FR-1.3 (Rule-Based Strategy Engine):** The system must implement a rule-based engine or grammar to define strategies. This approach must allow new strategies and candlestick patterns to be added via configuration (e.g., in `strategies.md`) **without requiring changes to the core engine's Python code.**
* **FR-1.4 (Market Regime Definition):** The system must be able to classify the market into one of three regimes: **Bullish, Neutral, or Bearish**. This will be determined by the Nifty 50 index's (`^NSEI`) position relative to its 50-day and 200-day simple moving averages (SMAs).
* [cite_start]**FR-1.5 (Automated Weekly "Bake-Off"):** The system must run an automated, scheduled "bake-off" process every weekend. [cite: 423]
* **FR-1.6 (Regime-Contextual Backtesting):** During the bake-off, the system must identify the current market regime. [cite_start]It will then backtest every strategy against every stock to find the strategy with the best historical performance **during past periods that match the current regime.** This uses the last 1-2 years of EOD data. [cite: 423]
* [cite_start]**FR-1.7 (Performance Metric):** For each strategy-stock-regime combination, the system must calculate the **Sharpe Ratio** as the definitive risk-adjusted return metric. [cite: 423]
* [cite_start]**FR-1.8 (Active Strategy Designation):** For each stock, the strategy with the highest Sharpe Ratio from the contextual backtest will be designated as the "Active Strategy" for the entire upcoming week. [cite: 423] [cite_start]This selection must be persisted. [cite: 423]

### **Epic 2: Daily Signal Generation & Delivery**
*Goal: To use the "Active Strategy" for each stock to generate daily trading signals and deliver them in a consolidated report.*

* **FR-2.1 (Automated Daily Process):** The system must run an automated process to generate signals. This process can be executed on-demand at any time.
* [cite_start]**FR-2.2 (Stateless Operation):** The system must be stateless. [cite: 423] [cite_start]It will not track open positions, portfolios, or historical trades for its logic. [cite: 423] [cite_start]Each day's signal generation is an independent event. [cite: 423]
* **FR-2.3 (Signal Logic):** For each stock in the universe, the system will retrieve the stock's "Active Strategy" for the week and run it on the latest market data to check for entry or exit conditions.
* [cite_start]**FR-2.4 (Daily Report Generation):** The system must generate a single, consolidated report for the day. [cite: 423]
* **FR-2.5 (Report Content):** The report must be clean and simple, containing three lists:
    * **Stocks to BUY Today:** Listing the stock ticker, the name of the triggering strategy, and key historical performance metrics for that combination (e.g., Backtested Sharpe Ratio and Cumulative Return).
    * **Stocks to SELL Today:** Listing the stock ticker and the name of the triggering strategy.
    * **Active HOLDS:** Listing all other stocks in the universe that are not generating a BUY or SELL signal today.
* [cite_start]**FR-2.6 (Delivery):** The report must be made available through a simple mechanism (e.g., a local file drop or a simple API endpoint). [cite: 423]

### **Epic 3: System Performance Validation & Monitoring**
*Goal: To create a mechanism to validate the historical performance of the system's combined signals.*

* [cite_start]**FR-3.1 (Validation Dashboard):** A system-level dashboard must be created to display the primary MVP success metric. [cite: 423]
* [cite_start]**FR-3.2 (Primary Metric Display):** The dashboard must show the cumulative backtested equity curve of the system's aggregate signals. [cite: 423] [cite_start]This is calculated by simulating a portfolio that takes every "BUY" and "SELL" signal generated by the system over a 2-year historical test period. [cite: 423]

## 6. Non-Functional Requirements (NFRs)

* [cite_start]**NFR-1 (Transparency):** The system must not use complex, opaque machine learning models. [cite: 423] [cite_start]All rules must be transparent and human-readable. [cite: 423]
* [cite_start]**NFR-2 (Reliability & Uptime):** The signal generation and delivery process must achieve >99% uptime and reliability. [cite: 423]
* **NFR-3 (Performance):**
    * [cite_start]The weekly "bake-off" must complete within the weekend window (e.g., under 48 hours). [cite: 423]
    * The daily signal generation process must be performant enough for on-demand execution.
* [cite_start]**NFR-4 (Data Granularity):** The system will be built and tested using end-of-day (EOD) historical data from `yfinance`. [cite: 423]
* [cite_start]**NFR-5 (Technology Stack):** The backend engine is required to be Python, leveraging data science and backtesting libraries (e.g., `pandas`, `numpy`, `vectorbt`). [cite: 423]

## 7. Post-MVP Features / Future Scope

1.  **Stateful Performance Tracking & Learning Engine:** Introduce a stateful mechanism to track the performance of historical signals and implement a feedback loop to learn from failed recommendations.
2.  **Predictive Analytics Module:** Develop and integrate a statistical model to provide forward-looking probabilities for signals (e.g., probability of a 1% price increase within 7 days).
3.  [cite_start]**Automated Rule Discovery Engine:** Evolve from strategy *selection* to strategy *discovery*, programmatically generating and testing novel `if-then-else` rules. [cite: 423]
4.  [cite_start]**Advanced Risk Management:** Introduce dynamic risk-management overlays like volatility-based position sizing or trailing stop-losses. [cite: 423]
5.  [cite_start]**Strategy Parameter Optimization:** Add an optimization layer to fine-tune parameters of proven strategies. [cite: 423]
6.  [cite_start]**Introduction of Short-Selling Strategies:** Develop and enable strategies for short-selling opportunities. [cite: 423]
7.  [cite_start]**Interactive Charting & Analysis Interface:** A web-based UI for users to view charts with signals and explore backtest reports. [cite: 423]

