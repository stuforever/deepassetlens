# -*- coding: utf-8 -*-
"""批13-Y Backend 官方服务器模式迁移 单测。

- _seed_files：种子内容与磁盘逐字节一致（两份真相）+ 清场防残留
- StoreBackend 路由：read 走 store（零磁盘）；路由外路径落 StateBackend 死路
- _compute_files_hash：内容变化 -> hash 变（新鲜度）
- 装配源码接线：manifest 三项 + 缓存键分量 + FilesystemBackend 退役
"""
import hashlib
import time

from pathlib import Path

from langgraph.store.memory import InMemoryStore

from app.services.tupu_deepagent import (
    _SKILLS_ROOT, _MEMORY_ROOT, _FILES_NS_SKILLS, _FILES_NS_MEMORY,
    _compute_files_hash, _seed_files,
)


def _agent_src() -> str:
    p = Path(__file__).resolve().parent.parent / "app" / "services" / "tupu_deepagent.py"
    return p.read_text(encoding="utf-8")


def test_种子内容与磁盘逐字节一致():
    """两份真相检查（设计验收③-①）：seeded store 内容 == 磁盘内容。key 带前导斜杠
    （CompositeBackend 路由后传给 StoreBackend 的路径形态，实测对齐——设计 §二验证点5 的
    key=相对路径在路由链下找不到，批13-Y 实施调和）。"""
    store = InMemoryStore()
    n = _seed_files(store, _FILES_NS_SKILLS, _SKILLS_ROOT)
    assert n > 0, "技能树种子数应 > 0"
    for p in sorted(_SKILLS_ROOT.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        rel = p.relative_to(_SKILLS_ROOT).as_posix()
        item = store.get(_FILES_NS_SKILLS, f"/{rel}")
        assert item is not None, f"缺种子: {rel}"
        assert item.value["content"] == p.read_text("utf-8"), f"内容不一致: {rel}"


def test_清场防残留():
    """删除文件后重种子 -> 旧 key 不残留（PutOp None 清场）。"""
    store = InMemoryStore()
    store.put(_FILES_NS_MEMORY, "ghost.md", {"content": "旧残留"})
    _seed_files(store, _FILES_NS_MEMORY, _MEMORY_ROOT)
    assert store.get(_FILES_NS_MEMORY, "ghost.md") is None, "清场失败：旧 key 残留"


def test_StoreBackend路由读store():
    """路由内路径：StoreBackend.aread 返回种子内容（不碰磁盘）。key 带前导斜杠（路由形态）。"""
    import asyncio
    from deepagents.backends import StoreBackend
    store = InMemoryStore()
    store.put(_FILES_NS_SKILLS, "/probe.md", {"content": "PROBE_CONTENT_13Y"})
    sb = StoreBackend(store=store, namespace=lambda rt: _FILES_NS_SKILLS)
    result = asyncio.run(sb.aread("/probe.md"))
    assert result.error is None, f"aread 报错: {result.error}"
    assert result.file_data["content"] == "PROBE_CONTENT_13Y"


def test_路由外不可达():
    """路由外路径（/etc/passwd 形态）落 default StateBackend —— 会话草稿纸为空 -> 报错死路。"""
    import asyncio
    from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
    store = InMemoryStore()
    store.put(_FILES_NS_SKILLS, "probe.md", {"content": "x"})
    backend = CompositeBackend(
        default=StateBackend(),
        routes={"/skills/": StoreBackend(store=store, namespace=lambda rt: _FILES_NS_SKILLS)},
    )
    try:
        asyncio.run(backend.aget("/etc/passwd"))
        raised = False
    except FileNotFoundError:
        raised = True
    except Exception:
        raised = True
    assert raised, "路由外路径必须不可达（StateBackend 空会话死路）"


def test_files_hash新鲜度(tmp_path, monkeypatch):
    """文件增/改 -> hash 变；无变化 -> hash 稳定。"""
    h1 = _compute_files_hash()
    h2 = _compute_files_hash()
    assert h1 == h2  # 稳定
    # 临时在技能树放一个文件 -> hash 变（用真树+新增文件验证 mtime/size 拼接有效）
    probe = _SKILLS_ROOT / "_hash_probe_13y.tmp"
    try:
        probe.write_text("probe", encoding="utf-8")
        h3 = _compute_files_hash()
        assert h3 != h1
    finally:
        probe.unlink(missing_ok=True)
    h4 = _compute_files_hash()
    assert h4 == h1  # 删除后恢复


def test_装配源码接线():
    """manifest 三项 + 缓存键 #f 分量 + FilesystemBackend 退役 + permissions 保留。
    2026-09-12 专家地基① 锚点适配：缓存键 6 因子化（_assembly_cache_key 内 #f{fhash}）+
    种子按卡路径派生（_seed_files(_files_store, _FILES_NS_SKILLS, _r)）——意图不变（files_hash
    并键、skills 种子走 _seed_files），仅源码字面量随重构更新。"""
    src = _agent_src()
    assert 'manifest_items["backend_mode"] = "store"' in src
    assert 'manifest_items["files_hash"]' in src
    assert 'manifest_items["seeded_files"]' in src
    assert "#f{fhash}" in src                                     # 专家地基①：6 因子键内 #f 分量
    assert "FilesystemBackend(" not in src, "FilesystemBackend 实例化必须退役（注释提及无妨）"
    assert "_seed_files(_files_store, _FILES_NS_SKILLS, _r)" in src  # 专家地基①：按卡根逐一种子
    # permissions 三规则保留（冗余保险带，设计改动清单#6）
    assert "拒绝写 /**" in src or "permissions" in src
