import React, { useEffect, useState } from 'react';
import {
  Card, Descriptions, Tag, Table, Space, Empty, Spin, message, Segmented, Alert,
} from 'antd';
import { DatabaseOutlined, TableOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { mappingApi, entityRelationManagerApi } from '../services/api';
import { StatusTag } from './shell';

// === 辅助函数（从 ModelTreeManager 抽出，保持一致） ===

const LEVEL_LABELS: Record<number, string> = {
  0: '业务域', 1: 'L1', 2: 'L2', 3: 'L3', 4: 'L4',
};

const getEntityCategoryLabel = (conceptLevel?: number) => {
  if (conceptLevel === 2) return '主数据实体';
  if (conceptLevel === 4) return '业务活动实体';
  return '数据实体';
};

const getEntityCategoryPreset = (conceptLevel?: number): 'warning' | 'info' | 'default' => {
  if (conceptLevel === 2) return 'warning';
  if (conceptLevel === 4) return 'info';
  return 'default';
};

const splitExplanationTerms = (value: any): string[] => {
  const raw = String(value || '').trim();
  if (!raw) return [];
  return Array.from(
    new Set(
      raw
        .split(/[,，、/|；;\n\r\t]+/)
        .map((item) => item.trim())
        .filter(Boolean)
    )
  );
};

// === Props 类型 ===

export type EntityDetail = {
  id: string;
  entity_name: string;
  entity_code: string;
  entity_en_name?: string;
  entity_explanation?: string;
  description?: string;
  is_main_table?: boolean;
  data_layer?: string;
  sort_order?: number;
  source_mode?: string;
  integration_sql?: string;
  properties_schema?: any[];
  concept_id?: string;
  // 用于推断主数据/业务活动分类（来自 graph 节点 entity_category 或父概念 level）
  entity_category?: string; // master_entity / activity_entity / data_entity
  parentConceptLevel?: number;
};

type Props = {
  entity: EntityDetail;
  // 可选：传入父概念名（用于"所属概念分类"字段展示）
  parentConceptName?: string;
  // 是否加载数据预览（默认 true）
  showDataPreview?: boolean;
  // 是否加载实体关系（默认 true）
  showRelations?: boolean;
};

const EntityDetailCard: React.FC<Props> = ({
  entity,
  parentConceptName,
  showDataPreview = true,
  showRelations = true,
}) => {
  // 推断父概念 level（优先使用 parentConceptLevel，否则从 entity_category 推断）
  const parentLevel = entity.parentConceptLevel ?? (
    entity.entity_category === 'master_entity' ? 2 :
    entity.entity_category === 'activity_entity' ? 4 :
    undefined
  );
  const categoryLabel = getEntityCategoryLabel(parentLevel);
  const categoryPreset = getEntityCategoryPreset(parentLevel);

  // === 数据预览 ===
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [previewTable, setPreviewTable] = useState<string | null>(null);
  const [previewHint, setPreviewHint] = useState<string | null>(null);

  const loadPreview = async () => {
    if (!entity.id) return;
    setPreviewLoading(true);
    try {
      const resp = await mappingApi.previewEntityData(entity.id, 20);
      const data = resp.data?.data || {};
      setPreviewRows(data.rows || []);
      setPreviewTable(data.table_name || null);
      setPreviewHint(data.hint || null);
    } catch (e: any) {
      setPreviewRows([]);
      setPreviewHint(e?.response?.data?.detail || '预览失败');
    } finally {
      setPreviewLoading(false);
    }
  };

  // === 实体间关系 ===
  const [relLoading, setRelLoading] = useState(false);
  const [relRows, setRelRows] = useState<any[]>([]);
  const [relFilter, setRelFilter] = useState<'all' | 'manual' | 'matrix'>('all');

  const loadRelations = async () => {
    if (!entity.id) return;
    setRelLoading(true);
    try {
      const resp = await entityRelationManagerApi.listItems({ entity_id: entity.id });
      setRelRows(resp.data?.data?.items || []);
    } catch (e) {
      setRelRows([]);
    } finally {
      setRelLoading(false);
    }
  };

  useEffect(() => {
    if (showDataPreview) loadPreview();
    if (showRelations) loadRelations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entity.id, showDataPreview, showRelations]);

  const mergedRelations = [...(relRows || [])]
    .map((r: any) => ({ ...r, row_type: r.relation_category === '打点维护' ? 'matrix' : 'manual' }))
    .sort((a, b) => {
      if (a.row_type === b.row_type) return String(a.relation_name || '').localeCompare(String(b.relation_name || ''), 'zh-CN');
      return a.row_type === 'manual' ? -1 : 1;
    });

  const filteredRelations = relFilter === 'all'
    ? mergedRelations
    : mergedRelations.filter((r: any) => r.row_type === relFilter);

  // 预览表格列（动态从首行取）
  const previewColumns = previewRows.length > 0
    ? Object.keys(previewRows[0]).map((col) => ({
        title: col,
        dataIndex: col,
        ellipsis: { showTitle: false },
        render: (v: any) => v === null || v === undefined ? <span style={{ color: 'var(--text-tertiary)' }}>-</span> : String(v),
      }))
    : [];

  return (
    <div>
      {/* === 顶部：数据预览 === */}
      {showDataPreview && (
        <Card
          size="small"
          title={
            <Space>
              <TableOutlined />
              <span>数据预览</span>
              {previewTable && <StatusTag preset="info">{previewTable}</StatusTag>}
            </Space>
          }
          extra={<Tag>{previewRows.length} 行</Tag>}
          style={{ marginBottom: 16, borderRadius: 12 }}
        >
          <Spin spinning={previewLoading}>
            {previewHint ? (
              <Alert
                type="info"
                showIcon
                icon={<InfoCircleOutlined />}
                message={previewHint}
              />
            ) : previewRows.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
            ) : (
              <Table
                size="small"
                rowKey={(_, i) => String(i)}
                dataSource={previewRows}
                columns={previewColumns}
                pagination={previewRows.length > 10 ? { pageSize: 10, size: 'small' } : false}
                scroll={{ x: 'max-content' }}
              />
            )}
          </Spin>
        </Card>
      )}

      {/* === 实体基本信息 === */}
      <Card
        size="small"
        title={
          <Space>
            <DatabaseOutlined />
            <span>{categoryLabel}基本信息</span>
          </Space>
        }
        style={{ marginBottom: 16, borderRadius: 12 }}
      >
        <Descriptions column={2} size="small" bordered>
          <Descriptions.Item label={`${categoryLabel}名称`}>{entity.entity_name}</Descriptions.Item>
          <Descriptions.Item label={`${categoryLabel}编码`}>{entity.entity_code}</Descriptions.Item>
          <Descriptions.Item label="落地英文表名">{entity.entity_en_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="所属概念分类">
            {parentConceptName || '-'} {parentLevel !== undefined && <Tag>{LEVEL_LABELS[parentLevel]}</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="数据实体类别">
            <StatusTag preset={categoryPreset}>{categoryLabel}</StatusTag>
          </Descriptions.Item>
          <Descriptions.Item label="是否主表">{entity.is_main_table ? '是' : '否'}</Descriptions.Item>
          <Descriptions.Item label="数据来源模式">
            {entity.source_mode === 'sql_integration' ? (
              <StatusTag preset="info">多源SQL整合(Doris)</StatusTag>
            ) : entity.source_mode === 'api_integration' ? (
              <StatusTag preset="ai">多源API整合(n8n)</StatusTag>
            ) : (
              <StatusTag preset="info">物理数据表</StatusTag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="数据层级">{entity.data_layer || '-'}</Descriptions.Item>
          <Descriptions.Item label="显示顺序">{entity.sort_order ?? 0}</Descriptions.Item>
          <Descriptions.Item label="属性数量">{(entity.properties_schema || []).length}</Descriptions.Item>
          <Descriptions.Item label="解释（别名同义词）" span={2}>
            {splitExplanationTerms(entity.entity_explanation).length ? (
              <Space size={[4, 4]} wrap>
                {splitExplanationTerms(entity.entity_explanation).map((item) => (
                  <StatusTag key={item} preset="ai">{item}</StatusTag>
                ))}
              </Space>
            ) : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="说明" span={2}>{entity.description || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* === 属性区域 === */}
      <Card
        size="small"
        title="属性区域"
        style={{ marginBottom: 16, borderRadius: 12 }}
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
            { title: '主键', dataIndex: 'isPrimaryKey', width: 90, render: (v: boolean) => (v ? <StatusTag preset="error">是</StatusTag> : '否') },
            {
              title: '参与问实体识别',
              dataIndex: 'enable_query_entity',
              width: 130,
              render: (v: boolean) => (v ? <StatusTag preset="success">是</StatusTag> : <Tag>否</Tag>),
            },
            { title: '说明', dataIndex: 'description' },
          ]}
        />
      </Card>

      {/* === 数据实体间关系 === */}
      {showRelations && (
        <Card
          size="small"
          title="数据实体间关系查询"
          style={{ borderRadius: 12 }}
          extra={
            <Space size={8}>
              <StatusTag preset="info">手工维护 {mergedRelations.filter((r: any) => r.row_type === 'manual').length}</StatusTag>
              <StatusTag preset="ai">打点维护 {mergedRelations.filter((r: any) => r.row_type === 'matrix').length}</StatusTag>
              <Segmented
                size="small"
                value={relFilter}
                onChange={(v) => setRelFilter(v as 'all' | 'manual' | 'matrix')}
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
            loading={relLoading}
            dataSource={filteredRelations}
            locale={{ emptyText: '暂无数据实体关系' }}
            onRow={(record: any) => ({
              style: record.row_type === 'matrix' ? { background: 'var(--color-ai-bg)' } : { background: 'var(--color-success-bg)' },
            })}
            columns={[
              {
                title: '关系分组',
                dataIndex: 'relation_group_label',
                width: 140,
                render: (v: string) => <StatusTag preset="info">{v}</StatusTag>,
              },
              {
                title: '类别',
                dataIndex: 'relation_category',
                width: 110,
                render: (v: string) => <StatusTag preset={v === '打点维护' ? 'ai' : 'info'}>{v || '手工维护'}</StatusTag>,
              },
              {
                title: '关系名',
                dataIndex: 'relation_name',
                width: 280,
                render: (v: string, row: any) => (
                  <span style={{ fontWeight: 500, color: row.row_type === 'matrix' ? '#531dab' : 'var(--color-primary-hover)' }}>{v}</span>
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
      )}
    </div>
  );
};

export default EntityDetailCard;
