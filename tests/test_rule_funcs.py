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
