"""Backtester - vectorbt-based Strategy Backtesting Module.

This module handles backtesting of rule combinations and edge score calculation.
"""

import logging
from datetime import date
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
import vectorbt as vbt

from . import rules

logger = logging.getLogger(__name__)


class Backtester:
    """Handles strategy backtesting and edge score calculation."""
    
    def __init__(self, hold_period: int = 20, min_trades_threshold: int = 10):
        """Initialize the backtester.
        
        Args:
            hold_period: Days to hold positions (time-based exit)
            min_trades_threshold: Minimum trades required for valid backtest
        """
        self.hold_period = hold_period
        self.min_trades_threshold = min_trades_threshold
        logger.info(f"Backtester initialized: hold_period={hold_period}, min_trades={min_trades_threshold}")
    
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
            try:
                logger.debug(f"Processing rule combination {i+1}/{len(rule_combinations)}: {rule_combo['rule_stack']}")
                
                # Generate signals
                entry_signals, exit_signals = self._generate_signals(rule_combo, price_data)
                
                # Create portfolio
                portfolio = self._create_portfolio(entry_signals, exit_signals, price_data)
                
                # Calculate metrics
                total_trades = self._calculate_total_trades(portfolio)
                
                # Skip strategies with insufficient trades
                if total_trades < self.min_trades_threshold:
                    logger.debug(f"Skipping strategy with {total_trades} trades (< {self.min_trades_threshold})")
                    continue
                
                win_pct = self._calculate_win_percentage(portfolio)
                sharpe = self._calculate_sharpe_ratio(portfolio)
                avg_return = self._calculate_average_return(portfolio)
                
                # Calculate edge score
                edge_score = self.calc_edge_score(win_pct, sharpe, edge_score_weights)
                
                strategy = {
                    'rule_stack': rule_combo['rule_stack'].copy(),
                    'parameters': rule_combo.get('parameters', {}).copy(),
                    'edge_score': edge_score,
                    'win_pct': win_pct,
                    'sharpe': sharpe,
                    'total_trades': total_trades,
                    'avg_return': avg_return
                }
                
                strategies.append(strategy)
                logger.debug(f"Strategy added: edge_score={edge_score:.4f}, win_pct={win_pct:.3f}, sharpe={sharpe:.3f}")
                
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
        logger.debug(f"Edge score calculated: {edge_score:.4f} (win_pct={win_pct:.3f}, sharpe={sharpe:.3f})")
        return edge_score

    def _generate_signals(self, rule_combo: Dict[str, Any], price_data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Generate entry and exit signals for a rule combination.
        
        Args:
            rule_combo: Rule combination configuration with rule_stack and parameters
            price_data: OHLCV price data
            
        Returns:
            Tuple of (entry_signals, exit_signals) as boolean Series
            
        Raises:
            ValueError: If rule combination is invalid or rule not found
        """
        rule_stack = rule_combo.get('rule_stack', [])
        parameters = rule_combo.get('parameters', {})
        
        if not rule_stack:
            raise ValueError("Rule combination must have non-empty rule_stack")
        
        logger.debug(f"Generating signals for rule stack: {rule_stack}")
        
        # Initialize entry signals (start with all False)
        entry_signals = pd.Series(False, index=price_data.index)
        
        # Process each rule in the stack
        for rule_name in rule_stack:
            if rule_name == 'baseline':
                # Baseline rule: always True (no additional filtering)
                rule_signals = pd.Series(True, index=price_data.index)
            else:
                # Get rule function and parameters
                rule_func = getattr(rules, rule_name, None)
                if rule_func is None:
                    raise ValueError(f"Rule function '{rule_name}' not found in rules module")
                
                rule_params = parameters.get(rule_name, {})
                
                # Check if rule parameters are provided for non-baseline rules
                if not rule_params:
                    raise ValueError(f"Missing parameters for rule '{rule_name}'")
                
                try:
                    rule_signals = rule_func(price_data, **rule_params)
                except Exception as e:
                    logger.error(f"Error executing rule '{rule_name}': {e}")
                    raise ValueError(f"Rule '{rule_name}' failed: {e}") from e
            
            # Combine signals (AND logic for rule stack)
            if rule_name == 'baseline':
                entry_signals = rule_signals
            else:
                entry_signals = entry_signals & rule_signals
        
        # Generate exit signals (time-based)
        exit_signals = self._generate_exit_signals(entry_signals, price_data)
        
        logger.debug(f"Generated {entry_signals.sum()} entry signals, {exit_signals.sum()} exit signals")
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
          # Create portfolio with basic settings
        portfolio = vbt.Portfolio.from_signals(
            close=close_prices,
            entries=entry_signals,
            exits=exit_signals,
            freq='D',  # Daily frequency            fees=0.001,  # 0.1% transaction fee (realistic for Indian markets)
            slippage=0.0005,  # 0.05% slippage
            init_cash=100000,  # 1 lakh initial capital
            size=np.inf  # Use all available cash for each trade (buy as many shares as possible)
        )
        
        logger.debug(f"Portfolio created with {len(portfolio.trades.records_readable)} trades")
        return portfolio

    def _calculate_win_percentage(self, portfolio: 'vbt.Portfolio') -> float:
        """Calculate win percentage from portfolio trades.
        
        Args:
            portfolio: Vectorbt Portfolio object
            
        Returns:
            Win percentage as float (0.0 to 1.0)
        """
        trades = portfolio.trades.records_readable
        if len(trades) == 0:
            return 0.0
        
        winning_trades = (trades['PnL'] > 0).sum()
        total_trades = len(trades)
        win_pct = winning_trades / total_trades
        
        logger.debug(f"Win percentage: {win_pct:.3f} ({winning_trades}/{total_trades})")
        return win_pct

    def _calculate_sharpe_ratio(self, portfolio: 'vbt.Portfolio', risk_free_rate: float = 0.05) -> float:
        """Calculate Sharpe ratio from portfolio returns.
        
        Args:
            portfolio: Vectorbt Portfolio object
            risk_free_rate: Annual risk-free rate (default 5%)
            
        Returns:
            Sharpe ratio as float
        """
        returns = portfolio.returns()
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        # Convert to annual figures
        annual_return = returns.mean() * 252  # 252 trading days
        annual_volatility = returns.std() * (252 ** 0.5)
        
        if annual_volatility == 0:
            return 0.0
        
        sharpe = (annual_return - risk_free_rate) / annual_volatility
        logger.debug(f"Sharpe ratio: {sharpe:.3f} (annual_return={annual_return:.3f}, volatility={annual_volatility:.3f})")
        return sharpe

    def _calculate_total_trades(self, portfolio: 'vbt.Portfolio') -> int:
        """Calculate total number of trades.
        
        Args:
            portfolio: Vectorbt Portfolio object
            
        Returns:
            Number of trades as integer
        """
        trades = portfolio.trades.records_readable
        total_trades = len(trades)
        logger.debug(f"Total trades: {total_trades}")
        return total_trades

    def _calculate_average_return(self, portfolio: 'vbt.Portfolio') -> float:
        """Calculate average return per trade.
        
        Args:
            portfolio: Vectorbt Portfolio object
            
        Returns:
            Average return per trade as float
        """
        trades = portfolio.trades.records_readable
        if len(trades) == 0:
            return 0.0
        
        # Calculate return percentage for each trade
        avg_return = (trades['Return'] / 100).mean()  # Convert from percentage
        logger.debug(f"Average return per trade: {avg_return:.4f}")
        return avg_return
