// 引擎批2 2.5：TutorHomeChat——DT 桌面对话窗口 1:1 骨架。
// 源=DT app/(workspace)/home/[[...sessionId]]/page.tsx（2347 行）。
// 结构/类名/交互 1:1；状态源=AgentChatContext（桥 SSE——2.4）而非 WS useUnifiedChat
// （实现级偏离，台账 E-20 登记：统一批6 切桥后 h5 与桌面同源）。
// 能力选择器数据源=平台技能表（?expert=tutor 8 项全显；未编排技能点击得桥 error 事件）。
"use client";

import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3, BookMarked, BrainCircuit, Clapperboard, ClipboardCheck, Code2, Compass, Database,
  FileSearch, Flame, Globe, GraduationCap, Image as ImageIcon, Lightbulb, MessageSquare,
  Microscope, PenLine, Sparkles, BookmarkPlus, Download, PanelRight,
  type LucideIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import ChatComposer from "../../../components/chat/home/ChatComposer";
import type { ContextBudget } from "../../../components/chat/home/ContextBudgetChip";
import { ChatMessageList } from "../../../components/chat/home/ChatMessages";
import { TurnNavigator } from "../../../components/chat/home/TurnNavigator";
import SessionLoadingView from "../../../components/chat/home/SessionLoadingView";
import FilePreviewDrawer from "../../../components/chat/preview/FilePreviewDrawer";
import { buildSessionActivity } from "../../../components/chat/home/SessionActivityPanel";
import Tooltip from "../../../components/common/Tooltip";
import SessionViewerPanel, {
  type SessionViewerPanelHandle,
} from "../../../components/chat/home/SessionViewerPanel";
import {
  QuizFollowupProvider,
  useQuizFollowupController,
} from "../../tutor/h5/h5shared/QuizFollowupContext";
import {
  GeogebraTabProvider,
  useGeogebraTabOpener,
} from "../../../context/GeogebraTabContext";
import type {
  MessageAttachment,
  MessageRequestSnapshot,
} from "../../tutor/h5/h5shared/UnifiedChatContext";
import type { FilePreviewSource } from "../../../components/chat/preview/previewerFor";
import type { LLMSelection, StreamEvent } from "../../../lib/unified-ws";
import {
  extractBase64FromDataUrl,
  readFileAsDataUrl,
} from "../../../lib/file-attachments";
import { classifyFile, isSvgFilename } from "../../../lib/doc-attachments";
import { useAttachmentLimits } from "../../../lib/attachment-limits";
import { useChatAutoScroll } from "../../../hooks/useChatAutoScroll";
import { useMeasuredHeight } from "../../../hooks/useMeasuredHeight";
import {
  loadCapabilityPlaygroundConfigs,
  resolveCapabilityPlaygroundConfig,
  type CapabilityPlaygroundConfigMap,
} from "../../../lib/playground-config";
import {
  DEFAULT_QUIZ_CONFIG,
  buildQuizWSConfig,
  type DeepQuestionFormConfig,
} from "../../../lib/quiz-types";
import {
  DEFAULT_VISUALIZE_CONFIG,
  buildVisualizeWSConfig,
  type VisualizeFormConfig,
} from "../../../lib/visualize-types";
import {
  buildResearchWSConfig,
  createEmptyResearchConfig,
  validateResearchConfig,
  type DeepResearchFormConfig,
  type OutlineItem,
} from "../../../lib/research-types";
import { listKnowledgeBases } from "../../../lib/knowledge-api";
import { getSubagentSettings } from "../../../lib/subagents-api";
import { listLLMOptions, type LLMOption } from "../../../lib/llm-options";
import {
  getEnabledOptionalTools,
  invalidateEnabledOptionalToolsCache,
} from "../../../lib/tools-settings";
import { downloadChatMarkdown } from "../../../lib/chat-export";
import { buildChatOutline } from "../../../lib/chat-outline";
import type { SpaceMemoryFile } from "../../../lib/space-items";
import {
  selectedBooksToPayload,
  type SelectedBookReference,
} from "../../../lib/book-references";
import type {
  SelectedRecord,
} from "../../../lib/notebook-selection-types";
import type { SelectedHistorySession } from "../../../components/chat/HistorySessionPicker";
import type { SelectedQuestionEntry } from "../../../components/chat/QuestionBankPicker";
import { listSkills } from "../../../lib/skills-api";
import { useStore } from "../../../store/useStore";
// UX3修复：欢迎区风格收敛数据源（色素/像素对齐问数）——设计 token + sishu 卡
import { tokens, spaceColors } from "../../../theme/tokens";
import { expertsApi } from "../../../services/api";
import type { ExpertCard } from "../../../services/api";
import { AgentChatProvider, useAgentChat, type AgentMessageItem } from "./AgentChatContext";

// next/dynamic → React.lazy（CRA 无 SSR；批2.3 垫片同款）
const NotebookRecordPicker = lazy(() => import("../../../components/notebook/NotebookRecordPicker"));
const HistorySessionPicker = lazy(() => import("../../../components/chat/HistorySessionPicker"));
const MyAgentsPicker = lazy(() => import("../../../components/chat/MyAgentsPicker"));
const QuestionBankPicker = lazy(() => import("../../../components/chat/QuestionBankPicker"));
const MemoryPicker = lazy(() => import("../../../components/chat/MemoryPicker"));
const BookReferencePicker = lazy(() => import("../../../components/chat/BookReferencePicker"));
const SaveToNotebookModal = lazy(() => import("../../../components/notebook/SaveToNotebookModal"));
const CapabilityConfigCard = lazy(() => import("../../../components/chat/home/CapabilityConfigCard"));
const QuizConfigPanel = lazy(() => import("../../../components/quiz/QuizConfigPanel"));
const VisualizeConfigPanel = lazy(() => import("../../../components/visualize/VisualizeConfigPanel"));
const ResearchConfigPanel = lazy(() => import("../../../components/research/ResearchConfigPanel"));

/* ------------------------------------------------------------------ */
/*  Type & data definitions（DT L176-310 1:1）                         */
/* ------------------------------------------------------------------ */

type ToolName =
  | "brainstorm" | "geogebra_analysis" | "web_search" | "code_execution"
  | "reason" | "paper_search" | "imagegen" | "videogen";

interface ToolDef { name: ToolName; label: string; icon: LucideIcon; }

const ALL_TOOLS: ToolDef[] = [
  { name: "brainstorm", label: "Brainstorm", icon: Lightbulb },
  { name: "geogebra_analysis", label: "GeoGebra", icon: Compass },
  { name: "web_search", label: "Web Search", icon: Globe },
  { name: "code_execution", label: "Code", icon: Code2 },
  { name: "reason", label: "Reason", icon: Sparkles },
  { name: "paper_search", label: "Arxiv Search", icon: FileSearch },
  { name: "imagegen", label: "Image Gen", icon: ImageIcon },
  { name: "videogen", label: "Video Gen", icon: Clapperboard },
];

interface CapabilityDef {
  value: string;
  /** 平台技能 code（桥 skill_code）；""=Chat→tutor/chat。 */
  skillCode: string;
  label: string;
  description: string;
  icon: LucideIcon;
  allowedTools: ToolName[];
  defaultTools: ToolName[];
  loopEngine?: boolean;
}

const CAPABILITIES: CapabilityDef[] = [
  {
    value: "", skillCode: "sishu/chat", label: "Chat",
    description: "Flexible conversation with any tool", icon: MessageSquare,
    allowedTools: ["brainstorm", "geogebra_analysis", "web_search", "code_execution", "reason", "paper_search", "imagegen", "videogen"],
    defaultTools: [],
  },
  {
    value: "deep_solve", skillCode: "sishu/solve", label: "Solve",
    description: "Multi-step reasoning & problem solving", icon: BrainCircuit,
    allowedTools: ["web_search", "code_execution", "reason"],
    defaultTools: ["web_search", "code_execution", "reason"],
    loopEngine: true,
  },
  {
    value: "deep_question", skillCode: "sishu/quiz", label: "Quiz",
    description: "Auto-validated question generation", icon: PenLine,
    allowedTools: ["web_search", "code_execution"],
    defaultTools: ["web_search", "code_execution"],
  },
  {
    // UX2批⑤（反馈⑥）：问答式错题录入——专用编排（抽取→确认卡→确认落库）
    value: "wrong_intake", skillCode: "sishu/wrong-intake", label: "错题录入",
    description: "上传错题照片，AI 识别题干并问答式确认录入",
    icon: ClipboardCheck, allowedTools: [], defaultTools: [],
  },
  {
    value: "deep_research", skillCode: "sishu/research", label: "Research",
    description: "Comprehensive multi-agent research", icon: Microscope,
    allowedTools: ["web_search", "paper_search", "code_execution"],
    defaultTools: ["web_search", "paper_search", "code_execution"],
  },
  {
    value: "visualize", skillCode: "sishu/visualize", label: "Visualize",
    description: "Generate charts, diagrams, interactive pages, or math animations",
    icon: BarChart3, allowedTools: [], defaultTools: [],
  },
  {
    value: "mastery_path", skillCode: "sishu/mastery", label: "Mastery Path",
    description: "Mastery-based tutoring with a hard gate", icon: GraduationCap,
    allowedTools: ["web_search", "code_execution"], defaultTools: [],
    loopEngine: true,
  },
  {
    value: "wrong_intake", skillCode: "sishu/wrong-intake", label: "Wrong Intake",
    description: "Record wrong questions through natural dialogue", icon: BookMarked,
    allowedTools: [], defaultTools: [], loopEngine: true,
  },
];

interface KnowledgeBase { name: string; is_default?: boolean; }
interface PendingAttachment {
  type: string; filename: string; base64?: string; previewUrl?: string;
  size?: number; mimeType?: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers（DT L316-346 1:1）                                         */
/* ------------------------------------------------------------------ */

function getCapability(value: string | null): CapabilityDef {
  return CAPABILITIES.find((c) => c.value === (value || "")) ?? CAPABILITIES[0];
}

function readContextBudget(events: StreamEvent[] | undefined): ContextBudget | null {
  if (!events) return null;
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const ev = events[i];
    if (ev.type !== "result") continue;
    const meta = ev.metadata?.metadata as Record<string, unknown> | undefined;
    const budget = meta?.context_budget as ContextBudget | undefined;
    if (budget && typeof budget.window === "number" && typeof budget.used_tokens === "number" && Array.isArray(budget.segments)) {
      return budget;
    }
  }
  return null;
}

/* ------------------------------------------------------------------ */
/*  Chat page                                                          */
/* ------------------------------------------------------------------ */

export default function TutorHomeChat() {
  // Provider 自供（DT 由全局 UnifiedChatProvider 供—— tupu 桥面独立成件，页面即边界）
  return (
    <AgentChatProvider>
      <TutorHomeChatInner />
    </AgentChatProvider>
  );
}

/** 桥 session_id ↔ 平台 store 会话（2.6 会话源：expertId='sishu'；桥 id 映射模块级，刷新后按标题首条回认）。 */
const bridgeToStoreSession = new Map<string, string>();

function usePlatformSessionBridge(agentSessionId: string | null, title: string) {
  const createNewSession = useStore((s) => s.createNewSession);
  const updateSession = useStore((s) => s.updateSession);
  useEffect(() => {
    if (!agentSessionId || bridgeToStoreSession.has(agentSessionId)) return;
    const id = createNewSession("sishu"); // 三轨M6：批1 改名漏网（ExpertId 无 tutor——旧值致会话专家归属错乱）
    updateSession(id, { title: title.trim().slice(0, 80) || "新对话" });
    bridgeToStoreSession.set(agentSessionId, id);
  }, [agentSessionId, title, createNewSession, updateSession]);
}

function TutorHomeChatInner() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const {
    state, send, stop, reset, loadSession: loadAgentSession,
  } = useAgentChatCompat();
  // 2.6：会话落平台 store（最近对话=私塾先生组数据源）
  usePlatformSessionBridge(state.sessionId, state.messages.find((m) => m.role === "user")?.content || "");

  /* ---- 会话/选项 state（DT 同名面；桥 per-request 携带） ---- */
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [llmOptions, setLLMOptions] = useState<LLMOption[]>([]);
  const [activeLLMDefault, setActiveLLMDefault] = useState<LLMSelection | null>(null);
  const [llmOptionsLoading, setLLMOptionsLoading] = useState(true);
  const [llmOptionsError, setLLMOptionsError] = useState(false);
  const [capabilityConfigs, setCapabilityConfigs] = useState<CapabilityPlaygroundConfigMap>({});
  const [userEnabledTools, setUserEnabledTools] = useState<string[] | null>(null);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const attachmentLimits = useAttachmentLimits();
  const [dragging, setDragging] = useState(false);
  const dragCounter = useRef(0);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [previewSource, setPreviewSource] = useState<FilePreviewSource | null>(null);
  const [viewerPanelOpen, setViewerPanelOpen] = useState(false);
  useEffect(() => {
    if (window.localStorage.getItem("dt:chat:viewer-panel") === "1") setViewerPanelOpen(true);
  }, []);
  const setViewerOpen = useCallback((next: boolean) => {
    setViewerPanelOpen(next);
    window.localStorage.setItem("dt:chat:viewer-panel", next ? "1" : "0");
  }, []);
  const toggleViewerPanel = useCallback(() => {
    setViewerPanelOpen((prev) => {
      const next = !prev;
      window.localStorage.setItem("dt:chat:viewer-panel", next ? "1" : "0");
      return next;
    });
  }, []);
  const viewerPanelRef = useRef<SessionViewerPanelHandle | null>(null);
  const ensureActivityPanelOpen = useCallback(() => {
    setViewerOpen(true);
    viewerPanelRef.current?.focusActivityHome();
  }, [setViewerOpen]);
  const attachmentErrorTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [capMenuOpen, setCapMenuOpen] = useState(false);
  const [spaceMenuOpen, setSpaceMenuOpen] = useState(false);
  const capMenuRef = useRef<HTMLDivElement>(null);
  const capBtnRef = useRef<HTMLButtonElement>(null);
  const spaceMenuRef = useRef<HTMLDivElement>(null);
  const spaceBtnRef = useRef<HTMLButtonElement>(null);
  // 三轨M6：useMeasuredHeight 改 callback ref 契约——提供 {current} 兼容桥
  const composerRefCompat = useRef<HTMLDivElement | null>(null);
  const composerHeight = useMeasuredHeight<HTMLDivElement>().height;
  const composerRef = useMemo(
    () =>
      Object.assign((el: HTMLDivElement | null) => {
        composerRefCompat.current = el;
      }, {
        get current() {
          return composerRefCompat.current;
        },
        set current(v: HTMLDivElement | null) {
          composerRefCompat.current = v;
        },
      }),
    [],
  );
  const prefillInputRef = useRef<((text: string) => void) | null>(null);

  // Capabilities / tools / KB / LLM / persona / memory / refs selection state
  const [enabledTools, setEnabledTools] = useState<string[]>([]);
  const [activeCap, setActiveCap] = useState<string | null>(null);
  const [selectedKbOnly, setSelectedKbOnly] = useState<string[]>([]);
  const [llmSelection, setLLMSelection] = useState<LLMSelection | null>(null);
  const [personaSelection, setPersonaSelection] = useState("");
  const [personaSelectorOpen, setPersonaSelectorOpen] = useState(false);
  const [selectedMemoryFiles, setSelectedMemoryFiles] = useState<SpaceMemoryFile[]>([]);
  const [subagentBudget, setSubagentBudget] = useState(1);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [agentOptions, setAgentOptions] = useState<Array<{ name: string; label?: string }>>([]);
  const [selectedBookReferences, setSelectedBookReferences] = useState<SelectedBookReference[]>([]);
  const [selectedNotebookRecords, setSelectedNotebookRecords] = useState<SelectedRecord[]>([]);
  const [selectedHistorySessions, setSelectedHistorySessions] = useState<SelectedHistorySession[]>([]);
  const [selectedAgentSessions, setSelectedAgentSessions] = useState<SelectedHistorySession[]>([]);
  const [selectedQuestionEntries, setSelectedQuestionEntries] = useState<SelectedQuestionEntry[]>([]);
  const [showNotebookPicker, setShowNotebookPicker] = useState(false);
  const [showBookPicker, setShowBookPicker] = useState(false);
  const [showHistoryPicker, setShowHistoryPicker] = useState(false);
  const [showAgentsPicker, setShowAgentsPicker] = useState(false);
  const [showQuestionBankPicker, setShowQuestionBankPicker] = useState(false);
  const [showMemoryPicker, setShowMemoryPicker] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [capabilityConfigConfirmed, setCapabilityConfigConfirmed] = useState(false);

  // Config-panel state（quiz/visualize/research——批4 接编排，面板先 1:1 挂上）
  const [quizConfig, setQuizConfig] = useState<DeepQuestionFormConfig>(DEFAULT_QUIZ_CONFIG);
  const [quizPdf, setQuizPdf] = useState<File | null>(null);
  const [visualizeConfig, setVisualizeConfig] = useState<VisualizeFormConfig>(DEFAULT_VISUALIZE_CONFIG);
  const [researchConfig, setResearchConfig] = useState<DeepResearchFormConfig>(createEmptyResearchConfig());

  const activeCapabilityDef = getCapability(activeCap);
  const isQuizMode = activeCapabilityDef.value === "deep_question";
  const isVisualizeMode = activeCapabilityDef.value === "visualize";
  const isResearchMode = activeCapabilityDef.value === "deep_research";
  const capabilityNeedsConfig = isQuizMode || isVisualizeMode || isResearchMode;
  const researchValidation = useMemo(() => validateResearchConfig(researchConfig), [researchConfig]);

  /* ---- 远端选项加载（skills 表为能力源——计划 2.5 明示） ---- */
  useEffect(() => {
    let alive = true;
    listSkills({ expert: "tutor" })
      .then((skills) => {
        if (!alive) return;
        // 8 项全显（含未编排项——点击得桥 error 事件；计划 L268）
        const codes = new Set(skills.map((s) => s.skill_code ?? s.name));
        void codes;
      })
      .catch(() => undefined);
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    let alive = true;
    listKnowledgeBases().then((kbs) => {
      if (!alive) return;
      const list = (Array.isArray(kbs) ? kbs : (kbs as { data?: KnowledgeBase[] })?.data ?? []) as KnowledgeBase[];
      setKnowledgeBases(list);
    }).catch(() => undefined);
    listLLMOptions().then((resp) => {
      if (!alive) return;
      setLLMOptions(resp.options ?? []);
      setActiveLLMDefault(resp.active ?? null);
      setLLMOptionsLoading(false);
    }).catch(() => { if (alive) { setLLMOptionsError(true); setLLMOptionsLoading(false); } });
    getSubagentSettings().then((s) => {
      if (!alive) return;
      if (s && typeof s === "object" && "budget" in (s as unknown as Record<string, unknown>)) {
        setSubagentBudget(Number((s as unknown as Record<string, unknown>).budget) || 1);
      }
    }).catch(() => undefined);
    getEnabledOptionalTools().then((tools) => {
      if (!alive) return;
      setUserEnabledTools(Array.isArray(tools) ? (tools as string[]) : null);
    }).catch(() => undefined);
    setCapabilityConfigs(loadCapabilityPlaygroundConfigs());
    return () => { alive = false; };
  }, []);

  /* ---- 欢迎语（DT L660-696 1:1） ---- */
  const hasMessages = state.messages.length > 0;
  const [welcomeGreeting, setWelcomeGreeting] = useState<string>("What would you like to learn?");
  useEffect(() => {
    const hour = new Date().getHours();
    let bucket: string[];
    if (hour >= 5 && hour < 12) {
      bucket = ["Good morning.", "Morning — let's learn something.", "What would you like to learn?"];
    } else if (hour >= 12 && hour < 17) {
      bucket = ["Good afternoon.", "Afternoon — what's on your mind?", "What would you like to learn?"];
    } else if (hour >= 17 && hour < 22) {
      bucket = ["Good evening.", "Evening — what shall we explore?", "What would you like to learn?"];
    } else {
      bucket = ["It's late today.", "Burning the midnight oil?", "What would you like to learn?"];
    }
    setWelcomeGreeting(bucket[Math.floor(Math.random() * bucket.length)]);
  }, []);

  /* ---- UX3修复（用户裁定）：?new=1 新建契约——门户卡进入/KeepAlive 复活均强制全新会话：
     桥 reset 清 sessionId/messages（中止在途流）→ 落欢迎页，随后剥参保持 URL 干净。
     修复曾现的「点私塾卡仍显示上轮对话」——组件被 KeepAlive 保活时不会自行重置。 ---- */
  const location = useLocation();
  useEffect(() => {
    const sp = new URLSearchParams(location.search);
    if (sp.get("new") !== "1") return;
    reset();
    sp.delete("new");
    navigate({ pathname: location.pathname, search: sp.toString() ? `?${sp.toString()}` : "" }, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search]);

  /* ---- UX3修复：欢迎区风格收敛数据源（只供视觉，失败静默降级，不碰桥功能面）——
     sishu 卡（suggestions/tagline）+ today-panel 胶囊动态数（同 ExpertChat 批16deep 17.1 平台面）。 ---- */
  const [sishuCard, setSishuCard] = useState<ExpertCard | null>(null);
  const [tutorProfile, setTutorProfile] = useState<{ due_count: number; streak_days: number } | null>(null);
  useEffect(() => {
    let alive = true;
    expertsApi.get("sishu").then((res) => {
      if (alive) setSishuCard(res.data as ExpertCard);
    }).catch(() => undefined);
    fetch("/api/v1/learning/today-panel").then((r) => r.json()).then((j) => {
      if (alive && j && (j.due_count !== undefined || j.streak_days !== undefined)) {
        setTutorProfile({ due_count: j.due_count ?? 0, streak_days: j.streak_days ?? 0 });
      }
    }).catch(() => undefined);
    return () => { alive = false; };
  }, []);
  const sishuSuggestions = (sishuCard?.suggestions && sishuCard.suggestions.length > 0
    ? sishuCard.suggestions
    : sishuCard?.ui_config?.suggestions) ?? ["帮我出三道二次函数练习题", "拍一张错题照片录入错题本", "生成本周的复习计划"];

  const firstUserTitle = useMemo(
    () => state.messages.find((msg) => msg.role === "user")?.content.trim().replace(/\s+/g, " ").slice(0, 80) || "",
    [state.messages],
  );
  const displaySessionTitle = firstUserTitle || t("New chat");
  const canRenameSession = Boolean(state.sessionId);

  /* ---- 保存/导出（DT L860-883/L1885 1:1） ---- */
  const chatSavePayload = useMemo(() => {
    if (!state.messages.length) return null;
    const title = state.messages.find((msg) => msg.role === "user")?.content.trim().slice(0, 80) || "Chat Session";
    return {
      recordType: "chat" as const,
      title,
      userQuery: "",
      output: "",
      metadata: {
        source: "chat",
        capability: activeCap || "chat",
        ui_language: "zh",
        session_id: state.sessionId,
        total_message_count: state.messages.length,
      },
    };
  }, [activeCap, state.messages, state.sessionId]);
  const chatSaveMessages = useMemo(() => state.messages, [state.messages]);

  const handleDownloadMarkdown = useCallback(() => {
    if (!state.messages.length) return;
    downloadChatMarkdown(state.messages, { title: displaySessionTitle });
  }, [state.messages, displaySessionTitle]);

  /* ---- 自动滚动/导航（DT L884-945 1:1） ---- */
  const lastMessage = state.messages[state.messages.length - 1];
  const {
    containerRef: messagesContainerRef,
    endRef: messagesEndRef,
    shouldAutoScrollRef,
    scrollToBottom,
    handleScroll: handleMessagesScroll,
  } = useChatAutoScroll({
    hasMessages,
    isStreaming: state.isStreaming,
    composerHeight,
    messageCount: state.messages.length,
    lastMessageContent: lastMessage?.content,
    lastEventCount: lastMessage?.events?.length,
  });
  const chatOutline = useMemo(
    () => buildChatOutline(state.messages as never, {}),
    [state.messages],
  );
  const jumpToTurn = useCallback((key: string) => {
    const container = messagesContainerRef.current;
    const target = container?.querySelector<HTMLElement>(`[data-turn-key="${key}"]`);
    if (!container || !target) return;
    shouldAutoScrollRef.current = false;
    const offset = target.getBoundingClientRect().top - container.getBoundingClientRect().top;
    container.scrollTo({ top: container.scrollTop + offset - 56, behavior: "smooth" });
    const bubble = target.querySelector<HTMLElement>("[data-turn-bubble]") ?? target;
    bubble.classList.remove("turn-flash");
    void bubble.offsetWidth;
    bubble.classList.add("turn-flash");
    window.setTimeout(() => bubble.classList.remove("turn-flash"), 1300);
  }, [messagesContainerRef, shouldAutoScrollRef]);
  const resumeFollowingLatest = useCallback(() => {
    shouldAutoScrollRef.current = true;
    scrollToBottom("instant");
  }, [scrollToBottom, shouldAutoScrollRef]);

  const copyAssistantMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;
    try { await navigator.clipboard.writeText(content); } catch (error) { console.error("Failed to copy assistant message:", error); }
  }, []);

  /* ---- 引用 payload（DT L797-845 1:1；须在 handleSend 之前定义） ---- */
  const notebookReferenceGroups = useMemo(() => {
    const groups = new Map<string, { notebookName: string; count: number }>();
    selectedNotebookRecords.forEach((record) => {
      const existing = groups.get(record.notebookId);
      if (existing) existing.count += 1;
      else groups.set(record.notebookId, { notebookName: record.notebookName, count: 1 });
    });
    return Array.from(groups.entries()).map(([notebookId, value]) => ({ notebookId, ...value }));
  }, [selectedNotebookRecords]);
  const notebookReferencesPayload = useMemo(() => {
    const grouped = new Map<string, string[]>();
    selectedNotebookRecords.forEach((record) => {
      const current = grouped.get(record.notebookId) || [];
      current.push(record.id);
      grouped.set(record.notebookId, current);
    });
    return Array.from(grouped.entries()).map(([notebook_id, record_ids]) => ({ notebook_id, record_ids }));
  }, [selectedNotebookRecords]);
  const bookReferencesPayload = useMemo(
    () => selectedBooksToPayload(selectedBookReferences),
    [selectedBookReferences],
  );
  const historyReferencesPayload = useMemo(
    () =>
      Array.from(
        new Set([
          ...selectedHistorySessions.map((s) => s.sessionId),
          ...selectedAgentSessions.map((s) => s.sessionId),
        ]),
      ),
    [selectedHistorySessions, selectedAgentSessions],
  );

  /* ---- 能力切换（DT L1210-1240 1:1；skillCode 进桥） ---- */
  const handleSelectCapability = useCallback((value: string) => {
    const cap = CAPABILITIES.find((c) => c.value === value) ?? CAPABILITIES[0];
    const storageKey = cap.value || "chat";
    const config = resolveCapabilityPlaygroundConfig(capabilityConfigs, storageKey, cap.allowedTools);
    setActiveCap(cap.value || null);
    const baseline = userEnabledTools === null ? cap.allowedTools : (userEnabledTools as ToolName[]);
    const enabledToolsForCap = capabilityConfigs[storageKey]
      ? [...config.enabledTools]
      : baseline.filter((tool) => cap.allowedTools.includes(tool as ToolName));
    setEnabledTools(enabledToolsForCap as string[]);
    if (config.knowledgeBase) setSelectedKbOnly([config.knowledgeBase]);
    setCapabilityConfigConfirmed(false);
    setCapMenuOpen(false);
  }, [capabilityConfigs, userEnabledTools]);

  /* ---- 能力选择器数据源=平台技能表 8 项全显（计划 2.5）：
     CAPABILITIES 静态面与技能表对账——桥 skill_code=capability.skillCode。
     未编排技能（如 tutor/wrong-intake 批3 前）点击后桥返回
     「能力编排未就绪」error 事件——L6 TC4 同款。 ---- */

  /* ---- 附件（DT L1242-1556 1:1） ---- */
  const fileToAttachment = useCallback((f: File): Promise<PendingAttachment> =>
    new Promise((resolve, reject) => {
      readFileAsDataUrl(f).then((raw) => {
        const svg = isSvgFilename(f.name) || f.type === "image/svg+xml";
        const isImage = !svg && f.type.startsWith("image/");
        const b64 = extractBase64FromDataUrl(raw);
        resolve({
          type: isImage ? "image" : "file",
          filename: f.name,
          base64: b64,
          previewUrl: isImage || svg ? raw : undefined,
          size: f.size,
          mimeType: f.type || undefined,
        });
      }).catch(reject);
    }), []);

  const showAttachmentError = useCallback((message: string) => {
    setAttachmentError(message);
    if (attachmentErrorTimer.current) clearTimeout(attachmentErrorTimer.current);
    attachmentErrorTimer.current = setTimeout(() => {
      setAttachmentError(null);
      attachmentErrorTimer.current = null;
    }, 4000);
  }, []);

  const filterAndReportFiles = useCallback((files: File[]): File[] => {
    let runningTotal = attachments.reduce((s, a) => s + (a.size ?? 0), 0);
    const accepted: File[] = [];
    const rejected: { name: string; reason: "unsupported" | "too_large" | "quota" }[] = [];
    for (const f of files) {
      const kind = classifyFile(f);
      if (!kind) { rejected.push({ name: f.name, reason: "unsupported" }); continue; }
      if (f.size > attachmentLimits.maxFileBytes) { rejected.push({ name: f.name, reason: "too_large" }); continue; }
      if (runningTotal + f.size > attachmentLimits.maxTotalBytes) { rejected.push({ name: f.name, reason: "quota" }); break; }
      runningTotal += f.size;
      accepted.push(f);
    }
    if (rejected.length) {
      const first = rejected[0];
      let msg: string;
      if (first.reason === "too_large") msg = t("File too large: {{name}}", { name: first.name });
      else if (first.reason === "quota") msg = t("Too many files, skipped some");
      else msg = t("Unsupported file type: {{name}}", { name: first.name });
      showAttachmentError(msg);
    }
    return accepted;
  }, [attachments, attachmentLimits, showAttachmentError, t]);

  const handlePaste = useCallback(async (event: React.ClipboardEvent) => {
    const items = Array.from(event.clipboardData.items);
    const files = items.filter((item) => item.kind === "file").map((item) => item.getAsFile()).filter((f): f is File => f !== null);
    const accepted = filterAndReportFiles(files);
    if (!accepted.length) return;
    const next = await Promise.all(accepted.map(fileToAttachment));
    setAttachments((prev) => [...prev, ...next]);
  }, [filterAndReportFiles, fileToAttachment]);

  const handleAddFiles = useCallback(async (files: File[]) => {
    const accepted = filterAndReportFiles(files);
    if (!accepted.length) return;
    const next = await Promise.all(accepted.map(fileToAttachment));
    setAttachments((prev) => [...prev, ...next]);
  }, [filterAndReportFiles, fileToAttachment]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    dragCounter.current += 1;
    if (e.dataTransfer.types.includes("Files")) setDragging(true);
  }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    dragCounter.current -= 1;
    if (dragCounter.current === 0) setDragging(false);
  }, []);
  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); }, []);
  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    setDragging(false);
    dragCounter.current = 0;
    const files = Array.from(e.dataTransfer.files);
    await handleAddFiles(files);
  }, [handleAddFiles]);

  const removeAttachment = useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }, []);
  const handlePreviewPendingAttachment = useCallback((index: number) => {
    const a: MessageAttachment | undefined = attachments[index];
    if (a?.base64 && a.filename) {
      setPreviewSource({ kind: "file", filename: a.filename, dataUrl: `data:${a.mime_type || "application/octet-stream"};base64,${a.base64}` } as FilePreviewSource);
    }
  }, [attachments]);
  const handlePreviewMessageAttachment = useCallback((a: MessageAttachment) => {
    if (a.url) setPreviewSource({ kind: "file", filename: a.filename || a.url, url: a.url } as FilePreviewSource);
  }, []);
  const handleClosePreview = useCallback(() => setPreviewSource(null), []);

  /* ---- KB/LLM/引用 toggle（DT L1723+ 1:1） ---- */
  const handleToggleKB = useCallback((kb: string) => {
    setSelectedKbOnly((prev) => (prev.includes(kb) ? prev.filter((k) => k !== kb) : [...prev, kb]));
  }, []);

  const handleSelectNotebookPicker = useCallback(() => { setShowNotebookPicker(true); setSpaceMenuOpen(false); }, []);
  const handleCloseNotebookPicker = useCallback(() => setShowNotebookPicker(false), []);
  const handleApplyNotebookRecords = useCallback((records: SelectedRecord[]) => {
    setSelectedNotebookRecords(records); setShowNotebookPicker(false);
  }, []);
  const handleRemoveNotebook = useCallback((notebookId: string) => {
    setSelectedNotebookRecords((prev) => prev.filter((x) => x.notebookId !== notebookId));
  }, []);
  const handleSelectBookPicker = useCallback(() => { setShowBookPicker(true); setSpaceMenuOpen(false); }, []);
  const handleCloseBookPicker = useCallback(() => setShowBookPicker(false), []);
  const handleApplyBookReferences = useCallback((refs: SelectedBookReference[]) => {
    setSelectedBookReferences(refs); setShowBookPicker(false);
  }, []);
  const handleRemoveBookReference = useCallback((bookId: string) => {
    setSelectedBookReferences((prev) => prev.filter((x) => x.bookId !== bookId));
  }, []);
  const handleSelectHistoryPicker = useCallback(() => { setShowHistoryPicker(true); setSpaceMenuOpen(false); }, []);
  const handleCloseHistoryPicker = useCallback(() => setShowHistoryPicker(false), []);
  const handleApplyHistorySessions = useCallback((sessions: SelectedHistorySession[]) => {
    setSelectedHistorySessions(sessions); setShowHistoryPicker(false);
  }, []);
  const handleRemoveHistory = useCallback((sessionId: string) => {
    setSelectedHistorySessions((prev) => prev.filter((x) => x.sessionId !== sessionId));
  }, []);
  const handleSelectAgentsPicker = useCallback(() => { setShowAgentsPicker(true); setSpaceMenuOpen(false); }, []);
  const handleCloseAgentsPicker = useCallback(() => setShowAgentsPicker(false), []);
  const handleApplyAgentSessions = useCallback((sessions: SelectedHistorySession[]) => {
    setSelectedAgentSessions(sessions); setShowAgentsPicker(false);
  }, []);
  const handleRemoveAgent = useCallback((sessionId: string) => {
    setSelectedAgentSessions((prev) => prev.filter((x) => x.sessionId !== sessionId));
  }, []);
  const handleSelectQuestionBankPicker = useCallback(() => { setShowQuestionBankPicker(true); setSpaceMenuOpen(false); }, []);
  const handleCloseQuestionBankPicker = useCallback(() => setShowQuestionBankPicker(false), []);
  const handleApplyQuestionEntries = useCallback((entries: SelectedQuestionEntry[]) => {
    setSelectedQuestionEntries(entries); setShowQuestionBankPicker(false);
  }, []);
  const handleRemoveQuestion = useCallback((entryId: number) => {
    setSelectedQuestionEntries((prev) => prev.filter((x) => x.id !== entryId));
  }, []);
  const handleSelectMemoryPicker = useCallback(() => { setShowMemoryPicker(true); setSpaceMenuOpen(false); }, []);
  const handleCloseMemoryPicker = useCallback(() => setShowMemoryPicker(false), []);
  const handleApplyMemoryFiles = useCallback((files: SpaceMemoryFile[]) => {
    setSelectedMemoryFiles(files); setShowMemoryPicker(false);
  }, []);
  const handleToggleMemoryFile = useCallback((file: SpaceMemoryFile) => {
    setSelectedMemoryFiles((prev) =>
      prev.includes(file)
        ? prev.filter((item) => item !== file)
        : [...prev, file],
    );
  }, []);
  const handleSelectAgent = useCallback((name: string | null) => setSelectedAgent(name), []);
  const handleClearPersona = useCallback(() => setPersonaSelection(""), []);

  const handleCloseSaveModal = useCallback(() => setShowSaveModal(false), []);

  /* ---- 发送（DT L1558-1673 结构 1:1；sendMessage→桥 send） ---- */
  const handleSend = useCallback(async (content: string) => {
    if ((!content && !attachments.length && !selectedBookReferences.length && !selectedNotebookRecords.length && !selectedHistorySessions.length && !selectedQuestionEntries.length && !selectedMemoryFiles.length) || state.isStreaming) return;

    let extraAttachments = attachments.map((a) => ({
      type: a.type, filename: a.filename, base64: a.base64, mime_type: a.mimeType,
    })) as MessageAttachment[];
    let config: Record<string, unknown> | undefined;

    if (isQuizMode) {
      config = buildQuizWSConfig(quizConfig) as Record<string, unknown>;
      if (quizConfig.mode === "mimic" && quizPdf) {
        const b64 = extractBase64FromDataUrl(await readFileAsDataUrl(quizPdf));
        extraAttachments = [...extraAttachments, { type: "pdf", filename: quizPdf.name, base64: b64, mime_type: "application/pdf" }];
      }
    }
    if (isVisualizeMode) config = buildVisualizeWSConfig(visualizeConfig) as Record<string, unknown>;
    if (isResearchMode) {
      if (!researchValidation.valid) return;
      config = buildResearchWSConfig(researchConfig) as Record<string, unknown>;
    }
    if (selectedAgent && subagentBudget) {
      config = { ...(config ?? {}), subagent_consult_budget: subagentBudget };
    }

    const messageContent =
      content ||
      (selectedNotebookRecords.length || selectedBookReferences.length || selectedHistorySessions.length || selectedAgentSessions.length || selectedQuestionEntries.length || selectedMemoryFiles.length
        ? t("Please use the selected context to help with this request.")
        : "") ||
      (attachments.some((a) => a.type === "image") ? t("Please analyze the attached image(s).") : "");

    const capDef = getCapability(activeCap);
    await send(messageContent, {
      skillCode: capDef.skillCode,
      tools: enabledTools,
      knowledgeBases: selectedKbOnly,
      attachments: extraAttachments,
      config,
      // 2.6：桥 session_id ↔ deepagent thread 多轮续接（TC1b 记忆语义）
      sessionId: state.sessionId,
      historyReferences: historyReferencesPayload.map((id) => ({ session_id: id })) as Array<Record<string, unknown>>,
      requestSnapshot: {
        content: messageContent,
        capability: capDef.value || null,
        enabledTools,
        knowledgeBases: selectedKbOnly,
        language: "zh",
        attachments: extraAttachments,
        config,
        bookReferences: bookReferencesPayload,
      },
    });
    shouldAutoScrollRef.current = true;
    setAttachments([]);
    setSelectedBookReferences([]);
    setSelectedNotebookRecords([]);
    setSelectedHistorySessions([]);
    setSelectedAgentSessions([]);
    setSelectedQuestionEntries([]);
    setSelectedMemoryFiles([]);
  }, [attachments, isQuizMode, isVisualizeMode, isResearchMode, quizConfig, quizPdf, visualizeConfig, researchConfig, researchValidation, selectedAgent, subagentBudget, selectedNotebookRecords, selectedBookReferences, selectedHistorySessions, selectedAgentSessions, selectedQuestionEntries, selectedMemoryFiles, send, shouldAutoScrollRef, state.isStreaming, t, activeCap, enabledTools, selectedKbOnly, historyReferencesPayload, bookReferencesPayload, notebookReferencesPayload]);

  /* ---- 再生成/删除轮（桥等价：重发同参——批3 TurnNavigator 深接线） ---- */
  const handleRegenerateMessage = useCallback(() => {
    const lastUser = [...state.messages].reverse().find((m) => m.role === "user");
    if (lastUser) void send(lastUser.content, { skillCode: getCapability(activeCap).skillCode, tools: enabledTools, knowledgeBases: selectedKbOnly });
  }, [state.messages, send, activeCap, enabledTools, selectedKbOnly]);
  const deleteTurn = useCallback((_messageId: number) => { /* 桥会话为服务端 thread——删除轮在批6 store 落地后接线（预登记） */ }, []);
  const editMessage = useCallback((_messageId: number, _newContent: string) => { /* 同上——编辑分支批6 */ }, []);
  const switchBranch = useCallback((_parentMessageId: number | null, _childId: number) => { /* 同上 */ }, []);
  const submitUserReply = useCallback((reply: string | { text?: string; answers?: Array<{ questionId: string; text: string }> }) => {
    const text = typeof reply === "string" ? reply : reply.text || "";
    if (text) void send(text, { skillCode: getCapability(activeCap).skillCode, tools: enabledTools, knowledgeBases: selectedKbOnly });
  }, [send, activeCap, enabledTools, selectedKbOnly]);

  const handleConfirmOutline = useCallback(
    (_outline: OutlineItem[], _topic: string, originalConfig?: Record<string, unknown> | null, requestSnapshot?: MessageRequestSnapshot | null) => {
      // 研究大纲确认→以确认后 config 重发（批4 research 编排接桥后激活）
      const capDef = getCapability("deep_research");
      void send(requestSnapshot?.content || "", {
        skillCode: capDef.skillCode,
        tools: enabledTools,
        knowledgeBases: selectedKbOnly,
        config: (originalConfig ?? undefined) as Record<string, unknown> | undefined,
      });
    },
    [send, enabledTools, selectedKbOnly],
  );

  /* ---- 活动面板聚合（DT L1357 1:1） ---- */
  const sessionActivity = useMemo(
    () => buildSessionActivity(state.messages as never),
    [state.messages],
  );
  /* ---- 配置面板确认（DT L1389-1451 1:1——configSection=CapabilityConfigCard JSX） ---- */
  const handleConfirmCapabilityConfig = useCallback(() => setCapabilityConfigConfirmed(true), []);
  const handleChangeQuizConfig = useCallback((c: DeepQuestionFormConfig) => { setCapabilityConfigConfirmed(false); setQuizConfig(c); }, []);
  const handleUploadQuizPdf = useCallback((f: File | null) => { setCapabilityConfigConfirmed(false); setQuizPdf(f); }, []);
  const handleChangeVisualizeConfig = useCallback((c: VisualizeFormConfig) => { setCapabilityConfigConfirmed(false); setVisualizeConfig(c); }, []);
  const handleChangeResearchConfig = useCallback((c: DeepResearchFormConfig) => { setCapabilityConfigConfirmed(false); setResearchConfig(c); }, []);
  const capabilityConfigSection = useMemo((): ReactNode => {
    if (!capabilityNeedsConfig) return null;
    if (isQuizMode) {
      return (
        <CapabilityConfigCard
          capability="deep_question"
          confirmed={capabilityConfigConfirmed}
          canConfirm
          onConfirm={handleConfirmCapabilityConfig}
        >
          <QuizConfigPanel
            value={quizConfig}
            onChange={handleChangeQuizConfig}
            uploadedPdf={quizPdf}
            onUploadPdf={handleUploadQuizPdf}
          />
        </CapabilityConfigCard>
      );
    }
    if (isVisualizeMode) {
      return (
        <CapabilityConfigCard
          capability="visualize"
          confirmed={capabilityConfigConfirmed}
          canConfirm
          onConfirm={handleConfirmCapabilityConfig}
        >
          <VisualizeConfigPanel
            value={visualizeConfig}
            onChange={handleChangeVisualizeConfig}
          />
        </CapabilityConfigCard>
      );
    }
    // Research: 校验错误前置透出（DT L1423-1440 1:1）
    const researchErrorMessages = Object.values(researchValidation.errors);
    return (
      <CapabilityConfigCard
        capability="deep_research"
        confirmed={capabilityConfigConfirmed}
        canConfirm={researchErrorMessages.length === 0}
        validationErrors={researchErrorMessages}
        onConfirm={handleConfirmCapabilityConfig}
      >
        <ResearchConfigPanel
          value={researchConfig}
          errors={researchValidation.errors}
          onChange={handleChangeResearchConfig}
        />
      </CapabilityConfigCard>
    );
  }, [capabilityNeedsConfig, isQuizMode, isVisualizeMode, capabilityConfigConfirmed,
    handleConfirmCapabilityConfig, quizConfig, quizPdf, handleChangeQuizConfig, handleUploadQuizPdf,
    visualizeConfig, handleChangeVisualizeConfig, researchConfig, researchValidation, handleChangeResearchConfig,
    activeCapabilityDef]);

  /* ---- 能力需配置→自动开活动面板（DT L652-659 1:1） ---- */
  const lastCapabilityNeedsConfigRef = useRef(capabilityNeedsConfig);
  useEffect(() => {
    const prev = lastCapabilityNeedsConfigRef.current;
    lastCapabilityNeedsConfigRef.current = capabilityNeedsConfig;
    if (!prev && capabilityNeedsConfig) ensureActivityPanelOpen();
  }, [capabilityNeedsConfig, ensureActivityPanelOpen]);

  const cancelStreamingTurn = useCallback(() => stop(), [stop]);
  const handleMessagesClick = useCallback(() => { /* DT：点击消息区收浮层（菜单关闭由组件内部处理） */ }, []);
  // UX3修复（用户裁定）：新建会话永远回首页门户——由用户在首页三卡按需选空间
  const navigateToHome = useCallback(() => navigate("/", { replace: true }), [navigate]);

  /* ---- 新会话 ---- */
  const newSession = useCallback(() => { reset(); navigateToHome(); }, [reset, navigateToHome]);

  // 三轨M7(U2) §3.3 E-101 修正：右栏信任设施改真右栏（232px 列+可折叠，同 ExpertChat 形制）——
  // 原实现误落主列文档流底部（全宽横条），并挤压欢迎宫格 flex-1 致第二行被 composer 遮挡。
  const [trustOpen, setTrustOpen] = useState(true);

  const contextBudget = readContextBudget(lastMessage?.events);

  return (
    <QuizFollowupProvider>
      <GeogebraTabProvider>
        <div className="relative flex h-full w-full items-stretch overflow-hidden">
        {/* v3 §2.4 空间色：对话页页头 3px 色条（sishu 琥珀） */}
        <div data-testid="space-color-bar" style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: '#D97706', zIndex: 5 }} />
        <div
          className="chat-preview-shell flex h-full min-w-0 flex-1 flex-col overflow-hidden text-[var(--foreground)]"
          style={{ background: "var(--bg-page, #f7f8fa)" }}  /* UX2批④：背景对齐问数 bgPage */
          data-preview-open={previewSource !== null ? "true" : "false"}
          data-viewer-open={viewerPanelOpen && previewSource === null ? "true" : "false"}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          {/* 头部（DT L1916-1981 1:1） */}
          <div className="mx-auto flex w-full max-w-[960px] flex-wrap items-center justify-between gap-x-3 gap-y-1.5 px-6 pt-3 pb-0">
            <div className="group/title min-w-0 flex flex-1 items-center gap-2">
              <span className="inline-flex min-w-0 max-w-full items-center gap-2 rounded-xl px-2 py-1 text-left font-serif text-[17px] font-semibold tracking-[-0.01em] text-[var(--foreground)]">
                <span className="truncate">{displaySessionTitle}</span>
                <button type="button" onClick={newSession} title={t("New chat")} className="shrink-0 rounded-md px-1 text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]">
                  +
                </button>
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-0.5">
              <HeaderActionButton onClick={() => setShowSaveModal(true)} disabled={!chatSavePayload} icon={BookmarkPlus} label={t("Save to Notebook")} />
              <HeaderActionButton onClick={handleDownloadMarkdown} disabled={!state.messages.length} icon={Download} label={t("Download Markdown")} title={t("Download chat history as Markdown")} />
              <HeaderActionButton onClick={toggleViewerPanel} active={viewerPanelOpen} icon={PanelRight} label={t("Activity")} title={t("Session activity, attachments & previews")} />
            </div>
          </div>

          {/* 消息区（DT L1982-2075 1:1） */}
          <div className="flex w-full flex-1 min-h-0 flex-col">
            {!hasMessages ? (
              <div className="animate-fade-in flex w-full flex-1 flex-col items-center justify-center px-6 pb-8" style={{ minHeight: "fit-content" }}>
                {/* UX3修复：欢迎区对齐问数视觉语言（色素/像素）——渐变大标题+副标语+today-panel 动态数。
                    问候语文案是功能保留（DT L660-696 时段桶），仅呈现样式从衬线收敛为问数渐变题 */}
                <div style={{ textAlign: "center", marginBottom: 20 }}>
                  <div
                    style={{
                      fontSize: tokens.fontSize.display,
                      fontWeight: 700,
                      letterSpacing: "-0.02em",
                      background: tokens.brandGradient,
                      WebkitBackgroundClip: "text",
                      backgroundClip: "text",
                      WebkitTextFillColor: "transparent",
                      color: "transparent",
                      lineHeight: 1.3,
                    }}
                  >
                    {t(welcomeGreeting)}
                  </div>
                  <div style={{ marginTop: 8, fontSize: 14, color: "var(--text-tertiary, #999)" }}>
                    {sishuCard?.ui_config?.welcome?.tagline ?? "出题 · 判分 · 错题本 · 学情规划"}
                  </div>
                  {tutorProfile && (tutorProfile.due_count > 0 || tutorProfile.streak_days > 0) && (
                    <div style={{ marginTop: 6, fontSize: 13, color: tokens.colors.info }}>
                      今日有 {tutorProfile.due_count} 题待复习，已连续学习 {tutorProfile.streak_days} 天
                    </div>
                  )}
                </div>
                {/* 统计胶囊（同问数 S1 卡规格——图标+tabular-nums 数字+12px 说明） */}
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center" }}>
                  {[
                    { label: "待复习", value: tutorProfile ? `${tutorProfile.due_count} 题` : "—", icon: <BookMarked className="h-4 w-4" />, color: spaceColors.sishu },
                    { label: "连续学习", value: tutorProfile ? `${tutorProfile.streak_days} 天` : "—", icon: <Flame className="h-4 w-4" />, color: tokens.colors.ai },
                  ].map((c) => (
                    <div
                      key={c.label}
                      data-testid={`sishu-capsule-${c.label}`}
                      style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "10px 18px", borderRadius: tokens.radius.card,
                        background: "var(--bg-content, #fff)",
                        border: `1px solid ${tokens.colors.border}`,
                        boxShadow: tokens.elevation.s1,
                      }}
                    >
                      <span style={{ color: c.color, fontSize: 16, display: "inline-flex" }}>{c.icon}</span>
                      <div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary, #222)", lineHeight: 1.2, fontVariantNumeric: "tabular-nums" }}>{c.value}</div>
                        <div style={{ fontSize: 12, color: "var(--text-tertiary, #999)" }}>{c.label}</div>
                      </div>
                    </div>
                  ))}
                </div>
                {/* UX2批⑧：7 功能入口已下沉管理台（v4§5.2 私塾管理组）——首屏宫格移除（用户反馈⑧） */}
              </div>
            ) : (
              <div className="relative flex w-full flex-1 min-h-0 flex-col">
                <div
                  ref={messagesContainerRef}
                  data-chat-scroll-root="true"
                  onScroll={handleMessagesScroll}
                  onClick={handleMessagesClick}
                  className={`w-full flex-1 min-h-0 overflow-y-auto [scrollbar-gutter:stable_both-edges] ${hasMessages ? "pt-6" : "pt-2 pb-6"}`}
                  style={
                    hasMessages
                      ? (() => {
                          const maskImage = "linear-gradient(to bottom, transparent 0px, #000 32px, #000 calc(100% - 40px), transparent 100%)";
                          return { paddingBottom: "48px", WebkitMaskImage: maskImage, maskImage };
                        })()
                      : undefined
                  }
                >
                  <div data-chat-column="true" className="mx-auto w-full space-y-9 px-6" style={{ maxWidth: "min(100%, max(720px, 60vw))" }}>
                    <ChatMessageList
                      messages={state.messages as never}
                      isStreaming={state.isStreaming}
                      sessionId={state.sessionId}
                      language="zh"
                      onCopyAssistantMessage={copyAssistantMessage}
                      onRegenerateMessage={handleRegenerateMessage}
                      onConfirmOutline={handleConfirmOutline}
                      onPreviewAttachment={handlePreviewMessageAttachment}
                      onDeleteTurn={deleteTurn}
                      onSubmitUserReply={submitUserReply}
                    />
                    {state.pendingConfirmation && (
                      <div
                        data-testid="wrong-intake-confirmation"
                        className="mt-4 rounded-2xl border border-[var(--border)] bg-[var(--muted)]/60 p-5"
                      >
                        <div className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-[var(--foreground)]">
                          <ClipboardCheck className="h-4 w-4 text-[var(--primary)]" />
                          {t("Wrong question confirmation")}
                        </div>
                        <dl className="space-y-1.5 text-[13px] leading-relaxed text-[var(--foreground)]/85">
                          <div className="flex gap-2"><dt className="shrink-0 text-[var(--muted-foreground)]">{t("Question")}</dt><dd className="min-w-0 break-words">{state.pendingConfirmation.card.question}</dd></div>
                          <div className="flex gap-2"><dt className="shrink-0 text-[var(--muted-foreground)]">{t("Correct answer")}</dt><dd className="min-w-0 break-words text-[var(--primary)]">{state.pendingConfirmation.card.correct_answer}</dd></div>
                          <div className="flex gap-2"><dt className="shrink-0 text-[var(--muted-foreground)]">{t("Your answer")}</dt><dd className="min-w-0 break-words">{state.pendingConfirmation.card.wrong_answer || "—"}</dd></div>
                          {state.pendingConfirmation.card.error_type && (
                            <div className="flex gap-2"><dt className="shrink-0 text-[var(--muted-foreground)]">{t("Error type")}</dt><dd>{state.pendingConfirmation.card.error_type}</dd></div>
                          )}
                        </dl>
                        <div className="mt-3 flex gap-2">
                          <button
                            type="button"
                            data-testid="wrong-intake-confirm-btn"
                            disabled={state.isStreaming}
                            onClick={() => void send("确认", { skillCode: state.pendingConfirmation!.skillCode, tools: enabledTools, knowledgeBases: selectedKbOnly, sessionId: state.sessionId })}
                            className="rounded-xl bg-[var(--primary)] px-4 py-1.5 text-[13px] font-medium text-white hover:opacity-90 disabled:opacity-50"
                          >
                            {t("Confirm and save")}
                          </button>
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} className="h-px w-full shrink-0" />
                  </div>
                </div>
                <TurnNavigator
                  entries={chatOutline as never}
                  scrollRootRef={messagesContainerRef}
                  onJump={jumpToTurn}
                  onJumpToBottom={resumeFollowingLatest}
                />
              </div>
            )}

            <div style={{ borderRadius: 24, boxShadow: '0 12px 32px rgba(15, 23, 42, 0.10)', background: 'var(--bg-content, #fff)', overflow: 'hidden' }}  /* UX2批④：composer 卡片化对齐问数 S3 面板 */>
            <ChatComposer
              composerRef={composerRef}
              capMenuRef={capMenuRef}
              capBtnRef={capBtnRef}
              spaceMenuRef={spaceMenuRef}
              spaceBtnRef={spaceBtnRef}
              dragCounter={dragCounter}
              dragging={dragging}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              capMenuOpen={capMenuOpen}
              spaceMenuOpen={spaceMenuOpen}
              hasMessages={hasMessages}
              attachments={attachments}
              attachmentError={attachmentError}
              activeCap={activeCapabilityDef}
              knowledgeBases={knowledgeBases}
              connectedAgents={agentOptions}
              selectedAgent={selectedAgent}
              onSelectAgent={handleSelectAgent}
              subagentBudget={subagentBudget}
              onSubagentBudgetChange={setSubagentBudget}
              llmOptions={llmOptions}
              activeLLMDefault={activeLLMDefault}
              llmSelection={llmSelection}
              llmOptionsLoading={llmOptionsLoading}
              llmOptionsError={llmOptionsError}
              contextBudget={contextBudget}
              selectedBookReferences={selectedBookReferences}
              selectedNotebookRecords={selectedNotebookRecords}
              selectedHistorySessions={selectedHistorySessions}
              selectedAgentSessions={selectedAgentSessions}
              selectedQuestionEntries={selectedQuestionEntries}
              notebookReferenceGroups={notebookReferenceGroups}
              selectedPersona={null}
              selectedMemoryFiles={selectedMemoryFiles}
              selectedKnowledgeBases={selectedKbOnly}
              isStreaming={state.isStreaming}
              isVisualizeMode={isVisualizeMode}
              capabilityNeedsConfig={capabilityNeedsConfig}
              capabilityConfigConfirmed={capabilityConfigConfirmed}
              onRequestConfigConfirm={ensureActivityPanelOpen}
              capabilities={CAPABILITIES as never}
              onSetCapMenuOpen={setCapMenuOpen}
              onSetSpaceMenuOpen={setSpaceMenuOpen}
              onToggleKB={handleToggleKB}
              onSelectLLM={setLLMSelection}
              onSelectNotebookPicker={handleSelectNotebookPicker}
              onSelectBookPicker={handleSelectBookPicker}
              onSelectHistoryPicker={handleSelectHistoryPicker}
              onSelectAgentsPicker={handleSelectAgentsPicker}
              onSelectQuestionBankPicker={handleSelectQuestionBankPicker}
              onSelectPersonaPicker={() => setPersonaSelectorOpen((v) => !v)}
              onSelectMemoryPicker={handleSelectMemoryPicker}
              onClearPersona={handleClearPersona}
              personaSelection={personaSelection}
              onPersonaSelectionChange={setPersonaSelection}
              personaSelectorOpen={personaSelectorOpen}
              onPersonaSelectorOpenChange={setPersonaSelectorOpen}
              onToggleMemoryFile={handleToggleMemoryFile}
              onSend={handleSend}
              onRemoveAttachment={removeAttachment}
              onPreviewAttachment={handlePreviewPendingAttachment}
              onRemoveHistory={handleRemoveHistory}
              onRemoveAgent={handleRemoveAgent}
              onRemoveBookReference={handleRemoveBookReference}
              onRemoveNotebook={handleRemoveNotebook}
              onRemoveQuestion={handleRemoveQuestion}
              onPaste={handlePaste}
              onAddFiles={handleAddFiles}
              onSelectCapability={handleSelectCapability}
              onCancelStreaming={cancelStreamingTurn}
              prefillInputRef={prefillInputRef}
            />
            </div>
            {/* UX3修复：建议卡（问数同款两列卡规格）——仅欢迎视图渲染；点击经 prefill 预填不直发，
                送信链路仍是桥 send（功能不换）。宽度对齐 ChatComposer 欢迎态 max-w-[768px]。 */}
            {!hasMessages && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10, width: "100%", maxWidth: 768, margin: "0 auto", padding: "0 24px 16px" }}>
                {sishuSuggestions.map((item, i) => (
                  <div
                    key={`suggest-${i}`}
                    role="button"
                    tabIndex={0}
                    data-testid={`sishu-suggest-${i}`}
                    onClick={() => prefillInputRef.current?.(item)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); prefillInputRef.current?.(item); } }}
                    style={{
                      display: "flex", alignItems: "center", gap: 10,
                      padding: "12px 14px", borderRadius: tokens.radius.card,
                      background: "var(--bg-content, #fff)",
                      border: `1px solid ${tokens.colors.border}`,
                      boxShadow: tokens.elevation.s1,
                      cursor: "pointer",
                    }}
                  >
                    <Sparkles className="h-4 w-4 shrink-0" style={{ color: spaceColors.sishu }} />
                    <span style={{ fontSize: 13, color: "var(--text-primary, #222)", lineHeight: 1.6 }}>{item}</span>
                  </div>
                ))}
              </div>
            )}
            <div
              aria-hidden="true"
              className="shrink-0"
              style={{ flexGrow: hasMessages ? 0 : 1.4, transition: "flex-grow 650ms cubic-bezier(0.16, 1, 0.3, 1)" }}
            />
          </div>

          {/* 浮层族（DT L2162-2213 1:1） */}
          <Suspense fallback={null}>
            <NotebookRecordPicker open={showNotebookPicker} onClose={handleCloseNotebookPicker} onApply={handleApplyNotebookRecords} />
            <BookReferencePicker open={showBookPicker} initialReferences={selectedBookReferences} onClose={handleCloseBookPicker} onApply={handleApplyBookReferences} />
            <HistorySessionPicker open={showHistoryPicker} onClose={handleCloseHistoryPicker} onApply={handleApplyHistorySessions} />
            <MyAgentsPicker open={showAgentsPicker} onClose={handleCloseAgentsPicker} onApply={handleApplyAgentSessions} />
            <QuestionBankPicker open={showQuestionBankPicker} onClose={handleCloseQuestionBankPicker} onApply={handleApplyQuestionEntries} />
            <MemoryPicker open={showMemoryPicker} initialFiles={selectedMemoryFiles} onClose={handleCloseMemoryPicker} onApply={handleApplyMemoryFiles} />
            <SaveToNotebookModal open={showSaveModal} payload={chatSavePayload} messages={chatSaveMessages as never} onClose={handleCloseSaveModal} />
          </Suspense>
          <FilePreviewDrawer open={previewSource !== null} source={previewSource} onClose={handleClosePreview} />
          <SessionViewerPanel
            ref={viewerPanelRef}
            open={viewerPanelOpen && previewSource === null}
            sessionId={state.sessionId}
            activity={sessionActivity}
            configSection={capabilityConfigSection as never}
            onClose={() => setViewerOpen(false)}
            onAutoOpen={() => setViewerOpen(true)}
          />
        </div>
        {/* 三轨M7(U2) §3.3 E-101 修正：右栏信任设施——课本章节/教学设置/书库（232px 真右栏+可折叠） */}
        {trustOpen ? (
          <aside
            data-testid="sishu-trust-panel"
            className="flex h-full w-[232px] shrink-0 flex-col overflow-y-auto border-l border-[var(--border)] bg-[var(--card)] px-4 py-4"
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="text-[13px] font-semibold text-[var(--foreground)]">学情上下文</span>
              <button
                type="button"
                data-testid="sishu-trust-collapse"
                onClick={() => setTrustOpen(false)}
                className="rounded-md px-1.5 py-0.5 text-xs text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
              >
                收起
              </button>
            </div>
            <div className="flex flex-col gap-1">
              {[
                { label: "课本章节", path: "/settings/curriculum/chapters" },
                { label: "教学设置", path: "/e/sishu/admin/settings" },
                { label: "书库", path: "/e/sishu/book" },
              ].map((e) => (
                <button
                  key={e.label}
                  data-testid={`sishu-trust-${e.label}`}
                  type="button"
                  onClick={() => navigate(e.path)}
                  className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[13px] text-[var(--foreground)] hover:bg-[var(--muted)]"
                >
                  <BookMarked className="h-3.5 w-3.5 text-amber-600" />
                  {e.label}
                </button>
              ))}
            </div>
          </aside>
        ) : (
          <button
            type="button"
            data-testid="sishu-trust-open"
            onClick={() => setTrustOpen(true)}
            className="absolute right-3 top-3 z-20 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          >
            学情上下文
          </button>
        )}
        </div>
      </GeogebraTabProvider>
    </QuizFollowupProvider>
  );
}

/** useAgentChat 兼容面：state 命名对齐 DT useUnifiedChat（messages/isStreaming/sessionId）。
    批3 确认门：pendingConfirmation 随 state 透传（wrong-intake 抽取卡渲染源）。 */
function useAgentChatCompat() {
  const agent = useAgentChat();
  return {
    state: {
      sessionId: agent.sessionId,
      messages: agent.messages,
      isStreaming: agent.isStreaming,
      pendingConfirmation: agent.pendingConfirmation,
    },
    send: agent.send,
    stop: agent.stop,
    reset: agent.reset,
    loadSession: agent.loadSession,
  };
}

/** DT L2315-2346 HeaderActionButton 1:1。 */
function HeaderActionButton({ onClick, disabled, active, icon: Icon, label, title }: {
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  icon: LucideIcon;
  label: string;
  title?: string;
}) {
  return (
    <Tooltip label={title || label}>
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        title={title || label}
        className={`inline-flex h-8 items-center gap-1.5 rounded-lg px-2 text-xs font-medium transition ${
          active
            ? "bg-[var(--primary)]/10 text-[var(--primary)]"
            : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
        } disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent`}
      >
        <Icon className="h-4 w-4" />
        <span className="hidden xl:inline">{label}</span>
      </button>
    </Tooltip>
  );
}
