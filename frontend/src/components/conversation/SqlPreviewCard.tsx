import React, { useState } from 'react';
import { Button, Card, Space, Table, Tooltip, Typography } from 'antd';
import { CodeOutlined, CopyOutlined, ThunderboltOutlined, CheckCircleFilled } from '@ant-design/icons';
import { StatusTag } from '../shell';

const { Text, Paragraph } = Typography;

type SqlPreviewCardProps = {
  data?: {
    sql?: string;
    executed?: boolean;
    row_count?: number;
    columns?: string[];
    rows_preview?: any[][];
    exec_time_ms?: number;
    execute_error?: string;
  };
  onExecute?: () => void;
};

const SqlPreviewCard: React.FC<SqlPreviewCardProps> = ({ data, onExecute }) => {
  const [copied, setCopied] = useState(false);

  if (!data?.sql) {
    return null;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(data.sql || '').then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const columns = (data.columns || []).map((c) => ({ title: c, dataIndex: c, key: c }));

  return (
    <Card
      size="small"
      title={
        <Space>
          <CodeOutlined style={{ color: 'var(--color-ai)' }} />
          <span>SQL 预览</span>
          {data.executed ? (
            <StatusTag icon={<CheckCircleFilled />} preset="success">
              已执行 · {data.row_count} 行 · {data.exec_time_ms}ms
            </StatusTag>
          ) : (
            <StatusTag preset="info">已拼装 · 待执行</StatusTag>
          )}
        </Space>
      }
      extra={
        <Space>
          <Tooltip title={copied ? '已复制' : '复制 SQL'}>
            <Button
              size="small"
              icon={copied ? <CheckCircleFilled /> : <CopyOutlined />}
              onClick={handleCopy}
            />
          </Tooltip>
          {!data.executed && onExecute && (
            <Button
              size="small"
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={onExecute}
            >
              执行
            </Button>
          )}
        </Space>
      }
    >
      <Paragraph
        copyable={{ text: data.sql, tooltips: ['复制', '已复制'] }}
        style={{
          marginBottom: 12,
          padding: 10,
          background: 'var(--color-success-bg)',
          color: 'var(--color-success)',
          border: '1px solid var(--color-success-bg)',
          borderRadius: 6,
          fontFamily: 'Consolas, Monaco, monospace',
          fontSize: 13,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
        }}
      >
        {data.sql}
      </Paragraph>
      {data.executed && data.rows_preview && data.rows_preview.length > 0 && (
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            数据预览（前 {data.rows_preview.length} 行）：
          </Text>
          <Table
            size="small"
            style={{ marginTop: 8 }}
            columns={columns}
            dataSource={data.rows_preview.map((row, i) => {
              const obj: Record<string, any> = { key: i };
              (data.columns || []).forEach((col, ci) => (obj[col] = row[ci]));
              return obj;
            })}
            pagination={false}
            scroll={{ x: true }}
          />
        </div>
      )}
      {data.execute_error && (
        <div style={{ marginTop: 8, padding: 8, background: 'var(--color-error-bg)', border: '1px solid var(--color-error-bg)', borderRadius: 4 }}>
          <Text type="danger" style={{ fontSize: 12, fontWeight: 600 }}>⚠ 执行失败：</Text>
          <Text type="danger" style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4 }}>
            {data.execute_error}
          </Text>
        </div>
      )}
    </Card>
  );
};

export default SqlPreviewCard;
