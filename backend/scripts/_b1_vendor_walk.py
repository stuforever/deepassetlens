# -*- coding: utf-8 -*-
"""⑤R B1 3.3：vendor 闭包机械拷贝+import 走查。

种子=learning 全包+mother_question 路由+runtime/home+path_service/file_io；
随后 import 试错：ModuleNotFoundError(deeptutor.*) → 拷入对应文件 → 重试，
直至闭环或撞外部 pip 依赖（登记）。vendor 原结构保原导入（零改码）。"""
import importlib
import shutil
import sys
from pathlib import Path

DT = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\deeptutor")
VENDOR = Path(__file__).resolve().parents[1] / "app" / "vendor"
VD = VENDOR / "deeptutor"

def copy_mod(rel: str) -> bool:
    """拷单个 py 模块（含沿途 __init__.py）。返回是否新拷。"""
    src = DT / rel
    if not src.exists():
        return False
    dst = VD / rel
    if dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True

def seed():
    n = 0
    # learning 整包（tests 随包=对拍资产；pycache 不拷）
    for f in (DT / "learning").rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts:
            rel = f.relative_to(DT)
            dst = VD / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            n += 1
    for rel in ["__init__.py", "api/__init__.py", "api/routers/__init__.py",
                "api/routers/mother_question.py", "runtime/__init__.py", "runtime/home.py",
                "services/path_service.py", "services/file_io.py",
                "multi_user/__init__.py", "multi_user/context.py"]:
        if copy_mod(rel):
            n += 1
    return n

if not VENDOR.exists():
    VENDOR.mkdir(parents=True)
    (VENDOR / "__init__.py").write_text(
        '"""⑤R vendor 路径钩子：deeptutor 子树原结构可导入 + DEEPTUTOR_HOME 单点（接线点2）。"""\n'
        "import os\nimport sys\nfrom pathlib import Path\n\n"
        "_HERE = str(Path(__file__).resolve().parent)\n"
        "if _HERE not in sys.path:\n"
        "    sys.path.insert(0, _HERE)\n"
        '_WS = os.getenv("DT_TUTOR_WORKSPACE_ROOT", "")\n'
        'if _WS and not os.getenv("DEEPTUTOR_HOME"):\n'
        '    os.environ["DEEPTUTOR_HOME"] = str(Path(_WS).resolve())\n',
        encoding="utf-8")

print("种子拷贝:", seed(), "文件")

sys.path.insert(0, str(VENDOR))
TARGETS = ["deeptutor.learning.curriculum", "deeptutor.api.routers.mother_question"]
missing = {}
for round_i in range(30):
    errs = []
    for t in TARGETS:
        try:
            importlib.import_module(t)
        except ModuleNotFoundError as e:
            errs.append((t, e.name))
        except Exception as e:
            errs.append((t, f"{type(e).__name__}: {e}"))
    if not errs:
        print("闭包闭环 ✓ 全部可导入")
        break
    progressed = False
    for t, name in errs:
        s = str(name)
        if isinstance(name, str) and name.startswith("deeptutor."):
            rel = name.replace("deeptutor.", "").replace(".", "/")
            a = copy_mod(rel + ".py")
            b = copy_mod(rel + "/__init__.py")
            if a or b:
                progressed = True
                print(f"  补 {name}")
                continue
        # cannot import name 'X' from partially initialized 'deeptutor.y.z' → 补 y/z/X.py
        import re as _re
        m = _re.search(r"cannot import name '(\w+)' from (?:partially initialized )?module '(deeptutor\.[\w.]+)'", s)
        if m:
            rel = m.group(2).replace("deeptutor.", "").replace(".", "/")
            if copy_mod(rel + "/" + m.group(1) + ".py") or copy_mod(rel + "/" + m.group(1) + "/__init__.py") \
               or copy_mod(rel + ".py"):
                progressed = True
                print(f"  补(名字导入) {m.group(2)}.{m.group(1)}")
                continue
        missing.setdefault(t, []).append(s[:120])
    if not progressed:
        for t, names in missing.items():
            print(f"外部依赖/待登记 {t}: {names[:4]}")
        break
