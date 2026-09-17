/**
 * SaveToNotebookModal——逐字移植自原仓 web/components/notebook/SaveToNotebookModal.tsx（639 行）。
 * 归属说明：源编辑页（co-writer/[docId]/page.tsx）直接 import 本件（co-writer 专用
 * 消费面：recordType "co_writer"、不传 messages），按"按源 import 关系移植"落到本目录。
 *
 * 替换点（登记）：
 * - "use client" 删除；lucide → @ant-design/icons：Check→CheckOutlined、
 *   Loader2→LoadingOutlined、MessageSquare→MessageOutlined、NotebookPen→FormOutlined
 *   （NotebookPage 批先例）、Sparkles→StarOutlined（消息图标语义，TracePanels 批先例）；
 *   size/strokeWidth→style.fontSize（antd 图标无 strokeWidth 参数）；
 * - react-i18next t() → locales/zh/app.json 中文值逐字直用（原渲染即中文；
 *   "Failed to save to notebook." 等键以 zh/app.json 原译文为准）；
 * - apiFetch(apiUrl(x), init) → fetch(x, init)（apiUrl 恒等；credentials:"include"
 *   显式保留；401→/login 跳转为 DeepTutor 鉴权专属不复刻，tupu 先例）；
 * - listNotebooks/NotebookSummary → 复用 tupu 已移植件 ../admin/notebook-api（逐字等价）；
 * - PickerShell/PickerHeader → 复用 tupu 已移植件 ../h5/h5shared/（桌面同名件 1:1）；
 *   源 backdropClass="bg-[var(--background)]/65" → "rgba(255,255,255,0.65)"
 *   （tupu 单亮色主题等价物；tupu PickerShell 的 backdropClass 即背景色字符串）；
 *   源 className="p-4 backdrop-blur-md" 保留传参（tupu 降级版未消费该 prop，void 吸收）；
 * - Tailwind → 内联样式逐项对位（CSS 变量带 fallback，NotebookPage 批8 先例）；
 *   hover/focus 变体用 onMouseEnter/Leave、onFocus/onBlur 直写（本仓先例）；
 * - line-clamp-2 → WebkitLineClamp 内联。
 */
import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, MouseEvent as ReactMouseEvent } from "react";
import {
  CheckOutlined,
  LoadingOutlined,
  MessageOutlined,
  FormOutlined,
  StarOutlined,
} from "@ant-design/icons";
// IA批6：源路径 @/components/notebook/SaveToNotebookModal——C2 于 cowriter/ 落盘后
// 归位 components/notebook/（partners 详情页同源依赖）；相对深度由父级校正。
import PickerShell from "../../pages/tutor/h5/h5shared/PickerShell";
import PickerHeader from "../../pages/tutor/h5/h5shared/PickerHeader";
import {
  listNotebooks,
  type NotebookSummary as RealNotebookSummary,
} from "../../pages/tutor/admin/notebook-api";

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const CARD = "var(--card, #ffffff)";
const MUTED = "var(--muted, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";
const PRIMARY_FG = "var(--primary-foreground, #ffffff)";
const DESTRUCTIVE = "var(--destructive, #dc2626)";

type RecordType =
  | "solve"
  | "question"
  | "research"
  | "chat"
  | "co_writer"
  | "tutorbot";

export interface NotebookSavePayload {
  recordType: RecordType;
  title: string;
  userQuery: string;
  output: string;
  metadata?: Record<string, unknown>;
  kbName?: string | null;
}

export interface NotebookSaveMessage {
  role: "user" | "assistant" | "system";
  content: string;
  capability?: string;
}

interface SaveToNotebookModalProps {
  open: boolean;
  payload: NotebookSavePayload | null;
  /**
   * Optional list of chat messages. When provided, the modal switches to
   * "selection mode" and lets the user pick which messages to include in the
   * saved notebook record. The transcript / userQuery in the final request
   * are rebuilt from the selected subset, while other fields (recordType,
   * metadata, kbName) come from `payload`.（原仓注释逐字保留）
   */
  messages?: NotebookSaveMessage[] | null;
  onClose: () => void;
  onSaved?: (result: { summary: string }) => void;
}

function parseSseEvents(
  buffer: string,
): Array<{ payload: Record<string, unknown> }> {
  const events: Array<{ payload: Record<string, unknown> }> = [];
  const chunks = buffer.split("\n\n");
  for (let i = 0; i < chunks.length - 1; i += 1) {
    const lines = chunks[i]
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    const dataLine = lines.find((line) => line.startsWith("data:"));
    if (!dataLine) continue;
    try {
      const payload = JSON.parse(dataLine.slice(5).trim()) as Record<
        string,
        unknown
      >;
      events.push({ payload });
    } catch {
      continue;
    }
  }
  return events;
}

function roleLabelKey(role: NotebookSaveMessage["role"]): string {
  if (role === "user") return "用户";
  if (role === "assistant") return "助手";
  return "系统";
}

function buildTranscript(messages: NotebookSaveMessage[]): string {
  return messages
    .map((msg) => {
      const role =
        msg.role === "user" ? "用户" : msg.role === "assistant" ? "助手" : "系统";
      return `## ${role}\n${msg.content}`;
    })
    .join("\n\n");
}

function buildUserQuery(messages: NotebookSaveMessage[]): string {
  return messages
    .filter((msg) => msg.role === "user")
    .map((msg) => msg.content)
    .join("\n\n");
}

function deriveTitle(
  messages: NotebookSaveMessage[],
  fallback: string,
): string {
  const firstUser = messages.find((msg) => msg.role === "user");
  const candidate = firstUser?.content.trim();
  if (!candidate) return fallback;
  return candidate.slice(0, 80);
}

/**
 * Compute the indexes of the most recent N "turns". A turn is loosely
 * defined as a user message plus any assistant/system messages that follow
 * it until the next user message. When N exceeds the available turn count
 * we just return all message indexes.（原仓注释逐字保留）
 */
function indexesForLastTurns(
  messages: NotebookSaveMessage[],
  turnCount: number,
): number[] {
  if (messages.length === 0 || turnCount <= 0) return [];
  const userPositions: number[] = [];
  messages.forEach((msg, idx) => {
    if (msg.role === "user") userPositions.push(idx);
  });
  if (userPositions.length === 0) {
    return messages.map((_, idx) => idx);
  }
  const startUserIdx = Math.max(0, userPositions.length - turnCount);
  const startMessageIdx = userPositions[startUserIdx];
  const result: number[] = [];
  for (let i = startMessageIdx; i < messages.length; i += 1) result.push(i);
  return result;
}

// 消息选择 chip / 笔记本条目的 hover 直写辅助（本仓先例：onMouseEnter/Leave）。
function hoverBg(e: ReactMouseEvent<HTMLElement>, on: boolean): void {
  e.currentTarget.style.background = on ? `${MUTED}66` : CARD;
  e.currentTarget.style.borderColor = on ? `${PRIMARY}66` : "transparent";
}

export default function SaveToNotebookModal({
  open,
  payload,
  messages,
  onClose,
  onSaved,
}: SaveToNotebookModalProps) {
  const [notebooks, setNotebooks] = useState<RealNotebookSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [titleEdited, setTitleEdited] = useState(false);
  const [summaryPreview, setSummaryPreview] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingNotebooks, setIsLoadingNotebooks] = useState(false);
  const [error, setError] = useState("");
  const [selectedMessageIdx, setSelectedMessageIdx] = useState<Set<number>>(
    new Set(),
  );
  const abortRef = useRef<AbortController | null>(null);

  const hasMessageSelection = Array.isArray(messages) && messages.length > 0;

  useEffect(() => {
    if (!open) {
      abortRef.current?.abort();
      return;
    }
    setSummaryPreview("");
    setError("");
    setSelectedIds([]);
    setTitleEdited(false);
    if (hasMessageSelection && messages) {
      setSelectedMessageIdx(new Set(messages.map((_, idx) => idx)));
      setTitle(deriveTitle(messages, payload?.title || ""));
    } else {
      setSelectedMessageIdx(new Set());
      setTitle(payload?.title || "");
    }
    setIsLoadingNotebooks(true);
    void (async () => {
      try {
        const list = await listNotebooks();
        setNotebooks(list);
      } catch {
        setNotebooks([]);
      } finally {
        setIsLoadingNotebooks(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 原仓依赖数组逐字保留
  }, [open, payload, messages, hasMessageSelection]);

  const orderedSelectedMessages = useMemo<NotebookSaveMessage[]>(() => {
    if (!hasMessageSelection || !messages) return [];
    const indexes = Array.from(selectedMessageIdx).sort((a, b) => a - b);
    return indexes
      .map((idx) => messages[idx])
      .filter((msg): msg is NotebookSaveMessage => Boolean(msg));
  }, [hasMessageSelection, messages, selectedMessageIdx]);

  // When the user hasn't manually edited the title yet, keep it in sync
  // with the first selected user message so it stays meaningful as the
  // selection changes.（原仓注释逐字保留）
  useEffect(() => {
    if (!open || !hasMessageSelection || titleEdited) return;
    const next = deriveTitle(orderedSelectedMessages, payload?.title || "");
    setTitle(next);
  }, [
    open,
    hasMessageSelection,
    titleEdited,
    orderedSelectedMessages,
    payload?.title,
  ]);

  const effectiveOutput = useMemo(() => {
    if (hasMessageSelection) {
      return buildTranscript(orderedSelectedMessages);
    }
    return payload?.output || "";
  }, [hasMessageSelection, orderedSelectedMessages, payload?.output]);

  const effectiveUserQuery = useMemo(() => {
    if (hasMessageSelection) {
      return buildUserQuery(orderedSelectedMessages);
    }
    return payload?.userQuery || "";
  }, [hasMessageSelection, orderedSelectedMessages, payload?.userQuery]);

  const canSave = useMemo(
    () =>
      Boolean(
        payload &&
        title.trim() &&
        selectedIds.length > 0 &&
        effectiveOutput.trim() &&
        (!hasMessageSelection || orderedSelectedMessages.length > 0),
      ),
    [
      payload,
      title,
      selectedIds.length,
      effectiveOutput,
      hasMessageSelection,
      orderedSelectedMessages.length,
    ],
  );

  const toggleNotebook = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const toggleMessage = (idx: number) => {
    setSelectedMessageIdx((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  const selectAllMessages = () => {
    if (!messages) return;
    setSelectedMessageIdx(new Set(messages.map((_, idx) => idx)));
  };

  const clearMessages = () => {
    setSelectedMessageIdx(new Set());
  };

  const selectLastTurns = (turnCount: number) => {
    if (!messages) return;
    setSelectedMessageIdx(new Set(indexesForLastTurns(messages, turnCount)));
  };

  const handleSave = async () => {
    if (!payload || !canSave) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);
    setError("");
    setSummaryPreview("");

    const metadata: Record<string, unknown> = { ...(payload.metadata || {}) };
    if (hasMessageSelection && messages) {
      metadata.message_count = orderedSelectedMessages.length;
      metadata.total_message_count = messages.length;
      metadata.selected_message_indexes = Array.from(selectedMessageIdx).sort(
        (a, b) => a - b,
      );
    }

    try {
      const response = await fetch(
        "/api/v1/notebook/add_record_with_summary",
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            notebook_ids: selectedIds,
            record_type: payload.recordType,
            title: title.trim(),
            user_query: effectiveUserQuery,
            output: effectiveOutput,
            metadata,
            kb_name: payload.kbName || null,
          }),
          signal: controller.signal,
        },
      );

      if (!response.ok || !response.body) {
        throw new Error("保存到 Notebook 失败。");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalSummary = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lastSeparator = buffer.lastIndexOf("\n\n");
        if (lastSeparator === -1) continue;

        const consumable = buffer.slice(0, lastSeparator + 2);
        buffer = buffer.slice(lastSeparator + 2);

        for (const event of parseSseEvents(consumable)) {
          const type = String(event.payload.type || "");
          if (type === "summary_chunk") {
            const chunk = String(event.payload.content || "");
            finalSummary += chunk;
            setSummaryPreview(finalSummary);
          } else if (type === "error") {
            throw new Error(
              String(event.payload.detail || "保存到 Notebook 失败。"),
            );
          } else if (type === "result") {
            const summary = String(event.payload.summary || finalSummary);
            setSummaryPreview(summary);
            onSaved?.({ summary });
            setIsLoading(false);
            onClose();
            return;
          }
        }
      }

      throw new Error("Notebook 保存流意外中断。");
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(
        err instanceof Error ? err.message : "保存到 Notebook 失败。",
      );
      setIsLoading(false);
    }
  };

  // payload may be null while the parent is preparing the save context.
  // Treat that as "not open" so the shell never renders without content.
  //（原仓注释逐字保留）
  const isOpen = open && !!payload;

  const totalMessages = messages?.length ?? 0;
  const selectedMessageCount = selectedMessageIdx.size;
  const allMessagesSelected =
    totalMessages > 0 && selectedMessageCount === totalMessages;

  const chipStyle: CSSProperties = {
    borderRadius: 6,
    border: `1px solid ${BORDER}`,
    background: CARD,
    padding: "4px 10px",
    fontSize: 11,
    fontWeight: 500,
    color: MUTED_FG,
    cursor: "pointer",
    transition: "border-color 150ms, color 150ms, background-color 150ms",
  };

  return (
    <PickerShell
      open={isOpen}
      onClose={onClose}
      labelledBy="save-to-notebook-title"
      zIndex={80}
      className="p-4 backdrop-blur-md"
      backdropClass="rgba(255, 255, 255, 0.65)"
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          maxHeight: "90vh",
          width: "100%",
          maxWidth: 672,
          overflow: "hidden",
          borderRadius: 16,
          border: `1px solid ${BORDER}`,
          background: CARD,
          color: FG,
          boxShadow: "0 22px 70px rgba(0, 0, 0, 0.18)",
        }}
      >
        <PickerHeader
          icon={FormOutlined}
          titleId="save-to-notebook-title"
          title={"保存到笔记本"}
          subtitle={
            hasMessageSelection
              ? "选择要包含的消息，挑选一个或多个笔记本，系统将自动生成摘要。"
              : "选择一个或多个笔记本，系统将自动生成摘要。"
          }
          onClose={onClose}
        />

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: 20,
            overflowY: "auto",
            padding: 20,
          }}
        >
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 8,
                fontSize: 14,
                fontWeight: 500,
                color: FG,
              }}
            >
              {"标题"}
            </label>
            <input
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setTitleEdited(true);
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = `${PRIMARY}99`;
                e.currentTarget.style.boxShadow = `0 0 0 2px ${PRIMARY}26`;
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = BORDER;
                e.currentTarget.style.boxShadow = "none";
              }}
              style={{
                width: "100%",
                borderRadius: 12,
                border: `1px solid ${BORDER}`,
                background: CARD,
                padding: "10px 16px",
                fontSize: 14,
                color: FG,
                outline: "none",
                transition: "border-color 150ms, box-shadow 150ms",
              }}
            />
          </div>

          {hasMessageSelection && messages && (
            <div>
              <div
                style={{
                  marginBottom: 8,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <label
                  style={{
                    display: "block",
                    fontSize: 14,
                    fontWeight: 500,
                    color: FG,
                  }}
                >
                  {"要包含的消息"}
                </label>
                <span style={{ fontSize: 12, color: MUTED_FG }}>
                  {`已选 ${selectedMessageCount} / ${totalMessages}`}
                </span>
              </div>
              <div
                style={{
                  marginBottom: 8,
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <button
                  type="button"
                  onClick={selectAllMessages}
                  disabled={allMessagesSelected}
                  style={{
                    ...chipStyle,
                    cursor: allMessagesSelected ? "not-allowed" : "pointer",
                    opacity: allMessagesSelected ? 0.5 : 1,
                  }}
                >
                  {"全选"}
                </button>
                <button
                  type="button"
                  onClick={clearMessages}
                  disabled={selectedMessageCount === 0}
                  style={{
                    ...chipStyle,
                    cursor:
                      selectedMessageCount === 0 ? "not-allowed" : "pointer",
                    opacity: selectedMessageCount === 0 ? 0.5 : 1,
                  }}
                >
                  {"清空"}
                </button>
                <button
                  type="button"
                  onClick={() => selectLastTurns(1)}
                  style={chipStyle}
                >
                  {"最近一轮"}
                </button>
                <button
                  type="button"
                  onClick={() => selectLastTurns(3)}
                  style={chipStyle}
                >
                  {"最近三轮"}
                </button>
              </div>
              <div
                style={{
                  maxHeight: 288,
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  overflowY: "auto",
                  borderRadius: 12,
                  border: `1px solid ${BORDER}`,
                  background: CARD,
                  padding: 8,
                }}
              >
                {messages.map((msg, idx) => {
                  const selected = selectedMessageIdx.has(idx);
                  const Icon =
                    msg.role === "user"
                      ? StarOutlined
                      : msg.role === "assistant"
                        ? StarOutlined
                        : MessageOutlined;
                  const preview = msg.content.replace(/\s+/g, " ").trim();
                  const empty = preview.length === 0;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => toggleMessage(idx)}
                      onMouseEnter={(e) => {
                        if (!selected) hoverBg(e, true);
                      }}
                      onMouseLeave={(e) => {
                        if (!selected) hoverBg(e, false);
                      }}
                      style={{
                        display: "flex",
                        width: "100%",
                        alignItems: "flex-start",
                        gap: 12,
                        borderRadius: 8,
                        border: `1px solid ${selected ? `${PRIMARY}66` : "transparent"}`,
                        background: selected ? `${PRIMARY}14` : "transparent",
                        padding: "8px 12px",
                        textAlign: "left",
                        cursor: "pointer",
                        transition: "border-color 150ms, background-color 150ms",
                      }}
                    >
                      <span
                        style={{
                          marginTop: 2,
                          display: "flex",
                          height: 18,
                          width: 18,
                          flexShrink: 0,
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 6,
                          border: `1px solid ${selected ? PRIMARY : BORDER}`,
                          background: selected ? PRIMARY : "transparent",
                          color: selected ? PRIMARY_FG : "transparent",
                        }}
                      >
                        <CheckOutlined style={{ fontSize: 12 }} />
                      </span>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div
                          style={{
                            marginBottom: 2,
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            fontSize: 11,
                            fontWeight: 500,
                            color: MUTED_FG,
                          }}
                        >
                          <Icon style={{ fontSize: 12 }} />
                          <span>{roleLabelKey(msg.role)}</span>
                          <span style={{ color: `${MUTED_FG}99` }}>·</span>
                          <span>#{idx + 1}</span>
                        </div>
                        <p
                          style={{
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                            margin: 0,
                            fontSize: 12,
                            lineHeight: "20px",
                            fontStyle: empty ? "italic" : "normal",
                            color: empty ? `${MUTED_FG}b3` : `${FG}d9`,
                          }}
                        >
                          {empty ? "（空消息）" : preview}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div>
            <div
              style={{
                marginBottom: 8,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <label
                style={{
                  display: "block",
                  fontSize: 14,
                  fontWeight: 500,
                  color: FG,
                }}
              >
                {"笔记本"}
              </label>
              {selectedIds.length > 0 && (
                <span style={{ fontSize: 12, color: MUTED_FG }}>
                  {selectedIds.length} {"项已选"}
                </span>
              )}
            </div>
            <div
              style={{
                maxHeight: 256,
                display: "flex",
                flexDirection: "column",
                gap: 8,
                overflowY: "auto",
                borderRadius: 12,
                border: `1px solid ${BORDER}`,
                background: CARD,
                padding: 8,
              }}
            >
              {isLoadingNotebooks ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "32px 12px",
                    color: MUTED_FG,
                  }}
                >
                  <LoadingOutlined style={{ fontSize: 16 }} spin />
                </div>
              ) : notebooks.length === 0 ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 8,
                    padding: "24px 12px",
                    textAlign: "center",
                    fontSize: 14,
                    color: MUTED_FG,
                  }}
                >
                  <FormOutlined
                    style={{ fontSize: 20, color: `${MUTED_FG}99` }}
                  />
                  <span>{"未找到笔记本。"}</span>
                  <span style={{ fontSize: 11, color: `${MUTED_FG}cc` }}>
                    {"可在“知识 → 笔记本”页面创建。"}
                  </span>
                </div>
              ) : (
                notebooks.map((notebook) => {
                  const selected = selectedIds.includes(notebook.id);
                  return (
                    <button
                      key={notebook.id}
                      onClick={() => toggleNotebook(notebook.id)}
                      onMouseEnter={(e) => {
                        if (!selected) hoverBg(e, true);
                      }}
                      onMouseLeave={(e) => {
                        if (!selected) hoverBg(e, false);
                      }}
                      style={{
                        display: "flex",
                        width: "100%",
                        alignItems: "flex-start",
                        gap: 12,
                        borderRadius: 8,
                        border: `1px solid ${selected ? `${PRIMARY}66` : "transparent"}`,
                        background: selected ? `${PRIMARY}14` : "transparent",
                        padding: "10px 12px",
                        textAlign: "left",
                        cursor: "pointer",
                        transition: "border-color 150ms, background-color 150ms",
                      }}
                    >
                      <div
                        style={{
                          marginTop: 4,
                          height: 12,
                          width: 12,
                          flexShrink: 0,
                          borderRadius: 9999,
                          background: notebook.color || PRIMARY,
                        }}
                      />
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: 8,
                          }}
                        >
                          <div
                            style={{
                              fontSize: 14,
                              fontWeight: 500,
                              color: FG,
                            }}
                          >
                            {notebook.name}
                          </div>
                          <span
                            style={{
                              display: "flex",
                              width: 18,
                              height: 18,
                              flexShrink: 0,
                              alignItems: "center",
                              justifyContent: "center",
                              borderRadius: 6,
                              border: `1px solid ${selected ? PRIMARY : BORDER}`,
                              background: selected ? PRIMARY : "transparent",
                              color: selected ? PRIMARY_FG : "transparent",
                              transition: "border-color 150ms, background-color 150ms",
                            }}
                          >
                            <CheckOutlined style={{ fontSize: 12 }} />
                          </span>
                        </div>
                        {notebook.description && (
                          <p
                            style={{
                              marginTop: 4,
                              display: "-webkit-box",
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: "vertical",
                              overflow: "hidden",
                              margin: "4px 0 0",
                              fontSize: 12,
                              color: MUTED_FG,
                            }}
                          >
                            {notebook.description}
                          </p>
                        )}
                        <div
                          style={{
                            marginTop: 4,
                            fontSize: 11,
                            color: `${MUTED_FG}d9`,
                          }}
                        >
                          {notebook.record_count ?? 0} {"条记录"}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div>
            <div style={{ marginBottom: 8, fontSize: 14, fontWeight: 500, color: FG }}>
              {"摘要预览"}
            </div>
            <div
              style={{
                minHeight: 96,
                borderRadius: 12,
                border: `1px solid ${BORDER}`,
                background: CARD,
                padding: "12px 16px",
                fontSize: 14,
                lineHeight: "24px",
                color: `${FG}d9`,
              }}
            >
              {summaryPreview || (
                <span style={{ color: MUTED_FG }}>
                  {"保存时生成的摘要将显示在此处。"}
                </span>
              )}
            </div>
          </div>

          {error && (
            <div
              style={{
                borderRadius: 12,
                border: `1px solid ${DESTRUCTIVE}4d`,
                background: `${DESTRUCTIVE}14`,
                padding: "12px 16px",
                fontSize: 14,
                color: DESTRUCTIVE,
              }}
            >
              {error}
            </div>
          )}
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 8,
            borderTop: `1px solid ${BORDER}`,
            background: CARD,
            padding: "16px 20px",
          }}
        >
          <button
            onClick={onClose}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = MUTED;
              e.currentTarget.style.color = FG;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.color = MUTED_FG;
            }}
            style={{
              borderRadius: 12,
              padding: "8px 16px",
              fontSize: 14,
              color: MUTED_FG,
              background: "transparent",
              border: "none",
              cursor: "pointer",
              transition: "background-color 150ms, color 150ms",
            }}
          >
            {"取消"}
          </button>
          <button
            onClick={handleSave}
            disabled={!canSave || isLoading}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              borderRadius: 12,
              background: PRIMARY,
              padding: "8px 16px",
              fontSize: 14,
              fontWeight: 500,
              color: PRIMARY_FG,
              border: "none",
              cursor: !canSave || isLoading ? "not-allowed" : "pointer",
              opacity: !canSave || isLoading ? 0.5 : 1,
            }}
          >
            {isLoading && <LoadingOutlined style={{ fontSize: 16 }} spin />}
            {"保存"}
          </button>
        </div>
      </div>
    </PickerShell>
  );
}
