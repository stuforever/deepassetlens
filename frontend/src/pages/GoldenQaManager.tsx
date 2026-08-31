/**
 * GoldenQaManager - 金标锚定管理页（批13-C 题库移除，/golden-qa）
 *
 * 能力：
 *   · 页签1 金标列表：问题/引擎/启停/命中统计(hit_count+last_hit_at)/创建时间；
 *     启停（Popconfirm + PATCH，同步 Qdrant tupu_golden_qa）/删除（Popconfirm + DELETE）
 *   · 页签2 候选推荐：近 7 天高频反馈且金标无覆盖问题 TopM（👍👎 纯观测聚合，
 *     无任何自动写路径）；「入金标」预填新增 Drawer，人工审核后录入
 *   · 顶栏：种子灌入（模板+历史成功查询，幂等）/ 重建向量（reseed，Qdrant 丢失恢复）/ 刷新
 *   · 新增金标：问题 + 期望 SQL（后端实时执行算 digest，失败拒绝入库）
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Drawer, Form, Input, message, Popconfirm, Select, Space, Tabs, Tag, Tooltip, Typography } from 'antd';
import { PlusOutlined, DeleteOutlined, PoweroffOutlined, ReloadOutlined, ThunderboltOutlined, StarOutlined, DatabaseOutlined } from '@ant-design/icons';
import { goldenQaApi, type GoldenQaItem, type GoldenCandidate } from '../services/api';
import { PageShell, StatusTag, DataTableShell, DrawerFooter } from '../components/shell';
import { tokens } from '../theme/tokens';

const { Text } = Typography;

const ENGINE_OPTIONS = [
  { value: 'doris', label: 'Doris 联邦' },
  { value: 'duckdb', label: 'DuckDB API 联邦' },
  { value: 'physical', label: '物理表直连' },
];

const ROUTE_OPTIONS = [
  { value: 'generic', label: '通用只读' },
  { value: 'scenario', label: '场景剧本' },
];

const ENGINE_LABEL: Record<string, string> = {
  doris: 'Doris', duckdb: 'DuckDB', physical: 'PG 直连', api_integration: 'API',
};

const GoldenQaManager: React.FC = () => {
  const [items, setItems] = useState<GoldenQaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [cands, setCands] = useState<GoldenCandidate[]>([]);
  const [candsLoading, setCandsLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [form] = Form.useForm();

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await goldenQaApi.list();
      const data = res.data?.data || {};
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (e) {
      console.error('[GoldenQa] 列表加载失败', e);
      message.error('金标列表加载失败');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCands = useCallback(async () => {
    setCandsLoading(true);
    try {
      const res = await goldenQaApi.candidates({ days: 7, top_m: 10 });
      setCands(Array.isArray(res.data?.data?.items) ? res.data.data.items : []);
    } catch {
      setCands([]);
    } finally {
      setCandsLoading(false);
    }
  }, []);

  useEffect(() => { fetchList(); fetchCands(); }, [fetchList, fetchCands]);

  const handleToggle = async (row: GoldenQaItem) => {
    const next = !row.enabled;
    try {
      const res = await goldenQaApi.setStatus(row.id, next);
      if (res.data?.ok === false) throw new Error(res.data?.error || '操作失败');
      message.success(next ? '已启用（向量同步 tupu_golden_qa）' : '已停用（不再参与锚定召回）');
      fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '状态更新失败');
    }
  };

  const handleDelete = async (row: GoldenQaItem) => {
    try {
      const res = await goldenQaApi.remove(row.id);
      if (res.data?.ok === false) throw new Error(res.data?.error || '删除失败');
      message.success('已删除（含向量点）');
      fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '删除失败');
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await goldenQaApi.seed();
      const d = res.data || {};
      message.success(`种子完成：新增 ${d.seeded ?? 0} 条（跳过 ${d.skipped ?? 0}，共 ${d.total ?? '—'} 条）`);
      fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '种子灌入失败');
    } finally {
      setSeeding(false);
    }
  };

  const handleReseedVectors = async () => {
    setSeeding(true);
    try {
      const res = await goldenQaApi.reseedVectors();
      message.success(`向量重建完成：${res.data?.synced ?? 0} 条已同步 tupu_golden_qa`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '向量重建失败');
    } finally {
      setSeeding(false);
    }
  };

  const openCreate = (preset?: { question?: string; sql?: string }) => {
    form.resetFields();
    form.setFieldsValue({
      question: preset?.question || '',
      expected_sql: preset?.sql || '',
      route_type: 'generic',
    });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const res = await goldenQaApi.create({
        question: values.question,
        expected_sql: values.expected_sql,
        route_type: values.route_type || 'generic',
        scenario_tag: values.scenario_tag || undefined,
        engine: values.engine || undefined,
      });
      if (res.data?.ok === false) throw new Error(res.data?.error || '新增失败');
      message.success('金标已新增（digest 实时校验 + 向量同步）');
      setDrawerOpen(false);
      fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '新增失败（期望 SQL 须可执行以计算 digest）');
    } finally {
      setSaving(false);
    }
  };

  const columns = useMemo(() => [
    { title: '问题', dataIndex: 'question', key: 'q', width: 300, ellipsis: true },
    { title: '引擎', dataIndex: 'engine', key: 'engine', width: 90, render: (v: string) => (
      <Tag style={{ margin: 0 }} color={v === 'doris' ? 'blue' : v === 'physical' ? 'green' : undefined}>{ENGINE_LABEL[v] || v || '—'}</Tag>
    )},
    { title: '路由', dataIndex: 'route_type', key: 'route', width: 90, render: (v: string) => <Tag style={{ margin: 0 }}>{v || '—'}</Tag> },
    { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 80, render: (v: boolean) => (
      <StatusTag preset={v ? 'success' : 'disabled'} dot>{v ? '启用' : '停用'}</StatusTag>
    )},
    { title: '命中', dataIndex: 'hit_count', key: 'hits', width: 80, sorter: (a: GoldenQaItem, b: GoldenQaItem) => (a.hit_count || 0) - (b.hit_count || 0),
      render: (v: number) => <span style={{ color: (v || 0) > 0 ? tokens.colors.success : tokens.colors.textTertiary, fontWeight: (v || 0) > 0 ? 600 : 400 }}>{v || 0}</span> },
    { title: '最近命中', dataIndex: 'last_hit_at', key: 'last_hit', width: 170, render: (v: string) => (
      <span style={{ color: tokens.colors.textTertiary, fontSize: 12 }}>{v ? v.replace('T', ' ').slice(0, 19) : '—'}</span>
    )},
    { title: '创建时间', dataIndex: 'created_at', key: 'created', width: 170, render: (v: string) => (
      <span style={{ color: tokens.colors.textTertiary, fontSize: 12 }}>{v ? v.replace('T', ' ').slice(0, 19) : '—'}</span>
    )},
    {
      title: '操作', key: 'action', width: 150, fixed: 'right' as const,
      render: (_: unknown, row: GoldenQaItem) => (
        <Space size={2}>
          <Popconfirm title={row.enabled ? '停用后不再参与锚定召回，确定？' : '启用后参与锚定召回，确定？'} onConfirm={() => handleToggle(row)}>
            <Button type="link" size="small" danger={row.enabled} icon={<PoweroffOutlined />}>{row.enabled ? '停用' : '启用'}</Button>
          </Popconfirm>
          <Popconfirm title="删除该金标（含向量点）？" onConfirm={() => handleDelete(row)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], []);

  const candColumns = useMemo(() => [
    { title: '问题', dataIndex: 'question', key: 'q', width: 300, ellipsis: true },
    { title: '👍', dataIndex: 'up_count', key: 'up', width: 60, render: (v: number) => (
      <span style={{ color: (v || 0) > 0 ? tokens.colors.success : tokens.colors.textTertiary, fontWeight: 600 }}>{v || 0}</span>
    )},
    { title: '👎', dataIndex: 'down_count', key: 'down', width: 60, render: (v: number) => (
      <span style={{ color: (v || 0) > 0 ? tokens.colors.error : tokens.colors.textTertiary }}>{v || 0}</span>
    )},
    { title: '反馈总数', dataIndex: 'total', key: 'total', width: 80 },
    { title: '最近反馈', dataIndex: 'last_seen', key: 'seen', width: 170, render: (v: string) => (
      <span style={{ color: tokens.colors.textTertiary, fontSize: 12 }}>{v ? v.replace('T', ' ').slice(0, 19) : '—'}</span>
    )},
    { title: 'SQL 存证', dataIndex: 'latest_sql', key: 'sql', ellipsis: true, render: (v: string) => v
      ? <Tooltip title={v}><code style={{ fontSize: 11 }}>{v.slice(0, 60)}</code></Tooltip> : <span style={{ color: tokens.colors.textTertiary }}>—</span> },
    {
      title: '操作', key: 'action', width: 100, fixed: 'right' as const,
      render: (_: unknown, row: GoldenCandidate) => (
        <Button type="link" size="small" icon={<StarOutlined />} onClick={() => openCreate({ question: row.question, sql: row.latest_sql })}>入金标</Button>
      ),
    },
  ], []);

  const goldenTab = (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
        <Space wrap>
          <Popconfirm title="按模板 + 历史成功查询灌入金标（幂等，同问题跳过）？" onConfirm={handleSeed}>
            <Button icon={<ThunderboltOutlined />} loading={seeding}>种子灌入</Button>
          </Popconfirm>
          <Popconfirm title="全量重建 tupu_golden_qa 向量（集合丢失/换库后恢复）？" onConfirm={handleReseedVectors}>
            <Button icon={<DatabaseOutlined />} loading={seeding}>重建向量</Button>
          </Popconfirm>
          <Button icon={<ReloadOutlined />} onClick={fetchList}>刷新</Button>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openCreate()}>新增金标</Button>
      </div>
      <Text type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
        批13-C：金标是运行时唯一锚定源（契约注入 golden_hits / 直通 sim≥0.95 / 首选计划 sim≥0.90 自评豁免 sim≥0.85）；增删改自动同步向量集合 tupu_golden_qa
      </Text>
      <DataTableShell
        loading={loading}
        tableProps={{
          dataSource: items,
          rowKey: 'id',
          columns,
          pagination: { pageSize: 20, showTotal: (t: number) => `共 ${t} 条`, hideOnSinglePage: true },
          scroll: { x: 1150 },
          size: 'small',
        }}
      />
    </div>
  );

  const candidatesTab = (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <Text type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
        候选推荐 = 近 7 天用户反馈（👍👎 纯观测信号）按问题聚合、且尚无金标覆盖的 Top 10；人工审核后点「入金标」录入（无任何自动写路径）
      </Text>
      <DataTableShell
        loading={candsLoading}
        tableProps={{
          dataSource: cands,
          rowKey: 'question',
          columns: candColumns,
          pagination: false,
          scroll: { x: 1000 },
          size: 'small',
          locale: { emptyText: '近 7 天无候选（反馈不足或已被金标覆盖）' },
        }}
      />
    </div>
  );

  return (
    <PageShell title="金标锚定管理" description="运行时唯一锚定源：金标注入 / 直通判定 / 首选计划 / 自评豁免">
      <Tabs
        style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        items={[
          { key: 'golden', label: '金标列表', children: goldenTab },
          { key: 'candidates', label: '候选推荐', children: candidatesTab },
        ]}
      />
      <Drawer
        title="新增金标"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={520}
        footer={
          <DrawerFooter>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={saving} onClick={handleSave}>新增</Button>
          </DrawerFooter>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="question" label="问题" rules={[{ required: true, message: '请输入问题' }]}>
            <Input.TextArea rows={2} placeholder="例如：统计用电客户总数" />
          </Form.Item>
          <Form.Item name="expected_sql" label="期望 SQL" rules={[{ required: true, message: '请输入期望 SQL' }]} extra="后端将实时执行以计算结果 digest（失败拒绝入库）">
            <Input.TextArea rows={4} placeholder="SELECT COUNT(*) ..." style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 12 }} />
          </Form.Item>
          <Form.Item name="route_type" label="路由类型">
            <Select options={ROUTE_OPTIONS} />
          </Form.Item>
          <Form.Item name="scenario_tag" label="场景标签" extra="可选：distribution-overload 等">
            <Input placeholder="留空=无" />
          </Form.Item>
          <Form.Item name="engine" label="引擎" extra="留空=按 SQL 前缀自动推断（internal./test_db./pg_tupu. -> Doris）">
            <Select allowClear options={ENGINE_OPTIONS} placeholder="自动推断" />
          </Form.Item>
        </Form>
      </Drawer>
    </PageShell>
  );
};

export default GoldenQaManager;
