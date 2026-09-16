/**
 * 复刻自 DeepTutor 原仓 web/components/h5/AssistantMessageBody.tsx（整件 1:1）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. next/link Link → react-router-dom Link；路由前缀 /h5/wrongbook →
 *    /e/tutor/h5/wrongbook（tupu h5 复刻路由映射，query 原样保留）；
 * 3. lucide → @ant-design/icons 语义就近：ChevronDown→DownOutlined、
 *    Download→DownloadOutlined、ExternalLink→ExportOutlined、FileText→FileTextOutlined、
 *    Image→PictureOutlined、Film→VideoCameraOutlined、BookOpen→ReadOutlined、
 *    Globe→GlobalOutlined、Newspaper→ProfileOutlined（antd 无报纸图标，文章语义就近）、
 *    CheckCircle2→CheckCircleFilled；
 * 4. AssistantResponse/VisualizationViewer/MathAnimatorViewer → 批8 admin/*；
 *    visualize-types/math-animator-types → 批8 admin/*；quiz-types → ./quizTypes；
 *    QuizViewer → ./QuizViewer（同批移植）；UnifiedChatContext → ./UnifiedChatContext；
 *    StreamEvent → 批8 admin/unified-ws.ts；
 * 5. Tailwind → 内联样式（H5 亮色，Tailwind 调色板 hex 直用）；active: 伪类经组件级
 *    <style> 承接；data-testid 全量保留。
 *
 * H5 助手消息体（M21 A1+A2+A4）——桌面 ChatMessages 能力分支的移动版。
 *
 * 复用桌面同源 lib/组件（铁律 2：不复制桌面组件，UI 移动端新写）：
 * - A1 产物渲染：extractVisualizeResult → VisualizationViewer（SVG/图表/Mermaid/HTML/Manim）、
 *   extractMathAnimatorResult → MathAnimatorViewer、generated 附件 → 产物卡（预览/下载）
 * - A1 deep_solve 阶段：stage_start 事件 → 阶段条 + currentStage 实时态
 * - A2 deep_question：extractQuizQuestions / extractStreamingQuizQuestions / extractQuizTurnId
 *   → QuizViewer（判分/收题/追问，追问面板由页面经 QuizFollowupProvider 提供）
 * - A4 RAG 引用：events 中 metadata.sources（rag/web_search/paper_search）→ 可折叠来源列表
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  DownOutlined,
  DownloadOutlined,
  ExportOutlined,
  FileTextOutlined,
  PictureOutlined,
  VideoCameraOutlined,
  ReadOutlined,
  GlobalOutlined,
  ProfileOutlined,
  CheckCircleFilled,
} from "@ant-design/icons";
import AssistantResponse from "../../admin/AssistantResponse";
import VisualizationViewer from "../../admin/VisualizationViewer";
import MathAnimatorViewer from "../../admin/MathAnimatorViewer";
import QuizViewer from "./QuizViewer";
import { extractVisualizeResult } from "../../admin/visualize-types";
import { extractMathAnimatorResult } from "../../admin/math-animator-types";
import {
  extractQuizQuestions,
  extractQuizTurnId,
  extractStreamingQuizQuestions,
} from "./quizTypes";
import type { MessageItem } from "./UnifiedChatContext";
import type { StreamEvent } from "../../admin/unified-ws";

const STAGE_LABELS: Record<string, string> = {
  planning: "📋 规划",
  reasoning: "🧠 推理",
  writing: "✍️ 撰写",
  exploring: "🔍 探索",
  researching: "📚 研究",
  analyzing: "📊 分析",
  generating: "⚙️ 生成",
  reviewing: "✅ 审查",
  replanning: "🔁 重规划",
  summarizing: "📝 总结",
};

function stageLabel(stage?: string): string {
  if (!stage) return "";
  const key = stage.toLowerCase().replace(/^deep_solve[.:_/]*/, "");
  return STAGE_LABELS[key] || stage;
}

function SourceIcon({ type }: { type: string }) {
  const t = type.toLowerCase();
  if (t.includes("web"))
    return <GlobalOutlined style={{ fontSize: 14, color: "#0ea5e9" }} />;
  if (t.includes("paper"))
    return <ProfileOutlined style={{ fontSize: 14, color: "#8b5cf6" }} />;
  return <ReadOutlined style={{ fontSize: 14, color: "#10b981" }} />;
}

function formatSize(bytes?: number): string {
  if (!bytes || bytes <= 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function AssistantMessageBody({
  msg,
  isStreaming,
  currentStage,
  sessionId,
  u,
  onAgainIntake,
}: {
  msg: MessageItem;
  isStreaming: boolean;
  currentStage?: string;
  sessionId?: string | null;
  /** H5 用户标识（透传给 QuizViewer 追问链路的 provider 由页面统一包） */
  u?: string;
  /** 录错题「再来一道」：由 chat 页传入（填入输入框） */
  onAgainIntake?: () => void;
}) {
  const events: StreamEvent[] = useMemo(() => msg.events ?? [], [msg.events]);
  const [citationsOpen, setCitationsOpen] = useState(false);

  const resultEvent = useMemo(
    () => events.find((e) => e.type === "result") ?? null,
    [events],
  );

  // ---- A1：可视化 / 数学动画产物 ----
  const visualizeResult = useMemo(() => {
    if (msg.capability !== "visualize" || !resultEvent) return null;
    try {
      return extractVisualizeResult(resultEvent.metadata);
    } catch {
      return null;
    }
  }, [msg.capability, resultEvent]);

  const mathAnimatorResult = useMemo(() => {
    if (msg.capability !== "math_animator" || !resultEvent) return null;
    try {
      return extractMathAnimatorResult(resultEvent.metadata);
    } catch {
      return null;
    }
  }, [msg.capability, resultEvent]);

  // ---- A2：深度出题 ----
  const quizQuestions = useMemo(() => {
    if (msg.capability !== "deep_question") return null;
    if (resultEvent) {
      try {
        return extractQuizQuestions(resultEvent.metadata);
      } catch {
        return null;
      }
    }
    try {
      return extractStreamingQuizQuestions(events);
    } catch {
      return null;
    }
  }, [msg.capability, resultEvent, events]);

  const quizTurnId = useMemo(() => {
    if (msg.capability !== "deep_question") return null;
    return extractQuizTurnId(events);
  }, [msg.capability, events]);

  // ---- A1：deep_solve 阶段条（stage_start 事件 + 实时 currentStage） ----
  const stages = useMemo(() => {
    const seen: string[] = [];
    for (const e of events) {
      if (e.type === "stage_start" && e.stage) {
        const label = stageLabel(e.stage);
        if (label && !seen.includes(label)) seen.push(label);
      }
    }
    return seen;
  }, [events]);

  // ---- A1：助手生成的文件产物 ----
  const artifacts = useMemo(
    () => (msg.attachments || []).filter((a) => a.generated && (a.url || a.base64)),
    [msg.attachments],
  );

  // ---- A4：引用来源（rag / web_search / paper_search 的 metadata.sources） ----
  const citations = useMemo(() => {
    const out: { title: string; type: string; query?: string; url?: string }[] = [];
    const seen = new Set<string>();
    for (const e of events) {
      const meta = (e.metadata ?? {}) as Record<string, unknown>;
      const sources = meta.sources;
      if (!Array.isArray(sources)) continue;
      for (const s of sources) {
        if (!s || typeof s !== "object") continue;
        const rec = s as Record<string, unknown>;
        const title = String(rec.title || rec.query || rec.type || "").trim();
        if (!title) continue;
        const key = `${title}|${String(rec.url || "")}`;
        if (seen.has(key)) continue;
        seen.add(key);
        out.push({
          title,
          type: String(rec.type || "rag"),
          query: rec.query ? String(rec.query) : undefined,
          url: rec.url ? String(rec.url) : undefined,
        });
      }
    }
    return out.slice(0, 12);
  }, [events]);

  const hasQuiz = quizQuestions && quizQuestions.length > 0;
  const showDefaultText = !visualizeResult && !mathAnimatorResult && !hasQuiz;

  // ---- M24：wrong_intake 保存成功卡 ----
  const wrongSaved = useMemo(() => {
    if (msg.capability !== "wrong_intake") return null;
    const call = events.find(
      (e) =>
        e.type === "tool_call" &&
        (e.metadata as { tool?: string } | undefined)?.tool === "save_wrong_question",
    );
    if (!call) return null;
    const result = events.find(
      (e) =>
        e.type === "tool_result" &&
        ((e.metadata as { tool_metadata?: Record<string, unknown> } | undefined)
          ?.tool_metadata as Record<string, unknown> | undefined)?.mid,
    );
    if (!result) return null;
    const meta = (result.metadata as { tool_metadata?: Record<string, unknown> } | undefined)
      ?.tool_metadata as { mid?: string; url?: string } | undefined;
    return { mid: meta?.mid || "", url: meta?.url || "" };
  }, [msg.capability, events]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }} data-testid="assistant-body">
      <style>{`
.amb-artlink:active{background:#f8fafc;}
.amb-againbtn:active{background:#d1fae5;}
.amb-citlink:active{opacity:.7;}
      `}</style>
      {/* A1：阶段条（deep_solve / 通用多阶段能力） */}
      {(stages.length > 0 || (isStreaming && currentStage)) && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }} data-testid="stage-strip">
          {stages.map((s) => (
            <span
              key={s}
              style={{
                fontSize: 11, padding: "2px 8px", borderRadius: 999,
                background: "#eef2ff", color: "#4f46e5", border: "1px solid #e0e7ff",
              }}
            >
              {s}
            </span>
          ))}
          {isStreaming && currentStage && !stages.includes(stageLabel(currentStage)) && (
            <span
              style={{
                fontSize: 11, padding: "2px 8px", borderRadius: 999,
                background: "#4f46e5", color: "#ffffff", animation: "ambPulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
              }}
            >
              {stageLabel(currentStage)}…
            </span>
          )}
          <style>{`@keyframes ambPulse{0%,100%{opacity:1}50%{opacity:.5}}`}</style>
        </div>
      )}

      {/* 分支：可视化产物 / 数学动画 / 出题卡 / 默认文本（互斥，同桌面 ChatMessages） */}
      {visualizeResult ? (
        <VisualizationViewer result={visualizeResult} />
      ) : mathAnimatorResult ? (
        <MathAnimatorViewer result={mathAnimatorResult} />
      ) : hasQuiz ? (
        <>
          {msg.content ? (
            <AssistantResponse content={msg.content} isStreaming={isStreaming} />
          ) : null}
          <QuizViewer
            questions={quizQuestions!}
            sessionId={sessionId || null}
            turnId={quizTurnId}
            language="zh"
          />
        </>
      ) : showDefaultText ? (
        <AssistantResponse content={msg.content} isStreaming={isStreaming} />
      ) : null}

      {/* M24：wrong_intake 保存成功卡（含跳转链接 + 再来一道） */}
      {wrongSaved && (
        <div
          style={{
            borderRadius: 16, border: "1px solid #a7f3d0", background: "#ecfdf5", padding: 12,
          }}
          data-testid="wrong-saved-card"
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 500, color: "#047857" }}>
            <CheckCircleFilled style={{ fontSize: 16 }} /> 已存入错题本
          </div>
          <Link
            to={wrongSaved.url || `/e/tutor/h5/wrongbook?mid=${wrongSaved.mid}${u ? `&u=${encodeURIComponent(u)}` : ""}`}
            style={{
              marginTop: 6, display: "block", fontSize: 12, color: "#4f46e5",
              textDecoration: "underline",
            }}
          >
            去错题本查看 →
          </Link>
          {onAgainIntake && (
            <button
              onClick={onAgainIntake}
              data-testid="wrong-again-btn"
              className="amb-againbtn"
              style={{
                marginTop: 8, width: "100%", padding: "10px 0", borderRadius: 12,
                background: "#ffffff", border: "1px solid #a7f3d0",
                color: "#047857", fontSize: 14, fontWeight: 500, cursor: "pointer",
              }}
            >
              📝 再来一道
            </button>
          )}
        </div>
      )}

      {/* A1：产物文件卡（生成文件：图片内联预览 / 文档下载卡） */}
      {artifacts.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }} data-testid="artifact-list">
          {artifacts.map((a, i) => {
            const mime = a.mime_type || "";
            const url = a.url || (a.base64 ? `data:${mime || "application/octet-stream"};base64,${a.base64}` : "");
            const isImage = mime.startsWith("image/");
            const isVideo = mime.startsWith("video/");
            const filename = a.filename || `产物 ${i + 1}`;
            return (
              <div
                key={a.id || i}
                style={{
                  borderRadius: 12, border: "1px solid #e2e8f0", background: "#ffffff",
                  overflow: "hidden",
                }}
              >
                {isImage && url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={url}
                    alt={filename}
                    style={{ display: "block", maxHeight: 288, width: "100%", background: "#ffffff", objectFit: "contain" }}
                  />
                ) : isVideo && url ? (
                  <video
                    src={url}
                    controls
                    preload="metadata"
                    style={{ display: "block", maxHeight: 288, width: "100%", background: "#000000" }}
                  />
                ) : null}
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="amb-artlink"
                  style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
                    borderTop: "1px solid #f1f5f9",
                  }}
                >
                  {isImage ? (
                    <PictureOutlined style={{ fontSize: 16, color: "#10b981", flexShrink: 0 }} />
                  ) : isVideo ? (
                    <VideoCameraOutlined style={{ fontSize: 16, color: "#f43f5e", flexShrink: 0 }} />
                  ) : (
                    <FileTextOutlined style={{ fontSize: 16, color: "#0ea5e9", flexShrink: 0 }} />
                  )}
                  <span
                    style={{
                      flex: 1, minWidth: 0, fontSize: 12, fontWeight: 500,
                      color: "#334155", overflow: "hidden", textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {filename}
                  </span>
                  <span style={{ fontSize: 11, color: "#94a3b8" }}>{formatSize(a.size_bytes)}</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 2, fontSize: 11, color: "#4f46e5", flexShrink: 0 }}>
                    {isImage || isVideo ? <ExportOutlined style={{ fontSize: 12 }} /> : <DownloadOutlined style={{ fontSize: 12 }} />}
                    打开
                  </span>
                </a>
              </div>
            );
          })}
        </div>
      )}

      {/* A4：引用来源（可折叠） */}
      {citations.length > 0 && (
        <div
          style={{ borderRadius: 12, border: "1px solid #e2e8f0", background: "#f8fafc" }}
          data-testid="citations"
        >
          <button
            onClick={() => setCitationsOpen((v) => !v)}
            style={{
              width: "100%", display: "flex", alignItems: "center", gap: 6,
              padding: "8px 12px", textAlign: "left", fontSize: 12, color: "#64748b",
              border: "none", background: "transparent", cursor: "pointer",
            }}
          >
            <ReadOutlined style={{ fontSize: 14, color: "#10b981" }} />
            引用来源（{citations.length}）
            <DownOutlined
              style={{
                fontSize: 12, marginLeft: "auto", transition: "transform .15s",
                transform: citationsOpen ? "rotate(180deg)" : "none",
              }}
            />
          </button>
          {citationsOpen && (
            <div style={{ padding: "0 12px 8px", display: "flex", flexDirection: "column", gap: 6 }}>
              {citations.map((c, i) => {
                const inner = (
                  <>
                    <SourceIcon type={c.type} />
                    <span
                      style={{
                        flex: 1, minWidth: 0, fontSize: 12, color: "#475569",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}
                    >
                      {c.title}
                    </span>
                    {c.url && <ExportOutlined style={{ fontSize: 12, color: "#cbd5e1", flexShrink: 0 }} />}
                  </>
                );
                return c.url ? (
                  <a
                    key={i}
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="amb-citlink"
                    style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 0" }}
                  >
                    {inner}
                  </a>
                ) : (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 0" }}>
                    {inner}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AssistantMessageBody;
