/**
 * PageShell - 页面外壳（统一资产管理页面骨架）。
 * 结构: PageHeader + FilterBar + children。
 * padded 默认 false -- 由 AppTabs 统一提供 contentPadding(20px)；画布类页面 AppTabs 已设 padding:0。
 * 需要额外内层 padding 时（如弹层内容）手动传 padded。
 */
import React from 'react';
import PageHeader from './PageHeader';
import FilterBar, { type FilterBarProps } from './FilterBar';
import { tokens } from '../../theme/tokens';

interface PageShellProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
  /** 页面主操作（右上角） */
  extra?: React.ReactNode;
  /** 筛选区配置；传 false 不渲染 */
  filters?: FilterBarProps | false;
  /** 是否有内边距；画布类页面传 false */
  padded?: boolean;
  /** 直接渲染 header 区（覆盖 title/description/extra） */
  header?: React.ReactNode;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

const PageShell: React.FC<PageShellProps> = ({
  title,
  description,
  extra,
  filters,
  padded = false,
  header,
  children,
  style,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0,
        height: '100%',
        padding: padded ? tokens.layout.contentPadding : 0,
        overflow: 'hidden',
        ...style,
      }}
    >
      {header ?? (title !== undefined ? <PageHeader title={title} description={description} extra={extra} /> : null)}
      {filters ? <FilterBar {...filters} /> : null}
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>{children}</div>
    </div>
  );
};

export default PageShell;
