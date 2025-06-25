"Analyze the attached #pytest_results.txt to identify all test failures. I suspect the root cause is a **structural issue** within the MEQSAP codebase, rather than a simple logical error in a single function.

Please perform the following:

1.  **Failure Identification**:
    * List the specific tests that are failing from `pytest_results.txt`.
    * Briefly state the direct error message/symptom for each.
    
2.  **Root Cause Analysis (Structural Focus)**:
    * Given the error messages and the MEQSAP architecture (e.g., interactions between `config.py`, `data.py`, `backtest.py`, `reporting.py`, Pydantic model usage, data flow through `StrategySignalGenerator` or `vectorbt` portfolio creation), investigate the codebase to determine the underlying **structural root cause**.
    * Explain this structural issue clearly. For instance, is it a problem with data integrity not being maintained across module boundaries? An incorrect assumption about object state? A misconfigured dependency? Or a flawed interaction pattern between classes/modules?

3.  **Proposed Fix**:
    * Provide specific code modifications (ideally in diff format or clearly indicating file and line numbers) to address the identified structural root cause.
    * Explain why this fix resolves the structural problem.
    * **Strictly ensure fix identified not a known issue documented in `memory.md` or `docs/resolved_issues.md`**

4.  ** #memory.md Entry**:
    * Draft a concise entry for our `docs/memory.md` file. This entry should:
        * Clearly describe the structural issue discovered.
        * Outline the nature of the fix or design principle reinforced.
        * Focus on the lesson learned to prevent similar structural issues in the future.

Example of a structural issue: 'Data from `data.py` was assumed to always have a `DateTimeIndex`, but edge cases in `yfinance` responses sometimes yielded a `RangeIndex` under certain error conditions, breaking `vectorbt` assumptions in `run_backtest`.'

Ensure your analysis goes beyond surface-level symptoms to the deeper architectural or design flaw."