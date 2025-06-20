"""Signal Generator - Rule-based Trading Signal Generation.

This module generates buy signals based on rule combinations and manages signal timing.
"""

import logging
from typing import Dict, List, Any, Optional

import pandas as pd

from .rules import sma_crossover, rsi_oversold, ema_crossover

__all__ = ["SignalGenerator"]

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generates trading signals based on rule combinations."""
    
    def __init__(self, rules_config: Dict[str, Any], hold_period: int = 20) -> None:
        """Initialize the signal generator.
        
        Args:
            rules_config: Rules configuration from rules.yaml
            hold_period: Days to hold positions (time-based exit)
        """
        self.rules_config = rules_config
        self.hold_period = hold_period
        logger.info(f"SignalGenerator initialized with {len(rules_config.get('rules', []))} rules, hold_period={hold_period}")
    
    def generate_signals(self, symbol: str, price_data: pd.DataFrame, 
                        rule_stack: List[str]) -> pd.DataFrame:
        """Generate buy/sell signals using rule stack.
        
        Args:
            symbol: NSE symbol to generate signals for
            price_data: OHLCV price data with DateTimeIndex
            rule_stack: List of rule names to combine
            
        Returns:
            DataFrame with columns: [timestamp, signal_type, symbol, 
                                   rule_stack, metadata]
                                   
        Raises:
            ValueError: If price_data doesn't have DateTimeIndex or required columns
        """
        logger.info(f"Generating signals for {symbol} using rules: {rule_stack}")
        
        # Validate inputs
        if not isinstance(price_data.index, pd.DatetimeIndex):
            raise ValueError("price_data must have DateTimeIndex")
        
        required_columns = {'open', 'high', 'low', 'close', 'volume'}
        if not required_columns.issubset(price_data.columns):
            raise ValueError(f"price_data must have columns: {required_columns}")
        
        # Handle empty rule stack gracefully
        if not rule_stack:
            logger.warning(f"Empty rule stack for {symbol}, returning empty signals")
            return self._create_empty_signals_dataframe()
        
        try:
            # Evaluate all rules in the stack
            rule_results = []
            for rule_name in rule_stack:
                try:
                    rule_signal = self.evaluate_rule(rule_name, price_data)
                    rule_results.append(rule_signal)
                except Exception as e:
                    logger.warning(f"Rule {rule_name} evaluation failed for {symbol}: {e}")
                    # Continue with other rules instead of failing completely
                    continue
            
            if not rule_results:
                logger.warning(f"No valid rules evaluated for {symbol}")
                return self._create_empty_signals_dataframe()
            
            # Combine rules using AND logic (all must trigger for buy signal)
            combined_signals = rule_results[0]
            for rule_signal in rule_results[1:]:
                combined_signals = combined_signals & rule_signal
            
            # Generate buy signals
            buy_signals = []
            buy_timestamps = combined_signals[combined_signals].index
            
            for timestamp in buy_timestamps:
                signal = {
                    'timestamp': timestamp,
                    'signal_type': 'BUY',
                    'symbol': symbol,
                    'rule_stack': rule_stack.copy(),  # Avoid reference sharing
                    'metadata': {
                        'signal_strength': len(rule_results),  # Number of rules that triggered
                        'price_at_signal': float(price_data.loc[timestamp, 'close']),
                        'hold_period': self.hold_period
                    }
                }
                buy_signals.append(signal)
            
            # Generate time-based sell signals
            sell_signals = self._generate_sell_signals(buy_signals, price_data)
            
            # Combine and create DataFrame
            all_signals = buy_signals + sell_signals
            if not all_signals:
                return self._create_empty_signals_dataframe()
            
            signals_df = pd.DataFrame(all_signals)
            signals_df = signals_df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Generated {len(buy_signals)} buy and {len(sell_signals)} sell signals for {symbol}")
            return signals_df
            
        except Exception as e:
            logger.error(f"Signal generation failed for {symbol}: {e}")
            # Don't let individual symbol failures crash the system
            return self._create_empty_signals_dataframe()
    
    def _create_empty_signals_dataframe(self) -> pd.DataFrame:
        """Create empty signals DataFrame with proper schema."""
        return pd.DataFrame(columns=['timestamp', 'signal_type', 'symbol', 'rule_stack', 'metadata'])
    
    def _generate_sell_signals(self, buy_signals: List[Dict[str, Any]], price_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate time-based sell signals after hold period.
        
        Args:
            buy_signals: List of buy signal dictionaries
            price_data: OHLCV price data for calculating exit prices
            
        Returns:
            List of sell signal dictionaries
        """
        sell_signals = []
        
        for buy_signal in buy_signals:
            buy_timestamp = buy_signal['timestamp']
            symbol = buy_signal['symbol']
            
            # Calculate exit date (hold_period business days later)
            exit_date = self._calculate_exit_date(buy_timestamp, price_data.index)
            
            if exit_date is not None and exit_date in price_data.index:
                sell_signal = {
                    'timestamp': exit_date,
                    'signal_type': 'SELL',
                    'symbol': symbol,
                    'rule_stack': buy_signal['rule_stack'],
                    'metadata': {
                        'exit_reason': 'time_based',
                        'buy_timestamp': buy_timestamp,
                        'hold_period': self.hold_period,
                        'buy_price': buy_signal['metadata']['price_at_signal'],
                        'sell_price': float(price_data.loc[exit_date, 'close'])
                    }
                }
                sell_signals.append(sell_signal)
            else:
                logger.debug(f"No exit date found for buy signal at {buy_timestamp}")
        
        return sell_signals
    
    def _calculate_exit_date(self, buy_date: pd.Timestamp, price_index: pd.DatetimeIndex) -> Optional[pd.Timestamp]:
        """Calculate exit date for a buy signal.
        
        Args:
            buy_date: Date of buy signal
            price_index: Available dates in price data
            
        Returns:
            Exit date or None if not found
        """
        # Find available dates after buy_date
        future_dates = price_index[price_index > buy_date]
        
        if len(future_dates) >= self.hold_period:
            return future_dates[self.hold_period - 1]  # 0-indexed
        
        # If not enough future data, return the last available date
        if len(future_dates) > 0:
            logger.debug("Insufficient future data, using last available date")
            return future_dates[-1]
        
        return None

    def evaluate_rule(self, rule_name: str, price_data: pd.DataFrame) -> pd.Series:
        """Evaluate single rule against price data.
        
        Args:
            rule_name: Name of rule to evaluate
            price_data: OHLCV price data
            
        Returns:
            Boolean series indicating rule trigger points
            
        Raises:
            ValueError: If rule not found or unknown rule type
        """
        logger.debug(f"Evaluating rule: {rule_name}")
        
        # Find rule configuration
        rule_config = None
        for rule in self.rules_config.get('rules', []):
            if rule['name'] == rule_name:
                rule_config = rule
                break
        
        if not rule_config:
            raise ValueError(f"Rule not found: {rule_name}")
        
        rule_type = rule_config['type']
        rule_params = rule_config.get('params', {})
        
        # Rule function lookup with error handling
        rule_functions = {
            'sma_crossover': sma_crossover,
            'rsi_oversold': rsi_oversold,
            'ema_crossover': ema_crossover,
        }
        
        if rule_type not in rule_functions:
            raise ValueError(f"Unknown rule type: {rule_type}")
        
        try:
            rule_function = rule_functions[rule_type]
            
            # Rule functions assume lowercase columns, which is a system-wide contract.
            signals = rule_function(price_data, **rule_params)
            
            logger.debug(f"Rule {rule_name} generated {signals.sum()} signals")
            return signals
            
        except Exception as e:
            logger.warning(f"Rule function {rule_type} failed: {e}")
            # Return empty series on failure instead of crashing
            return pd.Series(False, index=price_data.index)
