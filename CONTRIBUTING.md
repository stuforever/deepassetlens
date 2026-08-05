# 贡献指南

感谢你对 DeepAssetLens 的关注！欢迎提交 Issue 和 Pull Request。

## 开发环境

参考 [README.md](README.md) 的「快速启动」章节搭建本地开发环境。

## 贡献流程

1. **Fork** 仓库并克隆到本地
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改，确保：
   - 代码风格与现有代码一致
   - 不引入新的硬编码密码 / API key（敏感信息走环境变量）
   - 新增依赖写入 `requirements.txt` / `package.json`
4. 提交 Pull Request，描述改动内容与动机

## 代码规范

- **后端（Python）**：遵循 PEP 8，类型注解齐全，函数有 docstring
- **前端（TypeScript）**：`tsc --noEmit` 零错误，组件用函数式 + Hooks
- **数据库**：新增表用 SQLAlchemy 模型，`Base.metadata.create_all` 自动建表

## 安全要求

- ❌ 绝不在代码中硬编码密码、API key、连接串
- ✅ 敏感配置走环境变量（`.env` / `.env.infra`，已被 `.gitignore` 忽略）
- ✅ 提交前自检：`git grep -nE "sk-[a-zA-Z0-9]{20,}|password=.*[a-zA-Z0-9]{8}"` 应无真实凭据

## 提交信息

使用清晰的提交信息：

```
feat: 新增 XX 功能
fix: 修复 XX 问题
refactor: 重构 XX
docs: 文档更新
chore: 杂项
```

## License

提交即表示你同意将代码以 [Apache 2.0](LICENSE) 协议开源。
