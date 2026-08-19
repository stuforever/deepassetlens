/**
 * MetricAtomConfig —— 原子指标定义 + 口径过滤（atom_filters）（纯展示 + 事件上抛）
 *
 * 从 MetricManager 抽离：事实实体/数据源/聚合方式等表单 + 过滤条件行内编辑表。
 */
import React from 'react';
import { Card, Form, Input, Select, Space, Button, Table } from 'antd';
import type { FormInstance } from 'antd';

export type MetricAtomConfigProps = {
  atomForm: FormInstance;
  entityOptions: any[];
  dbEntities: any[];
  dataSources: any[];
  factFieldOptions: any[];
  onSaveAtom: () => void;
  atomFilters: any[];
  onAtomFiltersChange: React.Dispatch<React.SetStateAction<any[]>>;
  onSaveAtomFilters: () => void;
  loading: boolean;
};

const MetricAtomConfig: React.FC<MetricAtomConfigProps> = (p) => (
  <Card size="small" title="原子指标定义（可选择录入）">
    <Form form={p.atomForm} layout="vertical">
      <Space wrap>
        <Form.Item name="fact_entity_id" label="事实实体" rules={[{ required: true }]} style={{ width: 420 }}>
          <Select
            showSearch
            optionFilterProp="label"
            options={p.entityOptions}
            onChange={(v) => {
              const ent = (p.dbEntities || []).find((x: any) => String(x.id) === String(v));
              if (ent) {
                p.atomForm.setFieldsValue({
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
            options={(p.dataSources || []).map((d: any) => ({
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
          <Select allowClear showSearch optionFilterProp="label" options={p.factFieldOptions} />
        </Form.Item>
        <Form.Item name="time_field_en" label="时间字段" rules={[{ required: true }]} style={{ width: 320 }}>
          <Select allowClear showSearch optionFilterProp="label" options={p.factFieldOptions} />
        </Form.Item>
        <Form.Item name="default_limit" label="limit" style={{ width: 160 }}><Input /></Form.Item>
      </Space>
      <Button type="primary" onClick={p.onSaveAtom} loading={p.loading}>保存原子定义</Button>
    </Form>

    <Card size="small" title="口径过滤（atom_filters）" style={{ marginTop: 12 }}>
      <Table
        size="small"
        rowKey={(_, idx) => String(idx)}
        pagination={false}
        dataSource={p.atomFilters}
        columns={[
          {
            title: 'field_full_name',
            dataIndex: 'field_full_name',
            render: (_: any, r: any, idx: number) => (
              <Input value={r.field_full_name} onChange={(e) => p.onAtomFiltersChange((prev) => prev.map((x, i) => (i === idx ? { ...x, field_full_name: e.target.value } : x)))} />
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
                onChange={(v) => p.onAtomFiltersChange((prev) => prev.map((x, i) => (i === idx ? { ...x, op: v } : x)))}
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
              <Input value={typeof r.value_json === 'string' ? r.value_json : JSON.stringify(r.value_json ?? '')} onChange={(e) => p.onAtomFiltersChange((prev) => prev.map((x, i) => (i === idx ? { ...x, value_json: e.target.value } : x)))} />
            ),
          },
          { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => p.onAtomFiltersChange((prev) => prev.filter((_, i) => i !== idx))}>删除</Button> },
        ]}
      />
      <Space style={{ marginTop: 12 }} wrap>
        <Button onClick={() => p.onAtomFiltersChange((prev) => [...prev, { field_full_name: '', op: '=', value_json: '' }])}>新增过滤</Button>
        <Button type="primary" onClick={p.onSaveAtomFilters} loading={p.loading}>保存过滤</Button>
      </Space>
    </Card>
  </Card>
);

export default MetricAtomConfig;
