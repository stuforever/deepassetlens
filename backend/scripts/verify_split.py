#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_split.py - R2② 巨型文件拆分验收（协调者终检，cwd=backend）

验证：
  1. 巨型原文件行数 < 800（duckdb_engine 豁免，不在清单）
  2. 关键模块可 import（app.api.concept / app.api.v2_skills / app.api.data_intelligence /
     app.services.query_attribute_service）
  3. 关键符号保名（metadata_service 依赖的 _build_entity_brief/_build_relation_brief/
     _extract_attribute_detail_rows/build_attribute_metadata_from_system）

注：smart_skills.py / smart_skill_pipeline.py（原五巨人之一，1673 行）已于 R2②后
作为死代码整链删除——v1 API 从未挂载到 main.py（活 OpenAPI 216 路径零 smart）、
无 import 方/前端/测试引用、且 `from .smart_apps import` 为既有断链（app.api.smart_apps
全仓不存在）。删除即同时化解「>800」与断链，无需拆分。

用法: cd backend; python scripts/verify_split.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

GIANTS = {
    # R2② 五巨型文件：4 个已机械拆分至 <800；smart_skill_pipeline 已整链删除（见模块 docstring）
    "app/api/concept.py": 800,
    "app/api/data_intelligence.py": 800,
    "app/services/query_attribute_service.py": 800,
    "app/api/v2_skills.py": 800,
}

IMPORTS = [
    "app.api.concept",
    "app.api.v2_skills",
    "app.api.data_intelligence",
    "app.services.query_attribute_service",
    "app.services.metadata_service",
    # smart_skills/smart_skill_pipeline 已删除（死代码整链，见模块 docstring）
]

SYMBOLS = {
    "app.services.query_attribute_service": [
        "_build_entity_brief", "_build_relation_brief",
        "_extract_attribute_detail_rows", "build_attribute_metadata_from_system",
    ],
}


def main() -> int:
    ok = True
    print("== 1. 巨型文件行数 ==")
    for rel, cap in GIANTS.items():
        p = BACKEND / rel
        n = len(p.read_text(encoding="utf-8").splitlines()) if p.exists() else -1
        good = 0 < n < cap
        ok = ok and good
        print(f"  [{'PASS' if good else 'FAIL'}] {rel}: {n} 行 (<{cap})")

    print("== 2. 模块 import ==")
    import importlib
    for mod in IMPORTS:
        try:
            importlib.import_module(mod)
            print(f"  [PASS] import {mod}")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  [FAIL] import {mod}: {type(e).__name__}: {e}")

    print("== 3. 关键符号保名 ==")
    for mod, names in SYMBOLS.items():
        try:
            m = importlib.import_module(mod)
            for name in names:
                if hasattr(m, name):
                    print(f"  [PASS] {mod}.{name}")
                else:
                    ok = False
                    print(f"  [FAIL] {mod}.{name} 缺失")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  [FAIL] {mod} import 失败: {e}")

    print(f"\n== 结果: {'ALL PASS' if ok else 'FAILED'} ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
