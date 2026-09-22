/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/ChatComposer.tsx，1164 行）。
 * 消费方：h5/chat 的 FollowupChatComposer（原仓 components/quiz/FollowupChatComposer.tsx
 * L608 调用点，props 一一对位，见文件尾对位注释）。
 * 替换点（批8/批9 通行约定）：
 * - 删除 "use client"；不用 next/*；
 * - lucide-react → @ant-design/icons（size/strokeWidth → style.fontSize；色彩用
 *   style.color）：ArrowUp→ArrowUpOutlined、BookOpen→BookOutlined、Bot→RobotOutlined、
 *   Brain→BulbOutlined、Check→CheckOutlined、ChevronDown→DownOutlined、
 *   ChevronRight→RightOutlined、ClipboardList→SnippetsOutlined、Loader2→
 *   LoadingOutlined(spin)、MessageSquare→MessageOutlined、Mic→AudioOutlined、
 *   Paperclip→PaperClipOutlined、Plus→PlusOutlined、Sparkles→StarOutlined、
 *   Square→BorderOutlined、UserRound→UserOutlined、X→CloseOutlined；
 *   LucideIcon 类型 → ComponentType<{className?;style?}>（FollowupChatComposer 的
 *   FOLLOWUP_CAPABILITIES_RAW icon 字段需传 antd 图标组件）；
 * - framer-motion 未安装（登记式降级，批8 Mermaid.tsx/VisualizationViewer.tsx 先例）：
 *   AnimatePresence+motion.div（"+" 菜单入场/出场动画）→ 条件渲染普通 div；
 *   【登记替换点：安装 framer-motion 后恢复 motion.div initial/animate/exit 动画，
 *   原参数 initial={{opacity:0,y:6,scale:0.96}} animate={{opacity:1,y:0,scale:1}}
 *   exit={{opacity:0,y:4,scale:0.97}} transition={{duration:0.16,ease:[0.16,1,0.3,1]}}】；
 *   animate-spin/animate-pulse → 本文件内联 <style> @keyframes（dt-spin/dt-pulse）；
 * - Tailwind → 内联样式（颜色 token 批8 同款，见 dtStyle.ts）；hover →
 *   onMouseEnter/Leave 直写 style；group-hover 附件移除钮 → 卡片级 hover 状态；
 * - i18n t() → zh/app.json 原译文中文直出（"Book"→书籍、"Notebook"→笔记本、
 *   "Chat History"→聊天历史、"My Agents"→我的智能体、"Question Bank"→题库、
 *   "Memory"→记忆、"Summary"→总结、"Profile"→配置文件、"Send"→发送、
 *   "Stop generating"→停止生成、"Confirm settings on the right to send."→
 *   请先在右侧确认设置后再发送。、"Drop files here"→拖拽文件到此处、
 *   "Images, Office docs, code & text"→图片、Office 文档、代码和文本、"Preview"→预览、
 *   "Remove attachment"→移除附件、"Attachment preview"→附件预览、
 *   "More Capabilities"→更多能力、"Agent-loop driven modes"→由对话引擎驱动的模式）；
 *   zh/app.json 无键的 "Persona"/"Add files & context"/"Stop recording"/
 *   "Record voice"/"references" 按 i18next 缺键回退行为直出原 key；
 *   capability 的 label/description 由调用方预翻译，本件 t(x) 对已译文案恒等返回
 *   （i18next 对非键字符串原样返回的等价行为）；
 * - @/lib/doc-attachments → ./doc-attachments（批8 admin 件 + 批9 补齐
 *   isSvgFilename/docIconFor，lucide 图标表→antd 等价表，spec.tint 类串→rgba 色，
 *   消费侧由 className 改 style.color）；useVoiceRecorder → ../learn/useVoiceRecorder
 *   （批9 SA-A 已移植 1:1 件，复用不双写）；类型来自 ./HistorySessionPicker、
 *   ./QuestionBankPicker、../../admin/book-references、./space-items、
 *   ./notebook-selection-types、../../admin/unified-ws、./llmOptions；
 * - data-testid/aria-label 逐字保留（chat-send/chat-attachment-preview/
 *   chat-attachment-remove/chat-composer-input）。
 * 功能（四态发送钮/紧凑降级 ResizeObserver/能力菜单+More 飞出/引用树/附件预览卡/
 * 麦克风听写/预填 ref/焦点恢复）逐字未改。
 */
import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ComponentType,
  type CSSProperties,
  type RefObject,
} from "react";
import {
  ArrowUpOutlined,
  BookOutlined,
  RobotOutlined,
  BulbOutlined,
  CheckOutlined,
  DownOutlined,
  RightOutlined,
  SnippetsOutlined,
  LoadingOutlined,
  MessageOutlined,
  AudioOutlined,
  PaperClipOutlined,
  PlusOutlined,
  StarOutlined,
  BorderOutlined,
  UserOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import {
  ATTACHMENT_ACCEPT,
  docIconFor,
  formatBytes,
  isSvgFilename,
} from "./doc-attachments";
import type { SelectedHistorySession } from "./HistorySessionPicker";
import type { SelectedQuestionEntry } from "./QuestionBankPicker";
import type { SelectedRecord } from "./notebook-selection-types";
import type { LLMSelection } from "../../admin/unified-ws";
import type { LLMOption } from "./llmOptions";
import ChatSpaceMenu from "./ChatSpaceMenu";
import type { SpaceMemoryFile } from "./space-items";
import type { SelectedBookReference } from "../../admin/book-references";
import AgentSelector from "./AgentSelector";
import ContextBudgetChip, { type ContextBudget } from "./ContextBudgetChip";
import KnowledgeSelector from "./KnowledgeSelector";
import ModelSelector from "./ModelSelector";
import PersonaSelector from "./PersonaSelector";
import ContextReferenceTree, {
  type ContextTreeItem,
} from "./ContextReferenceTree";
import { ComposerInput, type ComposerInputHandle } from "./ComposerInput";
import { useVoiceRecorder } from "../learn/useVoiceRecorder";
import { DT, ellipsis } from "./dtStyle";

type SpaceSelectionCounts = {
  attachments: number;
  knowledge: number;
  chatHistory: number;
  myAgents: number;
  books: number;
  notebooks: number;
  questionBank: number;
  persona: number;
  memory: number;
};

/** @ant-design/icons 组件类型（原 LucideIcon 的等价替换）。 */
type IconType = ComponentType<{ className?: string; style?: CSSProperties }>;

interface PendingAttachment {
  type: string;
  filename: string;
  base64?: string;
  previewUrl?: string;
  size?: number;
  mimeType?: string;
}

interface KnowledgeBase {
  name: string;
}

interface CapabilityDef {
  value: string;
  label: string;
  description: string;
  icon: IconType;
  allowedTools: string[];
  // Loop-engine capabilities (solve / mastery) run on the chat agent loop and
  // are collapsed into the "More" flyout instead of listed directly.
  loopEngine?: boolean;
}

/** One row in the capability picker — shared by the built-in list and the
 *  "More" flyout so both render identically. */
function CapMenuItem({
  cap,
  selected,
  onSelect,
}: {
  cap: CapabilityDef;
  selected: boolean;
  onSelect: (value: string) => void;
}) {
  const Icon = cap.icon;
  return (
    <button
      type="button"
      onClick={() => onSelect(cap.value)}
      onMouseEnter={(e) => {
        if (!selected) e.currentTarget.style.background = DT.mutedAlpha(0.45);
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = selected
          ? DT.primaryAlpha(0.06)
          : "transparent";
      }}
      style={{
        display: "flex",
        width: "100%",
        alignItems: "center",
        gap: 10,
        padding: "6px 12px",
        textAlign: "left",
        border: "none",
        cursor: "pointer",
        background: selected ? DT.primaryAlpha(0.06) : "transparent",
        font: "inherit",
      }}
    >
      <Icon
        style={{
          fontSize: 15,
          flexShrink: 0,
          color: selected ? DT.primary : DT.mutedForeground,
        }}
      />
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ ...ellipsis, fontSize: 12.5, fontWeight: 500, lineHeight: 1.375, color: DT.foreground }}>
          {cap.label}
        </div>
        <div style={{ ...ellipsis, fontSize: 11, lineHeight: 1.375, color: DT.mutedForeground }}>
          {cap.description}
        </div>
      </div>
      {selected && (
        <CheckOutlined
          style={{ fontSize: 14, flexShrink: 0, color: DT.primary }}
        />
      )}
    </button>
  );
}

/**
 * The composer's primary action is a single control that spans the whole
 * turn — send, working, stop — rather than two buttons that swap places at
 * the moment of the click. These are its four states; only the skin changes.
 */
type SendState = "idle" | "blocked" | "ready" | "streaming";

/**
 * `idle` keeps a legible glyph on a hairline ring instead of fading the whole
 * button down: a translucent arrow on an equally translucent fill left the
 * arrow invisible in every theme. Readiness is carried by colour (neutral →
 * primary), not by opacity.
 *
 * Translucency goes through `color-mix` rather than Tailwind's `/NN` opacity
 * modifier. Tailwind 3 can only apply that modifier to colours it can split
 * into channels, so `bg-[var(--primary)]/90` — where the variable holds a hex
 * literal — compiles to nothing at all. `hover:ring-[5px]` and the lift carry
 * the hover state here; the fill deliberately doesn't shift, which also keeps
 * it from having to mix in a direction that reads right on all four themes.
 */
const SEND_STATE_STYLE: Record<
  SendState,
  { background: string; color: string; boxShadow?: string; cursor: string }
> = {
  idle: {
    background: "transparent",
    color: DT.mutedForeground,
    boxShadow: "inset 0 0 0 1px #e4e4e7",
    cursor: "default",
  },
  // The glyph goes to `--foreground`, not `--primary-foreground`: this fill is
  // a wash of `--muted-foreground` and therefore sits near the background, so
  // only the foreground colour is guaranteed to read against it on all four
  // themes. (Inherited as `--primary-foreground`, which was white on pale grey
  // — invisible — but never showed because the old `/30` compiled to nothing.)
  blocked: {
    background: "rgba(107,114,128,0.3)",
    color: DT.foreground,
    cursor: "pointer",
  },
  ready: {
    background: DT.primary,
    color: DT.primaryForeground,
    boxShadow: "0 0 0 3px rgba(22,119,255,0.18)",
    cursor: "pointer",
  },
  streaming: {
    background: DT.primary,
    color: DT.primaryForeground,
    cursor: "pointer",
  },
};

// zh/app.json 原译文替换表（t() 中文直出）；未列出的键走缺键回退（直出原 key）。
const ZH: Record<string, string> = {
  Book: "书籍",
  Notebook: "笔记本",
  "Chat History": "聊天历史",
  "My Agents": "我的智能体",
  "Question Bank": "题库",
  Memory: "记忆",
  Summary: "总结",
  Profile: "配置文件",
  Send: "发送",
  "Stop generating": "停止生成",
  "Confirm settings on the right to send.": "请先在右侧确认设置后再发送。",
  "Drop files here": "拖拽文件到此处",
  "Images, Office docs, code & text": "图片、Office 文档、代码和文本",
  Preview: "预览",
  "Remove attachment": "移除附件",
  "Attachment preview": "附件预览",
  "More Capabilities": "更多能力",
  "Agent-loop driven modes": "由对话引擎驱动的模式",
};

/** t(x) 的等价实现：键表命中直出译文，否则原样返回（i18next 缺键回退行为）。 */
function zh(text: string): string {
  return ZH[text] ?? text;
}

export default memo(function ChatComposer({
  composerRef,
  capMenuRef,
  capBtnRef,
  spaceMenuRef,
  spaceBtnRef,
  dragCounter,
  dragging,
  capMenuOpen,
  spaceMenuOpen,
  hasMessages,
  attachments,
  attachmentError,
  activeCap,
  knowledgeBases,
  connectedAgents = [],
  selectedAgent = null,
  onSelectAgent,
  subagentBudget = null,
  onSubagentBudgetChange,
  llmOptions,
  activeLLMDefault,
  llmSelection,
  llmOptionsLoading,
  llmOptionsError,
  contextBudget = null,
  selectedNotebookRecords,
  selectedBookReferences,
  selectedHistorySessions,
  selectedAgentSessions,
  selectedQuestionEntries,
  notebookReferenceGroups,
  selectedPersona,
  selectedMemoryFiles,
  selectedKnowledgeBases,
  isStreaming,
  isVisualizeMode,
  capabilityNeedsConfig,
  capabilityConfigConfirmed,
  onRequestConfigConfirm,
  capabilities,
  onSetCapMenuOpen,
  onSetSpaceMenuOpen,
  onToggleKB,
  onSelectLLM,
  onSelectNotebookPicker,
  onSelectBookPicker,
  onSelectHistoryPicker,
  onSelectAgentsPicker,
  onSelectQuestionBankPicker,
  onSelectPersonaPicker,
  onSelectMemoryPicker,
  onClearPersona,
  personaSelection,
  onPersonaSelectionChange,
  personaSelectorOpen,
  onPersonaSelectorOpenChange,
  agentsAvailable = true,
  onToggleMemoryFile,
  onSend,
  onRemoveAttachment,
  onPreviewAttachment,
  onRemoveHistory,
  onRemoveAgent,
  onRemoveBookReference,
  onRemoveNotebook,
  onRemoveQuestion,
  onDragEnter,
  onDragLeave,
  onDragOver,
  onDrop,
  onPaste,
  onAddFiles,
  onSelectCapability,
  onCancelStreaming,
  prefillInputRef,
  inputPlaceholder,
}: {
  // React 18 类型（@types/react 18.3）下 RefObject<T|null> 对 RefObject<T> 型变
  // 不兼容，故沿用原仓字面 RefObject<HTMLDivElement>（18.3 中 current 即
  // HTMLDivElement|null，与原仓 React 19 语义等价）。
  composerRef: RefObject<HTMLDivElement>;
  capMenuRef: RefObject<HTMLDivElement>;
  capBtnRef: RefObject<HTMLButtonElement>;
  spaceMenuRef: RefObject<HTMLDivElement>;
  spaceBtnRef: RefObject<HTMLButtonElement>;
  dragCounter: RefObject<number>;
  dragging: boolean;
  capMenuOpen: boolean;
  spaceMenuOpen: boolean;
  hasMessages: boolean;
  attachments: PendingAttachment[];
  attachmentError: string | null;
  activeCap: CapabilityDef;
  knowledgeBases: KnowledgeBase[];
  /** Connected local subagents (Claude Code / Codex) selectable for this turn. */
  connectedAgents?: { name: string; kind?: string }[];
  /** The connected agent selected for this turn, if any (single-select). */
  selectedAgent?: string | null;
  onSelectAgent?: (name: string | null) => void;
  /** Max times DeepTutor may consult the selected agent this turn. */
  subagentBudget?: number | null;
  onSubagentBudgetChange?: (budget: number) => void;
  llmOptions: LLMOption[];
  activeLLMDefault: LLMSelection | null;
  llmSelection: LLMSelection | null;
  llmOptionsLoading: boolean;
  llmOptionsError: boolean;
  /**
   * Context-window breakdown measured on the last turn that reported one.
   * Omitted by surfaces that don't track it (quiz follow-up) and null until
   * the first turn completes — the chip is skipped entirely in both cases.
   */
  contextBudget?: ContextBudget | null;
  selectedNotebookRecords: SelectedRecord[];
  selectedBookReferences: SelectedBookReference[];
  selectedHistorySessions: SelectedHistorySession[];
  selectedAgentSessions: SelectedHistorySession[];
  selectedQuestionEntries: SelectedQuestionEntry[];
  notebookReferenceGroups: Array<{
    notebookId: string;
    notebookName: string;
    count: number;
  }>;
  selectedPersona: string | null;
  selectedMemoryFiles: SpaceMemoryFile[];
  selectedKnowledgeBases: string[];
  isStreaming: boolean;
  isVisualizeMode: boolean;
  /**
   * True when the active capability (e.g. Quiz / Visualize / Research)
   * requires explicit configuration before sending. When true, `canSend`
   * is gated on `capabilityConfigConfirmed`.
   */
  capabilityNeedsConfig: boolean;
  capabilityConfigConfirmed: boolean;
  /**
   * Called when the user clicks the send button while config is required
   * but not yet confirmed. The page uses this to surface the config card
   * (open the Activity panel, scroll to it, etc.).
   */
  onRequestConfigConfirm: () => void;
  capabilities: CapabilityDef[];
  onSetCapMenuOpen: (open: boolean | ((prev: boolean) => boolean)) => void;
  onSetSpaceMenuOpen: (open: boolean | ((prev: boolean) => boolean)) => void;
  onToggleKB: (name: string) => void;
  onSelectLLM: (selection: LLMSelection | null) => void;
  onSelectNotebookPicker: () => void;
  onSelectBookPicker: () => void;
  onSelectHistoryPicker: () => void;
  onSelectAgentsPicker: () => void;
  onSelectQuestionBankPicker: () => void;
  onSelectPersonaPicker: () => void;
  onSelectMemoryPicker: () => void;
  onClearPersona: () => void;
  /**
   * Session-persona wiring (main chat only). When `onPersonaSelectionChange`
   * is provided, the toolbar shows a PersonaSelector chip and the composer
   * accepts the `/persona` slash command. The quiz follow-up surface omits
   * these and keeps its per-turn persona picker flow.
   */
  personaSelection?: string;
  onPersonaSelectionChange?: (persona: string) => void;
  personaSelectorOpen?: boolean;
  onPersonaSelectorOpenChange?: (open: boolean) => void;
  /** Hide the My Agents reference entry (e.g. the quiz follow-up surface). */
  agentsAvailable?: boolean;
  onToggleMemoryFile: (file: SpaceMemoryFile) => void;
  onSend: (content: string) => void;
  onRemoveAttachment: (index: number) => void;
  onPreviewAttachment?: (index: number) => void;
  onRemoveHistory: (sessionId: string) => void;
  onRemoveAgent: (sessionId: string) => void;
  onRemoveBookReference: (bookId: string) => void;
  onRemoveNotebook: (notebookId: string) => void;
  onRemoveQuestion: (entryId: number) => void;
  onDragEnter: (event: React.DragEvent) => void;
  onDragLeave: (event: React.DragEvent) => void;
  onDragOver: (event: React.DragEvent) => void;
  onDrop: (event: React.DragEvent) => void;
  onPaste: (event: React.ClipboardEvent) => void;
  onAddFiles: (files: File[]) => void;
  onSelectCapability: (value: string) => void;
  onCancelStreaming: () => void;
  /**
   * Optional ref the composer writes its ``prefillInput`` function into
   * once mounted, so the message-list side (specifically
   * ``AskUserOptions`` chips) can drop a string into the textarea
   * without owning the composer's imperative handle directly.
   */
  prefillInputRef?: React.MutableRefObject<((text: string) => void) | null>;
  /** Override the composer placeholder (e.g. quiz follow-up). */
  inputPlaceholder?: string;
}) {
  const CapIcon = activeCap.icon;

  const [hasContent, setHasContent] = useState(false);
  const [moreCapsOpen, setMoreCapsOpen] = useState(false);
  const [lastCapMenuOpen, setLastCapMenuOpen] = useState(capMenuOpen);
  const [hoveredAttachment, setHoveredAttachment] = useState<string | null>(
    null,
  );
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const restoreFocusOnReturnRef = useRef(false);
  const inputHandleRef = useRef<ComposerInputHandle>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  if (lastCapMenuOpen !== capMenuOpen) {
    setLastCapMenuOpen(capMenuOpen);
    if (!capMenuOpen) setMoreCapsOpen(false);
  }

  useEffect(() => {
    if (!prefillInputRef) return;
    prefillInputRef.current = (text: string) => {
      inputHandleRef.current?.setValue(text);
    };
    return () => {
      if (prefillInputRef) prefillInputRef.current = null;
    };
  }, [prefillInputRef]);

  // Microphone → speech-to-text. Appends the transcript to whatever is already
  // in the composer so a dictated phrase can be combined with typed text.
  const handleTranscript = useCallback((text: string) => {
    const current = inputHandleRef.current?.getValue() || "";
    const next = current.trim() ? `${current.trimEnd()} ${text}` : text;
    inputHandleRef.current?.setValue(next);
  }, []);
  const recorder = useVoiceRecorder(handleTranscript);

  // Composer-row compaction: when the available width drops below ~620 px
  // (e.g. the Viewer panel is open or the user is on a narrow viewport),
  // the cap chip + Tools/Attach/Space labels collide. We measure the
  // composer itself and flip those labels to icon-only below the
  // threshold. Count-badges stay visible so users still see how many
  // things are selected.
  const [composerCompact, setComposerCompact] = useState(false);
  useEffect(() => {
    const el = composerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    setComposerCompact(el.getBoundingClientRect().width < 620);
    const observer = new ResizeObserver(() => {
      if (composerRef.current) {
        setComposerCompact(
          composerRef.current.getBoundingClientRect().width < 620,
        );
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [composerRef]);

  const handlePickFiles = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const picked = Array.from(event.target.files ?? []);
      if (picked.length) onAddFiles(picked);
      // Reset so picking the same file twice still triggers `change`.
      event.target.value = "";
    },
    [onAddFiles],
  );

  const focusTextarea = useCallback(() => {
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  useEffect(() => {
    const rememberFocus = () => {
      restoreFocusOnReturnRef.current =
        document.activeElement === textareaRef.current;
    };
    const restoreFocus = () => {
      if (
        restoreFocusOnReturnRef.current &&
        document.visibilityState === "visible"
      ) {
        focusTextarea();
      }
    };

    window.addEventListener("blur", rememberFocus);
    window.addEventListener("focus", restoreFocus);
    document.addEventListener("visibilitychange", restoreFocus);
    return () => {
      window.removeEventListener("blur", rememberFocus);
      window.removeEventListener("focus", restoreFocus);
      document.removeEventListener("visibilitychange", restoreFocus);
    };
  }, [focusTextarea]);

  useEffect(() => {
    if (!hasMessages) focusTextarea();
  }, [hasMessages, focusTextarea]);

  const handleSelectCapability = useCallback(
    (value: string) => {
      setMoreCapsOpen(false);
      onSelectCapability(value);
    },
    [onSelectCapability],
  );

  // Functional-update form keeps `handleInputChange` identity stable across
  // every keystroke (no `hasContent` in deps), so the memoized ComposerInput
  // doesn't get re-rendered just because we observed a content-empty toggle.
  const handleInputChange = useCallback((val: string) => {
    const next = !!val.trim();
    setHasContent((prev) => (prev === next ? prev : next));
  }, []);

  const doSend = useCallback(
    (content: string) => {
      onSend(content);
      setHasContent(false);
      inputHandleRef.current?.clear();
      // Sending can move focus to the button or rerender the empty-state
      // composer into the conversation layout. Restore it after that update
      // so the user can keep typing, including after switching back to the tab.
      focusTextarea();
    },
    [focusTextarea, onSend],
  );

  const hasReferences =
    !!attachments.length ||
    !!selectedBookReferences.length ||
    !!selectedNotebookRecords.length ||
    !!selectedHistorySessions.length ||
    !!selectedAgentSessions.length ||
    !!selectedQuestionEntries.length ||
    !!selectedPersona ||
    !!selectedMemoryFiles.length;

  // `capabilityNeedsConfig && !capabilityConfigConfirmed` blocks send so the
  // user has to click *Confirm* in the right-side Activity panel first.
  // Clicking the send button while in this state surfaces the config card
  // (via `onRequestConfigConfirm`) instead of silently doing nothing.
  const isConfigBlocked = capabilityNeedsConfig && !capabilityConfigConfirmed;
  const hasIntent = hasContent || hasReferences;
  const canSend = hasIntent && !isStreaming && !isConfigBlocked;

  // `blocked` only exists once there is intent: without it the button stays
  // `idle` so an empty composer doesn't present a live send affordance. That
  // makes intent — not `canSend` — the thing that decides interactivity, so
  // the `blocked` state can stay clickable and surface the config card.
  const sendState: SendState = isStreaming
    ? "streaming"
    : !hasIntent
      ? "idle"
      : isConfigBlocked
        ? "blocked"
        : "ready";

  const spaceSelectionCounts: SpaceSelectionCounts = {
    attachments: attachments.length,
    knowledge: selectedKnowledgeBases.length,
    chatHistory: selectedHistorySessions.length,
    myAgents: selectedAgentSessions.length,
    books: selectedBookReferences.reduce(
      (total, ref) => total + ref.pages.length,
      0,
    ),
    notebooks: selectedNotebookRecords.length,
    questionBank: selectedQuestionEntries.length,
    persona: selectedPersona ? 1 : 0,
    memory: selectedMemoryFiles.length,
  };
  // Badge on the "+" button = how many things are selected through the
  // "+" menu. Knowledge is excluded: it no longer lives in this menu —
  // it has its own toolbar chip (KnowledgeSelector) with its own active
  // state, so counting it here would double-signal.
  const contextSelectionCount = Object.entries(spaceSelectionCounts).reduce(
    (total, [key, count]) => (key === "knowledge" ? total : total + count),
    0,
  );

  // Unified reference tree above the textarea: Space references, persona
  // and memory render as quiet monochrome rows, collapsed behind a count
  // by default. File attachments intentionally stay OUT of the tree —
  // they keep their preview cards below the textarea.
  // Knowledge bases are intentionally NOT in this tree: they are a
  // session-level retrieval SCOPE (sticky, persisted), not a one-shot
  // reference like the rows below. That sticky state lives in the
  // toolbar KnowledgeSelector chip instead — same lifecycle class as
  // the persona selector.
  const contextTreeItems: ContextTreeItem[] = [
    ...selectedBookReferences.map(
      (book): ContextTreeItem => ({
        key: `book-${book.bookId}`,
        icon: BookOutlined,
        kind: zh("Book"),
        label: `${book.bookTitle} (${book.pages.length})`,
        onRemove: () => onRemoveBookReference(book.bookId),
      }),
    ),
    ...notebookReferenceGroups.map(
      (group): ContextTreeItem => ({
        key: `nb-${group.notebookId}`,
        icon: BookOutlined,
        kind: zh("Notebook"),
        label: `${group.notebookName} (${group.count})`,
        onRemove: () => onRemoveNotebook(group.notebookId),
      }),
    ),
    ...selectedHistorySessions.map(
      (session): ContextTreeItem => ({
        key: `hist-${session.sessionId}`,
        icon: MessageOutlined,
        kind: zh("Chat History"),
        label: session.title,
        onRemove: () => onRemoveHistory(session.sessionId),
      }),
    ),
    ...selectedAgentSessions.map(
      (session): ContextTreeItem => ({
        key: `agent-${session.sessionId}`,
        icon: RobotOutlined,
        kind: zh("My Agents"),
        label: session.title,
        onRemove: () => onRemoveAgent(session.sessionId),
      }),
    ),
    ...selectedQuestionEntries.map(
      (entry): ContextTreeItem => ({
        key: `q-${entry.id}`,
        icon: SnippetsOutlined,
        kind: zh("Question Bank"),
        label: entry.question,
        onRemove: () => onRemoveQuestion(entry.id),
      }),
    ),
    ...(selectedPersona
      ? [
          {
            key: "persona",
            icon: UserOutlined,
            kind: zh("Persona"),
            label: selectedPersona,
            onRemove: onClearPersona,
          } satisfies ContextTreeItem,
        ]
      : []),
    ...selectedMemoryFiles.map(
      (file): ContextTreeItem => ({
        key: `mem-${file}`,
        icon: BulbOutlined,
        kind: zh("Memory"),
        label: file === "summary" ? zh("Summary") : zh("Profile"),
        onRemove: () => onToggleMemoryFile(file),
      }),
    ),
  ];

  const handleManualSend = useCallback(() => {
    if (isConfigBlocked) {
      // Don't silently fail — surface the config card so the user knows
      // they need to confirm settings first.
      onRequestConfigConfirm();
      return;
    }
    if (!canSend) return;
    const content = inputHandleRef.current?.getValue() || "";
    doSend(content);
  }, [canSend, doSend, isConfigBlocked, onRequestConfigConfirm]);

  // One button, so one handler: mid-turn the same control cancels.
  const handleSendButtonClick = useCallback(() => {
    if (isStreaming) {
      onCancelStreaming();
      return;
    }
    handleManualSend();
  }, [handleManualSend, isStreaming, onCancelStreaming]);

  const sendLabel =
    sendState === "streaming" ? zh("Stop generating") : zh("Send");
  const sendTitle =
    sendState === "blocked"
      ? zh("Confirm settings on the right to send.")
      : sendLabel;

  return (
    <div
      ref={composerRef}
      style={{
        position: "relative",
        zIndex: 20,
        margin: "0 auto",
        width: "100%",
        flexShrink: 0,
        padding: hasMessages ? "4px 24px 20px" : "0 24px 20px",
        maxWidth: hasMessages ? 960 : 768,
        transition: "max-width 650ms cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      {/* 纯 CSS 动画键帧（原 tailwind animate-spin/animate-pulse 等价物）。 */}
      <style>{`@keyframes dt-spin{to{transform:rotate(360deg)}}@keyframes dt-pulse{0%,100%{opacity:1}50%{opacity:.5}}`}</style>
      {hasMessages && (
        <div
          style={{
            pointerEvents: "none",
            position: "absolute",
            left: 0,
            right: 0,
            top: 0,
            height: 24,
            background:
              "linear-gradient(to bottom, transparent, rgba(255,255,255,0.72))",
          }}
        />
      )}

      <div style={{ position: "relative" }}>
        <div
          style={{
            position: "relative",
            borderRadius: 26,
            border: `1px solid ${dragging ? DT.primary : DT.borderAlpha(0.55)}`,
            background: dragging ? DT.primaryAlpha(0.03) : DT.card,
            boxShadow:
              "0 1px 2px rgba(0,0,0,0.025), 0 10px 28px -10px rgba(0,0,0,0.08)",
            transition: "border-color 150ms, background-color 150ms",
          }}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          onDragOver={onDragOver}
          onDrop={onDrop}
          data-drag-counter={dragCounter.current}
        >
          {dragging && (
            <div
              style={{
                pointerEvents: "none",
                position: "absolute",
                inset: 0,
                zIndex: 10,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 26,
                border: `2px dashed ${DT.primaryAlpha(0.5)}`,
                background: DT.primaryAlpha(0.04),
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 4,
                  color: DT.primary,
                }}
              >
                <PaperClipOutlined style={{ fontSize: 22 }} />
                <span style={{ fontSize: 13, fontWeight: 500 }}>
                  {zh("Drop files here")}
                </span>
                <span style={{ fontSize: 11, color: DT.primaryAlpha(0.7) }}>
                  {zh("Images, Office docs, code & text")}
                </span>
              </div>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ATTACHMENT_ACCEPT}
            onChange={handleFileInputChange}
            style={{ display: "none" }}
            aria-hidden="true"
            tabIndex={-1}
          />

          {contextTreeItems.length > 0 && (
            // The reference zone reads as its own layer: a faint muted band
            // with a hairline against the input area, following the card's
            // top radius.
            <div
              style={{
                borderTopLeftRadius: 26,
                borderTopRightRadius: 26,
                borderBottom: `1px solid ${DT.borderAlpha(0.3)}`,
                background: DT.mutedAlpha(0.3),
                padding: "10px 16px 8px",
              }}
            >
              {/* Narrower than the composer on purpose — long titles
                  truncate early so the tree reads as an annotation, not a
                  content row. */}
              <div style={{ maxWidth: "min(560px, 85%)" }}>
                <ContextReferenceTree
                  items={contextTreeItems}
                  direction="up"
                  summaryNoun={"references"}
                />
              </div>
            </div>
          )}
          <ComposerInput
            ref={inputHandleRef}
            textareaRef={textareaRef}
            isVisualizeMode={isVisualizeMode}
            isStreaming={isStreaming}
            canSendEmpty={hasReferences}
            onSend={doSend}
            onInputChange={handleInputChange}
            onPaste={onPaste}
            connectedAgents={connectedAgents}
            selectedAgent={selectedAgent}
            onSelectAgent={onSelectAgent}
            selectedCounts={spaceSelectionCounts}
            knowledgeAvailable={false}
            personaAvailable={!onPersonaSelectionChange}
            onSelectAttach={handlePickFiles}
            agentsAvailable={agentsAvailable}
            onSelectNotebookPicker={onSelectNotebookPicker}
            onSelectBookPicker={onSelectBookPicker}
            onSelectHistoryPicker={onSelectHistoryPicker}
            onSelectAgentsPicker={onSelectAgentsPicker}
            onSelectQuestionBankPicker={onSelectQuestionBankPicker}
            onSelectPersonaPicker={onSelectPersonaPicker}
            onSelectMemoryPicker={onSelectMemoryPicker}
            onOpenPersonaSelector={
              onPersonaSelectionChange && onPersonaSelectorOpenChange
                ? () => onPersonaSelectorOpenChange(true)
                : undefined
            }
            placeholder={inputPlaceholder}
            minHeight={hasMessages ? 28 : 64}
          />

          {!!attachments.length && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, padding: "0 16px 8px" }}>
              {attachments.map((a, i) => {
                const previewLabel = zh("Preview");
                const removeLabel = zh("Remove attachment");
                const attachmentKey = `${a.filename}-${i}`;
                const hovered = hoveredAttachment === attachmentKey;
                if (
                  (a.type === "image" || isSvgFilename(a.filename)) &&
                  a.previewUrl
                ) {
                  return (
                    <div
                      key={attachmentKey}
                      onMouseEnter={() => setHoveredAttachment(attachmentKey)}
                      onMouseLeave={() => setHoveredAttachment(null)}
                      style={{ position: "relative" }}
                      title={a.filename || previewLabel}
                    >
                      <button
                        type="button"
                        onClick={() => onPreviewAttachment?.(i)}
                        aria-label={previewLabel}
                        data-testid="chat-attachment-preview"
                        style={{
                          position: "relative",
                          display: "block",
                          height: 64,
                          width: 64,
                          overflow: "hidden",
                          borderRadius: 8,
                          border: `1px solid ${DT.border}`,
                          background: DT.card,
                          padding: 0,
                          cursor: "pointer",
                          transition: "box-shadow 150ms",
                          boxShadow: hovered
                            ? "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)"
                            : undefined,
                        }}
                      >
                        {/* Native <img> is safe for SVG: scripts inside an
                            SVG don't execute under <img> context. Next.js
                            <Image> rejects SVG by default. */}
                        <img
                          src={a.previewUrl}
                          alt={a.filename || zh("Attachment preview")}
                          style={{
                            height: "100%",
                            width: "100%",
                            objectFit: isSvgFilename(a.filename)
                              ? "contain"
                              : "cover",
                            padding: isSvgFilename(a.filename) ? 4 : 0,
                          }}
                        />
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemoveAttachment(i);
                        }}
                        aria-label={removeLabel}
                        data-testid="chat-attachment-remove"
                        style={{
                          position: "absolute",
                          right: -6,
                          top: -6,
                          display: "flex",
                          height: 16,
                          width: 16,
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 999,
                          border: "none",
                          padding: 0,
                          background: DT.foreground,
                          color: DT.background,
                          opacity: hovered ? 1 : 0,
                          cursor: "pointer",
                          transition: "opacity 150ms",
                          boxShadow:
                            "0 1px 2px 0 rgba(0,0,0,0.05)",
                        }}
                      >
                        <CloseOutlined style={{ fontSize: 10 }} />
                      </button>
                    </div>
                  );
                }
                const spec = docIconFor(a.filename);
                const Icon = spec.Icon;
                const sizeLabel = a.size ? formatBytes(a.size) : "";
                return (
                  <div
                    key={attachmentKey}
                    onMouseEnter={() => setHoveredAttachment(attachmentKey)}
                    onMouseLeave={() => setHoveredAttachment(null)}
                    style={{ position: "relative" }}
                    title={a.filename}
                  >
                    <button
                      type="button"
                      onClick={() => onPreviewAttachment?.(i)}
                      aria-label={previewLabel}
                      data-testid="chat-attachment-preview"
                      style={{
                        display: "flex",
                        height: 64,
                        width: 160,
                        alignItems: "center",
                        gap: 10,
                        borderRadius: 8,
                        border: `1px solid ${hovered ? DT.primaryAlpha(0.4) : DT.border}`,
                        background: hovered ? DT.mutedAlpha(0.3) : DT.card,
                        padding: "0 10px",
                        textAlign: "left",
                        cursor: "pointer",
                        transition: "border-color 150ms, background-color 150ms",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          height: 40,
                          width: 40,
                          flexShrink: 0,
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 6,
                          background: DT.mutedAlpha(0.6),
                        }}
                      >
                        <Icon style={{ fontSize: 22, color: spec.tint }} />
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ ...ellipsis, fontSize: 12, fontWeight: 500, color: DT.foreground }}>
                          {a.filename}
                        </div>
                        <div
                          style={{
                            ...ellipsis,
                            fontSize: 10,
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                            color: DT.mutedForeground,
                          }}
                        >
                          {sizeLabel
                            ? `${spec.label} · ${sizeLabel}`
                            : spec.label}
                        </div>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemoveAttachment(i);
                      }}
                      aria-label={removeLabel}
                      data-testid="chat-attachment-remove"
                      style={{
                        position: "absolute",
                        right: -6,
                        top: -6,
                        display: "flex",
                        height: 16,
                        width: 16,
                        alignItems: "center",
                        justifyContent: "center",
                        borderRadius: 999,
                        border: "none",
                        padding: 0,
                        background: DT.foreground,
                        color: DT.background,
                        opacity: hovered ? 1 : 0,
                        cursor: "pointer",
                        transition: "opacity 150ms",
                        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
                      }}
                    >
                      <CloseOutlined style={{ fontSize: 10 }} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {attachmentError && (
            <div style={{ padding: "0 16px 8px", fontSize: 11, color: DT.red600 }}>
              {attachmentError}
            </div>
          )}

          {/* Claude-style chrome-free toolbar: no divider against the input
              area, no pill borders — quiet text/icon buttons that surface
              on hover. */}
          <div style={{ padding: "2px 12px 8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{ position: "relative" }}>
                <button
                  ref={capBtnRef}
                  onClick={() => onSetCapMenuOpen((v) => !v)}
                  onMouseEnter={(e) => {
                    if (!capMenuOpen) {
                      e.currentTarget.style.background = DT.mutedAlpha(0.55);
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = capMenuOpen
                      ? DT.primaryAlpha(0.1)
                      : "transparent";
                  }}
                  style={{
                    display: "inline-flex",
                    height: 32,
                    flexShrink: 0,
                    alignItems: "center",
                    gap: 6,
                    borderRadius: 8,
                    padding: "0 8px",
                    fontSize: 14,
                    fontWeight: 500,
                    border: "none",
                    cursor: "pointer",
                    background: capMenuOpen
                      ? DT.primaryAlpha(0.1)
                      : "transparent",
                    color: capMenuOpen ? DT.primary : DT.foreground,
                    transition:
                      "background-color 150ms, color 150ms, transform 150ms",
                  }}
                >
                  <span style={{ display: "flex", minWidth: 0, alignItems: "center", gap: 6 }}>
                    <CapIcon style={{ fontSize: 16, flexShrink: 0 }} />
                    {composerCompact ? null : (
                      <span style={ellipsis}>{zh(activeCap.label)}</span>
                    )}
                  </span>
                  <DownOutlined
                    style={{
                      fontSize: 13,
                      flexShrink: 0,
                      marginRight: -2,
                      transition: "transform 200ms",
                      transform: capMenuOpen ? "rotate(180deg)" : undefined,
                    }}
                  />
                </button>

                {capMenuOpen && (
                  <div
                    ref={capMenuRef}
                    style={{
                      position: "absolute",
                      bottom: "100%",
                      left: 0,
                      zIndex: 50,
                      marginBottom: 6,
                      width: 260,
                      overflow: "visible",
                      borderRadius: 12,
                      border: `1px solid ${DT.border}`,
                      background: DT.popover,
                      boxShadow:
                        "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
                      padding: "4px 0",
                    }}
                  >
                    {capabilities
                      .filter((cap) => !cap.loopEngine)
                      .map((cap) => (
                        <CapMenuItem
                          key={cap.value}
                          cap={cap}
                          selected={activeCap.value === cap.value}
                          onSelect={handleSelectCapability}
                        />
                      ))}
                    {(() => {
                      const loopCaps = capabilities.filter(
                        (cap) => cap.loopEngine,
                      );
                      if (loopCaps.length === 0) return null;
                      const loopSelected = loopCaps.some(
                        (cap) => cap.value === activeCap.value,
                      );
                      return (
                        <div
                          style={{ position: "relative" }}
                          onMouseEnter={() => setMoreCapsOpen(true)}
                          onMouseLeave={() => setMoreCapsOpen(false)}
                          onFocus={() => setMoreCapsOpen(true)}
                          onBlur={(event) => {
                            const next = event.relatedTarget;
                            if (
                              !next ||
                              !event.currentTarget.contains(next as Node)
                            ) {
                              setMoreCapsOpen(false);
                            }
                          }}
                        >
                          <button
                            type="button"
                            aria-haspopup="menu"
                            aria-expanded={moreCapsOpen}
                            onClick={() => setMoreCapsOpen((open) => !open)}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background =
                                DT.mutedAlpha(0.45);
                            }}
                            style={{
                              display: "flex",
                              width: "100%",
                              alignItems: "center",
                              gap: 10,
                              padding: "6px 12px",
                              textAlign: "left",
                              border: "none",
                              cursor: "pointer",
                              background:
                                moreCapsOpen ||
                                (loopSelected && !moreCapsOpen)
                                  ? loopSelected && !moreCapsOpen
                                    ? DT.primaryAlpha(0.06)
                                    : DT.mutedAlpha(0.45)
                                  : "transparent",
                              font: "inherit",
                            }}
                          >
                            <StarOutlined
                              style={{
                                fontSize: 15,
                                flexShrink: 0,
                                color: loopSelected
                                  ? DT.primary
                                  : DT.mutedForeground,
                              }}
                            />
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div style={{ ...ellipsis, fontSize: 12.5, fontWeight: 500, lineHeight: 1.375, color: DT.foreground }}>
                                {zh("More Capabilities")}
                              </div>
                              <div style={{ ...ellipsis, fontSize: 11, lineHeight: 1.375, color: DT.mutedForeground }}>
                                {zh("Agent-loop driven modes")}
                              </div>
                            </div>
                            <RightOutlined
                              style={{
                                fontSize: 14,
                                flexShrink: 0,
                                color: DT.mutedForeground,
                              }}
                            />
                          </button>
                          {/* Right flyout. ``pl-1.5`` is a pointer bridge so the
                              cursor can cross the gap without dropping hover;
                              click/focus also open it for touch and keyboard. */}
                          <div
                            style={{
                              position: "absolute",
                              bottom: 0,
                              left: "100%",
                              zIndex: 50,
                              paddingLeft: 6,
                              transition: "opacity 150ms",
                              opacity: moreCapsOpen ? 1 : 0,
                              visibility: moreCapsOpen ? "visible" : "hidden",
                            }}
                          >
                            <div
                              style={{
                                width: 240,
                                overflow: "hidden",
                                borderRadius: 12,
                                border: `1px solid ${DT.border}`,
                                background: DT.popover,
                                boxShadow:
                                  "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
                                padding: "4px 0",
                              }}
                            >
                              {loopCaps.map((cap) => (
                                <CapMenuItem
                                  key={cap.value}
                                  cap={cap}
                                  selected={activeCap.value === cap.value}
                                  onSelect={handleSelectCapability}
                                />
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>

              <div style={{ position: "relative", display: "flex", minWidth: 0, flex: 1, alignItems: "center" }}>
                <button
                  ref={spaceBtnRef}
                  type="button"
                  onClick={() => onSetSpaceMenuOpen((v) => !v)}
                  title={"Add files & context"}
                  aria-label={"Add files & context"}
                  onMouseEnter={(e) => {
                    if (!spaceMenuOpen) {
                      e.currentTarget.style.background = DT.mutedAlpha(0.55);
                      e.currentTarget.style.color = DT.foreground;
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = spaceMenuOpen
                      ? DT.muted
                      : "transparent";
                    if (!spaceMenuOpen) {
                      e.currentTarget.style.color = DT.mutedForeground;
                    }
                  }}
                  style={{
                    position: "relative",
                    display: "flex",
                    height: 32,
                    width: 32,
                    flexShrink: 0,
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: 8,
                    border: "none",
                    cursor: "pointer",
                    background: spaceMenuOpen ? DT.muted : "transparent",
                    color: spaceMenuOpen ? DT.foreground : DT.mutedForeground,
                    transition:
                      "background-color 150ms, color 150ms, transform 150ms",
                  }}
                >
                  <PlusOutlined style={{ fontSize: 20 }} />
                  {contextSelectionCount > 0 && (
                    <span
                      style={{
                        position: "absolute",
                        right: -2,
                        top: -2,
                        display: "flex",
                        height: 13,
                        minWidth: 13,
                        alignItems: "center",
                        justifyContent: "center",
                        borderRadius: 999,
                        background: DT.primary,
                        padding: "0 3px",
                        fontSize: 8,
                        fontWeight: 600,
                        lineHeight: 1,
                        color: DT.primaryForeground,
                        boxShadow: `0 0 0 1.5px ${DT.card}`,
                      }}
                    >
                      {contextSelectionCount}
                    </span>
                  )}
                </button>
                {/* framer-motion 降级（登记替换点见文件头）：原
                    AnimatePresence+motion.div 入场/出场动画在此省略。 */}
                {spaceMenuOpen && (
                  <div
                    ref={spaceMenuRef}
                    style={{
                      position: "absolute",
                      bottom: "100%",
                      left: 0,
                      zIndex: 50,
                      marginBottom: 6,
                      transformOrigin: "bottom left",
                    }}
                  >
                    <ChatSpaceMenu
                      variant="toolbar"
                      selectedCounts={spaceSelectionCounts}
                      knowledgeAvailable={false}
                      personaAvailable={!onPersonaSelectionChange}
                      agentsAvailable={agentsAvailable}
                      onSelectItem={(key) => {
                        onSetSpaceMenuOpen(false);
                        if (key === "attach") handlePickFiles();
                        else if (key === "chat_history")
                          onSelectHistoryPicker();
                        else if (key === "my_agents") onSelectAgentsPicker();
                        else if (key === "books") onSelectBookPicker();
                        else if (key === "notebooks")
                          onSelectNotebookPicker();
                        else if (key === "question_bank")
                          onSelectQuestionBankPicker();
                        else if (key === "persona") onSelectPersonaPicker();
                        else if (key === "memory") onSelectMemoryPicker();
                      }}
                    />
                  </div>
                )}
              </div>

              <div style={{ marginLeft: "auto", display: "flex", flexShrink: 0, alignItems: "center", gap: 6 }}>
                {connectedAgents.length > 0 && onSelectAgent ? (
                  <AgentSelector
                    agents={connectedAgents}
                    selected={selectedAgent}
                    onSelect={onSelectAgent}
                    budget={subagentBudget}
                    onBudgetChange={onSubagentBudgetChange}
                  />
                ) : null}
                {knowledgeBases.length > 0 ? (
                  <KnowledgeSelector
                    knowledgeBases={knowledgeBases}
                    selected={selectedKnowledgeBases}
                    onToggle={onToggleKB}
                  />
                ) : null}
                {onPersonaSelectionChange ? (
                  <PersonaSelector
                    value={personaSelection ?? ""}
                    onChange={onPersonaSelectionChange}
                    open={personaSelectorOpen}
                    onOpenChange={onPersonaSelectorOpenChange}
                  />
                ) : null}
                <ModelSelector
                  options={llmOptions}
                  activeDefault={activeLLMDefault}
                  value={llmSelection}
                  loading={llmOptionsLoading}
                  error={llmOptionsError}
                  onChange={onSelectLLM}
                />
                {contextBudget ? (
                  <ContextBudgetChip budget={contextBudget} />
                ) : null}

                <button
                  type="button"
                  onClick={recorder.toggle}
                  disabled={recorder.state === "transcribing" || isStreaming}
                  style={{
                    position: "relative",
                    display: "inline-flex",
                    height: 32,
                    width: 32,
                    flexShrink: 0,
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: 10,
                    border: "none",
                    cursor: "pointer",
                    background:
                      recorder.state === "recording"
                        ? "rgba(239,68,68,0.15)"
                        : "transparent",
                    color:
                      recorder.state === "recording"
                        ? DT.red500
                        : DT.mutedForeground,
                    opacity:
                      recorder.state === "transcribing" || isStreaming ? 0.4 : 1,
                    transition:
                      "background-color 150ms, color 150ms, transform 150ms",
                  }}
                  aria-label={
                    recorder.state === "recording"
                      ? "Stop recording"
                      : "Record voice"
                  }
                  title={
                    recorder.error ||
                    (recorder.state === "recording"
                      ? "Stop recording"
                      : "Record voice")
                  }
                >
                  {recorder.state === "recording" && (
                    <span
                      style={{
                        pointerEvents: "none",
                        position: "absolute",
                        inset: 0,
                        borderRadius: 10,
                        border: "1px solid rgba(239,68,68,0.4)",
                        animation: "dt-pulse 2s cubic-bezier(0.4,0,0.6,1) infinite",
                      }}
                    />
                  )}
                  {recorder.state === "transcribing" ? (
                    <LoadingOutlined
                      spin
                      style={{ fontSize: 16 }}
                    />
                  ) : (
                    <AudioOutlined style={{ fontSize: 16 }} />
                  )}
                </button>

                {/* The thing you press is the thing that's working is the
                    thing you press to stop — one element for the whole turn,
                    so the button never swaps out from under the cursor at the
                    moment of the click. The glyph crossfades arrow→square in
                    place (both stacked in the same grid cell) and the progress
                    ring moves to the perimeter, where it can spin without
                    fighting the square for the same space. */}
                <button
                  type="button"
                  onClick={handleSendButtonClick}
                  disabled={sendState === "idle"}
                  data-testid="chat-send"
                  style={{
                    position: "relative",
                    marginLeft: 4,
                    display: "inline-grid",
                    height: 32,
                    width: 32,
                    flexShrink: 0,
                    placeItems: "center",
                    borderRadius: 999,
                    border: "none",
                    cursor: SEND_STATE_STYLE[sendState].cursor,
                    background: SEND_STATE_STYLE[sendState].background,
                    color: SEND_STATE_STYLE[sendState].color,
                    boxShadow: SEND_STATE_STYLE[sendState].boxShadow,
                    transition:
                      "background-color 200ms, box-shadow 200ms, transform 200ms",
                  }}
                  aria-label={sendLabel}
                  title={sendTitle}
                >
                  {sendState === "streaming" && (
                    // Outside the fill, so "still working" reads at a glance
                    // and dims on hover to hand the control back as "stop".
                    <span
                      style={{
                        pointerEvents: "none",
                        position: "absolute",
                        inset: -3,
                        borderRadius: 999,
                        border: "2px solid rgba(22,119,255,0.15)",
                        borderTopColor: DT.primary,
                        animation: "dt-spin 0.8s linear infinite",
                        transition: "opacity 150ms",
                      }}
                    />
                  )}
                  <ArrowUpOutlined
                    style={{
                      gridColumn: 1,
                      gridRow: 1,
                      fontSize: 16,
                      transition: "opacity 200ms, transform 200ms",
                      opacity: sendState === "streaming" ? 0 : 1,
                      transform:
                        sendState === "streaming" ? "scale(0.5)" : "scale(1)",
                    }}
                  />
                  <BorderOutlined
                    style={{
                      gridColumn: 1,
                      gridRow: 1,
                      fontSize: 10,
                      transition: "opacity 200ms, transform 200ms",
                      opacity: sendState === "streaming" ? 1 : 0,
                      transform:
                        sendState === "streaming" ? "scale(1)" : "scale(0.5)",
                    }}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});
