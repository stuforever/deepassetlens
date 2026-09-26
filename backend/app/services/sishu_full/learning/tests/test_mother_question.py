"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
from __future__ import annotations

import asyncio
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException  # noqa: F401  (HTTPException 供各用例 pytest.raises 使用)
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.api.sishu_learning import mother_question as mother_router
from app.services.sishu_full.learning.image_pipeline import (
    crop_by_bbox,
    detect_red_strokes,
    make_thumbnail,
    resolve_url_to_path,
    save_upload,
    split_questions,
)
from app.services.sishu_full.learning.mother_question import (
    MotherQuestion,
    MotherQuestionStore,
    QuestionVariant,
)
from app.services.sishu_full.learning.simhash_util import compute_simhash


def _mother(mid: str = "m1") -> MotherQuestion:
    return MotherQuestion(id=mid, title="应用题", question_text="小明有 3 个苹果")


def test_create_request_persists_all_wrong_question_fields(tmp_path, monkeypatch):
    store = MotherQuestionStore(root=tmp_path)
    monkeypatch.setattr(mother_router, "_store", lambda: store)

    body = mother_router.CreateMotherRequest(
        title="应用题",
        question_text="小明有 3 个苹果",
        standard_answer="3",
        wrong_answer="4",
        detailed_analysis="把题目中的数量重新数一遍。",
        note="下次先圈出已知条件。",
        wrong_reason="审题错误",
        related_lecture_doc_ids=["lecture-1"],
    )
    result = asyncio.run(mother_router.create_mother_question(body))
    saved = store.get_mother(result["id"])

    assert saved is not None
    assert saved.wrong_answer == "4"
    assert saved.detailed_analysis == "把题目中的数量重新数一遍。"
    assert saved.note == "下次先圈出已知条件。"
    assert saved.related_lecture_doc_ids == ["lecture-1"]
    assert saved.simhash is not None


def test_delete_variant_releases_lock_and_updates_counter(tmp_path):
    store = MotherQuestionStore(root=tmp_path)
    store.create_mother(_mother())
    variant = QuestionVariant(id="v1", mother_id="m1", question_text="变式题")
    store.create_variant(variant)

    result: list[bool] = []
    worker = Thread(target=lambda: result.append(store.delete_variant("v1")))
    worker.start()
    worker.join(timeout=1)

    assert not worker.is_alive(), "variant deletion must not deadlock on the store lock"
    assert result == [True]
    assert store.get_mother("m1").variant_count == 0


def test_review_log_appends_are_not_lost_under_concurrency(tmp_path):
    store = MotherQuestionStore(root=tmp_path)

    def append(index: int) -> int:
        return store.append_review_log({"mother_id": "m1", "index": index})

    with ThreadPoolExecutor(max_workers=8) as executor:
        totals = list(executor.map(append, range(40)))

    assert len(store.list_review_log("m1")) == 40
    assert max(totals) == 40


# --------------------------------------------------------------------------- #
# P2-B 错因 LLM 自动归因                                                      #
# --------------------------------------------------------------------------- #

def _attr_mother(mid: str = "m1", wrong_reason: str | None = None) -> MotherQuestion:
    return MotherQuestion(
        id=mid,
        title="计算题",
        question_text="25 × 4 = ?",
        standard_answer="100",
        wrong_answer="90",
        wrong_reason=wrong_reason,
    )


def test_attribute_cached_when_reason_exists(tmp_path, monkeypatch):
    """已有 wrong_reason 且未 force → 返回 cached，不触发 LLM。"""
    import urllib.request

    store = MotherQuestionStore(root=tmp_path)
    store.create_mother(_attr_mother(wrong_reason="计算错误"))
    monkeypatch.setattr(mother_router, "_store", lambda: store)
    # 若触发了 LLM，urlopen 被调用 → 抛异常暴露
    def _boom(*a, **k):
        raise AssertionError("LLM 不应被调用")
    monkeypatch.setattr(urllib.request, "urlopen", _boom)

    result = asyncio.run(mother_router.attribute_wrong_reason("m1", payload={}, u=""))
    assert result["cached"] is True
    assert result["wrong_reason"] == "计算错误"


def test_attribute_503_when_llm_not_configured(tmp_path, monkeypatch):
    """LLM key 未配置 → 503，不改写错因。"""
    from fastapi import HTTPException

    class _Cfg:
        api_key = "sk-placeholder"
        model = "x"

    store = MotherQuestionStore(root=tmp_path)
    store.create_mother(_attr_mother())
    monkeypatch.setattr(mother_router, "_store", lambda: store)
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _Cfg())

    try:
        asyncio.run(mother_router.attribute_wrong_reason("m1", payload={}, u=""))
        assert False, "应抛 503"
    except HTTPException as e:
        assert e.status_code == 503


def test_attribute_persists_reason_and_advice(tmp_path, monkeypatch):
    """LLM 正常返回 → 写入 wrong_reason/wrong_advice，且非枚举值兜底为「其他」。"""
    import json
    import urllib.request

    class _Cfg:
        api_key = "real-key"
        model = "deepseek"
        base_url = "http://localhost:9999/v1"

    class _Resp:
        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": '{"wrong_reason":"粗心","confidence":0.9,"advice":"先检查运算顺序"}'}}]}
            ).encode("utf-8")

    store = MotherQuestionStore(root=tmp_path)
    store.create_mother(_attr_mother())
    monkeypatch.setattr(mother_router, "_store", lambda: store)
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _Cfg())
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp())

    result = asyncio.run(mother_router.attribute_wrong_reason("m1", payload={}, u=""))
    assert result["cached"] is False
    assert result["wrong_reason"] == "粗心"
    saved = store.get_mother("m1")
    assert saved.wrong_reason == "粗心"
    assert saved.wrong_advice == "先检查运算顺序"


def test_attribute_fallback_reason_for_unknown(tmp_path, monkeypatch):
    """LLM 返回非枚举类别 → 兜底为「其他」，保证 error-patterns 图表不脏。"""
    import json
    import urllib.request

    class _Cfg:
        api_key = "real-key"
        model = "deepseek"
        base_url = "http://localhost:9999/v1"

    class _Resp:
        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": '{"wrong_reason":"手滑了","confidence":0.5,"advice":"注意"}'}}]}
            ).encode("utf-8")

    store = MotherQuestionStore(root=tmp_path)
    store.create_mother(_attr_mother())
    monkeypatch.setattr(mother_router, "_store", lambda: store)
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _Cfg())
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp())

    result = asyncio.run(mother_router.attribute_wrong_reason("m1", payload={}, u=""))
    assert result["wrong_reason"] == "其他"
    assert store.get_mother("m1").wrong_reason == "其他"


def test_attribute_batch_skips_failed(tmp_path, monkeypatch):
    """批量归因：单个失败跳过，成功计数正确。"""
    import urllib.request

    class _Cfg:
        api_key = "real-key"
        model = "deepseek"
        base_url = "http://localhost:9999/v1"

    store = MotherQuestionStore(root=tmp_path)
    store.create_mother(_attr_mother("m1"))
    store.create_mother(_attr_mother("m2", wrong_reason="审题"))  # 已有错因，不进 pending
    store.create_mother(_attr_mother("m3"))
    monkeypatch.setattr(mother_router, "_store", lambda: store)
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _Cfg())
    # m3 的 LLM 返回非法 JSON → 单题失败跳过
    def _flaky(*a, **k):
        raise RuntimeError("llm down")
    monkeypatch.setattr(urllib.request, "urlopen", _flaky)

    result = asyncio.run(mother_router.attribute_batch(payload={"limit": 10}, u=""))
    assert result["pending"] == 2  # m1 + m3
    assert result["attributed"] == 0  # 全部失败跳过


# --------------------------------------------------------------------------- #
# 任务 5.3 表征补全：mother_question 全家端点 + image_pipeline                  #
# 全部离线（fake LLM / stub OCR）；isolated_data 把 PathService / multi_user    #
# 根整体重定向到 tmp —— 真实 data/ 零侧效（5.2 泄漏先例：llm_calls.jsonl 与     #
# learning trace 曾被既有用例写穿）。                                           #
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """重定向 PathService 默认实例 + multi_user 路径根到 tmp_path。

    覆盖面：母题存储 / 图片存储 / memory trace / L2L3 画像 / llm_calls.jsonl，
    全部随 get_path_service()（含 user_context 下的 H5 工作区）落 tmp。
    """
    from app.services.sishu_full.multi_user import paths as mu_paths
    from app.services.sishu_full.services import path_service as ps_mod

    data_root = tmp_path / "data"
    monkeypatch.setattr(mu_paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mu_paths, "ADMIN_WORKSPACE_ROOT", data_root)
    monkeypatch.setattr(mu_paths, "USER_SECRETS_DIRNAME", "user-secrets")
    monkeypatch.setattr(mu_paths, "USERS_ROOT", data_root / "users")
    monkeypatch.setattr(mu_paths, "SYSTEM_ROOT", data_root / "system")
    monkeypatch.setattr(mu_paths, "_path_services", {})

    admin_service = ps_mod.PathService(workspace_root=data_root)
    monkeypatch.setattr(ps_mod.PathService, "_instance", admin_service, raising=False)
    monkeypatch.setattr(
        ps_mod.PathService, "get_instance", classmethod(lambda cls: admin_service)
    )
    return data_root


def _mk_mother(mid: str, title: str = "应用题", text: str = "小明有 3 个苹果", **kw) -> MotherQuestion:
    return MotherQuestion(id=mid, title=title, question_text=text, **kw)


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(mother_router.router, prefix="/api/v1/mother-questions")
    return app


def _png_bytes(color=(255, 255, 255), size=(120, 120), draw_red: bool = False) -> bytes:
    img = Image.new("RGB", size, color)
    if draw_red:
        # 红笔细笔画（✓ 形）：detect_red_strokes 的面积窗 [30,3000]px 针对
        # 笔画设计，实心大色块（膨胀后 >3000px）按设计排除，不能用夹具画。
        draw = ImageDraw.Draw(img)
        draw.line([(30, 70), (52, 92), (90, 34)], fill=(200, 30, 30), width=5)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _llm_cfg(api_key: str = "real-key") -> SimpleNamespace:
    return SimpleNamespace(api_key=api_key, model="test-model", base_url="http://llm.test/v1")


class _FakeResp:
    """urlopen 替身：带 .read()（explain/generate/recognize/attribute 路径）。"""

    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class _FakeSSEResp:
    """urlopen 替身：可迭代行（ai_solve SSE 路径）。"""

    def __init__(self, lines: list[bytes]):
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)


def _llm_content_resp(content: str) -> _FakeResp:
    return _FakeResp({"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 3, "completion_tokens": 5}})


# ── 母题 CRUD：get / patch / 软删回收站恢复 / 硬删 ────────────────────────────

def test_router_get_404_unknown():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(mother_router.get_mother_question("ghost"))
    assert exc.value.status_code == 404


def test_router_update_patch_title_recomputes_simhash():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    # 空更新 -> 400；不存在 -> 404
    with pytest.raises(HTTPException) as empty:
        asyncio.run(mother_router.update_mother_question("m1", mother_router.UpdateMotherRequest()))
    assert empty.value.status_code == 400
    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.update_mother_question("ghost", mother_router.UpdateMotherRequest(title="x")))
    assert miss.value.status_code == 404

    out = asyncio.run(
        mother_router.update_mother_question("m1", mother_router.UpdateMotherRequest(title="新标题"))
    )
    assert out["title"] == "新标题"
    saved = store.get_mother("m1")
    assert saved.simhash == compute_simhash("新标题", saved.question_text)


def test_router_soft_delete_trash_restore_roundtrip():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    out = asyncio.run(mother_router.delete_mother_question("m1", hard=False, u="", code=""))
    assert out == {"deleted": True, "mode": "soft"}
    assert store.get_mother("m1").status == "deleted"

    trash = asyncio.run(mother_router.list_trash_static(page=1, page_size=20, u="", code=""))
    assert trash["total"] == 1 and trash["items"][0]["id"] == "m1"

    restored = asyncio.run(mother_router.restore_mother("m1", u="", code=""))
    assert restored == {"restored": True, "id": "m1"}
    assert store.get_mother("m1").status == "active"
    # 已不在回收站的题再恢复 -> 404
    with pytest.raises(HTTPException) as exc:
        asyncio.run(mother_router.restore_mother("m1", u="", code=""))
    assert exc.value.status_code == 404


def test_router_hard_delete_removes_entry():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    out = asyncio.run(mother_router.delete_mother_question("m1", hard=True, u="", code=""))
    assert out == {"deleted": True, "mode": "hard"}
    assert store.get_mother("m1") is None
    with pytest.raises(HTTPException) as exc:
        asyncio.run(mother_router.delete_mother_question("m1", hard=True, u="", code=""))
    assert exc.value.status_code == 404


# ── 变式题端点 ────────────────────────────────────────────────────────────────

def test_router_variant_crud_via_endpoints():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    with pytest.raises(HTTPException) as miss:
        asyncio.run(
            mother_router.create_variant("ghost", mother_router.CreateVariantRequest(question_text="x"))
        )
    assert miss.value.status_code == 404

    created = asyncio.run(
        mother_router.create_variant(
            "m1", mother_router.CreateVariantRequest(question_text="变式一", answer="6", difficulty=2)
        )
    )
    assert created["question_text"] == "变式一" and created["source"] == "manual"
    assert store.get_mother("m1").variant_count == 1

    listed = asyncio.run(mother_router.list_variants("m1", status="active"))
    assert [v["id"] for v in listed["items"]] == [created["id"]]

    patched = asyncio.run(
        mother_router.update_variant(created["id"], mother_router.UpdateVariantRequest(difficulty=4))
    )
    assert patched["difficulty"] == 4

    deleted = asyncio.run(mother_router.delete_variant(created["id"], hard=False))
    assert deleted == {"deleted": True, "mode": "soft"}
    assert store.get_mother("m1").variant_count == 0
    with pytest.raises(HTTPException) as gone:
        asyncio.run(mother_router.delete_variant("no-such", hard=False))
    assert gone.value.status_code == 404


# ── attempts（答题记录）端点 ─────────────────────────────────────────────────

def test_router_attempts_crud_and_accuracy():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.create_attempt("ghost", mother_router.CreateAttemptRequest(is_correct=True)))
    assert miss.value.status_code == 404

    a1 = asyncio.run(
        mother_router.create_attempt("m1", mother_router.CreateAttemptRequest(is_correct=True, user_answer="3"))
    )
    asyncio.run(
        mother_router.create_attempt("m1", mother_router.CreateAttemptRequest(is_correct=False, user_answer="4"))
    )
    listed = asyncio.run(mother_router.list_attempts("m1", limit=100, u="", code=""))
    assert listed["total"] == 2 and listed["correct"] == 1
    assert listed["accuracy"] == 0.5

    deleted = asyncio.run(mother_router.delete_attempt(a1["id"]))
    assert deleted == {"deleted": True}
    with pytest.raises(HTTPException) as gone:
        asyncio.run(mother_router.delete_attempt(a1["id"]))
    assert gone.value.status_code == 404


# ── 导出（docx 组卷）────────────────────────────────────────────────────────

def test_router_export_docx_with_ids():
    store = MotherQuestionStore()
    store.create_mother(
        _mk_mother("m1", text="小明有 3 个苹果", standard_answer="3", wrong_answer="4",
                   wrong_reason="审题", detailed_analysis="重新数一遍", key_points=["加减法"], difficulty=5)
    )
    store.create_mother(_mk_mother("m2", text="1+1=?", difficulty=1))

    with TestClient(_app()) as client:
        res = client.post(
            "/api/v1/mother-questions/export",
            json={"ids": ["m1", "m2"], "title": "错题组卷测试"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert "attachment" in res.headers["content-disposition"]
        assert "filename*=UTF-8''" in res.headers["content-disposition"]
        assert res.content[:2] == b"PK"  # docx = zip 容器

        empty = client.post("/api/v1/mother-questions/export", json={"ids": ["ghost"]})
        assert empty.status_code == 404


# ── simhash 查重：创建短路 / 查重端点 / 相似题 ───────────────────────────────

def test_router_create_duplicate_409_and_force_skips():
    body = {"title": "鸡兔同笼", "question_text": "鸡兔同笼，头 10 只脚 28 只，求各几只"}
    first = asyncio.run(mother_router.create_mother_question(mother_router.CreateMotherRequest(**body)))
    assert first["simhash"] is not None

    with pytest.raises(HTTPException) as dup:
        asyncio.run(mother_router.create_mother_question(mother_router.CreateMotherRequest(**body)))
    assert dup.value.status_code == 409
    assert "查重短路" in dup.value.detail

    forced = asyncio.run(
        mother_router.create_mother_question(mother_router.CreateMotherRequest(**body, force=True))
    )
    assert forced["id"] != first["id"]
    assert len(MotherQuestionStore().list_all_mothers()) == 2


def test_router_duplicate_check_endpoints_and_batch_save():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1", title="鸡兔同笼", text="鸡兔同笼，头 10 只脚 28 只，求各几只"))
    store.get_mother("m1").simhash = None

    probe = {"title": "鸡兔同笼", "question_text": "鸡兔同笼，头 10 只脚 28 只，求各几只"}
    # recompute_simhash 先给 m1 补哈希（find_duplicates 跳过 simhash 为 None 的题）
    rec = asyncio.run(mother_router.recompute_simhash("m1"))
    assert rec["simhash"] == compute_simhash(probe["title"], probe["question_text"])

    single = asyncio.run(mother_router.check_duplicate(mother_router.CheckDuplicateRequest(**probe)))
    assert single["count"] == 1 and single["duplicates"][0]["id"] == "m1"

    batch = asyncio.run(mother_router.batch_check_duplicate({
        "items": [probe, {"title": "几何", "question_text": "三角形的内角和是 180 度"}]
    }))
    assert batch["results"][0]["is_duplicate"] is True
    assert batch["results"][1]["is_duplicate"] is False

    preview = asyncio.run(mother_router.batch_preview({"items": [probe]}))
    assert preview["items"][0]["duplicate"] is True

    saved = asyncio.run(mother_router.batch_save_corrected({
        "items": [probe, {"title": "几何", "question_text": "三角形的内角和是 180 度"}],
        "force": False,
    }))
    assert saved["saved"] == 1 and len(saved["duplicates"]) == 1
    assert saved["duplicates"][0]["duplicates"][0]["id"] == "m1"

    forced = asyncio.run(mother_router.batch_save_corrected({
        "items": [probe], "force": True,
    }))
    assert forced["saved"] == 1 and forced["duplicates"] == []


def test_router_similar_finds_near_duplicate():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1", title="鸡兔同笼", text="鸡兔同笼，头 10 只脚 28 只"))
    m2 = _mk_mother("m2", title="鸡兔同笼", text="鸡兔同笼，头 10 只脚 28 只")
    m2.simhash = compute_simhash(m2.title, m2.question_text)
    store.create_mother(m2)

    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.find_similar("ghost", top_k=5))
    assert miss.value.status_code == 404

    out = asyncio.run(mother_router.find_similar("m1", top_k=5))
    assert out["engine"] == "simhash"
    assert [i["id"] for i in out["items"]] == ["m2"]
    assert out["items"][0]["distance"] == 0
    # m1 的 simhash 已被端点现场补算
    assert store.get_mother("m1").simhash is not None


# ── 复习调度：due / due_count / plan / submit（FSRS 四档 + legacy 二值）───────

def test_router_review_fsrs_flow_due_plan_submit_state_history_retention():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))

    due = asyncio.run(mother_router.reviews_due(max_items=20, u="", code=""))
    assert [m["id"] for m in due["items"]] == ["m1"]
    count_before = asyncio.run(mother_router.reviews_due_count(u="", code=""))["due_count"]
    assert count_before == 1

    plan_before = asyncio.run(mother_router.reviews_plan(max_items=20, u="", code=""))
    entry = plan_before["plan"][0]
    assert entry["id"] == "m1" and entry["next_review_at"] is None and entry["retention"] == 0

    res = asyncio.run(
        mother_router.review_submit("m1", mother_router.ReviewSubmitRequest(rating=3, user_answer="3"), u="", code="")
    )
    assert res["recorded"] is True and res["total_reviews"] == 1
    assert res["card"] is not None and res["card"]["reps"] == 1
    assert res["mastery_status"] == "reviewing"
    assert res["retention"] >= 0

    count_after = asyncio.run(mother_router.reviews_due_count(u="", code=""))["due_count"]
    assert count_after == count_before - 1  # rating=3 → due 推迟到未来

    state = asyncio.run(mother_router.review_state("m1", u="", code=""))
    assert state["card"]["reps"] == 1 and state["mastery_status"] == "reviewing"

    history = asyncio.run(mother_router.review_history("m1"))
    assert history["total"] == 1 and history["correct"] == 1 and history["accuracy"] == 1.0

    attempts = store.list_attempts("m1")
    assert attempts[0]["source"] == "review" and attempts[0]["rating"] == 3

    retention = asyncio.run(mother_router.retention_analysis_static(u="", code=""))
    assert retention["reviewed_count"] == 1 and retention["total_count"] == 1

    # plan = 到期清单（list_due 派生）：rating=3 提交后 m1 移出到期 -> plan 为空
    plan_after = asyncio.run(mother_router.reviews_plan(max_items=20, u="", code=""))
    assert plan_after == {"plan": [], "count": 0}
    # 下次复习时间钉在 FSRS 卡片 due 上（> now）
    state_after = asyncio.run(mother_router.review_state("m1", u="", code=""))
    assert state_after["card"]["due"] > time.time()


def test_router_review_legacy_binary_submit_and_validation():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))

    res = asyncio.run(
        mother_router.review_submit("m1", mother_router.ReviewSubmitRequest(is_correct=False), u="", code="")
    )
    assert res["recorded"] is True
    assert res["card"] is None  # legacy scheduler 状态无 stability → 不产 FSRS 卡片
    assert res["new_state"]["consecutive_correct"] == 0
    assert res["new_state"]["next_review_at"] > time.time()
    assert res["mastery_status"] == "reviewing"
    assert asyncio.run(mother_router.review_history("m1"))["correct"] == 0

    with pytest.raises(HTTPException) as empty:
        asyncio.run(mother_router.review_submit("m1", mother_router.ReviewSubmitRequest(), u="", code=""))
    assert empty.value.status_code == 400

    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.review_submit("ghost", mother_router.ReviewSubmitRequest(rating=2), u="", code=""))
    assert miss.value.status_code == 404


def test_router_review_next_404_and_random_pick():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))

    with pytest.raises(HTTPException) as none:
        asyncio.run(mother_router.review_next("m1", u="", code=""))
    assert none.value.status_code == 404

    store.create_variant(QuestionVariant(id="v1", mother_id="m1", question_text="变式题"))
    picked = asyncio.run(mother_router.review_next("m1", u="", code=""))
    assert picked["variant_id"] == "v1" and picked["question_text"] == "变式题"

    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.review_next("ghost", u="", code=""))
    assert miss.value.status_code == 404


# ── 状态转移：transfer-to-correct / -mastered / -active ──────────────────────

def test_router_status_transfer_endpoints():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    store.create_mother(_mk_mother("m2"))

    res = asyncio.run(mother_router.transfer_to_correct("m1"))
    assert res["transferred"] is True and res["correct_transferred_at"] is not None
    assert store.get_mother("m1").mastery_status == "mastered"
    correct = asyncio.run(mother_router.list_correct_questions(limit=100))
    assert [m["id"] for m in correct["items"]] == ["m1"]

    out = asyncio.run(mother_router.transfer_to_mastered("m2", u="", code=""))
    assert out["mastery_status"] == "mastered"
    back = asyncio.run(mother_router.transfer_to_active("m2", u="", code=""))
    assert back["mastery_status"] == "not_mastered"

    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.transfer_to_correct("ghost"))
    assert miss.value.status_code == 404


# ── 认领（admin -> H5 用户复制）──────────────────────────────────────────────

def test_router_claim_copies_mother_and_variants_to_h5_user():
    from app.services.sishu_full.multi_user.context import reset_current_user, set_current_user
    from app.services.sishu_full.multi_user.h5 import h5_user

    store = MotherQuestionStore()  # isolated_data 下 = tmp admin 工作区
    store.create_mother(_mk_mother("m1", title="鸡兔同笼"))
    store.create_variant(QuestionVariant(id="v1", mother_id="m1", question_text="变式题"))

    res = asyncio.run(mother_router.claim_mothers({"target_u": "小明", "mids": ["m1"]}, u=""))
    assert res == {"claimed": 1, "skipped_dup": 0, "target_u": "小明"}

    token = set_current_user(h5_user("小明"))
    try:
        dst = MotherQuestionStore()
        copied = dst.list_all_mothers()
        assert len(copied) == 1
        assert copied[0].id != "m1"                      # 新 id
        assert "claimed:m1" in copied[0].tags            # 认领标记
        assert copied[0].title == "鸡兔同笼"
        assert "h5_小明" in str(dst._root)               # 落在 H5 用户工作区
        variants = dst.list_variants(copied[0].id)
        assert len(variants) == 1 and variants[0].mother_id == copied[0].id
    finally:
        reset_current_user(token)
    # admin 侧原件不动
    assert store.get_mother("m1") is not None

    # 重复认领 -> 判重跳过
    again = asyncio.run(mother_router.claim_mothers({"target_u": "小明", "mids": ["m1"]}, u=""))
    assert again["claimed"] == 0 and again["skipped_dup"] == 1

    # 孩子不能自己认领 -> 403；缺 target_u -> 400；找不到母题 -> 404
    with pytest.raises(HTTPException) as forbidden:
        asyncio.run(mother_router.claim_mothers({"target_u": "小红"}, u="小明"))
    assert forbidden.value.status_code == 403
    with pytest.raises(HTTPException) as bad:
        asyncio.run(mother_router.claim_mothers({"mids": ["m1"]}, u=""))
    assert bad.value.status_code == 400
    with pytest.raises(HTTPException) as none:
        asyncio.run(mother_router.claim_mothers({"target_u": "小红", "mids": ["ghost"]}, u=""))
    assert none.value.status_code == 404


# ── LLM 家族：generate_variants / explain / ai_solve ─────────────────────────

def test_router_generate_variants_503_unconfigured_and_404():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.generate_variants("ghost", payload={}))
    assert miss.value.status_code == 404

    import app.services.sishu_full.services.llm.config as llm_config
    monkeypatch_target = "app.services.sishu_full.services.llm.config.get_llm_config"
    from unittest.mock import patch

    with patch.object(llm_config, "get_llm_config", lambda: _llm_cfg("sk-placeholder"), create=True):
        with pytest.raises(HTTPException) as unconf:
            asyncio.run(mother_router.generate_variants("m1", payload={}))
    assert unconf.value.status_code == 503
    del monkeypatch_target


def test_router_generate_variants_llm_creates_variants(monkeypatch):
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _llm_cfg())
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _llm_content_resp(
            '[{"question_text":"变式一","answer":"6","difficulty":2,"variant_type":"数值变式"},'
            '{"question_text":"变式二","answer":"7","difficulty":3,"variant_type":"情境变式"}]'
        ),
    )
    out = asyncio.run(mother_router.generate_variants("m1", payload={"count": 2}))
    assert out["generated"] == 2
    assert all(v["source"] == "llm_gen" for v in out["items"])
    assert store.get_mother("m1").variant_count == 2


def test_router_explain_fallback_when_llm_unconfigured():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1", standard_answer="3"))
    from unittest.mock import patch
    import app.services.sishu_full.services.llm.config as llm_config

    with patch.object(llm_config, "get_llm_config", lambda: _llm_cfg("sk-placeholder"), create=True):
        out = asyncio.run(mother_router.explain("m1", u="", code=""))
    assert out["fallback"] is True
    assert out["explain"] == "3"
    assert out["rag_used"] is False  # KB 不存在 → RAG 降级

    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.explain("ghost", u="", code=""))
    assert miss.value.status_code == 404


def test_router_explain_llm_success(monkeypatch):
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1", standard_answer="3"))
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _llm_cfg())
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _llm_content_resp("先数苹果，再做减法。"))
    out = asyncio.run(mother_router.explain("m1", u="", code=""))
    assert out["fallback"] is False
    assert out["explain"] == "先数苹果，再做减法。"
    assert out["rag_used"] is False


def test_router_ai_solve_404_and_unconfigured_stream():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    from unittest.mock import patch
    import app.services.sishu_full.services.llm.config as llm_config

    with TestClient(_app()) as client:
        assert client.post("/api/v1/mother-questions/ghost/ai_solve").status_code == 404
        with patch.object(llm_config, "get_llm_config", lambda: _llm_cfg("sk-placeholder"), create=True):
            res = client.post("/api/v1/mother-questions/m1/ai_solve")
        assert res.status_code == 200
        assert res.text == "LLM key 未配置，无法使用 AI 解题。"


def test_router_ai_solve_streams_sse_chunks(monkeypatch):
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _llm_cfg())
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeSSEResp([
            'data: {"choices":[{"delta":{}}],"usage":{"total_tokens":7}}\n\n'.encode("utf-8"),
            'data: {"choices":[{"delta":{"content":"步骤一"}}]}\n\n'.encode("utf-8"),
            'data: {"choices":[{"delta":{"content":"步骤二"}}]}\n\n'.encode("utf-8"),
            b"data: [DONE]\n\n",
        ]),
    )
    with TestClient(_app()) as client:
        res = client.post("/api/v1/mother-questions/m1/ai_solve")
    assert res.status_code == 200
    assert res.text == "步骤一步骤二"  # [DONE] 截断，usage 块不产文本


# ── recognize_text（P0-1 AI 智能填充 + WQ1 门禁语义）─────────────────────────

def test_recognize_text_400_without_inputs():
    with pytest.raises(HTTPException) as empty:
        asyncio.run(mother_router.recognize_text({}, u="", code=""))
    assert empty.value.status_code == 400


def test_recognize_text_extracts_fields_for_h5_user(monkeypatch):
    """带 u 的字段提取：先过 h5_user_guarded（未配码放行），再走 LLM 抽字段。"""
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _llm_cfg())
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _llm_content_resp(
            '好的，抽取结果：{"title":"加法题","question_text":"1+1=?","standard_answer":"2",'
            '"key_points":["加法"],"wrong_reason":"计算错误","difficulty":1}'
        ),
    )
    out = asyncio.run(
        mother_router.recognize_text(
            {"text": "1+1=?", "wrong_answer": "3", "title": "加法"}, u="小明", code=""
        )
    )
    assert out["fallback"] is False
    assert out["fields"]["title"] == "加法题"
    assert out["fields"]["standard_answer"] == "2"
    assert out["fields"]["wrong_reason"] == "计算错误"


def test_recognize_text_normalizes_steps_and_synthesizes_analysis(monkeypatch):
    """2026-09-26 用户需求：AI 填充必须给详细解题过程——
    solution_steps 数组拍平为「每行一步」字符串；detailed_analysis 缺省时从步骤合成。"""
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _llm_cfg())
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _llm_content_resp(
            '{"title":"面积题","question_text":"长3宽2的长方形面积？","standard_answer":"6",'
            '"solution_steps":[{"step":1,"text":"识别长方形面积公式 S=长×宽"},'
            '{"step":2,"text":"代入 3×2=6"}],"wrong_reason":"知识点缺失","difficulty":2}'
        ),
    )
    out = asyncio.run(
        mother_router.recognize_text({"text": "长3宽2的长方形面积？"}, u="小明", code="")
    )
    f = out["fields"]
    assert f["solution_steps"] == "1. 识别长方形面积公式 S=长×宽\n2. 代入 3×2=6"
    assert "1. 识别长方形面积公式" in f["detailed_analysis"]  # 缺省时从步骤合成，不为空


def test_normalize_recognize_fields_pure():
    """归一化纯函数：字符串 steps 原样透传；空 steps 不合成详解。"""
    norm = mother_router._normalize_recognize_fields
    out = norm({"solution_steps": "1. 已就绪", "detailed_analysis": "既有详解"})
    assert out["solution_steps"] == "1. 已就绪"
    assert out["detailed_analysis"] == "既有详解"
    out2 = norm({"solution_steps": []})
    assert out2["solution_steps"] == ""
    assert not out2.get("detailed_analysis")


# ── 批量 OCR 管线（router 层，stub 引擎）────────────────────────────────────

def test_router_batch_recognize_uses_pipeline(monkeypatch):
    from app.services.sishu_full.learning import image_pipeline as ip

    monkeypatch.setattr(ip, "ocr_image", lambda raw: {"text": "1+1=?"})
    monkeypatch.setattr(
        ip, "ocr_image",
        lambda raw: (_ for _ in ()).throw(RuntimeError("no engine")) if raw == b"bad" else {"text": "1+1=?"},
    )
    with TestClient(_app()) as client:
        res = client.post(
            "/api/v1/mother-questions/batch_recognize",
            files=[
                ("files", ("a.png", _png_bytes(), "image/png")),
                ("files", ("bad.png", b"bad", "image/png")),
            ],
        )
    assert res.status_code == 200
    items = res.json()["items"]
    assert items[0]["ok"] is True and items[0]["text"] == "1+1=?"
    assert items[1]["ok"] is False and "no engine" in items[1]["error"]


def test_router_ocr_upload_success_and_engine_failure(monkeypatch):
    from app.services.sishu_full.learning import image_pipeline as ip

    png = _png_bytes()
    monkeypatch.setattr(
        ip, "ocr_image",
        lambda raw: {"text": "1+1=?", "lines": [{"text": "1+1=?", "bbox": [0, 0, 9, 9], "conf": 0.9}]},
    )
    with TestClient(_app()) as client:
        ok = client.post("/api/v1/mother-questions/ocr-upload", files={"file": ("p.png", png, "image/png")})
        assert ok.status_code == 200
        body = ok.json()
        assert body["text"] == "1+1=?" and body["line_count"] == 1
        assert body["photo_url"].startswith("/api/v1/mother-questions/files/originals/")
        assert body["thumbnail"].startswith("data:image/jpeg;base64,")

        monkeypatch.setattr(ip, "ocr_image", lambda raw: (_ for _ in ()).throw(RuntimeError("engine missing")))
        degraded = client.post("/api/v1/mother-questions/ocr-upload", files={"file": ("p.png", png, "image/png")})
        assert degraded.status_code == 503
        assert "OCR 识别失败" in degraded.json()["msg"]
        assert degraded.json()["photo_url"].startswith("/api/v1/mother-questions/files/")

        empty = client.post("/api/v1/mother-questions/ocr-upload", files={"file": ("p.png", b"", "image/png")})
        assert empty.status_code == 400


def test_router_recognize_endpoint_degrades_and_extracts(monkeypatch):
    from app.services.sishu_full.learning import image_pipeline as ip

    png = _png_bytes()
    monkeypatch.setattr(ip, "ocr_image", lambda raw: {"text": "2+2=?", "lines": []})

    with TestClient(_app()) as client:
        from unittest.mock import patch
        import app.services.sishu_full.services.llm.config as llm_config

        # LLM 未配置 → 降级返回 OCR 原文
        with patch.object(llm_config, "get_llm_config", lambda: _llm_cfg("sk-placeholder"), create=True):
            degraded = client.post("/api/v1/mother-questions/recognize", files={"file": ("p.png", png, "image/png")})
        assert degraded.status_code == 200
        body = degraded.json()
        assert body["ocr_text"] == "2+2=?" and body["fields"] == {}
        assert "LLM key 未配置" in body["msg"]

        # LLM 正常 → 结构化字段
        monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _llm_cfg())
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *a, **k: _llm_content_resp('{"title":"加法","question_text":"2+2=?","standard_answer":"4"}'),
        )
        good = client.post("/api/v1/mother-questions/recognize", files={"file": ("p.png", png, "image/png")})
        assert good.status_code == 200
        assert good.json()["fields"]["standard_answer"] == "4"
        assert good.json()["fallback"] is False


def test_router_batch_recognize_all_and_detect_red_mark(monkeypatch):
    from app.services.sishu_full.learning import image_pipeline as ip

    monkeypatch.setattr(
        ip, "split_questions",
        lambda raw: [{"qno": "1.", "text": "1+1=?", "bbox": [0, 0, 50, 50], "thumbnail": "data:image/jpeg;base64,xx", "crop_url": None}],
    )
    monkeypatch.setattr(ip, "detect_red_strokes", lambda raw: True)
    with TestClient(_app()) as client:
        res = client.post(
            "/api/v1/mother-questions/batch_recognize_all", files={"file": ("page.png", _png_bytes(), "image/png")}
        )
        assert res.status_code == 200
        body = res.json()
        assert body["question_count"] == 1 and body["has_checkmark"] is True
        assert body["source_image_url"].startswith("/api/v1/mother-questions/files/originals/")

        empty = client.post(
            "/api/v1/mother-questions/batch_recognize_all", files={"file": ("page.png", b"", "image/png")}
        )
        assert empty.status_code == 400


def test_router_detect_red_mark_real_cv2():
    """detect_red_strokes 真实现（cv2 已装）：白图无标记，红圈判 True。"""
    with TestClient(_app()) as client:
        white = client.post("/api/v1/mother-questions/detect_red_mark", files={"file": ("w.png", _png_bytes(), "image/png")})
        assert white.status_code == 200
        assert white.json()["has_checkmark"] is False

        red = client.post(
            "/api/v1/mother-questions/detect_red_mark",
            files={"file": ("r.png", _png_bytes(draw_red=True), "image/png")},
        )
        assert red.status_code == 200
        assert red.json()["has_checkmark"] is True


def test_router_upload_image_saves_file():
    with TestClient(_app()) as client:
        res = client.post("/api/v1/mother-questions/upload_image", files={"file": ("p.png", _png_bytes(), "image/png")})
        assert res.status_code == 200
        url = res.json()["url"]
        assert url.startswith("/api/v1/mother-questions/files/single_q/")
        path = resolve_url_to_path(url)
        assert path is not None and path.exists()

        empty = client.post("/api/v1/mother-questions/upload_image", files={"file": ("p.png", b"", "image/png")})
        assert empty.status_code == 400


# ── 分析聚合 / 知识点汇总 / 单题统计 / 字典 ──────────────────────────────────

def test_router_analysis_aggregations():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1", text="A", subject="math", knowledge_point_id="kp1",
                                   wrong_reason="审题", mastery_status="mastered", difficulty=5))
    store.create_mother(_mk_mother("m2", text="B", subject="math", difficulty=2))
    store.create_mother(_mk_mother("m3", text="C", subject="chinese", knowledge_point_id="kp1"))

    by_subject = asyncio.run(mother_router.by_subject_stats_static())
    math_row = next(r for r in by_subject["items"] if r["subject"] == "math")
    assert math_row["count"] == 2 and math_row["mastered"] == 1
    assert by_subject["total_subjects"] == 2

    stats = asyncio.run(mother_router.comprehensive_stats(u="", code=""))
    assert stats["total"] == 3
    assert stats["by_status"] == {"mastered": 1, "not_mastered": 2}
    assert stats["by_difficulty"] == {5: 1, 2: 1, 3: 1}

    patterns = asyncio.run(mother_router.error_patterns(u="", code=""))
    assert patterns["patterns"] == [{"reason": "审题", "count": 1}]

    weak = asyncio.run(mother_router.weak_points(u="", code=""))
    assert weak["weak_points"][0] == {"knowledge_point_id": "kp1", "mother_count": 2}

    trend = asyncio.run(mother_router.trends(days=30, u="", code=""))
    assert trend["days"] == 30 and sum(t["count"] for t in trend["trends"]) == 3


def test_router_kp_summary_stats_context_and_dict():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1", text="A", knowledge_point_id="kp1"))
    store.create_variant(QuestionVariant(id="v1", mother_id="m1", question_text="变式"))

    summary = asyncio.run(mother_router.by_knowledge_point())
    assert summary["total_kps"] == 1
    assert summary["items"][0] == {"knowledge_point_id": "kp1", "mother_count": 1, "variant_count": 1}

    stats = asyncio.run(mother_router.mother_question_stats("m1"))
    assert stats["variant_count"] == 1 and stats["attempt_count"] == 0
    assert stats["accuracy"] is None and stats["mastery_status"] == "not_mastered"

    ctx = asyncio.run(mother_router.mother_question_context("m1"))
    assert ctx["id"] == "m1" and ctx["textbook"] is None and ctx["knowledge_point"] is None

    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.mother_question_stats("ghost"))
    assert miss.value.status_code == 404

    dic = asyncio.run(mother_router.get_dictionary())
    assert set(dic.keys()) == {"textbooks", "chapters", "knowledge_points", "tags", "subjects"}
    assert "math" in dic["subjects"]


# ── 标签 / 多图资产（P1-7 / P1-9）───────────────────────────────────────────

def test_router_tags_and_assets_lifecycle():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))

    tag = asyncio.run(mother_router.create_tag(mother_router.CreateTagRequest(name="几何", color="#ff0000")))
    assert tag == {"id": "几何", "name": "几何", "color": "#ff0000"}

    listed = asyncio.run(mother_router.list_tags_static())
    assert {"id": "几何", "name": "几何", "color": "#ff0000"} in listed["items"]

    store.update_mother("m1", {"tags": ["几何"]})
    removed = asyncio.run(mother_router.delete_tag("几何"))
    assert removed == {"deleted": True, "name": "几何"}
    assert store.get_mother("m1").tags == []  # 删标签同步从母题移除

    asset = asyncio.run(
        mother_router.add_asset("m1", mother_router.AddAssetRequest(url="/f/a.png", asset_type="photo", ocr_text="1+1"))
    )
    assert asset["url"] == "/f/a.png"
    got = asyncio.run(mother_router.list_assets("m1"))
    assert got["total"] == 1 and got["items"][0]["type"] == "photo"

    gone = asyncio.run(mother_router.remove_asset("m1", url="/f/a.png"))
    assert gone == {"deleted": True}
    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.remove_asset("m1", url="/f/none.png"))
    assert miss.value.status_code == 404


# ── image_pipeline 单元（真实 PIL/cv2，无网络）───────────────────────────────

def test_image_pipeline_save_upload_normalizes_ext():
    url_jpg = save_upload(b"aaa", ext="jpeg", subdir="u1")
    assert url_jpg.endswith(".jpg") and url_jpg.startswith("/api/v1/mother-questions/files/u1/")
    url_default = save_upload(b"bbb", ext="exe", subdir="u1")
    assert url_default.endswith(".jpg")
    path = resolve_url_to_path(url_jpg)
    assert path is not None and path.read_bytes() == b"aaa"


def test_image_pipeline_resolve_url_rejects_external():
    assert resolve_url_to_path("") is None
    assert resolve_url_to_path("https://cdn.example.com/a.png") is None


def test_image_pipeline_make_thumbnail_handles_rgba():
    img = Image.new("RGBA", (100, 80), (0, 255, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    thumb = make_thumbnail(buf.getvalue(), max_size=50)
    assert thumb.startswith("data:image/jpeg;base64,")
    assert len(thumb) < 20000


def test_image_pipeline_crop_by_bbox_rejects_small_region():
    png = _png_bytes()
    with pytest.raises(ValueError) as small:
        crop_by_bbox(png, [0, 0, 30, 30])
    assert "too small" in str(small.value)
    crop, thumb = crop_by_bbox(png, [0, 0, 100, 100])
    assert crop[:2] == b"\xff\xd8"  # JPEG SOI
    assert thumb.startswith("data:image/jpeg;base64,")


def test_image_pipeline_detect_red_strokes_real():
    assert detect_red_strokes(_png_bytes()) is False
    assert detect_red_strokes(_png_bytes(draw_red=True)) is True
    assert detect_red_strokes(b"not-an-image") is False  # imdecode 失败安全降级


def test_image_pipeline_split_questions_segments_and_fallback(monkeypatch):
    from app.services.sishu_full.learning import image_pipeline as ip

    lines = [
        {"text": "1. 甲", "bbox": [10, 10, 80, 30]},
        {"text": "解：略", "bbox": [10, 34, 80, 50]},
        {"text": "2. 乙", "bbox": [10, 60, 80, 80]},
    ]
    monkeypatch.setattr(ip, "ocr_image", lambda raw: {"text": "\n".join(l["text"] for l in lines), "lines": lines})
    questions = split_questions(_png_bytes(size=(120, 120)))
    assert len(questions) == 2
    assert questions[0]["qno"] == "1. 甲" and questions[1]["qno"] == "2. 乙"  # qno=首行整行（前端 title 兜底用）
    assert questions[0]["text"] == "1. 甲\n解：略"
    assert questions[0]["bbox"][0] == 0 and questions[0]["crop_url"] is not None

    # 无题号 → 整页单题兜底
    monkeypatch.setattr(ip, "ocr_image", lambda raw: {"text": "没有题号的文本", "lines": [{"text": "没有题号的文本", "bbox": [0, 0, 60, 20]}]})
    whole = split_questions(_png_bytes(size=(120, 120)))
    assert len(whole) == 1 and whole[0]["qno"] is None and whole[0]["bbox"] == [0, 0, 120, 120]

    # OCR 无行 → 空列表
    monkeypatch.setattr(ip, "ocr_image", lambda raw: {"text": "", "lines": []})
    assert split_questions(_png_bytes()) == []


# ── 5.3 覆盖审计补全：以下端点此前零覆盖 ─────────────────────────────────────
# GET ""（列表过滤/排序/分页）、GET /{mid} 成功路径、PATCH /{mid}/note、
# lectures 关联/取消、knowledge-points/seed、knowledge-points/auto-build、
# chapters/auto-build、textbooks/import、export 无 ids 过滤分支、
# image_pipeline.ocr_image 的 box→bbox 归一化。

def test_router_list_mothers_filters_sort_pagination():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("a1", title="alpha", text="apple basket", subject="math", difficulty=5, tags=["几何"]))
    store.create_mother(_mk_mother("a2", title="beta", text="banana boat", subject="math", difficulty=2))
    store.create_mother(_mk_mother("a3", title="gamma", text="chinese poem", subject="chinese", difficulty=3))

    # page/page_size 是 Query 默认对象，直接调用需显式传 int（HTTP 层由 FastAPI 注入）
    def _list(**kw):
        kw.setdefault("page", 1)
        kw.setdefault("page_size", 20)
        return asyncio.run(
            mother_router.list_mother_questions(u="", code="", x_access_code="", **kw)
        )

    full = _list()
    assert full["total"] == 3
    assert {i["id"] for i in full["items"]} == {"a1", "a2", "a3"}
    assert full["page"] == 1 and full["page_size"] == 20

    assert _list(subject="math")["total"] == 2
    assert _list(difficulty_min=4)["total"] == 1
    assert _list(difficulty_max=2)["total"] == 1
    assert _list(tag="几何")["total"] == 1
    assert _list(keyword="banana")["total"] == 1

    # 软删后离开 active 列表、进入 status=deleted 检索
    store.delete_mother("a3", hard=False)
    assert _list()["total"] == 2
    deleted = _list(status="deleted")
    assert deleted["total"] == 1 and deleted["items"][0]["id"] == "a3"

    # 排序 + 分页（title asc：alpha, beta, gamma → 第 2 页 1 条 = beta）
    paged = _list(sort_by="title", sort_order="asc", page=2, page_size=1)
    assert [i["id"] for i in paged["items"]] == ["a2"]


def test_router_get_mother_success_embeds_variants():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    store.create_variant(QuestionVariant(id="v1", mother_id="m1", question_text="变式"))
    out = asyncio.run(mother_router.get_mother_question("m1"))
    assert out["id"] == "m1" and out["title"] == "应用题"
    assert [v["id"] for v in out["variants"]] == ["v1"]


def test_router_note_patch_strips_and_404():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    out = asyncio.run(mother_router.update_note("m1", {"note": "  先圈条件  "}))
    assert out == {"note": "先圈条件"}
    assert store.get_mother("m1").note == "先圈条件"
    # 空体 -> 清空笔记
    assert asyncio.run(mother_router.update_note("m1", {})) == {"note": ""}
    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.update_note("ghost", {"note": "x"}))
    assert miss.value.status_code == 404


def test_router_lecture_link_unlink_idempotent():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1"))
    linked = asyncio.run(mother_router.link_lecture("m1", "doc-1"))
    assert linked == {"linked": True, "related_lecture_doc_ids": ["doc-1"]}
    # 重复关联幂等
    again = asyncio.run(mother_router.link_lecture("m1", "doc-1"))
    assert again["related_lecture_doc_ids"] == ["doc-1"]
    asyncio.run(mother_router.link_lecture("m1", "doc-2"))
    unlinked = asyncio.run(mother_router.unlink_lecture("m1", "doc-1"))
    assert unlinked == {"unlinked": True, "related_lecture_doc_ids": ["doc-2"]}
    assert store.get_mother("m1").related_lecture_doc_ids == ["doc-2"]
    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.link_lecture("ghost", "doc-1"))
    assert miss.value.status_code == 404


def test_router_seed_knowledge_points_idempotent():
    from app.services.sishu_full.learning.curriculum import CurriculumStore

    first = asyncio.run(mother_router.seed_knowledge_points())
    assert first["total"] == 31 and first["seeded"] == 31
    assert len(CurriculumStore().list_kps()) == 31
    second = asyncio.run(mother_router.seed_knowledge_points())
    assert second["seeded"] == 0 and second["total"] == 31


def test_router_auto_build_knowledge_tree_gates_and_llm(monkeypatch):
    from app.services.sishu_full.learning.curriculum import CurriculumStore
    from unittest.mock import patch
    import app.services.sishu_full.services.llm.config as llm_config

    # 空库 -> 400
    with pytest.raises(HTTPException) as empty:
        asyncio.run(mother_router.auto_build_knowledge_tree())
    assert empty.value.status_code == 400

    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1", title="圆柱体积"))

    # LLM 未配置 -> 503
    with patch.object(llm_config, "get_llm_config", lambda: _llm_cfg("sk-placeholder"), create=True):
        with pytest.raises(HTTPException) as unconf:
            asyncio.run(mother_router.auto_build_knowledge_tree())
    assert unconf.value.status_code == 503

    # LLM 返回 KP 数组 -> 落库
    monkeypatch.setattr("app.services.sishu_full.services.llm.config.get_llm_config", lambda: _llm_cfg())
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _llm_content_resp('[{"grade":"六年级","name":"圆柱体积","description":"d"}]'),
    )
    out = asyncio.run(mother_router.auto_build_knowledge_tree())
    assert out == {"created": ["圆柱体积"], "count": 1}
    assert "圆柱体积" in {k.name for k in CurriculumStore().list_kps()}


def test_router_chapters_auto_build_standard_and_404():
    from app.services.sishu_full.learning.curriculum import CurriculumStore, Textbook

    cs = CurriculumStore()
    cs.create_textbook(Textbook(id="tb-5", name="五年级数学", grade="五年级", subject="math"))
    out = asyncio.run(mother_router.auto_build_chapters("tb-5"))
    assert out["count"] == 6
    assert out["created"][0] == "一、小数乘法" and out["created"][-1] == "六、多边形的面积"
    assert len(cs.list_chapters("tb-5")) == 6
    # 幂等：第二次不再创建
    assert asyncio.run(mother_router.auto_build_chapters("tb-5"))["count"] == 0
    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.auto_build_chapters("ghost"))
    assert miss.value.status_code == 404


def _upload(name: str, data: bytes):
    from fastapi import UploadFile

    return UploadFile(file=io.BytesIO(data), filename=name)


def test_router_textbook_import_404_empty_and_503(monkeypatch):
    import sys as _sys
    from app.services.sishu_full.learning.curriculum import CurriculumStore, Textbook

    CurriculumStore().create_textbook(Textbook(id="tb-p", name="导入教材", grade="五年级", subject="math"))
    with pytest.raises(HTTPException) as miss:
        asyncio.run(mother_router.import_textbook("ghost", _upload("t.pdf", b"x")))
    assert miss.value.status_code == 404
    with pytest.raises(HTTPException) as empty:
        asyncio.run(mother_router.import_textbook("tb-p", _upload("t.pdf", b"")))
    assert empty.value.status_code == 400
    # PyMuPDF 缺失 -> 503（sys.modules 塞 None 模拟 ImportError）
    monkeypatch.setitem(_sys.modules, "fitz", None)
    with pytest.raises(HTTPException) as unconf:
        asyncio.run(mother_router.import_textbook("tb-p", _upload("t.pdf", b"not-a-pdf")))
    assert unconf.value.status_code == 503


def test_router_textbook_import_pdf_renders_pages(monkeypatch):
    import fitz
    from app.services.sishu_full.learning import image_pipeline as ip
    from app.services.sishu_full.learning.curriculum import CurriculumStore, Textbook

    CurriculumStore().create_textbook(Textbook(id="tb-2", name="导入二", grade="五年级", subject="math"))
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    # stub OCR：本地 from-import 在调用时解析，monkeypatch 模块属性即可拦住
    monkeypatch.setattr(ip, "ocr_image", lambda raw: {"text": "1+1=?"})
    out = asyncio.run(mother_router.import_textbook("tb-2", _upload("t.pdf", pdf_bytes)))
    assert out["page_count"] == 1
    assert out["pages"][0]["page_num"] == 1 and out["pages"][0]["ocr_text"] == "1+1=?"
    assert out["pages"][0]["image_url"].startswith("/api/v1/mother-questions/files/textbooks/tb-2/")
    assert len(CurriculumStore().list_pages("tb-2")) == 1


def test_router_export_docx_filter_and_student_version():
    store = MotherQuestionStore()
    store.create_mother(_mk_mother("m1", text="math q", subject="math", difficulty=5))
    with TestClient(_app()) as client:
        # 无 ids 时走 subject/难度过滤：chinese 过滤掉全部 -> 404
        none = client.post("/api/v1/mother-questions/export", json={"subject": "chinese"})
        assert none.status_code == 404
        # 学生练习版（with_answer=False，无答案留空行）
        ok = client.post(
            "/api/v1/mother-questions/export", json={"with_answer": False, "title": "练习卷"}
        )
        assert ok.status_code == 200
        assert ok.content[:2] == b"PK"


def test_image_pipeline_ocr_image_normalizes_boxes(monkeypatch):
    from app.services.sishu_full.learning import image_pipeline as ip

    class _Engine:
        def __call__(self, arr):
            return ([([[0, 2], [10, 2], [10, 7], [0, 7]], "1+1=?", 0.987)], None)

    monkeypatch.setattr(ip, "_ocr_engine", _Engine())
    out = ip.ocr_image(_png_bytes())
    assert out["text"] == "1+1=?"
    assert out["lines"][0]["bbox"] == [0, 2, 10, 7]  # 4 点框 → [x1,y1,x2,y2]
    assert out["lines"][0]["conf"] == 0.987

    # 空结果分支
    monkeypatch.setattr(ip, "_ocr_engine", lambda arr: (None, None))
    assert ip.ocr_image(_png_bytes()) == {"text": "", "lines": [], "raw": []}

