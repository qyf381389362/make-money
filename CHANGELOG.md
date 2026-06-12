# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning.

## [0.2.0.0] - 2026-06-12

### Added
- **AI 决策动机审计**：接入 Gemini (`gemini-2.5-flash`)，交易日记写入后通过 FastAPI BackgroundTasks 异步审计交易心理（追涨杀跌 / 贪婪 / 恐慌 / 理性分析 / 其它），结果缓存至 `journal_entries.motivation_type` 与 `ai_audit`，并带超时与降级容错。
- **AI 复盘看板**：新增 `frontend/components/AiMetrics.tsx`，以交易心理健康分、性格雷达、偏误盈亏榜与累计已实现盈亏趋势曲线（recharts）多维呈现行为偏差。
- **场外公募基金行情**：扩展价格服务，对 6 位 `fund` 代码分流至天天基金接口拉取单位净值，支持场内外混合资产的盈亏核算。
- **日记搜索与筛选**：`JournalList` 支持按“原因”模糊搜索与筛选。
- 新增针对 AI 审计与基金价格路由的 `pytest` 用例。

### Changed
- 同步 `specs/v1b-ai-and-funds.md` 规格与实现：字段名 `ai_audit`（原文档误作 `motivation_analysis`）、模型 `gemini-2.5-flash`、心理类别枚举。

## [0.1.0.0] - 2026-06-09

### Added
- **单元测试支持**：为加权平均成本和超卖等核心业务逻辑编写了完整的 `pytest` 单元测试，将后端核心逻辑覆盖率提升至 100%。

### Changed
- **骨架屏与按钮状态**：在刷新价格期间增加了按钮禁用和更清晰的骨架屏遮罩过渡，优化了行情加载缓慢时的用户交互。
- **Snapshots SQL 优化**：使用窗口函数（Window Function）优化了获取最新价格的查询，解决每次拉取 positions 最新快照时的 N+1 SQL 性能隐患。

### Fixed
- **除零崩溃保护**：在 `backend/routers/journal.py` 的买入均价计算中，增加了 `new_shares <= 0` 的 422 异常处理，防止除零崩溃。
- **行情刷新冲突容错**：在 `/prices/refresh` 接口中，优雅捕获了 `IntegrityError` 唯一约束冲突，自动回滚并跳过已有快照，保证服务在周末或重复拉取时不崩溃。
- **物理清仓删除持仓**：修复了在全额卖出持仓后，由于仅更新份额为 0 导致前端持仓记录残留的问题，现在会自动从 `positions` 表中彻底删除对应的记录。
- **全显 '--' 逻辑修复**：修复了在部分持仓缺乏价格时，总市值和总盈亏由于严格校验全部显示为 '--' 的交互 Bug，改为降级使用均价兜底以提供完整的数据展示。
