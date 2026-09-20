/**
 * ForceCanvas - 力导向图画布（图谱管理默认视图）。
 *
 * 视觉规范（第二批）：
 *   - 节点：白色 fill + 类型色 stroke（1px）；选中态 2px 主色描边（不放大，避免布局跳动）
 *   - 边：默认浅灰，主-主/主-活动等按语义着色
 *   - 二级工具栏（40px）：搜索 + L1 过滤 + 显隐 + 适应画布 + 刷新
 *   - 右侧属性面板 320：单击节点显示精简属性，"查看完整详情"开 Drawer 1100
 *   - ResizeObserver 自适应 + activeMenuKey 激活刷新（解决页签隐藏后尺寸塌陷）
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import G6 from '@antv/g6';
import { Button, Spin, message, Select, Drawer, Typography, Modal, Descriptions, Tooltip } from 'antd';
import { SyncOutlined, CompressOutlined, CloseOutlined } from '@ant-design/icons';
import { useStore } from '../store/useStore';
import { conceptApi } from '../services/api';
import ModelTreeManager from './ModelTreeManager';
import { tokens, entitySemanticColors } from '../theme/tokens';
import { StatusTag } from './shell';

const { Text } = Typography;

// 实体类型语义色：取 chartPalette（设计 C34：画布节点配色走图表色板，禁止零散硬编码）
// 主数据=蓝(chart1) / 活动实体=teal(chart3) / 数据实体=红(chart6)
const ENTITY_CATEGORY_META: Record<string, { label: string; stroke: string }> = {
  master_entity: { label: '主数据实体', stroke: tokens.chartPalette[0] },
  activity_entity: { label: '业务活动实体', stroke: tokens.chartPalette[2] },
  data_entity: { label: '数据实体', stroke: tokens.chartPalette[5] },
};

// 关系边语义色
const EDGE_COLORS: Record<string, string> = {
  default: tokens.colors.border,
  crossChain: tokens.colors.ai,
  masterMaster: tokens.colors.primary,
  masterActivity: tokens.colors.error,
  other: tokens.colors.warning,
};

type GraphNodeModel = {
  type?: string;
  label?: string;
  entity_category?: string;
  entity_code?: string;
  entity_en_name?: string;
  landing_table_en_name?: string;
  id?: string;
  entity_id?: string;
  entity_name?: string;
  concept_id?: string;
  properties_schema?: any[];
  entity_explanation?: string;
  description?: string;
  is_main_table?: boolean;
  data_layer?: string;
  sort_order?: number;
  level?: number;
};

const ForceCanvas: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const graphDataRef = useRef<any>(null);
  const [loading, setLoading] = useState(false);
  const [graphReady, setGraphReady] = useState(false);
  const [showEntities, setShowEntities] = useState(true);
  const [showConcepts, setShowConcepts] = useState(true);
  const [graphData, setGraphData] = useState<any>(null);
  const [l1Ids, setL1Ids] = useState<string[]>([]);
  const [l1Options, setL1Options] = useState<{ label: string; value: string }[]>([]);
  // 右侧属性面板：单击节点显示精简属性
  const [panelNode, setPanelNode] = useState<any | null>(null);
  // Drawer：完整详情（点"查看完整详情"按钮打开）
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerEntityId, setDrawerEntityId] = useState<string | null>(null);
  const [drawerEntityName, setDrawerEntityName] = useState<string>('');
  const [drawerMode, setDrawerMode] = useState<'master' | 'activity'>('master');
  const [drawerConcept, setDrawerConcept] = useState<any | null>(null);
  const [relModalOpen, setRelModalOpen] = useState(false);
  const [relModalData, setRelModalData] = useState<any | null>(null);
  const setSelectedNode = useStore((state) => state.setSelectedNode);
  const activeMenuKey = useStore((state) => state.activeMenuKey);
  const [searchValue, setSearchValue] = useState<string>('');
  const highlightedRef = useRef<string | null>(null);
  const clickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const entityOptions = useMemo(() => {
    const nodes = (graphData?.nodes || []).filter((n: any) => n.type === 'entity');
    return nodes.map((n: any) => ({
      label: `${n.entity_name || n.label || '-'}（${n.entity_code || '-'}）`,
      value: String(n.id),
      name: n.entity_name || n.label || '',
      code: n.entity_code || '',
      enName: n.entity_en_name || '',
    }));
  }, [graphData]);

  // 焦点视图：以目标实体为中心重排整图--radial 布局；非邻居节点/边 dim 变暗
  const focusEntityView = (nodeId: string) => {
    const graph = graphRef.current;
    if (!graph) return;
    const target = graph.findById(nodeId);
    if (!target) return;
    if (highlightedRef.current && highlightedRef.current !== String(nodeId)) {
      const prev = graph.findById(highlightedRef.current);
      if (prev) graph.setItemState(prev, 'highlight', false);
    }
    // 计算邻居节点集合（含目标本身）
    const neighborIds = new Set<string>([String(nodeId)]);
    graph.getEdges().forEach((e: any) => {
      const model = e.getModel();
      if (model.source === nodeId) neighborIds.add(String(model.target));
      if (model.target === nodeId) neighborIds.add(String(model.source));
    });
    // 非邻居节点/边 dim 变暗，邻居保持正常
    graph.getNodes().forEach((n: any) => {
      const isNeighbor = neighborIds.has(String(n.getID()));
      graph.setItemState(n, 'dim', !isNeighbor);
      graph.setItemState(n, 'highlight', n === target);
    });
    graph.getEdges().forEach((e: any) => {
      const model = e.getModel();
      const isRelated = neighborIds.has(String(model.source)) && neighborIds.has(String(model.target));
      graph.setItemState(e, 'dim', !isRelated);
    });
    highlightedRef.current = String(nodeId);
    graph.updateLayout({
      type: 'radial',
      focusNode: nodeId,
      unitRadius: 130,
      linkDistance: 100,
      preventOverlap: true,
      nodeSize: 40,
      nodeSpacing: 18,
    });
    graph.layout();
    setTimeout(() => {
      if (!graphRef.current) return;
      const t = graphRef.current.findById(nodeId);
      if (t) graphRef.current.focusItem(t, true, { easing: 'easeCubic', duration: 500 });
      setTimeout(() => { if (graphRef.current) graphRef.current.zoomTo(1.0, undefined, true); }, 350);
    }, 650);
  };

  // 退出焦点视图：清除状态，切回 force 力导布局，全图 fitView
  const resetGraphView = () => {
    const graph = graphRef.current;
    if (!graph) return;
    graph.getNodes().forEach((n: any) => {
      graph.setItemState(n, 'highlight', false);
      graph.setItemState(n, 'dim', false);
    });
    graph.getEdges().forEach((e: any) => graph.setItemState(e, 'dim', false));
    highlightedRef.current = null;
    graph.updateLayout({
      type: 'force',
      preventOverlap: true,
      linkDistance: 150,
      nodeStrength: -50,
    });
    graph.layout();
    setTimeout(() => { if (graphRef.current) graphRef.current.fitView(20); }, 650);
  };

  const fetchGraphData = async (selectedL1Ids?: string[]) => {
    const ids = selectedL1Ids ?? l1Ids;
    setLoading(true);
    try {
      let response: any;
      if (ids && ids.length > 0) {
        if (ids.length === 1) {
          response = await conceptApi.getSubgraphByL1(ids[0]);
        } else {
          // 多选：并行拉取各 L1 子图后按 id 合并去重
          const responses = await Promise.all(ids.map((id) => conceptApi.getSubgraphByL1(id)));
          const nodeMap = new Map<string, any>();
          const edgeMap = new Map<string, any>();
          for (const sub of responses) {
            for (const n of sub.data?.nodes || []) if (!nodeMap.has(String(n.id))) nodeMap.set(String(n.id), n);
            for (const e of sub.data?.edges || []) {
              const key = String(e.id) || `${e.source}|${e.target}|${e.edge_type || ''}`;
              if (!edgeMap.has(key)) edgeMap.set(key, e);
            }
          }
          response = { data: { nodes: Array.from(nodeMap.values()), edges: Array.from(edgeMap.values()) } };
        }
      } else {
        response = await conceptApi.getGraphData();
      }
      setGraphData(response.data);
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
      message.error('获取图谱数据失败，请检查服务状态');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const resp = await conceptApi.getConcepts(1);
        const list = resp.data || [];
        const opts = list.map((c: any) => ({
          label: c.name || c.label || '-',
          value: c.id || '',
        })).filter((o: any) => o.value);
        setL1Options(opts);
      } catch (e) {
        // 静默回退
      }
    })();
  }, []);

  useEffect(() => {
    fetchGraphData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 图谱实例初始化
  useEffect(() => {
    if (!containerRef.current) return;

    if (!graphRef.current) {
      const graph = new G6.Graph({
        container: containerRef.current,
        width: containerRef.current.scrollWidth || 800,
        height: containerRef.current.scrollHeight || 800,
        // B3 美化：右下小地图（G6 内置 Minimap，零新依赖；位置由 index.css .g6-minimap 固定）
        plugins: [new G6.Minimap({ size: [180, 120], type: 'delegate' })],
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node', {
            type: 'tooltip',
            formatText(model: GraphNodeModel) {
              if (model.type === 'entity') {
                const entityCategory = model.entity_category || 'data_entity';
                const entityMeta = ENTITY_CATEGORY_META[entityCategory] || ENTITY_CATEGORY_META.data_entity;
                return `名称: ${model.label}<br/>类型: ${entityMeta.label}<br/>唯一编码: ${model.entity_code || '-'}<br/>落地英文表名: ${model.entity_en_name || model.landing_table_en_name || '-'}`;
              }
              return `名称: ${model.label}<br/>类型: 概念分类节点`;
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
          color: EDGE_COLORS.default,
          style: {
            endArrow: {
              path: G6.Arrow.triangle(5, 5, 2),
              fill: EDGE_COLORS.default,
            },
          },
          labelCfg: {
            autoRotate: true,
            style: {
              fontSize: 10,
            },
          },
        },
        // 选中态：2px 主色描边 + 4px 外发光（B3 美化）；暗化态：低透明度
        nodeStateStyles: {
          highlight: { stroke: tokens.colors.primary, lineWidth: 2, shadowColor: tokens.colors.primary, shadowBlur: 8 },
          dim: { opacity: 0.12 },
        },
        edgeStateStyles: {
          dim: { opacity: 0.08 },
        },
      });

      graph.on('node:click', (evt: any) => {
        const { item } = evt;
        const model = item.get('model');
        setSelectedNode(model);
        // 单击延迟显示右侧属性面板；若随后的双击在 250ms 内到来，则取消，改为焦点视图
        if (clickTimerRef.current) clearTimeout(clickTimerRef.current);
        clickTimerRef.current = setTimeout(() => {
          setPanelNode(model);
        }, 250);
      });

      graph.on('node:dblclick', (evt: any) => {
        const { item } = evt;
        const model = item.get('model');
        if (model.type !== 'entity') return;
        if (clickTimerRef.current) { clearTimeout(clickTimerRef.current); clickTimerRef.current = null; }
        const nid = String(item.getID());
        setSearchValue(nid);
        focusEntityView(nid);
      });

      graph.on('edge:click', (evt: any) => {
        const { item } = evt;
        const model = item.get('model');
        const edgeType = model.edge_type;
        if (edgeType !== 'entity_relation' && edgeType !== 'entity_generation') return;
        // 用 ref 取最新 graphData（避免闭包陈旧）
        const nodeMap: Map<string, any> = new Map(
          (graphDataRef.current?.nodes || []).map((n: any) => [String(n.id), n])
        );
        const srcNode = nodeMap.get(String(model.source));
        const tgtNode = nodeMap.get(String(model.target));
        setRelModalData({
          relation_name: model.relation_name || model.label,
          relation_category: model.relation_category || (edgeType === 'entity_generation' ? '打点维护' : '手工维护'),
          source_entity: srcNode?.entity_name || srcNode?.label || model.source,
          target_entity: tgtNode?.entity_name || tgtNode?.label || model.target,
          direction: model.direction || 'forward',
          cardinality: model.cardinality || 'N:N',
          source_field_name: model.source_field_name,
          target_field_name: model.target_field_name,
          join_expr: model.join_expr,
          description: model.description,
          remark: model.remark,
        });
        setRelModalOpen(true);
      });

      // 缩放级标签显隐：zoom < 0.6 时隐藏标签，减少视觉拥挤
      let labelHidden = false;
      graph.on('viewportchange', () => {
        const zoom = graph.getZoom();
        if (zoom < 0.6 && !labelHidden) {
          labelHidden = true;
          graph.getNodes().forEach((node: any) => {
            const group = node.getContainer();
            const children = group.get('children') || [];
            children.forEach((shape: any) => {
              if (shape.get('type') === 'text') shape.hide();
            });
          });
        } else if (zoom >= 0.6 && labelHidden) {
          labelHidden = false;
          graph.getNodes().forEach((node: any) => {
            const group = node.getContainer();
            const children = group.get('children') || [];
            children.forEach((shape: any) => {
              if (shape.get('type') === 'text') shape.show();
            });
          });
        }
      });

      graphRef.current = graph;
      setGraphReady(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setSelectedNode, graphData]);

  // 保持 graphDataRef 与最新 graphData 同步（供 edge:click 回调用）
  useEffect(() => {
    graphDataRef.current = graphData;
  }, [graphData]);

  // ResizeObserver：容器尺寸变化时同步画布
  useEffect(() => {
    if (!graphReady || !containerRef.current) return;
    const container = containerRef.current;
    const ro = new ResizeObserver(() => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w > 0 && h > 0 && graphRef.current) {
        graphRef.current.changeSize(w, h);
      }
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, [graphReady]);

  // 页签激活时刷新画布尺寸（KeepAlive display:none 恢复后尺寸可能为 0）
  useEffect(() => {
    if (activeMenuKey === 'graph' && graphRef.current && containerRef.current) {
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      if (w > 0 && h > 0) graphRef.current.changeSize(w, h);
    }
  }, [activeMenuKey]);

  // 当数据或过滤条件变化时，更新图谱
  useEffect(() => {
    setSearchValue('');
    highlightedRef.current = null;
    if (graphRef.current && graphData) {
      const { nodes, edges } = graphData;
      const conceptLevelMap = new Map(
        nodes
          .filter((n: any) => n.type === 'concept')
          .map((n: any) => [String(n.id), n.level])
      );

      const filteredNodes = nodes.filter((n: any) => {
        if (n.type === 'entity' && !showEntities) return false;
        if (n.type === 'concept' && !showConcepts) return false;
        return true;
      });

      const filteredNodeIds = new Set(filteredNodes.map((n: any) => n.id));
      const filteredEdges = edges.filter((e: any) =>
        filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
      );

      const processedNodes = filteredNodes.map((n: any) => {
        const displayName = n.type === 'concept' && n.level ? `L${n.level} ${n.label}` : n.label;
        const conceptLevel =
          n.type === 'entity' && n.concept_id
            ? conceptLevelMap.get(String(n.concept_id))
            : undefined;
        const entityCategory =
          n.type === 'entity'
            ? (n.entity_category || (conceptLevel === 2 ? 'master_entity' : conceptLevel === 4 ? 'activity_entity' : 'data_entity'))
            : undefined;
        const entityMeta = ENTITY_CATEGORY_META[entityCategory || 'data_entity'] || ENTITY_CATEGORY_META.data_entity;
        return {
          ...n,
          label: displayName,
          style: {
            fill: n.type === 'concept' ? tokens.colors.primaryBg : tokens.colors.bgContent,
            stroke: n.type === 'concept' ? tokens.colors.primary : entityMeta.stroke,
            lineWidth: 1,
          },
          size: 40,
          entity_category: entityCategory,
        };
      });
      const nodeCatMap = new Map<string, string | undefined>(
        processedNodes.map((n: any) => [String(n.id), n.entity_category])
      );
      const processedData = {
        nodes: processedNodes,
        edges: filteredEdges.map((e: any) => {
          const isEntityRel = e.edge_type === 'entity_relation';
          const isCrossChain = e.edge_type === 'concept_cross_chain';
          const isEntityGen = e.edge_type === 'entity_generation';
          let edgeColor: string = EDGE_COLORS.default;
          let edgeWidth = 1;
          if (isCrossChain) {
            edgeColor = EDGE_COLORS.crossChain; edgeWidth = 2;
          } else if (isEntityRel || isEntityGen) {
            const srcCat = nodeCatMap.get(String(e.source));
            const tgtCat = nodeCatMap.get(String(e.target));
            const isMaster = (c: string | undefined) => c === 'master_entity';
            const isActivity = (c: string | undefined) => c === 'activity_entity';
            if (isMaster(srcCat) && isMaster(tgtCat)) {
              edgeColor = EDGE_COLORS.masterMaster; edgeWidth = 2.5;
            } else if ((isMaster(srcCat) && isActivity(tgtCat)) || (isActivity(srcCat) && isMaster(tgtCat))) {
              edgeColor = EDGE_COLORS.masterActivity; edgeWidth = 2.5;
            } else {
              edgeColor = EDGE_COLORS.other; edgeWidth = 2;
            }
          }
          const fullLabel = e.label || '';
          const edgeLabel = fullLabel.length > 5 ? fullLabel.slice(0, 5) + '…' : fullLabel;
          return {
            ...e,
            label: edgeLabel,
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
                fill: edgeColor,
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
      graphRef.current.updateLayout({ type: 'force', preventOverlap: true, linkDistance: 150, nodeStrength: -50 });
      graphRef.current.layout();
    }
  }, [graphData, showEntities, showConcepts]);

  const handleL1Change = (ids: string[]) => {
    const next = ids || [];
    setL1Ids(next);
    fetchGraphData(next);
  };

  // 右侧面板"查看完整详情" -> 打开 Drawer 1100
  const openFullDetail = () => {
    if (!panelNode) return;
    if (panelNode.type === 'entity' && (panelNode.entity_id || panelNode.id)) {
      setDrawerConcept(null);
      setDrawerEntityId(panelNode.entity_id || panelNode.id);
      setDrawerEntityName(panelNode.entity_name || panelNode.label || '实体详情');
      setDrawerMode(panelNode.entity_category === 'activity_entity' ? 'activity' : 'master');
      setDrawerOpen(true);
    } else if (panelNode.type === 'concept') {
      setDrawerEntityId(null);
      setDrawerConcept({ label: panelNode.label, level: panelNode.level, description: panelNode.description });
      setDrawerOpen(true);
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 画布 + 右侧属性面板（B3：浮动玻璃工具条 + 图例 + 小地图浮在画布上，画布满撑） */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        <div style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}>
          {/* B3 美化：点阵网格背景（radial-gradient 1px 点 / 24px 间距） */}
          <div
            ref={containerRef}
            style={{
              width: '100%', height: '100%',
              backgroundColor: tokens.colors.bgPage,
              backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(15,23,42,0.07) 1px, transparent 0)',
              backgroundSize: '24px 24px',
            }}
          />
          {loading ? (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: `${tokens.colors.bgContent}CC`,
                zIndex: 30,
              }}
            >
              <Spin />
            </div>
          ) : null}
          {/* B3 美化：浮动玻璃工具条（S2 阴影 + blur(8px) + radius.card） */}
          <div
            style={{
              position: 'absolute', top: 12, left: 12, zIndex: 20,
              display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: tokens.space.s2,
              padding: '6px 10px', borderRadius: tokens.radius.card,
              background: 'rgba(255,255,255,.88)',
              WebkitBackdropFilter: 'blur(8px)', backdropFilter: 'blur(8px)',
              boxShadow: tokens.elevation.s2, border: `1px solid ${tokens.colors.border}`,
              maxWidth: 'calc(100% - 24px)',
            }}
          >
        <Select
          showSearch
          allowClear
          size="small"
          style={{ minWidth: 240 }}
          placeholder="搜索实体名称 / 编码 / 英文名"
          value={searchValue || undefined}
          options={entityOptions}
          filterOption={(input, option: any) => {
            const kw = input.toLowerCase().trim();
            if (!kw) return true;
            return [option?.name, option?.code, option?.enName].some((v) =>
              String(v || '').toLowerCase().includes(kw)
            );
          }}
          onChange={(value: string) => {
            setSearchValue(value || '');
            if (value) focusEntityView(value);
            else resetGraphView();
          }}
          onClear={() => {
            setSearchValue('');
            resetGraphView();
          }}
        />
        <Select
          mode="multiple"
          showSearch
          allowClear
          size="small"
          style={{ minWidth: 220, maxWidth: 360 }}
          placeholder="按 L1 行业域过滤（可多选）"
          value={l1Ids}
          onChange={handleL1Change}
          options={l1Options}
          maxTagCount="responsive"
        />
        <Button
          size="small"
          type={showConcepts ? 'primary' : 'default'}
          onClick={() => setShowConcepts(!showConcepts)}
        >
          概念
        </Button>
        <Button
          size="small"
          type={showEntities ? 'primary' : 'default'}
          onClick={() => setShowEntities(!showEntities)}
        >
          实体
        </Button>
        <Tooltip title="适应画布">
          <Button
            size="small"
            icon={<CompressOutlined />}
            onClick={() => { if (graphRef.current) graphRef.current.fitView(20); }}
          />
        </Tooltip>
        <Button size="small" icon={<SyncOutlined />} onClick={() => fetchGraphData()}>刷新</Button>
          </div>
          {/* 三轨M8(U3) §4.1：图例并入右下悬浮卡（与小地图同区；概念=语义紫） */}
          <div
            style={{
              position: 'absolute', right: 12, bottom: 12, zIndex: 20,
              padding: '8px 12px', borderRadius: tokens.radius.card,
              background: 'rgba(255,255,255,.9)',
              WebkitBackdropFilter: 'blur(8px)', backdropFilter: 'blur(8px)',
              boxShadow: tokens.elevation.s1, border: `1px solid ${tokens.colors.border}`,
            }}
          >
            <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>图例</Text>
            {(['master_entity', 'activity_entity', 'data_entity'] as const).map((cat) => (
              <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: tokens.colors.textSecondary, lineHeight: '20px' }}>
                <span style={{ width: 10, height: 10, borderRadius: 3, border: `2px solid ${(ENTITY_CATEGORY_META[cat] || ENTITY_CATEGORY_META.data_entity).stroke}`, background: tokens.colors.bgContent, flexShrink: 0 }} />
                {(ENTITY_CATEGORY_META[cat] || ENTITY_CATEGORY_META.data_entity).label}
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: tokens.colors.textSecondary, lineHeight: '20px' }}>
              <span style={{ width: 10, height: 10, borderRadius: 3, border: `2px solid ${tokens.entitySemanticColors.concept}`, background: tokens.colors.primaryBg, flexShrink: 0 }} />
              概念分类
            </div>
          </div>
        </div>

        {/* 右侧属性面板 320 */}
        {panelNode ? (
          <div
            style={{
              width: 320,
              flexShrink: 0,
              borderLeft: `1px solid ${tokens.colors.border}`,
              background: tokens.colors.bgContent,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: `${tokens.space.s3}px ${tokens.space.s4}px`,
                borderBottom: `1px solid ${tokens.colors.border}`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexShrink: 0,
              }}
            >
              <Text strong style={{ fontSize: tokens.fontSize.body }}>节点属性</Text>
              <CloseOutlined
                style={{ cursor: 'pointer', color: tokens.colors.textTertiary, fontSize: 12 }}
                onClick={() => setPanelNode(null)}
              />
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: tokens.space.s4 }}>
              <Descriptions column={1} size="small" labelStyle={{ width: 72 }}>
                <Descriptions.Item label="名称">{panelNode.label || '-'}</Descriptions.Item>
                <Descriptions.Item label="类型">
                  {panelNode.type === 'concept'
                    ? '概念分类'
                    : (ENTITY_CATEGORY_META[panelNode.entity_category]?.label || '实体')}
                </Descriptions.Item>
                {panelNode.type === 'entity' ? (
                  <>
                    <Descriptions.Item label="编码">{panelNode.entity_code || '-'}</Descriptions.Item>
                    <Descriptions.Item label="落地表">
                      {panelNode.entity_en_name || panelNode.landing_table_en_name || '-'}
                    </Descriptions.Item>
                  </>
                ) : null}
                {panelNode.level ? (
                  <Descriptions.Item label="层级">L{panelNode.level}</Descriptions.Item>
                ) : null}
              </Descriptions>
              {panelNode.description ? (
                <div style={{ marginTop: tokens.space.s3, fontSize: tokens.fontSize.caption, color: tokens.colors.textTertiary }}>
                  {panelNode.description}
                </div>
              ) : null}
              {panelNode.type === 'entity' ? (
                <Button type="primary" block style={{ marginTop: tokens.space.s4 }} onClick={openFullDetail}>
                  查看完整详情
                </Button>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>

      {/* 完整详情 Drawer（复用主数据维护同款组件） */}
      <Drawer
        title={drawerEntityId ? drawerEntityName : (drawerConcept?.label || '节点详情')}
        placement="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={1100}
        destroyOnHidden
      >
        {drawerEntityId ? (
          <ModelTreeManager
            mode={drawerMode}
            pageTitle={drawerEntityName}
            readOnly
            embedded
            initialEntityId={drawerEntityId}
          />
        ) : drawerConcept ? (
          <div style={{ padding: tokens.space.s4 }}>
            <StatusTag preset="info">概念分类节点</StatusTag>
            {drawerConcept.level ? (
              <div style={{ marginTop: tokens.space.s2, color: tokens.colors.textSecondary }}>
                层级: L{drawerConcept.level}
              </div>
            ) : null}
            <div style={{ marginTop: tokens.space.s2, color: tokens.colors.textTertiary, fontSize: tokens.fontSize.caption }}>
              {drawerConcept.description || '暂无描述'}
            </div>
          </div>
        ) : null}
      </Drawer>

      {/* 关系详情弹窗（点击实体间关系边） */}
      <Modal
        title="关系详情"
        open={relModalOpen}
        onCancel={() => setRelModalOpen(false)}
        footer={null}
        width={700}
      >
        {relModalData && (
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="关系名称" span={2}>{relModalData.relation_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="维护类别">
              <StatusTag preset={relModalData.relation_category === '打点维护' ? 'ai' : 'info'}>
                {relModalData.relation_category || '-'}
              </StatusTag>
            </Descriptions.Item>
            <Descriptions.Item label="方向">{relModalData.direction || '-'}</Descriptions.Item>
            <Descriptions.Item label="源实体">{relModalData.source_entity}</Descriptions.Item>
            <Descriptions.Item label="目标实体">{relModalData.target_entity}</Descriptions.Item>
            <Descriptions.Item label="基数">{relModalData.cardinality || '-'}</Descriptions.Item>
            <Descriptions.Item label="源字段">{relModalData.source_field_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="目标字段">{relModalData.target_field_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="关联说明" span={2}>{relModalData.join_expr || '-'}</Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>{relModalData.description || '-'}</Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>{relModalData.remark || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default ForceCanvas;
