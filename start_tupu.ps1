# tupu 工程统一启动脚本（纯静默后台执行，不弹任何 cmd 窗口）
#
# 启动顺序：
#   1) Docker 容器  qdrant + neo4j   (业务必备)
#      [可选] authentik 4 个容器     (-SkipAuth:$false 才启)
#   2) 后端 FastAPI   :8100  (py -3.11 -m uvicorn app.main:app)
#   3) 前端 CRA       :3000  (npm start，BROWSER=none)
#   4) LangGraph Studio :2024  (langgraph dev)
#
# 全部用 Start-Process -WindowStyle Hidden 静默后台启动，
# 输出重定向到 .runtime-logs\<svc>-YYYYMMDD-HHmmss.log
#
# 用法：
#   pwsh .\start_tupu.ps1                # 默认：跳过 authentik，启 qdrant+neo4j+前后端+langgraph
#   pwsh .\start_tupu.ps1 -SkipAuth:$false  # 顺带把 authentik 也起来
#   pwsh .\start_tupu.ps1 -SkipLangGraph    # 不开 langgraph studio
#   pwsh .\start_tupu.ps1 -SkipFrontend     # 只起后端 + langgraph

[CmdletBinding()]
param(
    [switch]$SkipAuth      = $true,
    [switch]$SkipLangGraph = $false,
    [switch]$SkipFrontend  = $false
)

$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"

$ProjectRoot = $PSScriptRoot
$BackendDir  = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$ComposeFile = Join-Path $ProjectRoot "docker-compose.infra.yml"
$LogDir      = Join-Path $ProjectRoot ".runtime-logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# ---------------- 工具 ----------------
function Test-Port {
    param([int]$Port)
    [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}
function Wait-Port {
    param([int]$Port, [string]$What, [int]$TimeoutSec = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $Port) {
            Write-Host "  [OK]   $What :$Port 已就绪" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Milliseconds 800
    }
    Write-Host "  [ERR]  $What :$Port 在 ${TimeoutSec}s 内未起来（看 .runtime-logs/）" -ForegroundColor Red
    return $false
}
function Get-ContainerStatus {
    param([string]$Name)
    $row = docker ps -a --format "{{.Names}}|{{.Status}}" 2>$null | Where-Object { $_ -like "$Name|*" }
    if (-not $row) { return "absent" }
    return ($row -split '\|')[1]
}

# 找一个**装了 uvicorn**的 python 解释器
# 你机器上 python 3.13 在 PATH 里但没装包；3.11 (通过 py 启动器) 才装了 uvicorn / langgraph
function Resolve-Python {
    $cands = @()
    # 优先走 py -3.11
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $exe = (& py -3.11 -c "import sys; print(sys.executable)" 2>$null)
            if ($exe) { $cands += $exe.Trim() }
        } catch {}
    }
    # 再 fallback 到 PATH 里的 python
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $cands += $cmd.Source }

    foreach ($p in $cands) {
        if (-not $p -or -not (Test-Path $p)) { continue }
        # 必须装了 uvicorn 才算合格
        & $p -c "import uvicorn,fastapi" 2>$null
        if ($LASTEXITCODE -eq 0) { return $p }
    }
    return $null
}

# 静默后台启动一个进程：不开 cmd 窗口，stdout/stderr 写入日志文件
function Start-BgProcess {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$LogFile,
        [hashtable]$EnvVars
    )
    if ($EnvVars) {
        foreach ($k in $EnvVars.Keys) {
            Set-Item -Path "Env:$k" -Value $EnvVars[$k] -Force
        }
    }
    $errLog = $LogFile -replace '\.log$', '.err.log'
    $proc = Start-Process -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError  $errLog `
        -PassThru
    return $proc
}

# ============================================================
# 1) Docker 容器
# ============================================================
Write-Host "`n=== 1/4  Docker 容器 (qdrant + neo4j$(if(-not $SkipAuth){' + authentik'})) ===" -ForegroundColor Cyan

if (-not (Test-Path $ComposeFile)) {
    Write-Host "  [ERR]  找不到 $ComposeFile" -ForegroundColor Red
    exit 1
}

$coreServices = @('qdrant', 'neo4j')
$authServices = @('authentik_postgres', 'authentik_redis', 'authentik_server', 'authentik_worker')
$wantedServices = @() + $coreServices
if (-not $SkipAuth) { $wantedServices += $authServices }

$toStart = @()
foreach ($s in $wantedServices) {
    $cName = "tupu_$s"
    $st    = Get-ContainerStatus $cName
    if ($st -like 'Up*') {
        Write-Host "  [SKIP] $cName 已在运行 ($st)" -ForegroundColor DarkGray
    } else {
        $toStart += $s
    }
}

if ($toStart.Count -gt 0) {
    Write-Host "  [..]   docker compose up -d $($toStart -join ' ')" -ForegroundColor Gray
    Push-Location $ProjectRoot
    try {
        & docker compose -f $ComposeFile up -d --no-deps @toStart 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK]   docker compose up -d 完成" -ForegroundColor Green
        } else {
            Write-Host "  [ERR]  docker compose 失败 (exit=$LASTEXITCODE)" -ForegroundColor Red
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  [SKIP] 目标容器全部已运行" -ForegroundColor DarkGray
}

Wait-Port 6333 "qdrant" 60 | Out-Null
Wait-Port 7474 "neo4j"  90 | Out-Null

# ============================================================
# 2) 后端 :8100
# ============================================================
Write-Host "`n=== 2/4  后端 FastAPI :8100 ===" -ForegroundColor Cyan

if (Test-Port 8100) {
    Write-Host "  [SKIP] 后端 :8100 已在监听" -ForegroundColor DarkGray
} else {
    $py = Resolve-Python
    if (-not $py) {
        Write-Host "  [ERR]  没找到 python（试过 python / py -3.11），请装 Python 3.11+" -ForegroundColor Red
        exit 1
    }
    $stamp   = Get-Date -Format "yyyyMMdd-HHmmss"
    $logFile = Join-Path $LogDir "backend-$stamp.log"
    $args    = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8100')
    $proc    = Start-BgProcess -FilePath $py -Arguments $args -WorkingDirectory $BackendDir -LogFile $logFile
    Write-Host "  [OK]   后端已后台启动 PID=$($proc.Id)，日志: $logFile" -ForegroundColor Green
}

if (-not (Wait-Port 8100 "backend" 90)) {
    Write-Host "  [ERR]  后端起不来，前端 / langgraph 可能依赖它，先看日志" -ForegroundColor Red
}

# ============================================================
# 3) 前端 :3000
# ============================================================
if ($SkipFrontend) {
    Write-Host "`n=== 3/4  前端 :3000  [SKIP] (-SkipFrontend) ===" -ForegroundColor Cyan
} else {
    Write-Host "`n=== 3/4  前端 CRA :3000 ===" -ForegroundColor Cyan
    if (Test-Port 3000) {
        Write-Host "  [SKIP] 前端 :3000 已在监听" -ForegroundColor DarkGray
    } else {
        if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
            Write-Host "  [WARN] frontend/node_modules 不存在，请先在 frontend 目录跑 npm install" -ForegroundColor Yellow
        } else {
            $stamp   = Get-Date -Format "yyyyMMdd-HHmmss"
            $logFile = Join-Path $LogDir "frontend-$stamp.log"
            # npm.cmd 是 npm 在 Windows 下的真实可执行文件；BROWSER=none 防止自动开浏览器
            $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue)
            if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
            if (-not $npm) {
                Write-Host "  [ERR]  没找到 npm，请安装 Node.js" -ForegroundColor Red
            } else {
                $proc = Start-BgProcess -FilePath $npm.Source -Arguments @('start') `
                    -WorkingDirectory $FrontendDir -LogFile $logFile `
                    -EnvVars @{ BROWSER = 'none' }
                Write-Host "  [OK]   前端已后台启动 PID=$($proc.Id)，日志: $logFile" -ForegroundColor Green
            }
        }
        Wait-Port 3000 "frontend" 120 | Out-Null
    }
}

# ============================================================
# 4) LangGraph Studio :2024
# ============================================================
if ($SkipLangGraph) {
    Write-Host "`n=== 4/4  LangGraph Studio :2024  [SKIP] (-SkipLangGraph) ===" -ForegroundColor Cyan
} else {
    Write-Host "`n=== 4/4  LangGraph Studio :2024 ===" -ForegroundColor Cyan
    if (Test-Port 2024) {
        Write-Host "  [SKIP] langgraph :2024 已在监听" -ForegroundColor DarkGray
    } else {
        $stamp   = Get-Date -Format "yyyyMMdd-HHmmss"
        $logFile = Join-Path $LogDir "langgraph-$stamp.log"
        # langgraph 是 Python 入口点脚本，用 py -3.11 -m langgraph_cli 最稳
        $py = Resolve-Python
        if (-not $py) {
            Write-Host "  [ERR]  没找到 python，无法启动 langgraph" -ForegroundColor Red
        } else {
            $args = @('-m', 'langgraph_cli', 'dev', '--host', '127.0.0.1', '--port', '2024')
            $proc = Start-BgProcess -FilePath $py -Arguments $args `
                -WorkingDirectory $BackendDir -LogFile $logFile `
                -EnvVars @{ PYTHONIOENCODING = 'utf-8' }
            Write-Host "  [OK]   langgraph 已后台启动 PID=$($proc.Id)，日志: $logFile" -ForegroundColor Green
        }
        Wait-Port 2024 "langgraph" 60 | Out-Null
    }
}

# ============================================================
# 总结
# ============================================================
Write-Host "`n=== 入口 ===" -ForegroundColor Cyan
Write-Host "  前端          : http://127.0.0.1:3000" -ForegroundColor White
Write-Host "  后端 docs     : http://127.0.0.1:8100/docs" -ForegroundColor White
Write-Host "  LangGraph UI  : https://smith.langchain.com/studio?baseUrl=http://127.0.0.1:2024" -ForegroundColor White
Write-Host "  Qdrant        : http://127.0.0.1:6333/dashboard" -ForegroundColor White
Write-Host "  Neo4j Browser : http://127.0.0.1:7474" -ForegroundColor White
if (-not $SkipAuth) {
    Write-Host "  Authentik     : http://127.0.0.1:9100" -ForegroundColor White
}
Write-Host "`n日志目录: $LogDir" -ForegroundColor DarkGray
Write-Host "停止全部: pwsh .\stop_tupu.ps1" -ForegroundColor DarkGray
Write-Host "`n>>> tupu 已启动（全部后台运行）" -ForegroundColor Green
