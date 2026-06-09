from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import DailySnapshot, Position
from schemas import PositionCreate, PositionOut

router = APIRouter(prefix="/positions", tags=["positions"])

# 距最近快照超过 1 个交易日（含周末按 3 天算）视为过期
_STALE_DAYS = 3


def _is_stale(price_date: Optional[date]) -> bool:
    if price_date is None:
        return True
    return (date.today() - price_date).days > _STALE_DAYS


@router.get("", response_model=list[PositionOut])
def list_positions(db: Session = Depends(get_db)):
    positions = db.execute(select(Position)).scalars().all()
    if not positions:
        return []

    from sqlalchemy import func
    symbols = [pos.symbol for pos in positions]

    # 使用 window function 一次性拉取所有 symbol 最新一条 snapshot
    subq = (
        select(
            DailySnapshot.symbol,
            DailySnapshot.close_price,
            DailySnapshot.date,
            func.row_number().over(
                partition_by=DailySnapshot.symbol,
                order_by=DailySnapshot.date.desc()
            ).label("rn")
        )
        .where(DailySnapshot.symbol.in_(symbols))
        .subquery()
    )

    stmt = select(subq.c.symbol, subq.c.close_price, subq.c.date).where(subq.c.rn == 1)
    snapshots = db.execute(stmt).all()
    price_map = {row.symbol: (row.close_price, row.date) for row in snapshots}

    result = []
    for pos in positions:
        snap = price_map.get(pos.symbol)
        current_price = Decimal(str(snap[0])) if snap else None
        price_date = snap[1] if snap else None

        result.append(
            PositionOut(
                id=pos.id,
                symbol=pos.symbol,
                name=pos.name,
                asset_type=pos.asset_type,
                shares=pos.shares,
                avg_cost=pos.avg_cost,
                current_price=current_price,
                price_date=price_date,
                is_stale=_is_stale(price_date),
            )
        )
    return result


@router.post("", response_model=PositionOut, status_code=201)
def create_position(body: PositionCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(Position).where(Position.symbol == body.symbol)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"持仓 {body.symbol} 已存在，请用交易记录更新持仓")

    pos = Position(
        symbol=body.symbol,
        name=body.name,
        asset_type=body.asset_type,
        shares=body.shares,
        avg_cost=body.avg_cost,
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)

    return PositionOut(
        id=pos.id,
        symbol=pos.symbol,
        name=pos.name,
        asset_type=pos.asset_type,
        shares=pos.shares,
        avg_cost=pos.avg_cost,
        is_stale=True,
    )


@router.delete("/{symbol}", status_code=204)
def delete_position(symbol: str, db: Session = Depends(get_db)):
    pos = db.execute(
        select(Position).where(Position.symbol == symbol)
    ).scalar_one_or_none()
    if not pos:
        raise HTTPException(404, f"持仓 {symbol} 不存在")
    db.delete(pos)
    db.commit()
