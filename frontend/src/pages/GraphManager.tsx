/**
 * GraphManager - 图谱画布统一外壳（纯画布，无工具栏/页签占位）。
 * 每个左侧菜单固定对应一种画布（由 App 按路由设置 canvasMode）：
 *   图谱管理/force -> ForceCanvas(力导向图)；四区建模/quad -> QuadCanvas(四区)；
 *   资产矩阵/matrix -> MatrixCanvas(矩阵)；图库/neo4j -> Neo4jForceCanvas(Neo4j)。
 * 画布满撑内容区（AppTabs 对画布页 padding:0）。
 */
import React from 'react';
import ForceCanvas from '../components/ForceCanvas';
import Neo4jForceCanvas from '../components/Neo4jForceCanvas';
import MatrixCanvas from '../components/MatrixCanvas';
import QuadCanvas from '../components/QuadCanvas';
import { useStore } from '../store/useStore';
import { tokens } from '../theme/tokens';

const GraphManager: React.FC = () => {
  const { canvasMode } = useStore();
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: tokens.colors.bgContent }}>
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
