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
        rule_combinations: List[Dict[str, Any]], 
        price_data: pd.DataFrame,
        freeze_date: Optional[date] = None,
        edge_score_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Find optimal rule combinations through backtesting.
        
        Args:
            rule_combinations: List of rule combination configs to test
            price_data: OHLCV price data for backtesting
            freeze_date: Optional cutoff date for data (for deterministic testing)
            edge_score_weights: Optional custom weights for edge score calculation
            
        Returns:
            List of strategies with edge scores and performance metrics, ranked by edge score
        """
        if not rule_combinations:
            logger.info("No rule combinations provided")
            return []
        
        if freeze_date:
            # Filter data up to freeze_date for deterministic testing
            price_data = price_data[price_data.index.date <= freeze_date]
            logger.info(f"Using data up to freeze date: {freeze_date}")
        
        # Default edge score weights
        if edge_score_weights is None:
            edge_score_weights = {'win_pct': 0.6, 'sharpe': 0.4}
        
        logger.info(f"Backtesting {len(rule_combinations)} rule combinations")
        strategies = []
        
        for i, rule_combo in enumerate(rule_combinations):
            try:                # Only log every 5th strategy to reduce verbosity
                if i % 5 == 0 or i == len(rule_combinations) - 1:
                    rule_name = rule_combo.get('name', rule_combo.get('rule_stack', ['unknown']))
                    logger.debug(f"Processing rule combination {i+1}/{len(rule_combinations)}: {rule_name}")
                  # Generate signals
                entry_signals = self._generate_signals(rule_combo, price_data)
                
                # Generate time-based exit signals: exit after hold_period days
                exit_signals = self._generate_time_based_exits(entry_signals, self.hold_period)

                # Create portfolio using vectorbt's from_signals method
                portfolio = vbt.Portfolio.from_signals(
                    close=price_data['close'],
                    entries=entry_signals,
                    exits=exit_signals,
                    freq='D',
                    fees=0.001,
                    slippage=0.0005,
                    init_cash=100000,
                    size=np.inf
                )                # Calculate metrics
                total_trades = portfolio.trades.count()
                if total_trades < self.min_trades_threshold:
                    logger.debug(f"Skipping strategy with {total_trades} trades (< {self.min_trades_threshold})")
                    continue

                # Use vectorbt's correct methods for metrics
                if total_trades > 0:
                    # Call methods correctly (they are methods, not properties)
                    win_pct = portfolio.trades.win_rate() / 100.0
                    sharpe = portfolio.sharpe_ratio()
                      # Calculate average return from trades
                    try:
                        trades_df = portfolio.trades.records_readable
                        avg_return = trades_df['Return [%]'].mean() / 100.0 if 'Return [%]' in trades_df.columns else 0.0
                    except Exception:
                        avg_return = 0.0
                else:
                    win_pct = 0.0
                    sharpe = 0.0
                    avg_return = 0.0

                # Handle NaN values from vectorbt if stats are not applicable
                win_pct = 0.0 if pd.isna(win_pct) else win_pct
                sharpe = 0.0 if pd.isna(sharpe) else sharpe

                # Calculate edge score
                edge_score = self.calc_edge_score(win_pct, sharpe, edge_score_weights)
                
                # Build strategy result. The rule_stack now contains the full
                # rule definition, making the persisted record self-contained.
                strategy = {
                    'rule_stack': [rule_combo],  # Persist the entire rule definition
                    'edge_score': edge_score,
                    'win_pct': win_pct,
                    'sharpe': sharpe,
                    'total_trades': total_trades,
                    'avg_return': avg_return,
                }
                
                strategies.append(strategy)
                # Only log successful strategies, not each individual one
                
            except Exception as e:
                logger.error(f"Error processing rule combination {rule_combo}: {e}")
                continue
          # Sort strategies by edge score (descending)
        strategies.sort(key=lambda x: x['edge_score'], reverse=True)
        
        logger.info(f"Found {len(strategies)} valid strategies (>= {self.min_trades_threshold} trades)")
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
        """
        Generate exit signals based on holding period after entry signals.
        
        Args:
            entry_signals: Boolean series indicating entry points
            hold_period: Number of days to hold position after entry
            
        Returns:
            Boolean series indicating exit points
        """
        exit_signals = pd.Series(False, index=entry_signals.index)
        
        # Get entry dates
        entry_dates = entry_signals[entry_signals].index
        
        for entry_date in entry_dates:
            # Calculate exit date (hold_period days after entry)
            entry_pos = entry_signals.index.get_loc(entry_date)
            exit_pos = min(entry_pos + hold_period, len(entry_signals) - 1)
            exit_date = entry_signals.index[exit_pos]
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
