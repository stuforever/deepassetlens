/**
 * SQL 查询结果表格
 * 接收后端 sql_result 事件推送的 { columns, rows, row_count, sql }
 * 渲染为 antd Table（超过 20 行自动分页）
 *
 * 增强（v2）：
 * - 列排序（sorter）
 * - CSV 导出（前端拼装 + Blob 下载）
 * - 复制 SQL 按钮
 * - showTotal / showSizeChanger
 * - 空结果友好提示
 */
import React, { useMemo, useState } from 'react';
import { Table, Typography, Empty, Button, Space, Tooltip, message } from 'antd';
import { TableOutlined, DownloadOutlined, CopyOutlined } from '@ant-design/icons';
import { StatusTag } from '../shell';

const { Text } = Typography;

export type SqlResultData = {
  columns?: string[];
  rows?: any[];
  row_count?: number;
  sql?: string;
};

type SqlResultTableProps = {
  data: SqlResultData | null;
};

const SqlResultTable: React.FC<SqlResultTableProps> = ({ data }) => {
  const [copied, setCopied] = useState(false);

  const columns = useMemo(() => {
    if (!data?.columns || data.columns.length === 0) return [];
    return data.columns.map((col, i) => ({
      title: col,
      dataIndex: `c${i}`,
      key: `c${i}`,
      ellipsis: true,
      width: 160,
      sorter: (a: any, b: any) => {
        const va = a[`c${i}`];
        const vb = b[`c${i}`];
        if (va === null || va === undefined) return -1;
        if (vb === null || vb === undefined) return 1;
        if (typeof va === 'number' && typeof vb === 'number') return va - vb;
        return String(va).localeCompare(String(vb), 'zh-CN');
      },
      render: (val: any) => {
        if (val === null || val === undefined) return <Text type="secondary">NULL</Text>;
        return String(val);
      },
    }));
  }, [data?.columns]);

  const dataSource = useMemo(() => {
    if (!data?.rows || data.rows.length === 0) return [];
    return data.rows.map((row, ri) => {
      const obj: any = { key: ri };
      if (Array.isArray(row)) {
        row.forEach((cell, ci) => { obj[`c${ci}`] = cell; });
      } else if (typeof row === 'object' && row !== null) {
        (data.columns || []).forEach((col, ci) => { obj[`c${ci}`] = row[col]; });
      }
      return obj;
    });
  }, [data?.rows, data?.columns]);

  if (!data || !data.columns || data.columns.length === 0) return null;

  const totalCount = data.row_count ?? dataSource.length;

  // CSV 导出：前端拼装 + Blob 下载
  const handleExportCsv = () => {
    if (!dataSource.length || !data.columns) return;
    const header = data.columns.map((c) => `"${(c || '').replace(/"/g, '""')}"`).join(',');
    const body = dataSource.map((row) =>
      data.columns!.map((_, ci) => {
        const val = row[`c${ci}`];
        if (val === null || val === undefined) return '';
        return `"${String(val).replace(/"/g, '""')}"`;
      }).join(',')
    ).join('\n');
    const csv = '\ufeff' + header + '\n' + body; // BOM 防止中文乱码
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `query_result_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success('已导出 CSV');
  };

  // 复制 SQL
  const handleCopySql = () => {
    if (!data.sql) return;
    navigator.clipboard.writeText(data.sql).then(() => {
      setCopied(true);
      message.success('SQL 已复制');
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      message.error('复制失败');
    });
  };

  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
        <Space size={8}>
          <StatusTag icon={<TableOutlined />} preset="info">查询结果</StatusTag>
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {totalCount} 行 × {data.columns.length} 列
            {dataSource.length < totalCount ? `（预览前 ${dataSource.length} 行）` : ''}
          </Text>
        </Space>
        <Space size={4}>
          {data.sql ? (
            <Tooltip title={copied ? '已复制' : '复制 SQL'}>
              <Button type="text" size="small" icon={<CopyOutlined />} onClick={handleCopySql} />
            </Tooltip>
          ) : null}
          {dataSource.length > 0 ? (
            <Tooltip title="导出 CSV">
              <Button type="text" size="small" icon={<DownloadOutlined />} onClick={handleExportCsv} />
            </Tooltip>
          ) : null}
        </Space>
      </div>
      {dataSource.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无数据（查询结果为空）" />
      ) : (
        <Table
          size="small"
          columns={columns}
          dataSource={dataSource}
          pagination={dataSource.length > 20 ? {
            pageSize: 20,
            size: 'small',
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 行`,
            pageSizeOptions: ['10', '20', '50', '100'],
          } : false}
          scroll={{ x: 'max-content' }}
          bordered
          style={{ fontSize: 12 }}
        />
      )}
    </div>
  );
};

export default SqlResultTable;
