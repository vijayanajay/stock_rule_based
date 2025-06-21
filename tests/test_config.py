import pytest
from your_module import Config  # Adjust the import based on your project structure

def test_config_database_path_field():
    """Test that database_path field is properly configured."""
    config_data = {
        "universe_path": "data/universe.csv",
        "edge_score_weights": {
            "win_pct": 0.4,
            "sharpe": 0.3,
            "total_trades": 0.2,
            "avg_return": 0.1
        },
        "hold_period": 5,
        "database_path": "custom/path/database.db"
    }
    
    config = Config(**config_data)
    
    assert config.database_path == "custom/path/database.db"

def test_config_database_path_default():
    """Test that database_path has correct default value."""
    config_data = {
        "universe_path": "data/universe.csv",
        "edge_score_weights": {
            "win_pct": 0.4,
            "sharpe": 0.3,
            "total_trades": 0.2,
            "avg_return": 0.1
        }
    }
    
    config = Config(**config_data)
    
    assert config.database_path == "data/kiss_signal.db"