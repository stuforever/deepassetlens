# -*- coding: utf-8 -*-
"""R5批⑧（清单安全）契约测试：sishu_data 跨用户隔离。

- notebook_store：add/remove_entry_to_category 归属校验（IDOR）
- mq_store.create_tag：全局 PK 冲突校验归属（他人占用报错，不再跨用户改写）
变异锚点：归属校验/冲突分支删除 → 对应测红。
"""
import inspect

import pytest

from app.services.sishu_data import mq_store


class _R:
    def __init__(self, v, rowcount=1):
        self._v = v
        self.rowcount = rowcount
    def first(self):
        return self._v
    def scalar(self):
        return self._v


class _FakeConn:
    def __init__(self, results):
        self.results = list(results)
        self.executed = []
    def execute(self, sql, params=None):
        self.executed.append((str(sql), params))
        return _R(self.results.pop(0) if self.results else None)


class _FakeBegin:
    def __init__(self, conn):
        self.conn = conn
    def __enter__(self):
        return self.conn
    def __exit__(self, *a):
        return False


class _FakeEngine:
    def __init__(self, conn):
        self.conn = conn
    def begin(self):
        return _FakeBegin(self.conn)


@pytest.fixture()
def scoped(monkeypatch):
    monkeypatch.setattr(mq_store, "_scope_user", lambda: "uA", raising=False)
    monkeypatch.setattr(mq_store, "_cas_lock", __import__("threading").Lock())


def test_create_tag_other_user_occupied_raises(scoped, monkeypatch):
    conn = _FakeConn([("uB",)])  # 已存在且归 uB
    monkeypatch.setattr(mq_store, "engine", _FakeEngine(conn))
    with pytest.raises(ValueError):
        mq_store.MotherQuestionStorePG.create_tag(None, "同名标签", "#fff")


def test_create_tag_same_user_updates(scoped, monkeypatch):
    conn = _FakeConn([("uA",), None])  # 已存在归本人 → UPDATE
    monkeypatch.setattr(mq_store, "engine", _FakeEngine(conn))
    out = mq_store.MotherQuestionStorePG.create_tag(None, "t1", "#0f0")
    assert out["color"] == "#0f0"
    assert any("UPDATE sishu_mq_tags" in s for s, _ in conn.executed)


def test_create_tag_fresh_inserts(scoped, monkeypatch):
    conn = _FakeConn([None, None])  # 不存在 → INSERT
    monkeypatch.setattr(mq_store, "engine", _FakeEngine(conn))
    out = mq_store.MotherQuestionStorePG.create_tag(None, "t2", None)
    assert out["id"] == "t2"
    assert any("INSERT INTO sishu_mq_tags" in s for s, _ in conn.executed)


def test_notebook_link_ops_carry_ownership_guards():
    """源码锚定：关联/解绑必须带 user_id 归属谓词（IDOR 防线）。"""
    from app.services.sishu_data import notebook_store as ns
    src = inspect.getsource(ns.PgNotebookSessionStore.add_entry_to_category)
    assert "user_id=:u" in src and "sishu_notebook_entries" in src \
        and "sishu_notebook_categories" in src
    src2 = inspect.getsource(ns.PgNotebookSessionStore.remove_entry_from_category)
    assert "e.user_id=:u" in src2 and "ct.user_id=:u" in src2
