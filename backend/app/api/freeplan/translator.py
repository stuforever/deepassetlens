# -*- coding: utf-8 -*-
"""freeplan/translator.py - think 流前缀状态机（批13-D Step3：从 stream 编排器封装为类）

ThinkRoundClassifier：每轮 LLM 输出的流式分类器——把 token 流判为四类：
- wait：前缀未定（标记/决策头部分到达），本轮不推帧
- decision_first / answer_first：分类落定后的首次冲刷（推完整累积，防丢前缀文字）
- decision_delta / answer_delta：已识别后的增量推送
- notes：任务笔记（## SESSION INTENT 等内部产物），不推任何帧

行为零变化：分类语义与帧 kind/delta 与内联版逐一对应（SSE 字节一致）；
帧的 yield 仍留在编排器 event_iter（translator 只做纯判定，不碰 I/O）。
"""
from __future__ import annotations

# deepagents 工具循环的"任务笔记"固定标题（模型每次调工具前输出，内部产物，不应作为回答上屏）
TOOL_NOTE_MARKERS = ("## SESSION INTENT", "## SUMMARY", "## ARTIFACTS", "## NEXT STEPS")
# 候选判断（"下一步判断"）固定头
DECISION_MARKER = "【下一步判断】"

# classify() 返回的动作码
WAIT = "wait"                    # 前缀未定，继续等 token
DECISION_FIRST = "decision_first"  # 决策流首次冲刷（kind=decision_draft, delta=accumulated）
ANSWER_FIRST = "answer_first"    # 答案流首次冲刷（kind=answer_draft, delta=accumulated）
DECISION_DELTA = "decision_delta"  # 决策流增量（kind=decision_draft, delta=token）
ANSWER_DELTA = "answer_delta"    # 答案流增量（kind=answer_draft, delta=token）
SKIP = "skip"                    # notes 类，不推帧


class ThinkRoundClassifier:
    """单轮 LLM 输出的前缀状态机（accumulated/classifier/seq 与内联版字段一致）。"""

    __slots__ = ("accumulated", "state", "seq")

    def __init__(self) -> None:
        self.accumulated = ""
        self.state = "detecting"  # detecting | decision | answer | notes
        self.seq = 0

    def feed(self, token: str) -> str:
        """喂入一个 token，返回动作码（见模块常量）。"""
        self.accumulated += token
        self.seq += 1
        if self.state == "detecting":
            _stripped = self.accumulated.lstrip()
            if DECISION_MARKER.startswith(_stripped) and len(_stripped) < len(DECISION_MARKER):
                return WAIT  # 仍是标记前缀，等待更多 token
            # 任务笔记标题前缀等待（如 "## S"）：前缀阶段不完整，须等待更多 token 再定
            if any(m.startswith(_stripped) and len(_stripped) < len(m) for m in TOOL_NOTE_MARKERS):
                return WAIT
            if _stripped.startswith(DECISION_MARKER):
                self.state = "decision"
                return DECISION_FIRST  # 首次冲刷：推完整累积内容（不丢前面的标记和文字）
            if any(_stripped.startswith(m) for m in TOOL_NOTE_MARKERS):
                # 工具任务笔记：内部中间产物，丢弃不推 answer_draft
                self.state = "notes"
                return SKIP
            self.state = "answer"
            return ANSWER_FIRST
        # 已识别，只推增量（notes 类不推任何 think_token）
        if self.state == "notes":
            return SKIP
        return DECISION_DELTA if self.state == "decision" else ANSWER_DELTA

    @staticmethod
    def kind_of(action: str) -> str:
        """动作码 -> SSE 帧 kind 字段（与内联版逐一对应）。"""
        return "decision_draft" if action in (DECISION_FIRST, DECISION_DELTA) else "answer_draft"
