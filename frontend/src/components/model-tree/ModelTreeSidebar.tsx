/**
 * ModelTreeSidebar —— 模型树左侧导航（纯展示）
 *
 * 从 ModelTreeManager 抽离：只负责「标题 + 树/加载/空态」展示，
 * 树数据与展开/选中状态由容器（ModelTreeManager）经 props 传入。
 */
import React from 'react';
import { Layout, Tree, Spin, Empty, Typography } from 'antd';

const { Sider } = Layout;
const { Text } = Typography;

type Props = {
  rootName: string;
  readOnly?: boolean;
  loading?: boolean;
  treeData: any[];
  selectedKey: string | null;
  expandedKeys: string[];
  onExpand: (keys: string[]) => void;
  onSelect: (key: string | null) => void;
};

const ModelTreeSidebar: React.FC<Props> = ({
  rootName,
  readOnly = false,
  loading = false,
  treeData,
  selectedKey,
  expandedKeys,
  onExpand,
  onSelect,
}) => (
  <Sider width={420} style={{ background: 'var(--bg-content)', borderRight: '1px solid var(--color-border)', padding: 12, overflow: 'auto' }}>
    <div style={{ marginBottom: 12 }}>
      <Text strong>{rootName}</Text>
      <div style={{ color: 'var(--text-tertiary)', fontSize: 12, marginTop: 4 }}>
        {readOnly
          ? '左侧树按顺序展示概念分类、数据实体与属性，右侧仅查看详情，可返回图谱页面。'
          : '左侧树按顺序展示概念分类、数据实体与属性，右侧按区域分别维护目录、数据实体、属性和数据实体关系。'}
      </div>
    </div>
    {loading ? (
      <div style={{ textAlign: 'center', paddingTop: 80 }}>
        <Spin />
      </div>
    ) : treeData.length > 0 ? (
      <Tree
        selectedKeys={selectedKey ? [selectedKey] : []}
        expandedKeys={expandedKeys}
        onExpand={(keys) => onExpand(keys as string[])}
        onSelect={(keys) => onSelect((keys[0] as string) || null)}
        treeData={treeData}
        blockNode
      />
    ) : (
      <Empty description="暂无数据" />
    )}
  </Sider>
);

export default ModelTreeSidebar;
