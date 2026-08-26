/**
 * RouteSimulator - 受控路由模拟器（设计 §10.3；批13-P 改为 Drawer 内嵌审计工具）
 * 输入问句（可带连续上下文）-> 调后端 SkillRouter 预览 -> 展示五张业务卡。
 * 前端不自行猜测路由/契约。由 FreePlanChat 的「审计模拟」按钮以 Drawer 打开，
 * 不再常驻问答页顶部。
 */
import React, { useState } from 'react';
import { Button, Input, Space, Tag, Typography, message } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';
import { dataIntelligenceApi } from '../../../services/dataIntelligenceApi';
import ContractCardsPanel from './ContractCardsPanel';
import type { QueryContractView, RouteResult } from './types';

const { Text } = Typography;

const SIM_EXAMPLES = ['所有用电户与配变户变关系', '哪些台区过载了？', '客户负载占有率倒排', '查一下用电客户总数'];

const RouteSimulator: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [contract, setContract] = useState<QueryContractView | null>(null);
  const [error, setError] = useState('');

  const run = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError('');
    try {
      const resp = await dataIntelligenceApi.simulateRoute({ user_input: question.trim() });
      if (resp.ok && resp.route) {
        setRoute(resp.route);
        setContract(resp.route.contract || null);
      } else {
        setError(resp.error || '路由预览失败');
      }
    } catch (e: any) {
      setError(String(e?.message || e));
      message.error('路由预览失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Space.Compact style={{ width: '100%' }}>
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onPressEnter={run}
          placeholder="输入问句，预览确定性路由与受控契约..."
          allowClear
        />
        <Button type="primary" onClick={run} loading={loading} icon={<ExperimentOutlined />}>预览路由</Button>
      </Space.Compact>
      <div style={{ marginTop: 6 }}>
        <Space size={[4, 4]} wrap>
          <Text type="secondary" style={{ fontSize: 11 }}>与生产对话同一 SkillRouter 裁判：</Text>
          {SIM_EXAMPLES.map((q) => (
            <Tag key={q} style={{ cursor: 'pointer' }} onClick={() => setQuestion(q)}>{q}</Tag>
          ))}
        </Space>
      </div>
      {error ? <Text type="danger" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>{error}</Text> : null}
      <div style={{ marginTop: 8 }}>
        <ContractCardsPanel route={route} contract={contract} />
      </div>
    </div>
  );
};

export default RouteSimulator;
