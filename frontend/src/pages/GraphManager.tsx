/**
 * GraphManager - 图谱画布统一外壳（v3 #10/#17 / Task 6：4 合 1 单入口页内 Tab）。
 * 四视图（quad 四区/force 图谱/matrix 矩阵/neo4j 图库）页内 Tabs 切换——
 * onChange 改 canvasMode + 同步 /graph?view= 参数；初始化读 ?view=。
 * 旧路由 /tree-model /matrix /gallery 已重定向到 /graph?view=...（routes.tsx）。
 * 画布满撑内容区（AppTabs 对画布页 padding:0）。
 */
import React, { useEffect } from 'react';
import { Tabs } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ForceCanvas from '../components/ForceCanvas';
import Neo4jForceCanvas from '../components/Neo4jForceCanvas';
import MatrixCanvas from '../components/MatrixCanvas';
import QuadCanvas from '../components/QuadCanvas';
import { useStore } from '../store/useStore';
import { tokens } from '../theme/tokens';

type CanvasMode = 'force' | 'neo4j' | 'matrix' | 'quad';

const VIEW_ITEMS: { key: CanvasMode; label: string }[] = [
  { key: 'quad', label: '四区建模' },
  { key: 'force', label: '图谱' },
  { key: 'matrix', label: '资产矩阵' },
  { key: 'neo4j', label: '图库' },
];

const GraphManager: React.FC = () => {
  const { canvasMode, setCanvasMode } = useStore();
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams(); // react-router v6 返回元组（E-25④ 同口径）

  // 初始化：?view= 优先（旧路由重定向/⌘K 直达落点）
  useEffect(() => {
    const v = search.get('view') as CanvasMode | null;
    if (v && v !== canvasMode && VIEW_ITEMS.some((i) => i.key === v)) {
      setCanvasMode(v);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onChange = (key: string) => {
    setCanvasMode(key as CanvasMode);
    setSearch(new URLSearchParams({ view: key }), { replace: true });
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: tokens.colors.bgContent }}>
      <div data-testid="graph-view-tabs" style={{ flexShrink: 0, background: tokens.colors.bgContent, padding: '0 16px', borderBottom: `1px solid ${tokens.colors.border}` }}>
        <Tabs
          activeKey={canvasMode}
          onChange={onChange}
          items={VIEW_ITEMS.map((i) => ({ key: i.key, label: i.label }))}
          style={{ marginBottom: 0 }}
          size="small"
        />
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        {canvasMode === 'quad' ? (
          <QuadCanvas />
        ) : canvasMode === 'force' ? (
          <ForceCanvas />
        ) : canvasMode === 'neo4j' ? (
          <Neo4jForceCanvas />
        ) : (
          <MatrixCanvas />
        )}
      </div>
    </div>
  );
};

export default GraphManager;
