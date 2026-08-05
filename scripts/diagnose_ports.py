"""
工程端口全景扫描器
扫描：
  1. 实际运行的 LISTENING 端口（带 PID + 进程 + 命令）
  2. 工程代码中固定配置的端口（uvicorn / proxy / config）
  3. 给出"期望 vs 实际"对比
"""
import subprocess
import json
import re
from pathlib import Path

ROOT = Path(r"D:\gitcangku\DB-GPT\tupu")


def get_listening_ports():
    out = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True, text=True, encoding="gbk", errors="ignore",
    ).stdout
    ports = []
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        m = re.match(r"\s*TCP\s+[\d.:*]+:(\d+)\s+[\d.:*]+:0\s+LISTENING\s+(\d+)", line)
        if not m:
            continue
        ports.append({"port": int(m.group(1)), "pid": int(m.group(2))})
    return ports


def get_all_processes():
    ps = """
Get-Process | Select-Object Id, ProcessName, @{Name='Cmd';Expression={
    (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
}}, @{Name='MemMB';Expression={[math]::Round($_.WorkingSet64/1MB,1)}} |
    Where-Object { $_.Cmd -ne $null -and $_.Cmd -ne '' } |
    Select-Object Id, ProcessName, Cmd, MemMB |
    ConvertTo-Json -Depth 2 -Compress
"""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    ).stdout.strip()
    try:
        data = json.loads(out) if out else []
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception:
        return []


def match_tupu(cmdline, name):
    text = ((cmdline or "") + " " + (name or "")).lower()
    keywords = ["tupu", "data-intelligence", "secretary_state",
                "uvicorn", "react-scripts", "vite",
                r"d:\gitcangku\db-gpt\tupu", "authentik"]
    return any(kw.lower() in text for kw in keywords)


# ----- 实际运行端口 -----
ports = get_listening_ports()
all_procs = get_all_processes()
proc_by_pid = {p["Id"]: p for p in all_procs}

seen = set()
results = []
for p in ports:
    pid = p["pid"]
    if pid in seen:
        for r in results:
            if r["pid"] == pid:
                r["ports"].append(p["port"])
                break
        continue
    seen.add(pid)

    info = proc_by_pid.get(pid, {})
    results.append({
        "pid": pid,
        "ports": [p["port"]],
        "name": info.get("ProcessName") or "?",
        "cmdline": (info.get("Cmd") or "")[:400],
        "memory_mb": info.get("MemMB"),
        "is_tupu": match_tupu(info.get("Cmd"), info.get("ProcessName")),
    })


tupu_procs = [r for r in results if r["is_tupu"]]

# ----- 工程代码中固定端口扫描 -----
def scan_code_ports():
    """扫描工程代码里的端口字符串 + 文件位置"""
    patterns = [
        # (regex, label)
        (r'["\'](?:port|PORT)\s*[=:]\s*["\']?(\d{2,5})["\']?', "port="),
        (r'localhost:(\d{2,5})', "localhost:"),
        (r'127\.0\.0\.1:(\d{2,5})', "127.0.0.1:"),
        (r'0\.0\.0\.0:(\d{2,5})', "0.0.0.0:"),
    ]
    skip_dirs = {"node_modules", ".git", "__pycache__", "venv", ".venv",
                 "data/runtime", ".langgraph_api", "build", "dist",
                 "frontend/build", "_artifacts_e2e", "tmp_e2e_screens"}
    skip_files = {"diagnose_ports.py", "package-lock.json"}

    found = []
    for fpath in ROOT.rglob("*"):
        rel = fpath.relative_to(ROOT)
        if any(part in skip_dirs for part in rel.parts):
            continue
        if not fpath.is_file():
            continue
        if fpath.name in skip_files:
            continue
        if fpath.suffix not in (".py", ".js", ".jsx", ".ts", ".tsx",
                                ".json", ".yaml", ".yml", ".toml", ".env",
                                ".html", ".md", ".ps1", ".bat", ".sh"):
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat, label in patterns:
            for m in re.finditer(pat, text):
                port = int(m.group(1))
                # 过滤常见误报（年份、版本号等）
                if port < 100 or port > 65535:
                    continue
                if port in (2000, 3000, 3001, 4000, 5000, 8000, 8080,
                            8100, 8101, 9000, 9001, 9100, 9200, 9300,
                            6380, 6379, 7474, 7687, 33060, 3306):
                    pass  # 关注端口
                line_no = text[:m.start()].count("\n") + 1
                found.append({
                    "port": port,
                    "label": label,
                    "file": str(rel),
                    "line": line_no,
                    "context": text.splitlines()[line_no - 1].strip()[:100],
                })
    return found


code_ports = scan_code_ports()

# ----- 输出 -----
print("=" * 120)
print("PART 1: TUPU 工程 - 实际运行中的进程")
print("=" * 120)
print(f"{'PID':<7}{'Port(s)':<22}{'Memory':<10}{'Name':<22}用途 / 命令")
print("-" * 120)
for r in sorted(tupu_procs, key=lambda x: x["ports"]):
    ports_str = ",".join(str(p) for p in r["ports"])
    mem = f"{r['memory_mb']}M" if r.get("memory_mb") else ""
    cmd = r["cmdline"].replace("\n", " ")[:200]
    print(f"{r['pid']:<7}{ports_str:<22}{mem:<10}{r['name'][:20]:<22}{cmd}")

print("\n" + "=" * 120)
print("PART 2: 端口用途对照表（当前运行中）")
print("=" * 120)
port_role_map = {
    3000: "前端 React dev server (CRA / react-scripts) - 用户浏览器入口 http://localhost:3000",
    8100: "后端 FastAPI (uvicorn 8100) - 我刚启动的 __start_8100.py (匹配前端 proxy)",
    8000: "后端 FastAPI (uvicorn 8000) - 工程默认启动脚本 __start_8000.py (注意：与前端 proxy 不一致)",
    9100: "Authentik OIDC SSO - 用于 OIDC 登录",
    5040: "IDE 服务端口",
}
for port in sorted(set(p for r in tupu_procs for p in r["ports"])):
    desc = port_role_map.get(port, "（未识别用途）")
    print(f"  端口 {port:<6} ← {desc}")

print("\n" + "=" * 120)
print("PART 3: 工程代码中固定配置的端口（uvicorn / proxy / config）")
print("=" * 120)
# 按端口聚合
from collections import defaultdict
by_port = defaultdict(list)
for c in code_ports:
    # 排除 build/node_modules 的（虽然已 skip，但保险）
    if "node_modules" in c["file"] or "/build/" in c["file"]:
        continue
    by_port[c["port"]].append(c)

for port in sorted(by_port.keys()):
    refs = by_port[port]
    print(f"\n  端口 {port}  ({len(refs)} 处引用)")
    seen_files = set()
    for ref in refs[:6]:
        key = (ref["file"], ref["line"])
        if key in seen_files:
            continue
        seen_files.add(key)
        print(f"    {ref['file']}:{ref['line']}  {ref['context']}")
    if len(refs) > 6:
        print(f"    ... 还有 {len(refs) - 6} 处")

print("\n" + "=" * 120)
print("PART 4: 系统端口全景（参考）")
print("=" * 120)
infra_map = {
    3306: "MySQL", 33060: "MySQL X Protocol",
    6379: "Redis", 6380: "Redis (备用)",
    7474: "Neo4j HTTP", 7687: "Neo4j Bolt",
    9000: "MinIO API", 9001: "MinIO Console",
    9222: "Chrome DevTools Protocol",
    80: "IIS / HTTP", 443: "IIS / HTTPS",
}
print(f"{'Port':<7}用途")
print("-" * 60)
seen_infra = set()
for p in sorted(set(x["port"] for x in ports)):
    if p < 1000 and p not in (80, 443, 3306, 33060):
        continue
    role = infra_map.get(p, "")
    if role:
        print(f"  {p:<5}{role}")
        seen_infra.add(p)
    elif p >= 1000 and p < 10000 and p not in (3000, 8100, 8000, 5040):
        proc = next((r for r in results if p in r["ports"]), None)
        if proc:
            print(f"  {p:<5}进程: {proc['name']} (PID {proc['pid']})")
