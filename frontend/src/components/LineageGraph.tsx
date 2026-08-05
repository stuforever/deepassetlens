import React, { useEffect, useMemo, useRef } from 'react';
import G6 from '@antv/g6';
import { Modal } from 'antd';
import { tokens } from '../theme/tokens';
// G6 使用 Canvas 2D API，无法解析 CSS var(--*)，画布内配色用 tokens 实际色值。

// 注册数据库节点图标
if (G6.registerNode) {
  G6.registerNode('database-node', {
    draw(cfg: any, group: any) {
      const { label } = cfg;
      const width = 120;
      const height = 40;
      
      const rect = group.addShape('rect', {
        attrs: {
          x: -width / 2,
          y: -height / 2,
          width,
          height,
          radius: 4,
          fill: tokens.colors.successBg,
          stroke: tokens.colors.successBg,
          lineWidth: 2,
        },
        name: 'rect-shape',
      });

      group.addShape('text', {
        attrs: {
          text: label,
          x: 0,
          y: 0,
          fill: tokens.colors.textPrimary,
          fontSize: 11,
          textAlign: 'center',
          textBaseline: 'middle',
        },
        name: 'text-shape',
      });

      return rect;
    },
  }, 'single-node');
}

interface LineageGraphProps {
  visible?: boolean;
  onClose?: () => void;
  data: any;
  mode?: 'modal' | 'embed';
  title?: string;
  height?: number;
  width?: number;
}

const LineageGraph: React.FC<LineageGraphProps> = ({ visible = false, onClose, data, mode = 'modal', title, height = 500, width = 800 }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const shouldRender = mode === 'embed' ? Boolean(data) : Boolean(visible && data);

  const g6Data = useMemo(() => {
    if (!data) return null;
    if (Array.isArray(data.nodes) && Array.isArray(data.edges)) {
      const nodes = (data.nodes || []).map((n: any) => {
        const dUp = n.depth_up;
        const dDown = n.depth_down;
        const isRoot = dUp === 0 && dDown === 0;
        const style = isRoot
          ? { fill: tokens.colors.errorBg, stroke: tokens.colors.error }
          : dUp && dDown > 0
            ? { fill: tokens.colors.primaryBg, stroke: tokens.colors.primary }
            : { fill: tokens.colors.successBg, stroke: '#73d13d' };
        return {
          id: n.id,
          label: n.label || n.metric_name || n.metric_code || n.id,
          style,
          owner: n.owner,
        };
      });
      const edges = (data.edges || []).map((e: any, idx: number) => ({
        id: e.id || `${e.source}-${e.target}-${idx}`,
        source: e.source,
        target: e.target,
        label: e.type || '',
        labelCfg: { autoRotate: true, style: { fontSize: 10 } },
      }));
      return { nodes, edges };
    }

    if (data.entity?.id && Array.isArray(data.lineage)) {
      const nodes: any[] = [];
      const edges: any[] = [];
      nodes.push({
        id: data.entity.id,
        label: data.entity.name,
        style: { fill: tokens.colors.errorBg, stroke: tokens.colors.error },
      });
      data.lineage.forEach((item: any, idx: number) => {
        const sourceId = item.source_table.id || `source-${item.mapping_id}-${idx}`;
        nodes.push({
          id: sourceId,
          label: item.source_table.table_name,
          type: 'database-node',
          style: { fill: tokens.colors.successBg, stroke: '#73d13d' },
        });
        edges.push({
          source: sourceId,
          target: data.entity.id,
          label: 'Mapping',
          labelCfg: {
            autoRotate: true,
            style: { fontSize: 10 },
          },
        });
      });
      return { nodes, edges };
    }

    return null;
  }, [data]);

  useEffect(() => {
    if (shouldRender && containerRef.current && g6Data) {
      if (!graphRef.current) {
        const graph = new G6.Graph({
          container: containerRef.current,
          width: mode === 'embed' ? (containerRef.current.scrollWidth || width) : 750,
          height: mode === 'embed' ? (containerRef.current.scrollHeight || height) : 400,
          modes: {
            default: ['drag-canvas', 'zoom-canvas'],
          },
          defaultNode: {
            size: [120, 40],
            type: 'rect',
            style: {
              fill: tokens.colors.primaryBg,
              stroke: tokens.colors.primary,
              lineWidth: 1,
              radius: 4,
            },
            labelCfg: {
              style: {
                fill: tokens.colors.textPrimary,
                fontSize: 12,
              },
            },
          },
          defaultEdge: {
            type: 'polyline',
            style: {
              endArrow: true,
              stroke: '#A3B1BF',
            },
          },
          layout: {
            type: 'dagre',
            rankdir: 'LR',
            nodesep: 30,
            ranksep: 50,
          },
        });
        graphRef.current = graph;
      }

      graphRef.current.data({ nodes: g6Data.nodes, edges: g6Data.edges });
      graphRef.current.render();
      graphRef.current.fitView();
    }
  }, [shouldRender, g6Data, mode, height, width]);

  useEffect(() => {
    return () => {
      try {
        if (graphRef.current) {
          graphRef.current.destroy();
          graphRef.current = null;
        }
      } catch {}
    };
  }, []);

  if (mode === 'embed') {
    return <div ref={containerRef} style={{ width: '100%', height, background: 'var(--bg-subtle)' }} />;
  }

  return (
    <Modal
      title={title || '数据溯源链路图'}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={width}
      bodyStyle={{ height }}
      destroyOnHidden
    >
      <div ref={containerRef} style={{ width: '100%', height: '100%', background: 'var(--bg-subtle)' }} />
    </Modal>
  );
};

export default LineageGraph;
