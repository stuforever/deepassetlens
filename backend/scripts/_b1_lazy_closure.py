# -*- coding: utf-8 -*-
"""⑤R B1：vendor 懒导入闭包补全——grep 全树 deeptutor.* 引用（含函数内懒导入），拷齐缺件。"""
import re
import shutil
from pathlib import Path

DT = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\deeptutor")
VD = Path(__file__).resolve().parents[1] / "app" / "vendor" / "deeptutor"

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

pat_from = re.compile(r"^\s*from\s+(deeptutor[\w.]*)\s+import\s+(.+)$", re.M)
pat_mod = re.compile(r"^\s*import\s+(deeptutor[\w.]*)", re.M)
pat_multi = re.compile(r"from (deeptutor[\w.]*) import \(([^)]*)\)", re.S)


def _clean(n: str) -> str:
    return n.strip().split(" as ")[0].strip().rstrip(",")


def extract_names(txt: str):
    out = set()
    for m in pat_multi.finditer(txt):
        base = m.group(1)
        for inner in m.group(2).split(","):
            inner = _clean(inner)
            if inner:
                out.add(base + "." + inner)
    for m in pat_from.finditer(txt):
        base, rest = m.group(1), m.group(2)
        if rest.strip().startswith("("):
            continue  # 多行块已由 pat_multi 覆盖
        for inner in rest.split(","):
            inner = _clean(inner)
            if not inner:
                continue
            out.add(base)                       # 包本身
            out.add(base + "." + inner)         # from 包 import 子模块（可为模块或符号）
    for m in pat_mod.finditer(txt):
        out.add(m.group(1))
    return out


added, rounds = 0, 0
while rounds < 12:
    rounds += 1
    need = set()
    for f in VD.rglob("*.py"):
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        need |= extract_names(txt)
    new = 0
    for name in sorted(need):
        rel = name.replace("deeptutor.", "").replace(".", "/")
        for cand in (rel + ".py", rel + "/__init__.py"):
            if copy_mod(cand):
                new += 1
                print("  补", cand)
    added += new
    if new == 0:
        break

print(f"懒导入补全: {added} 文件 / {rounds} 轮")
# 校验：vendor 树不再引用不存在的 deeptutor 子模块
missing = set()
for f in VD.rglob("*.py"):
    txt = f.read_text(encoding="utf-8", errors="replace")
    for m in pat_mod.finditer(txt):
        name = m.group(1)
        rel = name.replace("deeptutor.", "").replace(".", "/")
        if not (DT / (rel + ".py")).exists() and not (DT / rel / "__init__.py").exists():
            missing.add(name)
print("原仓也不存在的引用(动态导入,忽略):", sorted(missing)[:6] if missing else "无")
