/**
 * 复刻自 DeepTutor 原仓 web/components/partners/PartnerArchives.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文；"Load failed" /
 * "Conversations" / "{{count}} session(s)" / "No sessions" / "{{count}} messages" /
 * "Select a conversation" 在 zh 包未收录，保留英文原文）；Tailwind 类逐项换内联样式
 * （hover 用事件直写；line-clamp-2 用 -webkit-box 承载；响应式
 * lg:grid-cols-[280px_1fr] 直接取桌面两列）。
 * lucide-react→antd 图标登记：Archive → InboxOutlined（antd 无归档盒，取收件盒形）；
 * Clock3 → ClockCircleOutlined；MessageSquareText → MessageOutlined；
 * RefreshCw → SyncOutlined（同批5 口径）；RotateCcw → UndoOutlined；
 * Trash2 → DeleteOutlined。
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ClockCircleOutlined,
  DeleteOutlined,
  InboxOutlined,
  MessageOutlined,
  SyncOutlined,
  UndoOutlined,
} from "@ant-design/icons";
import {
  deletePartnerSession,
  getPartnerHistory,
  getPartnerSessions,
  resumePartnerSession,
  type PartnerSessionInfo,
} from "../../lib/partners-api";
import type { ExportableMessage } from "../../lib/chat-export";

const ZH_MESSAGES: Record<string, string> = {
  Refresh: "刷新",
  Archived: "已归档",
  "New conversation": "新对话",
  "No conversations yet": "暂无对话",
  "Archived conversation": "已归档对话",
  "Continue this conversation": "继续这个对话",
  Continue: "继续",
  "Delete conversation": "删除对话",
  "Loading...": "加载中…",
  "Conversation deleted": "对话已删除",
  "Delete failed": "删除失败",
};

function t(key: string, vars?: Record<string, string | number>): string {
  let text = ZH_MESSAGES[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{{${name}}}`).join(String(value));
    }
  }
  return text;
}

interface HistoryMessage {
  role: string;
  content: string;
  timestamp?: string;
  channel?: string;
}

function formatTime(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function PartnerArchives({
  partnerId,
  onToast,
  onMessagesChange,
  onResume,
}: {
  partnerId: string;
  onToast: (message: string) => void;
  /** Lifts the selected conversation up so the page header can export it.
   *  Empty array when nothing is selected (or while loading). */
  onMessagesChange?: (messages: ExportableMessage[]) => void;
  /** Continue a conversation in the Chat tab (un-archives it first). */
  onResume?: (sessionKey: string) => void;
}) {
  const [sessions, setSessions] = useState<PartnerSessionInfo[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [messages, setMessages] = useState<HistoryMessage[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [hoveredSession, setHoveredSession] = useState<string | null>(null);
  const [resumeHover, setResumeHover] = useState(false);
  const [deleteHover, setDeleteHover] = useState(false);

  const selected = useMemo(
    () =>
      sessions.find((session) => session.session_key === selectedKey) ?? null,
    [sessions, selectedKey],
  );

  const loadSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const next = await getPartnerSessions(partnerId);
      setSessions(next);
      setSelectedKey((current) => {
        if (
          current &&
          next.some((session) => session.session_key === current)
        ) {
          return current;
        }
        return next[0]?.session_key ?? "";
      });
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Load failed"));
    } finally {
      setLoadingSessions(false);
    }
  }, [partnerId, onToast, t]);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const handleResume = useCallback(
    async (session: PartnerSessionInfo) => {
      try {
        if (session.archived) {
          await resumePartnerSession(partnerId, session.session_key);
        }
        onResume?.(session.session_key);
      } catch (e) {
        onToast(e instanceof Error ? e.message : t("Load failed"));
      }
    },
    [partnerId, onResume, onToast, t],
  );

  const handleDelete = useCallback(
    async (session: PartnerSessionInfo) => {
      try {
        await deletePartnerSession(partnerId, session.session_key);
        if (selectedKey === session.session_key) setSelectedKey("");
        onToast(t("Conversation deleted"));
        await loadSessions();
      } catch (e) {
        onToast(e instanceof Error ? e.message : t("Delete failed"));
      }
    },
    [partnerId, selectedKey, loadSessions, onToast, t],
  );

  useEffect(() => {
    if (!selectedKey) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingMessages(true);
    void getPartnerHistory(partnerId, { sessionKey: selectedKey, limit: 200 })
      .then((history) => {
        if (!cancelled) setMessages(history);
      })
      .catch((e) => {
        if (!cancelled) {
          setMessages([]);
          onToast(e instanceof Error ? e.message : t("Load failed"));
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingMessages(false);
      });
    return () => {
      cancelled = true;
    };
  }, [partnerId, selectedKey, onToast, t]);

  // Report the selected conversation up for header export controls.
  useEffect(() => {
    if (!onMessagesChange) return;
    if (!selectedKey || loadingMessages) {
      onMessagesChange([]);
      return;
    }
    onMessagesChange(
      messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role, content: m.content })),
    );
  }, [messages, selectedKey, loadingMessages, onMessagesChange]);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "280px minmax(0, 1fr)",
        gap: 16,
        height: "100%",
        minHeight: 0,
      }}
    >
      <div
        style={{
          minHeight: 0,
          borderRight: "1px solid var(--border, #e2e8f0)",
          paddingRight: 16,
          overflowY: "auto",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
            marginBottom: 12,
          }}
        >
          <div>
            <h2
              style={{
                fontSize: 13,
                fontWeight: 500,
                color: "var(--foreground, #0f172a)",
                margin: 0,
              }}
            >
              {t("Conversations")}
            </h2>
            <p
              style={{
                fontSize: 11.5,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {sessions.length
                ? t("{{count}} session(s)", { count: sessions.length })
                : t("No sessions")}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadSessions()}
            disabled={loadingSessions}
            title={t("Refresh")}
            style={{
              display: "inline-flex",
              height: 28,
              width: 28,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 6,
              border: "none",
              background: "transparent",
              color: "var(--muted-foreground, #64748b)",
              cursor: "pointer",
              opacity: loadingSessions ? 0.4 : 1,
            }}
          >
            <SyncOutlined
              spin={loadingSessions}
              style={{ fontSize: 14 }}
            />
          </button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {sessions.map((session) => {
            const active = selectedKey === session.session_key;
            const hovered = hoveredSession === session.session_key;
            return (
              <button
                key={session.session_key}
                type="button"
                onClick={() => setSelectedKey(session.session_key)}
                onMouseEnter={() => setHoveredSession(session.session_key)}
                onMouseLeave={() => setHoveredSession(null)}
                style={{
                  width: "100%",
                  borderRadius: 8,
                  border: `1px solid ${
                    active
                      ? "var(--ring, #2563eb)"
                      : hovered
                        ? "var(--ring, #2563eb)"
                        : "var(--border, #e2e8f0)"
                  }`,
                  background: active ? "var(--muted, #f1f5f9)" : "transparent",
                  padding: "8px 12px",
                  textAlign: "left",
                  cursor: "pointer",
                  transition: "border-color 150ms, background-color 150ms",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {session.archived ? (
                    <InboxOutlined
                      style={{
                        fontSize: 14,
                        flexShrink: 0,
                        color: "var(--muted-foreground, #64748b)",
                      }}
                    />
                  ) : (
                    <MessageOutlined
                      style={{
                        fontSize: 14,
                        flexShrink: 0,
                        color: "var(--muted-foreground, #64748b)",
                      }}
                    />
                  )}
                  <span
                    style={{
                      minWidth: 0,
                      flex: 1,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      fontSize: 12.5,
                      fontWeight: 500,
                      color: "var(--foreground, #0f172a)",
                    }}
                  >
                    {session.title ||
                      (session.archived
                        ? t("Archived")
                        : t("New conversation"))}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      color: "var(--muted-foreground, #64748b)",
                    }}
                  >
                    {session.message_count}
                  </span>
                </div>
                {session.last_message ? (
                  <p
                    style={{
                      marginTop: 4,
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                      fontSize: 11.5,
                      lineHeight: 1.375,
                      color: "var(--muted-foreground, #64748b)",
                      margin: "4px 0 0",
                    }}
                  >
                    {session.last_message}
                  </p>
                ) : null}
                <div
                  style={{
                    marginTop: 4,
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: 10.5,
                    color: "var(--muted-foreground, #64748b)",
                  }}
                >
                  <ClockCircleOutlined style={{ fontSize: 12 }} />
                  {formatTime(session.updated_at)}
                </div>
              </button>
            );
          })}
          {!loadingSessions && sessions.length === 0 ? (
            <div
              style={{
                borderRadius: 8,
                border: "1px dashed var(--border, #e2e8f0)",
                padding: "32px 12px",
                textAlign: "center",
                fontSize: 12,
                color: "var(--muted-foreground, #64748b)",
              }}
            >
              {t("No conversations yet")}
            </div>
          ) : null}
        </div>
      </div>

      <div style={{ minHeight: 0, overflowY: "auto" }}>
        {selected ? (
          <div style={{ maxWidth: 672, margin: "0 auto", paddingBottom: 16 }}>
            <div
              style={{
                position: "sticky",
                top: 0,
                zIndex: 10,
                borderBottom: "1px solid var(--border, #e2e8f0)",
                background: "var(--background, #f6f8fc)",
                padding: "8px 0",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <h3
                    style={{
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      fontSize: 13,
                      fontWeight: 500,
                      color: "var(--foreground, #0f172a)",
                      margin: 0,
                    }}
                  >
                    {selected.title ||
                      (selected.archived
                        ? t("Archived conversation")
                        : t("New conversation"))}
                  </h3>
                  <p
                    style={{
                      fontSize: 11.5,
                      color: "var(--muted-foreground, #64748b)",
                      margin: 0,
                    }}
                  >
                    {(selected.archived ? `${t("Archived")} · ` : "") +
                      formatTime(selected.updated_at)}
                  </p>
                </div>
                <div
                  style={{
                    display: "flex",
                    flexShrink: 0,
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span
                    style={{
                      borderRadius: 6,
                      background: "var(--muted, #f1f5f9)",
                      padding: "4px 8px",
                      fontSize: 11,
                      color: "var(--muted-foreground, #64748b)",
                    }}
                  >
                    {t("{{count}} messages", { count: selected.message_count })}
                  </span>
                  <button
                    type="button"
                    onClick={() => void handleResume(selected)}
                    onMouseEnter={() => setResumeHover(true)}
                    onMouseLeave={() => setResumeHover(false)}
                    title={t("Continue this conversation")}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                      borderRadius: 6,
                      border: "1px solid var(--border, #e2e8f0)",
                      padding: "4px 8px",
                      fontSize: 11,
                      color: "var(--foreground, #0f172a)",
                      background: resumeHover
                        ? "var(--muted, #f1f5f9)"
                        : "transparent",
                      cursor: "pointer",
                      transition: "background-color 150ms",
                    }}
                  >
                    <UndoOutlined style={{ fontSize: 12 }} />
                    {t("Continue")}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete(selected)}
                    onMouseEnter={() => setDeleteHover(true)}
                    onMouseLeave={() => setDeleteHover(false)}
                    title={t("Delete conversation")}
                    style={{
                      display: "inline-flex",
                      height: 26,
                      width: 26,
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: 6,
                      border: "none",
                      color:
                        deleteHover
                          ? "#ef4444"
                          : "var(--muted-foreground, #64748b)",
                      background: deleteHover
                        ? "var(--muted, #f1f5f9)"
                        : "transparent",
                      cursor: "pointer",
                      transition: "background-color 150ms, color 150ms",
                    }}
                  >
                    <DeleteOutlined style={{ fontSize: 14 }} />
                  </button>
                </div>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 16,
                padding: "16px 0",
              }}
            >
              {loadingMessages ? (
                <p
                  style={{
                    fontSize: 12,
                    color: "var(--muted-foreground, #64748b)",
                    margin: 0,
                  }}
                >
                  {t("Loading...")}
                </p>
              ) : (
                messages
                  .filter(
                    (message) =>
                      message.role === "user" || message.role === "assistant",
                  )
                  .map((message, index) => (
                    <div
                      key={`${message.timestamp ?? index}-${index}`}
                      style={{
                        display: "flex",
                        justifyContent:
                          message.role === "user" ? "flex-end" : "flex-start",
                      }}
                    >
                      <div
                        style={{
                          maxWidth: "78%",
                          whiteSpace: "pre-wrap",
                          borderRadius: 8,
                          padding: "8px 12px",
                          fontSize: 13,
                          lineHeight: 1.625,
                          background:
                            message.role === "user"
                              ? "var(--secondary, #f1f5f9)"
                              : "transparent",
                          border:
                            message.role === "user"
                              ? "none"
                              : "1px solid var(--border, #e2e8f0)",
                          color: "var(--foreground, #0f172a)",
                        }}
                      >
                        {message.content}
                      </div>
                    </div>
                  ))
              )}
            </div>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              height: "100%",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 12,
              color: "var(--muted-foreground, #64748b)",
            }}
          >
            {t("Select a conversation")}
          </div>
        )}
      </div>
    </div>
  );
}
