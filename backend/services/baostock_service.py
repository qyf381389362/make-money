from datetime import datetime, timedelta
import baostock as bs


def _to_bs_code(symbol: str) -> str:
    if symbol.startswith(("5", "6", "9")):
        return f"sh.{symbol}"
    else:
        return f"sz.{symbol}"


def fetch_prices(symbols: list[str]) -> dict[str, tuple[float, str]]:
    """批量拉取收盘价，返回 {symbol: (price, date_str)}，失败的 symbol 不在结果中。"""
    results: dict[str, tuple[float, str]] = {}
    errors: list[str] = []

    bs.login()
    try:
        end = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=10)).strftime("%Y-%m-%d")

        for symbol in symbols:
            code = _to_bs_code(symbol)
            rs = bs.query_history_k_data_plus(
                code, "date,close",
                start_date=start, end_date=end,
                frequency="d", adjustflag="3",
            )
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())

            if not rows:
                errors.append(f"{symbol}: 无数据（{rs.error_msg}）")
                continue

            date_str, close_str = rows[-1]
            try:
                results[symbol] = (float(close_str), date_str)
            except (ValueError, TypeError):
                errors.append(f"{symbol}: 价格解析失败（{close_str}）")
    finally:
        bs.logout()

    return results, errors
