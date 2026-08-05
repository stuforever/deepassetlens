# ====================================================================
# tupu 项目 Git 初始化与 Gitea 推送脚本
#
# 前置条件：
#   1. Gitea 已通过 docker-compose.infra.yml 启动
#   2. 已在 Gitea Web 创建私有仓库 tupu（http://localhost:3001）
#   3. 本机已生成 SSH key 并添加到 Gitea 账号
#
# 用法：
#   .\scripts\init_gitea_repo.ps1
# ====================================================================

# 仓库地址（按需修改）
$GITEA_SSH = "ssh://git@localhost:2222"
$REPO_OWNER = "tupu"      # Gitea 中的组织/用户名
$REPO_NAME = "tupu"       # 仓库名

$REMOTE_URL = "$GITEA_SSH/$REPO_OWNER/$REPO_NAME.git"

Write-Host "=== tupu Git 初始化脚本 ===" -ForegroundColor Cyan
Write-Host "远程仓库: $REMOTE_URL"
Write-Host ""

# 1. 检查 .gitignore 是否存在
if (-not (Test-Path .gitignore)) {
    Write-Host "❌ .gitignore 不存在，请先创建" -ForegroundColor Red
    exit 1
}

# 2. 检查是否有敏感文件在暂存区
Write-Host "[1/6] 检查敏感文件..." -ForegroundColor Yellow
git init 2>$null
git add .gitignore
git add -A

$sensitive = @(".env.infra", "authentik_bootstrap.json", "backend/.env", "backend/authentik_bootstrap.json")
foreach ($f in $sensitive) {
    $staged = git diff --cached --name-only 2>$null
    if ($staged -match $f) {
        Write-Host "  ❌ 警告: $f 在暂存区！请检查 .gitignore" -ForegroundColor Red
        git reset HEAD $f 2>$null
    }
}

# 验证暂存区无敏感文件
$stagedFiles = git diff --cached --name-only
$dangerous = $stagedFiles | Where-Object {
    $_ -match "\.env(\.|$)" -or
    $_ -match "authentik_bootstrap" -or
    $_ -match "credentials" -or
    $_ -match "id_rsa"
}

if ($dangerous) {
    Write-Host "  ❌ 发现敏感文件在暂存区:" -ForegroundColor Red
    $dangerous | ForEach-Object { Write-Host "     $_" }
    Write-Host "  请处理后重新运行" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ 无敏感文件" -ForegroundColor Green

# 3. 检查大文件
Write-Host "[2/6] 检查大文件（>10MB）..." -ForegroundColor Yellow
$bigFiles = git diff --cached --name-only | ForEach-Object {
    if (Test-Path $_) {
        $size = (Get-Item $_).Length
        if ($size -gt 10MB) { "$_ ($([math]::Round($size/1MB,1))MB)" }
    }
}
if ($bigFiles) {
    Write-Host "  ⚠️  发现大文件:" -ForegroundColor Yellow
    $bigFiles | ForEach-Object { Write-Host "     $_" }
    Write-Host "  建议用 Git LFS 或排除" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ 无大文件" -ForegroundColor Green
}

# 4. 首次提交
Write-Host "[3/6] 创建首次提交..." -ForegroundColor Yellow
git commit -m "feat: 初始化 tupu 知识图谱平台代码" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ 提交成功" -ForegroundColor Green
} else {
    Write-Host "  ℹ️  已有提交，继续" -ForegroundColor Yellow
}

# 5. 添加远程并推送
Write-Host "[4/6] 配置远程仓库..." -ForegroundColor Yellow
$existing = git remote get-url origin 2>$null
if ($existing) {
    git remote set-url origin $REMOTE_URL
    Write-Host "  ✓ 更新 origin: $REMOTE_URL" -ForegroundColor Green
} else {
    git remote add origin $REMOTE_URL
    Write-Host "  ✓ 添加 origin: $REMOTE_URL" -ForegroundColor Green
}

Write-Host "[5/6] 推送到 Gitea..." -ForegroundColor Yellow
git branch -M main
git push -u origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ 推送成功" -ForegroundColor Green
} else {
    Write-Host "  ❌ 推送失败，请检查:" -ForegroundColor Red
    Write-Host "     1. Gitea 是否启动: docker ps | findstr gitea"
    Write-Host "     2. SSH key 是否添加到 Gitea"
    Write-Host "     3. 仓库 $REPO_OWNER/$REPO_NAME 是否在 Gitea 创建"
    exit 1
}

Write-Host "[6/6] 完成" -ForegroundColor Green
Write-Host ""
Write-Host "代码已推送至: $REMOTE_URL" -ForegroundColor Cyan
Write-Host "Web 访问: http://localhost:3001/$REPO_OWNER/$REPO_NAME" -ForegroundColor Cyan
