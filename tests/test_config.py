from tempfile import NamedTemporaryFile
from pathlib import Path

from kiss_signal.config import Config

def test_config_database_path_field():
    """Test that database_path field is properly configured."""
    # Create a temporary file for universe_path validation
    with NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("symbol\nRELIANCE.NS\n")
        temp_path = f.name
    
    try:
        config_data = {
            "universe_path": temp_path,
            "edge_score_weights": {
                "win_pct": 0.4,
                "sharpe": 0.6
            },
            "hold_period": 5,
            "database_path": "custom/path/database.db"
        }
        
        config = Config(**config_data)
        
        assert config.database_path == "custom/path/database.db"
    finally:
        Path(temp_path).unlink()

def test_config_database_path_default():
    """Test that database_path has correct default value."""
    # Create a temporary file for universe_path validation
    with NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("symbol\nRELIANCE.NS\n")
        temp_path = f.name
    
    try:
        config_data = {
            "universe_path": temp_path,
            "edge_score_weights": {
                "win_pct": 0.4,
                "sharpe": 0.6
            }
        }
        
        config = Config(**config_data)
        
        assert config.database_path == "data/kiss_signal.db"
    finally:
        Path(temp_path).unlink()