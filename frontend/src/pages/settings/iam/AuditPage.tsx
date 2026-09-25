/**
 * 权限重构T4（design §5.3）：审计日志只读页——五列表格+筛选。
 * 数据源 GET /api/v1/iam/audit（T5.5 端点——未就绪时静默空态）。
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Button, Input, Select, Table } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { SettingsPageHeader } from '../../../components/settings/shared';
import { iamApi } from '../../../services/api';

interface AuditRow {
  id: number;
  ts: string;
  user_sub: string;
  resource_type: string;
  resource_id: string;
  action: string;
  decision: string;
  reason: string | null;
}

const AuditPage: React.FC = () => {
  const [items, setItems] = useState<AuditRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [resourceType, setResourceType] = useState<string>('');
  const [decision, setDecision] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (p = page) => {
    setLoading(true);
    try {
      const r = await iamApi.listAudit({
        resource_type: resourceType || undefined,
        decision: decision || undefined,
        page: p,
        page_size: 50,
      });
      setItems(r.data?.data?.items || []);
      setTotal(r.data?.data?.total || 0);
    } catch {
      // T5.5 端点未落/异常——空态即可（只读页）
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, resourceType, decision]);

  useEffect(() => { void load(); }, [load]);

  const columns = [
    { title: '时间', dataIndex: 'ts', key: 'ts', width: 170, render: (v: string) => (v ? new Date(v).toLocaleString() : '—') },
    { title: '用户', dataIndex: 'user_sub', key: 'user_sub', width: 220, ellipsis: true },
    {
      title: '资源', key: 'res', width: 240,
      render: (_: unknown, r: AuditRow) => `${r.resource_type}/${r.resource_id}`,
    },
    { title: '动作', dataIndex: 'action', key: 'action', width: 90 },
    {
      title: '判定', dataIndex: 'decision', key: 'decision', width: 90,
      render: (v: string) => (
        <span style={{ color: v === 'allow' ? '#16a34a' : v === 'deny' ? '#ef4444' : '#d97706' }}>{v}</span>
      ),
    },
    { title: '原因', dataIndex: 'reason', key: 'reason', ellipsis: true },
  ];

  return (
    <div>
      <SettingsPageHeader title="审计日志" description="工具判定与授权变更留痕（只读）。" />
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Select
          allowClear
          placeholder="资源类型"
          style={{ width: 160 }}
          value={resourceType || undefined}
          onChange={(v) => { setPage(1); setResourceType(v || ''); }}
          options={['skill', 'workflow', 'data_source', 'expert', 'sishu', 'auth', 'tool', 'attachment'].map((v) => ({ label: v, value: v }))}
        />
        <Select
          allowClear
          placeholder="判定"
          style={{ width: 120 }}
          value={decision || undefined}
          onChange={(v) => { setPage(1); setDecision(v || ''); }}
          options={['allow', 'deny', 'approval'].map((v) => ({ label: v, value: v }))}
        />
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
      </div>
      <Table<AuditRow>
        rowKey="id"
        loading={loading}
        columns={columns as never}
        dataSource={items}
        pagination={{ current: page, total, pageSize: 50, onChange: (p) => { setPage(p); void load(p); } }}
        scroll={{ y: 'calc(100vh - 320px)' }}
        size="small"
        data-testid="iam-audit-table"
      />
    </div>
  );
};

export default AuditPage;
