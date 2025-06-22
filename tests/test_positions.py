"""Tests for position tracking module."""

import pytest
import sqlite3
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from kiss_signal.positions import (
    Position, Trade, calculate_position_from_trades, save_trade,
    get_trades_for_symbol, get_current_positions
)
from kiss_signal.persistence import create_database


class TestPosition:
    """Test Position dataclass."""
    
    def test_position_initialization(self) -> None:
        """Test position initialization and calculations."""
        pos = Position(
            symbol="TEST",
            quantity=100,
            avg_cost=Decimal("50.0"),
            current_price=Decimal("55.0"),
            market_value=Decimal("0"),  # Will be calculated
            unrealized_pnl=Decimal("0"),  # Will be calculated
            last_updated=datetime.now()
        )
        
        assert pos.market_value == Decimal("5500.0")
        assert pos.unrealized_pnl == Decimal("500.0")


class TestTrade:
    """Test Trade dataclass."""
    
    def test_trade_creation(self) -> None:
        """Test trade creation."""
        trade = Trade(
            symbol="TEST",
            quantity=100,
            price=Decimal("50.0"),
            trade_date=date.today(),
            trade_type="BUY"
        )
        
        assert trade.symbol == "TEST"
        assert trade.quantity == 100
        assert trade.price == Decimal("50.0")
        assert trade.trade_type == "BUY"


class TestPositionCalculation:
    """Test position calculation from trades."""
    
    def test_calculate_position_single_buy(self) -> None:
        """Test position calculation with single buy trade."""
        trades = [
            Trade("TEST", 100, Decimal("50.0"), date.today(), "BUY")
        ]
        
        position = calculate_position_from_trades("TEST", trades)
        
        assert position is not None
        assert position.symbol == "TEST"
        assert position.quantity == 100
        assert position.avg_cost == Decimal("50.0")
    
    def test_calculate_position_multiple_buys(self) -> None:
        """Test position calculation with multiple buy trades."""
        trades = [
            Trade("TEST", 100, Decimal("50.0"), date.today(), "BUY"),
            Trade("TEST", 50, Decimal("60.0"), date.today(), "BUY")
        ]
        
        position = calculate_position_from_trades("TEST", trades)
        
        assert position is not None
        assert position.quantity == 150
        # Weighted average: (100*50 + 50*60) / 150 = 53.33
        assert abs(position.avg_cost - Decimal("53.33")) < Decimal("0.01")
    
    def test_calculate_position_buy_and_sell(self) -> None:
        """Test position calculation with buy and sell trades."""
        trades = [
            Trade("TEST", 100, Decimal("50.0"), date.today(), "BUY"),
            Trade("TEST", 30, Decimal("55.0"), date.today(), "SELL")
        ]
        
        position = calculate_position_from_trades("TEST", trades)
        
        assert position is not None
        assert position.quantity == 70
        assert position.avg_cost == Decimal("50.0")  # Cost basis unchanged
    
    def test_calculate_position_fully_sold(self) -> None:
        """Test position calculation when fully sold."""
        trades = [
            Trade("TEST", 100, Decimal("50.0"), date.today(), "BUY"),
            Trade("TEST", 100, Decimal("55.0"), date.today(), "SELL")
        ]
        
        position = calculate_position_from_trades("TEST", trades)
        
        assert position is None
    
    def test_calculate_position_empty_trades(self) -> None:
        """Test position calculation with empty trades list."""
        position = calculate_position_from_trades("TEST", [])
        assert position is None


class TestDatabaseOperations:
    """Test database operations for position tracking."""
    
    @pytest.fixture
    def temp_db(self) -> str:
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_path = temp_file.name
        temp_file.close()
        
        create_database(db_path)
        yield db_path
        
        Path(db_path).unlink(missing_ok=True)
    
    def test_save_trade(self, temp_db: str) -> None:
        """Test saving trade to database."""
        trade = Trade(
            symbol="TEST",
            quantity=100,
            price=Decimal("50.0"),
            trade_date=date.today(),
            trade_type="BUY",
            strategy_id=1
        )
        
        save_trade(temp_db, trade)
        
        # Verify trade was saved
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades")
            count = cursor.fetchone()[0]
            assert count == 1
    
    def test_get_trades_for_symbol(self, temp_db: str) -> None:
        """Test retrieving trades for a symbol."""
        trades = [
            Trade("TEST", 100, Decimal("50.0"), date.today(), "BUY"),
            Trade("TEST", 50, Decimal("55.0"), date.today(), "SELL"),
            Trade("OTHER", 200, Decimal("30.0"), date.today(), "BUY")
        ]
        
        for trade in trades:
            save_trade(temp_db, trade)
        
        test_trades = get_trades_for_symbol(temp_db, "TEST")
        
        assert len(test_trades) == 2
        assert all(t.symbol == "TEST" for t in test_trades)
    
    def test_get_current_positions(self, temp_db: str) -> None:
        """Test getting current positions from database."""
        trades = [
            Trade("TEST1", 100, Decimal("50.0"), date.today(), "BUY"),
            Trade("TEST2", 200, Decimal("30.0"), date.today(), "BUY"),
            Trade("TEST1", 50, Decimal("55.0"), date.today(), "SELL")
        ]
        
        for trade in trades:
            save_trade(temp_db, trade)
        
        positions = get_current_positions(temp_db)
        
        assert len(positions) == 2
        assert "TEST1" in positions
        assert "TEST2" in positions
        assert positions["TEST1"].quantity == 50
        assert positions["TEST2"].quantity == 200


class TestIntegration:
    """Integration tests for position tracking."""
    
    @pytest.fixture
    def temp_db(self) -> str:
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_path = temp_file.name
        temp_file.close()
        
        create_database(db_path)
        yield db_path
        
        Path(db_path).unlink(missing_ok=True)
    
    def test_full_position_tracking_workflow(self, temp_db: str) -> None:
        """Test complete position tracking workflow."""
        # Execute several trades
        trades = [
            Trade("AAPL", 100, Decimal("150.0"), date.today(), "BUY"),
            Trade("AAPL", 50, Decimal("155.0"), date.today(), "BUY"),
            Trade("AAPL", 30, Decimal("160.0"), date.today(), "SELL"),
            Trade("MSFT", 200, Decimal("300.0"), date.today(), "BUY")
        ]
        
        for trade in trades:
            save_trade(temp_db, trade)
        
        # Get current positions
        positions = get_current_positions(temp_db)
        
        # Verify positions
        assert len(positions) == 2
        assert positions["AAPL"].quantity == 120
        assert positions["MSFT"].quantity == 200
        
        # Verify AAPL average cost calculation
        # (100*150 + 50*155) / 150 = 151.67 for original position
        # After selling 30 shares, remaining 120 shares keep same avg cost
        expected_avg_cost = (Decimal("150.0") * 100 + Decimal("155.0") * 50) / 150
        assert abs(positions["AAPL"].avg_cost - expected_avg_cost) < Decimal("0.01")
