/**
 * MappingRulesTable —— 映射规则列表（纯展示 + 事件上抛）
 *
 * 从 MappingManager 抽离：规则筛选栏 + 规则列表 Table（含字段映射明细展开行）。
 * 数据与回调全部经 props 传入；容器负责规则 CRUD 与查询状态。
 */
import React from 'react';
import { Card, Space, Button, Row, Col, Input, Select, Table, Popconfirm } from 'antd';
import { TERMS } from '../constants/standardTerms';

export type MappingRulesTableProps = {
  filteredMappingRules: any[];
  mappingInfoRows: any[];
  entityMetaById: Record<string, any>;
  dbEntities: any[];
  sourceMaster: any[];
  sourceBusiness: any[];
  sourceReference: any[];
  queryKeyword: string;
  onQueryKeywordChange: (v: string) => void;
  queryEntityId: string;
  onQueryEntityIdChange: (v: string) => void;
  querySourceTableId: string;
  onQuerySourceTableIdChange: (v: string) => void;
  viewingRuleId: string | null;
  onResetQuery: () => void;
  onCreateRule: () => void;
  onViewRule: (rule: any) => void;
  onEditRule: (rule: any) => void;
  onDeleteRule: (ruleId: string) => void;
  onPreviewSql: (rule: any) => void;
};

const MappingRulesTable: React.FC<MappingRulesTableProps> = (p) => {
  const allTables = [...p.sourceMaster, ...p.sourceBusiness, ...p.sourceReference];
  const getRuleEntityId = (r: any) => String((r?.entity_ids || [])[0] || '');
  const getRuleEntity = (r: any) => {
    const eid = getRuleEntityId(r);
    return (p.entityMetaById[eid] || p.dbEntities.find((e) => String(e.id) === eid)) || {};
  };
  const getEntityModeling = (r: any) => {
    const eid = getRuleEntityId(r);
    const ent = (p.entityMetaById[eid] || p.dbEntities.find((e) => String(e.id) === eid));
    return ent ? { model_table_cn: ent.entity_en_name || '' } : undefined;
  };
  const formatSourceTableNames = (r: any) => {
    const ids: string[] = r?.source_table_ids || [];
    const names = ids
      .map((id) => allTables.find((t) => String(t.id) === String(id)))
      .filter(Boolean)
      .map((t: any) => String(t.cnName || t.enName || '').trim())
      .filter(Boolean);
    return Array.from(new Set(names)).join('、');
  };

  const columns = [
    { title: TERMS.graphEntityCnName, key: 'entityName', width: 180, render: (_: any, r: any) => getRuleEntity(r)?.entity_name || getRuleEntity(r)?.label || '-' },
    { title: '实体落地中文表名', key: 'landingTableCn', width: 180, render: (_: any, r: any) => getEntityModeling(r)?.model_table_cn || '-' },
    { title: '来源表名', key: 'sourceTables', width: 240, ellipsis: true, render: (_: any, r: any) => formatSourceTableNames(r) || '-' },
    { title: '规则ID', dataIndex: 'id', width: 220, ellipsis: true },
    { title: '创建时间', dataIndex: 'created_at', width: 180, ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => p.onViewRule(record)}>查看</Button>
          <Button size="small" onClick={() => p.onPreviewSql(record)}>查看SQL</Button>
          <Button size="small" type="link" onClick={() => p.onEditRule(record)}>修改</Button>
          <Popconfirm title="确认删除该映射规则？" onConfirm={() => p.onDeleteRule(record.id)}>
            <Button size="small" danger type="link">删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <Card
      size="small"
      title={`${TERMS.mappingRule}列表`}
      style={{ marginBottom: 16 }}
      extra={
        <Space>
          <Button type="primary" onClick={p.onCreateRule}>新建映射规则</Button>
        </Space>
      }
    >
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={8}>
          <Input
            allowClear
            placeholder="按规则名/规则ID搜索"
            value={p.queryKeyword}
            onChange={(e) => p.onQueryKeywordChange(e.target.value)}
          />
        </Col>
        <Col span={7}>
          <Select
            allowClear
            showSearch
            placeholder="按图谱实体筛选"
            value={p.queryEntityId || undefined}
            onChange={(v) => p.onQueryEntityIdChange(v || '')}
            options={p.dbEntities.map((e) => ({
              value: String(e.id),
              label: `${e.entity_name || e.label} (${e.entity_code})`,
            }))}
            optionFilterProp="label"
            style={{ width: '100%' }}
          />
        </Col>
        <Col span={7}>
          <Select
            allowClear
            showSearch
            placeholder="按来源表筛选"
            value={p.querySourceTableId || undefined}
            onChange={(v) => p.onQuerySourceTableIdChange(v || '')}
            options={allTables.map((t) => ({
              value: String(t.id),
              label: `${t.enName} (${t.cnName || ''})`,
            }))}
            optionFilterProp="label"
            style={{ width: '100%' }}
          />
        </Col>
        <Col span={2}>
          <Button style={{ width: '100%' }} onClick={p.onResetQuery}>重置</Button>
        </Col>
      </Row>
      <Table
        size="small"
        rowKey="id"
        dataSource={p.filteredMappingRules}
        columns={columns}
        scroll={{ x: 'max-content' }}
        pagination={{ pageSize: 8 }}
        rowClassName={(record: any) => String(record.id) === String(p.viewingRuleId || '') ? 'ant-table-row-selected' : ''}
        expandable={{
          expandedRowRender: (record: any) => {
            const rows = p.mappingInfoRows.filter((r: any) => String(r.ruleId) === String(record.id));
            return (
              <Table
                size="small"
                rowKey="key"
                dataSource={rows}
                pagination={false}
                columns={[
                  { title: TERMS.entityFieldEnName, dataIndex: 'propEn', width: 120 },
                  { title: TERMS.entityFieldCnName, dataIndex: 'propCn', width: 120 },
                  { title: '是否主键', dataIndex: 'isPk', width: 80 },
                  { title: '字段类型', dataIndex: 'propType', width: 100 },
                  { title: TERMS.sourceTableEnName, dataIndex: 'tableEn', width: 150 },
                  { title: TERMS.sourceFieldEnName, dataIndex: 'fieldEn', width: 150 },
                  { title: TERMS.extractionLogic, dataIndex: 'desc' },
                ]}
                locale={{ emptyText: '该规则暂无字段映射明细' }}
              />
            );
          },
        }}
      />
    </Card>
  );
};

export default MappingRulesTable;
