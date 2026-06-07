from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import DailySnapshot, Position
from schemas import RefreshResult
from services.baostock_service import fetch_prices

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/refresh", response_model=RefreshResult)
def refresh_prices(db: Session = Depends(get_db)):
    symbols = db.execute(select(Position.symbol)).scalars().all()
    if not symbols:
        return RefreshResult(updated=0, skipped=0, errors=[])

    price_map, errors = fetch_prices(list(symbols))

    updated = 0
    skipped = 0

    for symbol, (price, date_str) in price_map.items():
        snapshot_date = date.fromisoformat(date_str)
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
            # ENG-8: UNIQUE(symbol, date) 冲突 = 今天已拉过，忽略
            db.rollback()
            skipped += 1

    db.commit()
    return RefreshResult(updated=updated, skipped=skipped, errors=errors)
