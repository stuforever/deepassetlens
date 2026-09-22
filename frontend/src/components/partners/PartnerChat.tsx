/**
 * 复刻自 DeepTutor 原仓 web/components/partners/PartnerChat.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文，未收录键保留
 * 英文原文，{{x}} 插值语义一致）；next/dynamic(ssr:false) → React.lazy + <Suspense
 * fallback={null}>（CRA 无 SSR，等价语义）；Tailwind 类逐项换内联样式；滚动容器
 * data-chat-scroll-root="true" 保留并内联 overflowAnchor:"none"（源仓由全局 CSS
 * 提供，本仓无该全局规则）；"use client" 去；next/image 无。
 * 依赖登记：@/components/chat/home/TracePanels → ../chat/home/TracePanels、
 * @/components/common/AssistantResponse → ../common/AssistantResponse（并行批次
 * 1:1 移植件，按源关系 import）；@/hooks/useChatAutoScroll → ../../hooks/
 * useChatAutoScroll（本批 1:1 补件）；@/lib/partners-api、partner-session、
 * chat-export、unified-ws、doc-attachments、stream → ../../lib/*（本批 1:1 补件）。
 * lucide-react→antd 图标登记：Paperclip → PaperClipOutlined。
 *
 * Web chat with a partner over `WS /api/v1/partners/{id}/ws`.
 *
 * The socket forwards every chat-loop StreamEvent verbatim (`stream_event`
 * frames carry the backend event's `to_dict()`, which IS the frontend
 * `StreamEvent` shape), so this reuses product chat's rendering wholesale:
 * `AssistantActivity` shows the live thinking/tool trace (open while
 * working, collapsed once answered) and the answer text is recomputed with
 * the same narration-demotion rules as chat.
 */

import {
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { PaperClipOutlined } from "@ant-design/icons";
import { wsUrl } from "../../lib/api";
import {
  archivePartnerSession,
  branchPartnerSession,
  deletePartnerSession,
  getPartnerHistory,
  getPartnerSessions,
  resumePartnerSession,
} from "../../lib/partners-api";
import { freshPartnerSessionKey } from "../../lib/partner-session";
import type { ExportableMessage } from "../../lib/chat-export";
import type { StreamEvent } from "../../lib/unified-ws";
import { docIconFor, formatBytes, isSvgFilename } from "../../lib/doc-attachments";
import {
  isNarrationMarker,
  recomputeAnswerContent,
  shouldAppendEventContent,
} from "../../lib/stream";
import { useChatAutoScroll } from "../../hooks/useChatAutoScroll";
import { AssistantActivity } from "../chat/home/TracePanels";
import {
  PartnerComposer,
  type PartnerPendingAttachment,
} from "./PartnerComposer";
import PartnerAvatar from "./PartnerAvatar";

const AssistantResponse = lazy(
  () => import("../common/AssistantResponse"),
);

const ZH_MESSAGES: Record<string, string> = {
  "Branched — the original is archived as {{id}}":
    "已分支——原对话已归档为 {{id}}",
  "Nothing to branch yet.": "暂时没有可分支的内容。",
  "Usage: /resume <session ID>": "用法：/resume <会话 ID>",
  "Session not found": "未找到该会话",
  "Usage: /delete <session ID>": "用法：/delete <会话 ID>",
  "Conversation deleted": "对话已删除",
  Archived: "已归档",
  "New conversation": "新对话",
  "Conversations:": "对话列表：",
  "Use /resume <session ID> or /delete <session ID>.":
    "使用 /resume <会话 ID> 或 /delete <会话 ID>。",
  "Please analyze the attached image(s).": "请分析附件中的图片。",
  "Please use the attached file(s).": "请结合附件文件回答。",
  "Say hello — this conversation shares the same memory your partner has on its connected channels.":
    "打个招呼吧——这里与伙伴在各频道上的对话共享同一份记忆。",
  "Partner is stopped. Start it before chatting.":
    "伙伴已停止。请先启动后再聊天。",
  "Connecting…": "连接中…",
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

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  attachments?: PartnerMessageAttachment[];
  /** Full turn event stream (live turns only; restored history has none). */
  events?: StreamEvent[];
  error?: boolean;
}

interface PartnerMessageAttachment {
  type: string;
  filename: string;
  mimeType?: string;
  size?: number;
  previewUrl?: string;
}

// Commands the web client handles itself (they change client state — the
// active session, or the in-flight turn — which a server text reply can't do).
const CLIENT_COMMANDS = new Set([
  "/new",
  "/clear",
  "/branch",
  "/resume",
  "/delete",
  "/sessions",
  "/stop",
]);

function parseClientCommand(
  content: string,
): { command: string; arg: string } | null {
  const trimmed = content.trim();
  if (!trimmed.startsWith("/")) return null;
  const [head, ...rest] = trimmed.split(/\s+/);
  const command = head.toLowerCase();
  if (!CLIENT_COMMANDS.has(command)) return null;
  return { command, arg: rest.join(" ").trim() };
}

function normalizeHistoryEvents(value: unknown): StreamEvent[] | undefined {
  if (!Array.isArray(value) || value.length === 0) return undefined;
  return value as StreamEvent[];
}

function normalizeHistoryAttachments(
  value: unknown,
): PartnerMessageAttachment[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item): PartnerMessageAttachment | null => {
      if (!item || typeof item !== "object") return null;
      const obj = item as Record<string, unknown>;
      const filename = String(obj.filename || "");
      if (!filename) return null;
      const sizeRaw = obj.size;
      return {
        type: String(obj.type || "file"),
        filename,
        mimeType: String(obj.mime_type || obj.mimeType || ""),
        size: typeof sizeRaw === "number" ? sizeRaw : undefined,
      };
    })
    .filter((item): item is PartnerMessageAttachment => item !== null);
}

function sentAttachmentsForMessage(
  attachments: PartnerPendingAttachment[],
): PartnerMessageAttachment[] {
  return attachments.map((item) => ({
    type: item.type,
    filename: item.filename,
    mimeType: item.mimeType,
    size: item.size,
    previewUrl: item.previewUrl,
  }));
}

function AttachmentStrip({
  attachments,
}: {
  attachments?: PartnerMessageAttachment[];
}) {
  if (!attachments?.length) return null;
  return (
    <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
      {attachments.map((attachment, index) => {
        if (
          (attachment.type === "image" || isSvgFilename(attachment.filename)) &&
          attachment.previewUrl
        ) {
          return (
            <div
              key={`${attachment.filename}-${index}`}
              title={attachment.filename}
              style={{
                height: 56,
                width: 56,
                overflow: "hidden",
                borderRadius: 8,
                border: "1px solid var(--border, #e2e8f0)",
                background: "rgba(241, 245, 249, 0.35)",
              }}
            >
              <img
                src={attachment.previewUrl}
                alt={attachment.filename}
                style={{
                  height: "100%",
                  width: "100%",
                  objectFit: isSvgFilename(attachment.filename)
                    ? "contain"
                    : "cover",
                  padding: isSvgFilename(attachment.filename) ? 4 : 0,
                }}
              />
            </div>
          );
        }

        const spec = docIconFor(attachment.filename);
        const Icon = spec.Icon;
        const sizeLabel = attachment.size ? formatBytes(attachment.size) : "";
        return (
          <div
            key={`${attachment.filename}-${index}`}
            title={attachment.filename}
            style={{
              display: "flex",
              maxWidth: 190,
              alignItems: "center",
              gap: 8,
              borderRadius: 8,
              border: "1px solid var(--border, #e2e8f0)",
              background: "rgba(255, 255, 255, 0.8)",
              padding: "6px 8px",
            }}
          >
            <div
              style={{
                display: "flex",
                height: 28,
                width: 28,
                flexShrink: 0,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 6,
                background: "rgba(241, 245, 249, 0.6)",
              }}
            >
              {attachment.filename ? (
                <Icon style={{ fontSize: 15, color: spec.tint }} />
              ) : (
                <PaperClipOutlined
                  style={{
                    fontSize: 14,
                    color: "var(--muted-foreground, #64748b)",
                  }}
                />
              )}
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontSize: 11,
                  fontWeight: 500,
                  color: "var(--foreground, #0f172a)",
                }}
              >
                {attachment.filename}
              </div>
              <div
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontSize: 9,
                  textTransform: "uppercase",
                  color: "var(--muted-foreground, #64748b)",
                }}
              >
                {sizeLabel ? `${spec.label} · ${sizeLabel}` : spec.label}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function PartnerChat({
  partnerId,
  partnerName,
  emoji,
  color,
  avatar,
  running,
  sessionKey,
  onSessionKeyChange,
  onToast,
  onMessagesChange,
}: {
  partnerId: string;
  partnerName: string;
  emoji?: string;
  color?: string;
  avatar?: string;
  running: boolean;
  /** The active web session key (canonical id), owned by the page so the
   *  Archive tab can switch which conversation the Chat tab is on. */
  sessionKey: string;
  /** Rotate to a different session (new / branch / resume / delete-current). */
  onSessionKeyChange: (key: string) => void;
  onToast?: (message: string) => void;
  /** Lifts the settled conversation up so the page header can export it.
   *  Fires only on discrete message events (send / turn done / clear), not
   *  per streamed token — the live `draft` is intentionally excluded. */
  onMessagesChange?: (messages: ExportableMessage[]) => void;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [connected, setConnected] = useState(false);
  // Live turn snapshot for rendering. The authoritative accumulator is a
  // local variable inside the socket effect (event handlers may mutate it
  // freely); every frame publishes a fresh snapshot object here.
  const [draft, setDraft] = useState<{
    events: StreamEvent[];
    content: string;
  } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  // Mirror the active session into a ref so the socket's onopen (which closes
  // over the effect's first render) attaches to the CURRENT session.
  const sessionKeyRef = useRef(sessionKey);
  sessionKeyRef.current = sessionKey;
  // Attach to an in-flight turn only AFTER history has loaded, so the replay's
  // echoed question + answer aren't clobbered by the history replace. Attach
  // once per socket connection.
  const historyReadyRef = useRef(false);
  const attachedRef = useRef(false);
  const lastMessage = messages[messages.length - 1];
  const {
    containerRef: scrollRef,
    shouldAutoScrollRef,
    scrollToBottom,
    handleScroll,
  } = useChatAutoScroll({
    hasMessages: messages.length > 0 || draft !== null,
    isStreaming: streaming,
    // PartnerComposer sits outside the scrollport and currently exposes no
    // measured-height callback. Sending explicitly re-arms the shared hook
    // below, while streamed content changes drive its normal pin logic.
    composerHeight: 0,
    messageCount: messages.length + (draft ? 1 : 0),
    lastMessageContent: draft?.content ?? lastMessage?.content,
    lastEventCount: draft?.events.length ?? lastMessage?.events?.length,
  });

  const tryAttach = useCallback(() => {
    if (attachedRef.current) return;
    if (!historyReadyRef.current || !sessionKeyRef.current) return;
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;
    attachedRef.current = true;
    wsRef.current.send(
      JSON.stringify({ action: "attach", session_key: sessionKeyRef.current }),
    );
  }, []);

  // Restore the active session's history (scoped to it — the cross-channel
  // "memory feel" is served by the read_memory tool now, not by merging raw
  // transcripts). Re-runs when the page switches the active session (resume /
  // branch). Persisted turn events rehydrate the collapsible "Done" activity.
  useEffect(() => {
    if (!sessionKey) return;
    let cancelled = false;
    historyReadyRef.current = false;
    void getPartnerHistory(partnerId, {
      sessionKey,
      limit: 60,
    })
      .then((history) => {
        if (cancelled) return;
        shouldAutoScrollRef.current = true;
        setMessages(
          history
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({
              role: m.role as "user" | "assistant",
              content: m.content,
              attachments: normalizeHistoryAttachments(
                (m as Record<string, unknown>).attachments,
              ),
              events: normalizeHistoryEvents(
                (m as Record<string, unknown>).events,
              ),
            })),
        );
        historyReadyRef.current = true;
        tryAttach();
        requestAnimationFrame(() => scrollToBottom("instant"));
      })
      .catch(() => {
        historyReadyRef.current = true;
        tryAttach();
      });
    return () => {
      cancelled = true;
    };
  }, [partnerId, sessionKey, scrollToBottom, shouldAutoScrollRef, tryAttach]);

  useEffect(() => {
    if (!running) {
      wsRef.current?.close();
      wsRef.current = null;
      setConnected(false);
      setStreaming(false);
      setDraft(null);
      return;
    }

    attachedRef.current = false;
    const ws = new WebSocket(wsUrl(`/api/v1/partners/${partnerId}/ws`));
    wsRef.current = ws;
    ws.onopen = () => {
      setConnected(true);
      // Reattach to an in-flight turn (survives a page refresh): the server
      // replays its buffered stream, so a mid-answer reload keeps streaming.
      // Sequenced after history load via tryAttach so the replay isn't
      // clobbered by the history replace.
      tryAttach();
    };

    // Authoritative live-turn accumulator. Lives in the effect scope so
    // socket handlers can mutate it cheaply; renders see snapshots only.
    let live: { events: StreamEvent[]; content: string } | null = null;
    const publish = () => {
      setDraft(
        live ? { events: [...live.events], content: live.content } : null,
      );
    };

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data) as {
        type: string;
        content?: string;
        event?: StreamEvent;
      };
      if (data.type === "resuming") {
        // Server is about to replay an in-flight turn (after a refresh).
        live = { events: [], content: "" };
        setStreaming(true);
        publish();
        return;
      }
      if (data.type === "user_echo") {
        // The question that opened the replayed turn (not yet persisted).
        setMessages((msgs) => [
          ...msgs,
          { role: "user", content: data.content ?? "" },
        ]);
        return;
      }
      if (data.type === "stream_event" && data.event) {
        const event = data.event;
        live ??= { events: [], content: "" };
        live.events.push(event);
        if (shouldAppendEventContent(event)) {
          live.content += event.content;
        } else if (isNarrationMarker(event)) {
          // A round resolved as narration — its streamed text belongs to
          // the trace, not the answer. Same demotion rule as product chat.
          live.content = recomputeAnswerContent(live.events);
        }
        publish();
      } else if (data.type === "content") {
        // Authoritative final text from the runner (covers terminator /
        // ask_user fallbacks the client-side recompute can't know about).
        const finished = live;
        live = null;
        setMessages((msgs) => [
          ...msgs,
          {
            role: "assistant",
            content: data.content || finished?.content || "",
            events: finished?.events.length ? finished.events : undefined,
          },
        ]);
        publish();
      } else if (data.type === "done") {
        setStreaming(false);
        live = null;
        publish();
      } else if (data.type === "stopped") {
        // Server cancelled the turn (/stop or the stop button). Keep any
        // partial answer the user already saw; drop the live draft.
        const finished = live;
        live = null;
        if (finished && (finished.content || finished.events.length)) {
          setMessages((msgs) => [
            ...msgs,
            {
              role: "assistant",
              content: finished.content,
              events: finished.events.length ? finished.events : undefined,
            },
          ]);
        }
        setStreaming(false);
        publish();
      } else if (data.type === "proactive") {
        setMessages((msgs) => [
          ...msgs,
          { role: "assistant", content: data.content ?? "" },
        ]);
      } else if (data.type === "error") {
        setMessages((msgs) => [
          ...msgs,
          { role: "assistant", content: data.content ?? "Error", error: true },
        ]);
        live = null;
        publish();
        setStreaming(false);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setStreaming(false);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [partnerId, running, tryAttach]);

  // Report the settled transcript to the parent for header export controls.
  useEffect(() => {
    onMessagesChange?.(
      messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
        attachments: msg.attachments?.map((a) => ({
          type: a.type,
          filename: a.filename,
          mime_type: a.mimeType,
        })),
      })),
    );
  }, [messages, onMessagesChange]);

  const sendStop = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ action: "stop", session_key: sessionKey }),
      );
    }
  }, [sessionKey]);

  // Session-management commands run client-side: they switch the active
  // session or stop the turn — things a server text reply can't do. Returns
  // true when handled (so the caller skips the normal send).
  const runClientCommand = useCallback(
    async (command: string, arg: string): Promise<void> => {
      switch (command) {
        case "/new":
        case "/clear": {
          await archivePartnerSession(partnerId, sessionKey).catch(() => {});
          setMessages([]);
          onSessionKeyChange(freshPartnerSessionKey());
          break;
        }
        case "/branch": {
          const next = freshPartnerSessionKey();
          try {
            await branchPartnerSession(partnerId, sessionKey, next);
            onToast?.(
              t("Branched — the original is archived as {{id}}", {
                id: sessionKey,
              }),
            );
            onSessionKeyChange(next); // history reload picks up the copy
          } catch {
            onToast?.(t("Nothing to branch yet."));
          }
          break;
        }
        case "/resume": {
          if (!arg) {
            onToast?.(t("Usage: /resume <session ID>"));
            break;
          }
          try {
            await resumePartnerSession(partnerId, arg);
            onSessionKeyChange(arg);
          } catch {
            onToast?.(t("Session not found"));
          }
          break;
        }
        case "/delete": {
          if (!arg) {
            onToast?.(t("Usage: /delete <session ID>"));
            break;
          }
          try {
            await deletePartnerSession(partnerId, arg);
            onToast?.(t("Conversation deleted"));
            if (arg === sessionKey) {
              setMessages([]);
              onSessionKeyChange(freshPartnerSessionKey());
            }
          } catch {
            onToast?.(t("Session not found"));
          }
          break;
        }
        case "/sessions": {
          try {
            const sessions = await getPartnerSessions(partnerId);
            const lines = sessions
              .slice(0, 30)
              .map(
                (s) =>
                  `- \`${s.session_key}\`${s.archived ? ` (${t("Archived")})` : ""} — ${
                    s.title || t("New conversation")
                  } · ${s.message_count}`,
              )
              .join("\n");
            setMessages((msgs) => [
              ...msgs,
              {
                role: "assistant",
                content: `${t("Conversations:")}\n${lines}\n\n${t(
                  "Use /resume <session ID> or /delete <session ID>.",
                )}`,
              },
            ]);
            scrollToBottom("instant");
          } catch {
            onToast?.(t("Load failed"));
          }
          break;
        }
        case "/stop": {
          sendStop();
          break;
        }
      }
    },
    [
      partnerId,
      sessionKey,
      onSessionKeyChange,
      onToast,
      scrollToBottom,
      sendStop,
      t,
    ],
  );

  const handleSend = useCallback(
    (content: string, attachments: PartnerPendingAttachment[]) => {
      if (streaming || !running) return;

      // A new user-authored turn explicitly returns to live-follow mode.
      // During the answer, the shared hook releases that mode as soon as the
      // user scrolls upward and only re-arms near the bottom.
      shouldAutoScrollRef.current = true;
      const command =
        attachments.length === 0 ? parseClientCommand(content) : null;
      if (command) {
        void runClientCommand(command.command, command.arg);
        return;
      }

      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      const visibleContent =
        content ||
        (attachments.every((item) => item.type === "image")
          ? t("Please analyze the attached image(s).")
          : t("Please use the attached file(s)."));
      wsRef.current.send(
        JSON.stringify({
          content: visibleContent,
          session_key: sessionKey,
          attachments: attachments.map((item) => ({
            type: item.type,
            filename: item.filename,
            base64: item.base64,
            mime_type: item.mimeType,
          })),
        }),
      );
      setMessages((msgs) => [
        ...msgs,
        {
          role: "user",
          content: visibleContent,
          attachments: sentAttachmentsForMessage(attachments),
        },
      ]);
      setDraft({ events: [], content: "" });
      setStreaming(true);
      scrollToBottom("instant");
    },
    [
      sessionKey,
      running,
      streaming,
      scrollToBottom,
      runClientCommand,
      shouldAutoScrollRef,
      t,
    ],
  );

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        minHeight: 0,
        flexDirection: "column",
      }}
    >
      <div
        ref={scrollRef}
        data-chat-scroll-root="true"
        onScroll={handleScroll}
        style={{
          minHeight: 0,
          flex: 1,
          overflowY: "auto",
          overflowAnchor: "none",
          padding: "16px 4px",
        }}
      >
        {messages.length === 0 && !draft ? (
          <div
            style={{
              display: "flex",
              height: "100%",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              textAlign: "center",
            }}
          >
            <PartnerAvatar
              name={partnerName}
              emoji={emoji}
              color={color}
              image={avatar}
              size={56}
            />
            <div>
              <p
                style={{
                  fontSize: 15,
                  fontWeight: 500,
                  color: "var(--foreground, #0f172a)",
                  margin: 0,
                }}
              >
                {partnerName}
              </p>
              <p
                style={{
                  marginTop: 4,
                  maxWidth: 384,
                  fontSize: 12.5,
                  color: "var(--muted-foreground, #64748b)",
                  margin: "4px auto 0",
                }}
              >
                {running
                  ? t(
                      "Say hello — this conversation shares the same memory your partner has on its connected channels.",
                    )
                  : t("Partner is stopped. Start it before chatting.")}
              </p>
            </div>
          </div>
        ) : (
          <div
            style={{
              maxWidth: 672,
              margin: "0 auto",
              display: "flex",
              flexDirection: "column",
              gap: 20,
            }}
          >
            {messages.map((msg, i) =>
              msg.role === "user" ? (
                <div key={i} style={{ display: "flex", justifyContent: "flex-end" }}>
                  <div
                    style={{
                      maxWidth: "75%",
                      borderRadius: 16,
                      background: "var(--secondary, #f1f5f9)",
                      padding: "10px 16px",
                      fontSize: 14,
                      lineHeight: 1.625,
                      color: "var(--foreground, #0f172a)",
                      boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
                    }}
                  >
                    {msg.content ? (
                      <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
                    ) : null}
                    <AttachmentStrip attachments={msg.attachments} />
                  </div>
                </div>
              ) : (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                  }}
                >
                  <PartnerAvatar
                    name={partnerName}
                    emoji={emoji}
                    color={color}
                    size={26}
                  />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    {msg.events && msg.events.length > 0 && (
                      <AssistantActivity
                        events={msg.events}
                        isStreaming={false}
                        content={msg.content}
                        className="mb-1.5"
                        agentName={partnerName}
                        showMark={false}
                        headerClassName="min-h-[26px]"
                      />
                    )}
                    {msg.error ? (
                      <p
                        style={{
                          fontSize: 13,
                          color: "var(--destructive, #ef4444)",
                          margin: 0,
                        }}
                      >
                        {msg.content}
                      </p>
                    ) : (
                      <Suspense fallback={null}>
                        <AssistantResponse content={msg.content} />
                      </Suspense>
                    )}
                  </div>
                </div>
              ),
            )}

            {draft && (
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                }}
              >
                <PartnerAvatar
                  name={partnerName}
                  emoji={emoji}
                  color={color}
                  size={26}
                />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <AssistantActivity
                    events={draft.events}
                    isStreaming
                    content={draft.content}
                    className="mb-1.5"
                    agentName={partnerName}
                    showMark={false}
                    headerClassName="min-h-[26px]"
                  />
                  {draft.content ? (
                    <Suspense fallback={null}>
                      <AssistantResponse content={draft.content} />
                    </Suspense>
                  ) : null}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div
        style={{
          maxWidth: 672,
          width: "100%",
          margin: "0 auto",
          padding: "0 4px 16px",
        }}
      >
        {!running ? (
          <p
            style={{
              marginBottom: 4,
              textAlign: "center",
              fontSize: 11,
              color: "var(--muted-foreground, #64748b)",
              margin: "0 0 4px",
            }}
          >
            {t("Partner is stopped. Start it before chatting.")}
          </p>
        ) : !connected ? (
          <p
            style={{
              textAlign: "center",
              fontSize: 11,
              color: "var(--muted-foreground, #64748b)",
              margin: "0 0 4px",
            }}
          >
            {t("Connecting…")}
          </p>
        ) : null}
        <PartnerComposer
          onSend={handleSend}
          onStop={sendStop}
          streaming={streaming}
          disabled={!connected || !running}
        />
      </div>
    </div>
  );
}
