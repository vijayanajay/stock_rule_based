"""Position tracking and management module."""

import logging
import sqlite3
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Represents a stock position."""
    symbol: str
    quantity: int
    avg_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    last_updated: datetime

    def __post_init__(self) -> None:
        """Calculate derived fields after initialization."""
        self.market_value = Decimal(str(self.current_price)) * self.quantity
        cost_basis = self.avg_cost * self.quantity
        self.unrealized_pnl = self.market_value - cost_basis

@dataclass
class Trade:
    """Represents a trade transaction."""
    symbol: str
    quantity: int
    price: Decimal
    trade_date: date
    trade_type: str  # 'BUY' or 'SELL'
    strategy_id: Optional[int] = None

def calculate_position_from_trades(symbol: str, trades: List[Trade]) -> Optional[Position]:
    """Calculate current position from trade history."""
    if not trades:
        return None
    
    total_quantity = 0
    total_cost = Decimal('0')
    
    for trade in trades:
        if trade.trade_type == 'BUY':
            total_quantity += trade.quantity
            total_cost += trade.quantity * trade.price
        elif trade.trade_type == 'SELL':
            total_quantity -= trade.quantity
            # FIFO cost basis reduction (simplified)
            if total_quantity > 0:
                avg_cost = total_cost / (total_quantity + trade.quantity)
                total_cost = avg_cost * total_quantity
    
    if total_quantity <= 0:
        return None
    
    avg_cost = total_cost / total_quantity
    
    # Get current price (placeholder - would integrate with data module)
    current_price = Decimal('100.0')  # TODO: Integrate with data.get_current_price()
    
    return Position(
        symbol=symbol,
        quantity=total_quantity,
        avg_cost=avg_cost,
        current_price=current_price,
        market_value=Decimal('0'),  # Will be calculated in __post_init__
        unrealized_pnl=Decimal('0'),  # Will be calculated in __post_init__
        last_updated=datetime.now()
    )

def save_trade(db_path: str, trade: Trade) -> None:
    """Save a trade to the database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trades (symbol, quantity, price, trade_date, trade_type, strategy_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            trade.symbol,
            trade.quantity,
            str(trade.price),
            trade.trade_date.isoformat(),
            trade.trade_type,
            trade.strategy_id
        ))
        conn.commit()

def get_trades_for_symbol(db_path: str, symbol: str) -> List[Trade]:
    """Get all trades for a specific symbol."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, quantity, price, trade_date, trade_type, strategy_id
            FROM trades
            WHERE symbol = ?
            ORDER BY trade_date
        """, (symbol,))
        
        trades = []
        for row in cursor.fetchall():
            trades.append(Trade(
                symbol=row[0],
                quantity=row[1],
                price=Decimal(row[2]),
                trade_date=datetime.fromisoformat(row[3]).date(),
                trade_type=row[4],
                strategy_id=row[5]
            ))
        
        return trades

def get_current_positions(db_path: str) -> Dict[str, Position]:
    """Get all current positions from trade history."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM trades")
        symbols = [row[0] for row in cursor.fetchall()]
    
    positions = {}
    for symbol in symbols:
        trades = get_trades_for_symbol(db_path, symbol)
        position = calculate_position_from_trades(symbol, trades)
        if position:
            positions[symbol] = position
    
    return positions

def update_position_prices(db_path: str, price_data: Dict[str, Decimal]) -> None:
    """Update current prices for all positions."""
    positions = get_current_positions(db_path)
    
    for symbol, position in positions.items():
        if symbol in price_data:
            position.current_price = price_data[symbol]
            position.__post_init__()  # Recalculate derived fields
