/**
 * 数据资产探查 - ChatGPT 式居中落地页
 *
 * 空会话：居中欢迎语（含纳管统计）+ 居中输入框
 * 有消息：消息列表 + 底部输入框
 * 侧边栏「数据资产探查」= 新建会话
 */
import React, { useEffect, useRef, useState } from 'react';
import { Button, Input, Select, Space, Typography, message } from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import ConversationMessageList from '../components/conversation/ConversationMessageList';
import { DATA_INTELLIGENCE_SCENE_CONFIG } from '../components/conversation/sceneConfigs';
import {
  dataIntelligenceApi,
  ChatResponse,
  UserSelectionPayload,
} from '../services/dataIntelligenceApi';
import { llmAdminApi, sourceTableApi } from '../services/api';
import { useStore } from '../store/useStore';
import type { ChatMessage } from '../components/conversation/types';

const { Text } = Typography;

const MODE = 'free_plan' as const;

const FREEPLAN_EXAMPLE_QUERIES = [
  '统计用电客户总数',
  '什么是变压器',
  '配电变压器有哪些？列出编号和名称',
  '用电客户数据的来源',
];

type ChatStatus = 'ready' | 'submitted' | 'streaming' | 'error' | 'stopped';

const FreePlanChat: React.FC = () => {
  // Session 状态来自 Zustand store（与 AppSider 共享）
  const sessions = useStore((s) => s.sessions);
  const activeSessionId = useStore((s) => s.activeSessionId);
  const setSessions = useStore((s) => s.setSessions);
  const updateSession = useStore((s) => s.updateSession);
  const createNewSession = useStore((s) => s.createNewSession);

  // 本地状态（仅对话相关）
  const [question, setQuestion] = useState('');
  const [status, setStatus] = useState<ChatStatus>('ready');
  const [llmConnectionId, setLlmConnectionId] = useState<string | undefined>(undefined);
  const [llmConnections, setLlmConnections] = useState<any[]>([]);
  const [stats, setStats] = useState<{ master: string; business: string; relation: string }>({ master: '-', business: '-', relation: '-' });

  const abortControllerRef = useRef<AbortController | null>(null);
  const stoppedRef = useRef(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

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

      const controller = dataIntelligenceApi.freePlanChatStream(
        {
          thread_id: sid,
          user_input: userText,
          user_selection: userSelection,
          format: 'card',
          llm_connection_id: llmConnectionId,
          mode: MODE,
        },
        (thinkItem) => {
          setSessions((prev) => prev.map((s) => {
            if (s.id !== sid) return s;
            const taskKey = thinkItem.task || '';
            const existIdx = s.thinkStream.findIndex((t) => (t.task || '') === taskKey);
            let newThink: any[];
            if (existIdx >= 0) {
              newThink = s.thinkStream.map((t, idx) => idx === existIdx
                ? { ...t, ...thinkItem, live_reason: t.live_reason || thinkItem.live_reason }
                : t);
            } else {
              newThink = [...s.thinkStream, thinkItem];
            }
            const messages = s.messages.map((m) => ({ ...m }));
            for (let i = messages.length - 1; i >= 0; i--) {
              if (messages[i].role === 'assistant' && messages[i].loading) {
                messages[i].payload = { ...(messages[i].payload || {}), thinkStream: newThink };
                break;
              }
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
          patchAssistant({ final_answer: final.answer });
        },
        (rec) => {
          patchAssistant({ recommendations: rec.questions });
        },
        (tk) => {
          setSessions((prev) => prev.map((s) => {
            if (s.id !== sid) return s;
            const messages = s.messages.map((m) => ({ ...m }));
            let ts: any[] = [];
            for (let i = messages.length - 1; i >= 0; i--) {
              if (messages[i].role === 'assistant' && messages[i].loading) {
                ts = [...(messages[i].payload?.thinkStream || [])];
                let targetIdx = -1;
                if (tk.task) {
                  for (let j = ts.length - 1; j >= 0; j--) {
                    if (ts[j].task === tk.task) { targetIdx = j; break; }
                  }
                }
                if (targetIdx === -1) {
                  const newItem: any = { task: tk.task || '', strategy: 'free_plan', action: tk.task || '', kind: tk.kind || 'decision', live_reason: '' };
                  ts.push(newItem);
                  targetIdx = ts.length - 1;
                }
                ts[targetIdx] = { ...ts[targetIdx], live_reason: (ts[targetIdx].live_reason || '') + tk.token };
                // 同步 kind（行动事件重建时会话级缺推理条目，导致推理被覆盖；这里统一同步会话级+消息级）
                if (tk.kind && !ts[targetIdx].kind) ts[targetIdx].kind = tk.kind;
                messages[i].payload = { ...(messages[i].payload || {}), thinkStream: ts };
                break;
              }
            }
            return { ...s, thinkStream: ts, messages };
          }));
        },
        (sqlResult) => {
          patchAssistant({ sql_result: sqlResult });
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
      // 保留 loading 占位消息的 live thinkStream（含 LLM 推理条目，比后端 think_stream 更全；
      // 后端 think_stream 只含行动条目，直接替换会丢失推理步骤）
      let liveThinkStream: any[] = [];
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant' && messages[i].loading) {
          liveThinkStream = messages[i].payload?.thinkStream || [];
          break;
        }
      }
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        text: resp.final_answer || '（自由规划未生成最终答案，可能因 LLM 连接中断。请查看上方思考步骤或重试）',
        loading: false,
        payload: {
          thinkStream: liveThinkStream.length > 0 ? liveThinkStream : (resp.think_stream || sess.thinkStream),
          final_answer: resp.final_answer || '',
          final_answer_structured: resp.final_answer_structured,
          sql_result: (resp as any).sql_result || null,
          recommendations: resp.recommendations || [],
          confirmed: resp.confirmed || {},
        },
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
        finalAnswer: resp.final_answer || '',
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
    setStatus('stopped');
    if (activeSession) {
      finalizePlaceholderMessage(activeSession.id);
    }
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
    if (wasStopped) {
      setStatus('ready');
      return;
    }
    setStatus('ready');
    if (!resp) return;
    applyResponse(sid, resp, userText);
  };

  const handleRecommendationSelect = (rec: any) => {
    setQuestion(rec.shortcut || rec.label);
  };

  const CONTENT_WIDTH = 1200;

  // 输入卡片（两种状态共用）
  const inputCard = (
    <div style={{
      borderRadius: 12,
      border: `1px solid var(--color-border)`,
      background: 'var(--bg-content)',
      overflow: 'hidden',
      boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
    }}>
      <Input.TextArea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        rows={2}
        placeholder="输入要探查的问题..."
        autoSize={{ minRows: 2, maxRows: 6 }}
        bordered={false}
        onPressEnter={(e) => {
          if (!e.shiftKey) {
            e.preventDefault();
            if (!isBusy && question.trim()) handleSubmit();
          }
        }}
        style={{ padding: '12px 16px 4px', resize: 'none' }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '2px 8px 6px 12px' }}>
        <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Shift+Enter 换行</span>
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
          {isBusy ? (
            <Button type="primary" danger size="small" shape="circle" icon={<StopOutlined />} onClick={handleStop} />
          ) : (
            <Button type="primary" size="small" shape="circle" icon={<PlayCircleOutlined />} onClick={handleSubmit} disabled={!question.trim()} />
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-page)' }}>
      {hasMessages ? (
        /* 有消息：消息列表 + 底部输入框 */
        <>
          <div ref={chatContainerRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
            <div style={{ maxWidth: CONTENT_WIDTH, margin: '0 auto', padding: '16px 24px' }}>
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
              />
            </div>
          </div>
          <div style={{ flexShrink: 0, maxWidth: CONTENT_WIDTH, width: '100%', margin: '0 auto', padding: '0 24px 16px' }}>
            {inputCard}
          </div>
        </>
      ) : (
        /* 欢迎页：欢迎语 + 示例 + 输入框，整体上下居中 */
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: 24 }}>
          <div style={{ textAlign: 'center', marginBottom: 24, maxWidth: 600 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
            <Text strong style={{ fontSize: 20, display: 'block', marginBottom: 8 }}>
              欢迎探索数据资产
            </Text>
            <Text type="secondary" style={{ fontSize: 14, lineHeight: 1.8 }}>
              当前纳管 <b style={{ color: 'var(--text-primary)' }}>{stats.master}</b> 主数据实体、<b style={{ color: 'var(--text-primary)' }}>{stats.business}</b> 业务实体、<b style={{ color: 'var(--text-primary)' }}>{stats.relation}</b> 关系，请开始你的畅游吧
            </Text>
          </div>
          <Space wrap size="small" style={{ justifyContent: 'center', maxWidth: 600, marginBottom: 24 }}>
            {FREEPLAN_EXAMPLE_QUERIES.map((item) => (
              <Button
                key={`example-${item}`}
                size="small"
                onClick={() => setQuestion(item)}
                style={{ borderRadius: 16, fontSize: 12, color: 'var(--text-secondary)', borderColor: 'var(--color-border)' }}
              >
                {item}
              </Button>
            ))}
          </Space>
          <div style={{ width: '100%', maxWidth: 800 }}>
            {inputCard}
          </div>
        </div>
      )}
    </div>
  );
};

export default FreePlanChat;
