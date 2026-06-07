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

    result = []
    for pos in positions:
        # 取该 symbol 最新快照
        snapshot = db.execute(
            select(DailySnapshot)
            .where(DailySnapshot.symbol == pos.symbol)
            .order_by(DailySnapshot.date.desc())
            .limit(1)
        ).scalar_one_or_none()

        current_price = Decimal(str(snapshot.close_price)) if snapshot else None
        price_date = snapshot.date if snapshot else None

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
