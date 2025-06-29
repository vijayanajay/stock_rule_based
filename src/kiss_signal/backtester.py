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

        if edge_score_weights is None:
            edge_score_weights = {'win_pct': 0.6, 'sharpe': 0.4}
        
        logger.info(f"Backtesting {len(combinations_to_test)} rule combinations for {symbol}")
        strategies = []
        
        for i, combo in enumerate(combinations_to_test):
            try:
                # Generate combined signal for the rule combination
                entry_signals = pd.Series(True, index=price_data.index)
                for rule_def in combo:
                    entry_signals &= self._generate_signals(rule_def, price_data)
                
                # Generate time-based exit signals: exit after hold_period days
                exit_signals = self._generate_time_based_exits(entry_signals, self.hold_period)
                portfolio = vbt.Portfolio.from_signals(
                    close=price_data['close'],
                    entries=entry_signals,
                    exits=exit_signals,
                    fees=0.001,
                    slippage=0.0005,
                    init_cash=self.initial_capital,
                    size=np.inf,
                )
                total_trades = portfolio.trades.count()
                
                rule_names = " + ".join([r.name for r in combo])
                if total_trades < self.min_trades_threshold:
                    logger.warning(f"Strategy '{rule_names}' on '{symbol}' generated only {total_trades} trades, which is below the threshold of {self.min_trades_threshold}.")
                    continue

                if total_trades > 0:
                    win_pct = portfolio.trades.win_rate() / 100.0
                    sharpe = portfolio.sharpe_ratio()
                    avg_return = portfolio.trades.pnl.mean() / 100.0 if not np.isnan(portfolio.trades.pnl.mean()) else 0.0
                else:
                    win_pct = 0.0
                    sharpe = 0.0
                    avg_return = 0.0
                edge_score = (win_pct * edge_score_weights['win_pct']) + (sharpe * edge_score_weights['sharpe'])
                strategy = {
                    'rule_stack': combo,  # Persist the entire rule combination
                    'edge_score': edge_score,
                    'win_pct': win_pct,
                    'sharpe': sharpe,
                    'total_trades': total_trades,
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
        # Handle both RuleDef objects and dictionaries for backward compatibility
        if hasattr(rule_def, 'type'):
            # RuleDef object
            rule_type = rule_def.type
            rule_params = rule_def.params
        else:
            # Dictionary format (legacy)
            rule_type = rule_def.get('type')
            rule_params = rule_def.get('params', {})
        
        if not rule_type:
            raise ValueError(f"Rule definition missing 'type' field: {rule_def}")

        rule_func = getattr(rules, rule_type, None)
        if rule_func is None:
            raise ValueError(f"Rule function '{rule_type}' not found in rules module")

        if not rule_params:
            raise ValueError(f"Missing parameters for rule '{rule_type}'")

        try:
            # Call the actual rule function from the rules module
            entry_signals = rule_func(price_data, **rule_params)
        except Exception as e:
            logger.error(f"Error executing rule '{rule_type}' with params {rule_params}: {e}")
            raise ValueError(f"Rule '{rule_type}' failed execution") from e

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Generated {entry_signals.sum()} entry signals for rule '{rule_type}'")

        return entry_signals
