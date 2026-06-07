"""
依赖安装：pip install baostock
运行方式：python fetch_prices.py
"""

import baostock as bs
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# 修改这里：填入你自己的持仓
# type: "stock" = A 股，"etf" = 场内 ETF
# shares: 持有股数 / 份额
# avg_cost: 买入均价（元/股 或 元/份）
# exchange 自动推断：6开头=sh，其余=sz
# ──────────────────────────────────────────────
HOLDINGS = [
    {"symbol": "600584", "name": "长电科技",        "type": "stock", "shares": 100,   "avg_cost": 85.92},
    {"symbol": "601212", "name": "白银有色",         "type": "stock", "shares": 3100,  "avg_cost": 10.714},
    {"symbol": "159819", "name": "人工智能ETF易方达", "type": "etf",   "shares": 19400, "avg_cost": 1.579},
]


def to_bs_code(symbol: str) -> str:
    return f"sh.{symbol}" if symbol.startswith("6") else f"sz.{symbol}"


def get_price(symbol: str) -> tuple[float, str]:
    """获取最近交易日收盘价，返回 (价格, 日期)"""
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=10)).strftime("%Y-%m-%d")
    code = to_bs_code(symbol)
    rs = bs.query_history_k_data_plus(
        code, "date,close",
        start_date=start, end_date=end,
        frequency="d", adjustflag="3"
    )
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        raise ValueError(f"未找到 {symbol} 的历史数据（error: {rs.error_msg}）")
    date, close = rows[-1]
    return float(close), date


def fetch_price(holding: dict) -> dict:
    price, date = get_price(holding["symbol"])
    shares = holding["shares"]
    avg_cost = holding["avg_cost"]
    pnl = (price - avg_cost) * shares
    pnl_pct = (price - avg_cost) / avg_cost * 100
    return {**holding, "current_price": price, "data_date": date, "pnl": pnl, "pnl_pct": pnl_pct}


def format_pnl(pnl: float, pnl_pct: float) -> str:
    sign = "▲" if pnl >= 0 else "▼"
    color = "\033[91m" if pnl >= 0 else "\033[92m"
    reset = "\033[0m"
    return f"{color}{sign} {pnl:+.2f} 元 ({pnl_pct:+.2f}%){reset}"


def main():
    bs.login()
    print(f"\n{'='*55}")
    print(f"  持仓价格查询  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")

    total_cost = 0.0
    total_value = 0.0

    for holding in HOLDINGS:
        symbol = holding["symbol"]
        name = holding["name"]
        print(f"\n  正在获取 {name}（{symbol}）...")
        try:
            result = fetch_price(holding)
            unit = "股" if holding["type"] == "stock" else "份"
            print(f"  {name}（{symbol}）")
            print(f"    现价：{result['current_price']:.3f} 元  |  数据日期：{result['data_date']}")
            print(f"    持仓：{result['shares']} {unit}  |  均价：{result['avg_cost']:.3f} 元")
            print(f"    盈亏：{format_pnl(result['pnl'], result['pnl_pct'])}")
            total_cost += holding["shares"] * holding["avg_cost"]
            total_value += holding["shares"] * result["current_price"]
        except Exception as e:
            print(f"  {name}（{symbol}）获取失败：{e}")

    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost > 0 else 0
    print(f"\n{'─'*55}")
    print(f"  总成本：{total_cost:.2f} 元  |  总市值：{total_value:.2f} 元")
    print(f"  总盈亏：{format_pnl(total_pnl, total_pnl_pct)}")
    print(f"{'='*55}\n")
    bs.logout()


if __name__ == "__main__":
    main()
