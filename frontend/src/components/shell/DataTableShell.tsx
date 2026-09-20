/**
 * DataTableShell - 表格区（B4 美化：S1 容器 + 密度开关 + 加载骨架屏）。
 * 批量操作提示条(可选) + 工具条（密度开关，可选）+ antd Table + 分页。
 * 支持 compact(行高36)/standard(44)，密度开关可运行时切换。
 * 名称列固定左、操作列固定右由调用方在 columns 配置，本组件不强制。
 */
import React, { useState } from 'react';
import { Table, Alert, Segmented, Skeleton, Empty } from 'antd';
import type { TableProps } from 'antd';
import { tokens } from '../../theme/tokens';

/** 密度开关持久化 key（规格 C42：dal_table_density） */
const DENSITY_STORAGE_KEY = 'dal_table_density';
function loadDensity(initial?: boolean): boolean {
  if (initial !== undefined) return initial;
  try {
    return localStorage.getItem(DENSITY_STORAGE_KEY) === 'compact';
  } catch {
    return false;
  }
}

interface DataTableShellProps<T> {
  /** 批量操作提示条文案；不传则不渲染 */
  bulkBar?: React.ReactNode;
  /** 表格属性，透传 antd Table */
  tableProps: TableProps<T>;
  /** 紧凑模式（行高 36），默认 standard(44)；作为内部密度开关初始值，选择会持久化到 localStorage */
  compact?: boolean;
  /** 是否显示密度开关（B4：默认/紧凑 切换，放工具条右侧） */
  showDensityToggle?: boolean;
  /** 加载中；透传 Table.loading（B4：加载且无数据时显示骨架屏） */
  loading?: boolean;
  /** 三轨M9(U4)：空态主操作（antd Empty + 主按钮——C 模板硬门） */
  emptyAction?: React.ReactNode;
  /** 三轨M9(U4)：空态描述文案 */
  emptyText?: string;
  /** 错误状态；传入则替代表格渲染（通常传 <ErrorState />） */
  error?: React.ReactNode;
  style?: React.CSSProperties;
}

function DataTableShell<T extends object = any>({
  bulkBar,
  tableProps,
  compact: initialCompact,
  showDensityToggle = true,
  loading,
  error,
  emptyAction,
  emptyText,
  style,
}: DataTableShellProps<T>) {
  const [compact, setCompact] = useState(() => loadDensity(initialCompact));
  const size = compact ? 'small' : 'middle';
  const rowCount = (tableProps.dataSource as any[] | undefined)?.length ?? 0;
  const showSkeleton = !!loading && rowCount === 0 && !error;

  const handleDensityChange = (v: string | number) => {
    const next = v === 'compact';
    setCompact(next);
    try {
      localStorage.setItem(DENSITY_STORAGE_KEY, next ? 'compact' : 'standard');
    } catch {
      /* 隐私模式忽略 */
    }
  };

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
      ) : showSkeleton ? (
        /* B4 三态：加载态用骨架屏（表 = 3 行条形）替代裸 Spin */
        <div style={{ background: tokens.colors.bgContent, borderRadius: tokens.radius.card, border: `1px solid ${tokens.colors.border}`, boxShadow: tokens.elevation.s1, padding: tokens.space.s4 }}>
          <Skeleton active paragraph={{ rows: 3 }} title={false} />
        </div>
      ) : (
        <div
          style={{
            display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0,
            background: tokens.colors.bgContent,
            borderRadius: tokens.radius.card,
            border: `1px solid ${tokens.colors.border}`,
            boxShadow: tokens.elevation.s1,
            overflow: 'hidden',
          }}
        >
          {showDensityToggle ? (
            <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '6px 10px 0' }}>
              <Segmented
                size="small"
                value={compact ? 'compact' : 'standard'}
                onChange={handleDensityChange}
                options={[
                  { label: '标准', value: 'standard' },
                  { label: '紧凑', value: 'compact' },
                ]}
              />
            </div>
          ) : null}
          <Table<T>
            size={size}
            loading={!!loading}
            locale={{
              emptyText: (
                <div style={{ padding: '32px 0' }} data-testid="table-empty">
                  <Empty description={emptyText || '暂无数据'}>
                    {emptyAction}
                  </Empty>
                </div>
              ),
            }}
            style={{ background: tokens.colors.bgContent, borderRadius: tokens.radius.card }}
            {...tableProps}
          />
        </div>
      )}
    </div>
  );
}

export default DataTableShell;
