import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.baostock_service import _to_bs_code, fetch_prices

def test_to_bs_code():
    # 5, 6, 9 开头为上海（sh）
    assert _to_bs_code("600519") == "sh.600519"
    assert _to_bs_code("510300") == "sh.510300"
    assert _to_bs_code("900001") == "sh.900001"
    # 其他开头为深圳（sz）
    assert _to_bs_code("000001") == "sz.000001"
    assert _to_bs_code("300750") == "sz.300750"

@patch("services.baostock_service.bs")
def test_fetch_prices_success(mock_bs):
    # Mock login/logout
    mock_bs.login = MagicMock()
    mock_bs.logout = MagicMock()
    
    # Mock query_history_k_data_plus return
    mock_rs = MagicMock()
    mock_rs.error_code = "0"
    # Set up mock_rs.next() to return True once, then False
    mock_rs.next.side_effect = [True, False]
    mock_rs.get_row_data.return_value = ["2026-06-08", "1500.0"]
    mock_bs.query_history_k_data_plus.return_value = mock_rs

    results, errors = fetch_prices(["600519"])
    
    assert "600519" in results
    assert results["600519"] == (1500.0, "2026-06-08")
    assert not errors

@patch("services.baostock_service.bs")
def test_fetch_prices_no_data(mock_bs):
    mock_bs.login = MagicMock()
    mock_bs.logout = MagicMock()
    
    mock_rs = MagicMock()
    mock_rs.error_code = "0"
    mock_rs.next.return_value = False
    mock_rs.error_msg = "No data"
    mock_bs.query_history_k_data_plus.return_value = mock_rs

    results, errors = fetch_prices(["600519"])
    
    assert "600519" not in results
    assert len(errors) == 1
    assert "无数据" in errors[0]

@patch("services.baostock_service.bs")
def test_fetch_prices_parse_error(mock_bs):
    mock_bs.login = MagicMock()
    mock_bs.logout = MagicMock()
    
    mock_rs = MagicMock()
    mock_rs.error_code = "0"
    mock_rs.next.side_effect = [True, False]
    mock_rs.get_row_data.return_value = ["2026-06-08", "invalid_price"]
    mock_bs.query_history_k_data_plus.return_value = mock_rs

    results, errors = fetch_prices(["600519"])
    
    assert "600519" not in results
    assert len(errors) == 1
    assert "价格解析失败" in errors[0]
