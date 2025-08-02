## Development Roadmap: Path to Professional-Grade Trading

This roadmap is designed to systematically eliminate the most critical flaws in the current system. We will prioritize robustness against overfitting, sophisticated risk management, and market adaptability to build a framework capable of discovering and validating genuinely profitable strategies.

### 1. ✅ Implement Walk-Forward Analysis (Story 030 - READY FOR DEVELOPMENT)

**Problem:** The system's greatest vulnerability is **overfitting**. Backtesting on a fixed historical dataset finds strategies that were perfect for the past, not the future. The Product Requirements Document (PRD) correctly identifies this gap (Story 2.2) but it remains unimplemented. All current performance metrics are dangerously misleading.

**Solution:**
Transform the backtester into a walk-forward validation engine that uses professional standards by default. This industry-standard technique simulates real-world performance by repeatedly optimizing a strategy on a "training" data segment and then validating it on a subsequent, unseen "testing" segment.

**Architectural Decision (Kailash Nadh Approach):**
**Make walk-forward analysis the DEFAULT behavior in the `run` command.** This eliminates foot-guns and aligns with professional trading practices where out-of-sample validation is mandatory, not optional.

**Technical Implementation:**
1.  **Configuration:** Add a `walk_forward` section to `config.yaml` with `training_period` (e.g., "730d"), `testing_period` (e.g., "180d"), and `step_size` (e.g., "90d").
2.  **Modify `find_optimal_strategies()` in `backtester.py`:** Use walk-forward analysis by default, with optional `in_sample` parameter for debugging only.
3.  **CLI Integration:** Modify `run` command to use walk-forward by default. Add `--in-sample` flag for academic/debugging use with explicit warnings.
4.  **Reporting:** Generate period-by-period out-of-sample performance reports that concatenate ONLY out-of-sample results. Include consistency scores and realistic expectation warnings.

**Professional Defaults:**
```bash
# DEFAULT: Professional walk-forward validation
quickedge run

# DANGEROUS: In-sample optimization (debugging only, with warnings)
quickedge run --in-sample
```

**Why it's #1:** This is non-negotiable. It is the single most important feature to build. It instills the discipline of out-of-sample testing, turning the tool from an academic exercise into a professional validation framework. **Without this, no other feature matters, as all results are untrustworthy.**

**Status:** Story 030 created and ready for development. Implements professional defaults that prevent accidental overfitting.

### 2. Build a Professional, Volatility-Based Trailing Stop

**Problem:** The performance report is a sea of red, with negative Sharpe ratios and returns. This proves the current exit logic is destroying the alpha captured by the strong entry signals. The `simple_trailing_stop_5pct` is a naive placeholder that fails to adapt to market volatility.

**Solution:**
Implement a professional, volatility-adaptive trailing stop like the **Chandelier Exit**. This mechanism uses the Average True Range (ATR) to set stop-loss levels that are dynamic. It keeps stops wider in volatile markets to avoid premature exits and tightens them in quiet markets to protect profits.

**Technical Implementation:**
1.  **Create `chandelier_exit` in `rules.py`:** The function will calculate the exit level based on the highest high (for longs) since the trade entry, minus a multiple of the ATR (e.g., `HighestHigh(22) - 3 * ATR(22)`).
2.  **Enhance Backtester State Management:** A trailing stop is stateful. The `_generate_exit_signals` function in `backtester.py` must be upgraded to track the `highest_high` on a per-trade basis. `vectorbt` provides mechanisms to handle this stateful logic efficiently.
3.  **Update `rules.yaml`:** Replace the ineffective `simple_trailing_stop` and the rigid `trend_reversal_exit` with the new, superior `chandelier_exit`.

**Why it's #2:** A robust exit strategy is the fastest path to profitability. It lets winning trades run to their full potential while aggressively protecting capital, directly addressing the abysmal Sharpe ratios.

### 3. Implement Risk-Based Position Sizing

**Problem:** The system generates signals but lacks a risk management core. It doesn't define *how much* to trade, which is the most critical question for capital preservation. Without it, a single oversized loss can wipe out weeks of gains.

**Solution:**
Integrate equal-risk position sizing. The size of each position should be calculated so that the initial risk (distance from entry to stop-loss) represents a fixed fraction of the portfolio (e.g., 1%).

**Technical Implementation:**
1.  **Configuration:** Add `risk_per_trade_pct: 0.01` to `config.yaml`.
2.  **Modify Backtester:** The `size` parameter in the `vbt.Portfolio.from_signals` call must be calculated dynamically for each trade.
3.  **Sizing Logic:** For each entry signal, the logic must be:
    *   `risk_per_share = entry_price - initial_stop_loss_price` (using the `atr_stop_loss_1.5x` rule).
    *   `dollar_risk = portfolio_value * risk_per_trade_pct`.
    *   `position_size = dollar_risk / risk_per_share`.
4.  **Vectorization:** This logic must be vectorized to create a `size` array that aligns with the `entries` signal array, ensuring high performance within `vectorbt`.

**Why it's #3:** This introduces professional-grade risk management. It ensures portfolio survivability and makes performance metrics truly comparable across different stocks and volatility regimes.

### 4. Introduce Parameter Robustness Testing

**Problem:** The parameters in `rules.yaml` (e.g., `min_body_ratio: 2.5`) are static "magic numbers." They are likely overfit and fragile. A strategy that works only for one specific parameter value is unreliable.

**Solution:**
Upgrade the "Strategy Seeker" to perform simple grid searches on key parameters and, more importantly, visualize the results to identify robust parameter ranges.

**Technical Implementation:**
1.  **Enhance `rules.yaml`:** Allow parameter values to be specified as a list of options (e.g., `spike_multiplier: [2.0, 2.5, 3.0]`).
2.  **Upgrade `find_optimal_strategies`:** The function must parse these lists and create a grid of all possible parameter combinations to backtest.
3.  **Robustness Reporting:** The `analyze-strategies` command must be enhanced to generate 3D surface plots or heatmaps. These visualizations will plot two parameters against a performance metric like the Sharpe Ratio. A top trader looks for wide, stable "plateaus" of profitability, not sharp, isolated "peaks," as plateaus indicate a robust edge.

**Why it's #4:** This shifts the goal from finding the "perfect" (and likely overfit) strategy to finding a *robust* one. A strategy that is profitable across a range of parameters is far more likely to remain profitable in the future.

### 5. Develop a "Stock Personality" Filter

**Problem:** The current system applies a single strategy type (trend-following pullback) to all stocks, ignoring their unique behaviors. This is like using a hammer for every task.

**Solution:**
Implement a pre-analysis module that classifies stocks into distinct "personalities" (e.g., "High-Momentum Trending," "Low-Volatility Mean-Reverting"). The backtester will then only apply strategies suitable for a stock's specific personality.

**Technical Implementation:**
1.  **Create `personality.py` module:** This module will contain functions to calculate long-term statistical properties of a stock, such as its average volatility (ATR %), trendiness (e.g., ADX score), and mean-reversion tendency (e.g., Hurst Exponent).
2.  **Classification Logic:** A simple classifier will bucket stocks into personalities based on these metrics.
3.  **Enhance `rules.yaml`:** Allow strategies to be tagged with a `personality_target` (e.g., `personality_target: "High-Momentum Trending"`).
4.  **Modify `cli.py`:** Before backtesting, the CLI will first run the personality analysis on the entire universe. During backtesting, it will only test strategies on stocks that match their designated personality target.

**Why it's #5:** This is the capstone feature, codifying the expert trader's wisdom of "fitting the strategy to the instrument." It dramatically increases the efficiency and effectiveness of the strategy discovery process, ensuring the right tool is used for the right job.