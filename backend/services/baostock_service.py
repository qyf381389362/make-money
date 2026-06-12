from datetime import datetime, timedelta
import re
import json
import time
import httpx
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


def fetch_fund_prices(symbols: list[str]) -> tuple[dict[str, tuple[float, str]], list[str]]:
    """
    通过天天基金爬虫接口拉取公募基金最新行情。
    返回 {symbol: (dwjz, jzrq_str)} 和 错误列表。
    """
    results: dict[str, tuple[float, str]] = {}
    errors: list[str] = []

    for symbol in symbols:
        # 天天基金公募基金代码一般为6位纯数字，做个基本防御
        if not symbol.isdigit() or len(symbol) != 6:
            errors.append(f"{symbol}: 非法的基金代码格式")
            continue

        # 接口限流控制，防止并发过高被封禁 (流控机制)
        time.sleep(0.1)

        url = f"http://fundgz.1234567.com.cn/js/{symbol}.js"
        try:
            # 天天基金响应应该在 5 秒内返回
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    errors.append(f"{symbol}: 天天基金接口状态码异常 ({resp.status_code})")
                    continue

                content = resp.text.strip()
                if not content:
                    errors.append(f"{symbol}: 天天基金返回空响应")
                    continue

                # 使用正则提取 jsonpgz(...) 包裹的 JSON 数据
                match = re.search(r"jsonpgz\(([\s\S]*?)\);", content)
                if not match:
                    # 容错：有些情况下可能没有 jsonpgz() 包装，直接作为 JSON 尝试解析
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        errors.append(f"{symbol}: 天天基金响应格式解析失败")
                        continue
                else:
                    try:
                        data = json.loads(match.group(1))
                    except json.JSONDecodeError:
                        errors.append(f"{symbol}: 天天基金 JSON 解析失败")
                        continue

                # 提取单位净值 dwjz 与净值日期 jzrq
                dwjz = data.get("dwjz")
                jzrq = data.get("jzrq")
                if not dwjz or not jzrq:
                    errors.append(f"{symbol}: 缺少必要的净值数据")
                    continue

                results[symbol] = (float(dwjz), jzrq)
        except Exception as e:
            errors.append(f"{symbol}: 拉取失败 ({type(e).__name__})")

    return results, errors
