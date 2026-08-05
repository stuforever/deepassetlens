import React, { useEffect, useRef } from 'react';
import G6 from '@antv/g6';
import { useStore } from '../store/useStore';
import { tokens } from '../theme/tokens';
// 注意：G6 使用 Canvas 2D API（fillStyle/strokeStyle），无法解析 CSS var(--*)，
// 故画布内配色必须用 tokens 的实际色值，不能用 CSS 变量。

// 将节点注册移出组件外部，防止 React 重新挂载时重复注册报错
if (G6.registerNode) {
  G6.registerNode('domain-node', {
    draw(cfg: any, group: any) {
      const { level, collapsed, children, isEntity, entityCategory } = cfg;
      const colors = ['#5B8FF9', '#5AD8A6', '#5D7092', '#F6BD16', tokens.colors.ai, '#eb2f96'];
      let color = '#5B8FF9';
      let fillColor: string = tokens.colors.bgContent;
      if (typeof level === 'number') {
        color = colors[level - 1] || colors[0];
      } else if (isEntity) {
        if (entityCategory === 'activity_entity') {
          color = '#13c2c2';
          fillColor = '#e6fffb';
        } else {
          color = '#fa8c16';
          fillColor = '#fff7e6';
        }
      }
      
      const width = 120;
      const height = 36;
      
      const rect = group.addShape('rect', {
        attrs: {
          x: 0,
          y: -height / 2,
          width,
          height,
          radius: 4,
          fill: fillColor,
          stroke: color,
          lineWidth: 2,
          cursor: 'pointer',
        },
        name: 'rect-shape',
      });

      const displayName =
        typeof level === 'number'
          ? `L${level} ${cfg.name}`
          : cfg.name;
      group.addShape('text', {
        attrs: {
          text: displayName,
          x: width / 2,
          y: 0,
          fill: tokens.colors.textPrimary,
          fontSize: 12,
          textAlign: 'center',
          textBaseline: 'middle',
          cursor: 'pointer',
        },
        name: 'text-shape',
      });

      if (children && children.length > 0) {
        const markerSize = 12;
        group.addShape('marker', {
          attrs: {
            x: width + 8,
            y: 0,
            r: markerSize / 2,
            symbol: collapsed ? G6.Marker.expand : G6.Marker.collapse,
            stroke: color,
            fill: tokens.colors.bgContent,
            lineWidth: 1,
            cursor: 'pointer',
          },
          name: 'collapse-icon',
        });
      }

      return rect;
    },
    setState(name?: string, value?: any, item?: any) {
      if (name === 'hover' && item) {
        const group = item.getContainer();
        const rect = group.find((e: any) => e.get('name') === 'rect-shape');
        if (rect) {
          rect.attr('fill', value ? tokens.colors.border : tokens.colors.bgContent);
        }
      }
    },
  }, 'single-node');
}

type TreeCanvasProps = {
  focusEntity?: { code: string; name?: string } | null;
};

const TreeCanvas: React.FC<TreeCanvasProps> = ({ focusEntity }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const { concepts, fetchConcepts, setSelectedNode, setModelingModalVisible } = useStore();

  // 1. 获取数据
  useEffect(() => {
    fetchConcepts();
  }, [fetchConcepts]);

  // 2. 构建树结构逻辑
  const buildTree = (data: any[]) => {
    if (!data || data.length === 0) return null;

    const map = new Map();
    const rootChildren: any[] = [];

    // 建立 ID 索引
    data.forEach(item => {
      const node: any = { ...item, children: [] };
      // 处理实体：L2 展示主数据实体，并在矩阵打点子树中展示业务活动实体
      if (item.level === 2 && item.entities && item.entities.length > 0) {
        item.entities.forEach((e: any) => {
          const eNodeId = `tree-entity-${item.id}-${e.id}`;
          const eNode: any = {
            id: eNodeId,
            name: `${e.entity_name} (主数据实体)`,
            level: 'Entity',
            type: 'entity',
            isEntity: true,
            entityCategory: 'master_entity',
            rawEntityId: e.id,
            entityCode: e.entity_code || '',
            entityName: e.entity_name || '',
            children: []
          };
          // 关键：如果实体有 dynamic_children (矩阵打点生成的业务子树)
          if (e.dynamic_children) {
            const buildDynamicSubtree = (dynNodes: any[], parentPath: string): any[] => {
              return dynNodes.map((dn: any) => {
                const currentPath = `${parentPath}_${dn.id}`;
                return {
                  id: currentPath,
                  name: dn.name,
                  level: dn.level,
                  type: 'concept',
                  children: dn.children 
                    ? buildDynamicSubtree(dn.children, currentPath) 
                    : (dn.entities ? dn.entities.map((ent: any) => ({
                          id: `${currentPath}_${ent.id}`,
                          name: `${ent.name} (业务活动实体)`,
                          level: 'FactEntity',
                          isEntity: true,
                          entityCategory: 'activity_entity',
                          rawEntityId: ent.id
                        })) : [])
                };
              });
            };
            eNode.children = buildDynamicSubtree(e.dynamic_children, eNodeId);
          }
          node.children.push(eNode);
        });
      }
      map.set(item.id, node);
    });

    data.forEach(item => {
      const node = map.get(item.id);
      // 恢复全量层级：L1->L2, L0->L3, L3->L4
      if (item.parent_id && map.has(item.parent_id)) {
        map.get(item.parent_id).children.push(node);
      } else if (item.level === 1 || item.level === 0) {
        rootChildren.push(node);
      }
    });

    return {
      id: 'root',
      name: '电力资产全景图谱',
      children: rootChildren
    };
  };

  // 3. 初始化图表
  useEffect(() => {
    if (!containerRef.current || graphRef.current) return;

    const graph = new G6.TreeGraph({
        // ... (existing config)
        container: containerRef.current,
        width: containerRef.current.scrollWidth,
        height: containerRef.current.scrollHeight || 800,
        modes: {
          default: [
            'drag-canvas',
            'zoom-canvas',
          ],
        },
        defaultNode: {
          type: 'domain-node',
        },
        defaultEdge: {
          type: 'cubic-horizontal',
          style: {
            stroke: '#A3B1BF',
          },
        },
        // 状态样式：聚焦实体时，非目标节点变暗、目标节点高亮
        nodeStateStyles: {
          dim: { opacity: 0.15 },
          highlight: { stroke: tokens.colors.primary, lineWidth: 2 },
        },
        edgeStateStyles: {
          dim: { opacity: 0.08 },
        },
        layout: {
          type: 'compactBox',
          direction: 'LR',
          getId: (d: any) => d.id,
          getHeight: () => 36,
          getWidth: () => 120,
          getVGap: () => 20,
          getHGap: () => 80,
        },
      });

      graph.on('node:click', (evt: any) => {
        const { item, target } = evt;
        const model = item.get('model');
        const targetName = target?.get('name');
        
        // 如果点击的是加减号图标
        if (targetName === 'collapse-icon') {
          const collapsed = !model.collapsed;
          graph.updateItem(item, { collapsed });
          graph.layout();
          return;
        }

        // 否则选中该概念分类节点
        // 如果是实体，尝试找到原始实体信息
        const actualModel = model.rawEntityId 
          ? { ...model, id: model.rawEntityId } 
          : model;
        setSelectedNode(actualModel);

        // 新增交互：点击 L2 节点弹出主数据建模，点击 L4 节点弹出业务活动建模
        if (model.level === 2) {
          setModelingModalVisible(true, 'master', `concept-${model.id}`);
        } else if (model.level === 4) {
          setModelingModalVisible(true, 'activity', `concept-${model.id}`);
        }
      });

    graph.on('node:mouseenter', (evt: any) => {
      const { item } = evt;
      graph.setItemState(item, 'hover', true);
    });

    graph.on('node:mouseleave', (evt: any) => {
      const { item } = evt;
      graph.setItemState(item, 'hover', false);
    });

    // 缩放级标签显隐：zoom < 0.5 时隐藏标签，减少视觉拥挤
    let labelHidden = false;
    graph.on('viewportchange', () => {
      const zoom = graph.getZoom();
      if (zoom < 0.5 && !labelHidden) {
        labelHidden = true;
        graph.getNodes().forEach((node: any) => {
          const group = node.getContainer();
          const text = group.find((s: any) => s.get('name') === 'text-shape');
          if (text) text.hide();
        });
      } else if (zoom >= 0.5 && labelHidden) {
        labelHidden = false;
        graph.getNodes().forEach((node: any) => {
          const group = node.getContainer();
          const text = group.find((s: any) => s.get('name') === 'text-shape');
          if (text) text.show();
        });
      }
    });

    graphRef.current = graph;

    // 如果初始化时已经有数据了，立即渲染
    if (concepts && concepts.length > 0) {
      const treeData = buildTree(concepts);
      if (treeData) {
        graph.data(treeData);
        graph.render();
        graph.fitView();
      }
    }
  }, [setSelectedNode, concepts, setModelingModalVisible]);

  // 4. 监听数据变化更新图表
  useEffect(() => {
    if (concepts.length > 0 && graphRef.current) {
      const treeData = buildTree(concepts);
      if (treeData) {
        graphRef.current.changeData(treeData);
        graphRef.current.fitView();
      }
    }
  }, [concepts]);

  // 5. focusEntity 变化时：高亮+放大+聚焦该实体节点
  useEffect(() => {
    if (!focusEntity?.code) return;

    const doHighlight = () => {
      if (!graphRef.current) return false;
      const graph = graphRef.current;
      const allNodes = graph.getNodes();
      if (!allNodes || allNodes.length === 0) return false;

      let targetNode: any = null;
      for (const n of allNodes) {
        const model = n.getModel();
        const name = String(model.name || '');
        if (
          model.entityCode === focusEntity.code ||
          model.entityName === focusEntity.name ||
          name.includes(focusEntity.code) ||
          (focusEntity.name && name.includes(focusEntity.name))
        ) {
          targetNode = n;
          break;
        }
      }
      if (!targetNode) return false;

      // 清除其他节点高亮，全部变暗
      allNodes.forEach((n: any) => {
        graph.setItemState(n, 'highlight', false);
        graph.setItemState(n, 'dim', true);
      });
      // 高亮+不暗化目标节点
      graph.setItemState(targetNode, 'highlight', true);
      graph.setItemState(targetNode, 'dim', false);
      // 边也同步 dim：非相关边变暗
      const targetId = targetNode.getModel().id;
      graph.getEdges().forEach((e: any) => {
        const em = e.getModel();
        const isRelated = em.source === targetId || em.target === targetId;
        graph.setItemState(e, 'dim', !isRelated);
      });
      // 聚焦到目标节点并放大
      graph.focusItem(targetNode, true, { easing: 'easeCubic', duration: 600 });
      setTimeout(() => {
        if (graphRef.current) {
          graphRef.current.zoomTo(1.5, undefined, true);
        }
      }, 400);
      return true;
    };

    // 延迟执行，确保图谱数据已渲染
    let retries = 0;
    const tryHighlight = () => {
      if (doHighlight() || retries >= 10) return;
      retries++;
      setTimeout(tryHighlight, 300);
    };
    const timer = setTimeout(tryHighlight, 500);
    return () => clearTimeout(timer);
  }, [focusEntity]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%', background: 'var(--bg-page)' }} />;
};

export default TreeCanvas;
