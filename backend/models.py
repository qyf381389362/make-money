from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime,
    Enum, Text, Index, UniqueConstraint,
)
from database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    asset_type = Column(Enum("stock", "etf", "fund"), nullable=False)
    shares = Column(Numeric(12, 2), nullable=False, default=0)
    avg_cost = Column(Numeric(12, 4), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    action = Column(Enum("buy", "sell"), nullable=False)
    shares = Column(Numeric(12, 2), nullable=False)
    price = Column(Numeric(12, 4), nullable=False)
    reason = Column(Text)
    pnl = Column(Numeric(12, 2))
    avg_cost_at_time = Column(Numeric(12, 4))
    trade_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 新增字段用于 AI 决策审计
    motivation_type = Column(String(50), nullable=True)
    ai_audit = Column(Text, nullable=True)

    # 新增字段用于交割单导入（T11）
    external_id = Column(String(64), nullable=True)  # 券商成交编号，用于幂等去重
    fee = Column(Numeric(12, 4), nullable=True)      # 手续费/印花税/过户费合计

    __table_args__ = (
        Index("idx_journal_symbol", "symbol"),
        # external_id 唯一索引：NULL 不参与唯一性，手工录入(NULL)不会冲突
        Index("uk_journal_external_id", "external_id", unique=True),
    )


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Numeric(12, 4), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("symbol", "date", name="uk_symbol_date"),)
