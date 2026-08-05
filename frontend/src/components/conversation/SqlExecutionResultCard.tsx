import React, { useMemo } from 'react';
import { Alert, Button, Card, Space, Table, Typography, message } from 'antd';
import { CopyOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { StatusTag } from '../shell';

const { Text } = Typography;

interface SqlExecutionResultData {
  sql?: string;
  rows?: any[][];
  columns?: string[];
  row_count?: number;
  took_ms?: number;
  error?: string;
  truncated?: boolean;
}

const SqlExecutionResultCard: React.FC<{
  data?: SqlExecutionResultData;
  onReExecute?: () => void;
}> = ({ data, onReExecute }) => {
  const columns = useMemo(() => {
    if (!data) return [];
    const cols = data.columns || (data.rows && data.rows[0] ? data.rows[0].map((_: any, i: number) => `col_${i}`) : []);
    return cols.map((c: string, i: number) => ({
      title: c,
      dataIndex: `col_${i}`,
      key: `col_${i}`,
      ellipsis: true,
      render: (v: any) => (v === null || v === undefined ? <Text type="secondary">NULL</Text> : String(v)),
    }));
  }, [data]);

  const dataSource = useMemo(() => {
    if (!data) return [];
    const rows = data.rows || [];
    const startIdx = data.columns ? 0 : 1;
    return rows.slice(startIdx).map((row: any[], i: number) => {
      const obj: any = { key: i };
      row.forEach((v: any, j: number) => { obj[`col_${j}`] = v; });
      return obj;
    });
  }, [data]);

  if (!data) return null;

  if (data.error) {
    return (
      <Card size="small" title="SQL 执行结果" extra={<StatusTag preset="error">失败</StatusTag>}>
        <Alert type="error" showIcon message="执行失败" description={data.error} />
        {data.sql && (
          <pre style={{ marginTop: 12, background: 'var(--bg-hover)', padding: 12, borderRadius: 4, fontSize: 12 }}>
            {data.sql}
          </pre>
        )}
        {onReExecute && (
          <Button icon={<ReloadOutlined />} onClick={onReExecute} style={{ marginTop: 12 }}>
            重新执行
          </Button>
        )}
      </Card>
    );
  }

  const handleCopy = () => {
    if (!data.sql) return;
    navigator.clipboard.writeText(data.sql).then(() => message.success('SQL 已复制'));
  };

  const handleExportCsv = () => {
    const rows = data.rows || [];
    if (rows.length === 0) { message.warning('无数据可导出'); return; }
    const cols = data.columns || rows[0].map((_: any, i: number) => `col_${i}`);
    const csv = [
      cols.join(','),
      ...rows.slice(data.columns ? 0 : 1).map(r => r.map((v: any) => {
        if (v === null || v === undefined) return '';
        const s = String(v);
        return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
      }).join(',')),
    ].join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sql_result_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('CSV 已下载');
  };

  return (
    <Card
      size="small"
      title="SQL 执行结果"
      extra={
        <Space size="small">
          <StatusTag preset={data.row_count && data.row_count > 0 ? 'success' : 'default'}>
            {data.row_count ?? dataSource.length} 行
          </StatusTag>
          {data.took_ms && <StatusTag preset="info">{data.took_ms} ms</StatusTag>}
          {data.truncated && <StatusTag preset="warning">已截断</StatusTag>}
        </Space>
      }
    >
      {data.sql && (
        <Space direction="vertical" style={{ width: '100%', marginBottom: 12 }}>
          <Space>
            <Button size="small" icon={<CopyOutlined />} onClick={handleCopy}>复制 SQL</Button>
            <Button size="small" icon={<DownloadOutlined />} onClick={handleExportCsv}>导出 CSV</Button>
            {onReExecute && <Button size="small" icon={<ReloadOutlined />} onClick={onReExecute}>重跑</Button>}
          </Space>
          <pre style={{ margin: 0, background: 'var(--bg-hover)', padding: 8, borderRadius: 4, fontSize: 12, maxHeight: 120, overflow: 'auto' }}>
            {data.sql}
          </pre>
        </Space>
      )}
      <Table
        size="small"
        columns={columns}
        dataSource={dataSource}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 行` }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: '查询结果为空' }}
      />
    </Card>
  );
};

export default SqlExecutionResultCard;
