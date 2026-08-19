/**
 * MappingRuleModalContent —— 新建/修改/查看映射规则弹窗主体（纯展示 + 事件上抛）
 *
 * 从 MappingManager 抽离：规则名称/来源表/实体选择头部 + 已选来源字段目录 +
 * 目标实体映射配置（复用 EntityPropertiesGrid）+ 自定义 SQL。
 * readOnly 分支在组件内解析 view* 数据（与容器行为一致）。
 */
import React from 'react';
import { Layout, Input, TreeSelect, Row, Col, Empty, Card, Space, Collapse, Button, Table, Upload, Divider, Typography } from 'antd';
import { DatabaseOutlined, AppstoreOutlined, UploadOutlined, ThunderboltOutlined, CodeOutlined } from '@ant-design/icons';
import { StatusTag } from './shell';
import { TERMS } from '../constants/standardTerms';
import EntityPropertiesGrid from './EntityPropertiesGrid';

const { Content } = Layout;
const { Text } = Typography;
const { TextArea } = Input;

export type MappingRuleModalContentProps = {
  readOnly: boolean;
  ruleName: string;
  viewingRuleName: string;
  onRuleNameChange: (v: string) => void;
  sourceTableIds: string[];
  viewSourceTableIds: string[];
  entityIds: string[];
  viewEntityIds: string[];
  selectedSourceTables: any[];
  viewSelectedSourceTables: any[];
  selectedEntities: any[];
  viewSelectedEntities: any[];
  mainSourceTableId: string;
  viewMainSourceTableId: string;
  sqlContent: string;
  viewSqlContent: string;
  pkOverrides: Record<string, boolean>;
  viewPkOverrides: Record<string, boolean>;
  fieldMappings: Record<string, string[]>;
  viewFieldMappings: Record<string, string[]>;
  mappingDesc: Record<string, string>;
  viewMappingDesc: Record<string, string>;
  rowSourceTableFilter: Record<string, string>;
  sourceTreeData: any[];
  entityTreeData: any[];
  sourceTableFields: Record<string, any[]>;
  parseMappingValue: (mv: string) => { tableId: string; fieldEn: string };
  onSourceTableChange: (vals: string[]) => void;
  onEntityIdsChange: (v: any) => void;
  onMainSourceTableChange: (tableId: string) => void;
  onSqlChange: (v: string) => void;
  onImportCsv: (file: File) => void;
  onAutoMatch: () => void;
  onGenerateSql: () => void;
  onPkChange: (entityId: string, propName: string, checked: boolean) => void;
  onRowSourceTableChange: (entityId: string, propName: string, tableId: string) => void;
  onMappingDescChange: (entityId: string, propName: string, desc: string) => void;
  onOpenFieldPicker: (entity: any, record: any) => void;
};

const MappingRuleModalContent: React.FC<MappingRuleModalContentProps> = (p) => {
  const modalSourceIds = p.readOnly ? p.viewSourceTableIds : p.sourceTableIds;
  const modalEntityIds = p.readOnly ? p.viewEntityIds : p.entityIds;
  const modalSelectedSourceTables = p.readOnly ? p.viewSelectedSourceTables : p.selectedSourceTables;
  const modalSelectedEntities = p.readOnly ? p.viewSelectedEntities : p.selectedEntities;
  const modalMainSourceTableId = p.readOnly ? p.viewMainSourceTableId : p.mainSourceTableId;
  const modalSql = p.readOnly ? p.viewSqlContent : p.sqlContent;

  return (
    <Layout style={{ height: '70vh', background: 'var(--bg-content)' }}>
      <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--color-border)', background: 'var(--bg-subtle)' }}>
        <Row gutter={12} align="middle">
          <Col span={8}>
            <Text strong style={{ marginRight: 8 }}>规则名称：</Text>
            <Input
              placeholder="请输入映射规则名称"
              value={p.readOnly ? p.viewingRuleName : p.ruleName}
              onChange={(e) => p.onRuleNameChange(e.target.value)}
              disabled={p.readOnly}
            />
          </Col>
          <Col span={8}>
            <Text strong style={{ marginRight: 8 }}>选择{TERMS.sourceTableCatalog}：</Text>
            <TreeSelect
              style={{ width: '100%' }}
              treeData={p.sourceTreeData}
              value={modalSourceIds}
              onChange={p.onSourceTableChange}
              treeCheckable
              showCheckedStrategy={TreeSelect.SHOW_CHILD}
              placeholder={`请选择${TERMS.sourceTableCatalog}`}
              allowClear
              showSearch
              disabled={p.readOnly}
              treeNodeFilterProp="title"
              maxTagCount={3}
            />
          </Col>
          <Col span={8}>
            <Text strong style={{ marginRight: 8 }}>选择图谱实体：</Text>
            <TreeSelect
              style={{ width: '100%' }}
              treeData={p.entityTreeData}
              value={modalEntityIds[0] || undefined}
              onChange={p.onEntityIdsChange}
              placeholder="请选择图谱实体"
              allowClear
              showSearch
              disabled={p.readOnly}
              treeNodeFilterProp="title"
              maxTagCount={3}
            />
          </Col>
        </Row>
      </div>
      <Content style={{ padding: '24px', overflowY: 'auto' }}>
        {modalSourceIds.length === 0 || modalEntityIds.length === 0 ? (
          <div style={{ textAlign: 'center', marginTop: 100 }}>
            <Empty description={`请先选择至少一个${TERMS.sourceTableCatalog}和图谱实体`} />
          </div>
        ) : (
          <div>
            <Card
              size="small"
              title={<Space><DatabaseOutlined />已选来源字段目录</Space>}
              type="inner"
              style={{ marginBottom: 16 }}
            >
              <Collapse ghost>
                {modalSelectedSourceTables.map(t => (
                  <Collapse.Panel
                    key={t.id}
                    header={
                      <Space>
                        <StatusTag preset="info">{t.enName}</StatusTag>
                        <Text type="secondary">{t.cnName}</Text>
                        {String(modalMainSourceTableId) === String(t.id) ? <StatusTag preset="error">主表</StatusTag> : null}
                        {!p.readOnly ? (
                          <Button
                            size="small"
                            type={String(modalMainSourceTableId) === String(t.id) ? 'primary' : 'default'}
                            onClick={(e) => {
                              e.stopPropagation();
                              p.onMainSourceTableChange(String(modalMainSourceTableId) === String(t.id) ? '' : String(t.id));
                            }}
                          >
                            {String(modalMainSourceTableId) === String(t.id) ? '取消主表' : '设为主表'}
                          </Button>
                        ) : null}
                      </Space>
                    }
                  >
                    <Table
                      size="small"
                      pagination={{ pageSize: 5 }}
                      rowKey="field_en"
                      dataSource={p.sourceTableFields[t.id] || []}
                      columns={[
                        { title: '列英文名', dataIndex: 'field_en', key: 'field_en', render: text => <Text code>{text}</Text> },
                        { title: '列中文名', dataIndex: 'field_cn', key: 'field_cn', render: text => <Text type="secondary" style={{ fontSize: 12 }}>{text}</Text> },
                      ]}
                      locale={{ emptyText: '该表暂未导入字段' }}
                    />
                  </Collapse.Panel>
                ))}
              </Collapse>
            </Card>

            <Card
              size="small"
              title={<Space><AppstoreOutlined />目标实体映射配置</Space>}
              type="inner"
              extra={
                !p.readOnly ? (
                  <Space>
                    <Upload beforeUpload={p.onImportCsv} showUploadList={false} accept=".csv">
                      <Button icon={<UploadOutlined />}>导入映射</Button>
                    </Upload>
                    <Button type="dashed" icon={<ThunderboltOutlined />} onClick={p.onAutoMatch}>智能自动匹配</Button>
                    <Button type="dashed" icon={<CodeOutlined />} onClick={p.onGenerateSql}>生成SQL</Button>
                  </Space>
                ) : null
              }
            >
              <div style={{ maxHeight: '40vh', overflowY: 'auto', marginBottom: 16 }}>
                {modalSelectedEntities.map((entity) => (
                  <EntityPropertiesGrid
                    key={entity.id}
                    entity={entity}
                    readOnly={p.readOnly}
                    pkOverrides={p.readOnly ? p.viewPkOverrides : p.pkOverrides}
                    rowSourceTableFilter={p.readOnly ? {} : p.rowSourceTableFilter}
                    fieldMappings={p.readOnly ? p.viewFieldMappings : p.fieldMappings}
                    mappingDesc={p.readOnly ? p.viewMappingDesc : p.mappingDesc}
                    selectedSourceTables={p.readOnly ? p.viewSelectedSourceTables : p.selectedSourceTables}
                    parseMappingValue={p.parseMappingValue}
                    onPkChange={p.onPkChange}
                    onRowSourceTableChange={p.onRowSourceTableChange}
                    onMappingDescChange={p.onMappingDescChange}
                    onOpenFieldPicker={p.onOpenFieldPicker}
                  />
                ))}
              </div>

              <Divider orientation="left">自定义 SQL</Divider>
              <TextArea
                rows={6}
                readOnly={p.readOnly}
                style={{ fontFamily: 'monospace', background: '#1e1e1e', color: '#d4d4d4' }}
                placeholder={`SELECT \n  A.ID AS id,\n  B.NAME AS customer_name\nFROM ${modalSelectedSourceTables[0]?.enName} A \nJOIN ... B ON A.ID = B.ID`}
                value={modalSql}
                onChange={e => p.onSqlChange(e.target.value)}
              />
            </Card>
          </div>
        )}
      </Content>
    </Layout>
  );
};

export default MappingRuleModalContent;
