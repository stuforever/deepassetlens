import React, { useCallback, useEffect, useState } from 'react';
import { Button, Card, Divider, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Typography, message, Switch } from 'antd';
import { AppstoreAddOutlined, EditOutlined, ExperimentOutlined } from '@ant-design/icons';
import { llmAdminApi } from '../services/api';
import { PageShell, StatusTag } from '../components/shell';

const { Text } = Typography;
const MODE_OPTIONS = [
  { value: 'quick', label: '快速响应' },
  { value: 'deep', label: '深度思考' },
];
const EFFORT_OPTIONS = [
  { value: 'low', label: 'low' },
  { value: 'medium', label: 'medium' },
  { value: 'high', label: 'high' },
];

const parseJsonObject = (raw?: string, fallback: Record<string, any> = {}) => {
  const text = String(raw || '').trim();
  if (!text) return { ...fallback };
  const parsed = JSON.parse(text);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('必须是 JSON 对象');
  }
  return parsed as Record<string, any>;
};

const getReasoningEffort = (profile?: Record<string, any>) => {
  const direct = String(profile?.reasoning_effort || '').trim().toLowerCase();
  if (direct) return direct;
  const nested = String(profile?.extra_body?.reasoning?.effort || '').trim().toLowerCase();
  return nested || undefined;
};

const buildModeProfile = (values: any, prefix: 'quick' | 'deep') => {
  const extraBody = parseJsonObject(values[`${prefix}_extra_body`], {});
  const profile: Record<string, any> = {
    temperature: values[`${prefix}_temperature`] ?? undefined,
    max_tokens: values[`${prefix}_max_tokens`] ?? undefined,
    timeout_seconds: values[`${prefix}_timeout_seconds`] ?? undefined,
    reasoning_effort: values[`${prefix}_reasoning_effort`] || undefined,
    extra_body: extraBody,
  };
  Object.keys(profile).forEach((key) => {
    if (profile[key] === undefined || profile[key] === null || profile[key] === '') {
      delete profile[key];
    }
  });
  return profile;
};

const buildConnectionExtraConfig = (values: any) => {
  const base = parseJsonObject(values.extra_config, {});
  return {
    ...base,
    default_mode: values.default_mode || 'quick',
    mode_profiles: {
      ...(base.mode_profiles && typeof base.mode_profiles === 'object' ? base.mode_profiles : {}),
      quick: buildModeProfile(values, 'quick'),
      deep: buildModeProfile(values, 'deep'),
    },
  };
};

const LLMConfigManager: React.FC = () => {
  const [connections, setConnections] = useState<any[]>([]);
  const [planner, setPlanner] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [connOpen, setConnOpen] = useState(false);
  const [editingConn, setEditingConn] = useState<any | null>(null);
  const [plannerLoading, setPlannerLoading] = useState(false);
  const [connForm] = Form.useForm();
  const [plannerForm] = Form.useForm();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, pRes] = await Promise.all([llmAdminApi.getConnections(), llmAdminApi.getPlannerConfig()]);
      setConnections(cRes?.data?.data || []);
      const p = pRes?.data?.data || null;
      setPlanner(p);
      plannerForm.setFieldsValue({
        planner_mode: p?.planner_mode || 'rule',
        llm_connection_id: p?.llm_connection_id,
        enabled: p?.enabled ?? true,
        system_prompt: p?.system_prompt,
        query_entity_workflow_code: p?.query_entity_workflow_code || 'query_entity_main_workflow',
      });
    } catch (e) {
      console.error(e);
      message.error('加载LLM配置失败');
    } finally {
      setLoading(false);
    }
  }, [plannerForm]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditingConn(null);
    connForm.resetFields();
    connForm.setFieldsValue({
      provider: 'openai_compatible',
      description: 'OpenAI兼容连接',
      is_default: false,
      enabled: true,
      temperature: '0.2',
      max_tokens: 512,
      timeout_seconds: 60,
      base_url: 'https://api.openai.com/v1',
      api_path: '/chat/completions',
      extra_config: '{}',
      default_mode: 'quick',
      quick_temperature: '0.2',
      quick_max_tokens: 512,
      quick_timeout_seconds: 30,
      quick_reasoning_effort: 'low',
      quick_extra_body: '{}',
      deep_temperature: '0.2',
      deep_max_tokens: 2048,
      deep_timeout_seconds: 120,
      deep_reasoning_effort: 'high',
      deep_extra_body: '{}',
    });
    setConnOpen(true);
  };

  const openEdit = (row: any) => {
    const extra = row.extra_config && typeof row.extra_config === 'object' ? row.extra_config : {};
    const quickProfile = extra?.mode_profiles?.quick || {};
    const deepProfile = extra?.mode_profiles?.deep || {};
    setEditingConn(row);
    connForm.setFieldsValue({
      ...row,
      is_default: !!row.is_default,
      extra_config: JSON.stringify(extra, null, 2),
      default_mode: extra.default_mode || 'quick',
      quick_temperature: quickProfile.temperature ?? row.temperature ?? '0.2',
      quick_max_tokens: quickProfile.max_tokens ?? row.max_tokens ?? 512,
      quick_timeout_seconds: quickProfile.timeout_seconds ?? row.timeout_seconds ?? 60,
      quick_reasoning_effort: getReasoningEffort(quickProfile) || 'low',
      quick_extra_body: JSON.stringify(quickProfile.extra_body || {}, null, 2),
      deep_temperature: deepProfile.temperature ?? row.temperature ?? '0.2',
      deep_max_tokens: deepProfile.max_tokens ?? Math.max(Number(row.max_tokens || 512), 2048),
      deep_timeout_seconds: deepProfile.timeout_seconds ?? Math.max(Number(row.timeout_seconds || 60), 120),
      deep_reasoning_effort: getReasoningEffort(deepProfile) || 'high',
      deep_extra_body: JSON.stringify(deepProfile.extra_body || {}, null, 2),
    });
    setConnOpen(true);
  };

  const saveConn = async () => {
    const v = await connForm.validateFields();
    try {
      const payload = {
        ...v,
        extra_config: buildConnectionExtraConfig(v),
      };
      if (editingConn) {
        await llmAdminApi.updateConnection(editingConn.id, payload);
      } else {
        await llmAdminApi.createConnection(payload);
      }
      message.success('连接保存成功');
      setConnOpen(false);
      loadData();
    } catch (e: any) {
      message.error(e?.message || e?.response?.data?.detail || '连接保存失败');
    }
  };

  const testConn = async (id: string) => {
    try {
      const res = await llmAdminApi.testConnection(id);
      const data = res?.data?.data || {};
      if (data.ok) {
        message.success('连接测试成功');
      } else {
        message.warning(`连接测试失败: ${data.error || '未知错误'}`);
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '连接测试失败');
    }
  };

  const removeConn = async (id: string) => {
    await llmAdminApi.deleteConnection(id);
    message.success('连接已删除');
    loadData();
  };

  const savePlanner = async () => {
    const v = await plannerForm.validateFields();
    setPlannerLoading(true);
    try {
      await llmAdminApi.upsertPlannerConfig({
        planner_mode: v.planner_mode,
        llm_connection_id: v.llm_connection_id || null,
        enabled: !!v.enabled,
        system_prompt: v.system_prompt,
        query_entity_workflow_code: v.query_entity_workflow_code || 'query_entity_main_workflow',
      });
      message.success('规划器配置已保存');
      loadData();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '规划器配置保存失败');
    } finally {
      setPlannerLoading(false);
    }
  };

  return (
    <PageShell title="LLM 配置">
      <Tabs
        items={[
          {
            key: 'conn',
            label: '大模型连接',
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button type="primary" icon={<AppstoreAddOutlined />} onClick={openCreate}>
                  新增连接
                </Button>
                <Table
                  rowKey="id"
                  loading={loading}
                  dataSource={connections}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 240, render: (v: string) => v ? <Text copyable>{v}</Text> : '-' },
                    { title: '名称', dataIndex: 'name', width: 140 },
                    {
                      title: '默认',
                      dataIndex: 'is_default',
                      width: 90,
                      render: (v: boolean) => v ? <StatusTag preset="warning">默认</StatusTag> : '-',
                    },
                    { title: 'Provider', dataIndex: 'provider', width: 150 },
                    { title: '描述', dataIndex: 'description', width: 220, ellipsis: true },
                    { title: 'Base URL', dataIndex: 'base_url', ellipsis: true },
                    { title: 'API Path', dataIndex: 'api_path', width: 160 },
                    { title: '模型', dataIndex: 'model_name', width: 140 },
                    {
                      title: '默认模式',
                      width: 100,
                      render: (_: any, row: any) => (
                        <StatusTag preset={(row?.extra_config?.default_mode || 'quick') === 'deep' ? 'ai' : 'info'}>
                          {(row?.extra_config?.default_mode || 'quick') === 'deep' ? '深度思考' : '快速响应'}
                        </StatusTag>
                      ),
                    },
                    { title: '超时(秒)', dataIndex: 'timeout_seconds', width: 100, render: (v: number) => v || 60 },
                    {
                      title: '状态',
                      dataIndex: 'enabled',
                      width: 90,
                      render: (v: boolean) => <StatusTag preset={v ? 'success' : 'default'}>{v ? '启用' : '停用'}</StatusTag>,
                    },
                    {
                      title: '操作',
                      width: 420,
                      render: (_: any, row: any) => (
                        <Space>
                          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>
                            编辑
                          </Button>
                          {!row.is_default ? (
                            <Button size="small" onClick={() => llmAdminApi.updateConnection(row.id, { is_default: true }).then(() => { message.success('默认大模型已更新'); loadData(); }).catch((e: any) => message.error(e?.response?.data?.detail || '设置默认大模型失败'))}>
                              设为默认
                            </Button>
                          ) : (
                            <StatusTag preset="warning">当前默认</StatusTag>
                          )}
                          <Button size="small" icon={<ExperimentOutlined />} onClick={() => testConn(row.id)}>
                            测试连接
                          </Button>
                          <Button size="small" danger onClick={() => removeConn(row.id)}>
                            删除
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: 'planner',
            label: 'LLM规划器',
            children: (
              <Form form={plannerForm} layout="vertical">
                <Form.Item name="enabled" label="启用规划器" valuePropName="checked">
                  <Switch />
                </Form.Item>
                <Form.Item name="planner_mode" label="规划模式" rules={[{ required: true }]}>
                  <Select options={[{ value: 'rule', label: '规则规划' }, { value: 'llm', label: 'LLM规划' }]} />
                </Form.Item>
                <Form.Item name="llm_connection_id" label="LLM连接">
                  <Select
                    allowClear
                    options={connections.map((c: any) => ({ value: c.id, label: `${c.name} (${c.model_name})` }))}
                  />
                </Form.Item>
                <Form.Item name="system_prompt" label="规划系统提示词">
                  <Input.TextArea rows={6} placeholder="可选，留空走默认规划提示词" />
                </Form.Item>
                <Form.Item
                  name="query_entity_workflow_code"
                  label="问实体工作流代码"
                  rules={[{ required: true, message: '请输入问实体工作流代码' }]}
                  extra="问实体主入口会按这里配置的 workflow code 执行，默认使用 query_entity_main_workflow。"
                >
                  <Input placeholder="query_entity_main_workflow" />
                </Form.Item>
                <Space>
                  <Button type="primary" loading={plannerLoading} onClick={savePlanner}>
                    保存规划配置
                  </Button>
                  {planner ? <Tag>当前模式: {planner.planner_mode}</Tag> : null}
                  {planner?.query_entity_workflow_code ? <StatusTag preset="info">问实体工作流: {planner.query_entity_workflow_code}</StatusTag> : null}
                </Space>
              </Form>
            ),
          },
        ]}
      />

      <Modal
        title={editingConn ? '编辑LLM连接' : '新增LLM连接'}
        open={connOpen}
        onOk={saveConn}
        onCancel={() => setConnOpen(false)}
        width={920}
      >
        <Form form={connForm} layout="vertical">
          <Form.Item name="name" label="连接名称" rules={[{ required: true }]}>
            <Input placeholder="例如：openai-prod" disabled={!!editingConn} />
          </Form.Item>
          <Form.Item name="provider" label="Provider" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'openai_compatible', label: 'openai_compatible' },
                { value: 'volcengine_doubao', label: 'volcengine_doubao(豆包)' },
              ]}
            />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input placeholder="例如：豆包生产连接（方舟）" />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL" rules={[{ required: true }]}>
            <Input placeholder="例如：https://api.openai.com/v1" />
          </Form.Item>
          <Form.Item name="api_path" label="API Path" rules={[{ required: true }]}>
            <Input placeholder="例如：/chat/completions" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder="sk-..." />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true }]}>
            <Input placeholder="例如：gpt-4o-mini" />
          </Form.Item>
          <Form.Item name="is_default" label="设为默认大模型" valuePropName="checked" initialValue={false}>
            <Switch />
          </Form.Item>
          <Form.Item name="enabled" label="是否启用" rules={[{ required: true }]}>
            <Select options={[{ value: true, label: '启用' }, { value: false, label: '停用' }]} />
          </Form.Item>
          <Form.Item name="temperature" label="temperature">
            <Input />
          </Form.Item>
          <Form.Item name="max_tokens" label="max_tokens">
            <Input />
          </Form.Item>
          <Form.Item
            name="timeout_seconds"
            label="超时时间（秒）"
            extra="所有调用该大模型连接的请求，超过这个时间后统一报错；内部更大的超时阈值也不会超过这里。"
            rules={[{ required: true, message: '请输入超时时间' }]}
          >
            <InputNumber min={1} max={600} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Divider orientation="left">模式预设</Divider>
          <Form.Item name="default_mode" label="默认调用模式" rules={[{ required: true, message: '请选择默认模式' }]}>
            <Select options={MODE_OPTIONS} />
          </Form.Item>
          <Space size={16} align="start" style={{ width: '100%', display: 'flex' }}>
            <Card size="small" title="快速响应" style={{ flex: 1 }}>
              <Form.Item name="quick_temperature" label="temperature">
                <Input />
              </Form.Item>
              <Form.Item name="quick_max_tokens" label="max_tokens">
                <InputNumber min={1} max={65535} precision={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="quick_timeout_seconds" label="超时（秒）">
                <InputNumber min={1} max={600} precision={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="quick_reasoning_effort" label="思考强度">
                <Select allowClear options={EFFORT_OPTIONS} />
              </Form.Item>
              <Form.Item name="quick_extra_body" label="附加请求体(JSON)">
                <Input.TextArea rows={4} placeholder='例如：{"reasoning":{"effort":"low"}}' />
              </Form.Item>
            </Card>
            <Card size="small" title="深度思考" style={{ flex: 1 }}>
              <Form.Item name="deep_temperature" label="temperature">
                <Input />
              </Form.Item>
              <Form.Item name="deep_max_tokens" label="max_tokens">
                <InputNumber min={1} max={65535} precision={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="deep_timeout_seconds" label="超时（秒）">
                <InputNumber min={1} max={600} precision={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="deep_reasoning_effort" label="思考强度">
                <Select allowClear options={EFFORT_OPTIONS} />
              </Form.Item>
              <Form.Item name="deep_extra_body" label="附加请求体(JSON)">
                <Input.TextArea rows={4} placeholder='例如：{"reasoning":{"effort":"high"}}' />
              </Form.Item>
            </Card>
          </Space>
          <Form.Item name="extra_config" label="扩展配置(JSON)">
            <Input.TextArea rows={6} placeholder='例如：{"vendor":"custom","mode_profiles":{"quick":{"extra_body":{}}}}' />
          </Form.Item>
        </Form>
      </Modal>
    </PageShell>
  );
};

export default LLMConfigManager;
