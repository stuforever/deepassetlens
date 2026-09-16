/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/HistorySessionPicker.tsx，397 行）。
 * 替换点：删除 "use client"；lucide Check/History/Loader2/MessageSquare/Search/
 * Sparkles/UserRound→CheckOutlined/HistoryOutlined/LoadingOutlined(spin)/
 * MessageOutlined/SearchOutlined/StarOutlined/UserOutlined；PickerShell/
 * PickerHeader→本目录件；session-api→../../admin/session-api（批8 件，
 * listSessions(limit,offset,{force})/getSession 契约一致）；message-content→
 * ./messageContent（SA-D 批件，normalizeMessageContent/truncateText 同名同签）；
 * Tailwind→内联样式（md: 断点在 tupu 单列容器内降级为左列固定 42%/380px 宽）；
 * t() 译文命中 zh/app.json 直出（"Select History Sessions"→选择历史会话、
 * "Search sessions by title or last message"→按标题或最后一条消息搜索会话、
 * "Clear"→清空、"Untitled session"→未命名会话、"messages"→条消息、
 * "No matching sessions found."→未找到匹配的会话。、"No messages in this session."
 * →该会话暂无消息。、"Select a session to preview it here."→选择一个会话，在此预览
 * 内容。、"You"→你、"Assistant"→助手、"Choose one or more past conversations to
 * analyze before this turn."→在本轮对话前，选择一个或多个历史会话作为参考。），
 * "Selected"/"Loading preview…"/计数与按钮键未命中按 i18next 回退直出原 key。
 * 悬停预览/懒加载/缓存逐字未改。
 */
import { useEffect, useMemo, useRef, useState } from "react";
import {
  CheckOutlined,
  HistoryOutlined,
  LoadingOutlined,
  MessageOutlined,
  SearchOutlined,
  StarOutlined,
  UserOutlined,
} from "@ant-design/icons";
import PickerShell from "./PickerShell";
import PickerHeader from "./PickerHeader";
import {
  getSession,
  listSessions,
  type SessionDetail,
  type SessionSummary,
} from "../../admin/session-api";
import { normalizeMessageContent, truncateText } from "./messageContent";
import { DT, ellipsis } from "./dtStyle";

export interface SelectedHistorySession {
  sessionId: string;
  title: string;
}

interface HistorySessionPickerProps {
  open: boolean;
  onClose: () => void;
  onApply: (sessions: SelectedHistorySession[]) => void;
}

/**
 * Format a backend session timestamp (stored as float seconds via time.time())
 * into a localized string. Returns an empty string when the timestamp is
 * missing or non-positive so we don't render nonsensical 1970 dates.
 */
function formatSessionTimestamp(value?: number): string {
  if (!value || value <= 0) return "";
  // Backend stores REAL seconds. JS Date expects milliseconds.
  return new Date(value * 1000).toLocaleString();
}

function sessionKey(session: SessionSummary): string {
  return session.session_id || session.id;
}

export default function HistorySessionPicker({
  open,
  onClose,
  onApply,
}: HistorySessionPickerProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  // The session shown in the right-hand preview pane. Driven by hover/focus
  // and click so the preview tracks wherever the user's attention is — the
  // list reads like a mail client: glide over a row, see its conversation.
  const [activeId, setActiveId] = useState<string | null>(null);
  // Fetched session transcripts, cached so re-hovering a row is instant.
  const [details, setDetails] = useState<Record<string, SessionDetail>>({});
  const detailsRef = useRef(details);
  useEffect(() => {
    detailsRef.current = details;
  }, [details]);
  const [previewLoadingId, setPreviewLoadingId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;

    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const data = await listSessions(200, 0, { force: true });
        if (!mounted) return;
        setSessions(data);
        // Default the preview to the most recent session so the right pane is
        // never blank on open.
        setActiveId((prev) => {
          if (prev && data.some((s) => sessionKey(s) === prev)) return prev;
          return data.length ? sessionKey(data[0]) : null;
        });
      } catch {
        if (!mounted) return;
        setSessions([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    void load();
    return () => {
      mounted = false;
    };
  }, [open]);

  // Lazily fetch the active session's transcript for the preview pane.
  useEffect(() => {
    if (!open || !activeId) return;
    if (detailsRef.current[activeId]) return;
    let cancelled = false;
    setPreviewLoadingId(activeId);
    getSession(activeId)
      .then((detail) => {
        if (cancelled) return;
        setDetails((prev) => ({ ...prev, [activeId]: detail }));
      })
      .catch(() => {
        /* preview is best-effort; the list still works without it */
      })
      .finally(() => {
        if (cancelled) return;
        setPreviewLoadingId((cur) => (cur === activeId ? null : cur));
      });
    return () => {
      cancelled = true;
    };
  }, [activeId, open]);

  const filteredSessions = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return sessions;
    return sessions.filter((session) => {
      const title = String(session.title || "").toLowerCase();
      const lastMessage = normalizeMessageContent(
        session.last_message,
      ).toLowerCase();
      return title.includes(keyword) || lastMessage.includes(keyword);
    });
  }, [query, sessions]);

  const toggleSession = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const handleApply = () => {
    const selected = sessions
      .filter((session) => selectedIds.includes(sessionKey(session)))
      .map((session) => ({
        sessionId: sessionKey(session),
        title: session.title || "未命名会话",
      }));
    onApply(selected);
    onClose();
  };

  const activeSession = activeId
    ? sessions.find((s) => sessionKey(s) === activeId)
    : undefined;
  const activeDetail = activeId ? details[activeId] : undefined;
  const activeLoading =
    previewLoadingId !== null && previewLoadingId === activeId;

  return (
    <PickerShell
      open={open}
      onClose={onClose}
      labelledBy="history-picker-title"
      backdropClass="rgba(255,255,255,0.65)"
    >
      <div
        style={{
          display: "flex",
          height: "78vh",
          maxHeight: 660,
          width: "100%",
          maxWidth: 896,
          flexDirection: "column",
          overflow: "hidden",
          borderRadius: 16,
          border: `1px solid ${DT.border}`,
          background: DT.card,
          color: DT.foreground,
          boxShadow: "0 22px 70px rgba(0,0,0,0.18)",
        }}
      >
        <PickerHeader
          icon={HistoryOutlined}
          titleId="history-picker-title"
          title={"选择历史会话"}
          subtitle={
            "在本轮对话前，选择一个或多个历史会话作为参考。"
          }
          onClose={onClose}
        />

        <div style={{ display: "flex", minHeight: 0, flex: 1 }}>
          {/* ── Left: searchable, selectable session list ── */}
          <div
            style={{
              display: "flex",
              width: "100%",
              minWidth: 0,
              flexDirection: "column",
              borderRight: `1px solid ${DT.border}`,
              maxWidth: "42%",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "16px 16px 12px" }}>
              <div style={{ position: "relative", flex: 1 }}>
                <SearchOutlined
                  style={{
                    pointerEvents: "none",
                    position: "absolute",
                    left: 12,
                    top: "50%",
                    fontSize: 16,
                    transform: "translateY(-50%)",
                    color: DT.mutedForeground,
                  }}
                />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="按标题或最后一条消息搜索会话"
                  style={{
                    width: "100%",
                    borderRadius: 12,
                    border: `1px solid ${DT.border}`,
                    background: DT.card,
                    padding: "10px 12px 10px 36px",
                    fontSize: 13,
                    color: DT.foreground,
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              {selectedIds.length > 0 && (
                <button
                  onClick={() => setSelectedIds([])}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = DT.muted;
                    e.currentTarget.style.color = DT.foreground;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = DT.card;
                    e.currentTarget.style.color = DT.mutedForeground;
                  }}
                  style={{
                    flexShrink: 0,
                    borderRadius: 12,
                    border: `1px solid ${DT.border}`,
                    background: DT.card,
                    padding: "10px 12px",
                    fontSize: 12,
                    fontWeight: 500,
                    cursor: "pointer",
                    color: DT.mutedForeground,
                    transition: "background-color 150ms, color 150ms",
                  }}
                >
                  清空
                </button>
              )}
            </div>

            <div style={{ minHeight: 0, flex: 1, overflowY: "auto", padding: "0 8px 8px" }}>
              {loading ? (
                <div style={{ minHeight: 280, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <LoadingOutlined spin style={{ fontSize: 20, color: DT.mutedForeground }} />
                </div>
              ) : filteredSessions.length ? (
                <div style={{ display: "flex", flexDirection: "column", rowGap: 2 }}>
                  {filteredSessions.map((session) => {
                    const id = sessionKey(session);
                    const selected = selectedIds.includes(id);
                    const active = id === activeId;
                    return (
                      <button
                        key={id}
                        onClick={() => {
                          toggleSession(id);
                          setActiveId(id);
                        }}
                        onMouseEnter={() => setActiveId(id)}
                        onFocus={() => setActiveId(id)}
                        style={{
                          position: "relative",
                          display: "flex",
                          width: "100%",
                          alignItems: "flex-start",
                          gap: 10,
                          borderRadius: 12,
                          padding: "10px 10px",
                          textAlign: "left",
                          border: "none",
                          cursor: "pointer",
                          background: active
                            ? DT.mutedAlpha(0.6)
                            : selected
                              ? DT.primaryAlpha(0.05)
                              : "transparent",
                          font: "inherit",
                          transition: "background-color 150ms",
                        }}
                      >
                        {/* Accent rail marks the previewed row */}
                        <span
                          style={{
                            position: "absolute",
                            top: 6,
                            bottom: 6,
                            left: 0,
                            width: 2.5,
                            borderRadius: 999,
                            background: DT.primary,
                            transition: "opacity 150ms",
                            opacity: active ? 1 : 0,
                          }}
                        />
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
                            border: `1px solid ${selected ? DT.primary : DT.border}`,
                            background: selected ? DT.primary : "transparent",
                            color: selected ? DT.primaryForeground : "transparent",
                            transition: "background-color 150ms, border-color 150ms",
                          }}
                        >
                          <CheckOutlined style={{ fontSize: 11 }} />
                        </span>
                        <span style={{ minWidth: 0, flex: 1 }}>
                          <span style={{ display: "block", ...ellipsis, fontSize: 13, fontWeight: 500, color: DT.foreground }}>
                            {session.title || "未命名会话"}
                          </span>
                          <span style={{ marginTop: 2, display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: DT.mutedForegroundAlpha(0.85) }}>
                            <MessageOutlined style={{ fontSize: 11 }} />
                            {session.message_count ?? 0} 条消息
                          </span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div style={{ padding: "56px 24px", textAlign: "center", fontSize: 13, color: DT.mutedForeground }}>
                  未找到匹配的会话。
                </div>
              )}
            </div>
          </div>

          {/* ── Right: live preview of the focused session ── */}
          <div style={{ display: "flex", minWidth: 0, flex: 1, flexDirection: "column", background: "rgba(255,255,255,0.3)" }}>
            {activeSession ? (
              <>
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 12,
                    borderBottom: `1px solid ${DT.borderAlpha(0.7)}`,
                    padding: "14px 20px",
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ ...ellipsis, fontSize: 14, fontWeight: 600, color: DT.foreground }}>
                      {activeSession.title || "未命名会话"}
                    </div>
                    <div style={{ marginTop: 2, display: "flex", alignItems: "center", gap: 10, fontSize: 11, color: DT.mutedForeground }}>
                      <span>
                        {activeSession.message_count ?? 0} 条消息
                      </span>
                      {formatSessionTimestamp(
                        activeSession.updated_at || activeSession.created_at,
                      ) && (
                        <span>
                          {formatSessionTimestamp(
                            activeSession.updated_at ||
                              activeSession.created_at,
                          )}
                        </span>
                      )}
                    </div>
                  </div>
                  {selectedIds.includes(activeId!) && (
                    <span
                      style={{
                        display: "inline-flex",
                        flexShrink: 0,
                        alignItems: "center",
                        gap: 4,
                        borderRadius: 999,
                        background: DT.primaryAlpha(0.1),
                        padding: "2px 8px",
                        fontSize: 10,
                        fontWeight: 600,
                        color: DT.primary,
                      }}
                    >
                      <CheckOutlined style={{ fontSize: 10 }} />
                      selected
                    </span>
                  )}
                </div>

                <div style={{ minHeight: 0, flex: 1, overflowY: "auto", padding: "16px 20px" }}>
                  {activeLoading && !activeDetail ? (
                    <div style={{ minHeight: 200, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, fontSize: 12, color: DT.mutedForeground }}>
                      <LoadingOutlined spin style={{ fontSize: 16 }} />
                      Loading preview…
                    </div>
                  ) : activeDetail ? (
                    <ConversationPreview detail={activeDetail} />
                  ) : (
                    <div style={{ minHeight: 200, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, color: DT.mutedForeground }}>
                      该会话暂无消息。
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8, padding: "0 32px", textAlign: "center", color: DT.mutedForeground }}>
                <HistoryOutlined style={{ fontSize: 24, opacity: 0.4 }} />
                <p style={{ margin: 0, fontSize: 12 }}>
                  选择一个会话，在此预览内容。
                </p>
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, borderTop: `1px solid ${DT.border}`, padding: "14px 20px" }}>
          <div style={{ fontSize: 12, color: DT.mutedForeground }}>
            {selectedIds.length === 1
              ? "1 session selected"
              : `${selectedIds.length} sessions selected`}
          </div>
          <button
            onClick={handleApply}
            disabled={!selectedIds.length}
            style={{
              borderRadius: 12,
              border: "none",
              cursor: !selectedIds.length ? "not-allowed" : "pointer",
              background: DT.primary,
              padding: "10px 16px",
              fontSize: 13,
              fontWeight: 500,
              color: DT.primaryForeground,
              opacity: !selectedIds.length ? 0.4 : 1,
              transition: "opacity 150ms",
              font: "inherit",
            }}
          >
            {`Use Selected Sessions (${selectedIds.length})`}
          </button>
        </div>
      </div>
    </PickerShell>
  );
}

/**
 * Read-only transcript rendering for the preview pane. We render the stored
 * final `content` of each message (not the streaming trace) as plain,
 * role-labelled text — enough to recognize a conversation at a glance without
 * pulling in the full markdown/KaTeX renderer.
 */
function ConversationPreview({ detail }: { detail: SessionDetail }) {
  const turns = useMemo(
    () =>
      (detail.messages || [])
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({
          id: m.id,
          role: m.role,
          text: truncateText(normalizeMessageContent(m.content), 1400),
        }))
        .filter((m) => m.text.trim().length > 0),
    [detail.messages],
  );

  if (turns.length === 0) {
    return (
      <div style={{ minHeight: 200, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, color: DT.mutedForeground }}>
        该会话暂无消息。
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", rowGap: 16 }}>
      {turns.map((turn) => {
        const isUser = turn.role === "user";
        return (
          <div key={turn.id}>
            <div style={{ marginBottom: 4, display: "flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 500, color: DT.mutedForeground }}>
              {isUser ? (
                <UserOutlined style={{ fontSize: 12 }} />
              ) : (
                <StarOutlined style={{ fontSize: 12 }} />
              )}
              {isUser ? "你" : "助手"}
            </div>
            <div
              style={{
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontSize: 12.5,
                lineHeight: 1.625,
                color: "rgba(0,0,0,0.85)",
              }}
            >
              {turn.text}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// 具名再导出：批9 SA-A FollowupChatComposer 以 lazy(() => import(...).then((m) => ({ default: m.HistorySessionPicker }))) 消费（桌面原件仅 default 导出，此为批内契约对齐，非新逻辑）。
export { HistorySessionPicker };
