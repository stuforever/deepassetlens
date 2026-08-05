import type { ChatMessagePayload, ConversationSceneConfig } from './types';

const buildDefaultAssistantText = (payload?: ChatMessagePayload) => {
  if (payload?.text) return payload.text;
  if (payload?.llm_error) return '执行失败，请检查配置或服务状态。';
  if ((payload?.cards || []).length > 0) return '已完成执行。';
  return '已完成执行。';
};

export const LLM_CHAT_SCENE_CONFIG: ConversationSceneConfig = {
  sceneCode: 'llm_chat',
  pageCode: 'llmchat',
  conversationTitle: '模型对话统一会话',
  pageTitle: '大模型对话调试台（统一会话版）',
  assistantName: '模型助手',
  emptyMessage: '暂无对话',
  emptyDescription: '选择一个模型连接，输入问题后通过统一 Run API 与模型实时对话。',
  placeholder: '输入问题，按回车发送',
  exampleQueries: ['请介绍一下你自己', '帮我写一段关于数据治理的开场白'],
  sendButtonText: '发送',
  clearButtonText: '清空',
  chatCardTitle: '模型对话',
  inputCardTitle: '输入区',
  chatHeight: 520,
  runtime: {
    buildSubmitOptions: ({ runtimeState }) => ({
      inputPayload: {
        llm_connection_id: runtimeState?.connectionId || undefined,
        system_prompt: runtimeState?.systemPrompt || '你是一个专业的数据智能助手。',
      },
      initialLoadingText: '正在建立统一会话并调用大模型...',
      runStartedText: '统一 Run 已创建，正在等待模型回复...',
      failedText: '模型对话失败，请检查连接配置或稍后重试。',
      interruptedText: '事件流连接中断，请查看当前回复。',
      errorToastText: '模型对话失败',
      buildAssistantText: (payload) => {
        if (payload?.text) return payload.text;
        if (payload?.llm_error) return '本次模型对话失败，请检查连接配置。';
        return buildDefaultAssistantText(payload);
      },
    }),
  },
};

export const DATA_INTELLIGENCE_SCENE_CONFIG: ConversationSceneConfig = {
  sceneCode: 'data_intelligence',
  pageCode: 'dataintelligence',
  conversationTitle: '数据智能对话',
  pageTitle: '数据智能对话（8 任务节点老板状态机）',
  assistantName: '数据资产探查助手',
  emptyMessage: '暂无对话',
  emptyDescription: '基于 8 任务节点老板状态机：实体定位 → 属性定位 → SQL 拼装 → SQL 执行，一步步引导你完成数据查询。',
  placeholder: '例如：帮我查客户的联系电话',
  exampleQueries: [
    '查客户的联系电话',
    '查客户的用电地址',
    '随便问下',
    '拼 SQL',
    '执行',
  ],
  sendButtonText: '发送',
  clearButtonText: '清空',
  chatCardTitle: '对话区',
  inputCardTitle: '输入区',
  chatHeight: 600,
  // 不使用 useConversationRun 的 runtime（不走 SSE/Run 协议）
  // 自己直接调 /api/data-intelligence/chat
  runtime: {
    buildSubmitOptions: () => ({}),
  },
};
