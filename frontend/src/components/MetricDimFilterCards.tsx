/**
 * MetricDimFilterCards —— 维度白名单 + 过滤白名单 + 治理流转（纯展示 + 事件上抛）
 *
 * 从 MetricManager 抽离：维度绑定/过滤字段 行内编辑表与治理流转操作按钮。
 */
import React from 'react';
import { Card, Table, Input, Select, Space, Button } from 'antd';
import { StatusTag } from './shell';

export type WorkflowAction = 'submit' | 'approve' | 'reject' | 'publish';

export type MetricDimFilterCardsProps = {
  dimBindings: any[];
  onDimBindingsChange: React.Dispatch<React.SetStateAction<any[]>>;
  onSaveDimBindings: () => void;
  filterWhitelist: any[];
  onFilterWhitelistChange: React.Dispatch<React.SetStateAction<any[]>>;
  onSaveFilterWhitelist: () => void;
  entityOptions: any[];
  dbEntities: any[];
  runWorkflowAction: (action: WorkflowAction) => void;
  loading: boolean;
};

const MetricDimFilterCards: React.FC<MetricDimFilterCardsProps> = (p) => (
  <>
    <Card size="small" title="维度白名单（可选择录入）">
      <Table
        size="small"
        rowKey={(_, idx) => String(idx)}
        pagination={false}
        dataSource={p.dimBindings}
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
                options={p.entityOptions}
                onChange={(v) => {
                  const ent = (p.dbEntities || []).find((x: any) => String(x.id) === String(v));
                  p.onDimBindingsChange((prev) =>
                    prev.map((x, i) =>
                      i === idx ? { ...x, dim_entity_id: v, dim_entity_name: ent?.entity_name || x.dim_entity_name } : x
                    )
                  );
                }}
              />
            ),
          },
          { title: '路由状态', dataIndex: 'join_route_status', width: 120, render: (v: any) => <StatusTag preset={v === 'ready' ? 'success' : v === 'missing' ? 'error' : 'default'}>{v || '-'}</StatusTag> },
          { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => p.onDimBindingsChange((prev) => prev.filter((_, i) => i !== idx))}>删除</Button> },
        ]}
      />
      <Space style={{ marginTop: 12 }} wrap>
        <Button onClick={() => p.onDimBindingsChange((prev) => [...prev, { dim_entity_id: '', dim_entity_name: '', enabled: true }])}>新增维度</Button>
        <Button type="primary" onClick={p.onSaveDimBindings} loading={p.loading}>保存白名单</Button>
      </Space>
    </Card>

    <Card size="small" title="过滤白名单（可选择录入）">
      <Table
        size="small"
        rowKey={(_, idx) => String(idx)}
        pagination={false}
        dataSource={p.filterWhitelist}
        columns={[
          {
            title: 'field_full_name',
            dataIndex: 'field_full_name',
            render: (_: any, r: any, idx: number) => (
              <Input value={r.field_full_name} onChange={(e) => p.onFilterWhitelistChange((prev) => prev.map((x, i) => (i === idx ? { ...x, field_full_name: e.target.value } : x)))} />
            ),
          },
          {
            title: 'field_cn',
            dataIndex: 'field_cn',
            width: 180,
            render: (_: any, r: any, idx: number) => (
              <Input value={r.field_cn || ''} onChange={(e) => p.onFilterWhitelistChange((prev) => prev.map((x, i) => (i === idx ? { ...x, field_cn: e.target.value } : x)))} />
            ),
          },
          {
            title: 'op_whitelist_json',
            dataIndex: 'op_whitelist_json',
            width: 260,
            render: (_: any, r: any, idx: number) => (
              <Input value={typeof r.op_whitelist_json === 'string' ? r.op_whitelist_json : JSON.stringify(r.op_whitelist_json ?? '')} onChange={(e) => p.onFilterWhitelistChange((prev) => prev.map((x, i) => (i === idx ? { ...x, op_whitelist_json: e.target.value } : x)))} />
            ),
          },
          { title: '操作', width: 120, render: (_: any, __: any, idx: number) => <Button danger onClick={() => p.onFilterWhitelistChange((prev) => prev.filter((_, i) => i !== idx))}>删除</Button> },
        ]}
      />
      <Space style={{ marginTop: 12 }} wrap>
        <Button onClick={() => p.onFilterWhitelistChange((prev) => [...prev, { field_full_name: '', field_cn: '', op_whitelist_json: '["=","!=","IN","BETWEEN"]', enabled: true }])}>新增字段</Button>
        <Button type="primary" onClick={p.onSaveFilterWhitelist} loading={p.loading}>保存白名单</Button>
      </Space>
    </Card>

    <Card size="small" title="治理流转">
      <Space wrap>
        <Button onClick={() => p.runWorkflowAction('submit')} disabled={p.loading}>提交评审</Button>
        <Button onClick={() => p.runWorkflowAction('approve')} disabled={p.loading}>审核通过</Button>
        <Button danger onClick={() => p.runWorkflowAction('reject')} disabled={p.loading}>驳回</Button>
        <Button type="primary" onClick={() => p.runWorkflowAction('publish')} disabled={p.loading}>发布</Button>
      </Space>
    </Card>
  </>
);

export default MetricDimFilterCards;
