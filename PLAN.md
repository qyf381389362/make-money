<!-- /autoplan restore point: /Users/michael/.gstack/projects/make-money/feature-v1b-ai-fund-autoplan-restore-20260612-210450.md -->
# Make Money - 下阶段开发计划 (v2.0)

在完成了 v1b 的 AI 决策审计、混合资产价格拉取（BaoStock + 天天基金）以及完善了系统的健壮性之后，系统已经具备了核心的“记录 -> AI 反馈 -> 资产统计”的闭环。

针对下一步的开发，我们有以下几个重点方向可以探索：

## 选项 A: 深度复盘图表分析 (推荐)
目前的日记列表只能通过文字和标签查看过去的决策，缺乏全局视角。
- **盈亏日历/时间线图表**：直观展示不同日期的总盈亏变化。
- **心理偏误雷达图**：根据 AI 打上的标签（如“追涨杀跌”、“恐慌”、“理性分析”），绘制出属于你个人的交易性格雷达图或饼图，帮助你了解最容易犯的错误类型。
- **个股/基金专属复盘**：点击某个资产，显示你在它身上的“买卖点标记图”（类似同花顺的 B/S 标记）以及它给你带来的总盈亏。

## 选项 B: 用户账户与权限系统
目前系统是单机版，所有人访问 localhost 看到的数据都是一样的。
- **注册/登录功能**：基于 JWT 和 Bcrypt 加密的独立账号系统。
- **多租户数据隔离**：修改 `Position` 和 `JournalEntry` 表，加入 `user_id`，让你可以在云服务器上部署给朋友们一起使用。

## 选项 C: 自动化预警与数据导出
- **止盈止损预警**：在添加持仓时设定目标价/止损价，利用定时任务（BackgroundTasks/Celery）拉取价格并发送邮件或系统内提醒。
- **月度复盘导出**：将过去一个月的决策日记和 AI 评语一键导出为精美的长图或 Excel 文件，方便存档。

---

**当前架构健康度评估 (Auto-Review):**
- **✅ 类型安全**: 后端全面使用 Pydantic 和 SQLAlchemy 2.0，前端已补充完整 API 类型。
- **✅ 容错性**: 爬虫和 AI 服务都加入了超时和异常捕获，`httpx.ReadTimeout` 已经修复，UI 轮询也已实装。
- **⚠️ 测试覆盖率**: 需要随着新功能的加入继续补充 `pytest` 案例。

---
<!-- AUTONOMOUS DECISION LOG -->
## 🔍 /autoplan 审查报告 — CEO 战略审查 (Phase 1)

> 审查模式：**SELECTIVE EXPANSION（选择性扩展）**
> 双 voice 状态：**单审查员模式** — 本机未安装 Codex CLI，本次仅由 Claude 主审，**无第二模型独立 voice**。
> 时间：2026-06-12 ｜ 分支：`feature/v1b-ai-fund` ｜ commit `1a3d5de`

### 0A · 前提挑战 (Premise Challenge)

| 前提 | 计划的假设 | 审查判定 |
|---|---|---|
| P1 | “v1b 已完成” | ❌ **不成立**。v1b 是 **889 行未提交**的工作区改动；`gemini.py`、`AiMetrics.tsx`、`list_models.py` 甚至未 `git add`。没有提交、没有 PR、没有合并。 |
| P2 | “现在应挑选 v2.0 大方向” | ⚠️ **为时过早**。P1 未成立时，最高杠杆的下一步是**先把 v1b 落地**。 |
| P3 | “选项 A（复盘图表）是新增能力” | ❌ **大部分已建成**。`AiMetrics.tsx` 已渲染累计盈亏时间线、心理偏误雷达、偏误盈亏柱状图——正是 A 的两个头牌功能。`recharts` 已是依赖。A 真正新增的只有“个股 B/S 标记图”。 |
| P4 | “A/B/C 是正确的候选集” | ⚠️ **不完整**。`TODOS.md` 已把 v2.0 定义为 T10–T13，其中**最高优先级 T11（券商交割单自动导入，P1）被排除在菜单外**；而选项 C（预警/导出）不在 TODOS 中。菜单与既有路线图未对齐。 |

### 0B · 复用地图 (What Already Exists)

| 子问题 | 既有实现 | 状态 |
|---|---|---|
| 盈亏时间线图 | `AiMetrics.tsx` 累计已实现盈亏趋势 AreaChart | ✅ 已建 |
| 心理偏误雷达/分布 | `AiMetrics.tsx` 性格雷达 + 偏误盈亏榜 | ✅ 已建 |
| 交易健康分 | `AiMetrics.tsx` healthScore（计划之外的额外能力） | ✅ 已建 |
| 图表库 | `recharts ^3.8.1` 已在 `package.json` | ✅ 已有 |
| AI 动机标签数据 | `journal_entries.motivation_type` + `ai_audit`，`gemini.py` | ✅ 已建 |
| 混合资产净值 | `baostock_service.py` + 天天基金路由，`prices.py` | ✅ 已建 |
| 日记搜索/筛选 | `JournalList.tsx`（v1b T9） | ✅ 已建 |
| 个股 B/S 标记数据 | `journal_entries` 已含 symbol/action/price/trade_date/pnl | ⚠️ 数据齐备，**仅缺按标的的图表视图** |

### ⚠️ v1b 落地前需修正的漂移 (Spec/Code Drift)

- **字段命名**：规格写 `motivation_analysis`，实际代码（`models.py`/`schemas.py`/`journal.py`）用 `ai_audit`。代码内部一致，**规格文档已过期**。
- **模型版本**：规格写 `gemini-1.5-flash`，代码用 `gemini-2.5-flash`。
- **枚举**：规格 `['跟风','恐慌','盲目冲动','理性分析','其它']`，代码 `['追涨杀跌','贪婪','恐慌','理性分析','其它']`（前后端一致）。
- 建议落地前用一次提交把规格同步到实现，避免后人误读。

### 0C · 校正后的方向对比 (Corrected Options)

> “选项 A”大部分已完成，不再是一个独立方向。先落地 v1b，再在以下真实分叉中取舍：

| 方向 | 真正的净新增工作 | CC 估时 | 价值 | 风险 |
|---|---|---|---|---|
| **① 先落地 v1b（建议首做）** | 修正规格漂移、跑 pytest、提交、开 PR | ~20–40min | 解锁一切；为 889 行未发布代码去风险 | 低 |
| A′ 复盘图表（精简） | 仅个股 B/S 标记图（+可选 T12 资产漏斗 / T13 总资产曲线） | ~1–2h | 中（锦上添花） | 低 |
| B 账户/多租户 (T10) | JWT+Bcrypt、三表加 `user_id`、每条查询按 user 隔离、前端登录 | ~半天 | 高（若目标是“给朋友用/上云”） | 中（迁移 + 每条查询都必须过滤 `user_id`，安全关键） |
| C 预警+导出 | 目标/止损价字段、定时拉价、通知渠道、导出 | ~半天 | 中高（主动提醒） | 中（BackgroundTasks 不足以做周期任务，需 APScheduler/cron；邮件投递） |
| **T11 券商交割单导入（被漏掉，P1）** | 解析券商 CSV → `journal_entries` + 初始化持仓 | ~半天 | **高**（消除最大摩擦：手工录入；让工具能跑真实历史） | 中（各券商格式长尾） |

### 推荐路径 (Recommendation)

1. **立刻：先落地 v1b**（修正规格漂移 → pytest → 提交 → PR）。889 行已能工作、带测试的代码停在工作区，先发布它的价值高于规划 v2.0。
2. **顺手：把“个股 B/S 标记图”当作一个小任务并入**，而非一个大方向——A 的其余部分已在 `AiMetrics.tsx` 里。
3. **v2.0 真正的取舍取决于你的目标**：想用真实交易历史 → **T11 导入**（ROI 最高）；想给朋友用/上云 → **B 账户**；想被动盯盘 → **C 预警**。

> 这一步是 autoplan 的**前提确认门**——需要你拍板，下面的工程/设计深审将基于你选择的路径展开。

<!-- Decision Audit Trail -->
### 决策审计 (Decision Audit Trail)

| # | 阶段 | 决策 | 分类 | 原则 | 理由 |
|---|---|---|---|---|---|
| 1 | CEO | 审查模式 = SELECTIVE EXPANSION | Mechanical | P1 | 计划漏项（T11）且高估 A，需校正而非重写 |
| 2 | CEO | 挑战“v1b 已完成”前提 | 前提门 | P6 | 889 行未提交，落地优先 |
| 3 | CEO | 判定 Option A 大部分已建成 | Mechanical | P4 (DRY) | `AiMetrics.tsx` 已渲染时间线+雷达+柱状 |
| 4 | CEO | 把 T11 重新纳入候选 | Taste | P1/P2 | TODOS 中 P1 项被菜单遗漏，价值高 |
| 5 | CEO | 推荐“先落地 v1b” | 前提门→用户 | P6 | bias toward action：先发布在制品 |

> **v1b 落地状态：✅ 已完成** — 代码 commit `7e8caaf` + 整理 commit `7e73ff3`，已推送并开 PR #2（22/22 测试通过，规格已同步实现）。

---
## 🔧 /autoplan 审查报告 — T11 工程/设计深审 (Phase 3 Eng + Phase 2 Design)

> 方向：**T11 券商交割单自动导入**（你的 D2 选择）。模式 SELECTIVE EXPANSION，单审查员（Claude，无 Codex 第二 voice）。
> 性质：本节是**实现计划 + 审查**，尚未编码；建议 v1b（PR #2）合并后另开分支 `feature/v2-broker-import` 实施。

### Phase 3 · 工程审查 (Eng)

#### 架构总览

```
[券商交割单 CSV (GBK)]
      │ 上传 (multipart)
      ▼
[POST /import/preview] ──▶ [broker_import 解析层]
      │                       ├── base_parser (列映射协议)
      │                       ├── adapters/ (同花顺 / 东方财富 / 通用映射)
      │                       └── 产出: ParsedTrade[] + 问题清单(不可解析/疑似重复)
      │ (只读, 不写库)
      ▼
[前端预览表] ──用户确认──▶ [POST /import/commit]
                                  │ 按 (trade_date, 行序) 稳定排序
                                  ▼
                          [trade_engine.apply_trade()] ◀── 复用 (record_trade 也调用它)
                                  ├── 建/改 Position（含首买建仓）
                                  ├── 加权均价 / 超卖保护 / 平仓 pnl / 清仓删除
                                  └── 写 JournalEntry(external_id 去重)
                                  ▼
                          [导入结果摘要: 成功 N / 跳过重复 M / 失败 K]
```

#### 0 · 复用地图与关键重构（DRY — 最重要的一条）

当前 `routers/journal.py:record_trade` 把「加权均价 / 超卖保护 / 平仓盈亏 / 清仓删除」**内联**写在 HTTP 处理函数里，且**强制要求持仓已存在**（`pos is None → 404`，line 26-27）。导入要逐笔回放这套逻辑，**绝不能复制一份**。

**重构（T11 的地基）**：抽取核心为纯服务函数
```python
# services/trade_engine.py
def apply_trade(db, *, symbol, name, asset_type, action, shares, price,
                trade_date, reason=None, external_id=None,
                create_position_if_missing=False, fee=Decimal(0)) -> JournalEntry:
    # 返回写入的 JournalEntry；不抛 HTTPException，改抛领域异常 TradeError
```
- `record_trade` 改为：调 `apply_trade(create_position_if_missing=False)` → 捕获 `TradeError` 转 HTTPException → 仍触发 AI 审计（行为不变）。
- 导入器：逐笔调 `apply_trade(create_position_if_missing=True)`，**不**触发 AI 审计。
- 收益：单一可信记账核心，两入口共享；现有 22 条测试继续护航。

#### 1 · 数据模型变更

| 变更 | 原因 |
|---|---|
| `journal_entries.external_id VARCHAR(64) NULL` + 唯一索引（仅非空生效） | **幂等去重**：以券商「成交编号」为键，重复导入同一对账单不重复计数 |
| `journal_entries.fee NUMERIC NULL` ✅ | 交割单含手续费/印花税；**计入成本**：买入并入 `avg_cost`、卖出从 `pnl` 净扣（手工录入保持 `fee=0`）|
| 首买建仓需 `name`/`asset_type` | `positions.symbol` 唯一且当前 `record_trade` 不建仓；交割单未必含名称/类型，需推断或预览补全 |

> **排序隐患**：模型仅有 `trade_date`(date) 无日内时序。同日多笔成交的均价回放顺序依赖行序。MVP：解析保留行序，按 (trade_date, 行序) 稳定排序回放；必要时加 `trade_seq`。

#### 2 · 解析层

- **编码**：国内券商导出多为 **GBK/GB2312**，必须显式解码（先 utf-8-sig 再回退 gbk），否则中文列名乱码。
- **格式差异**：各券商列名/动作词不同。MVP 范围：1 个具体适配器（取你实际用的券商）+ 1 个**通用列映射**（预览时把 CSV 列对到 {日期,代码,名称,方向,数量,价格,成交编号,费用}）。
- **动作映射**：买入类→buy，卖出类→sell；**非买卖行（分红/送股/银证转账/利息）MVP 跳过并在预览标注**，不静默吞掉。

#### 3 · 接口（两步：预览 → 确认）

- `POST /import/preview`（文件 + 可选 broker/列映射）→ 只读解析，返回 `{rows, issues, dup_count, parsable_count}`，**不写库**。
- `POST /import/commit`（已确认 rows）→ **单事务**批量回放 `apply_trade`，按 external_id 去重，返回 `{imported, skipped_dup, failed:[{row,reason}]}`。

#### 失败模式登记表 (Failure Modes Registry)

| ID | 场景 | 不处理的后果 | MVP 对策 |
|---|---|---|---|
| F1 | GBK 编码未处理 | 中文乱码，解析全错 | 显式 gbk 回退解码 |
| F2 | 重复导入同一对账单 | 持仓与盈亏翻倍 | `external_id` 唯一去重 + 预览标重复 |
| F3 | 同日多笔乱序回放 | 加权均价算错 | 按 (trade_date, 行序) 稳定排序 |
| F4 | 手续费/印花税未计 | 成本/盈亏与券商对不上 | ✅ **计入成本**：买入并入 `avg_cost`、卖出净扣 `pnl`，新增 `fee` 列；手工录入暂保持 `fee=0`（已标注不一致）|
| F5 | 首买无持仓 | 现有 `record_trade` 直接 404 | `apply_trade` 支持建仓 |
| F6 | 非买卖行（分红/送股） | 解析报错或错记为买卖 | 识别跳过 + 预览标注（公司行为不在 MVP）|
| F7 | 批量触发 AI 审计 | 数百次 Gemini 调用，配额/费用爆炸 | 导入不触发审计 |
| F8 | 半途失败 | 脏均价/部分持仓 | 整批单事务回滚 |
| F9 | 代码类型推断错 | 行情路由错（天天基金 vs BaoStock）| 预览让用户确认 asset_type |

#### 测试图谱 (Test Diagram → 覆盖)

| 代码路径/流程 | 测试类型 | 新增? |
|---|---|---|
| 买入加权均价 / 卖出 pnl / 超卖 / 清仓删除 | 单元 | 复用现有 |
| `apply_trade` 首买建仓 | 单元 | 新增 |
| GBK 解析 + 列映射 | 单元（GBK 字节样例） | 新增 |
| `external_id` 去重（重复导入） | 集成 | 新增 |
| 同日乱序排序正确性 | 单元 | 新增 |
| 非买卖行跳过 | 单元 | 新增 |
| `/import/preview` 只读不写库 | 集成 | 新增 |
| `/import/commit` 单事务回滚 | 集成 | 新增 |
| 混合：手工持仓 + 导入去重不冲突 | 集成 | 新增 |

### Phase 2 · 设计审查 (Design)

UI 范围：是（导入弹窗 + 预览表）｜ 开发者体验范围：否（个人工具）。

#### 导入旅程与关键状态

上传 → 解析中 → **预览(核心)** → 确认 → 完成；异常：解析失败 / 编码错 / 全部重复。

| 状态 | 设计要点（复用 v1a/v1b 已有骨架屏与兜底风格）|
|---|---|
| 上传 | 拖拽/选择 CSV + 券商格式下拉（含“通用映射”）|
| 解析中 | loading（复用刷新置灰/遮罩）|
| **预览** | 表格：日期/代码/名称/方向/数量/价格/费用/状态；**重复行**灰显标“已存在”，**异常行**红标可展开原因；顶部统计「可导入 N / 重复 M / 异常 K」；通用映射模式顶部一排列映射下拉 |
| 确认 | 「导入 N 笔」主按钮 + 二次确认（写库不可一键撤销）|
| 完成 | 摘要卡：成功/跳过/失败，失败行可展开；引导去仪表盘 |
| 错误 | 编码错/空文件/列缺失 → problem + cause + fix 文案 |

> **信息层级**：预览页第一眼是「可导入多少 / 有多少异常」，其次逐行核对，最后才是确认——让用户**先信任解析结果再落库**。

### 单审查员共识表（无第二模型 voice）

| 维度 | Claude 判定 | 说明 |
|---|---|---|
| 架构是否合理 | ✅ | 命门是抽取 `apply_trade` 复用记账核心 |
| 测试是否充分 | ⚠️→✅ | 需补解析/去重/排序/事务回滚用例（已列） |
| 性能风险 | ✅ | 批量单事务；唯一风险=导入触发 AI 审计→已禁用 |
| 安全/数据完整 | ⚠️ | `external_id` 去重 + 原子性是数据正确性命门，必须先做 |
| 错误路径 | ✅ | 失败模式表覆盖编码/重复/乱序/公司行为/半途 |
| 交付风险 | ✅(可控) | MVP 限 1 适配器+通用映射，公司行为/多账户显式 defer |

### MVP 范围 vs 明确推迟 (NOT in scope)

- **MVP**：`apply_trade` 重构 + `external_id` 去重 + **同花顺适配器** + 通用列映射 + `fee` 计入成本 + 预览/确认两步 + 上述测试。
- **推迟（写入 TODOS）**：公司行为（分红/送股/拆合股）自动入账、多券商×多账户合并、费用精确税费明细、PDF/图片 OCR 对账单、增量自动同步。

#### 决策审计追加 (Decision Audit Trail — T11)

| # | 阶段 | 决策 | 分类 | 原则 | 理由 |
|---|---|---|---|---|---|
| 6 | Eng | 抽取 `apply_trade` 复用记账核心 | Mechanical | P4 DRY | 避免导入复制 `record_trade` |
| 7 | Eng | 加 `external_id` 唯一去重 | Mechanical | P1 | 幂等导入，防翻倍 |
| 8 | Eng | 导入不触发 AI 审计 | Mechanical | P3 | 防数百次 Gemini 调用 |
| 9 | Eng | MVP 首个适配器 = **同花顺** + 通用映射 | ✅ 已定（你的实际券商） | P5/P3 | 贴合真实数据 |
| 10 | Eng | 费用处理 = **计入成本**（+`fee` 列） | ✅ 已定 | P1 | 与对账单一致；手工录入暂 `fee=0` |
| 11 | Design | 强制预览/确认两步 | Mechanical | P1 | 写库不可一键撤销，先信任后落库 |
| 12 | Scope | 公司行为/多账户 defer | Mechanical | P2 | 超出 MVP blast radius |
