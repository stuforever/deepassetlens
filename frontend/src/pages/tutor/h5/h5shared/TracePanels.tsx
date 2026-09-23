/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/TracePanels.tsx，2696 行）。
 * 消费方：h5shared/QuizFollowupTabBody.tsx（批9 SA-A，import { StreamingStatus, TraceFlow }）；
 * 原仓同链消费方还有 ChatMessages/PartnerChat/SubagentRunTranscript/SubagentTabBody（后续批可迁位复用）。
 * 替换点（全批通用约定）：
 * 1. 删除 "use client"；
 * 2. lucide → @ant-design/icons：ChevronDown→DownOutlined（"-rotate-90" 折叠旋转→
 *    style.transform rotate(-90deg) + transition）、Loader2→LoadingOutlined（animate-spin→spin）、
 *    Sparkles→StarOutlined（size/strokeWidth→style.fontSize，antd 图标无 strokeWidth 参数，登记）；
 * 3. MarkdownRenderer→../../admin/MarkdownRenderer（批8 等价 stub，props 契约 content/variant
 *    含 "trace"，逐字保留调用）；trace-timing/trace-tools→本目录同名件（本波次同步交付）；
 *    StreamEvent→../../admin/unified-ws（批8 件）；
 * 4. i18n t()→zhT()：ZH 表译自原仓 locales/zh/app.json 逐键核对（含 research.stage.* 8 键、
 *    "{{name}} ……" 状态系列、"Using/Running {{param}}" 等）；zh/app.json 无 "Exploring" 键，
 *    按 i18next 缺键回退行为直出原 key；{{param}} 手工插值（与 ContextBudgetChip 同法）；
 * 5. Tailwind→内联样式（逐类换算，批量8 token：muted-foreground→#6b7280、border→#e4e4e7、
 *    primary→#1677ff、red-400/80→rgba(248,113,113,0.8)、bg-[#292524]/text-[#D6D3D1] 字面）；
 *    group-hover/row→局部 hovered state（与 ContextReferenceTree 同法）；
 *    line-clamp-2/3→WebkitLineClamp；truncate→ellipsis 三件套；tabular-nums→fontVariantNumeric；
 *    ScrollableTraceBody 的 className 参数（Tailwind 串）→style 对象参数（登记换算）；
 * 6. 原仓 globals.css 工具类 dt-breathing-text / dt-mark-pulse→ensureTraceStyles() 注入等价
 *    @keyframes（参数逐字取自原仓 globals.css：dt-breathing opacity .45↔1 1.8s
 *    cubic-bezier(.4,0,.6,1) infinite；dt-mark-pulse scale .9↔1.08 2.4s 同 bezier、
 *    transform-box fill-box），幂等注入一次；
 * 7. 【登记·动画降级】AssistantActivity 的嵌套 trace 展开/收起原为
 *    grid-rows-[0fr]→[1fr] + opacity 过渡（transition-[grid-template-rows,opacity]
 *    duration-300 ease-out）→ 降级为条件渲染（open 即渲染）；安装 framer-motion 后可恢复；
 * 8. 手绘 Mark 系列（ReasoningMark/ToolMark/CommandMark 等 11 个）为原仓自绘 SVG，
 *    非 lucide，逐字保留（size/strokeWidth/className props 契约不变）。
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type CSSProperties,
  type ReactNode,
} from "react";
import {
  DownOutlined,
  LoadingOutlined,
  StarOutlined,
} from "@ant-design/icons";
import MarkdownRenderer from "../../admin/MarkdownRenderer";
import { formatTurnDuration, getTurnDurationSeconds } from "./trace-timing";
import {
  describeProviderTool,
  formatProgressLabel,
  type ToolProvider,
} from "./trace-tools";
import type { StreamEvent } from "../../admin/unified-ws";
import { DT } from "./dtStyle";

const MONO_FONT =
  "ui-monospace, SFMono-Regular, Consolas, 'Courier New', monospace";

// zh/app.json 原译文替换表（t() 中文直出；"Exploring" 缺键按 i18next 回退直出原 key）。
const ZH: Record<string, string> = {
  "Running command": "运行命令",
  "Running code": "运行代码",
  "Searching knowledge": "检索知识库",
  "Listing knowledge base files": "查看知识库文件清单",
  "Searching the web": "联网搜索",
  "Searching papers": "检索论文",
  "Fetching page": "抓取网页",
  "Reading skill": "读取技能",
  "Loading tools": "加载工具",
  "Reading source": "读取来源",
  "Reading file": "读取文件",
  "Writing file": "写入文件",
  "Editing file": "编辑文件",
  "Listing files": "列出文件",
  "Writing note": "记录笔记",
  "Recalling memory": "检索记忆",
  "Saving memory": "保存记忆",
  Reasoning: "推理",
  Brainstorming: "头脑风暴",
  "Asking you": "向你提问",
  "Querying GitHub": "查询 GitHub",
  "Analyzing figure": "分析图形",
  Visualizing: "生成图示",
  Animating: "生成动画",
  "Context exploration": "上下文调查",
  Retrieve: "检索",
  "Tool call": "工具调用",
  "Round {{n}}": "第 {{n}} 轮",
  "Step {{n}}": "第 {{n}} 步",
  Plan: "规划",
  Observe: "观察",
  Question: "题目",
  Response: "回复",
  Reflecting: "反思",
  Thought: "思考",
  "Generating {{label}}": "正在生成 {{label}}",
  "Writing {{label}}": "正在撰写 {{label}}",
  Tool: "工具",
  "Raw logs": "原始日志",
  Sources: "来源",
  "{{count}} round": "{{count}} 轮",
  "research.stage.understand.title": "理解问题",
  "research.stage.understand.hint": "先澄清主题与研究目标。",
  "research.stage.decompose.title": "拆解主题",
  "research.stage.decompose.hint": "把问题拆成可检索、可学习的子主题。",
  "research.stage.evidence.title": "检索证据",
  "research.stage.evidence.hint": "结合所选 sources 收集和整理证据。",
  "research.stage.result.title": "形成结果",
  "research.stage.result.hint": "把证据整理成最终输出。",
  "Decomposing Target": "Decomposing Target",
  "Researching Topic #{{n}}": "Researching Topic #{{n}}",
  "Researching Topic": "Researching Topic",
  "Reporting Intro": "Reporting Intro",
  "Reporting Outline": "Reporting Outline",
  "Reporting Conclusion": "Reporting Conclusion",
  "Reporting Section #{{n}}": "Reporting Section #{{n}}",
  "Reporting Section": "Reporting Section",
  Reporting: "撰写报告",
  "Exploring your context…": "正在调查你的上下文…",
  "{{name}} Reasoning…": "{{name}} 推理中…",
  "Tool Calling…": "调用工具中…",
  "{{name}} Planning…": "{{name}} 规划中…",
  "{{name}} Drafting…": "{{name}} 撰写中…",
  "{{name}} Responding…": "{{name}} 回答中…",
  "{{name}} Exploring…": "{{name}} 探索中…",
  "{{name}} Quizzing…": "{{name}} 出题中…",
  "{{name}} Reflecting…": "{{name}} 反思中…",
  "DeepTutor responded.": "已完成",
  "Using {{service}}": "调用 {{service}}",
  "Running {{app}}": "运行 {{app}}",
};

type TranslateFn = (
  key: string,
  opts?: Record<string, unknown>,
) => string;

function zhT(key: string, opts?: Record<string, unknown>): string {
  const tpl = ZH[key] ?? key;
  if (!opts) return tpl;
  return tpl.replace(/\{\{(\w+)\}\}/g, (match, name: string) =>
    name in opts ? String(opts[name]) : match,
  );
}

/* 原仓 globals.css 工具类的等价注入（幂等）——见文件头替换点 6。 */
function ensureTraceStyles() {
  if (typeof document === "undefined") return;
  if (document.getElementById("dt-trace-style-block")) return;
  const el = document.createElement("style");
  el.id = "dt-trace-style-block";
  el.textContent = `
@keyframes dt-breathing { 0%, 100% { opacity: 0.45; } 50% { opacity: 1; } }
@keyframes dt-mark-pulse { 0%, 100% { transform: scale(0.9); } 50% { transform: scale(1.08); } }
.dt-breathing-text { animation: dt-breathing 1.8s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
.dt-mark-pulse { animation: dt-mark-pulse 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite; transform-origin: center; transform-box: fill-box; }
`;
  document.head.appendChild(el);
}

type TraceMetadata = {
  call_id?: string;
  phase?: string;
  label?: string;
  call_kind?: string;
  trace_role?: string;
  trace_group?: string;
  trace_kind?: string;
  trace_id?: string;
  call_state?: string;
  // Set on the per-round ``call_status`` marker by the chat single loop:
  // "narration" = a tool-calling round's text (stays in the trace),
  // "finish"    = the final, tool-less round's text (the bubble answer).
  // The "finish" marker is the signal that the turn entered its final
  // answer phase.
  call_role?: string;
  // Set by the chat pipeline on the final iteration's reasoning sub-trace.
  // Marks "this sub-trace's text has been re-emitted as the final-response
  // CONTENT event in the same turn, so don't render it as a duplicate row."
  absorbed_into_final?: boolean;
  step_id?: string;
  round?: number;
  query?: string;
  tool_name?: string;
  // Which external provider is running, stamped by the tool dispatcher from the
  // tool object itself. `"mcp"` or `"cli"`; absent for a built-in. Read rather
  // than parsed out of the tool name: `mcp_<server>_<tool>` is ambiguous the
  // moment a server's own name contains an underscore.
  tool_source?: string;
  tool_provider?: string;
  // On a `trace_kind="tool_progress"` event: how far along the provider says it
  // is (0–1), and how long a CLI app has been running.
  progress_fraction?: number;
  elapsed_s?: number;
  block_id?: string;
  trace_layer?: string;
  output_mode?: string;
  quality?: string;
  sources?: Array<Record<string, unknown>>;
  // Set by deep_question's QuestionPipeline on per-question content events
  // (call_kind="quiz_question_emitted"). 0-based; display as 1-based.
  question_index?: number;
  total_questions?: number;
  qa_pair?: Record<string, unknown>;
  // Set by deep_research so the top-level trace row can show the active
  // research/reporting sub-state instead of generic reasoning/tool labels.
  research_status_key?: string;
  topic_index?: number | string;
  topic_title?: string;
  report_part?: string;
  section_index?: number | string;
  section_count?: number | string;
  section_title?: string;
  // Set on each native event streamed from a connected subagent
  // (trace_kind="subagent_event"): the channel it came from and which consult.
  subagent_channel?: string;
  subagent_kind?: string;
  subagent_name?: string;
  consult_index?: number;
  // Correlates a fill-in tool's start/finish events (e.g. a web search) so the
  // transcript collapses them into one evolving row.
  subagent_merge_id?: string;
};

type ResearchStageId = "understand" | "decompose" | "evidence" | "result";

type ResearchStageCard = {
  id: ResearchStageId;
  title: string;
  hint: string;
  events: StreamEvent[];
};

// `title` and `hint` are i18n keys resolved via `t(...)` at render time so the
// stage banner follows the active UI language instead of being locked to one.
const RESEARCH_STAGE_SPECS: Array<{
  id: ResearchStageId;
  titleKey: string;
  hintKey: string;
}> = [
  {
    id: "understand",
    titleKey: "research.stage.understand.title",
    hintKey: "research.stage.understand.hint",
  },
  {
    id: "decompose",
    titleKey: "research.stage.decompose.title",
    hintKey: "research.stage.decompose.hint",
  },
  {
    id: "evidence",
    titleKey: "research.stage.evidence.title",
    hintKey: "research.stage.evidence.hint",
  },
  {
    id: "result",
    titleKey: "research.stage.result.title",
    hintKey: "research.stage.result.hint",
  },
];

type TraceItem = { callId: string; events: StreamEvent[] };
type DisplayItem =
  | { kind: "trace"; trace: TraceItem }
  | { kind: "step"; stepId: string; traces: TraceItem[] };

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Collapse whitespace and clip to ``max`` chars with an ellipsis. */
function clip(value: string, max = 56) {
  const text = value.replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

/** Last path segment (handles both / and \\ separators). */
function basename(path: string) {
  const trimmed = path.replace(/[/\\]+$/, "");
  const parts = trimmed.split(/[/\\]/);
  return parts[parts.length - 1] || trimmed;
}

/** A trace-row glyph: either a hand-drawn Mark or a lucide icon. Both accept
 *  this prop subset, so the row renders them uniformly. */
type GlyphProps = { size?: number; strokeWidth?: number; className?: string };
type GlyphComponent = ComponentType<GlyphProps>;

type ToolDescriptor = {
  Icon: GlyphComponent;
  /** Human action verb (already translated). */
  verb: string;
  /** The concrete artifact this call touched (file, query, …), or null. */
  chip: string | null;
  /** Render the chip in a mono face (code / paths / commands). */
  mono: boolean;
};

/**
 * Maps a tool call to the activity-row vocabulary: a hand-drawn glyph (the
 * same organic mark family as the status header — see {@link CommandMark}
 * &c.), a human action verb ("Running command", "Reading skill"), and a
 * compact chip naming the artifact it acted on (the command, the file, the
 * query). Falls back to a humanized tool name + generic mark for unknown
 * tools so new tools still read sensibly without a code change.
 *
 * `provider` short-circuits the switch for tools that come from an MCP server
 * or an installed CLI app. Their names are *generated*, so the fallback would
 * title-case a machine string — "Mcp Wolfram Wolframalpha" — and tell the reader
 * neither which service is being used nor what it was asked to do.
 */
function describeToolCall(
  toolName: string,
  args: Record<string, unknown> | undefined,
  t: (key: string, opts?: Record<string, unknown>) => string,
  provider?: ToolProvider | null,
): ToolDescriptor {
  const a = args ?? {};
  const str = (value: unknown) =>
    typeof value === "string" ? value.trim() : "";

  // An external provider's row is decided in `lib/trace-tools` — the whole
  // decision is data there, so it is unit-tested; only the glyph is resolved
  // here, where the marks live.
  const providerRow = describeProviderTool(toolName, args, provider, t);
  if (providerRow) {
    return {
      Icon: providerRow.glyph === "link" ? LinkMark : CommandMark,
      verb: providerRow.verb,
      chip: providerRow.chip,
      mono: providerRow.mono,
    };
  }
  const host = (url: string) => {
    if (!url) return "";
    try {
      return new URL(url).hostname.replace(/^www\./, "");
    } catch {
      return url;
    }
  };

  switch (toolName) {
    case "exec":
      return {
        Icon: CommandMark,
        verb: t("Running command"),
        chip: clip(str(a.command), 48) || null,
        mono: true,
      };
    case "code_execution":
      return {
        Icon: CommandMark,
        verb: t("Running code"),
        chip: str(a.language) || t("Code"),
        mono: true,
      };
    case "rag":
      return {
        Icon: KnowledgeMark,
        verb: t("Searching knowledge"),
        chip: clip(str(a.query)) || null,
        mono: false,
      };
    case "kb_files":
      return {
        Icon: KnowledgeMark,
        verb: t("Listing knowledge base files"),
        chip: str(a.kb_name) || null,
        mono: false,
      };
    case "web_search":
      return {
        Icon: GlobeMark,
        verb: t("Searching the web"),
        chip: clip(str(a.query)) || null,
        mono: false,
      };
    case "paper_search":
      return {
        Icon: LoupeMark,
        verb: t("Searching papers"),
        chip: clip(str(a.query)) || null,
        mono: false,
      };
    case "web_fetch":
      return {
        Icon: GlobeMark,
        verb: t("Fetching page"),
        chip: host(str(a.url)) || null,
        mono: true,
      };
    case "read_skill":
      return {
        Icon: BookMark,
        verb: t("Reading skill"),
        chip: str(a.name) || null,
        mono: false,
      };
    case "load_tools": {
      const names = Array.isArray(a.names)
        ? (a.names as unknown[]).map((n) => String(n))
        : [];
      return {
        Icon: ToolMark,
        verb: t("Loading tools"),
        chip: names.join(", ") || null,
        mono: true,
      };
    }
    case "read_source":
      return {
        Icon: BookMark,
        verb: t("Reading source"),
        chip: str(a.source_id) || null,
        mono: false,
      };
    case "read_file":
      return {
        Icon: BookMark,
        verb: t("Reading file"),
        chip: basename(str(a.path)) || null,
        mono: true,
      };
    case "write_file":
      return {
        Icon: RespondingMark,
        verb: t("Writing file"),
        chip: basename(str(a.path)) || null,
        mono: true,
      };
    case "edit_file":
      return {
        Icon: RespondingMark,
        verb: t("Editing file"),
        chip: basename(str(a.path)) || null,
        mono: true,
      };
    case "list_dir":
      return {
        Icon: BookMark,
        verb: t("Listing files"),
        chip: basename(str(a.path)) || null,
        mono: true,
      };
    case "write_note":
      return {
        Icon: RespondingMark,
        verb: t("Writing note"),
        chip: clip(str(a.title), 40) || null,
        mono: false,
      };
    case "read_memory":
      return {
        Icon: MemoryMark,
        verb: t("Recalling memory"),
        chip: null,
        mono: false,
      };
    case "write_memory":
      return {
        Icon: MemoryMark,
        verb: t("Saving memory"),
        chip: null,
        mono: false,
      };
    case "reason":
      return {
        Icon: ReasoningMark,
        verb: t("Reasoning"),
        chip: clip(str(a.query)) || null,
        mono: false,
      };
    case "brainstorm":
      return {
        Icon: ReasoningMark,
        verb: t("Brainstorming"),
        chip: clip(str(a.topic)) || null,
        mono: false,
      };
    case "ask_user":
      return {
        Icon: SpeechMark,
        verb: t("Asking you"),
        chip: null,
        mono: false,
      };
    case "github":
      return {
        Icon: ToolMark,
        verb: t("Querying GitHub"),
        chip: str(a.target) || null,
        mono: true,
      };
    case "geogebra_analysis":
      return {
        Icon: FrameMark,
        verb: t("Analyzing figure"),
        chip: null,
        mono: false,
      };
    case "visualize":
      return {
        Icon: FrameMark,
        verb: t("Visualizing"),
        chip: null,
        mono: false,
      };
    case "math_animator":
      return { Icon: FrameMark, verb: t("Animating"), chip: null, mono: false };
    default:
      return {
        Icon: ToolMark,
        verb: titleCase(toolName),
        chip: null,
        mono: false,
      };
  }
}

function humanizeQuestionId(
  value: string,
  t?: (key: string, opts?: Record<string, unknown>) => string,
) {
  return value.replace(/\bq_(\d+)\b/gi, (_match, n) =>
    t ? t("Question {{n}}", { n }) : `Question ${n}`,
  );
}

export function getTraceMeta(event: StreamEvent): TraceMetadata {
  return (event.metadata ?? {}) as TraceMetadata;
}

function getTraceLabel(
  events: StreamEvent[],
  t?: (key: string, opts?: Record<string, unknown>) => string,
) {
  for (const event of events) {
    const meta = getTraceMeta(event);
    if (meta.label) return humanizeQuestionId(String(meta.label), t);
  }
  const fallback = events[0]?.stage || "trace";
  return humanizeQuestionId(titleCase(fallback), t);
}

/**
 * The external provider this trace's tool belongs to, or null for a built-in.
 *
 * Exported for tests: this and {@link getLatestToolProgress} are the wiring
 * between what the backend stamps on a turn's events and what the row shows, and
 * they are checked against events recorded from a real LLM turn
 * (`tests/fixtures/provider-trace-events.json`).
 *
 * Scanned across the group rather than read off the `tool_call` event alone: the
 * status and progress events carry it too, and a group whose opening event was
 * dropped (a reconnect mid-turn) should still be labelled correctly.
 */
export function getToolProvider(events: StreamEvent[]): ToolProvider | null {
  for (const event of events) {
    const meta = getTraceMeta(event);
    if (meta.tool_source) {
      return {
        source: String(meta.tool_source),
        id: String(meta.tool_provider || ""),
      };
    }
  }
  return null;
}

/** The newest `tool_progress` line in this group, or `""`. */
export function getLatestToolProgress(events: StreamEvent[]): string {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.type !== "progress") continue;
    if (String(getTraceMeta(event).trace_kind || "") !== "tool_progress")
      continue;
    const text = event.content.trim();
    if (text) return formatProgressLabel(text);
  }
  return "";
}

function getTraceCallKind(events: StreamEvent[]) {
  for (const event of events) {
    const meta = getTraceMeta(event);
    if (meta.call_kind) return String(meta.call_kind);
  }
  return "";
}

function getTraceRole(events: StreamEvent[]) {
  for (const event of events) {
    const meta = getTraceMeta(event);
    if (meta.trace_role) return String(meta.trace_role);
  }
  return "";
}

function getTraceGroup(events: StreamEvent[]) {
  for (const event of events) {
    const meta = getTraceMeta(event);
    if (meta.trace_group) return String(meta.trace_group);
  }
  return "";
}

function isTracePending(events: StreamEvent[]) {
  let hasRunning = false;
  let hasTerminal = false;
  for (const event of events) {
    const state = String(getTraceMeta(event).call_state || "");
    if (state === "running") hasRunning = true;
    if (state === "complete" || state === "error") hasTerminal = true;
  }
  return hasRunning && !hasTerminal;
}

function getTraceHeader(
  events: StreamEvent[],
  nested?: boolean,
  t: (key: string, opts?: Record<string, unknown>) => string = (k) => k,
) {
  const label = getTraceLabel(events, t);
  const role = getTraceRole(events);
  const group = getTraceGroup(events);
  const kind = getTraceCallKind(events);
  const meta = getTraceMeta(events[0]);

  let title = label;
  if (
    [
      "math_concept_analysis",
      "math_concept_design",
      "math_code_generation",
      "math_code_retry",
      "math_summary",
      "math_render_output",
    ].includes(kind)
  ) {
    title = label;
  } else if (kind === "context_exploration") {
    // The pre-pass that investigates the turn's attached sources before
    // answering. Noun header for the trace row — the turn-level status row
    // carries the verb form ("Exploring your context…") so the two never
    // read as the same label stacked on itself.
    title = t("Context exploration");
  } else if (role === "retrieve") {
    title = t("Retrieve");
  } else if (role === "explore" || kind === "agent_loop_round") {
    title = t("Exploring");
  } else if (kind === "tool_planning") {
    title = t("Tool call");
  } else if (group === "react_round") {
    if (nested) {
      title = meta.round ? t("Round {{n}}", { n: meta.round }) : label;
    } else {
      const step = meta.step_id ? t("Step {{n}}", { n: meta.step_id }) : "";
      const round = meta.round ? t("Round {{n}}", { n: meta.round }) : label;
      title = [step, round].filter(Boolean).join(" · ");
    }
  } else if (role === "plan" && kind === "llm_planning") {
    title = t("Plan");
  } else if (role === "observe" || kind === "llm_observation") {
    title = t("Observe");
  } else if (role === "quiz_question" || kind === "quiz_question_emitted") {
    // Each quiz question gets its own sub-trace card; index is 0-based in
    // metadata, so display as 1-based for the user.
    const idx = Number(meta.question_index);
    title = Number.isFinite(idx)
      ? t("Question {{n}}", { n: idx + 1 })
      : t("Question");
  } else if (role === "response" || kind === "llm_final_response") {
    title = t("Response");
  } else if (role === "reflection" || kind === "tool_result_reflection") {
    // Tool Summarizer sub-trace (Phase 1 of the question pipeline). The
    // top-level status row carries the verbose "DeepTutor Reflecting…"
    // wording; the sub-trace just labels itself "Reflecting" so the card
    // header stays short.
    title = t("Reflecting");
  } else if (role === "thought" || kind === "llm_reasoning") {
    title = t("Thought");
  } else if (kind === "llm_generation") {
    if (/^generate\s+/i.test(label)) {
      title = t("Generating {{label}}", {
        label: label.replace(/^generate\s+/i, ""),
      });
    } else if (/^write\s+/i.test(label)) {
      title = t("Writing {{label}}", {
        label: label.replace(/^write\s+/i, ""),
      });
    }
  }

  return title;
}

// Chat-loop `content` (call_kind "agent_loop_round") is the model's
// user-facing text. Whether it belongs in the trace depends on the round:
//   - a NARRATION round (the round ended with a tool call) → its text was
//     the model's commentary before acting. It is stripped from the answer
//     bubble, so it MUST surface in the trace.
//   - a FINISH round (the round ended with no tool call) → its text IS the
//     answer bubble; keep it out of the trace to avoid duplication.
// The differentiator is the round's own ``call_status`` marker (call_role).
function isChatLoopAnswerContent(event: StreamEvent): boolean {
  return (
    event.type === "content" &&
    String(getTraceMeta(event).call_kind || "") === "agent_loop_round"
  );
}

/**
 * A chat-loop round whose ``call_status`` marker is tagged ``narration``:
 * the round produced text and then called a tool, so its text is trace
 * commentary (it is NOT in the answer bubble). The marker lives on the same
 * call_id group, so this is decidable per-group without any global state.
 */
function isNarrationRound(events: StreamEvent[]): boolean {
  // Mirror `collectNarrationCallIds` in lib/stream.ts so the trace and the
  // answer bubble agree on exactly which rounds are narration.
  return events.some((event) => {
    const meta = getTraceMeta(event);
    return (
      meta.trace_kind === "call_status" &&
      meta.call_state === "complete" &&
      meta.call_role === "narration"
    );
  });
}

function getTraceText(
  events: StreamEvent[],
  eventTypes: Array<StreamEvent["type"]>,
  // When the caller knows this group is a narration round, its
  // ``agent_loop_round`` content is trace material and should NOT be
  // filtered out as answer-bubble text.
  includeChatLoopContent = false,
) {
  const textEvents = events.filter(
    (event) =>
      eventTypes.includes(event.type) &&
      event.content.trim().length > 0 &&
      (includeChatLoopContent || !isChatLoopAnswerContent(event)),
  );
  if (!textEvents.length) return "";

  const explicitOutputs = textEvents.filter(
    (event) => String(getTraceMeta(event).trace_kind || "") === "llm_output",
  );
  if (explicitOutputs.length > 0) {
    return explicitOutputs[explicitOutputs.length - 1].content;
  }

  return textEvents.map((event) => event.content).join("");
}

// Long string values in tool args are almost always base64 payloads
// (image bytes, file blobs) the LLM never typed itself — they were
// server-injected by the chat pipeline. Pretty-printing the raw value
// fills the trace with megabytes of noise, so we elide anything past
// this many characters down to a short summary.
const TRACE_ARGS_MAX_STRING_CHARS = 200;

function elideLongStrings(value: unknown): unknown {
  if (typeof value === "string") {
    if (value.length > TRACE_ARGS_MAX_STRING_CHARS) {
      const head = value.slice(0, 40);
      return `${head}… <${value.length.toLocaleString()} chars elided>`;
    }
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(elideLongStrings);
  }
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = elideLongStrings(v);
    }
    return out;
  }
  return value;
}

function formatTraceArgs(args: unknown) {
  if (args == null) return "";
  try {
    return JSON.stringify(elideLongStrings(args), null, 2);
  } catch {
    return String(args);
  }
}

/**
 * Per-tool nice rendering for ``tool_call`` args. Some tools (notably
 * ``ask_user``) have args that are large structured payloads which the
 * UI also renders as a dedicated card below the trace — dumping the raw
 * JSON twice is just noise. Returning ``null`` falls back to the
 * generic JSON ``<pre>`` block.
 */
function renderNiceToolArgs(
  toolName: string | undefined,
  rawArgs: unknown,
): ReactNode | null {
  if (toolName !== "ask_user" || !rawArgs || typeof rawArgs !== "object") {
    return null;
  }
  const obj = rawArgs as Record<string, unknown>;
  const questions = Array.isArray(obj.questions)
    ? (obj.questions as Array<Record<string, unknown>>)
    : [];
  if (questions.length === 0) return null;
  return (
    <ul
      style={{
        margin: "2px 0 0 12px",
        padding: 0,
        listStyle: "none",
        display: "grid",
        rowGap: 2,
        fontSize: 10.5,
        lineHeight: 1.5,
        fontStyle: "normal",
      }}
    >
      {questions.map((q, idx) => {
        const prompt = String(q.prompt ?? q.question ?? "").trim();
        if (!prompt) return null;
        return (
          <li
            key={idx}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 6,
              color: DT.mutedForeground,
            }}
          >
            <span style={{ flexShrink: 0, fontVariantNumeric: "tabular-nums", opacity: 0.5 }}>
              {idx + 1}.
            </span>
            <span style={{ minWidth: 0, flex: 1 }}>{prompt}</span>
          </li>
        );
      })}
    </ul>
  );
}

/* ------------------------------------------------------------------ */
/*  Display-item grouping (step-level)                                 */
/* ------------------------------------------------------------------ */

// Whether a call's events carry anything worth a trace row: reasoning, a tool
// call/result, an error, or a non-status progress line. Chat-loop user text
// (`isChatLoopAnswerContent`) does not count — it belongs to the answer bubble.
function groupHasTraceSubstance(events: StreamEvent[]): boolean {
  // Narration rounds carry trace-worthy commentary in their `content`; a
  // finish round's content is the answer bubble and never counts here.
  const narration = isNarrationRound(events);
  return events.some((event) => {
    if (
      event.type === "tool_call" ||
      event.type === "tool_result" ||
      event.type === "error"
    ) {
      return true;
    }
    if (event.type === "thinking" || event.type === "observation") {
      return event.content.trim().length > 0;
    }
    if (event.type === "progress") {
      const traceKind = String(getTraceMeta(event).trace_kind || "");
      return traceKind !== "call_status" && event.content.trim().length > 0;
    }
    if (event.type === "content") {
      const isTraceText = narration || !isChatLoopAnswerContent(event);
      return isTraceText && event.content.trim().length > 0;
    }
    return false;
  });
}

function buildDisplayItems(traceGroups: TraceItem[]): DisplayItem[] {
  const items: DisplayItem[] = [];
  let stepId_: string | null = null;
  let stepTraces: TraceItem[] = [];

  function flushStep() {
    if (stepId_ !== null && stepTraces.length > 0) {
      items.push({ kind: "step", stepId: stepId_, traces: stepTraces });
    }
    stepId_ = null;
    stepTraces = [];
  }

  for (const group of traceGroups) {
    const meta = getTraceMeta(group.events[0]);
    const groupType = getTraceGroup(group.events);
    const stepId = meta.step_id ? String(meta.step_id) : "";
    const kind = getTraceCallKind(group.events);

    if (kind === "llm_final_response") continue;
    // Some pipelines keep a hidden sub-trace for text that is also emitted as
    // final response content. Drop those absorbed rows so the answer does not
    // appear twice.
    if (group.events.some((e) => getTraceMeta(e).absorbed_into_final === true))
      continue;

    // A chat-loop round whose only substance is its user-facing `content`
    // (the finish answer → bubble, or a suppressed narration line) carries
    // nothing to show in the trace — skip it so no empty "Exploring" card
    // appears. Rounds with reasoning, tool calls, progress, or errors stay.
    if (!groupHasTraceSubstance(group.events)) continue;

    if (groupType === "react_round" && stepId) {
      if (stepId_ === stepId) {
        stepTraces.push(group);
      } else {
        flushStep();
        stepId_ = stepId;
        stepTraces = [group];
      }
    } else if (stepId_ !== null && kind !== "llm_generation") {
      stepTraces.push(group);
    } else {
      flushStep();
      items.push({ kind: "trace", trace: group });
    }
  }
  flushStep();
  return items;
}

/* ------------------------------------------------------------------ */
/*  Primitive UI pieces                                                */
/* ------------------------------------------------------------------ */

/* 原件 className 参数（Tailwind 串）换算为 style 对象（见文件头替换点 5）。 */
const TRACE_BODY_DEFAULT_STYLE: CSSProperties = {
  marginLeft: 20,
  marginRight: 12,
  marginTop: 2,
  maxHeight: 180,
  overflowY: "auto",
  padding: "4px 12px",
};

function ScrollableTraceBody({
  children,
  autoScroll,
  style = TRACE_BODY_DEFAULT_STYLE,
}: {
  children: ReactNode;
  autoScroll?: boolean;
  style?: CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);

  useEffect(() => {
    if (!autoScroll || !stickRef.current) return;
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  });

  useEffect(() => {
    if (autoScroll) stickRef.current = true;
  }, [autoScroll]);

  const handleScroll = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 30;
  }, []);

  return (
    <div ref={ref} onScroll={handleScroll} style={style}>
      {children}
    </div>
  );
}

/**
 * Inline expandable row header. Collapsed rows read as a single line;
 * the chevron points right when folded and down when open. ``onToggle``
 * is absent for rows with nothing to expand (the pending-dot state).
 */
function TraceRowHeader({
  open,
  expandable,
  active,
  onToggle,
  children,
}: {
  open: boolean;
  expandable: boolean;
  active: boolean;
  onToggle?: () => void;
  children: ReactNode;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      type="button"
      onClick={expandable ? onToggle : undefined}
      aria-expanded={expandable ? open : undefined}
      disabled={!expandable}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        width: "100%",
        alignItems: "center",
        gap: 8,
        borderRadius: 6,
        padding: "2px 0",
        textAlign: "left",
        fontSize: 12,
        fontWeight: 500,
        background: "none",
        border: "none",
        font: "inherit",
        color: hovered && expandable ? DT.foreground : DT.mutedForeground,
        cursor: expandable ? "pointer" : "default",
        transition: "color 150ms",
      }}
    >
      {expandable ? (
        <DownOutlined
          style={{
            flexShrink: 0,
            fontSize: 12,
            transform: open ? undefined : "rotate(-90deg)",
            transition: "transform 150ms",
          }}
        />
      ) : (
        // Pending row with no content yet — a faint dot preserves the
        // chevron's column width and keeps the icon + label from sliding
        // left every time a trace starts.
        <span
          style={{
            display: "flex",
            width: 12,
            flexShrink: 0,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            style={{
              height: 3,
              width: 3,
              borderRadius: 999,
              background: "currentColor",
              opacity: 0.45,
            }}
          />
        </span>
      )}
      {children}
      {active && (
        <LoadingOutlined spin style={{ fontSize: 11 }} />
      )}
    </button>
  );
}

/**
 * Generic live-follow fold: open while ``active`` (the work is streaming),
 * folded once it completes, manual toggles pin the choice. Used for rows
 * whose body is supplied as children (e.g. solve steps).
 */
function LiveFoldRow({
  active,
  summary,
  children,
}: {
  active: boolean;
  summary: ReactNode;
  children: ReactNode;
}) {
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const open = userOpen ?? active;
  return (
    <div>
      <TraceRowHeader
        open={open}
        expandable
        active={active}
        onToggle={() => setUserOpen(!open)}
      >
        {summary}
      </TraceRowHeader>
      {open ? children : null}
    </div>
  );
}

/** The glyph for a non-tool pipeline row, keyed off its kind/phase. Tool rows
 *  resolve their glyph through {@link describeToolCall} instead. */
function pickKindIcon(kind: string, phase: string): GlyphComponent {
  if (kind === "rag_retrieval") return KnowledgeMark;
  if (kind === "tool_planning" || phase === "acting") return CommandMark;
  if (kind === "agent_loop_round" || phase === "exploring")
    return ReasoningMark;
  if (kind === "llm_final_response") return ReasoningMark;
  if (kind === "llm_observation") return ReasoningMark;
  if (kind === "llm_generation" || phase === "writing") return RespondingMark;
  if (phase === "planning") return ReasoningMark;
  return ReasoningMark;
}

function TraceSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  if (!children) return null;
  return (
    <div style={{ display: "grid", rowGap: 2 }}>
      <div
        style={{
          fontStyle: "normal",
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.04em",
          color: DT.mutedForegroundAlpha(0.7),
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Per-trace rendering                                                */
/* ------------------------------------------------------------------ */

const ARGS_PRE_STYLE: CSSProperties = {
  margin: "2px 0 0 12px",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
  borderRadius: 6,
  background: DT.muted,
  padding: "4px 8px",
  fontFamily: MONO_FONT,
  fontSize: 10,
  fontStyle: "normal",
  lineHeight: 1.5,
  color: DT.mutedForeground,
};

const RAW_LOGS_STYLE: CSSProperties = {
  maxHeight: 200,
  overflowY: "auto",
  borderRadius: 6,
  border: `1px solid ${DT.border}`,
  background: "#292524",
  padding: "8px 12px",
  fontFamily: MONO_FONT,
  fontSize: 10,
  lineHeight: 1.55,
  color: "#D6D3D1",
  boxShadow: "inset 0 2px 4px rgba(0,0,0,0.06)",
};

function TraceRowBody({
  callId,
  callEvents,
  group,
  role,
  kind,
  t,
}: {
  callId: string;
  callEvents: StreamEvent[];
  group: string;
  role: string;
  kind: string;
  t: (key: string) => string;
}) {
  const progressEvents = callEvents.filter((event) => {
    if (event.type !== "progress") return false;
    const traceKind = String(getTraceMeta(event).trace_kind || "");
    if (traceKind === "call_status") return false;
    return event.content.trim().length > 0;
  });
  const toolEvents = callEvents.filter(
    (event) => event.type === "tool_call" || event.type === "tool_result",
  );
  const summaryProgressEvents = progressEvents.filter(
    (event) => String(getTraceMeta(event).trace_layer || "summary") !== "raw",
  );
  const rawProgressEvents = progressEvents.filter(
    (event) => String(getTraceMeta(event).trace_layer || "") === "raw",
  );
  const errorEvents = callEvents.filter(
    (event) => event.type === "error" && event.content.trim().length > 0,
  );
  const thoughtText = getTraceText(callEvents, ["thinking"]);
  const observationText = getTraceText(callEvents, ["observation"]);
  // A chat round can emit BOTH reasoning (thinking) and narration commentary
  // (content) in a single call; both are trace material and render as
  // separate stacked blocks. Other pipelines keep the legacy "thought or
  // content" fallback so their rows are unchanged.
  const isChatRound = kind === "agent_loop_round";
  const contentText = getTraceText(
    callEvents,
    ["content"],
    isNarrationRound(callEvents),
  );
  const bodyBlocks =
    role === "observe"
      ? [observationText]
      : role === "retrieve"
        ? []
        : isChatRound
          ? [thoughtText, contentText]
          : [thoughtText || contentText];
  const renderableBodyBlocks = bodyBlocks.filter(
    (text): text is string => Boolean(text) && text.trim().length > 0,
  );
  // A connected subagent's native run streams in as ``subagent_event`` progress
  // lines, but those are shown in the side viewer's per-agent tab — keep the
  // inline trace compact (the question + the agent's final reply).
  const plainSummaryEvents = summaryProgressEvents.filter(
    (event) => getTraceMeta(event).trace_kind !== "subagent_event",
  );
  const inlineSources = callEvents.flatMap(
    (event) => getTraceMeta(event).sources ?? [],
  );

  return (
    <div
      style={{
        fontSize: 11.5,
        lineHeight: 1.6,
        color: DT.mutedForeground,
      }}
    >
      {group === "react_round" ? (
        <div style={{ display: "grid", rowGap: 8 }}>
          <TraceSection title={t("Thought")}>
            {thoughtText ? (
              <MarkdownRenderer content={thoughtText} variant="trace" />
            ) : null}
          </TraceSection>
          <TraceSection title={t("Tool")}>
            {toolEvents.length > 0 ? (
              <div style={{ display: "grid", rowGap: 2 }}>
                {toolEvents.map((event, idx) => {
                  if (event.type === "tool_call") {
                    const toolName =
                      (event.metadata?.tool as string | undefined) ?? undefined;
                    const niceArgs = renderNiceToolArgs(
                      toolName,
                      event.metadata?.args,
                    );
                    const formattedArgs = niceArgs
                      ? ""
                      : formatTraceArgs(event.metadata?.args);
                    return (
                      <div key={`${callId}-tool-call-${idx}`}>
                        <span style={{ opacity: 0.5 }}>→ </span>
                        <span>{event.content}</span>
                        {niceArgs ?? null}
                        {formattedArgs && <pre style={ARGS_PRE_STYLE}>{formattedArgs}</pre>}
                      </div>
                    );
                  }
                  return (
                    <div key={`${callId}-tool-result-${idx}`}>
                      <span style={{ opacity: 0.5 }}>✓ </span>
                      <span>{String(event.metadata?.tool ?? "result")}</span>
                      {event.content && (
                        <div style={{ margin: "2px 0 0 12px" }}>
                          <MarkdownRenderer
                            content={event.content}
                            variant="trace"
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : null}
          </TraceSection>
          <TraceSection title={t("Observe")}>
            {observationText ? (
              <MarkdownRenderer content={observationText} variant="trace" />
            ) : null}
          </TraceSection>
        </div>
      ) : (
        <div style={{ display: "grid", rowGap: 4 }}>
          {plainSummaryEvents.length > 0 && (
            <div style={{ display: "grid", rowGap: 2 }}>
              {plainSummaryEvents.map((event, idx) => (
                <div key={`${callId}-progress-${idx}`} style={{ opacity: 0.7 }}>
                  {event.content}
                </div>
              ))}
            </div>
          )}

          {(role === "retrieve" || kind === "math_render_output") &&
            rawProgressEvents.length > 0 && (
              <div style={{ display: "grid", rowGap: 2 }}>
                <div
                  style={{
                    fontStyle: "normal",
                    fontSize: 11,
                    fontWeight: 500,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: DT.mutedForeground,
                  }}
                >
                  {t("Raw logs")}
                </div>
                <div style={RAW_LOGS_STYLE}>
                  {rawProgressEvents.map((event, idx) => (
                    <div
                      key={`${callId}-raw-${idx}`}
                      style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}
                    >
                      {event.content}
                    </div>
                  ))}
                </div>
              </div>
            )}

          {toolEvents.length > 0 && (
            <div style={{ display: "grid", rowGap: 2 }}>
              {toolEvents.map((event, idx) => {
                if (event.type === "tool_call") {
                  const toolName =
                    (event.metadata?.tool as string | undefined) ?? undefined;
                  const niceArgs = renderNiceToolArgs(
                    toolName,
                    event.metadata?.args,
                  );
                  const formattedArgs = niceArgs
                    ? ""
                    : formatTraceArgs(event.metadata?.args);
                  return (
                    <div key={`${callId}-tool-call-${idx}`}>
                      <span style={{ opacity: 0.5 }}>→ </span>
                      <span>{event.content}</span>
                      {niceArgs ?? null}
                      {formattedArgs && <pre style={ARGS_PRE_STYLE}>{formattedArgs}</pre>}
                    </div>
                  );
                }
                return (
                  <div key={`${callId}-tool-result-${idx}`}>
                    <span style={{ opacity: 0.5 }}>✓ </span>
                    <span>{String(event.metadata?.tool ?? "result")}</span>
                    {event.content && (
                      <div style={{ margin: "2px 0 0 12px" }}>
                        <MarkdownRenderer
                          content={event.content}
                          variant="trace"
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {renderableBodyBlocks.length > 0 && (
            <div style={{ marginTop: 4, display: "grid", rowGap: 6 }}>
              {renderableBodyBlocks.map((text, idx) => (
                <MarkdownRenderer
                  key={`${callId}-body-${idx}`}
                  content={text}
                  variant="trace"
                />
              ))}
            </div>
          )}
        </div>
      )}

      {inlineSources.length > 0 && (
        <div style={{ marginTop: 4, opacity: 0.5 }}>
          {t("Sources")}:{" "}
          {inlineSources.map((source, idx) => (
            <span key={`${callId}-source-${idx}`}>
              {idx > 0 && " · "}
              {String(source.title || source.query || source.type || "source")}
            </span>
          ))}
        </div>
      )}

      {errorEvents.length > 0 && (
        <div style={{ marginTop: 4, display: "grid", rowGap: 2 }}>
          {errorEvents.map((event, idx) => (
            <div
              key={`${callId}-error-${idx}`}
              style={{ color: "rgba(248,113,113,0.8)" }}
            >
              ✗ {event.content}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function hasExpandableContent(
  callEvents: StreamEvent[],
  group: string,
  role: string,
) {
  const progressEvents = callEvents.filter((event) => {
    if (event.type !== "progress") return false;
    const traceKind = String(getTraceMeta(event).trace_kind || "");
    if (traceKind === "call_status") return false;
    return event.content.trim().length > 0;
  });
  const toolEvents = callEvents.filter(
    (event) => event.type === "tool_call" || event.type === "tool_result",
  );
  const summaryProgressEvents = progressEvents.filter(
    (event) => String(getTraceMeta(event).trace_layer || "summary") !== "raw",
  );
  const rawProgressEvents = progressEvents.filter(
    (event) => String(getTraceMeta(event).trace_layer || "") === "raw",
  );
  const errorEvents = callEvents.filter(
    (event) => event.type === "error" && event.content.trim().length > 0,
  );
  const thoughtText = getTraceText(callEvents, ["thinking"]);
  const observationText = getTraceText(callEvents, ["observation"]);
  const contentText = getTraceText(
    callEvents,
    ["content"],
    isNarrationRound(callEvents),
  );
  const genericBodyText =
    role === "observe"
      ? observationText
      : role === "retrieve"
        ? ""
        : thoughtText || contentText;
  const inlineSources = callEvents.flatMap(
    (event) => getTraceMeta(event).sources ?? [],
  );

  return (
    toolEvents.length > 0 ||
    summaryProgressEvents.length > 0 ||
    rawProgressEvents.length > 0 ||
    errorEvents.length > 0 ||
    Boolean(genericBodyText) ||
    inlineSources.length > 0 ||
    (group === "react_round" &&
      (Boolean(thoughtText) || Boolean(observationText)))
  );
}

/* ------------------------------------------------------------------ */
/*  Inline trace rows                                                  */
/* ------------------------------------------------------------------ */

/**
 * One trace = one Claude-style flat activity line in the message flow:
 * a small icon + the meaningful text of this step (reasoning / narration,
 * or a tool action with a tool-name chip) shown inline. There is no boxed
 * header and no always-visible chevron — a faint chevron only appears on
 * hover for rows that carry extra detail.
 *
 * The live step is auto-expanded so its reasoning streams in full; once it
 * completes it folds to a one-line preview (the activity-feed look). A
 * manual toggle pins the row from then on.
 */
function TraceRowItem({
  trace,
  active,
  nested,
}: {
  trace: TraceItem;
  active: boolean;
  nested: boolean;
}) {
  const t = zhT;
  const [hovered, setHovered] = useState(false);
  const [userOpen, setUserOpen] = useState<boolean | null>(null);

  const { callId, events: callEvents } = trace;
  const first = callEvents[0];
  const meta = getTraceMeta(first);
  const phase = String(meta.phase || first?.stage || "");
  const role = getTraceRole(callEvents);
  const group = getTraceGroup(callEvents);
  const kind = getTraceCallKind(callEvents);
  const header = getTraceHeader(callEvents, nested, t);

  if (kind === "llm_final_response") return null;
  const expandable = hasExpandableContent(callEvents, group, role);
  if (!expandable && !active) return null;

  const isToolRow = kind === "tool_planning" || group === "tool_call";
  const isChatRound = kind === "agent_loop_round";
  const isRetrieve = role === "retrieve";
  const narration = isNarrationRound(callEvents);
  // The model's own text-form deliberation — chat-loop reasoning/narration and
  // pipeline "Thought"/"Plan" rounds. Unlike a tool call (whose result is
  // secondary detail worth folding away), here the text IS the substance, so
  // it always streams in full and is never collapsed behind a chevron.
  const isThinking =
    isChatRound ||
    role === "thought" ||
    kind === "llm_reasoning" ||
    kind === "llm_planning";
  // Thinking rows pin open; everything else folds to a preview once settled
  // unless the user pins it. The context-exploration pre-pass is the
  // exception to "auto-open while live": its briefing can be long, and
  // auto-opening it lets the trace climb the viewport (the page is pinned to
  // the bottom while streaming). Keep it folded by default — a compact,
  // pulsing one-liner the user can expand to read/watch the briefing.
  const isContextExploration = kind === "context_exploration";
  const autoOpen = isContextExploration ? false : active;
  const open = isThinking ? true : expandable && (userOpen ?? autoOpen);
  const canToggle = expandable && !isThinking;

  const toolCallEvent = callEvents.find((event) => event.type === "tool_call");
  const toolName = String(
    (toolCallEvent &&
      (getTraceMeta(toolCallEvent).tool_name ||
        toolCallEvent.metadata?.tool)) ||
      toolCallEvent?.content ||
      "",
  ).trim();
  const toolArgs = toolCallEvent?.metadata?.args as
    | Record<string, unknown>
    | undefined;

  const thoughtText = getTraceText(callEvents, ["thinking"]).trim();
  const contentText = getTraceText(callEvents, ["content"], narration).trim();

  // Resolve every row into a uniform { icon, headline, chip } triple so the
  // activity feed reads consistently across pipelines. Tool calls get a human
  // action verb + an artifact chip (the Claude-cowork pattern); retrieval
  // surfaces its query; chat reasoning rounds ARE their text (rendered inline
  // when open, clamped to a preview when folded).
  const provider = getToolProvider(callEvents);
  const descriptor =
    isToolRow && toolName
      ? describeToolCall(toolName, toolArgs, t, provider)
      : null;
  // What the provider last said about its own progress. Only MCP servers and
  // CLI apps publish these, and only while the call is open.
  const liveStatus = active ? getLatestToolProgress(callEvents) : "";

  let resolvedIcon: GlyphComponent;
  let headline: string;
  let chip: { text: string; mono: boolean } | null = null;

  if (descriptor) {
    resolvedIcon = descriptor.Icon;
    headline = descriptor.verb;
    chip = descriptor.chip
      ? { text: descriptor.chip, mono: descriptor.mono }
      : null;
    // While it runs, how far along it is displaces what it is: the identity is
    // already in the verb, and "fetching pages (30%)" is the only thing that
    // distinguishes a working call from a hung one. It reverts once settled.
    if (liveStatus) chip = { text: liveStatus, mono: false };
    // Name the consult after the agent it targets (e.g. "Consult Subagent
    // test-cc"); the name rides on the streamed subagent events in the group.
    if (toolName === "consult_subagent") {
      const agentName = String(
        callEvents.map((e) => getTraceMeta(e).subagent_name).find(Boolean) ||
          "",
      );
      headline = agentName
        ? `${t("Consult Subagent")} ${agentName}`
        : t("Consult Subagent");
    }
  } else if (isRetrieve) {
    resolvedIcon = KnowledgeMark;
    headline = header;
    const query = clip(
      String(callEvents.map((e) => getTraceMeta(e).query).find(Boolean) || ""),
    );
    chip = query ? { text: query, mono: false } : null;
  } else if (isChatRound) {
    resolvedIcon = ReasoningMark;
    headline =
      [thoughtText, contentText].filter(Boolean).join("  ·  ") || header;
  } else {
    resolvedIcon = pickKindIcon(kind, phase);
    headline = header;
  }
  // Render through a property access (``glyph.Icon``) rather than a bare
  // local ``<RowIcon>`` — a locally-assigned capitalized component trips
  // react-hooks/static-components, member-expression JSX does not.
  const glyph = { Icon: resolvedIcon };

  // Chat rounds ARE their text, so an open chat row renders the full
  // reasoning/narration inline (markdown) rather than a separate detail
  // body. Tool / pipeline rows keep their structured detail body.
  const showDetailBody = open && !isThinking;
  const showChatBody = open && isChatRound;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        role={canToggle ? "button" : undefined}
        aria-expanded={canToggle ? open : undefined}
        onClick={canToggle ? () => setUserOpen(!open) : undefined}
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 10,
          padding: "6px 0",
          fontSize: 14,
          lineHeight: 1.5,
          color:
            canToggle && hovered ? DT.foreground : DT.mutedForeground,
          cursor: canToggle ? "pointer" : "default",
          transition: "color 150ms",
        }}
      >
        {/* While the row is live the mark pulses (and tints primary) like the
            status header's own mark, so activity reads at a glance without a
            separate spinner; settled rows fade to a quiet monochrome glyph. */}
        <span
          style={{
            marginTop: 2,
            flexShrink: 0,
            color: active
              ? DT.primaryAlpha(0.85)
              : hovered
                ? DT.mutedForegroundAlpha(0.8)
                : DT.mutedForegroundAlpha(0.55),
            transition: "color 150ms",
          }}
        >
          <glyph.Icon
            size={15}
            strokeWidth={1.5}
            className={active ? "dt-mark-pulse" : undefined}
          />
        </span>
        <div style={{ minWidth: 0, flex: 1 }}>
          {showChatBody ? (
            <div
              style={{
                display: "grid",
                rowGap: 6,
                lineHeight: 1.6,
              }}
            >
              {thoughtText ? (
                <MarkdownRenderer content={thoughtText} variant="trace" />
              ) : null}
              {contentText ? (
                <MarkdownRenderer content={contentText} variant="trace" />
              ) : null}
            </div>
          ) : isThinking ? (
            // Pipeline "Thought"/"Plan" rounds: a quiet label, then the
            // model's reasoning streamed inline below it — never folded. The
            // body sits at the row's own 14px for comfortable reading, the
            // label one notch heavier so the two read as label + prose.
            <>
              <span
                className={active ? "dt-breathing-text" : undefined}
                style={{ display: "block", fontWeight: 500 }}
              >
                {headline}
              </span>
              {thoughtText || contentText ? (
                <div style={{ marginTop: 4, lineHeight: 1.6 }}>
                  <MarkdownRenderer
                    content={thoughtText || contentText}
                    variant="trace"
                  />
                </div>
              ) : null}
            </>
          ) : (
            <>
              {chip ? (
                // Action verb + its artifact collapse onto a single line: the
                // verb anchors (never truncates, always legible) while the
                // dimmer query trails and ellipsizes. Reads "读取技能 pdf" /
                // "联网搜索 …" at a glance — the colour drop is the only cue
                // separating the two, no pill chrome.
                <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                  <span
                    className={active ? "dt-breathing-text" : undefined}
                    style={{ flexShrink: 0 }}
                  >
                    {headline}
                  </span>
                  <span
                    style={{
                      minWidth: 0,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      color: DT.mutedForegroundAlpha(0.55),
                      ...(chip.mono
                        ? { fontFamily: MONO_FONT, fontSize: 12.5 }
                        : {}),
                    }}
                  >
                    {chip.text}
                  </span>
                </div>
              ) : (
                <span
                  className={active ? "dt-breathing-text" : undefined}
                  style={{
                    display: "-webkit-box",
                    WebkitLineClamp: isChatRound ? 3 : 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    
                  }}
                >
                  {headline}
                </span>
              )}
            </>
          )}
        </div>
        {/* No trailing spinner while active — the pulsing leading mark carries
            that signal. A faint chevron surfaces on hover for any expandable
            row (live or settled) so the detail is always one click away. */}
        {canToggle ? (
          <DownOutlined
            style={{
              marginTop: 4,
              flexShrink: 0,
              fontSize: 13,
              color: DT.mutedForegroundAlpha(0.4),
              opacity: hovered ? 1 : 0,
              transform: open ? undefined : "rotate(-90deg)",
              transition: "transform 150ms, opacity 150ms",
            }}
          />
        ) : null}
      </div>
      {showDetailBody ? (
        <ScrollableTraceBody
          autoScroll={active}
          style={{
            marginLeft: 26,
            marginRight: 8,
            marginTop: 2,
            maxHeight: 260,
            overflowY: "auto",
            paddingRight: 4,
          }}
        >
          <TraceRowBody
            callId={callId}
            callEvents={callEvents}
            group={group}
            role={role}
            kind={kind}
            t={t}
          />
        </ScrollableTraceBody>
      ) : null}
    </div>
  );
}

export function CallTracePanel({
  events,
  isStreaming,
  nested = false,
}: {
  events: StreamEvent[];
  isStreaming?: boolean;
  // Kept for callers that render the rows inside their own framed shell;
  // rows are inline either way, ``nested`` only affects sub-row layout.
  nested?: boolean;
}) {
  const t = zhT;
  ensureTraceStyles();

  const traceGroups = useMemo(() => {
    const groups: TraceItem[] = [];
    const indexById = new Map<string, number>();

    for (const event of events) {
      const callId = String(getTraceMeta(event).call_id || "");
      if (!callId) continue;
      const existingIndex = indexById.get(callId);
      if (existingIndex === undefined) {
        indexById.set(callId, groups.length);
        groups.push({ callId, events: [event] });
      } else {
        groups[existingIndex].events.push(event);
      }
    }

    return groups;
  }, [events]);

  const displayItems = useMemo(
    () => buildDisplayItems(traceGroups),
    [traceGroups],
  );

  // Hide the outer container entirely when no sub-trace ends up being
  // rendered. ``traceGroups`` can be non-empty even when every group is
  // filtered out by ``buildDisplayItems`` (final-response groups and groups
  // tagged ``absorbed_into_final``) — in that case we used to draw an
  // empty bordered box. Check the materialised displayItems instead.
  if (!displayItems.length) return null;

  // Rows flow inline with the message — no outer card, no shared scroll
  // region. Each row manages its own fold state (live-follow + manual pin)
  // and its expanded body has its own bounded scroll area.
  return (
    <div style={{ marginBottom: 12, display: "grid", rowGap: 2 }}>
      {displayItems.map((item, displayIdx) => {
        const isLastDisplayItem = displayIdx === displayItems.length - 1;

        if (item.kind === "step") {
          const roundCount = item.traces.filter(
            (tr) => getTraceGroup(tr.events) === "react_round",
          ).length;
          const lastTrace = item.traces[item.traces.length - 1];
          const isActiveStep =
            Boolean(isStreaming) &&
            isLastDisplayItem &&
            isTracePending(lastTrace.events);

          return (
            <LiveFoldRow
              key={item.stepId}
              active={isActiveStep}
              summary={
                <>
                  <StarOutlined style={{ fontSize: 12, flexShrink: 0 }} />
                  <span>{t("Step {{n}}", { n: item.stepId })}</span>
                  <span style={{ fontSize: 11, opacity: 0.6 }}>
                    {t("{{count}} round", { count: roundCount })}
                  </span>
                </>
              }
            >
              <ScrollableTraceBody
                autoScroll={isActiveStep}
                style={{
                  marginLeft: 20,
                  marginRight: 12,
                  marginTop: 2,
                  maxHeight: 280,
                  overflowY: "auto",
                  padding: "4px 12px",
                }}
              >
                <div
                  style={{
                    fontSize: 11.5,
                    lineHeight: 1.6,
                    color: DT.mutedForeground,
                  }}
                >
                  {item.traces.map((trace, idx) => {
                    const trGroup = getTraceGroup(trace.events);
                    const trKind = getTraceCallKind(trace.events);
                    const trRole = getTraceRole(trace.events);
                    const trMeta = getTraceMeta(trace.events[0]);

                    if (trKind === "llm_final_response") return null;

                    if (trGroup === "react_round") {
                      const roundNum = trMeta.round;
                      const thoughtText = getTraceText(trace.events, [
                        "thinking",
                      ]);
                      const observationText = getTraceText(trace.events, [
                        "observation",
                      ]);
                      const traceToolEvents = trace.events.filter(
                        (e) =>
                          e.type === "tool_call" || e.type === "tool_result",
                      );
                      const isLastInStep = idx === item.traces.length - 1;
                      const roundActive =
                        Boolean(isStreaming) &&
                        isLastDisplayItem &&
                        isLastInStep &&
                        isTracePending(trace.events);

                      return (
                        <div key={trace.callId}>
                          {idx > 0 && (
                            <div
                              style={{
                                marginTop: 6,
                                marginBottom: 6,
                                height: 1,
                                background: DT.borderAlpha(0.3),
                              }}
                            />
                          )}
                          <div
                            style={{
                              marginBottom: 4,
                              display: "flex",
                              alignItems: "center",
                              gap: 6,
                              fontStyle: "normal",
                              fontSize: 11,
                            }}
                          >
                            <span
                              style={{
                                fontWeight: 700,
                                textTransform: "uppercase",
                                letterSpacing: "0.08em",
                                color: DT.mutedForeground,
                              }}
                            >
                              {t("Round {{n}}", { n: roundNum })}
                            </span>
                            {roundActive && (
                              <LoadingOutlined spin style={{ fontSize: 10 }} />
                            )}
                          </div>
                          <div
                            style={{
                              display: "grid",
                              rowGap: 6,
                              paddingLeft: 2,
                            }}
                          >
                            <TraceSection title={t("Thought")}>
                              {thoughtText ? (
                                <MarkdownRenderer
                                  content={thoughtText}
                                  variant="trace"
                                />
                              ) : null}
                            </TraceSection>
                            <TraceSection title={t("Tool")}>
                              {traceToolEvents.length > 0 ? (
                                <div style={{ display: "grid", rowGap: 2 }}>
                                  {traceToolEvents.map((ev, ei) => {
                                    if (ev.type === "tool_call") {
                                      const fa = formatTraceArgs(
                                        ev.metadata?.args,
                                      );
                                      return (
                                        <div key={`${trace.callId}-tc-${ei}`}>
                                          <span style={{ opacity: 0.5 }}>→ </span>
                                          <span>{ev.content}</span>
                                          {fa && <pre style={ARGS_PRE_STYLE}>{fa}</pre>}
                                        </div>
                                      );
                                    }
                                    return (
                                      <div key={`${trace.callId}-tr-${ei}`}>
                                        <span style={{ opacity: 0.5 }}>✓ </span>
                                        <span>
                                          {String(
                                            ev.metadata?.tool ?? "result",
                                          )}
                                        </span>
                                        {ev.content && (
                                          <div style={{ margin: "2px 0 0 12px" }}>
                                            <MarkdownRenderer
                                              content={ev.content}
                                              variant="trace"
                                            />
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              ) : null}
                            </TraceSection>
                            <TraceSection title={t("Observe")}>
                              {observationText ? (
                                <MarkdownRenderer
                                  content={observationText}
                                  variant="trace"
                                />
                              ) : null}
                            </TraceSection>
                          </div>
                        </div>
                      );
                    }

                    /* Non-round trace (retrieve, tool, etc.) — inline within the step */
                    const inlineHeader = getTraceHeader(trace.events, true, t);
                    const progressEvts = trace.events.filter(
                      (e) =>
                        e.type === "progress" &&
                        String(getTraceMeta(e).trace_kind || "") !==
                          "call_status" &&
                        e.content.trim().length > 0,
                    );
                    const rawEvts = progressEvts.filter(
                      (e) =>
                        String(getTraceMeta(e).trace_layer || "") === "raw",
                    );
                    const summaryEvts = progressEvts.filter(
                      (e) =>
                        String(getTraceMeta(e).trace_layer || "summary") !==
                        "raw",
                    );
                    const inlineToolEvts = trace.events.filter(
                      (e) => e.type === "tool_call" || e.type === "tool_result",
                    );
                    const genericText =
                      trRole === "observe"
                        ? getTraceText(trace.events, ["observation"])
                        : trRole === "retrieve"
                          ? ""
                          : getTraceText(trace.events, ["thinking"]) ||
                            getTraceText(trace.events, ["content"]);

                    const hasContent =
                      summaryEvts.length > 0 ||
                      rawEvts.length > 0 ||
                      inlineToolEvts.length > 0 ||
                      Boolean(genericText);
                    if (!hasContent) return null;

                    return (
                      <div key={trace.callId} style={{ marginTop: 6, paddingLeft: 2 }}>
                        <div
                          style={{
                            fontStyle: "normal",
                            fontSize: 11,
                            fontWeight: 700,
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                            color: DT.mutedForeground,
                          }}
                        >
                          {inlineHeader}
                        </div>
                        <div style={{ marginTop: 2, display: "grid", rowGap: 2 }}>
                          {summaryEvts.map((ev, ei) => (
                            <div
                              key={`${trace.callId}-sp-${ei}`}
                              style={{ opacity: 0.7 }}
                            >
                              {ev.content}
                            </div>
                          ))}
                          {(trRole === "retrieve" ||
                            trKind === "math_render_output") &&
                            rawEvts.length > 0 && (
                              <div
                                style={{
                                  ...RAW_LOGS_STYLE,
                                  maxHeight: 160,
                                }}
                              >
                                {rawEvts.map((ev, ei) => (
                                  <div
                                    key={`${trace.callId}-rw-${ei}`}
                                    style={{
                                      whiteSpace: "pre-wrap",
                                      wordBreak: "break-word",
                                    }}
                                  >
                                    {ev.content}
                                  </div>
                                ))}
                              </div>
                            )}
                          {inlineToolEvts.map((ev, ei) => (
                            <div key={`${trace.callId}-it-${ei}`}>
                              <span style={{ opacity: 0.5 }}>
                                {ev.type === "tool_call" ? "→ " : "✓ "}
                              </span>
                              <span>
                                {ev.type === "tool_call"
                                  ? ev.content
                                  : String(ev.metadata?.tool ?? "result")}
                              </span>
                            </div>
                          ))}
                          {genericText && (
                            <div style={{ marginTop: 2 }}>
                              <MarkdownRenderer
                                content={genericText}
                                variant="trace"
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollableTraceBody>
            </LiveFoldRow>
          );
        }

        const active =
          Boolean(isStreaming) &&
          isLastDisplayItem &&
          isTracePending(item.trace.events);
        return (
          <TraceRowItem
            key={item.trace.callId}
            trace={item.trace}
            active={active}
            nested={nested}
          />
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  StreamingStatus — breathing "reasoning" / "tool using" indicator   */
/* ------------------------------------------------------------------ */

type MarkProps = {
  size?: number;
  className?: string;
  strokeWidth?: number;
};

function MarkSvg({
  size = 16,
  className,
  strokeWidth = 1.5,
  children,
}: MarkProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/**
 * Reasoning — asymmetric 12-ray radial burst. Tilted ~12° so it reads as
 * hand-sketched rather than geometric; long cardinal rays + medium diagonals
 * + short accent rays in between for an organic sparkle.
 */
function ReasoningMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <g transform="rotate(12 12 12)">
        <path d="M12 2 L12 7.5" />
        <path d="M12 22 L12 16.5" />
        <path d="M2 12 L7.5 12" />
        <path d="M22 12 L16.5 12" />
        <path d="M4.6 4.6 L8.4 8.4" />
        <path d="M19.4 19.4 L15.6 15.6" />
        <path d="M4.2 19.8 L8.2 15.8" />
        <path d="M19.8 4.2 L15.8 8.2" />
        <path d="M7.6 2.3 L9 5.8" />
        <path d="M16.4 2.3 L15 5.8" />
        <path d="M7.6 21.7 L9 18.2" />
        <path d="M16.4 21.7 L15 18.2" />
      </g>
    </MarkSvg>
  );
}

/**
 * Tool using — an off-axis orbital motif: a soft elliptical orbit arc with
 * a small filled satellite riding it and two stray sparks. Reads as something
 * "in motion / being operated" without being a literal wrench.
 */
function ToolMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      {/* Central node */}
      <circle cx="12" cy="13" r="2.4" />
      {/* Open orbital arc on a slight tilt */}
      <path d="M3.5 9.5 A 10.5 8 -18 0 1 20.5 14" />
      {/* Filled satellite riding the orbit */}
      <circle cx="20.5" cy="14" r="1.5" fill="currentColor" stroke="none" />
      {/* Stray accent sparks */}
      <path d="M5 19 L7.2 17.5" />
      <path d="M18 4 L19.5 6" />
    </MarkSvg>
  );
}

/**
 * Responding — a flowing ink-stroke that swoops up to the right, terminating
 * in a small dot, like a quill marking paper. Suggests "writing out an
 * answer" without being a literal pen icon.
 */
function RespondingMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      {/* Sweeping brush curve */}
      <path d="M3 18 Q 8 7 14 11 T 21 6.5" />
      {/* Quill tip — short tick + filled dot */}
      <circle cx="21" cy="6.5" r="1.4" fill="currentColor" stroke="none" />
      {/* Ink drop accent below */}
      <circle cx="5.5" cy="20.5" r="0.9" fill="currentColor" stroke="none" />
    </MarkSvg>
  );
}

/**
 * Responded — a settled, slightly softer mark: a compact 4-ray bloom with
 * a filled inner dot. Conveys "thought captured, complete" without echoing
 * the reasoning burst.
 */
function RespondedMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <g transform="rotate(8 12 12)">
        {/* Inner anchor */}
        <circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none" />
        {/* 4 short cardinal rays */}
        <path d="M12 4.5 L12 8" />
        <path d="M12 19.5 L12 16" />
        <path d="M4.5 12 L8 12" />
        <path d="M19.5 12 L16 12" />
        {/* 2 longer diagonal accents — asymmetric for character */}
        <path d="M6 6 L8.6 8.6" />
        <path d="M18 18 L15.4 15.4" />
      </g>
    </MarkSvg>
  );
}

/* ---- Trace-row glyphs (same hand-drawn family as the status marks) ---- */

/** Command / code — an open shell prompt: a chevron + an underscore, gently
 *  tilted so it reads sketched rather than boxed. */
function CommandMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <g transform="rotate(-3 12 12)">
        <path d="M6 8 L10 12 L6 16" />
        <path d="M12.5 16 H18" />
      </g>
    </MarkSvg>
  );
}

/** A connected service — two half-rings coupled by a short bar, reading as a
 *  link rather than a socket. Used for MCP servers: the row is naming something
 *  outside DeepTutor that the turn is talking to. */
function LinkMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      {/* Two open hooks joined by a diagonal — a chain link. Drawn open rather
          than as two closed rings: a closed pair reads as a globe at 15px, which
          is the glyph web tools already use. */}
      <g transform="rotate(-4 12 12)">
        <path d="M10.4 13.6 L13.6 10.4" />
        <path d="M9.2 11.1 L7.7 12.6 A 2.7 2.7 0 0 0 11.5 16.4 L13 14.9" />
        <path d="M14.8 12.9 L16.3 11.4 A 2.7 2.7 0 0 0 12.5 7.6 L11 9.1" />
      </g>
    </MarkSvg>
  );
}

/** Web — an organic globe: a soft sphere with two meridian sweeps and one
 *  off-centre latitude line. */
function GlobeMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <g transform="rotate(-6 12 12)">
        <circle cx="12" cy="12" r="6.2" />
        <path d="M12 5.8 Q 7 12 12 18.2" />
        <path d="M12 5.8 Q 17 12 12 18.2" />
        <path d="M6 10.3 H18" />
      </g>
    </MarkSvg>
  );
}

/** Search — a hand-drawn loupe: a lens, a curved handle that swoops away,
 *  and a stray spark for life. */
function LoupeMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <g transform="rotate(-4 12 12)">
        <circle cx="10.3" cy="10.3" r="5" />
        <path d="M14 14 Q 17.5 16.8 20 20" />
        <path d="M17.6 5 L18.9 6.3" />
      </g>
    </MarkSvg>
  );
}

/** Knowledge — layered strata: a soft top lens over a single curved shelf,
 *  reading as stacked data without the literal cylinder. */
function KnowledgeMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <path d="M4.5 9 Q 12 5 19.5 9 Q 12 13 4.5 9 Z" />
      <path d="M5.2 13.4 Q 12 17 18.8 13.4" />
      <circle cx="12" cy="9" r="1.1" fill="currentColor" stroke="none" />
    </MarkSvg>
  );
}

/** Read — a bookmark ribbon: a single clean pennant with softly rounded
 *  shoulders and a notched foot. One closed stroke reads crisply at glyph
 *  size, where the old open-book's spine + two leaves muddied into a blob. */
function BookMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <g transform="rotate(-2 12 12)">
        <path d="M7.4 6.2 Q 7.4 4.8 8.8 4.8 H15.2 Q 16.6 4.8 16.6 6.2 V19 L12 14.9 L7.4 19 Z" />
      </g>
    </MarkSvg>
  );
}

/** Memory — a small constellation: a filled core node with three satellites
 *  on thin connectors, like a recall graph. */
function MemoryMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <path d="M12 12 L6 6.6" />
      <path d="M12 12 L18.4 8" />
      <path d="M12 12 L9.2 18.8" />
      <circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" />
      <circle cx="6" cy="6.6" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="18.4" cy="8" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="9.2" cy="18.8" r="1.4" fill="currentColor" stroke="none" />
    </MarkSvg>
  );
}

/** Ask — a soft speech bubble with a tail and three waiting dots. */
function SpeechMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <path d="M6 16.2 Q 4.5 6.5 12 6.5 Q 19.5 6.5 19.5 11.4 Q 19.5 15.9 13 15.9 L8.6 19.4 L9 16 Q 6.9 15.8 6 16.2 Z" />
      <circle cx="9" cy="11" r="1" fill="currentColor" stroke="none" />
      <circle cx="12" cy="11" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="11" r="1" fill="currentColor" stroke="none" />
    </MarkSvg>
  );
}

/** Media — an image/animation frame implied by two ridge peaks and a small
 *  sun, the lightest possible "picture" mark. */
function FrameMark(props: MarkProps) {
  return (
    <MarkSvg {...props}>
      <g transform="rotate(-2 12 12)">
        <path d="M4 16.6 L9 10.6 L12.4 14.4" />
        <path d="M11 16.6 L15 11.6 L20 17" />
        <circle cx="17" cy="7.4" r="1.5" />
      </g>
    </MarkSvg>
  );
}

type StreamingMode =
  | "reasoning"
  | "tool_using"
  | "responding"
  | "responded"
  | "planning"
  | "drafting"
  | "exploring"
  | "quizzing"
  | "reflecting";

/**
 * Picks the status label shown above the trace card.
 *
 * We scan in reverse so each round's latest signal wins — a tool result
 * mid-iteration flips the label back to reasoning, a planning chunk
 * arriving after a tool flips it to planning, etc. Per-mode mapping:
 *
 *   ``agent_loop_round``     → exploring  (chat exploring loop)
 *   ``llm_planning`` chunks  → planning   (solve plan / replan / pre-retrieve)
 *   ``tool_call`` event      → tool_using (any explicit tool call)
 *   ``llm_final_response``
 *     stage=``writing``      → responding (solve synthesize, also chat default)
 *     stage=``reasoning``    → drafting   (solve per-step answer)
 *   ``llm_reasoning`` chunks → reasoning  (generic reasoning trace)
 *
 * Falls back to ``reasoning`` while events are still warming up.
 */
function detectStreamingMode(
  events: StreamEvent[],
  hasFinalContent: boolean,
  isStreaming: boolean,
): StreamingMode {
  if (!isStreaming) return "responded";

  for (let idx = events.length - 1; idx >= 0; idx -= 1) {
    const event = events[idx];
    const meta = (event.metadata ?? {}) as Record<string, unknown>;
    const callKind = String(meta.call_kind ?? "");

    if (event.type === "tool_call") {
      // Tool calls inherit the active stage so the top-level status stays
      // coherent (e.g., a rag call during explore reads as "Exploring",
      // not generic "Tool Calling").
      if (event.stage === "exploring") return "exploring";
      if (event.stage === "quizzing") return "quizzing";
      return "tool_using";
    }
    if (event.type === "tool_result") {
      // Tool finished — keep scanning for the iteration's actual mode.
      continue;
    }
    // Quiz pipeline emits one ``quiz_question_emitted`` content event per
    // question with the structured qa_pair in metadata — that's the signal
    // the quizzing phase is active.
    if (callKind === "agent_loop_round") {
      // The chat loop streams user-facing text as `content` (a short
      // narration before a tool call, or the finish answer): show
      // "responding" while text is flowing; thinking keeps "exploring".
      return event.type === "content" ? "responding" : "exploring";
    }
    if (callKind === "quiz_question_emitted") return "quizzing";
    // Question pipeline's Tool Summarizer (Phase 1 reflection over a raw
    // tool result) streams chunks under ``call_kind="tool_result_reflection"``.
    // While those chunks are arriving — and until the next reasoning / tool
    // event flips the mode again — the top-level status row reads
    // "DeepTutor Reflecting…".
    if (callKind === "tool_result_reflection") return "reflecting";
    if (event.type === "content" && callKind === "llm_final_response") {
      // Some pipelines stream response text while an exploration stage is
      // still open; keep the top-level title on "DeepTutor Exploring…" until
      // the bus moves on.
      if (event.stage === "exploring") return "exploring";
      if (event.stage === "writing") return "responding";
      if (event.stage === "reasoning") return "drafting";
      return "responding";
    }
    if (callKind === "llm_planning") return "planning";
    if (event.type === "thinking" && callKind === "llm_reasoning") {
      if (event.stage === "exploring") return "exploring";
      if (event.stage === "quizzing") return "quizzing";
      return "reasoning";
    }
  }
  if (hasFinalContent) return "responding";
  return "reasoning";
}

function parsePositiveInt(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value) && value > 0) {
    return Math.floor(value);
  }
  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    if (Number.isFinite(parsed) && parsed > 0) return parsed;
  }
  return null;
}

function getResearchTopicIndex(meta: TraceMetadata): number | null {
  const explicit = parsePositiveInt(meta.topic_index);
  if (explicit) return explicit;

  const searchable = [meta.block_id, meta.call_id, meta.trace_id]
    .map((value) => String(value || ""))
    .join(" ");
  const match = /\bblock_(\d+)\b/.exec(searchable);
  return match ? parsePositiveInt(match[1]) : null;
}

function getDeepResearchStatusLabel(
  events: StreamEvent[],
  t: (key: string, opts?: Record<string, unknown>) => string,
  isStreaming: boolean,
) {
  if (!isStreaming) return null;

  for (let idx = events.length - 1; idx >= 0; idx -= 1) {
    const event = events[idx];
    if (event.source !== "deep_research") continue;

    const meta = getTraceMeta(event);
    const key = String(meta.research_status_key || "");

    if (key === "decompose_target" || event.stage === "decomposing") {
      return t("Decomposing Target");
    }

    if (key === "research_topic" || event.stage === "researching") {
      const topicIndex = getResearchTopicIndex(meta);
      return topicIndex
        ? t("Researching Topic #{{n}}", { n: topicIndex })
        : t("Researching Topic");
    }

    if (key === "report_intro") return t("Reporting Intro");
    if (key === "report_outline") return t("Reporting Outline");
    if (key === "report_conclusion") return t("Reporting Conclusion");
    if (key === "report_section") {
      const sectionIndex = parsePositiveInt(meta.section_index);
      return sectionIndex
        ? t("Reporting Section #{{n}}", { n: sectionIndex })
        : t("Reporting Section");
    }

    if (event.stage === "reporting") {
      const label = String(meta.label || "").toLowerCase();
      if (label.includes("intro") || label.includes("引言")) {
        return t("Reporting Intro");
      }
      if (label.includes("conclusion") || label.includes("结论")) {
        return t("Reporting Conclusion");
      }
      if (label.includes("section") || label.includes("章节")) {
        const sectionIndex = parsePositiveInt(meta.section_index);
        return sectionIndex
          ? t("Reporting Section #{{n}}", { n: sectionIndex })
          : t("Reporting Section");
      }
      return t("Reporting");
    }
  }

  return null;
}

// While the explore_context pre-pass is the most recent activity, the
// turn-level status reads "Exploring Your Contexts" instead of the generic
// reasoning label. Mirrors getDeepResearchStatusLabel: a backward scan that
// bails as soon as a later (answer-phase) activity is seen.
function getExploreContextStatusLabel(
  events: StreamEvent[],
  t: (key: string, opts?: Record<string, unknown>) => string,
  isStreaming: boolean,
) {
  if (!isStreaming) return null;
  for (let idx = events.length - 1; idx >= 0; idx -= 1) {
    const event = events[idx];
    const meta = getTraceMeta(event);
    const kind = String(meta.call_kind || "");
    const stage = String(event.stage || meta.phase || "");
    // Anything still inside the explore pre-pass — its reasoning rounds AND the
    // read_source tool calls it fires (stage="context_exploration") — keeps the
    // status on the explore verb, so it doesn't flicker to "Tool Calling…".
    if (kind === "context_exploration" || stage === "context_exploration") {
      return t("Exploring your context…");
    }
    // The answer loop has taken over — let the normal mode label win.
    if (
      kind === "agent_loop_round" ||
      kind === "llm_final_response" ||
      event.type === "tool_call" ||
      event.type === "content"
    ) {
      return null;
    }
  }
  return null;
}

export function StreamingStatus({
  events,
  isStreaming,
  content,
  className = "",
  expandable = false,
  expanded = false,
  onToggle,
  agentName,
  showMark = true,
}: {
  events: StreamEvent[];
  isStreaming?: boolean;
  content?: string;
  // Extra layout classes from the call site (e.g. ``mt-3`` when the row
  // sits at the bottom of the assistant output).
  className?: string;
  // When ``expandable`` the row becomes a disclosure toggle (a trailing
  // chevron rotates with ``expanded``) — used by ``AssistantActivity`` to
  // fold the trace nested beneath it.
  expandable?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
  // Who is doing the thinking — partner chat passes the partner's name so
  // the status reads "Ada Exploring…" instead of the product name.
  agentName?: string;
  // Partner chat shows the partner avatar beside this row, which already
  // signals "who / working", so it hides the activity mark to avoid two
  // icons fighting on one line.
  showMark?: boolean;
}) {
  const t = zhT;
  const [hovered, setHovered] = useState(false);
  const hasFinalContent = Boolean(content && content.trim().length > 0);
  const [nowSeconds, setNowSeconds] = useState(() => Date.now() / 1000);
  useEffect(() => {
    if (!isStreaming) return;
    const timer = window.setInterval(
      () => setNowSeconds(Date.now() / 1000),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [isStreaming]);

  // Only render once we either have a streaming turn OR a completed turn that
  // produced visible content — empty placeholders (e.g. system message
  // shells) shouldn't show a status row.
  if (!isStreaming && !hasFinalContent) return null;
  const mode = detectStreamingMode(
    events,
    hasFinalContent,
    Boolean(isStreaming),
  );

  const name = agentName?.trim() || "DeepTutor";
  let modeLabel = t("{{name}} Reasoning…", { name });
  if (mode === "tool_using") modeLabel = t("Tool Calling…");
  else if (mode === "planning") modeLabel = t("{{name}} Planning…", { name });
  else if (mode === "drafting") modeLabel = t("{{name}} Drafting…", { name });
  else if (mode === "responding")
    modeLabel = t("{{name}} Responding…", { name });
  else if (mode === "exploring") modeLabel = t("{{name}} Exploring…", { name });
  else if (mode === "quizzing") modeLabel = t("{{name}} Quizzing…", { name });
  else if (mode === "reflecting")
    modeLabel = t("{{name}} Reflecting…", { name });
  else if (mode === "responded") modeLabel = t("DeepTutor responded.");

  const label =
    getExploreContextStatusLabel(events, t, Boolean(isStreaming)) ??
    getDeepResearchStatusLabel(events, t, Boolean(isStreaming)) ??
    modeLabel;

  // Single turn-level clock. Ticks every second while the turn is in
  // flight and freezes on the final elapsed time once the answer ends —
  // replaces the per-sub-trace duration chips that used to live inside
  // the trace card.
  const turnSeconds = getTurnDurationSeconds(
    events,
    nowSeconds,
    Boolean(isStreaming),
  );
  const durationLabel =
    turnSeconds != null ? formatTurnDuration(turnSeconds) : null;
  // Static label after the answer is done — no breathing animation. The other
  // three states are live so they pulse to signal ongoing work. The icon also
  // stretches/contracts on its own cycle (out of phase with the opacity fade)
  // so the mark feels alive rather than just dimming with the label.
  const breathingClass = mode === "responded" ? "" : "dt-breathing-text";
  const markPulseClass = mode === "responded" ? "" : "dt-mark-pulse";
  const baseColor =
    mode === "responded"
      ? DT.mutedForegroundAlpha(0.7)
      : DT.mutedForeground;
  const Mark =
    mode === "tool_using"
      ? ToolMark
      : mode === "responding" || mode === "drafting"
        ? RespondingMark
        : mode === "responded"
          ? RespondedMark
          : ReasoningMark;

  const rowInner = (
    <>
      {showMark ? (
        <span
          style={{ color: DT.primaryAlpha(0.9), flexShrink: 0, display: "inline-flex" }}
        >
          <Mark
            size={22}
            strokeWidth={1.5}
            className={`${breathingClass} ${markPulseClass}`.trim() || undefined}
          />
        </span>
      ) : null}
      <span className={breathingClass || undefined}>{label}</span>
      {durationLabel ? (
        <span
          style={{
            fontSize: 12,
            fontWeight: 500,
            fontVariantNumeric: "tabular-nums",
            color: DT.mutedForegroundAlpha(0.55),
          }}
        >
          · {durationLabel}
        </span>
      ) : null}
    </>
  );

  // Disclosure-header flavor: clickable, with a trailing chevron that points
  // down when the nested trace is open and right when it's folded.
  if (expandable) {
    return (
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-live="polite"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className={className}
        style={{
          display: "flex",
          width: "100%",
          alignItems: "center",
          gap: 10,
          fontSize: 14,
          fontWeight: 600,
          lineHeight: 1,
          background: "none",
          border: "none",
          padding: 0,
          cursor: "pointer",
          font: "inherit",
          textAlign: "left",
          color: hovered ? DT.foreground : baseColor,
          transition: "color 150ms",
        }}
      >
        {rowInner}
        <DownOutlined
          style={{
            marginLeft: 2,
            flexShrink: 0,
            fontSize: 14,
            color: DT.mutedForegroundAlpha(0.45),
            transform: expanded ? undefined : "rotate(-90deg)",
            transition: "transform 200ms, color 200ms",
          }}
        />
      </button>
    );
  }

  // aria-live="polite" surfaces mode transitions to screen readers without
  // barging in on the user.
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="false"
      className={className}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontSize: 14,
        fontWeight: 600,
        lineHeight: 1,
        color: baseColor,
      }}
    >
      {rowInner}
    </div>
  );
}

/**
 * Whether ``events`` contain at least one renderable trace group — i.e. a
 * call_id whose group is NOT a pure final-response and NOT absorbed into the
 * final answer. Mirrors the gate ``TraceFlow``/``CallTracePanel`` use to
 * decide whether anything will actually render, so callers (e.g. the
 * activity header) can show a disclosure affordance only when there is a
 * trace to disclose.
 */
function hasRenderableCallTrace(events: StreamEvent[]): boolean {
  const seen = new Map<string, { hasFinal: boolean; hasAbsorbed: boolean }>();
  for (const event of events) {
    const meta = (event.metadata ?? {}) as Record<string, unknown>;
    const cid = String(meta.call_id || "");
    if (!cid) continue;
    const entry = seen.get(cid) ?? { hasFinal: false, hasAbsorbed: false };
    if (meta.call_kind === "llm_final_response") entry.hasFinal = true;
    if (meta.absorbed_into_final === true) entry.hasAbsorbed = true;
    seen.set(cid, entry);
  }
  // 原件为 for..of seen.values()（Map 迭代器语法）；tupu target es5 下该语法需
  // downlevelIteration，等价改写为 Array.from(...) 数组遍历（语义一致，登记）。
  for (const { hasFinal, hasAbsorbed } of Array.from(seen.values())) {
    if (!hasFinal && !hasAbsorbed) return true;
  }
  return false;
}

/**
 * Inline trace rows for the assistant message flow: each trace renders as
 * its own one-line, expandable, live-streaming row — there is no outer
 * trace card. Group-level fold (open while working, collapsed once the
 * final answer lands) is handled by ``AssistantActivity``, which nests this
 * directly under the status header.
 */
export function TraceFlow({
  events,
  isStreaming,
}: {
  events: StreamEvent[];
  isStreaming?: boolean;
}) {
  // Mount only when at least one renderable trace group exists — groups
  // that CallTracePanel would discard (final-response only, or reasoning
  // sub-traces absorbed into the final answer) must not leave a stray
  // margin behind.
  const hasCallTrace = useMemo(() => hasRenderableCallTrace(events), [events]);

  if (!hasCallTrace) return null;
  return <CallTracePanel events={events} isStreaming={isStreaming} />;
}

/**
 * Has the turn entered its final-answer phase? Used to auto-collapse the
 * reasoning trace once DeepTutor stops working and starts (or has finished)
 * its answer.
 *
 *  - turn complete (``!isStreaming``)                    → final
 *  - a pipeline streaming its final write (solve/research) → final
 *    (``detectStreamingMode`` → responding / responded)
 *  - chat single loop: the tool-less round's ``finish`` marker landed
 *
 * The chat loop streams its final answer as ``agent_loop_round`` content
 * (which ``detectStreamingMode`` reads as "exploring"), so the ``finish``
 * marker — emitted when that round completes — is the chat-path signal.
 */
function hasFinishMarker(events: StreamEvent[]): boolean {
  for (let idx = events.length - 1; idx >= 0; idx -= 1) {
    const meta = getTraceMeta(events[idx]);
    if (
      meta.trace_kind === "call_status" &&
      meta.call_state === "complete" &&
      meta.call_role === "finish"
    ) {
      return true;
    }
  }
  return false;
}

function isChatLoopTurn(events: StreamEvent[]): boolean {
  for (const event of events) {
    if (String(getTraceMeta(event).call_kind || "") === "agent_loop_round") {
      return true;
    }
  }
  return false;
}

function isFinalAnswerPhase(
  events: StreamEvent[],
  isStreaming: boolean,
  hasFinalContent: boolean,
): boolean {
  if (!isStreaming) return true;
  if (hasFinishMarker(events)) return true;
  const mode = detectStreamingMode(events, hasFinalContent, true);
  if (mode === "responding" || mode === "responded") {
    // Chat's single loop streams narration text mid-loop, which also reads
    // as "responding" — there only the finish marker (above) settles the
    // phase; trusting the mode would flap the trace shut on every
    // narration line and open again on the next tool call.
    return !isChatLoopTurn(events);
  }
  return false;
}

/**
 * The assistant activity block: the status header
 * ("DeepTutor Exploring… · 8s", settling to "DeepTutor responded. · 10s")
 * with the exploring trace nested directly beneath it.
 *
 * The trace is expanded by default while DeepTutor is still reasoning /
 * exploring, and collapses once the turn resolves into its final answer.
 * The header doubles as a disclosure toggle, so the user can re-open a
 * collapsed trace (or fold an expanded one) at any time.
 */
export function AssistantActivity({
  events,
  isStreaming,
  content,
  className = "",
  agentName,
  showMark = true,
  headerClassName = "",
}: {
  events: StreamEvent[];
  isStreaming?: boolean;
  content?: string;
  className?: string;
  /** Forwarded to StreamingStatus — names the thinker in the status row. */
  agentName?: string;
  /** Hide the activity mark (partner chat shows its avatar instead). */
  showMark?: boolean;
  /** Extra classes on the status header row (e.g. a min-height so the row
   *  vertically centers against an adjacent avatar). */
  headerClassName?: string;
}) {
  const hasTrace = useMemo(() => hasRenderableCallTrace(events), [events]);
  const hasFinalContent = Boolean(content && content.trim().length > 0);
  const finalPhase = useMemo(
    () => isFinalAnswerPhase(events, Boolean(isStreaming), hasFinalContent),
    [events, isStreaming, hasFinalContent],
  );
  // null = follow the phase automatically (open while working, collapsed
  // once answered). A click pins the user's choice for this message.
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const open = hasTrace && (userOpen ?? !finalPhase);

  // Match StreamingStatus's own null-guard: nothing to show for an empty,
  // non-streaming shell with no trace either.
  if (!isStreaming && !hasFinalContent && !hasTrace) return null;

  return (
    <div className={className}>
      <StreamingStatus
        events={events}
        isStreaming={isStreaming}
        content={content}
        expandable={hasTrace}
        expanded={open}
        onToggle={() => setUserOpen(!open)}
        agentName={agentName}
        showMark={showMark}
        className={headerClassName}
      />
      {/* 【登记·降级】原实现为 grid-rows-[0fr]→[1fr] + opacity 过渡
          （transition-[grid-template-rows,opacity] duration-300 ease-out），
          此处按登记式降级改为条件渲染；参数见文件头替换点 7。 */}
      {hasTrace && open ? (
        <div style={{ overflow: "hidden" }}>
          {/* The trace hangs from a faint guide line aligned under the
              header's activity mark, so it reads as "nested below" the
              status (the elbow/tree language used elsewhere). */}
          <div
            style={{
              marginLeft: 11,
              borderLeft: `1px solid ${DT.borderAlpha(0.45)}`,
              paddingLeft: 13,
              paddingTop: 8,
            }}
          >
            <TraceFlow events={events} isStreaming={isStreaming} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ResearchStagePanel                                                 */
/* ------------------------------------------------------------------ */

function getResearchStageId(event: StreamEvent): ResearchStageCard["id"] {
  const meta = getTraceMeta(event);
  const explicitStage = String(
    (event.metadata as Record<string, unknown> | undefined)
      ?.research_stage_card || "",
  );
  if (
    explicitStage === "understand" ||
    explicitStage === "decompose" ||
    explicitStage === "evidence" ||
    explicitStage === "result"
  ) {
    return explicitStage;
  }
  const stage = String(event.stage || meta.phase || "");
  const text = String(event.content || "").toLowerCase();
  const agent = String(
    (event.metadata as Record<string, unknown> | undefined)?.agent_name || "",
  );

  if (stage === "reporting") return "result";
  if (stage === "decomposing" || agent === "decompose_agent")
    return "decompose";
  if (stage === "rephrasing" || agent === "rephrase_agent") return "understand";
  if (stage === "planning") {
    if (text.includes("decompose") || text.includes("queue"))
      return "decompose";
    return "understand";
  }
  return "evidence";
}

function formatResearchStageSummary(events: StreamEvent[], fallback: string) {
  const progressEvents = events.filter(
    (event) => event.type === "progress" && event.content.trim().length > 0,
  );
  const lastProgress = progressEvents.at(-1)?.content.trim();
  if (lastProgress) {
    return humanizeQuestionId(titleCase(lastProgress.replaceAll("-", "_")));
  }

  const thought = getTraceText(events, ["thinking"]);
  if (thought) return thought.slice(0, 120);

  const content = getTraceText(events, ["content"]);
  if (content) return content.slice(0, 120);

  return fallback;
}

export function ResearchStagePanel({
  events,
  isStreaming,
}: {
  events: StreamEvent[];
  isStreaming?: boolean;
}) {
  const t = zhT;
  const cards = useMemo<ResearchStageCard[]>(() => {
    return RESEARCH_STAGE_SPECS.map((spec) => ({
      id: spec.id,
      title: t(spec.titleKey),
      hint: t(spec.hintKey),
      events: events.filter((event) => getResearchStageId(event) === spec.id),
    })).filter((card) => card.events.length > 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events]);

  if (!cards.length) return null;

  return (
    <div style={{ marginBottom: 12, display: "grid", rowGap: 2 }}>
      {cards.map((card, index) => {
        const hasTrace = card.events.some((event) =>
          Boolean(getTraceMeta(event).call_id),
        );
        const active =
          Boolean(isStreaming) &&
          index === cards.length - 1 &&
          card.events.some(
            (event) => isTracePending([event]) || event.type === "progress",
          );
        const summary = formatResearchStageSummary(card.events, card.hint);

        return (
          <div key={card.id}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "4px 0",
                fontSize: 12,
                color: DT.mutedForeground,
              }}
            >
              <span style={{ fontWeight: 600 }}>{card.title}</span>
              <span style={{ fontSize: 11, opacity: 0.6 }}>{summary}</span>
              {active && (
                <LoadingOutlined
                  spin
                  style={{ fontSize: 11, color: DT.primary }}
                />
              )}
            </div>
            {hasTrace ? (
              <CallTracePanel events={card.events} isStreaming={isStreaming} />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
