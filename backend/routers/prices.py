from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import DailySnapshot, Position
from schemas import RefreshResult
from services.baostock_service import fetch_prices, fetch_fund_prices

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/refresh", response_model=RefreshResult)
def refresh_prices(db: Session = Depends(get_db)):
    # 同时查询 symbol 和 asset_type，以进行数据源路由
    positions = db.execute(
        select(Position.symbol, Position.asset_type)
    ).all()
    
    if not positions:
        return RefreshResult(updated=0, skipped=0, errors=[])

    stock_symbols = [p.symbol for p in positions if p.asset_type in ("stock", "etf")]
    fund_symbols = [p.symbol for p in positions if p.asset_type == "fund"]

    price_map = {}
    errors = []

    # 1. 股票与 ETF 行情获取 (BaoStock)
    if stock_symbols:
        stock_map, stock_errors = fetch_prices(stock_symbols)
        price_map.update(stock_map)
        errors.extend(stock_errors)

    # 2. 公募基金行情获取 (天天基金)
    if fund_symbols:
        fund_map, fund_errors = fetch_fund_prices(fund_symbols)
        price_map.update(fund_map)
        errors.extend(fund_errors)

    updated = 0
    skipped = 0

    for symbol, (price, date_str) in price_map.items():
        try:
            snapshot_date = date.fromisoformat(date_str)
        except ValueError:
            errors.append(f"{symbol}: 日期格式非法 ({date_str})")
            continue

        # 检查是否已有该日期该标的的收盘价快照
        existing = db.execute(
            select(DailySnapshot).where(
                DailySnapshot.symbol == symbol,
                DailySnapshot.date == snapshot_date
            )
        ).scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        snapshot = DailySnapshot(
            symbol=symbol,
            date=snapshot_date,
            close_price=price,
        )
        db.add(snapshot)
        try:
            db.flush()
            updated += 1
        except IntegrityError:
            db.rollback()
            errors.append(f"{symbol} 写入快照冲突")

    db.commit()
    return RefreshResult(updated=updated, skipped=skipped, errors=errors)
