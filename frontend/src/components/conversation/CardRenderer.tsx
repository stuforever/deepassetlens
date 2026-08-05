import React from 'react';
import { Alert, Card, Typography } from 'antd';
import QueryEntityResultCard from './QueryEntityResultCard';
import ClarificationCard from './ClarificationCard';
import ProgressFlagsCard from './ProgressFlagsCard';
import RecommendedNextCard from './RecommendedNextCard';
import ConfirmedEntitiesCard from './ConfirmedEntitiesCard';
import SqlPreviewCard from './SqlPreviewCard';
import SqlExecutionResultCard from './SqlExecutionResultCard';
import ClassificationResultCard from './ClassificationResultCard';
import ExploreAnswerCard from './ExploreAnswerCard';
import type { ConversationCard, ConversationCardAction, RunEventRecord } from './types';

const { Paragraph } = Typography;

const CardRenderer: React.FC<{
  card?: ConversationCard | null;
  disabled?: boolean;
  onAction?: (action: ConversationCardAction) => void;
  streamEvents?: RunEventRecord[];
  onSelectRecommendation?: (rec: any) => void;
  onExecuteSql?: () => void;
}> = ({ card, disabled = false, onAction, streamEvents = [], onSelectRecommendation, onExecuteSql }) => {
  if (!card) return null;

  if (card.card_type === 'query_entity_result') {
    return <QueryEntityResultCard data={card.data} events={streamEvents} />;
  }

  if (card.card_type === 'clarification') {
    return <ClarificationCard card={card} disabled={disabled} onAction={onAction} />;
  }

  // 数据智能对话新增的 4 种 card_type
  if (card.card_type === 'progress_flags') {
    return <ProgressFlagsCard data={card.data} />;
  }

  if (card.card_type === 'recommended_next') {
    return <RecommendedNextCard data={card.data} onSelect={onSelectRecommendation} />;
  }

  if (card.card_type === 'confirmed_entities') {
    return <ConfirmedEntitiesCard data={card.data} />;
  }

  if (card.card_type === 'sql_preview') {
    return <SqlPreviewCard data={card.data} onExecute={onExecuteSql} />;
  }

  if (card.card_type === 'sql_execution_result') {
    return <SqlExecutionResultCard data={card.data} />;
  }

  if (card.card_type === 'classification_result') {
    return <ClassificationResultCard data={card.data} />;
  }

  if (card.card_type === 'explore_answer') {
    return <ExploreAnswerCard data={card.data} />;
  }

  if (card.card_type === 'rich_text') {
    return (
      <Card size="small" title={card.title || '回复'}>
        <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>{card.data?.text || ''}</Paragraph>
      </Card>
    );
  }

  return (
    <Alert
      type="info"
      showIcon
      message={`暂未支持的卡片类型：${card.card_type}`}
      description="当前统一会话容器已经切到 card_type 协议，但这个卡片类型还没有对应渲染器。"
    />
  );
};

export default CardRenderer;
