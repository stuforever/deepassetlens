/**
 * GovernanceObservatory - 运行观测台（受控 Skill 问答平台 v2，批4 生产治理）
 *
 * 消费后端治理端点（统一裁判，前端不镜像规则）：
 *   GET /api/data-intelligence/skills/catalog   -> Skill 目录快照（enabled/version/disabled_reason）
 *   GET /api/data-intelligence/skills/metrics    -> 运行指标 + 审计轨迹
 *
 * 用途：上线审核 / 运行观测 / 违规预警（rejected/blocked 指标）。
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Button, Space, Table, Tag, Typography, message, Switch, Card, Statistic, Row, Col, Tooltip, Spin,
} from 'antd';
import { ReloadOutlined, DashboardOutlined, SafetyCertificateOutlined, AuditOutlined } from '@ant-design/icons';
import { PageShell } from '../components/shell';
import { dataIntelligenceApi } from '../services/dataIntelligenceApi';
import { tokens } from '../theme/tokens';

const { Text } = Typography;

type CatalogEntry = {
  skill_id: string;
  enabled: boolean;
  version?: string | null;
  priority?: number | null;
  sha256?: string | null;
  steps: string[];
  template_count: number;
  entity_alias_count: number;
  disabled_reason?: string;
  multi_engine?: boolean;
};

const ROUTE_TYPE_CN: Record<string, string> = {
  scenario: '场景',
  clarification: '澄清',
  generic: '通用',
  fallback: '降级',
  reject: '拒绝',
};

const EVENT_CN: Record<string, string> = {
  'route.scenario': '路由·场景',
  'route.clarification': '路由·澄清',
  'route.generic': '路由·通用',
  'route.fallback': '路由·降级',
  'route.reject': '路由·拒绝',
  'policy.rejected': '策略·拒绝',
  'policy.blocked': '策略·阻断',
  'engine.selected': '引擎·选定',
  'stop.reached': '终止·命中',
  'template.bound': '模板·绑定',
  'template.drift': '模板·漂移',
  'output.scrubbed': '输出·清洗',
};

const GovernanceObservatory: React.FC = () => {
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [c, m] = await Promise.all([
        dataIntelligenceApi.skillsCatalog(),
        dataIntelligenceApi.skillsMetrics(),
      ]);
      if (c.ok && Array.isArray(c.catalog)) {
        setCatalog(c.catalog as CatalogEntry[]);
        setWarnings(c.warnings || []);
      }
      if (m.ok) setMetrics(m);
    } catch (e) {
      message.error(`运行观测数据加载失败：${(e as Error).message || e}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!autoRefresh) return;
    timerRef.current = setInterval(load, 10000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [autoRefresh, load]);

  const counters = metrics?.counters || {};
  // 三轨M10(U5) §六：KPI 卡趋势箭头——后端 counters 快照无历史序列时 delta 取自
  // metrics.delta_*（可选项，缺省 0=中性→箭头占位）；历史序列接入后自动生效。
  const deltaOf = (key: string) => Number((metrics as any)?.[`delta_${key}`] ?? 0);
  const statItems = [
    { title: '路由决策', value: counters.route_total ?? 0, color: '#1677ff', delta: deltaOf('route_total') },
    { title: '策略拒绝', value: counters.rejected_total ?? 0, color: '#faad14', delta: deltaOf('rejected_total') },
    { title: '策略阻断', value: counters.blocked_total ?? 0, color: '#ff4d4f', delta: deltaOf('blocked_total') },
    { title: '引擎选定', value: counters.engine_selected_total ?? 0, color: '#52c41a', delta: deltaOf('engine_selected_total') },
    { title: '终止命中', value: counters.stop_reached_total ?? 0, color: '#13c2c2', delta: deltaOf('stop_reached_total') },
    { title: '输出清洗', value: counters.output_scrubbed_total ?? 0, color: '#722ed1', delta: deltaOf('output_scrubbed_total') },
  ];

  const audit: any[] = (metrics?.audit as any[]) || [];

  return (
    <PageShell
      title="运行观测台"
      description="受控 Skill 问答平台 · 生产治理（Skill 目录 / 运行指标 / 审计轨迹）"
      extra={
        <Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            自动刷新 <Switch size="small" checked={autoRefresh} onChange={setAutoRefresh} />
          </Text>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            刷新
          </Button>
        </Space>
      }
      padded
    >
      <div style={{ height: '100%', overflow: 'auto', padding: tokens.layout.contentPadding }}>
        {/* 运行指标 */}
        <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
          {statItems.map((s) => (
            <Col span={4} key={s.title}>
              <Card size="small" styles={{ body: { padding: '14px 18px' } }}>
                <Statistic
                  title={<Text type="secondary" style={{ fontSize: 12 }}>{s.title}</Text>}
                  value={s.value}
                  valueStyle={{ fontSize: 22, fontWeight: 600, color: s.color }}
                  suffix={
                    <span style={{ fontSize: 12, color: s.delta > 0 ? '#52c41a' : s.delta < 0 ? '#ff4d4f' : 'var(--text-tertiary)' }}>
                      {s.delta > 0 ? '↑' : s.delta < 0 ? '↓' : '→'}
                      {s.delta !== 0 ? Math.abs(s.delta) : ''}
                    </span>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>

        <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
          <Col span={12}>
            <Card
              size="small"
              title={
                <Space>
                  <SafetyCertificateOutlined />
                  <span>路由分布</span>
                </Space>
              }
            >
              <Space wrap>
                {Object.entries(metrics?.by_route_type || {}).map(([k, v]) => (
                  <Tag key={k} color="blue">
                    {ROUTE_TYPE_CN[k] || k}: {String(v)}
                  </Tag>
                ))}
                {!Object.keys(metrics?.by_route_type || {}).length && <Text type="secondary">暂无路由记录</Text>}
              </Space>
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>按技能：</Text>
                <Space wrap size={[4, 4]}>
                  {Object.entries(metrics?.by_skill || {}).map(([k, v]) => (
                    <Tag key={k}>{k}: {String(v)}</Tag>
                  ))}
                </Space>
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card
              size="small"
              title={
                <Space>
                  <DashboardOutlined />
                  <span>策略拒绝原因 TOP</span>
                </Space>
              }
            >
              {Object.entries(metrics?.policy_by_reason || {})
                .sort((a, b) => Number(b[1]) - Number(a[1]))
                .slice(0, 5)
                .map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                    <Text style={{ fontSize: 12 }} ellipsis={{ tooltip: k }}>{k}</Text>
                    <Tag color={k.includes('禁用') || k.includes('不在') ? 'red' : 'orange'}>{String(v)}</Tag>
                  </div>
                ))}
              {!Object.keys(metrics?.policy_by_reason || {}).length && <Text type="secondary">暂无拒绝记录</Text>}
            </Card>
          </Col>
        </Row>

        {/* Skill 目录 */}
        <Card
          size="small"
          title={
            <Space>
              <SafetyCertificateOutlined />
              <span>Skill 目录（SKILL.md 唯一来源解析状态）</span>
            </Space>
          }
          style={{ marginBottom: 12 }}
        >
          <Table<CatalogEntry>
            size="small"
            rowKey="skill_id"
            dataSource={catalog}
            pagination={false}
            columns={[
              {
                title: '技能', dataIndex: 'skill_id', width: 190,
                render: (v, r) => (
                  <Space size={4}>
                    <Text strong>{v}</Text>
                    {r.multi_engine && <Tag color="purple">多引擎</Tag>}
                  </Space>
                ),
              },
              {
                title: '状态', dataIndex: 'enabled', width: 90,
                render: (v) => (v ? <Tag color="success">启用</Tag> : <Tag color="error">禁用</Tag>),
              },
              { title: '版本', dataIndex: 'version', width: 70, render: (v) => v ?? '—' },
              { title: '优先级', dataIndex: 'priority', width: 80, render: (v) => v ?? '—' },
              { title: '步骤', dataIndex: 'steps', render: (v: string[]) => (Array.isArray(v) ? v.join(' → ') : '—') },
              {
                title: '模板', dataIndex: 'template_count', width: 60,
                render: (v, r) => <Text>{v}</Text>,
              },
              {
                title: '禁用原因', dataIndex: 'disabled_reason', render: (v) =>
                  v ? <Text type="danger" style={{ fontSize: 12 }}>{v}</Text> : null,
              },
              {
                title: '哈希', dataIndex: 'sha256', width: 150, render: (v) =>
                  v ? <Text code style={{ fontSize: 11 }}>{v}</Text> : null,
              },
            ]}
          />
          {warnings.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <Text type="warning" style={{ fontSize: 12 }}>告警：</Text>
              {warnings.map((w, i) => (
                <div key={i}><Text type="secondary" style={{ fontSize: 12 }}>· {w}</Text></div>
              ))}
            </div>
          )}
        </Card>

        {/* 审计轨迹 */}
        <Card
          size="small"
          title={
            <Space>
              <AuditOutlined />
              <span>审计轨迹（最近 {audit.length} 条）</span>
            </Space>
          }
        >
          <Table
            size="small"
            rowKey={(r, i) => `${r.ts}-${i}`}
            dataSource={audit.slice().reverse()}
            pagination={{ pageSize: 10, showSizeChanger: false }}
            columns={[
              { title: '时间', dataIndex: 'ts', width: 200, render: (v) => <Text style={{ fontSize: 12 }}>{String(v).replace('T', ' ').slice(5, 19)}</Text> },
              {
                title: '事件', dataIndex: 'event', width: 140,
                render: (v) => {
                  const blocked = v === 'policy.blocked';
                  const rejected = v === 'policy.rejected';
                  return <Tag color={blocked ? 'red' : rejected ? 'orange' : 'blue'}>{EVENT_CN[v] || v}</Tag>;
                },
              },
              {
                title: '明细', dataIndex: 'payload', render: (p) => {
                  if (!p) return null;
                  const parts = [p.route_type && `${ROUTE_TYPE_CN[p.route_type] || p.route_type}`, p.skill_id, p.workflow_step, p.reason, p.detail]
                    .filter(Boolean)
                    .join(' / ');
                  return <Text style={{ fontSize: 12 }} ellipsis={{ tooltip: parts }}>{parts}</Text>;
                },
              },
            ]}
          />
          {!audit.length && !loading && <Text type="secondary">暂无审计记录（运行一次受控对话或模拟路由后出现）</Text>}
        </Card>

        {loading && (
          <div style={{ textAlign: 'center', padding: 12 }}>
            <Spin size="small" />
          </div>
        )}
      </div>
    </PageShell>
  );
};

export default GovernanceObservatory;
