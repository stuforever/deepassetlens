import React from 'react';
import { Card, Empty, Space, Typography } from 'antd';
import { StatusTag } from '../shell';

const { Paragraph, Text } = Typography;

interface ExploreAnswerData {
  answer?: string;
  related_entities?: any[];
  related_attributes?: any[];
  suggest_classification?: boolean;
}

const ExploreAnswerCard: React.FC<{ data?: ExploreAnswerData }> = ({ data }) => {
  if (!data) return null;
  const answer = data.answer || '';
  const entities = data.related_entities || [];
  const attributes = data.related_attributes || [];

  if (!answer && entities.length === 0 && attributes.length === 0) {
    return <Empty description="暂无探索结果" />;
  }

  return (
    <Card size="small" title={<Space><Text strong>知识探索</Text><StatusTag preset="info">RAG</StatusTag></Space>} style={{ width: '100%' }}>
      {answer ? (
        <Paragraph style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginBottom: entities.length || attributes.length ? 12 : 0 }}>
          {answer}
        </Paragraph>
      ) : null}
      {entities.length > 0 ? (
        <div style={{ marginBottom: attributes.length ? 8 : 0 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>相关实体：</Text>
          <Space size={[4, 4]} wrap>
            {entities.slice(0, 10).map((e, i) => (
              <StatusTag key={i} preset="info">{e.get('name') || e.get('entity_name') || e.get('code') || String(e)}</StatusTag>
            ))}
          </Space>
        </div>
      ) : null}
      {attributes.length > 0 ? (
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>相关属性：</Text>
          <Space size={[4, 4]} wrap>
            {attributes.slice(0, 10).map((a, i) => (
              <StatusTag key={i} preset="success">{a.get('name') || a.get('attribute_name') || a.get('code') || String(a)}</StatusTag>
            ))}
          </Space>
        </div>
      ) : null}
      {data.suggest_classification ? (
        <div style={{ marginTop: 8, padding: 8, background: 'var(--color-success-bg)', border: '1px solid var(--color-success-bg)', borderRadius: 4 }}>
          <Text style={{ fontSize: 12, color: 'var(--color-success)' }}>💡 建议进一步查询分类以定位具体实体</Text>
        </div>
      ) : null}
    </Card>
  );
};

export default ExploreAnswerCard;
