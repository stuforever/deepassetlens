import React from 'react';
import { Alert, Card, Skeleton, Space, Spin, Typography } from 'antd';
import ThinkStream from './ThinkStream';
import FinalAnswer from './FinalAnswer';
import AssistantCanvas from './AssistantCanvas';
import type { ChatMessage, ConversationCardAction, ConversationSceneConfig } from './types';

const { Text } = Typography;

const ConversationMessageList: React.FC<{
  messages: ChatMessage[];
  sceneConfig: ConversationSceneConfig;
  loading?: boolean;
  liveStatus?: string;
  liveTokens?: string[];
  liveFinalAnswer?: string;
  liveRecommendations?: Array<{ label: string; shortcut?: string }>;
  liveMetaInfo?: string;
  confirmedData?: Record<string, any>;
  onCardAction?: (action: ConversationCardAction) => void;
  onSelectRecommendation?: (rec: any) => void;
  onExecuteSql?: () => void;
  onEntityClick?: (entityCode: string, entityName?: string) => void;
}> = ({
  messages,
  sceneConfig,
  loading = false,
  liveStatus,
  liveTokens,
  liveFinalAnswer,
  liveRecommendations,
  liveMetaInfo,
  confirmedData,
  onCardAction,
  onSelectRecommendation,
  onExecuteSql,
  onEntityClick,
}) => {
  if (messages.length === 0) {
    return (
      <Alert
        type="info"
        showIcon
        message={sceneConfig.emptyMessage || '暂无对话'}
        description={sceneConfig.emptyDescription || '请输入问题开始对话。'}
      />
    );
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      {messages.map((msg, msgIdx) => {
        const isLast = msgIdx === messages.length - 1;

        return (
          <div key={msg.id} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', width: '100%' }}>
            <Card
              size="small"
              bordered={false}
              style={{
                width: msg.role === 'user' ? 'min(1200px, 72%)' : '100%',
                maxWidth: '100%',
                background: msg.role === 'user' ? 'var(--color-primary-bg)' : 'transparent',
                boxShadow: 'none',
              }}
              title={msg.role === 'user' ? undefined : (sceneConfig.assistantName || '统一会话助手')}
              bodyStyle={msg.role === 'user' ? { padding: '6px 12px' } : { padding: '0' }}
            >
              {msg.role === 'user' ? (
                <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{msg.text}</div>
              ) : msg.loading ? (
                <Space direction="vertical" style={{ width: '100%' }} size={12}>
                  {/* 思考面板：读占位消息自身的 payload，实时渲染 */}
                  {msg.payload?.thinkStream && msg.payload.thinkStream.length > 0 ? (
                    <ThinkStream
                      items={msg.payload.thinkStream}
                      active={true}
                      liveStatus={msg.payload?.live_text}
                      metaInfo={msg.payload?.live_meta}
                    />
                  ) : (
                    <Space>
                      <Spin size="small" />
                      <Text strong>{msg.payload?.live_text || msg.text || '正在思考...'}</Text>
                    </Space>
                  )}
                  {/* 最终答案：token 逐字流式渲染（读占位消息 payload） */}
                  {msg.payload?.finalTokens && msg.payload.finalTokens.length > 0 ? (
                    <FinalAnswer answer="" tokens={msg.payload.finalTokens} isStreaming={true} />
                  ) : null}
                  {msg.payload?.final_answer && (!msg.payload?.finalTokens || msg.payload.finalTokens.length === 0) ? (
                    <FinalAnswer answer={msg.payload.final_answer} tokens={[]} isStreaming={false} />
                  ) : null}
                  {(!msg.payload?.thinkStream || msg.payload.thinkStream.length === 0) && !msg.payload?.finalTokens?.length && !msg.payload?.final_answer ? (
                    <Skeleton active paragraph={{ rows: 1 }} title={false} />
                  ) : null}
                </Space>
              ) : (
                <AssistantCanvas
                  payload={msg.payload}
                  isLast={isLast}
                  liveMetaInfo={liveMetaInfo}
                  liveFinalAnswer={liveFinalAnswer}
                  onSelectRecommendation={onSelectRecommendation}
                />
              )}
            </Card>
          </div>
        );
      })}
    </Space>
  );
};

export default ConversationMessageList;
