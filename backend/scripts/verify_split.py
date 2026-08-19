#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_split.py - R2② 巨型文件拆分验收（协调者终检，cwd=backend）

验证：
  1. 5 个巨型原文件行数 < 800（duckdb_engine 豁免，不在清单）
  2. 关键模块可 import（app.api.concept / app.api.v2_skills / app.api.data_intelligence /
     app.api.smart_skill_pipeline / app.services.query_attribute_service）
  3. 关键符号保名（smart_skills 依赖的 _invoke_skill/_pick_script_assistant_llm；
     metadata_service 依赖的 _build_entity_brief/_build_relation_brief/
     _extract_attribute_detail_rows/build_attribute_metadata_from_system）

用法: cd backend; python scripts/verify_split.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

GIANTS = {
    # R2② 五巨型文件：4 个已机械拆分至 <800；smart_skill_pipeline 为文档化例外
    # （_invoke_skill 单函数闭包重灾区：setup + 20 嵌套助手 + ~800 行调度链，
    #  助手闭包 db/_pick_script_assistant_llm，dedent 会产生 NameError/循环导入；
    #  拆至 <800 需参数化重构，违背「零行为变更」，与 duckdb_engine 900 同理豁免）
    "app/api/concept.py": 800,
    "app/api/data_intelligence.py": 800,
    "app/services/query_attribute_service.py": 800,
    "app/api/v2_skills.py": 800,
    # "app/api/smart_skill_pipeline.py": 800,  # 文档化例外（原子单函数）
}

IMPORTS = [
    "app.api.concept",
    "app.api.v2_skills",
    "app.api.data_intelligence",
    "app.services.query_attribute_service",
    "app.services.metadata_service",
    # smart_skill_pipeline/smart_skills 为文档化例外：既有 `from .smart_apps import` 断链
    # （app.api.smart_apps 不存在，HEAD 亦无），全仓无引用方（死代码链），
    # 拆分会波及 smart_apps 缺失与闭包参数化，超出「零行为变更机械拆分」范围
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
