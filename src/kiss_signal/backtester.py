"""Backtester - vectorbt-based Strategy Backtesting Module.

This module handles backtesting of rule combinations and edge score calculation.
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

import numpy as np
import pandas as pd
import vectorbt as vbt

# Configure pandas to opt into future behavior for downcasting
pd.set_option('future.no_silent_downcasting', True)

from . import rules
from .config import RulesConfig, EdgeScoreWeights, Config, WalkForwardConfig, RuleDef
from .performance import performance_monitor
from .exceptions import DataMismatchError

__all__ = ["Backtester"]

logger = logging.getLogger(__name__)

class Backtester:
    """Handles strategy backtesting and edge score calculation."""

    def __init__(
        self,
        hold_period: int = 20,
        min_trades_threshold: int = 10,
        initial_capital: float = 100000.0
    ) -> None:
        """Initialize the backtester."""
        self.hold_period = hold_period
        self.min_trades_threshold = min_trades_threshold
        self.initial_capital = initial_capital
        logger.info(
            f"Backtester initialized: hold_period={hold_period}, "
            f"min_trades={min_trades_threshold}"
        )

    def _backtest_combination(
        self,
        combo: List[Any],
        price_data: pd.DataFrame,
        rules_config: RulesConfig,
        edge_score_weights: EdgeScoreWeights,
        symbol: str,
        market_data: Optional[pd.DataFrame] = None,
    ) -> Optional[Dict[str, Any]]:
        """Backtest a single rule combination and return its performance metrics."""
        try:
            # NEW: Apply preconditions first - if stock personality doesn't fit, skip entirely
            if rules_config.preconditions:
                precondition_result = self._check_preconditions(
                    price_data, rules_config.preconditions, symbol
                )
                
                # If preconditions fail, skip this symbol entirely  
                if not precondition_result:
                    logger.debug(f"Stock {symbol} failed precondition checks, skipping strategy evaluation")
                    return None
            
            # NEW: Apply context filters first if any are defined
            if rules_config.context_filters:
                context_signals = self._apply_context_filters(
                    price_data, rules_config.context_filters, symbol, market_data
                )
                
                # If no favorable context periods, skip expensive rule evaluation
                if not context_signals.any():
                    logger.debug(f"No favorable context for {symbol}, skipping")
                    return None
            else:
                # No context filters - allow all periods
                context_signals = pd.Series(True, index=price_data.index)
            
            # Generate combined signal for the rule combination
            entry_signals = self.generate_signals_for_stack(combo, price_data)
            
            if entry_signals is None or not entry_signals.any():
                logger.warning(f"Could not generate entry signals for combo: {[r.name for r in combo]}")
                return None
            
            # Apply context filters to final signals
            final_entry_signals = entry_signals & context_signals
            
            # Generate exit signals from exit_conditions and time-based exits
            exit_signals, sl_stop, tp_stop = self._generate_exit_signals(
                final_entry_signals, price_data, rules_config.exit_conditions
            )
            
            # Debug logging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Raw entry signals for {symbol}: {entry_signals.sum()} total")
                logger.debug(f"Final entry signals for {symbol}: {final_entry_signals.sum()} total")
                logger.debug(f"Exit signals for {symbol}: {exit_signals.sum()} total")
                if sl_stop:
                    logger.debug(f"Stop loss: {sl_stop:.1%}")
                if tp_stop:
                    logger.debug(f"Take profit: {tp_stop:.1%}")
                if final_entry_signals.sum() > 0:
                    logger.debug(f"First 3 entry dates: {final_entry_signals[final_entry_signals].index[:3].tolist()}")
                    logger.debug(f"Last 3 entry dates: {final_entry_signals[final_entry_signals].index[-3:].tolist()}")
            
            portfolio = vbt.Portfolio.from_signals(
                close=price_data['close'],
                entries=final_entry_signals,
                exits=exit_signals,
                sl_stop=sl_stop,
                tp_stop=tp_stop,
                fees=0.001,
                slippage=0.0005,
                init_cash=self.initial_capital,
                size=np.inf,
            )
            
            # More debug logging
            total_trades = portfolio.trades.count()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Portfolio trades count for {symbol}: {total_trades}")
                logger.debug(f"Trade count type: {type(total_trades)}")
                if total_trades == 0 and final_entry_signals.sum() > 0:
                    logger.debug(f"WARNING: {final_entry_signals.sum()} entry signals but 0 trades generated!")
            
            return self._calculate_performance_metrics(
                portfolio, combo, symbol, edge_score_weights, self.min_trades_threshold
            )
        except Exception as e:
            logger.error(f"Error processing rule combination {[r.name for r in combo]}: {e}")
            return None

    def _calculate_performance_metrics(
        self,
        portfolio: vbt.Portfolio,
        combo: List[Any],
        symbol: str,
        edge_score_weights: EdgeScoreWeights,
        min_trades_threshold: int,
    ) -> Optional[Dict[str, Any]]:
        """Calculate performance metrics for a backtest portfolio."""
        total_trades = int(portfolio.trades.count())
        rule_names = " + ".join([r.name for r in combo])

        if total_trades < min_trades_threshold:
            logger.warning(
                f"Strategy '{rule_names}' on '{symbol}' generated only {total_trades} trades, "
                f"below threshold of {min_trades_threshold}."
            )
            return None

        win_pct = portfolio.trades.win_rate()
        sharpe = portfolio.sharpe_ratio()
        avg_return = portfolio.trades.pnl.mean() if not np.isnan(portfolio.trades.pnl.mean()) else 0.0

        edge_score = (win_pct * edge_score_weights.win_pct) + (sharpe * edge_score_weights.sharpe)
        return {
            "symbol": symbol,
            "rule_stack": combo,
            "edge_score": edge_score,
            "win_pct": win_pct,
            "sharpe": sharpe,
            "total_trades": total_trades,
            "avg_return": avg_return,
        }

    def _parse_period(self, period_str: str) -> int:
        """Parse period string like '730d' into number of days."""
        if period_str.endswith('d'):
            return int(period_str[:-1])
        elif period_str.endswith('m'):
            return int(period_str[:-1]) * 30  # Approximate months
        elif period_str.endswith('y'):
            return int(period_str[:-1]) * 365  # Approximate years
        else:
            raise ValueError(f"Invalid period format: {period_str}. Use 'd', 'm', or 'y' suffix.")
    
    def _get_rolling_periods(
        self, 
        data: pd.DataFrame, 
        training_days: int, 
        testing_days: int, 
        step_days: int
    ) -> List[pd.Timestamp]:
        """Generate rolling period start dates for walk-forward analysis."""
        periods: List[pd.Timestamp] = []
        min_required_data = training_days + testing_days
        
        if len(data) < min_required_data:
            logger.warning(f"Insufficient data: {len(data)} days < {min_required_data} required")
            return periods
        
        # Start from the first possible training period
        current_start = data.index[0]
        data_end = data.index[-1]
        
        while True:
            # Calculate the end of testing period for this window
            training_end = current_start + pd.Timedelta(days=training_days)
            testing_end = training_end + pd.Timedelta(days=testing_days)
            
            # Check if we have enough data for this complete window
            if testing_end > data_end:
                break
                
            periods.append(current_start)
            current_start += pd.Timedelta(days=step_days)
            
        return periods
    
    def _legacy_in_sample_optimization(
        self,
        price_data: pd.DataFrame,
        rules_config: RulesConfig, 
        symbol: str,
        freeze_date: Optional[date] = None,
        edge_score_weights: Optional[EdgeScoreWeights] = None,
        config: Optional[Config] = None,
        market_data: Optional[pd.DataFrame] = None
    ) -> List[Dict[str, Any]]:
        """Legacy in-sample optimization - DANGEROUS for live trading decisions."""
        logger.warning("USING IN-SAMPLE OPTIMIZATION - Results are NOT reliable for live trading!")
        
        # This is the current implementation moved here for debugging purposes
        entry_signals = rules_config.entry_signals

        if not entry_signals:
            logger.warning("No entry signals found in configuration for %s.", symbol)
            return []

        # Simple thresholds
        min_edge_score = config.seeker_min_edge_score if config else 0.60
        min_trades = config.seeker_min_trades if config else 20

        if freeze_date is not None:
            price_data = price_data[price_data.index.date <= freeze_date]
            logger.info(f"Using data up to freeze date: {freeze_date}")

        # Infer frequency for vectorbt compatibility
        if price_data.index.freq is None:
            inferred_freq = pd.infer_freq(price_data.index)
            if inferred_freq:
                price_data = price_data.asfreq(inferred_freq)
                logger.debug(f"Inferred frequency '{inferred_freq}' for {symbol}")
            else:
                price_data = price_data.asfreq('D')
                logger.warning(f"Could not infer frequency for {symbol}. Forcing daily frequency ('D').")
            
            # Handle NaN values created by asfreq - forward fill to preserve trading data
            if price_data.isnull().any(axis=None):
                price_data = price_data.ffill()
                logger.debug(f"Forward-filled NaN values after frequency adjustment for {symbol}")

        if edge_score_weights is None:
            edge_score_weights = EdgeScoreWeights(win_pct=0.6, sharpe=0.4)
        
        best_result = None
        
        # Phase 1: Test individual rules
        for rule in entry_signals:
            result = self._test_single_rule([rule], price_data, rules_config, edge_score_weights, symbol, market_data)
            if result and result["edge_score"] >= min_edge_score and result["total_trades"] >= min_trades:
                logger.info(f"Good enough individual rule found: {rule.name} (EdgeScore: {result['edge_score']:.3f})")
                # Augment with full context before returning
                full_context_and_exit_rules = rules_config.context_filters + rules_config.exit_conditions
                result["rule_stack"].extend(full_context_and_exit_rules)
                return [result]
            best_result = self._track_best(result, best_result)
        
        # Phase 2: Test best individual + one confirmation (if needed)
        # Only test if we have multiple rules and didn't find good enough individual
        if len(entry_signals) > 1 and best_result:
            best_rule = None
            # Find the best individual rule from the result
            for rule in entry_signals:
                if rule.name == best_result["rule_stack"][0].name:
                    best_rule = rule
                    break
            
            if best_rule:
                logger.info(f"Testing combinations with best individual rule: {best_rule.name}")
                for confirmation in entry_signals:
                    if confirmation.name != best_rule.name:
                        combo = [best_rule, confirmation]
                        result = self._test_single_rule(combo, price_data, rules_config, edge_score_weights, symbol, market_data)
                        if result and result["edge_score"] >= min_edge_score and result["total_trades"] >= min_trades:
                            logger.info(f"Good enough combination found: {best_rule.name} + {confirmation.name}")
                            # Augment with full context before returning
                            full_context_and_exit_rules = rules_config.context_filters + rules_config.exit_conditions
                            result["rule_stack"].extend(full_context_and_exit_rules)
                            return [result]
                        best_result = self._track_best(result, best_result)
        
        # Return best found and augment with full context
        final_strategies = [best_result] if best_result else []
        
        # Augment the rule_stack for each successful strategy to include the full context.
        # This ensures the persisted strategy reflects all rules used in the backtest.
        full_context_and_exit_rules = rules_config.context_filters + rules_config.exit_conditions
        for strategy in final_strategies:
            strategy["rule_stack"].extend(full_context_and_exit_rules)
        
        return final_strategies
    
    def walk_forward_backtest(
        self,
        data: pd.DataFrame,
        walk_forward_config: WalkForwardConfig,
        rules_config: RulesConfig,
        symbol: str,
        edge_score_weights: Optional[EdgeScoreWeights] = None,
        config: Optional[Config] = None,
        market_data: Optional[pd.DataFrame] = None
    ) -> List[Dict[str, Any]]:
        """
        Industry-standard walk-forward analysis - DEFAULT behavior.
        
        Returns ONLY out-of-sample performance - the only metrics that matter.
        """
        # --- NEW VALIDATION BLOCK ---
        if market_data is not None and not market_data.empty:
            if data.index.min() < market_data.index.min() or data.index.max() > market_data.index.max():
                error_msg = (
                    f"CRITICAL DATA MISMATCH for {symbol}: Market data range "
                    f"({market_data.index.min().date()} to {market_data.index.max().date()}) "
                    f"does not fully cover stock data range "
                    f"({data.index.min().date()} to {data.index.max().date()}). "
                    "Ensure market data history is as long as stock data history."
                )
                logger.error(error_msg)
                # Fail loudly instead of silently producing no results.
                raise DataMismatchError(error_msg)
        # --- END NEW BLOCK ---

        training_days = self._parse_period(walk_forward_config.training_period)
        testing_days = self._parse_period(walk_forward_config.testing_period)
        step_days = self._parse_period(walk_forward_config.step_size)
        
        oos_results = []  # Out-of-sample results only
        periods = self._get_rolling_periods(data, training_days, testing_days, step_days)
        
        if not periods:
            logger.warning(f"No valid periods for walk-forward analysis on {symbol}")
            return []
        
        # Roll through time periods
        for i, period_start in enumerate(periods):
            # Calculate all period boundaries upfront
            training_start = period_start
            training_end = period_start + pd.Timedelta(days=training_days)
            test_start = training_end
            test_end = test_start + pd.Timedelta(days=testing_days)
            
            # 1. Training phase - find best strategy on training data only
            train_data = data[training_start:training_end]
            
            if train_data.empty:
                logger.warning(f"Empty training data for period {i+1}, skipping")
                continue
                
            # Slice market data to match training period for proper alignment
            sliced_market_data = None
            if market_data is not None:
                sliced_market_data = market_data[training_start:training_end]
                logger.debug(f"Sliced market data from {len(market_data)} to {len(sliced_market_data)} rows for training period")
            
            # Find best strategy using in-sample optimization on training data only
            best_strategies = self._legacy_in_sample_optimization(
                train_data, rules_config, symbol, None, edge_score_weights, config, sliced_market_data
            )
            
            if not best_strategies:
                logger.warning(f"No viable strategy found in training period {i+1}")
                continue
                
            best_strategy = best_strategies[0]  # Take the best one
            
            # 2. Testing phase - apply strategy to unseen out-of-sample data
            test_start = training_end
            test_end = test_start + pd.Timedelta(days=testing_days)
            test_data = data[test_start:test_end]
            
            if test_data.empty:
                logger.warning(f"Empty testing data for period {i+1}, skipping")
                continue
            
            # Slice market data to match testing period for proper alignment
            sliced_test_market_data = None
            if market_data is not None:
                sliced_test_market_data = market_data[test_start:test_end]
                logger.debug(f"Sliced market data for testing period from {len(market_data)} to {len(sliced_test_market_data)} rows")
            
            # 3. Record ONLY out-of-sample performance
            oos_performance = self._backtest_single_strategy_oos(
                test_data, best_strategy["rule_stack"], rules_config, 
                edge_score_weights, symbol, period_start, test_start, test_end, sliced_test_market_data
            )
            
            if oos_performance and oos_performance["total_trades"] >= walk_forward_config.min_trades_per_period:
                oos_results.append(oos_performance)
            else:
                logger.debug(f"Period {i+1} insufficient trades, skipping")
        
        # Final metrics come from concatenated out-of-sample periods only
        if not oos_results:
            logger.warning(f"No valid out-of-sample periods for {symbol}")
            return []
            
        consolidated_result = self._consolidate_oos_results(oos_results, symbol, edge_score_weights)
        return [consolidated_result] if consolidated_result else []
    
    def _backtest_single_strategy_oos(
        self,
        test_data: pd.DataFrame,
        rule_stack: List[Any],
        rules_config: RulesConfig,
        edge_score_weights: Optional[EdgeScoreWeights],
        symbol: str,
        period_start: pd.Timestamp,
        test_start: pd.Timestamp, 
        test_end: pd.Timestamp,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[Dict[str, Any]]:
        """Backtest a single strategy on out-of-sample test data."""
        try:
            # Normalize column names to lowercase for consistent data contract
            test_data = test_data.copy()
            if len(test_data.columns) > 0:
                test_data.columns = test_data.columns.str.lower()
                
            # Apply the same logic as _backtest_combination but for testing only
            if edge_score_weights is None:
                edge_score_weights = EdgeScoreWeights(win_pct=0.6, sharpe=0.4)
                
            # Apply context filters if any are defined
            if rules_config.context_filters:
                context_signals = self._apply_context_filters(
                    test_data, rules_config.context_filters, symbol, market_data
                )
                
                # If no favorable context periods, skip
                if not context_signals.any():
                    logger.debug(f"No favorable context for {symbol} in OOS period")
                    return None
            else:
                # No context filters - allow all periods
                context_signals = pd.Series(True, index=test_data.index)
            
            # Generate combined signal for the rule combination
            entry_signals = self.generate_signals_for_stack(rule_stack, test_data)
            
            # Apply context filter to entry signals
            entry_signals = entry_signals & context_signals
            
            if not entry_signals.any():
                logger.debug(f"No entry signals generated for {symbol} in OOS period")
                return None
            
            # Generate exit signals
            exit_signals, sl_stop, tp_stop = self._generate_exit_signals(
                entry_signals, test_data, rules_config.exit_conditions
            )
            
            # Create vectorbt portfolio
            portfolio = vbt.Portfolio.from_signals(
                test_data["close"],
                entries=entry_signals,
                exits=exit_signals,
                init_cash=self.initial_capital,
                sl_stop=sl_stop,
                tp_stop=tp_stop,
            )
            
            total_trades = len(portfolio.trades.records_readable)
            if total_trades < self.min_trades_threshold:
                return None

            win_pct = portfolio.trades.win_rate()
            sharpe = portfolio.sharpe_ratio()
            avg_return = portfolio.trades.pnl.mean() if not np.isnan(portfolio.trades.pnl.mean()) else 0.0

            edge_score = (win_pct * edge_score_weights.win_pct) + (sharpe * edge_score_weights.sharpe)
            
            return {
                "symbol": symbol,
                "rule_stack": rule_stack,
                "edge_score": edge_score,
                "win_pct": win_pct,
                "sharpe": sharpe,
                "total_trades": total_trades,
                "avg_return": avg_return,
                "oos_period_start": period_start,
                "oos_test_start": test_start,
                "oos_test_end": test_end,
                "is_oos": True  # Mark as out-of-sample
            }
            
        except Exception as e:
            logger.error(f"OOS backtest failed for {symbol}: {e}")
            return None
    
    def _consolidate_oos_results(
        self, 
        oos_results: List[Dict[str, Any]], 
        symbol: str,
        edge_score_weights: Optional[EdgeScoreWeights] = None
    ) -> Optional[Dict[str, Any]]:
        """Consolidate multiple out-of-sample results into final metrics.
        
        Uses mathematically correct aggregation:
        - Win percentage: weighted by trade count (total_wins / total_trades)
        - Sharpe ratio: trade-weighted average (approximation)
        - Average return: weighted by trade count
        - Edge score: recalculated from consolidated metrics
        """
        if not oos_results:
            return None
            
        if edge_score_weights is None:
            edge_score_weights = EdgeScoreWeights(win_pct=0.6, sharpe=0.4)
            
        # Calculate trade-weighted consolidation
        total_trades = sum(r["total_trades"] for r in oos_results)
        
        # Win percentage: total wins / total trades (not simple average)
        total_wins = sum(r["win_pct"] * r["total_trades"] for r in oos_results)
        consolidated_win_pct = total_wins / total_trades if total_trades > 0 else 0.0
        
        # Sharpe ratio: trade-weighted average (best approximation without individual returns)
        weighted_sharpe_sum = sum(r["sharpe"] * r["total_trades"] for r in oos_results)
        consolidated_sharpe = weighted_sharpe_sum / total_trades if total_trades > 0 else 0.0
        
        # Average return: trade-weighted average
        weighted_return_sum = sum(r["avg_return"] * r["total_trades"] for r in oos_results)
        consolidated_avg_return = weighted_return_sum / total_trades if total_trades > 0 else 0.0
        
        # Edge score: recalculate from consolidated metrics
        consolidated_edge_score = (
            consolidated_win_pct * edge_score_weights.win_pct + 
            consolidated_sharpe * edge_score_weights.sharpe
        )
        
        # Find the most common rule stack by its signature
        signatures = [self._create_rule_stack_signature(r["rule_stack"]) for r in oos_results]
        most_common_sig = Counter(signatures).most_common(1)[0][0]
        representative_stack = next(
            r["rule_stack"] for r in oos_results 
            if self._create_rule_stack_signature(r["rule_stack"]) == most_common_sig
        )
        
        return {
            "symbol": symbol,
            "rule_stack": representative_stack,
            "edge_score": consolidated_edge_score,
            "win_pct": consolidated_win_pct,
            "sharpe": consolidated_sharpe,
            "total_trades": total_trades,
            "avg_return": consolidated_avg_return,
            "oos_periods": len(oos_results),
            "is_oos": True
        }

    def _create_rule_stack_signature(self, rule_stack: List[Any]) -> str:
        """Create a signature for rule stack comparison.
        
        Args:
            rule_stack: List of rule definitions
            
        Returns:
            String signature for comparison
        """
        if not rule_stack:
            return "empty"
            
        # Extract rule types and key parameters for comparison
        signature_parts = []
        for rule in rule_stack:
            if hasattr(rule, 'type'):
                rule_type = rule.type
                # Include key parameters that affect strategy identity
                if hasattr(rule, 'params') and rule.params:
                    key_params = {k: v for k, v in rule.params.items() 
                                if k in ['short', 'long', 'period', 'threshold']}
                    if key_params:
                        signature_parts.append(f"{rule_type}({key_params})")
                    else:
                        signature_parts.append(rule_type)
                else:
                    signature_parts.append(rule_type)
            elif isinstance(rule, dict):
                rule_type = rule.get('type', 'unknown')
                params = rule.get('params', {})
                key_params = {k: v for k, v in params.items() 
                            if k in ['short', 'long', 'period', 'threshold']}
                if key_params:
                    signature_parts.append(f"{rule_type}({key_params})")
                else:
                    signature_parts.append(rule_type)
            else:
                signature_parts.append(str(rule))
                
        return "|".join(sorted(signature_parts))
    
    @performance_monitor.profile_performance
    def find_optimal_strategies(
        self,
        price_data: pd.DataFrame,
        rules_config: RulesConfig,
        symbol: str = "",  # Keep symbol before market_data for backward compatibility
        market_data: Optional[pd.DataFrame] = None,
        freeze_date: Optional[date] = None,
        edge_score_weights: Optional[EdgeScoreWeights] = None,
        config: Optional[Config] = None,  # Add config parameter
        in_sample: bool = False  # NEW: For debugging only
    ) -> Any:
        """
        Discover optimal strategies using professional walk-forward analysis by default.
        
        Args:
            rules_config: RulesConfig Pydantic model with entry_signals and exit_conditions.
            price_data: OHLCV price data for backtesting
            symbol: The stock symbol being tested, for logging purposes.
            market_data: Optional market data for context filters
            freeze_date: Optional cutoff date for data (for deterministic testing)
            edge_score_weights: Optional EdgeScoreWeights model for edge score calculation
            config: Optional Config object for walk-forward and seeker thresholds
            in_sample: If True, uses dangerous in-sample optimization (debugging only)
            
        Returns:
            List of strategies with edge scores and performance metrics, ranked by edge score
        """
        if in_sample:
            logger.warning("USING IN-SAMPLE optimization. Results are NOT reliable for live trading!")
            return self._legacy_in_sample_optimization(
                price_data, rules_config, symbol, freeze_date, edge_score_weights, config, market_data
            )
        
        # DEFAULT: Professional walk-forward analysis
        if config and config.walk_forward.enabled:
            logger.info(f"Using walk-forward analysis for {symbol}")
            return self.walk_forward_backtest(
                price_data, config.walk_forward, rules_config, symbol, edge_score_weights, config, market_data
            )
        else:
            # For MVP: Fall back to in-sample if walk-forward not enabled
            logger.warning(f"Walk-forward analysis disabled for {symbol}, using in-sample optimization")
            return self._legacy_in_sample_optimization(
                price_data, rules_config, symbol, freeze_date, edge_score_weights, config, market_data
            )

    def _generate_time_based_exits(self, entry_signals: pd.Series, hold_period: int) -> pd.Series:
        """Generate exit signals based on holding period after entry signals."""
        return entry_signals.vbt.fshift(hold_period)

    def _generate_signals(self, rule_def: Any, price_data: pd.DataFrame) -> pd.Series:
        """
        Generates entry signals for a given rule definition.
        Raises:
            ValueError: If rule definition is invalid or rule not found
        """
        # Handle both object and dict formats
        if hasattr(rule_def, 'type'):
            # Pydantic model format
            rule_type = rule_def.type
            rule_params = rule_def.params
        else:
            # Dict format (from JSON)
            rule_type = rule_def.get('type')
            rule_params = rule_def.get('params', {})

        if not rule_type:
            raise ValueError(f"Rule definition missing 'type' field: {rule_def}")

        rule_func = getattr(rules, rule_type, None)
        if rule_func is None:
            raise ValueError(f"Rule function '{rule_type}' not found in rules module")

        # Remove overly strict parameter validation - let Python handle it naturally
        # Some rules have optional parameters with defaults and should work with empty params
        
        # Handle empty DataFrame - return empty Series immediately
        if price_data.empty:
            return pd.Series(dtype=bool, name='signals')
        
        # Normalize column names to lowercase for consistent data contract
        # Many rules expect lowercase column names ('close', 'open', 'high', 'low')
        price_data_normalized = price_data.copy()
        if len(price_data_normalized.columns) > 0:
            price_data_normalized.columns = price_data_normalized.columns.str.lower()
        
        try:
            # Defensive parameter type conversion - ensure numeric strings become numbers
            converted_params: Dict[str, Any] = {}
            for key, value in rule_params.items():
                # Filter out index_symbol parameter as it's not accepted by rule functions
                if key == 'index_symbol':
                    continue
                if isinstance(value, str):
                    # Try to convert string to number if it looks numeric
                    try:
                        if '.' in value and value.replace('.', '').replace('-', '').isdigit():
                            converted_params[key] = float(value)
                        elif value.replace('-', '').isdigit():
                            converted_params[key] = int(value)
                        else:
                            converted_params[key] = str(value)
                    except ValueError:
                        # If conversion fails, keep as string (might be a symbol/name)
                        converted_params[key] = str(value)
                else:
                    converted_params[key] = value
                    
            # Call the actual rule function from the rules module
            entry_signals = rule_func(price_data_normalized, **converted_params)
        except Exception as e:
            logger.error(f"Error executing rule '{rule_type}' with params {rule_params}: {e}")
            raise ValueError(f"Rule '{rule_type}' failed execution") from e

        # Log only if signal count is unusually low (potential issue)
        signal_count = entry_signals.sum()
        if signal_count == 0:
            logger.debug(f"Rule '{rule_type}' generated no signals on {len(price_data)} data points")
        elif signal_count < 5:
            logger.debug(f"Rule '{rule_type}' generated only {signal_count} signals on {len(price_data)} data points")

        return entry_signals

    def generate_signals_for_stack(
        self, rule_stack: List[Any], price_data: pd.DataFrame
    ) -> pd.Series:
        """Generates combined entry signals for a given rule stack.
        
        This is the single, reusable implementation for running a rule stack.
        It filters out ATR exit functions and combines entry signals using AND logic.
        
        Args:
            rule_stack: List of rule definitions to combine (can be objects or dicts)
            price_data: DataFrame with OHLCV data
            
        Returns:
            Combined boolean Series with entry signals
        """
        combined_signals: Optional[pd.Series] = None
        
        # Filter out ATR exit functions - handle both object and dict formats
        entry_rules = []
        for r in rule_stack:
            rule_type = r.type if hasattr(r, 'type') else r.get('type')
            if rule_type not in ['stop_loss_atr', 'take_profit_atr']:
                entry_rules.append(r)

        for rule_def in entry_rules:
            rule_signals = self._generate_signals(rule_def, price_data)
            if combined_signals is None:
                combined_signals = rule_signals.copy()
            else:
                combined_signals &= rule_signals

        if combined_signals is not None:
            return combined_signals.fillna(False)
        return pd.Series(False, index=price_data.index)

    def _generate_exit_signals(
        self, 
        entry_signals: pd.Series, 
        price_data: pd.DataFrame, 
        exit_conditions: List[Any]
    ) -> tuple[pd.Series, Optional[float], Optional[float]]:
        """Generate combined exit signals from exit_conditions and time-based exits.
        
        Args:
            entry_signals: Boolean series of entry signals
            price_data: DataFrame with OHLCV data
            exit_conditions: List of RuleDef objects for exit conditions
            
        Returns:
            Tuple of (exit_signals, sl_stop, tp_stop)
        """
        # Initialize return values
        sl_stop = None
        tp_stop = None
        exit_signals_list = []
        
        # Process exit_conditions
        if exit_conditions:
            for rule_def in exit_conditions:
                if rule_def.type == 'stop_loss_pct':
                    if sl_stop is None:
                        sl_stop = rule_def.params['percentage']
                    else:
                        logger.warning(f"Multiple stop_loss_pct rules found, using first one: {sl_stop:.1%}")
                        
                elif rule_def.type == 'take_profit_pct':
                    if tp_stop is None:
                        tp_stop = rule_def.params['percentage']
                    else:
                        logger.warning(f"Multiple take_profit_pct rules found, using first one: {tp_stop:.1%}")
                        
                elif rule_def.type in ['stop_loss_atr', 'take_profit_atr']:
                    # Handle ATR-based exits with position tracking
                    try:
                        atr_exit_signals = self._generate_atr_exit_signals(
                            entry_signals, price_data, rule_def
                        )
                        exit_signals_list.append(atr_exit_signals)
                        logger.debug(f"Generated {atr_exit_signals.sum()} ATR exit signals for {rule_def.name}")
                    except Exception as e:
                        logger.error(f"Failed to generate ATR exit signals for {rule_def.name}: {e}")
                        
                else:
                    # Generate signals for indicator-based exits
                    try:
                        exit_signal = self._generate_signals(rule_def, price_data)
                        exit_signals_list.append(exit_signal)
                        logger.debug(f"Generated {exit_signal.sum()} exit signals for {rule_def.name}")
                    except Exception as e:
                        logger.error(f"Failed to generate exit signals for {rule_def.name}: {e}")
        
        # Combine indicator-based exits with logical OR
        combined_exit_signals = pd.Series(False, index=price_data.index)
        if exit_signals_list:
            combined_exit_signals = pd.concat(exit_signals_list, axis=1).any(axis=1)
        
        # Add time-based exit (always included as fallback)
        time_based_exits = self._generate_time_based_exits(entry_signals, self.hold_period)
        final_exit_signals = combined_exit_signals | time_based_exits
        
        logger.debug(f"Combined exit signals: {final_exit_signals.sum()} total")
        return final_exit_signals, sl_stop, tp_stop

    def _track_entry_prices(self, entry_signals: pd.Series, price_data: pd.DataFrame) -> pd.Series:
        """Track entry prices for each position to enable ATR-based exits.
        
        Args:
            entry_signals: Boolean series indicating entry dates
            price_data: DataFrame with OHLCV data
            
        Returns:
            Series with entry prices aligned to price_data index, NaN for non-entry dates
        """
        entry_prices = pd.Series(index=price_data.index, dtype=float)
        
        # Fill entry prices on entry signal dates
        entry_dates = entry_signals[entry_signals].index
        for entry_date in entry_dates:
            if entry_date in price_data.index:
                entry_prices[entry_date] = price_data.loc[entry_date, 'close']
        
        return entry_prices

    def _generate_atr_exit_signals(
        self,
        entry_signals: pd.Series,
        price_data: pd.DataFrame,
        rule_def: Any
    ) -> pd.Series:
        """Generate exit signals for ATR-based rules.
        
        Args:
            entry_signals: Boolean series of entry signals
            price_data: DataFrame with OHLCV data
            rule_def: RuleDef object for ATR exit condition
            
        Returns:
            Boolean series of exit signals
        """
        # Get ATR parameters
        period = rule_def.params.get('period', 14)
        multiplier = rule_def.params.get('multiplier', 2.0 if rule_def.type == 'stop_loss_atr' else 4.0)
        
        # Pre-calculate ATR for performance (cache it)
        try:
            atr_values = rules.calculate_atr(price_data, period)
        except Exception as e:
            logger.warning(f"Failed to calculate ATR for {rule_def.name}: {e}")
            return pd.Series(False, index=price_data.index)

        # Vectorized approach: forward-fill entry prices and calculate exit levels
        entry_prices = price_data['close'].where(entry_signals).ffill()
        
        if rule_def.type == 'stop_loss_atr':
            exit_level = entry_prices - (multiplier * atr_values)
            exit_signals = price_data['close'] <= exit_level
        else:  # take_profit_atr
            exit_level = entry_prices + (multiplier * atr_values)
            exit_signals = price_data['close'] >= exit_level
        
        logger.debug(f"Generated {exit_signals.sum()} ATR-based exit signals for {rule_def.name}")
        return exit_signals

    def _check_preconditions(
        self,
        price_data: pd.DataFrame,
        preconditions: List[Any],
        symbol: str
    ) -> bool:
        """Check if stock meets all precondition requirements.
        
        Use full historical data for calculation (to allow indicators like 200-day SMA),
        but check only the most recent result to determine if the precondition is currently met.
        """
        if not preconditions:
            return True
        
        for precondition in preconditions:
            try:
                # Apply precondition function to FULL data for proper calculation
                precondition_params = precondition.params.copy()
                precondition_signals = getattr(rules, precondition.type)(price_data, **precondition_params)
                
                # Simple check: Are we meeting the precondition now (most recent valid period)?
                recent_valid_signals = precondition_signals.dropna()
                if len(recent_valid_signals) == 0:
                    logger.debug(f"Stock {symbol} failed precondition '{precondition.name}': No valid data")
                    return False
                    
                currently_meets_condition = recent_valid_signals.iloc[-1]
                if not currently_meets_condition:
                    logger.debug(f"Stock {symbol} failed precondition '{precondition.name}': Current condition not met")
                    return False
                    
                logger.debug(f"Stock {symbol} passed precondition '{precondition.name}': Currently meets condition")
                            
            except Exception as e:
                logger.error(f"Error checking precondition '{precondition.name}' for {symbol}: {e}")
                # Fail-safe: if precondition check fails, exclude stock
                return False
        
        logger.info(f"Stock {symbol} passed all {len(preconditions)} precondition checks")
        return True

    def _apply_context_filters(
        self,
        stock_data: pd.DataFrame,
        context_filters: List[Any],
        symbol: str,
        market_data: Optional[pd.DataFrame],
    ) -> pd.Series:
        """Apply context filters and return combined boolean series."""
        if not context_filters:
            return pd.Series(True, index=stock_data.index)
        
        combined_signals = pd.Series(True, index=stock_data.index)
        
        for filter_def in context_filters:
            try:
                if filter_def.type == "market_above_sma":
                    # Check if market data is provided
                    if market_data is None:
                        logger.warning(f"Market data not provided for context filter on {symbol}")
                        return pd.Series(False, index=stock_data.index)
                    
                    # Apply the filter with only valid parameters for market_above_sma
                    valid_params = {}
                    if "period" in filter_def.params:
                        valid_params["period"] = filter_def.params["period"]
                    
                    # Convert string parameters to appropriate types (defensive programming)
                    converted_valid_params = {}
                    for key, value in valid_params.items():
                        if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                            converted_valid_params[key] = float(value) if '.' in value else int(value)
                        else:
                            converted_valid_params[key] = value
                    
                    filter_signals = getattr(rules, filter_def.type)(market_data, **converted_valid_params)
                    
                    # Align with stock data and apply AND logic
                    stock_index = stock_data.index
                    aligned_filter = filter_signals.reindex(stock_index)
                    aligned_filter = aligned_filter.ffill().fillna(False).infer_objects(copy=False)
                    combined_signals &= aligned_filter
                    
                    # Log filter effectiveness
                    filter_count = int(aligned_filter.sum())  # Ensure numeric type for arithmetic
                    logger.debug(f"Context filter '{filter_def.name}' for {symbol}: "
                                f"{filter_count}/{len(aligned_filter)} days pass "
                                f"({filter_count/len(aligned_filter)*100:.1f}%)")
                else:
                    raise ValueError(f"Unknown context filter type: {filter_def.type}")
                    
            except Exception as e:
                logger.error(f"Error applying context filter '{filter_def.name}' to {symbol}: {e}")
                # Fail-safe: if context filter fails, exclude all signals
                return pd.Series(False, index=stock_data.index)
        
        combined_count = int(combined_signals.sum())
        # Only log if filter pass rate is unusually low
        pass_rate = combined_count/len(combined_signals)*100
        if pass_rate < 20:
            logger.debug(f"Low filter pass rate for {symbol}: {pass_rate:.1f}% ({combined_count}/{len(combined_signals)} days)")
        
        return combined_signals

    def _test_single_rule(self, entry_rules: List[RuleDef], price_data: pd.DataFrame, 
                          rules_config: RulesConfig, edge_score_weights: EdgeScoreWeights, 
                          symbol: str, market_data: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Test a specific combination of entry rules."""
        return self._backtest_combination(entry_rules, price_data, rules_config, edge_score_weights, symbol, market_data)

    def _track_best(self, current: Optional[Dict[str, Any]], best: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Track the best result by edge score."""
        if not current:
            return best
        if not best or current["edge_score"] > best["edge_score"]:
            return current
        return best
