# -*- coding: utf-8 -*-
"""⑤R R2 A4：零重设计审计——vendor 子树 sha256 全对原仓（差异逐一映射登记接线点）。
数据模型字段级 diff=模型件哈希一致蕴含字段级一致；端点契约 diff=A1（108 PASS+5 豁免）。"""
import hashlib
import io
import json
from pathlib import Path

SRC = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\deeptutor")
DST = Path(r"D:\gitcangku\deepassetlens\backend\app\vendor\deeptutor")
BASE = Path(__file__).resolve().parent / "dt_baseline"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    diffs = []
    new_files = []
    for f in sorted(SRC.rglob("*.py")):
        rel = f.relative_to(SRC)
        if "__pycache__" in str(rel):
            continue
        t = DST / rel
        if not t.exists():
            new_files.append(str(rel))
            continue
        if sha256(f) != sha256(t):
            diffs.append(str(rel))
    out = {"diff_files": diffs, "missing_in_vendor": new_files}
    for d in diffs:
        print("  [DIFF]", d)
    for n in new_files:
        print("  [MISSING]", n)
    print(f"vendor py 总差异: {len(diffs)} / 缺失: {len(new_files)}")
    json.dump(out, io.open(BASE / "r2_a4_hashdiff.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
