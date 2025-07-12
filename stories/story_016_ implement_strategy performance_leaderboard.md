# Story 16: Implement Strategy Performance Leaderboard

## Status: ✅ COMPLETED

**Completed Date:** 2025-07-13

**Priority:** High (Provides critical system-level feedback)
**Estimated Story Points:** 5
**Prerequisites:** Story 015 (Dynamic Exit Conditions) ✅ Complete
**Created:** 2025-07-23

## User Story
As a trader, I want to generate a single CSV report that analyzes and ranks the historical performance of **every strategy combination** I've ever tested, so I can quickly identify which strategies have a real, persistent edge and which ones are underperforming or too restrictive.

## Context & Rationale
The system is excellent at finding the *optimal* strategy for a given stock on a given day. However, it lacks a "memory" or a high-level "boardroom view" of which strategy *archetypes* are consistently effective over time and across the entire stock universe. This report provides that memory.

By analyzing the entire `strategies` table in the database, we can answer critical questions:
*   Which rule combinations appear most frequently as "optimal"?
*   Which strategies have the best average performance, not just in a single run?
*   Are some of my defined strategies too restrictive and never get selected?

This story directly addresses the user need to "determine if the strategies are well defined, too restrictive and how to improve it" by providing a data-driven leaderboard. It follows the KISS principle by **analyzing existing data** rather than performing new, slow, complex calculations.

## Acceptance Criteria

### AC-1: New CLI Command
- [x] A new command `analyze-strategies` is added to the CLI.
- [x] The command accepts an optional `--output <filename>.csv` argument, defaulting to `strategy_performance_report.csv`.
- [x] The command operates on the existing database specified in `config.yaml`.

### AC-2: Strategy Performance Aggregation
- [x] A new function `analyze_strategy_performance(db_path)` is implemented in `reporter.py`.
- [x] It queries the **entire `strategies` table** to fetch all historical optimal strategy records.
- [x] It groups records by the unique `rule_stack` combination (e.g., "bullish_engulfing_reversal + filter_with_rsi_oversold").
- [x] For each unique strategy, it calculates the following **aggregated metrics**:
    - **Frequency:** The total count of times this strategy was chosen as optimal for any stock.
    - **Avg. Edge Score:** The average edge score across all times it was chosen.
    - **Avg. Win %:** The average win percentage.
    - **Avg. Sharpe:** The average Sharpe ratio.
    - **Avg. Trades:** The average number of trades generated during its backtests.
    - **Top Symbols:** A comma-separated string of the top 3 symbols where this strategy was most frequently optimal.

### AC-3: Clear CSV Report
- [x] The command generates a clean, readable CSV file with the analysis results.
- [x] The report contains a CSV table sorted by **Avg. Edge Score** in descending order.
- [x] The table columns are: `strategy_rule_stack`, `frequency`, `avg_edge_score`, `avg_win_pct`, `avg_sharpe`, `avg_return`, `avg_trades`, `top_symbols`.

### AC-4: Code Quality and Compliance
- [x] The implementation adds **no new external dependencies** (H-10).
- [x] The new logic is housed entirely within `cli.py` and `reporter.py`.
- [x] All new functions are fully type-hinted and pass `mypy --strict` (H-7).
- [x] The new command and its logic are covered by unit and integration tests.
- [x] The implementation avoids re-backtesting and works exclusively with data already in the `strategies` table.

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
        "strategy_performance_report.csv",
        "--output", "-o",
        help="Path to save the strategy performance report as a CSV file.",
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
        report_content = reporter.format_strategy_analysis_as_csv(strategy_performance)
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
def format_strategy_analysis_as_csv(analysis: List[Dict[str, Any]]) -> str:
    """Formats the strategy performance analysis into a CSV string."""
    if not analysis:
        return ""

    df = pd.DataFrame(analysis)
    df = df.rename(columns={
        'strategy_name': 'strategy_rule_stack',
        'frequency': 'frequency',
        'avg_edge_score': 'avg_edge_score',
        'avg_win_pct': 'avg_win_pct',
        'avg_sharpe': 'avg_sharpe',
        'avg_return': 'avg_return',
        'avg_trades': 'avg_trades',
        'top_symbols': 'top_symbols'
    })
    output = StringIO()
    df.to_csv(output, index=False, float_format='%.4f')
    return output.getvalue()
```

### 3. Sample CSV Output (`strategy_performance_report.csv`)

```csv
strategy_rule_stack,frequency,avg_edge_score,avg_win_pct,avg_sharpe,avg_return,avg_trades,top_symbols
bullish_engulfing_reversal + filter_with_rsi_oversold,15,0.72,0.685,1.35,0.095,12.3,"RELIANCE, INFY, HDFCBANK"
sma_10_20_crossover + confirm_with_macd_momentum,28,0.65,0.612,1.10,0.081,25.1,"TCS, WIPRO, SBIN"
bollinger_breakout,5,0.51,0.550,0.85,0.042,8.5,"TATAMOTORS, LT, AXISBANK"
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
- [x] All acceptance criteria are met and tested.
- [x] The `analyze-strategies` command is functional and generates a correct CSV file.
- [x] The analysis logic correctly queries, groups, and aggregates performance data from the database.
- [x] The generated report is sorted and formatted as specified.
- [x] The feature is covered by unit tests (for the aggregation logic) and an integration test (for the CLI command).
- [x] All code passes `mypy --strict` and adheres to all project hard rules.

## Detailed Task List

- **Task 1: Add `analyze-strategies` command to `cli.py`**
  - [x] Add the new Typer command stub.
  - [x] Implement the orchestration logic: call the reporter, handle results, write the file.
  - [x] Add robust error handling.

- **Task 2: Implement `analyze_strategy_performance` in `reporter.py`**
  - [x] Write the SQL query to fetch all required data from the `strategies` table.
  - [x] Implement the loop to parse `rule_stack` JSON and aggregate metrics into a `defaultdict`.
  - [x] Implement the final processing loop to calculate averages and identify top symbols.
  - [x] Ensure the final list is sorted by `avg_edge_score`.

- **Task 3: Implement `format_strategy_analysis_as_csv` in `reporter.py`**
  - [x] Create the function to generate the CSV table from the analysis data.
  - [x] Ensure correct formatting for numbers, percentages, and text alignment.

- **Task 4: Add Comprehensive Tests**
  - [x] In `tests/test_reporter_advanced.py`, add tests for `analyze_strategy_performance` using a pre-populated in-memory DB with sample strategy data.
  - [x] In `tests/test_cli_advanced.py`, add integration tests for the `analyze-strategies` command.
  - [x] Test edge cases: empty database, malformed JSON, missing columns.

## ✅ STORY COMPLETED SUCCESSFULLY

**Completion Summary:**
- All acceptance criteria fulfilled and tested
- CLI command `analyze-strategies` implemented and functional
- CSV report generation working correctly with real data
- Comprehensive test coverage added
- Code quality standards met (mypy, type hints, KISS principles)
- No new dependencies introduced
- Generated sample report: `strategy_performance_report.csv`