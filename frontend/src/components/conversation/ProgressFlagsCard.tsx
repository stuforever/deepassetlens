import React from 'react';
import { Card, Space, Tooltip, Typography } from 'antd';
import { CheckCircleFilled, ClockCircleOutlined } from '@ant-design/icons';
import { StatusTag } from '../shell';

const { Text } = Typography;

type FlagItem = {
  key: string;
  label: string;
  done: boolean;
  icon?: string;
  tip?: string;
};

type ProgressFlagsCardProps = {
  data?: {
    flags?: FlagItem[];
    done_count?: number;
    total_count?: number;
  };
};

const ProgressFlagsCard: React.FC<ProgressFlagsCardProps> = ({ data }) => {
  const flags = data?.flags || [];
  const done = data?.done_count || 0;
  const total = data?.total_count || flags.length || 5;

  return (
    <Card
      size="small"
      title={
        <Space>
          <span>任务进度</span>
          <StatusTag preset={done === total ? 'success' : done > 0 ? 'info' : 'default'}>
            {done}/{total} 已完成
          </StatusTag>
        </Space>
      }
    >
      <Space wrap size={12}>
        {flags.map((f) => (
          <Tooltip key={f.key} title={f.tip || f.label}>
            <StatusTag
              preset={f.done ? 'success' : 'default'}
              icon={f.done ? <CheckCircleFilled /> : <ClockCircleOutlined />}
              style={{
                fontSize: 13,
                padding: '4px 10px',
                opacity: f.done ? 1 : 0.6,
              }}
            >
              {f.icon && <span style={{ marginRight: 4 }}>{f.icon}</span>}
              {f.label}
            </StatusTag>
          </Tooltip>
        ))}
      </Space>
      <div style={{ marginTop: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          进度：{Array.from({ length: total }, (_, i) => i < done ? '●' : '○').join(' ')}
        </Text>
      </div>
    </Card>
  );
};

export default ProgressFlagsCard;
