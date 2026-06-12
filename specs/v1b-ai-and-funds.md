# v1b 规格说明书：AI 决策动机复盘与多数据源基金支持

本规格说明书针对 Make Money 项目在 `v1a` 交付之后的 `v1b` 深度迭代展开。目标是引入 Gemini API 对用户的投资决策进行动机偏差审计，并增加对场外公募基金净值获取的支持。

---

## 1. AI 决策动机审计 (AI Audit)

### 1.1 数据库结构更新 (`journal_entries`)
需要对 `journal_entries` 表增加两个字段，以缓存大模型的异步审计结果：
```sql
ALTER TABLE journal_entries ADD COLUMN motivation_type VARCHAR(20) DEFAULT NULL;
ALTER TABLE journal_entries ADD COLUMN ai_audit TEXT DEFAULT NULL;
```
在 Python SQLAlchemy `models.py` 中对应的实体更新：
```python
motivation_type = Column(String(20), nullable=True)
ai_audit = Column(Text, nullable=True)
```

### 1.2 异步 AI 审计工作流 (FastAPI BackgroundTasks)
当用户提交交易记录时，后端在事务提交后触发异步的 Gemini 审计，以避免阻塞核心接口响应。

1. **接口变更**：`POST /journal` 接口接收 `BackgroundTasks`。
2. **异步执行方法**：
   ```python
   def audit_motivation_task(entry_id: int, db_session_factory):
       # 1. 查询 entry
       # 2. 调用 Gemini API 传入交易上下文
       # 3. 解析 JSON 响应
       # 4. 更新数据库对应行
   ```
3. **Gemini API 请求定义**：
   - **API 端点**：`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}`
   - **请求体 (Payload)**：
     ```json
     {
       "contents": [{
         "parts": [{
           "text": "你是一位 brutally 且专业的投资心理分析师。分析以下交易决策动机，判定其心理动机类型。\n类型限定为以下之一：['追涨杀跌', '贪婪', '恐慌', '理性分析', '其它']。\n\n交易明细：\n证券代码：{symbol}\n方向：{action}\n份额：{shares}\n价格：{price}\n决策动机：{reason}\n\n必须且仅返回如下严格的 JSON 格式：\n{\n  \"motivation_type\": \"跟风/恐慌/盲目冲动/理性分析/其它\",\n  \"motivation_analysis\": \"一句话直击要害的心理偏差诊断\"\n}"
         }]
       }],
       "generationConfig": {
         "responseMimeType": "application/json"
       }
     }
     ```

> 注：1.2 的示例 Prompt 仅为早期示意；权威实现以 `backend/services/gemini.py` 为准（枚举 `['追涨杀跌','贪婪','恐慌','理性分析','其它']`，输出字段为 `ai_audit`，而非 `motivation_analysis`）。

### 1.3 前端统计面板 (AI Dashboard) — ✅ 已实现于 `frontend/components/AiMetrics.tsx`
前端看板增加以“决策动机”为维度的盈亏核算：
- 聚合每个 `motivation_type` 对应的平仓已实现盈亏 (P&L)。
- 使用饼图或卡片展示本周“盲目冲动”、“跟风”所带来的亏损占比，以进行心理矫正与行为问责。

---

## 2. 场外公募基金与多数据源价格拉取 (Fund Support)

BaoStock 不支持 6 位场外基金（如 `161725` 等）。我们需要设计数据源路由器（Data Source Router）。

### 2.1 基金代码识别与 API 路由
- 规则：如果 `asset_type == 'fund'` 且代码长度为 6，系统将其判定为场外基金，分流至天天基金数据源。
- **天天基金 API 端点**：
  `http://fundgz.1234567.com.cn/js/{symbol}.js?rt={timestamp}`
- **响应体解析**：
  接口返回 JSONP 字符串：`jsonpgz({"fundcode":"161725","dwjz":"0.8520","jzrq":"2026-06-08",...});`
  使用正则提取并解析成日终快照写入 `daily_snapshots` 表：
  - `dwjz` (单位净值) -> `close_price`
  - `jzrq` (净值日期) -> `date`

---

## 3. 任务分解与开发顺序

| 任务 ID | 优先级 | 组件 | 影响文件 | 估算工时 | 验证标准 |
|---|---|---|---|---|---|
| **T5** | P1 | Backend | `models.py`, `schemas.py`, `routers/journal.py`, `services/gemini.py` | 2.5h | 调用 `/journal` 写入后，数据库异步填充正确的动机类型与短评 |
| **T6** | P2 | Frontend | `components/Ai看板.tsx`, `page.tsx` | 2h | 能够按决策心理类别统计平仓盈亏占比并以图表显示 |
| **T7** | P1 | Backend | `services/baostock_service.py`, `routers/prices.py` | 1.5h | 输入基金代码（如 161725）刷新价格，天天基金接口成功拉取并持久化快照 |
| **T8** | P2 | Frontend | `components/PortfolioTable.tsx` | 1h | 场外基金显示净值、价格日期且盈亏准确，价格刷新期间无报错 |
| **T9** | P3 | Frontend | `components/JournalList.tsx` | 1h | 列表能够通过顶部输入框对“原因”字段进行前端模糊搜索及日期筛选 |

---

## 4. 回滚方案
- **数据结构**：如果需要回滚数据库，运行以下 SQL：
  ```sql
  ALTER TABLE journal_entries DROP COLUMN motivation_type;
  ALTER TABLE journal_entries DROP COLUMN motivation_analysis;
  ```
