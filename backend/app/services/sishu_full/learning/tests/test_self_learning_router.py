"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.sishu_full.api.routers import self_learning as sl
from app.services.sishu_full.book.models import Book, BookStatus
from app.services.sishu_full.book.storage import BookStorage
from app.services.sishu_full.learning.curriculum import Chapter, CurriculumStore, KnowledgePoint, Textbook
from app.services.sishu_full.learning.mother_question import MotherQuestion, MotherQuestionStore


# --------------------------------------------------------------------------- #
# 隔离夹具（沿用 5.3 test_mother_question.isolated_data 先例：整体重定向）        #
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """PathService 默认实例 + multi_user 路径根全部落 tmp_path。

    h5 模块顶层 `from .paths import USERS_ROOT` 是 import 时快照
    （_load_h5_settings 用它定位 h5.json），须一并补丁才封闭。
    """
    from app.services.sishu_full.multi_user import h5 as h5_mod
    from app.services.sishu_full.multi_user import paths as mu_paths
    from app.services.sishu_full.services import path_service as ps_mod

    data_root = tmp_path / "data"
    monkeypatch.setattr(mu_paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mu_paths, "ADMIN_WORKSPACE_ROOT", data_root)
    monkeypatch.setattr(mu_paths, "USER_SECRETS_DIRNAME", "user-secrets")
    monkeypatch.setattr(mu_paths, "USERS_ROOT", data_root / "users")
    monkeypatch.setattr(mu_paths, "SYSTEM_ROOT", data_root / "system")
    monkeypatch.setattr(mu_paths, "_path_services", {})
    monkeypatch.setattr(h5_mod, "USERS_ROOT", data_root / "users")

    admin_service = ps_mod.PathService(workspace_root=data_root)
    monkeypatch.setattr(ps_mod.PathService, "_instance", admin_service, raising=False)
    monkeypatch.setattr(
        ps_mod.PathService, "get_instance", classmethod(lambda cls: admin_service)
    )
    return data_root


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(sl.router, prefix="/api/v1/self-learning")
    return TestClient(app)


# --------------------------------------------------------------------------- #
# 种子工具                                                                     #
# --------------------------------------------------------------------------- #


def _seed_curriculum() -> None:
    cs = CurriculumStore()
    cs.create_textbook(Textbook(id="tb1", name="七年级数学上", subject="math", grade="七年级"))
    cs.create_chapter(
        Chapter(id="ch1", textbook_id="tb1", name="有理数", order=1, kp_ids=["kp_cat", "kp_easy"])
    )
    cs.create_chapter(
        Chapter(
            id="ch1-1",
            textbook_id="tb1",
            parent_id="ch1",
            name="1.1 正数和负数",
            order=1,
            kp_ids=["kp_a"],
            page_start=2,
            page_end=5,
        )
    )
    # 分类节点（无难度）继承子节点最大难度；叶子带实例/公式/图形/相关关系
    cs.create_kp(KnowledgePoint(id="kp_cat", name="有理数分类"))
    cs.create_kp(
        KnowledgePoint(
            id="kp_a",
            name="正负数",
            parent_id="kp_cat",
            difficulty=3,
            related=[{"kp_id": "kp_b", "relation": "prerequisite"}],
        )
    )
    cs.create_kp(KnowledgePoint(id="kp_b", name="数轴", parent_id="kp_cat", difficulty=5))
    cs.create_kp(
        KnowledgePoint(
            id="kp_easy",
            name="零的认识",
            difficulty=1,
            examples=[{"title": "t", "content": "c"}],
            formula={"name": "f", "latex": "x=0"},
            figure={"type": "number_line", "config": {}},
        )
    )


def _seed_mothers() -> None:
    store = MotherQuestionStore()
    store.create_mother(
        MotherQuestion(id="mq1", title="有理数加法", question_text="1+1=?", chapter_id="ch1")
    )
    store.create_mother(
        MotherQuestion(
            id="mq2",
            title="有理数减法",
            question_text="2-3=?",
            chapter_id="ch1",
            difficulty=4,
            mastery_status="reviewing",
        )
    )
    store.create_mother(MotherQuestion(id="mq3", title="别章题", question_text="9*9=?", chapter_id="ch2"))
    deleted = MotherQuestion(id="mq4", title="已删", question_text="0/1=?", chapter_id="ch1")
    deleted.deleted_time = 123.0
    store.create_mother(deleted)


def _ws_dir(data_root) -> Any:
    """PathService.get_workspace_dir() = <workspace_root>/user/workspace。"""
    return data_root / "user" / "workspace"


def _write_manifest(data_root, book_id: str, payload: dict) -> None:
    d = _ws_dir(data_root) / "books" / book_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_progress(data_root, book_id: str, modules: list[dict]) -> None:
    d = _ws_dir(data_root) / "learning_progress"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{book_id}.json").write_text(json.dumps({"modules": modules}), encoding="utf-8")


def _write_grade7_index(data_root, index: dict) -> None:
    d = _ws_dir(data_root) / "grade7"
    d.mkdir(parents=True, exist_ok=True)
    (d / "grade7_index.json").write_text(json.dumps(index), encoding="utf-8")


# --------------------------------------------------------------------------- #
# 1. GET /chapter/{id} —— 章节聚合                                             #
# --------------------------------------------------------------------------- #


def test_overview_unknown_chapter_returns_error_dict(client):
    resp = client.get("/api/v1/self-learning/chapter/ghost")
    assert resp.status_code == 200
    assert resp.json() == {"error": "chapter not found", "chapter_id": "ghost"}


def test_overview_aggregates_chapter_textbook_children(client):
    _seed_curriculum()
    data = client.get("/api/v1/self-learning/chapter/ch1").json()
    assert data["chapter"]["id"] == "ch1"
    assert data["chapter"]["name"] == "有理数"
    assert data["chapter"]["textbook_id"] == "tb1"
    assert data["chapter"]["kp_ids"] == ["kp_cat", "kp_easy"]
    assert data["textbook"] == {"id": "tb1", "name": "七年级数学上", "subject": "math", "grade": "七年级"}
    assert [c["id"] for c in data["children"]] == ["ch1-1"]
    assert data["children"][0]["name"] == "1.1 正数和负数"


def test_overview_kps_sorted_by_effective_difficulty_with_full_payload(client):
    """无难度分类节点按子节点最大难度（5）参与排序；载荷带祖先链/相关名/实例/公式/图形。"""
    _seed_curriculum()
    data = client.get("/api/v1/self-learning/chapter/ch1").json()
    kps = data["knowledge_points"]
    # 难度 1 的叶子在前；分类节点有效难度 = max(3, 5) = 5 在后
    assert [k["id"] for k in kps] == ["kp_easy", "kp_cat"]
    easy = kps[0]
    assert easy["name"] == "零的认识"
    assert easy["difficulty"] == 1
    assert easy["examples"] == [{"title": "t", "content": "c"}]
    assert easy["formula"] == {"name": "f", "latex": "x=0"}
    assert easy["figure"] == {"type": "number_line", "config": {}}
    assert easy["path"] == ""  # 根节点无祖先链
    cat = kps[1]
    assert cat["difficulty"] is None  # 载荷保留原始难度；有效难度仅用于排序
    assert cat["path"] == ""


def test_overview_kp_payload_ancestor_chain_and_related_names(client):
    _seed_curriculum()
    data = client.get("/api/v1/self-learning/chapter/ch1-1").json()
    (kp_a,) = data["knowledge_points"]
    assert kp_a["path"] == "有理数分类"  # 祖先分类链
    assert kp_a["related"] == [{"kp_id": "kp_b", "relation": "prerequisite", "name": "数轴"}]


def test_overview_wrong_questions_count_recent_and_u_isolation(client):
    _seed_curriculum()
    _seed_mothers()
    data = client.get("/api/v1/self-learning/chapter/ch1").json()
    assert data["wrong_questions"]["count"] == 2  # 别章 + 已软删的不计
    recent_ids = {r["id"] for r in data["wrong_questions"]["recent"]}
    assert recent_ids == {"mq1", "mq2"}
    recent = {r["id"]: r for r in data["wrong_questions"]["recent"]}
    assert recent["mq2"]["difficulty"] == 4
    assert recent["mq2"]["mastery_status"] == "reviewing"

    # F2（M14-B）u 感知：?u= 读该用户工作区（空）→ 0，不串 admin 错题
    h5_data = client.get("/api/v1/self-learning/chapter/ch1", params={"u": "xiaoming"}).json()
    assert h5_data["wrong_questions"]["count"] == 0
    assert h5_data["wrong_questions"]["recent"] == []


def test_overview_access_code_wrong_code_rejected_with_401(client, isolated_data):
    """R1-c：chapter_overview 访问码守卫必须在 try 之外——错码 → 401，
    不得被 best-effort 吞成「200 + 公共段照返」（5.4 审查修复：闭合与
    resources 端点同款不变量；原表征用例锁定缺陷现状，本轮翻转为规格）。"""
    _seed_curriculum()
    _seed_mothers()
    settings_dir = isolated_data / "user" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "h5.json").write_text(json.dumps({"access_code": "topsecret"}), encoding="utf-8")

    resp = client.get("/api/v1/self-learning/chapter/ch1", params={"u": "xiaoming"})
    assert resp.status_code == 401  # 修复前：401 被 try/except 吞成 200
    # 对码放行：u 感知段在守卫返回的用户上下文内读取
    ok = client.get(
        "/api/v1/self-learning/chapter/ch1", params={"u": "xiaoming", "code": "topsecret"}
    )
    assert ok.status_code == 200


def test_overview_invalid_u_rejected_with_400(client):
    """R1-c 守卫上提到 try 之外后，非法 u 的 400 同样不再被吞（修复前 200）。"""
    _seed_curriculum()
    resp = client.get("/api/v1/self-learning/chapter/ch1", params={"u": "../evil"})
    assert resp.status_code == 400


def test_overview_related_books_matched_by_title_or_textbook_id(client, isolated_data):
    _seed_curriculum()
    _write_manifest(
        isolated_data,
        "bk_a",
        {"id": "bk_a", "title": "有理数巩固手册", "status": "ready", "page_count": 10, "chapter_count": 2},
    )
    _write_manifest(
        isolated_data,
        "bk_b",
        {"id": "bk_b", "title": "无关书名", "status": "compiling", "textbook_id": "tb1"},
    )
    _write_manifest(isolated_data, "bk_c", {"id": "bk_c", "title": "完全无关"})
    (isolated_data / "books" / "bk_bad").mkdir(parents=True, exist_ok=True)
    (isolated_data / "books" / "bk_bad" / "manifest.json").write_text("not-json", encoding="utf-8")

    books = client.get("/api/v1/self-learning/chapter/ch1").json()["related_books"]
    ids = {b["id"] for b in books}
    assert ids == {"bk_a", "bk_b"}  # 标题命中 + 教材 id 命中；无关/坏 JSON 排除
    by_id = {b["id"]: b for b in books}
    assert by_id["bk_a"]["page_count"] == 10
    assert by_id["bk_b"]["status"] == "compiling"


def test_overview_mastery_progress_matches_module_name(client, isolated_data):
    _seed_curriculum()
    _write_progress(
        isolated_data,
        "bk_x",
        [
            {"name": "有理数加法", "status": "completed"},
            {"name": "有理数减法", "status": "learning"},
            {"name": "几何入门", "status": "completed"},
        ],
    )
    mp = client.get("/api/v1/self-learning/chapter/ch1").json()["mastery_progress"]
    assert mp == {"book_id": "bk_x", "total_modules": 3, "matched_modules": 2, "completed": 2}


def test_overview_mastery_progress_none_when_no_match(client, isolated_data):
    _seed_curriculum()
    assert (
        client.get("/api/v1/self-learning/chapter/ch1").json()["mastery_progress"] is None
    )


# --------------------------------------------------------------------------- #
# 2. GET /textbooks —— 教材-章节树                                             #
# --------------------------------------------------------------------------- #


def test_textbooks_returns_full_tree(client):
    _seed_curriculum()
    tree = client.get("/api/v1/self-learning/textbooks").json()
    assert [tb["id"] for tb in tree] == ["tb1"]
    (ch,) = tree[0]["chapters"]
    assert ch["id"] == "ch1"
    assert ch["children"][0]["id"] == "ch1-1"
    assert ch["children"][0]["knowledge_points"][0]["name"] == "正负数"


# --------------------------------------------------------------------------- #
# 3. POST /chapter/{id}/book —— 一键生成课件书                                  #
# --------------------------------------------------------------------------- #


def test_create_book_404_unknown_chapter(client):
    resp = client.post("/api/v1/self-learning/chapter/ghost/book")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "chapter not found"


def test_create_book_reuses_existing_non_archived_book(client, isolated_data):
    _seed_curriculum()
    BookStorage().save_book(
        Book(id="bk_keep", title="有理数", status=BookStatus.READY,
             metadata={"curriculum_chapter_id": "ch1"})
    )
    data = client.post("/api/v1/self-learning/chapter/ch1/book").json()
    assert data == {"book_id": "bk_keep", "status": "ready", "reused": True}


def test_create_book_archived_book_is_not_reused(client, isolated_data, monkeypatch):
    _seed_curriculum()
    BookStorage().save_book(
        Book(id="bk_old", title="旧书", status=BookStatus.ARCHIVED,
             metadata={"curriculum_chapter_id": "ch1"})
    )
    captured: dict[str, Any] = {}

    class _FakeEngine:
        def list_books(self):
            # 真实形状：BookEngine.list_books 不含状态过滤，归档书照样返回；
            # 归档排除是路由自身的过滤分支（meta 匹配 + status 谓词），须真实行使。
            return [
                Book(id="bk_old", title="旧书", status=BookStatus.ARCHIVED,
                     metadata={"curriculum_chapter_id": "ch1"})
            ]

        async def create_from_chapter(self, **kwargs):
            captured.update(kwargs)
            return Book(id="bk_new", title=kwargs["chapter_name"], status=BookStatus.SPINE_READY), None

    monkeypatch.setattr("app.services.sishu_full.book.engine.get_book_engine", lambda: _FakeEngine())
    data = client.post("/api/v1/self-learning/chapter/ch1/book").json()
    assert data == {"book_id": "bk_new", "status": "spine_ready", "reused": False}


def test_create_book_passes_chapter_context_to_engine(client, isolated_data, monkeypatch):
    """新建路径把章节上下文（子章页码/kp 名/错题统计/学科 KB 映射）聚合给 BookEngine。"""
    _seed_curriculum()
    _seed_mothers()
    captured: dict[str, Any] = {}

    class _FakeEngine:
        def list_books(self):
            return []

        async def create_from_chapter(self, **kwargs):
            captured.update(kwargs)
            return Book(id="bk_new", title=kwargs["chapter_name"], status=BookStatus.SPINE_READY), None

    monkeypatch.setattr("app.services.sishu_full.book.engine.get_book_engine", lambda: _FakeEngine())
    data = client.post("/api/v1/self-learning/chapter/ch1/book").json()
    assert data == {"book_id": "bk_new", "status": "spine_ready", "reused": False}
    assert captured["curriculum_chapter_id"] == "ch1"
    assert captured["chapter_name"] == "有理数"
    assert captured["textbook_id"] == "tb1"
    assert captured["textbook_name"] == "七年级数学上"
    assert captured["subject"] == "math"
    assert captured["knowledge_base"] == "七年级数学上"  # _SUBJECT_KB 映射
    assert captured["children"] == [
        {"name": "1.1 正数和负数", "page_start": 2, "page_end": 5}
    ]
    assert captured["kp_names"] == ["有理数分类", "零的认识"]
    assert captured["wrong_count"] == 2
    # 存储返回顺序是实现细节，不锚定：聚合只保证章内错题全量取前 5
    assert set(captured["wrong_titles"]) == {"有理数加法", "有理数减法"}


# --------------------------------------------------------------------------- #
# 4. GET /chapter/{id}/books —— 章节课件书（父章继承）                           #
# --------------------------------------------------------------------------- #


def _seed_books() -> None:
    store = BookStorage()
    store.save_book(
        Book(id="bk_parent", title="有理数书", status=BookStatus.READY,
             chapter_count=2, page_count=12, metadata={"curriculum_chapter_id": "ch1"})
    )
    store.save_book(
        Book(id="bk_sub", title="正负数书", status=BookStatus.SPINE_READY,
             metadata={"curriculum_chapter_id": "ch1-1"})
    )
    store.save_book(
        Book(id="bk_arch", title="归档书", status=BookStatus.ARCHIVED,
             metadata={"curriculum_chapter_id": "ch1"})
    )
    store.save_book(
        Book(id="bk_other", title="别章书", status=BookStatus.READY,
             metadata={"curriculum_chapter_id": "ch9"})
    )


def test_chapter_books_sub_chapter_inherits_parent_books(client):
    _seed_curriculum()  # 父子继承按课程树解析，须先种教材/章节
    _seed_books()
    data = client.get("/api/v1/self-learning/chapter/ch1-1/books").json()
    assert data["count"] == 2  # 父章 + 自身；归档/别章排除
    ids = {b["id"] for b in data["items"]}
    assert ids == {"bk_parent", "bk_sub"}
    parent = next(b for b in data["items"] if b["id"] == "bk_parent")
    assert parent == {
        "id": "bk_parent",
        "title": "有理数书",
        "status": "ready",
        "chapter_count": 2,
        "page_count": 12,
    }


def test_chapter_books_parent_chapter_query_excludes_children_books(client):
    """chapter_books 只解析「自身 + 父章」（子章书不上卷到父章查询；
    资源端点的子章扩展是另一套语义，两处不对称按现状锁定）。"""
    _seed_curriculum()
    _seed_books()
    data = client.get("/api/v1/self-learning/chapter/ch1/books").json()
    assert data["count"] == 1
    assert {b["id"] for b in data["items"]} == {"bk_parent"}


def test_chapter_books_empty_when_no_books(client):
    _seed_curriculum()
    data = client.get("/api/v1/self-learning/chapter/ch1/books").json()
    assert data == {"items": [], "count": 0}


# --------------------------------------------------------------------------- #
# 5. GET /chapter/{id}/resources —— 章节资源 + 自适应选题                       #
# --------------------------------------------------------------------------- #


def test_resources_missing_index_returns_empty(client):
    _seed_curriculum()
    resp = client.get("/api/v1/self-learning/chapter/ch1-1/resources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["courseware"] == []
    assert data["exercises"] == []
    assert data["voices"] == []
    assert data["figures"] == []
    # 索引缺失走早退分支：无 adaptive 键（与索引存在的响应形状不对称，按现状锁定）
    assert "adaptive" not in data


def _seed_index() -> dict:
    return {
        "courseware": [{"id": "cw1", "chapter_ids": ["ch1"]}],
        "exercises": [
            {"id": "ex_sub", "title": "1.1 闯关", "chapter_ids": ["ch1-1"], "questions": [{"q": 1}]},
            {"id": "ex_parent", "title": "第一章 闯关", "chapter_ids": ["ch1"], "questions": []},
            {"id": "ex_other", "title": "别章 闯关", "chapter_ids": ["ch9"], "questions": []},
        ],
        "voices": [{"id": "v1", "chapter_ids": ["ch1"]}],
        "figures": [{"id": "f1", "chapter_ids": ["ch1-1"]}],
    }


def test_resources_match_chapter_and_parent_inheritance(client, isolated_data):
    _seed_curriculum()
    _write_grade7_index(isolated_data, _seed_index())
    data = client.get("/api/v1/self-learning/chapter/ch1-1/resources").json()
    assert [c["id"] for c in data["courseware"]] == ["cw1"]  # 父章课件继承
    assert {e["id"] for e in data["exercises"]} == {"ex_sub", "ex_parent"}
    assert [v["id"] for v in data["voices"]] == ["v1"]
    assert [f["id"] for f in data["figures"]] == ["f1"]
    # 自适应选题管道生效：每题带 priority / adaptive_reason（无画像 → normal）
    ex = next(e for e in data["exercises"] if e["id"] == "ex_sub")
    assert ex["priority"] == 3
    assert ex["adaptive_reason"] == "normal"
    assert data["adaptive"] == {"adapted": False, "summary": []}


def test_resources_parent_chapter_includes_sub_chapter_resources(client, isolated_data):
    _seed_curriculum()
    _write_grade7_index(isolated_data, _seed_index())
    data = client.get("/api/v1/self-learning/chapter/ch1/resources").json()
    assert {e["id"] for e in data["exercises"]} == {"ex_sub", "ex_parent"}


def test_resources_u_personalization_runs_selector(client, isolated_data):
    """带 ?u= 时在 H5 用户上下文构建画像选题（空画像 → 不调整、无摘要）。"""
    _seed_curriculum()
    _write_grade7_index(isolated_data, _seed_index())
    data = client.get(
        "/api/v1/self-learning/chapter/ch1-1/resources", params={"u": "xiaoming"}
    ).json()
    assert {e["id"] for e in data["exercises"]} == {"ex_sub", "ex_parent"}
    assert data["adaptive"] == {"adapted": False, "summary": []}


def test_resources_access_code_enforced_when_configured(client, isolated_data):
    """R1-c：访问码门禁在 best-effort 之外，错码 → 401 不被吞。"""
    _seed_curriculum()
    _write_grade7_index(isolated_data, _seed_index())
    settings_dir = isolated_data / "user" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "h5.json").write_text(json.dumps({"access_code": "topsecret"}), encoding="utf-8")

    assert (
        client.get("/api/v1/self-learning/chapter/ch1-1/resources", params={"u": "xiaoming"}).status_code
        == 401
    )
    ok = client.get(
        "/api/v1/self-learning/chapter/ch1-1/resources", params={"u": "xiaoming", "code": "topsecret"}
    )
    assert ok.status_code == 200
    # u 缺省（桌面/admin）不受访问码约束
    assert client.get("/api/v1/self-learning/chapter/ch1-1/resources").status_code == 200
