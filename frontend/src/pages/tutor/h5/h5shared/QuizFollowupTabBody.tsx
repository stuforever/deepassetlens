/**
 * 复刻自 DeepTutor 原仓 web/components/quiz/QuizFollowupTabBody.tsx（整件 1:1）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. MarkdownRenderer → 批8 admin/MarkdownRenderer.tsx；useSmoothStreamText →
 *    批8 admin/useSmoothStreamText.ts；getSession → 批8 admin/session-api.ts；
 * 3. FollowupChatComposer → ./FollowupChatComposer；AskUserOptions →
 *    ./AskUserOptions（同批移植）；QuizFollowupContext → ./QuizFollowupContext；
 *    StreamEvent → 批8 admin/unified-ws.ts；
 * 4. StreamingStatus / TraceFlow 来自 TracePanels（波次2 SA-F 交付：
 *    h5shared/TracePanels.tsx 具名导出，登记见收尾报告）；
 * 5. lucide Sparkles → @ant-design/icons ThunderboltOutlined（antd 无 sparkle）；
 * 6. i18n t() → 中文直出（译自原仓 locales/zh/app.json 逐键核对）；
 * 7. apiUrl(url) → url（剥掉透传）；Tailwind → 内联样式（Snow 亮色常量，
 *    dark: 变体裁剪）；图片栅格响应式经组件级 <style> 承接。
 */
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
} from "react";
import { ThunderboltOutlined } from "@ant-design/icons";
import MarkdownRenderer from "../../admin/MarkdownRenderer";
import FollowupChatComposer from "./FollowupChatComposer";
import { AskUserOptions, extractMessageSegments } from "./AskUserOptions";
import { StreamingStatus, TraceFlow } from "./TracePanels";
import { useSmoothStreamText } from "../../admin/useSmoothStreamText";
import {
  type QuizFollowupTabContext,
  useFollowupThread,
  useQuizFollowupController,
} from "./QuizFollowupContext";
import { getSession } from "../../admin/session-api";
import type { StreamEvent } from "../../admin/unified-ws";

// Snow 亮色主题 CSS 变量取值（本文件局部对位用）。
const FG = "#0f172a";
const MUTED_FG = "#64748b";
const PRIMARY = "#4f46e5";
const CARD = "#ffffff";
const BORDER = "#e2e8f0";
const BG = "#f8fafc";

const QuizFollowupTabBodyStyleBlock = () => (
  <style>{`
.qf-imggrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;}
@media(min-width:640px){.qf-imggrid{grid-template-columns:repeat(4,minmax(0,1fr));}}
@media(min-width:768px){.qf-imggrid{grid-template-columns:repeat(5,minmax(0,1fr));}}
  `}</style>
);

/** Resolve a possibly-relative AttachmentStore URL to an absolute one. */
function resolveImageSrc(url: string | null | undefined): string {
  if (!url) return "";
  if (/^(https?:|data:|blob:)/i.test(url)) return url;
  return url;
}

interface QuizFollowupTabBodyProps {
  context: QuizFollowupTabContext;
}

export default function QuizFollowupTabBody({
  context,
}: QuizFollowupTabBodyProps) {
  const controller = useQuizFollowupController();
  const thread = useFollowupThread(context.questionKey);
  const threadEndRef = useRef<HTMLDivElement | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const shouldFollowRef = useRef(true);

  // Pin-to-bottom autoscroll: direct ``scrollTop = scrollHeight`` in
  // layout phase, no smooth animation. ``scrollIntoView`` with
  // ``behavior: 'smooth'`` was the previous strategy here, but it
  // races against the next-frame layout update during fast streams
  // (the in-flight animation interrupts itself when a new delta
  // lands and grows the container again), producing the visible
  // jitter we're trying to eliminate. The pin pattern matches what
  // ``useChatAutoScroll`` does on the main chat surface so the two
  // surfaces feel identical mid-stream.
  useLayoutEffect(() => {
    if (!shouldFollowRef.current) return;
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [thread.messages, thread.isStreaming]);

  const handleScroll = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    shouldFollowRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }, []);

  // Hydrate prior chat history when the tab opens and the notebook
  // entry has a persisted ``followup_session_id``. Skipped when the
  // in-memory thread is already populated (page reload while the
  // controller still holds state, or the user toggles the tab).
  useEffect(() => {
    const followupSessionId = context.followupSessionId;
    if (!followupSessionId) return;
    if (thread.messages.length > 0 || thread.sessionId) return;
    let cancelled = false;
    const run = async () => {
      try {
        const detail = await getSession(followupSessionId);
        if (cancelled || !detail) return;
        const hydrated = (detail.messages ?? []).map((m) => ({
          role: m.role,
          content: m.content || "",
          events: m.events ?? [],
        }));
        controller.hydrateThread(
          context.questionKey,
          followupSessionId,
          hydrated,
        );
      } catch {
        /* best-effort — leave the thread empty so the user can re-ask */
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [
    context.followupSessionId,
    context.questionKey,
    controller,
    thread.messages.length,
    thread.sessionId,
  ]);

  const visibleMessages = thread.messages.filter((m) => m.role !== "system");
  const isCoding = context.question.question_type === "coding";

  return (
    <div style={{ display: "flex", height: "100%", flexDirection: "column", background: CARD }}>
      <QuizFollowupTabBodyStyleBlock />
      {/* Header strip — mimics a chat-page title bar but with quiz crumbs. */}
      <div
        style={{
          display: "flex", flexShrink: 0, alignItems: "center", gap: 8,
          borderBottom: "1px solid rgba(226,232,240,.4)", background: CARD,
          padding: "10px 16px",
        }}
      >
        <div
          style={{
            display: "flex", height: 28, width: 28, flexShrink: 0,
            alignItems: "center", justifyContent: "center", borderRadius: 6,
            background: "rgba(79,70,229,.12)",
          }}
        >
          <ThunderboltOutlined
            style={{ fontSize: 13, color: PRIMARY, fontWeight: 300 }}
          />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              fontSize: 12.5, fontWeight: 600, color: FG,
            }}
          >
            {context.tabLabel}
          </div>
          <div
            style={{
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              fontSize: 10, textTransform: "uppercase", letterSpacing: "0.025em",
              color: MUTED_FG,
            }}
          >
            {"追问对话"}
            {context.question.question_type
              ? ` · ${context.question.question_type}`
              : ""}
          </div>
        </div>
      </div>

      {/* Scrollable body: pinned context + chat thread.
          ``data-chat-scroll-root`` opts this surface into the global
          ``overflow-anchor: none`` + ``scroll-behavior: auto`` rule
          (see app/globals.css) so the manual pin isn't fought by the
          browser's built-in scroll anchoring. */}
      <div
        ref={scrollerRef}
        onScroll={handleScroll}
        data-chat-scroll-root="true"
        style={{ flex: 1, overflowY: "auto", padding: "12px 16px" }}
      >
        <div
          style={{
            margin: "0 auto", maxWidth: 640, display: "flex",
            flexDirection: "column", gap: 12,
          }}
        >
          <div
            style={{
              borderRadius: 6, border: "1px solid rgba(226,232,240,.7)",
              background: "rgba(248,250,252,.7)", padding: "8px 12px",
            }}
          >
            <div
              style={{
                marginBottom: 4, fontSize: 10, fontWeight: 600,
                textTransform: "uppercase", letterSpacing: "0.05em",
                color: MUTED_FG,
              }}
            >
              题目
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.625, color: FG }}>
              <MarkdownRenderer
                content={context.question.question}
                variant="compact"
              />
            </div>
          </div>

          <div
            style={{
              borderRadius: 6, border: "1px solid rgba(226,232,240,.7)",
              background: "rgba(248,250,252,.7)", padding: "8px 12px",
            }}
          >
            <div
              style={{
                marginBottom: 4, fontSize: 10, fontWeight: 600,
                textTransform: "uppercase", letterSpacing: "0.05em",
                color: MUTED_FG,
              }}
            >
              你的答案
            </div>
            {context.userAnswer ? (
              <div style={{ fontSize: 13, lineHeight: 1.625, color: FG }}>
                <MarkdownRenderer
                  content={
                    isCoding &&
                    !context.userAnswer.trimStart().startsWith("```")
                      ? `\`\`\`python\n${context.userAnswer}\n\`\`\``
                      : context.userAnswer
                  }
                  variant="compact"
                />
              </div>
            ) : context.answerImages.length === 0 ? (
              <div style={{ fontSize: 12, fontStyle: "italic", color: MUTED_FG }}>
                暂无文字作答。
              </div>
            ) : null}
            {context.answerImages.length > 0 && (
              <div className="qf-imggrid" style={{ marginTop: 8 }}>
                {context.answerImages.map((image) => {
                  const src = image.previewUrl ?? resolveImageSrc(image.url);
                  return (
                    <div
                      key={image.id}
                      style={{
                        overflow: "hidden", borderRadius: 6,
                        border: `1px solid ${BORDER}`, background: CARD,
                      }}
                    >
                      {src ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={src}
                          alt={image.filename}
                          style={{ height: 64, width: "100%", objectFit: "cover" }}
                        />
                      ) : (
                        <div
                          style={{
                            display: "flex", height: 64, width: "100%",
                            alignItems: "center", justifyContent: "center",
                            fontSize: 10, color: MUTED_FG,
                          }}
                        >
                          {image.filename}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {context.aiJudgment && (
            <div
              style={{
                borderRadius: 6, border: "1px solid rgba(79,70,229,.3)",
                background: "rgba(79,70,229,.04)", padding: "8px 12px",
              }}
            >
              <div
                style={{
                  marginBottom: 4, display: "flex", alignItems: "center", gap: 4,
                  fontSize: 10, fontWeight: 600, textTransform: "uppercase",
                  letterSpacing: "0.05em", color: PRIMARY,
                }}
              >
                <ThunderboltOutlined style={{ fontSize: 10 }} />
                AI 评判
              </div>
              <div style={{ fontSize: 12.5, lineHeight: 1.625, color: FG }}>
                <MarkdownRenderer
                  content={context.aiJudgment}
                  variant="compact"
                />
              </div>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "4px 0" }}>
            {visibleMessages.length === 0 ? (
              <div
                style={{
                  borderRadius: 6, border: `1px dashed ${BORDER}`,
                  background: "rgba(248,250,252,.4)", padding: "12px 12px",
                  fontSize: 12, color: MUTED_FG,
                }}
              >
                对这道题、你的作答或 AI 评判进行任何提问…
              </div>
            ) : (
              visibleMessages.map((message, index) => {
                if (message.role === "user") {
                  return (
                    <div key={`user-${index}`} style={{ display: "flex", justifyContent: "flex-end" }}>
                      <div
                        style={{
                          maxWidth: "88%", whiteSpace: "pre-wrap", wordBreak: "break-word",
                          borderRadius: 14, borderBottomRightRadius: 6,
                          background: PRIMARY, padding: "8px 12px", fontSize: 13,
                          lineHeight: 1.6, color: "#ffffff",
                        }}
                      >
                        {message.content}
                      </div>
                    </div>
                  );
                }
                // Assistant message: render the same inline trace rows the
                // main chat uses (TraceFlow) followed by the message body
                // and the bottom-pinned StreamingStatus row. If
                // the turn paused on ``ask_user``, splice the picker card
                // into the body in stream order — text emitted before the
                // pause sits above the card, text from the resumed
                // iteration sits below.
                const isLast = index === visibleMessages.length - 1;
                const isStreamingThis = isLast && thread.isStreaming;
                return (
                  <AssistantThreadMessage
                    key={`assistant-${index}`}
                    message={message}
                    isStreaming={isStreamingThis}
                    onSubmitUserReply={(reply) =>
                      controller.submitAskUserReply(context.questionKey, reply)
                    }
                  />
                );
              })
            )}
            {thread.error && (
              <div
                style={{
                  borderRadius: 6, border: "1px solid #fecaca", background: "#fef2f2",
                  padding: "4px 8px", fontSize: 11, color: "#b91c1c",
                }}
              >
                {thread.error}
              </div>
            )}
            <div ref={threadEndRef} />
          </div>
        </div>
      </div>

      {/* Composer — the same ChatComposer used on the main chat page,
          wired through FollowupChatComposer to route sends into the
          QuizFollowupController and keep its own state pool. */}
      <div
        style={{
          flexShrink: 0, borderTop: "1px solid rgba(226,232,240,.5)",
          background: CARD, padding: "12px 16px 0",
        }}
      >
        <FollowupChatComposer context={context} />
      </div>
    </div>
  );
}

/**
 * Per-assistant-message renderer for the follow-up thread. Splits the
 * event stream into ordered text + ``ask_user`` segments so the picker
 * card lives inline with the surrounding narration — mirroring the
 * default chat surface's behaviour from ``ChatMessages``.
 */
function AssistantThreadMessage({
  message,
  isStreaming,
  onSubmitUserReply,
}: {
  message: {
    role: "user" | "assistant" | "system";
    content: string;
    events?: StreamEvent[];
  };
  isStreaming: boolean;
  onSubmitUserReply: (reply: {
    text?: string;
    answers?: Array<{ questionId: string; text: string }>;
  }) => void;
}) {
  const segments = useMemo(
    () => extractMessageSegments(message.events),
    [message.events],
  );
  const hasInlineAskUser = segments.some((s) => s.kind === "ask_user");
  // Smooth the trailing-text growth via the shared rAF typewriter so
  // the markdown renderer sees a steadily-growing string instead of
  // bursty deltas. Off when ``isStreaming`` is false — the hook
  // short-circuits to a pure pass-through in that case.
  const smoothedContent = useSmoothStreamText(message.content, isStreaming);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <TraceFlow events={message.events ?? []} isStreaming={isStreaming} />
      {hasInlineAskUser ? (
        segments.map((seg) =>
          seg.kind === "text" ? (
            seg.text ? (
              <div
                key={seg.key}
                style={{ fontSize: 13, lineHeight: 1.6, color: FG }}
              >
                <MarkdownRenderer content={seg.text} variant="compact" />
              </div>
            ) : null
          ) : (
            <AskUserOptions
              key={seg.key}
              data={seg.data}
              onSubmit={onSubmitUserReply}
            />
          ),
        )
      ) : smoothedContent ? (
        <div style={{ fontSize: 13, lineHeight: 1.6, color: FG }}>
          <MarkdownRenderer content={smoothedContent} variant="compact" />
        </div>
      ) : null}
      {/* Status row pinned to the bottom of the assistant output. */}
      <StreamingStatus
        events={message.events ?? []}
        isStreaming={isStreaming}
        content={message.content}
      />
    </div>
  );
}
