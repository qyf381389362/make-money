# Make Money — 个人持仓仪表板与决策日记 (v1a)

Make Money 是一个专为个人投资者打造的**本地持仓仪表板与投资决策日记**系统。针对主流证券 App 缺乏个人账户连接、无法闭环决策反馈的核心缺口，Make Money v1a 版本提供了一个本地化的解决方案：记录您每次交易背后的决策动机，自动进行均价计算与盈亏核算，为未来的 AI 复盘打下基础。

---

## 🌟 核心功能

1. **持仓仪表板**
   - **手动录入**：支持录入持仓（代码、名称、股数、均价、资产类型）。
   - **每日收盘行情拉取**：集成 `baostock` 自动批量下载 A 股最新快照价格。
   - **实时损益汇总**：自动计算总成本、当前总市值、总盈亏金额及百分比。
   - **交互友好**：行情刷新状态提供按钮置灰及骨架屏半透明遮罩，具备数据过期（Stale）及缺失兜底。

2. **决策日记**
   - **交易记录**：买入/卖出时录入股数、价格、日期及投资原因（自由文本）。
   - **加权平均成本核算**：采用移动加权平均成本法（买入重新折算均价，卖出保持均价不变）。
   - **清仓物理删除**：卖出持仓量归零时，自动物理删除 `positions` 对应记录，保持仪表盘干净。
   - **除零与超卖保护**：后端在 Pydantic 校验和 Service 层严格防御，防范超卖（HTTP 422）及均价折算除零崩溃。

---

## 🛠️ 技术栈与架构

- **前端**：Next.js 14 (TypeScript, App Router, Vanilla CSS, Tailwind CSS)
- **后端**：FastAPI (Python 3.11+, SQLAlchemy, Uvicorn)
- **数据库**：MySQL / SQLite
- **数据源**：BaoStock API
- **包管理**：`uv` (Python) + `pnpm` (Node.js)

### 架构拓扑
```
[用户浏览器 (localhost:3000)]
      │ (CORS)
      ▼ [HTTP JSON]
[FastAPI 后端 (localhost:8000)]
      ├── [SQLAlchemy ORM] ──▶ [MySQL / SQLite]
      └── [baostock_service] ──▶ [baostock API (外部数据)]
```

---

## 🚀 快速启动指南

### 1. 后端配置与运行
需要安装 `uv` 模块包管理器。

1. 进入后端目录：
   ```bash
   cd backend
   ```
2. 安装依赖：
   ```bash
   uv sync
   ```
3. 配置环境变量（默认使用 SQLite 本地数据库 `make_money.db`）：
   创建 `.env` 并注入数据库连接：
   ```env
   DATABASE_URL=sqlite:///./make_money.db
   ```
4. 运行数据库表初始化与启动后端服务：
   ```bash
   uv run uvicorn main:app --port 8000 --reload
   ```
5. 运行单元测试：
   本系统具备完整的自动化单元测试，核心加权平均计算及超卖容错覆盖率达 **100%**：
   ```bash
   uv run pytest
   ```

### 2. 前端配置与运行
需要安装 `pnpm` 包管理器。

1. 进入前端目录：
   ```bash
   cd frontend
   ```
2. 安装项目依赖：
   ```bash
   pnpm install
   ```
3. 启动本地开发服务：
   ```bash
   pnpm dev
   ```
4. 打开浏览器访问：`http://localhost:3000`

---

## 📡 API 路由接口参考

- `GET  /positions` ：查询持仓列表，包含各持仓最新收盘价、`price_date` 以及是否过期的布尔值 `is_stale`。
- `POST /positions` ：手动录入新增持仓。
- `GET  /journal` ：查询交易日记列表（支持 `?symbol=xxx` 股票代码过滤）。
- `POST /journal` ：记录买入/卖出日记（事务安全，买入折算均价，卖出自动扣减，清仓物理删除）。
- `POST /prices/refresh` ：手动触发 `baostock` 行情下载（具备唯一约束 `IntegrityError` 周末重复冲突容错）。

---

## 🎨 界面配色 Token (A股红涨绿跌)
本系统采用符合中国 A 股及基金市场的配色 Token：
- 红色 (上涨)：`#E03A3A`
- 绿色 (下跌)：`#1DB954`
- 灰色 (持平/无价格)：`#8B8B8B`
