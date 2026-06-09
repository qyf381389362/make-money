# Contributing Guide — 开发者与贡献者指南

感谢您参与 Make Money 的开发！作为本项目的核心开发指南，本文档用于规范本地开发流程、分支管理、代码提交以及编码风格，以确保多端协作时的工程质量。

---

## 💻 本地开发环境搭建

项目采用双端分离架构：后端使用 `FastAPI` (Python)，前端使用 `Next.js` (Node.js)。

### 前提条件
- 安装 **Node.js** (≥ 18.0.0) 和 **pnpm** (推荐)
- 安装 **Python** (≥ 3.11) 和 **uv** (现代、极速的 Python 包管理器)

### 1. 后端配置 (backend)
1. 进入后端目录：
   ```bash
   cd backend
   ```
2. 使用 `uv` 安装依赖并同步虚拟环境：
   ```bash
   uv sync
   ```
3. 创建 `.env` 环境配置文件并注入 SQLite 本地连接：
   ```env
   DATABASE_URL=sqlite:///./make_money.db
   ```
4. 启动后端开发服务器（开启热重载）：
   ```bash
   uv run uvicorn main:app --port 8000 --reload
   ```

### 2. 前端配置 (frontend)
1. 进入前端目录：
   ```bash
   cd frontend
   ```
2. 安装依赖包：
   ```bash
   pnpm install
   ```
3. 启动前端 Next.js 开发服务器：
   ```bash
   pnpm dev
   ```
4. 访问本地控制台：`http://localhost:3000`

---

## 🌿 分支管理与发布工作流

项目使用基于特性的合并工作流（GitHub Flow）：

1. **拉取最新代码**：开发任何功能前，保证本地 `main` 分支是最新状态。
2. **创建特性分支**：以 `feature/` 或 `fix/` 开头，并具备明确的语义。
   ```bash
   git checkout -b feature/v1b-ai-summary
   ```
3. **提交与推送**：在特性分支上进行修改、测试并推送：
   ```bash
   git push -u origin feature/v1b-ai-summary
   ```
4. **运行测试**：在推送或提交 PR 前，**必须**运行全部测试：
   ```bash
   cd backend && uv run pytest
   ```
5. **发起 PR**：在 GitHub 上针对特性分支向 `main` 分支发起 Pull Request。

---

## 📝 代码提交规范 (Conventional Commits)

为使 `CHANGELOG.md` 自动提取更加清晰，提交信息必须遵循 Conventional Commits 规范，格式为：`<type>(<scope>): <subject>`

### 常用类别 (type)：
- **`feat`**：新增用户功能。
- **`fix`**：修复缺陷/Bug。
- **`docs`**：修改文档、README 或架构说明。
- **`test`**：新增、修改或扩展测试用例。
- **`refactor`**：代码重构（既不修复缺陷也不增加新功能）。
- **`chore`**：构建流程、依赖更新或版本发布等杂务。

### 示例：
```bash
git commit -m "feat(backend): 增加买入时的加权成本均价计算逻辑"
git commit -m "fix(frontend): 修复部分持仓缺乏价格时盈亏显示为 '--' 的交互 Bug"
```

---

## 🎨 编码规范与风格限制

### 1. Python 后端规范
- **类型标注**：所有公共函数、路由处理程序及 Service 层逻辑必须写明参数和返回值的强类型注解（例如：`def get_positions(db: Session) -> list[Position]:`）。
- **注释要求**：复杂的交易逻辑及财务核算公式必须附带中文注释，解释“为什么要这样写”。
- **测试保护**：涉及核心加权成本、超卖和数据库事务的代码，**必须**编写相对应的 `pytest` 测试用例，不允许出现无测试覆盖的交易逻辑改动。

### 2. TypeScript/Next.js 前端规范
- **React 风格**：优先采用函数式组件与现代 Hooks（如 `useCallback`, `useMemo`），避免编写类（Class）组件。
- **Props 约束**：所有 React 组件的 Props 必须有明确的 TypeScript 类型接口定义。
- **防占位符**：禁止在交互界面使用虚假的 Lorem Ipsum 等占位文本。若涉及图片或 UI 原型渲染，应使用真实的演示资产或生成符合项目背景的实际图像。
