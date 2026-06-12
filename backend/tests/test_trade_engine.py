import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from database import Base
from models import Position
from services.trade_engine import apply_trade, TradeError

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _get_pos(db, symbol):
    return db.execute(
        select(Position).where(Position.symbol == symbol)
    ).scalar_one_or_none()


def test_first_buy_creates_position(db):
    # 导入场景：首买不存在的标的应自动建仓
    entry = apply_trade(
        db, symbol="161725", action="buy", shares=Decimal("1000"),
        price=Decimal("0.85"), trade_date=date(2026, 6, 8),
        name="招商中证白酒", asset_type="fund",
        create_position_if_missing=True,
    )
    db.commit()
    pos = _get_pos(db, "161725")
    assert pos is not None
    assert pos.name == "招商中证白酒"
    assert pos.asset_type == "fund"
    assert Decimal(str(pos.shares)) == Decimal("1000")
    assert Decimal(str(pos.avg_cost)) == Decimal("0.85")
    assert entry.avg_cost_at_time == Decimal("0")  # 建仓时交易前均价为 0


def test_buy_fee_folded_into_cost(db):
    # 买入 100 @10，手续费 50 → 全入成本：(100*10 + 50)/100 = 10.5
    apply_trade(
        db, symbol="600519", action="buy", shares=Decimal("100"),
        price=Decimal("10"), trade_date=date(2026, 6, 8),
        name="贵州茅台", asset_type="stock", fee=Decimal("50"),
        create_position_if_missing=True,
    )
    db.commit()
    pos = _get_pos(db, "600519")
    assert Decimal(str(pos.avg_cost)) == Decimal("10.5")


def test_sell_fee_deducted_from_pnl(db):
    apply_trade(
        db, symbol="600519", action="buy", shares=Decimal("100"),
        price=Decimal("10"), trade_date=date(2026, 6, 8),
        name="贵州茅台", asset_type="stock",
        create_position_if_missing=True,
    )
    db.commit()
    # 卖 50 @12，手续费 10 → pnl =(12-10)*50 - 10 = 90
    entry = apply_trade(
        db, symbol="600519", action="sell", shares=Decimal("50"),
        price=Decimal("12"), trade_date=date(2026, 6, 9), fee=Decimal("10"),
    )
    db.commit()
    assert entry.pnl == Decimal("90")


def test_sell_missing_position_raises(db):
    # 卖出不存在的持仓即便允许建仓也应报错（不能凭空卖出）
    with pytest.raises(TradeError) as exc:
        apply_trade(
            db, symbol="999999", action="sell", shares=Decimal("10"),
            price=Decimal("5"), trade_date=date(2026, 6, 8),
            create_position_if_missing=True,
        )
    assert exc.value.status_code == 422


def test_buy_missing_no_create_raises(db):
    # 手工记账路径：不允许建仓时买入不存在持仓报 404
    with pytest.raises(TradeError) as exc:
        apply_trade(
            db, symbol="999999", action="buy", shares=Decimal("10"),
            price=Decimal("5"), trade_date=date(2026, 6, 8),
            create_position_if_missing=False,
        )
    assert exc.value.status_code == 404


def test_external_id_dedup(db):
    apply_trade(
        db, symbol="600519", action="buy", shares=Decimal("100"),
        price=Decimal("10"), trade_date=date(2026, 6, 8),
        name="贵州茅台", asset_type="stock", external_id="THS-0001",
        create_position_if_missing=True,
    )
    db.commit()
    # 相同 external_id 再次写入 → flush 时唯一索引冲突
    with pytest.raises(IntegrityError):
        apply_trade(
            db, symbol="600519", action="buy", shares=Decimal("100"),
            price=Decimal("10"), trade_date=date(2026, 6, 8),
            external_id="THS-0001",
        )
    db.rollback()


def test_null_external_id_allows_multiple(db):
    # 手工录入 external_id 为 NULL，多条不应冲突
    apply_trade(
        db, symbol="600519", action="buy", shares=Decimal("100"),
        price=Decimal("10"), trade_date=date(2026, 6, 8),
        name="贵州茅台", asset_type="stock",
        create_position_if_missing=True,
    )
    apply_trade(
        db, symbol="600519", action="buy", shares=Decimal("100"),
        price=Decimal("11"), trade_date=date(2026, 6, 9),
    )
    db.commit()
    pos = _get_pos(db, "600519")
    assert Decimal(str(pos.shares)) == Decimal("200")
