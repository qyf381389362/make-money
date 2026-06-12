"""交割单导入接口（T11）：两步式 预览 -> 确认。

- POST /import/preview：上传 CSV，只读解析并标记重复行，不写库。
- POST /import/commit：对确认后的行单事务回放 apply_trade，幂等去重，
  任一行失败整批回滚（回放有均价前后依赖，半途提交会留脏数据）。
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import JournalEntry
from services.trade_engine import apply_trade, TradeError
from services.broker_import import parse_statement, ParsedTrade

router = APIRouter(prefix="/import", tags=["import"])


class PreviewResult(BaseModel):
    rows: list[ParsedTrade]
    parsable_count: int
    skip_count: int
    error_count: int
    dup_count: int


class CommitPayload(BaseModel):
    rows: list[ParsedTrade]


class CommitResult(BaseModel):
    imported: int
    skipped_dup: int
    failed: list[dict]
    committed: bool


def _existing_external_ids(db: Session, ids: list[str]) -> set:
    ids = [i for i in ids if i]
    if not ids:
        return set()
    rows = db.execute(
        select(JournalEntry.external_id).where(JournalEntry.external_id.in_(ids))
    ).scalars().all()
    return set(rows)


@router.post("/preview", response_model=PreviewResult)
async def preview_import(
    file: UploadFile = File(...),
    broker: str = Form("ths"),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "上传文件为空")

    result = parse_statement(data, broker=broker)

    # 标记数据库中已存在的成交编号（重复导入）
    existing = _existing_external_ids(db, [r.external_id for r in result.rows])
    dup = 0
    for r in result.rows:
        if r.status == "ok" and r.external_id and r.external_id in existing:
            r.status = "skip"
            r.note = "已导入过（成交编号重复）"
            dup += 1

    return PreviewResult(
        rows=result.rows,
        parsable_count=sum(1 for r in result.rows if r.status == "ok"),
        skip_count=sum(1 for r in result.rows if r.status == "skip"),
        error_count=result.error_count,
        dup_count=dup,
    )


@router.post("/commit", response_model=CommitResult)
def commit_import(payload: CommitPayload, db: Session = Depends(get_db)):
    candidates = [r for r in payload.rows if r.status == "ok"]

    # 1. 去重过滤：DB 已存在 + 批内重复
    existing = _existing_external_ids(db, [r.external_id for r in candidates])
    seen: set = set()
    to_apply: list[ParsedTrade] = []
    skipped_dup = 0
    for r in candidates:
        if r.external_id and (r.external_id in existing or r.external_id in seen):
            skipped_dup += 1
            continue
        if r.external_id:
            seen.add(r.external_id)
        to_apply.append(r)

    # 2. 按 (trade_date, row_index) 稳定排序，单事务回放
    to_apply.sort(key=lambda r: (r.trade_date, r.row_index))
    imported = 0
    failed: list[dict] = []
    for r in to_apply:
        try:
            apply_trade(
                db, symbol=r.symbol, action=r.action, shares=r.shares,
                price=r.price, trade_date=r.trade_date, name=r.name,
                asset_type=r.asset_type, external_id=r.external_id,
                fee=r.fee, create_position_if_missing=True,
            )
            imported += 1
        except TradeError as e:
            failed.append({"row": r.row_index, "reason": e.detail})
            break

    if failed:
        db.rollback()
        return CommitResult(imported=0, skipped_dup=skipped_dup,
                            failed=failed, committed=False)

    db.commit()
    return CommitResult(imported=imported, skipped_dup=skipped_dup,
                        failed=failed, committed=True)
