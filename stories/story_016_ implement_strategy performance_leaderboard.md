# Story 16: Implement Strategy Performance Leaderboard

## Status: Ready for Development

**Priority:** High (Provides critical system-level feedback)
**Estimated Story Points:** 5
**Prerequisites:** Story 015 (Dynamic Exit Conditions) ✅ Complete
**Created:** 2025-07-23

## User Story
As a trader, I want to generate a single Markdown report that analyzes and ranks the historical performance of **every strategy combination** I've ever tested, so I can quickly identify which strategies have a real, persistent edge and which ones are underperforming or too restrictive.

## Context & Rationale
The system is excellent at finding the *optimal* strategy for a given stock on a given day. However, it lacks a "memory" or a high-level "boardroom view" of which strategy *archetypes* are consistently effective over time and across the entire stock universe. This report provides that memory.

By analyzing the entire `strategies` table in the database, we can answer critical questions:
*   Which rule combinations appear most frequently as "optimal"?
*   Which strategies have the best average performance, not just in a single run?
*   Are some of my defined strategies too restrictive and never get selected?

This story directly addresses the user need to "determine if the strategies are well defined, too restrictive and how to improve it" by providing a data-driven leaderboard. It follows the KISS principle by **analyzing existing data** rather than performing new, slow, complex calculations.

## Acceptance Criteria

### AC-1: New CLI Command
- [ ] A new command `analyze-strategies` is added to the CLI.
- [ ] The command accepts an optional `--output <filename>.md` argument, defaulting to `strategy_performance_report.md`.
- [ ] The command operates on the existing database specified in `config.yaml`.

### AC-2: Strategy Performance Aggregation
- [ ] A new function `analyze_strategy_performance(db_path)` is implemented in `reporter.py`.
- [ ] It queries the **entire `strategies` table** to fetch all historical optimal strategy records.
- [ ] It groups records by the unique `rule_stack` combination (e.g., "bullish_engulfing_reversal + filter_with_rsi_oversold").
- [ ] For each unique strategy, it calculates the following **aggregated metrics**:
    - **Frequency:** The total count of times this strategy was chosen as optimal for any stock.
    - **Avg. Edge Score:** The average edge score across all times it was chosen.
    - **Avg. Win %:** The average win percentage.
    - **Avg. Sharpe:** The average Sharpe ratio.
    - **Avg. Trades:** The average number of trades generated during its backtests.
    - **Top Symbols:** A comma-separated string of the top 3 symbols where this strategy was most frequently optimal.

### AC-3: Clear Markdown Report
- [ ] The command generates a clean, readable Markdown file with the analysis results.
- [ ] The report contains a Markdown table sorted by **Avg. Edge Score** in descending order.
- [ ] The table columns are: `Strategy (Rule Stack)`, `Frequency`, `Avg Edge Score`, `Avg Win %`, `Avg Sharpe`, `Avg Trades`, `Top Symbols`.

### AC-4: Code Quality and Compliance
- [ ] The implementation adds **no new external dependencies** (H-10).
- [ ] The new logic is housed entirely within `cli.py` and `reporter.py`.
- [ ] All new functions are fully type-hinted and pass `mypy --strict` (H-7).
- [ ] The new command and its logic are covered by unit and integration tests.
- [ ] The implementation avoids re-backtesting and works exclusively with data already in the `strategies` table.

## Technical Design (KISS Approach)

We will not add complexity. We will read the database, group the data, calculate averages, and print a table. That's it.

### 1. CLI Command (`src/kiss_signal/cli.py`)
A new command will be added to orchestrate the analysis. It's a simple wrapper around the core logic in the reporter.

```python
# In src/kiss_signal/cli.py

@app.command(name="analyze-strategies")
def analyze_strategies(
    ctx: typer.Context,
    output_file: Path = typer.Option(
        "strategy_performance_report.md",
        "--output", "-o",
        help="Path to save the strategy performance report.",
    ),
) -> None:
    """Analyze and report on the historical performance of all strategy combinations."""
    console.print("[bold blue]Analyzing historical strategy performance...[/bold blue]")
    app_config = ctx.obj["config"]
    db_path = Path(app_config.database_path)

    # ... (Error handling for DB not found) ...

    try:
        # Core logic call
        strategy_performance = reporter.analyze_strategy_performance(db_path)
        if not strategy_performance:
            console.print("[yellow]No historical strategies found to analyze.[/yellow]")
            return

        # Formatting call
        report_content = reporter.format_strategy_analysis_as_md(strategy_performance)
        output_file.write_text(report_content, encoding="utf-8")
        console.print(f"✅ Strategy performance report saved to: [cyan]{output_file}[/cyan]")

    except Exception as e:
        # ... (Standard exception handling) ...
```

### 2. Analysis Logic (`src/kiss_signal/reporter.py`)
This is where the work happens. We will add two new functions.

```python
# In src/kiss_signal/reporter.py
from collections import Counter, defaultdict

# impure
def analyze_strategy_performance(db_path: Path) -> List[Dict[str, Any]]:
    """Analyzes the entire history of strategies to rank strategy combinations."""
    # Use a defaultdict to easily aggregate data for each unique strategy.
    # The key will be the string representation of the rule stack.
    stats = defaultdict(lambda: {'metrics': [], 'symbols': []})

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        # Select all the data we need from every strategy ever saved.
        cursor = conn.execute("SELECT symbol, rule_stack, edge_score, win_pct, sharpe, total_trades FROM strategies")
        strategies = cursor.fetchall()

    for strategy in strategies:
        try:
            rules_in_stack = json.loads(strategy['rule_stack'])
            # Create a consistent, readable key for the strategy combination.
            # e.g., "baseline_rule + rsi_filter + volume_filter"
            strategy_key = " + ".join(r.get('name', 'N/A') for r in rules_in_stack)
            if not strategy_key:
                continue

            # Append the metrics and symbol for later aggregation.
            stats[strategy_key]['metrics'].append(dict(strategy))
            stats[strategy_key]['symbols'].append(strategy['symbol'])
        except (json.JSONDecodeError, TypeError):
            continue # Silently skip malformed data in the DB.

    # Now, process the aggregated data to calculate averages.
    analysis = []
    for key, data in stats.items():
        freq = len(data['metrics'])
        analysis.append({
            'strategy_name': key,
            'frequency': freq,
            'avg_edge_score': sum(m['edge_score'] for m in data['metrics']) / freq,
            'avg_win_pct': sum(m['win_pct'] for m in data['metrics']) / freq,
            'avg_sharpe': sum(m['sharpe'] for m in data['metrics']) / freq,
            'avg_trades': sum(m['total_trades'] for m in data['metrics']) / freq,
            'top_symbols': ", ".join(s for s, _ in Counter(data['symbols']).most_common(3)),
        })

    # Sort by the primary performance metric.
    return sorted(analysis, key=lambda x: x['avg_edge_score'], reverse=True)

# pure
def format_strategy_analysis_as_md(analysis: List[Dict[str, Any]]) -> str:
    """Formats the strategy performance analysis into a markdown table."""
    header = "| Strategy (Rule Stack) | Freq. | Avg Edge | Avg Win % | Avg Sharpe | Avg Trades | Top Symbols |\n"
    separator = "|:---|---:|---:|---:|---:|---:|:---|\n"
    
    rows = []
    for stats in analysis:
        row = (
            f"| `{stats['strategy_name']}` "
            f"| {stats['frequency']} "
            f"| {stats['avg_edge_score']:.2f} "
            f"| {stats['avg_win_pct']:.1%} "
            f"| {stats['avg_sharpe']:.2f} "
            f"| {stats['avg_trades']:.1f} "
            f"| {stats['top_symbols']} |"
        )
        rows.append(row)
    
    return f"# Strategy Performance Report\n\n{header}{separator}" + "\n".join(rows)

```

### 3. Sample Markdown Output (`strategy_performance_report.md`)

```markdown
# Strategy Performance Report

| Strategy (Rule Stack) | Freq. | Avg Edge | Avg Win % | Avg Sharpe | Avg Trades | Top Symbols |
|:---|---:|---:|---:|---:|---:|:---|
| `bullish_engulfing_reversal + filter_with_rsi_oversold` | 15 | 0.72 | 68.5% | 1.35 | 12.3 | RELIANCE, INFY, HDFCBANK |
| `sma_10_20_crossover + confirm_with_macd_momentum` | 28 | 0.65 | 61.2% | 1.10 | 25.1 | TCS, WIPRO, SBIN |
| `bollinger_breakout` | 5 | 0.51 | 55.0% | 0.85 | 8.5 | TATAMOTORS, LT, AXISBANK |
```

## Architectural Considerations
*   **Performance:** The analysis queries the entire `strategies` table. For a very large database (millions of rows), this could become slow. This is acceptable for now. If it becomes a bottleneck, we can consider creating a separate, aggregated summary table, but we will not do this now (YAGNI).
*   **Data Integrity:** The analysis is read-only, so it poses no risk to the database. It is designed to be resilient to malformed JSON in the `rule_stack` column by simply skipping those rows.
*   **Simplicity:** The logic is self-contained within the `reporter` module, reinforcing its role as the source for all analytical outputs. It introduces no new modules or complex inter-dependencies.

## Out of Scope
*   **Per-Stock Breakdown:** This report aggregates across all stocks. A detailed, per-stock performance view for each strategy is a separate feature (Story 17).
*   **Calculating New Metrics:** This report will **only** use data already present in the `strategies` table (`edge_score`, `win_pct`, `sharpe`). It will not calculate new, complex metrics like `Max Drawdown` or `Profit Factor`, as that would require re-running backtests, which is slow and violates the KISS principle for this feature.
*   **Automated Suggestions:** The report provides data for a human to analyze. It will not generate automated "AI" improvement suggestions.

## Definition of Done
- [ ] All acceptance criteria are met and tested.
- [ ] The `analyze-strategies` command is functional and generates a correct Markdown file.
- [ ] The analysis logic correctly queries, groups, and aggregates performance data from the database.
- [ ] The generated report is sorted and formatted as specified.
- [ ] The feature is covered by unit tests (for the aggregation logic) and an integration test (for the CLI command).
- [ ] All code passes `mypy --strict` and adheres to all project hard rules.

## Detailed Task List

- **Task 1: Add `analyze-strategies` command to `cli.py`**
  - [ ] Add the new Typer command stub.
  - [ ] Implement the orchestration logic: call the reporter, handle results, write the file.
  - [ ] Add robust error handling.

- **Task 2: Implement `analyze_strategy_performance` in `reporter.py`**
  - [ ] Write the SQL query to fetch all required data from the `strategies` table.
  - [ ] Implement the loop to parse `rule_stack` JSON and aggregate metrics into a `defaultdict`.
  - [ ] Implement the final processing loop to calculate averages and identify top symbols.
  - [ ] Ensure the final list is sorted by `avg_edge_score`.

- **Task 3: Implement `format_strategy_analysis_as_md` in `reporter.py`**
  - [ ] Create the function to generate the Markdown table from the analysis data.
  - [ ] Ensure correct formatting for numbers, percentages, and text alignment.

- **Task 4: Add Comprehensive Tests**
  - [ ] In `tests/test_reporter_advanced.py`, add tests for `analyze_strategy_performance` using a pre-populated in-memory DB with various strategy combinations.
  - [ ] Add a test for `format_strategy_analysis_as_md` to check for correct output against a golden string.
  - [ ] In `tests/test_cli_advanced.py`, add an integration test for the `analyze-strategies` command, mocking the reporter functions.

- **Task 5: Update `DEVELOPMENT_ROADMAP.md`**
  - [ ] Mark Story 16 as complete.
  - [ ] Update the "Current Story" to the next in the pipeline.

  ## Next Set of Stories Planned

### Story 17: Implement Detailed Strategy Drill-Down Report
*   **Priority:** High
*   **Points:** 6
*   **Goal:** To allow a user to drill down into a single strategy's performance from the leaderboard. This report will show detailed per-stock metrics, a trade log, and an equity curve to explain *why* a strategy is performing well or poorly.
*   **Rationale:** The leaderboard (Story 16) identifies *what* works. This story explains *how* and *where* it works. It's the logical next step in analysis, providing the deeper insights needed to refine or trust a strategy. It directly addresses the "last successful exit" and "stats of successful strategies per stock" user requests.

### Story 18: Enhance Reports with ASCII Sparkline Visualizations
*   **Priority:** Medium
*   **Points:** 2
*   **Goal:** To add simple, dependency-free ASCII sparklines (e.g., `  ▂▄▆█▇`) to the report tables to provide an instant visual summary of performance trends over time.
*   **Rationale:** This is a classic KISS/Kailash Nadh feature: a tiny amount of code that dramatically improves the report's "glance value" and helps spot edge decay without needing complex charting libraries.

### Story 19: Implement Volatility-Adjusted Position Sizing (ATR)
*   **Priority:** High
*   **Points:** 8
*   **Goal:** To introduce professional risk management by sizing positions based on the stock's Average True Range (ATR). This normalizes risk across all trades, so the portfolio is not overly exposed to a single, volatile stock.
*   **Rationale:** This is a foundational step in moving from a pure signal generator to a robust trading *system*. Equal risk per trade is a cornerstone of professional portfolio management.