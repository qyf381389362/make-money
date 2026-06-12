import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, get_db
from main import app
from models import Position, DailySnapshot
from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)

def test_refresh_prices_no_positions():
    response = client.post("/prices/refresh")
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] == 0
    assert data["skipped"] == 0
    assert data["errors"] == []

@patch("routers.prices.fetch_prices")
def test_refresh_prices_success_and_skipped(mock_fetch):
    db = TestingSessionLocal()
    pos1 = Position(symbol="600519", name="贵州茅台", asset_type="stock", shares=Decimal("10"), avg_cost=Decimal("1500"))
    pos2 = Position(symbol="000001", name="平安银行", asset_type="stock", shares=Decimal("100"), avg_cost=Decimal("10"))
    db.add_all([pos1, pos2])
    db.commit()

    # Pre-add snapshot for 000001 for today so it gets skipped
    today = date.today()
    snap_existing = DailySnapshot(symbol="000001", date=today, close_price=Decimal("10.5"))
    db.add(snap_existing)
    db.commit()
    db.close()

    # Mock fetch_prices return: {symbol: (price, date_str)}
    mock_fetch.return_value = (
        {
            "600519": (1510.0, today.isoformat()),
            "000001": (10.5, today.isoformat()),
        },
        []
    )

    response = client.post("/prices/refresh")
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] == 1  # 600519 updated
    assert data["skipped"] == 1  # 000001 skipped because of existing
    assert data["errors"] == []

    # Verify 600519 snapshot in DB
    db = TestingSessionLocal()
    snap = db.query(DailySnapshot).filter(DailySnapshot.symbol == "600519").first()
    assert snap is not None
    assert float(snap.close_price) == 1510.0
    db.close()

@patch("routers.prices.fetch_prices")
def test_refresh_prices_integrity_error(mock_fetch):
    db = TestingSessionLocal()
    pos = Position(symbol="600519", name="贵州茅台", asset_type="stock", shares=Decimal("10"), avg_cost=Decimal("1500"))
    db.add(pos)
    db.commit()
    db.close()

    today = date.today()
    mock_fetch.return_value = (
        {
            "600519": (1510.0, today.isoformat()),
        },
        []
    )

    # We mock db.flush to raise IntegrityError on the first call
    original_flush = Session.flush
    call_count = 0
    def mock_flush(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IntegrityError("mock statement", "mock params", Exception("mock orig"))
        return original_flush(self, *args, **kwargs)

    with patch.object(Session, "flush", mock_flush):
        response = client.post("/prices/refresh")
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 0
        assert data["skipped"] == 0
        assert len(data["errors"]) == 1
        assert "写入快照冲突" in data["errors"][0]


@patch("routers.prices.fetch_fund_prices")
@patch("routers.prices.fetch_prices")
def test_refresh_prices_routing(mock_fetch_stock, mock_fetch_fund):
    db = TestingSessionLocal()
    pos1 = Position(symbol="600519", name="贵州茅台", asset_type="stock", shares=Decimal("10"), avg_cost=Decimal("1500"))
    pos2 = Position(symbol="161725", name="招商中证白酒", asset_type="fund", shares=Decimal("1000"), avg_cost=Decimal("1"))
    db.add_all([pos1, pos2])
    db.commit()
    db.close()

    today = date.today()
    mock_fetch_stock.return_value = ({"600519": (1510.0, today.isoformat())}, [])
    mock_fetch_fund.return_value = ({"161725": (0.8350, today.isoformat())}, [])

    response = client.post("/prices/refresh")
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] == 2
    assert data["errors"] == []

    # 验证是否两个 mock 方法均被正确参数调用
    mock_fetch_stock.assert_called_once_with(["600519"])
    mock_fetch_fund.assert_called_once_with(["161725"])


from services.baostock_service import fetch_fund_prices

@patch("httpx.Client.get")
def test_fetch_fund_prices_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = 'jsonpgz({"fundcode":"161725","name":"招商中证白酒","dwjz":"0.8350","jzrq":"2026-06-08"});'
    mock_get.return_value = mock_resp

    results, errors = fetch_fund_prices(["161725"])
    assert "161725" in results
    assert results["161725"] == (0.8350, "2026-06-08")
    assert not errors


@patch("httpx.Client.get")
def test_fetch_fund_prices_error_response(mock_get):
    # 测试天天基金非标或错误响应
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_get.return_value = mock_resp

    results, errors = fetch_fund_prices(["161725"])
    assert "161725" not in results
    assert len(errors) == 1
    assert "状态码异常" in errors[0]
