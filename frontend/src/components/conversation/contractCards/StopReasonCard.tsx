/**
 * StopReasonCard - 终止条件（设计 §5 stop_when / §6.1）
 * 展示拿到结果即终止的硬规则；若已命中则高亮"已满足"。
 */
import React from 'react';
import { Space, Tag, Typography } from 'antd';
import { StopOutlined } from '@ant-design/icons';
import ContractCardShell from './ContractCardShell';

const { Text } = Typography;

type Props = {
  stopWhen?: string[];
  resultObtained?: boolean;
  terminal?: boolean;
};

const StopReasonCard: React.FC<Props> = ({ stopWhen = [], resultObtained, terminal }) => (
  <ContractCardShell icon={<StopOutlined />} title="终止条件" subtitle={terminal ? '终端步骤 · 拿到结果即停' : '可继续后续步骤'}>
    {stopWhen.length > 0 ? (
      <Space size={[4, 4]} wrap>
        {stopWhen.map((s) => (
          <Tag key={s} color={resultObtained ? 'green' : 'default'} style={{ fontSize: 11 }}>
            {s}
          </Tag>
        ))}
        {resultObtained ? <Tag color="green">已命中：禁止继续检索</Tag> : null}
      </Space>
    ) : (
      <Text type="secondary" style={{ fontSize: 12 }}>本步骤未声明硬终止条件（按流程步骤推进）</Text>
    )}
  </ContractCardShell>
);

export default StopReasonCard;
