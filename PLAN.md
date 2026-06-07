# v1a 实施计划：持仓仪表板 + 决策日记

基于 /office-hours 设计文档（2026-05-31），v1a 是最小可用版本。
目标：1-2 个周末完成，证明核心工作流可运行。

## 问题背景

前端工程师持有 A 股和基金持仓，现有工具的核心缺口：
1. 没有连接个人账户的工具——AI 推荐不知道你持有什么
2. 没有决策反馈闭环——买了什么、为什么买、结果如何从未串联

v1a 解决第一个问题：让用户在一个地方看到自己的持仓和盈亏，并记录每笔操作的原因。

## v1a 范围（严格限定）

### 包含
1. **持仓仪表板**
   - 手动录入持仓（代码、名称、股数、均价、资产类型）
   - 通过 baostock API 每日批量拉取收盘价（已验证可用）
   - 展示：当前价、盈亏金额、盈亏百分比、总成本、总市值
   - 数据标注日期（"收盘价，非实时，数据日期：YYYY-MM-DD"）

2. **决策日记**
   - 每次买入/卖出时录入：日期、代码、方向（买/卖）、数量、价格、原因（自由文本）
   - 卖出时自动计算 P&L = (卖出价 - 均价) × 数量
   - 使用加权平均成本法更新均价
   - 日记按时间倒序展示，支持按代码过滤

### 不包含（v1b/v2）
- AI 持仓简报（每日分析）
- 候选股票推荐
- 周度 AI 复盘
- 港股、美股支持
- 定时任务/推送
- K 线图
- 用户账号系统（v1 单用户本地运行）

## 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 前端 | Next.js 14 (TypeScript, App Router) | 开发者熟悉前端，App Router 是现代标准 |
| 后端 | FastAPI (Python 3.11+) | baostock 是 Python 库，数据处理自然 |
| 数据库 | MySQL (SQLAlchemy + pymysql) | 用户提供现成数据库，直接对接 |
| 行情数据 | baostock | 免费、稳定、无 TLS 指纹问题（已验证） |
| 包管理 | uv (Python) + pnpm (Node) | 速度快 |

**数据库连接**：通过环境变量 `DATABASE_URL` 注入，格式：
```
DATABASE_URL=mysql+pymysql://用户名:密码@host:3306/数据库名
```
需额外安装：`uv add pymysql`

## 数据库 Schema（MySQL）

工程审查修正（ENG-2, ENG-4, ENG-11）：

```sql
-- 持仓表（当前持仓状态）
CREATE TABLE positions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  symbol VARCHAR(10) NOT NULL UNIQUE,       -- ENG-2: 禁止同一代码两行
  name VARCHAR(50) NOT NULL,
  asset_type ENUM('stock', 'etf', 'fund') NOT NULL,
  shares DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK(shares >= 0),  -- ENG-4: 禁止负持仓
  avg_cost DECIMAL(12,4) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 决策日记（每笔买卖）
CREATE TABLE journal_entries (
  id INT PRIMARY KEY AUTO_INCREMENT,
  symbol VARCHAR(10) NOT NULL,
  action ENUM('buy', 'sell') NOT NULL,
  shares DECIMAL(12,2) NOT NULL,
  price DECIMAL(12,4) NOT NULL,
  reason TEXT,
  pnl DECIMAL(12,2),          -- 仅 sell 时：(price - avg_cost_at_time) × shares
  avg_cost_at_time DECIMAL(12,4),  -- sell 时记录当时均价
  trade_date DATE NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_journal_symbol (symbol)   -- ENG-11
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 每日价格快照（baostock 批量写入，前端只读此表）
CREATE TABLE daily_snapshots (
  id INT PRIMARY KEY AUTO_INCREMENT,
  symbol VARCHAR(10) NOT NULL,
  date DATE NOT NULL,
  close_price DECIMAL(12,4) NOT NULL,
  fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 系统架构

```
用户浏览器 (Next.js)
    ↓ HTTP (localhost:3000 → :8000)
FastAPI 后端
    ├── GET  /positions          — 持仓列表 + 最新价格
    ├── POST /positions          — 新增持仓
    ├── POST /journal            — 记录买卖（触发均价更新）
    ├── GET  /journal            — 日记列表（支持 ?symbol=xxx 过滤）
    └── POST /prices/refresh     — 触发 baostock 批量拉取
SQLite (make_money.db)
baostock (外部数据，按需调用)
```

## UI 规范

**A 股颜色 Token（必须锁定）：**
```css
--color-gain: #E03A3A;   /* 红色 = 涨 */
--color-loss: #1DB954;   /* 绿色 = 跌 */
--color-neutral: #8B8B8B;
```

**主仪表板布局（单页滚动）：**
1. 顶部横幅：总成本 / 总市值 / 总盈亏（金额 + 百分比）
2. 持仓表格：代码、名称、持仓量、均价、现价、盈亏金额、盈亏%、[记录交易] 按钮
3. 决策日记（同页下方）：时间倒序，每行显示操作摘要 + 原因

**5 种交互状态：**

| 状态 | 展示 |
|------|------|
| Loading | 骨架屏，最长等待 15 秒 |
| 无持仓 | 提示文字 + "添加第一笔持仓" 按钮 |
| 部分失败 | 失败行显示 "--" + 提示，其余正常 |
| 数据过期 | 价格旁显示灰色日期 |
| 提交中 | 表单按钮 disabled + loading 指示器 |

## 项目目录结构

```
make-money/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── models.py            # SQLAlchemy 模型
│   ├── schemas.py           # Pydantic 请求/响应模型
│   ├── database.py          # DB 连接与会话
│   ├── routers/
│   │   ├── positions.py     # 持仓 CRUD
│   │   ├── journal.py       # 决策日记 CRUD
│   │   └── prices.py        # 行情刷新
│   ├── services/
│   │   └── baostock_service.py  # baostock 封装
│   └── make_money.db        # SQLite 数据库文件
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # 主仪表板
│   │   ├── layout.tsx
│   │   └── api/             # Next.js API Routes（可选代理）
│   ├── components/
│   │   ├── PortfolioTable.tsx
│   │   ├── JournalList.tsx
│   │   ├── AddPositionModal.tsx
│   │   └── RecordTradeModal.tsx
│   └── lib/
│       └── api.ts           # 后端 API 客户端
├── fetch_prices.py          # 已验证脚本（数据层概念验证）
├── PLAN.md                  # 本文件
└── CLAUDE.md
```

## P&L 计算逻辑

使用加权平均成本法（FIFO 不适合 A 股散户实际操作习惯）：

- **买入**：`new_avg_cost = (old_shares × old_avg_cost + new_shares × price) / (old_shares + new_shares)`
- **卖出**：P&L = (price - avg_cost) × shares；剩余持仓 avg_cost 不变
- **清仓**：shares 归零，记录保留；下次买入视为新持仓（avg_cost 重置）

## 实施顺序（最小风险路径）

### Day 1（周六）：后端可运行
1. `uv init backend && uv add fastapi uvicorn sqlalchemy pymysql baostock`
2. 实现 database.py + models.py
3. 实现 `/positions` CRUD（含买入触发均价计算）
4. 实现 `/prices/refresh` 调用 baostock
5. 用 curl 验证全流程

### Day 2（周日）：前端可运行
1. `pnpm create next-app frontend`
2. 实现 PortfolioTable（展示持仓 + 价格 + 盈亏）
3. 实现 AddPositionModal（新增持仓）
4. 实现 RecordTradeModal（记录买卖）
5. 实现 JournalList（日记展示）
6. 端到端测试：录入持仓 → 刷新价格 → 记录卖出 → 查看 P&L

## 工程实现要求（/autoplan 审查产出）

以下为工程审查确认的必须实现细节：

### 事务安全（ENG-1 Critical）
POST /journal 必须用 SQLAlchemy 事务同时写 journal_entries + 更新 positions：
```python
with db.begin():
    db.add(journal_entry)
    db.query(Position).filter_by(symbol=...).update({...})
```

### 超卖保护（ENG-5 High）
POST /journal action=sell 时，service 层在写 DB 前校验：
```python
if position.shares < sell_shares:
    raise HTTPException(422, "卖出数量超过持仓")
```

### baostock session 生命周期（ENG-6 High）
每次 POST /prices/refresh 调用时：
```python
bs.login()
try:
    # 查询所有持仓
finally:
    bs.logout()
```
不持久化 session，不并发调用。

### GET /positions 返回 is_stale 字段（ENG-3 High）
响应中包含 `price_date` 和 `is_stale: bool`（最近快照日期距今 > 1 个交易日则 true）。

### float 转换（ENG-7 Medium）
baostock 返回字符串，服务层必须 `float(rs.get_row_data()[1])`。

### 周末重复快照（ENG-8 Medium）
捕获 UNIQUE(symbol, date) 冲突视为成功返回（not error）。

## 开放问题

1. **价格刷新触发**：v1 手动点击"刷新价格"按钮，不做定时任务
2. **baostock 非交易日**：baostock 返回最近交易日数据，直接展示即可，标注日期
3. **跨域**：FastAPI 需启用 CORS（localhost:3000 → :8000）（自动决策 #2）
4. **SQLite 并发**：单用户本地运行，无并发问题

## 成功标准

- 能录入 3 只持仓，看到盈亏数字
- 能记录一笔卖出，看到 P&L 自动计算
- 每天打开这个工具 > 每天打开证券 App
