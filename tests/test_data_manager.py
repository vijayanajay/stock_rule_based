"""Tests for Data Manager module."""

import pytest
from pathlib import Path
from kiss_signal.data_manager import DataManager


def test_data_manager_initialization(temp_dir: Path):
    """Test DataManager initialization."""
    dm = DataManager(cache_dir=temp_dir)
    assert dm.cache_dir == temp_dir
    assert dm.freeze_date is None
