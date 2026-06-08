from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field


class PositionCreate(BaseModel):
    symbol: str
    name: str
    asset_type: Literal["stock", "etf", "fund"]
    shares: Decimal = Field(ge=0)
    avg_cost: Decimal = Field(ge=0)


class PositionOut(BaseModel):
    id: int
    symbol: str
    name: str
    asset_type: str
    shares: Decimal
    avg_cost: Decimal
    # 价格字段（来自 daily_snapshots）
    current_price: Optional[Decimal] = None
    price_date: Optional[date] = None
    is_stale: bool = False

    model_config = {"from_attributes": True}


class JournalCreate(BaseModel):
    symbol: str
    action: Literal["buy", "sell"]
    shares: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    reason: Optional[str] = None
    trade_date: date


class JournalOut(BaseModel):
    id: int
    symbol: str
    action: str
    shares: Decimal
    price: Decimal
    reason: Optional[str]
    pnl: Optional[Decimal]
    avg_cost_at_time: Optional[Decimal]
    trade_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class RefreshResult(BaseModel):
    updated: int
    skipped: int
    errors: list[str]
