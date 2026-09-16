/**
 * 复刻自 DeepTutor 原仓 web/components/quiz/FollowupChatComposer.tsx（整件 1:1）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. next/dynamic → React.lazy + Suspense（ssr:false 语义由 lazy+Suspense 承接）。
 *    6 个 @space 弹层为波次2（SA-F 交付）组件：h5shared/NotebookRecordPicker.tsx、
 *    HistorySessionPicker.tsx、QuestionBankPicker.tsx、PersonaPicker.tsx、
 *    MemoryPicker.tsx、BookReferencePicker.tsx（具名导出，lazy 转默认导出）；
 * 3. ChatComposer 默认导入自 "./ChatComposer"（SA-F 交付，同目录 h5shared 内；
 *    父代指令中 "../h5shared/ChatComposer" 写法按文件实际落位修正为 "./ChatComposer"，
 *    见收尾报告）；
 * 4. isSvgFilename：批8 admin/doc-attachments.ts 裁剪未收录 → SA-F 已在
 *    h5shared/doc-attachments.ts 按原仓实现补齐，本文件按原仓形状从 "./doc-attachments"
 *    导入（classifyFile 经该件 re-export 批8 实现）；
 * 5. classifyFile → 批8 admin/doc-attachments.ts；useAttachmentLimits → 批8
 *    admin/attachment-limits.ts；file-attachments/knowledge-api/book-references →
 *    批8 admin/*；llm-options → ./llmOptions；quiz-types → ./quizTypes；
 *    QuizFollowupContext → ./QuizFollowupContext；unified-ws → 批8 admin/unified-ws.ts；
 *    SelectedRecord/SpaceMemoryFile → ./notebookSelectionTypes / ./spaceItems；
 * 6. lucide MessageSquare → @ant-design/icons MessageOutlined；
 * 7. i18n t() → 中文直出（译自原仓 locales/zh/app.json 逐键核对）；
 *    label/description 的 t() 解析改为直接携带中文文案。
 */
import {
  Suspense,
  lazy,
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { MessageOutlined } from "@ant-design/icons";
import ChatComposer from "./ChatComposer";
import {
  type QuizFollowupTabContext,
  useFollowupThread,
  useQuizFollowupController,
} from "./QuizFollowupContext";
import { buildQuizFollowupConfig } from "./quizTypes";
// classifyFile re-export 自批8 admin/doc-attachments.ts；isSvgFilename 批8 裁剪，
// 由 SA-F 在 h5shared/doc-attachments.ts 按原仓实现补齐（原仓导入形状保持不变）。
import { classifyFile, isSvgFilename } from "./doc-attachments";
import { useAttachmentLimits } from "../../admin/attachment-limits";
import {
  extractBase64FromDataUrl,
  readFileAsDataUrl,
} from "../../admin/file-attachments";
import { listKnowledgeBases } from "../../admin/knowledge-api";
import { listLLMOptions, type LLMOption } from "./llmOptions";
import { selectedBooksToPayload } from "../../admin/book-references";
import type { SelectedBookReference } from "../../admin/book-references";
import type { SelectedHistorySession } from "./HistorySessionPicker";
import type { SelectedQuestionEntry } from "./QuestionBankPicker";
import type { SelectedRecord } from "./notebookSelectionTypes";
import type { SpaceMemoryFile } from "./spaceItems";
import type { LLMSelection } from "../../admin/unified-ws";

// 6 个弹层均为波次2（SA-F）交付文件——lazy 具名转默认，命中即加载。
const NotebookRecordPicker = lazy(() =>
  import("./NotebookRecordPicker").then((m) => ({
    default: m.NotebookRecordPicker,
  })),
);
const HistorySessionPicker = lazy(() =>
  import("./HistorySessionPicker").then((m) => ({
    default: m.HistorySessionPicker,
  })),
);
const QuestionBankPicker = lazy(() =>
  import("./QuestionBankPicker").then((m) => ({
    default: m.QuestionBankPicker,
  })),
);
const PersonaPicker = lazy(() =>
  import("./PersonaPicker").then((m) => ({ default: m.PersonaPicker })),
);
const MemoryPicker = lazy(() =>
  import("./MemoryPicker").then((m) => ({ default: m.MemoryPicker })),
);
const BookReferencePicker = lazy(() =>
  import("./BookReferencePicker").then((m) => ({
    default: m.BookReferencePicker,
  })),
);

interface KnowledgeBase {
  name: string;
  is_default?: boolean;
}

interface PendingAttachment {
  type: string;
  filename: string;
  base64?: string;
  previewUrl?: string;
  size?: number;
  mimeType?: string;
}

// Single-capability list — the follow-up tab is locked to "chat".
// label/description are i18n keys; resolved via t() inside the component.
// （i18n→中文直出：「Chat」「Flexible conversation with any tool」）
const FOLLOWUP_CAPABILITIES_RAW = [
  {
    value: "",
    label: "聊天",
    description: "灵活对话，可使用任意工具",
    icon: MessageOutlined,
    allowedTools: [],
  },
];

interface FollowupChatComposerProps {
  context: QuizFollowupTabContext;
}

function FollowupChatComposerImpl({ context }: FollowupChatComposerProps) {
  const controller = useQuizFollowupController();
  const thread = useFollowupThread(context.questionKey);

  // ── Composer DOM refs ─────────────────────────────────────────
  const composerRef = useRef<HTMLDivElement>(null);
  const capMenuRef = useRef<HTMLDivElement>(null);
  const capBtnRef = useRef<HTMLButtonElement>(null);
  const spaceMenuRef = useRef<HTMLDivElement>(null);
  const spaceBtnRef = useRef<HTMLButtonElement>(null);
  const dragCounter = useRef(0);

  // ── Composer local state ──────────────────────────────────────
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const attachmentLimits = useAttachmentLimits();
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const attachmentErrorTimer = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const [dragging, setDragging] = useState(false);
  const [capMenuOpen, setCapMenuOpen] = useState(false);
  const [spaceMenuOpen, setSpaceMenuOpen] = useState(false);

  const [selectedKnowledgeBases, setSelectedKnowledgeBases] = useState<
    string[]
  >([]);
  const [selectedBookReferences, setSelectedBookReferences] = useState<
    SelectedBookReference[]
  >([]);
  const [selectedNotebookRecords, setSelectedNotebookRecords] = useState<
    SelectedRecord[]
  >([]);
  const [selectedHistorySessions, setSelectedHistorySessions] = useState<
    SelectedHistorySession[]
  >([]);
  const [selectedQuestionEntries, setSelectedQuestionEntries] = useState<
    SelectedQuestionEntry[]
  >([]);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [selectedMemoryFiles, setSelectedMemoryFiles] = useState<
    SpaceMemoryFile[]
  >([]);

  // ── Picker dialog visibility ──────────────────────────────────
  const [showNotebookPicker, setShowNotebookPicker] = useState(false);
  const [showBookPicker, setShowBookPicker] = useState(false);
  const [showHistoryPicker, setShowHistoryPicker] = useState(false);
  const [showQuestionBankPicker, setShowQuestionBankPicker] = useState(false);
  const [showPersonaPicker, setShowPersonaPicker] = useState(false);
  const [showMemoryPicker, setShowMemoryPicker] = useState(false);

  // ── Shared data (KBs + LLMs) ──────────────────────────────────
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [llmOptions, setLLMOptions] = useState<LLMOption[]>([]);
  const [activeLLMDefault, setActiveLLMDefault] = useState<LLMSelection | null>(
    null,
  );
  const [llmSelection, setLLMSelection] = useState<LLMSelection | null>(null);
  const [llmOptionsLoading, setLLMOptionsLoading] = useState(true);
  const [llmOptionsError, setLLMOptionsError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const list = await listKnowledgeBases({ force: false });
        if (!cancelled) setKnowledgeBases(list);
      } catch {
        if (!cancelled) setKnowledgeBases([]);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLLMOptionsLoading(true);
      try {
        const payload = await listLLMOptions();
        if (cancelled) return;
        setLLMOptions(payload.options);
        setActiveLLMDefault(payload.active);
        setLLMOptionsError(false);
      } catch {
        if (cancelled) return;
        setLLMOptionsError(true);
        setLLMOptions([]);
        setActiveLLMDefault(null);
      } finally {
        if (!cancelled) setLLMOptionsLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  // Default to the server-side active LLM until the user picks one.
  useEffect(() => {
    if (llmSelection || !activeLLMDefault) return;
    setLLMSelection(activeLLMDefault);
  }, [activeLLMDefault, llmSelection]);

  // Click-outside handlers for menu chrome (cap / space).
  useEffect(() => {
    if (!capMenuOpen && !spaceMenuOpen) return;
    const handler = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (
        capMenuOpen &&
        capMenuRef.current &&
        !capMenuRef.current.contains(target) &&
        capBtnRef.current &&
        !capBtnRef.current.contains(target)
      ) {
        setCapMenuOpen(false);
      }
      if (
        spaceMenuOpen &&
        spaceMenuRef.current &&
        !spaceMenuRef.current.contains(target) &&
        spaceBtnRef.current &&
        !spaceBtnRef.current.contains(target)
      ) {
        setSpaceMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [capMenuOpen, spaceMenuOpen]);

  // ── Attachment helpers ────────────────────────────────────────
  const showAttachmentError = useCallback((message: string) => {
    setAttachmentError(message);
    if (attachmentErrorTimer.current) {
      clearTimeout(attachmentErrorTimer.current);
    }
    attachmentErrorTimer.current = setTimeout(() => {
      setAttachmentError(null);
      attachmentErrorTimer.current = null;
    }, 4000);
  }, []);

  const fileToAttachment = useCallback(
    (f: File): Promise<PendingAttachment> =>
      new Promise((resolve, reject) => {
        readFileAsDataUrl(f)
          .then((raw) => {
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
          })
          .catch(reject);
      }),
    [],
  );

  const filterAndReportFiles = useCallback(
    (files: File[]): File[] => {
      let runningTotal = attachments.reduce((s, a) => s + (a.size ?? 0), 0);
      const accepted: File[] = [];
      const rejected: {
        name: string;
        reason: "unsupported" | "too_large" | "quota";
      }[] = [];
      for (const f of files) {
        const kind = classifyFile(f);
        if (!kind) {
          rejected.push({ name: f.name, reason: "unsupported" });
          continue;
        }
        if (f.size > attachmentLimits.maxFileBytes) {
          rejected.push({ name: f.name, reason: "too_large" });
          continue;
        }
        if (runningTotal + f.size > attachmentLimits.maxTotalBytes) {
          rejected.push({ name: f.name, reason: "quota" });
          break;
        }
        runningTotal += f.size;
        accepted.push(f);
      }
      if (rejected.length) {
        const first = rejected[0];
        let msg: string;
        if (first.reason === "too_large") {
          msg = `文件过大：${first.name}`;
        } else if (first.reason === "quota") {
          msg = "附件总量超出限制，已跳过部分文件";
        } else {
          msg = `不支持的文件类型：${first.name}`;
        }
        showAttachmentError(msg);
      }
      return accepted;
    },
    [attachments, attachmentLimits, showAttachmentError],
  );

  const handleAddFiles = useCallback(
    async (files: File[]) => {
      const accepted = filterAndReportFiles(files);
      if (!accepted.length) return;
      const next = await Promise.all(accepted.map(fileToAttachment));
      setAttachments((prev) => [...prev, ...next]);
    },
    [fileToAttachment, filterAndReportFiles],
  );

  const removeAttachment = useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handlePaste = useCallback(
    async (event: React.ClipboardEvent) => {
      const items = Array.from(event.clipboardData.items);
      const files = items
        .filter((item) => item.kind === "file")
        .map((item) => item.getAsFile())
        .filter((f): f is File => f !== null);
      const accepted = filterAndReportFiles(files);
      if (!accepted.length) return;
      event.preventDefault();
      const next = await Promise.all(accepted.map(fileToAttachment));
      setAttachments((prev) => [...prev, ...next]);
    },
    [fileToAttachment, filterAndReportFiles],
  );

  // ── Drag-and-drop on the composer surface ─────────────────────
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current += 1;
    if (e.dataTransfer.types.includes("Files")) setDragging(true);
  }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setDragging(false);
    }
  }, []);
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);
  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setDragging(false);
      const files = Array.from(e.dataTransfer.files);
      await handleAddFiles(files);
    },
    [handleAddFiles],
  );

  // ── Picker handlers ───────────────────────────────────────────
  const handleToggleKB = useCallback((name: string) => {
    setSelectedKnowledgeBases((prev) =>
      prev.includes(name) ? prev.filter((kb) => kb !== name) : [...prev, name],
    );
  }, []);

  const handleSelectNotebookPicker = useCallback(() => {
    setShowNotebookPicker(true);
  }, []);
  const handleSelectBookPicker = useCallback(() => {
    setShowBookPicker(true);
  }, []);
  const handleSelectHistoryPicker = useCallback(() => {
    setShowHistoryPicker(true);
  }, []);
  const handleSelectQuestionBankPicker = useCallback(() => {
    setShowQuestionBankPicker(true);
  }, []);
  const handleSelectPersonaPicker = useCallback(() => {
    setShowPersonaPicker(true);
  }, []);
  const handleSelectMemoryPicker = useCallback(() => {
    setShowMemoryPicker(true);
  }, []);

  const handleClearPersona = useCallback(() => {
    setSelectedPersona(null);
  }, []);
  const handleToggleMemoryFile = useCallback((file: SpaceMemoryFile) => {
    setSelectedMemoryFiles((prev) =>
      prev.includes(file) ? prev.filter((f) => f !== file) : [...prev, file],
    );
  }, []);

  const handleRemoveHistory = useCallback((sessionId: string) => {
    setSelectedHistorySessions((prev) =>
      prev.filter((s) => s.sessionId !== sessionId),
    );
  }, []);
  const handleRemoveBookReference = useCallback((bookId: string) => {
    setSelectedBookReferences((prev) =>
      prev.filter((b) => b.bookId !== bookId),
    );
  }, []);
  const handleRemoveNotebook = useCallback((notebookId: string) => {
    setSelectedNotebookRecords((prev) =>
      prev.filter((r) => r.notebookId !== notebookId),
    );
  }, []);
  const handleRemoveQuestion = useCallback((entryId: number) => {
    setSelectedQuestionEntries((prev) => prev.filter((e) => e.id !== entryId));
  }, []);

  // ── References payloads ───────────────────────────────────────
  const notebookReferencesPayload = useMemo(() => {
    const grouped = new Map<string, string[]>();
    selectedNotebookRecords.forEach((record) => {
      const current = grouped.get(record.notebookId) || [];
      current.push(record.id);
      grouped.set(record.notebookId, current);
    });
    return Array.from(grouped.entries()).map(([notebook_id, record_ids]) => ({
      notebook_id,
      record_ids,
    }));
  }, [selectedNotebookRecords]);
  const bookReferencesPayload = useMemo(
    () => selectedBooksToPayload(selectedBookReferences),
    [selectedBookReferences],
  );
  const historyReferencesPayload = useMemo(
    () => selectedHistorySessions.map((s) => s.sessionId),
    [selectedHistorySessions],
  );
  const questionNotebookReferencesPayload = useMemo(
    () => selectedQuestionEntries.map((entry) => entry.id),
    [selectedQuestionEntries],
  );
  const memoryReferencesPayload = useMemo(
    () => [...selectedMemoryFiles],
    [selectedMemoryFiles],
  );
  const notebookReferenceGroups = useMemo(() => {
    return notebookReferencesPayload.map((ref) => {
      const sample = selectedNotebookRecords.find(
        (r) => r.notebookId === ref.notebook_id,
      );
      return {
        notebookId: ref.notebook_id,
        notebookName: sample?.notebookName ?? ref.notebook_id,
        count: ref.record_ids.length,
      };
    });
  }, [notebookReferencesPayload, selectedNotebookRecords]);

  // Once the user has clicked Send we wipe transient selections — the
  // follow-up chat session has captured them and later turns ride on
  // server-side memory, mirroring the main chat behavior.
  const handleSend = useCallback(
    (content: string) => {
      const hasContent = content.trim().length > 0;
      const hasReferences =
        attachments.length > 0 ||
        selectedKnowledgeBases.length > 0 ||
        selectedBookReferences.length > 0 ||
        selectedNotebookRecords.length > 0 ||
        selectedHistorySessions.length > 0 ||
        selectedQuestionEntries.length > 0 ||
        !!selectedPersona ||
        selectedMemoryFiles.length > 0;
      if (!hasContent && !hasReferences) return;
      if (thread.isStreaming) return;

      const isFirstSend = !thread.sessionId && thread.messages.length === 0;
      const answerImageAttachments = isFirstSend
        ? context.answerImages
            .map((image) => {
              if (image.base64) {
                return {
                  type: "image",
                  base64: image.base64,
                  filename: image.filename,
                  mime_type: image.mime,
                } as const;
              }
              if (image.url) {
                return {
                  type: "image",
                  url: image.url,
                  filename: image.filename,
                  mime_type: image.mime,
                } as const;
              }
              return null;
            })
            .filter(
              (entry): entry is NonNullable<typeof entry> => entry !== null,
            )
        : [];

      const composerAttachments = attachments.map((a) => ({
        type: a.type,
        filename: a.filename,
        base64: a.base64,
        mime_type: a.mimeType,
      }));

      const personaPayload = selectedPersona ?? undefined;

      const baseConfig = buildQuizFollowupConfig(
        context.question,
        context.userAnswer,
        context.isCorrect,
        context.parentQuizSessionId,
        {
          userAnswerImageFilenames: context.answerImages.map(
            (image) => image.filename,
          ),
          aiJudgment: context.aiJudgment,
        },
      );

      // Memory references ride on ``config`` — same convention as the
      // main chat sendMessage path.
      const config: Record<string, unknown> = { ...baseConfig };
      if (memoryReferencesPayload.length > 0) {
        config.memory_references = memoryReferencesPayload;
      }

      controller.sendMessage({
        questionKey: context.questionKey,
        content,
        attachments: [...answerImageAttachments, ...composerAttachments],
        config,
        language: context.language,
        knowledgeBases: selectedKnowledgeBases,
        notebookReferences: notebookReferencesPayload,
        historyReferences: historyReferencesPayload,
        bookReferences: bookReferencesPayload,
        questionNotebookReferences: questionNotebookReferencesPayload,
        persona: personaPayload,
        llmSelection,
      });

      // Wipe transient selections — the chat session now owns them.
      setAttachments([]);
      setSelectedBookReferences([]);
      setSelectedNotebookRecords([]);
      setSelectedHistorySessions([]);
      setSelectedQuestionEntries([]);
      setSelectedPersona(null);
      setSelectedMemoryFiles([]);
    },
    [
      attachments,
      bookReferencesPayload,
      context,
      controller,
      historyReferencesPayload,
      llmSelection,
      memoryReferencesPayload,
      notebookReferencesPayload,
      questionNotebookReferencesPayload,
      selectedBookReferences.length,
      selectedHistorySessions.length,
      selectedKnowledgeBases,
      selectedMemoryFiles,
      selectedNotebookRecords.length,
      selectedQuestionEntries.length,
      selectedPersona,
      thread.isStreaming,
      thread.messages.length,
      thread.sessionId,
    ],
  );

  const handleCancelStreaming = useCallback(() => {
    // The follow-up runner is owned by the controller; we don't expose
    // a hard cancel from the public surface. Treat this as a no-op for
    // now — the user can refresh or close the tab to recover.
  }, []);

  // ── Active capability is always "chat" for follow-up ──────────
  const FOLLOWUP_CAPABILITIES = useMemo(
    () =>
      FOLLOWUP_CAPABILITIES_RAW.map((cap) => ({
        ...cap,
      })),
    [],
  );
  const activeCap = FOLLOWUP_CAPABILITIES[0];

  return (
    <>
      <ChatComposer
        composerRef={composerRef}
        capMenuRef={capMenuRef}
        capBtnRef={capBtnRef}
        spaceMenuRef={spaceMenuRef}
        spaceBtnRef={spaceBtnRef}
        dragCounter={dragCounter}
        dragging={dragging}
        capMenuOpen={capMenuOpen}
        spaceMenuOpen={spaceMenuOpen}
        hasMessages={
          thread.messages.filter((m) => m.role !== "system").length > 0
        }
        attachments={attachments}
        attachmentError={attachmentError}
        activeCap={activeCap}
        knowledgeBases={knowledgeBases}
        llmOptions={llmOptions}
        activeLLMDefault={activeLLMDefault}
        llmSelection={llmSelection}
        llmOptionsLoading={llmOptionsLoading}
        llmOptionsError={llmOptionsError}
        selectedBookReferences={selectedBookReferences}
        selectedNotebookRecords={selectedNotebookRecords}
        selectedHistorySessions={selectedHistorySessions}
        selectedAgentSessions={[]}
        selectedQuestionEntries={selectedQuestionEntries}
        notebookReferenceGroups={notebookReferenceGroups}
        selectedPersona={selectedPersona}
        selectedMemoryFiles={selectedMemoryFiles}
        selectedKnowledgeBases={selectedKnowledgeBases}
        isStreaming={thread.isStreaming}
        isVisualizeMode={false}
        capabilityNeedsConfig={false}
        capabilityConfigConfirmed={true}
        onRequestConfigConfirm={() => {}}
        capabilities={FOLLOWUP_CAPABILITIES}
        onSetCapMenuOpen={setCapMenuOpen}
        onSetSpaceMenuOpen={setSpaceMenuOpen}
        onToggleKB={handleToggleKB}
        onSelectLLM={setLLMSelection}
        onSelectNotebookPicker={handleSelectNotebookPicker}
        onSelectBookPicker={handleSelectBookPicker}
        onSelectHistoryPicker={handleSelectHistoryPicker}
        agentsAvailable={false}
        onSelectAgentsPicker={() => {}}
        onSelectQuestionBankPicker={handleSelectQuestionBankPicker}
        onSelectPersonaPicker={handleSelectPersonaPicker}
        onSelectMemoryPicker={handleSelectMemoryPicker}
        onClearPersona={handleClearPersona}
        onToggleMemoryFile={handleToggleMemoryFile}
        onSend={handleSend}
        onRemoveAttachment={removeAttachment}
        onRemoveHistory={handleRemoveHistory}
        onRemoveAgent={() => {}}
        onRemoveBookReference={handleRemoveBookReference}
        onRemoveNotebook={handleRemoveNotebook}
        onRemoveQuestion={handleRemoveQuestion}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onPaste={handlePaste}
        onAddFiles={handleAddFiles}
        onSelectCapability={() => {}}
        onCancelStreaming={handleCancelStreaming}
        inputPlaceholder="对这道题、你的作答或 AI 评判进行任何提问…"
      />

      <Suspense fallback={null}>
        <NotebookRecordPicker
          open={showNotebookPicker}
          onClose={() => setShowNotebookPicker(false)}
          onApply={(records: SelectedRecord[]) => {
            setSelectedNotebookRecords(records);
            setShowNotebookPicker(false);
          }}
        />
        <BookReferencePicker
          open={showBookPicker}
          initialReferences={selectedBookReferences}
          onClose={() => setShowBookPicker(false)}
          onApply={(refs: SelectedBookReference[]) => {
            setSelectedBookReferences(refs);
            setShowBookPicker(false);
          }}
        />
        <HistorySessionPicker
          open={showHistoryPicker}
          onClose={() => setShowHistoryPicker(false)}
          onApply={(sessions: SelectedHistorySession[]) => {
            setSelectedHistorySessions(sessions);
            setShowHistoryPicker(false);
          }}
        />
        <QuestionBankPicker
          open={showQuestionBankPicker}
          onClose={() => setShowQuestionBankPicker(false)}
          onApply={(entries: SelectedQuestionEntry[]) => {
            setSelectedQuestionEntries(entries);
            setShowQuestionBankPicker(false);
          }}
        />
        <PersonaPicker
          open={showPersonaPicker}
          initialPersona={selectedPersona}
          onClose={() => setShowPersonaPicker(false)}
          onApply={(persona: string | null) => {
            setSelectedPersona(persona);
            setShowPersonaPicker(false);
          }}
        />
        <MemoryPicker
          open={showMemoryPicker}
          initialFiles={selectedMemoryFiles}
          onClose={() => setShowMemoryPicker(false)}
          onApply={(files: SpaceMemoryFile[]) => {
            setSelectedMemoryFiles(files);
            setShowMemoryPicker(false);
          }}
        />
      </Suspense>
    </>
  );
}

const FollowupChatComposer = memo(FollowupChatComposerImpl);
export default FollowupChatComposer;

export type { FollowupChatComposerProps };
