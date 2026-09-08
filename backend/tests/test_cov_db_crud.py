# -*- coding: utf-8 -*-
"""覆盖补全批次1a：common_stop_word + standard_dict CRUD 语义（此前零直接测试）。

characterization 纪律：每个测试注明会让它失败的生产改动。
DB 惯例沿 test_g1/test_s4：真实 SessionLocal + 唯一标记 + finally 清理。
"""
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.base import CommonStopWord as CommonStopWordModel  # noqa: E402
from app.models.base import StandardDict as StandardDictModel  # noqa: E402
from app.services import common_stop_word as csw  # noqa: E402
from app.services import standard_dict as sd  # noqa: E402

_MARKER = "ZZCOV" + uuid.uuid4().hex[:8]


def _cleanup_stop_words():
    db = SessionLocal()
    try:
        for row in db.query(CommonStopWordModel).filter(CommonStopWordModel.word.like(_MARKER + "%")).all():
            db.delete(row)
        db.commit()
    finally:
        db.close()


def _cleanup_standard_dict():
    db = SessionLocal()
    try:
        for row in db.query(StandardDictModel).filter(StandardDictModel.non_standard.like(_MARKER + "%")).all():
            db.delete(row)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# common_stop_word
# ---------------------------------------------------------------------------

def test_stop_word_create_then_duplicate_returns_existing():
    """重复创建返回既有行+True（去重语义）。改动：create_stop_word 去重分支被删 -> 失败。"""
    db = SessionLocal()
    try:
        w1, dup1 = csw.create_stop_word(db, f"{_MARKER}的", category="filler", description="t")
        w2, dup2 = csw.create_stop_word(db, f"{_MARKER}的", category="filler", description="t")
        assert dup1 is False and dup2 is True
        assert w1.id == w2.id
    finally:
        _cleanup_stop_words()


def test_stop_word_list_filters():
    """category/enabled_only 过滤语义。改动：任一 filter 分支被删 -> 失败。"""
    db = SessionLocal()
    try:
        a, _ = csw.create_stop_word(db, f"{_MARKER}A词", category="unit", description="")
        b, _ = csw.create_stop_word(db, f"{_MARKER}B词", category="ops", description="")
        csw.update_stop_word(db, b.id, enabled=False)
        by_cat = csw.list_stop_words(db, category="unit")
        assert all(r.category == "unit" and r.word.startswith(_MARKER) for r in by_cat)
        assert a.id in {r.id for r in by_cat} and b.id not in {r.id for r in by_cat}
        enabled = csw.list_stop_words(db, enabled_only=True)
        assert a.id in {r.id for r in enabled} and b.id not in {r.id for r in enabled}
    finally:
        _cleanup_stop_words()


def test_stop_word_update_partial_and_missing():
    """部分字段更新不动其他字段；不存在 id -> None。改动：update 的 None 跳过逻辑被删 -> 失败。"""
    db = SessionLocal()
    try:
        row, _ = csw.create_stop_word(db, f"{_MARKER}U词", category="unit", description="d0")
        out = csw.update_stop_word(db, row.id, description="d1")
        assert out.description == "d1" and out.word == f"{_MARKER}U词" and out.category == "unit"
        assert out.enabled is True  # 未传 enabled，保持原值
        assert csw.update_stop_word(db, "no-such-id-xyz", word="x") is None
    finally:
        _cleanup_stop_words()


def test_stop_word_delete_semantics():
    """存在删除返回 True 且查无；不存在返回 False。改动：delete 的 not found 分支被删 -> 失败。"""
    db = SessionLocal()
    try:
        row, _ = csw.create_stop_word(db, f"{_MARKER}D词", category="unit", description="")
        assert csw.delete_stop_word(db, row.id) is True
        assert db.query(CommonStopWordModel).filter(CommonStopWordModel.id == row.id).first() is None
        assert csw.delete_stop_word(db, row.id) is False
    finally:
        _cleanup_stop_words()


# ---------------------------------------------------------------------------
# standard_dict
# ---------------------------------------------------------------------------

def test_standard_dict_create_dedup_and_keyword_search():
    """去重语义 + keyword 双列 ilike 搜索。改动：keyword 的 OR 过滤被删 -> 失败。"""
    db = SessionLocal()
    try:
        i1, dup1 = sd.create_standard_dict(db, f"{_MARKER}电费", "居民电费", category="unit")
        assert dup1 is False
        i2, dup2 = sd.create_standard_dict(db, f"{_MARKER}电费", "居民电费")
        assert dup2 is True and i2.id == i1.id
        # 关键词命中 non_standard 列
        hits_ns = sd.list_standard_dict(db, keyword=f"{_MARKER}电费")
        assert i1.id in {r.id for r in hits_ns}
        # 关键词命中 standard 列
        hits_std = sd.list_standard_dict(db, keyword="居民电费")
        assert i1.id in {r.id for r in hits_std}
        # 无关关键词不命中
        assert sd.list_standard_dict(db, keyword="ZZ毫无关系词QQ") == []
    finally:
        _cleanup_standard_dict()


def test_standard_dict_category_and_enabled_filter():
    """category 过滤 + enabled 过滤。改动：filter 分支被删 -> 失败。"""
    db = SessionLocal()
    try:
        a, _ = sd.create_standard_dict(db, f"{_MARKER}C1", "标准C1", category="catA")
        b, _ = sd.create_standard_dict(db, f"{_MARKER}C2", "标准C2", category="catB")
        sd.update_standard_dict(db, str(b.id), enabled=False)
        cat_a = sd.list_standard_dict(db, category="catA")
        assert a.id in {r.id for r in cat_a} and b.id not in {r.id for r in cat_a}
        enabled_rows = sd.list_standard_dict(db, enabled=True)
        assert a.id in {r.id for r in enabled_rows} and b.id not in {r.id for r in enabled_rows}
    finally:
        _cleanup_standard_dict()


def test_standard_dict_update_and_missing():
    """更新走 uuid 解析；合法但不存在的 uuid -> None。改动：not-found 分支被删 -> 失败。"""
    db = SessionLocal()
    try:
        row, _ = sd.create_standard_dict(db, f"{_MARKER}U1", "旧标准", category="unit")
        out = sd.update_standard_dict(db, str(row.id), standard="新标准")
        assert out.standard == "新标准" and out.non_standard == f"{_MARKER}U1"
        assert out.enabled is True  # 未传字段保持
        assert sd.update_standard_dict(db, str(uuid.uuid4()), standard="x") is None
    finally:
        _cleanup_standard_dict()


def test_standard_dict_invalid_uuid_raises_valueerror():
    """characterization：非法 uuid 串 -> ValueError（uuid.UUID 解析边界，API 层应转 400）。
    改动：update 不再解析 uuid -> 此测试失败（提醒同步调整）。"""
    db = SessionLocal()
    with pytest.raises(ValueError):
        sd.update_standard_dict(db, "not-a-uuid", standard="x")
    with pytest.raises(ValueError):
        sd.delete_standard_dict(db, "not-a-uuid")


def test_standard_dict_delete_semantics():
    """存在删除 True 且查无；合法不存在 uuid 删除 False。改动：delete 分支被删 -> 失败。"""
    db = SessionLocal()
    try:
        row, _ = sd.create_standard_dict(db, f"{_MARKER}D1", "标准D1")
        assert sd.delete_standard_dict(db, str(row.id)) is True
        assert db.query(StandardDictModel).filter(StandardDictModel.id == row.id).first() is None
        assert sd.delete_standard_dict(db, str(uuid.uuid4())) is False
    finally:
        _cleanup_standard_dict()
