"""Backtester - vectorbt-based Strategy Backtesting Module.

This module handles backtesting of rule combinations and edge score calculation.
"""

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd
import vectorbt as vbt

from . import rules
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
        rules_config: Dict[str, Any], 
        price_data: pd.DataFrame, 
        symbol: str = "",  # Added symbol for logging
        freeze_date: Any = None,  # Accept date or None
        edge_score_weights: Dict[str, float] = None,
        **kwargs: Any
    ) -> Any:
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

        if freeze_date is not None:
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
                    init_cash=self.initial_capital,
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
        return entry_signals.vbt.fshift(hold_period)

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

    def calculate_portfolio_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate comprehensive portfolio metrics.
        
        Refactored for H-9 compliance (was 48 lines, now split).
        """
        if returns.empty:
            return self._empty_metrics()
        
        basic_metrics = self._calculate_basic_metrics(returns)
        risk_metrics = self._calculate_risk_metrics(returns)
        advanced_metrics = self._calculate_advanced_metrics(returns)
        
        return {**basic_metrics, **risk_metrics, **advanced_metrics}
    
    def _calculate_basic_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate basic performance metrics."""
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        volatility = returns.std() * np.sqrt(252)
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility
        }
    
    def _calculate_risk_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate risk-related metrics."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        return {
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        }
    
    def _calculate_advanced_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate advanced performance metrics."""
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        
        win_rate = len(positive_returns) / len(returns) if len(returns) > 0 else 0
        avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0
        avg_loss = negative_returns.mean() if len(negative_returns) > 0 else 0
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
    
    def _empty_metrics(self) -> Dict[str, float]:
        """Return empty metrics for invalid inputs."""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0
        }
