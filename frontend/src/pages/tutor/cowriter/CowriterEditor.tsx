/**
 * CowriterEditor——Co-Writer AI 写作「编辑页」1:1 移植。
 * 源仓：web/app/(workspace)/co-writer/[docId]/page.tsx（2495 行，默认导出 CoWriterPage）。
 * tupu 接线：默认导出 props={docId?: string}（源取动态路由 useParams().docId；
 * tupu 经 expertPages 挂载，props 传参优先，回退 useSearchParams 读 ?doc=）。
 *
 * 替换点（登记）：
 * - "use client"/next/dynamic 删除（MarkdownRenderer 直接 import 本目录移植件，
 *   trackSourceLines 在该件内真实生效——滚动同步数据面）；
 * - next/navigation → react-router-dom：useRouter.push → useNavigate；
 *   router.push("/co-writer") → navigate("/e/sishu/co-writer")（tupu AI 写作列表页，
 *   navigation.tsx menuKey e:sishu:co-writer 同路径）；useParams → props/?doc=；
 * - lucide → @ant-design/icons 映射表（size/strokeWidth→style.fontSize；
 *   antd 图标无 strokeWidth 参数，登记省略）：
 *   ArrowRight→ArrowRightOutlined、ArrowUpRight→ExportOutlined（外链语义）、
 *   Bold→BoldOutlined、Braces→CodeTwoTone（antd 无 braces，Code 家族区分 codeblock）、
 *   Check→CheckOutlined、
 *   ChevronDown→DownOutlined、ChevronLeft→LeftOutlined、ChevronRight→RightOutlined、
 *   Code2→CodeOutlined、Download→DownloadOutlined、Eraser→ClearOutlined（就近）、
 *   FileText→FileTextOutlined、Heading1..6→内联 H1..H6 文本组件（antd 无标题图标；
 *   源 math 项本就内联 span，同法）、Highlighter→HighlightOutlined、
 *   Image→PictureOutlined、Italic→ItalicOutlined、Link→LinkOutlined、
 *   List→UnorderedListOutlined、ListOrdered→OrderedListOutlined、
 *   ListTodo→CheckSquareOutlined、Loader2→LoadingOutlined、Minus→MinusOutlined、
 *   NotebookPen→FormOutlined（NotebookPage 批先例）、Quote→BlockOutlined（就近）、
 *   Redo2→RedoOutlined、Strikethrough→StrikethroughOutlined、Table2→TableOutlined、
 *   Undo2→UndoOutlined、WandSparkles→ThunderboltOutlined（AI 动作就近，批8 先例）、
 *   Workflow→PartitionOutlined（流程图语义）；
 * - react-i18next t() → locales/zh/app.json 中文值逐字直用（原渲染即中文）；
 *   "Select a knowledge base..." 未收录键保留英文原文；插值串
 *   "Applied {{action}} to the full draft."→「已对全文草稿执行{action}。」、
 *   "{{count}} tools"→「{count} 个工具」直拼；
 * - apiFetch(apiUrl(x), init) → fetch(x, init)（apiUrl 恒等；credentials:"include"
 *   显式保留；401→/login 跳转为 DeepTutor 鉴权专属不复刻，tupu 先例）；
 * - listKnowledgeBases → 复用 tupu 已移植件 ../admin/knowledge-api（含 client 缓存，
 *   等价原仓 knowledge-api 语义）；getCoWriterDocument/updateCoWriterDocument →
 *   本目录 co-writer-api.ts；notifyCoWriterChanged → 本目录 co-writer-events.ts；
 * - SaveToNotebookModal/NotebookSavePayload → 本目录移植件；
 * - CO_WRITER_SAMPLE_TEMPLATE → 本目录 sampleTemplate.ts（逐字）；
 * - Tailwind → 内联样式逐项对位（CSS 变量带 fallback，NotebookPage 批8 先例）；
 *   hover/focus 用 onMouseEnter/Leave、onFocus/onBlur 直写（本仓先例）；
 *   sm:/md: 响应式变体无法内联，按共享层先例省略（保存状态/字数常显）；
 *   active:scale、disabled:*、group-hover、dark: 变体按共享层先例以等价手段落地
 *   （group-hover tooltip 以 hovered state 直写）；dt-popup-up 为原仓全局动画类，
 *   tupu 无对应全局样式，类名位置以等价内联过渡替代；
 * - 保存/自动保存/防抖语义逐字：AUTOSAVE_DEBOUNCE_MS=1500、undo 防抖 400ms、
 *   localStorage 草稿镜像/清除、title 提交、in-flight 快照校验（markdownRef）全部未改。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ComponentType,
  CSSProperties,
  KeyboardEvent as ReactKeyboardEvent,
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
  ReactNode,
} from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowRightOutlined,
  BoldOutlined,
  CodeTwoTone,
  CheckOutlined,
  ClearOutlined,
  CodeOutlined,
  DownOutlined,
  DownloadOutlined,
  ExportOutlined,
  FileTextOutlined,
  HighlightOutlined,
  ItalicOutlined,
  LeftOutlined,
  LinkOutlined,
  LoadingOutlined,
  MinusOutlined,
  OrderedListOutlined,
  PartitionOutlined,
  PictureOutlined,
  RightOutlined,
  StrikethroughOutlined,
  TableOutlined,
  ThunderboltOutlined,
  UnorderedListOutlined,
  BlockOutlined,
  CheckSquareOutlined,
  FormOutlined,
  RedoOutlined,
  UndoOutlined,
} from "@ant-design/icons";
import { listKnowledgeBases } from "../admin/knowledge-api";
import {
  getCoWriterDocument,
  updateCoWriterDocument,
} from "./co-writer-api";
import { notifyCoWriterChanged } from "./co-writer-events";
import SaveToNotebookModal, {
  type NotebookSavePayload,
} from "../../../components/notebook/SaveToNotebookModal";
import { CO_WRITER_SAMPLE_TEMPLATE } from "./sampleTemplate";
import MarkdownRenderer from "./MarkdownRenderer";

// ── 主题 token（NotebookPage 批8 先例：CSS 变量带 fallback）──
const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const CARD = "var(--card, #ffffff)";
const MUTED = "var(--muted, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";
const PRIMARY_FG = "var(--primary-foreground, #ffffff)";
const POPOVER = "var(--popover, #ffffff)";
const BACKGROUND = "var(--background, #ffffff)";

const MONO_FONT =
  "ui-monospace, SFMono-Regular, Consolas, 'Courier New', monospace";

type EditAction = "rewrite" | "shorten" | "expand";
type SelectionMode = EditAction | "none";
type SourceOption = "none" | "rag" | "web";
type ConfirmAction = "clear" | "template";
// Only retrieval tools the backend actually wires into the selection edit.
//（原仓注释逐字保留）
type ToolName = "rag" | "web";

interface KnowledgeBase {
  name: string;
  is_default?: boolean;
}

const SPLIT_RATIO_KEY = "deeptutor.co_writer.split_ratio";
const SYNC_SCROLL_KEY = "deeptutor.co_writer.sync_scroll";
const LOCAL_DRAFT_PREFIX = "deeptutor.co_writer.draft.";
const AUTOSAVE_DEBOUNCE_MS = 1500;
const MIN_PANEL_RATIO = 0.18;
const MAX_PANEL_RATIO = 0.82;

const ACTION_LABELS: Record<EditAction, string> = {
  rewrite: "重写",
  shorten: "缩短",
  expand: "展开",
};

const TOOL_OPTIONS: Array<{ name: ToolName; label: string }> = [
  { name: "rag", label: "知识库" },
  { name: "web", label: "网络搜索" },
];

const MODE_OPTIONS: Array<{ value: SelectionMode; label: string }> = [
  { value: "none", label: "无" },
  { value: "shorten", label: "缩短" },
  { value: "expand", label: "展开" },
  { value: "rewrite", label: "重写" },
];

interface ToolbarItem {
  id: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  title: string;
  snippet?: string;
  type?: "separator";
  action?: () => void;
}

interface SelectedRange {
  start: number;
  end: number;
  text: string;
  snapshot: string;
}

interface SelectionPopoverState {
  visible: boolean;
  top: number;
  left: number;
}

interface SelectionToolTrace {
  kind?: "tool_call" | "tool_result";
  name: string;
  arguments: Record<string, unknown>;
  result: string;
  success: boolean;
  sources: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
}

interface SelectionTraceData {
  toolTraces: SelectionToolTrace[];
  response: string;
}

interface StreamTraceEvent {
  type: string;
  stage?: string;
  content?: string;
  metadata?: Record<string, unknown>;
}

interface StreamEditResult {
  edited_text?: string;
}

// antd 无标题图标：H1..H6 以内联文本组件呈现（源 math 项同法先例）。
function HeadingGlyph({ level }: { level: number }) {
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 700,
        lineHeight: 1,
        fontFamily: "sans-serif",
        letterSpacing: "-0.02em",
      }}
    >
      {`H${level}`}
    </span>
  );
}

// ToolbarIconBtn 的 hover 直写辅助（本仓先例：onMouseEnter/Leave 直写）。
function toneHover(tone: "default" | "danger" | "warning", on: boolean): CSSProperties {
  if (tone === "danger") {
    return { background: on ? "#e11d481a" : "transparent", color: on ? "#e11d48" : MUTED_FG };
  }
  if (tone === "warning") {
    return { background: on ? "#f59e0b1a" : "transparent", color: on ? "#b45309" : MUTED_FG };
  }
  return { background: on ? `${MUTED}8c` : "transparent", color: on ? FG : MUTED_FG };
}

export default function CowriterEditor({ docId: docIdProp }: { docId?: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  // 源：useParams<{ docId?: string | string[] }> → 数组分支取首元素；
  // tupu 挂载等价物（⑤R F1 先例）：KeepAlive 无 <Routes>，useParams 恒空——
  // 从 pathname 尾段解析（/:docId 参数路由，IA批6 列表跳转承接）；props / ?doc= 兜底。
  const docId = useMemo(() => {
    const tail = location.pathname.split("/").filter(Boolean).pop() || "";
    const raw = tail || docIdProp || searchParams.get("doc") || "";
    return raw;
  }, [location.pathname, docIdProp, searchParams]);
  const draftStorageKey = useMemo(
    () => (docId ? `${LOCAL_DRAFT_PREFIX}${docId}` : null),
    [docId],
  );
  const lastSavedContentRef = useRef<string>("");
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isUnmountedRef = useRef(false);
  const [docTitle, setDocTitle] = useState<string>("");
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState<string>("");
  const titleInputRef = useRef<HTMLInputElement>(null);
  const [docNotFound, setDocNotFound] = useState(false);
  const [isLoadingDoc, setIsLoadingDoc] = useState(true);
  const [isSavingDoc, setIsSavingDoc] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previewScrollRef = useRef<HTMLDivElement>(null);
  const splitContainerRef = useRef<HTMLDivElement>(null);
  const scrollSyncSourceRef = useRef<"editor" | "preview" | null>(null);
  const scrollSyncResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const selectionPopoverRef = useRef<HTMLDivElement>(null);
  const preserveSelectionTraceRef = useRef(false);
  const selectionRequestAbortRef = useRef<AbortController | null>(null);
  const selectionDragStateRef = useRef<{
    offsetX: number;
    offsetY: number;
  } | null>(null);
  const [markdown, setMarkdown] = useState("");
  // Async edits (full-draft edit, auto-mark, selection edit) must verify the
  // draft hasn't changed while the request was in flight before replacing
  // content. State captured in their closures is stale by then; this ref
  // always holds the latest value.（原仓注释逐字保留）
  const markdownRef = useRef("");
  const [instruction, setInstruction] = useState("");
  const [action, setAction] = useState<EditAction>("rewrite");
  const [source, setSource] = useState<SourceOption>("none");
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [kbName, setKbName] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [isAutoMarking, setIsAutoMarking] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [pendingConfirmAction, setPendingConfirmAction] =
    useState<ConfirmAction | null>(null);
  const [notebookSavePayload, setNotebookSavePayload] =
    useState<NotebookSavePayload | null>(null);
  const [selectedRange, setSelectedRange] = useState<SelectedRange | null>(
    null,
  );
  const [selectionPopover, setSelectionPopover] =
    useState<SelectionPopoverState>({
      visible: false,
      top: 0,
      left: 0,
    });
  const [selectionInstruction, setSelectionInstruction] = useState("");
  const [selectionMode, setSelectionMode] = useState<SelectionMode>("rewrite");
  const [selectionTools, setSelectionTools] = useState<ToolName[]>([]);
  const [isToolMenuOpen, setIsToolMenuOpen] = useState(false);
  const [isModeMenuOpen, setIsModeMenuOpen] = useState(false);
  const [selectionTrace, setSelectionTrace] =
    useState<SelectionTraceData | null>(null);
  const [isTraceExpanded, setIsTraceExpanded] = useState(true);
  const [selectionPopoverPinned, setSelectionPopoverPinned] = useState(false);
  const [isDraggingSelectionPopover, setIsDraggingSelectionPopover] =
    useState(false);

  const [editorCollapsed, setEditorCollapsed] = useState(false);
  const [previewCollapsed, setPreviewCollapsed] = useState(false);
  const [editorRatio, setEditorRatio] = useState(0.5);
  const [isResizingSplit, setIsResizingSplit] = useState(false);
  const [syncScrollEnabled, setSyncScrollEnabled] = useState(true);
  const showEditor = !editorCollapsed;
  const showPreview = !previewCollapsed;

  const [undoStack, setUndoStack] = useState<string[]>([]);
  const [redoStack, setRedoStack] = useState<string[]>([]);
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingUndoSnapshotRef = useRef<string | null>(null);
  const [hasLoadedDraft, setHasLoadedDraft] = useState(false);

  useEffect(() => {
    const savedRatio = window.localStorage.getItem(SPLIT_RATIO_KEY);
    if (savedRatio) {
      const parsed = Number.parseFloat(savedRatio);
      if (Number.isFinite(parsed)) {
        setEditorRatio(
          Math.min(MAX_PANEL_RATIO, Math.max(MIN_PANEL_RATIO, parsed)),
        );
      }
    }

    const savedSync = window.localStorage.getItem(SYNC_SCROLL_KEY);
    if (savedSync !== null) {
      setSyncScrollEnabled(savedSync !== "0");
    }
  }, []);

  useEffect(() => {
    isUnmountedRef.current = false;
    return () => {
      isUnmountedRef.current = true;
    };
  }, []);

  useEffect(() => {
    markdownRef.current = markdown;
  }, [markdown]);

  // Load document content from server when docId is available.
  //（原仓注释逐字保留）
  useEffect(() => {
    if (!docId) return;
    let cancelled = false;
    setIsLoadingDoc(true);
    setDocNotFound(false);
    setHasLoadedDraft(false);
    (async () => {
      try {
        const document = await getCoWriterDocument(docId);
        if (cancelled) return;
        // Prefer server content; fall back to local draft buffer if newer (rare:
        // page reloaded before debounced autosave completed).（原仓注释逐字保留）
        let content = document.content ?? "";
        if (draftStorageKey) {
          try {
            const localDraft = window.localStorage.getItem(draftStorageKey);
            if (localDraft !== null && localDraft !== content) {
              content = localDraft;
            }
          } catch {
            /* ignore */
          }
        }
        setMarkdown(content);
        setDocTitle(document.title || "");
        lastSavedContentRef.current = document.content ?? "";
        setLastSavedAt(
          document.updated_at ? document.updated_at * 1000 : Date.now(),
        );
        setHasLoadedDraft(true);
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes("404")) {
          setDocNotFound(true);
        } else {
          setError(msg);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingDoc(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docId, draftStorageKey]);

  // Mirror the in-flight content to localStorage so an accidental reload
  // doesn't lose unsaved characters before autosave fires.（原仓注释逐字保留）
  useEffect(() => {
    if (!hasLoadedDraft || !draftStorageKey) return;
    try {
      window.localStorage.setItem(draftStorageKey, markdown);
    } catch {
      /* ignore quota errors */
    }
  }, [hasLoadedDraft, draftStorageKey, markdown]);

  // Debounced autosave to the server.（原仓注释逐字保留；防抖 1500ms 逐字）
  useEffect(() => {
    if (!hasLoadedDraft || !docId) return;
    if (markdown === lastSavedContentRef.current) return;
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    autosaveTimerRef.current = setTimeout(async () => {
      try {
        setIsSavingDoc(true);
        const updated = await updateCoWriterDocument(docId, {
          content: markdown,
        });
        if (isUnmountedRef.current) return;
        lastSavedContentRef.current = markdown;
        setDocTitle(updated.title || "");
        setLastSavedAt(
          updated.updated_at ? updated.updated_at * 1000 : Date.now(),
        );
        if (draftStorageKey) {
          try {
            window.localStorage.removeItem(draftStorageKey);
          } catch {
            /* ignore */
          }
        }
        notifyCoWriterChanged();
      } catch (err) {
        if (isUnmountedRef.current) return;
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
      } finally {
        if (!isUnmountedRef.current) {
          setIsSavingDoc(false);
        }
      }
    }, AUTOSAVE_DEBOUNCE_MS);
    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    };
  }, [docId, hasLoadedDraft, markdown, draftStorageKey]);

  useEffect(() => {
    window.localStorage.setItem(SPLIT_RATIO_KEY, String(editorRatio));
  }, [editorRatio]);

  useEffect(() => {
    window.localStorage.setItem(SYNC_SCROLL_KEY, syncScrollEnabled ? "1" : "0");
  }, [syncScrollEnabled]);

  useEffect(() => {
    // Drop the cached editor line positions when the viewport changes width;
    // wrapping behavior depends on it.（原仓注释逐字保留）
    const handleResize = () => {
      editorYCacheRef.current = null;
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Editor inner width can change without a window resize (collapsing the
  // preview pane, dragging the splitter, etc). Invalidate the y cache so the
  // mirror remeasures with the new wrap width.（原仓注释逐字保留）
  useEffect(() => {
    editorYCacheRef.current = null;
  }, [editorRatio, editorCollapsed, previewCollapsed]);

  useEffect(() => {
    (async () => {
      try {
        const list = await listKnowledgeBases();
        setKnowledgeBases(list);
        const defaultKb =
          list.find((k: KnowledgeBase) => k.is_default)?.name ||
          list[0]?.name ||
          "";
        setKbName((prev) => prev || defaultKb);
      } catch {
        setKnowledgeBases([]);
      }
    })();
  }, []);

  const pushUndo = useCallback((prev: string) => {
    setUndoStack((s) => [...s.slice(-50), prev]);
    setRedoStack([]);
  }, []);

  const commitPendingTypingUndo = useCallback(() => {
    if (undoTimerRef.current) {
      clearTimeout(undoTimerRef.current);
      undoTimerRef.current = null;
    }
    const snapshot = pendingUndoSnapshotRef.current;
    pendingUndoSnapshotRef.current = null;
    if (snapshot !== null && snapshot !== markdown) {
      pushUndo(snapshot);
    }
  }, [markdown, pushUndo]);

  const handleMarkdownChange = useCallback(
    (value: string) => {
      if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
      if (pendingUndoSnapshotRef.current === null) {
        pendingUndoSnapshotRef.current = markdown;
      }
      const snapshot = pendingUndoSnapshotRef.current;
      undoTimerRef.current = setTimeout(() => {
        pendingUndoSnapshotRef.current = null;
        undoTimerRef.current = null;
        if (snapshot !== null && snapshot !== value) {
          pushUndo(snapshot);
        }
      }, 400);
      setMarkdown(value);
    },
    [markdown, pushUndo],
  );

  const handleUndo = useCallback(() => {
    if (undoTimerRef.current) {
      clearTimeout(undoTimerRef.current);
      undoTimerRef.current = null;
    }
    const pendingSnapshot = pendingUndoSnapshotRef.current;
    pendingUndoSnapshotRef.current = null;
    if (pendingSnapshot !== null && pendingSnapshot !== markdown) {
      setRedoStack((s) => [...s, markdown]);
      setMarkdown(pendingSnapshot);
      return;
    }

    if (undoStack.length === 0) return;
    const prev = undoStack[undoStack.length - 1];
    setRedoStack((s) => [...s, markdown]);
    setUndoStack((s) => s.slice(0, -1));
    setMarkdown(prev);
  }, [undoStack, markdown]);

  const handleRedo = useCallback(() => {
    if (redoStack.length === 0) return;
    const next = redoStack[redoStack.length - 1];
    setUndoStack((s) => [...s, markdown]);
    setRedoStack((s) => s.slice(0, -1));
    setMarkdown(next);
  }, [redoStack, markdown]);

  const handleEditorKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
      const key = event.key.toLowerCase();
      const hasUndoModifier = event.metaKey || event.ctrlKey;
      if (!hasUndoModifier || event.altKey) return;

      if (key === "z" && event.shiftKey) {
        event.preventDefault();
        handleRedo();
        return;
      }

      if (key === "z") {
        event.preventDefault();
        handleUndo();
        return;
      }

      if (key === "y") {
        event.preventDefault();
        handleRedo();
      }
    },
    [handleRedo, handleUndo],
  );

  const startEditingTitle = useCallback(() => {
    if (isLoadingDoc) return;
    setTitleDraft(docTitle);
    setIsEditingTitle(true);
  }, [docTitle, isLoadingDoc]);

  const cancelEditingTitle = useCallback(() => {
    setIsEditingTitle(false);
    setTitleDraft("");
  }, []);

  const commitTitle = useCallback(async () => {
    if (!docId) {
      setIsEditingTitle(false);
      return;
    }
    const next = titleDraft.trim();
    const current = (docTitle || "").trim();
    setIsEditingTitle(false);
    if (next === current) return;
    try {
      setError("");
      setIsSavingDoc(true);
      const updated = await updateCoWriterDocument(docId, { title: next });
      if (isUnmountedRef.current) return;
      setDocTitle(updated.title || "");
      setLastSavedAt(
        updated.updated_at ? updated.updated_at * 1000 : Date.now(),
      );
      notifyCoWriterChanged();
    } catch (err) {
      if (isUnmountedRef.current) return;
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (!isUnmountedRef.current) setIsSavingDoc(false);
    }
  }, [docId, docTitle, titleDraft]);

  useEffect(() => {
    if (!isEditingTitle) return;
    const input = titleInputRef.current;
    if (!input) return;
    input.focus();
    input.select();
  }, [isEditingTitle]);

  const wordCount = useMemo(() => {
    const trimmed = markdown.trim();
    if (!trimmed) return 0;
    // CJK has no word-delimiting spaces: count each CJK char as one word,
    // then whitespace-split whatever remains.（原仓注释逐字保留）
    const cjkPattern = /[一-鿿㐀-䶿぀-ヿ가-힯]/g;
    const cjkCount = trimmed.match(cjkPattern)?.length ?? 0;
    const latinWords = trimmed
      .replace(cjkPattern, " ")
      .split(/\s+/)
      .filter(Boolean).length;
    return cjkCount + latinWords;
  }, [markdown]);

  const charCount = markdown.length;

  const hideSelectionPopover = useCallback(() => {
    selectionRequestAbortRef.current?.abort();
    selectionRequestAbortRef.current = null;
    selectionDragStateRef.current = null;
    setSelectionPopoverPinned(false);
    setIsDraggingSelectionPopover(false);
    setSelectionPopover((prev) => ({ ...prev, visible: false }));
    setSelectedRange(null);
    setSelectionInstruction("");
    setIsToolMenuOpen(false);
    setIsModeMenuOpen(false);
    setSelectionTrace(null);
    setIsTraceExpanded(true);
  }, []);

  const measureSelectionAnchor = useCallback(
    (textarea: HTMLTextAreaElement, index: number) => {
      const rect = textarea.getBoundingClientRect();
      const computed = window.getComputedStyle(textarea);
      const mirror = document.createElement("div");
      const properties = [
        "box-sizing",
        "width",
        "height",
        "overflow-x",
        "overflow-y",
        "border-top-width",
        "border-right-width",
        "border-bottom-width",
        "border-left-width",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "font-style",
        "font-variant",
        "font-weight",
        "font-stretch",
        "font-size",
        "font-size-adjust",
        "line-height",
        "font-family",
        "letter-spacing",
        "text-align",
        "text-transform",
        "text-indent",
        "text-decoration",
        "tab-size",
      ];

      properties.forEach((property) => {
        mirror.style.setProperty(property, computed.getPropertyValue(property));
      });

      mirror.style.position = "fixed";
      mirror.style.top = `${rect.top}px`;
      mirror.style.left = `${rect.left}px`;
      mirror.style.whiteSpace = "pre-wrap";
      mirror.style.overflowWrap = "break-word";
      mirror.style.visibility = "hidden";
      mirror.style.pointerEvents = "none";

      mirror.textContent = textarea.value.slice(0, index);

      const marker = document.createElement("span");
      marker.textContent = textarea.value.slice(index) || ".";
      mirror.appendChild(marker);

      document.body.appendChild(mirror);

      const top = rect.top + marker.offsetTop - textarea.scrollTop;
      const left = rect.left + marker.offsetLeft - textarea.scrollLeft;

      document.body.removeChild(mirror);
      return { top, left };
    },
    [],
  );

  const updateSelectionPopover = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      hideSelectionPopover();
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    if (start === end) {
      hideSelectionPopover();
      return;
    }

    const text = textarea.value.slice(start, end);
    if (!text.trim()) {
      hideSelectionPopover();
      return;
    }

    const anchor = measureSelectionAnchor(textarea, end);
    const width = 360;
    const left = Math.min(
      Math.max(anchor.left - width / 2, 12),
      window.innerWidth - width - 12,
    );
    const top = Math.max(anchor.top - 98, 12);

    setSelectedRange((prev) => {
      const changed =
        !prev ||
        prev.start !== start ||
        prev.end !== end ||
        prev.text !== text ||
        prev.snapshot !== markdown;
      if (changed) {
        setSelectionPopoverPinned(false);
        if (preserveSelectionTraceRef.current) {
          preserveSelectionTraceRef.current = false;
        } else {
          setSelectionTrace(null);
        }
        setIsTraceExpanded(true);
      }
      return { start, end, text, snapshot: markdown };
    });
    setSelectionPopover((prev) => ({
      visible: true,
      top: selectionPopoverPinned ? prev.top : top,
      left: selectionPopoverPinned ? prev.left : left,
    }));
  }, [
    hideSelectionPopover,
    markdown,
    measureSelectionAnchor,
    selectionPopoverPinned,
  ]);

  const insertSnippet = useCallback(
    (snippet: string) => {
      commitPendingTypingUndo();
      pushUndo(markdown);
      const textarea = textareaRef.current;
      if (!textarea) {
        setMarkdown((prev) => `${prev}\n${snippet}`);
        return;
      }
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const next = `${markdown.slice(0, start)}${snippet}${markdown.slice(end)}`;
      setMarkdown(next);
      requestAnimationFrame(() => {
        textarea.focus();
        const cursor = start + snippet.length;
        textarea.setSelectionRange(cursor, cursor);
      });
    },
    [commitPendingTypingUndo, markdown, pushUndo],
  );

  const clearDocument = useCallback(() => {
    if (!markdown) {
      setStatus("草稿已经是空的。");
      setError("");
      return;
    }
    commitPendingTypingUndo();
    pushUndo(markdown);
    setMarkdown("");
    setStatus("草稿已清空。按 Ctrl/Cmd+Z 或使用撤销按钮可恢复。");
    setError("");
  }, [commitPendingTypingUndo, markdown, pushUndo]);

  const loadExampleTemplate = useCallback(() => {
    if (markdown === CO_WRITER_SAMPLE_TEMPLATE) {
      setStatus("示例模板已加载。");
      setError("");
      return;
    }

    commitPendingTypingUndo();
    pushUndo(markdown);
    setMarkdown(CO_WRITER_SAMPLE_TEMPLATE);
    setStatus("已加载示例模板。按 Ctrl/Cmd+Z 或使用撤销按钮可恢复。");
    setError("");
  }, [commitPendingTypingUndo, markdown, pushUndo]);

  const requestClearDocument = useCallback(() => {
    if (!markdown) {
      clearDocument();
      return;
    }
    setPendingConfirmAction("clear");
  }, [clearDocument, markdown]);

  const requestLoadExampleTemplate = useCallback(() => {
    if (markdown === CO_WRITER_SAMPLE_TEMPLATE) {
      loadExampleTemplate();
      return;
    }
    setPendingConfirmAction("template");
  }, [loadExampleTemplate, markdown]);

  const confirmActionCopy = useMemo(() => {
    if (pendingConfirmAction === "clear") {
      return {
        title: "清空这个草稿？",
        description:
          "这会清空编辑器。离开此草稿前，原内容会保留在撤销记录中。",
        confirmLabel: "清空草稿",
        tone: "danger" as const,
        onConfirm: clearDocument,
      };
    }

    if (pendingConfirmAction === "template") {
      return {
        title: "替换为示例模板？",
        description:
          "这会替换当前编辑器内容。离开此草稿前，原内容会保留在撤销记录中。",
        confirmLabel: "加载模板",
        tone: "warning" as const,
        onConfirm: loadExampleTemplate,
      };
    }

    return null;
  }, [clearDocument, loadExampleTemplate, pendingConfirmAction]);

  const handleDownload = () => {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    const safeTitle = (docTitle || "co-writer")
      .trim()
      .replace(/[\\/:*?"<>|]/g, "-")
      .slice(0, 80);
    anchor.download = `${safeTitle || "co-writer"}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleOpenSaveToNotebook = useCallback(() => {
    if (!markdown.trim()) {
      setError("请先写一些内容再保存到笔记本。");
      return;
    }
    const fallbackTitle = "未命名的 Co-Writer 文档";
    const titleForRecord = (docTitle || fallbackTitle).trim() || fallbackTitle;
    setNotebookSavePayload({
      recordType: "co_writer",
      title: titleForRecord,
      userQuery: titleForRecord,
      output: markdown,
      metadata: {
        source: "co_writer",
        doc_id: docId,
      },
      kbName: kbName || null,
    });
  }, [docId, docTitle, kbName, markdown]);

  const replaceSelectedText = useCallback(
    (range: SelectedRange, replacement: string) => {
      pushUndo(range.snapshot);
      const next = `${range.snapshot.slice(0, range.start)}${replacement}${range.snapshot.slice(range.end)}`;
      preserveSelectionTraceRef.current = true;
      setMarkdown(next);
      setSelectedRange({
        start: range.start,
        end: range.start + replacement.length,
        text: replacement,
        snapshot: next,
      });

      requestAnimationFrame(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;
        textarea.focus();
        textarea.setSelectionRange(
          range.start,
          range.start + replacement.length,
        );
        updateSelectionPopover();
      });
    },
    [pushUndo, updateSelectionPopover],
  );

  const toggleSelectionTool = useCallback((tool: ToolName) => {
    setSelectionTools((prev) =>
      prev.includes(tool)
        ? prev.filter((item) => item !== tool)
        : [...prev, tool],
    );
  }, []);

  const handleSelectionPopoverDragStart = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      const target = event.target as HTMLElement;
      if (
        target.closest(
          "input, textarea, button, select, option, a, [data-no-drag='true']",
        )
      ) {
        return;
      }
      event.preventDefault();
      selectionDragStateRef.current = {
        offsetX: event.clientX - selectionPopover.left,
        offsetY: event.clientY - selectionPopover.top,
      };
      setSelectionPopoverPinned(true);
      setIsDraggingSelectionPopover(true);
      setIsToolMenuOpen(false);
      setIsModeMenuOpen(false);
    },
    [selectionPopover.left, selectionPopover.top],
  );

  const updateSelectionTraceFromEvent = useCallback(
    (event: StreamTraceEvent) => {
      setSelectionTrace((prev) => {
        const current = prev ?? { toolTraces: [], response: "" };
        if (event.type === "tool_call") {
          return {
            ...current,
            toolTraces: [
              ...current.toolTraces,
              {
                kind: "tool_call",
                name: String(event.content || ""),
                arguments:
                  event.metadata && typeof event.metadata.args === "object"
                    ? (event.metadata.args as Record<string, unknown>)
                    : {},
                result: "",
                success: true,
                sources: [],
                metadata: event.metadata || {},
              },
            ],
          };
        }
        if (event.type === "tool_result") {
          return {
            ...current,
            toolTraces: [
              ...current.toolTraces,
              {
                kind: "tool_result",
                name: String(event.metadata?.tool || "result"),
                arguments: {},
                result: String(event.content || ""),
                success: true,
                sources: [],
                metadata: event.metadata || {},
              },
            ],
          };
        }
        if (event.type === "content" && event.stage === "responding") {
          return {
            ...current,
            response: `${current.response}${event.content || ""}`,
          };
        }
        return current;
      });
    },
    [],
  );

  const applyReactSelectionEdit = useCallback(async () => {
    if (!selectedRange) {
      setError("请先选择一段文本。");
      return;
    }

    if (selectionMode === "none" && !selectionInstruction.trim()) {
      setError("请输入指令或选择一种模式。");
      return;
    }

    setIsEditing(true);
    setError("");
    setStatus("");
    setSelectionTrace({ toolTraces: [], response: "" });
    setIsTraceExpanded(true);
    selectionRequestAbortRef.current?.abort();
    const controller = new AbortController();
    selectionRequestAbortRef.current = controller;

    try {
      const response = await fetch("/api/v1/co_writer/edit_react/stream", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          selected_text: selectedRange.text,
          instruction: selectionInstruction.trim(),
          mode: selectionMode,
          tools: selectionTools,
          kb_name: selectionTools.includes("rag") ? kbName || null : null,
        }),
      });
      if (!response.ok) {
        throw new Error(
          (await response.text()) || "编辑选中文本失败。",
        );
      }
      if (!response.body) {
        throw new Error("流式响应体缺失。");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalResult: StreamEditResult | undefined;

      const processSseChunk = (chunk: string) => {
        const lines = chunk.split(/\r?\n/);
        let eventName = "message";
        const dataLines: string[] = [];
        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trimStart());
          }
        }
        if (dataLines.length === 0) return;
        const payload = JSON.parse(dataLines.join("\n"));
        if (eventName === "stream") {
          updateSelectionTraceFromEvent(payload as StreamTraceEvent);
          return;
        }
        if (eventName === "result") {
          finalResult = payload as StreamEditResult;
          return;
        }
        if (eventName === "error") {
          throw new Error(
            String(payload?.detail || "编辑选中文本失败。"),
          );
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        while (true) {
          const delimiterIndex = buffer.indexOf("\n\n");
          if (delimiterIndex === -1) break;
          const rawEvent = buffer.slice(0, delimiterIndex);
          buffer = buffer.slice(delimiterIndex + 2);
          processSseChunk(rawEvent);
        }
      }
      buffer += decoder.decode();
      if (buffer.trim()) {
        processSseChunk(buffer.trim());
      }
      if (finalResult === undefined) {
        throw new Error("未接收到最终的编辑结果。");
      }
      const editedText = finalResult.edited_text ?? "";

      if (markdownRef.current !== selectedRange.snapshot) {
        throw new Error(
          "在 AI 编辑完成前草稿已发生变化。请重新选择文本并重试。",
        );
      }

      replaceSelectedText(selectedRange, editedText);
      setStatus("已将 AI 编辑应用到所选内容。");
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      setError(
        err instanceof Error ? err.message : "编辑选中文本失败。",
      );
    } finally {
      selectionRequestAbortRef.current = null;
      setIsEditing(false);
    }
  }, [
    kbName,
    replaceSelectedText,
    selectedRange,
    selectionInstruction,
    selectionMode,
    selectionTools,
    updateSelectionTraceFromEvent,
  ]);

  const applyEdit = async () => {
    if (!instruction.trim()) {
      setError("请先输入编辑指令。");
      return;
    }
    const snapshot = markdown;
    setIsEditing(true);
    setError("");
    setStatus("");
    try {
      const response = await fetch("/api/v1/co_writer/edit", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: snapshot,
          instruction: instruction.trim(),
          action,
          source: source === "none" ? null : source,
          kb_name: source === "rag" ? kbName || null : null,
        }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data?.detail || "编辑文档失败。");
      if (markdownRef.current !== snapshot) {
        throw new Error(
          "AI 编辑运行期间草稿已发生变化，请重试。",
        );
      }
      pushUndo(snapshot);
      setMarkdown(data.edited_text || "");
      setStatus(`已对全文草稿执行${ACTION_LABELS[action]}。`);
      setIsEditModalOpen(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "编辑文档失败。",
      );
    } finally {
      setIsEditing(false);
    }
  };

  const applyAutoMark = async () => {
    if (!markdown.trim()) {
      setError("请先写一些内容再运行自动标注。");
      return;
    }
    const snapshot = markdown;
    setIsAutoMarking(true);
    setError("");
    setStatus("");
    try {
      const response = await fetch("/api/v1/co_writer/automark", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: snapshot }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data?.detail || "自动标注文档失败。");
      if (markdownRef.current !== snapshot) {
        throw new Error(
          "AI 编辑运行期间草稿已发生变化，请重试。",
        );
      }
      pushUndo(snapshot);
      setMarkdown(data.marked_text || "");
      setStatus("已应用自动批注。");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "自动标注文档失败。",
      );
    } finally {
      setIsAutoMarking(false);
    }
  };

  const TOOLBAR: ToolbarItem[] = useMemo(
    () => [
      { id: "undo", icon: UndoOutlined, title: "撤销", action: handleUndo },
      { id: "redo", icon: RedoOutlined, title: "重做", action: handleRedo },
      { id: "sep-1", icon: MinusOutlined, title: "", type: "separator" },
      { id: "h1", icon: () => <HeadingGlyph level={1} />, title: "标题 1", snippet: "\n# " },
      { id: "h2", icon: () => <HeadingGlyph level={2} />, title: "标题 2", snippet: "\n## " },
      { id: "h3", icon: () => <HeadingGlyph level={3} />, title: "标题 3", snippet: "\n### " },
      { id: "h4", icon: () => <HeadingGlyph level={4} />, title: "标题 4", snippet: "\n#### " },
      { id: "h5", icon: () => <HeadingGlyph level={5} />, title: "标题 5", snippet: "\n##### " },
      { id: "h6", icon: () => <HeadingGlyph level={6} />, title: "标题 6", snippet: "\n###### " },
      { id: "sep-2", icon: MinusOutlined, title: "", type: "separator" },
      { id: "bold", icon: BoldOutlined, title: "粗体", snippet: "**bold**" },
      { id: "italic", icon: ItalicOutlined, title: "斜体", snippet: "*italic*" },
      {
        id: "strikethrough",
        icon: StrikethroughOutlined,
        title: "删除线",
        snippet: "~~text~~",
      },
      { id: "code", icon: CodeTwoTone, title: "行内代码", snippet: "`code`" },
      { id: "sep-3", icon: MinusOutlined, title: "", type: "separator" },
      { id: "quote", icon: BlockOutlined, title: "引用", snippet: "\n> " },
      {
        id: "ul",
        icon: UnorderedListOutlined,
        title: "无序列表",
        snippet: "\n- Item\n- Item\n",
      },
      {
        id: "ol",
        icon: OrderedListOutlined,
        title: "有序列表",
        snippet: "\n1. Item\n2. Item\n",
      },
      {
        id: "task",
        icon: CheckSquareOutlined,
        title: "任务列表",
        snippet: "\n- [ ] Task\n- [x] Done\n",
      },
      { id: "sep-4", icon: MinusOutlined, title: "", type: "separator" },
      { id: "hr", icon: MinusOutlined, title: "分割线", snippet: "\n---\n" },
      {
        id: "table",
        icon: TableOutlined,
        title: "表格",
        snippet:
          "\n| Column | Column |\n| ------ | ------ |\n| Cell   | Cell   |\n",
      },
      {
        id: "link",
        icon: LinkOutlined,
        title: "链接",
        snippet: "[text](https://)",
      },
      {
        id: "image",
        icon: PictureOutlined,
        title: "图片",
        snippet: "![alt](https://)",
      },
      { id: "sep-5", icon: MinusOutlined, title: "", type: "separator" },
      {
        id: "codeblock",
        icon: CodeOutlined,
        title: "代码块",
        snippet: '\n```python\nprint("hello")\n```\n',
      },
      {
        id: "mermaid",
        icon: PartitionOutlined,
        title: "Mermaid 图表",
        snippet: "\n```mermaid\nflowchart TD\n  A[Start] --> B[End]\n```\n",
      },
      {
        id: "math",
        icon: () => (
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              lineHeight: 1,
              display: "inline-block",
            }}
          >
            Σ
          </span>
        ),
        title: "数学公式",
        snippet: "\n$$\na^2 + b^2 = c^2\n$$\n",
      },
    ],
    [handleUndo, handleRedo],
  );

  useEffect(() => {
    if (!selectionPopover.visible) return;
    const handleViewportChange = () => updateSelectionPopover();
    window.addEventListener("resize", handleViewportChange);
    return () => window.removeEventListener("resize", handleViewportChange);
  }, [selectionPopover.visible, updateSelectionPopover]);

  useEffect(() => {
    if (!selectionPopover.visible) return;
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (selectionPopoverRef.current?.contains(target)) return;
      if (textareaRef.current?.contains(target)) return;
      hideSelectionPopover();
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [hideSelectionPopover, selectionPopover.visible]);

  useEffect(() => {
    if (!isDraggingSelectionPopover) return;
    const handleMouseMove = (event: MouseEvent) => {
      const dragState = selectionDragStateRef.current;
      const popover = selectionPopoverRef.current;
      if (!dragState || !popover) return;
      const width = popover.offsetWidth || 360;
      const height = popover.offsetHeight || 200;
      const nextLeft = Math.min(
        Math.max(event.clientX - dragState.offsetX, 12),
        window.innerWidth - width - 12,
      );
      const nextTop = Math.min(
        Math.max(event.clientY - dragState.offsetY, 12),
        window.innerHeight - height - 12,
      );
      setSelectionPopover((prev) => ({
        ...prev,
        visible: true,
        top: nextTop,
        left: nextLeft,
      }));
    };
    const handleMouseUp = () => {
      selectionDragStateRef.current = null;
      setIsDraggingSelectionPopover(false);
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDraggingSelectionPopover]);

  useEffect(() => {
    return () => {
      selectionRequestAbortRef.current?.abort();
      if (scrollSyncResetTimerRef.current) {
        clearTimeout(scrollSyncResetTimerRef.current);
      }
    };
  }, []);

  const handleSplitterPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!showEditor || !showPreview) return;
      event.preventDefault();
      setIsResizingSplit(true);
      try {
        (event.target as HTMLDivElement).setPointerCapture(event.pointerId);
      } catch {
        /* ignore */
      }
    },
    [showEditor, showPreview],
  );

  useEffect(() => {
    if (!isResizingSplit) return;
    const handleMove = (event: PointerEvent) => {
      const container = splitContainerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      if (rect.width <= 0) return;
      const ratio = (event.clientX - rect.left) / rect.width;
      setEditorRatio(
        Math.min(MAX_PANEL_RATIO, Math.max(MIN_PANEL_RATIO, ratio)),
      );
    };
    const handleEnd = () => setIsResizingSplit(false);
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleEnd);
    window.addEventListener("pointercancel", handleEnd);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleEnd);
      window.removeEventListener("pointercancel", handleEnd);
    };
  }, [isResizingSplit]);

  const releaseScrollSyncSource = useCallback(() => {
    if (scrollSyncResetTimerRef.current) {
      clearTimeout(scrollSyncResetTimerRef.current);
    }
    scrollSyncResetTimerRef.current = setTimeout(() => {
      scrollSyncSourceRef.current = null;
    }, 90);
  }, []);

  // ── Line-anchored scroll synchronization ──
  //
  // Each block element rendered in the preview carries a `data-source-line`
  // attribute that points back at its starting line in the markdown source
  // (provided by remark's AST position info). For the editor side we cannot
  // assume `scrollTop / lineHeight = source line` because long lines wrap
  // visually. Instead we build a hidden mirror that mimics the textarea's
  // wrapping and read the real pixel y of every source line. With both sides
  // expressed as pixel coordinates we can interpolate either direction with
  // a single piecewise-linear map.（原仓注释逐字保留）

  // Cache: rebuilding the mirror is moderately expensive, so cache by
  // (markdown content, textarea inner width). Both invalidate the cache.
  //（原仓注释逐字保留）
  const editorYCacheRef = useRef<{
    signature: string;
    ys: Map<number, number>;
  } | null>(null);

  const measureEditorLineYs = useCallback((): Map<number, number> => {
    const editor = textareaRef.current;
    if (!editor) return new Map();
    const value = editor.value;
    const sourceLines = value.split("\n");
    if (sourceLines.length === 0) return new Map();

    const computed = window.getComputedStyle(editor);
    const rect = editor.getBoundingClientRect();
    const mirror = document.createElement("div");

    const properties = [
      "box-sizing",
      "width",
      "border-top-width",
      "border-right-width",
      "border-bottom-width",
      "border-left-width",
      "padding-top",
      "padding-right",
      "padding-bottom",
      "padding-left",
      "font-style",
      "font-variant",
      "font-weight",
      "font-stretch",
      "font-size",
      "font-size-adjust",
      "line-height",
      "font-family",
      "letter-spacing",
      "text-align",
      "text-transform",
      "text-indent",
      "tab-size",
    ];
    for (const property of properties) {
      mirror.style.setProperty(property, computed.getPropertyValue(property));
    }

    mirror.style.position = "fixed";
    mirror.style.top = `${rect.top}px`;
    mirror.style.left = `${rect.left}px`;
    mirror.style.height = "auto";
    mirror.style.maxHeight = "none";
    mirror.style.minHeight = "0";
    mirror.style.whiteSpace = "pre-wrap";
    mirror.style.overflowWrap = "break-word";
    mirror.style.wordBreak = "normal";
    mirror.style.visibility = "hidden";
    mirror.style.pointerEvents = "none";
    mirror.style.zIndex = "-1";

    const spans: HTMLSpanElement[] = [];
    for (let i = 0; i < sourceLines.length; i += 1) {
      if (i > 0) mirror.appendChild(document.createTextNode("\n"));
      const span = document.createElement("span");
      // Empty lines need measurable content for offsetTop to be meaningful.
      //（原仓注释逐字保留）
      span.textContent = sourceLines[i].length > 0 ? sourceLines[i] : "\u200B";
      mirror.appendChild(span);
      spans.push(span);
    }

    document.body.appendChild(mirror);

    const result = new Map<number, number>();
    // span.offsetTop is the y-position of the line within the mirror, which
    // mirrors the textarea's scroll content. Setting `editor.scrollTop` to
    // this value lifts that source line to the top of the visible viewport.
    //（原仓注释逐字保留）
    for (let i = 0; i < spans.length; i += 1) {
      result.set(i + 1, spans[i].offsetTop);
    }

    document.body.removeChild(mirror);
    return result;
  }, []);

  const getEditorLineYs = useCallback((): Map<number, number> => {
    const editor = textareaRef.current;
    if (!editor) return new Map();
    const signature = `${editor.clientWidth}|${markdown}`;
    const cached = editorYCacheRef.current;
    if (cached && cached.signature === signature) return cached.ys;
    const ys = measureEditorLineYs();
    editorYCacheRef.current = { signature, ys };
    return ys;
  }, [markdown, measureEditorLineYs]);

  const collectPreviewLineYs = useCallback((): Map<number, number> => {
    const preview = previewScrollRef.current;
    if (!preview) return new Map();
    const nodes = preview.querySelectorAll<HTMLElement>("[data-source-line]");
    if (nodes.length === 0) return new Map();
    const previewRect = preview.getBoundingClientRect();
    const baseTop = previewRect.top - preview.scrollTop;
    const result = new Map<number, number>();
    for (const el of Array.from(nodes)) {
      const raw = el.getAttribute("data-source-line");
      const line = raw ? Number.parseInt(raw, 10) : NaN;
      if (!Number.isFinite(line)) continue;
      // Keep the first occurrence; nested wrappers often repeat the same line.
      //（原仓注释逐字保留）
      if (result.has(line)) continue;
      const rect = el.getBoundingClientRect();
      result.set(line, rect.top - baseTop);
    }
    return result;
  }, []);

  const buildJointMarkers = useCallback((): Array<{
    line: number;
    editorY: number;
    previewY: number;
  }> => {
    const editorYs = getEditorLineYs();
    const previewYs = collectPreviewLineYs();
    if (editorYs.size === 0 || previewYs.size === 0) return [];

    const lines = Array.from(previewYs.keys())
      .filter((line) => editorYs.has(line))
      .sort((a, b) => a - b);

    const editor = textareaRef.current;
    const preview = previewScrollRef.current;
    const markers: Array<{ line: number; editorY: number; previewY: number }> =
      [];
    for (const line of lines) {
      const editorY = editorYs.get(line);
      const previewY = previewYs.get(line);
      if (typeof editorY !== "number" || typeof previewY !== "number") continue;
      markers.push({ line, editorY, previewY });
    }

    // Anchor the very top so we don't snap to the first heading when the user
    // is still above it.（原仓注释逐字保留）
    if (
      markers.length === 0 ||
      markers[0].editorY > 0 ||
      markers[0].previewY > 0
    ) {
      markers.unshift({ line: 0, editorY: 0, previewY: 0 });
    }

    // Anchor the bottom so the bottom of the document matches.
    //（原仓注释逐字保留）
    if (editor && preview) {
      const editorMax = Math.max(0, editor.scrollHeight - editor.clientHeight);
      const previewMax = Math.max(
        0,
        preview.scrollHeight - preview.clientHeight,
      );
      const last = markers[markers.length - 1];
      if (editorMax > last.editorY + 1 || previewMax > last.previewY + 1) {
        markers.push({
          line: last.line + 1,
          editorY: editorMax,
          previewY: previewMax,
        });
      }
    }

    return markers;
  }, [collectPreviewLineYs, getEditorLineYs]);

  const interpolate = (
    value: number,
    fromA: number,
    fromB: number,
    toA: number,
    toB: number,
  ): number => {
    if (fromA === fromB) return toA;
    const ratio = (value - fromA) / (fromB - fromA);
    return toA + (toB - toA) * ratio;
  };

  const handleEditorScrollSync = useCallback(() => {
    updateSelectionPopover();
    if (!syncScrollEnabled) return;
    if (scrollSyncSourceRef.current === "preview") return;
    const editor = textareaRef.current;
    const preview = previewScrollRef.current;
    if (!editor || !preview) return;
    const markers = buildJointMarkers();
    if (markers.length === 0) return;

    const editorScroll = editor.scrollTop;
    let lower = markers[0];
    let upper = markers[markers.length - 1];
    for (const marker of markers) {
      if (marker.editorY <= editorScroll) lower = marker;
      if (marker.editorY >= editorScroll) {
        upper = marker;
        break;
      }
    }

    const target = interpolate(
      editorScroll,
      lower.editorY,
      upper.editorY,
      lower.previewY,
      upper.previewY,
    );

    const max = preview.scrollHeight - preview.clientHeight;
    const next = Math.max(0, Math.min(max, target));
    if (Math.abs(next - preview.scrollTop) < 0.5) return;
    scrollSyncSourceRef.current = "editor";
    preview.scrollTop = next;
    releaseScrollSyncSource();
  }, [
    buildJointMarkers,
    releaseScrollSyncSource,
    syncScrollEnabled,
    updateSelectionPopover,
  ]);

  const handlePreviewScrollSync = useCallback(() => {
    if (!syncScrollEnabled) return;
    if (scrollSyncSourceRef.current === "editor") return;
    const editor = textareaRef.current;
    const preview = previewScrollRef.current;
    if (!editor || !preview) return;
    const markers = buildJointMarkers();
    if (markers.length === 0) return;

    const previewScroll = preview.scrollTop;
    let lower = markers[0];
    let upper = markers[markers.length - 1];
    for (const marker of markers) {
      if (marker.previewY <= previewScroll) lower = marker;
      if (marker.previewY >= previewScroll) {
        upper = marker;
        break;
      }
    }

    const target = interpolate(
      previewScroll,
      lower.previewY,
      upper.previewY,
      lower.editorY,
      upper.editorY,
    );

    const max = editor.scrollHeight - editor.clientHeight;
    const next = Math.max(0, Math.min(max, target));
    if (Math.abs(next - editor.scrollTop) < 0.5) return;
    scrollSyncSourceRef.current = "preview";
    editor.scrollTop = next;
    releaseScrollSyncSource();
  }, [buildJointMarkers, releaseScrollSyncSource, syncScrollEnabled]);

  // Mermaid diagrams, images, and KaTeX render asynchronously, so the preview's
  // scrollHeight (and the y position of every marker after them) shifts well
  // after the initial render. Without intervention, the user's last alignment
  // becomes stale and the next scroll feels "jumpy" because all the markers
  // moved underneath them. Whenever the preview's intrinsic height changes we
  // re-run the editor→preview sync to put the preview back in lock-step with
  // the editor's current scroll position.（原仓注释逐字保留）
  const handleEditorScrollSyncRef = useRef(handleEditorScrollSync);
  useEffect(() => {
    handleEditorScrollSyncRef.current = handleEditorScrollSync;
  }, [handleEditorScrollSync]);

  useEffect(() => {
    const preview = previewScrollRef.current;
    if (!preview) return;
    const inner = preview.firstElementChild as HTMLElement | null;
    if (!inner) return;

    let raf = 0;
    const schedule = () => {
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        raf = 0;
        // Treat this as an editor-driven update; we want preview to follow
        // wherever the editor cursor currently anchors us, not the other way
        // around (which would feed back into editor scroll).
        //（原仓注释逐字保留）
        if (scrollSyncSourceRef.current) return;
        handleEditorScrollSyncRef.current();
      });
    };

    const observer = new ResizeObserver(schedule);
    observer.observe(inner);

    // Images load asynchronously and don't always trigger a ResizeObserver
    // update on the parent, so we listen to load events directly too.
    //（原仓注释逐字保留）
    const onLoad = (event: Event) => {
      const target = event.target as HTMLElement | null;
      if (!target) return;
      if (target.tagName === "IMG" || target.tagName === "IFRAME") schedule();
    };
    inner.addEventListener("load", onLoad, true);

    return () => {
      if (raf) cancelAnimationFrame(raf);
      observer.disconnect();
      inner.removeEventListener("load", onLoad, true);
    };
  }, [showPreview]);

  if (docNotFound) {
    return (
      <div
        style={{
          display: "flex",
          height: "100%",
          minHeight: "100%",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
          background: BACKGROUND,
          padding: 40,
          textAlign: "center",
        }}
      >
        <p style={{ margin: 0, fontSize: 18, fontWeight: 500, color: FG }}>
          {"未找到文档"}
        </p>
        <p style={{ margin: 0, fontSize: 14, color: MUTED_FG }}>
          {"此文档可能已被删除，或链接不正确。"}
        </p>
        <button
          type="button"
          onClick={() => navigate("/e/sishu/co-writer")}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            borderRadius: 8,
            background: PRIMARY,
            color: PRIMARY_FG,
            padding: "8px 14px",
            fontSize: 12.5,
            fontWeight: 500,
            border: "none",
            cursor: "pointer",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = "0.9";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = "1";
          }}
        >
          <LeftOutlined style={{ fontSize: 14 }} />
          {"返回 Co-Writer"}
        </button>
      </div>
    );
  }

  if (isLoadingDoc && !hasLoadedDraft) {
    return (
      <div
        style={{
          display: "flex",
          height: "100%",
          minHeight: "100%",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          background: BACKGROUND,
          padding: 40,
          textAlign: "center",
          color: MUTED_FG,
        }}
      >
        <LoadingOutlined style={{ fontSize: 20 }} spin />
        <span style={{ fontSize: 14 }}>{"正在加载文档…"}</span>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        minHeight: "100%",
        flexDirection: "column",
        overflow: "hidden",
        background: BACKGROUND,
      }}
    >
      {/* ── Top bar ── */}
      <header
        style={{
          display: "flex",
          flexShrink: 0,
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: `1px solid ${BORDER}`,
          padding: "6px 16px",
        }}
      >
        <div
          style={{
            display: "flex",
            minWidth: 0,
            alignItems: "center",
            gap: 12,
            fontSize: 14,
            color: MUTED_FG,
          }}
        >
          <button
            type="button"
            onClick={() => navigate("/e/sishu/co-writer")}
            title={"返回文档列表"}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = MUTED;
              e.currentTarget.style.color = FG;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.color = MUTED_FG;
            }}
            style={{
              display: "inline-flex",
              flexShrink: 0,
              alignItems: "center",
              gap: 4,
              borderRadius: 6,
              padding: "2px 6px",
              fontSize: 12,
              fontWeight: 500,
              color: MUTED_FG,
              background: "transparent",
              border: "none",
              cursor: "pointer",
              transition: "background-color 150ms, color 150ms",
            }}
          >
            <LeftOutlined style={{ fontSize: 11 }} />
            <span>{"智能写作"}</span>
          </button>
          <span style={{ color: `${MUTED_FG}66` }}>/</span>
          {isEditingTitle ? (
            <input
              ref={titleInputRef}
              value={titleDraft}
              onChange={(event) => setTitleDraft(event.target.value)}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = PRIMARY;
                e.currentTarget.style.boxShadow = `0 0 0 1px ${PRIMARY}4d`;
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = `${PRIMARY}66`;
                e.currentTarget.style.boxShadow = "none";
                void commitTitle();
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void commitTitle();
                } else if (event.key === "Escape") {
                  event.preventDefault();
                  cancelEditingTitle();
                }
              }}
              maxLength={120}
              spellCheck={false}
              placeholder={"未命名草稿"}
              aria-label={"文档标题"}
              style={{
                minWidth: 0,
                flex: 1,
                maxWidth: 384,
                borderRadius: 6,
                border: `1px solid ${PRIMARY}66`,
                background: BACKGROUND,
                padding: "2px 8px",
                fontWeight: 500,
                color: FG,
                outline: "none",
              }}
            />
          ) : (
            <span
              role="button"
              tabIndex={0}
              onDoubleClick={startEditingTitle}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === "F2") {
                  event.preventDefault();
                  startEditingTitle();
                }
              }}
              title={"双击重命名"}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = `${MUTED}99`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
              }}
              style={{
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                cursor: "text",
                borderRadius: 6,
                padding: "2px 8px",
                fontWeight: 500,
                color: FG,
                transition: "background-color 150ms",
              }}
            >
              {docTitle || "未命名草稿"}
            </span>
          )}
          <span style={{ fontSize: 12 }}>
            {`${wordCount} 词 · ${charCount} 字符`}
          </span>
          {isSavingDoc ? (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                fontSize: 10,
                color: `${MUTED_FG}b3`,
              }}
            >
              <LoadingOutlined style={{ fontSize: 10 }} spin />
              {"正在保存…"}
            </span>
          ) : lastSavedAt ? (
            <span style={{ fontSize: 10, color: `${MUTED_FG}99` }}>
              {"已保存"}
            </span>
          ) : null}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <ToolbarIconBtn
            title={"清空"}
            onClick={requestClearDocument}
            tone="danger"
          >
            <ClearOutlined style={{ fontSize: 17 }} />
          </ToolbarIconBtn>
          <ToolbarIconBtn title={"导出 Markdown"} onClick={handleDownload}>
            <DownloadOutlined style={{ fontSize: 17 }} />
          </ToolbarIconBtn>
          <ToolbarIconBtn
            title={"保存到笔记本"}
            onClick={handleOpenSaveToNotebook}
          >
            <FormOutlined style={{ fontSize: 17 }} />
          </ToolbarIconBtn>
          <ToolbarIconBtn
            title={"加载示例模板"}
            onClick={requestLoadExampleTemplate}
            tone="warning"
          >
            <FileTextOutlined style={{ fontSize: 17 }} />
          </ToolbarIconBtn>
          <a
            href="https://litewrite.ai/"
            target="_blank"
            rel="noreferrer"
            onMouseEnter={(e) => {
              e.currentTarget.style.background = MUTED;
              e.currentTarget.style.color = FG;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.color = MUTED_FG;
            }}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              borderRadius: 9999,
              border: `1px solid ${BORDER}`,
              padding: "4px 10px",
              fontSize: 11,
              fontWeight: 500,
              color: MUTED_FG,
              textDecoration: "none",
              transition: "background-color 150ms, color 150ms",
            }}
          >
            <span>{"Pro Vide Writing"}</span>
            <ExportOutlined style={{ fontSize: 12 }} aria-hidden="true" />
          </a>
          <div style={{ margin: "0 4px", height: 20, width: 1, background: BORDER }} />
          <button
            onClick={() => setIsEditModalOpen(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 8,
              background: PRIMARY,
              padding: "6px 12px",
              fontSize: 12.5,
              fontWeight: 500,
              color: PRIMARY_FG,
              border: "none",
              cursor: "pointer",
              transition: "opacity 150ms, transform 150ms",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.opacity = "0.9";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = "1";
            }}
            onMouseDown={(e) => {
              e.currentTarget.style.transform = "scale(0.97)";
            }}
            onMouseUp={(e) => {
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            <ThunderboltOutlined style={{ fontSize: 13 }} />
            {"全文"}
          </button>
        </div>
      </header>

      {/* ── Toolbar ── */}
      <div
        style={{
          display: "flex",
          flexShrink: 0,
          alignItems: "center",
          gap: 2,
          overflowX: "auto",
          borderBottom: `1px solid ${BORDER}`,
          padding: "4px 12px",
        }}
      >
        {TOOLBAR.map((item) => {
          if (item.type === "separator") {
            return (
              <div
                key={item.id}
                style={{ margin: "0 4px", height: 16, width: 1, flexShrink: 0, background: BORDER }}
              />
            );
          }
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              title={item.title}
              onClick={() =>
                item.action ? item.action() : insertSnippet(item.snippet || "")
              }
              onMouseEnter={(e) => {
                e.currentTarget.style.background = `${MUTED}8c`;
                e.currentTarget.style.color = FG;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = MUTED_FG;
              }}
              onMouseDown={(e) => {
                e.currentTarget.style.transform = "scale(0.97)";
              }}
              onMouseUp={(e) => {
                e.currentTarget.style.transform = "scale(1)";
              }}
              style={{
                flexShrink: 0,
                borderRadius: 6,
                padding: 6,
                color: MUTED_FG,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                lineHeight: 0,
                transition: "background-color 150ms, color 150ms, transform 100ms",
              }}
            >
              <Icon size={16} />
            </button>
          );
        })}

        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            flexShrink: 0,
            alignItems: "center",
            gap: 6,
            paddingLeft: 12,
            fontSize: 10.5,
            color: MUTED_FG,
          }}
        >
          <button
            type="button"
            onClick={() => setSyncScrollEnabled((prev) => !prev)}
            disabled={!showEditor || !showPreview}
            title={
              syncScrollEnabled
                ? "滚动同步已开启，点击关闭"
                : "滚动同步已关闭，点击开启"
            }
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 8,
              padding: "4px 8px",
              fontSize: 10.5,
              fontWeight: 500,
              cursor: !showEditor || !showPreview ? "not-allowed" : "pointer",
              opacity: !showEditor || !showPreview ? 0.4 : 1,
              background: syncScrollEnabled ? `${PRIMARY}1a` : "transparent",
              color: syncScrollEnabled ? PRIMARY : MUTED_FG,
              border: "none",
              transition: "background-color 150ms, color 150ms",
            }}
          >
            <span
              aria-hidden="true"
              style={{
                display: "inline-block",
                height: 6,
                width: 6,
                borderRadius: 9999,
                background: syncScrollEnabled ? PRIMARY : `${MUTED_FG}99`,
              }}
            />
            {"同步滚动"}
          </button>
          <span
            aria-hidden="true"
            style={{ margin: "0 2px", height: 12, width: 1, background: BORDER }}
          />
          <span style={{ borderRadius: 6, background: MUTED, padding: "2px 6px" }}>
            {"GFM"}
          </span>
          <span style={{ borderRadius: 6, background: MUTED, padding: "2px 6px" }}>
            {"KaTeX"}
          </span>
          <span style={{ borderRadius: 6, background: MUTED, padding: "2px 6px" }}>
            {"Mermaid"}
          </span>
        </div>
      </div>

      {/* ── Editor + Preview ── */}
      <div
        ref={splitContainerRef}
        style={{
          position: "relative",
          display: "flex",
          minWidth: 0,
          flex: 1,
          userSelect: isResizingSplit ? "none" : "auto",
        }}
      >
        {/* Editor panel */}
        {showEditor && (
          <div
            style={{
              display: "flex",
              minWidth: 0,
              flexDirection: "column",
              width: showPreview ? `${editorRatio * 100}%` : "100%",
            }}
          >
            <div
              style={{
                display: "flex",
                flexShrink: 0,
                alignItems: "center",
                justifyContent: "space-between",
                borderBottom: `1px solid ${BORDER}`,
                padding: "4px 12px",
              }}
            >
              <span style={{ fontSize: 12, fontWeight: 500, color: MUTED_FG }}>
                {"编辑器"}
              </span>
              <button
                title={"收起编辑器"}
                onClick={() => setEditorCollapsed(true)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = MUTED;
                  e.currentTarget.style.color = FG;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = MUTED_FG;
                }}
                style={{
                  borderRadius: 4,
                  padding: 2,
                  color: MUTED_FG,
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  lineHeight: 0,
                  transition: "background-color 150ms, color 150ms",
                }}
              >
                <LeftOutlined style={{ fontSize: 14 }} />
              </button>
            </div>
            <textarea
              ref={textareaRef}
              value={markdown}
              onChange={(e) => handleMarkdownChange(e.target.value)}
              onSelect={updateSelectionPopover}
              onKeyDown={handleEditorKeyDown}
              onKeyUp={updateSelectionPopover}
              onMouseUp={updateSelectionPopover}
              onScroll={handleEditorScrollSync}
              spellCheck={false}
              style={{
                minWidth: 0,
                flex: 1,
                resize: "none",
                background: "transparent",
                padding: 16,
                fontFamily: MONO_FONT,
                fontSize: 13,
                lineHeight: 1.625,
                color: FG,
                outline: "none",
                border: "none",
              }}
              placeholder={"开始用 Markdown 写作…"}
            />
          </div>
        )}

        {/* Draggable splitter (only when both panes are visible) */}
        {showEditor && showPreview && (
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label={"调整编辑器与预览的比例"}
            onPointerDown={handleSplitterPointerDown}
            onDoubleClick={() => setEditorRatio(0.5)}
            title={"拖动以调整大小，双击复位"}
            style={{
              position: "relative",
              zIndex: 10,
              display: "flex",
              width: 4,
              flexShrink: 0,
              alignItems: "stretch",
              cursor: "col-resize",
              borderLeft: `1px solid ${BORDER}`,
              borderRight: `1px solid ${BORDER}`,
              background: isResizingSplit ? `${PRIMARY}66` : "transparent",
              transition: "background-color 150ms",
            }}
            onMouseEnter={(e) => {
              if (!isResizingSplit) {
                e.currentTarget.style.background = `${PRIMARY}4d`;
              }
            }}
            onMouseLeave={(e) => {
              if (!isResizingSplit) {
                e.currentTarget.style.background = "transparent";
              }
            }}
          >
            {/* Wider invisible hit-area so the handle is easy to grab */}
            <div style={{ position: "absolute", top: 0, bottom: 0, left: -6, right: -6 }} />
            <div
              style={{
                pointerEvents: "none",
                position: "absolute",
                left: "50%",
                top: "50%",
                height: 40,
                width: 3,
                transform: "translate(-50%, -50%)",
                borderRadius: 9999,
                background: isResizingSplit ? PRIMARY : `${MUTED_FG}66`,
                opacity: isResizingSplit ? 1 : 0.4,
              }}
            />
          </div>
        )}

        {/* Collapse gutter / expand buttons */}
        {editorCollapsed && (
          <button
            onClick={() => setEditorCollapsed(false)}
            title={"展开编辑器"}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = MUTED;
              e.currentTarget.style.color = FG;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.color = MUTED_FG;
            }}
            style={{
              display: "flex",
              width: 28,
              flexShrink: 0,
              alignItems: "center",
              justifyContent: "center",
              borderRight: `1px solid ${BORDER}`,
              color: MUTED_FG,
              background: "transparent",
              cursor: "pointer",
              transition: "background-color 150ms, color 150ms",
            }}
          >
            <RightOutlined style={{ fontSize: 14 }} />
          </button>
        )}

        {previewCollapsed && (
          <button
            onClick={() => setPreviewCollapsed(false)}
            title={"展开预览"}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = MUTED;
              e.currentTarget.style.color = FG;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.color = MUTED_FG;
            }}
            style={{
              display: "flex",
              width: 28,
              flexShrink: 0,
              alignItems: "center",
              justifyContent: "center",
              borderLeft: `1px solid ${BORDER}`,
              color: MUTED_FG,
              background: "transparent",
              cursor: "pointer",
              transition: "background-color 150ms, color 150ms",
            }}
          >
            <LeftOutlined style={{ fontSize: 14 }} />
          </button>
        )}

        {/* Preview panel */}
        {showPreview && (
          <div
            style={{
              display: "flex",
              minWidth: 0,
              flexDirection: "column",
              width: showEditor ? `${(1 - editorRatio) * 100}%` : "100%",
            }}
          >
            <div
              style={{
                display: "flex",
                flexShrink: 0,
                alignItems: "center",
                justifyContent: "space-between",
                borderBottom: `1px solid ${BORDER}`,
                padding: "4px 12px",
              }}
            >
              <span style={{ fontSize: 12, fontWeight: 500, color: MUTED_FG }}>
                {"预览"}
              </span>
              <button
                title={"收起预览"}
                onClick={() => setPreviewCollapsed(true)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = MUTED;
                  e.currentTarget.style.color = FG;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = MUTED_FG;
                }}
                style={{
                  borderRadius: 4,
                  padding: 2,
                  color: MUTED_FG,
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  lineHeight: 0,
                  transition: "background-color 150ms, color 150ms",
                }}
              >
                <RightOutlined style={{ fontSize: 14 }} />
              </button>
            </div>
            <div
              ref={previewScrollRef}
              onScroll={handlePreviewScrollSync}
              style={{ minWidth: 0, flex: 1, overflowY: "auto", padding: 20 }}
            >
              <MarkdownRenderer
                content={markdown || "_暂无内容可预览。_"}
                variant="prose"
                trackSourceLines
              />
            </div>
          </div>
        )}
      </div>

      {selectionPopover.visible && selectedRange && (
        <div
          ref={selectionPopoverRef}
          onMouseDown={handleSelectionPopoverDragStart}
          style={{
            position: "fixed",
            zIndex: 50,
            borderRadius: 16,
            border: `1px solid ${BORDER}`,
            background: POPOVER,
            padding: 10,
            boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
            backdropFilter: "blur(8px)",
            cursor: isDraggingSelectionPopover ? "grabbing" : "grab",
            top: selectionPopover.top,
            left: selectionPopover.left,
            width: 360,
          }}
        >
          <div
            style={{ marginBottom: 8, display: "flex", justifyContent: "center" }}
            aria-hidden="true"
          >
            <div style={{ height: 4, width: 40, borderRadius: 9999, background: `${BORDER}cc` }} />
          </div>

          <div style={{ position: "relative" }}>
            <input
              value={selectionInstruction}
              onChange={(e) => setSelectionInstruction(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void applyReactSelectionEdit();
                }
              }}
              style={{
                height: 40,
                width: "100%",
                borderRadius: 12,
                background: "transparent",
                paddingLeft: 12,
                paddingRight: 40,
                fontSize: 13,
                color: FG,
                outline: "none",
                border: "none",
              }}
              placeholder={"告诉 AI 如何处理所选内容…"}
            />
            <button
              onClick={() => void applyReactSelectionEdit()}
              disabled={isEditing || isAutoMarking}
              title={"应用 AI 编辑"}
              style={{
                position: "absolute",
                right: 6,
                top: 6,
                display: "inline-flex",
                height: 28,
                width: 28,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 10,
                background: PRIMARY,
                color: PRIMARY_FG,
                border: "none",
                cursor: isEditing || isAutoMarking ? "not-allowed" : "pointer",
                opacity: isEditing || isAutoMarking ? 0.25 : 1,
                transition: "background-color 150ms, transform 150ms, opacity 150ms",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = `${PRIMARY}e6`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = PRIMARY;
              }}
              onMouseDown={(e) => {
                e.currentTarget.style.transform = "scale(0.95)";
              }}
              onMouseUp={(e) => {
                e.currentTarget.style.transform = "scale(1)";
              }}
            >
              {isEditing ? (
                <LoadingOutlined style={{ fontSize: 13 }} spin />
              ) : (
                <ArrowRightOutlined style={{ fontSize: 13 }} />
              )}
            </button>
          </div>

          <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div style={{ position: "relative" }}>
              <button
                onClick={() => {
                  setIsToolMenuOpen((prev) => !prev);
                  setIsModeMenuOpen(false);
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `${MUTED}8c`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
                style={{
                  display: "flex",
                  height: 32,
                  width: "100%",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderRadius: 8,
                  border: `1px solid ${BORDER}`,
                  padding: "0 10px",
                  fontSize: 12.5,
                  color: FG,
                  background: "transparent",
                  cursor: "pointer",
                  transition: "background-color 150ms",
                }}
              >
                <span
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {selectionTools.length === 0
                    ? "工具"
                    : selectionTools.length === 1
                      ? TOOL_OPTIONS.find(
                          (item) => item.name === selectionTools[0],
                        )?.label || "工具"
                      : `${selectionTools.length} 个工具`}
                </span>
                <DownOutlined
                  style={{
                    fontSize: 13,
                    flexShrink: 0,
                    transition: "transform 150ms",
                    transform: isToolMenuOpen ? "rotate(180deg)" : "none",
                  }}
                />
              </button>
              {isToolMenuOpen && (
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: "100%",
                    zIndex: 20,
                    marginTop: 4,
                    width: "100%",
                    borderRadius: 12,
                    border: `1px solid ${BORDER}`,
                    background: POPOVER,
                    padding: 4,
                    boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  {TOOL_OPTIONS.map((tool) => {
                    const active = selectionTools.includes(tool.name);
                    return (
                      <button
                        key={tool.name}
                        onClick={() => toggleSelectionTool(tool.name)}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = `${MUTED}73`;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                        }}
                        style={{
                          display: "flex",
                          width: "100%",
                          alignItems: "center",
                          justifyContent: "space-between",
                          borderRadius: 8,
                          padding: "6px 10px",
                          textAlign: "left",
                          fontSize: 12.5,
                          color: FG,
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                          transition: "background-color 150ms",
                        }}
                      >
                        <span>{tool.label}</span>
                        {active ? (
                          <CheckOutlined style={{ fontSize: 12 }} />
                        ) : (
                          <span style={{ width: 12 }} />
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div style={{ position: "relative" }}>
              <button
                onClick={() => {
                  setIsModeMenuOpen((prev) => !prev);
                  setIsToolMenuOpen(false);
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `${MUTED}8c`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
                style={{
                  display: "flex",
                  height: 32,
                  width: "100%",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderRadius: 8,
                  border: `1px solid ${BORDER}`,
                  padding: "0 10px",
                  fontSize: 12.5,
                  color: FG,
                  background: "transparent",
                  cursor: "pointer",
                  transition: "background-color 150ms",
                }}
              >
                <span>
                  {MODE_OPTIONS.find((item) => item.value === selectionMode)
                    ?.label || "模式"}
                </span>
                <DownOutlined
                  style={{
                    fontSize: 13,
                    flexShrink: 0,
                    transition: "transform 150ms",
                    transform: isModeMenuOpen ? "rotate(180deg)" : "none",
                  }}
                />
              </button>
              {isModeMenuOpen && (
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: "100%",
                    zIndex: 20,
                    marginTop: 4,
                    width: "100%",
                    borderRadius: 12,
                    border: `1px solid ${BORDER}`,
                    background: POPOVER,
                    padding: 4,
                    boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  {MODE_OPTIONS.map((mode) => (
                    <button
                      key={mode.value}
                      onClick={() => {
                        setSelectionMode(mode.value);
                        setIsModeMenuOpen(false);
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = MUTED;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "transparent";
                      }}
                      style={{
                        display: "flex",
                        width: "100%",
                        alignItems: "center",
                        justifyContent: "space-between",
                        borderRadius: 8,
                        padding: "8px 10px",
                        textAlign: "left",
                        fontSize: 12,
                        color: FG,
                        background: "transparent",
                        border: "none",
                        cursor: "pointer",
                        transition: "background-color 150ms",
                      }}
                    >
                      <span>{mode.label}</span>
                      {selectionMode === mode.value ? (
                        <CheckOutlined style={{ fontSize: 12 }} />
                      ) : (
                        <span style={{ width: 12 }} />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {selectionTools.includes("rag") && (
            <select
              value={kbName}
              onChange={(e) => setKbName(e.target.value)}
              aria-label={"知识库"}
              style={{
                marginTop: 8,
                height: 32,
                width: "100%",
                borderRadius: 8,
                border: `1px solid ${BORDER}`,
                background: "transparent",
                padding: "0 10px",
                fontSize: 12.5,
                color: FG,
                outline: "none",
                transition: "border-color 150ms",
                cursor: "pointer",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = `${PRIMARY}59`;
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = BORDER;
              }}
            >
              <option value="">{"Select a knowledge base..."}</option>
              {knowledgeBases.map((k) => (
                <option key={k.name} value={k.name}>
                  {k.name}
                </option>
              ))}
            </select>
          )}

          {(isEditing || selectionTrace) && (
            <div
              style={{
                marginTop: 8,
                borderRadius: 12,
                border: `1px solid ${BORDER}b3`,
                background: `${MUTED}2e`,
              }}
            >
              <button
                onClick={() => setIsTraceExpanded((prev) => !prev)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = FG;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = MUTED_FG;
                }}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 12px",
                  textAlign: "left",
                  fontSize: 12,
                  color: MUTED_FG,
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  transition: "color 150ms",
                }}
              >
                <DownOutlined
                  style={{
                    fontSize: 12,
                    flexShrink: 0,
                    transition: "transform 150ms",
                    transform: isTraceExpanded ? "rotate(180deg)" : "none",
                  }}
                />
                <span style={{ fontWeight: 500, color: FG }}>{"追踪"}</span>
                {isEditing ? (
                  <LoadingOutlined style={{ fontSize: 12, marginLeft: "auto" }} spin />
                ) : null}
              </button>

              {isTraceExpanded && (
                <div
                  data-no-drag="true"
                  style={{
                    maxHeight: 280,
                    overflowY: "auto",
                    borderTop: `1px solid ${BORDER}99`,
                    padding: "8px 12px",
                    fontSize: 12,
                    lineHeight: 1.7,
                    color: MUTED_FG,
                  }}
                >
                  {selectionTrace && selectionTrace.toolTraces.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      <div
                        style={{
                          fontSize: 11,
                          fontWeight: 500,
                          textTransform: "uppercase",
                          letterSpacing: "0.08em",
                          color: `${MUTED_FG}99`,
                        }}
                      >
                        {"工具"}
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {selectionTrace.toolTraces.map((trace, index) => (
                          <div
                            key={`${trace.name}-${index}`}
                            style={{ display: "flex", flexDirection: "column", gap: 4 }}
                          >
                            <div>
                              <span style={{ opacity: 0.5 }}>
                                {trace.kind === "tool_result" ? "✓ " : "→ "}
                              </span>
                              <span style={{ color: FG }}>
                                {TOOL_OPTIONS.find(
                                  (item) => item.name === trace.name,
                                )?.label || trace.name}
                              </span>
                            </div>
                            {trace.arguments &&
                            Object.keys(trace.arguments).length > 0 ? (
                              <pre
                                style={{
                                  marginLeft: 12,
                                  whiteSpace: "pre-wrap",
                                  overflowWrap: "break-word",
                                  borderRadius: 6,
                                  background: `${MUTED}73`,
                                  padding: "4px 8px",
                                  fontFamily: MONO_FONT,
                                  fontSize: 11,
                                  lineHeight: 1.55,
                                  color: `${MUTED_FG}c7`,
                                  margin: 0,
                                }}
                              >
                                {JSON.stringify(trace.arguments, null, 2)}
                              </pre>
                            ) : null}
                            {trace.result ? (
                              <div style={{ marginLeft: 12 }}>
                                <MarkdownRenderer
                                  content={trace.result}
                                  variant="trace"
                                />
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectionTrace?.response ? (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                        marginTop: selectionTrace.toolTraces.length > 0 ? 12 : 0,
                      }}
                    >
                      <div
                        style={{
                          fontSize: 11,
                          fontWeight: 500,
                          textTransform: "uppercase",
                          letterSpacing: "0.08em",
                          color: `${MUTED_FG}99`,
                        }}
                      >
                        {"回复"}
                      </div>
                      <MarkdownRenderer
                        content={selectionTrace.response}
                        variant="trace"
                      />
                    </div>
                  ) : null}

                  {isEditing &&
                  selectionTrace &&
                  selectionTrace.toolTraces.length === 0 &&
                  !selectionTrace.response ? (
                    <div style={{ opacity: 0.7 }}>
                      {"正在运行工具并准备最终编辑…"}
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Status bar ── */}
      {(error || status) && (
        <div
          style={{
            flexShrink: 0,
            borderTop: `1px solid ${error ? "#fecaca" : "#a7f3d0"}`,
            background: error ? "#fef2f2" : "#ecfdf5",
            color: error ? "#dc2626" : "#059669",
            padding: "6px 16px",
            fontSize: 12,
          }}
        >
          {error || status}
        </div>
      )}

      {/* ── AI Edit modal ── */}
      {isEditModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0, 0, 0, 0.4)",
            backdropFilter: "blur(4px)",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsEditModalOpen(false);
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 448,
              borderRadius: 16,
              border: `1px solid ${BORDER}`,
              background: CARD,
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                borderBottom: `1px solid ${BORDER}`,
                padding: "12px 16px",
              }}
            >
              <h2 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: FG }}>
                {"全文 AI 编辑"}
              </h2>
              <button
                onClick={() => setIsEditModalOpen(false)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = FG;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = MUTED_FG;
                }}
                style={{
                  fontSize: 12,
                  color: MUTED_FG,
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  transition: "color 150ms",
                }}
              >
                {"关闭"}
              </button>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 12,
                padding: "16px",
              }}
            >
              <div style={{ display: "flex", gap: 6 }}>
                {(Object.keys(ACTION_LABELS) as EditAction[]).map((a) => (
                  <button
                    key={a}
                    onClick={() => setAction(a)}
                    style={{
                      borderRadius: 8,
                      padding: "6px 12px",
                      fontSize: 12.5,
                      fontWeight: 500,
                      cursor: "pointer",
                      transition: "background-color 150ms, color 150ms",
                      background: action === a ? PRIMARY : "transparent",
                      color: action === a ? PRIMARY_FG : FG,
                      border: action === a ? "none" : `1px solid ${BORDER}`,
                    }}
                    onMouseEnter={(e) => {
                      if (action !== a) {
                        e.currentTarget.style.background = `${MUTED}8c`;
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (action !== a) {
                        e.currentTarget.style.background = "transparent";
                      }
                    }}
                  >
                    {ACTION_LABELS[a]}
                  </button>
                ))}
              </div>

              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                rows={4}
                style={{
                  width: "100%",
                  borderRadius: 8,
                  border: `1px solid ${BORDER}`,
                  background: BACKGROUND,
                  padding: "8px 12px",
                  fontSize: 14,
                  color: FG,
                  outline: "none",
                  fontFamily: "inherit",
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = PRIMARY;
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = BORDER;
                }}
                placeholder={"描述你想如何编辑文本…"}
              />

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label
                    style={{
                      display: "block",
                      marginBottom: 4,
                      fontSize: 10,
                      fontWeight: 500,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      color: MUTED_FG,
                    }}
                  >
                    {"来源"}
                  </label>
                  <select
                    value={source}
                    onChange={(e) => setSource(e.target.value as SourceOption)}
                    style={{
                      width: "100%",
                      borderRadius: 8,
                      border: `1px solid ${BORDER}`,
                      background: BACKGROUND,
                      padding: "6px 8px",
                      fontSize: 12,
                      color: FG,
                      outline: "none",
                      transition: "border-color 150ms",
                      cursor: "pointer",
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = PRIMARY;
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = BORDER;
                    }}
                  >
                    <option value="none">{"无"}</option>
                    <option value="rag">{"知识库"}</option>
                    <option value="web">{"网络搜索"}</option>
                  </select>
                </div>
                <div>
                  <label
                    style={{
                      display: "block",
                      marginBottom: 4,
                      fontSize: 10,
                      fontWeight: 500,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      color: MUTED_FG,
                    }}
                  >
                    {"知识库"}
                  </label>
                  <select
                    value={kbName}
                    onChange={(e) => setKbName(e.target.value)}
                    disabled={source !== "rag"}
                    style={{
                      width: "100%",
                      borderRadius: 8,
                      border: `1px solid ${BORDER}`,
                      background: BACKGROUND,
                      padding: "6px 8px",
                      fontSize: 12,
                      color: FG,
                      outline: "none",
                      transition: "border-color 150ms",
                      cursor: source !== "rag" ? "not-allowed" : "pointer",
                      opacity: source !== "rag" ? 0.4 : 1,
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = PRIMARY;
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = BORDER;
                    }}
                  >
                    <option value="">{"选择…"}</option>
                    {knowledgeBases.map((k) => (
                      <option key={k.name} value={k.name}>
                        {k.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 8,
                borderTop: `1px solid ${BORDER}`,
                padding: "12px 16px",
              }}
            >
              <button
                onClick={applyAutoMark}
                disabled={isEditing || isAutoMarking}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 8,
                  border: `1px solid ${BORDER}`,
                  padding: "6px 12px",
                  fontSize: 12.5,
                  fontWeight: 500,
                  color: FG,
                  background: "transparent",
                  cursor: isEditing || isAutoMarking ? "not-allowed" : "pointer",
                  opacity: isEditing || isAutoMarking ? 0.5 : 1,
                  transition: "background-color 150ms",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `${MUTED}8c`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
              >
                {isAutoMarking ? (
                  <LoadingOutlined style={{ fontSize: 13 }} spin />
                ) : (
                  <HighlightOutlined style={{ fontSize: 13 }} />
                )}
                {"自动批注"}
              </button>
              <button
                onClick={applyEdit}
                disabled={isEditing || isAutoMarking}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 8,
                  background: PRIMARY,
                  padding: "6px 12px",
                  fontSize: 12.5,
                  fontWeight: 500,
                  color: PRIMARY_FG,
                  border: "none",
                  cursor: isEditing || isAutoMarking ? "not-allowed" : "pointer",
                  opacity: isEditing || isAutoMarking ? 0.5 : 1,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.opacity =
                    isEditing || isAutoMarking ? "0.5" : "0.9";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.opacity =
                    isEditing || isAutoMarking ? "0.5" : "1";
                }}
              >
                {isEditing ? (
                  <LoadingOutlined style={{ fontSize: 13 }} spin />
                ) : (
                  <ArrowRightOutlined style={{ fontSize: 13 }} />
                )}
                {"应用"}
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmActionCopy && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0, 0, 0, 0.4)",
            padding: 16,
            backdropFilter: "blur(4px)",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setPendingConfirmAction(null);
          }}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="co-writer-confirm-title"
            aria-describedby="co-writer-confirm-description"
            style={{
              width: "100%",
              maxWidth: 384,
              borderRadius: 16,
              border: `1px solid ${BORDER}`,
              background: CARD,
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            }}
          >
            <div style={{ borderBottom: `1px solid ${BORDER}`, padding: "12px 16px" }}>
              <h2
                id="co-writer-confirm-title"
                style={{ margin: 0, fontSize: 14, fontWeight: 600, color: FG }}
              >
                {confirmActionCopy.title}
              </h2>
              <p
                id="co-writer-confirm-description"
                style={{ marginTop: 4, marginBottom: 0, fontSize: 12, lineHeight: 1.625, color: MUTED_FG }}
              >
                {confirmActionCopy.description}
              </p>
            </div>

            <div style={{ padding: "12px 16px" }}>
              <div
                style={{
                  borderRadius: 8,
                  border: "1px solid #fde68a",
                  background: "#fffbeb",
                  padding: "8px 12px",
                  fontSize: 11,
                  lineHeight: 1.625,
                  color: "#92400e",
                }}
              >
                {"可按 Ctrl/Cmd+Z，或使用工具栏撤销按钮恢复。"}
              </div>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 8,
                borderTop: `1px solid ${BORDER}`,
                padding: "12px 16px",
              }}
            >
              <button
                type="button"
                onClick={() => setPendingConfirmAction(null)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `${MUTED}8c`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
                style={{
                  borderRadius: 8,
                  border: `1px solid ${BORDER}`,
                  padding: "6px 12px",
                  fontSize: 12.5,
                  fontWeight: 500,
                  color: FG,
                  background: "transparent",
                  cursor: "pointer",
                  transition: "background-color 150ms",
                }}
              >
                {"取消"}
              </button>
              <button
                type="button"
                onClick={() => {
                  const onConfirm = confirmActionCopy.onConfirm;
                  setPendingConfirmAction(null);
                  onConfirm();
                }}
                style={{
                  borderRadius: 8,
                  padding: "6px 12px",
                  fontSize: 12.5,
                  fontWeight: 500,
                  color: "#ffffff",
                  background: confirmActionCopy.tone === "danger" ? "#e11d48" : "#d97706",
                  border: "none",
                  cursor: "pointer",
                  transition: "opacity 150ms",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.opacity = "0.9";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.opacity = "1";
                }}
              >
                {confirmActionCopy.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}

      <SaveToNotebookModal
        open={notebookSavePayload !== null}
        payload={notebookSavePayload}
        onClose={() => setNotebookSavePayload(null)}
        onSaved={() => {
          setStatus("已保存到笔记本。");
          setError("");
        }}
      />
    </div>
  );
}

function ToolbarIconBtn({
  title,
  onClick,
  children,
  tone = "default",
}: {
  title: string;
  onClick: () => void;
  children: ReactNode;
  tone?: "default" | "danger" | "warning";
}) {
  const [hovered, setHovered] = useState(false);
  const toneStyle = toneHover(tone, hovered);

  return (
    <button
      type="button"
      aria-label={title}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        position: "relative",
        display: "inline-flex",
        height: 32,
        width: 32,
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 8,
        border: "none",
        cursor: "pointer",
        background: toneStyle.background,
        color: toneStyle.color,
        transition: "background-color 150ms, color 150ms",
      }}
    >
      {children}
      <span
        role="tooltip"
        style={{
          pointerEvents: "none",
          position: "absolute",
          left: "50%",
          top: "100%",
          zIndex: 30,
          marginTop: 6,
          transform: "translateX(-50%)",
          whiteSpace: "nowrap",
          borderRadius: 6,
          border: `1px solid ${BORDER}`,
          background: CARD,
          padding: "4px 8px",
          fontSize: 10,
          fontWeight: 500,
          color: FG,
          opacity: hovered ? 1 : 0,
          boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
          transition: "opacity 100ms",
        }}
      >
        {title}
      </span>
    </button>
  );
}
