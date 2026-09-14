# -*- coding: utf-8 -*-
"""记忆插槽②（2026-09-12 spec）单测：批1 槽模型 / 批2 树与搬迁 / 批3 L1+f因子 / 批4 越界 / 批5 consolidator。

变异锚点：每测 docstring 标明何种生产改动会让它红。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 批 1：槽类型注册表+形状兼容+五规则（D3 素材）
# ---------------------------------------------------------------------------

def test_slot_type_registry_four_kinds():
    """四张接线卡（spec §四注册表）。变异锚点：删任一类型 → 红。"""
    from app.services.memory_slots import SLOT_TYPE_REGISTRY
    assert set(SLOT_TYPE_REGISTRY) == {"L1_TRACE", "L2_SUMMARY", "L3_PROFILE", "RAW_MD"}


def test_normalize_memory_field_compat():
    """形状兼容读（spec §四）：①期列表→{slots:[], legacy_paths}；对象直通；非法形状抛错。
    wenshu 卡（①种子的列表形状）读出即归一——升级窗口两形状并存。"""
    from app.services.memory_slots import normalize_memory_field
    assert normalize_memory_field(["/memory/AGENTS.md"]) == \
        {"slots": [], "legacy_paths": ["/memory/AGENTS.md"]}
    assert normalize_memory_field({"slots": [], "legacy_paths": ["/memory/AGENTS.md"]}) == \
        {"slots": [], "legacy_paths": ["/memory/AGENTS.md"]}
    assert normalize_memory_field(None) == {"slots": [], "legacy_paths": []}
    with pytest.raises(ValueError):
        normalize_memory_field("bad")


def test_validate_slots_five_rules():
    """五规则（spec §四，D3 验收依据）：正例过+五类反例各拒。"""
    from app.services.memory_slots import validate_slots
    ok = [
        {"slot": "对话轨迹", "type": "L1_TRACE", "surface": "chat", "read": "不注入"},
        {"slot": "会话摘要", "type": "L2_SUMMARY", "surface": "chat", "read": "注入", "order": 2},
        {"slot": "用户画像", "type": "L3_PROFILE", "slot_key": "profile", "read": "注入", "order": 3},
        {"slot": "偏好", "type": "RAW_MD", "path": "/memory/偏好.md",
         "writer": "agent_edit", "read": "注入", "order": 4},
    ]
    assert validate_slots(ok)["injected"] == \
        ["/memory/L2/chat.md", "/memory/L3/profile.md", "/memory/偏好.md"]  # 规范路径+order
    with pytest.raises(ValueError, match="槽类型不在注册表"):
        validate_slots([{"slot": "x", "type": "L4_MAGIC", "surface": "chat"}])
    with pytest.raises(ValueError, match="重复"):
        validate_slots([{"slot": "x", "type": "L1_TRACE", "surface": "a"},
                        {"slot": "x", "type": "L1_TRACE", "surface": "b"}])
    with pytest.raises(ValueError, match="consolidator"):
        validate_slots(ok, consolidator_on=False)            # 规则2：L2/L3 需服务开
    with pytest.raises(ValueError, match="AGENTS.md"):
        validate_slots([{"slot": "手", "type": "RAW_MD", "path": "/memory/AGENTS.md",
                         "writer": "agent_edit", "read": "不注入"}])   # 规则3：不得为手册
    with pytest.raises(ValueError, match="surface"):
        validate_slots([{"slot": "x", "type": "L1_TRACE", "surface": "不良 Surface!"}])  # 规则5


def test_injection_list_order():
    """注入列表：legacy 手册优先+槽按 order（spec §四规则4）。"""
    from app.services.memory_slots import injection_list
    mem = {"slots": [
        {"slot": "偏好", "type": "RAW_MD", "path": "/memory/偏好.md", "writer": "agent_edit", "read": "注入", "order": 4},
        {"slot": "会话摘要", "type": "L2_SUMMARY", "surface": "chat", "read": "注入", "order": 2}],
        "legacy_paths": ["/memory/AGENTS.md"]}
    assert injection_list(mem) == \
        ["/memory/AGENTS.md", "/memory/L2/chat.md", "/memory/偏好.md"]  # L2 走规范路径


# ---------------------------------------------------------------------------
# 批 2：per-user 根 + MemoryTreeBackend 三分支 + AGENTS.md 搬迁
# ---------------------------------------------------------------------------

def test_memory_roots_per_user():
    """expert_paths 扩 per-user（spec §八）：专家根/用户根落 backend/data/memory 下。"""
    from app.services.expert_paths import memory_expert_root, memory_user_root
    assert memory_expert_root("wenshu").as_posix().endswith("data/memory/wenshu")
    assert memory_user_root("wenshu", "anonymous").as_posix().endswith("data/memory/wenshu/anonymous")


def test_memory_tree_backend_three_branches(tmp_path, monkeypatch):
    """三分支（spec §五/§十二风险4，硬约束）：双根读/单根写（专家根拒）/越界拒。
    变异锚点：任一分支语义破 → 红。"""
    from app.services import memory_tree_backend as mtb
    _e = tmp_path / "wenshu"; _u = _e / "alice"
    _u.mkdir(parents=True); (_e / "AGENTS.md").write_text("手册", encoding="utf-8")
    (_u / "偏好.md").write_text("旧", encoding="utf-8")
    monkeypatch.setattr(mtb, "memory_expert_root", lambda e: _e)
    monkeypatch.setattr(mtb, "memory_user_root", lambda e, u: _u)
    card = {"expert_id": "wenshu", "memory": {"slots": [
        {"slot": "偏好", "type": "RAW_MD", "path": "/memory/偏好.md",
         "writer": "agent_edit", "read": "注入", "order": 4}], "legacy_paths": []}}
    b = mtb.MemoryTreeBackend("wenshu", card)
    # 结果对象全 @dataclass（deepagents.backends.protocol 实测，含 __post_init__）——
    # 属性访问 r.error/r.file_data（计划 R2 第3条「纯 dict 键访问」误诊，实证修正）。
    r = b.read("/memory/AGENTS.md")                       # 分支1：双根读（用户根 miss→专家根）
    assert (r.file_data or {}).get("content") == "手册"
    r2 = b.read("/memory/偏好.md")                        # 分支1：用户根命中
    assert not r2.error
    w = b.write("/memory/AGENTS.md", "篡改")              # 分支2：专家根（手册）写即拒
    assert w.error                                         # 手册防改第二道锁
    w2 = b.write("/memory/偏好.md", "新内容")              # 分支2：用户根写成功+备份轮转
    assert not w2.error
    assert (_u / "偏好.md").read_text(encoding="utf-8") == "新内容"
    assert any(((_u / "backup").glob("*/偏好.md")))         # 写前备份已轮转
    w3 = b.write("/memory/未声明.md", "x")                 # 分支3：越界（卡外）拒
    assert w3.error
    w4 = b.write("/etc/passwd", "x")                       # 分支3：树外拒
    assert w4.error


def test_migrate_agents_md_idempotent(tmp_path, monkeypatch):
    """AGENTS.md 受控搬迁（spec §九步骤2/F1）：搬→校验和逐字节→旧位 .bak；幂等重跑跳过。
    变异锚点：搬迁改内容一字节/漏 .bak/不幂等 → 红。"""
    import hashlib
    from app.services import memory_tree_backend as mtb
    _plat = tmp_path / "memory"; _plat.mkdir()
    (_plat / "AGENTS.md").write_bytes("纪律树内容逐字节".encode("utf-8"))
    monkeypatch.setattr(mtb, "_MEMORY_ROOT", _plat)
    src = _plat / "AGENTS.md"; dst = _plat / "wenshu" / "AGENTS.md"
    mtb._migrate_agents_md()
    assert dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() == \
        hashlib.sha256("纪律树内容逐字节".encode()).hexdigest()   # 逐字节
    assert (_plat / "AGENTS.md.bak").exists()                    # 旧位留 .bak
    mtb._migrate_agents_md()                                     # 幂等：目标在+校验同→跳过零写
    assert dst.read_text(encoding="utf-8") == "纪律树内容逐字节"


# ---------------------------------------------------------------------------
# 批 3：L1 轨迹（永不抛错/f 因子排除/A4）
# ---------------------------------------------------------------------------

def test_trace_append_never_raises(tmp_path, monkeypatch):
    """永不抛错（spec §六）：append 失败即吞+warning；JSONL 行含四类必需键。
    变异锚点：异常外泄 → 红。"""
    import json as _json
    from app.services import memory_trace as mt
    _f = tmp_path / "chat.jsonl"
    monkeypatch.setattr(mt, "_trace_file", lambda e, u, s: _f)
    mt.append_event("wenshu", "alice", "chat",
                    {"kind": "user_msg", "payload": {"text": "你好"}})   # 正常落盘
    assert "user_msg" in _f.read_text(encoding="utf-8")
    def _boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(mt, "_trace_file", _boom)
    mt.append_event("wenshu", "alice", "chat", {"kind": "user_msg"})      # 失败即吞
    rows = [_json.loads(l) for l in _f.read_text(encoding="utf-8").splitlines()]
    assert all({"id", "ts", "surface", "kind", "payload", "session_id", "turn_id"} <= set(r)
              for r in rows)                                             # 七键齐


def test_f_factor_excludes_trace(tmp_path, monkeypatch):
    """A4 前置（spec §五 f 因子修正）：trace/*.jsonl 增删不进哈希；注入槽文件变化进哈希。
    变异锚点：哈希含 trace → 红。"""
    from app.services import tupu_deepagent as td
    import app.services.expert_paths as ep
    _m = tmp_path / "memory" / "wenshu" / "alice"
    (_m / "trace" / "chat").mkdir(parents=True)
    (_m / "L2").mkdir(); (_m / "L2" / "chat.md").write_text("v1", encoding="utf-8")
    monkeypatch.setattr(ep, "memory_expert_root", lambda e: tmp_path / "memory" / e)
    monkeypatch.setattr(ep, "memory_user_root", lambda e, u: tmp_path / "memory" / e / u)
    card = {"expert_id": "wenshu", "memory": {"slots": [
        {"slot": "会话摘要", "type": "L2_SUMMARY", "surface": "chat", "read": "注入", "order": 2}],
        "legacy_paths": ["/memory/AGENTS.md"]}}
    h1 = td._compute_files_hash(card, user="alice")
    (_m / "trace" / "chat" / "d.jsonl").write_text('{"kind":"user_msg"}\n', encoding="utf-8")
    h2 = td._compute_files_hash(card, user="alice")                 # trace 追加→键不变
    assert h1 == h2
    (_m / "L2" / "chat.md").write_text("v2 固化后", encoding="utf-8")
    assert td._compute_files_hash(card, user="alice") != h1         # 注入槽变化→键变（正确）


# ---------------------------------------------------------------------------
# 批 4：权限规则卡驱动生成（D1/D2 素材）
# ---------------------------------------------------------------------------

def test_permission_rules_generation():
    """规则序列（spec §八）：skills allow + 逐槽 read/write + deny 基座垫底；
    wenshu slots=[] → 序列=现状三条逐字节等值（A2）。"""
    from app.services.tupu_deepagent import _memory_permission_rules
    wenshu = {"skills": ["/skills/"], "memory": {"slots": [], "legacy_paths": ["/memory/AGENTS.md"]}}
    assert _memory_permission_rules(wenshu) == [
        {"op": "read", "paths": ["/skills/**"], "mode": "allow"},
        {"op": "read", "paths": ["/**"], "mode": "deny"},
        {"op": "write", "paths": ["/**"], "mode": "deny"},
    ]
    card = {"skills": ["/skills/"], "memory": {"slots": [
        {"slot": "偏好", "type": "RAW_MD", "path": "/memory/偏好.md",
         "writer": "agent_edit", "read": "注入", "order": 4}], "legacy_paths": []}}
    rules = _memory_permission_rules(card)
    allows = [r for r in rules if r["mode"] == "allow"]
    assert {"op": "read", "paths": ["/skills/**"], "mode": "allow"} in allows
    assert {"op": "read", "paths": ["/memory/偏好.md"], "mode": "allow"} in allows   # edit 先读
    assert {"op": "write", "paths": ["/memory/偏好.md"], "mode": "allow"} in allows  # 逐槽精确到文件
    assert rules[-1] == {"op": "write", "paths": ["/**"], "mode": "deny"}            # deny 垫底
    assert rules[-2] == {"op": "read", "paths": ["/**"], "mode": "deny"}


def test_out_of_bounds_matrix():
    """越界矩阵（spec §八表，D1/D2）：四行全拒；AGENTS.md 双锁（权限层规则+Backend 层各验）。
    权限层=规则生成结果判定；Backend 层=批 2 已测。"""
    from app.services.tupu_deepagent import _memory_permission_rules
    def _allowed(rules, op, path):
        for r in rules:                                  # 按序匹配，首条命中生效
            import fnmatch
            if op == r["op"] and any(fnmatch.fnmatch(path, p) for p in r["paths"]):
                return r["mode"] == "allow"
        return True                                      # 无命中默认允许（框架语义）
    card = {"skills": ["/skills/"], "memory": {"slots": [
        {"slot": "偏好", "type": "RAW_MD", "path": "/memory/偏好.md",
         "writer": "agent_edit", "read": "注入", "order": 4}], "legacy_paths": []}}
    rules = _memory_permission_rules(card)
    assert _allowed(rules, "write", "/memory/偏好.md") is True          # ✅ 已声明
    assert _allowed(rules, "write", "/memory/AGENTS.md") is False       # ❌ 手册（权限锁1）
    assert _allowed(rules, "write", "/memory/未声明.md") is False       # ❌ 树内卡外
    assert _allowed(rules, "write", "/skills/foo.md") is False          # ❌ /skills/**
    assert _allowed(rules, "read", "/skills/foo.md") is True            # 读技能照常
    assert _allowed(rules, "write", "/etc/passwd") is False              # ❌ 树外
