# LangGraph Studio 启动脚本
#
# 启动后会在本地起一个 LangGraph dev server（默认 :2024），
# 可在浏览器访问 https://smith.langchain.com/studio?baseUrl=http://127.0.0.1:2024
# 用 LangGraph Studio Web UI 可视化调试 query_attribute 图。
#
# 用法：
#   pwsh ./scripts/run_langgraph_studio.ps1
# 停止：Ctrl+C

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

# 可选：把当前 8000 后端的环境变量复用过来（如 DATABASE_URL）
if (Test-Path .env) {
    Write-Host "Using .env in current directory" -ForegroundColor Cyan
}

# 启动 langgraph dev server（开发模式，热重载，挂载本地代码）
# --host 0.0.0.0 允许从其他机器访问；本地用 127.0.0.1 即可
# --port 2024 是默认端口，避开 tupu 后端 8000
Write-Host "Starting LangGraph dev server on http://127.0.0.1:2024 ..." -ForegroundColor Green
Write-Host "Studio URL: https://smith.langchain.com/studio?baseUrl=http://127.0.0.1:2024" -ForegroundColor Yellow

langgraph dev --host 127.0.0.1 --port 2024
