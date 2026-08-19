/**
 * ModelDetailPanel —— 模型树右侧详情面板（纯展示 + 事件上抛）
 *
 * 从 ModelTreeManager 抽离：概念/实体/属性三态详情 + 空态。
 * 不持有任何状态；数据与回调全部经 props 传入（容器 = ModelTreeManager）。
 */
import React from 'react';
import {
  Card, Descriptions, Space, Button, Popconfirm, Typography, Badge, List, Table,
  Segmented, Empty, Radio, Select, Tooltip, Tag,
} from 'antd';
import {
  PlusOutlined, DatabaseOutlined, EditOutlined, DeleteOutlined, LinkOutlined, EyeOutlined,
} from '@ant-design/icons';
import { StatusTag } from '../shell';
import { LEVEL_LABELS, getEntityCategoryLabel, getEntityCategoryPreset, splitExplanationTerms } from './modelTree';

const { Text } = Typography;

export type ModelDetailPanelProps = {
  selectedMeta: any;
  config: any; // MODE_CONFIG[mode]
  readOnly: boolean;

  // 实体详情：数据来源配置
  dataSources: any[];
  sourceMode: string;
  savingSourceMode: boolean;
  savingDataSource: boolean;
  previewLoading: boolean;

  // 实体详情：关系查询
  loadingDetail: boolean;
  relationFilter: 'all' | 'manual' | 'matrix';
  mergedRelations: any[];
  filteredRelations: any[];
  relationHighlight: any;

  // 事件（由容器实现，保持行为不变）
  onSetSelectedKey: (key: string | null) => void;
  onOpenCreateChildConcept: () => void;
  onOpenCreateEntity: (concept?: any) => void;
  onOpenEditConcept: () => void;
  onOpenEditEntity: (entity: any, parentConcept?: any) => void;
  onDeleteConcept: () => void;
  onDeleteEntity: (id: string) => void;
  onOpenCreateProperty: (entity?: any) => void;
  onOpenEditProperty: () => void;
  onDeleteProperty: () => void;
  onConfigMapping: () => void;
  onDataPreview: () => void;
  onSourceModeChange: (value: string) => void;
  onDataSourceChange: (value: string | undefined) => void;
  onRelationFilterChange: (value: 'all' | 'manual' | 'matrix') => void;
};

const renderConceptDetail = (p: ModelDetailPanelProps) => {
  const { selectedMeta, config, readOnly } = p;
  const concept = selectedMeta.concept;
  const canAddChild = !!config.childLevelMap[concept.level];
  return (
    <>
      <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="概念分类名称">{concept.name}</Descriptions.Item>
          <Descriptions.Item label="层级">
            <StatusTag preset="info">{LEVEL_LABELS[concept.level] || `L${concept.level}`}</StatusTag>
          </Descriptions.Item>
          <Descriptions.Item label="显示顺序">{concept.sort_order ?? 0}</Descriptions.Item>
          {concept.level === 3 ? (
            <Descriptions.Item label="所属系统">
              {concept.system_names?.length ? (
                <Space size={[4, 4]} wrap>
                  {concept.system_names.map((item: string) => (
                    <StatusTag key={item} preset="ai">
                      {item}
                    </StatusTag>
                  ))}
                </Space>
              ) : (
                '-'
              )}
            </Descriptions.Item>
          ) : null}
          <Descriptions.Item label="说明">{concept.description || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        size="small"
        title="概念分类维护"
        style={{ marginBottom: 16, borderRadius: 12 }}
        extra={<Badge color={concept.level === config.leafLevel ? 'var(--color-warning)' : 'var(--color-primary)'} text={readOnly ? '只读查看' : concept.level === config.leafLevel ? '可维护数据实体' : '可维护概念分类'} />}
      >
        {readOnly ? (
          <Text type="secondary">当前为只读查看模式，概念分类和数据实体维护请在后台建模页处理。</Text>
        ) : (
          <Space wrap>
            {canAddChild ? (
              <Button type="dashed" icon={<PlusOutlined />} onClick={p.onOpenCreateChildConcept}>
                新增下级概念分类
              </Button>
            ) : null}
            {concept.level === config.leafLevel ? (
              <Button type="dashed" icon={<DatabaseOutlined />} onClick={() => p.onOpenCreateEntity(concept)}>
                新增{getEntityCategoryLabel(concept.level)}
              </Button>
            ) : null}
            <Button icon={<EditOutlined />} onClick={p.onOpenEditConcept}>
              编辑概念分类
            </Button>
            <Popconfirm title="确认删除当前概念分类？" onConfirm={p.onDeleteConcept}>
              <Button danger icon={<DeleteOutlined />}>
                删除概念分类
              </Button>
            </Popconfirm>
          </Space>
        )}
      </Card>

      {concept.level === config.leafLevel ? (
        <Card
          size="small"
          title={`下属${getEntityCategoryLabel(concept.level)}`}
          style={{ borderRadius: 12 }}
          extra={<StatusTag preset={getEntityCategoryPreset(concept.level)}>共 {(concept.entities || []).length} 个{getEntityCategoryLabel(concept.level)}</StatusTag>}
        >
          {(concept.entities || []).length > 0 ? (
            <List
              size="small"
              bordered
              dataSource={[...(concept.entities || [])].sort((a: any, b: any) => {
                const orderDiff = (a.sort_order || 0) - (b.sort_order || 0);
                if (orderDiff !== 0) return orderDiff;
                return String(a.entity_name || '').localeCompare(String(b.entity_name || ''), 'zh-CN');
              })}
              renderItem={(item: any) => (
                <List.Item
                  actions={[
                    <Button key="locate" type="link" size="small" onClick={() => p.onSetSelectedKey(`entity-${item.id}`)}>
                      定位
                    </Button>,
                    ...(!readOnly ? [
                      <Button key="edit" type="link" size="small" onClick={() => p.onOpenEditEntity(item, concept)}>
                        编辑
                      </Button>,
                      <Popconfirm key="delete" title={`确认删除该${getEntityCategoryLabel(concept.level)}？`} onConfirm={() => p.onDeleteEntity(item.id)}>
                        <Button type="link" size="small" danger>
                          删除
                        </Button>
                      </Popconfirm>,
                    ] : []),
                  ]}
                >
                  <Space>
                    <DatabaseOutlined style={{ color: concept.level === 4 ? '#13c2c2' : 'var(--color-warning)' }} />
                    <span>{item.entity_name}</span>
                    <Text type="secondary">{item.entity_code}</Text>
                    <StatusTag preset={getEntityCategoryPreset(concept.level)}>{getEntityCategoryLabel(concept.level)}</StatusTag>
                    <StatusTag preset="default">顺序 {item.sort_order ?? 0}</StatusTag>
                    {item.is_main_table ? <StatusTag preset="info">主表</StatusTag> : null}
                    <Tag>{(item.properties_schema || []).length} 个属性</Tag>
                    {splitExplanationTerms(item.entity_explanation).length ? <StatusTag preset="ai">{splitExplanationTerms(item.entity_explanation).length} 个同义词</StatusTag> : null}
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`暂无${getEntityCategoryLabel(concept.level)}`} />
          )}
        </Card>
      ) : null}
    </>
  );
};

const renderEntityDetail = (p: ModelDetailPanelProps) => {
  const { selectedMeta, readOnly } = p;
  const entity = selectedMeta.entity;
  return (
    <>
      {!readOnly ? (
        <Card size="small" title={`删除${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}`} style={{ marginBottom: 16, borderRadius: 12 }}>
          <Popconfirm title={`确认删除该${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}？`} onConfirm={() => p.onDeleteEntity(entity.id)}>
            <Button danger icon={<DeleteOutlined />}>
              删除{getEntityCategoryLabel(selectedMeta.parentConcept?.level)}
            </Button>
          </Popconfirm>
        </Card>
      ) : null}

      <Card
        size="small"
        title={`${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}基本信息`}
        style={{ marginBottom: 16, borderRadius: 12 }}
        extra={
          !readOnly ? (
            <Button icon={<EditOutlined />} onClick={() => p.onOpenEditEntity(entity, selectedMeta.parentConcept)}>
              维护{getEntityCategoryLabel(selectedMeta.parentConcept?.level)}
            </Button>
          ) : null
        }
      >
        <Descriptions column={2} size="small" bordered>
          <Descriptions.Item label={`${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}名称`}>{entity.entity_name}</Descriptions.Item>
          <Descriptions.Item label={`${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}编码`}>{entity.entity_code}</Descriptions.Item>
          <Descriptions.Item label="落地英文表名">{entity.entity_en_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="所属概念分类">
            {selectedMeta.parentConcept?.name || '-'} {selectedMeta.parentConcept ? <Tag>{LEVEL_LABELS[selectedMeta.parentConcept.level]}</Tag> : null}
          </Descriptions.Item>
          <Descriptions.Item label="数据实体类别">
            <StatusTag preset={getEntityCategoryPreset(selectedMeta.parentConcept?.level)}>{getEntityCategoryLabel(selectedMeta.parentConcept?.level)}</StatusTag>
          </Descriptions.Item>
          <Descriptions.Item label="是否主表">{entity.is_main_table ? '是' : '否'}</Descriptions.Item>
          <Descriptions.Item label="数据层级">{entity.data_layer || '-'}</Descriptions.Item>
          <Descriptions.Item label="显示顺序">{entity.sort_order ?? 0}</Descriptions.Item>
          <Descriptions.Item label="属性数量">{(entity.properties_schema || []).length}</Descriptions.Item>
          <Descriptions.Item label="解释（别名同义词）" span={2}>
            {splitExplanationTerms(entity.entity_explanation).length ? (
              <Space size={[4, 4]} wrap>
                {splitExplanationTerms(entity.entity_explanation).map((item) => (
                  <StatusTag key={item} preset="ai">
                    {item}
                  </StatusTag>
                ))}
              </Space>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="说明" span={2}>{entity.description || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card size="small" title="数据来源配置" style={{ marginBottom: 16, borderRadius: 12 }} extra={
        <Space>
          <Button size="small" type="primary" ghost icon={<LinkOutlined />} onClick={p.onConfigMapping}>
            配置映射
          </Button>
          <Button size="small" icon={<EyeOutlined />} loading={p.previewLoading} onClick={p.onDataPreview}>
            数据预览
          </Button>
        </Space>
      }>
        <Radio.Group
          value={p.sourceMode}
          onChange={(e) => p.onSourceModeChange(e.target.value)}
          disabled={p.savingSourceMode}
        >
          <Tooltip title="实体直接读取物理表数据（PostgreSQL），在「落地实体表映射」中配置字段映射">
            <Radio value="physical_table">物理数据表</Radio>
          </Tooltip>
          <Tooltip title="通过 Doris 执行整合 SQL 获取数据，可跨源整合">
            <Radio value="sql_integration">多源SQL整合(Doris)</Radio>
          </Tooltip>
          <Tooltip title="通过 DuckDB 联邦查询整合 API 数据，配置端点与伪逻辑 SQL">
            <Radio value="api_integration">多源API整合(DuckDB)</Radio>
          </Tooltip>
        </Radio.Group>
        {p.sourceMode === 'physical_table' && (
          <div style={{ marginTop: 10 }}>
            <span style={{ marginRight: 8, color: 'var(--text-secondary)' }}>数据源绑定：</span>
            <Select
              style={{ width: 300 }}
              placeholder="默认（全局数据源）"
              allowClear
              loading={p.savingDataSource}
              value={(selectedMeta?.entity as any)?.data_source_id || undefined}
              onChange={(v) => p.onDataSourceChange(v)}
              options={p.dataSources.map((ds: any) => ({
                label: `${ds.name}（${ds.host}:${ds.port}/${ds.database}）`,
                value: ds.id,
              }))}
            />
            <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-tertiary)' }}>
              不同实体绑不同数据源时，跨源查询自动走 Doris 联邦
            </span>
          </div>
        )}
      </Card>

      <Card
        size="small"
        title="属性区域"
        style={{ marginBottom: 16, borderRadius: 12 }}
        extra={
          !readOnly ? (
            <Button type="dashed" icon={<PlusOutlined />} onClick={() => p.onOpenCreateProperty(entity)}>
              属性维护
            </Button>
          ) : null
        }
      >
        <Table
          size="small"
          scroll={{ y: 240 }}
          pagination={{ pageSize: 5, showSizeChanger: true, size: 'small' }}
          rowKey={(row: any, idx?: number) => `${row.name}-${idx ?? 0}`}
          dataSource={entity.properties_schema || []}
          locale={{ emptyText: '暂无属性' }}
          columns={[
            { title: '属性英文名', dataIndex: 'name', width: 180 },
            { title: '属性中文名', dataIndex: 'cnName', width: 180 },
            { title: '类型', dataIndex: 'type', width: 100 },
            { title: '主键', dataIndex: 'isPrimaryKey', width: 90, render: (val: boolean) => (val ? <StatusTag preset="error">是</StatusTag> : '否') },
            {
              title: '参与问实体识别',
              dataIndex: 'enable_query_entity',
              width: 130,
              render: (val: boolean) => (val ? <StatusTag preset="success">是</StatusTag> : <Tag>否</Tag>)
            },
            { title: '说明', dataIndex: 'description' },
            {
              title: '操作',
              width: readOnly ? 80 : 140,
              render: (_: any, row: any, index: number) => (
                <Space size="small">
                  <Button type="link" size="small" onClick={() => p.onSetSelectedKey(`property-${entity.id}-${index}`)}>
                    查看
                  </Button>
                  {!readOnly ? (
                    <Button
                      type="link"
                      size="small"
                      onClick={() => {
                        p.onSetSelectedKey(`property-${entity.id}-${index}`);
                        setTimeout(() => p.onOpenEditProperty(), 0);
                      }}
                    >
                      编辑
                    </Button>
                  ) : null}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Card
        size="small"
        title="数据实体间关系查询"
        style={{ borderRadius: 12 }}
        extra={
          <Space size={8}>
            <StatusTag preset="info">手工维护 {p.mergedRelations.filter((item: any) => item.row_type === 'manual').length}</StatusTag>
            <StatusTag preset="ai">打点维护 {p.mergedRelations.filter((item: any) => item.row_type === 'matrix').length}</StatusTag>
            <Segmented
              size="small"
              value={p.relationFilter}
              onChange={(value) => p.onRelationFilterChange(value as 'all' | 'manual' | 'matrix')}
              options={[
                { label: '全部', value: 'all' },
                { label: '手工维护', value: 'manual' },
                { label: '打点维护', value: 'matrix' },
              ]}
            />
          </Space>
        }
      >
        <Table
          size="small"
          pagination={false}
          rowKey="id"
          loading={p.loadingDetail}
          dataSource={p.filteredRelations}
          locale={{ emptyText: '暂无数据实体关系' }}
          onRow={(record: any) => ({
            style: record.id === p.relationHighlight?.linkId
              ? { background: 'var(--color-warning-bg)', boxShadow: 'inset 3px 0 0 var(--color-warning)' }
              : record.row_type === 'matrix'
                ? { background: 'var(--color-ai-bg)' }
                : { background: 'var(--color-success-bg)' },
          })}
          columns={[
            {
              title: '关系分组',
              dataIndex: 'relation_group_label',
              width: 140,
              render: (value: string) => <StatusTag preset="info">{value}</StatusTag>,
            },
            {
              title: '类别',
              dataIndex: 'relation_category',
              width: 110,
              render: (value: string) => (
                <StatusTag preset={value === '打点维护' ? 'ai' : 'info'}>{value || '手工维护'}</StatusTag>
              ),
            },
            {
              title: '关系名',
              dataIndex: 'relation_name',
              width: 280,
              render: (value: string, row: any) => (
                <span style={{ fontWeight: row.id === p.relationHighlight?.linkId ? 700 : 500, color: row.row_type === 'matrix' ? '#531dab' : 'var(--color-primary-hover)' }}>
                  {value}
                </span>
              ),
            },
            { title: '源数据实体', dataIndex: 'source_entity_name', width: 180 },
            { title: '目标数据实体', dataIndex: 'target_entity_name', width: 180 },
            { title: '方向', dataIndex: 'direction', width: 100 },
            { title: '基数', dataIndex: 'cardinality', width: 100 },
            { title: '源字段', dataIndex: 'source_field_name', width: 140 },
            { title: '目标字段', dataIndex: 'target_field_name', width: 140 },
            { title: '关联说明', dataIndex: 'join_expr' },
            { title: '备注', dataIndex: 'remark', width: 220 },
          ]}
        />
      </Card>
    </>
  );
};

const renderPropertyDetail = (p: ModelDetailPanelProps) => {
  const { selectedMeta, readOnly } = p;
  const prop = selectedMeta.property;
  return (
    <>
      <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
        <Descriptions column={2} size="small" bordered>
          <Descriptions.Item label="所属数据实体">{selectedMeta.entity?.entity_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="属性英文名">{prop.name || '-'}</Descriptions.Item>
          <Descriptions.Item label="属性中文名">{prop.cnName || '-'}</Descriptions.Item>
          <Descriptions.Item label="类型">{prop.type || '-'}</Descriptions.Item>
          <Descriptions.Item label="是否主键">{prop.isPrimaryKey ? '是' : '否'}</Descriptions.Item>
          <Descriptions.Item label="参与问实体识别">{prop.enable_query_entity ? '是' : '否'}</Descriptions.Item>
          <Descriptions.Item label="说明">{prop.description || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card size="small" title="属性维护" style={{ borderRadius: 12 }}>
        <Space wrap>
          {!readOnly ? (
            <Button icon={<EditOutlined />} onClick={p.onOpenEditProperty}>
              编辑属性
            </Button>
          ) : null}
          {!readOnly ? (
            <Popconfirm title="确认删除当前属性？" onConfirm={p.onDeleteProperty}>
              <Button danger icon={<DeleteOutlined />}>
                删除属性
              </Button>
            </Popconfirm>
          ) : null}
          <Button type="dashed" onClick={() => p.onSetSelectedKey(`entity-${selectedMeta.entity.id}`)}>
            返回数据实体
          </Button>
        </Space>
      </Card>
    </>
  );
};

const ModelDetailPanel: React.FC<ModelDetailPanelProps> = (props) => {
  const { selectedMeta } = props;
  if (!selectedMeta) {
    return <Empty description="请从左侧树中选择一个节点" />;
  }
  if (selectedMeta.nodeType === 'concept') return renderConceptDetail(props);
  if (selectedMeta.nodeType === 'entity') return renderEntityDetail(props);
  if (selectedMeta.nodeType === 'property') return renderPropertyDetail(props);
  return <Empty description="暂无详情" />;
};

export default ModelDetailPanel;
