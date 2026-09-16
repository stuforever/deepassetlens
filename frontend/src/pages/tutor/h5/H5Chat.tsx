/**
 * 复刻自 DeepTutor 原仓 web/app/h5/chat/page.tsx（整件 1:1），落位
 * frontend/src/pages/tutor/h5/H5Chat.tsx（路由 /e/tutor/h5/chat，已注册）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. next/navigation useRouter → react-router-dom useNavigate（back()→navigate(-1)、
 *    push(x)→navigate(x)）；useSearchParams → react-router-dom 同名（get 语义一致）；
 * 3. next/link Link → react-router-dom Link；路由前缀 /h5/* → /e/tutor/h5/*
 *    （withU 包裹的路径同步改写，query 原样）；
 * 4. fetch(apiUrl("/api/v1/...")) → fetch("/api/v1/...")（同源相对路径，路径/方法/
 *    头/体/query 逐字保留）；
 * 5. lucide → @ant-design/icons 语义就近：ChevronLeft→LeftOutlined、Copy→CopyOutlined、
 *    Check→CheckOutlined、RefreshCw→RedoOutlined、Volume2→SoundOutlined、
 *    BookMarked→BookOutlined、Send→SendOutlined、Plus→PlusOutlined、
 *    History→HistoryOutlined、Mic→AudioOutlined、X→CloseOutlined、
 *    Loader2→LoadingOutlined、Pencil→EditOutlined、Trash2→DeleteOutlined、
 *    Brain→RobotOutlined（antd 无脑形图标，AI 思考语义就近）、Camera→CameraOutlined、
 *    FileText→FileTextOutlined；
 * 6. i18n：本页原文即中文，无 t()；
 * 7. Tailwind → 内联样式 + 组件级 <style> 承接 active:/focus:/disabled: 伪类与
 *    animate-pulse/bounce/delay 关键帧（Tailwind 调色板 hex 直用）；data-testid 与
 *    aria-label 全量保留；
 * 8. import("@/lib/learning-api") → import("./h5shared/learningApi")（SA-D 交付，
 *    ProgressSummary 类型同源）；@/context/UnifiedChatContext → ./h5shared/
 *    UnifiedChatContext；./AskUserCard → ./h5shared/AskUserCard；ask-user-state →
 *    ./h5shared/askUserState；AskUserOptions → ./h5shared/AskUserOptions；
 *    AssistantMessageBody → ./h5shared/AssistantMessageBody；QuizFollowupContext →
 *    ./h5shared/QuizFollowupContext；QuizFollowupTabBody → ./h5shared/
 *    QuizFollowupTabBody；h5-utils → ./h5shared/h5Utils；message-branches →
 *    ./h5shared/messageBranches；h5-tts → ./h5shared/h5Tts；ChatPlusPanel →
 *    ./h5shared/ChatPlusPanel；book-references/file-attachments/doc-attachments →
 *    ./h5shared（doc-attachments re-export 批8 classifyFile，isSvgFilename 原仓实现
 *    由 SA-F 补齐）；thinking-events → ./h5shared/thinkingEvents；playground-config →
 *    ./h5shared/playgroundConfig；H5Shell → ./h5shared/H5Shell；H5Sheet →
 *    ./h5shared/H5Sheet；
 * 9. alert() → window.alert（原仓 h5 原生弹窗语义保留，文案逐字）。
 *
 * H5 对话页（design §三 + 第十一篇 N3/N4/N5 + 第十二篇 T2）。
 *
 * 复用桌面 UnifiedChatProvider（WS 流式）+ 轻量气泡 UI（不引桌面大组件）。
 * - 会话按 ``h5:{u}:`` 前缀过滤（MU-3 隔离）
 * - 按住说话（webkitSpeechRecognition，能力不可用时隐藏）——与 📷 拍照并存（N4）
 * - 消息操作：复制 / 重新生成 / 朗读（h5Speak：浏览器→服务端兜底）/ 存入错题本
 * - 「＋」面板：7 能力（4 配置卡）/ 人格 / 模型 / 工具 / KB / 笔记本 / 书 / 语言 / 附件
 */
import React, {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import {
  LeftOutlined,
  CopyOutlined,
  CheckOutlined,
  RedoOutlined,
  SoundOutlined,
  BookOutlined,
  SendOutlined,
  PlusOutlined,
  HistoryOutlined,
  AudioOutlined,
  CloseOutlined,
  LoadingOutlined,
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
  CameraOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { UnifiedChatProvider, useUnifiedChat } from "./h5shared/UnifiedChatContext";
import type { MessageItem } from "./h5shared/UnifiedChatContext";
import H5AskUserCard from "./h5shared/AskUserCard";
import { hasPendingAskUserInMessages } from "./h5shared/askUserState";
import { extractAskUserPayload } from "./h5shared/AskUserOptions";
// M21 A1/A2/A4：能力产物 / 出题卡 / 引用（移动版消息体）
import AssistantMessageBody from "./h5shared/AssistantMessageBody";
// M21 A2：出题卡 + 追问（复用桌面 QuizViewer 与 QuizFollowupContext）
import {
  QuizFollowupProvider,
  useQuizFollowupController,
  type QuizFollowupTabContext,
} from "./h5shared/QuizFollowupContext";
import QuizFollowupTabBody from "./h5shared/QuizFollowupTabBody";
import { withU } from "./h5shared/h5Utils";
import { buildVisiblePath, type SiblingInfo } from "./h5shared/messageBranches";
import type { ProgressSummary } from "./h5shared/learningApi";
import { H5Shell } from "./h5shared/H5Shell";
import { H5Sheet } from "./h5shared/H5Sheet";
// 第十一篇 N5 / N4 + 第十二篇 T2 复用层
import { h5Speak, h5StopSpeak } from "./h5shared/h5Tts";
import ChatPlusPanel, {
  capabilityShortLabel,
  type NotebookRefPayload,
} from "./h5shared/ChatPlusPanel";
import type { SelectedBookReference } from "../admin/book-references";
import { selectedBooksToPayload } from "../admin/book-references";
import {
  readFileAsDataUrl,
  extractBase64FromDataUrl,
} from "../admin/file-attachments";
// classifyFile re-export 自批8；isSvgFilename 批8 裁剪、SA-F 按原仓实现补齐。
import { classifyFile, isSvgFilename } from "./h5shared/doc-attachments";
import {
  getActiveThinkingBurst,
  formatThinkingElapsed,
} from "./h5shared/thinkingEvents";
import {
  loadCapabilityPlaygroundConfigs,
  resolveCapabilityPlaygroundConfig,
  type CapabilityPlaygroundConfigMap,
} from "./h5shared/playgroundConfig";

// Tailwind 调色板 hex 对位（本文件局部用）。
const V600 = "#7c3aed";
const V500 = "#8b5cf6";
const V400 = "#a78bfa";
const V200 = "#ddd6fe";
const V100 = "#ede9fe";
const V50 = "#f5f3ff";
const VLIGHT = "#c4b5fd";
const I300 = "#a5b4fc";
const I600 = "#4f46e5";
const I100 = "#e0e7ff";
const S50 = "#f8fafc";
const S100 = "#f1f5f9";
const S200 = "#e2e8f0";
const S300 = "#cbd5e1";
const S400 = "#94a3b8";
const S500 = "#64748b";
const S600 = "#475569";
const S700 = "#334155";
const R500 = "#f43f5e";
const R600 = "#e11d48";
const R100 = "#ffe4e6";
const SKY500 = "#0ea5e9";
const SKY100 = "#e0f2fe";
const SKY700 = "#0369a1";
const A100 = "#fef3c7";
const A700 = "#b45309";
const E100 = "#d1fae5";
const E700 = "#047857";
const T100 = "#ccfbf1";
const T700 = "#0f766e";
const P600 = "#9333ea";

const H5ChatStyleBlock = () => (
  <style>{`
@keyframes h5cPulse{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes h5cBounce{0%,100%{transform:translateY(-25%)}50%{transform:translateY(25%)}}
.h5c-bounce{animation:h5cBounce 1s infinite;}
.h5c-bounce-d120{animation:h5cBounce 1s infinite;animation-delay:120ms;}
.h5c-bounce-d240{animation:h5cBounce 1s infinite;animation-delay:240ms;}
.h5c-editbtn:active{color:${I600}!important;}
.h5c-branchbtn:active{color:${I600}!important;}
.h5c-del-confirm:active{color:${R600}!important;}
.h5c-actbtn:active{color:${S600}!important;}
.h5c-renamebtn:active{background:${I100}!important;}
.h5c-delbtn:active{background:${R100}!important;}
.h5c-sessbtn:active{opacity:.7;}
.h5c-camera:active{background:${S200}!important;}
.h5c-plus:active{background:${V200}!important;}
.h5c-chipbtn:active{background:${S50}!important;}
.h5c-coachlink:active{background:${S50}!important;}
.h5c-input:focus{outline:none;box-shadow:0 0 0 2px ${V200};}
.h5c-editarea:focus{outline:none;box-shadow:0 0 0 2px ${I300};}
.h5c-send:disabled{opacity:.4;cursor:not-allowed;}
.h5c-edit-send:disabled{opacity:.4;}
  `}</style>
);

interface PendingAttachment {
  type: "image" | "file";
  filename: string;
  base64: string;
  mime_type?: string;
  previewUrl?: string;
  size: number;
}

// 卡点② 前端：H5 深度思考状态行（thinking burst 活跃时显示，1s 计时；
// 桌面端 StreamingStatus 零改动，本组件仅在 H5 ChatBubble 占位分支使用）
function ThinkingStatusLine({ events }: { events: any[] }) {
  const burst = getActiveThinkingBurst(events || []);
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!burst) return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [burst?.startedAt, burst?.count]);
  if (!burst) return null;
  return (
    <div
      style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 0", fontSize: 13, color: S500 }}
      data-testid="thinking-status-line"
    >
      <RobotOutlined style={{ fontSize: 16, color: S500, animation: "h5cPulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite" }} />
      <span style={{ fontVariantNumeric: "tabular-nums" }}>深度思考中 · 已{formatThinkingElapsed((Date.now() / 1000 - burst.startedAt) * 1000)}</span>
    </div>
  );
}

function ChatBubble({ msg, isStreaming, u, sessionId, currentStage, onRegenerate, onStoreWrong, onEditMessage, onDeleteTurn, siblingInfo, onSwitchBranch, onAgainIntake }: {
  msg: MessageItem;
  isStreaming: boolean;
  u: string;
  sessionId?: string | null;
  currentStage?: string;
  onRegenerate: () => void;
  onStoreWrong: (msg: MessageItem) => void;
  onEditMessage?: (messageId: number, newContent: string) => void;
  onDeleteTurn?: (messageId: number) => Promise<void>;
  // V1（M22）：分支切换——桌面同源 buildVisiblePath 语义
  siblingInfo?: SiblingInfo;
  onSwitchBranch?: (parentMessageId: number | null, childId: number) => void;
  // M24：wrong_intake「再来一道」——父组件填入输入框
  onAgainIntake?: () => void;
}) {
  const isUser = msg.role === "user";
  const [copied, setCopied] = useState(false);
  // G1（M24-A）：删除消息（同桌面 turn 级删除，二次点按确认）
  const [confirmDel, setConfirmDel] = useState(false);
  // A3（M21）：消息编辑分支——与桌面 UserMessage 同语义（editMessage 处理分支+重生成）
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");
  // M16-D（第八篇核实缺口 2）：本回合 AI 是否调用了 read_memory（感知「AI 记得我」）
  const usedMemory = (msg.events || []).some((ev: any) => {
    if (ev?.type !== "tool_call") return false;
    const name = String(
      (ev.metadata && (ev.metadata.tool_name || ev.metadata.tool)) || ev.content || "",
    ).trim();
    return name === "read_memory";
  });
  const canEdit = Boolean(onEditMessage) && typeof msg.id === "number";

  if (isUser) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end" }} data-testid="user-bubble">
        <div style={{ maxWidth: "82%" }}>
          {editing ? (
            <div style={{ background: "#ffffff", borderRadius: 16, border: `1px solid ${I300}`, padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={Math.min(5, Math.max(2, editText.split("\n").length))}
                className="h5c-editarea"
                style={{
                  width: "100%", padding: "8px 10px", borderRadius: 12,
                  border: `1px solid ${S200}`, fontSize: 14, resize: "none",
                  boxSizing: "border-box",
                }}
                autoFocus
              />
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  onClick={() => setEditing(false)}
                  style={{
                    flex: 1, padding: "6px 0", borderRadius: 8,
                    border: `1px solid ${S200}`, color: S500, fontSize: 12,
                    background: "transparent", cursor: "pointer",
                  }}
                >
                  取消
                </button>
                <button
                  onClick={() => {
                    const trimmed = editText.trim();
                    if (!trimmed || typeof msg.id !== "number") return;
                    onEditMessage?.(msg.id, trimmed);
                    setEditing(false);
                  }}
                  disabled={!editText.trim()}
                  className="h5c-edit-send"
                  style={{
                    flex: 1, padding: "6px 0", borderRadius: 8, background: I600,
                    color: "#ffffff", fontSize: 12, fontWeight: 500,
                    border: "none", cursor: "pointer",
                  }}
                >
                  发送并生成分支
                </button>
              </div>
            </div>
          ) : (
            <>
              <div
                style={{
                  background: I600, color: "#ffffff", borderRadius: 16,
                  borderBottomRightRadius: 6, padding: "10px 14px", fontSize: 15,
                  lineHeight: 1.625, whiteSpace: "pre-wrap", wordBreak: "break-word",
                }}
              >
                {msg.content || "（图片）"}
                {(msg.attachments || []).length > 0 &&
                  msg.attachments!.map((a, i) =>
                    a.base64 ? (
                      <img
                        key={i}
                        src={`data:${a.mime_type || "image/jpeg"};base64,${a.base64}`}
                        alt="附件"
                        style={{ marginTop: 8, borderRadius: 12, maxHeight: 208, width: "auto" }}
                      />
                    ) : null,
                  )}
              </div>
              {canEdit && !isStreaming && (
                <div style={{ marginTop: 4, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 12, paddingRight: 4 }}>
                  {/* V1（M22）：‹ n/m › 分支切换（编辑重问产生兄弟分支后出现） */}
                  {siblingInfo && siblingInfo.total > 1 && onSwitchBranch && (
                    <span
                      style={{ display: "inline-flex", alignItems: "center", gap: 2, fontSize: 11, color: S400 }}
                      data-testid="branch-nav"
                    >
                      <button
                        type="button"
                        aria-label="上一个分支"
                        className="h5c-branchbtn"
                        style={{
                          padding: "0 4px", border: "none", background: "transparent",
                          cursor: "pointer", color: S400, fontSize: 12,
                        }}
                        disabled={siblingInfo.index <= 1}
                        onClick={() => {
                          const prev = siblingInfo.siblingIds[siblingInfo.index - 2];
                          if (prev !== undefined) onSwitchBranch(siblingInfo.parentId, prev);
                        }}
                      >
                        ‹
                      </button>
                      <span style={{ userSelect: "none", fontVariantNumeric: "tabular-nums" }}>
                        {siblingInfo.index}/{siblingInfo.total}
                      </span>
                      <button
                        type="button"
                        aria-label="下一个分支"
                        className="h5c-branchbtn"
                        style={{
                          padding: "0 4px", border: "none", background: "transparent",
                          cursor: "pointer", color: S400, fontSize: 12,
                        }}
                        disabled={siblingInfo.index >= siblingInfo.total}
                        onClick={() => {
                          const next = siblingInfo.siblingIds[siblingInfo.index];
                          if (next !== undefined) onSwitchBranch(siblingInfo.parentId, next);
                        }}
                      >
                        ›
                      </button>
                    </span>
                  )}
                  <button
                    onClick={() => {
                      setEditText(msg.content);
                      setEditing(true);
                    }}
                    className="h5c-editbtn"
                    style={{
                      display: "flex", alignItems: "center", gap: 4, fontSize: 11,
                      color: S400, border: "none", background: "transparent", cursor: "pointer",
                    }}
                  >
                    <EditOutlined style={{ fontSize: 12 }} /> 编辑重问
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  const textOnly = (msg.content || "").replace(/#/g, "").replace(/\*/g, "").trim();
  return (
    <div style={{ display: "flex", justifyContent: "flex-start" }}>
      <div style={{ maxWidth: "92%", width: "100%" }}>
        <div
          style={{
            background: "#ffffff", borderRadius: 16, borderBottomLeftRadius: 6,
            border: `1px solid ${S200}`, padding: "10px 14px", fontSize: 15,
          }}
        >
          {/* M21 A1/A2/A4：能力产物 / 出题卡 / 引用 / 生成文件（复用桌面 lib 与共享 viewer） */}
          {!msg.content && isStreaming && !usedMemory ? (
            getActiveThinkingBurst(msg.events || []) ? (
              <ThinkingStatusLine events={msg.events || []} />
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 0" }}>
                <span className="h5c-bounce" style={{ width: 6, height: 6, borderRadius: 999, background: S300, display: "inline-block" }} />
                <span className="h5c-bounce-d120" style={{ width: 6, height: 6, borderRadius: 999, background: S300, display: "inline-block" }} />
                <span className="h5c-bounce-d240" style={{ width: 6, height: 6, borderRadius: 999, background: S300, display: "inline-block" }} />
              </div>
            )
          ) : (
            <AssistantMessageBody
              msg={msg}
              isStreaming={isStreaming}
              currentStage={currentStage}
              sessionId={sessionId}
              u={u}
              onAgainIntake={onAgainIntake}
            />
          )}
        </div>
        {!isStreaming && textOnly && (
          <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 12, padding: "0 4px", fontSize: 11, color: S400 }}>
            <button
              onClick={() => {
                navigator.clipboard.writeText(textOnly);
                setCopied(true);
                setTimeout(() => setCopied(false), 1200);
              }}
              className="h5c-actbtn"
              style={{ display: "flex", alignItems: "center", gap: 4, color: S400, border: "none", background: "transparent", cursor: "pointer", fontSize: 11 }}
            >
              {copied ? <CheckOutlined style={{ fontSize: 12 }} /> : <CopyOutlined style={{ fontSize: 12 }} />}
              {copied ? "已复制" : "复制"}
            </button>
            <button
              onClick={() => void h5Speak(textOnly)}
              className="h5c-actbtn"
              style={{ display: "flex", alignItems: "center", gap: 4, color: S400, border: "none", background: "transparent", cursor: "pointer", fontSize: 11 }}
            >
              <SoundOutlined style={{ fontSize: 12 }} /> 朗读
            </button>
            <button
              onClick={onRegenerate}
              className="h5c-actbtn"
              style={{ display: "flex", alignItems: "center", gap: 4, color: S400, border: "none", background: "transparent", cursor: "pointer", fontSize: 11 }}
            >
              <RedoOutlined style={{ fontSize: 12 }} /> 重新生成
            </button>
            <button
              onClick={() => onStoreWrong(msg)}
              className="h5c-actbtn"
              style={{ display: "flex", alignItems: "center", gap: 4, color: S400, border: "none", background: "transparent", cursor: "pointer", fontSize: 11 }}
            >
              <BookOutlined style={{ fontSize: 12 }} /> 存错题本
            </button>
            {/* G1（M24-A）：删除该轮（对话+回答一起删，桌面同款语义） */}
            {onDeleteTurn && typeof msg.id === "number" && (
              confirmDel ? (
                <>
                  <button
                    onClick={() => {
                      setConfirmDel(false);
                      void onDeleteTurn(msg.id as number);
                    }}
                    className="h5c-del-confirm"
                    style={{ color: R500, fontWeight: 500, border: "none", background: "transparent", cursor: "pointer", fontSize: 11 }}
                    data-testid="msg-del-confirm"
                  >
                    确认删除
                  </button>
                  <button
                    onClick={() => setConfirmDel(false)}
                    className="h5c-actbtn"
                    style={{ color: S400, border: "none", background: "transparent", cursor: "pointer", fontSize: 11 }}
                  >
                    取消
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setConfirmDel(true)}
                  className="h5c-actbtn"
                  style={{ display: "flex", alignItems: "center", gap: 4, color: S400, border: "none", background: "transparent", cursor: "pointer", fontSize: 11 }}
                  data-testid="msg-del-btn"
                >
                  <DeleteOutlined style={{ fontSize: 12 }} /> 删除
                </button>
              )
            )}
            {/* M16-D：AI 参考了学习记录 -> 小标（记忆对学生的感知露脸） */}
            {usedMemory && (
              <span style={{ display: "flex", alignItems: "center", gap: 4, color: V500 }}>
                <RobotOutlined style={{ fontSize: 12 }} /> 已参考学习记录
              </span>
            )}
            {u && <span style={{ marginLeft: "auto", fontSize: 10, color: S300 }}>@{u}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

function HistoryDrawer({
  open,
  onClose,
  u,
  onLoad,
}: {
  open: boolean;
  onClose: () => void;
  u: string;
  onLoad: (sessionId: string) => void;
}) {
  const [sessions, setSessions] = useState<
    { session_id: string; title: string; updated_at: number }[]
  >([]);
  const [loading, setLoading] = useState(false);

  // F5（M14-C）：会话重命名/删除（与桌面同 sessions API）
  const loadSessions = useCallback(async () => {
    try {
      const qs = u ? `&u=${encodeURIComponent(u)}` : "";
      const res = await fetch(`/api/v1/sessions?limit=100&offset=0${qs}`);
      if (!res.ok) return;
      const data = await res.json();
      const list: any[] = data.sessions ?? [];
      const mine = [...list].sort(
        (a, b) => (b.updated_at || 0) - (a.updated_at || 0),
      );
      setSessions(mine);
    } catch {
      /* ignore */
    }
  }, [u]);

  const renameSession = useCallback(
    async (id: string) => {
      const title = window.prompt("输入新标题", "");
      if (title === null || !title.trim()) return;
      try {
        await fetch(`/api/v1/sessions/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: title.trim() }),
        });
      } catch {
        /* ignore */
      }
      void loadSessions();
    },
    [loadSessions],
  );

  const deleteSession = useCallback(
    async (id: string) => {
      if (!window.confirm("确定删除该对话？删除后不可恢复")) return;
      try {
        await fetch(`/api/v1/sessions/${id}`, { method: "DELETE" });
      } catch {
        /* ignore */
      }
      void loadSessions();
    },
    [loadSessions],
  );

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    void loadSessions().finally(() => setLoading(false));
  }, [open, u, loadSessions]);

  if (!open) return null;

  return (
    // S1（M23）：H5Sheet 统一基座（历史对话抽屉）
    <H5Sheet
      open
      onClose={onClose}
      title={
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <HistoryOutlined style={{ fontSize: 16, color: "#6366f1" }} /> 历史对话
        </span>
      }
    >
      <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 0", color: S400 }}>
            <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载中…
          </div>
        ) : sessions.length === 0 ? (
          <div style={{ textAlign: "center", padding: "48px 0", color: S400, fontSize: 14 }}>
            {u ? `「${u}」还没有历史对话` : "还没有历史对话"}
            <div style={{ fontSize: 12, marginTop: 8 }}>发一条消息，对话会自动保存</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {sessions.map((s) => (
              <div
                key={s.session_id}
                style={{ display: "flex", alignItems: "center", gap: 4, borderRadius: 12, border: `1px solid ${S200}`, padding: "10px 12px" }}
              >
                <button
                  onClick={() => {
                    onLoad(s.session_id);
                    onClose();
                  }}
                  className="h5c-sessbtn"
                  style={{ flex: 1, minWidth: 0, textAlign: "left", border: "none", background: "transparent", cursor: "pointer", padding: 0 }}
                >
                  <div
                    style={{
                      fontSize: 14, fontWeight: 500, color: S700,
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}
                  >
                    {s.title || "未命名对话"}
                  </div>
                  <div style={{ fontSize: 11, color: S400, marginTop: 2 }}>
                    {s.updated_at
                      ? new Date(s.updated_at * 1000).toLocaleString()
                      : ""}
                  </div>
                </button>
                <button
                  onClick={() => void renameSession(s.session_id)}
                  aria-label="重命名"
                  className="h5c-renamebtn"
                  style={{
                    flexShrink: 0, width: 36, height: 36, borderRadius: 8,
                    background: S50, color: S500, display: "flex", alignItems: "center",
                    justifyContent: "center", border: "none", cursor: "pointer",
                  }}
                >
                  <EditOutlined style={{ fontSize: 16 }} />
                </button>
                <button
                  onClick={() => void deleteSession(s.session_id)}
                  aria-label="删除"
                  className="h5c-delbtn"
                  style={{
                    flexShrink: 0, width: 36, height: 36, borderRadius: 8,
                    background: S50, color: S500, display: "flex", alignItems: "center",
                    justifyContent: "center", border: "none", cursor: "pointer",
                  }}
                >
                  <DeleteOutlined style={{ fontSize: 16 }} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </H5Sheet>
  );
}

/** M21-A2：把 QuizViewer 的「追问」桥接到 H5 底部弹层（桌面同语义，替代 SessionViewerPanel） */
function H5QuizFollowupBridge({ onOpen }: { onOpen: (ctx: QuizFollowupTabContext) => void }) {
  const controller = useQuizFollowupController();
  useEffect(() => {
    controller.setOpenTabHandler(onOpen);
    return () => controller.setOpenTabHandler(null);
  }, [controller, onOpen]);
  return null;
}

function H5ChatContentInner() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const mode = searchParams.get("mode") || "";
  const pathId = searchParams.get("path") || "";
  const presetPrompt = searchParams.get("prompt") || "";
  const capabilityParam = searchParams.get("capability") || "";
  const deepText = searchParams.get("text") || "";
  const isMastery = mode === "mastery" && !!pathId;
  const {
    state,
    sendMessage,
    loadSession,
    newSession,
    regenerateLastMessage,
    setCapability,
    setPersonaSelection,
    setLLMSelection,
    setTools,
    setKBs,
    submitUserReply,
    sessionStatuses,
    editMessage,
    deleteTurn,
    switchBranch,
  } = useUnifiedChat();
  const [input, setInput] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const recogRef = useRef<any>(null);
  // E4（M12）：自动播报 + 连续语音模式
  const [voiceLoop, setVoiceLoop] = useState(false);
  const voiceLoopRef = useRef(false);
  const loopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevStreamingRef = useRef(state.isStreaming);
  // U6（第六篇）：对话页进入精通辅导（普通模式顶栏入口）
  const [coachOpen, setCoachOpen] = useState(false);
  const [coachPaths, setCoachPaths] = useState<ProgressSummary[]>([]);
  const [coachLoading, setCoachLoading] = useState(false);
  // F4（M14-B）：深度解题能力（chat/deep_solve 切换，拍题页可直达）
  const [isDeepSolve, setIsDeepSolve] = useState(capabilityParam === "deep_solve");
  const deepSentRef = useRef(false);

  // ---- N4/N5：待发附件 + 「＋」面板 + 会话引用 ----
  const [pendingAtts, setPendingAtts] = useState<PendingAttachment[]>([]);
  const [plusOpen, setPlusOpen] = useState(false);
  const [notebookRefs, setNotebookRefs] = useState<NotebookRefPayload[]>([]);
  const [bookRefs, setBookRefs] = useState<SelectedBookReference[]>([]);
  const [capabilityConfigs, setCapabilityConfigs] = useState<CapabilityPlaygroundConfigMap>({});
  useEffect(() => {
    setCapabilityConfigs(loadCapabilityPlaygroundConfigs());
  }, []);

  const toggleDeepSolve = useCallback(
    (on: boolean) => {
      setIsDeepSolve(on);
      setCapability(on ? "deep_solve" : "chat");
    },
    [setCapability],
  );

  const openCoach = useCallback(async () => {
    setCoachOpen(true);
    setCoachLoading(true);
    try {
      const { fetchAllProgress } = await import("./h5shared/learningApi");
      const data = await fetchAllProgress(u);
      setCoachPaths(data.summaries || []);
    } catch {
      setCoachPaths([]);
    } finally {
      setCoachLoading(false);
    }
  }, [u]);
  useEffect(() => {
    voiceLoopRef.current = voiceLoop;
  }, [voiceLoop]);
  useEffect(() => {
    try {
      setVoiceLoop(localStorage.getItem("h5_voice_loop") === "1");
    } catch {
      /* ignore */
    }
  }, []);

  // 精通之路模式（总纲 G2）：进入时切到 mastery_path capability。
  // 每次发送带 book_references=[pathId]，让引擎解析 mastery_path_id。
  useEffect(() => {
    if (isMastery) setCapability("mastery_path");
  }, [isMastery, setCapability]);

  // F4（M14-B）：deep_solve 直达（拍题页"深度解题"→ ?capability=deep_solve&text=…）
  useEffect(() => {
    if (capabilityParam === "deep_solve") setCapability("deep_solve");
  }, [capabilityParam, setCapability]);

  // F4：带 text 时自动发起深度解题（已有历史则预填输入框）。
  // 能力已由 capability=deep_solve 设定，直接发题干即可，不拼前缀（避免污染会话记录）。
  useEffect(() => {
    if (!deepText || deepSentRef.current) return;
    deepSentRef.current = true;
    const t = setTimeout(() => {
      if (state.messages.length === 0) {
        sendMessage(deepText);
      } else {
        setInput(deepText);
      }
    }, 800);
    return () => clearTimeout(t);
  }, [deepText, state.messages.length, sendMessage]);

  useEffect(() => {
    setSpeechSupported(
      typeof window !== "undefined" &&
        Boolean(
          (window as any).SpeechRecognition ||
            (window as any).webkitSpeechRecognition,
        ),
    );
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [state.messages]);

  // F1（M14-A）：ask_user 交互卡——精通辅导出题 / 普通对话反问都靠它恢复回合
  const activeTurnId = state.sessionId
    ? (sessionStatuses[state.sessionId]?.activeTurnId ?? null)
    : null;
  // V1（M22）：分支导航——渲染走「可见路径」，兄弟分支经 ‹ n/m › 切换（桌面同源语义）
  const { messages: visibleMessages, siblingsByMessageId } = useMemo(
    () => buildVisiblePath(state.messages, state.selectedBranches),
    [state.messages, state.selectedBranches],
  );

  const pendingAskUserCard = useMemo(() => {
    if (!activeTurnId) return null;
    if (!hasPendingAskUserInMessages(state.messages, activeTurnId)) return null;
    for (let i = state.messages.length - 1; i >= 0; i--) {
      const m = state.messages[i];
      if (m.role !== "assistant") continue;
      const d = extractAskUserPayload(m.events);
      if (d && !d.resolved) return d;
    }
    return null;
  }, [state.messages, activeTurnId]);
  const hasPendingAskUser = !!pendingAskUserCard;

  const stopListening = useCallback(() => {
    try {
      recogRef.current?.stop();
    } catch {
      /* ignore */
    }
    setListening(false);
  }, []);

  // N4：附件归类（image/file），超限拒绝（与桌面 attachment-limits 同量级）
  const pickFiles = useCallback(async (files: File[]) => {
    const next: PendingAttachment[] = [];
    for (const f of files) {
      if (!classifyFile(f)) continue;
      if (f.size > 20 * 1024 * 1024) continue;
      try {
        const raw = await readFileAsDataUrl(f);
        const svg = isSvgFilename(f.name) || f.type === "image/svg+xml";
        const isImage = !svg && f.type.startsWith("image/");
        next.push({
          type: isImage ? "image" : "file",
          filename: f.name,
          base64: extractBase64FromDataUrl(raw),
          mime_type: f.type || undefined,
          previewUrl: isImage || svg ? raw : undefined,
          size: f.size,
        });
      } catch {
        /* 单文件失败跳过 */
      }
    }
    if (next.length) setPendingAtts((prev) => [...prev, ...next].slice(0, 8));
  }, []);

  const removePending = (idx: number) =>
    setPendingAtts((prev) => prev.filter((_, i) => i !== idx));

  const handleSend = useCallback(
    (textOverride?: string) => {
      const text = (textOverride ?? input).trim();
      if ((!text && pendingAtts.length === 0) || (state.isStreaming && !hasPendingAskUser)) return;
      // E4：新 turn 开始打断旧朗读（浏览器 + 服务端双通道）；手动发送 = 人在回路优先
      h5StopSpeak();
      stopListening();
      // N4：默认文案——只发图 → 请讲解；只发文档 → 请阅读附件
      const messageContent =
        text ||
        (pendingAtts.some((a) => a.type === "image")
          ? "请讲解这道题"
          : pendingAtts.length
            ? "请阅读附件内容后回答"
            : "");
      if (!messageContent) return;
      // N5：可配置能力发送时带 config（playground-config 持久化的必填项）
      const cap = state.activeCapability || "";
      let config: Record<string, unknown> | undefined;
      if (["deep_question", "visualize", "deep_research", "math_animator"].includes(cap)) {
        const resolved = resolveCapabilityPlaygroundConfig(capabilityConfigs, cap, []);
        if (resolved.config && Object.keys(resolved.config).length > 0) {
          config = resolved.config;
        }
      }
      const attachmentsPayload = pendingAtts.length
        ? pendingAtts.map((a) => ({
            type: a.type,
            filename: a.filename,
            base64: a.base64,
            mime_type: a.mime_type,
          }))
        : undefined;
      const nbPayload = notebookRefs.length ? notebookRefs : undefined;
      // 精通之路 refs 优先；否则用「＋」面板的书引用
      const bookOptions = isMastery
        ? { bookReferences: [{ book_id: pathId, page_ids: [] }] }
        : bookRefs.length
          ? { bookReferences: selectedBooksToPayload(bookRefs) }
          : undefined;
      if (hasPendingAskUser) {
        // F1（M14-A）：有待答 ask_user 卡 -> 走 submitUserReply 恢复回合，
        // 绝不能发新消息（start_turn 会把暂停中的精通辅导回合标 failed）。
        submitUserReply(messageContent);
        return;
      }
      sendMessage(
        messageContent,
        attachmentsPayload,
        config,
        nbPayload,
        undefined,
        bookOptions,
      );
      setInput("");
      setPendingAtts([]);
      setNotebookRefs([]);
      setBookRefs([]);
    },
    [input, pendingAtts, state.isStreaming, state.activeCapability, capabilityConfigs, notebookRefs, bookRefs, sendMessage, isMastery, pathId, stopListening, hasPendingAskUser, submitUserReply],
  );

  // 预设 prompt（design T2 AI 资源入口：/h5/chat?prompt=…）：进入后自动发送一次。
  const presetSentRef = useRef(false);
  useEffect(() => {
    if (!presetPrompt || presetSentRef.current) return;
    if (state.messages.length > 0) {
      // 已有历史（如历史会话恢复），预填到输入框让用户自己点发送
      setInput(presetPrompt);
      presetSentRef.current = true;
      return;
    }
    const t = setTimeout(() => {
      if (!presetSentRef.current) {
        presetSentRef.current = true;
        handleSend(presetPrompt);
      }
    }, 800);
    return () => clearTimeout(t);
  }, [presetPrompt, state.messages.length, handleSend]);

  const startListening = useCallback(
    (autoSend = false) => {
      const SR =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;
      if (!SR) return;
      const recog = new SR();
      recog.lang = "zh-CN";
      recog.interimResults = true;
      recog.continuous = false;
      recog.onresult = (e: any) => {
        let text = "";
        for (let i = 0; i < e.results.length; i++) {
          text += e.results[i][0].transcript;
        }
        if (autoSend) {
          const t = text.trim();
          if (t.length >= 2) handleSend(t); // E4 连续模式：识别即发送
        } else {
          setInput(text);
        }
      };
      recog.onend = () => {
        setListening(false);
        // E4 连续模式：识别自然结束后稍候继续听（人在回路由 focus/手动接管）
        if (autoSend && voiceLoopRef.current && !state.isStreaming) {
          loopTimerRef.current = setTimeout(() => {
            if (voiceLoopRef.current && !state.isStreaming) startListening(true);
          }, 300);
        }
      };
      recog.onerror = () => setListening(false);
      recogRef.current = recog;
      setListening(true);
      try {
        recog.start();
      } catch {
        setListening(false);
      }
    },
    [handleSend, state.isStreaming],
  );

  // E4 连续语音模式：开启即自动开听（免按住）；退出时清理
  useEffect(() => {
    if (!voiceLoop) return;
    if (!speechSupported) {
      setVoiceLoop(false);
      return;
    }
    // iOS 解锁预热（T4 已全局解锁，此处保底）
    if ("speechSynthesis" in window) {
      try {
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(""));
      } catch {
        /* ignore */
      }
    }
    const t = setTimeout(() => startListening(true), 400);
    return () => {
      clearTimeout(t);
      if (loopTimerRef.current) clearTimeout(loopTimerRef.current);
      stopListening();
    };
  }, [voiceLoop, speechSupported, startListening, stopListening]);

  // E4 自动播报 + 连续续听：turn 完成（isStreaming true -> false）时触发
  useEffect(() => {
    const turnedDone = prevStreamingRef.current && !state.isStreaming;
    prevStreamingRef.current = state.isStreaming;
    if (!turnedDone) return;
    let auto = false;
    try {
      auto = localStorage.getItem("h5_tts_auto") === "1";
    } catch {
      /* ignore */
    }
    const last = state.messages[state.messages.length - 1];
    const text =
      last && last.role === "assistant" && last.content
        ? last.content.replace(/#/g, "").replace(/\*/g, "").trim()
        : "";
    if (!text) return;
    if (auto) {
      // T2：h5Speak（浏览器优先，无中文语音自动落服务端）
      void h5Speak(text, {
        onDone: () => {
          if (voiceLoopRef.current) {
            loopTimerRef.current = setTimeout(() => startListening(true), 300);
          }
        },
      });
    } else if (voiceLoopRef.current) {
      loopTimerRef.current = setTimeout(() => startListening(true), 300);
    }
  }, [state.isStreaming, state.messages, startListening]);

  // W1（第八篇 M16-A，P0）：对话存错题本重构——存问题不存回答。
  const storeWrong = useCallback(
    async (msg: MessageItem) => {
      try {
        const idx = state.messages.indexOf(msg);
        const lastUser =
          idx >= 0
            ? [...state.messages.slice(0, idx)].reverse().find((m) => m.role === "user")
            : undefined;
        const rawQ = (lastUser?.content || "").trim();
        const question =
          rawQ.slice(0, 500) ||
          `（拍照提问的题目，见原对话 chat:${state.sessionId || ""}）`;
        const title = question.slice(0, 20);
        const qs = u ? `?u=${encodeURIComponent(u)}` : "";
        const res = await fetch(`/api/v1/mother-questions${qs}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title,
            question_text: question,
            standard_answer: (msg.content || "").slice(0, 2000),
            detailed_analysis: (msg.content || "").slice(0, 4000),
            tags: ["h5", "src:chat", ...(u ? [`u:${u}`] : [])],
            subject: "math",
            note: state.sessionId ? `chat:${state.sessionId}` : undefined,
          }),
        });
        if (res.status === 409) {
          window.alert("这道题已在错题本 📖");
        } else if (res.ok) {
          window.alert("已加入错题本 📖，系统会安排到期复习");
        } else {
          const data = await res.json().catch(() => ({}));
          window.alert("存入失败：" + (data.detail || "请重试"));
        }
      } catch {
        window.alert("网络错误，请重试");
      }
    },
    [u, state.messages, state.sessionId],
  );

  // M21-A2：出题卡「追问」底部弹层（QuizFollowupTabBody 复用桌面组件）
  const [followupTab, setFollowupTab] = useState<QuizFollowupTabContext | null>(null);
  const openFollowupTab = useCallback((ctx: QuizFollowupTabContext) => {
    setFollowupTab(ctx);
  }, []);

  const goBack = () => {
    // 直接打开（无 referrer）时 back() 会退到 about:blank——回 /h5 更稳
    if (
      typeof window !== "undefined" &&
      window.history.length > 1 &&
      document.referrer
    ) {
      navigate(-1);
    } else {
      navigate(withU("/e/tutor/h5", u));
    }
  };

  // N5：chips 行——当前会话带着什么上下文，一屏可见，可点 × 移除
  const kbCount = state.knowledgeBases?.length || 0;
  const nbCount = notebookRefs.reduce((s, r) => s + r.record_ids.length, 0);
  const bookCount = bookRefs.reduce((s, r) => s + r.pages.length, 0);
  const modelLabel = state.llmSelection
    ? `${state.llmSelection.profile_id}:${state.llmSelection.model_id}`.slice(0, 22)
    : "";
  const capLabel = capabilityShortLabel(state.activeCapability);
  const hasChips =
    (state.activeCapability && state.activeCapability !== "chat") ||
    state.personaSelection ||
    modelLabel ||
    kbCount > 0 ||
    nbCount > 0 ||
    bookCount > 0 ||
    pendingAtts.length > 0;

  const chipBtn = { border: "none", background: "transparent", cursor: "pointer", padding: 0, color: "inherit", display: "inline-flex" } as React.CSSProperties;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100dvh" }}>
      <H5ChatStyleBlock />
      {/* 顶栏（N3：[← 返回][🕘 历史]  💬 对话  [＋]） */}
      <div
        style={{
          background: `linear-gradient(to right, ${V600}, ${P600})`, color: "#ffffff",
          padding: "48px 16px 12px", borderBottomLeftRadius: 24,
          borderBottomRightRadius: 24, flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button
              onClick={goBack}
              aria-label="返回"
              data-testid="chat-back"
              style={{ display: "flex", alignItems: "center", gap: 2, fontSize: 14, color: "#ddd6fe", border: "none", background: "transparent", cursor: "pointer" }}
            >
              <LeftOutlined style={{ fontSize: 18 }} /> 返回
            </button>
            <button
              onClick={() => setHistoryOpen(true)}
              style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 14, color: "#ddd6fe", border: "none", background: "transparent", cursor: "pointer" }}
            >
              <HistoryOutlined style={{ fontSize: 16 }} /> 历史
            </button>
          </div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>💬 对话</div>
          <button
            onClick={() => {
              newSession();
              setInput("");
            }}
            aria-label="新对话"
            style={{ color: "#ddd6fe", border: "none", background: "transparent", cursor: "pointer" }}
          >
            <PlusOutlined style={{ fontSize: 20 }} />
          </button>
        </div>
        <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: VLIGHT }}>
          {u ? `${u} 的 AI 私教` : "AI 私教 · 随时提问"}
          {isMastery && (
            <span
              style={{
                padding: "2px 6px", borderRadius: 4, background: "rgba(167,139,250,.3)",
                color: "#f5f3ff", fontSize: 11, fontWeight: 500,
              }}
            >
              🏆 精通模式
            </span>
          )}
          {isDeepSolve && (
            <span
              style={{
                padding: "2px 6px", borderRadius: 4, background: "rgba(56,189,248,.3)",
                color: "#f0f9ff", fontSize: 11, fontWeight: 500,
              }}
            >
              🔬 深度解题
            </span>
          )}
          {!isMastery && !isDeepSolve && (
            <>
              <button
                onClick={() => toggleDeepSolve(true)}
                style={{
                  padding: "4px 8px", borderRadius: 999, background: "rgba(167,139,250,.2)",
                  color: "#f5f3ff", fontSize: 11, border: "1px solid rgba(196,181,253,.3)",
                  cursor: "pointer",
                }}
              >
                🔬 深度解题
              </button>
              <button
                onClick={() => void openCoach()}
                style={{
                  padding: "4px 8px", borderRadius: 999, background: "rgba(167,139,250,.2)",
                  color: "#f5f3ff", fontSize: 11, border: "1px solid rgba(196,181,253,.3)",
                  cursor: "pointer",
                }}
              >
                🏆 开始辅导
              </button>
            </>
          )}
          {isDeepSolve && (
            <button
              onClick={() => toggleDeepSolve(false)}
              style={{
                padding: "4px 8px", borderRadius: 999, background: "rgba(167,139,250,.2)",
                color: "#f5f3ff", fontSize: 11, border: "1px solid rgba(196,181,253,.3)",
                cursor: "pointer",
              }}
            >
              ✋ 回普通问答
            </button>
          )}
        </div>
        {isMastery && (
          <div style={{ marginTop: 6 }}>
            <Link
              to={withU("/e/tutor/h5/chat", u)}
              style={{
                display: "inline-flex", alignItems: "center", gap: 4,
                padding: "4px 10px", borderRadius: 999, background: "rgba(167,139,250,.2)",
                color: "#ede9fe", fontSize: 11, border: "1px solid rgba(196,181,253,.3)",
                textDecoration: "none",
              }}
            >
              🚪 退出辅导，回普通对话
            </Link>
          </div>
        )}
      </div>

      {/* 消息列表 */}
      <div
        ref={scrollRef}
        style={{ flex: 1, overflowY: "auto", padding: "16px 12px", background: S50, display: "flex", flexDirection: "column", gap: 12 }}
      >
        {state.messages.length === 0 ? (
          <div
            style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", height: "100%", textAlign: "center",
              color: S400, padding: "0 32px",
            }}
          >
            <div style={{ fontSize: 48, marginBottom: 12 }}>💬</div>
            <div style={{ fontWeight: 500, color: S500 }}>
              和 AI 私教聊聊学习
            </div>
            <div style={{ fontSize: 14, marginTop: 8 }}>
              不会的题、想讲解的知识点、复习安排…… 直接问
            </div>
          </div>
        ) : (
          visibleMessages.map((msg, i) => (
            <ChatBubble
              key={msg.id ?? i}
              msg={msg}
              isStreaming={state.isStreaming && i === visibleMessages.length - 1}
              u={u}
              sessionId={state.sessionId}
              currentStage={state.currentStage}
              onRegenerate={() => regenerateLastMessage()}
              onStoreWrong={storeWrong}
              onEditMessage={editMessage}
              onDeleteTurn={deleteTurn}
              siblingInfo={siblingsByMessageId.get(msg.id as number)}
              onSwitchBranch={switchBranch}
              onAgainIntake={() => setInput("再录一道错题")}
            />
          ))
        )}
      </div>

      {/* F1（M14-A）：当前待答 ask_user 卡（消息列表末尾、输入框上方） */}
      {pendingAskUserCard && (
        <div style={{ flexShrink: 0, padding: "8px 12px 4px", background: S50 }}>
          <H5AskUserCard
            data={pendingAskUserCard}
            onSubmit={(answers) => submitUserReply({ answers })}
          />
        </div>
      )}

      {/* N5：上下文 chips 行（可 × 移除） */}
      {hasChips ? (
        <div
          style={{ flexShrink: 0, background: "#ffffff", padding: "8px 12px 0", display: "flex", flexWrap: "wrap", gap: 6 }}
          data-testid="context-chips"
        >
          {state.activeCapability && state.activeCapability !== "chat" && (
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
                borderRadius: 999, background: I100, color: "#4338ca", fontSize: 11,
              }}
            >
              🧠 {capLabel}
              <button onClick={() => setCapability("chat")} aria-label="移除能力模式" style={chipBtn}>
                <CloseOutlined style={{ fontSize: 11 }} />
              </button>
            </span>
          )}
          {state.personaSelection && (
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
                borderRadius: 999, background: A100, color: A700, fontSize: 11,
              }}
            >
              🎭 {state.personaSelection}
              <button onClick={() => setPersonaSelection("")} aria-label="移除人格" style={chipBtn}>
                <CloseOutlined style={{ fontSize: 11 }} />
              </button>
            </span>
          )}
          {modelLabel && (
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
                borderRadius: 999, background: SKY100, color: SKY700, fontSize: 11,
              }}
            >
              🤖 {modelLabel}
              <button onClick={() => setLLMSelection(null)} aria-label="移除模型" style={chipBtn}>
                <CloseOutlined style={{ fontSize: 11 }} />
              </button>
            </span>
          )}
          {kbCount > 0 && (
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
                borderRadius: 999, background: E100, color: E700, fontSize: 11,
              }}
            >
              📚 知识库×{kbCount}
              <button onClick={() => setKBs([])} aria-label="移除知识库" style={chipBtn}>
                <CloseOutlined style={{ fontSize: 11 }} />
              </button>
            </span>
          )}
          {nbCount > 0 && (
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
                borderRadius: 999, background: I100, color: "#4338ca", fontSize: 11,
              }}
            >
              📓 笔记×{nbCount}
              <button onClick={() => setNotebookRefs([])} aria-label="移除笔记引用" style={chipBtn}>
                <CloseOutlined style={{ fontSize: 11 }} />
              </button>
            </span>
          )}
          {bookCount > 0 && (
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
                borderRadius: 999, background: T100, color: T700, fontSize: 11,
              }}
            >
              📖 书页×{bookCount}
              <button onClick={() => setBookRefs([])} aria-label="移除书引用" style={chipBtn}>
                <CloseOutlined style={{ fontSize: 11 }} />
              </button>
            </span>
          )}
          {pendingAtts.length > 0 && (
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
                borderRadius: 999, background: S100, color: S600, fontSize: 11,
              }}
            >
              📎 附件×{pendingAtts.length}
              <button onClick={() => setPendingAtts([])} aria-label="清空附件" style={chipBtn}>
                <CloseOutlined style={{ fontSize: 11 }} />
              </button>
            </span>
          )}
        </div>
      ) : null}

      {/* N4：待发附件预览条 */}
      {pendingAtts.length > 0 && (
        <div
          style={{
            flexShrink: 0, background: "#ffffff", padding: "4px 12px 6px",
            display: "flex", gap: 8, overflowX: "auto",
          }}
          data-testid="attachment-preview"
        >
          {pendingAtts.map((a, i) => (
            <div key={i} style={{ position: "relative", flexShrink: 0 }}>
              {a.type === "image" && a.previewUrl ? (
                <img
                  src={a.previewUrl}
                  alt={a.filename}
                  style={{ width: 56, height: 56, objectFit: "cover", borderRadius: 12, border: `1px solid ${S200}` }}
                />
              ) : (
                <div
                  style={{
                    width: 56, height: 56, borderRadius: 12, border: `1px solid ${S200}`,
                    background: S50, display: "flex", flexDirection: "column",
                    alignItems: "center", justifyContent: "center", padding: "0 4px",
                    boxSizing: "border-box",
                  }}
                >
                  <FileTextOutlined style={{ fontSize: 16, color: SKY500 }} />
                  <span
                    style={{
                      fontSize: 9, color: S400, overflow: "hidden",
                      textOverflow: "ellipsis", whiteSpace: "nowrap", width: "100%",
                      textAlign: "center", marginTop: 2,
                    }}
                  >
                    {a.filename}
                  </span>
                </div>
              )}
              <button
                onClick={() => removePending(i)}
                aria-label="移除附件"
                style={{
                  position: "absolute", top: -6, right: -6, width: 20, height: 20,
                  borderRadius: 999, background: S700, color: "#ffffff",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  border: "none", cursor: "pointer",
                }}
              >
                <CloseOutlined style={{ fontSize: 10 }} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 输入栏（N4：[＋][textarea][📷][🎤][➤] —— 📷 与 🎤 并排共存） */}
      <div
        style={{
          flexShrink: 0, background: "#ffffff", borderTop: `1px solid ${S200}`,
          padding: "8px 12px", paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
          {/* N5：「＋」动作面板入口 */}
          <button
            onClick={() => setPlusOpen(true)}
            aria-label="添加与设置"
            data-testid="chat-plus"
            className="h5c-plus"
            style={{
              width: 44, height: 44, borderRadius: 999, background: V100,
              color: V600, display: "flex", alignItems: "center",
              justifyContent: "center", flexShrink: 0, border: "none", cursor: "pointer",
            }}
          >
            <PlusOutlined style={{ fontSize: 20 }} />
          </button>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            rows={Math.min(4, Math.max(1, input.split("\n").length))}
            placeholder={hasPendingAskUser ? "请作答…" : "输入问题，Enter 发送"}
            onFocus={() => {
              // E4：用户手动点输入框 = 人在回路优先，退出连续语音
              if (voiceLoopRef.current) setVoiceLoop(false);
            }}
            className="h5c-input"
            style={{
              flex: 1, padding: "8px 12px", borderRadius: 16, border: `1px solid ${S200}`,
              background: S50, fontSize: 15, resize: "none",
              fontFamily: "inherit", boxSizing: "border-box",
            }}
          />
          {/* N4 修复：拍照按钮恒在（不再被语音互斥挤掉）——直接调相机 */}
          <button
            onClick={() => {
              const el = document.getElementById(
                "h5-chat-camera-input",
              ) as HTMLInputElement | null;
              el?.click();
            }}
            aria-label="拍照"
            data-testid="chat-photo"
            className="h5c-camera"
            style={{
              width: 44, height: 44, borderRadius: 999, background: S100,
              color: S500, display: "flex", alignItems: "center",
              justifyContent: "center", flexShrink: 0, border: "none", cursor: "pointer",
            }}
          >
            <CameraOutlined style={{ fontSize: 20 }} />
          </button>
          <input
            id="h5-chat-camera-input"
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: "none" }}
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              e.target.value = "";
              if (files.length) void pickFiles(files);
            }}
          />
          {/* N4 修复：麦克风独立按钮（支持语音时才显示）——与拍照共存 */}
          {speechSupported && (
            <button
              onPointerDown={() => {
                // E4：手动按住说话 = 人在回路优先，退出连续模式
                if (voiceLoopRef.current) setVoiceLoop(false);
                startListening();
              }}
              onPointerUp={stopListening}
              onPointerLeave={stopListening}
              aria-label="按住说话"
              data-testid="chat-mic"
              style={{
                width: 44, height: 44, borderRadius: 999,
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0, border: "none", cursor: "pointer",
                transition: "all .15s",
                background: listening ? R500 : S100,
                color: listening ? "#ffffff" : S500,
                transform: listening ? "scale(1.1)" : "none",
              }}
            >
              <AudioOutlined style={{ fontSize: 20 }} />
            </button>
          )}
          <button
            onClick={() => handleSend()}
            disabled={(!input.trim() && pendingAtts.length === 0) || state.isStreaming}
            aria-label="发送"
            className="h5c-send"
            style={{
              width: 44, height: 44, borderRadius: 999, background: I600,
              color: "#ffffff", display: "flex", alignItems: "center",
              justifyContent: "center", flexShrink: 0, border: "none", cursor: "pointer",
            }}
          >
            <SendOutlined style={{ fontSize: 20 }} />
          </button>
        </div>
      </div>

      {/* N5：「＋」动作面板（全部子面板二级弹层） */}
      <H5QuizFollowupBridge onOpen={openFollowupTab} />
      <ChatPlusPanel
        open={plusOpen}
        onClose={() => setPlusOpen(false)}
        u={u}
        activeCapability={state.activeCapability}
        onSetCapability={(cap) => {
          setCapability(cap);
          if (cap === "deep_solve") setIsDeepSolve(true);
          if (cap === "" || cap === null) setIsDeepSolve(false);
        }}
        persona={state.personaSelection}
        onSetPersona={setPersonaSelection}
        llmSelection={state.llmSelection}
        onSetLLM={setLLMSelection}
        tools={state.enabledTools || []}
        onSetTools={setTools}
        kbs={state.knowledgeBases || []}
        onSetKBs={setKBs}
        notebookRefs={notebookRefs}
        onSetNotebookRefs={setNotebookRefs}
        bookRefs={bookRefs}
        onSetBookRefs={setBookRefs}
        onPickFiles={(files) => void pickFiles(files)}
        capabilityConfigs={capabilityConfigs}
        onCapabilityConfigsChange={setCapabilityConfigs}
      />

      {/* U6（第六篇）：开始辅导——底部弹层选精通之路（S1/M23 H5Sheet 基座） */}
      <H5Sheet open={coachOpen} onClose={() => setCoachOpen(false)} title="🏆 选择精通之路">
        <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
          {coachLoading && (
            <div style={{ fontSize: 14, color: S400, padding: "24px 0", textAlign: "center" }}>加载中…</div>
          )}
          {!coachLoading && coachPaths.length === 0 && (
            <div style={{ textAlign: "center", padding: "24px 0", display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ fontSize: 14, color: S500 }}>还没有精通之路，先创建一条吧。</div>
              <Link
                to={withU("/e/tutor/h5/paths", u)}
                onClick={() => setCoachOpen(false)}
                style={{
                  display: "inline-block", padding: "10px 16px", borderRadius: 12,
                  background: V600, color: "#ffffff", fontSize: 14, fontWeight: 500,
                  textDecoration: "none",
                }}
              >
                去创建精通之路
              </Link>
            </div>
          )}
          {!coachLoading &&
            coachPaths.map((p) => (
              <Link
                key={p.book_id}
                to={withU(
                  `/e/tutor/h5/chat?mode=mastery&path=${encodeURIComponent(p.book_id)}`,
                  u,
                )}
                onClick={() => setCoachOpen(false)}
                className="h5c-coachlink"
                style={{
                  display: "block", padding: "10px 12px", borderRadius: 12,
                  border: `1px solid ${S200}`, marginBottom: 6, textDecoration: "none",
                }}
              >
                <div style={{ fontSize: 14, fontWeight: 500, color: S700 }}>
                  {p.name || p.book_id}
                </div>
                <div style={{ fontSize: 12, color: S400, marginTop: 2 }}>
                  掌握度 {p.avg_mastery_pct}% · {p.kp_count} 个知识点
                </div>
              </Link>
            ))}
        </div>
      </H5Sheet>

      {/* M21-A2：出题追问底部弹层（复用桌面 QuizFollowupTabBody；S1/M23 H5Sheet 基座） */}
      <H5Sheet
        open={!!followupTab}
        onClose={() => setFollowupTab(null)}
        title={followupTab ? `💬 题目追问 · ${followupTab.tabLabel}` : ""}
        testId="quiz-followup-sheet"
      >
        {followupTab && (
          <div style={{ height: "62dvh", minHeight: 320 }}>
            <QuizFollowupTabBody context={followupTab} />
          </div>
        )}
      </H5Sheet>

      {/* 历史抽屉 */}
      <HistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        u={u}
        onLoad={(id) => void loadSession(id)}
      />
    </div>
  );
}

function H5ChatContent() {
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || "";
  const [h5Code, setH5Code] = useState<string | undefined>(undefined);
  useEffect(() => {
    const sync = () => {
      try {
        setH5Code(sessionStorage.getItem("dsh_h5_code") || undefined);
      } catch {
        /* ignore */
      }
    };
    sync();
    // 立即同步：H5Shell（子组件）effect 先跑，已把 URL code 写入 sessionStorage；
    // 仅监听会错过其 dispatch 的事件（bottom-up effect 顺序）。
    sync();
    window.addEventListener("dsh-h5-code", sync);
    return () => window.removeEventListener("dsh-h5-code", sync);
  }, []);
  return (
    <H5Shell active="chat" hideNav>
      <UnifiedChatProvider h5U={u} h5Code={h5Code}>
        {/* M21-A2：QuizViewer 追问链路的 provider（追问 runner 携带 H5 身份） */}
        <QuizFollowupProvider h5U={u} h5Code={h5Code}>
          <H5ChatContentInner />
        </QuizFollowupProvider>
      </UnifiedChatProvider>
    </H5Shell>
  );
}

export default function H5ChatPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh", display: "flex", alignItems: "center",
            justifyContent: "center", color: S400,
          }}
        >
          <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载中…
        </div>
      }
    >
      <H5ChatContent />
    </Suspense>
  );
}
