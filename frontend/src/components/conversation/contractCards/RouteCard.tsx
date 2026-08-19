/**
 * RouteCard - 路由判定结果（设计 §4.1）
 * 展示 SkillRouter 的确定性路由结论：route_type/skill/step/命中规则/原因/优先级。
 */
import React from 'react';
import { Space, Tag, Typography } from 'antd';
import { ApiOutlined } from '@ant-design/icons';
import ContractCardShell from './ContractCardShell';
import { ROUTE_TYPE_META, SKILL_CN } from './types';

const { Text, Paragraph } = Typography;

type Props = {
  route: {
    route_type: string;
    skill_id?: string;
    workflow_step?: string;
    matched_rules?: string[];
    route_reason?: string;
    confidence?: string;
    fallback_level?: string;
    candidates?: Array<{ skill_id: string; description?: string }>;
    priority?: number;
  };
};

const RouteCard: React.FC<Props> = ({ route }) => {
  const meta = ROUTE_TYPE_META[route.route_type] || ROUTE_TYPE_META.generic;
  const skillCn = SKILL_CN[route.skill_id || ''] || route.skill_id || '—';
  return (
    <ContractCardShell icon={<ApiOutlined />} title="路由判定" subtitle={`确定性路由 · 优先级 ${route.priority ?? '—'}`}>
      <Space size={[4, 4]} wrap>
        <Tag color={meta.color}>{meta.label}</Tag>
        {route.route_type === 'scenario' && route.skill_id ? (
          <>
            <Tag>技能：{skillCn}</Tag>
            <Tag color="geekblue">步骤：{route.workflow_step || '—'}</Tag>
          </>
        ) : null}
        {route.confidence ? <Tag>置信：{route.confidence}</Tag> : null}
      </Space>
      {(route.matched_rules || []).length > 0 ? (
        <Paragraph style={{ marginTop: 6, marginBottom: 2, fontSize: 12 }}>
          <Text type="secondary">命中规则：</Text>
          <Space size={[4, 2]} wrap style={{ marginTop: 2 }}>
            {(route.matched_rules || []).map((r, i) => <Tag key={`rule-${i}`} style={{ fontSize: 11 }}>{r}</Tag>)}
          </Space>
        </Paragraph>
      ) : null}
      {route.route_type === 'clarification' && (route.candidates || []).length > 0 ? (
        <Paragraph style={{ marginTop: 4, marginBottom: 2, fontSize: 12 }}>
          <Text type="warning">同时命中多个场景，需确认：</Text>
          <Space size={[4, 2]} wrap style={{ marginTop: 2 }}>
            {(route.candidates || []).map((c) => (
              <Tag key={c.skill_id} color="orange">{SKILL_CN[c.skill_id] || c.skill_id}</Tag>
            ))}
          </Space>
        </Paragraph>
      ) : null}
      {route.route_reason ? (
        <Paragraph style={{ marginTop: 4, marginBottom: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
          {route.route_reason}
        </Paragraph>
      ) : null}
    </ContractCardShell>
  );
};

export default RouteCard;
