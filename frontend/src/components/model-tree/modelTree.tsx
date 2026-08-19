/**
 * modelTree.tsx —— 模型树（ModelTreeManager）纯工具层
 *
 * 从 ModelTreeManager.tsx 抽离的纯函数 + JSX 构建器，与 React 状态完全解耦。
 * 拆分依据：均为纯逻辑，输入输出确定，可在任意组件复用。
 */
import React from 'react';
import { Space, Tag, Typography } from 'antd';
import { ApartmentOutlined, DatabaseOutlined, TagsOutlined } from '@ant-design/icons';
import { StatusTag } from '../shell';

const { Text } = Typography;

export type Mode = 'master' | 'activity';

export type ExplanationSource = 'manual' | 'auto' | 'field';

export type ExplanationItem = {
  id: string;
  text: string;
  source: ExplanationSource;
};

export const LEVEL_LABELS: Record<number, string> = {
  0: '业务域',
  1: 'L1',
  2: 'L2',
  3: 'L3',
  4: 'L4',
};

export const getEntityCategoryLabel = (conceptLevel?: number) => {
  if (conceptLevel === 2) return '主数据实体';
  if (conceptLevel === 4) return '业务活动实体';
  return '数据实体';
};

export const getEntityCategoryPreset = (conceptLevel?: number): 'warning' | 'info' | 'default' => {
  if (conceptLevel === 2) return 'warning';
  if (conceptLevel === 4) return 'info';
  return 'default';
};

export const MODE_CONFIG: Record<Mode, any> = {
  master: {
    includeLevel0: false,
    levels: [1, 2],
    rootLevel: 1,
    rootCreateLabel: '新增 L1 概念分类',
    childLevelMap: { 1: 2 },
    leafLevel: 2,
    rootName: '主数据概念分类树',
  },
  activity: {
    includeLevel0: true,
    levels: [0, 3, 4],
    rootLevel: 0,
    rootCreateLabel: '新增业务域',
    childLevelMap: { 0: 3, 3: 4 },
    leafLevel: 4,
    rootName: '业务活动建模树',
  },
};

export const sortByDisplay = (items: any[]) =>
  [...items].sort((a: any, b: any) => {
    const areaDiff = (a.area_index || 0) - (b.area_index || 0);
    if (areaDiff !== 0) return areaDiff;
    const orderDiff = (a.sort_order || 0) - (b.sort_order || 0);
    if (orderDiff !== 0) return orderDiff;
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN');
  });

export const QUERY_ENTITY_PROPERTY_HINTS = ['编号', '编码', '名称', '证件', '地址', '类型', '状态', '单号', '申请', '记录'];

export const EXPLANATION_SOURCE_META: Record<ExplanationSource, { label: string; preset: 'info' | 'ai' }> = {
  manual: { label: '手工新增', preset: 'info' },
  auto: { label: '自动提取', preset: 'ai' },
  field: { label: '字段选择', preset: 'info' },
};

export const normalizeExplanationTerm = (value: any) => String(value || '').trim();

export const createExplanationItem = (text: string, source: ExplanationSource): ExplanationItem => ({
  id: `${source}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  text: normalizeExplanationTerm(text),
  source,
});

export const splitExplanationTerms = (value: any): string[] => {
  const raw = String(value || '').trim();
  if (!raw) return [];
  return Array.from(
    new Set(
      raw
        .split(/[,，、/|；;\n\r\t]+/)
        .map((item) => item.trim())
        .filter(Boolean)
    )
  );
};

export const mergeExplanationTerms = (...groups: any[]): string => {
  const allItems = groups.reduce<string[]>((acc, group) => {
    const nextItems = Array.isArray(group) ? group : splitExplanationTerms(group);
    return acc.concat(nextItems);
  }, []);
  const merged = Array.from(
    new Set(
      allItems
        .map((item) => String(item || '').trim())
        .filter(Boolean)
    )
  );
  return merged.join('，');
};

export const buildExplanationItems = (value: any, propertyKeywordOptions: string[] = []): ExplanationItem[] => {
  const fieldKeywordSet = new Set((propertyKeywordOptions || []).map((item) => normalizeExplanationTerm(item)).filter(Boolean));
  return splitExplanationTerms(value).map((item) =>
    createExplanationItem(item, fieldKeywordSet.has(normalizeExplanationTerm(item)) ? 'field' : 'manual')
  );
};

export const mergeExplanationItems = (
  currentItems: ExplanationItem[],
  nextTerms: string[],
  source: ExplanationSource,
  options?: { replaceSource?: boolean }
) => {
  const normalizedIncoming = splitExplanationTerms(nextTerms).map((item) => normalizeExplanationTerm(item)).filter(Boolean);
  const baseItems = options?.replaceSource ? currentItems.filter((item) => item.source !== source) : [...currentItems];
  const seen = new Set(baseItems.map((item) => normalizeExplanationTerm(item.text)));
  normalizedIncoming.forEach((term) => {
    if (seen.has(term)) return;
    baseItems.push(createExplanationItem(term, source));
    seen.add(term);
  });
  return baseItems;
};

export const serializeExplanationItems = (items: ExplanationItem[]) =>
  mergeExplanationTerms(items.map((item) => normalizeExplanationTerm(item.text)).filter(Boolean));

export const getPropertyKeywordOptions = (properties: any[] = []) => {
  const prioritized: string[] = [];
  const others: string[] = [];
  properties.forEach((prop: any) => {
    const label = String(
      prop?.cnName || prop?.label || prop?.display_name || prop?.name_zh || prop?.name || prop?.field_name || ''
    ).trim();
    if (!label) return;
    if (
      prop?.enable_query_entity ||
      prop?.is_alias_key ||
      prop?.is_key_attribute ||
      prop?.key_attribute ||
      prop?.keyword ||
      prop?.isPrimaryKey ||
      prop?.is_primary_key ||
      QUERY_ENTITY_PROPERTY_HINTS.some((hint) => label.includes(hint))
    ) {
      prioritized.push(label);
      return;
    }
    others.push(label);
  });
  return Array.from(new Set([...prioritized, ...others]));
};

export const buildTree = (concepts: any[], mode: Mode) => {
  const config = MODE_CONFIG[mode];
  const metaMap = new Map<string, any>();

  const buildEntityNode = (entity: any, parentConcept: any) => {
    const entityKey = `entity-${entity.id}`;
    const propertyChildren = (entity.properties_schema || []).map((prop: any, index: number) => {
      const propKey = `property-${entity.id}-${index}`;
      metaMap.set(propKey, {
        nodeType: 'property',
        property: prop,
        propertyIndex: index,
        entity,
        parentConcept,
      });
      return {
        key: propKey,
        title: (
          <Space size={6}>
            <TagsOutlined style={{ color: 'var(--color-ai)' }} />
            <span>{prop.cnName || prop.name || `属性${index + 1}`}</span>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {prop.name || '-'}
            </Text>
          </Space>
        ),
        children: [],
      };
    });

    metaMap.set(entityKey, {
      nodeType: 'entity',
      entity,
      parentConcept,
    });

    return {
      key: entityKey,
      title: (
        <Space size={6}>
          <DatabaseOutlined style={{ color: parentConcept.level === 4 ? '#13c2c2' : 'var(--color-warning)' }} />
          <span>{entity.entity_name}</span>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {entity.entity_code}
          </Text>
          <StatusTag preset={getEntityCategoryPreset(parentConcept.level)}>{getEntityCategoryLabel(parentConcept.level)}</StatusTag>
          {entity.is_main_table ? <StatusTag preset="info">主表</StatusTag> : null}
        </Space>
      ),
      children: propertyChildren,
    };
  };

  const buildConceptNode = (concept: any): any => {
    metaMap.set(`concept-${concept.id}`, {
      nodeType: 'concept',
      concept,
    });

    const childConceptNodes = sortByDisplay(
      concepts.filter((item: any) => item.parent_id === concept.id && config.levels.includes(item.level))
    ).map((child: any) => buildConceptNode(child));

    const entityNodes =
      concept.level === config.leafLevel
        ? [...(concept.entities || [])]
            .sort((a: any, b: any) => {
              const orderDiff = (a.sort_order || 0) - (b.sort_order || 0);
              if (orderDiff !== 0) return orderDiff;
              return String(a.entity_name || '').localeCompare(String(b.entity_name || ''), 'zh-CN');
            })
            .map((entity: any) => buildEntityNode(entity, concept))
        : [];

    return {
      key: `concept-${concept.id}`,
      title: (
        <Space size={6}>
          <ApartmentOutlined style={{ color: concept.level === config.rootLevel ? 'var(--color-primary)' : 'var(--color-success)' }} />
          <span>{concept.name}</span>
          <Tag>{LEVEL_LABELS[concept.level] || `L${concept.level}`}</Tag>
        </Space>
      ),
      children: [...childConceptNodes, ...entityNodes],
    };
  };

  const rootNodes = sortByDisplay(concepts.filter((item: any) => item.level === config.rootLevel)).map((concept: any) =>
    buildConceptNode(concept)
  );

  return { treeData: rootNodes, metaMap };
};

export const findFirstKey = (treeData: any[]): string | null => {
  if (!treeData.length) return null;
  return treeData[0].key;
};
