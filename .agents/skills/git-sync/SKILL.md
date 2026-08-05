---
name: git-sync
description: 将 tupu 项目代码同步到 Gitea 仓库。当用户说"上传同步到git"、"同步到git"、"推送到git"、"提交到git"、"git同步"、"代码同步"、"上传代码"时触发。自动执行 git add、commit、push 到 Gitea 远程仓库。
---

# Skill: git-sync

将 tupu 项目代码变更同步到 Gitea 仓库。

## 仓库信息

- **Gitea 地址**: http://127.0.0.1:3001/
- **仓库**: tupuadmin/tupu（私有）
- **远程 URL**: http://127.0.0.1:3001/tupuadmin/tupu.git
- **分支**: main
- **凭据**: 已配置 credential.store（免密，凭据存于 ~/.git-credentials）
- **项目根目录**: D:/gitcangku/DB-GPT/tupu

## 执行步骤

收到"上传同步到git"等触发语后，按以下步骤执行：

### 1. 检查变更状态

```bash
cd "D:/gitcangku/DB-GPT/tupu" && git status --short
```

- 如果没有变更（输出为空），告知用户"工作区干净，无需同步"并结束。
- 如果有变更，继续下一步。

### 2. 暂存变更

```bash
cd "D:/gitcangku/DB-GPT/tupu" && git add -A
```

### 3. 生成提交信息并提交

根据 `git status --short` 和 `git diff --cached --stat` 的输出，自动生成简洁的中文提交信息，概括本次变更内容（涉及哪些文件、什么类型的改动）。格式：

```
<类型>: <简述>

<改动要点1>
<改动要点2>
```

类型用 feat（新功能）/ fix（修复）/ refactor（重构）/ chore（杂项）/ docs（文档）。

```bash
cd "D:/gitcangku/DB-GPT/tupu" && git commit -m "<提交信息>"
```

### 4. 拉取远程更新（避免冲突）

```bash
cd "D:/gitcangku/DB-GPT/tupu" && git pull --rebase origin main 2>&1
```

- 如果有冲突，告知用户冲突文件，不要强行解决，让用户决定。
- 如果无冲突或无远程更新，继续推送。

### 5. 推送到 Gitea

```bash
cd "D:/gitcangku/DB-GPT/tupu" && git push origin main 2>&1
```

### 6. 报告结果

推送成功后，输出：
- 提交哈希（`git log --oneline -1`）
- 变更文件数
- 远程仓库链接：http://127.0.0.1:3001/tupuadmin/tupu

## 注意事项

- **敏感文件不入库**：.env、.env.infra、credentials、密钥等已被 .gitignore 排除，不要强制 add。
- **大文件不入库**：models/、node_modules/、build/ 等已被 .gitignore 排除。
- **不要修改 .gitignore** 除非用户明确要求。
- **不要 force push** 除非用户明确要求。
- 如果推送失败（403/网络错误），先检查 Gitea 服务是否可达：
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3001/
  ```
- 如果凭据失效（401），重新配置：
  ```bash
  echo "http://tupuadmin:Tupu@2026admin@127.0.0.1:3001" > ~/.git-credentials
  git config --global credential.helper store
  ```

## 协作说明

其他开发者加入时：
1. 管理员在 http://127.0.0.1:3001 用 tupuadmin 登录 → 右上角 → 管理面板 → 用户管理 → 添加账号
2. 新开发者：`git clone http://127.0.0.1:3001/tupuadmin/tupu.git`（输入账号密码）
