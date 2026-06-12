"""券商交割单解析层（T11）。

把券商导出的 CSV 交割单解析为标准化的 ParsedTrade 列表，供导入接口回放。
MVP 内置同花顺(ths)适配器 + 通用列映射；编码自动处理 GBK/UTF-8。

注意：场外公募基金的申赎不出现在券商交割单里，交割单只含场内成交，
因此本层产出的 asset_type 仅为 stock / etf。
"""
import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel

# 内置券商列映射：券商导出的中文列名 -> 内部字段名
THS_MAPPING = {
    "成交日期": "trade_date",
    "成交时间": "trade_time",
    "证券代码": "symbol",
    "证券名称": "name",
    "操作": "action",
    "买卖标志": "action",
    "成交数量": "shares",
    "成交价格": "price",
    "手续费": "fee_commission",
    "佣金": "fee_commission",
    "印花税": "fee_stamp",
    "过户费": "fee_transfer",
    "成交编号": "external_id",
    "合同编号": "external_id",
}

BROKER_MAPPINGS = {
    "ths": THS_MAPPING,  # 同花顺
}


class ParsedTrade(BaseModel):
    row_index: int
    trade_date: Optional[date] = None
    symbol: Optional[str] = None
    name: Optional[str] = None
    asset_type: str = "stock"
    action: Optional[str] = None  # buy / sell
    shares: Optional[Decimal] = None
    price: Optional[Decimal] = None
    fee: Decimal = Decimal(0)
    external_id: Optional[str] = None
    status: str = "ok"  # ok / skip / error
    note: Optional[str] = None


class ParseResult(BaseModel):
    rows: list[ParsedTrade]
    parsable_count: int
    skip_count: int
    error_count: int


def decode_csv(data: bytes) -> str:
    """券商导出多为 GBK；优先 UTF-8(含 BOM)，回退 GBK/GB18030。"""
    for enc in ("utf-8-sig", "gbk", "gb18030"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    # 兜底：替换非法字节，避免整体崩溃
    return data.decode("utf-8", errors="replace")


def _infer_asset_type(symbol: str) -> str:
    # ETF/LOF 归 etf，其余 stock（交割单不含场外基金）
    if symbol[:2] in ("51", "56", "58", "15", "16", "11", "50"):
        return "etf"
    return "stock"


def _parse_date(raw: str) -> Optional[date]:
    raw = (raw or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _to_decimal(raw) -> Optional[Decimal]:
    try:
        s = str(raw).strip().replace(",", "")
        if s == "":
            return None
        return Decimal(s)
    except (InvalidOperation, AttributeError):
        return None


def _map_action(raw: str) -> Optional[str]:
    raw = (raw or "").strip()
    if "买" in raw:
        return "buy"
    if "卖" in raw:
        return "sell"
    return None  # 分红/转账/利息等非买卖行


def parse_statement(
    data: bytes, broker: str = "ths", mapping: Optional[dict] = None
) -> ParseResult:
    """解析 CSV 字节为标准化交易行。mapping 为通用映射时优先生效。"""
    text = decode_csv(data)
    reader = csv.DictReader(io.StringIO(text))
    col_map = mapping or BROKER_MAPPINGS.get(broker, THS_MAPPING)

    rows: list[ParsedTrade] = []
    parsable = skip = error = 0

    for i, raw_row in enumerate(reader):
        fields: dict = {}
        fee_parts: list[Decimal] = []
        for col, val in raw_row.items():
            key = col_map.get((col or "").strip())
            if key is None:
                continue
            if key.startswith("fee_"):
                fee_parts.append(_to_decimal(val) or Decimal(0))
            else:
                fields[key] = val

        symbol = (fields.get("symbol") or "").strip()
        name = (fields.get("name") or "").strip() or None
        action = _map_action(fields.get("action", ""))
        trade_date = _parse_date(fields.get("trade_date", ""))
        shares = _to_decimal(fields.get("shares"))
        price = _to_decimal(fields.get("price"))
        fee = sum(fee_parts, Decimal(0))
        external_id = (fields.get("external_id") or "").strip() or None

        # 非买卖行（分红/转账/利息）跳过，不静默吞掉
        if action is None:
            rows.append(ParsedTrade(row_index=i, symbol=symbol or None, name=name,
                                    status="skip", note="非买卖行，已跳过"))
            skip += 1
            continue

        # 必填校验
        if not symbol or trade_date is None or not shares or not price:
            rows.append(ParsedTrade(row_index=i, symbol=symbol or None, name=name,
                                    action=action, status="error",
                                    note="缺少必填字段(代码/日期/数量/价格)"))
            error += 1
            continue

        rows.append(ParsedTrade(
            row_index=i, trade_date=trade_date, symbol=symbol, name=name,
            asset_type=_infer_asset_type(symbol), action=action,
            shares=shares, price=price, fee=fee, external_id=external_id,
            status="ok",
        ))
        parsable += 1

    return ParseResult(rows=rows, parsable_count=parsable,
                       skip_count=skip, error_count=error)
