/**
 * SourceTreeSider —— 来源表管理的左侧筛选树侧栏（纯展示 + 事件上抛）
 *
 * 从 SourceManager 抽离：主数据/业务/参考三个 Tab 共用的
 * 「搜索框 + 筛选树」Sider。树数据、选中/展开与选择逻辑由容器经 props 提供。
 */
import React from 'react';
import { Layout, Input, Tree } from 'antd';
import { SearchOutlined } from '@ant-design/icons';

const { Sider } = Layout;

export type SourceTreeSiderProps = {
  placeholder: string;
  search: string;
  onSearchChange: (v: string) => void;
  treeData: any[];
  selectedKeys: React.Key[];
  expandedKeys: React.Key[];
  onExpand: (keys: React.Key[]) => void;
  onSelect: (keys: React.Key[]) => void;
};

const SourceTreeSider: React.FC<SourceTreeSiderProps> = (p) => (
  <Sider
    width={280}
    style={{ background: 'var(--bg-content)', borderRight: '1px solid var(--color-border)', padding: '16px' }}
  >
    <div style={{ marginBottom: '16px' }}>
      <Input
        placeholder={p.placeholder}
        prefix={<SearchOutlined />}
        value={p.search}
        onChange={(e) => p.onSearchChange(e.target.value)}
        allowClear
      />
    </div>
    <Tree
      showIcon
      treeData={p.treeData}
      selectedKeys={p.selectedKeys}
      expandedKeys={p.expandedKeys}
      onExpand={p.onExpand}
      onSelect={p.onSelect}
    />
  </Sider>
);

export default SourceTreeSider;
