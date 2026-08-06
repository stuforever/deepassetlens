# tupu 工程统一停止脚本（纯静默，不弹窗）
#
# 覆盖：
#   进程：前端 :23000 / 后端 :28000 / LangGraph Studio :2024
#   容器：tupu_qdrant / tupu_neo4j (核心)
#         tupu_authentik_pg / tupu_authentik_redis / tupu_authentik_server / tupu_authentik_worker (默认也停)
#
# 用法：
#   pwsh .\stop_tupu.ps1            # 停所有
#   pwsh .\stop_tupu.ps1 -SkipAuth  # 不动 authentik 4 个容器
#
# 不会触碰：ragflow 5 个容器 / 本机 MySQL / 本机 Redis

[CmdletBinding()]
param(
    [switch]$SkipAuth = $false
)

$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"

function Stop-PortOwners {
    param([int[]]$Ports, [string]$What)
    foreach ($port in $Ports) {
        # 重试最多 3 轮：langgraph / uvicorn 会 fork 子进程，父进程死后端口还可能被子进程占住
        for ($round = 1; $round -le 3; $round++) {
            $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
            if (-not $conns) {
                if ($round -eq 1) {
                    Write-Host "  [SKIP] $What :$port 未监听" -ForegroundColor DarkGray
                }
                break
            }
            $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($targetPid in $procIds) {
                try {
                    $proc = Get-Process -Id $targetPid -ErrorAction Stop
                    # /T 杀掉整个进程树（含子进程）；/F 强制
                    & taskkill.exe /PID $targetPid /T /F 2>&1 | Out-Null
                    Write-Host "  [OK]   $What :$port -> 已杀 PID=$targetPid ($($proc.ProcessName)) 含子进程" -ForegroundColor Green
                } catch {
                    Write-Host "  [SKIP] $What :$port PID=$targetPid 已退出" -ForegroundColor DarkGray
                }
            }
            Start-Sleep -Milliseconds 500
        }
    }
}

function Stop-LeftoversByCmdline {
    param([string]$Pattern, [string]$Label)
    $left = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and ($_.CommandLine -match $Pattern) }
    foreach ($p in $left) {
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            Write-Host "  [OK]   $Label 残留 PID=$($p.ProcessId) -> 已杀" -ForegroundColor Green
        } catch {}
    }
}

function Stop-ContainerIfRunning {
    param([string]$Name)
    $row = docker ps -a --format "{{.Names}}|{{.Status}}" 2>$null | Where-Object { $_ -like "$Name|*" }
    if (-not $row) {
        Write-Host "  [SKIP] 容器 $Name 不存在" -ForegroundColor DarkGray
        return
    }
    $status = ($row -split '\|')[1]
    if ($status -like 'Up*') {
        docker stop $Name 2>&1 | Out-Null
        Write-Host "  [OK]   容器 $Name 已停止" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] 容器 $Name 已是 $status" -ForegroundColor DarkGray
    }
}

# 1) LangGraph Studio
Write-Host "`n=== 1/4  停 LangGraph Studio :2024 ===" -ForegroundColor Cyan
Stop-PortOwners -Ports @(2024) -What "langgraph"
Stop-LeftoversByCmdline -Pattern 'langgraph(\.exe)?\s+dev|langgraph_api' -Label "langgraph"

# 2) 前端
Write-Host "`n=== 2/4  停前端 :23000 ===" -ForegroundColor Cyan
Stop-PortOwners -Ports @(23000) -What "frontend"
Stop-LeftoversByCmdline -Pattern 'react-scripts\s+start' -Label "react-scripts"

# 3) 后端
Write-Host "`n=== 3/4  停后端 :28000 ===" -ForegroundColor Cyan
Stop-PortOwners -Ports @(28000) -What "backend"
Stop-LeftoversByCmdline -Pattern 'uvicorn\s+app\.main:app' -Label "uvicorn"

# 4) Docker 容器
Write-Host "`n=== 4/4  停 docker 容器 (tupu_*) ===" -ForegroundColor Cyan
'tupu_qdrant', 'tupu_neo4j' | ForEach-Object { Stop-ContainerIfRunning $_ }
if ($SkipAuth) {
    Write-Host "  [SKIP] -SkipAuth 跳过 authentik 4 个容器" -ForegroundColor DarkGray
} else {
    'tupu_authentik_server', 'tupu_authentik_worker',
    'tupu_authentik_pg',     'tupu_authentik_redis' |
        ForEach-Object { Stop-ContainerIfRunning $_ }
}

# 核验
Write-Host "`n=== 核验 ===" -ForegroundColor Cyan
foreach ($p in 23000, 6333, 7474, 7687, 28000, 2024) {
    $busy = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if (-not $busy) {
        Write-Host ("  [OK]   :{0} 空闲" -f $p) -ForegroundColor Green
        continue
    }
    # 检查 OwningProcess 是不是真活着；Windows 偶尔会留 LISTEN 僵尸 socket
    $alivePids = @()
    foreach ($targetPid in ($busy.OwningProcess | Select-Object -Unique)) {
        if (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) {
            $alivePids += $targetPid
        }
    }
    if ($alivePids.Count -eq 0) {
        Write-Host ("  [OK]   :{0} 进程已死（仅内核残留 LISTEN 套接字，不影响重启）" -f $p) -ForegroundColor Green
    } else {
        Write-Host ("  [WARN] :{0} 仍在监听 PID={1}" -f $p, ($alivePids -join ',')) -ForegroundColor Yellow
    }
}
$running = docker ps --format "{{.Names}}" 2>$null | Where-Object { $_ -like 'tupu_*' }
if ($running) {
    Write-Host "  [WARN] 仍在运行：$($running -join ', ')" -ForegroundColor Yellow
} else {
    Write-Host "  [OK]   无 tupu_* 容器在运行" -ForegroundColor Green
}

Write-Host "`n>>> tupu 已停止" -ForegroundColor Green
