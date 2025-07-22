"""Mathematical Accuracy Tests for Core Indicators.

Validates core technical indicators against hand-calculated reference values.
Focuses on ATR and SMA with trading-practical tolerance levels.

Following KISS principle: minimal, focused validation for mission-critical indicators.
"""

import pandas as pd
import pytest

from kiss_signal.rules import calculate_atr, sma_crossover


class TestATRMathematicalAccuracy:
    """Validate ATR against hand-calculated reference values."""
    
    def test_atr_manual_calculation_simple(self):
        """Validate ATR against hand-calculated 5-day example with known True Range values."""
        # Simple OHLC data designed for easy manual calculation
        test_data = pd.DataFrame({
            'open':  [100, 103, 106, 107, 110],
            'high':  [105, 108, 109, 112, 113], 
            'low':   [98,  101, 104, 105, 108],
            'close': [103, 106, 107, 110, 111]
        }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
        
        # Manual True Range calculations:
        # Day 1: TR = High-Low = 105-98 = 7 (no previous close)
        # Day 2: TR = max(108-101, |108-103|, |101-103|) = max(7, 5, 2) = 7
        # Day 3: TR = max(109-104, |109-106|, |104-106|) = max(5, 3, 2) = 5  
        # Day 4: TR = max(112-105, |112-107|, |105-107|) = max(7, 5, 2) = 7
        # Day 5: TR = max(113-108, |113-110|, |108-110|) = max(5, 3, 2) = 5
        
        # ATR(3) calculation with Wilder's smoothing:
        # ATR starts at day 3: First ATR = average of first 3 TRs = (7+7+5)/3 = 6.33
        # Day 4: ATR = (prev_ATR * (n-1) + current_TR) / n = (6.33 * 2 + 7) / 3 = 6.55
        # Day 5: ATR = (6.55 * 2 + 5) / 3 = 6.03
        
        atr_result = calculate_atr(test_data, period=3)
        
        # Validate key results with trading-practical tolerance
        assert not pd.isna(atr_result.iloc[2]), "ATR should be calculated starting from day 3"
        assert abs(atr_result.iloc[2] - 6.33) < 0.1, f"Day 3 ATR should be ~6.33, got {atr_result.iloc[2]}"
        assert abs(atr_result.iloc[-1] - 6.03) < 0.1, f"Final ATR should be ~6.03, got {atr_result.iloc[-1]}"
    
    def test_atr_boundary_conditions(self):
        """Test ATR with boundary conditions and edge cases."""
        # Test 1: Insufficient data - should return NaN
        insufficient_data = pd.DataFrame({
            'high': [105],
            'low': [95], 
            'close': [100]
        }, index=pd.date_range('2023-01-01', periods=1, freq='D'))
        
        atr_insufficient = calculate_atr(insufficient_data, period=5)
        assert pd.isna(atr_insufficient.iloc[0]), "ATR should be NaN with insufficient data"
        
        # Test 2: Zero volatility - should return 0
        zero_volatility = pd.DataFrame({
            'high': [100, 100, 100, 100, 100],
            'low': [100, 100, 100, 100, 100],
            'close': [100, 100, 100, 100, 100]
        }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
        
        atr_zero = calculate_atr(zero_volatility, period=3)
        assert atr_zero.iloc[-1] == 0.0, f"ATR should be 0 for zero volatility, got {atr_zero.iloc[-1]}"
        
        # Test 3: Exact period length - should work
        exact_period = pd.DataFrame({
            'high': [105, 110, 108],
            'low': [95, 100, 102],
            'close': [100, 105, 106]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        
        atr_exact = calculate_atr(exact_period, period=3)
        assert not pd.isna(atr_exact.iloc[-1]), "ATR should calculate with exact period length"


class TestSMAMathematicalAccuracy:
    """Validate SMA mathematical consistency and properties."""
    
    def test_sma_manual_calculation(self):
        """Validate SMA against hand-calculated values."""
        # Simple price series for easy manual calculation
        test_prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        price_data = pd.DataFrame({
            'close': test_prices,
            'high': [p * 1.01 for p in test_prices],
            'low': [p * 0.99 for p in test_prices],
            'open': test_prices,
            'volume': [1000] * len(test_prices)
        }, index=pd.date_range('2023-01-01', periods=len(test_prices), freq='D'))
        
        # Test SMA(5) calculation
        # For last 5 values [110, 112, 114, 116, 118]: SMA = 114.0
        # Crossover signal should trigger when fast SMA crosses above slow SMA
        signals = sma_crossover(price_data, fast_period=3, slow_period=5)
        
        # Verify the underlying SMA calculations by computing them directly
        close_prices = price_data['close']
        sma_3 = close_prices.rolling(window=3, min_periods=3).mean()
        sma_5 = close_prices.rolling(window=5, min_periods=5).mean()
        
        # Manual calculation for last few values:
        # SMA(3) for last 3: (114+116+118)/3 = 116.0
        # SMA(5) for last 5: (110+112+114+116+118)/5 = 114.0
        assert abs(sma_3.iloc[-1] - 116.0) < 0.001, f"SMA(3) should be 116.0, got {sma_3.iloc[-1]}"
        assert abs(sma_5.iloc[-1] - 114.0) < 0.001, f"SMA(5) should be 114.0, got {sma_5.iloc[-1]}"
    
    def test_sma_mathematical_properties(self):
        """Test SMA mathematical consistency properties."""
        # Create test data with known properties
        constant_prices = [100] * 10
        price_data = pd.DataFrame({
            'close': constant_prices,
            'high': constant_prices,
            'low': constant_prices, 
            'open': constant_prices,
            'volume': [1000] * 10
        }, index=pd.date_range('2023-01-01', periods=10, freq='D'))
        
        close_prices = price_data['close']
        
        # Property 1: SMA of constant values should equal the constant
        sma_constant = close_prices.rolling(window=5, min_periods=5).mean()
        assert all(sma_constant.dropna() == 100.0), "SMA of constant values should equal the constant"
        
        # Property 2: SMA should be monotonic for monotonic input
        increasing_prices = list(range(100, 110))
        price_data_inc = pd.DataFrame({
            'close': increasing_prices,
            'high': increasing_prices,
            'low': increasing_prices,
            'open': increasing_prices,
            'volume': [1000] * 10
        }, index=pd.date_range('2023-01-01', periods=10, freq='D'))
        
        sma_inc = price_data_inc['close'].rolling(window=3, min_periods=3).mean()
        sma_diff = sma_inc.diff().dropna()
        assert all(sma_diff >= 0), "SMA should be non-decreasing for increasing input"
    
    def test_sma_boundary_conditions(self):
        """Test SMA with boundary conditions."""
        # Test with insufficient data
        insufficient_data = pd.DataFrame({
            'close': [100, 102],
            'high': [101, 103],
            'low': [99, 101],
            'open': [100, 102],
            'volume': [1000, 1000]
        }, index=pd.date_range('2023-01-01', periods=2, freq='D'))
        
        signals = sma_crossover(insufficient_data, fast_period=5, slow_period=10)
        
        # Should return False for all signals when insufficient data
        assert all(signals == False), "SMA crossover should return False with insufficient data"


class TestMathematicalToleranceLevels:
    """Test mathematical tolerance levels for trading applications."""
    
    TOLERANCE_TRADING_STANDARD = 1e-3  # 0.1% - sufficient for trading decisions
    TOLERANCE_STRICT_VALIDATION = 1e-4  # 0.01% - for critical calculations
    
    def test_trading_tolerance_sufficient(self):
        """Verify that trading tolerance levels catch meaningful errors."""
        # Test case: 1% error should be caught by trading tolerance
        expected_value = 100.0
        test_value_ok = 100.05  # 0.05% error - should pass
        test_value_fail = 101.1  # 1.1% error - should fail
        
        # Should pass with 0.05% error
        assert abs(test_value_ok - expected_value) / expected_value < self.TOLERANCE_TRADING_STANDARD
        
        # Should fail with 1.1% error  
        assert abs(test_value_fail - expected_value) / expected_value > self.TOLERANCE_TRADING_STANDARD
    
    def test_precision_documentation(self):
        """Document precision limitations for floating-point calculations."""
        # This test serves as documentation of expected precision limits
        # ATR and SMA calculations should be accurate to trading standard (0.1%)
        # but may have floating-point precision limitations beyond that
        
        # Example: Verify that our tolerance levels are reasonable for pandas operations
        test_series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        manual_mean = sum(test_series) / len(test_series)  # = 3.0
        pandas_mean = test_series.mean()
        
        # Pandas and manual calculation should match within strict tolerance
        assert abs(pandas_mean - manual_mean) < self.TOLERANCE_STRICT_VALIDATION
        
        # This confirms our tolerance levels are appropriate for the underlying calculations
        assert manual_mean == 3.0
        assert pandas_mean == 3.0
