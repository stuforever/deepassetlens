// 引擎批2 2.4：AgentChatContext——桌面窗口桥 SSE 消费层。
// POST /api/v2/skills/capability 流式消费（fetch ReadableStream 逐帧解析 SSE）→
// StreamEvent 分发。对外 API 镜像 h5shared/UnifiedChatContext 形状
// （messages/isStreaming/currentStage/send/stop——等价承接职责；实现级偏离=WS→SSE 桥，
// 台账 E-20 登记）。事件类型 import 自 lib/unified-ws（类型保留契约——预-3）。
// h5_user 不设（桌面端 anonymous 段——dt_agent_capabilities._user_prefix）。
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { StreamEvent } from "../../../lib/unified-ws";
import type {
  MessageAttachment,
  MessageRequestSnapshot,
} from "../../tutor/h5/h5shared/UnifiedChatContext";

export interface AgentMessageItem {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  capability?: string;
  /** 本轮桥事件流（渲染层消费——ChatMessageItem.events 同语义）。 */
  events?: StreamEvent[];
  attachments?: MessageAttachment[];
  requestSnapshot?: MessageRequestSnapshot;
}

export interface AgentSendOptions {
  skillCode?: string;
  tools?: string[];
  knowledgeBases?: string[];
  attachments?: MessageAttachment[];
  historyReferences?: Array<Record<string, unknown>>;
  config?: Record<string, unknown>;
  /** 请求快照（随消息落 messages 供上下文读数/再生成消费）。 */
  requestSnapshot?: MessageRequestSnapshot;
  /** 复用既有会话（不传则首帧 session_meta 回填）。 */
  sessionId?: string | null;
}

interface AgentChatState {
  sessionId: string | null;
  messages: AgentMessageItem[];
  isStreaming: boolean;
  /** 推理段聚合文本（thinking 事件——DT 思考块渲染源）。 */
  thinkingText: string;
  /** 当前阶段（stage_start/stage_end 的 stage 值）。 */
  currentStage: string;
  /** 最近一轮 turn_id（TurnNavigator 接桥锚点——批3 消费）。 */
  lastTurnId: string | null;
  /** 桥事件计数（上下文读数 chip 数据源之一——批3 接量）。 */
  lastUsage: { tokens: number; costUsd: number; calls: number } | null;
  error: string | null;
}

interface AgentChatContextValue extends AgentChatState {
  send: (content: string, opts?: AgentSendOptions) => Promise<void>;
  stop: () => void;
  reset: () => void;
  loadSession: (sessionId: string, messages: AgentMessageItem[]) => void;
}

const AgentChatContext = createContext<AgentChatContextValue | null>(null);

const BRIDGE_URL = "/api/v2/skills/capability";

/** SSE 帧解析：fetch body 流 → 事件帧（event:/data: 对）。 */
async function* parseSse(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<{ event: string; data: string }> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const raw = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) yield { event, data };
    }
  }
}

export function AgentChatProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AgentChatState>({
    sessionId: null,
    messages: [],
    isStreaming: false,
    thinkingText: "",
    currentStage: "",
    lastTurnId: null,
    lastUsage: null,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  /** 尾消息 id（链式 parentMessageId——DT 乐观链语义；buildVisiblePath 沿链走） */
  const lastIdRef = useRef<number | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  const send = useCallback(async (content: string, opts?: AgentSendOptions) => {
    const skillCode = opts?.skillCode || "tutor/chat";
    const snapshot: MessageRequestSnapshot = {
      content,
      capability: skillCode,
      enabledTools: opts?.tools || [],
      knowledgeBases: opts?.knowledgeBases || [],
      language: "zh",
      attachments: opts?.attachments,
      config: opts?.config,
      historyReferences: opts?.historyReferences as MessageRequestSnapshot["historyReferences"],
    };
    // DT UnifiedChatContext 乐观 id 语义（负 id=未持久化；buildVisiblePath 依赖 id+父子链）
    const userMsg: AgentMessageItem = {
      id: -Date.now(),
      parentMessageId: lastIdRef.current,
      role: "user",
      content,
      capability: skillCode,
      attachments: opts?.attachments,
      requestSnapshot: snapshot,
    };
    const assistantMsg: AgentMessageItem = {
      id: (userMsg.id as number) - 1,
      parentMessageId: userMsg.id,
      role: "assistant",
      content: "",
      capability: skillCode,
      events: [],
    };
    lastIdRef.current = assistantMsg.id as number;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setState((s) => ({
      ...s,
      messages: [...s.messages, userMsg, assistantMsg],
      isStreaming: true,
      thinkingText: "",
      currentStage: "prepare",
      error: null,
    }));

    const patchAssistant = (patch: (m: AgentMessageItem) => AgentMessageItem) => {
      setState((s) => {
        const msgs = [...s.messages];
        for (let i = msgs.length - 1; i >= 0; i--) {
          if (msgs[i].role === "assistant") {
            msgs[i] = patch(msgs[i]);
            break;
          }
        }
        return { ...s, messages: msgs };
      });
    };

    try {
      const resp = await fetch(BRIDGE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: ac.signal,
        body: JSON.stringify({
          skill_code: skillCode,
          message: content,
          session_id: opts?.sessionId || undefined,
          tools: opts?.tools || [],
          knowledge_bases: opts?.knowledgeBases || [],
          attachments: opts?.attachments || [],
          history_references: opts?.historyReferences || [],
          config: opts?.config || {},
        }),
      });
      if (!resp.ok || !resp.body) {
        throw new Error(`桥端点 HTTP ${resp.status}`);
      }
      for await (const frame of parseSse(resp.body)) {
        let ev: StreamEvent;
        try {
          ev = JSON.parse(frame.data) as StreamEvent;
        } catch {
          continue;
        }
        // 事件序累积进 assistant 消息（events 数组——渲染层与 DT 同构）
        patchAssistant((m) => ({ ...m, events: [...(m.events || []), ev] }));
        switch (ev.type) {
          case "session_meta":
            setState((s) => ({
              ...s,
              sessionId: ev.session_id || s.sessionId,
              lastTurnId: ev.turn_id || s.lastTurnId,
            }));
            break;
          case "thinking":
            setState((s) => ({ ...s, thinkingText: s.thinkingText + ev.content }));
            break;
          case "content":
            patchAssistant((m) => ({ ...m, content: m.content + ev.content }));
            break;
          case "stage_start":
            setState((s) => ({ ...s, currentStage: ev.stage || s.currentStage }));
            break;
          case "stage_end":
            setState((s) => ({ ...s, currentStage: "" }));
            break;
          case "tool_call":
          case "tool_result":
          case "sources":
          case "progress":
          case "observation":
            // 渲染层从 events 数组消费（DT 同构）；聚合态无需处理
            break;
          case "result":
            patchAssistant((m) => ({ ...m, content: ev.content || m.content }));
            break;
          case "error":
            setState((s) => ({ ...s, error: ev.content }));
            break;
          case "done":
            setState((s) => ({
              ...s,
              isStreaming: false,
              currentStage: "",
              lastTurnId: ev.turn_id || s.lastTurnId,
            }));
            break;
          default:
            break;
        }
      }
      setState((s) => ({ ...s, isStreaming: false }));
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setState((s) => ({
        ...s,
        isStreaming: false,
        error: (e as Error).message || String(e),
      }));
    } finally {
      if (abortRef.current === ac) abortRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    lastIdRef.current = null;
    setState({
      sessionId: null,
      messages: [],
      isStreaming: false,
      thinkingText: "",
      currentStage: "",
      lastTurnId: null,
      lastUsage: null,
      error: null,
    });
  }, []);

  const loadSession = useCallback(
    (sessionId: string, messages: AgentMessageItem[]) => {
      abortRef.current?.abort();
      abortRef.current = null;
      setState((s) => ({
        ...s,
        sessionId,
        messages,
        isStreaming: false,
        thinkingText: "",
        currentStage: "",
      }));
    },
    [],
  );

  const value = useMemo(
    () => ({ ...state, send, stop, reset, loadSession }),
    [state, send, stop, reset, loadSession],
  );

  return <AgentChatContext.Provider value={value}>{children}</AgentChatContext.Provider>;
}

export function useAgentChat(): AgentChatContextValue {
  const ctx = useContext(AgentChatContext);
  if (!ctx) throw new Error("useAgentChat 必须在 AgentChatProvider 内使用");
  return ctx;
}
