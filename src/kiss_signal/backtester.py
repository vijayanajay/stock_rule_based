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
from .performance import performance_monitor
from .cache import global_cache, cached

__all__ = ["Backtester"]

logger = logging.getLogger(__name__)

class StrategyValidationResult:
    """Result of strategy validation checks."""
    is_valid: bool
    reason: str
    confidence_score: float
    metrics: Dict[str, float]

class Backtester:
    """Handles strategy backtesting and edge score calculation."""

    def __init__(
        self,
        hold_period: int = 20,
        min_trades_threshold: int = 10,
        # Enhanced validation parameters
        min_win_rate: float = 0.55,
        max_drawdown: float = 0.15,
        min_trades: int = 10,
        min_profit_factor: float = 1.2,
        volatility_threshold: float = 0.25,
    ) -> None:
        """Initialize the backtester."""
        self.hold_period = hold_period
        self.min_trades_threshold = min_trades_threshold
        self.min_win_rate = min_win_rate
        self.max_drawdown = max_drawdown
        self.min_trades = min_trades
        self.min_profit_factor = min_profit_factor
        self.volatility_threshold = volatility_threshold
        
        # Performance tracking
        self.validation_cache: Dict[str, StrategyValidationResult] = {}
    
        logger.info(
            f"Backtester initialized: hold_period={hold_period}, "
            f"min_trades={min_trades_threshold}"
        )
    
    @performance_monitor.profile_performance
    @cached(global_cache, ttl_hours=6)
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

    def _validate_and_rank_strategies(self, strategies: List[Dict]) -> List[Dict]:
        """Enhanced strategy validation and ranking."""
        validated_strategies = []
        
        for strategy in strategies:
            validation_result = self._validate_strategy_comprehensive(strategy)
            
            if validation_result.is_valid:
                # Add confidence score and enhanced metrics
                strategy['confidence_score'] = validation_result.confidence_score
                strategy['validation_metrics'] = validation_result.metrics
                validated_strategies.append(strategy)
            else:
                logger.debug(f"Strategy rejected: {validation_result.reason}")
        
        # Sort by composite score (edge_score * confidence_score)
        validated_strategies.sort(
            key=lambda s: s['edge_score'] * s['confidence_score'], 
            reverse=True
        )
        
        return validated_strategies

    def _validate_strategy_comprehensive(self, strategy: Dict) -> StrategyValidationResult:
        """Comprehensive strategy validation with multiple criteria."""
        portfolio = strategy.get('portfolio')
        if not portfolio:
            return StrategyValidationResult(False, "No portfolio data", 0.0, {})
        
        try:
            # Basic metrics
            trades = portfolio.trades
            stats = portfolio.stats()
            
            # Extract key metrics
            total_trades = len(trades.records_readable)
            if total_trades < self.min_trades:
                return StrategyValidationResult(
                    False, f"Insufficient trades: {total_trades} < {self.min_trades}", 0.0, {}
                )
            
            win_rate = trades.win_rate() / 100.0
            if win_rate < self.min_win_rate:
                return StrategyValidationResult(
                    False, f"Low win rate: {win_rate:.1%} < {self.min_win_rate:.1%}", 0.0, {}
                )
            
            max_dd = portfolio.drawdown().max()
            if max_dd > self.max_drawdown:
                return StrategyValidationResult(
                    False, f"Excessive drawdown: {max_dd:.1%} > {self.max_drawdown:.1%}", 0.0, {}
                )
            
            # Profit factor check
            gross_profit = trades.winning_trades.total_return.sum()
            gross_loss = abs(trades.losing_trades.total_return.sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            if profit_factor < self.min_profit_factor:
                return StrategyValidationResult(
                    False, f"Low profit factor: {profit_factor:.2f} < {self.min_profit_factor}", 0.0, {}
                )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                win_rate, max_dd, profit_factor, total_trades
            )
            
            # Market regime consistency check
            regime_consistency = self._check_market_regime_consistency(portfolio)
            if regime_consistency < 0.7:
                confidence_score *= 0.8  # Reduce confidence for inconsistent performance
            
            validation_metrics = {
                'win_rate': win_rate,
                'max_drawdown': max_dd,
                'profit_factor': profit_factor,
                'total_trades': total_trades,
                'regime_consistency': regime_consistency,
                'sharpe_ratio': stats.get('Sharpe Ratio', 0.0),
            }
            
            return StrategyValidationResult(
                True, "Strategy passed validation", confidence_score, validation_metrics
            )
            
        except Exception as e:
            logger.warning(f"Strategy validation error: {e}")
            return StrategyValidationResult(False, f"Validation error: {e}", 0.0, {})
    
    def _calculate_confidence_score(
        self, win_rate: float, max_dd: float, profit_factor: float, total_trades: int
    ) -> float:
        """Calculate strategy confidence score (0-1)."""
        # Normalize metrics to 0-1 scale
        win_rate_score = min(win_rate / 0.8, 1.0)  # Cap at 80% win rate
        dd_score = max(0, 1 - (max_dd / 0.2))  # Penalize drawdown > 20%
        pf_score = min(profit_factor / 3.0, 1.0)  # Cap at 3.0 profit factor
        trades_score = min(total_trades / 50.0, 1.0)  # Cap at 50 trades
        
        # Weighted average
        confidence = (
            win_rate_score * 0.3 +
            dd_score * 0.3 +
            pf_score * 0.25 +
            trades_score * 0.15
        )
        
        return max(0.0, min(1.0, confidence))
    
    def _check_market_regime_consistency(self, portfolio) -> float:
        """Check strategy performance consistency across market regimes."""
        try:
            # Simple regime detection based on volatility
            returns = portfolio.total_return()
            volatility = returns.rolling(20).std()
            
            # Define regimes: low/high volatility
            vol_median = volatility.median()
            low_vol_mask = volatility <= vol_median
            high_vol_mask = volatility > vol_median
            
            # Calculate performance in each regime
            low_vol_returns = returns[low_vol_mask].mean()
            high_vol_returns = returns[high_vol_mask].mean()
            
            # Consistency score: how similar performance is across regimes
            if low_vol_returns == 0 and high_vol_returns == 0:
                return 0.5  # Neutral
            
            consistency = 1.0 - abs(low_vol_returns - high_vol_returns) / (
                abs(low_vol_returns) + abs(high_vol_returns) + 1e-6
            )
            
            return max(0.0, min(1.0, consistency))
            
        except Exception:
            return 0.5  # Default neutral score
