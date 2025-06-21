"""Backtester - vectorbt-based Strategy Backtesting Module.

This module handles backtesting of rule combinations and edge score calculation.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

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
                entry_signals, exit_signals = self._generate_signals(rule_combo, price_data)
                
                # Create portfolio
                portfolio = self._create_portfolio(entry_signals, exit_signals, price_data)
                
                # Calculate metrics
                total_trades = portfolio.trades.count()
                  # Skip strategies with insufficient trades
                if total_trades < self.min_trades_threshold:
                    logger.debug(f"Skipping strategy with {total_trades} trades (< {self.min_trades_threshold})")
                    continue
                
                # Calculate win rate manually from trades
                if total_trades > 0:
                    trades_df = portfolio.trades.records_readable
                    win_pct = (trades_df['Return'] > 0).mean()
                    avg_return = trades_df['Return'].mean()
                else:
                    win_pct = 0.0
                    avg_return = 0.0
                
                # Calculate Sharpe ratio from portfolio stats
                try:
                    sharpe = portfolio.stats()['Sharpe Ratio']
                except (KeyError, AttributeError):
                    # Fallback calculation if stats method doesn't work
                    returns = portfolio.total_return()
                    if isinstance(returns, (int, float)) and returns != 0:
                        sharpe = returns / abs(returns) if abs(returns) > 0 else 0.0
                    else:
                        sharpe = 0.0
                  # Calculate edge score
                edge_score = self.calc_edge_score(win_pct, sharpe, edge_score_weights)
                
                # Build strategy result, handling both old and new formats
                if 'rule_stack' in rule_combo:
                    # Old format
                    strategy = {
                        'rule_stack': rule_combo['rule_stack'].copy(),
                        'parameters': rule_combo.get('parameters', {}).copy(),
                        'edge_score': edge_score,
                        'win_pct': win_pct,
                        'sharpe': sharpe,
                        'total_trades': total_trades,
                        'avg_return': avg_return
                    }
                else:
                    # New format (rules.yaml)
                    strategy = {
                        'rule_stack': [rule_combo.get('name', rule_combo['type'])],
                        'parameters': {rule_combo['type']: rule_combo.get('params', {})},
                        'edge_score': edge_score,
                        'win_pct': win_pct,
                        'sharpe': sharpe,
                        'total_trades': total_trades,
                        'avg_return': avg_return,
                        'name': rule_combo.get('name', 'unnamed_rule'),
                        'description': rule_combo.get('description', '')
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

    def _generate_signals(self, rule_combo: Dict[str, Any], price_data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Generate entry and exit signals for a rule combination.
        
        Args:
            rule_combo: Rule combination configuration (from rules.yaml format)
            price_data: OHLCV price data
            
        Returns:
            Tuple of (entry_signals, exit_signals) as boolean Series
            
        Raises:
            ValueError: If rule combination is invalid or rule not found
        """
        # Handle both old and new rule formats
        if 'rule_stack' in rule_combo:
            # Old format: {'rule_stack': ['rule_name'], 'parameters': {...}}
            rule_stack = rule_combo.get('rule_stack', [])
            parameters = rule_combo.get('parameters', {})
        else:
            # New format: {'type': 'rule_name', 'params': {...}}
            rule_type = rule_combo.get('type')
            if not rule_type:
                raise ValueError(f"Rule combination missing 'type' field: {rule_combo}")
            rule_stack = [rule_type]
            parameters = {rule_type: rule_combo.get('params', {})}
        
        # Only log for complex rule stacks (more than 1 rule)
        if len(rule_stack) > 1:
            logger.debug(f"Generating signals for rule stack: {rule_stack}")
        
        # Initialize entry signals (start with all True for AND logic)
        entry_signals = pd.Series(True, index=price_data.index)
        
        # Process each rule in the stack
        for rule_name in rule_stack:
            # Get rule function and parameters
            rule_func = getattr(rules, rule_name, None)
            if rule_func is None:
                raise ValueError(f"Rule function '{rule_name}' not found in rules module")
            
            rule_params = parameters.get(rule_name, {})
            
            # Check if rule parameters are provided for non-baseline rules
            if not rule_params:
                raise ValueError(f"Missing parameters for rule '{rule_name}'")

            try:
                # Call the actual rule function from the rules module
                rule_signals = rule_func(price_data, **rule_params)
            except Exception as e:
                logger.error(f"Error executing rule '{rule_name}' with params {rule_params}: {e}")
                raise ValueError(f"Rule '{rule_name}' failed execution") from e

            # Combine signals (AND logic for rule stack)
            entry_signals = entry_signals & rule_signals
        
        # Generate exit signals (time-based)
        exit_signals = self._generate_exit_signals(entry_signals, price_data)
        
        # Debug: Check signal counts
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Final entry signals: {entry_signals.sum()}, exit signals: {exit_signals.sum()}")
            if entry_signals.sum() > 0:
                logger.debug(f"Entry signal dates: {entry_signals[entry_signals].index[:5].tolist()}")
        
        return entry_signals, exit_signals

    def _generate_exit_signals(self, entry_signals: pd.Series, price_data: pd.DataFrame) -> pd.Series:
        """Generate time-based exit signals.
        
        Args:
            entry_signals: Boolean series indicating entry points
            price_data: OHLCV price data
            
        Returns:
            Boolean series indicating exit points
        """
        exit_signals = pd.Series(False, index=price_data.index)
        
        # For each entry signal, create exit signal after hold_period days
        entry_dates = entry_signals[entry_signals].index
        
        for entry_date in entry_dates:
            try:
                # Calculate exit date (hold_period days later)
                exit_date = entry_date + pd.Timedelta(days=self.hold_period)
                
                # Find the next available trading date on or after exit_date
                available_dates = price_data.index[price_data.index >= exit_date]
                if len(available_dates) > 0:
                    actual_exit_date = available_dates[0]
                    exit_signals.loc[actual_exit_date] = True
                    
            except (KeyError, IndexError):
                # Exit date beyond available data - skip this trade                
                continue        
        return exit_signals

    def _create_portfolio(self, entry_signals: pd.Series, exit_signals: pd.Series, 
                         price_data: pd.DataFrame) -> 'vbt.Portfolio':
        """Create vectorbt portfolio from entry/exit signals.
        
        Args:
            entry_signals: Boolean series indicating entry points
            exit_signals: Boolean series indicating exit points
            price_data: OHLCV price data
            
        Returns:
            Vectorbt Portfolio object with simulation results
        """
        logger.debug(f"Creating portfolio with {entry_signals.sum()} entries, {exit_signals.sum()} exits")
        
        # Use close prices for simulation
        close_prices = price_data['close']
        
        # Debug: Check data alignment
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Price data shape: {price_data.shape}, close prices shape: {close_prices.shape}")
            logger.debug(f"Entry signals shape: {entry_signals.shape}, Exit signals shape: {exit_signals.shape}")
            logger.debug(f"Index types - Price: {type(price_data.index[0])}, Entry: {type(entry_signals.index[0])}")
        
        # Create portfolio with basic settings
        portfolio = vbt.Portfolio.from_signals(
            close=close_prices,
            entries=entry_signals,
            exits=exit_signals,
            freq='D',  # Daily frequency
            fees=0.001,  # 0.1% transaction fee (realistic for Indian markets)
            slippage=0.0005,  # 0.05% slippage
            init_cash=100000,  # 1 lakh initial capital
            size=np.inf  # Use all available cash for each trade (buy as many shares as possible)
        )
        
        return portfolio
