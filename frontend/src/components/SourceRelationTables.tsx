/**
 * SourceRelationTables —— 表间关联关系管理（L2/L4/跨层 三表切换，纯展示 + 事件上抛）
 *
 * 从 SourceManager 抽离：L2对象关系 / L4活动关系 / L4主表-L2主表关系 三个子 Tab。
 * 数据与编辑/删除回调经 props 传入；列定义按子 Tab 差异在此统一构建。
 */
import React from 'react';
import { Tabs, Table, Space, Button, Popconfirm } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';

export type RelationSubTab = 'l2' | 'l4' | 'cross';

export type SourceRelationTablesProps = {
  relationSubTab: RelationSubTab;
  onRelationSubTabChange: (k: RelationSubTab) => void;
  l2Relations: any[];
  l4Relations: any[];
  crossRelations: any[];
  onEdit: (record: any) => void;
  onDelete: (id: string | number) => void;
};

type ColumnOptions = { l3?: boolean; cross?: boolean };

const buildColumns = (opts: ColumnOptions, onEdit: (r: any) => void, onDelete: (id: any) => void) => [
  { title: 'L1名称', dataIndex: 'l1', width: 120 },
  { title: 'L2名称', dataIndex: 'l2', width: 120 },
  ...(opts.l3 ? [
    { title: 'L3名称', dataIndex: 'l3', width: 180 },
    { title: 'L4名称', dataIndex: 'l4', width: 160 },
  ] : []),
  { title: '关联说明', dataIndex: 'relation_desc', width: 180 },
  { title: opts.cross ? '主表中文名(L4前)' : '主表中文名', dataIndex: 'main_table_cn', width: opts.cross ? 160 : 140 },
  { title: opts.cross ? '主表英文名(L4前)' : '主表英文名', dataIndex: 'main_table_en', width: opts.cross ? 160 : 140 },
  { title: opts.cross ? '关联表中文名(L2后)' : '关联表中文名', dataIndex: 'related_table_cn', width: opts.cross ? 160 : 140 },
  { title: opts.cross ? '关联表英文名(L2后)' : '关联表英文名', dataIndex: 'related_table_en', width: opts.cross ? 160 : 140 },
  { title: '关系类别', dataIndex: 'relation_category', width: 120 },
  { title: '关联条件说明', dataIndex: 'relation_expr', width: 260 },
  { title: '备注', dataIndex: 'remark', width: 160 },
  {
    title: '操作',
    width: 100,
    render: (_: any, record: any) => (
      <Space size="small">
        <Button type="link" icon={<EditOutlined />} onClick={() => onEdit(record)} />
        <Popconfirm title="确定删除该关系吗?" onConfirm={() => onDelete(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      </Space>
    )
  },
];

const renderTable = (dataSource: any[], columns: any[]) => (
  <Table
    rowKey="id"
    size="small"
    bordered
    pagination={{ pageSize: 15 }}
    dataSource={dataSource}
    scroll={{ x: 'max-content' }}
    columns={columns}
  />
);

const SourceRelationTables: React.FC<SourceRelationTablesProps> = (p) => (
  <Tabs
    activeKey={p.relationSubTab}
    onChange={(k) => p.onRelationSubTabChange(k as RelationSubTab)}
    items={[
      { key: 'l2', label: 'L2对象关系', children: renderTable(p.l2Relations, buildColumns({}, p.onEdit, p.onDelete)) },
      { key: 'l4', label: 'L4活动关系', children: renderTable(p.l4Relations, buildColumns({ l3: true }, p.onEdit, p.onDelete)) },
      { key: 'cross', label: 'L4主表-L2主表关系', children: renderTable(p.crossRelations, buildColumns({ l3: true, cross: true }, p.onEdit, p.onDelete)) },
    ]}
  />
);

export default SourceRelationTables;
