/**
 * DataTableShell - 表格区。
 * 批量操作提示条(可选) + antd Table + 分页。支持 compact(行高36)/standard(44)。
 * 名称列固定左、操作列固定右由调用方在 columns 配置，本组件不强制。
 */
import React from 'react';
import { Table, Alert } from 'antd';
import type { TableProps } from 'antd';
import { tokens } from '../../theme/tokens';

interface DataTableShellProps<T> {
  /** 批量操作提示条文案；不传则不渲染 */
  bulkBar?: React.ReactNode;
  /** 表格属性，透传 antd Table */
  tableProps: TableProps<T>;
  /** 紧凑模式（行高 36），默认 standard(44) */
  compact?: boolean;
  /** 加载中；透传 Table.loading */
  loading?: boolean;
  /** 错误状态；传入则替代表格渲染（通常传 <ErrorState />） */
  error?: React.ReactNode;
  style?: React.CSSProperties;
}

function DataTableShell<T extends object = any>({
  bulkBar,
  tableProps,
  compact,
  loading,
  error,
  style,
}: DataTableShellProps<T>) {
  const size = compact ? 'small' : 'middle';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, ...style }}>
      {bulkBar ? (
        <Alert
          type="info"
          showIcon
          message={bulkBar}
          style={{ marginBottom: tokens.space.s2, borderRadius: tokens.radius.default }}
        />
      ) : null}
      {error ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 0 }}>
          {error}
        </div>
      ) : (
        <Table<T>
          size={size}
          loading={loading}
          style={{
            background: tokens.colors.bgContent,
            borderRadius: tokens.radius.card,
          }}
          {...tableProps}
        />
      )}
    </div>
  );
}

export default DataTableShell;
