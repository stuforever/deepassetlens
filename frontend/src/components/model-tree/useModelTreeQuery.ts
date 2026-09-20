/**
 * useModelTreeQuery —— 模型树数据加载 + 选择/展开 + 关系过滤状态
 *
 * 从 ModelTreeManager 抽离：owned 状态 = 数据(concepts/allEntities/relationRows/loading/loadingDetail)
 * + 选择(selectedKey/expandedKeys) + 关系过滤(relationFilter) + refreshData + 初始加载效果。
 * 容器仍负责：metaMap/selectedMeta 派生、建模跳转效果、关系高亮效果、详情加载效果、全部 CRUD 业务。
 */
import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { message } from 'antd';
import { conceptApi, entityApi } from '../../services/api';
import { buildTree, findFirstKey, type Mode } from './modelTree';

type ModelTreeQueryConfig = {
  includeLevel0: boolean;
  levels: number[];
};

export type ModelTreeQuery = {
  loading: boolean;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  concepts: any[];
  setConcepts: React.Dispatch<React.SetStateAction<any[]>>;
  allEntities: any[];
  setAllEntities: React.Dispatch<React.SetStateAction<any[]>>;
  selectedKey: string | null;
  setSelectedKey: React.Dispatch<React.SetStateAction<string | null>>;
  expandedKeys: string[];
  setExpandedKeys: React.Dispatch<React.SetStateAction<string[]>>;
  relationRows: any[];
  setRelationRows: React.Dispatch<React.SetStateAction<any[]>>;
  loadingDetail: boolean;
  setLoadingDetail: React.Dispatch<React.SetStateAction<boolean>>;
  relationFilter: 'all' | 'manual' | 'matrix';
  setRelationFilter: React.Dispatch<React.SetStateAction<'all' | 'manual' | 'matrix'>>;
  mergedRelations: any[];
  filteredRelations: any[];
  refreshData: (keepKey?: boolean) => Promise<void>;
};

export function useModelTreeQuery(args: { mode: Mode; config: ModelTreeQueryConfig; initialEntityId?: string }): ModelTreeQuery {
  const { mode, config, initialEntityId } = args;
  const [loading, setLoading] = useState(false);
  const [concepts, setConcepts] = useState<any[]>([]);
  const [allEntities, setAllEntities] = useState<any[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [relationRows, setRelationRows] = useState<any[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [relationFilter, setRelationFilter] = useState<'all' | 'manual' | 'matrix'>('all');

  // 三轨M8 顺手修(:54)：过期响应防护——mode/config 快速变化或并发 refreshData 时，
  // 先发后至的旧响应不再覆盖新批次结果（请求序号守卫）。
  const requestSeqRef = useRef(0);
  const refreshData = useCallback(async (keepKey = true) => {
    const seq = ++requestSeqRef.current;
    setLoading(true);
    try {
      const [conceptRes, entityRes] = await Promise.all([
        conceptApi.getConcepts(undefined, config.includeLevel0),
        entityApi.listEntities(),
      ]);
      if (seq !== requestSeqRef.current) return; // 过期响应丢弃
      const allConcepts = conceptRes.data || [];
      const filteredConcepts = allConcepts.filter((item: any) => config.levels.includes(item.level));
      const entityItems = entityRes.data?.data?.items || [];
      setConcepts(filteredConcepts);
      setAllEntities(entityItems);

      // 顺手修（:64）：buildTree 单次调用解构（原两次全量建树）
      const { treeData: nextTree, metaMap: nextMetaMap } = buildTree(filteredConcepts, mode);
      const nextFirstKey = findFirstKey(nextTree);

      // 如果有 initialEntityId，定位到该实体并展开父节点
      let extraExpand: string | null = null;
      if (initialEntityId) {
        const targetKey = `entity-${initialEntityId}`;
        const meta = nextMetaMap.get(targetKey);
        if (meta?.parentConcept) {
          extraExpand = `concept-${meta.parentConcept.id}`;
        }
      }

      setExpandedKeys(() => {
        const base = nextTree.map((node: any) => node.key);
        if (extraExpand && !base.includes(extraExpand)) base.push(extraExpand);
        return base;
      });
      setSelectedKey((prev) => {
        if (initialEntityId) {
          const targetKey = `entity-${initialEntityId}`;
          if (nextMetaMap.has(targetKey)) return targetKey;
        }
        if (keepKey && prev && nextMetaMap.has(prev)) return prev;
        return nextFirstKey;
      });
    } catch (error) {
      console.error('[useModelTreeQuery] 加载建模数据失败:', error);
      message.error('加载建模数据失败');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.includeLevel0, config.levels.join(','), mode, initialEntityId]);

  useEffect(() => {
    refreshData(false);
  }, [mode, refreshData]);

  const mergedRelations = useMemo(() => {
    return [...(relationRows || [])]
      .map((relation: any) => ({
        ...relation,
        row_type: relation.relation_category === '打点维护' ? 'matrix' : 'manual',
      }))
      .sort((a: any, b: any) => {
        if (a.row_type === b.row_type) return String(a.relation_name || '').localeCompare(String(b.relation_name || ''), 'zh-CN');
        return a.row_type === 'manual' ? -1 : 1;
      });
  }, [relationRows]);
  const filteredRelations = useMemo(() => {
    if (relationFilter === 'manual') return mergedRelations.filter((item: any) => item.row_type === 'manual');
    if (relationFilter === 'matrix') return mergedRelations.filter((item: any) => item.row_type === 'matrix');
    return mergedRelations;
  }, [mergedRelations, relationFilter]);

  return {
    loading, setLoading,
    concepts, setConcepts,
    allEntities, setAllEntities,
    selectedKey, setSelectedKey,
    expandedKeys, setExpandedKeys,
    relationRows, setRelationRows,
    loadingDetail, setLoadingDetail,
    relationFilter, setRelationFilter,
    mergedRelations, filteredRelations,
    refreshData,
  };
}
