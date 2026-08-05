import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Card, Drawer, Form, Input, Modal, Select, Space, Table, Tabs, Tag, Typography, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { conceptApi, metricCenterApi } from '../services/api';
import LineageGraph from '../components/LineageGraph';
import { PageShell, DataTableShell, FilterBar, StatusTag } from '../components/shell';

const { Text } = Typography;

type MetricRow = {
  id: string;
  metric_code: string;
  metric_name: string;
  metric_type: string;
  domain?: string;
  status?: string;
  version_current?: number;
  enabled?: boolean;
  updated_at?: string;
};

const MetricManager: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<MetricRow[]>([]);
  const [keyword, setKeyword] = useState('');
  const [domain, setDomain] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [metricTypeFilter, setMetricTypeFilter] = useState<string>('');

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeMetricId, setActiveMetricId] = useState<string>('');
  const [metricDetail, setMetricDetail] = useState<any>(null);
  const [detailTab, setDetailTab] = useState('base');

  const [baseForm] = Form.useForm();
  const [atomForm] = Form.useForm();
  const [derivedForm] = Form.useForm();

  const [aliases, setAliases] = useState<any[]>([]);
  const [atomFilters, setAtomFilters] = useState<any[]>([]);
  const [deps, setDeps] = useState<any[]>([]);
  const [dimBindings, setDimBindings] = useState<any[]>([]);
  const [filterWhitelist, setFilterWhitelist] = useState<any[]>([]);

  const [versions, setVersions] = useState<any[]>([]);
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotData, setSnapshotData] = useState<any>(null);

  const [dbEntities, setDbEntities] = useState<any[]>([]);
  const [atomicMetricOptions, setAtomicMetricOptions] = useState<any[]>([]);
  const [dataSources, setDataSources] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [lineageData, setLineageData] = useState<any>(null);

  const [derivedPresetFilters, setDerivedPresetFilters] = useState<any[]>([]);
  const [derivedAvailableDims, setDerivedAvailableDims] = useState<string[]>([]);
  const [derivedBaseMetricId, setDerivedBaseMetricId] = useState<string>('');

  const watchedFactEntityId = Form.useWatch('fact_entity_id', atomForm);
  const watchedDerivedMode = Form.useWatch('config_mode', derivedForm);

  const entityOptions = useMemo(
    () =>
      (dbEntities || []).map((e: any) => ({
        label: `${e.entity_name || e.label || e.id}${e.landing_table_en ? ` (${e.landing_table_en})` : ''}`,
        value: String(e.id),
        entity: e,
      })),
    [dbEntities]
  );

  const factEntity = useMemo(() => {
    const id = String(watchedFactEntityId || '');
    return (dbEntities || []).find((e: any) => String(e.id) === id) || null;
  }, [dbEntities, watchedFactEntityId]);

  const factFieldOptions = useMemo(() => {
    const props = factEntity?.properties_schema;
    const list = Array.isArray(props) ? props : [];
    const landingTable = factEntity?.landing_table_en || factEntity?.entity_en_name || '';
    return list
      .map((p: any) => {
        const cn = String(p.label || p.display_name || p.name_zh || p.name || '').trim();
        const en = String(p.name || p.field_name || p.attribute_name || '').trim();
        if (!en) return null;
        const full = landingTable ? `${landingTable}.${en}` : en;
        return { label: cn ? `${cn} (${full})` : full, value: en, full };
      })
      .filter(Boolean) as any[];
  }, [factEntity]);

  const dimFieldOptions = useMemo(() => {
    const rows = dimBindings || [];
    const options: any[] = [];
    rows.forEach((r: any) => {
      const dimId = String(r.dim_entity_id || '').trim();
      if (!dimId) return;
      const e = (dbEntities || []).find((x: any) => String(x.id) === dimId);
      if (!e) return;
      const landingTable = e.landing_table_en || e.entity_en_name || '';
      const props = Array.isArray(e.properties_schema) ? e.properties_schema : [];
      props.forEach((p: any) => {
        const cn = String(p.label || p.display_name || p.name_zh || p.name || '').trim();
        const en = String(p.name || p.field_name || p.attribute_name || '').trim();
        if (!landingTable || !en) return;
        const full = `${landingTable}.${en}`;
        options.push({ label: `${e.entity_name} / ${cn || en} (${full})`, value: full });
      });
    });
    const seen = new Set<string>();
    return options.filter((o) => {
      if (seen.has(o.value)) return false;
      seen.add(o.value);
      return true;
    });
  }, [dimBindings, dbEntities]);

  const filterFieldOptions = useMemo(() => {
    const rows = filterWhitelist || [];
    return rows
      .map((x: any) => {
        const fn = String(x.field_full_name || '').trim();
        if (!fn) return null;
        const cn = String(x.field_cn || '').trim();
        return { label: cn ? `${cn} (${fn})` : fn, value: fn };
      })
      .filter(Boolean) as any[];
  }, [filterWhitelist]);

  const onDropBaseMetric = (e: React.DragEvent) => {
    e.preventDefault();
    try {
      const raw = e.dataTransfer.getData('text/plain');
      const obj = JSON.parse(raw);
      if (obj?.type === 'base_metric' && obj?.value) {
        setDerivedBaseMetricId(String(obj.value));
        derivedForm.setFieldsValue({ base_metric_id: String(obj.value), config_mode: 'config' });
      }
    } catch {}
  };

  const onDropDim = (e: React.DragEvent) => {
    e.preventDefault();
    try {
      const raw = e.dataTransfer.getData('text/plain');
      const obj = JSON.parse(raw);
      if (obj?.type === 'dim_field' && obj?.value) {
        const v = String(obj.value);
        setDerivedAvailableDims((p) => (p.includes(v) ? p : [...p, v]));
        derivedForm.setFieldsValue({ available_dims_json: (derivedAvailableDims || []).includes(v) ? derivedAvailableDims : [...(derivedAvailableDims || []), v], config_mode: 'config' });
      }
    } catch {}
  };

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await metricCenterApi.listMetrics({
        keyword: keyword || undefined,
        domain: domain || undefined,
        status: status || undefined,
        metric_type: metricTypeFilter || undefined,
      });
      setList(res.data?.data || []);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [domain, keyword, metricTypeFilter, status]);

  const fetchDeps = async () => {
    try {
      const conceptRes = await conceptApi.getConcepts();
      const concepts = conceptRes?.data || [];
      const entities = concepts.flatMap((c: any) =>
        (c.entities || []).map((e: any) => ({
          ...e,
          concept_id: c.id,
          concept_name: c.name,
          landing_table_en: e?.landing_table_en_name || e?.entity_en_name || e?.entity_landing_table_en || e?.entity_en_name || '',
        }))
      );
      setDbEntities(entities);
    } catch {}

    try {
      const res = await metricCenterApi.listMetrics({ metric_type: 'atomic' });
      const rows = res.data?.data || [];
      setAtomicMetricOptions(
        (rows || []).map((x: any) => ({
          label: `${x.metric_name} (${x.metric_code})`,
          value: x.id,
          metric_code: x.metric_code,
          metric_name: x.metric_name,
        }))
      );
    } catch {}

    fetch('/api/v1/data-sources')
      .then((r) => r.json())
      .then((data) => {
        setDataSources(data?.data || []);
      })
      .catch(() => {});
  };

  const fetchDetail = async (id: string) => {
    setLoading(true);
    try {
      const res = await metricCenterApi.getMetric(id);
      const data = res.data?.data || {};
      setMetricDetail(data);

      const m = data.metric || {};
      baseForm.setFieldsValue({
        metric_name: m.metric_name,
        metric_name_en: m.metric_name_en,
        metric_type: m.metric_type,
        domain: m.domain,
        description: m.description,
        metric_level: m.metric_level,
        metric_unit: m.metric_unit,
        metric_subject: m.metric_subject,
        stat_grain: m.stat_grain,
        owner_user: m.owner_user,
        business_owner: m.business_owner,
        business_dept: m.business_dept,
        requester_user: m.requester_user,
        reviewer_user: m.reviewer_user,
        manager_owner: m.manager_owner,
        business_caliber: m.business_caliber,
        tech_caliber: m.tech_caliber,
        dev_owner: m.dev_owner,
        similarity_threshold: m.similarity_threshold,
        enabled: m.enabled,
      });

      setAliases(data.aliases || []);
      setAtomFilters(data.atom_filters || []);
      setDeps(data.deps || []);
      setDimBindings(data.dim_bindings || []);
      setFilterWhitelist(data.filter_whitelist || []);

      const atom = data.atom || null;
      atomForm.setFieldsValue(atom || {});
      const derived = data.derived || null;
      derivedForm.setFieldsValue(derived || {});
      setDerivedPresetFilters(derived?.preset_filters_json || []);
      setDerivedAvailableDims(derived?.available_dims_json || []);
      setDerivedBaseMetricId(derived?.base_metric_id || '');

      const vres = await metricCenterApi.listVersions(id);
      setVersions(vres.data?.data || []);

      try {
        const ares = await metricCenterApi.listAuditLogs(id);
        setAuditLogs(ares.data?.data || []);
      } catch {
        setAuditLogs([]);
      }
      try {
        const lres = await metricCenterApi.getLineage(id, 2);
        setLineageData(lres.data?.data || null);
      } catch {
        setLineageData(null);
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '加载详情失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
    fetchDeps();
  }, [fetchList]);

  const openMetric = async (id: string) => {
    setActiveMetricId(id);
    setDrawerOpen(true);
    setDetailTab('base');
    await fetchDetail(id);
  };

  const onCreate = async () => {
    const values = await createForm.validateFields();
    setLoading(true);
    try {
      await metricCenterApi.createMetric(values);
      message.success('已创建');
      setCreateOpen(false);
      createForm.resetFields();
      await fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const onUpdateBase = async () => {
    if (!activeMetricId) return;
    const values = await baseForm.validateFields();
    setLoading(true);
    try {
      await metricCenterApi.updateMetric(activeMetricId, values);
      message.success('已保存');
      await fetchDetail(activeMetricId);
      await fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const onSaveAliases = async () => {
    if (!activeMetricId) return;
    setLoading(true);
    try {
      await metricCenterApi.upsertAliases(activeMetricId, aliases);
      message.success('别名已保存');
      await fetchDetail(activeMetricId);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const onSaveAtom = async () => {
    if (!activeMetricId) return;
    const values = await atomForm.validateFields();
    setLoading(true);
    try {
      await metricCenterApi.upsertAtom(activeMetricId, values);
      message.success('原子指标定义已保存');
      await fetchDetail(activeMetricId);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const onSaveAtomFilters = async () => {
    if (!activeMetricId) return;
    setLoading(true);
    try {
      const normalized = atomFilters.map((x) => {
        const v = x.value_json;
        if (typeof v === 'string' && v.trim().startsWith('[')) {
          try {
            return { ...x, value_json: JSON.parse(v) };
          } catch {
            return x;
          }
        }
        if (typeof v === 'string' && v.trim().startsWith('{')) {
          try {
            return { ...x, value_json: JSON.parse(v) };
          } catch {
            return x;
          }
        }
        return x;
      });
      await metricCenterApi.upsertAtomFilters(activeMetricId, normalized);
      message.success('口径过滤已保存');
      await fetchDetail(activeMetricId);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const onSaveDerived = async () => {
    if (!activeMetricId) return;
    const values = await derivedForm.validateFields();
    setLoading(true);
    try {
      const mode = (values.config_mode || 'dsl') as string;
      const payload: any = { ...values };
      if (mode === 'config') {
        payload.base_metric_id = derivedBaseMetricId || values.base_metric_id;
        payload.available_dims_json = derivedAvailableDims;
        payload.preset_filters_json = derivedPresetFilters;
        delete payload.expr_dsl;
      } else {
        payload.config_mode = 'dsl';
        payload.expr_dsl = values.expr_dsl;
        payload.base_metric_id = null;
        payload.time_period = null;
        payload.available_dims_json = [];
        payload.preset_filters_json = [];
      }
      await metricCenterApi.upsertDerived(activeMetricId, payload);
      message.success('派生指标定义已保存');
      await fetchDetail(activeMetricId);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const onSaveDeps = async () => {
    if (!activeMetricId) return;
    setLoading(true);
    try {
      await metricCenterApi.upsertDeps(activeMetricId, deps);
      message.success('依赖已保存');
      await fetchDetail(activeMetricId);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const onSaveDimBindings = async () => {
    if (!activeMetricId) return;
    setLoading(true);
    try {
      await metricCenterApi.upsertDimBindings(activeMetricId, dimBindings);
      message.success('维度白名单已保存');
      await fetchDetail(activeMetricId);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const onSaveFilterWhitelist = async () => {
    if (!activeMetricId) return;
    setLoading(true);
    try {
      const normalized = filterWhitelist.map((x) => {
        const v = x.op_whitelist_json;
        if (typeof v === 'string' && (v.trim().startsWith('[') || v.trim().startsWith('{'))) {
          try {
            return { ...x, op_whitelist_json: JSON.parse(v) };
          } catch {
            return x;
          }
        }
        return x;
      });
      await metricCenterApi.upsertFilterWhitelist(activeMetricId, normalized);
      message.success('过滤白名单已保存');
      await fetchDetail(activeMetricId);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const runWorkflowAction = async (action: 'submit' | 'approve' | 'reject' | 'publish') => {
    if (!activeMetricId) return;
    const operator = baseForm.getFieldValue('owner_user') || 'operator';
    let reason: string | undefined = undefined;
    if (action === 'reject') {
      reason = await new Promise<string>((resolve) => {
        let temp = '';
        Modal.confirm({
          title: '请输入驳回原因',
          content: <Input.TextArea autoSize={{ minRows: 3, maxRows: 6 }} onChange={(e) => { temp = e.target.value; }} />,
          onOk: () => resolve(temp),
          onCancel: () => resolve(''),
        });
      });
    }
    setLoading(true);
    try {
      if (action === 'submit') await metricCenterApi.submit(activeMetricId, { operator });
      if (action === 'approve') await metricCenterApi.approve(activeMetricId, { operator });
      if (action === 'reject') await metricCenterApi.reject(activeMetricId, { operator, reason });
      if (action === 'publish') await metricCenterApi.publish(activeMetricId, { operator });
      message.success('已执行');
      await fetchDetail(activeMetricId);
      await fetchList();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '执行失败');
    } finally {
      setLoading(false);
    }
  };

  const previewSnapshot = async (v: number) => {
    if (!activeMetricId) return;
    setLoading(true);
    try {
      const res = await metricCenterApi.getVersionSnapshot(activeMetricId, v);
      setSnapshotData(res.data?.data || {});
      setSnapshotOpen(true);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || '加载快照失败');
    } finally {
      setLoading(false);
    }
  };

  const doRollback = async (v: number) => {
    if (!activeMetricId) return;
    Modal.confirm({
      title: `确认回滚到版本 ${v}？`,
      onOk: async () => {
        setLoading(true);
        try {
          await metricCenterApi.rollback(activeMetricId, { version: v, operator: baseForm.getFieldValue('owner_user') || 'operator' });
          message.success('已回滚');
          await fetchDetail(activeMetricId);
          await fetchList();
        } catch (e: any) {
          message.error(e?.response?.data?.detail || e?.message || '回滚失败');
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const metricOptions = useMemo(() => list.map((x) => ({ label: `${x.metric_name} (${x.metric_code})`, value: x.id })), [list]);

  const columns = [
    { title: '指标编码', dataIndex: 'metric_code', key: 'metric_code', width: 180, ellipsis: true },
    { title: '指标名称', dataIndex: 'metric_name', key: 'metric_name', width: 240, ellipsis: true },
    { title: '类型', dataIndex: 'metric_type', key: 'metric_type', width: 90, render: (v: string) => <StatusTag preset={v === 'derived' ? 'ai' : 'info'}>{v}</StatusTag> },
    { title: '域', dataIndex: 'domain', key: 'domain', width: 120, ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 120, render: (v: string) => <StatusTag preset="default">{v}</StatusTag> },
    { title: '版本', dataIndex: 'version_current', key: 'version_current', width: 80 },
    { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 70, render: (v: boolean) => (v ? <StatusTag preset="success">启用</StatusTag> : <StatusTag preset="error">禁用</StatusTag>) },
    { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 160, ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, r: MetricRow) => (
        <Space>
          <Button size="small" type="link" onClick={() => openMetric(r.id)}>配置</Button>
          <Button
            size="small"
            danger
            type="link"
            onClick={() => {
              Modal.confirm({
                title: `确认删除指标 ${r.metric_name}？`,
                onOk: async () => {
                  setLoading(true);
                  try {
                    await metricCenterApi.deleteMetric(r.id);
                    message.success('已删除');
                    await fetchList();
                  } catch (e: any) {
                    message.error(e?.response?.data?.detail || e?.message || '删除失败');
                  } finally {
                    setLoading(false);
                  }
                },
              });
            }}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <PageShell
      title="指标管理"
      description="原子指标与衍生指标的统一管理"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchList} loading={loading}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建指标</Button>
        </Space>
      }
      filters={{
        search: { placeholder: '关键词（编码/名称）', value: keyword, onChange: setKeyword },
        filters: [
          <Input style={{ width: 200 }} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="域（domain）" allowClear />,
          <Select
            style={{ width: 180 }}
            value={metricTypeFilter || undefined}
            onChange={(v) => setMetricTypeFilter(v || '')}
            placeholder="指标类型"
            allowClear
            options={[{ label: 'atomic', value: 'atomic' }, { label: 'derived', value: 'derived' }]}
          />,
          <Select
            style={{ width: 180 }}
            value={status || undefined}
            onChange={(v) => setStatus(v || '')}
            allowClear
            placeholder="状态"
            options={[
              { label: 'draft', value: 'draft' },
              { label: 'reviewing', value: 'reviewing' },
              { label: 'approved', value: 'approved' },
              { label: 'published', value: 'published' },
              { label: 'deprecated', value: 'deprecated' },
            ]}
          />,
        ],
      }}
    >
      <DataTableShell
        compact
        tableProps={{
          dataSource: list,
          rowKey: 'id',
          columns: columns as any,
          loading,
          pagination: { pageSize: 20 },
          scroll: { x: 1200 },
        }}
      />

      <Modal
        open={createOpen}
        title="新建指标"
        okText="创建"
        cancelText="取消"
        onOk={onCreate}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={loading}
      >
        <Form form={createForm} layout="vertical" initialValues={{ metric_type: 'atomic', domain: 'demo' }}>
          <Form.Item name="metric_code" label="指标编码（唯一）" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="metric_name" label="指标名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="metric_type" label="类型" rules={[{ required: true }]}>
            <Select options={[{ label: 'atomic', value: 'atomic' }, { label: 'derived', value: 'derived' }]} />
          </Form.Item>
          <Form.Item name="domain" label="域（domain）"><Input /></Form.Item>
          <Form.Item name="description" label="说明"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="owner_user" label="负责人"><Input /></Form.Item>
        </Form>
      </Modal>

      <Drawer
        open={drawerOpen}
        width={980}
        title={<Space><Text strong>指标配置</Text><Text type="secondary">{metricDetail?.metric?.metric_name} ({metricDetail?.metric?.metric_code})</Text></Space>}
        onClose={() => setDrawerOpen(false)}
      >
        <Tabs
          activeKey={detailTab}
          onChange={setDetailTab}
          items={[
            {
              key: 'base',
              label: '指标基础信息',
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size={12}>
                  <Card size="small" title="指标字典（按属性分组）">
                    <Form form={baseForm} layout="vertical">
                      <Card size="small" title="基础属性" style={{ marginBottom: 12 }}>
                        <Space wrap>
                          <Form.Item label="指标ID" style={{ width: 220 }}>
                            <Input value={metricDetail?.metric?.metric_code || ''} disabled />
                          </Form.Item>
                          <Form.Item name="metric_name" label="指标中文名" style={{ width: 260 }} rules={[{ required: true }]}><Input /></Form.Item>
                          <Form.Item name="metric_name_en" label="指标英文名" style={{ width: 220 }}><Input /></Form.Item>
                          <Form.Item name="metric_level" label="指标等级" style={{ width: 160 }}>
                            <Select
                              allowClear
                              options={[
                                { label: 'L1', value: 'L1' },
                                { label: 'L2', value: 'L2' },
                                { label: 'L3', value: 'L3' },
                                { label: 'L4', value: 'L4' },
                              ]}
                            />
                          </Form.Item>
                          <Form.Item name="metric_unit" label="计量单位" style={{ width: 160 }}><Input /></Form.Item>
                        </Space>
                        <Space wrap>
                          <Form.Item label="创建时间" style={{ width: 240 }}>
                            <Input value={metricDetail?.metric?.created_at || ''} disabled />
                          </Form.Item>
                          <Form.Item label="更新时间" style={{ width: 240 }}>
                            <Input value={metricDetail?.metric?.updated_at || ''} disabled />
                          </Form.Item>
                          <Form.Item name="enabled" label="启用" style={{ width: 160 }}>
                            <Select options={[{ label: 'true', value: true }, { label: 'false', value: false }]} />
                          </Form.Item>
                        </Space>
                      </Card>

                      <Card size="small" title="业务属性" style={{ marginBottom: 12 }}>
                        <Form.Item name="business_caliber" label="业务口径"><Input.TextArea rows={3} /></Form.Item>
                        <Space wrap>
                          <Form.Item name="business_owner" label="业务负责人" style={{ width: 220 }}><Input /></Form.Item>
                          <Form.Item name="business_dept" label="负责部门" style={{ width: 220 }}><Input /></Form.Item>
                          <Form.Item name="requester_user" label="提需人" style={{ width: 220 }}><Input /></Form.Item>
                        </Space>
                      </Card>

                      <Card size="small" title="技术属性" style={{ marginBottom: 12 }}>
                        <Space wrap>
                          <Form.Item name="metric_type" label="指标类型" style={{ width: 160 }} rules={[{ required: true }]}>
                            <Select options={[{ label: 'atomic', value: 'atomic' }, { label: 'derived', value: 'derived' }]} />
                          </Form.Item>
                          <Form.Item name="metric_subject" label="指标主题" style={{ width: 220 }}><Input /></Form.Item>
                          <Form.Item name="stat_grain" label="统计粒度" style={{ width: 160 }}>
                            <Select
                              allowClear
                              options={[
                                { label: 'day', value: 'day' },
                                { label: 'month', value: 'month' },
                                { label: 'year', value: 'year' },
                              ]}
                            />
                          </Form.Item>
                          <Form.Item name="domain" label="域" style={{ width: 200 }}><Input /></Form.Item>
                        </Space>
                        <Form.Item name="tech_caliber" label="技术口径"><Input.TextArea rows={3} /></Form.Item>
                        <Space wrap>
                          <Form.Item name="dev_owner" label="研发负责人" style={{ width: 220 }}><Input /></Form.Item>
                          <Form.Item name="similarity_threshold" label="检索阈值" style={{ width: 180 }}><Input /></Form.Item>
                        </Space>
                      </Card>

                      <Card size="small" title="管理属性">
                        <Space wrap>
                          <Form.Item label="版本号" style={{ width: 160 }}>
                            <Input value={String(metricDetail?.metric?.version_current ?? '')} disabled />
                          </Form.Item>
                          <Form.Item name="owner_user" label="指标负责人" style={{ width: 220 }}><Input /></Form.Item>
                          <Form.Item name="manager_owner" label="管理负责人" style={{ width: 220 }}><Input /></Form.Item>
                          <Form.Item name="reviewer_user" label="审核人" style={{ width: 220 }}><Input /></Form.Item>
                        </Space>
                        <Form.Item name="description" label="补充说明"><Input.TextArea rows={2} /></Form.Item>
                      </Card>

                      <Space wrap style={{ marginTop: 12 }}>
                        <Button type="primary" onClick={onUpdateBase} loading={loading}>保存基础信息</Button>
                        <Tag>status: {metricDetail?.metric?.status}</Tag>
                      </Space>
                    </Form>
                  </Card>

                  <Card size="small" title="别名（用于指标检索）">
                    <Table
                      size="small"
                      rowKey={(_, idx) => String(idx)}
                      pagination={false}
                      dataSource={aliases}
                      columns={[
                        {
                          title: 'alias',
                          dataIndex: 'alias',
                          render: (_: any, r: any, idx: number) => (
                            <Input value={r.alias} onChange={(e) => setAliases((p) => p.map((x, i) => (i === idx ? { ...x, alias: e.target.value } : x)))} />
                          ),
                        },
                        {
                          title: 'type',
                          dataIndex: 'alias_type',
                          width: 140,
                          render: (_: any, r: any, idx: number) => (
                            <Select
                              value={r.alias_type || 'synonym'}
                              style={{ width: '100%' }}
                              onChange={(v) => setAliases((p) => p.map((x, i) => (i === idx ? { ...x, alias_type: v } : x)))}
                              options={[
                                { label: 'name', value: 'name' },
                                { label: 'abbrev', value: 'abbrev' },
                                { label: 'synonym', value: 'synonym' },
                                { label: 'phrase', value: 'phrase' },
                              ]}
                            />
                          ),
                        },
                        {
                          title: 'weight',
                          dataIndex: 'weight',
                          width: 120,
                          render: (_: any, r: any, idx: number) => (
                            <Input value={String(r.weight ?? 1.0)} onChange={(e) => setAliases((p) => p.map((x, i) => (i === idx ? { ...x, weight: Number(e.target.value || 1.0) } : x)))} />
                          ),
                        },
                        {
                          title: '操作',
                          width: 120,
                          render: (_: any, __: any, idx: number) => <Button danger onClick={() => setAliases((p) => p.filter((_, i) => i !== idx))}>删除</Button>,
                        },
                      ]}
                    />
                    <Space style={{ marginTop: 12 }} wrap>
                      <Button onClick={() => setAliases((p) => [...p, { alias: '', alias_type: 'synonym', weight: 1.0, enabled: true }])}>新增别名</Button>
                      <Button type="primary" onClick={onSaveAliases} loading={loading}>保存别名</Button>
                    </Space>
                  </Card>

                  {(metricDetail?.metric?.metric_type || '') === 'atomic' ? (
                    <Card size="small" title="原子指标定义（可选择录入）">
                      <Form form={atomForm} layout="vertical">
                        <Space wrap>
                          <Form.Item name="fact_entity_id" label="事实实体" rules={[{ required: true }]} style={{ width: 420 }}>
                            <Select
                              showSearch
                              optionFilterProp="label"
                              options={entityOptions}
                              onChange={(v) => {
                                const ent = (dbEntities || []).find((x: any) => String(x.id) === String(v));
                                if (ent) {
                                  atomForm.setFieldsValue({
                                    fact_entity_name: ent.entity_name,
                                    fact_table_en: ent.landing_table_en || '',
                                  });
                                }
                              }}
                            />
                          </Form.Item>
                          <Form.Item name="fact_table_en" label="事实表（可覆盖）" style={{ width: 240 }}><Input /></Form.Item>
                          <Form.Item name="data_source_id" label="数据源" style={{ width: 240 }}>
                            <Select
                              allowClear
                              options={(dataSources || []).map((d: any) => ({
                                label: `${d.name} (${d.host}:${d.port}/${d.database})${d.is_default ? ' [默认]' : ''}`,
                                value: d.id,
                                disabled: !d.enabled,
                              }))}
                            />
                          </Form.Item>
                        </Space>
                        <Space wrap>
                          <Form.Item name="agg_func" label="聚合方式" rules={[{ required: true }]} style={{ width: 200 }}>
                            <Select options={[
                              { label: 'count', value: 'count' },
                              { label: 'distinct_count', value: 'distinct_count' },
                              { label: 'sum', value: 'sum' },
                              { label: 'avg', value: 'avg' },
                              { label: 'max', value: 'max' },
                              { label: 'min', value: 'min' },
                            ]} />
                          </Form.Item>
                          <Form.Item name="measure_field_en" label="度量字段" style={{ width: 320 }}>
                            <Select allowClear showSearch optionFilterProp="label" options={factFieldOptions} />
                          </Form.Item>
                          <Form.Item name="time_field_en" label="时间字段" rules={[{ required: true }]} style={{ width: 320 }}>
                            <Select allowClear showSearch optionFilterProp="label" options={factFieldOptions} />
                          </Form.Item>
                          <Form.Item name="default_limit" label="limit" style={{ width: 160 }}><Input /></Form.Item>
                        </Space>
                        <Button type="primary" onClick={onSaveAtom} loading={loading}>保存原子定义</Button>
                      </Form>

                      <Card size="small" title="口径过滤（atom_filters）" style={{ marginTop: 12 }}>
                        <Table
                          size="small"
                          rowKey={(_, idx) => String(idx)}
                          pagination={false}
                          dataSource={atomFilters}
                          columns={[
                            {
                              title: 'field_full_name',
                              dataIndex: 'field_full_name',
                              render: (_: any, r: any, idx: number) => (
                                <Input value={r.field_full_name} onChange={(e) => setAtomFilters((p) => p.map((x, i) => (i === idx ? { ...x, field_full_name: e.target.value } : x)))} />
                              ),
                            },
                            {
                              title: 'op',
                              dataIndex: 'op',
                              width: 140,
                              render: (_: any, r: any, idx: number) => (
                                <Select
                                  value={r.op || '='}
                                  style={{ width: '100%' }}
                                  onChange={(v) => setAtomFilters((p) => p.map((x, i) => (i === idx ? { ...x, op: v } : x)))}
                                  options={[
                                    { label: '=', value: '=' },
                                    { label: '!=', value: '!=' },
                                    { label: 'IN', value: 'IN' },
                                    { label: 'NOT IN', value: 'NOT IN' },
                                    { label: 'BETWEEN', value: 'BETWEEN' },
                                    { label: 'IS NULL', value: 'IS NULL' },
                                    { label: 'IS NOT NULL', value: 'IS NOT NULL' },
                                  ]}
                                />
                              ),
                            },
                            {
                              title: 'value_json',
                              dataIndex: 'value_json',
                              render: (_: any, r: any, idx: number) => (
                                <Input value={typeof r.value_json === 'string' ? r.value_json : JSON.stringify(r.value_json ?? '')} onChange={(e) => setAtomFilters((p) => p.map((x, i) => (i === idx ? { ...x, value_json: e.target.value } : x)))} />
                              ),
                            },
                            { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => setAtomFilters((p) => p.filter((_, i) => i !== idx))}>删除</Button> },
                          ]}
                        />
                        <Space style={{ marginTop: 12 }} wrap>
                          <Button onClick={() => setAtomFilters((p) => [...p, { field_full_name: '', op: '=', value_json: '' }])}>新增过滤</Button>
                          <Button type="primary" onClick={onSaveAtomFilters} loading={loading}>保存过滤</Button>
                        </Space>
                      </Card>
                    </Card>
                  ) : null}

                  <Card size="small" title="维度白名单（可选择录入）">
                    <Table
                      size="small"
                      rowKey={(_, idx) => String(idx)}
                      pagination={false}
                      dataSource={dimBindings}
                      columns={[
                        {
                          title: '维度实体',
                          dataIndex: 'dim_entity_id',
                          width: 520,
                          render: (_: any, r: any, idx: number) => (
                            <Select
                              showSearch
                              optionFilterProp="label"
                              value={r.dim_entity_id}
                              style={{ width: '100%' }}
                              options={entityOptions}
                              onChange={(v) => {
                                const ent = (dbEntities || []).find((x: any) => String(x.id) === String(v));
                                setDimBindings((p) =>
                                  p.map((x, i) =>
                                    i === idx ? { ...x, dim_entity_id: v, dim_entity_name: ent?.entity_name || x.dim_entity_name } : x
                                  )
                                );
                              }}
                            />
                          ),
                        },
                        { title: '路由状态', dataIndex: 'join_route_status', width: 120, render: (v: any) => <StatusTag preset={v === 'ready' ? 'success' : v === 'missing' ? 'error' : 'default'}>{v || '-'}</StatusTag> },
                        { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => setDimBindings((p) => p.filter((_, i) => i !== idx))}>删除</Button> },
                      ]}
                    />
                    <Space style={{ marginTop: 12 }} wrap>
                      <Button onClick={() => setDimBindings((p) => [...p, { dim_entity_id: '', dim_entity_name: '', enabled: true }])}>新增维度</Button>
                      <Button type="primary" onClick={onSaveDimBindings} loading={loading}>保存白名单</Button>
                    </Space>
                  </Card>

                  <Card size="small" title="过滤白名单（可选择录入）">
                    <Table
                      size="small"
                      rowKey={(_, idx) => String(idx)}
                      pagination={false}
                      dataSource={filterWhitelist}
                      columns={[
                        {
                          title: 'field_full_name',
                          dataIndex: 'field_full_name',
                          render: (_: any, r: any, idx: number) => (
                            <Input value={r.field_full_name} onChange={(e) => setFilterWhitelist((p) => p.map((x, i) => (i === idx ? { ...x, field_full_name: e.target.value } : x)))} />
                          ),
                        },
                        {
                          title: 'field_cn',
                          dataIndex: 'field_cn',
                          width: 180,
                          render: (_: any, r: any, idx: number) => (
                            <Input value={r.field_cn || ''} onChange={(e) => setFilterWhitelist((p) => p.map((x, i) => (i === idx ? { ...x, field_cn: e.target.value } : x)))} />
                          ),
                        },
                        {
                          title: 'op_whitelist_json',
                          dataIndex: 'op_whitelist_json',
                          width: 260,
                          render: (_: any, r: any, idx: number) => (
                            <Input value={typeof r.op_whitelist_json === 'string' ? r.op_whitelist_json : JSON.stringify(r.op_whitelist_json ?? '')} onChange={(e) => setFilterWhitelist((p) => p.map((x, i) => (i === idx ? { ...x, op_whitelist_json: e.target.value } : x)))} />
                          ),
                        },
                        { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => setFilterWhitelist((p) => p.filter((_, i) => i !== idx))}>删除</Button> },
                      ]}
                    />
                    <Space style={{ marginTop: 12 }} wrap>
                      <Button onClick={() => setFilterWhitelist((p) => [...p, { field_full_name: '', field_cn: '', op_whitelist_json: '["=","!=","IN","BETWEEN"]', enabled: true }])}>新增字段</Button>
                      <Button type="primary" onClick={onSaveFilterWhitelist} loading={loading}>保存白名单</Button>
                    </Space>
                  </Card>

                  <Card size="small" title="治理流转">
                    <Space wrap>
                      <Button onClick={() => runWorkflowAction('submit')} disabled={loading}>提交评审</Button>
                      <Button onClick={() => runWorkflowAction('approve')} disabled={loading}>审核通过</Button>
                      <Button danger onClick={() => runWorkflowAction('reject')} disabled={loading}>驳回</Button>
                      <Button type="primary" onClick={() => runWorkflowAction('publish')} disabled={loading}>发布</Button>
                    </Space>
                  </Card>
                </Space>
              ),
            },
            {
              key: 'derived',
              label: '派生指标管理',
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size={12}>
                  {(metricDetail?.metric?.metric_type || '') !== 'derived' ? (
                    <Card size="small" title="提示">
                      <Text type="secondary">当前指标不是 derived 类型。</Text>
                    </Card>
                  ) : (
                    <>
                      <Card size="small" title="拖拽配置（原子指标 / 统计周期 / 可用维度）">
                        <Space align="start" style={{ width: '100%' }} size={12}>
                          <Card size="small" title="原子指标池（可拖拽）" style={{ width: 320 }}>
                            <div style={{ maxHeight: 320, overflow: 'auto' }}>
                              {(atomicMetricOptions || []).map((o: any) => (
                                <div
                                  key={o.value}
                                  draggable
                                  onDragStart={(e) => e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'base_metric', value: o.value }))}
                                  style={{ padding: '6px 8px', border: '1px solid var(--color-border)', borderRadius: 4, marginBottom: 8, cursor: 'grab', background: 'var(--bg-content)' }}
                                >
                                  <Text>{o.label}</Text>
                                </div>
                              ))}
                            </div>
                          </Card>
                          <Card
                            size="small"
                            title="派生配置区"
                            style={{ flex: 1 }}
                            extra={
                              <Button
                                onClick={() => {
                                  derivedForm.setFieldsValue({ config_mode: 'config' });
                                }}
                              >
                                切换到配置模式
                              </Button>
                            }
                          >
                            <Form form={derivedForm} layout="vertical" initialValues={{ config_mode: 'config' }}>
                              <Space wrap>
                                <Form.Item name="config_mode" label="配置模式" style={{ width: 200 }}>
                                  <Select
                                    options={[
                                      { label: 'config（拖拽/选择）', value: 'config' },
                                      { label: 'dsl（表达式）', value: 'dsl' },
                                    ]}
                                  />
                                </Form.Item>
                                <Form.Item name="time_period" label="统计周期" style={{ width: 220 }}>
                                  <Select
                                    allowClear
                                    disabled={watchedDerivedMode !== 'config'}
                                    options={[
                                      { label: 'CURRENT_MONTH(本月)', value: 'CURRENT_MONTH' },
                                      { label: 'LAST_MONTH(上月)', value: 'LAST_MONTH' },
                                      { label: 'YTD(年初至今)', value: 'YTD' },
                                      { label: 'CURRENT_YEAR(今年)', value: 'CURRENT_YEAR' },
                                      { label: 'LAST_YEAR(去年)', value: 'LAST_YEAR' },
                                      { label: 'LAST_7_DAYS(近7天)', value: 'LAST_7_DAYS' },
                                      { label: 'LAST_30_DAYS(近30天)', value: 'LAST_30_DAYS' },
                                    ]}
                                  />
                                </Form.Item>
                                <Form.Item name="unit" label="单位" style={{ width: 160 }}><Input /></Form.Item>
                                <Form.Item name="precision" label="精度" style={{ width: 160 }}><Input /></Form.Item>
                              </Space>

                              <Card
                                size="small"
                                title="原子指标（拖拽到此处 / 或下拉选择）"
                                style={{ marginBottom: 12 }}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={onDropBaseMetric}
                              >
                                <Space wrap>
                                  <Form.Item name="base_metric_id" label="原子指标" style={{ width: 420 }}>
                                    <Select
                                      showSearch
                                      optionFilterProp="label"
                                      disabled={watchedDerivedMode !== 'config'}
                                      options={atomicMetricOptions}
                                      value={derivedBaseMetricId || undefined}
                                      onChange={(v) => {
                                        setDerivedBaseMetricId(String(v || ''));
                                        derivedForm.setFieldsValue({ base_metric_id: v });
                                      }}
                                    />
                                  </Form.Item>
                                  <StatusTag preset={derivedBaseMetricId ? 'success' : 'error'}>{derivedBaseMetricId ? '已选择原子指标' : '未选择'}</StatusTag>
                                </Space>
                              </Card>

                              <Card
                                size="small"
                                title="可用维度（拖拽维度字段到此处 / 或多选）"
                                style={{ marginBottom: 12 }}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={onDropDim}
                              >
                                <Space align="start" style={{ width: '100%' }} size={12}>
                                  <Card size="small" title="维度字段池（来自维度白名单）" style={{ width: 360 }}>
                                    <div style={{ maxHeight: 260, overflow: 'auto' }}>
                                      {(dimFieldOptions || []).map((o: any) => (
                                        <div
                                          key={o.value}
                                          draggable
                                          onDragStart={(e) => e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'dim_field', value: o.value }))}
                                          style={{ padding: '6px 8px', border: '1px solid var(--color-border)', borderRadius: 4, marginBottom: 8, cursor: 'grab', background: 'var(--bg-content)' }}
                                        >
                                          <Text>{o.label}</Text>
                                        </div>
                                      ))}
                                    </div>
                                  </Card>
                                  <div style={{ flex: 1 }}>
                                    <Select
                                      mode="multiple"
                                      style={{ width: '100%' }}
                                      disabled={watchedDerivedMode !== 'config'}
                                      value={derivedAvailableDims}
                                      onChange={(v) => {
                                        setDerivedAvailableDims(v as string[]);
                                        derivedForm.setFieldsValue({ available_dims_json: v });
                                      }}
                                      options={dimFieldOptions}
                                      placeholder="选择可用维度字段"
                                    />
                                    <div style={{ marginTop: 8 }}>
                                      {(derivedAvailableDims || []).map((x) => (
                                        <Tag
                                          key={x}
                                          closable
                                          onClose={() => {
                                            setDerivedAvailableDims((p) => p.filter((y) => y !== x));
                                          }}
                                        >
                                          {x}
                                        </Tag>
                                      ))}
                                    </div>
                                  </div>
                                </Space>
                              </Card>

                              <Card size="small" title="派生预置过滤（列表配置）" style={{ marginBottom: 12 }}>
                                <Table
                                  size="small"
                                  rowKey={(_, idx) => String(idx)}
                                  pagination={false}
                                  dataSource={derivedPresetFilters}
                                  columns={[
                                    {
                                      title: 'field_full_name',
                                      dataIndex: 'field_full_name',
                                      render: (_: any, r: any, idx: number) => (
                                        <Select
                                          showSearch
                                          optionFilterProp="label"
                                          value={r.field_full_name}
                                          style={{ width: '100%' }}
                                          options={filterFieldOptions}
                                          onChange={(v) => setDerivedPresetFilters((p) => p.map((x, i) => (i === idx ? { ...x, field_full_name: v } : x)))}
                                        />
                                      ),
                                    },
                                    {
                                      title: 'op',
                                      dataIndex: 'op',
                                      width: 140,
                                      render: (_: any, r: any, idx: number) => (
                                        <Select
                                          value={r.op || '='}
                                          style={{ width: '100%' }}
                                          onChange={(v) => setDerivedPresetFilters((p) => p.map((x, i) => (i === idx ? { ...x, op: v } : x)))}
                                          options={[
                                            { label: '=', value: '=' },
                                            { label: '!=', value: '!=' },
                                            { label: 'IN', value: 'IN' },
                                            { label: 'NOT IN', value: 'NOT IN' },
                                            { label: 'BETWEEN', value: 'BETWEEN' },
                                            { label: 'IS NULL', value: 'IS NULL' },
                                            { label: 'IS NOT NULL', value: 'IS NOT NULL' },
                                            { label: 'LIKE', value: 'LIKE' },
                                            { label: 'NOT LIKE', value: 'NOT LIKE' },
                                          ]}
                                        />
                                      ),
                                    },
                                    {
                                      title: 'value',
                                      dataIndex: 'value',
                                      render: (_: any, r: any, idx: number) => (
                                        <Input value={r.value ?? ''} onChange={(e) => setDerivedPresetFilters((p) => p.map((x, i) => (i === idx ? { ...x, value: e.target.value } : x)))} />
                                      ),
                                    },
                                    { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => setDerivedPresetFilters((p) => p.filter((_, i) => i !== idx))}>删除</Button> },
                                  ]}
                                />
                                <Space style={{ marginTop: 12 }} wrap>
                                  <Button onClick={() => setDerivedPresetFilters((p) => [...p, { field_full_name: '', op: '=', value: '' }])}>新增过滤</Button>
                                </Space>
                              </Card>

                              {watchedDerivedMode === 'dsl' ? (
                                <Card size="small" title="表达式DSL（可选）" style={{ marginBottom: 12 }}>
                                  <Form.Item name="expr_dsl" label="表达式DSL" rules={[{ required: true }]}>
                                    <Input.TextArea rows={4} placeholder="示例：metric('m_a') / nullif(metric('m_b'),0)" />
                                  </Form.Item>
                                </Card>
                              ) : null}

                              <Space wrap>
                                <Button type="primary" onClick={onSaveDerived} loading={loading}>保存派生配置</Button>
                              </Space>
                            </Form>
                          </Card>
                        </Space>
                      </Card>

                      <Card size="small" title="依赖指标（deps）">
                        <Table
                          size="small"
                          rowKey={(_, idx) => String(idx)}
                          pagination={false}
                          dataSource={deps}
                          columns={[
                            {
                              title: 'dep_metric_id',
                              dataIndex: 'dep_metric_id',
                              render: (_: any, r: any, idx: number) => (
                                <Select
                                  value={r.dep_metric_id}
                                  style={{ width: '100%' }}
                                  options={metricOptions}
                                  onChange={(v) => setDeps((p) => p.map((x, i) => (i === idx ? { ...x, dep_metric_id: v } : x)))}
                                />
                              ),
                            },
                            {
                              title: 'dep_role',
                              dataIndex: 'dep_role',
                              width: 160,
                              render: (_: any, r: any, idx: number) => (
                                <Input value={r.dep_role || ''} onChange={(e) => setDeps((p) => p.map((x, i) => (i === idx ? { ...x, dep_role: e.target.value } : x)))} />
                              ),
                            },
                            { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => setDeps((p) => p.filter((_, i) => i !== idx))}>删除</Button> },
                          ]}
                        />
                        <Space style={{ marginTop: 12 }} wrap>
                          <Button onClick={() => setDeps((p) => [...p, { dep_metric_id: '', dep_role: '' }])}>新增依赖</Button>
                          <Button type="primary" onClick={onSaveDeps} loading={loading}>保存依赖</Button>
                        </Space>
                      </Card>
                    </>
                  )}
                </Space>
              ),
            },
            {
              key: 'lineage',
              label: '指标血缘',
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size={12}>
                  <Card size="small" title="指标血缘图">
                    {lineageData ? <LineageGraph mode="embed" data={lineageData} height={420} /> : <Text type="secondary">暂无血缘数据</Text>}
                  </Card>
                  <Card size="small" title="变更记录（MetricAuditLog）">
                    <Table
                      size="small"
                      rowKey="id"
                      pagination={{ pageSize: 8 }}
                      dataSource={auditLogs}
                      columns={[
                        { title: 'action', dataIndex: 'action', width: 120 },
                        { title: 'operator', dataIndex: 'operator', width: 160 },
                        { title: 'created_at', dataIndex: 'created_at', width: 200 },
                        {
                          title: 'after_json',
                          dataIndex: 'after_json',
                          render: (v: any) => (
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 120, overflow: 'auto' }}>
                              {JSON.stringify(v ?? {}, null, 2)}
                            </pre>
                          ),
                        },
                      ]}
                    />
                  </Card>
                </Space>
              ),
            },
            {
              key: 'versions',
              label: '版本快照',
              children: (
                <Card size="small" title="版本列表">
                  <Table
                    size="small"
                    rowKey="version"
                    pagination={false}
                    dataSource={versions}
                    columns={[
                      { title: 'version', dataIndex: 'version', width: 100 },
                      { title: 'status', dataIndex: 'status', width: 120 },
                      { title: 'created_by', dataIndex: 'created_by', width: 160 },
                      { title: 'created_at', dataIndex: 'created_at', width: 200 },
                      {
                        title: '操作',
                        width: 180,
                        render: (_: any, r: any) => (
                          <Space>
                            <Button size="small" onClick={() => previewSnapshot(Number(r.version))}>预览</Button>
                            <Button size="small" danger onClick={() => doRollback(Number(r.version))}>回滚</Button>
                          </Space>
                        ),
                      },
                    ]}
                  />
                  <Text type="secondary">说明：发布/提交/审核会写入版本快照，便于稽核与回滚。</Text>
                </Card>
              ),
            },
          ]}
        />
      </Drawer>

      <Modal open={snapshotOpen} title="版本快照预览" footer={null} onCancel={() => setSnapshotOpen(false)} width={900}>
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 560, overflow: 'auto' }}>
          {JSON.stringify(snapshotData, null, 2)}
        </pre>
      </Modal>
    </PageShell>
  );
};

export default MetricManager;
