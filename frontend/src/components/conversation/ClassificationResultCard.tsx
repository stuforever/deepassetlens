import React from 'react';
import { Card, Empty, Space, Table, Tag, Typography } from 'antd';
import { StatusTag, type StatusPreset } from '../shell';

const { Text } = Typography;

interface ClassificationResultData {
  query_type?: 'children' | 'subtree' | 'fields' | 'relations';
  target_code?: string;
  summary?: string;
  results?: any[];
  cross_chain_relations?: any[];
}

const QUERY_TYPE_LABEL: Record<string, { label: string; preset: StatusPreset }> = {
  children: { label: '直接子分类', preset: 'info' },
  subtree: { label: '子树', preset: 'ai' },
  fields: { label: '字段列表', preset: 'success' },
  relations: { label: '跨链关系', preset: 'warning' },
};

const ClassificationResultCard: React.FC<{ data?: ClassificationResultData }> = ({ data }) => {
  if (!data) return null;

  const qt = data.query_type || 'children';
  const qtMeta = QUERY_TYPE_LABEL[qt] || { label: qt, preset: 'default' as StatusPreset };
  const results = data.results || [];

  const columns = (() => {
    if (qt === 'fields') {
      return [
        { title: '字段编码', dataIndex: 'attribute_code', key: 'attribute_code', ellipsis: true },
        { title: '字段名', dataIndex: 'attribute_name', key: 'attribute_name', ellipsis: true },
        { title: '类型', dataIndex: 'attribute_type_cn', key: 'attribute_type_cn', width: 120 },
        { title: '分类', dataIndex: 'attribute_category', key: 'attribute_category', width: 120 },
      ];
    }
    // children / subtree
    return [
      { title: '编码', dataIndex: 'code', key: 'code', ellipsis: true },
      { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
      { title: '层级', dataIndex: 'level', key: 'level', width: 80,
        render: (v: string) => <StatusTag preset="info">{v}</StatusTag> },
      ...(qt === 'subtree' ? [{ title: '深度', dataIndex: 'depth', key: 'depth', width: 80 }] : []),
      { title: '链类型', dataIndex: 'chain_type', key: 'chain_type', width: 120 },
    ];
  })();

  const dataSource = results.map((r: any, i: number) => ({ ...r, key: r.code || i }));

  return (
    <Card
      size="small"
      title={
        <Space>
          <span>分类查询结果</span>
          <StatusTag preset={qtMeta.preset}>{qtMeta.label}</StatusTag>
          {data.target_code && <Tag>{data.target_code}</Tag>}
        </Space>
      }
      extra={<Text type="secondary">{data.summary || `${results.length} 条`}</Text>}
    >
      {results.length === 0 ? (
        <Empty description="无结果" />
      ) : (
        <Table
          size="small"
          columns={columns}
          dataSource={dataSource}
          pagination={results.length > 20 ? { pageSize: 20 } : false}
          scroll={{ x: 'max-content' }}
        />
      )}

      {qt === 'relations' && data.cross_chain_relations && data.cross_chain_relations.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <Text strong>跨链关系详情：</Text>
          <Table
            size="small"
            style={{ marginTop: 8 }}
            columns={[
              { title: '源', dataIndex: 'source', key: 'source', ellipsis: true,
                render: (v: string, r: any) => `${r.source_name || ''} (${v})` },
              { title: '目标', dataIndex: 'target', key: 'target', ellipsis: true,
                render: (v: string, r: any) => `${r.target_name || ''} (${v})` },
              { title: '派生自', dataIndex: 'derived_from', key: 'derived_from', width: 120 },
            ]}
            dataSource={data.cross_chain_relations.map((r: any, i: number) => ({ ...r, key: i }))}
            pagination={false}
            scroll={{ x: 'max-content' }}
          />
        </div>
      )}
    </Card>
  );
};

export default ClassificationResultCard;
