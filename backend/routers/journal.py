from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import JournalEntry, Position
from schemas import JournalCreate, JournalOut

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("", response_model=JournalOut, status_code=201)
def record_trade(body: JournalCreate, db: Session = Depends(get_db)):
    pos = db.execute(
        select(Position).where(Position.symbol == body.symbol)
    ).scalar_one_or_none()

    if pos is None:
        raise HTTPException(404, f"持仓 {body.symbol} 不存在，请先添加持仓")

    pnl: Optional[Decimal] = None
    avg_cost_at_time = Decimal(str(pos.avg_cost))

    if body.action == "sell":
        # ENG-5: 超卖保护
        if pos.shares < body.shares:
            raise HTTPException(422, f"卖出数量 {body.shares} 超过持仓 {pos.shares}")
        pnl = (body.price - avg_cost_at_time) * body.shares

    with db.begin_nested():
        entry = JournalEntry(
            symbol=body.symbol,
            action=body.action,
            shares=body.shares,
            price=body.price,
            reason=body.reason,
            pnl=pnl,
            avg_cost_at_time=avg_cost_at_time,
            trade_date=body.trade_date,
        )
        db.add(entry)

        if body.action == "buy":
            old_shares = Decimal(str(pos.shares))
            old_avg = Decimal(str(pos.avg_cost))
            new_shares = old_shares + body.shares
            if new_shares <= 0:
                raise HTTPException(422, "计算后的持仓份额必须大于 0")
            new_avg = (old_shares * old_avg + body.shares * body.price) / new_shares
            pos.shares = new_shares
            pos.avg_cost = new_avg
        else:
            new_shares = Decimal(str(pos.shares)) - body.shares
            if new_shares == 0:
                db.delete(pos)
            else:
                pos.shares = new_shares

    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[JournalOut])
def list_journal(symbol: Optional[str] = None, db: Session = Depends(get_db)):
    stmt = select(JournalEntry).order_by(JournalEntry.created_at.desc())
    if symbol:
        stmt = stmt.where(JournalEntry.symbol == symbol)
    entries = db.execute(stmt).scalars().all()
    return entries
