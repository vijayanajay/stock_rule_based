"""Tests for migrated business logic now residing in cli.py.

Focused on small, isolated behaviors. Avoids duplication with existing reporter tests.
Covers:
- check_exit_conditions (basic triggers only; comprehensive variants existed in old reporter tests)
- calculate_position_returns (basic + invalid)
- identify_new_signals filtering
- process_open_positions minimal flow (hold vs close)
- update_positions_and_generate_report_data integration skeleton

Constraints: keep tests short, no external I/O, patch persistence & data calls.
"""
from datetime import date
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch, Mock

import pandas as pd
import pytest

from kiss_signal.config import Config, RuleDef
from kiss_signal import cli

@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    # Ensure universe file exists to satisfy strict validator (minimal content)
    universe_file = tmp_path / 'u.csv'
    if not universe_file.exists():
        universe_file.write_text('symbol\nDUMMY.NS\n', encoding='utf-8')
    return Config(
        universe_path=str(universe_file),
        historical_data_years=1,
        cache_dir=str(tmp_path / 'cache'),
        hold_period=20,
        database_path=str(tmp_path / 'test.db'),
        min_trades_threshold=5,
        edge_score_weights={'win_pct':0.6,'sharpe':0.4},
        edge_score_threshold=0.5,
        reports_output_dir=str(tmp_path / 'reports'),
        freeze_date=date(2025,1,1)
    )

# ---------------------------------------------------------------------------
# check_exit_conditions
# ---------------------------------------------------------------------------

def test_check_exit_conditions_stop_loss() -> None:
    pos = {'symbol':'X','entry_price':100}
    df = pd.DataFrame({'close':[95],'high':[96],'low':[94]})
    cond = [RuleDef(name='sl', type='stop_loss_pct', params={'percentage':0.05})]
    reason = cli.check_exit_conditions(pos, df, 94, 96, cond, days_held=3, hold_period=20)
    assert reason and 'Stop-loss' in reason

def test_check_exit_conditions_time_based() -> None:
    pos = {'symbol':'X','entry_price':100}
    df = pd.DataFrame({'close':[100],'high':[101],'low':[99]})
    reason = cli.check_exit_conditions(pos, df, 99, 101, [], days_held=20, hold_period=20)
    assert 'holding period' in (reason or '')

# ---------------------------------------------------------------------------
# calculate_position_returns
# ---------------------------------------------------------------------------

def test_calculate_position_returns_basic() -> None:
    pos = {'symbol':'X','entry_price':100,'entry_date':'2025-01-01'}
    result = cli.calculate_position_returns(pos, 110)
    assert pytest.approx(result['return_pct'], rel=1e-3) == 10.0

def test_calculate_position_returns_invalid_entry() -> None:
    pos = {'symbol':'X','entry_price':0}
    result = cli.calculate_position_returns(pos, 110)
    assert result['return_pct'] == 0.0

# ---------------------------------------------------------------------------
# identify_new_signals
# ---------------------------------------------------------------------------

@patch('kiss_signal.cli.persistence.get_open_positions')
def test_identify_new_signals_filters(mock_get_open, tmp_path: Path) -> None:
    mock_get_open.return_value = [{'symbol':'HOLD'}]
    results: List[Dict[str, Any]] = [
        {'symbol':'HOLD','rule_stack':[],'edge_score':0.6,'latest_close':10},
        {'symbol':'NEW','rule_stack':[],'edge_score':0.7,'latest_close':20},
    ]
    signals = cli.identify_new_signals(results, tmp_path/'db.db', current_date=date(2025,1,2))
    assert len(signals) == 1 and signals[0]['ticker'] == 'NEW'

# ---------------------------------------------------------------------------
# process_open_positions
# ---------------------------------------------------------------------------

@patch('kiss_signal.cli.persistence.get_open_positions')
@patch('kiss_signal.cli.get_position_pricing')
def test_process_open_positions_close(mock_price, mock_open, cfg: Config, tmp_path: Path) -> None:
    mock_open.return_value = [{'id':1,'symbol':'X','entry_date':'2024-12-20','entry_price':100}]
    # Force pricing triggering stop loss
    mock_price.return_value = {'current_price':90,'current_high':91,'current_low':80,'price_data':pd.DataFrame({'close':[90],'high':[91],'low':[80]})}
    cond = [RuleDef(name='sl', type='stop_loss_pct', params={'percentage':0.05})]
    hold, close = cli.process_open_positions(tmp_path/'db.db', cfg, cond, None)
    assert not hold and len(close) == 1

@patch('kiss_signal.cli.persistence.get_open_positions')
@patch('kiss_signal.cli.get_position_pricing')
def test_process_open_positions_hold(mock_price, mock_open, cfg: Config, tmp_path: Path) -> None:
    mock_open.return_value = [{'id':1,'symbol':'X','entry_date':'2024-12-20','entry_price':100}]
    mock_price.return_value = {'current_price':102,'current_high':103,'current_low':101,'price_data':pd.DataFrame({'close':[102],'high':[103],'low':[101]})}
    hold, close = cli.process_open_positions(tmp_path/'db.db', cfg, [], None)
    assert len(hold) == 1 and not close

# ---------------------------------------------------------------------------
# update_positions_and_generate_report_data (integration skeleton)
# ---------------------------------------------------------------------------

@patch('kiss_signal.cli.persistence.get_open_positions')
@patch('kiss_signal.cli.persistence.add_new_positions_from_signals')
@patch('kiss_signal.cli.persistence.close_positions_batch')
@patch('kiss_signal.cli.data.get_price_data')
def test_update_positions_and_generate_report_data(mock_price, mock_close, mock_add, mock_open, cfg: Config, tmp_path: Path) -> None:
    mock_open.return_value = []
    # NIFTY data minimal
    mock_price.return_value = pd.DataFrame({'close':[100,101]})
    results = [{'symbol':'NEW','rule_stack':[],'edge_score':0.8,'latest_close':50.0}]
    out = cli.update_positions_and_generate_report_data(tmp_path/'db.db', 'ts', cfg, Mock(exit_conditions=[]), results)
    assert 'new_buys' in out and len(out['new_buys']) == 1
