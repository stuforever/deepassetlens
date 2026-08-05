import React from 'react';
import { Card, Descriptions, Space, Typography } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { StatusTag, type StatusPreset } from '../shell';

const { Text } = Typography;

type ConfirmedItem = {
  type: string;
  code: string;
  label: string;
  name?: string;
};

type ConfirmedEntitiesCardProps = {
  data?: {
    items?: ConfirmedItem[];
  };
};

const TYPE_PRESET: Record<string, StatusPreset> = {
  L1: 'default',
  L2: 'default',
  L2X: 'error',
  L2X_related: 'warning',
  L3: 'info',
  L4: 'info',
  L4X: 'info',
  attr: 'success',
};

const ConfirmedEntitiesCard: React.FC<ConfirmedEntitiesCardProps> = ({ data }) => {
  const items = data?.items || [];

  // 按类型分组
  const grouped: Record<string, ConfirmedItem[]> = {};
  for (const it of items) {
    if (!grouped[it.type]) grouped[it.type] = [];
    grouped[it.type].push(it);
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <CheckCircleOutlined style={{ color: 'var(--color-success)' }} />
          <span>已锁定内容</span>
          <StatusTag preset="default">{items.length} 项</StatusTag>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size={8}>
        {Object.entries(grouped).map(([type, list]) => (
          <div key={type}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {list[0].label}（{type}）
            </Text>
            <div style={{ marginTop: 4 }}>
              <Space wrap size={6}>
                {list.map((it, i) => (
                  <StatusTag key={`${it.code}-${i}`} preset={TYPE_PRESET[it.type] || 'default'}>
                    {it.name || it.code}
                    {it.type === 'attr' && <Text type="secondary" style={{ marginLeft: 4, fontSize: 11 }}>({it.code})</Text>}
                  </StatusTag>
                ))}
              </Space>
            </div>
          </div>
        ))}
      </Space>
    </Card>
  );
};

export default ConfirmedEntitiesCard;
