/**
 * MetricAliasesEditor —— 指标别名编辑表（纯展示 + 事件上抛）
 *
 * 从 MetricManager 抽离：别名/类型/权重 行内编辑 Table + 新增/保存。
 */
import React from 'react';
import { Card, Table, Input, Select, Space, Button } from 'antd';

export type MetricAliasesEditorProps = {
  aliases: any[];
  onAliasesChange: React.Dispatch<React.SetStateAction<any[]>>;
  onSave: () => void;
  loading: boolean;
};

const MetricAliasesEditor: React.FC<MetricAliasesEditorProps> = (p) => (
  <Card size="small" title="别名（用于指标检索）">
    <Table
      size="small"
      rowKey={(_, idx) => String(idx)}
      pagination={false}
      dataSource={p.aliases}
      columns={[
        {
          title: 'alias',
          dataIndex: 'alias',
          render: (_: any, r: any, idx: number) => (
            <Input value={r.alias} onChange={(e) => p.onAliasesChange((prev) => prev.map((x, i) => (i === idx ? { ...x, alias: e.target.value } : x)))} />
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
              onChange={(v) => p.onAliasesChange((prev) => prev.map((x, i) => (i === idx ? { ...x, alias_type: v } : x)))}
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
            <Input value={String(r.weight ?? 1.0)} onChange={(e) => p.onAliasesChange((prev) => prev.map((x, i) => (i === idx ? { ...x, weight: Number(e.target.value || 1.0) } : x)))} />
          ),
        },
        {
          title: '操作',
          width: 120,
          render: (_: any, __: any, idx: number) => <Button danger onClick={() => p.onAliasesChange((prev) => prev.filter((_, i) => i !== idx))}>删除</Button>,
        },
      ]}
    />
    <Space style={{ marginTop: 12 }} wrap>
      <Button onClick={() => p.onAliasesChange((prev) => [...prev, { alias: '', alias_type: 'synonym', weight: 1.0, enabled: true }])}>新增别名</Button>
      <Button type="primary" onClick={p.onSave} loading={p.loading}>保存别名</Button>
    </Space>
  </Card>
);

export default MetricAliasesEditor;
