from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import JournalEntry, Position
from schemas import JournalCreate, JournalOut
from services.gemini import audit_decision

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("", response_model=JournalOut, status_code=201)
def record_trade(
    body: JournalCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
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

    # 异步触发 AI 决策审计
    background_tasks.add_task(audit_journal_entry_task, entry.id)

    return entry


def audit_journal_entry_task(entry_id: int):
    """
    异步决策日记 AI 审计任务
    在后台线程中独立打开并关闭数据库连接，防止主请求死锁或连接泄漏
    """
    db = SessionLocal()
    try:
        entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
        if not entry:
            return

        # 若未填写交易原因，直接归为“理性分析”或“其它”并不发大模型请求
        if not entry.reason or not entry.reason.strip():
            entry.motivation_type = "理性分析"
            entry.ai_audit = "用户未填写交易原因，暂无法进行心理偏差评估。"
            db.commit()
            return

        motivation_type, ai_audit = audit_decision(
            symbol=entry.symbol,
            action=entry.action,
            shares=float(entry.shares),
            price=float(entry.price),
            reason=entry.reason,
        )

        entry.motivation_type = motivation_type
        entry.ai_audit = ai_audit
        db.commit()
    except Exception:
        # 后台静默处理，确保不引发崩溃
        pass
    finally:
        db.close()


@router.get("", response_model=list[JournalOut])
def list_journal(symbol: Optional[str] = None, db: Session = Depends(get_db)):
    stmt = select(JournalEntry).order_by(JournalEntry.created_at.desc())
    if symbol:
        stmt = stmt.where(JournalEntry.symbol == symbol)
    entries = db.execute(stmt).scalars().all()
    return entries


@router.delete("/{entry_id}", status_code=204)
def delete_journal(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="决策日记不存在")
    db.delete(entry)
    db.commit()
    return
