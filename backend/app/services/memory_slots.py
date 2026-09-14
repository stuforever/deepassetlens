# -*- coding: utf-8 -*-
"""记忆插槽②（2026-09-12 spec §四）：槽类型注册表+卡 memory 字段演进+五规则校验。

四类接线卡（deepagents 原语×DeepTutor 纪律，代码零搬运——仅纪律与文案级继承）：
  L1_TRACE=洋葱新中间件 / L2_SUMMARY+L3_PROFILE=consolidator 后台线程 /
  RAW_MD=write_file+edit_file+槽级权限。
"""
import os
import re
from typing import Any, Dict, List, Optional

# 类型注册表：params=实例参数形状；writer=写入者（类型定死，spec §四表）
SLOT_TYPE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "L1_TRACE":   {"params": ("surface",), "writer": "middleware"},
    "L2_SUMMARY": {"params": ("surface", "order"), "writer": "consolidator"},
    "L3_PROFILE": {"params": ("slot_key", "order"), "writer": "consolidator"},
    "RAW_MD":     {"params": ("path", "writer", "order"), "writer": "card"},
}

_SURFACE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def consolidator_enabled() -> bool:
    """env 开关（默认开，spec §四规则2）。"""
    return os.getenv("TUPU_MEMORY_CONSOLIDATOR", "1") == "1"


def normalize_memory_field(memory: Any) -> Dict[str, List[Any]]:
    """形状兼容读（spec §四）：①期路径列表 → {slots: [], legacy_paths}（升级窗口两形状并存，
    读时归一——wenshu 卡 DB 里的列表形状零迁移）。"""
    if memory is None:
        return {"slots": [], "legacy_paths": []}
    if isinstance(memory, list):
        return {"slots": [], "legacy_paths": list(memory)}
    if isinstance(memory, dict):
        return {"slots": list(memory.get("slots") or []),
                "legacy_paths": list(memory.get("legacy_paths") or [])}
    raise ValueError("memory 字段形状非法（①期列表 或 {slots, legacy_paths} 对象）")


def validate_slots(slots: List[Dict[str, Any]], *, consolidator_on: Optional[bool] = None) -> Dict[str, List[str]]:
    """五规则（spec §四 CRUD 组合校验白名单，D3 验收依据）。返回 {injected: 注入路径列表}。"""
    if consolidator_on is None:
        consolidator_on = consolidator_enabled()
    names: set = set()
    keys: set = set()
    has_l2l3 = False
    injected: List[tuple] = []
    for s in slots or []:
        t = s.get("type")
        if t not in SLOT_TYPE_REGISTRY:                                  # 规则1
            raise ValueError(f"槽类型不在注册表: {t}")
        name = (s.get("slot") or "").strip()
        if not name or name in names:                                    # 规则1
            raise ValueError(f"槽名缺失或与同卡重复: {name!r}")
        names.add(name)
        if t in ("L2_SUMMARY", "L3_PROFILE"):
            has_l2l3 = True
        if t == "L3_PROFILE" and (not (s.get("slot_key") or "").strip()
                                  or s.get("slot_key") in keys):         # 规则1
            raise ValueError(f"slot_key 缺失或重复: {s.get('slot_key')!r}")
        if t == "L3_PROFILE":
            keys.add(s["slot_key"])
        if t in ("L1_TRACE", "L2_SUMMARY") and not _SURFACE_RE.match(s.get("surface") or ""):
            raise ValueError(f"surface 格式非法（小写字母数字-_）: {s.get('surface')!r}")  # 规则5
        if t == "RAW_MD":
            path = s.get("path") or ""
            if s.get("writer") == "agent_edit":                          # 规则3
                if not path.startswith("/memory/") or len(path.strip("/").split("/")) < 2:
                    raise ValueError(f"RAW_MD path 必须落在 {{expert}}/{{user}} 记忆树内: {path}")
                if path.rstrip("/").endswith("AGENTS.md"):
                    raise ValueError("RAW_MD 槽 path 不得为 AGENTS.md（专家手册受控）")
        if s.get("read") == "注入":                                       # 规则4
            injected.append((int(s.get("order") or 99), slot_virtual_path(s)))
    if has_l2l3 and not consolidator_on:                                 # 规则2
        raise ValueError("L2/L3 槽需要 consolidator 服务启用（TUPU_MEMORY_CONSOLIDATOR=1）")
    return {"injected": [p for _, p in sorted(injected)]}


def slot_virtual_path(s: Dict[str, Any]) -> str:
    """槽→虚拟路径唯一映射：RAW_MD=声明 path；L2_SUMMARY=/memory/L2/{surface}.md；
    L3_PROFILE=/memory/L3/{slot_key}.md（=consolidator 落盘约定，批 5 步骤 5.3 同源）。
    L1_TRACE 无注入路径——声明 read=注入 的 L1 在此 fail-closed 抛错（原料不注入，
    spec §四默认），CRUD 源头转 422。"""
    t = s.get("type")
    if t == "RAW_MD":
        return s["path"]
    if t == "L2_SUMMARY":
        return f"/memory/L2/{s.get('surface') or 'chat'}.md"
    if t == "L3_PROFILE":
        return f"/memory/L3/{s.get('slot_key') or 'profile'}.md"
    raise ValueError(f"槽类型无注入路径（L1 原料不注入）: {t}")


def injection_list(memory_norm: Dict[str, List[Any]]) -> List[str]:
    """memory 注入参数（spec §四规则4）：legacy 手册优先 + 注入槽按 order——
    L2/L3 用规范路径（consolidator 落盘物）、RAW_MD 用声明 path。批 3 f 因子哈希
    对象同走本函数（固化后 f 变→下一装配注入新摘要，spec §五）。"""
    return list(memory_norm.get("legacy_paths") or []) + \
        [p for _, p in sorted((int(s.get("order") or 99), slot_virtual_path(s))
                              for s in memory_norm.get("slots") or []
                              if s.get("read") == "注入")]
