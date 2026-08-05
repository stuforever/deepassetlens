import React from 'react';
import { Button, Card, Space, Typography } from 'antd';
import { ArrowRightOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { StatusTag } from '../shell';

const { Text, Paragraph } = Typography;

type RecommendationItem = {
  task: string;
  label: string;
  shortcut?: string;
};

type RecommendedNextCardProps = {
  data?: {
    recommendations?: RecommendationItem[];
  };
  onSelect?: (item: RecommendationItem) => void;
};

const RecommendedNextCard: React.FC<RecommendedNextCardProps> = ({ data, onSelect }) => {
  const recs = data?.recommendations || [];
  if (recs.length === 0) {
    return (
      <Card size="small" title="推荐下一步">
        <Text type="secondary">已完成所有任务</Text>
      </Card>
    );
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <ThunderboltOutlined style={{ color: 'var(--color-warning)' }} />
          <span>推荐下一步</span>
        </Space>
      }
    >
      <Paragraph type="secondary" style={{ marginBottom: 12, fontSize: 12 }}>
        基于当前秘书态，AI 建议按以下顺序推进：
      </Paragraph>
      <Space direction="vertical" style={{ width: '100%' }} size={8}>
        {recs.map((r, i) => (
          <Button
            key={`${r.task}-${i}`}
            block
            onClick={() => onSelect?.(r)}
            style={{ textAlign: 'left', height: 'auto', padding: '8px 12px', whiteSpace: 'normal' }}
          >
            <Space direction="vertical" size={2} style={{ width: '100%' }}>
              <Space>
                <StatusTag preset="info">{r.task}</StatusTag>
                <Text strong>{r.label}</Text>
                <ArrowRightOutlined style={{ color: 'var(--color-primary)' }} />
              </Space>
              {r.shortcut && (
                <Text type="secondary" style={{ fontSize: 12 }}>示例："{r.shortcut}"</Text>
              )}
            </Space>
          </Button>
        ))}
      </Space>
    </Card>
  );
};

export default RecommendedNextCard;
