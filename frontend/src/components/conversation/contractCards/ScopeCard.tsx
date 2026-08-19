/**
 * ScopeCard - 范围（设计 §5 scope）
 * 展示本契约的客户名精确集合、承诺与来源。
 */
import React from 'react';
import { Space, Tag, Typography } from 'antd';
import { AimOutlined } from '@ant-design/icons';
import ContractCardShell from './ContractCardShell';

const { Text } = Typography;

type Props = {
  scope?: Record<string, any>;
};

const COMMITMENT_CN: Record<string, string> = {
  exact_set: '精确集合',
  none: '未限定',
  user_input: '用户输入',
};

const ScopeCard: React.FC<Props> = ({ scope }) => {
  const customerNames = scope?.customer_names;
  const customers: string[] = Array.isArray(customerNames) ? customerNames : [];
  const commitment = scope?.commitment || 'none';
  const source = scope?.source || '';
  return (
    <ContractCardShell icon={<AimOutlined />} title="范围" subtitle={`承诺：${COMMITMENT_CN[commitment] || commitment}`}>
      {customers.length > 0 ? (
        <Space size={[4, 4]} wrap>
          {customers.map((c) => <Tag key={c} color="blue">{c}</Tag>)}
          <Text type="secondary" style={{ fontSize: 11 }}>{source ? `来源：${source}` : ''}</Text>
        </Space>
      ) : (
        <Text type="secondary" style={{ fontSize: 12 }}>无客户名限定（{source ? `来源：${source}` : '未限定范围'}）</Text>
      )}
    </ContractCardShell>
  );
};

export default ScopeCard;
