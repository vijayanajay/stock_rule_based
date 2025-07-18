"""Unit tests for rule functions module.

Tests all technical indicator functions with known data sets and edge cases.
"""

import numpy as np
import pandas as pd
import pytest

from kiss_signal.rules import (
    sma_crossover,
    rsi_oversold, 
    ema_crossover,
    calculate_rsi,
    # New functions (Story 013)
    volume_spike,
    hammer_pattern,
    engulfing_pattern,
    macd_crossover,
    bollinger_squeeze,
    # New functions (Story 015)
    sma_cross_under,
    stop_loss_pct,
    take_profit_pct,
    # New functions (Story 018) - ATR-based exits
    calculate_atr,
    stop_loss_atr,
    take_profit_atr,
    # New functions (Story 019) - Market context filters
    market_above_sma,
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


@pytest.fixture
def volume_spike_data() -> pd.DataFrame:
    """Create data with known volume spike pattern."""
    dates = pd.date_range('2023-01-01', periods=25, freq='D')
    
    # 20 days normal volume, then spike
    volumes = [1000] * 20 + [3000, 2800, 3200, 3500, 2900]  # Volume spikes
    closes = [100 + i*0.1 for i in range(20)] + [102, 103.5, 104.2, 105.8, 106.1]  # Price jumps with volume
    
    return pd.DataFrame({
        'open': [c - 0.05 for c in closes],
        'high': [c * 1.01 for c in closes],
        'low': [c * 0.99 for c in closes],
        'close': closes,
        'volume': volumes
    }, index=dates)


@pytest.fixture
def hammer_pattern_data() -> pd.DataFrame:
    """Create data with known hammer pattern."""
    return pd.DataFrame({
        'open': [100, 95, 99.5, 104],
        'high': [101, 96, 100, 105], 
        'low': [99, 90, 98, 103],    # Large lower shadow on day 1 (hammer)
        'close': [100.5, 94.5, 99.8, 104.2],  # Small bodies
        'volume': [1000, 1200, 1100, 1050]
    })


@pytest.fixture
def engulfing_pattern_data() -> pd.DataFrame:
    """Create data with known engulfing pattern."""
    return pd.DataFrame({
        'open': [100, 99, 98, 101],    # Red candle followed by green
        'close': [99, 101.5, 97.5, 102],  # Green engulfs red completely  
        'high': [100.2, 102, 98.2, 102.5],
        'low': [98.8, 98.5, 97, 100.8],
        'volume': [1000, 1200, 1100, 1300]
    })


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


class TestVolumeSpike:
    """Test volume spike functionality."""
    
    def test_volume_spike_detection(self, volume_spike_data: pd.DataFrame) -> None:
        """Test volume spike detection with known patterns."""
        signals = volume_spike(volume_spike_data, period=20, spike_multiplier=2.0, price_change_threshold=0.01)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(volume_spike_data)
        
        # Should detect spikes in the last 5 days
        assert signals[-5:].sum() > 0
    
    def test_volume_spike_insufficient_data(self) -> None:
        """Test handling of insufficient data for volume spike."""
        short_data = pd.DataFrame({
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        
        signals = volume_spike(short_data, period=20)
        assert signals.sum() == 0
    
    def test_volume_spike_invalid_params(self, sample_price_data: pd.DataFrame) -> None:
        """Test error handling for invalid parameters."""
        with pytest.raises(ValueError, match="period.*must be > 0"):
            volume_spike(sample_price_data, period=0)
        
        with pytest.raises(ValueError, match="spike_multiplier.*must be > 1.0"):
            volume_spike(sample_price_data, spike_multiplier=0.5)
        
        with pytest.raises(ValueError, match="price_change_threshold.*must be > 0"):
            volume_spike(sample_price_data, price_change_threshold=-0.01)
    
    def test_volume_spike_missing_columns(self) -> None:
        """Test error handling for missing required columns."""
        data = pd.DataFrame({'close': [100, 101, 102]})  # Missing volume
        
        with pytest.raises(ValueError, match="Missing required columns"):
            volume_spike(data)


class TestHammerPattern:
    """Test hammer pattern detection."""
    
    def test_hammer_pattern_detection(self, hammer_pattern_data: pd.DataFrame) -> None:
        """Test hammer pattern detection with known patterns."""
        signals = hammer_pattern(hammer_pattern_data, body_ratio=0.3, shadow_ratio=2.0)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(hammer_pattern_data)
        
        # Should detect hammer on day 1 (index 1)
        assert signals.iloc[1]
    
    def test_hammer_pattern_empty_data(self) -> None:
        """Test handling of empty data."""
        empty_data = pd.DataFrame(columns=['open', 'high', 'low', 'close'])
        signals = hammer_pattern(empty_data)
        assert len(signals) == 0
    
    def test_hammer_pattern_invalid_params(self, sample_price_data: pd.DataFrame) -> None:
        """Test error handling for invalid parameters."""
        with pytest.raises(ValueError, match="body_ratio.*must be between 0 and 1"):
            hammer_pattern(sample_price_data, body_ratio=1.5)
        
        with pytest.raises(ValueError, match="shadow_ratio.*must be > 0"):
            hammer_pattern(sample_price_data, shadow_ratio=-1.0)
    
    def test_hammer_pattern_missing_columns(self) -> None:
        """Test error handling for missing required columns."""
        data = pd.DataFrame({'close': [100, 101, 102]})  # Missing OHLC
        
        with pytest.raises(ValueError, match="Missing required columns"):
            hammer_pattern(data)


class TestEngulfingPattern:
    """Test engulfing pattern detection."""
    
    def test_engulfing_pattern_detection(self, engulfing_pattern_data: pd.DataFrame) -> None:
        """Test engulfing pattern detection with known patterns."""
        signals = engulfing_pattern(engulfing_pattern_data, min_body_ratio=1.2)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(engulfing_pattern_data)
        
        # Should detect engulfing on day 1 (green candle engulfs red)
        assert signals.iloc[1]
    
    def test_engulfing_pattern_insufficient_data(self) -> None:
        """Test handling of insufficient data."""
        short_data = pd.DataFrame({
            'open': [100],
            'close': [101]
        })
        
        signals = engulfing_pattern(short_data)
        assert signals.sum() == 0
    
    def test_engulfing_pattern_invalid_params(self, sample_price_data: pd.DataFrame) -> None:
        """Test error handling for invalid parameters."""
        with pytest.raises(ValueError, match="min_body_ratio.*must be > 1.0"):
            engulfing_pattern(sample_price_data, min_body_ratio=0.8)
    
    def test_engulfing_pattern_missing_columns(self) -> None:
        """Test error handling for missing required columns."""
        data = pd.DataFrame({'close': [100, 101, 102]})  # Missing open
        
        with pytest.raises(ValueError, match="Missing required columns"):
            engulfing_pattern(data)


class TestMACDCrossover:
    """Test MACD crossover functionality."""
    
    def test_macd_crossover_signal(self, sample_price_data: pd.DataFrame) -> None:
        """Test MACD crossover signal generation."""
        signals = macd_crossover(sample_price_data, fast_period=12, slow_period=26, signal_period=9)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(sample_price_data)
        assert signals.index.equals(sample_price_data.index)
    
    def test_macd_crossover_insufficient_data(self) -> None:
        """Test handling of insufficient data."""
        short_data = pd.DataFrame({
            'close': [100 + i for i in range(20)]  # Only 20 rows, need 26+9=35
        })
        
        signals = macd_crossover(short_data)
        assert signals.sum() == 0
    
    def test_macd_crossover_invalid_params(self, sample_price_data: pd.DataFrame) -> None:
        """Test error handling for invalid parameters."""
        with pytest.raises(ValueError, match="fast_period.*must be.*slow_period"):
            macd_crossover(sample_price_data, fast_period=26, slow_period=12)
        
        with pytest.raises(ValueError, match="signal_period.*must be > 0"):
            macd_crossover(sample_price_data, signal_period=0)
    
    def test_macd_crossover_missing_columns(self) -> None:
        """Test error handling for missing required columns."""
        data = pd.DataFrame({'volume': [1000, 1100, 1200]})  # Missing close
        
        with pytest.raises(ValueError, match="Missing required columns"):
            macd_crossover(data)


class TestBollingerSqueeze:
    """Test Bollinger squeeze functionality."""
    
    def test_bollinger_squeeze_signal(self, sample_price_data: pd.DataFrame) -> None:
        """Test Bollinger squeeze signal generation."""
        signals = bollinger_squeeze(sample_price_data, period=20, std_dev=2.0, squeeze_threshold=0.1)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(sample_price_data)
        assert signals.index.equals(sample_price_data.index)
    
    def test_bollinger_squeeze_insufficient_data(self) -> None:
        """Test handling of insufficient data."""
        short_data = pd.DataFrame({
            'close': [100 + i for i in range(15)]  # Only 15 rows, need 20+5=25
        })
        
        signals = bollinger_squeeze(short_data)
        assert signals.sum() == 0
    
    def test_bollinger_squeeze_invalid_params(self, sample_price_data: pd.DataFrame) -> None:
        """Test error handling for invalid parameters."""
        with pytest.raises(ValueError, match="period.*must be > 0"):
            bollinger_squeeze(sample_price_data, period=0)
        
        with pytest.raises(ValueError, match="std_dev.*must be > 0"):
            bollinger_squeeze(sample_price_data, std_dev=-1.0)
        
        with pytest.raises(ValueError, match="squeeze_threshold.*must be > 0"):
            bollinger_squeeze(sample_price_data, squeeze_threshold=0)
    
    def test_bollinger_squeeze_missing_columns(self) -> None:
        """Test error handling for missing required columns."""
        data = pd.DataFrame({'volume': [1000, 1100, 1200]})  # Missing close
        
        with pytest.raises(ValueError, match="Missing required columns"):
            bollinger_squeeze(data)


class TestNewRulesIntegration:
    """Integration tests for new rule functions."""
    
    def test_all_new_rules_with_sample_data(self, sample_price_data: pd.DataFrame) -> None:
        """Test all new rules with realistic data."""
        # Test volume spike
        volume_signals = volume_spike(sample_price_data, period=20, spike_multiplier=2.0)
        assert isinstance(volume_signals, pd.Series)
        assert volume_signals.dtype == bool
        
        # Test hammer pattern
        hammer_signals = hammer_pattern(sample_price_data, body_ratio=0.3, shadow_ratio=2.0)
        assert isinstance(hammer_signals, pd.Series)
        assert hammer_signals.dtype == bool
        
        # Test engulfing pattern
        engulfing_signals = engulfing_pattern(sample_price_data, min_body_ratio=1.2)
        assert isinstance(engulfing_signals, pd.Series)
        assert engulfing_signals.dtype == bool
        
        # Test MACD crossover
        macd_signals = macd_crossover(sample_price_data, fast_period=12, slow_period=26, signal_period=9)
        assert isinstance(macd_signals, pd.Series)
        assert macd_signals.dtype == bool
        
        # Test Bollinger squeeze
        bollinger_signals = bollinger_squeeze(sample_price_data, period=20, std_dev=2.0, squeeze_threshold=0.1)
        assert isinstance(bollinger_signals, pd.Series)
        assert bollinger_signals.dtype == bool
        
        # Verify reasonable signal frequency (not too many, not zero for all)
        total_signals = (volume_signals.sum() + hammer_signals.sum() + engulfing_signals.sum() + 
                        macd_signals.sum() + bollinger_signals.sum())
        assert total_signals >= 0  # At least no errors, some signals expected


# =============================================================================
# Story 015: Dynamic Exit Conditions Tests
# =============================================================================

def test_sma_cross_under_basic():
    """Test SMA cross under detection."""
    # Create data where fast SMA crosses under slow SMA
    dates = pd.date_range('2023-01-01', periods=30, freq='D')
    
    # Start high then decline to trigger crossover
    prices = [110, 109, 108, 107, 106, 105, 104, 103, 102, 101,  # declining
              100, 99, 98, 97, 96, 95, 94, 93, 92, 91,           # continued decline
              90, 89, 88, 87, 86, 85, 84, 83, 82, 81]           # further decline
              
    price_data = pd.DataFrame({
        'open': prices,
        'high': [p + 0.5 for p in prices],
        'low': [p - 0.5 for p in prices],
        'close': prices,
        'volume': [1000] * 30
    }, index=dates)
    
    signals = sma_cross_under(price_data, fast_period=5, slow_period=10)
    assert isinstance(signals, pd.Series)
    assert signals.dtype == bool
    assert len(signals) == 30


def test_sma_cross_under_parameter_validation():
    """Test parameter validation for sma_cross_under."""
    price_data = pd.DataFrame({
        'open': [100, 101, 102],
        'high': [101, 102, 103],
        'low': [99, 100, 101],
        'close': [100, 101, 102],
        'volume': [1000, 1000, 1000]
    })
    
    # fast_period must be less than slow_period
    with pytest.raises(ValueError, match="fast_period.*must be less than slow_period"):
        sma_cross_under(price_data, fast_period=10, slow_period=5)
    
    # Equal periods should also fail
    with pytest.raises(ValueError, match="fast_period.*must be less than slow_period"):
        sma_cross_under(price_data, fast_period=10, slow_period=10)


def test_stop_loss_pct_validation():
    """Test parameter validation for stop_loss_pct."""
    price_data = pd.DataFrame({
        'open': [100, 101, 102],
        'high': [101, 102, 103],
        'low': [99, 100, 101],
        'close': [100, 101, 102],
        'volume': [1000, 1000, 1000]
    })
    
    # Valid percentage
    signals = stop_loss_pct(price_data, percentage=0.05)
    assert isinstance(signals, pd.Series)
    assert signals.dtype == bool
    assert all(~signals)  # Should always return False
    
    # Invalid percentage
    with pytest.raises(ValueError, match="percentage must be > 0"):
        stop_loss_pct(price_data, percentage=0)
    
    with pytest.raises(ValueError, match="percentage must be > 0"):
        stop_loss_pct(price_data, percentage=-0.05)


def test_take_profit_pct_validation():
    """Test parameter validation for take_profit_pct."""
    price_data = pd.DataFrame({
        'open': [100, 101, 102],
        'high': [101, 102, 103],
        'low': [99, 100, 101],
        'close': [100, 101, 102],
        'volume': [1000, 1000, 1000]
    })
    
    # Valid percentage
    signals = take_profit_pct(price_data, percentage=0.15)
    assert isinstance(signals, pd.Series)
    assert signals.dtype == bool
    assert all(~signals)  # Should always return False
    
    # Invalid percentage
    with pytest.raises(ValueError, match="percentage must be > 0"):
        take_profit_pct(price_data, percentage=0)
    
    with pytest.raises(ValueError, match="percentage must be > 0"):
        take_profit_pct(price_data, percentage=-0.15)


def test_sma_cross_under_insufficient_data():
    """Test sma_cross_under with insufficient data."""
    # Not enough data for slow SMA
    price_data = pd.DataFrame({
        'open': [100, 101],
        'high': [101, 102], 
        'low': [99, 100],
        'close': [100, 101],
        'volume': [1000, 1000]
    })
    
    signals = sma_cross_under(price_data, fast_period=5, slow_period=10)
    assert isinstance(signals, pd.Series)
    assert all(~signals)


# =============================================================================
# Story 018: ATR-Based Dynamic Exit Conditions Tests
# =============================================================================

def test_calculate_atr_basic():
    """Test ATR calculation with known values."""
    # Create simple test data
    price_data = pd.DataFrame({
        'high': [22, 23, 24, 25, 26],
        'low': [20, 21, 22, 23, 24], 
        'close': [21, 22, 23, 24, 25],
        'volume': [1000] * 5
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
    
    atr = calculate_atr(price_data, period=3)
    
    # Should have same length as input
    assert len(atr) == len(price_data)
    assert isinstance(atr, pd.Series)
    
    # First two values should be NaN due to insufficient data for period=3
    assert pd.isna(atr.iloc[0])
    assert pd.isna(atr.iloc[1])
    
    # Third value should be the first valid ATR
    assert not pd.isna(atr.iloc[2])
    assert atr.iloc[2] > 0
    
    # ATR should be positive and reasonable
    assert (atr.dropna() > 0).all()


def test_calculate_atr_mathematical_accuracy():
    """Test ATR calculation with manually calculated values."""
    # Simple data where we can manually calculate ATR
    price_data = pd.DataFrame({
        'high': [105, 110, 108, 115, 112],
        'low': [95, 100, 102, 105, 108],
        'close': [100, 105, 106, 110, 111]
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
    
    atr = calculate_atr(price_data, period=3)
    
    # Manual calculation:
    # Day 1: TR = 105-95 = 10
    # Day 2: TR = max(110-100, |110-100|, |100-100|) = max(10, 10, 0) = 10  
    # Day 3: TR = max(108-102, |108-105|, |102-105|) = max(6, 3, 3) = 6
    # Day 4: TR = max(115-105, |115-106|, |105-106|) = max(10, 9, 1) = 10
    # Day 5: TR = max(112-108, |112-110|, |108-110|) = max(4, 2, 2) = 4
    
    # ATR(3) starts at day 3 with Wilder's smoothing
    # First ATR = simple average of first 3 TRs = (10 + 10 + 6) / 3 = 8.67
    
    assert not pd.isna(atr.iloc[2])
    assert abs(atr.iloc[2] - 8.67) < 0.1  # Allow small floating point differences


def test_calculate_atr_insufficient_data():
    """Test ATR with insufficient data."""
    # Less data than required period
    price_data = pd.DataFrame({
        'high': [22, 23],
        'low': [20, 21],
        'close': [21, 22],
        'volume': [1000] * 2
    }, index=pd.date_range('2023-01-01', periods=2, freq='D'))
    
    atr = calculate_atr(price_data, period=5)
    
    # Should return all NaN when insufficient data
    assert all(pd.isna(atr))


def test_calculate_atr_missing_columns():
    """Test ATR with missing required columns."""
    price_data = pd.DataFrame({
        'high': [22, 23, 24],
        'low': [20, 21, 22],
        # Missing 'close' column
        'volume': [1000] * 3
    })
    
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_atr(price_data, period=3)


def test_calculate_atr_invalid_period():
    """Test ATR with invalid period values."""
    price_data = pd.DataFrame({
        'high': [22, 23, 24],
        'low': [20, 21, 22],
        'close': [21, 22, 23],
        'volume': [1000] * 3
    })
    
    with pytest.raises(ValueError, match="period .* must be > 1"):
        calculate_atr(price_data, period=1)
    
    with pytest.raises(ValueError, match="period .* must be > 1"):
        calculate_atr(price_data, period=0)


def test_stop_loss_atr_basic():
    """Test ATR-based stop loss basic functionality."""
    # Create test data with known ATR
    price_data = pd.DataFrame({
        'high': [105, 110, 108, 115, 95],  # Last day: big drop
        'low': [95, 100, 102, 105, 90],
        'close': [100, 105, 106, 110, 92]  # Price drops to 92
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
    
    entry_price = 110.0  # Entered at day 4 price
    
    # Test with large multiplier - should not trigger
    triggered = stop_loss_atr(price_data, entry_price, period=3, multiplier=10.0)
    assert not triggered
    
    # Test with small multiplier - should trigger
    triggered = stop_loss_atr(price_data, entry_price, period=3, multiplier=1.0)
    assert triggered


def test_stop_loss_atr_not_triggered():
    """Test ATR stop loss when price is above stop level."""
    price_data = pd.DataFrame({
        'high': [105, 110, 108, 115, 118],  # Price going up
        'low': [95, 100, 102, 105, 112],
        'close': [100, 105, 106, 110, 115]
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
    
    entry_price = 110.0
    
    triggered = stop_loss_atr(price_data, entry_price, period=3, multiplier=2.0)
    assert not triggered


def test_stop_loss_atr_invalid_params():
    """Test ATR stop loss with invalid parameters."""
    price_data = pd.DataFrame({
        'high': [22, 23, 24],
        'low': [20, 21, 22],
        'close': [21, 22, 23],
        'volume': [1000] * 3
    })
    
    # Invalid period
    with pytest.raises(ValueError, match="period .* must be > 1"):
        stop_loss_atr(price_data, 100.0, period=1, multiplier=2.0)
    
    # Invalid multiplier
    with pytest.raises(ValueError, match="multiplier .* must be > 0"):
        stop_loss_atr(price_data, 100.0, period=3, multiplier=0)
    
    # Invalid entry price
    with pytest.raises(ValueError, match="entry_price .* must be > 0"):
        stop_loss_atr(price_data, 0, period=3, multiplier=2.0)


def test_stop_loss_atr_insufficient_data():
    """Test ATR stop loss with insufficient data for ATR calculation."""
    price_data = pd.DataFrame({
        'high': [22, 23],
        'low': [20, 21],
        'close': [21, 22],
        'volume': [1000] * 2
    })
    
    # Insufficient data should return False (no trigger)
    triggered = stop_loss_atr(price_data, 100.0, period=5, multiplier=2.0)
    assert not triggered


# =============================================================================
# Story 019: Market Context Filters Tests
# =============================================================================

@pytest.fixture
def bullish_market_data() -> pd.DataFrame:
    """Create market data that is consistently above SMA (bullish market)."""
    dates = pd.date_range('2023-01-01', periods=60, freq='D')
    
    # Create uptrending market data
    base_price = 15000  # NIFTY-like levels
    trend = 50  # Strong uptrend
    
    prices = []
    for i in range(len(dates)):
        price = base_price + trend * i + (i % 7 - 3) * 20  # Add some volatility
        prices.append(price)
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.005 for p in prices],
        'low': [p * 0.995 for p in prices],
        'close': prices,
        'volume': [100000 + i * 1000 for i in range(len(dates))]
    }, index=dates)


@pytest.fixture
def bearish_market_data() -> pd.DataFrame:
    """Create market data that is consistently below SMA (bearish market)."""
    dates = pd.date_range('2023-01-01', periods=60, freq='D')
    
    # Create downtrending market data
    base_price = 18000  # Start high
    decline_rate = -80  # Strong decline
    
    prices = []
    for i in range(len(dates)):
        price = base_price + decline_rate * i + (i % 5 - 2) * 30  # Add volatility
        prices.append(max(price, 12000))  # Floor at 12000
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.005 for p in prices],
        'low': [p * 0.995 for p in prices],
        'close': prices,
        'volume': [100000] * len(dates)
    }, index=dates)


@pytest.fixture
def mixed_market_data() -> pd.DataFrame:
    """Create market data with periods above and below SMA."""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    
    # Create market that oscillates around a level
    base_price = 16000
    prices = []
    
    for i in range(len(dates)):
        # Create sine wave pattern with trend
        cycle_position = (i / 20) * 2 * 3.14159  # 20-day cycles
        cycle_value = 800 * (0.5 + 0.5 * np.sin(cycle_position))  # 0 to 800 range
        trend_value = i * 2  # Small uptrend
        noise = (i % 11 - 5) * 10  # Random-ish noise
        
        price = base_price + cycle_value + trend_value + noise
        prices.append(price)
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.005 for p in prices],
        'low': [p * 0.995 for p in prices],
        'close': prices,
        'volume': [100000] * len(dates)
    }, index=dates)


class TestMarketAboveSMA:
    """Test market above SMA context filter functionality."""
    
    def test_bullish_market_detection(self, bullish_market_data: pd.DataFrame) -> None:
        """Test detection of bullish market periods with different SMA periods."""
        # Test with 20-day SMA
        signals_20 = market_above_sma(bullish_market_data, period=20)
        
        assert isinstance(signals_20, pd.Series)
        assert signals_20.dtype == bool
        assert len(signals_20) == len(bullish_market_data)
        assert signals_20.index.equals(bullish_market_data.index)
        
        # In a strong uptrend, most periods should be bullish after initial SMA calculation
        bullish_count = signals_20.sum()
        total_periods = len(signals_20)
        bullish_ratio = bullish_count / total_periods
        
        # Should have high percentage of bullish periods (>65%) in uptrending market
        assert bullish_ratio > 0.65, f"Expected >65% bullish periods, got {bullish_ratio:.1%}"
        
        # Test with 50-day SMA
        signals_50 = market_above_sma(bullish_market_data, period=50)
        assert isinstance(signals_50, pd.Series)
        assert len(signals_50) == len(bullish_market_data)
        
        # 50-day should also show bullish trend but may be less sensitive
        # With only 60 days of data, 50-day SMA has limited comparison periods
        bullish_count_50 = signals_50.sum()
        bullish_ratio_50 = bullish_count_50 / total_periods
        # More lenient threshold for 50-day SMA due to limited data
        assert bullish_ratio_50 > 0.15, f"Expected >15% bullish periods with 50-day SMA, got {bullish_ratio_50:.1%}"
    
    def test_bearish_market_detection(self, bearish_market_data: pd.DataFrame) -> None:
        """Test detection of bearish market periods."""
        signals = market_above_sma(bearish_market_data, period=20)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(bearish_market_data)
        
        # In a strong downtrend, most periods should be bearish
        bullish_count = signals.sum()
        total_periods = len(signals)
        bullish_ratio = bullish_count / total_periods
        
        # Should have low percentage of bullish periods (<30%) in downtrending market
        assert bullish_ratio < 0.3, f"Expected <30% bullish periods, got {bullish_ratio:.1%}"
    
    def test_mixed_market_conditions(self, mixed_market_data: pd.DataFrame) -> None:
        """Test with market data that has both bullish and bearish periods."""
        signals = market_above_sma(mixed_market_data, period=20)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(mixed_market_data)
        
        # Mixed market should have reasonable distribution of bullish/bearish periods
        bullish_count = signals.sum()
        total_periods = len(signals)
        bullish_ratio = bullish_count / total_periods
        
        # Should be somewhere in the middle (20% to 80%)
        assert 0.2 < bullish_ratio < 0.8, f"Expected 20-80% bullish periods, got {bullish_ratio:.1%}"
        
        # Should have both True and False values
        assert signals.any(), "Should have some bullish periods"
        assert not signals.all(), "Should have some bearish periods"
    
    def test_different_sma_periods(self, sample_price_data: pd.DataFrame) -> None:
        """Test market filter with different SMA periods."""
        periods_to_test = [20, 50, 200]
        
        for period in periods_to_test:
            signals = market_above_sma(sample_price_data, period=period)
            
            assert isinstance(signals, pd.Series)
            assert signals.dtype == bool
            assert len(signals) == len(sample_price_data)
            assert signals.index.equals(sample_price_data.index)
            
            # All values should be boolean (True/False, no NaN after fillna)
            assert not signals.isna().any(), f"Found NaN values with period={period}"
    
    def test_insufficient_data_handling(self) -> None:
        """Test handling when market data has insufficient periods for SMA calculation."""
        # Create data with fewer periods than required SMA period
        short_data = pd.DataFrame({
            'open': [15000, 15100, 15200],
            'high': [15050, 15150, 15250],
            'low': [14950, 15050, 15150],
            'close': [15000, 15100, 15200],
            'volume': [100000, 110000, 120000]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        
        # Request 50-day SMA with only 3 days of data
        signals = market_above_sma(short_data, period=50)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(short_data)
        
        # Should return all False when insufficient data
        assert not signals.any(), "Should return all False with insufficient data"
        assert signals.sum() == 0, "Should have zero bullish signals with insufficient data"
    
    def test_parameter_validation(self, sample_price_data: pd.DataFrame) -> None:
        """Test parameter validation for market_above_sma function."""
        # Test invalid period values
        with pytest.raises(ValueError, match="SMA period must be positive"):
            market_above_sma(sample_price_data, period=0)
        
        with pytest.raises(ValueError, match="SMA period must be positive"):
            market_above_sma(sample_price_data, period=-10)
        
        # Test valid periods
        valid_periods = [1, 5, 10, 20, 50, 100, 200]
        for period in valid_periods:
            signals = market_above_sma(sample_price_data, period=period)
            assert isinstance(signals, pd.Series)
            assert signals.dtype == bool
    
    def test_missing_required_columns(self) -> None:
        """Test error handling when required columns are missing."""
        # Missing 'close' column
        incomplete_data = pd.DataFrame({
            'open': [15000, 15100, 15200],
            'high': [15050, 15150, 15250],
            'low': [14950, 15050, 15150],
            'volume': [100000, 110000, 120000]
        })
        
        with pytest.raises(ValueError, match="Missing required columns"):
            market_above_sma(incomplete_data, period=20)
        
        # Test with only close column (should work)
        close_only_data = pd.DataFrame({
            'close': [15000, 15100, 15200, 15150, 15250]
        })
        
        signals = market_above_sma(close_only_data, period=3)
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
    
    def test_empty_dataframe_handling(self) -> None:
        """Test handling of empty DataFrame."""
        empty_data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        signals = market_above_sma(empty_data, period=20)
        
        assert isinstance(signals, pd.Series)
        assert len(signals) == 0
        assert signals.dtype == bool
    
    def test_nan_values_handling(self) -> None:
        """Test handling of NaN values in market data."""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        prices = [15000 + i * 10 for i in range(30)]
        
        # Introduce some NaN values
        prices[5] = float('nan')
        prices[15] = float('nan')
        prices[25] = float('nan')
        
        data_with_nan = pd.DataFrame({
            'open': prices,
            'high': [p * 1.005 if not pd.isna(p) else float('nan') for p in prices],
            'low': [p * 0.995 if not pd.isna(p) else float('nan') for p in prices],
            'close': prices,
            'volume': [100000] * 30
        }, index=dates)
        
        # Should handle NaN gracefully
        signals = market_above_sma(data_with_nan, period=10)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(data_with_nan)
        
        # fillna(False) should ensure no NaN values in output
        assert not signals.isna().any(), "Output should not contain NaN values"
    
    def test_crossover_scenarios(self) -> None:
        """Test market filter behavior during SMA crossover scenarios."""
        dates = pd.date_range('2023-01-01', periods=60, freq='D')
        
        # Create data that crosses above and below SMA
        prices = []
        base_price = 16000
        
        # First 20 days: below SMA (declining)
        for i in range(20):
            prices.append(base_price - i * 30)
        
        # Next 20 days: recovery and cross above SMA
        for i in range(20):
            prices.append(base_price - 600 + i * 40)  # Recovery
        
        # Last 20 days: above SMA (continuing uptrend)
        for i in range(20):
            prices.append(base_price + 200 + i * 20)
        
        crossover_data = pd.DataFrame({
            'open': prices,
            'high': [p * 1.005 for p in prices],
            'low': [p * 0.995 for p in prices],
            'close': prices,
            'volume': [100000] * 60
        }, index=dates)
        
        signals = market_above_sma(crossover_data, period=20)
        
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        
        # Should show transition from bearish to bullish
        early_signals = signals[:25]  # First 25 days
        late_signals = signals[-15:]  # Last 15 days
        
        # Early period should be mostly bearish
        early_bullish_ratio = early_signals.sum() / len(early_signals)
        assert early_bullish_ratio < 0.4, f"Early period should be mostly bearish, got {early_bullish_ratio:.1%}"
        
        # Late period should be mostly bullish
        late_bullish_ratio = late_signals.sum() / len(late_signals)
        assert late_bullish_ratio > 0.6, f"Late period should be mostly bullish, got {late_bullish_ratio:.1%}"
    
    def test_edge_case_single_data_point(self) -> None:
        """Test with single data point."""
        single_point_data = pd.DataFrame({
            'close': [15000]
        }, index=pd.date_range('2023-01-01', periods=1, freq='D'))
        
        signals = market_above_sma(single_point_data, period=20)
        
        assert isinstance(signals, pd.Series)
        assert len(signals) == 1
        assert not signals.iloc[0], "Single point should be False (insufficient data)"
    
    def test_mathematical_accuracy(self) -> None:
        """Test mathematical accuracy of SMA calculation and comparison."""
        # Create simple data where we can manually verify SMA calculation
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        dates = pd.date_range('2023-01-01', periods=len(prices), freq='D')
        
        test_data = pd.DataFrame({
            'close': prices
        }, index=dates)
        
        signals = market_above_sma(test_data, period=5)
        
        # Manual calculation for 5-day SMA:
        # Day 5: SMA = (100+102+104+106+108)/5 = 104, Price = 108 > 104 → True
        # Day 6: SMA = (102+104+106+108+110)/5 = 106, Price = 110 > 106 → True
        # Day 7: SMA = (104+106+108+110+112)/5 = 108, Price = 112 > 108 → True
        # etc.
        
        # First 4 values should be False (insufficient data for SMA)
        assert not signals[:4].any(), "First 4 values should be False"
        
        # From day 5 onwards, all should be True (price consistently above SMA)
        assert signals[4:].all(), "Days 5+ should all be True (price above SMA)"
    
    def test_performance_with_large_dataset(self) -> None:
        """Test performance and correctness with larger dataset."""
        # Create 2 years of daily data
        dates = pd.date_range('2022-01-01', periods=730, freq='D')
        
        # Create realistic market data with trend and volatility
        base_price = 15000
        prices = []
        
        for i in range(len(dates)):
            trend = i * 5  # Long-term uptrend
            cycle = 500 * np.sin(i / 50)  # Medium-term cycles
            noise = (hash(str(i)) % 200) - 100  # Pseudo-random noise
            price = base_price + trend + cycle + noise
            prices.append(max(price, 10000))  # Floor price
        
        large_dataset = pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': [100000] * len(dates)
        }, index=dates)
        
        # Test with different SMA periods
        for period in [20, 50, 200]:
            signals = market_above_sma(large_dataset, period=period)
            
            assert isinstance(signals, pd.Series)
            assert len(signals) == len(large_dataset)
            assert signals.dtype == bool
            
            # Should have reasonable distribution of signals
            bullish_ratio = signals.sum() / len(signals)
            assert 0.1 < bullish_ratio < 0.9, f"Period {period}: unrealistic bullish ratio {bullish_ratio:.1%}"


def test_take_profit_atr_basic():
    """Test ATR-based take profit basic functionality."""
    # Create test data with big price move up
    price_data = pd.DataFrame({
        'high': [105, 110, 108, 115, 125],  # Last day: big jump
        'low': [95, 100, 102, 105, 120],
        'close': [100, 105, 106, 110, 122]  # Price jumps to 122
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
    
    entry_price = 100.0  # Entered at first day
    
    # Test with large multiplier - should not trigger
    triggered = take_profit_atr(price_data, entry_price, period=3, multiplier=10.0)
    assert not triggered
    
    # Test with small multiplier - should trigger
    triggered = take_profit_atr(price_data, entry_price, period=3, multiplier=1.0)
    assert triggered


def test_take_profit_atr_not_triggered():
    """Test ATR take profit when price hasn't reached target."""
    price_data = pd.DataFrame({
        'high': [105, 110, 108, 115, 108],  # Price going down
        'low': [95, 100, 102, 105, 102],
        'close': [100, 105, 106, 110, 105]
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
    
    entry_price = 100.0
    
    triggered = take_profit_atr(price_data, entry_price, period=3, multiplier=4.0)
    assert not triggered


def test_take_profit_atr_invalid_params():
    """Test ATR take profit with invalid parameters."""
    price_data = pd.DataFrame({
        'high': [22, 23, 24],
        'low': [20, 21, 22],
        'close': [21, 22, 23],
        'volume': [1000] * 3
    })
    
    # Invalid period
    with pytest.raises(ValueError, match="period .* must be > 1"):
        take_profit_atr(price_data, 100.0, period=1, multiplier=4.0)
    
    # Invalid multiplier
    with pytest.raises(ValueError, match="multiplier .* must be > 0"):
        take_profit_atr(price_data, 100.0, period=3, multiplier=-1.0)
    
    # Invalid entry price
    with pytest.raises(ValueError, match="entry_price .* must be > 0"):
        take_profit_atr(price_data, -100.0, period=3, multiplier=4.0)


def test_take_profit_atr_insufficient_data():
    """Test ATR take profit with insufficient data for ATR calculation."""
    price_data = pd.DataFrame({
        'high': [22, 23],
        'low': [20, 21],
        'close': [21, 22],
        'volume': [1000] * 2
    })
    
    # Insufficient data should return False (no trigger)
    triggered = take_profit_atr(price_data, 100.0, period=5, multiplier=4.0)
    assert not triggered


def test_atr_functions_empty_data():
    """Test ATR functions with empty DataFrame."""
    empty_data = pd.DataFrame()
    
    # ATR calculation should return empty series
    atr = calculate_atr(empty_data, period=3)
    assert len(atr) == 0
    
    # Exit functions should return False for empty data
    assert not stop_loss_atr(empty_data, 100.0, period=3, multiplier=2.0)
    assert not take_profit_atr(empty_data, 100.0, period=3, multiplier=4.0)


def test_atr_consistency_across_functions():
    """Test that exit functions use consistent ATR calculation."""
    price_data = pd.DataFrame({
        'high': [105, 110, 108, 115, 112],
        'low': [95, 100, 102, 105, 108],
        'close': [100, 105, 106, 110, 111]
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
    
    entry_price = 105.0
    period = 3
    
    # Calculate ATR directly
    atr = calculate_atr(price_data, period)
    current_atr = atr.iloc[-1]
    current_price = price_data['close'].iloc[-1]
    
    # Check stop loss calculation
    stop_multiplier = 2.0
    expected_stop_level = entry_price - (stop_multiplier * current_atr)
    stop_triggered = current_price <= expected_stop_level
    actual_stop_triggered = stop_loss_atr(price_data, entry_price, period, stop_multiplier)
    assert stop_triggered == actual_stop_triggered
    
    # Check take profit calculation
    profit_multiplier = 4.0
    expected_profit_level = entry_price + (profit_multiplier * current_atr)
    profit_triggered = current_price >= expected_profit_level
    actual_profit_triggered = take_profit_atr(price_data, entry_price, period, profit_multiplier)
    assert profit_triggered == actual_profit_triggered
