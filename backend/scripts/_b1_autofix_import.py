# -*- coding: utf-8 -*-
"""⑤R B1：vendor 导入自动修复环——子进程试导 knowledge 路由，缺件即拷，循环至闭环。"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DT = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\deeptutor")
VENDOR = Path(__file__).resolve().parents[1] / "app" / "vendor"
VD = VENDOR / "deeptutor"
PY = sys.executable

VERIFY = (
    "import sys; sys.path.insert(0, r'{v}'); import importlib\n"
    "try:\n"
    "    m = importlib.import_module('deeptutor.api.routers.knowledge')\n"
    "    print('ROUTES', len(m.router.routes))\n"
    "except Exception as e:\n"
    "    print('FAIL', type(e).__name__, str(e))\n"
).format(v=str(VENDOR))

_WS = VENDOR.parents[1] / "data" / "experts" / "tutor" / "workspace"
BASEENV = dict(os.environ, PYTHONUTF8="1",
               DEEPTUTOR_HOME=str(_WS),
               DT_TUTOR_WORKSPACE_ROOT=str(_WS))


def copy_mod(rel: str) -> bool:
    src = DT / rel
    if not src.exists():
        return False
    dst = VD / rel
    if dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def copy_module_and_pkg(mod: str) -> int:
    """拷模块本体+其包 __init__ 链。"""
    n = 0
    rel = mod.replace("deeptutor.", "").replace(".", "/")
    if copy_mod(rel + ".py"):
        n += 1
    if copy_mod(rel + "/__init__.py"):
        n += 1
    # 包链：a/b/c 缺时补 a/__init__ b/__init__
    parts = rel.split("/")
    for i in range(1, len(parts)):
        if copy_mod("/".join(parts[:i]) + "/__init__.py"):
            n += 1
    return n


for i in range(60):
    r = subprocess.run([PY, "-c", VERIFY], capture_output=True, text=True, timeout=120,
                       cwd=str(Path(__file__).resolve().parents[1]), env=BASEENV)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"ROUTES (\d+)", out)
    if m:
        print(f"闭环 OK knowledge 路由 {m.group(1)} routes（{i} 轮修复）")
        break
    mm = re.search(r"No module named '(deeptutor[\w.]*)'", out)
    if not mm:
        print("非缺件失败:", out.strip()[:300])
        break
    mod = mm.group(1)
    n = copy_module_and_pkg(mod)
    if n == 0:
        print("原仓也没有:", mod, "——外部 pip 依赖候选")
        break
    print(f"  轮{i}: 补 {mod} ({n} 文件)")
else:
    print("60 轮未闭环——停")
