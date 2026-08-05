import React, { useEffect, useRef, useState } from 'react';
import G6 from '@antv/g6';
import { Button, Space, Card, Spin, message } from 'antd';
import { SyncOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useStore } from '../store/useStore';
import { conceptApi } from '../services/api';
import { tokens } from '../theme/tokens';
import { StatusTag } from './shell';
// G6 使用 Canvas 2D API，无法解析 CSS var(--*)，画布内配色用 tokens 实际色值。

type GraphNodeModel = {
  type?: string;
  label?: string;
  level_label?: string;
  code?: string;
};

const LEVEL_META: Record<string, { label: string; fill: string; stroke: string }> = {
  L1: { label: 'L1 业务域', fill: '#fff0f6', stroke: '#eb2f96' },
  L2: { label: 'L2 主数据', fill: '#fff7e6', stroke: '#fa8c16' },
  L3: { label: 'L3 业务活动', fill: '#e6fffb', stroke: '#13c2c2' },
  L4: { label: 'L4 业务数据', fill: '#fff1f0', stroke: '#ff7875' },
  L2X: { label: 'L2X 主数据实体', fill: '#f9f0ff', stroke: tokens.colors.ai },
  L4X: { label: 'L4X 业务数据实体', fill: tokens.colors.primaryBg, stroke: '#2f54eb' },
};

const Neo4jForceCanvas: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState<any>(null);
  const [showEntities, setShowEntities] = useState(false);
  const [showConcepts, setShowConcepts] = useState(true);
  const [stats, setStats] = useState({ nodes: 0, edges: 0, l2Children: 0 });
  const setSelectedNode = useStore((state) => state.setSelectedNode);

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const response = await conceptApi.getNeo4jGraphData();
      const data = response.data || response;
      setGraphData(data);
      const nodes = data.nodes || [];
      const edges = data.edges || [];
      const l2Children = edges.filter((e: any) =>
        e.edge_type === 'concept_hierarchy' && e.target === 'L1-CUSTOMER'
      ).length;
      setStats({ nodes: nodes.length, edges: edges.length, l2Children });
      message.success(`已加载 Neo4j 图数据：${nodes.length} 节点 / ${edges.length} 边`);
    } catch (error) {
      console.error('Failed to fetch Neo4j graph data:', error);
      message.error('获取 Neo4j 图数据失败，请检查 Neo4j 服务状态');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  // 图谱实例初始化（完全照抄 ForceCanvas）
  useEffect(() => {
    if (!containerRef.current) return;

    if (!graphRef.current) {
      const graph = new G6.Graph({
        container: containerRef.current,
        width: containerRef.current.scrollWidth || 800,
        height: containerRef.current.scrollHeight || 800,
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node', {
            type: 'tooltip',
            formatText(model: GraphNodeModel) {
              return `名称: ${model.label}<br/>编码: ${model.code || '-'}<br/>层级: ${model.level_label || '-'}`;
            },
          }],
        },
        layout: {
          type: 'force',
          preventOverlap: true,
          linkDistance: 150,
          nodeStrength: -50,
        },
        defaultNode: {
          size: 40,
        },
        defaultEdge: {
          size: 1,
          color: '#e2e2e2',
          style: {
            endArrow: {
              path: G6.Arrow.triangle(5, 5, 2),
              fill: '#e2e2e2',
            },
          },
          labelCfg: {
            autoRotate: true,
            style: {
              fontSize: 10,
            },
          },
        },
      });

      graph.on('node:click', (evt: any) => {
        const { item } = evt;
        const model = item.get('model');
        setSelectedNode(model);
      });

      graphRef.current = graph;
    }
  }, [setSelectedNode]);

  // 当数据或过滤条件变化时，更新图谱（照抄 ForceCanvas）
  useEffect(() => {
    if (graphRef.current && graphData) {
      const { nodes, edges } = graphData;

      const filteredNodes = nodes.filter((n: any) => {
        if (n.type === 'entity' && !showEntities) return false;
        if (n.type === 'concept' && !showConcepts) return false;
        return true;
      });

      const filteredNodeIds = new Set(filteredNodes.map((n: any) => n.id));
      const filteredEdges = edges.filter((e: any) =>
        filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
      );

      const processedData = {
        nodes: filteredNodes.map((n: any) => {
          const lv = n.level_label || '';
          const meta = LEVEL_META[lv] || { fill: tokens.colors.primaryBg, stroke: '#3f7efb' };
          return {
            ...n,
            label: n.label || n.name,
            style: {
              fill: meta.fill,
              stroke: meta.stroke,
            },
          };
        }),
        edges: filteredEdges.map((e: any) => {
          const isEntityRel = e.edge_type === 'entity_generation';
          const isHierarchy = e.edge_type === 'concept_hierarchy';
          const isCrossChain = e.edge_type === 'concept_cross_chain';
          let edgeColor = '#A3B1BF';
          let edgeWidth = 1;
          if (isEntityRel) { edgeColor = tokens.colors.error; edgeWidth = 2.5; }
          else if (isCrossChain) { edgeColor = tokens.colors.ai; edgeWidth = 2; }
          else if (isHierarchy) { edgeColor = tokens.colors.success; edgeWidth = 1.5; }
          return {
            ...e,
            label: e.label,
            style: {
              stroke: edgeColor,
              lineWidth: edgeWidth,
              lineDash: isCrossChain ? [4, 4] : [],
              endArrow: {
                path: G6.Arrow.triangle(5, 5, 2),
                fill: edgeColor,
              },
            },
            labelCfg: {
              autoRotate: true,
              style: {
                fontSize: 10,
                fill: isCrossChain ? tokens.colors.ai : isEntityRel ? '#cf1322' : tokens.colors.textSecondary,
                background: {
                  fill: tokens.colors.bgContent,
                  padding: [2, 2, 2, 2],
                  radius: 2,
                }
              }
            }
          };
        })
      };

      graphRef.current.changeData(processedData);
      graphRef.current.layout();
      // 力导布局稳定后自动 fitView
      setTimeout(() => {
        if (graphRef.current) {
          graphRef.current.fitView(20);
        }
      }, 800);
    }
  }, [graphData, showEntities, showConcepts]);

  return (
    <Card
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, padding: 0, position: 'relative' }}
    >
      <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 10 }}>
        <Space>
          <StatusTag icon={<DatabaseOutlined />} preset="ai">数据源：Neo4j</StatusTag>
          <StatusTag preset="info">节点 {stats.nodes}</StatusTag>
          <StatusTag preset="info">边 {stats.edges}</StatusTag>
          <StatusTag preset="warning">L1-CUSTOMER 子节点 {stats.l2Children}</StatusTag>
          <Button
            type={showConcepts ? 'primary' : 'default'}
            onClick={() => setShowConcepts(!showConcepts)}
          >
            概念
          </Button>
          <Button
            type={showEntities ? 'primary' : 'default'}
            onClick={() => setShowEntities(!showEntities)}
          >
            实体
          </Button>
          <Button
            icon={<SyncOutlined />}
            onClick={fetchGraphData}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      </div>
      <Spin spinning={loading} style={{ position: 'absolute', top: '50%', left: '50%' }} />
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </Card>
  );
};

export default Neo4jForceCanvas;
