import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date
from decimal import Decimal
import sys
import os

# 确保 python 寻路正常
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, get_db
from main import app
from models import Position, JournalEntry

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


def test_record_trade_validation():
    # 先创建持仓
    client.post(
        "/positions",
        json={
            "symbol": "600519",
            "name": "贵州茅台",
            "asset_type": "stock",
            "shares": 0,
            "avg_cost": 0,
        },
    )

    # 1. 验证 shares 必须大于 0 (gt=0)
    response = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "buy",
            "shares": 0,
            "price": 1500,
            "trade_date": "2026-06-08",
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "buy",
            "shares": -10,
            "price": 1500,
            "trade_date": "2026-06-08",
        },
    )
    assert response.status_code == 422

    # 2. 验证 price 必须大于 0 (gt=0)
    response = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "buy",
            "shares": 10,
            "price": 0,
            "trade_date": "2026-06-08",
        },
    )
    assert response.status_code == 422


def test_record_trade_flow():
    # 1. 创建持仓
    resp = client.post(
        "/positions",
        json={
            "symbol": "600519",
            "name": "贵州茅台",
            "asset_type": "stock",
            "shares": 0,
            "avg_cost": 0,
        },
    )
    assert resp.status_code == 201

    # 2. 首次买入 100 股，价格 1500
    resp = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "buy",
            "shares": 100,
            "price": 1500,
            "reason": "看好茅台长期价值",
            "trade_date": "2026-06-08",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["pnl"] is None
    assert float(data["avg_cost_at_time"]) == 0.0

    # 校验持仓变化
    resp = client.get("/positions")
    pos_list = resp.json()
    pos = [p for p in pos_list if p["symbol"] == "600519"][0]
    assert float(pos["shares"]) == 100.0
    assert float(pos["avg_cost"]) == 1500.0

    # 3. 追加买入 100 股，价格 1600
    resp = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "buy",
            "shares": 100,
            "price": 1600,
            "trade_date": "2026-06-08",
        },
    )
    assert resp.status_code == 201
    
    # 校验均价更新: (100 * 1500 + 100 * 1600) / 200 = 1550
    resp = client.get("/positions")
    pos = [p for p in resp.json() if p["symbol"] == "600519"][0]
    assert float(pos["shares"]) == 200.0
    assert float(pos["avg_cost"]) == 1550.0

    # 4. 超卖保护拦截（卖出 250 股，超过持仓的 200 股）
    resp = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "sell",
            "shares": 250,
            "price": 1700,
            "trade_date": "2026-06-08",
        },
    )
    assert resp.status_code == 422
    assert "超过持仓" in resp.json()["detail"]

    # 5. 部分卖出 50 股，价格 1700
    # 预期 P&L = (1700 - 1550) * 50 = 7500
    resp = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "sell",
            "shares": 50,
            "price": 1700,
            "trade_date": "2026-06-08",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["pnl"]) == 7500.0
    assert float(data["avg_cost_at_time"]) == 1550.0

    # 校验均价保持不变，持仓减少
    resp = client.get("/positions")
    pos = [p for p in resp.json() if p["symbol"] == "600519"][0]
    assert float(pos["shares"]) == 150.0
    assert float(pos["avg_cost"]) == 1550.0

    # 6. 清仓（卖出 150 股，价格 1800）
    # 预期 P&L = (1800 - 1550) * 150 = 37500
    resp = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "sell",
            "shares": 150,
            "price": 1800,
            "trade_date": "2026-06-08",
        },
    )
    assert resp.status_code == 201
    assert float(resp.json()["pnl"]) == 37500.0

    # 校验持仓是否已被彻底删除（列表里不能再找到 600519）
    resp = client.get("/positions")
    assert not any(p["symbol"] == "600519" for p in resp.json())

    # 7. 重新买入前，必须重新添加持仓（因为已经清仓被删除了）
    resp = client.post(
        "/positions",
        json={
            "symbol": "600519",
            "name": "贵州茅台",
            "asset_type": "stock",
            "shares": 0,
            "avg_cost": 0,
        },
    )
    assert resp.status_code == 201

    # 8. 重新买入 100 股，价格 1400
    # 清仓后再次买入，均价重置为 1400
    resp = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "buy",
            "shares": 100,
            "price": 1400,
            "trade_date": "2026-06-08",
        },
    )
    assert resp.status_code == 201

    resp = client.get("/positions")
    pos = [p for p in resp.json() if p["symbol"] == "600519"][0]
    assert float(pos["shares"]) == 100.0
    assert float(pos["avg_cost"]) == 1400.0


def test_record_trade_position_not_found():
    # 验证交易记录在持仓不存在时报 404
    response = client.post(
        "/journal",
        json={
            "symbol": "999999",
            "action": "buy",
            "shares": 100,
            "price": 10,
            "trade_date": "2026-06-08",
        },
    )
    assert response.status_code == 404
    assert "不存在" in response.json()["detail"]


def test_record_trade_buy_new_shares_invalid():
    # 模拟数据库中已存在非法的负持仓（如 -10 股），然后买入 10 股，导致总持仓 <= 0，触发 422
    db = TestingSessionLocal()
    pos = Position(symbol="600519", name="贵州茅台", asset_type="stock", shares=Decimal("-10"), avg_cost=Decimal("1500"))
    db.add(pos)
    db.commit()
    db.close()

    response = client.post(
        "/journal",
        json={
            "symbol": "600519",
            "action": "buy",
            "shares": 10,
            "price": 1500,
            "trade_date": "2026-06-08",
        },
    )
    assert response.status_code == 422
    assert "份额必须大于 0" in response.json()["detail"]


def test_list_journal_filtering():
    # 创建持仓
    client.post(
        "/positions",
        json={"symbol": "600519", "name": "贵州茅台", "asset_type": "stock", "shares": 0, "avg_cost": 0},
    )
    client.post(
        "/positions",
        json={"symbol": "000001", "name": "平安银行", "asset_type": "stock", "shares": 0, "avg_cost": 0},
    )

    # 记录几笔交易
    client.post(
        "/journal",
        json={"symbol": "600519", "action": "buy", "shares": 100, "price": 1500, "trade_date": "2026-06-08"},
    )
    client.post(
        "/journal",
        json={"symbol": "000001", "action": "buy", "shares": 100, "price": 10, "trade_date": "2026-06-08"},
    )

    # 1. 列表不带 symbol -> 应该返回全部交易记录（2条）
    response = client.get("/journal")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # 2. 列表带 symbol="600519" -> 应该只返回 1 条
    response = client.get("/journal", params={"symbol": "600519"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "600519"


def test_record_trade_with_ai_audit_empty_reason():
    # 1. 验证无 reason 时，不调用大模型，直接标记为理性分析
    client.post(
        "/positions",
        json={"symbol": "000002", "name": "万科A", "asset_type": "stock", "shares": 0, "avg_cost": 0},
    )
    resp = client.post(
        "/journal",
        json={
            "symbol": "000002",
            "action": "buy",
            "shares": 100,
            "price": 10,
            "trade_date": "2026-06-08",
            "reason": ""
        },
    )
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    # 模拟测试环境下的 SessionLocal 运行后台任务
    with patch("routers.journal.SessionLocal", TestingSessionLocal):
        from routers.journal import audit_journal_entry_task
        audit_journal_entry_task(entry_id)

    # 重新查询数据库
    db = TestingSessionLocal()
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    assert entry.motivation_type == "理性分析"
    assert "未填写" in entry.ai_audit
    db.close()


from unittest.mock import patch

def test_record_trade_with_ai_audit_mocked_success():
    # 2. 验证有 reason 时，异步触发 AI 审计成功
    client.post(
        "/positions",
        json={"symbol": "000003", "name": "PT", "asset_type": "stock", "shares": 0, "avg_cost": 0},
    )
    resp = client.post(
        "/journal",
        json={
            "symbol": "000003",
            "action": "buy",
            "shares": 100,
            "price": 10,
            "trade_date": "2026-06-08",
            "reason": "看它天天涨，感觉还要再涨点，赶紧上车"
        },
    )
    assert resp.status_code == 201
    entry_id = resp.json()["id"]
    
    mock_audit = ("追涨杀跌", "看到别人买就盲目跟风，属于明显的羊群效应心理。")
    with patch("routers.journal.SessionLocal", TestingSessionLocal):
        with patch("routers.journal.audit_decision", return_value=mock_audit) as mock_func:
            from routers.journal import audit_journal_entry_task
            audit_journal_entry_task(entry_id)
            mock_func.assert_called_once()
        
    # 查询数据库，确认字段更新
    db = TestingSessionLocal()
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    assert entry is not None
    assert entry.motivation_type == "追涨杀跌"
    assert "羊群效应" in entry.ai_audit
    db.close()

