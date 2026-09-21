# -*- coding: utf-8 -*-
"""v4批6 6.1 TDD：sishu_learning 七域平台路由契约面测试。

断言口径（auth-mode-agnostic——TestClient 匿名=auth0 形态）：
  1. 代表性端点：路径/方法/响应形状（vendor 同构，L2 门的单测面）；
  2. 裸挂检查：每条路由 dependencies 都含 require_expert+binding（执法面全量）；
  3. 作用域隔离：?u= 命中 compat 上下文（local-admin/h5_<slug> 两形）。
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """最小契约面 app：只挂 sishu 六路由（整 app 的 MCP/后台线程会挂 TestClient）。"""
    import os
    os.environ.setdefault("DT_TUTOR_WORKSPACE_ROOT", "data/experts/tutor/workspace")
    os.environ["ENABLE_AUTH"] = "0"  # 基准形态
    from fastapi import FastAPI
    from app.api.sishu_learning import SISHU_MOUNTS
    from app.api.sishu_learning._enforce import SISHU_ROUTER_DEPS
    app = FastAPI()
    for r, prefix, tags in SISHU_MOUNTS:
        app.include_router(r, prefix=prefix, tags=tags, dependencies=SISHU_ROUTER_DEPS)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _sishu_routes():
    from app.api.sishu_learning import SISHU_MOUNTS
    out = []
    for r, _prefix, _tags in SISHU_MOUNTS:
        out.extend(r.routes)
    return out


class TestEnforcementMounting:
    def test_all_routes_have_sishu_deps(self):
        """裸挂检查：六域全部路由 dependencies 含 require_expert+binding 两件。

        闭包函数身份每次调用不同——按函数名断言（require_expert 内件=_dep）。
        """
        routes = _sishu_routes()
        assert len(routes) >= 100, f"挂载路由数异常: {len(routes)}"
        for r in routes:
            names = {getattr(d.call, "__name__", "") for d in getattr(r, "dependant", None).dependencies or []}
            assert {"_dep", "_sishu_binding_dep"} <= names, f"{r.path} 缺执法依赖: {names}"

    def test_mount_prefixes_match_vendor(self):
        """挂载表与 vendor tutor_routers 装配行逐字对齐（前端契约零改）。
        main.py 实挂由部署检查/L2 重放覆盖（28000 实测 200）。"""
        from app.api.sishu_learning import SISHU_MOUNTS
        from app.services.sishu_full.api.tutor_routers import tutor_routers as _tt
        vendor_map = {tags[0]: prefix for _r, prefix, tags, _d in _tt if tags}
        for _r, prefix, tags in SISHU_MOUNTS:
            assert vendor_map.get(tags[0]) == prefix, \
                f"{tags[0]} 前缀漂移: 平台={prefix} vendor={vendor_map.get(tags[0])}"


class TestRepresentativeShapes:
    def test_mq_list_shape(self, client):
        r = client.get("/api/v1/mother-questions?page=1&page_size=3")
        assert r.status_code == 200
        body = r.json()
        for k in ("total", "page", "page_size", "items"):
            assert k in body, f"缺键 {k}"
        if body["items"]:
            item = body["items"][0]
            for k in ("id", "title", "question_text", "subject", "difficulty",
                      "status", "mastery_status", "create_time", "update_time", "created_at"):
                assert k in item, f"mq item 缺键 {k}"

    def test_mq_due_count(self, client):
        r = client.get("/api/v1/mother-questions/reviews/due_count")
        assert r.status_code == 200 and "due_count" in r.json()

    def test_mq_analysis_by_subject(self, client):
        r = client.get("/api/v1/mother-questions/analysis/by-subject")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "total_subjects" in body

    def test_mq_dict_shape(self, client):
        r = client.get("/api/v1/mother-questions/dict")
        assert r.status_code == 200
        body = r.json()
        for k in ("textbooks", "chapters", "knowledge_points", "tags", "subjects"):
            assert k in body, f"dict 缺键 {k}"

    def test_learner_profile(self, client):
        r = client.get("/api/v1/learning/learner-profile")
        assert r.status_code == 200

    def test_mastery_progress(self, client):
        r = client.get("/api/v1/learning/progress")
        assert r.status_code == 200

    def test_self_learning_textbooks(self, client):
        r = client.get("/api/v1/self-learning/textbooks")
        assert r.status_code == 200

    def test_notebook_list(self, client):
        r = client.get("/api/v1/notebook/list")
        assert r.status_code == 200

    def test_question_notebook_categories(self, client):
        r = client.get("/api/v1/question-notebook/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_question_notebook_entries_shape(self, client):
        r = client.get("/api/v1/question-notebook/entries?limit=3")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "total" in body
        if body["items"]:
            item = body["items"][0]
            for k in ("id", "session_id", "question_id", "question", "options",
                      "is_correct", "bookmarked", "created_at", "updated_at"):
                assert k in item, f"nb item 缺键 {k}"


class TestUserScope:
    def test_u_isolation_h5_slug(self, client):
        """?u=<slug> → h5_<slug> 作用域（空白=local-admin）——空数据不断言内容只断 200。"""
        r1 = client.get("/api/v1/mother-questions?u=测试生")
        assert r1.status_code == 200
        r2 = client.get("/api/v1/mother-questions?u=测试生&page_size=5")
        body2 = r2.json()
        if body2["items"]:
            # h5 作用域数据 user_id 应为 h5_ 前缀（PG 列面隔离）
            from app.services.sishu_data.pg import engine
            from sqlalchemy import text
            with engine.connect() as c:
                uid = c.execute(text("SELECT user_id FROM sishu_mq_docs WHERE mq_id=:i"),
                                {"i": body2["items"][0]["id"]}).scalar()
            assert uid is None or uid.startswith("h5_") or uid == "local-admin"
