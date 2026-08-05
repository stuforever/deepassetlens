import { useEffect, useRef, useState } from 'react';
import { message } from 'antd';
import { runApi } from '../../services/api';
import type { ChatMessage, ChatMessagePayload, ConversationBlock, ConversationCard, ConversationSceneConfig, ConversationSubmitOptions, RunEventRecord, RuntimeContextRecord } from './types';

const defaultExtractAssistantPayload = (runData: any, events: RunEventRecord[] = []): ChatMessagePayload => {
  const cardEvent = [...events].reverse().find((item) => item?.event_type === 'message.card');
  const contextEvent = [...events].reverse().find((item) => item?.event_type === 'context.prepared');
  const assistantDeltas = events.filter((item) => item?.event_type === 'assistant.delta');
  const blockEvents = events.filter((item) => item?.event_type === 'block.completed');
  const eventPayload = cardEvent?.payload || {};
  const directCard = eventPayload?.card as ConversationCard | undefined;
  const runCards = (runData?.output_payload?.cards || []) as ConversationCard[];
  const cards = directCard ? [directCard] : runCards;
  const liveText = (assistantDeltas[assistantDeltas.length - 1]?.payload?.text || '').trim();
  const text = eventPayload?.text || runData?.output_payload?.assistant_text || liveText || '';
  const llmError = directCard?.data?.llm_error || runData?.output_payload?.llm_error || null;
  const runtimeContext = (contextEvent?.payload?.runtime_context || runData?.output_payload?.runtime_context || null) as RuntimeContextRecord | null;
  const blocks = blockEvents
    .map((item) => item?.payload || {})
    .filter((item) => item?.block_id || item?.block_type)
    .map((item) => ({
      block_id: item.block_id,
      block_type: item.block_type,
      title: item.title,
      text: item.text,
      data: item.data,
    })) as ConversationBlock[];
  return {
    text,
    live_text: liveText || text,
    cards,
    llm_error: llmError,
    runtime_context: runtimeContext,
    blocks,
  };
};

const defaultBuildAssistantText = (payload?: ChatMessagePayload) => {
  if (payload?.live_text) return payload.live_text;
  if (payload?.text) return payload.text;
  if (payload?.llm_error) return '执行失败，请检查配置或服务状态。';
  if ((payload?.cards || []).length > 0) return '已完成执行。';
  return '已完成执行。';
};

export const useConversationRun = (sceneConfig: ConversationSceneConfig) => {
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  const closeEventSource = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };

  const updateAssistantMessage = (messageId: string, updater: (prev: ChatMessage) => ChatMessage) => {
    setMessages((prev) => prev.map((item) => (item.id === messageId ? updater(item) : item)));
  };

  const ensureConversation = async () => {
    if (conversationId) {
      return conversationId;
    }
    const res = await runApi.createConversation({
      scene_code: sceneConfig.sceneCode,
      page_code: sceneConfig.pageCode,
      title: sceneConfig.conversationTitle,
    });
    const nextConversationId = res.data?.data?.id || '';
    if (!nextConversationId) {
      throw new Error('创建统一会话失败');
    }
    setConversationId(nextConversationId);
    return nextConversationId;
  };

  const clearConversation = () => {
    closeEventSource();
    setMessages([]);
    setConversationId('');
    setLoading(false);
  };

  const submitMessage = async (args: { userText: string; runtimeState?: Record<string, any>; overrides?: Partial<ConversationSubmitOptions> }) => {
    const derivedOptions = sceneConfig.runtime?.buildSubmitOptions({
      userText: args.userText,
      runtimeState: args.runtimeState,
    }) || {};
    const options: ConversationSubmitOptions = {
      userText: args.userText,
      ...derivedOptions,
      ...(args.overrides || {}),
    };
    const userText = String(options.userText || '').trim();
    if (!userText) return;

    const buildAssistantPayload = options.buildAssistantPayload || defaultExtractAssistantPayload;
    const buildAssistantText = options.buildAssistantText || defaultBuildAssistantText;
    const userMessageId = `user-${Date.now()}`;
    const assistantMessageId = `assistant-${Date.now() + 1}`;

    setMessages((prev) => [
      ...prev,
      { id: userMessageId, role: 'user', text: userText },
      {
        id: assistantMessageId,
        role: 'assistant',
        loading: true,
        text: options.initialLoadingText || '正在创建统一 Run 并建立事件流连接...',
        payload: { stream_events: [] },
      },
    ]);
    setLoading(true);

    try {
      closeEventSource();
      const currentConversationId = await ensureConversation();
      const runRes = await runApi.createRun({
        conversation_id: currentConversationId,
        scene_code: sceneConfig.sceneCode,
        page_code: sceneConfig.pageCode,
        message: userText,
        async_mode: true,
        input_payload: options.inputPayload,
      });
      const runData = runRes.data?.data || {};
      const runId = runData.id;
      if (!runId) {
        throw new Error('统一 Run 创建失败');
      }

      const appendStreamEvent = (eventType: string, payload: any) => {
        updateAssistantMessage(assistantMessageId, (prev) => ({
          ...prev,
          payload: {
            ...(prev.payload || {}),
            stream_events: [...(prev.payload?.stream_events || []), { event_type: eventType, payload }],
          },
        }));
      };

      const upsertPayload = (updater: (prevPayload: ChatMessagePayload) => ChatMessagePayload) => {
        updateAssistantMessage(assistantMessageId, (prev) => ({
          ...prev,
          payload: updater(prev.payload || { stream_events: [] }),
        }));
      };

      const eventSource = new EventSource(runApi.getRunEventsStreamUrl(runId));
      eventSourceRef.current = eventSource;

      const listenJsonEvent = (eventName: string, handler: (payload: any) => void) => {
        eventSource.addEventListener(eventName, (event) => {
          const payload = JSON.parse((event as MessageEvent).data || '{}');
          appendStreamEvent(eventName, payload);
          handler(payload);
        });
      };

      listenJsonEvent('run.started', () => {
        updateAssistantMessage(assistantMessageId, (prev) => ({
          ...prev,
          text: options.runStartedText || '统一 Run 已创建，正在实时接收事件...',
        }));
      });

      listenJsonEvent('context.prepared', (payload) => {
        upsertPayload((prevPayload) => ({
          ...prevPayload,
          runtime_context: payload?.runtime_context || prevPayload.runtime_context || null,
          stream_events: prevPayload.stream_events || [],
        }));
      });

      listenJsonEvent('block.completed', (payload) => {
        upsertPayload((prevPayload) => ({
          ...prevPayload,
          blocks: [
            ...(prevPayload.blocks || []).filter((item) => item.block_id !== payload?.block_id),
            {
              block_id: payload?.block_id,
              block_type: payload?.block_type,
              title: payload?.title,
              text: payload?.text,
              data: payload?.data,
            },
          ],
          stream_events: prevPayload.stream_events || [],
        }));
      });

      listenJsonEvent('assistant.delta', (payload) => {
        const nextText = payload?.text || '';
        upsertPayload((prevPayload) => ({
          ...prevPayload,
          live_text: nextText,
          text: nextText,
          stream_events: prevPayload.stream_events || [],
        }));
        updateAssistantMessage(assistantMessageId, (prev) => ({
          ...prev,
          text: nextText || prev.text,
        }));
      });

      listenJsonEvent('tool.delta', () => {
        // 工具事件统一进入 stream_events，由消息区按需展示。
      });

      listenJsonEvent('step.started', (payload) => {
        if (options.stepStartedText) {
          updateAssistantMessage(assistantMessageId, (prev) => {
            const nextText = options.stepStartedText?.({ payload, prev });
            return nextText ? { ...prev, text: nextText } : prev;
          });
        }
      });

      listenJsonEvent('step.completed', (payload) => {
        if (options.stepCompletedText) {
          updateAssistantMessage(assistantMessageId, (prev) => {
            const completedCount = (prev.payload?.stream_events || []).filter((item) => item.event_type === 'step.completed').length;
            const nextText = options.stepCompletedText?.({ payload, completedCount, prev });
            return nextText ? { ...prev, text: nextText } : prev;
          });
        }
      });

      listenJsonEvent('step.failed', (payload) => {
        if (options.stepFailedText) {
          updateAssistantMessage(assistantMessageId, (prev) => {
            const nextText = options.stepFailedText?.({ payload, prev });
            return nextText ? { ...prev, text: nextText } : prev;
          });
        }
      });

      listenJsonEvent('message.card', (payload) => {
        const assistantPayload = buildAssistantPayload(runData, [{ event_type: 'message.card', payload }]);
        updateAssistantMessage(assistantMessageId, (prev) => ({
          ...prev,
          loading: false,
          text: buildAssistantText(assistantPayload),
          payload: {
            ...(prev.payload || {}),
            ...assistantPayload,
            runtime_context: assistantPayload.runtime_context || prev.payload?.runtime_context || null,
            blocks: assistantPayload.blocks || prev.payload?.blocks || [],
            stream_events: prev.payload?.stream_events || [],
          },
        }));
        const shouldShowSuccessToast = options.shouldShowSuccessToast
          ? options.shouldShowSuccessToast({ payload, assistantPayload })
          : payload?.card_type !== 'clarification';
        if (options.successToastText && shouldShowSuccessToast) {
          message.success(options.successToastText);
        }
      });

      listenJsonEvent('run.failed', (payload) => {
        closeEventSource();
        setLoading(false);
        updateAssistantMessage(assistantMessageId, (prev) => ({
          ...prev,
          loading: false,
          text: options.failedText || '执行失败，请检查配置或服务状态。',
          payload: {
            ...(prev.payload || {}),
            cards: [],
            llm_error: {
              message: payload?.message || options.failedText || '执行失败',
            },
          },
        }));
      });

      eventSource.addEventListener('stream.end', async () => {
        closeEventSource();
        const finalRunRes = await runApi.getRun(runId);
        const finalRunData = finalRunRes.data?.data || {};
        const finalEventsRes = await runApi.getRunEvents(runId);
        const finalEvents = finalEventsRes.data?.data || [];
        const assistantPayload = buildAssistantPayload(finalRunData, finalEvents);
        updateAssistantMessage(assistantMessageId, (prev) => ({
          ...prev,
          loading: false,
          text: buildAssistantText(assistantPayload),
          payload: {
            ...(prev.payload || {}),
            ...assistantPayload,
            runtime_context: assistantPayload.runtime_context || prev.payload?.runtime_context || null,
            blocks: assistantPayload.blocks || prev.payload?.blocks || [],
            stream_events: finalEvents.length > 0 ? finalEvents : prev.payload?.stream_events || [],
          },
        }));
        setLoading(false);
      });

      eventSource.onerror = async () => {
        closeEventSource();
        const finalRunRes = await runApi.getRun(runId).catch(() => null);
        const finalRunData = finalRunRes?.data?.data || {};
        const finalEventsRes = await runApi.getRunEvents(runId).catch(() => null);
        const finalEvents = finalEventsRes?.data?.data || [];
        const assistantPayload = buildAssistantPayload(finalRunData, finalEvents);
        updateAssistantMessage(assistantMessageId, (prev) => ({
          ...prev,
          loading: false,
          text:
            (assistantPayload.cards || []).length > 0 || assistantPayload.llm_error
              ? buildAssistantText(assistantPayload)
              : options.interruptedText || '事件流连接中断，请查看当前结果。',
          payload: {
            ...(prev.payload || {}),
            ...assistantPayload,
            runtime_context: assistantPayload.runtime_context || prev.payload?.runtime_context || null,
            blocks: assistantPayload.blocks || prev.payload?.blocks || [],
            stream_events: finalEvents.length > 0 ? finalEvents : prev.payload?.stream_events || [],
          },
        }));
        setLoading(false);
      };
    } catch (error: any) {
      closeEventSource();
      updateAssistantMessage(assistantMessageId, (prev) => ({
        ...prev,
        loading: false,
        text: options.failedText || '执行失败，请检查配置或服务状态。',
        payload: {
          cards: [],
          llm_error: {
            message: error?.response?.data?.detail || error?.message || options.failedText || '执行失败',
          },
        },
      }));
      setLoading(false);
      message.error(options.errorToastText || error?.response?.data?.detail || error?.message || '执行失败');
    }
  };

  return {
    loading,
    messages,
    setMessages,
    chatContainerRef,
    clearConversation,
    closeEventSource,
    submitMessage,
  };
};

export default useConversationRun;
