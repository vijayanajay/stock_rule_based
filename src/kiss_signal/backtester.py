"""Backtester - vectorbt-based Strategy Backtesting Module.

This module handles backtesting of rule combinations and edge score calculation.
"""

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import vectorbt as vbt

from . import rules
from .config import RulesConfig
from .performance import performance_monitor

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

    @performance_monitor.profile_performance
    def find_optimal_strategies(
        self, 
        price_data: pd.DataFrame,
        rules_config: RulesConfig,
        symbol: str = "",  # Added symbol for logging
        freeze_date: Any = None,  # Accept date or None
        edge_score_weights: Optional[Dict[str, float]] = None
    ) -> Any:
        """Find optimal rule combinations through backtesting.
        
        Args:
            rules_config: RulesConfig Pydantic model with 'baseline' and 'layers' rule configs.
            price_data: OHLCV price data for backtesting
            symbol: The stock symbol being tested, for logging purposes.
            freeze_date: Optional cutoff date for data (for deterministic testing)
            edge_score_weights: Optional custom weights for edge score calculation
            
        Returns:
            List of strategies with edge scores and performance metrics, ranked by edge score
        """
        baseline_rule = rules_config.baseline
        layers = rules_config.layers

        if not baseline_rule:
            logger.warning("No baseline rule found in configuration for %s.", symbol)
            return []

        # Create combinations to test: baseline alone, and baseline + each layer
        combinations_to_test = [[baseline_rule]] + [[baseline_rule, layer] for layer in layers]

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
            if price_data.isnull().any().any():
                price_data = price_data.ffill()
                logger.debug(f"Forward-filled NaN values after frequency adjustment for {symbol}")

        if edge_score_weights is None:
            edge_score_weights = {'win_pct': 0.6, 'sharpe': 0.4}
        
        logger.info(f"Backtesting {len(combinations_to_test)} rule combinations for {symbol}")
        strategies = []
        
        for i, combo in enumerate(combinations_to_test):
            try:
                # Generate combined signal for the rule combination
                entry_signals: Optional[pd.Series] = None
                for rule_def in combo:
                    rule_signals = self._generate_signals(rule_def, price_data)
                    if entry_signals is None:
                        entry_signals = rule_signals.copy()
                    else:
                        entry_signals &= rule_signals
                
                if entry_signals is None:
                    # This case should ideally not be reached if combos are always non-empty
                    logger.warning(f"Could not generate entry signals for combo: {[r.name for r in combo]}")
                    continue
                
                # Generate exit signals from sell_conditions and time-based exits
                exit_signals, sl_stop, tp_stop = self._generate_exit_signals(
                    entry_signals, price_data, rules_config.sell_conditions
                )
                
                # Debug logging
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Entry signals for {symbol}: {entry_signals.sum()} total")
                    logger.debug(f"Exit signals for {symbol}: {exit_signals.sum()} total")
                    if sl_stop:
                        logger.debug(f"Stop loss: {sl_stop:.1%}")
                    if tp_stop:
                        logger.debug(f"Take profit: {tp_stop:.1%}")
                    if entry_signals.sum() > 0:
                        logger.debug(f"First 3 entry dates: {entry_signals[entry_signals].index[:3].tolist()}")
                        logger.debug(f"Last 3 entry dates: {entry_signals[entry_signals].index[-3:].tolist()}")
                
                portfolio = vbt.Portfolio.from_signals(
                    close=price_data['close'],
                    entries=entry_signals,
                    exits=exit_signals,
                    sl_stop=sl_stop,
                    tp_stop=tp_stop,
                    fees=0.001,
                    slippage=0.0005,
                    init_cash=self.initial_capital,
                    size=np.inf,
                )
                total_trades = portfolio.trades.count()
                
                # More debug logging
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Portfolio trades count for {symbol}: {total_trades}")
                    logger.debug(f"Trade count type: {type(total_trades)}")
                    if total_trades == 0 and entry_signals.sum() > 0:
                        logger.debug(f"WARNING: {entry_signals.sum()} entry signals but 0 trades generated!")
                
                # Ensure total_trades is explicitly cast to Python int to avoid any vectorbt-specific type issues
                total_trades = int(total_trades)
                
                rule_names = " + ".join([r.name for r in combo])
                
                # Calculate performance metrics regardless of threshold for completeness
                if total_trades > 0:
                    win_pct = portfolio.trades.win_rate()  # Already returns decimal ratio (e.g., 0.65 for 65%)
                    sharpe = portfolio.sharpe_ratio()
                    avg_return = portfolio.trades.pnl.mean() if not np.isnan(portfolio.trades.pnl.mean()) else 0.0
                else:
                    win_pct = 0.0
                    sharpe = 0.0
                    avg_return = 0.0
                
                # Skip strategies that don't meet the minimum trades threshold
                if total_trades < self.min_trades_threshold:
                    logger.warning(f"Strategy '{rule_names}' on '{symbol}' generated only {total_trades} trades, which is below the threshold of {self.min_trades_threshold}.")
                    continue
                edge_score = (win_pct * edge_score_weights['win_pct']) + (sharpe * edge_score_weights['sharpe'])
                strategy = {
                    'rule_stack': combo,  # Persist the entire rule combination
                    'edge_score': edge_score,
                    'win_pct': win_pct,
                    'sharpe': sharpe,
                    'total_trades': int(total_trades),  # Ensure this is always an integer
                    'avg_return': avg_return,
                }
                
                strategies.append(strategy)
            except Exception as e:
                logger.error(f"Error processing rule combination {combo}: {e}")
                continue
        strategies.sort(key=lambda x: x['edge_score'], reverse=True)
        return strategies

    def calc_edge_score(self, win_pct: float, sharpe: float, weights: Dict[str, float]) -> float:
        """Calculate edge score using weighted metrics.
        
        Args:
            win_pct: Win percentage (0.0 to 1.0)
            sharpe: Sharpe ratio
            weights: EdgeScoreWeights dict
            
        Returns:
            Calculated edge score
        """
        edge_score = (win_pct * weights['win_pct']) + (sharpe * weights['sharpe'])
        return edge_score

    def _generate_time_based_exits(self, entry_signals: pd.Series, hold_period: int) -> pd.Series:
        """Generate exit signals based on holding period after entry signals."""
        return entry_signals.vbt.fshift(hold_period)

    def _generate_signals(self, rule_def: Any, price_data: pd.DataFrame) -> pd.Series:
        """
        Generates entry signals for a given rule definition.
        Raises:
            ValueError: If rule definition is invalid or rule not found
        """
        # Enforce Pydantic model contract
        rule_type = rule_def.type
        rule_params = rule_def.params

        if not rule_type:
            raise ValueError(f"Rule definition missing 'type' field: {rule_def}")

        rule_func = getattr(rules, rule_type, None)
        if rule_func is None:
            raise ValueError(f"Rule function '{rule_type}' not found in rules module")

        if not rule_params:
            raise ValueError(f"Missing parameters for rule '{rule_type}'") # This is the new, better message

        try:
            # Call the actual rule function from the rules module
            entry_signals = rule_func(price_data, **rule_params)
        except Exception as e:
            logger.error(f"Error executing rule '{rule_type}' with params {rule_params}: {e}")
            raise ValueError(f"Rule '{rule_type}' failed execution") from e

        # Always log signal count for debugging
        signal_count = entry_signals.sum()
        logger.info(f"Rule '{rule_type}' generated {signal_count} signals on {len(price_data)} data points")

        return entry_signals

    def _generate_exit_signals(
        self, 
        entry_signals: pd.Series, 
        price_data: pd.DataFrame, 
        sell_conditions: list
    ) -> tuple[pd.Series, Optional[float], Optional[float]]:
        """Generate combined exit signals from sell_conditions and time-based exits.
        
        Args:
            entry_signals: Boolean series of entry signals
            price_data: DataFrame with OHLCV data
            sell_conditions: List of RuleDef objects for exit conditions
            
        Returns:
            Tuple of (exit_signals, sl_stop, tp_stop)
        """
        # Initialize return values
        sl_stop = None
        tp_stop = None
        exit_signals_list = []
        
        # Process sell_conditions
        if sell_conditions:
            for rule_def in sell_conditions:
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
