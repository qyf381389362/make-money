import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Position

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
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


HEADER = "成交日期,证券代码,证券名称,操作,成交数量,成交价格,手续费,印花税,过户费,成交编号"


def _gbk_csv(*lines: str) -> bytes:
    return ("\n".join([HEADER, *lines]) + "\n").encode("gbk")


def _upload(data: bytes, broker: str = "ths"):
    return client.post(
        "/import/preview",
        files={"file": ("statement.csv", data, "text/csv")},
        data={"broker": broker},
    )


def test_preview_parses_gbk_and_classifies():
    csv_bytes = _gbk_csv(
        "20260608,600519,贵州茅台,证券买入,100,1500.00,5.00,0.00,0.10,T0001",
        "20260609,600519,贵州茅台,证券卖出,50,1700.00,5.00,85.00,0.05,T0002",
        "20260608,000001,银行转账,银行转证券,0,0,0,0,0,T0003",
    )
    resp = _upload(csv_bytes)
    assert resp.status_code == 200
    body = resp.json()
    assert body["parsable_count"] == 2
    assert body["skip_count"] == 1
    assert body["error_count"] == 0

    buy = body["rows"][0]
    assert buy["name"] == "贵州茅台"  # GBK 未乱码
    assert buy["action"] == "buy"
    assert buy["asset_type"] == "stock"
    assert Decimal(str(buy["fee"])) == Decimal("5.10")  # 5+0+0.1
    sell = body["rows"][1]
    assert Decimal(str(sell["fee"])) == Decimal("90.05")  # 5+85+0.05
    assert body["rows"][2]["status"] == "skip"


def test_commit_rebuilds_positions():
    csv_bytes = _gbk_csv(
        "20260608,600519,贵州茅台,买入,100,1500,0,0,0,A0001",
        "20260609,600519,贵州茅台,买入,100,1600,0,0,0,A0002",
        "20260610,600519,贵州茅台,卖出,50,1700,0,0,0,A0003",
    )
    rows = _upload(csv_bytes).json()["rows"]
    resp = client.post("/import/commit", json={"rows": rows})
    assert resp.status_code == 200
    body = resp.json()
    assert body["committed"] is True
    assert body["imported"] == 3
    assert body["skipped_dup"] == 0

    db = TestingSessionLocal()
    pos = db.query(Position).filter(Position.symbol == "600519").first()
    assert Decimal(str(pos.shares)) == Decimal("150")
    assert Decimal(str(pos.avg_cost)) == Decimal("1550")
    db.close()


def test_commit_dedup_skips_reimport():
    csv_bytes = _gbk_csv(
        "20260608,600519,贵州茅台,买入,100,1500,0,0,0,B0001",
    )
    rows = _upload(csv_bytes).json()["rows"]
    first = client.post("/import/commit", json={"rows": rows}).json()
    assert first["imported"] == 1

    # 再次提交同一批 → 成交编号已存在，全部跳过
    second = client.post("/import/commit", json={"rows": rows}).json()
    assert second["imported"] == 0
    assert second["skipped_dup"] == 1

    # preview 同样会把已导入的标为重复
    prev = _upload(csv_bytes).json()
    assert prev["dup_count"] == 1


def test_commit_rolls_back_on_oversell():
    csv_bytes = _gbk_csv(
        "20260608,600519,贵州茅台,买入,100,1500,0,0,0,C0001",
        "20260609,600519,贵州茅台,卖出,200,1700,0,0,0,C0002",
    )
    rows = _upload(csv_bytes).json()["rows"]
    body = client.post("/import/commit", json={"rows": rows}).json()
    assert body["committed"] is False
    assert body["imported"] == 0
    assert len(body["failed"]) == 1

    # 整批回滚：持仓不应残留
    db = TestingSessionLocal()
    assert db.query(Position).filter(Position.symbol == "600519").first() is None
    db.close()


def test_preview_empty_file_rejected():
    resp = client.post(
        "/import/preview",
        files={"file": ("empty.csv", b"", "text/csv")},
        data={"broker": "ths"},
    )
    assert resp.status_code == 400
