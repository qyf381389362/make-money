# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is a new, empty project. Update this file as the codebase takes shape.

## 语言规范

- 所有文档、注释、设计文档、计划文件、PRD 一律使用**简体中文**撰写
- 代码中的变量名、函数名、类名保持英文（代码规范不受此约束）
- 代码注释如无特殊原因，使用简体中文
- 与外部系统对接的 API 字段名、枚举值保持英文

## 占位符与 TODO 规范

代码中存在暂时无法填入的值（如待确认的 URL、密钥、环境参数）时，**必须**在同一行或紧邻行添加 `TODO:` 注释，说明待填内容和原因，避免遗漏。

示例：
```typescript
// TODO: Tesla CN OAuth 回调地址待 ICP 备案完成后确认
callbackUrl: '<TESLA_CN_OAUTH_CALLBACK_URL>',
```

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec
