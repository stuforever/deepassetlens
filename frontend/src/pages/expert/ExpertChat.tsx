/**
 * 专家对话页 - ChatGPT 式居中落地页（专家地基①，spec §七）
 *
 * 以 FreePlanChat.tsx 为基线复制（A4 等值保护：六处卡驱动改动，其余逐字节保留）：
 * ①头部卡驱动 ②欢迎页三处卡驱动 ③placeholder ④请求体 expert_id ⑤document.title ⑥Spin/cardError
 * 空会话：居中欢迎语（含纳管统计）+ 居中输入框
 * 有消息：消息列表 + 底部输入框
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button, Drawer, Input, Popconfirm, Select, Space, Spin, Typography, message } from 'antd';
import {
  ApiOutlined, ApartmentOutlined, ArrowDownOutlined, BookOutlined, ClearOutlined,
  DatabaseOutlined, ExperimentOutlined, PlayCircleOutlined, ShareAltOutlined, StopOutlined, TeamOutlined,
} from '@ant-design/icons';
import ConversationMessageList from '../../components/conversation/ConversationMessageList';
import { DATA_INTELLIGENCE_SCENE_CONFIG } from '../../components/conversation/sceneConfigs';
import {
  dataIntelligenceApi,
  ChatResponse,
  UserSelectionPayload,
} from '../../services/dataIntelligenceApi';
import { expertsApi, llmAdminApi, sourceTableApi } from '../../services/api';
import type { ExpertCard } from '../../services/api';
import { useStore } from '../../store/useStore';
import type { ChatMessage, ChatMessagePayload } from '../../components/conversation/types';
import { thinkReducer, decisionCommittedReducer } from '../../utils/thinkStreamReducer';
import { buildFinalDeliveryView, resolveFinalAnswer } from '../../utils/finalDelivery';
import RouteSimulator from '../../components/conversation/contractCards/RouteSimulator';
import { tokens } from '../../theme/tokens';

const { Text } = Typography;

const MODE = 'free_plan' as const;

const FREEPLAN_EXAMPLE_QUERIES = [
  '统计用电客户总数',
  '什么是变压器',
  '配电变压器有哪些？列出编号和名称',
  '用电客户数据的来源',
];

// B2 美化：2×2 建议卡图标（与示例问题一一对应）
const FREEPLAN_SUGGEST_ICONS: React.ReactNode[] = [
  <TeamOutlined key="s1" />,
  <BookOutlined key="s2" />,
  <DatabaseOutlined key="s3" />,
  <ApiOutlined key="s4" />,
];

type ChatStatus = 'ready' | 'submitted' | 'streaming' | 'error' | 'stopped';

const ExpertChat: React.FC = () => {
  // 专家地基①（spec §七）：卡驱动——slug 拉卡；关停/非 chat 入口礼貌跳门户；卡读失败不降级 wenshu（spec §十）
  // 注：KeepAlive 架构按页签渲染（无 <Routes>），useParams 不可用——slug 从 location.pathname 解析
  // （/e/{slug}/chat；/home 老书签路径 slug 缺省 wenshu）。
  const location = useLocation();
  const slug = location.pathname.startsWith('/e/')
    ? (location.pathname.split('/')[2] || 'wenshu')
    : 'wenshu';
  const navigate = useNavigate();
  const [card, setCard] = useState<ExpertCard | null>(null);
  const [cardError, setCardError] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const res = await expertsApi.get(slug || '');
        const c = res.data as ExpertCard;
        if (!c.enabled) { message.warning('该专家已关停'); navigate('/', { replace: true }); return; }
        if (c.entry_kind !== 'chat') { message.warning('该专家入口非对话形态'); navigate('/', { replace: true }); return; }
        setCard(c);
      } catch { setCardError('专家卡不可用'); }
    })();
  }, [slug, navigate]);
  // ⑤ document.title 按卡名
  useEffect(() => {
    if (card?.name) document.title = `${card.name} · 图谱平台`;
  }, [card?.name]);
  // ② 建议卡卡驱动（本地保留原常量为缺省——卡读失败时等值兜底）
  // 附件四 A-1：卡级 suggestions 优先（tutor 三条）——空/缺省回落 ui_config（wenshu 零变化）
const SUGGESTIONS = (card?.suggestions && card.suggestions.length > 0
  ? card.suggestions
  : card?.ui_config?.suggestions) ?? FREEPLAN_EXAMPLE_QUERIES;

  // ⑤补补-2：欢迎语动态数（仅 tutor——wenshu 不调接口零变化）
  const [tutorProfile, setTutorProfile] = useState<{ due_count: number; streak_days: number } | null>(null);
  useEffect(() => {
    if (slug !== 'tutor') return;
    (async () => {
      try {
        const r = await fetch('/api/tutor/profile');
        const j = await r.json();
        if (j?.data) setTutorProfile({ due_count: j.data.due_count ?? 0, streak_days: j.data.streak_days ?? 0 });
      } catch { /* 画像失败静默——欢迎语回落 */ }
    })();
  }, [slug]);

  // Session 状态来自 Zustand store（与 AppSider 共享）
  const sessions = useStore((s) => s.sessions);
  const activeSessionId = useStore((s) => s.activeSessionId);
  const setSessions = useStore((s) => s.setSessions);
  const updateSession = useStore((s) => s.updateSession);
  const createNewSession = useStore((s) => s.createNewSession);
  const deleteMessage = useStore((s) => s.deleteMessage);
  const clearMessages = useStore((s) => s.clearMessages);

  // 本地状态（仅对话相关）
  const [question, setQuestion] = useState('');
  // 附件四 A-1：门户卡建议点击→跳 chat 预填（sessionStorage 一次性消费）
  useEffect(() => {
    const pre = sessionStorage.getItem('dal_chat_prefill');
    if (pre) {
      sessionStorage.removeItem('dal_chat_prefill');
      setQuestion(pre);
    }
  }, []);
  // 批13-P：受控路由模拟器 Drawer 开关（审计入口，不常驻前台）
  const [simOpen, setSimOpen] = useState(false);
  const [status, setStatus] = useState<ChatStatus>('ready');
  const [llmConnectionId, setLlmConnectionId] = useState<string | undefined>(undefined);
  const [llmConnections, setLlmConnections] = useState<any[]>([]);
  const [stats, setStats] = useState<{ master: string; business: string; relation: string }>({ master: '-', business: '-', relation: '-' });

  const abortControllerRef = useRef<AbortController | null>(null);
  const stoppedRef = useRef(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  // B2 美化：滚动到底按钮（新内容到达且不在底部时浮出）
  const [showScrollDown, setShowScrollDown] = useState(false);
  const handleChatScroll = useCallback(() => {
    const el = chatContainerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 200;
    setShowScrollDown(!nearBottom);
  }, []);
  const scrollToBottom = useCallback(() => {
    const el = chatContainerRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, []);
  // reasoning(思考流)缓冲: LLM 决策某步骤前的思考累积于此, on_tool_start 新步骤产生时挂到该步骤
  const reasoningBufRef = useRef('');
  // v3.4 rAF 批处理：token 增量缓冲 + 已关闭 round 防护
  const tokenBufRef = useRef<Map<string, {kind: string, text: string}[]>>(new Map());
  const closedRoundsRef = useRef<Set<string>>(new Set());
  const rafRef = useRef(0);
  // 批1-A 答案直出：最近一次答案 round_id（rubric 修订轮判定新答案）
  const lastAnswerRoundRef = useRef<string>('');
  // v3.5: 当前流式会话 id, flushTokens 只写该会话（防多会话串流）
  const streamingSidRef = useRef<string | null>(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const isBusy = status === 'submitted' || status === 'streaming';
  const confirmed = activeSession?.confirmed || {};
  const hasMessages = !!(activeSession && activeSession.messages.length > 0);

  // 加载纳管统计（主数据实体 / 业务实体 / 关系）
  useEffect(() => {
    (async () => {
      try {
        const [tablesRes, relationsRes] = await Promise.allSettled([
          sourceTableApi.getAllTables(),
          sourceTableApi.getAllRelations(),
        ]);
        const td = tablesRes.status === 'fulfilled' ? (tablesRes.value?.data?.data ?? tablesRes.value?.data) : null;
        const master = td && Array.isArray(td.master) ? String(td.master.length) : '-';
        const business = td && Array.isArray(td.business) ? String(td.business.length) : '-';
        let relation = '-';
        if (relationsRes.status === 'fulfilled') {
          const rd = relationsRes.value?.data;
          const inner = rd?.data ?? rd; // 兼容 {code,data:{...}} 和直接 {...}
          if (Array.isArray(inner)) relation = String(inner.length);
          else if (inner && typeof inner === 'object') {
            const total = Object.values(inner).reduce((n: number, v: any) => n + (Array.isArray(v) ? v.length : 0), 0);
            relation = String(total);
          }
        }
        setStats({ master: String(master), business: String(business), relation: String(relation) });
      } catch {}
    })();
  }, []);

  useEffect(() => {
    const loadLlmOptions = async () => {
      try {
        const resp = await llmAdminApi.getConnections();
        const body = resp.data || resp;
        const list = (body?.data || body || []) as any[];
        const chatModels = list
          .filter((c) => c.enabled && c.capability === 'chat')
          .map((c) => ({ id: c.id, name: c.name || c.model_name || c.id, model: c.model_name }));
        setLlmConnections(chatModels);
        const def = list.find((c) => c.is_default && c.enabled && c.capability === 'chat');
        if (def) setLlmConnectionId(def.id);
        else if (chatModels.length > 0) setLlmConnectionId(chatModels[0].id);
      } catch (e) {
        console.error('加载 LLM 列表失败', e);
      }
    };
    loadLlmOptions();
  }, []);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [activeSession?.messages, status, activeSession?.thinkStream]);

  const callBackend = async (
    sid: string,
    userText: string,
    userSelection?: UserSelectionPayload[],
  ): Promise<ChatResponse | null> => {
    return new Promise((resolve) => {
      let resolved = false;
      streamingSidRef.current = sid;  // v3.5: flushTokens 只写该会话
      const timeoutId = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          console.error('[freeplan] timeout 300s');
          message.warning('请求超时（300s），请重试');
          resolve(null);
        }
      }, 300000);

      const patchAssistant = (payloadPatch: Record<string, any>) => {
        setSessions((prev) => prev.map((s) => {
          if (s.id !== sid) return s;
          const messages = s.messages.map((m) => ({ ...m }));
          for (let i = messages.length - 1; i >= 0; i--) {
            if (messages[i].role === 'assistant' && messages[i].loading) {
              messages[i].payload = { ...(messages[i].payload || {}), ...payloadPatch };
              break;
            }
          }
          return { ...s, messages };
        }));
      };

      // 评审 P2-2（二轮）：策略/模板事件按 kind+tool_call_id+内容 追加去重，
      // 不再"每条覆盖前一条"（此前 policy_events: [policyEvent] 只留最后一条）。
      const accumulateAssistantEvent = (payloadKey: 'policy_events' | 'template_events', event: Record<string, any> | null | undefined) => {
        if (!event) return;
        setSessions((prev) => prev.map((s) => {
          if (s.id !== sid) return s;
          const messages = s.messages.map((m) => ({ ...m }));
          for (let i = messages.length - 1; i >= 0; i--) {
            if (messages[i].role === 'assistant' && messages[i].loading) {
              const list: Array<Record<string, any>> = [...((messages[i].payload?.[payloadKey] as Array<Record<string, any>> | undefined) || [])];
              const key = `${event.kind || ''}|${event.tool_call_id || ''}|${event.detail || event.reason || ''}`;
              if (!list.some((e) => `${e.kind || ''}|${e.tool_call_id || ''}|${e.detail || e.reason || ''}` === key)) {
                list.push(event);
              }
              messages[i].payload = { ...(messages[i].payload || {}), [payloadKey]: list };
              break;
            }
          }
          return { ...s, messages };
        }));
      };

      const controller = dataIntelligenceApi.freePlanChatStream(
        {
          thread_id: sid,
          user_input: userText,
          user_selection: userSelection,
          format: 'card',
          llm_connection_id: llmConnectionId,
          mode: MODE,
          expert_id: slug || 'wenshu',  // 专家地基①④：请求带专家维度
        },
        (thinkItem) => {
          // v3.5: phase 由后端显式发送(done/error/running)；兼容旧版 result_status 映射
          const _rs = (thinkItem as any).result_status;
          if (!(thinkItem as any).phase) {
            if (_rs === 'running') (thinkItem as any).phase = 'running';
            else if (_rs === 'done') (thinkItem as any).phase = 'done';
            else if (_rs === 'error') (thinkItem as any).phase = 'error';
          }
          setSessions((prev) => prev.map((s) => {
            if (s.id !== sid) return s;
            // v3.5: 从 loading 消息的 payload.thinkStream 读取（单一数据源）。
            // 不再从 s.thinkStream 读取 —— decision_committed 只写 payload，
            // 从 s.thinkStream 读会拿到不含 live_reason 的旧列表，覆盖丢失判断文本。
            const messages = s.messages.map((m) => ({ ...m }));
            let loadingIdx = -1;
            for (let i = messages.length - 1; i >= 0; i--) {
              if (messages[i].role === 'assistant' && messages[i].loading) { loadingIdx = i; break; }
            }
            const currentThink = loadingIdx >= 0
              ? [...(messages[loadingIdx].payload?.thinkStream || [])]
              : [...s.thinkStream];
            // P2-2: 使用提取的生产 reducer（thinkStreamReducer.ts），测试直接覆盖
            const newThink = thinkReducer(currentThink, thinkItem as any);
            // 写回 loading 消息（单一数据源）+ session.thinkStream（兼容）
            if (loadingIdx >= 0) {
              messages[loadingIdx].payload = { ...(messages[loadingIdx].payload || {}), thinkStream: newThink };
            }
            return { ...s, thinkStream: newThink, messages };
          }));
        },
        (resp) => {
          if (resolved) return;
          resolved = true;
          clearTimeout(timeoutId);
          resolve(resp);
        },
        (err) => {
          if (resolved) return;
          resolved = true;
          clearTimeout(timeoutId);
          if (stoppedRef.current || abortControllerRef.current?.signal.aborted) {
            resolve(null);
          } else {
            console.error('free plan chat stream failed', err);
            message.error(`调用失败: ${err}`);
            resolve(null);
          }
        },
        (s) => {
          if (!resolved) {
            clearTimeout(timeoutId);
            setStatus((st) => (st === 'submitted' ? 'streaming' : st));
          }
          setSessions((prev) => prev.map((sess) => {
            if (sess.id !== sid) return sess;
            const stepCount = sess.thinkStream.length;
            const messages = sess.messages.map((m) => ({ ...m }));
            for (let i = messages.length - 1; i >= 0; i--) {
              if (messages[i].role === 'assistant' && messages[i].loading) {
                messages[i].payload = {
                  ...(messages[i].payload || {}),
                  live_text: s.text,
                  live_meta: s.phase === 'running'
                    ? `自由规划中 · 已执行 ${stepCount} 步`
                    : `规划完成 · 共 ${stepCount} 步`,
                };
                break;
              }
            }
            return { ...sess, messages };
          }));
        },
        (token) => {
          setSessions((prev) => prev.map((s) => {
            if (s.id !== sid) return s;
            const messages = s.messages.map((m) => ({ ...m }));
            for (let i = messages.length - 1; i >= 0; i--) {
              if (messages[i].role === 'assistant' && messages[i].loading) {
                const finalTokens = [...(messages[i].payload?.finalTokens || []), token.text];
                messages[i].payload = { ...(messages[i].payload || {}), finalTokens };
                break;
              }
            }
            return { ...s, messages };
          }));
        },
        (final) => {
          // 交付体验演进 v2：final（答案提交）→ 状态机切「答案整理中…」，覆盖 rubric 评分尾巴与收尾期
          patchAssistant({ final_answer: final.answer, answer_generating: false, answer_finalizing: true });
        },
        (rec) => {
          patchAssistant({ recommendations: rec.questions });
        },
        (tk) => {
          // reasoning(思考流)累积到缓冲, 不进 thinkStream/对话流; 等 on_tool_start 新步骤产生时挂到该步骤
          if (tk.kind === 'reasoning') {
            reasoningBufRef.current += tk.token || '';
            return;
          }

          // v3.4 候选判断实时流：decision_draft / answer_draft 逐 token 流式（rAF 批处理）
          if (tk.kind === 'decision_draft' || tk.kind === 'answer_draft') {
            const roundId = (tk as any).round_id || '';
            const delta = tk.delta || '';
            if (!roundId || !delta) return;
            // 检查该 round 是否已关闭（committed/rejected 已处理）
            if (closedRoundsRef.current.has(roundId)) return;
            // 缓冲到 ref
            if (!tokenBufRef.current.has(roundId)) {
              tokenBufRef.current.set(roundId, []);
            }
            tokenBufRef.current.get(roundId)!.push({ kind: tk.kind, text: delta });
            // 排队 rAF 批量刷新
            if (!rafRef.current) {
              rafRef.current = requestAnimationFrame(flushTokens);
            }
            return;
          }

          // decision_committed: 闸门通过，覆盖校准 + 绑定 tool_call_id
          if (tk.kind === 'decision_committed') {
            const roundId = (tk as any).round_id;
            const tcid = (tk as any).tool_call_id;
            const content = (tk as any).content || '';
            const task = (tk as any).task || '';
            const toolName = (tk as any).tool_name || '';
            // 原子清缓冲：删除该 round_id 的待处理 delta + 标记已关闭
            tokenBufRef.current.delete(roundId || '');
            if (roundId) closedRoundsRef.current.add(roundId);
            setSessions((prev) => prev.map((s) => {
              if (s.id !== sid) return s;
              const messages = s.messages.map((m) => ({ ...m }));
              for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].role === 'assistant' && messages[i].loading) {
                  const ts = [...(messages[i].payload?.thinkStream || [])];
                  // P2-2: 使用提取的生产 reducer（补判不删除 rejected，标记 superseded）
                  const filtered = decisionCommittedReducer(ts, {
                    tool_call_id: tcid, round_id: roundId, tool_name: toolName,
                    content, task,
                  });
                  // 按 round_id 找草稿步骤（降级按 tool_call_id 找/建）
                  let idx = -1;
                  if (roundId) {
                    idx = filtered.findIndex((t: any) => t.round_id === roundId);
                  }
                  if (idx === -1 && tcid) {
                    idx = filtered.findIndex((t: any) => t.tool_call_id === tcid);
                  }
                  const finalTs = idx >= 0 ? filtered : [...filtered]; // reducer 已处理新建/覆盖
                  messages[i].payload = { ...(messages[i].payload || {}), thinkStream: finalTs };
                  break;
                }
              }
              return { ...s, messages };
            }));
            return;
          }

          // decision_rejected: 闸门拒绝。区分格式拒绝（静默删步骤）和范围拒绝（显示详情）
          if (tk.kind === 'decision_rejected') {
            const roundId = (tk as any).round_id;
            const tcid = (tk as any).tool_call_id;
            const candidateContent = (tk as any).candidate_content || '';
            const rejectReason = (tk as any).reason || '';
            // 原子清缓冲
            tokenBufRef.current.delete(roundId || '');
            if (roundId) closedRoundsRef.current.add(roundId);
            // 空内容拒绝（LLM 忘写【下一步判断】标记，纯格式问题）->
            // 删除 on_tool_start 创建的空壳步骤，用户完全不可见，LLM 自动补判重发
            if (!candidateContent.trim()) {
              setSessions((prev) => prev.map((s) => {
                if (s.id !== sid) return s;
                const messages = s.messages.map((m) => ({ ...m }));
                for (let i = messages.length - 1; i >= 0; i--) {
                  if (messages[i].role === 'assistant' && messages[i].loading) {
                    let ts = [...(messages[i].payload?.thinkStream || [])];
                    // 删除该 tool_call_id / round_id 的空壳步骤（on_tool_start 创建的）
                    ts = ts.filter((t: any) =>
                      !(tcid && t.tool_call_id === tcid) && !(roundId && t.round_id === roundId));
                    messages[i].payload = { ...(messages[i].payload || {}), thinkStream: ts };
                    break;
                  }
                }
                return { ...s, messages };
              }));
              return;
            }
            // 非空内容（范围拒绝等真实业务拒绝）-> 显示详情：存 reject_reason + candidate_content
            setSessions((prev) => prev.map((s) => {
              if (s.id !== sid) return s;
              const messages = s.messages.map((m) => ({ ...m }));
              for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].role === 'assistant' && messages[i].loading) {
                  const ts = [...(messages[i].payload?.thinkStream || [])];
                  let idx = -1;
                  if (roundId) idx = ts.findIndex((t: any) => t.round_id === roundId);
                  if (idx === -1 && tcid) idx = ts.findIndex((t: any) => t.tool_call_id === tcid);
                  if (idx >= 0) {
                    ts[idx] = { ...ts[idx], phase: 'rejected', result_status: 'rejected',
                               result_summary: '判定需补充信息·补判中',
                               reject_reason: rejectReason,
                               candidate_content: candidateContent,
                               tool_call_id: tcid || ts[idx].tool_call_id };
                  } else {
                    ts.push({ task: '判定需补充信息', strategy: 'free_plan', kind: 'decision',
                             phase: 'rejected', result_status: 'rejected',
                             result_summary: '判定需补充信息·补判中',
                             reject_reason: rejectReason,
                             candidate_content: candidateContent,
                             tool_call_id: tcid, round_id: roundId });
                  }
                  messages[i].payload = { ...(messages[i].payload || {}), thinkStream: ts };
                  break;
                }
              }
              return { ...s, messages };
            }));
            return;
          }

          // answer_committed: 最终答案完整正文校准
          // 流式期间 draft 实时打字给用户看"正在生成答案"；committed 后清 draft 改用 result_summary
          // 避免完整答案在 ThinkStream 和主消息区重复展示（用户反馈"两遍"）
          if (tk.kind === 'answer_committed') {
            const roundId = (tk as any).round_id;
            const content = (tk as any).content || '';
            const charCount = content.length;
            tokenBufRef.current.delete(roundId || '');
            if (roundId) closedRoundsRef.current.add(roundId);
            setSessions((prev) => prev.map((s) => {
              if (s.id !== sid) return s;
              const messages = s.messages.map((m) => ({ ...m }));
              for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].role === 'assistant' && messages[i].loading) {
                  const ts = [...(messages[i].payload?.thinkStream || [])];
                  let idx = ts.findIndex((t: any) => t.kind === 'answer' || t.kind === 'draft');
                  if (idx === -1) {
                    ts.push({ task: '答案生成', strategy: 'free_plan', kind: 'answer',
                             phase: 'done', draft: '', round_id: roundId,
                             result_summary: `答案已生成（${charCount} 字）` });
                    idx = ts.length - 1;
                  } else {
                    // 交付体验演进 v2：折叠区不存答案正文（draft 恒空），done 兜底由 payload.final_answer 承担
                    ts[idx] = { ...ts[idx], kind: 'answer', phase: 'done', draft: '',
                               round_id: roundId || ts[idx].round_id,
                               result_summary: `答案已生成（${charCount} 字）` };
                  }
                  // P0-fix: 把完整答案写入 payload.final_answer，作为 done 事件的兜底
                  // （done 若 resp.final_answer 为空，applyResponse 会用此值，不覆盖为空）
                  messages[i].payload = {
                    ...(messages[i].payload || {}),
                    thinkStream: ts,
                    final_answer: (messages[i].payload?.final_answer || content),
                    // 批1-A：标记答案已提交（rubric 修订轮 roundChanged 判定用）；answer_revising 保留至 rubric 事件到达再清
                    answer_committed: true,
                    // 交付体验演进 v2：答案提交 → 生成态结束（ThinkStream 不存正文，draft 恒空）
                    answer_generating: false,
                  };
                  break;
                }
              }
              return { ...s, messages };
            }));
            return;
          }

          // 兼容旧版 draft 事件（answer_draft 已处理，这里处理旧 kind=draft）
          if (tk.kind === 'draft') {
            setSessions((prev) => prev.map((s) => {
              if (s.id !== sid) return s;
              const messages = s.messages.map((m) => ({ ...m }));
              for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].role === 'assistant' && messages[i].loading) {
                  const ts = [...(messages[i].payload?.thinkStream || [])];
                  let idx = ts.findIndex((t: any) => t.kind === 'draft' || t.kind === 'answer');
                  if (idx === -1) {
                    const reasoning = reasoningBufRef.current;
                    reasoningBufRef.current = '';
                    ts.push({ task: '答案生成', strategy: 'free_plan', kind: 'answer', draft: '', reason: reasoning || undefined });
                    idx = ts.length - 1;
                  }
                  ts[idx] = { ...ts[idx], draft: (ts[idx].draft || '') + (tk.token || '') };
                  messages[i].payload = { ...(messages[i].payload || {}), thinkStream: ts };
                  break;
                }
              }
              return { ...s, messages };
            }));
            return;
          }

          // 兼容旧版 decision 事件（kind=decision，有 token 字段）
          if (tk.kind === 'decision' && tk.token) {
            setSessions((prev) => prev.map((s) => {
              if (s.id !== sid) return s;
              const messages = s.messages.map((m) => ({ ...m }));
              for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].role === 'assistant' && messages[i].loading) {
                  const ts = [...(messages[i].payload?.thinkStream || [])];
                  const _tcid = (tk as any).tool_call_id;
                  let targetIdx = -1;
                  if (_tcid) {
                    for (let j = ts.length - 1; j >= 0; j--) {
                      if (ts[j].tool_call_id === _tcid) { targetIdx = j; break; }
                    }
                  } else if (tk.task) {
                    for (let j = ts.length - 1; j >= 0; j--) {
                      if (!ts[j].tool_call_id && ts[j].task === tk.task) { targetIdx = j; break; }
                    }
                  }
                  if (targetIdx === -1) {
                    ts.push({ task: tk.task || '', strategy: 'free_plan', kind: 'decision', live_reason: '', tool_call_id: _tcid || undefined });
                    targetIdx = ts.length - 1;
                  }
                  ts[targetIdx] = { ...ts[targetIdx], live_reason: (ts[targetIdx].live_reason || '') + tk.token };
                  if (_tcid && !ts[targetIdx].tool_call_id) ts[targetIdx].tool_call_id = _tcid;
                  if (tk.kind && !ts[targetIdx].kind) ts[targetIdx].kind = tk.kind;
                  messages[i].payload = { ...(messages[i].payload || {}), thinkStream: ts };
                  break;
                }
              }
              return { ...s, messages };
            }));
            return;
          }
        },
        (sqlResult) => {
          // 按 step_id 归属到对应执行步骤(不覆盖, 剧本多步 execute_sql 各存各的); 同时保留顶部最后一次结果
          // 注意: stepId 是步骤序号(定位 thinkStream 项), 不要与外层会话 sid(会话UUID)混淆——
          // 旧代码此处 const sid = step_id 会遮蔽外层 sid, 导致 s.id !== sid 恒真, 结果永远挂不上步骤。
          const stepId = (sqlResult as any).step_id;
          setSessions((prev) => prev.map((s) => {
            if (s.id !== sid) return s;
            const messages = s.messages.map((m) => ({ ...m }));
            for (let i = messages.length - 1; i >= 0; i--) {
              if (messages[i].role === 'assistant' && messages[i].loading) {
                const ts = [...(messages[i].payload?.thinkStream || [])];
                if (stepId != null) {
                  const idx = ts.findIndex((t: any) => t.step_id === stepId);
                  if (idx >= 0) ts[idx] = { ...ts[idx], sql_result: sqlResult };
                }
                messages[i].payload = { ...(messages[i].payload || {}), thinkStream: ts, sql_result: sqlResult };
                break;
              }
            }
            return { ...s, messages };
          }));
        },
        (trace) => {
          if (!trace.detail) return;
          setSessions((prev) => prev.map((s) => {
            if (s.id !== sid) return s;
            const messages = s.messages.map((m) => ({ ...m }));
            for (let i = messages.length - 1; i >= 0; i--) {
              if (messages[i].role === 'assistant' && messages[i].loading) {
                const traces = [...(messages[i].payload?.traceLogs || []), trace];
                messages[i].payload = { ...(messages[i].payload || {}), traceLogs: traces };
                break;
              }
            }
            return { ...s, messages };
          }));
        },
        (intent) => {
          // 意图理解卡：任务+过滤条件，置顶显示让用户一眼确认AI听懂了
          patchAssistant({ intent });
        },
        (filterCheck) => {
          // 过滤对照：实际SQL的WHERE + 行数，与用户过滤意图对照
          patchAssistant({ filter_check: filterCheck });
        },
        (route) => {
          // 受控 Skill 问答平台 v2：确定性路由结果（RouteCard）
          patchAssistant({ route });
        },
        (contract) => {
          // 受控执行契约（五张业务卡数据源）
          patchAssistant({ contract });
        },
        (contractUpdate) => {
          // 评审 P1-3：运行中引擎确认/复合终止实时更新契约（五卡即时刷新，不等 done）
          if (contractUpdate && contractUpdate.contract) {
            patchAssistant({ contract: contractUpdate.contract });
          }
        },
        (policyEvent) => {
          // 策略拒绝/阻断：实时追加去重到 payload（评审 P2：不再覆盖前一条）
          accumulateAssistantEvent('policy_events', policyEvent);
          // S5（HITL v2）：policy.interrupt -> 置 hitl_interrupt，loading 分支渲染「批准/拒绝」横条
          if (policyEvent && policyEvent.kind === 'policy.interrupt' && policyEvent.interrupt_id) {
            patchAssistant({
              hitl_interrupt: {
                interrupt_id: policyEvent.interrupt_id,
                reason: policyEvent.reason || '',
                proposal: policyEvent.proposal || '',
                tool_name: policyEvent.tool_name || '',
                error_class: policyEvent.error_class || '',
                thread_id: sid,
              },
            });
          }
        },
        (templateEvent) => {
          // 模板绑定/漂移：实时追加去重到 payload（评审 P2）
          accumulateAssistantEvent('template_events', templateEvent);
        },
        (v) => {
          // 融合 M3 G7：G4 验证结论（query_verified）实时写 payload
          patchAssistant({ verification_live: v.verification || null, confidence: v.confidence || undefined });
        },
        (r) => {
          // 融合 M3 G7：Rubric 自评状态（rubric 事件）实时写 payload
          patchAssistant({ rubric_live: r || null });
        },
        (fr) => {
          // S3b（G9）：追问改写透明性 —— 最终答案上方渲染「理解为：xxx」
          if (fr && fr.original && fr.rewritten && fr.rewritten !== fr.original) {
            patchAssistant({ followup_rewritten: { original: fr.original, rewritten: fr.rewritten } });
          }
        },
      );
      abortControllerRef.current = controller;
    });
  };

  const applyResponse = (sid: string, resp: ChatResponse, userText?: string) => {
    setSessions((prev) => {
      const sess = prev.find((s) => s.id === sid);
      if (!sess) return prev;
      const messages = sess.messages.map((m) => ({ ...m }));
      const title = (sess.title === '新对话' && userText) ? userText.slice(0, 20) : sess.title;
      // v3.5: 保留 loading 占位消息的 live thinkStream（含 LLM 推理条目，比后端 think_stream 更全；
      // 后端 think_stream 只含行动条目，直接替换会丢失推理步骤）
      let liveThinkStream: any[] = [];
      // P0-fix: 兜底答案优先级 done.final_answer → loading.payload.final_answer → answer draft → 失败提示
      // final 事件已通过 patchAssistant 写入 payload.final_answer；answer_committed 也已写入。
      // done 若 resp.final_answer 为空，必须保留已写入的答案，不能覆盖为空。
      let payloadFinalAnswer = '';
      // 评审 P1-1（三轮）：完成态继承 loading payload 的运行治理状态——
      // policy_events/template_events（执行期间追加去重）必须随历史消息保存，
      // 否则 loading 消息被最终消息替换后，折叠条徽标与展开后的审计事件全部丢失。
      let loadingPayload: ChatMessagePayload | undefined;
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant' && messages[i].loading) {
          liveThinkStream = messages[i].payload?.thinkStream || [];
          payloadFinalAnswer = messages[i].payload?.final_answer || '';
          loadingPayload = messages[i].payload;
          break;
        }
      }
      // 批1-A: 兜底优先级 done.final_answer → loading.payload.final_answer → streaming_answer → answer draft
      // （final 事件已写入 payload，done.final_answer 为空时保留，不覆盖为空）
      const finalAnswer = resolveFinalAnswer(resp.final_answer, payloadFinalAnswer, liveThinkStream, loadingPayload?.streaming_answer);
      // v3.5: 不再"实时非空就完全放弃后端快照"。改为按 ID 合并：
      // live 保留 live_reason/决策步骤，backend 补 result_status/phase/duration_ms/result_summary
      const backendThink = resp.think_stream || sess.thinkStream || [];
      let mergedThink: any[];
      if (liveThinkStream.length > 0 && backendThink.length > 0) {
        // 按 tool_call_id / step_id 合并：live 为基底，backend 补终态字段
        mergedThink = liveThinkStream.map((t: any) => {
          const bStep = backendThink.find((b: any) =>
            (b.tool_call_id && b.tool_call_id === t.tool_call_id) ||
            (b.step_id != null && b.step_id === t.step_id));
          if (bStep) {
            // backend 有权威的 result_status/phase/duration_ms/result_summary
            const merged = { ...t, ...bStep, live_reason: t.live_reason || bStep.live_reason };
            // 保护 live 的 rejected 状态：后端 think_stream 可能标 done，不应覆盖 rejected
            if (t.phase === 'rejected' || t.result_status === 'rejected') {
              merged.phase = 'rejected';
              merged.result_status = 'rejected';
            }
            return merged;
          }
          return t;
        });
        // 补上 backend 有但 live 没有的步骤
        for (const b of backendThink) {
          const exists = mergedThink.some((t: any) =>
            (t.tool_call_id && t.tool_call_id === b.tool_call_id) ||
            (t.step_id != null && t.step_id === b.step_id));
          if (!exists) mergedThink.push(b);
        }
      } else {
        mergedThink = liveThinkStream.length > 0 ? liveThinkStream : backendThink;
      }
      // v3.5 终态兜底：所有 running/drafting/committed 步骤强制 done（防遗漏完成事件）
      mergedThink = mergedThink.map((t: any) => {
        if (t.phase === 'running' || t.phase === 'drafting' || t.phase === 'committed') {
          return { ...t, phase: 'done', result_status: t.result_status === 'error' ? 'error' : (t.result_status || 'done') };
        }
        return t;
      });
      // v3.5: 答案草稿保留（不再清除）-- 完成后 ThinkStream 仍显示推理过程
      // phase:'done' 时 ThinkStream 自动停光标，文字保留作为推理记录
      const assistantPayload: ChatMessagePayload = {
        thinkStream: mergedThink,
        final_answer: finalAnswer,
        final_answer_structured: resp.final_answer_structured,
        final_delivery: (resp as any).final_delivery || null,
        response_format_degraded: (resp as any).response_format_degraded || false,
        sql_result: (resp as any).sql_result || null,
        recommendations: resp.recommendations || [],
        confirmed: resp.confirmed || {},
        // 受控 Skill 问答平台 v2：路由+契约（五张业务卡）
        // 优先用后端 done 快照；缺失时继承 loading payload 的流式最新值（含 contract_update 后的契约）
        route: (resp as any).route ?? loadingPayload?.route ?? null,
        contract: (resp as any).contract ?? loadingPayload?.contract ?? null,
        // 评审 P1-1（三轮）：事件随历史消息持久化 —— 完成态继承执行期间累积的策略/模板事件
        policy_events: loadingPayload?.policy_events || [],
        template_events: loadingPayload?.template_events || [],
        // 融合 M3 G7：证据链（done 快照，缺省回退实时继承的验证/自评）
        evidence: (resp as any).evidence ?? {
          route: (resp as any).route?.route_type ?? loadingPayload?.route?.route_type ?? null,
          verification: loadingPayload?.verification_live ?? null,
          rubric: loadingPayload?.rubric_live
            ? { status: loadingPayload?.rubric_live.status, iterations: loadingPayload?.rubric_live.iterations }
            : null,
          corrections: 0,
        } ?? null,
        confidence: (resp as any).confidence ?? loadingPayload?.confidence ?? null,
        // 批3-F：分段计时外露（done 载荷 timing -> payload，置信度徽标悬停显示）
        timing: (resp as any).timing ?? loadingPayload?.timing ?? undefined,
      };
      // 统一最终交付视图：模型无文本但确有查询数据时，用交付摘要兜底主区文字
      const deliveryView = buildFinalDeliveryView(assistantPayload);
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        // P0-fix: 用兜底答案（done.final_answer → loading.payload.final_answer → answer draft），
        // 空时再退回交付摘要行，最后才显示失败提示，避免"已生成结果但主区为空"
        text: finalAnswer || deliveryView.deliverySummaryLine || '（自由规划未生成最终答案，可能因 LLM 连接中断。请查看上方思考步骤或重试）',
        loading: false,
        payload: assistantPayload,
      };
      // 把 loading 占位消息替换为最终消息
      let replaced = false;
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant' && messages[i].loading) {
          messages[i] = assistantMsg;
          replaced = true;
          break;
        }
      }
      if (!replaced) messages.push(assistantMsg);
      return prev.map((s) => s.id === sid ? {
        ...s,
        messages,
        confirmed: resp.confirmed || {},
        flags: resp.flags || {},
        lastResponse: resp,
        goal: resp.goal,
        currentTask: resp.current_task,
        liveStatus: '',
        liveMetaInfo: '',
        finalTokens: [],
        finalAnswer: finalAnswer,
        recommendations: resp.recommendations || [],
        title,
      } : s);
    });
  };

  const finalizePlaceholderMessage = (sid: string, text = '已停止生成') => {
    setSessions((prev) => prev.map((s) => {
      if (s.id !== sid) return s;
      const messages = s.messages.map((m) => ({ ...m }));
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant' && messages[i].loading) {
          messages[i].loading = false;
          messages[i].text = text;
          break;
        }
      }
      return { ...s, messages };
    }));
  };

  const handleStop = () => {
    stoppedRef.current = true;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    // v3.4: 停止时冲刷 + 清理 rAF/缓冲
    flushTokens();
    if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = 0; }
    tokenBufRef.current.clear();
    closedRoundsRef.current.clear();
    setStatus('stopped');
    if (activeSession) {
      finalizePlaceholderMessage(activeSession.id);
    }
  };

  // v3.4 rAF 批量刷新 token 缓冲到 setSessions（避免每个 token 一次重渲染）
  const flushTokens = () => {
    rafRef.current = 0;
    const buf = tokenBufRef.current;
    if (buf.size === 0) return;
    tokenBufRef.current = new Map();  // 原子换出
    const _sid = streamingSidRef.current;
    setSessions((prev) => prev.map((s) => {
      if (s.id !== _sid) return s;  // v3.5: 只写当前流式会话，防多会话串流
      const messages = s.messages.map((m) => ({ ...m }));
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant' && messages[i].loading) {
          const ts = [...(messages[i].payload?.thinkStream || [])];
          for (const [roundId, tokens] of Array.from(buf)) {
            if (closedRoundsRef.current.has(roundId)) continue;  // 已关闭 round 的旧 delta 丢弃
            const kind = tokens[0]?.kind || 'decision_draft';
            const combined = tokens.map((t: { kind: string; text: string }) => t.text).join('');
            if (kind === 'answer_draft') {
              // 交付体验演进 v2（用户定调）：批1-A 双写回退——answer_draft token 全部丢弃，
              // 不再写 streaming_answer/气泡；仅驱动状态机「答案生成中…」。
              // 正文唯一来源 = done 时的结构化渲染，裸文本期从机制上不可能发生。
              const roundChanged = !!lastAnswerRoundRef.current
                && lastAnswerRoundRef.current !== roundId
                && !!messages[i].payload?.answer_committed;   // rubric 修订：新一轮答案
              messages[i].payload = {
                ...(messages[i].payload || {}),
                answer_generating: true,   // 状态机：「答案生成中…」
                answer_revising: roundChanged ? true : (messages[i].payload?.answer_revising || false),
              };
              lastAnswerRoundRef.current = roundId;
              // ThinkStream 的 answer 项只保留状态步骤（不存全文）
              let ansIdx = ts.findIndex((t: any) => t.kind === 'answer');
              if (ansIdx === -1) {
                ts.push({ task: '答案生成', strategy: 'free_plan', kind: 'answer', phase: 'drafting', round_id: roundId, draft: '' });
              } else {
                ts[ansIdx] = { ...ts[ansIdx], phase: 'drafting', draft: '' };
              }
              continue;
            }
            const field = 'live_reason';
            const stepKind = 'decision';
            // decision_draft: 每个决策是独立步骤，按 round_id 归并
            let idx = ts.findIndex((t: any) => t.round_id === roundId);
            if (idx === -1) {
              ts.push({ task: '', strategy: 'free_plan', kind: stepKind, phase: 'drafting', round_id: roundId, [field]: '' });
              idx = ts.length - 1;
            }
            ts[idx] = { ...ts[idx], [field]: (ts[idx][field] || '') + combined };
          }
          messages[i].payload = { ...(messages[i].payload || {}), thinkStream: ts };
          break;
        }
      }
      return { ...s, messages };
    }));
  };

  const handleSubmit = async () => {
    if (!question.trim() || isBusy) return;
    const userText = question.trim();
    // 没有活跃会话时，发送第一条消息才正式创建会话
    let sid = activeSession?.id;
    if (!sid) {
      sid = createNewSession();
    }
    setQuestion('');

    const userMsg: ChatMessage = { id: `user-${Date.now()}`, role: 'user', text: userText };
    const assistantPlaceholder: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      text: '正在思考...',
      loading: true,
      payload: { thinkStream: [], finalTokens: [], live_text: '', live_meta: '' },
    };
    const sess = sessions.find((s) => s.id === sid);
    updateSession(sid, { messages: [...(sess?.messages || []), userMsg, assistantPlaceholder], thinkStream: [], finalTokens: [], finalAnswer: '', recommendations: [], liveStatus: '', liveMetaInfo: '', confirmed: {}, flags: {} });

    stoppedRef.current = false;
    setStatus('submitted');
    const resp = await callBackend(sid, userText);
    const wasStopped = stoppedRef.current;
    stoppedRef.current = false;
    abortControllerRef.current = null;
    // v3.4: SSE 结束/停止时冲刷残留 token + 清理 rAF + 清空缓冲
    flushTokens();
    if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = 0; }
    tokenBufRef.current.clear();
    closedRoundsRef.current.clear();
    if (wasStopped) {
      setStatus('ready');
      return;
    }
    setStatus('ready');
    if (!resp) return;
    applyResponse(sid, resp, userText);
  };

  const handleRecommendationSelect = useCallback((rec: any) => {
    setQuestion(rec.shortcut || rec.label);
  }, [setQuestion]);

  // 稳定引用：避免内联箭头导致消息列表项 React.memo 失效
  const handleDeleteMessage = useCallback(
    (msgId: string) => deleteMessage(activeSessionId, msgId),
    [activeSessionId, deleteMessage],
  );

  // S5（HITL v2）：批准/拒绝人审中断 -> POST /chat/freeplan/resume（服务端据此恢复同 thread 续跑）
  // 稳定引用（useCallback + 仅依赖状态 setter），保证消息行 memo 不失效；线程 id 由调用方（消息 payload）携带。
  const handleHITLDecision = useCallback(async (interruptId: string, approve: boolean) => {
    try {
      const res = await dataIntelligenceApi.resumeInterrupt({ interrupt_id: interruptId, approve, thread_id: activeSessionId });
      if (res && res.code === 200) {
        message.success(approve ? '已批准，正在继续查询…' : '已拒绝，按原流程继续');
      } else {
        message.warning((res && res.message) || '恢复请求未命中（可能已超时/已处理）');
      }
    } catch (e) {
      console.error('[HITL] resume 失败', e);
      message.error('恢复请求发送失败');
    }
  }, [activeSessionId]);

  const CONTENT_WIDTH = 1200;

  // 输入卡片（两种状态共用；B2 美化：S3 阴影 + 聚焦主色描边环 + 渐变发送钮）
  const inputCard = (
    <div
      className="dal-composer"
      style={{
        borderRadius: 12,
        border: '1px solid var(--color-border)',
        background: 'var(--bg-content)',
        overflow: 'hidden',
        boxShadow: tokens.elevation.s3,
      }}
    >
      <Input.TextArea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        rows={2}
        placeholder={card?.ui_config?.placeholder ?? '想问什么数据？'}
        autoSize={{ minRows: 2, maxRows: 6 }}
        bordered={false}
        onPressEnter={(e) => {
          if (!e.shiftKey) {
            e.preventDefault();
            if (!isBusy && question.trim()) handleSubmit();
          }
        }}
        style={{ padding: '14px 16px 4px', resize: 'none' }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '2px 8px 6px 12px' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Select
            size="small"
            variant="borderless"
            style={{ width: 130, fontSize: 12 }}
            placeholder="模型"
            allowClear
            value={llmConnectionId}
            onChange={(v) => setLlmConnectionId(v)}
            options={llmConnections.map((c: any) => ({ label: c.name || c.model_name || c.id, value: c.id }))}
            popupMatchSelectWidth={180}
          />
          <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Shift+Enter 换行</span>
          <Button
            size="small"
            type="text"
            icon={<ExperimentOutlined />}
            style={{ fontSize: 12, color: 'var(--text-tertiary)' }}
            onClick={() => setSimOpen(true)}
          >
            审计模拟
          </Button>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {isBusy ? (
            /* P3 修正：Stop 白底红边（规格），非 antd danger 实心 */
            <Button
              size="small"
              icon={<StopOutlined />}
              onClick={handleStop}
              aria-label="停止生成"
              style={{ background: 'var(--bg-content)', borderColor: tokens.colors.error, color: tokens.colors.error, width: 32, height: 32, borderRadius: tokens.radius.card }}
            />
          ) : (
            /* P3 修正：发送钮方形 32 / r8（规格），渐变填充保持 */
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              className="dal-send-btn"
              onClick={handleSubmit}
              disabled={!question.trim()}
              aria-label="发送"
              style={{ background: tokens.brandGradient, borderColor: 'transparent', width: 32, height: 32, borderRadius: tokens.radius.card }}
            />
          )}
        </div>
      </div>
    </div>
  );

  // ⑥ 专家地基①：卡 loading 期间 Spin；卡读失败上屏（不降级 wenshu，spec §十）
  if (cardError) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
        <div style={{ fontSize: 16, color: 'var(--text-secondary)' }}>{cardError}</div>
        <Button type="primary" onClick={() => navigate('/', { replace: true })}>返回专家门户</Button>
      </div>
    );
  }
  if (!card) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" tip="正在加载专家卡…" />
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-page)' }}>
      {/* 批13-P：受控路由模拟器收进「审计模拟」按钮（Drawer），不再常驻问答页顶部 */}
      <Drawer
        title={<Space><ExperimentOutlined /> 受控路由模拟器（审计）</Space>}
        placement="right"
        width={560}
        open={simOpen}
        onClose={() => setSimOpen(false)}
        destroyOnClose
      >
        <RouteSimulator />
      </Drawer>
      {hasMessages ? (
        /* 有消息：消息列表 + 底部输入框 */
        <>
          <div ref={chatContainerRef} onScroll={handleChatScroll} style={{ flex: 1, minHeight: 0, overflowY: 'auto', position: 'relative' }}>
            <div style={{ maxWidth: CONTENT_WIDTH, margin: '0 auto', padding: '16px 24px' }}>
              {(activeSession?.messages?.length || 0) > 0 ? (
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
                  <Popconfirm title="清空当前会话所有消息？" okText="清空" cancelText="取消" onConfirm={async () => {
                    const ok = await clearMessages(activeSessionId);
                    if (!ok) message.warning('服务端记忆清理失败，当前会话未清空，下次问答可能仍受旧上下文影响');
                  }}>
                    <Button size="small" type="text" icon={<ClearOutlined />} style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>清空会话</Button>
                  </Popconfirm>
                </div>
              ) : null}
              <ConversationMessageList
                messages={activeSession?.messages || []}
                sceneConfig={DATA_INTELLIGENCE_SCENE_CONFIG}
                loading={isBusy}
                liveStatus={activeSession?.liveStatus}
                liveTokens={activeSession?.finalTokens}
                liveFinalAnswer={activeSession?.finalAnswer}
                liveRecommendations={activeSession?.recommendations}
                liveMetaInfo={activeSession?.liveMetaInfo}
                confirmedData={confirmed}
                onSelectRecommendation={handleRecommendationSelect}
                onDeleteMessage={handleDeleteMessage}
                onHITLDecision={handleHITLDecision}
              />
            </div>
          </div>
          {/* B2 美化：滚动到底圆钮（不在底部时浮出，S2 阴影） */}
          {showScrollDown ? (
            <div style={{ position: 'relative', flexShrink: 0, height: 0 }}>
              <Button
                shape="circle"
                icon={<ArrowDownOutlined />}
                onClick={scrollToBottom}
                aria-label="滚动到底部"
                style={{
                  position: 'absolute', right: 28, bottom: 18, zIndex: 20,
                  boxShadow: tokens.elevation.s2, background: 'var(--bg-content)',
                  color: tokens.colors.primary, borderColor: tokens.colors.border,
                }}
              />
            </div>
          ) : null}
          <div style={{ flexShrink: 0, maxWidth: CONTENT_WIDTH, width: '100%', margin: '0 auto', padding: '0 24px 16px' }}>
            {inputCard}
          </div>
        </>
      ) : (
        /* 欢迎页（B2 美化）：渐变主视觉 + 统计胶囊 + 2×2 建议卡 + 悬浮 composer */
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: 24, overflowY: 'auto' }}>
          {/* 主视觉：display 字号 + brand-gradient 渐变文字 */}
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <div
              style={{
                fontSize: tokens.fontSize.display,
                fontWeight: 700,
                letterSpacing: '-0.02em',
                background: tokens.brandGradient,
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                color: 'transparent',
                lineHeight: 1.3,
              }}
            >
              {card?.ui_config?.welcome?.title ?? '数据资产探查'}
            </div>
            <div style={{ marginTop: 8, fontSize: 14, color: 'var(--text-tertiary)' }}>
              {card?.ui_config?.welcome?.tagline ?? '一句话问数 · 受控执行 · 全程可审计'}
            </div>
            {/* ⑤补补-2：tutor 欢迎语动态数（画像聚合 /api/tutor/profile——N 题待复习/M 天连续） */}
            {slug === 'tutor' && tutorProfile && (tutorProfile.due_count > 0 || tutorProfile.streak_days > 0) && (
              <div style={{ marginTop: 6, fontSize: 13, color: tokens.colors.info }}>
                今日有 {tutorProfile.due_count} 题待复习，已连续学习 {tutorProfile.streak_days} 天
              </div>
            )}
          </div>

          {/* 统计胶囊（S1 卡：图标 + tabular-nums 数字 + 12px 说明） */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
            {[
              { label: '主数据实体', value: stats.master, icon: <DatabaseOutlined />, color: tokens.colors.primary },
              { label: '业务实体', value: stats.business, icon: <ApartmentOutlined />, color: tokens.colors.ai },
              { label: '关系', value: stats.relation, icon: <ShareAltOutlined />, color: tokens.colors.info },
            ].map((c) => (
              <div
                key={c.label}
                className="dal-stat-capsule"
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 18px', borderRadius: tokens.radius.card,
                  background: 'var(--bg-content)',
                  border: `1px solid ${tokens.colors.border}`,
                  boxShadow: tokens.elevation.s1,
                }}
              >
                <span style={{ color: c.color, fontSize: 16, display: 'inline-flex' }}>{c.icon}</span>
                <div>
                  <div className="dal-num" style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}>{c.value}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{c.label}</div>
                </div>
              </div>
            ))}
          </div>

          {/* 悬浮 composer（S3 阴影 + 聚焦主色描边环；规格 maxWidth 720） */}
          <div style={{ width: '100%', maxWidth: 720, marginBottom: 24 }}>
            {inputCard}
          </div>

          {/* 2×2 建议卡（带图标，hover 抬升 S2；规格 maxWidth 720） */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10, width: '100%', maxWidth: 720 }}>
            {SUGGESTIONS.map((item, i) => (
              <div
                key={`suggest-${i}`}
                role="button"
                tabIndex={0}
                onClick={() => setQuestion(item)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setQuestion(item); } }}
                className="dal-suggest-card"
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '12px 14px', borderRadius: tokens.radius.card,
                  background: 'var(--bg-content)',
                  border: `1px solid ${tokens.colors.border}`,
                  boxShadow: tokens.elevation.s1,
                  cursor: 'pointer',
                  transition: `box-shadow ${tokens.motion.duration.fast}ms ${tokens.motion.easing.enter}`,
                }}
              >
                <span style={{ color: tokens.colors.primary, fontSize: 15, display: 'inline-flex' }}>{FREEPLAN_SUGGEST_ICONS[i]}</span>
                <Text style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6 }}>{item}</Text>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExpertChat;
