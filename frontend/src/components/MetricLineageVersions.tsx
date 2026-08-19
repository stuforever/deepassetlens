/**
 * MetricLineageVersions —— 指标血缘 + 版本快照 tab（纯展示 + 事件上抛）
 *
 * 从 MetricManager 抽离：血缘图 + 变更记录（审计日志）与版本列表（预览/回滚）。
 */
import React from 'react';
import { Card, Space, Table, Button, Typography } from 'antd';
import LineageGraph from './LineageGraph';

const { Text } = Typography;

// 指标血缘 tab
export type MetricLineageTabProps = {
  lineageData: any;
  auditLogs: any[];
};

export const MetricLineageTab: React.FC<MetricLineageTabProps> = (p) => (
  <Space direction="vertical" style={{ width: '100%' }} size={12}>
    <Card size="small" title="指标血缘图">
      {p.lineageData ? <LineageGraph mode="embed" data={p.lineageData} height={420} /> : <Text type="secondary">暂无血缘数据</Text>}
    </Card>
    <Card size="small" title="变更记录（MetricAuditLog）">
      <Table
        size="small"
        rowKey="id"
        pagination={{ pageSize: 8 }}
        dataSource={p.auditLogs}
        columns={[
          { title: 'action', dataIndex: 'action', width: 120 },
          { title: 'operator', dataIndex: 'operator', width: 160 },
          { title: 'created_at', dataIndex: 'created_at', width: 200 },
          {
            title: 'after_json',
            dataIndex: 'after_json',
            render: (v: any) => (
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 120, overflow: 'auto' }}>
                {JSON.stringify(v ?? {}, null, 2)}
              </pre>
            ),
          },
        ]}
      />
    </Card>
  </Space>
);

// 版本快照 tab
export type MetricVersionsTabProps = {
  versions: any[];
  onPreview: (v: number) => void;
  onRollback: (v: number) => void;
};

export const MetricVersionsTab: React.FC<MetricVersionsTabProps> = (p) => (
  <Card size="small" title="版本列表">
    <Table
      size="small"
      rowKey="version"
      pagination={false}
      dataSource={p.versions}
      columns={[
        { title: 'version', dataIndex: 'version', width: 100 },
        { title: 'status', dataIndex: 'status', width: 120 },
        { title: 'created_by', dataIndex: 'created_by', width: 160 },
        { title: 'created_at', dataIndex: 'created_at', width: 200 },
        {
          title: '操作',
          width: 180,
          render: (_: any, r: any) => (
            <Space>
              <Button size="small" onClick={() => p.onPreview(Number(r.version))}>预览</Button>
              <Button size="small" danger onClick={() => p.onRollback(Number(r.version))}>回滚</Button>
            </Space>
          ),
        },
      ]}
    />
    <Text type="secondary">说明：发布/提交/审核会写入版本快照，便于稽核与回滚。</Text>
  </Card>
);
