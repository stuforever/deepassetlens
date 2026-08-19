/**
 * EntityPropertiesGrid —— 目标实体字段映射配置网格（纯展示 + 事件上抛）
 *
 * 从 MappingManager 抽离：实体属性表 + 主键开关 + 来源表选择 + 字段选择 + 抽取逻辑说明。
 * 数据与回调全部经 props 传入；readOnly 分支由容器解析好后传入对应 view* 数据。
 */
import React from 'react';
import { Card, Table, Switch, Select, Space, Button, Input, Typography } from 'antd';
import { AppstoreOutlined } from '@ant-design/icons';
import { StatusTag } from './shell';
import { TERMS } from '../constants/standardTerms';

const { Text } = Typography;

export type EntityPropertiesGridProps = {
  entity: any;
  readOnly?: boolean;
  pkOverrides: Record<string, boolean>;
  rowSourceTableFilter: Record<string, string>;
  fieldMappings: Record<string, string[]>;
  mappingDesc: Record<string, string>;
  selectedSourceTables: any[];
  parseMappingValue: (mv: string) => { tableId: string; fieldEn: string };
  onPkChange: (entityId: string, propName: string, checked: boolean) => void;
  onRowSourceTableChange: (entityId: string, propName: string, tableId: string) => void;
  onMappingDescChange: (entityId: string, propName: string, desc: string) => void;
  onOpenFieldPicker: (entity: any, record: any) => void;
};

const EntityPropertiesGrid: React.FC<EntityPropertiesGridProps> = ({
  entity, readOnly = false, pkOverrides, rowSourceTableFilter, fieldMappings,
  mappingDesc, selectedSourceTables, parseMappingValue,
  onPkChange, onRowSourceTableChange, onMappingDescChange, onOpenFieldPicker,
}) => {
  const props = entity.properties_schema || [];
  return (
    <Card
      size="small"
      title={
        <Space>
          <AppstoreOutlined />
          {entity.label}
          {entity.is_main_table ? <StatusTag preset="error">主表</StatusTag> : <StatusTag preset="default">辅表</StatusTag>}
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <Table
        size="small"
        pagination={false}
        rowKey="name"
        dataSource={props}
        columns={[
          { title: TERMS.entityFieldEnName, dataIndex: 'name', key: 'name', width: 100, render: (text: string) => <Text strong>{text}</Text> },
          { title: TERMS.entityFieldCnName, dataIndex: 'cnName', key: 'cnName', width: 100, render: (text: string) => <Text type="secondary">{text}</Text> },
          { title: '是否主键', dataIndex: 'isPrimaryKey', width: 100, render: (_: boolean, record: any) => {
            const key = `${entity.id}_${record.name}`;
            if (readOnly) {
              return <StatusTag preset={pkOverrides[key] ? 'error' : 'default'}>{pkOverrides[key] ? '是' : '否'}</StatusTag>;
            }
            return (
              <Switch
                checked={!!pkOverrides[key]}
                checkedChildren="是"
                unCheckedChildren="否"
                onChange={(checked) => onPkChange(entity.id, record.name, checked)}
              />
            );
          }},
          { title: '字段类型', dataIndex: 'type', width: 90 },
          { title: TERMS.sourceTableEnName, key: 'sourceTable', width: 140, render: (_: any, record: any) => {
              const key = `${entity.id}_${record.name}`;
              if (readOnly) {
                const mappingVals = fieldMappings[key] || [];
                const tableNames = (Array.isArray(mappingVals) ? mappingVals : [mappingVals]).map((mv: string) => {
                  const { tableId } = parseMappingValue(mv);
                  return selectedSourceTables.find(t => String(t.id) === String(tableId))?.enName || '';
                }).filter(Boolean);
                return <Text>{Array.from(new Set(tableNames)).join(' | ') || '-'}</Text>;
              }
              return (
                <Select
                  style={{ width: '100%' }}
                  placeholder="选择来源表英文名"
                  allowClear
                  value={rowSourceTableFilter[key]}
                  onChange={(val) => onRowSourceTableChange(entity.id, record.name, val)}
                >
                  {selectedSourceTables.map(t => (
                    <Select.Option key={t.id} value={t.id}>{t.enName}</Select.Option>
                  ))}
                </Select>
              );
          }},
          { title: TERMS.sourceFieldEnName, key: 'mapping', width: 220, render: (_: any, record: any) => {
            const key = `${entity.id}_${record.name}`;
            const currentVals = fieldMappings[key] || [];
            if (readOnly) {
              return <Text>{(Array.isArray(currentVals) ? currentVals : [currentVals]).map((mv: string) => parseMappingValue(mv).fieldEn).filter(Boolean).join(' | ') || '-'}</Text>;
            }
            return (
              <Space direction="vertical" style={{ width: '100%' }} size={4}>
                <Button size="small" onClick={() => onOpenFieldPicker(entity, record)}>
                  选择来源字段(多选)
                </Button>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  已选 {currentVals.length} 项
                </Text>
              </Space>
          )}},
          { title: TERMS.extractionLogic, key: 'desc', width: 150, render: (_: any, record: any) => {
            const key = `${entity.id}_${record.name}`;
            if (readOnly) {
              return <Text>{mappingDesc[key] || '-'}</Text>;
            }
            return (
              <Input
                placeholder={TERMS.extractionLogic}
                value={mappingDesc[key]}
                onChange={(e) => onMappingDescChange(entity.id, record.name, e.target.value)}
              />
            );
          }}
        ]}
        locale={{ emptyText: '该实体暂无属性，请先在资产管理中维护' }}
      />
    </Card>
  );
};

export default EntityPropertiesGrid;
