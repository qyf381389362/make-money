# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning.

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
