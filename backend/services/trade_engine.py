"""
交易记账核心引擎。

从 routers/journal.py 抽取，供「手工记账」与「交割单导入(T11)」复用同一套
加权平均成本 / 超卖保护 / 平仓盈亏 / 清仓删除 / 首买建仓 逻辑，避免逻辑分叉。

约定：apply_trade 只写入 session（add/flush），**不提交事务**，由调用方负责
commit / rollback。手工记账逐笔提交；批量导入整批包在一个事务里。
"""
from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import JournalEntry, Position


class TradeError(Exception):
    """领域层交易异常，由调用方（HTTP 层）转换为对应的响应码与文案。"""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _d(value) -> Decimal:
    """统一转 Decimal，避免 float 精度问题。"""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def apply_trade(
    db: Session,
    *,
    symbol: str,
    action: str,
    shares,
    price,
    trade_date: date_type,
    reason: Optional[str] = None,
    name: Optional[str] = None,
    asset_type: Optional[str] = None,
    external_id: Optional[str] = None,
    fee=Decimal(0),
    create_position_if_missing: bool = False,
) -> JournalEntry:
    """
    回放一笔交易并更新持仓，返回写入的 JournalEntry（已 flush，可取 id）。
    不提交事务（由调用方 commit / rollback）。

    - 买入：移动加权平均成本，**费用并入成本**；`create_position_if_missing`
      为真时允许首买建仓（导入历史交割单场景）。
    - 卖出：超卖保护；平仓盈亏 =(卖价-交易前均价)*份额 - 费用；清仓物理删除。
    """
    shares = _d(shares)
    price = _d(price)
    fee = _d(fee or 0)

    pos = db.execute(
        select(Position).where(Position.symbol == symbol)
    ).scalar_one_or_none()

    if pos is None:
        if not (create_position_if_missing and action == "buy"):
            if action == "sell":
                raise TradeError(422, f"持仓 {symbol} 不存在，无法卖出")
            raise TradeError(404, f"持仓 {symbol} 不存在，请先添加持仓")
        # 首买建仓：以 0 份额 / 0 成本起始，随后走买入逻辑累加
        pos = Position(
            symbol=symbol,
            name=name or symbol,
            asset_type=asset_type or "stock",
            shares=Decimal(0),
            avg_cost=Decimal(0),
        )
        db.add(pos)

    avg_cost_at_time = _d(pos.avg_cost)
    pnl: Optional[Decimal] = None

    if action == "sell":
        if _d(pos.shares) < shares:
            raise TradeError(422, f"卖出数量 {shares} 超过持仓 {pos.shares}")
        pnl = (price - avg_cost_at_time) * shares - fee

    entry = JournalEntry(
        symbol=symbol,
        action=action,
        shares=shares,
        price=price,
        reason=reason,
        pnl=pnl,
        avg_cost_at_time=avg_cost_at_time,
        trade_date=trade_date,
        external_id=external_id,
        fee=fee,
    )
    db.add(entry)

    if action == "buy":
        old_shares = _d(pos.shares)
        old_avg = _d(pos.avg_cost)
        new_shares = old_shares + shares
        if new_shares <= 0:
            raise TradeError(422, "计算后的持仓份额必须大于 0")
        # 费用并入成本：总成本 =(旧份额*旧均价 + 买入金额 + 费用)
        new_avg = (old_shares * old_avg + shares * price + fee) / new_shares
        pos.shares = new_shares
        pos.avg_cost = new_avg
    else:
        new_shares = _d(pos.shares) - shares
        if new_shares == 0:
            db.delete(pos)
        else:
            pos.shares = new_shares

    db.flush()
    return entry
