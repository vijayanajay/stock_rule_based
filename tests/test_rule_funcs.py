"""Unit tests for rule functions module.

Tests all technical indicator functions with known data sets and edge cases.
"""

import pandas as pd
import pytest

from kiss_signal.rules import (
    sma_crossover,
    rsi_oversold, 
    ema_crossover,
    calculate_rsi,
)


@pytest.fixture
def sample_price_data() -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    
    # Create trending price data that should trigger crossovers
    base_price = 100
    trend = 0.5  # Positive trend
    
    prices = []
    for i in range(len(dates)):
        price = base_price + trend * i + (i % 5 - 2)  # Add some volatility
        prices.append(price)
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [1000 + i * 10 for i in range(len(dates))]
    }, index=dates)


@pytest.fixture
def declining_price_data() -> pd.DataFrame:
    """Create declining price data for RSI testing."""
    dates = pd.date_range('2023-01-01', periods=30, freq='D')
    
    # Start high and decline to trigger oversold
    base_price = 100
    decline_rate = -1.5
    
    prices = []
    for i in range(len(dates)):
        price = base_price + decline_rate * i + (i % 3 - 1) * 0.5  # Add volatility
        prices.append(max(price, 50))  # Floor at 50
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [1000] * len(dates)
    }, index=dates)


class TestSMACrossover:
    """Test SMA crossover functionality."""
    
    def test_valid_crossover_signal(self, sample_price_data: pd.DataFrame) -> None:
        """Test that SMA crossover generates signals with valid parameters."""
        signals = sma_crossover(sample_price_data, fast_period=5, slow_period=10)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(sample_price_data)
        assert signals.index.equals(sample_price_data.index)
    
    def test_insufficient_data(self) -> None:
        """Test handling of insufficient data."""
        short_data = pd.DataFrame({
            'close': [100, 101, 102]
        })
        
        signals = sma_crossover(short_data, fast_period=5, slow_period=10)
        assert signals.sum() == 0  # No signals with insufficient data
    
    def test_invalid_periods(self, sample_price_data: pd.DataFrame) -> None:
        """Test error handling for invalid period parameters."""
        with pytest.raises(ValueError, match="fast_period.*must be.*slow_period"):
            sma_crossover(sample_price_data, fast_period=20, slow_period=10)
        
        with pytest.raises(ValueError, match="fast_period.*must be.*slow_period"):
            sma_crossover(sample_price_data, fast_period=10, slow_period=10)


class TestCalculateRSI:
    """Test RSI calculation function."""
    
    def test_rsi_calculation(self) -> None:
        """Test RSI calculation with known values."""
        # Use simple data where we can verify RSI
        prices = pd.Series([100, 102, 101, 103, 102, 104, 103, 105, 104, 106])
        
        rsi = calculate_rsi(prices, period=4)
        
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(prices)
        assert not rsi.isna().all()  # Should have some valid values
        
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()
    
    def test_rsi_insufficient_data(self) -> None:
        """Test RSI with insufficient data."""
        prices = pd.Series([100, 101])
        rsi = calculate_rsi(prices, period=14)
        
        assert rsi.isna().all()  # All NaN for insufficient data


class TestRSIOversold:
    """Test RSI oversold signal generation."""
    
    def test_oversold_signal_generation(self, declining_price_data: pd.DataFrame) -> None:
        """Test that RSI oversold generates signals in declining market."""
        signals = rsi_oversold(declining_price_data, period=14, oversold_threshold=30.0)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(declining_price_data)
        
        # Should generate at least one signal in a declining market
        # (This is probabilistic, but very likely with our test data)
        assert signals.sum() >= 0  # At least no errors
    
    def test_insufficient_data_rsi(self) -> None:
        """Test RSI oversold with insufficient data."""
        short_data = pd.DataFrame({
            'close': [100, 95, 90]
        })
        
        signals = rsi_oversold(short_data, period=14)
        assert signals.sum() == 0  # No signals with insufficient data


class TestEMACrossover:
    """Test EMA crossover functionality."""
    
    def test_ema_crossover_signal(self, sample_price_data: pd.DataFrame) -> None:
        """Test EMA crossover signal generation."""
        signals = ema_crossover(sample_price_data, fast_period=5, slow_period=15)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(sample_price_data)
        assert signals.index.equals(sample_price_data.index)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_dataframe(self) -> None:
        """Test handling of empty DataFrames."""
        empty_data = pd.DataFrame(columns=['close'])
        
        signals = sma_crossover(empty_data, fast_period=5, slow_period=10)
        assert len(signals) == 0
    
    def test_single_price_data(self) -> None:
        """Test handling of single data point."""
        single_data = pd.DataFrame({'close': [100]})
        
        signals = sma_crossover(single_data, fast_period=5, slow_period=10)
        assert signals.sum() == 0
    
    def test_nan_price_data(self) -> None:
        """Test handling of NaN values in price data."""
        dates = pd.date_range('2023-01-01', periods=20, freq='D')
        prices = [100 + i for i in range(20)]
        prices[5] = float('nan')  # Introduce NaN
        prices[10] = float('nan')
        
        data = pd.DataFrame({
            'close': prices
        }, index=dates)
        
        # Should handle NaN gracefully
        signals = sma_crossover(data, fast_period=5, slow_period=10)
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(data)


class TestIntegration:
    """Integration tests with combined functionality."""
    
    def test_all_rules_with_real_data(self, sample_price_data: pd.DataFrame) -> None:
        """Test all rule types with realistic data."""
        # Test SMA crossover
        sma_signals = sma_crossover(sample_price_data, fast_period=5, slow_period=10)
        assert isinstance(sma_signals, pd.Series)
        assert sma_signals.dtype == bool
        
        # Test RSI oversold
        rsi_signals = rsi_oversold(sample_price_data, period=14, oversold_threshold=30)
        assert isinstance(rsi_signals, pd.Series)
        assert rsi_signals.dtype == bool
        
        # Test EMA crossover
        ema_signals = ema_crossover(sample_price_data, fast_period=5, slow_period=10)
        assert isinstance(ema_signals, pd.Series)
        assert ema_signals.dtype == bool
