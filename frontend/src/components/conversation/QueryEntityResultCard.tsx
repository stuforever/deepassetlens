import React, { useMemo, useState } from 'react';
import { Alert, Card, Descriptions, Segmented, Space, Table, Tag, Typography } from 'antd';
import WorkflowExecutionTimeline from './WorkflowExecutionTimeline';
import { StatusTag } from '../shell';
import type { RunEventRecord } from './types';

const { Text } = Typography;

type QueryEntityCardData = {
  final_result?: any;
  result_panels?: any;
  llm_error?: any;
  normalized_query?: string;
  metadata_summary?: any;
  step_trace?: any[];
  workflow_execution_code?: string;
};

const QueryEntityResultCard: React.FC<{ data?: QueryEntityCardData; events?: RunEventRecord[] }> = ({ data, events = [] }) => {
  const [resultView, setResultView] = useState<'table' | 'json'>('table');
  const safeData = data || {};
  const finalResult = safeData.final_result || null;
  const resultPanels = safeData.result_panels || {};
  const llmError = safeData.llm_error || null;
  const stepTrace = safeData.step_trace || [];
  const isRelationMissingError = !!(finalResult?.reason && String(finalResult.reason).includes('主数据对象上未发生该业务'));
  const hasHardError = !!llmError || isRelationMissingError;
  const summary = resultPanels.summary || finalResult || null;
  const masterRows = resultPanels.master_entities || [];
  const activityRows = resultPanels.activity_entities || [];
  const relationGroups = resultPanels.relation_groups || {};
  const jsonViewPayload = {
    summary,
    master_entities: masterRows,
    activity_entities: activityRows,
    relation_groups: relationGroups,
  };

  const masterEntityColumns = useMemo(
    () => [
      { title: 'L1', dataIndex: 'l1', width: 120 },
      { title: 'L2', dataIndex: 'l2', width: 140 },
      { title: 'L2X主数据实体', dataIndex: 'l2x', width: 220 },
      {
        title: '是否主表',
        dataIndex: 'is_main_table',
        width: 100,
        render: (value: boolean) => (value ? <StatusTag preset="info">是</StatusTag> : <Tag>否</Tag>),
      },
      {
        title: '置信度',
        dataIndex: 'confidence',
        width: 100,
        render: (value: string) => <StatusTag preset={value === 'HIGH' ? 'success' : value === 'MEDIUM' ? 'info' : 'warning'}>{value}</StatusTag>,
      },
      { title: '命中依据', dataIndex: 'match_reason', width: 420 },
    ],
    []
  );

  const activityEntityColumns = useMemo(
    () => [
      { title: 'L3', dataIndex: 'l3', width: 140 },
      { title: 'L4', dataIndex: 'l4', width: 140 },
      { title: 'L4X业务活动实体', dataIndex: 'l4x', width: 220 },
      {
        title: '置信度',
        dataIndex: 'confidence',
        width: 100,
        render: (value: string) => <StatusTag preset={value === 'HIGH' ? 'success' : value === 'MEDIUM' ? 'info' : 'warning'}>{value}</StatusTag>,
      },
      { title: '命中依据', dataIndex: 'match_reason', width: 420 },
    ],
    []
  );

  const relationColumns = useMemo(
    () => [
      { title: '类别', dataIndex: 'relation_category', width: 120, render: (value: string) => value || '-' },
      { title: '关系名', dataIndex: 'relation_name', width: 220 },
      { title: '源实体', dataIndex: 'source_entity_name', width: 180 },
      { title: '目标实体', dataIndex: 'target_entity_name', width: 180 },
      { title: '方向', dataIndex: 'direction', width: 100 },
      { title: '基数', dataIndex: 'cardinality', width: 100 },
      { title: '源字段', dataIndex: 'source_field_name', width: 140 },
      { title: '目标字段', dataIndex: 'target_field_name', width: 140 },
      { title: '关联说明', dataIndex: 'join_expr', width: 300 },
      { title: '备注', dataIndex: 'remark', width: 220 },
    ],
    []
  );

  if (!data) return null;

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      {safeData.normalized_query ? <Text type="secondary">归一化问句：{safeData.normalized_query}</Text> : null}
      <WorkflowExecutionTimeline
        title="流程执行过程"
        stepTrace={stepTrace}
        events={events}
        emptyText="当前结果没有携带真实步骤轨迹"
      />
      {llmError ? <Alert type="error" showIcon message="大模型不可用" description={llmError.message || llmError.reason || '当前未找到可用真实LLM，请先配置并启用后再执行。'} /> : null}
      {isRelationMissingError ? <Alert type="error" showIcon message="关系不存在" description={finalResult?.reason || '主数据对象上未发生该业务，请建立关系后再问。'} /> : null}
      {finalResult ? (
        <Card
          size="small"
          title="结构化结果"
          extra={
            <Segmented
              size="small"
              value={resultView}
              onChange={(value) => setResultView(value as 'table' | 'json')}
              options={[
                { label: '表格视图', value: 'table' },
                { label: 'JSON视图', value: 'json' },
              ]}
            />
          }
        >
          <Descriptions size="small" bordered column={2} style={{ marginBottom: 12, border: hasHardError ? '1px solid var(--color-error-bg)' : undefined }}>
            <Descriptions.Item label="置信度">
              <StatusTag preset={summary?.confidence === 'HIGH' ? 'success' : summary?.confidence === 'MEDIUM' ? 'info' : 'warning'}>{summary?.confidence || '-'}</StatusTag>
            </Descriptions.Item>
            <Descriptions.Item label="判定依据">{summary?.reason || '-'}</Descriptions.Item>
          </Descriptions>
          {resultView === 'table' ? (
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <Card size="small" title={`定位到的主数据实体（${masterRows.length} 条）`}>
                <Table size="small" rowKey={(row: any, index) => row.id || `master-${index}`} columns={masterEntityColumns} dataSource={masterRows} pagination={false} scroll={{ x: 1200 }} locale={{ emptyText: '未定位到主数据实体' }} />
              </Card>
              <Card size="small" title={`定位到的业务活动实体（${activityRows.length} 条）`}>
                <Table size="small" rowKey={(row: any, index) => row.id || `activity-${index}`} columns={activityEntityColumns} dataSource={activityRows} pagination={false} scroll={{ x: 1200 }} locale={{ emptyText: '未定位到业务活动实体' }} />
              </Card>
              <Card size="small" title="关联关系">
                <Space direction="vertical" style={{ width: '100%' }} size={12}>
                  <Card size="small" title={`主数据实体与主数据实体（${(relationGroups.master_to_master || []).length} 条）`}>
                    <Table size="small" rowKey={(row: any, index) => row.id || `mm-${index}`} columns={relationColumns} dataSource={relationGroups.master_to_master || []} pagination={false} scroll={{ x: 1800 }} locale={{ emptyText: '暂无主数据实体间关联关系' }} />
                  </Card>
                  <Card size="small" title={`业务活动实体与业务活动实体（${(relationGroups.activity_to_activity || []).length} 条）`}>
                    <Table size="small" rowKey={(row: any, index) => row.id || `aa-${index}`} columns={relationColumns} dataSource={relationGroups.activity_to_activity || []} pagination={false} scroll={{ x: 1800 }} locale={{ emptyText: '暂无业务活动实体间关联关系' }} />
                  </Card>
                  <Card size="small" title={`主数据实体与业务活动实体（${(relationGroups.master_to_activity || []).length} 条）`}>
                    <Table size="small" rowKey={(row: any, index) => row.id || `ma-${index}`} columns={relationColumns} dataSource={relationGroups.master_to_activity || []} pagination={false} scroll={{ x: 1800 }} locale={{ emptyText: '暂无主数据与业务活动间关联关系' }} />
                  </Card>
                </Space>
              </Card>
            </Space>
          ) : (
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(jsonViewPayload, null, 2)}</pre>
          )}
        </Card>
      ) : null}
    </Space>
  );
};

export default QueryEntityResultCard;
