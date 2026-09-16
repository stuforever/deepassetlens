"""RecitationStore（M25 T10）+ recite 四端点（M25 T11）测试。

T10 存储层：
- per-u 物理隔离：两个 h5 u 各自 workspace 下的 recitation/attempts.json，
  互不可见（路径级隔离，铁律 1）
- 记录 schema 钉死 = 规格 §4.5 十四字段（id/ts/u/textbook_id/chapter_id/
  material_id/material_title/mode/input_mode/segmented/total_score/
  per_segment/wrong_chars/homophones）
- partial attempt（segmented=true 未完成态）可留档（规格 §4.8）
- list_attempts(u, chapter_id) 返回最近 50 条倒序 + 文件级 50 条截断

T11 端点层（规格 §4.6，materials / check / attempts POST+GET）：
- 全带 u 门禁：带 u 无码 → 401（蓝本 test_access_code_gate.R1-c，逐端点钉）
- materials：glob workspace/*/grade*_index.json 读 recite_materials 键
  （无键=空列表，七年级自然为空）按 chapter_ids 过滤
- check：零 LLM 纯算法（check_segment 逐段 + 总分，验收判例 7/10）
- attempts POST：store 留档 + L1 事件 recitation_completed
  （learner_profile L608 契约）且 FSRS 隔离（reviews 队列不变——判例 9）
- attempts GET：最近 50 条倒序 + chapter_id 过滤

蓝本 = tests/capabilities/test_wrong_intake.py 的 mu_isolated_root +
set_current_user(h5_user(...)) 形态：per-u path_service 重根 tmp_path，
零真实 data/ 写入（铁律 2）。
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import HTTPException

# 零 LLM 断言的 provider 入口（module 顶层 import：llm.factory 导入链在
# import 期经 path_service 构造只读路径，须在 recite_ws 补丁生效前的收集期
# 完成——函数内 import 会撞上 _FakeRecitePathService 的形态缺口）。
import deeptutor.services.llm.factory as llm_factory  # noqa: E402

# mu_isolated_root 照 tests/capabilities/conftest.py 同款转出（重绑
# multi_user 全局路径至 tmp_path 并清 _path_services 缓存）。
from tests.multi_user.conftest import mu_isolated_root  # noqa: F401


def _h5(slug: str):
    from deeptutor.multi_user.context import set_current_user
    from deeptutor.multi_user.h5 import h5_user

    return set_current_user(h5_user(slug))


def _record(store, *, ts: float = 1000.0, **overrides):
    """规格 §4.5 全字段入参的最简 attempt（各用例按需覆盖）。

    ts 显式传参：倒序/截断断言不依赖时钟分辨率。
    """
    kwargs = dict(
        u="小明",
        textbook_id="tb_bnu_math_3a",
        chapter_id="u1",
        material_id="mat_001",
        material_title="大青树下的小学",
        mode="recite",
        input_mode="voice",
        segmented=True,
        total_score=1.0,
        per_segment=[{"idx": 0, "score": 1.0}],
        wrong_chars=[],
        homophones=[],
        ts=ts,
    )
    kwargs.update(overrides)
    return store.record(**kwargs)


def _attempts_file(slug: str):
    """该 h5 u 的 attempts.json 物理路径（get_workspace_dir 布局）。"""
    from deeptutor.multi_user import paths as mu_paths
    from deeptutor.multi_user.h5 import h5_user_id

    return (
        mu_paths.USERS_ROOT
        / h5_user_id(slug)
        / "user"
        / "workspace"
        / "recitation"
        / "attempts.json"
    )


# ---------------------------------------------------------------------------
# schema：记录 = 规格 §4.5 十四字段，一字段不多不少
# ---------------------------------------------------------------------------


def test_attempt_schema_pins_spec_fields(mu_isolated_root) -> None:
    """记录 schema 钉死规格 §4.5：十四字段 + 字段语义逐一对账。"""
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.context import reset_current_user

    token = _h5("小明")
    try:
        att = _record(RecitationStore(), ts=1700000000.0)
        # 恰好十四字段（顺序不敏感）
        assert set(att.model_dump().keys()) == {
            "id", "ts", "u", "textbook_id", "chapter_id", "material_id",
            "material_title", "mode", "input_mode", "segmented",
            "total_score", "per_segment", "wrong_chars", "homophones",
        }
        assert att.id  # uuid hex
        assert att.ts == 1700000000.0
        assert att.u == "小明"
        assert att.textbook_id == "tb_bnu_math_3a"
        assert att.chapter_id == "u1"
        assert att.material_id == "mat_001"
        assert att.material_title == "大青树下的小学"
        assert att.mode == "recite"          # recite|dictation
        assert att.input_mode == "voice"     # voice|type
        assert att.segmented is True
        assert att.total_score == 1.0
        assert att.per_segment == [{"idx": 0, "score": 1.0}]
        assert att.wrong_chars == []
        assert att.homophones == []
    finally:
        reset_current_user(token)


# ---------------------------------------------------------------------------
# 铁律 1：per-u 物理隔离
# ---------------------------------------------------------------------------


def test_two_users_attempts_physically_isolated(mu_isolated_root) -> None:
    """两个 u 的 attempts 物理隔离：各自 attempts.json，互不可见。"""
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.context import reset_current_user

    token = _h5("小明")
    try:
        att_xm = _record(RecitationStore(), material_id="mat_xm")
        # 物理落位：小明 workspace 下的 attempts.json（路径级隔离的锚）
        assert _attempts_file("小明").is_file()
    finally:
        reset_current_user(token)

    token = _h5("小红")
    try:
        store_xh = RecitationStore()
        att_xh = _record(store_xh, u="小红", material_id="mat_xh")
        # 文件物理分离：小红有自己的 attempts.json
        assert _attempts_file("小红").is_file()
        assert _attempts_file("小红") != _attempts_file("小明")
        # 互不可见：小红文件里查不到小明的记录，只看得到自己的
        assert [a.id for a in store_xh.list_attempts(u="小红")] == [att_xh.id]
        assert store_xh.list_attempts(u="小明") == []
    finally:
        reset_current_user(token)

    # 回到小明上下文重新开 store：仍只看到自己的那条（磁盘上互不可见）
    token = _h5("小明")
    try:
        store_xm = RecitationStore()
        got = store_xm.list_attempts(u="小明")
        assert [a.id for a in got] == [att_xm.id]
        assert got[0].material_id == "mat_xm"
        assert store_xm.list_attempts(u="小红") == []
    finally:
        reset_current_user(token)


# ---------------------------------------------------------------------------
# 规格 §4.8：partial attempt（segmented=true 未完成态）可留档
# ---------------------------------------------------------------------------


def test_partial_attempt_segmented_kept(mu_isolated_root) -> None:
    """逐段中途中断：已判段落即时留档一次，segmented=true 未完成态原样入库。"""
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.context import reset_current_user

    token = _h5("小明")
    try:
        store = RecitationStore()
        att = _record(
            store,
            ts=1700000001.0,
            total_score=0.5,
            per_segment=[{"idx": 0, "score": 1.0}, {"idx": 1, "score": 0.0}],
            wrong_chars=["雪"],
            homophones=["校"],
        )
        # 重开 store 读回：确认持久化在磁盘而非内存
        got = RecitationStore().list_attempts(u="小明")
        assert len(got) == 1 and got[0].id == att.id
        assert got[0].segmented is True  # 未完成态标记原样保留
        assert got[0].total_score == 0.5
        assert got[0].per_segment == [{"idx": 0, "score": 1.0}, {"idx": 1, "score": 0.0}]
        assert got[0].wrong_chars == ["雪"]
        assert got[0].homophones == ["校"]
    finally:
        reset_current_user(token)


# ---------------------------------------------------------------------------
# list_attempts(u, chapter_id)：最近 50 条倒序 + 50 条截断
# ---------------------------------------------------------------------------


def test_list_attempts_newest_first_and_cap_50(mu_isolated_root) -> None:
    """list_attempts：最近 50 条倒序（最新在前）；第 51 条起截断丢弃。"""
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.context import reset_current_user

    token = _h5("小明")
    try:
        store = RecitationStore()
        for i in range(55):
            _record(store, ts=float(i), material_id=f"m{i}")
        got = store.list_attempts(u="小明")
        # 截断：只余最近 50 条（ts 5..54），最老的 5 条（m0..m4）被丢弃
        assert len(got) == 50
        assert [a.material_id for a in got] == [f"m{i}" for i in range(54, 4, -1)]
        # 倒序：ts 严格递减（最新在前）
        ts_list = [a.ts for a in got]
        assert ts_list == sorted(ts_list, reverse=True)
    finally:
        reset_current_user(token)


def test_list_attempts_filters_by_chapter(mu_isolated_root) -> None:
    """chapter_id 过滤：只返回该章节的 attempts，仍倒序。"""
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.context import reset_current_user

    token = _h5("小明")
    try:
        store = RecitationStore()
        _record(store, ts=1.0, chapter_id="u1", material_id="m1")
        _record(store, ts=2.0, chapter_id="u2", material_id="m2")
        _record(store, ts=3.0, chapter_id="u1", material_id="m3")
        got = store.list_attempts(u="小明", chapter_id="u1")
        assert [a.material_id for a in got] == ["m3", "m1"]  # 倒序
        got_u2 = store.list_attempts(u="小明", chapter_id="u2")
        assert [a.material_id for a in got_u2] == ["m2"]
    finally:
        reset_current_user(token)


# ---------------------------------------------------------------------------
# T10 折叠项：过滤×截断组合（两章节交替 55 条钉文件级淘汰语义）
# ---------------------------------------------------------------------------


def test_filter_truncation_combo_pins_file_level_elimination(mu_isolated_root) -> None:
    """record 时的 50 条截断发生在文件级（全局最老先淘汰），非过滤后截断。

    两章节交替 55 条：u1/u2 各 27/28 条。截断后文件恰余最近 50 条
    （ts 5..54，最老 5 条含 u1 的 0/2/4 被淘汰）→ u1 过滤后恰 25 条；
    若实现错误为「先过滤后截断」，u1 会余 27 条——本用例钉死两者之差。
    """
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.context import reset_current_user

    token = _h5("小明")
    try:
        store = RecitationStore()
        for i in range(55):
            store.record(
                u="小明", textbook_id="tb",
                chapter_id="u1" if i % 2 == 0 else "u2",
                material_id=f"m{i}", material_title=f"课{i}",
                mode="recite", input_mode="type", ts=float(i),
            )
        # 文件级：磁盘文件恰 50 条（ts 5..54，append 序）
        raw = json.loads(_attempts_file("小明").read_text(encoding="utf-8"))
        assert [r["material_id"] for r in raw] == [f"m{i}" for i in range(5, 55)]
        # 过滤×截断组合：u1 只余 25 条（ts 6..54 偶数，倒序）
        got = store.list_attempts(u="小明", chapter_id="u1")
        assert [a.material_id for a in got] == [f"m{i}" for i in range(54, 4, -2)]
        assert len(got) == 25
    finally:
        reset_current_user(token)


# ===========================================================================
# T11 · recite 四端点（规格 §4.6：materials / check / attempts POST+GET）
# —— 门禁蓝本 = test_access_code_gate.R1-c（带 u 无码 → 401，逐端点钉）；
#    check 零 LLM 纯算法（验收判例 7/10）；attempts POST 留档 + L1 事件
#    recitation_completed（learner_profile L608 契约）且 FSRS 隔离
#    （reviews 队列不变——验收判例 9）。
# ===========================================================================


@pytest.fixture
def h5_settings(tmp_path, monkeypatch):
    """访问码门禁隔离环境（test_access_code_gate.h5_settings 同款本文件转出）：
    access_code=1234 写入 tmp 设置目录，USERS_ROOT 双处重绑（零真实 data/ 读取）。"""
    from deeptutor.api.routers import h5_links
    from deeptutor.multi_user import h5 as h5_mod

    users_root = tmp_path / "users"
    users_root.mkdir(parents=True, exist_ok=True)
    settings_dir = tmp_path / "user" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "h5.json").write_text(
        json.dumps(
            {"public_base": "https://h5.example.com", "access_code": "1234"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(h5_mod, "USERS_ROOT", users_root)
    monkeypatch.setattr(h5_links, "USERS_ROOT", users_root)
    return tmp_path


class _FakeRecitePathService:
    """指向 tmp 工作区的 PathService 替身（materials/check 的索引数据源隔离）。"""

    def __init__(self, root):
        self._root = root

    def get_workspace_dir(self):
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root


@pytest.fixture
def recite_ws(tmp_path, monkeypatch):
    """workspace 重定向到 tmp：端点内局部 import 的真实解析点 =
    deeptutor.services.path_service.get_path_service（T7 self_learning_client
    同款解析点——materials/check 不触 curriculum store，单点补丁即足）。"""
    fake = _FakeRecitePathService(tmp_path)
    monkeypatch.setattr(
        "deeptutor.services.path_service.get_path_service", lambda: fake
    )
    return tmp_path


def _write_grade_index(ws_root, grade_dir: str, index: dict) -> None:
    """落一个 <ws>/<grade_dir>/<grade_dir>_index.json（T7 测试同款）。"""
    d = ws_root / grade_dir
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{grade_dir}_index.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8"
    )


def _learning_trace_events() -> list[dict]:
    """当前用户上下文 memory 根下的 L1 learning trace 事件（跨日期聚合）。"""
    from deeptutor.services.memory import paths as memory_paths

    trace_dir = memory_paths.trace_dir("learning")
    events: list[dict] = []
    if trace_dir.exists():
        for f in sorted(trace_dir.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    events.append(json.loads(line))
    return events


# ---------------------------------------------------------------------------
# 铁律 1：全带 u 门禁（逐端点 401）
# ---------------------------------------------------------------------------


def test_recite_endpoints_guarded(h5_settings):
    """带 u 无码 → 401（规格 §4.6 全带 u 门禁；蓝本 test_access_code_gate.R1-c
    语义）。直调端点函数（materials/check/attempts POST+GET 同一守卫）。"""
    from deeptutor.api.routers import self_learning as sl

    with pytest.raises(HTTPException) as exc:
        sl.recite_materials(textbook_id="tb", chapter_id="c1",
                            u="小明", code="", x_access_code="")
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        sl.recite_check(
            body=sl.ReciteCheckRequest(
                material_id="m1", mode="recite", input_mode="type", segments=[],
            ),
            u="小明", code="", x_access_code="",
        )
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        sl.recite_attempt_create(
            body=sl.ReciteAttemptRequest(material_id="m1"),
            u="小明", code="", x_access_code="",
        )
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        sl.recite_attempts_list(
            u="小明", chapter_id="c1", code="", x_access_code=""
        )
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# materials：glob 读 recite_materials 键 + 按 chapter_ids 过滤
# ---------------------------------------------------------------------------


def test_materials_reads_recite_key_and_filters_by_chapter(recite_ws):
    """materials：glob 合并各年级索引的 recite_materials 键，按 chapter_ids
    过滤返回该章节素材；grade7 索引无该键 = 空列表（规格 §4.4，自然为空）。"""
    from deeptutor.api.routers import self_learning as sl

    _write_grade_index(recite_ws, "grade3", {
        "courseware": [],
        "exercises": [],
        "voices": [],
        "figures": [],
        "recite_materials": [
            {"id": "m1", "subject": "chinese", "type": "chinese_passage",
             "title": "大青树下的小学", "chapter_ids": ["c1"], "segments": []},
            {"id": "m2", "subject": "chinese", "type": "chinese_passage",
             "title": "花的学校", "chapter_ids": ["c2"], "segments": []},
        ],
    })
    # grade7 索引只有四消费键（无 recite_materials 键）——读键为空，不报错
    _write_grade_index(recite_ws, "grade7", {
        "courseware": [], "exercises": [], "voices": [], "figures": [],
    })

    out = sl.recite_materials(textbook_id="tb3", chapter_id="c1",
                              u="", code="", x_access_code="")
    assert [m["id"] for m in out["items"]] == ["m1"]
    assert out["count"] == 1

    # 七年级章节：索引无键 → 空列表（规格 §4.4「七年级无背诵素材」）
    out_g7 = sl.recite_materials(textbook_id="tb7", chapter_id="c-g7",
                                 u="", code="", x_access_code="")
    assert out_g7 == {"items": [], "count": 0}


# ---------------------------------------------------------------------------
# check：零 LLM 纯算法（判例 7/10）
# ---------------------------------------------------------------------------


def test_check_endpoint_pure_algorithm(recite_ws, monkeypatch):
    """POST check：check_segment 逐段 + 总分（规格 §4.6 响应形态
    {per_segment, total_score, wrong_chars, homophones}）。
    断言：零 LLM（factory 入口零触达）、错字/同音分类正确（验收判例 7/10）。"""
    from deeptutor.api.routers import self_learning as sl

    llm_calls: list = []

    async def _no_llm(*args, **kwargs):
        llm_calls.append(args)
        raise AssertionError("check 端点不得触达 LLM provider")

    monkeypatch.setattr(llm_factory, "complete", _no_llm)
    monkeypatch.setattr(llm_factory, "stream", _no_llm)

    _write_grade_index(recite_ws, "grade3", {
        "recite_materials": [{
            "id": "u1_daqingshu", "subject": "chinese",
            "type": "chinese_passage", "title": "大青树下的小学",
            "chapter_ids": ["c1"],
            "segments": [
                {"idx": 0, "text": "大青树下的小学"},  # 归一化 7 单元
                {"idx": 1, "text": "共１２３只"},      # 5 单元（判例 10 全角）
                {"idx": 2, "text": "不懂就要问"},      # 5 单元
            ],
        }],
    })

    out = sl.recite_check(
        body=sl.ReciteCheckRequest(
            material_id="u1_daqingshu", mode="recite", input_mode="type",
            segments=[
                {"idx": 0, "text": "大青树下的雪"},  # 学→雪 同音（判例 7）
                {"idx": 1, "text": "共123只"},       # 全角=半角（判例 10）
                {"idx": 2, "text": "不懂就要间"},    # 问→间 错字（判例 7）
            ],
        ),
        u="", code="", x_access_code="",
    )

    assert set(out.keys()) == {
        "per_segment", "total_score", "wrong_chars", "homophones",
    }
    per = out["per_segment"]
    assert [p["idx"] for p in per] == [0, 1, 2]
    # 判例 7 同音：学→雪 拼音同，不算错，score 满分
    assert per[0]["score"] == 1.0
    assert per[0]["diff"]["homophones"] == ["雪"]
    assert per[0]["diff"]["wrong_chars"] == []
    # 判例 10：NFKC 全角（１２３）与（123）等价
    assert per[1]["score"] == 1.0
    assert per[1]["diff"] == {
        "wrong_chars": [], "homophones": [], "missing": [], "extra": [],
    }
    # 判例 7 错字：问→间 拼音异，计错
    assert per[2]["diff"]["wrong_chars"] == ["间"]
    assert abs(per[2]["score"] - 4 / 5) < 1e-9
    assert out["wrong_chars"] == ["间"]
    assert out["homophones"] == ["雪"]
    # 篇级总分按原文归一化单元数加权（§4.3 段/篇两级）：(7*1 + 5*1 + 5*0.8)/17
    assert out["total_score"] == pytest.approx(16 / 17)
    assert llm_calls == []  # 零 LLM


def test_check_whole_text_full_reference(recite_ws, monkeypatch):
    """审查 R1-必修2：整篇模式参考=全部段参考文本按 idx 拼接。

    此前前端整篇送 {idx:0, whole} → 仅与第 0 段比对，其余全文进 extra
    不入分母（第 0 段对+废话可判满分 1.0）。"""
    from fastapi import HTTPException

    from deeptutor.api.routers import self_learning as sl

    async def _no_llm(*args, **kwargs):
        raise AssertionError("check 端点不得触达 LLM provider")

    monkeypatch.setattr(llm_factory, "complete", _no_llm)
    monkeypatch.setattr(llm_factory, "stream", _no_llm)

    _write_grade_index(recite_ws, "grade3", {
        "recite_materials": [{
            "id": "u1_daqingshu", "subject": "chinese",
            "type": "chinese_passage", "title": "大青树下的小学",
            "chapter_ids": ["c1"],
            "segments": [
                {"idx": 0, "text": "大青树下的小学"},
                {"idx": 1, "text": "共１２３只"},
                {"idx": 2, "text": "不懂就要问"},
            ],
        }],
    })

    def _check(**kw):
        return sl.recite_check(
            body=sl.ReciteCheckRequest(
                material_id="u1_daqingshu", mode="recite", input_mode="type", **kw,
            ),
            u="", code="", x_access_code="",
        )

    # 第 0 段对 + 尾部无关废话 → 必须不满分
    out = _check(whole_text="大青树下的小学今天中午吃什么好呢完全无关的废话越来越多")
    assert out["total_score"] < 1.0
    assert len(out["per_segment"]) == 1
    assert out["per_segment"][0]["idx"] == 0
    assert len(out["per_segment"][0]["diff"]["extra"]) > 0

    # 全篇全对（三段拼接）→ 1.0
    out_full = _check(whole_text="大青树下的小学\n共１２３只\n不懂就要问")
    assert out_full["total_score"] == 1.0
    assert out_full["per_segment"][0]["diff"] == {
        "wrong_chars": [], "homophones": [], "missing": [], "extra": [],
    }

    # 二选一契约：既有 segments 又有 whole_text → 422；两者皆空 → 422
    with pytest.raises(HTTPException) as ei:
        _check(whole_text="大青树下的小学",
               segments=[{"idx": 0, "text": "大青树下的小学"}])
    assert ei.value.status_code == 422
    with pytest.raises(HTTPException) as ei2:
        _check()
    assert ei2.value.status_code == 422


# ---------------------------------------------------------------------------
# attempts POST：store 留档 + L1 事件 + FSRS 隔离（判例 9）
# ---------------------------------------------------------------------------


def test_attempts_post_writes_store_and_l1_event(mu_isolated_root, monkeypatch):
    """POST attempts：store 留档 + emit_learning_event(kind="recitation_completed",
    payload={chapter_id, material_title, mode, score})（learner_profile L608
    契约）；FSRS 隔离——reviews 队列长度与卡片状态零变化（验收判例 9）。"""
    # trace per-surface 锁跨 loop 复用会被 append 静默吞掉
    # （套件先例：test_h5_progress.ws 的 trace 锁隔离）。
    from deeptutor.services.memory import trace as trace_mod

    monkeypatch.setattr(trace_mod, "_lock_for", lambda surface: asyncio.Lock())

    from deeptutor.api.routers import self_learning as sl

    token = _h5("小明")
    try:
        # —— 判例 9 基线：先种一条非空 FSRS 复习队列到该用户的影子进度 ——
        from deeptutor.learning.models import (
            KnowledgeType,
            LearningProgress,
            RepetitionState,
            ReviewTask,
        )
        from deeptutor.learning.storage import LearningStore
        from deeptutor.services.path_service import get_path_service

        ws = get_path_service().get_workspace_dir()
        lstore = LearningStore(ws / "learning")
        card = RepetitionState(
            next_review_at=1700000000.0, fsrs=True, stability=1.0, reps=1,
        )
        lstore.save(LearningProgress(
            book_id="shadow_u1",
            review_queue=[ReviewTask(
                id="rt-1", knowledge_point_id="kp_a",
                knowledge_type=KnowledgeType.MEMORY,
                due_at=1700000000.0, priority=1, state=card,
            )],
            repetition_states={"kp_a": card},
        ))

        out = sl.recite_attempt_create(
            body=sl.ReciteAttemptRequest(
                textbook_id="tb_bnu_math_3a", chapter_id="u1",
                material_id="u1_daqingshu", material_title="大青树下的小学",
                mode="recite", input_mode="voice", segmented=True,
                total_score=0.875, per_segment=[{"idx": 0, "score": 1.0}],
                wrong_chars=[], homophones=["雪"],
            ),
            u="小明", code="", x_access_code="",
        )

        # store 留档（磁盘回读，路径级隔离锚）
        from deeptutor.learning.recitation.store import RecitationStore

        assert _attempts_file("小明").is_file()
        got = RecitationStore().list_attempts(u="小明")
        assert len(got) == 1
        assert got[0].chapter_id == "u1"
        assert got[0].material_title == "大青树下的小学"
        assert got[0].mode == "recite" and got[0].input_mode == "voice"
        assert got[0].total_score == 0.875
        assert got[0].homophones == ["雪"]
        assert out["id"] == got[0].id

        # L1 事件：kind/payload 对账（§4.7 {chapter_id, material_title, mode, score}）
        events = [e for e in _learning_trace_events()
                  if e["kind"] == "recitation_completed"]
        assert len(events) == 1
        assert events[0]["payload"] == {
            "chapter_id": "u1", "material_title": "大青树下的小学",
            "mode": "recite", "score": 0.875,
        }

        # FSRS 隔离（判例 9）：reviews 队列长度不变、FSRS 卡片零新增
        after = lstore.load("shadow_u1")
        assert [t.id for t in after.review_queue] == ["rt-1"]
        assert set(after.repetition_states.keys()) == {"kp_a"}
    finally:
        from deeptutor.multi_user.context import reset_current_user

        reset_current_user(token)


# ---------------------------------------------------------------------------
# attempts GET：最近 50 条倒序 + chapter_id 过滤
# ---------------------------------------------------------------------------


def test_attempts_get_recent_50_and_chapter_filter(mu_isolated_root):
    """GET attempts：历史最近 50 条倒序（规格 §4.6）+ chapter_id 过滤透传。"""
    from deeptutor.api.routers import self_learning as sl
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.context import reset_current_user

    token = _h5("小明")
    try:
        store = RecitationStore()
        for i in range(55):
            store.record(
                u="小明", textbook_id="tb",
                chapter_id="u1" if i % 2 == 0 else "u2",
                material_id=f"m{i}", material_title=f"课{i}",
                mode="recite", input_mode="type", ts=float(i),
            )
        out = sl.recite_attempts_list(
            u="小明", chapter_id="", code="", x_access_code=""
        )
        assert out["count"] == 50
        assert [it["material_id"] for it in out["items"]] == [
            f"m{i}" for i in range(54, 4, -1)
        ]
        out_u1 = sl.recite_attempts_list(
            u="小明", chapter_id="u1", code="", x_access_code=""
        )
        assert out_u1["count"] == 25
        assert [it["material_id"] for it in out_u1["items"]] == [
            f"m{i}" for i in range(54, 4, -2)
        ]
    finally:
        reset_current_user(token)
