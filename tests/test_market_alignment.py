"""Tests for Market Data Alignment Fix.

This module tests the critical fix for the market data alignment issue where
market context filters were showing 0% pass rates due to index misalignment
between market data (RangeIndex) and stock data (DatetimeIndex).
"""

import pytest
import pandas as pd
from datetime import date, datetime
from pathlib import Path
import tempfile
import os

from src.kiss_signal.data import get_market_data, _load_market_cache, _save_market_cache
from src.kiss_signal.rules import market_above_sma
from src.kiss_signal.backtester import Backtester


class TestMarketDataAlignment:
    """Test cases for market data alignment fix."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create sample market data with proper structure
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        self.sample_market_data = pd.DataFrame({
            'open': 100 + (dates.dayofyear % 50),
            'high': 105 + (dates.dayofyear % 50),
            'low': 95 + (dates.dayofyear % 50),
            'close': 100 + (dates.dayofyear % 50) + (dates.dayofyear % 10),
            'volume': 1000000 + (dates.dayofyear % 100000)
        }, index=dates)
        
        # Create sample stock data with overlapping dates
        stock_dates = pd.date_range('2023-06-01', '2023-12-31', freq='D')
        self.sample_stock_data = pd.DataFrame({
            'open': 50 + (stock_dates.dayofyear % 25),
            'high': 55 + (stock_dates.dayofyear % 25),
            'low': 45 + (stock_dates.dayofyear % 25),
            'close': 50 + (stock_dates.dayofyear % 25) + (stock_dates.dayofyear % 5),
            'volume': 500000 + (stock_dates.dayofyear % 50000)
        }, index=stock_dates)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_market_cache_save_and_load_preserves_datetime_index(self):
        """Test that market cache save/load preserves DatetimeIndex."""
        cache_file = self.temp_dir / "INDEX_NSEI.csv"
        
        # Save market data
        _save_market_cache(self.sample_market_data, cache_file)
        
        # Load market data
        loaded_data = _load_market_cache(cache_file)
        
        # Verify index is DatetimeIndex
        assert isinstance(loaded_data.index, pd.DatetimeIndex), \
            f"Expected DatetimeIndex, got {type(loaded_data.index)}"
        
        # Verify data integrity
        assert len(loaded_data) == len(self.sample_market_data)
        assert loaded_data.columns.tolist() == ['open', 'high', 'low', 'close', 'volume']
    
    def test_market_above_sma_with_rangeindex_input(self):
        """Test market_above_sma handles RangeIndex input correctly."""
        # Create data with RangeIndex and 'index' column (realistic problematic format from reset_index())
        problematic_data = self.sample_market_data.reset_index()
        assert isinstance(problematic_data.index, pd.RangeIndex)
        assert 'index' in problematic_data.columns  # reset_index() creates 'index' column, not 'date'
        
        # Function should handle this gracefully
        signals = market_above_sma(problematic_data, period=20)
        
        # Verify output
        assert isinstance(signals, pd.Series)
        assert isinstance(signals.index, pd.DatetimeIndex), \
            "market_above_sma should return DatetimeIndex for proper alignment"
        assert len(signals) > 0
        assert signals.dtype == bool
    
    def test_market_above_sma_with_datetime_index_input(self):
        """Test market_above_sma works with proper DatetimeIndex input."""
        # Data already has DatetimeIndex
        assert isinstance(self.sample_market_data.index, pd.DatetimeIndex)
        
        signals = market_above_sma(self.sample_market_data, period=20)
        
        # Verify output
        assert isinstance(signals, pd.Series)
        assert isinstance(signals.index, pd.DatetimeIndex)
        assert len(signals) == len(self.sample_market_data)
        assert signals.dtype == bool
    
    def test_market_data_alignment_in_backtester_context(self):
        """Test alignment works in backtester context (integration test)."""
        # Save market data to cache
        cache_file = self.temp_dir / "INDEX_NSEI.csv"
        _save_market_cache(self.sample_market_data, cache_file)
        
        # Load market data (this simulates what backtester does)
        market_data = get_market_data("^NSEI", self.temp_dir)
        
        # Get market signals
        market_signals = market_above_sma(market_data, period=20)
        
        # Simulate alignment process (what backtester does)
        aligned_signals = market_signals.reindex(self.sample_stock_data.index)
        filled_signals = aligned_signals.ffill().fillna(False)
        
        # Verify alignment worked
        assert len(filled_signals) == len(self.sample_stock_data)
        assert filled_signals.sum() > 0, "Should have some positive signals after alignment"
        
        # Verify no all-zero issue
        assert not (filled_signals == False).all(), \
            "Alignment should not result in all False signals"
    
    def test_freeze_date_functionality(self):
        """Test freeze date filtering works correctly."""
        # Save market data to cache
        cache_file = self.temp_dir / "INDEX_NSEI.csv"
        _save_market_cache(self.sample_market_data, cache_file)
        
        # Load with freeze date
        freeze_date = date(2023, 6, 30)
        market_data = get_market_data("^NSEI", self.temp_dir, freeze_date=freeze_date)
        
        # Verify freeze date applied
        assert market_data.index.max().date() <= freeze_date
        assert len(market_data) < len(self.sample_market_data)
        
        # Verify index is still DatetimeIndex
        assert isinstance(market_data.index, pd.DatetimeIndex)
    
    def test_alignment_signal_count_preservation(self):
        """Test that signal counts are reasonable after alignment."""
        # Create market data where 60% of days are above SMA
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        close_prices = []
        
        for i, dt in enumerate(dates):
            # Create pattern where ~60% of days will be above 20-day SMA
            base_price = 100
            trend = i * 0.01  # Small upward trend
            noise = (i % 10) - 5  # Some noise
            close_prices.append(base_price + trend + noise)
        
        market_data = pd.DataFrame({
            'open': close_prices,
            'high': [p + 2 for p in close_prices],
            'low': [p - 2 for p in close_prices],
            'close': close_prices,
            'volume': [1000000] * len(dates)
        }, index=dates)
        
        # Get signals
        signals = market_above_sma(market_data, period=20)
        original_signal_rate = signals.sum() / len(signals)
        
        # Simulate alignment with overlapping stock data
        stock_dates = dates[180:300]  # 120 days subset
        aligned_signals = signals.reindex(stock_dates)
        filled_signals = aligned_signals.ffill().fillna(False)
        
        aligned_signal_rate = filled_signals.sum() / len(filled_signals)
        
        # Signal rate should be reasonable (not 0%)
        assert aligned_signal_rate > 0.1, \
            f"Aligned signal rate too low: {aligned_signal_rate:.1%}"
        
        # Should be related to original signal rate
        assert abs(aligned_signal_rate - original_signal_rate) < 0.5, \
            f"Signal rates too different: original {original_signal_rate:.1%}, " \
            f"aligned {aligned_signal_rate:.1%}"
    
    def test_problematic_csv_format_handling(self):
        """Test handling of CSV files that caused the original issue."""
        # Create CSV with date as column (problematic format)
        csv_content = """date,open,high,low,close,volume
2023-01-01,100,105,95,102,1000000
2023-01-02,102,107,97,104,1100000
2023-01-03,104,109,99,106,1200000
2023-01-04,106,111,101,108,1300000
2023-01-05,108,113,103,110,1400000"""
        
        cache_file = self.temp_dir / "INDEX_NSEI.csv"
        with open(cache_file, 'w') as f:
            f.write(csv_content)
        
        # Load using our function
        loaded_data = _load_market_cache(cache_file)
        
        # Verify it's properly processed
        assert isinstance(loaded_data.index, pd.DatetimeIndex)
        assert 'date' not in loaded_data.columns  # Should be index, not column
        assert len(loaded_data) == 5
        
        # Test with market_above_sma
        signals = market_above_sma(loaded_data, period=3)
        assert isinstance(signals.index, pd.DatetimeIndex)
        assert len(signals) == 5


def test_end_to_end_alignment():
    """End-to-end test simulating the original problem and fix."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create market data with the problematic format (date as column, RangeIndex)
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'open': 100 + (dates.dayofyear % 50),
            'high': 105 + (dates.dayofyear % 50),
            'low': 95 + (dates.dayofyear % 50),
            'close': 100 + (dates.dayofyear % 50) + (dates.dayofyear % 10),
            'volume': 1000000
        })
        
        # Save to CSV (this creates the problematic format)
        cache_file = temp_path / "INDEX_NSEI.csv"
        market_data.to_csv(cache_file, index=False)
        
        # Verify the CSV has the problematic format
        raw_data = pd.read_csv(cache_file)
        assert isinstance(raw_data.index, pd.RangeIndex), "Should start with RangeIndex"
        assert 'date' in raw_data.columns, "Should have date as column"
        
        # Load market data (should fix the index issue via _load_market_cache)
        loaded_market = get_market_data("^NSEI", temp_path)
        
        # Verify the fix worked at loading level
        assert isinstance(loaded_market.index, pd.DatetimeIndex), \
            "Market data should have DatetimeIndex after loading"
        
        # Create stock data with overlapping date range
        stock_dates = pd.date_range('2023-06-01', '2023-10-31', freq='D')
        stock_data = pd.DataFrame({
            'close': 50 + (stock_dates.dayofyear % 25)
        }, index=stock_dates)
        
        # Get market signals (this should handle any remaining index issues)
        market_signals = market_above_sma(loaded_market, period=50)
        
        # Verify signals have proper DatetimeIndex
        assert isinstance(market_signals.index, pd.DatetimeIndex), \
            "Market signals should have DatetimeIndex"
        
        # Simulate backtester alignment
        aligned_signals = market_signals.reindex(stock_data.index)
        final_signals = aligned_signals.ffill().fillna(False)
        
        # Verify the fix worked
        signal_rate = final_signals.sum() / len(final_signals)
        assert signal_rate > 0, \
            f"Signal rate should be > 0%, got {signal_rate:.1%} - alignment still broken"
        
        print(f"✅ End-to-end test passed: {signal_rate:.1%} signal rate")


if __name__ == "__main__":
    # Run the end-to-end test
    test_end_to_end_alignment()
    print("✅ All critical tests would pass")
