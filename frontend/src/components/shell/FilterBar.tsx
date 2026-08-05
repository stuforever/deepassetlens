/**
 * FilterBar - 筛选区。
 * 单行排列：搜索框(260) + 筛选项(≤4 单行) + 更多筛选抽屉(>4) + 右侧 extra。
 */
import React, { useState } from 'react';
import { Input, Button, Drawer, Space } from 'antd';
import { SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { tokens } from '../../theme/tokens';

export interface FilterBarProps {
  /** 搜索框配置；不传则不渲染搜索框 */
  search?: { placeholder?: string; value?: string; onChange?: (v: string) => void; onSearch?: (v: string) => void; width?: number };
  /** 筛选项节点；前 4 个单行展示，超出进"更多筛选"抽屉 */
  filters?: React.ReactNode[];
  /** 右侧辅助操作 */
  extra?: React.ReactNode;
  style?: React.CSSProperties;
}

const INLINE_MAX = 4;

const FilterBar: React.FC<FilterBarProps> = ({ search, filters = [], extra, style }) => {
  const [moreOpen, setMoreOpen] = useState(false);
  const inlineFilters = filters.slice(0, INLINE_MAX);
  const moreFilters = filters.slice(INLINE_MAX);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: tokens.space.s2,
        flexWrap: 'wrap',
        marginBottom: tokens.space.s3,
        ...style,
      }}
    >
      {search ? (
        <Input
          prefix={<SearchOutlined style={{ color: tokens.colors.textTertiary }} />}
          placeholder={search.placeholder ?? '搜索'}
          value={search.value}
          onChange={(e) => search.onChange?.(e.target.value)}
          onPressEnter={(e) => search.onSearch?.((e.target as HTMLInputElement).value)}
          allowClear
          style={{ width: search.width ?? 260, flexShrink: 0 }}
        />
      ) : null}

      {inlineFilters.map((f, i) => (
        <div key={i} style={{ flexShrink: 0 }}>{f}</div>
      ))}

      {moreFilters.length > 0 ? (
        <Button icon={<FilterOutlined />} onClick={() => setMoreOpen(true)}>更多筛选</Button>
      ) : null}

      <div style={{ flex: 1 }} />

      {extra ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: tokens.space.s2 }}>{extra}</div>
      ) : null}

      <Drawer
        title="更多筛选"
        open={moreOpen}
        onClose={() => setMoreOpen(false)}
        width={320}
        extra={
          <Button type="primary" size="small" onClick={() => setMoreOpen(false)}>应用</Button>
        }
      >
        <Space direction="vertical" size={tokens.space.s3} style={{ width: '100%' }}>
          {moreFilters.map((f, i) => <div key={i} style={{ width: '100%' }}>{f}</div>)}
        </Space>
      </Drawer>
    </div>
  );
};

export default FilterBar;
