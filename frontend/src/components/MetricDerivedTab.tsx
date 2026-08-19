/**
 * MetricDerivedTab —— 派生指标管理（拖拽配置 + 依赖指标，纯展示 + 事件上抛）
 *
 * 从 MetricManager 抽离：非 derived 提示 / 原子指标池拖拽 / 派生配置区（config+dsl）/
 * 派生预置过滤 / 表达式 DSL / 依赖指标表。
 */
import React from 'react';
import { Card, Form, Input, Select, Space, Button, Table, Tag, Typography } from 'antd';
import type { FormInstance } from 'antd';
import { StatusTag } from './shell';

const { Text } = Typography;

export type MetricDerivedTabProps = {
  metricType: string;
  derivedForm: FormInstance;
  watchedDerivedMode: string | undefined;
  atomicMetricOptions: any[];
  dimFieldOptions: any[];
  filterFieldOptions: any[];
  metricOptions: any[];
  derivedBaseMetricId: string;
  onDerivedBaseMetricIdChange: React.Dispatch<React.SetStateAction<string>>;
  derivedAvailableDims: string[];
  onDerivedAvailableDimsChange: React.Dispatch<React.SetStateAction<string[]>>;
  derivedPresetFilters: any[];
  onDerivedPresetFiltersChange: React.Dispatch<React.SetStateAction<any[]>>;
  deps: any[];
  onDepsChange: React.Dispatch<React.SetStateAction<any[]>>;
  onDropBaseMetric: (e: React.DragEvent) => void;
  onDropDim: (e: React.DragEvent) => void;
  onSaveDerived: () => void;
  onSaveDeps: () => void;
  loading: boolean;
};

const MetricDerivedTab: React.FC<MetricDerivedTabProps> = (p) => {
  const isDerived = (p.metricType || '') === 'derived';
  const configMode = p.watchedDerivedMode === 'config';

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      {!isDerived ? (
        <Card size="small" title="提示">
          <Text type="secondary">当前指标不是 derived 类型。</Text>
        </Card>
      ) : (
        <>
          <Card size="small" title="拖拽配置（原子指标 / 统计周期 / 可用维度）">
            <Space align="start" style={{ width: '100%' }} size={12}>
              <Card size="small" title="原子指标池（可拖拽）" style={{ width: 320 }}>
                <div style={{ maxHeight: 320, overflow: 'auto' }}>
                  {(p.atomicMetricOptions || []).map((o: any) => (
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
                      p.derivedForm.setFieldsValue({ config_mode: 'config' });
                    }}
                  >
                    切换到配置模式
                  </Button>
                }
              >
                <Form form={p.derivedForm} layout="vertical" initialValues={{ config_mode: 'config' }}>
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
                        disabled={!configMode}
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
                    onDrop={p.onDropBaseMetric}
                  >
                    <Space wrap>
                      <Form.Item name="base_metric_id" label="原子指标" style={{ width: 420 }}>
                        <Select
                          showSearch
                          optionFilterProp="label"
                          disabled={!configMode}
                          options={p.atomicMetricOptions}
                          value={p.derivedBaseMetricId || undefined}
                          onChange={(v) => {
                            p.onDerivedBaseMetricIdChange(String(v || ''));
                            p.derivedForm.setFieldsValue({ base_metric_id: v });
                          }}
                        />
                      </Form.Item>
                      <StatusTag preset={p.derivedBaseMetricId ? 'success' : 'error'}>{p.derivedBaseMetricId ? '已选择原子指标' : '未选择'}</StatusTag>
                    </Space>
                  </Card>

                  <Card
                    size="small"
                    title="可用维度（拖拽维度字段到此处 / 或多选）"
                    style={{ marginBottom: 12 }}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={p.onDropDim}
                  >
                    <Space align="start" style={{ width: '100%' }} size={12}>
                      <Card size="small" title="维度字段池（来自维度白名单）" style={{ width: 360 }}>
                        <div style={{ maxHeight: 260, overflow: 'auto' }}>
                          {(p.dimFieldOptions || []).map((o: any) => (
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
                          disabled={!configMode}
                          value={p.derivedAvailableDims}
                          onChange={(v) => {
                            p.onDerivedAvailableDimsChange(v as string[]);
                            p.derivedForm.setFieldsValue({ available_dims_json: v });
                          }}
                          options={p.dimFieldOptions}
                          placeholder="选择可用维度字段"
                        />
                        <div style={{ marginTop: 8 }}>
                          {(p.derivedAvailableDims || []).map((x) => (
                            <Tag
                              key={x}
                              closable
                              onClose={() => {
                                p.onDerivedAvailableDimsChange((prev) => prev.filter((y) => y !== x));
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
                      dataSource={p.derivedPresetFilters}
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
                              options={p.filterFieldOptions}
                              onChange={(v) => p.onDerivedPresetFiltersChange((prev) => prev.map((x, i) => (i === idx ? { ...x, field_full_name: v } : x)))}
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
                              onChange={(v) => p.onDerivedPresetFiltersChange((prev) => prev.map((x, i) => (i === idx ? { ...x, op: v } : x)))}
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
                            <Input value={r.value ?? ''} onChange={(e) => p.onDerivedPresetFiltersChange((prev) => prev.map((x, i) => (i === idx ? { ...x, value: e.target.value } : x)))} />
                          ),
                        },
                        { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => p.onDerivedPresetFiltersChange((prev) => prev.filter((_, i) => i !== idx))}>删除</Button> },
                      ]}
                    />
                    <Space style={{ marginTop: 12 }} wrap>
                      <Button onClick={() => p.onDerivedPresetFiltersChange((prev) => [...prev, { field_full_name: '', op: '=', value: '' }])}>新增过滤</Button>
                    </Space>
                  </Card>

                  {p.watchedDerivedMode === 'dsl' ? (
                    <Card size="small" title="表达式DSL（可选）" style={{ marginBottom: 12 }}>
                      <Form.Item name="expr_dsl" label="表达式DSL" rules={[{ required: true }]}>
                        <Input.TextArea rows={4} placeholder="示例：metric('m_a') / nullif(metric('m_b'),0)" />
                      </Form.Item>
                    </Card>
                  ) : null}

                  <Space wrap>
                    <Button type="primary" onClick={p.onSaveDerived} loading={p.loading}>保存派生配置</Button>
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
              dataSource={p.deps}
              columns={[
                {
                  title: 'dep_metric_id',
                  dataIndex: 'dep_metric_id',
                  render: (_: any, r: any, idx: number) => (
                    <Select
                      value={r.dep_metric_id}
                      style={{ width: '100%' }}
                      options={p.metricOptions}
                      onChange={(v) => p.onDepsChange((prev) => prev.map((x, i) => (i === idx ? { ...x, dep_metric_id: v } : x)))}
                    />
                  ),
                },
                {
                  title: 'dep_role',
                  dataIndex: 'dep_role',
                  width: 160,
                  render: (_: any, r: any, idx: number) => (
                    <Input value={r.dep_role || ''} onChange={(e) => p.onDepsChange((prev) => prev.map((x, i) => (i === idx ? { ...x, dep_role: e.target.value } : x)))} />
                  ),
                },
                { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => p.onDepsChange((prev) => prev.filter((_, i) => i !== idx))}>删除</Button> },
              ]}
            />
            <Space style={{ marginTop: 12 }} wrap>
              <Button onClick={() => p.onDepsChange((prev) => [...prev, { dep_metric_id: '', dep_role: '' }])}>新增依赖</Button>
              <Button type="primary" onClick={p.onSaveDeps} loading={p.loading}>保存依赖</Button>
            </Space>
          </Card>
        </>
      )}
    </Space>
  );
};

export default MetricDerivedTab;
