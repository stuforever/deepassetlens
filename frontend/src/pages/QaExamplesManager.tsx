/**
 * QaExamplesManager - G1 验证示例库管理页（融合设计 §4.1，/qa-examples）
 *
 * 能力：
 *   · 列表（keyword / status 过滤 + 分页，DataTableShell 统一密度/骨架屏）
 *   · 新增手工示例（Drawer：问题 + SQL + 路由 + 引擎 + 类型，DB 行 + Qdrant 点同步）
 *   · 启停（enabled <-> disabled，Popconfirm + PATCH status）
 *   · 审核（status=review 的反馈修正示例 -> enabled，走同一条 PATCH）
 *   · 删除（Popconfirm + DELETE，DB 行 + Qdrant 点同步）
 *   · 类型/状态徽标走 StatusTag token 语义色，零硬编码
 *   · S4a：30 天命中列（近 30 天 examples.injected 命中事件数）+ 行操作「相似预览」
 *     （Drawer 内 top-5 相似问题 + 相似度，走 GET /qa-examples/{id}/similar）
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Drawer, Form, Input, message, Popconfirm, Select, Space, Spin, Tag } from 'antd';
import { PlusOutlined, DeleteOutlined, PoweroffOutlined, CheckCircleOutlined, ReloadOutlined, LinkOutlined } from '@ant-design/icons';
import { qaExamplesApi, type QaExampleItem, type QaExampleSimilarItem } from '../services/api';
import { PageShell, StatusTag, DataTableShell, DrawerFooter } from '../components/shell';
import { tokens } from '../theme/tokens';

export const STATUS_META: Record<string, { label: string; preset: 'success' | 'warning' | 'disabled' | 'info' }> = {
  enabled: { label: '启用', preset: 'success' },
  disabled: { label: '停用', preset: 'disabled' },
  review: { label: '待审核', preset: 'warning' },
};

export const TYPE_META: Record<string, { label: string; preset: 'success' | 'info' | 'ai' }> = {
  user_confirmed: { label: '用户确认', preset: 'success' },
  manual: { label: '手工', preset: 'info' },
  golden: { label: '金标', preset: 'ai' },
};

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'enabled', label: '启用' },
  { value: 'disabled', label: '停用' },
  { value: 'review', label: '待审核' },
];

const TYPE_OPTIONS = [
  { value: 'manual', label: '手工' },
  { value: 'user_confirmed', label: '用户确认' },
  { value: 'golden', label: '金标' },
];

const ROUTE_OPTIONS = [
  { value: 'generic', label: '通用只读' },
  { value: 'scenario', label: '场景剧本' },
  { value: 'clarification', label: '需澄清' },
  { value: 'fallback', label: '降级' },
  { value: 'reject', label: '拒绝' },
];

const ENGINE_OPTIONS = [
  { value: 'doris', label: 'Doris 联邦' },
  { value: 'duckdb', label: 'DuckDB API 联邦' },
  { value: 'physical', label: '物理表直连' },
];

const QaExamplesManager: React.FC = () => {
  const [items, setItems] = useState<QaExampleItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [simOpen, setSimOpen] = useState(false);
  const [simLoading, setSimLoading] = useState(false);
  const [simTarget, setSimTarget] = useState<QaExampleItem | null>(null);
  const [simItems, setSimItems] = useState<QaExampleSimilarItem[]>([]);
  const size = 20;

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await qaExamplesApi.list({ status: status || undefined, keyword: keyword || undefined, page, size });
      const data = res.data?.data || {};
      setItems(Array.isArray(data.items) ? data.items : []);
      setTotal(Number(data.total || 0));
    } catch (e) {
      console.error('[QaExamples] 列表加载失败', e);
      message.error('示例列表加载失败');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [status, keyword, page]);

  useEffect(() => { fetchList(); }, [fetchList]);

  const handleSearch = (nextKeyword: string) => {
    setKeyword(nextKeyword);
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatus(value);
    setPage(1);
  };

  const handleToggle = async (row: QaExampleItem) => {
    const next = row.status === 'enabled' ? 'disabled' : 'enabled';
    try {
      const res = await qaExamplesApi.setStatus(row.id, next);
      if (res.data?.code !== 200) throw new Error(res.data?.message || '操作失败');
      message.success(next === 'enabled' ? '已启用' : '已停用');
      fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '状态更新失败');
    }
  };

  const handleApprove = async (row: QaExampleItem) => {
    try {
      const res = await qaExamplesApi.setStatus(row.id, 'enabled');
      if (res.data?.code !== 200) throw new Error(res.data?.message || '操作失败');
      message.success('已审核通过并启用');
      fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '审核失败');
    }
  };

  const handleDelete = async (row: QaExampleItem) => {
    try {
      const res = await qaExamplesApi.remove(row.id);
      if (res.data?.code !== 200) throw new Error(res.data?.message || '操作失败');
      message.success('已删除（含向量点）');
      fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '删除失败');
    }
  };

  const handleCreate = () => {
    form.resetFields();
    form.setFieldsValue({ route_type: 'generic', example_type: 'manual' });
    setDrawerOpen(true);
  };

  const handleShowSimilar = useCallback(async (row: QaExampleItem) => {
    setSimTarget(row);
    setSimItems([]);
    setSimOpen(true);
    setSimLoading(true);
    try {
      const res = await qaExamplesApi.similar(row.id);
      const data = res.data?.data || {};
      setSimItems(Array.isArray(data.items) ? data.items : []);
    } catch (e) {
      console.error('[QaExamples] 相似检索失败', e);
      message.error('相似问题检索失败（向量库不可用时为空）');
      setSimItems([]);
    } finally {
      setSimLoading(false);
    }
  }, []);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const res = await qaExamplesApi.create({
        question_raw: values.question_raw,
        sql: values.sql || undefined,
        entity_codes: [],
        route_type: values.route_type || 'generic',
        engine: values.engine || undefined,
        example_type: values.example_type || 'manual',
      });
      if (res.data?.code !== 200) throw new Error(res.data?.message || '新增失败');
      message.success('示例已新增（DB + 向量库）');
      setDrawerOpen(false);
      setPage(1);
      fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '新增失败');
    } finally {
      setSaving(false);
    }
  };

  const columns = useMemo(() => [
    { title: '问题', dataIndex: 'question_raw', key: 'q', width: 260, ellipsis: true },
    { title: '类型', dataIndex: 'example_type', key: 'type', width: 90, render: (v: string) => {
      const m = TYPE_META[v] || { label: v || '—', preset: 'default' as const };
      return <StatusTag preset={m.preset}>{m.label}</StatusTag>;
    }},
    { title: '路由', dataIndex: 'route_type', key: 'route', width: 90, render: (v: string) => <Tag style={{ margin: 0 }}>{v || '—'}</Tag> },
    { title: '引擎', dataIndex: 'engine', key: 'engine', width: 90, render: (v: string) => <Tag style={{ margin: 0 }}>{v || '—'}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => {
      const m = STATUS_META[v] || { label: v || '—', preset: 'default' as const };
      return <StatusTag preset={m.preset} dot>{m.label}</StatusTag>;
    }},
    { title: '累计命中', dataIndex: 'hit_count', key: 'hits', width: 80, render: (v: number) => <span style={{ color: tokens.colors.textSecondary }}>{v || 0}</span> },
    { title: '30天命中', dataIndex: 'hit_count_30d', key: 'hits30', width: 80, render: (v: number, row: QaExampleItem) => (
      <span style={{ color: (row.hit_count_30d || 0) > 0 ? tokens.colors.success : tokens.colors.textTertiary }}>
        {v || 0}
      </span>
    )},
    { title: '创建时间', dataIndex: 'created_at', key: 'created', width: 170, render: (v: string) => <span style={{ color: tokens.colors.textTertiary, fontSize: 12 }}>{v ? v.replace('T', ' ').slice(0, 19) : '—'}</span> },
    {
      title: '操作', key: 'action', width: 210, fixed: 'right' as const,
      render: (_: unknown, row: QaExampleItem) => (
        <Space size={2}>
          <Button type="link" size="small" icon={<LinkOutlined />} onClick={() => handleShowSimilar(row)}>相似</Button>
          {row.status === 'review' ? (
            <Button type="link" size="small" icon={<CheckCircleOutlined />} style={{ color: tokens.colors.success }} onClick={() => handleApprove(row)}>通过</Button>
          ) : (
            <Popconfirm title={row.status === 'enabled' ? '停用后不再参与示例召回，确定？' : '启用后参与示例召回，确定？'} onConfirm={() => handleToggle(row)}>
              <Button type="link" size="small" danger={row.status === 'enabled'} icon={<PoweroffOutlined />}>{row.status === 'enabled' ? '停用' : '启用'}</Button>
            </Popconfirm>
          )}
          <Popconfirm title="删除该示例（含向量点）？" onConfirm={() => handleDelete(row)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], []);

  return (
    <PageShell title="示例库管理">
      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
          <Space wrap>
            <Input.Search
              allowClear
              placeholder="按问题关键词搜索"
              style={{ width: 260 }}
              onSearch={handleSearch}
              defaultValue=""
            />
            <Select
              style={{ width: 130 }}
              value={status}
              onChange={handleStatusChange}
              options={STATUS_OPTIONS}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchList}>刷新</Button>
          </Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增手工示例</Button>
        </div>
        <DataTableShell
          loading={loading}
          tableProps={{
            dataSource: items,
            rowKey: 'id',
            columns,
            pagination: { current: page, pageSize: size, total, showTotal: (t: number) => `共 ${t} 条`, onChange: setPage },
            scroll: { x: 1200 },
            size: 'small',
          }}
        />
      </div>

      <Drawer
        title="新增手工示例"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
        footer={
          <DrawerFooter>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={saving} onClick={handleSave}>新增</Button>
          </DrawerFooter>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="question_raw" label="问题原文" rules={[{ required: true, message: '请输入问题' }]}>
            <Input.TextArea rows={2} placeholder="例如：统计用电客户总数" />
          </Form.Item>
          <Form.Item name="sql" label="验证 SQL" rules={[{ required: true, message: '请输入验证 SQL' }]}>
            <Input.TextArea rows={4} placeholder="SELECT COUNT(*) ..." style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 12 }} />
          </Form.Item>
          <Form.Item name="route_type" label="路由类型">
            <Select options={ROUTE_OPTIONS} />
          </Form.Item>
          <Form.Item name="engine" label="引擎">
            <Select allowClear options={ENGINE_OPTIONS} placeholder="留空=自动" />
          </Form.Item>
          <Form.Item name="example_type" label="示例类型">
            <Select options={TYPE_OPTIONS} />
          </Form.Item>
        </Form>
      </Drawer>

      <Drawer
        title="相似问题预览（top-5，带相似度）"
        open={simOpen}
        onClose={() => setSimOpen(false)}
        width={520}
      >
        {simTarget ? (
          <div style={{ marginBottom: 12, padding: '8px 12px', background: tokens.colors.bgSubtle, borderRadius: 6 }}>
            <div style={{ fontSize: 12, color: tokens.colors.textTertiary, marginBottom: 4 }}>当前示例</div>
            <div style={{ color: tokens.colors.textPrimary }}>{simTarget.question_raw}</div>
          </div>
        ) : null}
        <Spin spinning={simLoading}>
          {simItems.length === 0 ? (
            <div style={{ color: tokens.colors.textTertiary, padding: '24px 0', textAlign: 'center' }}>
              {simLoading ? '检索中…' : '无相似示例（向量库不可用或未达相似度阈值 0.75）'}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {simItems.map((s) => {
                const pct = s.score != null ? Math.round(Number(s.score) * 100) : null;
                return (
                  <div key={s.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 12px', border: `1px solid ${tokens.colors.border}`, borderRadius: 6 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ color: tokens.colors.textPrimary, wordBreak: 'break-all' }}>{s.question_raw}</div>
                      <div style={{ fontSize: 12, color: tokens.colors.textTertiary, marginTop: 2 }}>{s.id}</div>
                    </div>
                    <Tag style={{ margin: 0, flexShrink: 0 }} color={pct != null && pct >= 75 ? 'green' : undefined}>
                      {pct != null ? `${pct}%` : '—'}
                    </Tag>
                  </div>
                );
              })}
            </div>
          )}
        </Spin>
      </Drawer>
    </PageShell>
  );
};

export default QaExamplesManager;
