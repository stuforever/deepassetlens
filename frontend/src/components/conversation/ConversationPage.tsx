import React from 'react';
import { Button, Card, Input, Space, Typography } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import ConversationMessageList from './ConversationMessageList';
import type { ChatMessage, ConversationCardAction, ConversationSceneConfig } from './types';

const { Title } = Typography;

type ConversationPageProps = {
  sceneConfig: ConversationSceneConfig;
  title?: React.ReactNode;
  headerExtra?: React.ReactNode;
  inputExtra?: React.ReactNode;
  messages: ChatMessage[];
  chatContainerRef?: React.RefObject<HTMLDivElement>;
  question: string;
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  loading?: boolean;
  exampleQueries?: string[];
  onExampleClick?: (value: string) => void;
  onCardAction?: (action: ConversationCardAction) => void;
};

const ConversationPage: React.FC<ConversationPageProps> = ({
  sceneConfig,
  title,
  headerExtra,
  inputExtra,
  messages,
  chatContainerRef,
  question,
  onQuestionChange,
  onSubmit,
  onClear,
  loading = false,
  exampleQueries = [],
  onExampleClick,
  onCardAction,
}) => {
  const resolvedTitle = title || sceneConfig.pageTitle;
  const resolvedExamples = exampleQueries.length > 0 ? exampleQueries : sceneConfig.exampleQueries || [];
  return (
    <div style={{ height: '100%', width: '100%', overflow: 'auto', paddingRight: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
        <Title level={4} style={{ margin: 0 }}>
          {resolvedTitle}
        </Title>
        {headerExtra}
      </div>

      <Space direction="vertical" style={{ width: '100%', display: 'flex' }} size={12}>
        <Card size="small" title={sceneConfig.chatCardTitle || '问答对话框'}>
          <div
            ref={chatContainerRef}
            style={{
              height: sceneConfig.chatHeight || 560,
              overflowY: 'auto',
              padding: 12,
              background: 'var(--bg-subtle)',
              borderRadius: 8,
              border: '1px solid var(--color-border)',
            }}
          >
            <ConversationMessageList messages={messages} sceneConfig={sceneConfig} loading={loading} onCardAction={onCardAction} />
          </div>
        </Card>

        <Card size="small" title={sceneConfig.inputCardTitle || '输入区'}>
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            {inputExtra}
            <Input.TextArea
              value={question}
              onChange={(e) => onQuestionChange(e.target.value)}
              rows={3}
              placeholder={sceneConfig.placeholder}
              allowClear
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  if (!loading && question.trim()) {
                    onSubmit();
                  }
                }
              }}
            />
            <Space wrap>
              {resolvedExamples.map((item) => (
                <Button key={`example-${item}`} size="small" onClick={() => onExampleClick?.(item)}>
                  {item}
                </Button>
              ))}
            </Space>
            <Space>
              <Button type="primary" icon={<PlayCircleOutlined />} onClick={onSubmit} loading={loading} disabled={!question.trim() || loading}>
                {sceneConfig.sendButtonText || '发送'}
              </Button>
              <Button onClick={onClear} disabled={loading || messages.length === 0}>
                {sceneConfig.clearButtonText || '清空'}
              </Button>
            </Space>
          </Space>
        </Card>
      </Space>
    </div>
  );
};

export default ConversationPage;
