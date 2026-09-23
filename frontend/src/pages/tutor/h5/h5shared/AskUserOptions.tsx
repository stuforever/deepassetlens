/**
 * 复刻自 DeepTutor 原仓 web/components/chat/home/AskUserOptions.tsx（整件 1:1）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. lucide ChevronDown/ChevronLeft/ChevronRight → @ant-design/icons DownOutlined/
 *    LeftOutlined/RightOutlined；
 * 3. i18n t() → 中文直出（译自原仓 locales/zh/app.json；"Select all that apply."/
 *    "answered" 原仓 zh 无 key，按语义直出「可多选。」「已答」）；
 * 4. Tailwind（shadcn CSS 变量类）→ 内联样式 + 组件级 <style> 承接 hover/disabled 伪类。
 *    CSS 变量取原仓 Snow 亮色主题实测值：--foreground #0f172a、--muted-foreground #64748b、
 *    --primary #4f46e5（indigo-600，与 H5 全站主色一致）、--primary-foreground #ffffff、
 *    --card #ffffff、--border #e2e8f0、--muted #f1f5f9、--background #f8fafc；
 *    color-mix(...) 按 srgb 百分比换算为静态 rgba/hex。
 * 5. @/lib/stream → 批8 admin/stream.ts；@/lib/unified-ws → 批8 admin/unified-ws.ts。
 */
import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DownOutlined, LeftOutlined, RightOutlined } from "@ant-design/icons";

import {
  collectNarrationCallIds,
  shouldAppendEventContent,
} from "../../admin/stream";
import type { StreamEvent } from "../../admin/unified-ws";

/** 原仓 Snow 亮色主题 CSS 变量取值（本文件局部对位用）。 */
const FG = "#0f172a";
const MUTED_FG = "#64748b";
const PRIMARY = "#4f46e5";
const PRIMARY_FG = "#ffffff";
const CARD = "#ffffff";
const BORDER = "#e2e8f0";
const MUTED = "#f1f5f9";
const BG = "#f8fafc";

/**
 * v3 ``ask_user`` payload. Mirrors ``deeptutor.tools.ask_user.AskUserPayload``.
 *
 * Every question is rendered as one tab on the card (labelled by its
 * short ``header`` when present); the user can switch between tabs
 * freely, answer each (or skip), and submit once via the footer
 * "Submit answers" button. Options carry a short ``label`` plus an
 * optional ``description`` explaining what picking it implies —
 * mirroring Claude Code's ``AskUserQuestion``. The frontend always
 * carries the v3 shape internally — legacy payloads (plain-string
 * options, single-question) are normalised at extraction time.
 */
export interface AskUserOption {
  label: string;
  description: string | null;
}

export interface AskUserQuestion {
  id: string;
  prompt: string;
  header: string | null;
  multi_select: boolean;
  options: AskUserOption[];
  allow_free_text: boolean;
  placeholder: string | null;
}

export interface AskUserPayload {
  intro: string | null;
  questions: AskUserQuestion[];
}

export interface AskUserAnswer {
  questionId: string;
  /** Empty string = skipped / no answer. */
  text: string;
}

/**
 * Bundled data the chat surface reads from an assistant message's
 * event stream. Always returned together so the card can render in
 * either ``interactive`` (still waiting on user) or ``resolved``
 * (read-only Q&A summary) mode without losing its place in chat
 * history. Returns ``null`` only when the message has no ``ask_user``
 * tool result at all.
 */
export interface AskUserCardData {
  payload: AskUserPayload;
  /** Present when the user has submitted; ``null`` while still pending. */
  answers: AskUserAnswer[] | null;
  resolved: boolean;
}

/**
 * Read the ``ask_user`` card data from an assistant message's events.
 *
 * Walks the events forward (oldest first) so multiple ``ask_user``
 * calls within one turn render as separate Q&A summaries in order.
 * Today only the *latest* unresolved card is interactive; older ones
 * are forced into resolved mode by the corresponding ``progress``
 * event carrying ``ask_user_resolved=true`` (and ideally
 * ``ask_user_tool_call_id``, used to match resolutions to the right
 * question card).
 *
 * Returns the most-recent card so the caller renders one. (Past turns
 * with multiple ask_user calls collapse to the last one — surfacing
 * every one would clutter chat history; the rest are visible in the
 * underlying tool-trace view anyway.)
 */
export function extractAskUserPayload(
  events: StreamEvent[] | undefined,
): AskUserCardData | null {
  if (!events || events.length === 0) return null;

  let latest: {
    payload: AskUserPayload;
    toolCallId: string | null;
  } | null = null;
  let resolution: {
    toolCallId: string | null;
    answers: AskUserAnswer[];
    text: string;
  } | null = null;

  for (const event of events) {
    const meta = (event.metadata ?? {}) as Record<string, unknown>;
    if (event.type === "tool_result") {
      const toolMetadata = meta.tool_metadata;
      if (!toolMetadata || typeof toolMetadata !== "object") continue;
      const askUser = (toolMetadata as Record<string, unknown>).ask_user;
      const normalised = normaliseAskUserPayload(askUser);
      if (!normalised) continue;
      latest = {
        payload: normalised,
        toolCallId:
          (event as { tool_call_id?: string }).tool_call_id ??
          (typeof meta.tool_call_id === "string" ? meta.tool_call_id : null),
      };
      resolution = null;
      continue;
    }
    if (event.type === "progress" && meta.ask_user_resolved) {
      const answersRaw = Array.isArray(meta.answers)
        ? (meta.answers as unknown[])
        : [];
      resolution = {
        toolCallId:
          typeof meta.ask_user_tool_call_id === "string"
            ? meta.ask_user_tool_call_id
            : null,
        answers: answersRaw
          .map((entry) => {
            if (!entry || typeof entry !== "object") return null;
            const obj = entry as Record<string, unknown>;
            const qid = String(obj.questionId || obj.id || "").trim();
            if (!qid) return null;
            return { questionId: qid, text: String(obj.text || "") };
          })
          .filter((a): a is AskUserAnswer => a !== null),
        text:
          typeof meta.reply_preview === "string"
            ? (meta.reply_preview as string)
            : "",
      };
    }
  }

  if (!latest) return null;

  if (
    resolution &&
    (resolution.toolCallId === latest.toolCallId || latest.toolCallId === null)
  ) {
    const answers =
      resolution.answers.length > 0
        ? resolution.answers
        : // Legacy flat-text resolution: backfill as a single synthetic
          // answer attached to the (first) question so the resolved view
          // still has something to display.
          latest.payload.questions.length > 0
          ? [
              {
                questionId: latest.payload.questions[0].id,
                text: resolution.text || "",
              },
            ]
          : [];
    return { payload: latest.payload, answers, resolved: true };
  }

  return { payload: latest.payload, answers: null, resolved: false };
}

/**
 * Interleaved message body. Walks the event stream forward and emits a
 * sequence of segments in the order they were produced, so that text
 * generated before an ``ask_user`` tool result renders ABOVE the card
 * and text generated by the resumed iteration renders BELOW it. The
 * default chat surface uses this instead of pairing a flat
 * ``msg.content`` blob with a card stuck at the bottom.
 *
 * Each ``ask_user`` tool result becomes its own segment with its own
 * resolution state — multiple ask_user calls in one turn render as
 * separate cards in stream order. Only the latest unresolved card is
 * interactive; resolved cards show their Q&A summary.
 */
export type MessageSegment =
  | { kind: "text"; text: string; key: string }
  | {
      kind: "ask_user";
      data: AskUserCardData;
      toolCallId: string | null;
      key: string;
    };

export function extractMessageSegments(
  events: StreamEvent[] | undefined,
): MessageSegment[] {
  if (!events || events.length === 0) return [];

  const segments: MessageSegment[] = [];
  // Index of each ask_user segment by tool_call_id so a later
  // ``progress`` event carrying ``ask_user_resolved`` can flip the
  // matching card to resolved mode without a second pass.
  const byToolCall = new Map<string, number>();
  const seenAskUserCards = new Set<string>();
  let pendingTextIdx: number | null = null;
  let seq = 0;
  // Narration rounds (chat-loop preamble alongside a tool call) stream as
  // content but belong in the trace, not the answer — keep them out of the
  // inline text segments too.
  const narrationCallIds = collectNarrationCallIds(events);

  const ensureTextSegment = () => {
    if (pendingTextIdx === null) {
      pendingTextIdx = segments.length;
      segments.push({ kind: "text", text: "", key: `t${seq++}` });
    }
    return pendingTextIdx;
  };

  for (const event of events) {
    if (shouldAppendEventContent(event)) {
      const callId = ((event.metadata ?? {}) as { call_id?: string }).call_id;
      if (callId && narrationCallIds.has(callId)) continue;
      const idx = ensureTextSegment();
      const seg = segments[idx];
      if (seg.kind === "text") {
        segments[idx] = { ...seg, text: seg.text + event.content };
      }
      continue;
    }
    const meta = (event.metadata ?? {}) as Record<string, unknown>;
    if (event.type === "tool_result") {
      const toolMetadata = meta.tool_metadata;
      if (!toolMetadata || typeof toolMetadata !== "object") continue;
      const askUser = (toolMetadata as Record<string, unknown>).ask_user;
      const normalised = normaliseAskUserPayload(askUser);
      if (!normalised) continue;
      const toolCallId =
        (event as { tool_call_id?: string }).tool_call_id ??
        (typeof meta.tool_call_id === "string" ? meta.tool_call_id : null);
      const cardKey = toolCallId
        ? `call:${toolCallId}`
        : `payload:${JSON.stringify(normalised)}`;
      if (seenAskUserCards.has(cardKey)) continue;
      seenAskUserCards.add(cardKey);
      // Close the current text run so the next text chunk starts a new
      // segment after this card.
      pendingTextIdx = null;
      const idx = segments.length;
      segments.push({
        kind: "ask_user",
        data: { payload: normalised, answers: null, resolved: false },
        toolCallId,
        key: `a${seq++}`,
      });
      if (toolCallId) byToolCall.set(toolCallId, idx);
      continue;
    }
    if (event.type === "progress" && meta.ask_user_resolved) {
      const replyToolCallId =
        typeof meta.ask_user_tool_call_id === "string"
          ? meta.ask_user_tool_call_id
          : null;
      // Match by tool_call_id; fall back to the most recent unresolved
      // ask_user segment if the resolver did not echo the id back.
      let targetIdx =
        replyToolCallId !== null ? (byToolCall.get(replyToolCallId) ?? -1) : -1;
      if (targetIdx < 0) {
        for (let i = segments.length - 1; i >= 0; i--) {
          const s = segments[i];
          if (s.kind === "ask_user" && !s.data.resolved) {
            targetIdx = i;
            break;
          }
        }
      }
      if (targetIdx < 0) continue;
      const target = segments[targetIdx];
      if (target.kind !== "ask_user") continue;
      const answersRaw = Array.isArray(meta.answers)
        ? (meta.answers as unknown[])
        : [];
      const answers: AskUserAnswer[] = answersRaw
        .map((entry) => {
          if (!entry || typeof entry !== "object") return null;
          const obj = entry as Record<string, unknown>;
          const qid = String(obj.questionId || obj.id || "").trim();
          if (!qid) return null;
          return { questionId: qid, text: String(obj.text || "") };
        })
        .filter((a): a is AskUserAnswer => a !== null);
      const replyText =
        typeof meta.reply_preview === "string"
          ? (meta.reply_preview as string)
          : "";
      const finalAnswers =
        answers.length > 0
          ? answers
          : target.data.payload.questions.length > 0
            ? [
                {
                  questionId: target.data.payload.questions[0].id,
                  text: replyText || "",
                },
              ]
            : [];
      segments[targetIdx] = {
        ...target,
        data: {
          payload: target.data.payload,
          answers: finalAnswers,
          resolved: true,
        },
      };
    }
  }

  // Drop empty trailing/leading text segments so the renderer doesn't
  // emit blank ``<AssistantResponse>`` nodes.
  return segments.filter((s) => s.kind !== "text" || s.text.length > 0);
}

/**
 * One option: v3 emits ``{label, description}`` objects; v2 payloads
 * stored in older sessions carry plain strings. Both normalise to the
 * object shape.
 */
function normaliseOption(raw: unknown): AskUserOption | null {
  if (raw && typeof raw === "object") {
    const o = raw as Record<string, unknown>;
    const label = String(o.label ?? "").trim();
    if (!label) return null;
    const description =
      typeof o.description === "string" && o.description.trim()
        ? o.description.trim()
        : null;
    return { label, description };
  }
  const label = String(raw ?? "").trim();
  return label ? { label, description: null } : null;
}

function normaliseAskUserPayload(raw: unknown): AskUserPayload | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;

  // v2/v3 shape: ``{intro?, questions: [...]}``
  if (Array.isArray(obj.questions)) {
    const questions: AskUserQuestion[] = [];
    for (const item of obj.questions) {
      if (!item || typeof item !== "object") continue;
      const q = item as Record<string, unknown>;
      const prompt = String(q.prompt ?? q.question ?? "").trim();
      if (!prompt) continue;
      const optionsRaw = Array.isArray(q.options) ? q.options : [];
      questions.push({
        id: String(q.id || `q${questions.length + 1}`),
        prompt,
        header:
          typeof q.header === "string" && q.header.trim()
            ? q.header.trim()
            : null,
        multi_select: Boolean(q.multi_select ?? q.multiSelect),
        options: optionsRaw
          .map(normaliseOption)
          .filter((o): o is AskUserOption => o !== null),
        allow_free_text: q.allow_free_text === false ? false : true,
        placeholder:
          typeof q.placeholder === "string" && q.placeholder.trim()
            ? (q.placeholder as string).trim()
            : null,
      });
    }
    if (questions.length === 0) return null;
    return {
      intro:
        typeof obj.intro === "string" && obj.intro.trim()
          ? (obj.intro as string).trim()
          : null,
      questions,
    };
  }

  // Legacy single-question shape from before the multi-question refactor.
  const prompt = String(obj.question ?? "").trim();
  if (!prompt) return null;
  const optionsRaw = Array.isArray(obj.options) ? obj.options : [];
  return {
    intro: null,
    questions: [
      {
        id: "q1",
        prompt,
        header: null,
        multi_select: false,
        options: optionsRaw
          .map(normaliseOption)
          .filter((o): o is AskUserOption => o !== null),
        allow_free_text: true,
        placeholder: null,
      },
    ],
  };
}

const LETTERS = "ABCDEFGH"; // matches MAX_OPTIONS=8

/** hover/disabled 伪类承接（原 Tailwind hover 与 disabled 变体）。 */
const AskUserStyleBlock = () => (
  <style>{`
.dsh-au-tab:hover:not(:disabled){border-color:rgba(15,23,42,.25)!important;color:${FG}!important;}
.dsh-au-tab:disabled{cursor:not-allowed;opacity:.6;}
.dsh-au-prev:hover:not(:disabled){border-color:rgba(15,23,42,.3)!important;background:rgba(15,23,42,.04)!important;}
.dsh-au-prev:disabled{cursor:not-allowed;opacity:.4;}
.dsh-au-next:hover:not(:disabled){opacity:.9;}
.dsh-au-next:disabled,.dsh-au-submit:disabled{cursor:not-allowed;opacity:.4;}
.dsh-au-submit:hover:not(:disabled){opacity:.9;}
.dsh-au-opt:hover:not(:disabled){border-color:rgba(15,23,42,.3)!important;background:#f8f8f8!important;}
.dsh-au-opt:hover:not(:disabled) .dsh-au-opt-badge{background:#e7e8ea!important;color:${FG}!important;}
.dsh-au-opt:disabled{cursor:not-allowed;opacity:.6;}
.dsh-au-custom:hover:not(:disabled){border-color:rgba(15,23,42,.3)!important;background:rgba(15,23,42,.03)!important;color:${FG}!important;}
.dsh-au-custom:disabled{cursor:not-allowed;opacity:.6;}
.dsh-au-resolved-toggle:hover:not(:disabled){background:rgba(100,116,139,.025);}
.dsh-au-chevron-collapsed{transform:rotate(-90deg);}
.dsh-au-custom-input::placeholder{color:rgba(100,116,139,.8);}
  `}</style>
);

/**
 * Render the ``ask_user`` card.
 *
 * Two visual modes share the same outer container so the card stays
 * in place in the message stream — never unmounts. Switches from
 * ``interactive`` (the agent is still paused) to ``resolved`` (the
 * user has submitted) once a ``progress`` event with
 * ``ask_user_resolved=true`` arrives in the message events.
 */
export const AskUserOptions = memo(function AskUserOptions({
  data,
  onSubmit,
  collapsible,
  defaultCollapsed,
}: {
  data: AskUserCardData;
  onSubmit: (payload: {
    text?: string;
    answers?: Array<{ questionId: string; text: string }>;
  }) => void;
  /** When true, the resolved Q&A card renders with an inline toggle so
   * the user can hide / show the question + answer summary. Resolved cards
   * default to collapsible+collapsed (the Q&A history stays addressable
   * without dominating the bubble); callers can override explicitly —
   * research keeps its own phase-driven rule. */
  collapsible?: boolean;
  /** Only honoured when ``collapsible`` is true. */
  defaultCollapsed?: boolean;
}) {
  if (data.resolved) {
    return (
      <>
        <AskUserStyleBlock />
        <ResolvedAskUserCard
          payload={data.payload}
          answers={data.answers ?? []}
          collapsible={collapsible ?? true}
          defaultCollapsed={defaultCollapsed ?? true}
        />
      </>
    );
  }
  return (
    <>
      <AskUserStyleBlock />
      <InteractiveAskUserCard payload={data.payload} onSubmit={onSubmit} />
    </>
  );
});
AskUserOptions.displayName = "AskUserOptions";

// ---------- interactive mode ----------

const InteractiveAskUserCard = memo(function InteractiveAskUserCard({
  payload,
  onSubmit,
}: {
  payload: AskUserPayload;
  onSubmit: (payload: {
    text?: string;
    answers?: Array<{ questionId: string; text: string }>;
  }) => void;
}) {
  const totalQuestions = payload.questions.length;

  // Picked option labels per question. Single-select questions hold at
  // most one entry; multi-select questions accumulate toggled labels.
  const [picks, setPicks] = useState<Record<string, string[]>>({});
  // Sticky free-text draft per question. Preserved across option picks
  // and tab switches so the user never loses what they typed.
  const [customText, setCustomText] = useState<Record<string, string>>({});
  // Whether the free-text input is an active choice for a question.
  // Drives both textarea visibility and the "picked" visual state. On
  // multi-select questions it coexists with picked options.
  const [customSelected, setCustomSelected] = useState<Record<string, boolean>>(
    {},
  );
  const [activeIdx, setActiveIdx] = useState(0);
  const [submitted, setSubmitted] = useState(false);

  const activeQuestion = payload.questions[activeIdx] ?? payload.questions[0];

  // Committed answer per question, derived from picks + free text.
  // Multi-select answers join labels with ", " — the same flat string
  // travels to the backend, so the ``{text, answers}`` submit protocol
  // is unchanged.
  const answers = useMemo(() => {
    const out: Record<string, string> = {};
    for (const q of payload.questions) {
      const picked = picks[q.id] ?? [];
      const custom = customSelected[q.id]
        ? (customText[q.id] ?? "").trim()
        : "";
      if (q.multi_select) {
        const parts = [...picked];
        if (custom) parts.push(custom);
        out[q.id] = parts.join(", ");
      } else {
        out[q.id] = customSelected[q.id] ? custom : (picked[0] ?? "");
      }
    }
    return out;
  }, [payload.questions, picks, customText, customSelected]);

  const allAnswered = useMemo(
    () =>
      payload.questions.every((q) => (answers[q.id] ?? "").trim().length > 0),
    [payload.questions, answers],
  );

  const handleSubmit = useCallback(() => {
    if (submitted) return;
    setSubmitted(true);
    const list: Array<{ questionId: string; text: string }> =
      payload.questions.map((q) => ({
        questionId: q.id,
        text: (answers[q.id] ?? "").trim(),
      }));
    // Always include a flat ``text`` synopsis for back-compat with any
    // older server path that only looks at ``text``.
    const flat = list
      .map(({ text }) => text || "(skipped)")
      .filter((s) => s !== "(skipped)")
      .join(" | ");
    onSubmit({ text: flat, answers: list });
  }, [submitted, payload.questions, answers, onSubmit]);

  const pickOption = useCallback(
    (question: AskUserQuestion, label: string) => {
      const qid = question.id;
      if (question.multi_select) {
        // Toggle — no auto-advance; the user may pick several.
        setPicks((prev) => {
          const cur = prev[qid] ?? [];
          const next = cur.includes(label)
            ? cur.filter((l) => l !== label)
            : [...cur, label];
          return { ...prev, [qid]: next };
        });
        return;
      }
      setPicks((prev) => ({ ...prev, [qid]: [label] }));
      setCustomSelected((prev) => ({ ...prev, [qid]: false }));
      // Single-select pick answers this question — hop to the next
      // unanswered one so the flow needs no extra "Next" click
      // (mirrors Claude Code's AskUserQuestion card).
      if (totalQuestions > 1) {
        for (let step = 1; step < totalQuestions; step++) {
          const j = (activeIdx + step) % totalQuestions;
          const other = payload.questions[j];
          if (other.id === qid) continue;
          if (!(answers[other.id] ?? "").trim()) {
            setActiveIdx(j);
            break;
          }
        }
      }
    },
    [totalQuestions, activeIdx, payload.questions, answers],
  );

  const selectCustom = useCallback((question: AskUserQuestion) => {
    setCustomSelected((prev) => ({ ...prev, [question.id]: true }));
    if (!question.multi_select) {
      // Mutually exclusive with option picks on single-select.
      setPicks((prev) => ({ ...prev, [question.id]: [] }));
    }
  }, []);

  const updateCustomText = useCallback((qid: string, text: string) => {
    setCustomText((prev) => ({ ...prev, [qid]: text }));
    setCustomSelected((prev) => ({ ...prev, [qid]: true }));
  }, []);

  return (
    <div
      style={{
        marginTop: 12, borderRadius: 16, border: `1px solid ${BORDER}`,
        background: CARD, padding: 16,
        boxShadow: "0 1px 2px rgba(0,0,0,0.04), 0 4px 14px rgba(0,0,0,0.04)",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div
          style={{
            display: "flex", height: 24, width: 24, flexShrink: 0,
            alignItems: "center", justifyContent: "center", borderRadius: 999,
            background: "rgba(15,23,42,0.08)", fontSize: 12, fontWeight: 600,
            color: "rgba(15,23,42,0.7)",
          }}
        >
          ?
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.375, color: FG }}>
            {payload.intro || "请作答以继续。"}
          </div>
          <div style={{ marginTop: 2, fontSize: 11, color: MUTED_FG }}>
            {submitted
              ? "正在发送回答…"
              : totalQuestions > 1
                ? `${totalQuestions} 个问题 — 点击标签切换。`
                : "选择一个选项或输入自定义回复以继续。"}
          </div>
        </div>
      </div>

      {totalQuestions > 1 ? (
        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 6 }}>
          {payload.questions.map((q, idx) => {
            const isActive = idx === activeIdx;
            const answered = (answers[q.id] ?? "").trim().length > 0;
            return (
              <button
                key={q.id}
                type="button"
                onClick={() => setActiveIdx(idx)}
                disabled={submitted}
                data-testid="ask-user-tab"
                style={{
                  display: "flex", alignItems: "center", gap: 6, borderRadius: 999,
                  border: `1px solid ${isActive ? "rgba(15,23,42,.35)" : BORDER}`,
                  background: isActive ? "rgba(15,23,42,.05)" : "transparent",
                  color: isActive ? FG : MUTED_FG,
                  padding: "4px 10px", fontSize: 11.5, fontWeight: 500,
                  transition: "all .15s", cursor: submitted ? "not-allowed" : "pointer",
                }}
                className="dsh-au-tab"
              >
                <span
                  style={{
                    display: "flex", height: 16, width: 16, flexShrink: 0,
                    alignItems: "center", justifyContent: "center", borderRadius: 999,
                    fontSize: 10,
                    background: answered ? PRIMARY : "rgba(241,245,249,.6)",
                    color: answered ? PRIMARY_FG : MUTED_FG,
                  }}
                >
                  {answered ? "✓" : idx + 1}
                </span>
                <span style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {q.header || q.prompt}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}

      <QuestionBody
        key={activeQuestion.id}
        question={activeQuestion}
        pickedLabels={picks[activeQuestion.id] ?? []}
        customDraft={customText[activeQuestion.id] ?? ""}
        customSelected={!!customSelected[activeQuestion.id]}
        locked={submitted}
        onPickOption={(label) => pickOption(activeQuestion, label)}
        onSelectCustom={() => selectCustom(activeQuestion)}
        onCustomTextChange={(text) => updateCustomText(activeQuestion.id, text)}
      />

      <div
        style={{
          marginTop: 12, display: "flex", alignItems: "center",
          justifyContent: "space-between", gap: 8,
          borderTop: "1px solid rgba(226,232,240,.6)", paddingTop: 12,
        }}
      >
        <div style={{ display: "flex", minWidth: 0, flex: 1, alignItems: "center" }}>
          {totalQuestions > 1 && activeIdx > 0 ? (
            <button
              type="button"
              onClick={() => setActiveIdx((idx) => Math.max(0, idx - 1))}
              disabled={submitted}
              data-testid="ask-user-prev"
              className="dsh-au-prev"
              style={{
                display: "inline-flex", alignItems: "center", gap: 4, borderRadius: 6,
                border: `1px solid ${BORDER}`, background: "transparent",
                padding: "6px 10px", fontSize: 12, fontWeight: 500, color: FG,
                transition: "all .15s", cursor: submitted ? "not-allowed" : "pointer",
              }}
            >
              <LeftOutlined style={{ fontSize: 12 }} />
              <span>上一题</span>
            </button>
          ) : (
            <div style={{ fontSize: 11.5, color: MUTED_FG }}>
              {allAnswered
                ? "所有问题已回答。"
                : "未回答的问题将作为「已跳过」提交。"}
            </div>
          )}
        </div>
        {totalQuestions > 1 && activeIdx < totalQuestions - 1 ? (
          <button
            type="button"
            onClick={() =>
              setActiveIdx((idx) => Math.min(totalQuestions - 1, idx + 1))
            }
            disabled={submitted}
            data-testid="ask-user-next"
            className="dsh-au-next"
            style={{
              display: "inline-flex", alignItems: "center", gap: 4, borderRadius: 6,
              background: PRIMARY, padding: "6px 12px", fontSize: 12,
              fontWeight: 500, color: PRIMARY_FG, border: "none",
              transition: "all .15s", cursor: submitted ? "not-allowed" : "pointer",
            }}
          >
            <span>下一题</span>
            <RightOutlined style={{ fontSize: 12 }} />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitted}
            data-testid="ask-user-submit"
            className="dsh-au-submit"
            style={{
              borderRadius: 6, background: PRIMARY, padding: "6px 12px",
              fontSize: 12, fontWeight: 500, color: PRIMARY_FG, border: "none",
              transition: "all .15s", cursor: submitted ? "not-allowed" : "pointer",
            }}
          >
            {totalQuestions > 1 ? "提交回答" : "提交"}
          </button>
        )}
      </div>
    </div>
  );
});
InteractiveAskUserCard.displayName = "InteractiveAskUserCard";

const QuestionBody = memo(function QuestionBody({
  question,
  pickedLabels,
  customDraft,
  customSelected,
  locked,
  onPickOption,
  onSelectCustom,
  onCustomTextChange,
}: {
  question: AskUserQuestion;
  pickedLabels: string[];
  customDraft: string;
  customSelected: boolean;
  locked: boolean;
  onPickOption: (label: string) => void;
  onSelectCustom: () => void;
  onCustomTextChange: (text: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (customSelected) {
      textareaRef.current?.focus();
    }
  }, [customSelected]);

  return (
    <>
      <div style={{ marginTop: 12, fontSize: 14, fontWeight: 500, lineHeight: 1.375, color: FG }}>
        {question.prompt}
        {question.multi_select ? (
          <span style={{ marginLeft: 6, fontSize: 11, fontWeight: 400, color: MUTED_FG }}>
            可多选。
          </span>
        ) : null}
      </div>

      {question.options.length > 0 ? (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          {question.options.map((option, idx) => {
            const letter = LETTERS[idx] ?? String(idx + 1);
            const isPicked = question.multi_select
              ? pickedLabels.includes(option.label)
              : !customSelected && pickedLabels[0] === option.label;
            return (
              <button
                key={`${letter}-${option.label}`}
                type="button"
                onClick={() => !locked && onPickOption(option.label)}
                disabled={locked}
                data-testid="ask-user-option"
                className="dsh-au-opt"
                style={{
                  display: "flex", width: "100%", alignItems: "center", gap: 12,
                  borderRadius: 12, border: `1px solid ${isPicked ? "rgba(79,70,229,.7)" : BORDER}`,
                  background: isPicked ? "#f3f2fe" : CARD, color: FG,
                  padding: "8px 12px", textAlign: "left", transition: "all .15s",
                  cursor: locked ? "not-allowed" : "pointer",
                }}
              >
                <span
                  className={isPicked ? "" : "dsh-au-opt-badge"}
                  style={{
                    display: "flex", height: 24, width: 24, flexShrink: 0,
                    alignItems: "center", justifyContent: "center", borderRadius: 6,
                    fontSize: 12, fontWeight: 600, transition: "all .15s",
                    background: isPicked ? PRIMARY : "rgba(241,245,249,.7)",
                    color: isPicked ? PRIMARY_FG : MUTED_FG,
                  }}
                >
                  {question.multi_select && isPicked ? "✓" : letter}
                </span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{ display: "block", fontSize: 13.5, lineHeight: 1.375 }}>
                    {option.label}
                  </span>
                  {option.description ? (
                    <span style={{ marginTop: 2, display: "block", fontSize: 11.5, lineHeight: 1.375, color: MUTED_FG }}>
                      {option.description}
                    </span>
                  ) : null}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}

      {question.allow_free_text ? (
        <div style={{ marginTop: 6 }}>
          {customSelected ? (
            <div
              style={{
                display: "flex", alignItems: "flex-start", gap: 12, borderRadius: 12,
                border: "1px solid rgba(79,70,229,.7)",
                background: "#f6f6fe", padding: "8px 12px", transition: "all .15s",
              }}
            >
              <span
                style={{
                  marginTop: 2, display: "flex", height: 24, width: 24, flexShrink: 0,
                  alignItems: "center", justifyContent: "center", borderRadius: 6,
                  background: PRIMARY, fontSize: 12, fontWeight: 600, color: PRIMARY_FG,
                }}
              >
                {LETTERS[question.options.length] ?? "+"}
              </span>
              <textarea
                ref={textareaRef}
                value={customDraft}
                onChange={(event) => onCustomTextChange(event.target.value)}
                placeholder={question.placeholder ?? "输入回复…"}
                rows={3}
                disabled={locked}
                data-testid="ask-user-custom-input"
                className="dsh-au-custom-input"
                style={{
                  minHeight: 36, width: "100%", resize: "vertical", background: "transparent",
                  fontSize: 13.5, lineHeight: 1.375, color: FG, outline: "none",
                  border: "none", opacity: locked ? 0.6 : 1,
                }}
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => !locked && onSelectCustom()}
              disabled={locked}
              data-testid="ask-user-custom"
              className="dsh-au-custom"
              style={{
                display: "flex", width: "100%", alignItems: "center", gap: 12,
                borderRadius: 12, border: `1px dashed ${BORDER}`, background: "transparent",
                padding: "8px 12px", textAlign: "left", fontSize: 13, color: MUTED_FG,
                transition: "all .15s", cursor: locked ? "not-allowed" : "pointer",
              }}
            >
              <span
                style={{
                  display: "flex", height: 24, width: 24, flexShrink: 0,
                  alignItems: "center", justifyContent: "center", borderRadius: 6,
                  background: "rgba(241,245,249,.7)", fontSize: 12, fontWeight: 600,
                  color: MUTED_FG,
                }}
              >
                {LETTERS[question.options.length] ?? "+"}
              </span>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {customDraft.trim()
                  ? `其他：${customDraft.trim()}`
                  : "其他 — 自定义回复…"}
              </span>
            </button>
          )}
        </div>
      ) : null}
    </>
  );
});
QuestionBody.displayName = "QuestionBody";

// ---------- resolved (read-only) mode ----------

const ResolvedAskUserCard = memo(function ResolvedAskUserCard({
  payload,
  answers,
  collapsible,
  defaultCollapsed,
}: {
  payload: AskUserPayload;
  answers: AskUserAnswer[];
  collapsible: boolean;
  defaultCollapsed: boolean;
}) {
  // Null means "follow defaultCollapsed"; once the user toggles, their
  // explicit choice wins across research-progress re-renders.
  const [manualCollapsed, setManualCollapsed] = useState<boolean | null>(null);
  const collapsed = collapsible ? (manualCollapsed ?? defaultCollapsed) : false;

  const toggleCollapsed = useCallback(() => {
    setManualCollapsed((current) => !(current ?? defaultCollapsed));
  }, [defaultCollapsed]);

  const byId = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of answers) map.set(a.questionId, a.text);
    return map;
  }, [answers]);

  const answeredCount = useMemo(() => {
    let n = 0;
    for (const q of payload.questions) {
      if ((byId.get(q.id) ?? "").trim().length > 0) n += 1;
    }
    return n;
  }, [payload.questions, byId]);

  // Match the look-and-feel of ``ResearchOutlineEditor`` so the two
  // collapsible cards stack consistently in the merged research bubble.
  return (
    <div
      style={{
        margin: "8px 0", borderRadius: 8,
        border: "1px solid rgba(226,232,240,.3)", background: BG,
        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
      }}
    >
      <button
        type="button"
        disabled={!collapsible}
        onClick={collapsible ? toggleCollapsed : undefined}
        className="dsh-au-resolved-toggle"
        style={{
          display: "block", width: "100%", textAlign: "left",
          borderBottom: collapsed ? "none" : "1px solid rgba(226,232,240,.2)",
          padding: "8px 16px", cursor: collapsible ? "pointer" : "default",
          background: "transparent",
          borderLeft: "none", borderRight: "none", borderTop: "none",
          transition: "background .15s",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {collapsible && (
            <DownOutlined
              className={collapsed ? "dsh-au-chevron-collapsed" : ""}
              style={{
                fontSize: 10, flexShrink: 0, color: "rgba(100,116,139,.5)",
                transition: "transform .15s",
              }}
            />
          )}
          <h3 style={{ fontSize: 13, fontWeight: 600, color: FG, margin: 0 }}>
            你的回答
          </h3>
          {collapsible && collapsed && (
            <span style={{ fontSize: 11, color: "rgba(100,116,139,.45)" }}>
              · {answeredCount}/{payload.questions.length} 已答
            </span>
          )}
        </div>
      </button>
      {!collapsed && (
        <div>
          {payload.questions.map((q, index) => {
            const value = (byId.get(q.id) ?? "").trim();
            return (
              <div
                key={q.id}
                style={{
                  display: "flex", alignItems: "flex-start", gap: 8,
                  padding: "6px 12px",
                  borderTop: index > 0 ? "1px solid rgba(226,232,240,.15)" : "none",
                }}
              >
                <span
                  style={{
                    marginTop: 3, width: 16, flexShrink: 0, textAlign: "center",
                    fontSize: 11, fontWeight: 500, fontVariantNumeric: "tabular-nums",
                    lineHeight: 1.25, color: "rgba(100,116,139,.3)",
                  }}
                >
                  {index + 1}
                </span>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, lineHeight: 1.375, color: FG }}>
                    {q.prompt}
                  </div>
                  <div style={{ fontSize: 11, lineHeight: 1.375, color: "rgba(100,116,139,.7)" }}>
                    {value ? (
                      value
                    ) : (
                      <span style={{ color: "var(--text-tertiary, #999)" }}>（已跳过）</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
});
ResolvedAskUserCard.displayName = "ResolvedAskUserCard";
