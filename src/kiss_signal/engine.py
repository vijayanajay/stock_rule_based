"""Core analysis engine that orchestrates all components."""

import logging
from typing import Dict, Any
from datetime import date

from .config import Config
from . import data

__all__ = ["run_analysis"]

logger = logging.getLogger(__name__)


def run_analysis(config: Config) -> Dict[str, Any]:
    """Run the complete signal analysis pipeline.
    
    Args:
        config: Validated configuration object containing all settings
        
    Returns:
        Dictionary containing analysis results and signals
        
    Raises:
        Exception: If any step in the analysis pipeline fails
    """
    logger.debug("Starting analysis pipeline")
    
    # Step 1: Refresh market data if needed
    freeze_date = getattr(config, 'freeze_date', None)
    
    if freeze_date:
        logger.debug(f"Freeze mode active: {freeze_date}")
        results = {}  # Skip data refresh in freeze mode
    else:
        logger.debug("Refreshing market data")
        results = data.refresh_market_data(
            universe_path=config.universe_path,
            cache_dir=config.cache_dir,
            refresh_days=config.cache_refresh_days,
            years=config.historical_data_years,
            freeze_date=freeze_date
        )
    
    # Step 2: Generate signals (placeholder for now)
    # TODO: Integrate with backtester and signal_generator modules
    signals = {
        "refresh_results": results,
        "analysis_date": date.today().isoformat(),
        "signals": []  # Placeholder for actual signals
    }
    
    logger.debug("Analysis pipeline completed")
    return signals
