import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Drawer, Form, Input, Modal, Select, Space, Tabs, Typography, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { conceptApi, metricCenterApi, dataSourceApi } from '../services/api';
import { PageShell, DataTableShell, StatusTag } from '../components/shell';
import MetricBaseInfo from '../components/MetricBaseInfo';
import MetricAliasesEditor from '../components/MetricAliasesEditor';
import MetricAtomConfig from '../components/MetricAtomConfig';
import MetricDimFilterCards from '../components/MetricDimFilterCards';
import MetricDerivedTab from '../components/MetricDerivedTab';
import { MetricLineageTab, MetricVersionsTab } from '../components/MetricLineageVersions';

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

    try {
      const dsRes = await dataSourceApi.list({ silent: true });
      setDataSources(dsRes?.data?.data || []);
    } catch {}
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
                  <MetricBaseInfo baseForm={baseForm} metricDetail={metricDetail} onSave={onUpdateBase} loading={loading} />
                  <MetricAliasesEditor aliases={aliases} onAliasesChange={setAliases} onSave={onSaveAliases} loading={loading} />
                  {(metricDetail?.metric?.metric_type || '') === 'atomic' ? (
                    <MetricAtomConfig
                      atomForm={atomForm}
                      entityOptions={entityOptions}
                      dbEntities={dbEntities}
                      dataSources={dataSources}
                      factFieldOptions={factFieldOptions}
                      onSaveAtom={onSaveAtom}
                      atomFilters={atomFilters}
                      onAtomFiltersChange={setAtomFilters}
                      onSaveAtomFilters={onSaveAtomFilters}
                      loading={loading}
                    />
                  ) : null}
                  <MetricDimFilterCards
                    dimBindings={dimBindings}
                    onDimBindingsChange={setDimBindings}
                    onSaveDimBindings={onSaveDimBindings}
                    filterWhitelist={filterWhitelist}
                    onFilterWhitelistChange={setFilterWhitelist}
                    onSaveFilterWhitelist={onSaveFilterWhitelist}
                    entityOptions={entityOptions}
                    dbEntities={dbEntities}
                    runWorkflowAction={runWorkflowAction}
                    loading={loading}
                  />
                </Space>
              ),
            },
            {
              key: 'derived',
              label: '派生指标管理',
              children: (
                <MetricDerivedTab
                  metricType={metricDetail?.metric?.metric_type || ''}
                  derivedForm={derivedForm}
                  watchedDerivedMode={watchedDerivedMode}
                  atomicMetricOptions={atomicMetricOptions}
                  dimFieldOptions={dimFieldOptions}
                  filterFieldOptions={filterFieldOptions}
                  metricOptions={metricOptions}
                  derivedBaseMetricId={derivedBaseMetricId}
                  onDerivedBaseMetricIdChange={setDerivedBaseMetricId}
                  derivedAvailableDims={derivedAvailableDims}
                  onDerivedAvailableDimsChange={setDerivedAvailableDims}
                  derivedPresetFilters={derivedPresetFilters}
                  onDerivedPresetFiltersChange={setDerivedPresetFilters}
                  deps={deps}
                  onDepsChange={setDeps}
                  onDropBaseMetric={onDropBaseMetric}
                  onDropDim={onDropDim}
                  onSaveDerived={onSaveDerived}
                  onSaveDeps={onSaveDeps}
                  loading={loading}
                />
              ),
            },
            {
              key: 'lineage',
              label: '指标血缘',
              children: <MetricLineageTab lineageData={lineageData} auditLogs={auditLogs} />,
            },
            {
              key: 'versions',
              label: '版本快照',
              children: <MetricVersionsTab versions={versions} onPreview={previewSnapshot} onRollback={doRollback} />,
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
