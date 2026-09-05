# -*- coding: utf-8 -*-
"""批15 单测：SKILL 文件缓存新鲜度收口（设计 §四验收标准）。

件1：_load_skill_md 拆两层指纹键——指纹变→新正文；同指纹→`is` 同一对象；
件2：_GUIDANCE_SECTIONS 指纹感知——文件变→小节更新；
硬判据：既有 test_13g 四测原样绿（零语义变化）由全量回归承担。
"""
import importlib
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# 件1：_load_skill_md_cached 指纹键
# ---------------------------------------------------------------------------

def _mk_skill_md(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_cached_same_sig_same_object(tmp_path):
    """同指纹二调 → `is` 同一对象（13-G 同一性契约 + test_13g 同断言语义）。"""
    from app.services.tupu_deepagent import _load_skill_md_cached
    p = _mk_skill_md(tmp_path, "正文内容 A")
    st = p.stat()
    a = _load_skill_md_cached(str(p), st.st_mtime_ns, st.st_size)
    b = _load_skill_md_cached(str(p), st.st_mtime_ns, st.st_size)
    assert a is b


def test_cached_new_sig_new_content(tmp_path):
    """改内容+utime 强制 mtime_ns 变 → 同路径不同指纹 → 新正文。"""
    from app.services.tupu_deepagent import _load_skill_md_cached
    p = _mk_skill_md(tmp_path, "正文内容 A")
    st = p.stat()
    a = _load_skill_md_cached(str(p), st.st_mtime_ns, st.st_size)
    time.sleep(0.02)
    p.write_text("正文内容 B（新）", encoding="utf-8")
    os.utime(p, None)  # 强制刷新 mtime
    st2 = p.stat()
    assert (st2.st_mtime_ns, st2.st_size) != (st.st_mtime_ns, st.st_size)
    b = _load_skill_md_cached(str(p), st2.st_mtime_ns, st2.st_size)
    assert b == "正文内容 B（新）"
    assert b != a


def test_public_entry_reads_file(tmp_path, monkeypatch):
    """公开入口零语义变化：真实技能返回正文且 frontmatter 已去（--- 头剥离）；未知技能返回空串。"""
    from app.services import tupu_deepagent as td
    real = td._load_skill_md("distribution-overload")
    assert real and not real.startswith("---")
    assert td._load_skill_md("no-such-skill-xyz") == ""
    assert td._load_skill_md("") == ""


def test_subskill_shared_cache_entry():
    """子技能降级五名共享一条缓存（键=resolved_path）。"""
    from app.services.tupu_deepagent import _load_skill_md
    a = _load_skill_md("distribution-overload")
    b = _load_skill_md("distribution-overload-impact")
    assert a is b


# ---------------------------------------------------------------------------
# 件2：_GUIDANCE_SECTIONS 指纹感知
# ---------------------------------------------------------------------------

def test_guidance_refresh_on_file_change(tmp_path, monkeypatch):
    """monkeypatch 路径指向 tmp 文件 → 调用 → 改文件+utime → 再调 → 小节更新。"""
    import app.services.query_contract as qc
    p = tmp_path / "SKILL.md"
    p.write_text("### 小节一\n旧内容行\n", encoding="utf-8")
    monkeypatch.setattr(qc, "_SKILL_SQL_QUERY_PATH", str(p))
    monkeypatch.setattr(qc, "_GUIDANCE_SECTIONS", None)
    monkeypatch.setattr(qc, "_GUIDANCE_SIG", None)
    s1 = qc._load_guidance_sections()
    assert s1.get("小节一") == "旧内容行"
    time.sleep(0.02)
    p.write_text("### 小节一\n新内容行\n### 小节二\n追加\n", encoding="utf-8")
    os.utime(p, None)
    s2 = qc._load_guidance_sections()
    assert s2.get("小节一") == "新内容行"
    assert "小节二" in s2


def test_guidance_unchanged_hits_cache(tmp_path, monkeypatch):
    """未变：二调返回同一 dict 对象（现状行为保持）。"""
    import app.services.query_contract as qc
    p = tmp_path / "SKILL.md"
    p.write_text("### A\nx\n", encoding="utf-8")
    monkeypatch.setattr(qc, "_SKILL_SQL_QUERY_PATH", str(p))
    monkeypatch.setattr(qc, "_GUIDANCE_SECTIONS", None)
    monkeypatch.setattr(qc, "_GUIDANCE_SIG", None)
    a = qc._load_guidance_sections()
    b = qc._load_guidance_sections()
    assert a is b


def test_guidance_missing_file_tolerant(tmp_path, monkeypatch):
    """文件消失：沿用旧值（容错语义与现状一致）。"""
    import app.services.query_contract as qc
    p = tmp_path / "SKILL.md"
    p.write_text("### A\nx\n", encoding="utf-8")
    monkeypatch.setattr(qc, "_SKILL_SQL_QUERY_PATH", str(p))
    monkeypatch.setattr(qc, "_GUIDANCE_SECTIONS", None)
    monkeypatch.setattr(qc, "_GUIDANCE_SIG", None)
    assert qc._load_guidance_sections().get("A") == "x"
    monkeypatch.setattr(qc, "_SKILL_SQL_QUERY_PATH", str(tmp_path / "gone.md"))
    assert qc._load_guidance_sections().get("A") == "x"
