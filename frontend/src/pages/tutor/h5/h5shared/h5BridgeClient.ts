/**
 * 引擎批6 6.1/6.4：H5 桥传输客户端——UnifiedWSClient 的桥 SSE 等价件。
 * 接口面 1:1（connected/connect/disconnect/setResumeState/send），
 * 传输面 WS→桥 POST /api/v2/skills/capability SSE（StreamEvent 逐字段同型）。
 * ChatMessage 变体处置（E-26）：
 *   message/start_turn→桥 turn（skill_code 由 capability 映射）；
 *   cancel_turn→abort 在途 SSE（服务端生成器随断连取消，观察行为等价）；
 *   regenerate→桥 tutor/chat config.action="regenerate"（服务端重跑末轮）；
 *   subscribe/resume/unsubscribe→桥无订阅语义（no-op）；
 *   submit_user_reply→桥 chat 无 ask_user 中断面（no-op，台账登记）。
 */
import { apiUrl } from "../../../../lib/api";
import type { ChatMessage, StreamEvent } from "../../admin/unified-ws";

/** capability（DT 语义 id）→桥 skill_code 映射。 */
export function capabilityToSkill(capability: string | null | undefined): string {
  switch (capability) {
    case null:
    case undefined:
    case "":
    case "chat":
      return "tutor/chat";
    case "solve":
      return "tutor/solve";
    case "mastery":
      return "tutor/mastery";
    case "wrong_intake":
      return "tutor/wrong-intake";
    case "deep_question":
    case "quiz":
      return "tutor/quiz";
    case "visualize":
      return "tutor/visualize";
    case "deep_research":
      return "tutor/research";
    default:
      return "tutor/chat";
  }
}

interface StartTurnLike {
  type: "message" | "start_turn";
  content: string;
  tools?: string[];
  capability?: string | null;
  knowledge_bases?: string[];
  session_id?: string | null;
  attachments?: {
    type: string;
    url?: string;
    base64?: string;
    filename?: string;
    mime_type?: string;
  }[];
  language?: string;
  config?: Record<string, unknown>;
  notebook_references?: { notebook_id: string; record_ids: string[] }[];
  history_references?: string[];
  question_notebook_references?: number[];
  book_references?: { book_id: string; page_ids: string[] }[];
  persona?: string;
  llm_selection?: { profile_id: string; model_id: string } | null;
  u?: string;
  code?: string;
  parent_message_id?: number | null;
}

export class H5BridgeClient {
  private onEvent: (event: StreamEvent) => void;
  private onClose?: () => void;
  private controller: AbortController | null = null;
  private lastTurnId: string | null = null;
  private lastSeq = 0;
  /** 桥面恒连（SSE 无连接阶段——connected 语义=可立即 send）。 */
  connected = true;

  constructor(onEvent: (event: StreamEvent) => void, onClose?: () => void) {
    this.onEvent = onEvent;
    this.onClose = onClose;
  }

  connect(): void {
    /* no-op：SSE 按轮建立 */
  }

  disconnect(): void {
    this.abort();
  }

  setResumeState(turnId: string | null, seq: number): void {
    // 桥面无断线续传（每轮全量流）；仅存档供语义对齐。
    this.lastTurnId = turnId;
    this.lastSeq = seq;
  }

  send(msg: ChatMessage): void {
    if (msg.type === "cancel_turn") {
      this.abort();
      return;
    }
    if (msg.type === "subscribe_turn" || msg.type === "subscribe_session" ||
        msg.type === "resume_from" || msg.type === "unsubscribe") {
      return; // 桥无订阅语义（每轮独立 SSE 全量流）
    }
    if (msg.type === "submit_user_reply") {
      // 桥 chat 编排无 ask_user 中断面（E-26④）——暂停-应答链路不触发。
      return;
    }
    if (msg.type === "regenerate") {
      void this.runTurn({
        skill_code: "tutor/chat",
        message: "",
        session_id: msg.session_id,
        h5_user: msg.u ?? null,
        code: msg.code ?? null,
        config: { action: "regenerate" },
      });
      return;
    }
    const start = msg as StartTurnLike;
    void this.runTurn({
      skill_code: capabilityToSkill(start.capability),
      message: start.content,
      session_id: start.session_id ?? undefined,
      tools: start.tools ?? [],
      knowledge_bases: start.knowledge_bases ?? [],
      attachments: start.attachments ?? [],
      history_references: start.history_references ?? [],
      h5_user: start.u ?? null,
      code: start.code ?? null,
      config: {
        ...(start.config ?? {}),
        enabled_tools: start.tools ?? [],
        capability: start.capability ?? null,
        persona: start.persona ?? "",
        language: start.language ?? "zh",
        notebook_references: start.notebook_references ?? [],
        question_notebook_references: start.question_notebook_references ?? [],
        book_references: start.book_references ?? [],
        llm_selection: start.llm_selection ?? null,
        parent_message_id: start.parent_message_id ?? null,
        h5_user: start.u ?? null,
        code: start.code ?? null,
      },
    });
  }

  private abort(): void {
    if (this.controller) {
      try {
        this.controller.abort();
      } catch {
        /* ignore */
      }
      this.controller = null;
    }
  }

  private async runTurn(body: Record<string, unknown>): Promise<void> {
    this.abort();
    const controller = new AbortController();
    this.controller = controller;
    try {
      const resp = await fetch(apiUrl("/api/v2/skills/capability"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify(body),
      });
      if (!resp.ok || !resp.body) throw new Error(`桥端点 HTTP ${resp.status}`);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let streamOpen = true;
      while (streamOpen) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          const raw = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          let type = "";
          let data = "";
          for (const line of raw.split("\n")) {
            if (line.startsWith("event:")) type = line.slice(6).trim();
            else if (line.startsWith("data:")) data = line.slice(5).trim();
          }
          if (!data) continue;
          let ev: Partial<StreamEvent> & { metadata?: Record<string, unknown> };
          try {
            ev = JSON.parse(data);
          } catch {
            continue;
          }
          const streamEvent: StreamEvent = {
            type: (ev.type || type) as StreamEvent["type"],
            source: ev.source || "agent",
            stage: ev.stage || "",
            content: ev.content || "",
            metadata: ev.metadata || {},
            session_id: ev.session_id,
            turn_id: ev.turn_id,
            seq: ev.seq,
            timestamp: ev.timestamp || Date.now(),
          };
          if (streamEvent.turn_id) this.lastTurnId = streamEvent.turn_id;
          if (typeof streamEvent.seq === "number") this.lastSeq = streamEvent.seq;
          this.onEvent(streamEvent);
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return; // cancel/disconnect 语义
      // 桥失败→合成 error+done 帧（调用方 STREAM_END failed 面不缺帧）
      this.onEvent({
        type: "error", source: "bridge", stage: "session",
        content: err instanceof Error ? err.message : String(err),
        metadata: {}, timestamp: Date.now(),
      });
      this.onEvent({
        type: "done", source: "bridge", stage: "session", content: "",
        metadata: { ok: false }, timestamp: Date.now(),
      });
      this.onClose?.();
    }
  }
}
