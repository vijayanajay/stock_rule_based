"""Backtester - vectorbt-based Strategy Backtesting Module.

This module handles backtesting of rule combinations and edge score calculation.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import vectorbt as vbt

from . import rules

__all__ = ["Backtester"]

logger = logging.getLogger(__name__)


class Backtester:
    """Handles strategy backtesting and edge score calculation."""

    def __init__(self, hold_period: int = 20, min_trades_threshold: int = 10) -> None:
        """Initialize the backtester."""
        self.hold_period = hold_period
        self.min_trades_threshold = min_trades_threshold
        logger.info(
            f"Backtester initialized: hold_period={hold_period}, "
            f"min_trades={min_trades_threshold}"
        )
    
    def find_optimal_strategies(
        self, 
        rules_config: Dict[str, Any], 
        price_data: pd.DataFrame,
        symbol: str,
        freeze_date: Optional[date] = None,
        edge_score_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Find optimal rule combinations through backtesting.
        
        Args:
            rules_config: Dictionary with 'baseline' and 'layers' rule configs
            price_data: OHLCV price data for backtesting
            symbol: The stock symbol being tested, for logging purposes.
            freeze_date: Optional cutoff date for data (for deterministic testing)
            edge_score_weights: Optional custom weights for edge score calculation
            
        Returns:
            List of strategies with edge scores and performance metrics, ranked by edge score
        """
        baseline_rule = rules_config.get('baseline')
        layers = rules_config.get('layers', [])

        if not baseline_rule:
            logger.warning("No baseline rule found in configuration for %s.", symbol)
            return []

        # Create combinations to test: baseline alone, and baseline + each layer
        combinations_to_test = [[baseline_rule]] + [[baseline_rule, layer] for layer in layers]

        if freeze_date:
            # Filter data up to freeze_date for deterministic testing
            price_data = price_data[price_data.index.date <= freeze_date]
            logger.info(f"Using data up to freeze date: {freeze_date}")
        
        # VectorBT can work without explicit frequency, so let's skip frequency setting
        # to avoid complex resampling issues
        logger.debug("Skipping frequency setting for VectorBT compatibility")
        
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
                    init_cash=100000,
                    size=np.inf,
                    freq='D'  # Explicitly set frequency for VectorBT
                )
                total_trades = portfolio.trades.count()
                
                rule_names = " + ".join([r.get('name', r.get('type', '')) for r in combo])
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
        # Create exit signals: exit after hold_period days from each entry
        exit_signals = pd.Series(False, index=entry_signals.index)
        
        # For each entry signal, set exit signal hold_period days later
        entry_dates = entry_signals[entry_signals].index
        for entry_date in entry_dates:
            # Find the exit date (hold_period days after entry)
            entry_idx = entry_signals.index.get_loc(entry_date)
            exit_idx = entry_idx + hold_period
            
            # Ensure we don't go beyond the data bounds
            if exit_idx < len(entry_signals):
                exit_date = entry_signals.index[exit_idx]
                exit_signals.loc[exit_date] = True
        
        return exit_signals

    def _generate_signals(self, rule_combo: Dict[str, Any], price_data: pd.DataFrame) -> pd.Series:
        """
        Generates entry signals for a given rule combination.
        Raises:
            ValueError: If rule combination is invalid or rule not found
        """
        rule_type = rule_combo.get('type')
        if not rule_type:
            raise ValueError(f"Rule combination missing 'type' field: {rule_combo}")

        rule_func = getattr(rules, rule_type, None)
        if rule_func is None:
            raise ValueError(f"Rule function '{rule_type}' not found in rules module")

        rule_params = rule_combo.get('params', {})
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
