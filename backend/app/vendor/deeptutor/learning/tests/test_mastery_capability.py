"""mastery_path 能力面表征测试（任务 5.4）。

覆盖 ``deeptutor/capabilities/mastery/capability.py`` 与 ``loop.py``：
  - 能力注册面：manifest 断言 + builtin_capabilities.py 类路径对照
  - resolve_mastery_path_id 优先级链（显式 > 书引用 str/dict > session > default）+ 净化
  - run() 打标（mastery_mode + mastery_path_id）并委托 AgenticChatPipeline（fake）
  - MasteryLoopCapability 钩子：is_active 门控 / system_block（覆盖 > 打包 prompt，
    zh/en 语言回退）/ augment_kwargs（仅对 mastery 工具注入引擎键）/ pre_loop_seed

纯内存、零 IO 侧效（打包 prompt 只读）。
"""

from __future__ import annotations

import pytest

from deeptutor.capabilities.mastery.capability import (
    MasteryPathCapability,
    resolve_mastery_path_id,
)
from deeptutor.capabilities.mastery.loop import MasteryLoopCapability
from deeptutor.capabilities.mastery.tools import MASTERY_TOOL_NAMES
from deeptutor.core.context import UnifiedContext
from deeptutor.runtime.bootstrap.builtin_capabilities import BUILTIN_CAPABILITY_CLASSES


# --------------------------------------------------------------------------- #
# 注册面（对照 builtin_capabilities.py —— 0.3 已验证的注册口径）                  #
# --------------------------------------------------------------------------- #


def test_manifest_registration_face():
    cap = MasteryPathCapability()
    assert cap.manifest.name == "mastery_path"
    assert cap.manifest.stages == ["responding"]
    assert "ask_user" in cap.manifest.tools_used  # 出题卡经 ask_user 交互
    assert set(MASTERY_TOOL_NAMES) <= set(cap.manifest.tools_used)
    assert cap.manifest.cli_aliases == ["mastery"]


def test_builtin_capabilities_class_path_matches_actual_class():
    """注册表字符串与实际类模块路径一致（防漂移）。"""
    registered = BUILTIN_CAPABILITY_CLASSES["mastery_path"]
    expected = f"{MasteryPathCapability.__module__}:{MasteryPathCapability.__qualname__}"
    assert registered == expected


def test_registry_exports_loop_capability():
    from deeptutor.capabilities.mastery import MasteryLoopCapability as exported

    assert exported is MasteryLoopCapability


# --------------------------------------------------------------------------- #
# resolve_mastery_path_id：优先级链 + 净化                                      #
# --------------------------------------------------------------------------- #


def test_resolve_prefers_explicit_metadata_and_strips():
    ctx = UnifiedContext(session_id="sess-1", metadata={"mastery_path_id": "  my-path  "})
    assert resolve_mastery_path_id(ctx) == "my-path"


def test_resolve_sanitizes_unsafe_chars():
    ctx = UnifiedContext(metadata={"mastery_path_id": "a/b c!"})
    assert resolve_mastery_path_id(ctx) == "a_b_c"  # 非法字符 → 下划线，首尾 _ 去除


def test_resolve_sanitized_empty_falls_back_to_default():
    ctx = UnifiedContext(metadata={"mastery_path_id": "///"})
    assert resolve_mastery_path_id(ctx) == "default"


def test_resolve_book_reference_string():
    ctx = UnifiedContext(metadata={"book_references": ["bk1"]})
    assert resolve_mastery_path_id(ctx) == "bk1"


def test_resolve_book_reference_dict_prefers_book_id():
    ctx = UnifiedContext(metadata={"book_references": [{"book_id": "bk2", "id": "ignored"}]})
    assert resolve_mastery_path_id(ctx) == "bk2"


def test_resolve_book_reference_dict_falls_back_to_id():
    ctx = UnifiedContext(metadata={"book_references": [{"id": "bk3"}]})
    assert resolve_mastery_path_id(ctx) == "bk3"


def test_resolve_blank_string_reference_falls_through_to_session():
    ctx = UnifiedContext(session_id="sess-9", metadata={"book_references": ["   "]})
    assert resolve_mastery_path_id(ctx) == "sess-9"


def test_resolve_final_fallback_session_then_default():
    assert resolve_mastery_path_id(UnifiedContext(session_id="s1")) == "s1"
    assert resolve_mastery_path_id(UnifiedContext()) == "default"


# --------------------------------------------------------------------------- #
# run()：打标 + 委托 chat 管线                                                  #
# --------------------------------------------------------------------------- #


class _FakePipeline:
    instances: list["_FakePipeline"] = []

    def __init__(self, language: str = "en"):
        self.language = language
        self.ran_with: UnifiedContext | None = None
        self.ran_stream = None
        _FakePipeline.instances.append(self)

    async def run(self, context: UnifiedContext, stream) -> None:
        self.ran_with = context
        self.ran_stream = stream


@pytest.fixture
def fake_pipeline(monkeypatch):
    _FakePipeline.instances = []
    monkeypatch.setattr(
        "deeptutor.capabilities.mastery.capability.AgenticChatPipeline", _FakePipeline
    )
    return _FakePipeline


@pytest.mark.asyncio
async def test_run_marks_mastery_metadata_and_delegates(fake_pipeline):
    ctx = UnifiedContext(session_id="sess-1", metadata={"mastery_path_id": "p/1"}, language="zh")
    stream = object()
    await MasteryPathCapability().run(ctx, stream)
    assert ctx.metadata["mastery_mode"] is True
    assert ctx.metadata["mastery_path_id"] == "p_1"  # 净化后的路径 id 写回 metadata
    (fake,) = _FakePipeline.instances
    assert fake.language == "zh"
    assert fake.ran_with is ctx
    assert fake.ran_stream is stream


@pytest.mark.asyncio
async def test_run_resolves_path_id_from_session_when_absent(fake_pipeline):
    ctx = UnifiedContext(session_id="sess-42", metadata={})
    await MasteryPathCapability().run(ctx, object())
    assert ctx.metadata["mastery_path_id"] == "sess-42"


# --------------------------------------------------------------------------- #
# MasteryLoopCapability 钩子                                                    #
# --------------------------------------------------------------------------- #


def _active_ctx(**meta) -> UnifiedContext:
    return UnifiedContext(session_id="sess-7", metadata={"mastery_mode": True, **meta})


def test_loop_inactive_by_default():
    loop = MasteryLoopCapability()
    ctx = UnifiedContext(session_id="s", metadata={})
    assert loop.is_active(ctx) is False
    assert loop.system_block(ctx, language="zh", prompts={}) is None
    kwargs = {"query": "x"}
    assert loop.augment_kwargs("mastery_quiz", kwargs, ctx) is kwargs  # 原样透传
    assert loop.pre_loop_seed(ctx) == ""


def test_loop_system_block_uses_override_over_packaged_prompt():
    loop = MasteryLoopCapability()
    block = loop.system_block(
        _active_ctx(), language="zh", prompts={"mastery": {"system": "覆盖提示词"}}
    )
    assert block is not None
    assert block.name == "mastery_tutor"
    assert block.content == "覆盖提示词"


def test_loop_system_block_falls_back_to_packaged_prompts():
    from importlib import resources

    loop = MasteryLoopCapability()
    zh_expected = (
        resources.files("deeptutor.capabilities.mastery")
        .joinpath("prompts", "zh", "system.md")
        .read_text(encoding="utf-8")
        .strip()
    )
    en_expected = (
        resources.files("deeptutor.capabilities.mastery")
        .joinpath("prompts", "en", "system.md")
        .read_text(encoding="utf-8")
        .strip()
    )
    zh_block = loop.system_block(_active_ctx(), language="zh", prompts={})
    en_block = loop.system_block(_active_ctx(), language="en-US", prompts={})
    assert zh_block.content == zh_expected
    assert en_block.content == en_expected
    assert zh_block.content != en_block.content  # 双语 prompt 确实分流


def test_loop_language_fallback_non_zh_uses_english():
    loop = MasteryLoopCapability()
    fr_block = loop.system_block(_active_ctx(), language="fr", prompts={})
    en_block = loop.system_block(_active_ctx(), language="en", prompts={})
    assert fr_block.content == en_block.content


def test_loop_augment_kwargs_injects_engine_keys_for_mastery_tools_only():
    loop = MasteryLoopCapability()
    ctx = _active_ctx(mastery_path_id="p1", turn_id="t1")
    injected = loop.augment_kwargs("mastery_quiz", {"knowledge_point_id": "kp"}, ctx)
    assert injected == {
        "knowledge_point_id": "kp",
        "_mastery_path_id": "p1",
        "_session_id": "sess-7",
        "_turn_id": "t1",
    }
    # 非 mastery 工具不注入（原对象透传）
    passthrough = {"query": "x"}
    assert loop.augment_kwargs("rag", passthrough, ctx) is passthrough


def test_loop_augment_kwargs_empty_ids_fail_closed_to_empty_strings():
    """path id 缺失时注入空串——工具侧 _resolve_path_id 判空 fail-closed。"""
    loop = MasteryLoopCapability()
    ctx = UnifiedContext(session_id="", metadata={"mastery_mode": True})
    injected = loop.augment_kwargs("mastery_grade", {}, ctx)
    assert injected == {"_mastery_path_id": "", "_session_id": "", "_turn_id": ""}


def test_loop_owned_tools_match_engine_tool_names():
    assert MasteryLoopCapability.owned_tools == MASTERY_TOOL_NAMES
    assert MasteryLoopCapability.name == "mastery"


def test_mastery_tool_types_and_names_stay_in_agreement():
    """MASTERY_TOOL_NAMES is "kept so the mount policy and the registration
    list can't disagree" (tools.py) — pin that agreement: each type in
    MASTERY_TOOL_TYPES defines exactly the name at its position.
    """
    from deeptutor.capabilities.mastery.tools import MASTERY_TOOL_TYPES

    definition_names = [
        tool_cls().get_definition().name for tool_cls in MASTERY_TOOL_TYPES
    ]
    assert definition_names == list(MASTERY_TOOL_NAMES)


def test_packaged_prompts_carry_learner_profile_hook():
    """收编的 §3.6 学情感知 prompt（前会话在途件，随本任务入库）双语都指示
    导师会话开始时调 read_memory 读学情画像，且以引擎 mastery_status 为准。

    轻量钉子：只钉钩子存在性（read_memory + 画像优先级语义），不锁全文，
    避免措辞微调造成脆断。
    """
    from importlib import resources

    package = resources.files("deeptutor.capabilities.mastery")
    zh = package.joinpath("prompts", "zh", "system.md").read_text(encoding="utf-8")
    en = package.joinpath("prompts", "en", "system.md").read_text(encoding="utf-8")
    for text in (zh, en):
        assert "read_memory" in text
        assert "mastery_status" in text  # 引擎判断权威
    assert "学情画像" in zh
    assert "Learner-aptitude awareness" in en
