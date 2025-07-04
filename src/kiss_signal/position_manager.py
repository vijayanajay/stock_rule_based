"""
Manages open positions, calculating metrics and determining their status.
"""

import logging
from datetime import date
from typing import List, Dict, Any, Tuple
import pandas as pd

from .config import Config
from . import data

logger = logging.getLogger(__name__)

def _calculate_open_position_metrics(
    open_positions: List[Dict[str, Any]], 
    config: Config
) -> List[Dict[str, Any]]:
    """
    Augments a list of open positions with calculated metrics like current
    return, days held, and relative performance against the NIFTY index.
    
    Args:
        open_positions: A list of open position dictionaries.
        config: The application's configuration object.
        
    Returns:
        The list of open positions, with each dictionary augmented with new
        metric key-value pairs.
    """
    
    augmented_positions = []
    run_date = config.freeze_date or date.today()

    for pos in open_positions:
        try:
            entry_date = date.fromisoformat(pos["entry_date"])
            days_held = (run_date - entry_date).days

            price_data = data.get_price_data(
                symbol=pos["symbol"],
                cache_dir=config.cache_dir,
                refresh_days=config.cache_refresh_days,
                start_date=entry_date,
                end_date=run_date,
                freeze_date=config.freeze_date,
                years=config.historical_data_years
            )
            nifty_data = data.get_price_data(
                symbol="^NSEI",
                cache_dir=config.cache_dir,
                refresh_days=config.cache_refresh_days,
                start_date=entry_date,
                end_date=run_date,
                freeze_date=config.freeze_date,
                years=config.historical_data_years
            )

            current_price = price_data['close'].iloc[-1] if price_data is not None and not price_data.empty else pos['entry_price']
            return_pct = (current_price - pos['entry_price']) / pos['entry_price'] * 100 if pos['entry_price'] > 0 else 0.0
            
            nifty_return_pct = 0.0
            if nifty_data is not None and not nifty_data.empty and nifty_data['close'].iloc[0] > 0:
                nifty_return_pct = (nifty_data['close'].iloc[-1] - nifty_data['close'].iloc[0]) / nifty_data['close'].iloc[0] * 100

            pos.update({
                'current_price': current_price,
                'return_pct': return_pct,
                'nifty_return_pct': nifty_return_pct,
                'days_held': days_held
            })
            augmented_positions.append(pos)
        except Exception as e:
            logger.warning(f"Could not process position for {pos['symbol']}: {e}")
            pos.update({
                "current_price": None, "return_pct": None,
                "nifty_return_pct": None, "days_held": (run_date - date.fromisoformat(pos["entry_date"])).days,
            })
            augmented_positions.append(pos)
            
    return augmented_positions


def _manage_open_positions(
    open_positions: List[Dict[str, Any]], 
    config: Config
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Separates open positions into two lists: those to hold and those to close.
    
    Args:
        open_positions: A list of open position dictionaries.
        config: The application's configuration object.
        
    Returns:
        A tuple containing two lists: (positions_to_hold, positions_to_close).
    """
    
    positions_to_hold = []
    positions_to_close = []
    run_date = config.freeze_date or date.today()

    # First, calculate metrics for all positions
    all_positions_with_metrics = _calculate_open_position_metrics(open_positions, config)

    # Now, separate them based on the hold period
    for pos in all_positions_with_metrics:
        if pos['days_held'] >= config.hold_period:
            # Add exit information to the position
            pos.update({
                'exit_date': run_date.strftime('%Y-%m-%d'),
                'exit_price': pos['current_price'],
                'final_return_pct': pos['return_pct'],
                'final_nifty_return_pct': pos['nifty_return_pct'],
            })
            positions_to_close.append(pos)
        else:
            positions_to_hold.append(pos)
            
    return positions_to_hold, positions_to_close
