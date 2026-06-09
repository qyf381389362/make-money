import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, timedelta
from decimal import Decimal
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

def test_list_positions_empty():
    response = client.get("/positions")
    assert response.status_code == 200
    assert response.json() == []

def test_list_positions_no_snapshots():
    db = TestingSessionLocal()
    pos = Position(symbol="600519", name="贵州茅台", asset_type="stock", shares=Decimal("10"), avg_cost=Decimal("1500"))
    db.add(pos)
    db.commit()
    db.close()

    response = client.get("/positions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "600519"
    assert data[0]["current_price"] is None
    assert data[0]["price_date"] is None
    assert data[0]["is_stale"] is True

def test_list_positions_with_snapshots_and_stale():
    db = TestingSessionLocal()
    pos1 = Position(symbol="600519", name="贵州茅台", asset_type="stock", shares=Decimal("10"), avg_cost=Decimal("1500"))
    pos2 = Position(symbol="000001", name="平安银行", asset_type="stock", shares=Decimal("100"), avg_cost=Decimal("10"))
    db.add_all([pos1, pos2])
    db.commit()

    # pos1 (600519) has two snapshots, one old, one new (today) -> should use new, is_stale=False
    today = date.today()
    three_days_ago = today - timedelta(days=3)
    snap_old = DailySnapshot(symbol="600519", date=three_days_ago, close_price=Decimal("1490"))
    snap_new = DailySnapshot(symbol="600519", date=today, close_price=Decimal("1510"))

    # pos2 (000001) has one snapshot that is 4 days old -> is_stale=True
    four_days_ago = today - timedelta(days=4)
    snap_stale = DailySnapshot(symbol="000001", date=four_days_ago, close_price=Decimal("9.5"))

    db.add_all([snap_old, snap_new, snap_stale])
    db.commit()
    db.close()

    response = client.get("/positions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    p1 = [p for p in data if p["symbol"] == "600519"][0]
    assert float(p1["current_price"]) == 1510.0
    assert p1["price_date"] == today.isoformat()
    assert p1["is_stale"] is False

    p2 = [p for p in data if p["symbol"] == "000001"][0]
    assert float(p2["current_price"]) == 9.5
    assert p2["price_date"] == four_days_ago.isoformat()
    assert p2["is_stale"] is True

def test_create_position():
    # 成功创建
    response = client.post(
        "/positions",
        json={
            "symbol": "600519",
            "name": "贵州茅台",
            "asset_type": "stock",
            "shares": 10,
            "avg_cost": 1500,
        }
    )
    assert response.status_code == 201
    assert response.json()["symbol"] == "600519"

    # 重复创建 -> 409
    response = client.post(
        "/positions",
        json={
            "symbol": "600519",
            "name": "贵州茅台",
            "asset_type": "stock",
            "shares": 10,
            "avg_cost": 1500,
        }
    )
    assert response.status_code == 409

    # 验证 validation ge=0
    response = client.post(
        "/positions",
        json={
            "symbol": "600520",
            "name": "测试",
            "asset_type": "stock",
            "shares": -1,
            "avg_cost": 1500,
        }
    )
    assert response.status_code == 422

    response = client.post(
        "/positions",
        json={
            "symbol": "600520",
            "name": "测试",
            "asset_type": "stock",
            "shares": 10,
            "avg_cost": -10,
        }
    )
    assert response.status_code == 422

def test_delete_position():
    db = TestingSessionLocal()
    pos = Position(symbol="600519", name="贵州茅台", asset_type="stock", shares=Decimal("10"), avg_cost=Decimal("1500"))
    db.add(pos)
    db.commit()
    db.close()

    # 成功删除
    response = client.delete("/positions/600519")
    assert response.status_code == 204

    # 验证是否真的被删除
    response = client.get("/positions")
    assert len(response.json()) == 0

    # 再次删除 -> 404
    response = client.delete("/positions/600519")
    assert response.status_code == 404
