import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Layout,
  Card,
  Tree,
  Space,
  Button,
  Tag,
  Descriptions,
  Empty,
  Table,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  message,
  List,
  Popconfirm,
  Typography,
  Spin,
  Upload,
  Badge,
  Segmented,
  Tabs,
  Radio,
  Checkbox,
  Tooltip,
} from 'antd';
import { StatusTag } from './shell';
import {
  ApartmentOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  ExportOutlined,
  EyeOutlined,
  ImportOutlined,
  LinkOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  TagsOutlined,
} from '@ant-design/icons';
import { conceptApi, entityApi, entityRelationManagerApi, mappingApi, kgApi } from '../services/api';
import axios from 'axios';
import { useStore } from '../store/useStore';

const { Sider, Content } = Layout;
const { Text } = Typography;

type Mode = 'master' | 'activity';

type Props = {
  mode: Mode;
  pageTitle: string;
  readOnly?: boolean;
  embedded?: boolean;
  onOpenTarget?: (menuKey: string) => void;
  initialEntityId?: string;  // 图谱抽屉传入：自动定位到该实体
};

type ExplanationSource = 'manual' | 'auto' | 'field';

type ExplanationItem = {
  id: string;
  text: string;
  source: ExplanationSource;
};

const LEVEL_LABELS: Record<number, string> = {
  0: '业务域',
  1: 'L1',
  2: 'L2',
  3: 'L3',
  4: 'L4',
};

const getEntityCategoryLabel = (conceptLevel?: number) => {
  if (conceptLevel === 2) return '主数据实体';
  if (conceptLevel === 4) return '业务活动实体';
  return '数据实体';
};

const getEntityCategoryPreset = (conceptLevel?: number): 'warning' | 'info' | 'default' => {
  if (conceptLevel === 2) return 'warning';
  if (conceptLevel === 4) return 'info';
  return 'default';
};

const MODE_CONFIG: Record<Mode, any> = {
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

const sortByDisplay = (items: any[]) =>
  [...items].sort((a: any, b: any) => {
    const areaDiff = (a.area_index || 0) - (b.area_index || 0);
    if (areaDiff !== 0) return areaDiff;
    const orderDiff = (a.sort_order || 0) - (b.sort_order || 0);
    if (orderDiff !== 0) return orderDiff;
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN');
  });

const QUERY_ENTITY_PROPERTY_HINTS = ['编号', '编码', '名称', '证件', '地址', '类型', '状态', '单号', '申请', '记录'];

const EXPLANATION_SOURCE_META: Record<ExplanationSource, { label: string; preset: 'info' | 'ai' }> = {
  manual: { label: '手工新增', preset: 'info' },
  auto: { label: '自动提取', preset: 'ai' },
  field: { label: '字段选择', preset: 'info' },
};

const normalizeExplanationTerm = (value: any) => String(value || '').trim();

const createExplanationItem = (text: string, source: ExplanationSource): ExplanationItem => ({
  id: `${source}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  text: normalizeExplanationTerm(text),
  source,
});

const splitExplanationTerms = (value: any): string[] => {
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

const mergeExplanationTerms = (...groups: any[]): string => {
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

const buildExplanationItems = (value: any, propertyKeywordOptions: string[] = []): ExplanationItem[] => {
  const fieldKeywordSet = new Set((propertyKeywordOptions || []).map((item) => normalizeExplanationTerm(item)).filter(Boolean));
  return splitExplanationTerms(value).map((item) =>
    createExplanationItem(item, fieldKeywordSet.has(normalizeExplanationTerm(item)) ? 'field' : 'manual')
  );
};

const mergeExplanationItems = (
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

const serializeExplanationItems = (items: ExplanationItem[]) =>
  mergeExplanationTerms(items.map((item) => normalizeExplanationTerm(item.text)).filter(Boolean));

const getPropertyKeywordOptions = (properties: any[] = []) => {
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

const buildTree = (concepts: any[], mode: Mode) => {
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

const findFirstKey = (treeData: any[]): string | null => {
  if (!treeData.length) return null;
  return treeData[0].key;
};

const ModelTreeManager: React.FC<Props> = ({ mode, pageTitle, readOnly = false, embedded = false, onOpenTarget, initialEntityId }) => {
  const config = MODE_CONFIG[mode];
  const { relationHighlight, modelingInitialKey, setMappingFilterEntityId, setMappingJumpTab } = useStore();
  const [loading, setLoading] = useState(false);
  const [concepts, setConcepts] = useState<any[]>([]);
  const [allEntities, setAllEntities] = useState<any[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [relationRows, setRelationRows] = useState<any[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const [conceptModalVisible, setConceptModalVisible] = useState(false);
  const [conceptModalMode, setConceptModalMode] = useState<'create' | 'edit'>('create');
  const [conceptForm] = Form.useForm();
  const conceptFormLevel = Form.useWatch('level', conceptForm);

  const [entityModalVisible, setEntityModalVisible] = useState(false);
  const [editingEntity, setEditingEntity] = useState<any>(null);
  const [entityTargetConcept, setEntityTargetConcept] = useState<any>(null);
  const [entityForm] = Form.useForm();
  const [explanationKeywordModalVisible, setExplanationKeywordModalVisible] = useState(false);
  const [selectedExplanationKeywords, setSelectedExplanationKeywords] = useState<string[]>([]);
  const [loadingExplanationSuggest, setLoadingExplanationSuggest] = useState(false);
  const [explanationItems, setExplanationItems] = useState<ExplanationItem[]>([]);
  const [newManualExplanation, setNewManualExplanation] = useState('');

  const [propertyModalVisible, setPropertyModalVisible] = useState(false);
  const [editingPropertyIndex, setEditingPropertyIndex] = useState<number | null>(null);
  const [propertyTargetEntity, setPropertyTargetEntity] = useState<any>(null);
  const [propertyForm] = Form.useForm();

  const [relationFilter, setRelationFilter] = useState<'all' | 'manual' | 'matrix'>('all');

  const { treeData, metaMap } = useMemo(() => buildTree(concepts, mode), [concepts, mode]);
  const selectedMeta = selectedKey ? metaMap.get(selectedKey) : null;

  // 新增：监听 modelingInitialKey 变化，自动跳转到对应节点
  useEffect(() => {
    if (modelingInitialKey && metaMap.has(modelingInitialKey)) {
      setSelectedKey(modelingInitialKey);
      // 同时确保父节点展开
      const keysToExpand = [...expandedKeys];
      if (!keysToExpand.includes(modelingInitialKey)) {
        keysToExpand.push(modelingInitialKey);
      }
      setExpandedKeys(keysToExpand);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelingInitialKey, metaMap]);
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

  const refreshData = useCallback(async (keepKey = true) => {
    setLoading(true);
    try {
      const [conceptRes, entityRes] = await Promise.all([
        conceptApi.getConcepts(undefined, config.includeLevel0),
        entityApi.listEntities(),
      ]);
      const allConcepts = conceptRes.data || [];
      const filteredConcepts = allConcepts.filter((item: any) => config.levels.includes(item.level));
      const entityItems = entityRes.data?.data?.items || [];
      setConcepts(filteredConcepts);
      setAllEntities(entityItems);

      const nextTree = buildTree(filteredConcepts, mode).treeData;
      const nextMetaMap = buildTree(filteredConcepts, mode).metaMap;
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
      console.error(error);
      message.error('加载建模数据失败');
    } finally {
      setLoading(false);
    }
  }, [config.includeLevel0, config.levels, mode, initialEntityId]);

  useEffect(() => {
    refreshData(false);
  }, [mode, refreshData]);

  useEffect(() => {
    if (!relationHighlight || !allEntities.length || !concepts.length) return;
    const focusEntityId = mode === 'master' ? relationHighlight.masterEntityId : relationHighlight.activityEntityId;
    const focusEntity = allEntities.find((item: any) => item.id === focusEntityId);
    if (!focusEntity) return;
    const focusConcept = concepts.find((item: any) => item.id === focusEntity.concept_id);
    if (!focusConcept || focusConcept.level !== config.leafLevel) return;
    setRelationFilter('matrix');
    setSelectedKey(`entity-${focusEntityId}`);
  }, [allEntities, concepts, config.leafLevel, mode, relationHighlight]);

  useEffect(() => {
    const loadEntityDetails = async () => {
      if (!selectedMeta || selectedMeta.nodeType !== 'entity') {
        setRelationRows([]);
        return;
      }
      setLoadingDetail(true);
      try {
        const entityId = selectedMeta.entity.id;
        const relRes = await entityRelationManagerApi.listItems({ entity_id: entityId });
        setRelationRows(relRes.data?.data?.items || []);
      } catch (error) {
        console.error(error);
        message.error('加载实体详情失败');
      } finally {
        setLoadingDetail(false);
      }
    };
    loadEntityDetails();
  }, [selectedMeta]);

  const openCreateRootConcept = () => {
    setConceptModalMode('create');
    conceptForm.setFieldsValue({
      level: config.rootLevel,
      parent_id: null,
      name: '',
      sort_order: undefined,
      description: '',
      system_names: [],
    });
    setConceptModalVisible(true);
  };

  const openCreateChildConcept = () => {
    if (!selectedMeta || selectedMeta.nodeType !== 'concept') {
      message.warning('请先选择一个概念分类节点');
      return;
    }
    const nextLevel = config.childLevelMap[selectedMeta.concept.level];
    if (!nextLevel) {
      message.warning('当前节点下不支持继续新增下级概念分类');
      return;
    }
    setConceptModalMode('create');
    conceptForm.setFieldsValue({
      level: nextLevel,
      parent_id: selectedMeta.concept.id,
      name: '',
      sort_order: undefined,
      description: '',
      system_names: [],
    });
    setConceptModalVisible(true);
  };

  const openEditConcept = () => {
    if (!selectedMeta || selectedMeta.nodeType !== 'concept') {
      message.warning('请先选择一个概念分类节点');
      return;
    }
    setConceptModalMode('edit');
    conceptForm.setFieldsValue({
      name: selectedMeta.concept.name,
      sort_order: selectedMeta.concept.sort_order,
      description: selectedMeta.concept.description,
      system_names: selectedMeta.concept.system_names || [],
    });
    setConceptModalVisible(true);
  };

  const saveConcept = async () => {
    try {
      const values = await conceptForm.validateFields();
      const conceptLevel =
        conceptModalMode === 'create' ? Number(values.level) : Number(selectedMeta?.concept?.level);
      const payload = {
        name: values.name,
        description: values.description,
        sort_order: values.sort_order,
        system_names: conceptLevel === 3 ? values.system_names || [] : [],
      };
      if (conceptModalMode === 'create') {
        await conceptApi.createConcept({
          ...payload,
          level: Number(values.level),
          parent_id: values.parent_id || null,
        });
        message.success('概念分类新增成功');
      } else {
        await conceptApi.updateConcept(selectedMeta.concept.id, payload);
        message.success('概念分类更新成功');
      }
      setConceptModalVisible(false);
      await refreshData();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || '概念分类保存失败');
    }
  };

  const deleteConcept = async () => {
    if (!selectedMeta || selectedMeta.nodeType !== 'concept') return;
    try {
      await conceptApi.deleteConcept(selectedMeta.concept.id);
      message.success('概念分类删除成功');
      await refreshData(false);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '概念分类删除失败');
    }
  };

  const openCreateEntity = (concept?: any) => {
    const targetConcept = concept || (selectedMeta?.nodeType === 'concept' ? selectedMeta.concept : null);
    if (!targetConcept || targetConcept.level !== config.leafLevel) {
      message.warning(`请先选择 ${LEVEL_LABELS[config.leafLevel]} 概念分类节点`);
      return;
    }
    setEditingEntity(null);
    setEntityTargetConcept(targetConcept);
    setSelectedExplanationKeywords([]);
    setExplanationItems([]);
    setNewManualExplanation('');
    entityForm.resetFields();
    entityForm.setFieldsValue({ is_main_table: false, sort_order: undefined });
    setEntityModalVisible(true);
  };

  const openEditEntity = (entity: any, parentConcept?: any) => {
    setEditingEntity(entity);
    setEntityTargetConcept(parentConcept || selectedMeta?.parentConcept || null);
    const initialItems = buildExplanationItems(entity.entity_explanation, getPropertyKeywordOptions(entity.properties_schema || []));
    setExplanationItems(initialItems);
    setSelectedExplanationKeywords(initialItems.filter((item) => item.source === 'field').map((item) => item.text));
    setNewManualExplanation('');
    entityForm.setFieldsValue({
      entity_name: entity.entity_name,
      entity_en_name: entity.entity_en_name,
      entity_code: entity.entity_code,
      description: entity.description,
      data_layer: entity.data_layer,
      is_main_table: entity.is_main_table,
      sort_order: entity.sort_order,
    });
    setEntityModalVisible(true);
  };

  const saveEntity = async () => {
    try {
      const values = await entityForm.validateFields();
      const payload = {
        ...values,
        entity_explanation: serializeExplanationItems(explanationItems),
      };
      if (editingEntity) {
        await entityApi.updateEntity(editingEntity.id, payload);
        message.success(`${getEntityCategoryLabel(entityTargetConcept?.level)}更新成功`);
      } else {
        await entityApi.createEntity({
          ...payload,
          concept_id: entityTargetConcept.id,
        });
        message.success(`${getEntityCategoryLabel(entityTargetConcept?.level)}新增成功`);
      }
      setEntityModalVisible(false);
      await refreshData();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || `${getEntityCategoryLabel(entityTargetConcept?.level)}保存失败`);
    }
  };

  const currentEntityProperties = useMemo(() => {
    return Array.isArray(editingEntity?.properties_schema) ? editingEntity.properties_schema : [];
  }, [editingEntity]);

  const currentPropertyKeywordOptions = useMemo(() => getPropertyKeywordOptions(currentEntityProperties), [currentEntityProperties]);
  const explanationValue = useMemo(() => serializeExplanationItems(explanationItems), [explanationItems]);
  const explanationStats = useMemo(
    () => ({
      manual: explanationItems.filter((item) => item.source === 'manual').length,
      auto: explanationItems.filter((item) => item.source === 'auto').length,
      field: explanationItems.filter((item) => item.source === 'field').length,
    }),
    [explanationItems]
  );

  const handleAutoSuggestExplanation = async () => {
    try {
      const values = entityForm.getFieldsValue();
      const parentConcept =
        entityTargetConcept?.parent_id ? concepts.find((item: any) => item.id === entityTargetConcept.parent_id) : null;
      setLoadingExplanationSuggest(true);
      const res = await entityApi.suggestEntityExplanations({
        entity_name: values.entity_name,
        concept_name: entityTargetConcept?.name,
        parent_concept_name: parentConcept?.name,
        description: values.description,
        entity_explanation: explanationValue,
        properties_schema: currentEntityProperties,
      });
      const payload = res.data?.data || {};
      const nextItems = mergeExplanationItems(explanationItems, payload.suggestions || [], 'auto');
      setExplanationItems(nextItems);
      message.success(`已新增 ${Math.max(nextItems.length - explanationItems.length, 0)} 条自动提取同义词`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '自动提取解释失败');
    } finally {
      setLoadingExplanationSuggest(false);
    }
  };

  const openExplanationKeywordPicker = () => {
    if (!currentPropertyKeywordOptions.length) {
      message.warning('当前实体还没有可选属性，请先维护属性后再选关键词');
      return;
    }
    setSelectedExplanationKeywords(explanationItems.filter((item) => item.source === 'field').map((item) => item.text));
    setExplanationKeywordModalVisible(true);
  };

  const applySelectedExplanationKeywords = () => {
    const nextItems = mergeExplanationItems(
      explanationItems,
      selectedExplanationKeywords,
      'field',
      { replaceSource: true }
    );
    setExplanationItems(nextItems);
    setExplanationKeywordModalVisible(false);
    message.success(`已写入 ${selectedExplanationKeywords.length} 个字段关键词`);
  };

  const addManualExplanationItems = () => {
    const terms = splitExplanationTerms(newManualExplanation);
    if (!terms.length) {
      message.warning('请先输入要新增的同义词');
      return;
    }
    const nextItems = mergeExplanationItems(explanationItems, terms, 'manual');
    setExplanationItems(nextItems);
    setNewManualExplanation('');
    message.success(`已新增 ${Math.max(nextItems.length - explanationItems.length, 0)} 条手工同义词`);
  };

  const updateExplanationItem = (id: string, nextText: string) => {
    setExplanationItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, text: nextText } : item))
    );
  };

  const removeExplanationItem = (id: string) => {
    setExplanationItems((prev) => prev.filter((item) => item.id !== id));
  };

  const clearExplanationItems = () => {
    setExplanationItems([]);
    setSelectedExplanationKeywords([]);
    setNewManualExplanation('');
  };

  const deleteEntity = async (entityId: string) => {
    try {
      await entityApi.deleteEntity(entityId);
      message.success('数据实体删除成功');
      await refreshData(false);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '数据实体删除失败');
    }
  };

  const openCreateProperty = (entity?: any) => {
    const targetEntity = entity || (selectedMeta?.nodeType === 'entity' ? selectedMeta.entity : selectedMeta?.entity);
    if (!targetEntity) {
      message.warning('请先选择一个数据实体节点');
      return;
    }
    setPropertyTargetEntity(targetEntity);
    setEditingPropertyIndex(null);
    propertyForm.resetFields();
    setPropertyModalVisible(true);
  };

  const openEditProperty = () => {
    if (!selectedMeta || selectedMeta.nodeType !== 'property') {
      message.warning('请先选择一个属性节点');
      return;
    }
    setPropertyTargetEntity(selectedMeta.entity);
    setEditingPropertyIndex(selectedMeta.propertyIndex);
    propertyForm.setFieldsValue({
      name: selectedMeta.property.name,
      cnName: selectedMeta.property.cnName,
      type: selectedMeta.property.type,
      isPrimaryKey: selectedMeta.property.isPrimaryKey,
      description: selectedMeta.property.description,
    });
    setPropertyModalVisible(true);
  };

  const saveProperty = async () => {
    try {
      const values = await propertyForm.validateFields();
      const props = [...(propertyTargetEntity.properties_schema || [])];
      if (editingPropertyIndex === null) {
        props.push(values);
      } else {
        props[editingPropertyIndex] = values;
      }
      await entityApi.updateEntity(propertyTargetEntity.id, { properties_schema: props });
      message.success(editingPropertyIndex === null ? '属性新增成功' : '属性更新成功');
      setPropertyModalVisible(false);
      await refreshData();
      setSelectedKey(`entity-${propertyTargetEntity.id}`);
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || '属性保存失败');
    }
  };

  const deleteProperty = async () => {
    if (!selectedMeta || selectedMeta.nodeType !== 'property') return;
    try {
      const props = [...(selectedMeta.entity.properties_schema || [])];
      props.splice(selectedMeta.propertyIndex, 1);
      await entityApi.updateEntity(selectedMeta.entity.id, { properties_schema: props });
      message.success('属性删除成功');
      await refreshData();
      setSelectedKey(`entity-${selectedMeta.entity.id}`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '属性删除失败');
    }
  };

  // 导入时是否先清空当前模式数据（清空后重导入）
  const [importClear, setImportClear] = useState(false);

  const handleExport = () => {
    window.open(conceptApi.exportExcel(mode), '_blank');
    message.success('导出任务已启动');
  };

  const handleImport = async (options: any) => {
    const { file, onSuccess, onError } = options;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const resp = await conceptApi.importExcel(formData, mode, importClear);
      const data = resp.data || {};
      const msg = data.message || '导入成功';
      if (data.status === 'warning') {
        message.warning(msg);
      } else {
        message.success((importClear ? '已清空并重新导入：' : '') + msg);
      }
      onSuccess('ok');
      await refreshData(false);
    } catch (error: any) {
      message.error(`导入失败: ${error.response?.data?.detail || error.message}`);
      onError(error);
    }
  };

  const handleReset = async () => {
    try {
      await conceptApi.clearGraphData(mode);
      message.success('当前数据已清空，可重新导入');
      await refreshData(false);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '清空失败');
    }
  };

  const openMappingManager = () => {
    if (selectedMeta?.nodeType === 'entity') {
      setMappingFilterEntityId(selectedMeta.entity.id);
    }
    onOpenTarget?.('mapping');
  };

  // 配置映射：按 source_mode 直跳来源表映射管理对应 Tab，自动过滤当前实体
  const handleConfigMapping = () => {
    if (selectedMeta?.nodeType !== 'entity') return;
    const ent = selectedMeta.entity;
    setMappingFilterEntityId(ent.id);
    const tabMap: Record<string, string> = { physical_table: '1', sql_integration: '2', api_integration: '3' };
    setMappingJumpTab(tabMap[sourceMode] || '1');
    onOpenTarget?.('mapping');
  };

  // === 数据来源配置 Tab ===
  const [sourceMode, setSourceMode] = useState<string>('physical_table');
  const [integrationSql, setIntegrationSql] = useState<string>('');
  const [savingSourceMode, setSavingSourceMode] = useState(false);
  const [savingSql, setSavingSql] = useState(false);
  // per-entity 数据源绑定（physical_table 模式用）
  const [dataSources, setDataSources] = useState<any[]>([]);
  const [savingDataSource, setSavingDataSource] = useState(false);
  // 数据预览
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [previewColumns, setPreviewColumns] = useState<any[]>([]);
  const [previewTitle, setPreviewTitle] = useState('');

  useEffect(() => {
    if (selectedMeta?.nodeType === 'entity') {
      const ent = selectedMeta.entity;
      const mode = ent.source_mode || 'physical_table';
      setSourceMode(mode);
      setIntegrationSql(ent.integration_sql || '');
    }
  }, [selectedMeta]);

  // 加载数据源列表（physical_table 模式绑定用）
  useEffect(() => {
    axios.get('/api/v1/data-sources').then((res) => {
      const list = (res.data?.data || []).filter((ds: any) => ds.enabled);
      setDataSources(list);
    }).catch(() => { /* 静默失败，不影响主流程 */ });
  }, []);

  const handleSourceModeChange = async (value: string) => {
    if (selectedMeta?.nodeType !== 'entity') return;
    const ent = selectedMeta.entity;
    setSavingSourceMode(true);
    try {
      await entityApi.updateEntity(ent.id, { source_mode: value });
      setSourceMode(value);
      const modeLabel: Record<string, string> = {
        physical_table: '物理数据表',
        sql_integration: '多源SQL整合',
        api_integration: '多源API整合',
      };
      message.success(`已切换为「${modeLabel[value] || value}」模式`);
      // 就地更新该实体字段，避免 refreshData 触发整树转圈+折叠
      setConcepts((prev) =>
        prev.map((c: any) => ({
          ...c,
          entities: (c.entities || []).map((e: any) =>
            e.id === ent.id ? { ...e, source_mode: value } : e
          ),
        }))
      );
      setAllEntities((prev) =>
        prev.map((e: any) => (e.id === ent.id ? { ...e, source_mode: value } : e))
      );
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '切换失败');
    } finally {
      setSavingSourceMode(false);
    }
  };

  // per-entity 数据源绑定（physical_table 模式）
  const handleDataSourceChange = async (value: string | undefined) => {
    if (selectedMeta?.nodeType !== 'entity') return;
    const ent = selectedMeta.entity;
    setSavingDataSource(true);
    try {
      await entityApi.updateEntity(ent.id, { data_source_id: value || null });
      // 就地更新该实体字段
      setConcepts((prev) =>
        prev.map((c: any) => ({
          ...c,
          entities: (c.entities || []).map((e: any) =>
            e.id === ent.id ? { ...e, data_source_id: value || null } : e
          ),
        }))
      );
      setAllEntities((prev) =>
        prev.map((e: any) => (e.id === ent.id ? { ...e, data_source_id: value || null } : e))
      );
      message.success(value ? '已绑定数据源' : '已恢复默认数据源');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '绑定失败');
    } finally {
      setSavingDataSource(false);
    }
  };

  const handleSaveIntegrationSql = async () => {
    if (selectedMeta?.nodeType !== 'entity') return;
    const ent = selectedMeta.entity;
    setSavingSql(true);
    try {
      await entityApi.updateEntity(ent.id, { integration_sql: integrationSql });
      message.success('整合 SQL 已保存');
      // 就地更新该实体字段，避免 refreshData 触发整树转圈+折叠
      setConcepts((prev) =>
        prev.map((c: any) => ({
          ...c,
          entities: (c.entities || []).map((e: any) =>
            e.id === ent.id ? { ...e, integration_sql: integrationSql } : e
          ),
        }))
      );
      setAllEntities((prev) =>
        prev.map((e: any) =>
          e.id === ent.id ? { ...e, integration_sql: integrationSql } : e
        )
      );
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally {
      setSavingSql(false);
    }
  };

  // 数据预览：按 source_mode 路由到不同取数方式
  const handleDataPreview = async () => {
    if (selectedMeta?.nodeType !== 'entity') return;
    const ent = selectedMeta.entity;
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewRows([]);
    setPreviewColumns([]);
    try {
      if (sourceMode === 'physical_table') {
        // 物理数据表：复用 entity-preview 端点
        setPreviewTitle(`数据预览 - 物理数据表模式`);
        const resp = await mappingApi.previewEntityData(ent.id, 20);
        const data = resp.data?.data || {};
        const rows = data.rows || [];
        setPreviewRows(rows);
        setPreviewColumns(rows.length > 0
          ? Object.keys(rows[0]).map(k => ({ title: k, dataIndex: k, ellipsis: true, width: 150 }))
          : []
        );
        if (rows.length === 0) message.warning(data.hint || '无数据可预览');
      } else if (sourceMode === 'sql_integration') {
        // 多源SQL整合：执行 integration_sql
        if (!integrationSql?.trim()) {
          message.warning('请先配置整合 SQL');
          setPreviewTitle('数据预览 - 整合SQL未配置');
          return;
        }
        setPreviewTitle(`数据预览 - 多源SQL整合(Doris)`);
        const resp = await kgApi.executeSql(integrationSql);
        const data = resp.data || {};
        if (data.error) {
          message.error(data.error);
          return;
        }
        const cols = data.columns || [];
        const rows2d = data.rows || [];
        // rows 是二维数组，按 columns 映射成对象
        const rows = rows2d.map((r: any[]) => {
          const obj: any = {};
          cols.forEach((c: string, i: number) => { obj[c] = r[i]; });
          return obj;
        });
        setPreviewRows(rows);
        setPreviewColumns(cols.map((c: string) => ({ title: c, dataIndex: c, ellipsis: true, width: 150 })));
        message.success(`预览成功，返回 ${data.row_count || rows.length} 行`);
      } else if (sourceMode === 'api_integration') {
        // 多源API整合：走 /entity-preview（后端按 source_mode 路由到 DuckDB 联邦查询 ApiEndpoint）
        setPreviewTitle(`数据预览 - 多源API整合(DuckDB)`);
        const resp = await mappingApi.previewEntityData(ent.id, 20);
        const data = resp.data?.data || {};
        const rows = data.rows || [];
        setPreviewRows(rows);
        setPreviewColumns(rows.length > 0
          ? Object.keys(rows[0]).map(k => ({ title: k, dataIndex: k, ellipsis: true, width: 150 }))
          : []
        );
        if (rows.length === 0) message.warning(data.hint || '无数据可预览');
        else message.success(`预览成功，返回 ${data.row_count || rows.length} 行`);
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.response?.data?.error || '预览失败');
    } finally {
      setPreviewLoading(false);
    }
  };

  const renderConceptDetail = () => {
    const concept = selectedMeta.concept;
    const canAddChild = !!config.childLevelMap[concept.level];
    return (
      <>
        <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="概念分类名称">{concept.name}</Descriptions.Item>
            <Descriptions.Item label="层级">
              <StatusTag preset="info">{LEVEL_LABELS[concept.level] || `L${concept.level}`}</StatusTag>
            </Descriptions.Item>
            <Descriptions.Item label="显示顺序">{concept.sort_order ?? 0}</Descriptions.Item>
            {concept.level === 3 ? (
              <Descriptions.Item label="所属系统">
                {concept.system_names?.length ? (
                  <Space size={[4, 4]} wrap>
                    {concept.system_names.map((item: string) => (
                      <StatusTag key={item} preset="ai">
                        {item}
                      </StatusTag>
                    ))}
                  </Space>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
            ) : null}
            <Descriptions.Item label="说明">{concept.description || '-'}</Descriptions.Item>
          </Descriptions>
        </Card>

        <Card
          size="small"
          title="概念分类维护"
          style={{ marginBottom: 16, borderRadius: 12 }}
          extra={<Badge color={concept.level === config.leafLevel ? 'var(--color-warning)' : 'var(--color-primary)'} text={readOnly ? '只读查看' : concept.level === config.leafLevel ? '可维护数据实体' : '可维护概念分类'} />}
        >
          {readOnly ? (
            <Text type="secondary">当前为只读查看模式，概念分类和数据实体维护请在后台建模页处理。</Text>
          ) : (
            <Space wrap>
              {canAddChild ? (
                <Button type="dashed" icon={<PlusOutlined />} onClick={openCreateChildConcept}>
                  新增下级概念分类
                </Button>
              ) : null}
              {concept.level === config.leafLevel ? (
                <Button type="dashed" icon={<DatabaseOutlined />} onClick={() => openCreateEntity(concept)}>
                  新增{getEntityCategoryLabel(concept.level)}
                </Button>
              ) : null}
              <Button icon={<EditOutlined />} onClick={openEditConcept}>
                编辑概念分类
              </Button>
              <Popconfirm title="确认删除当前概念分类？" onConfirm={deleteConcept}>
                <Button danger icon={<DeleteOutlined />}>
                  删除概念分类
                </Button>
              </Popconfirm>
            </Space>
          )}
        </Card>

        {concept.level === config.leafLevel ? (
          <Card
            size="small"
            title={`下属${getEntityCategoryLabel(concept.level)}`}
            style={{ borderRadius: 12 }}
            extra={<StatusTag preset={getEntityCategoryPreset(concept.level)}>共 {(concept.entities || []).length} 个{getEntityCategoryLabel(concept.level)}</StatusTag>}
          >
            {(concept.entities || []).length > 0 ? (
              <List
                size="small"
                bordered
                dataSource={[...(concept.entities || [])].sort((a: any, b: any) => {
                  const orderDiff = (a.sort_order || 0) - (b.sort_order || 0);
                  if (orderDiff !== 0) return orderDiff;
                  return String(a.entity_name || '').localeCompare(String(b.entity_name || ''), 'zh-CN');
                })}
                renderItem={(item: any) => (
                  <List.Item
                    actions={[
                      <Button key="locate" type="link" size="small" onClick={() => setSelectedKey(`entity-${item.id}`)}>
                        定位
                      </Button>,
                      ...(!readOnly ? [
                        <Button key="edit" type="link" size="small" onClick={() => openEditEntity(item, concept)}>
                          编辑
                        </Button>,
                        <Popconfirm key="delete" title={`确认删除该${getEntityCategoryLabel(concept.level)}？`} onConfirm={() => deleteEntity(item.id)}>
                          <Button type="link" size="small" danger>
                            删除
                          </Button>
                        </Popconfirm>,
                      ] : []),
                    ]}
                  >
                    <Space>
                      <DatabaseOutlined style={{ color: concept.level === 4 ? '#13c2c2' : 'var(--color-warning)' }} />
                      <span>{item.entity_name}</span>
                      <Text type="secondary">{item.entity_code}</Text>
                      <StatusTag preset={getEntityCategoryPreset(concept.level)}>{getEntityCategoryLabel(concept.level)}</StatusTag>
                      <StatusTag preset="default">顺序 {item.sort_order ?? 0}</StatusTag>
                      {item.is_main_table ? <StatusTag preset="info">主表</StatusTag> : null}
                      <Tag>{(item.properties_schema || []).length} 个属性</Tag>
                      {splitExplanationTerms(item.entity_explanation).length ? <StatusTag preset="ai">{splitExplanationTerms(item.entity_explanation).length} 个同义词</StatusTag> : null}
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`暂无${getEntityCategoryLabel(concept.level)}`} />
            )}
          </Card>
        ) : null}
      </>
    );
  };

  const renderEntityDetail = () => {
    const entity = selectedMeta.entity;
    return (
      <>
        {!readOnly ? (
          <Card size="small" title={`删除${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}`} style={{ marginBottom: 16, borderRadius: 12 }}>
            <Popconfirm title={`确认删除该${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}？`} onConfirm={() => deleteEntity(entity.id)}>
              <Button danger icon={<DeleteOutlined />}>
                删除{getEntityCategoryLabel(selectedMeta.parentConcept?.level)}
              </Button>
            </Popconfirm>
          </Card>
        ) : null}

        <Card
          size="small"
          title={`${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}基本信息`}
          style={{ marginBottom: 16, borderRadius: 12 }}
          extra={
            !readOnly ? (
              <Button icon={<EditOutlined />} onClick={() => openEditEntity(entity, selectedMeta.parentConcept)}>
                维护{getEntityCategoryLabel(selectedMeta.parentConcept?.level)}
              </Button>
            ) : null
          }
        >
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label={`${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}名称`}>{entity.entity_name}</Descriptions.Item>
            <Descriptions.Item label={`${getEntityCategoryLabel(selectedMeta.parentConcept?.level)}编码`}>{entity.entity_code}</Descriptions.Item>
            <Descriptions.Item label="落地英文表名">{entity.entity_en_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="所属概念分类">
              {selectedMeta.parentConcept?.name || '-'} {selectedMeta.parentConcept ? <Tag>{LEVEL_LABELS[selectedMeta.parentConcept.level]}</Tag> : null}
            </Descriptions.Item>
            <Descriptions.Item label="数据实体类别">
              <StatusTag preset={getEntityCategoryPreset(selectedMeta.parentConcept?.level)}>{getEntityCategoryLabel(selectedMeta.parentConcept?.level)}</StatusTag>
            </Descriptions.Item>
            <Descriptions.Item label="是否主表">{entity.is_main_table ? '是' : '否'}</Descriptions.Item>
            <Descriptions.Item label="数据层级">{entity.data_layer || '-'}</Descriptions.Item>
            <Descriptions.Item label="显示顺序">{entity.sort_order ?? 0}</Descriptions.Item>
            <Descriptions.Item label="属性数量">{(entity.properties_schema || []).length}</Descriptions.Item>
            <Descriptions.Item label="解释（别名同义词）" span={2}>
              {splitExplanationTerms(entity.entity_explanation).length ? (
                <Space size={[4, 4]} wrap>
                  {splitExplanationTerms(entity.entity_explanation).map((item) => (
                    <StatusTag key={item} preset="ai">
                      {item}
                    </StatusTag>
                  ))}
                </Space>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="说明" span={2}>{entity.description || '-'}</Descriptions.Item>
          </Descriptions>
        </Card>

        <Card size="small" title="数据来源配置" style={{ marginBottom: 16, borderRadius: 12 }} extra={
          <Space>
            <Button size="small" type="primary" ghost icon={<LinkOutlined />} onClick={handleConfigMapping}>
              配置映射
            </Button>
            <Button size="small" icon={<EyeOutlined />} loading={previewLoading} onClick={handleDataPreview}>
              数据预览
            </Button>
          </Space>
        }>
          <Radio.Group
            value={sourceMode}
            onChange={(e) => handleSourceModeChange(e.target.value)}
            disabled={savingSourceMode}
          >
            <Tooltip title="实体直接读取物理表数据（PostgreSQL），在「落地实体表映射」中配置字段映射">
              <Radio value="physical_table">物理数据表</Radio>
            </Tooltip>
            <Tooltip title="通过 Doris 执行整合 SQL 获取数据，可跨源整合">
              <Radio value="sql_integration">多源SQL整合(Doris)</Radio>
            </Tooltip>
            <Tooltip title="通过 DuckDB 联邦查询整合 API 数据，配置端点与伪逻辑 SQL">
              <Radio value="api_integration">多源API整合(DuckDB)</Radio>
            </Tooltip>
          </Radio.Group>
          {sourceMode === 'physical_table' && (
            <div style={{ marginTop: 10 }}>
              <span style={{ marginRight: 8, color: 'var(--text-secondary)' }}>数据源绑定：</span>
              <Select
                style={{ width: 300 }}
                placeholder="默认（全局数据源）"
                allowClear
                loading={savingDataSource}
                value={(selectedMeta?.entity as any)?.data_source_id || undefined}
                onChange={(v) => handleDataSourceChange(v)}
                options={dataSources.map((ds: any) => ({
                  label: `${ds.name}（${ds.host}:${ds.port}/${ds.database}）`,
                  value: ds.id,
                }))}
              />
              <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-tertiary)' }}>
                不同实体绑不同数据源时，跨源查询自动走 Doris 联邦
              </span>
            </div>
          )}
        </Card>

        <Card
          size="small"
          title="属性区域"
          style={{ marginBottom: 16, borderRadius: 12 }}
          extra={
            !readOnly ? (
              <Button type="dashed" icon={<PlusOutlined />} onClick={() => openCreateProperty(entity)}>
                属性维护
              </Button>
            ) : null
          }
        >
        <Table
          size="small"
          scroll={{ y: 240 }}
          pagination={{ pageSize: 5, showSizeChanger: true, size: 'small' }}
          rowKey={(row: any, idx?: number) => `${row.name}-${idx ?? 0}`}
          dataSource={entity.properties_schema || []}
          locale={{ emptyText: '暂无属性' }}
          columns={[
            { title: '属性英文名', dataIndex: 'name', width: 180 },
            { title: '属性中文名', dataIndex: 'cnName', width: 180 },
            { title: '类型', dataIndex: 'type', width: 100 },
            { title: '主键', dataIndex: 'isPrimaryKey', width: 90, render: (val: boolean) => (val ? <StatusTag preset="error">是</StatusTag> : '否') },
            {
              title: '参与问实体识别',
              dataIndex: 'enable_query_entity',
              width: 130,
              render: (val: boolean) => (val ? <StatusTag preset="success">是</StatusTag> : <Tag>否</Tag>)
            },
            { title: '说明', dataIndex: 'description' },
            {
              title: '操作',
              width: readOnly ? 80 : 140,
              render: (_: any, row: any, index: number) => (
                <Space size="small">
                  <Button type="link" size="small" onClick={() => setSelectedKey(`property-${entity.id}-${index}`)}>
                    查看
                  </Button>
                  {!readOnly ? (
                    <Button
                      type="link"
                      size="small"
                      onClick={() => {
                        setSelectedKey(`property-${entity.id}-${index}`);
                        setTimeout(() => openEditProperty(), 0);
                      }}
                    >
                      编辑
                    </Button>
                  ) : null}
                </Space>
              ),
            },
          ]}
        />
        </Card>

        <Card
          size="small"
          title="数据实体间关系查询"
          style={{ borderRadius: 12 }}
          extra={
            <Space size={8}>
              <StatusTag preset="info">手工维护 {mergedRelations.filter((item: any) => item.row_type === 'manual').length}</StatusTag>
              <StatusTag preset="ai">打点维护 {mergedRelations.filter((item: any) => item.row_type === 'matrix').length}</StatusTag>
              <Segmented
                size="small"
                value={relationFilter}
                onChange={(value) => setRelationFilter(value as 'all' | 'manual' | 'matrix')}
                options={[
                  { label: '全部', value: 'all' },
                  { label: '手工维护', value: 'manual' },
                  { label: '打点维护', value: 'matrix' },
                ]}
              />
            </Space>
          }
        >
        <Table
          size="small"
          pagination={false}
          rowKey="id"
          loading={loadingDetail}
          dataSource={filteredRelations}
          locale={{ emptyText: '暂无数据实体关系' }}
          onRow={(record: any) => ({
            style: record.id === relationHighlight?.linkId
              ? { background: 'var(--color-warning-bg)', boxShadow: 'inset 3px 0 0 var(--color-warning)' }
              : record.row_type === 'matrix'
                ? { background: 'var(--color-ai-bg)' }
                : { background: 'var(--color-success-bg)' },
          })}
          columns={[
            {
              title: '关系分组',
              dataIndex: 'relation_group_label',
              width: 140,
              render: (value: string) => <StatusTag preset="info">{value}</StatusTag>,
            },
            {
              title: '类别',
              dataIndex: 'relation_category',
              width: 110,
              render: (value: string) => (
                <StatusTag preset={value === '打点维护' ? 'ai' : 'info'}>{value || '手工维护'}</StatusTag>
              ),
            },
            {
              title: '关系名',
              dataIndex: 'relation_name',
              width: 280,
              render: (value: string, row: any) => (
                <span style={{ fontWeight: row.id === relationHighlight?.linkId ? 700 : 500, color: row.row_type === 'matrix' ? '#531dab' : 'var(--color-primary-hover)' }}>
                  {value}
                </span>
              ),
            },
            { title: '源数据实体', dataIndex: 'source_entity_name', width: 180 },
            { title: '目标数据实体', dataIndex: 'target_entity_name', width: 180 },
            { title: '方向', dataIndex: 'direction', width: 100 },
            { title: '基数', dataIndex: 'cardinality', width: 100 },
            { title: '源字段', dataIndex: 'source_field_name', width: 140 },
            { title: '目标字段', dataIndex: 'target_field_name', width: 140 },
            { title: '关联说明', dataIndex: 'join_expr' },
            { title: '备注', dataIndex: 'remark', width: 220 },
          ]}
        />
        </Card>
      </>
    );
  };

  const renderPropertyDetail = () => {
    const prop = selectedMeta.property;
    return (
      <>
        <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="所属数据实体">{selectedMeta.entity?.entity_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="属性英文名">{prop.name || '-'}</Descriptions.Item>
            <Descriptions.Item label="属性中文名">{prop.cnName || '-'}</Descriptions.Item>
            <Descriptions.Item label="类型">{prop.type || '-'}</Descriptions.Item>
            <Descriptions.Item label="是否主键">{prop.isPrimaryKey ? '是' : '否'}</Descriptions.Item>
            <Descriptions.Item label="参与问实体识别">{prop.enable_query_entity ? '是' : '否'}</Descriptions.Item>
            <Descriptions.Item label="说明">{prop.description || '-'}</Descriptions.Item>
          </Descriptions>
        </Card>
        <Card size="small" title="属性维护" style={{ borderRadius: 12 }}>
          <Space wrap>
            {!readOnly ? (
              <Button icon={<EditOutlined />} onClick={openEditProperty}>
                编辑属性
              </Button>
            ) : null}
            {!readOnly ? (
              <Popconfirm title="确认删除当前属性？" onConfirm={deleteProperty}>
                <Button danger icon={<DeleteOutlined />}>
                  删除属性
                </Button>
              </Popconfirm>
            ) : null}
            <Button type="dashed" onClick={() => setSelectedKey(`entity-${selectedMeta.entity.id}`)}>
              返回数据实体
            </Button>
          </Space>
        </Card>
      </>
    );
  };

  const renderDetail = () => {
    if (!selectedMeta) {
      return <Empty description="请从左侧树中选择一个节点" />;
    }
    if (selectedMeta.nodeType === 'concept') return renderConceptDetail();
    if (selectedMeta.nodeType === 'entity') return renderEntityDetail();
    if (selectedMeta.nodeType === 'property') return renderPropertyDetail();
    return <Empty description="暂无详情" />;
  };

    return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <Card
        style={{ width: '100%', maxWidth: '100%', height: '100%', display: 'flex', flexDirection: 'column', boxShadow: embedded ? 'none' : undefined, overflow: 'hidden' }}
        bodyStyle={{ padding: 0, flex: 1, overflow: 'hidden' }}
        title={pageTitle}
        extra={
          <Space wrap>
            {!readOnly ? (
              <Button icon={<ExportOutlined />} onClick={handleExport}>
                导出
              </Button>
            ) : null}
            {!readOnly ? (
              <Checkbox checked={importClear} onChange={(e) => setImportClear(e.target.checked)}>清空后重导入</Checkbox>
            ) : null}
            {!readOnly ? (
              <Upload customRequest={handleImport} showUploadList={false} accept=".xlsx">
                <Button icon={<ImportOutlined />}>导入</Button>
              </Upload>
            ) : null}
            {!readOnly ? (
              <Popconfirm title={`确认清空当前【${pageTitle}】的全部概念、实体及关系？此操作不可恢复。`} onConfirm={handleReset}>
                <Button danger icon={<ReloadOutlined />}>
                  重置模板
                </Button>
              </Popconfirm>
            ) : null}
            {!readOnly ? (
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateRootConcept}>
                {config.rootCreateLabel}
              </Button>
            ) : null}
          </Space>
        }
      >
        <Layout style={{ height: '100%', background: 'transparent' }}>
          {!embedded && (
            <Sider width={420} style={{ background: 'var(--bg-content)', borderRight: '1px solid var(--color-border)', padding: 12, overflow: 'auto' }}>
              <div style={{ marginBottom: 12 }}>
                <Text strong>{config.rootName}</Text>
                <div style={{ color: 'var(--text-tertiary)', fontSize: 12, marginTop: 4 }}>
                  {readOnly ? '左侧树按顺序展示概念分类、数据实体与属性，右侧仅查看详情，可返回图谱页面。' : '左侧树按顺序展示概念分类、数据实体与属性，右侧按区域分别维护目录、数据实体、属性和数据实体关系。'}
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
                  onExpand={(keys) => setExpandedKeys(keys as string[])}
                  onSelect={(keys) => setSelectedKey((keys[0] as string) || null)}
                  treeData={treeData}
                  blockNode
                />
              ) : (
                <Empty description="暂无数据" />
              )}
            </Sider>
          )}
          <Content style={{ padding: 16, overflow: 'auto' }}>
            {renderDetail()}
          </Content>
        </Layout>
      </Card>

      <Modal
        title={conceptModalMode === 'create' ? '新增概念分类' : '编辑概念分类'}
        open={conceptModalVisible}
        onCancel={() => setConceptModalVisible(false)}
        onOk={saveConcept}
        destroyOnHidden
      >
        <Form form={conceptForm} layout="vertical">
          {conceptModalMode === 'create' ? (
            <>
              <Form.Item name="level" label="层级">
                <Input disabled />
              </Form.Item>
              <Form.Item name="parent_id" label="父级ID">
                <Input disabled />
              </Form.Item>
            </>
          ) : null}
          <Form.Item name="name" label="概念分类名称" rules={[{ required: true, message: '请输入概念分类名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="sort_order" label="显示顺序">
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
          {(conceptModalMode === 'create' ? Number(conceptFormLevel) : selectedMeta?.concept?.level) === 3 ? (
            <Form.Item name="system_names" label="所属系统">
              <Select
                mode="tags"
                allowClear
                tokenSeparators={[',', '，', ';', '；']}
                placeholder="可输入 1 个或多个所属系统"
              />
            </Form.Item>
          ) : null}
        </Form>
      </Modal>

      <Modal
        title={editingEntity ? `编辑${getEntityCategoryLabel(entityTargetConcept?.level)}` : `新增${getEntityCategoryLabel(entityTargetConcept?.level)}`}
        open={entityModalVisible}
        onCancel={() => {
          setEntityModalVisible(false);
          setExplanationKeywordModalVisible(false);
        }}
        onOk={saveEntity}
        destroyOnHidden
      >
        <Form form={entityForm} layout="vertical">
          <Form.Item label="所属概念分类">
            <Input value={entityTargetConcept?.name || ''} disabled />
          </Form.Item>
          <Form.Item name="entity_name" label={`${getEntityCategoryLabel(entityTargetConcept?.level)}名称`} rules={[{ required: true, message: `请输入${getEntityCategoryLabel(entityTargetConcept?.level)}名称` }]}>
            <Input />
          </Form.Item>
          <Form.Item name="entity_en_name" label="落地英文表名">
            <Input />
          </Form.Item>
          <Form.Item name="entity_code" label={`${getEntityCategoryLabel(entityTargetConcept?.level)}编码`} rules={[{ required: true, message: `请输入${getEntityCategoryLabel(entityTargetConcept?.level)}编码` }]}>
            <Input disabled={!!editingEntity} />
          </Form.Item>
          <Form.Item label="解释（别名同义词）" extra="自动提取、字段选择、手工新增三路解耦维护；最终统一汇总到下方总表，任何一条都可以直接修改或删除。">
            <Space wrap style={{ marginBottom: 12 }}>
              <Button onClick={handleAutoSuggestExplanation} loading={loadingExplanationSuggest}>
                自动提取同义词
              </Button>
              <Button onClick={openExplanationKeywordPicker} disabled={!currentPropertyKeywordOptions.length}>
                从字段选择同义词
              </Button>
              <Button onClick={clearExplanationItems} disabled={!explanationItems.length}>
                清空全部
              </Button>
              <StatusTag preset="info">手工 {explanationStats.manual}</StatusTag>
              <StatusTag preset="ai">自动 {explanationStats.auto}</StatusTag>
              <StatusTag preset="info">字段 {explanationStats.field}</StatusTag>
              <Text type="secondary">总计 {explanationItems.length} 条</Text>
            </Space>

            <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
              <Input
                value={newManualExplanation}
                onChange={(e) => setNewManualExplanation(e.target.value)}
                onPressEnter={addManualExplanationItems}
                placeholder="输入手工同义词，支持逗号/分号批量录入"
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={addManualExplanationItems}>
                新增手工同义词
              </Button>
            </Space.Compact>

            <Table
              size="small"
              pagination={false}
              rowKey="id"
              dataSource={explanationItems}
              locale={{ emptyText: '暂无同义词，可先自动提取、从字段选择，或手工新增' }}
              columns={[
                {
                  title: '来源',
                  dataIndex: 'source',
                  width: 100,
                  render: (source: ExplanationSource) => (
                    <StatusTag preset={EXPLANATION_SOURCE_META[source].preset}>{EXPLANATION_SOURCE_META[source].label}</StatusTag>
                  ),
                },
                {
                  title: '同义词',
                  dataIndex: 'text',
                  render: (value: string, row: ExplanationItem) => (
                    <Input
                      value={value}
                      placeholder="请输入同义词"
                      onChange={(e) => updateExplanationItem(row.id, e.target.value)}
                    />
                  ),
                },
                {
                  title: '操作',
                  width: 90,
                  render: (_: any, row: ExplanationItem) => (
                    <Button danger type="link" size="small" onClick={() => removeExplanationItem(row.id)}>
                      删除
                    </Button>
                  ),
                },
              ]}
            />
            {explanationItems.length ? (
              <div style={{ marginTop: 12 }}>
                <Text type="secondary">最终保存值：</Text>
                <div style={{ marginTop: 8, color: 'var(--text-secondary)', wordBreak: 'break-all' }}>{explanationValue || '-'}</div>
              </div>
            ) : null}
          </Form.Item>
          <Form.Item name="sort_order" label="显示顺序">
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="data_layer" label="数据层级">
            <Select allowClear>
              <Select.Option value="ODS">ODS</Select.Option>
              <Select.Option value="DWD">DWD</Select.Option>
              <Select.Option value="DWS">DWS</Select.Option>
              <Select.Option value="ADS">ADS</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="is_main_table" label="是否主表" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="从字段选择关键词"
        open={explanationKeywordModalVisible}
        onCancel={() => setExplanationKeywordModalVisible(false)}
        onOk={applySelectedExplanationKeywords}
        destroyOnHidden
      >
        {currentPropertyKeywordOptions.length ? (
          <>
            <div style={{ color: 'var(--text-tertiary)', marginBottom: 12 }}>
              这里只维护“来自字段”的关键词。勾选后会写入解释字段，取消勾选后保存会真正移除；你手工录入的其它同义词不会受影响。
            </div>
            <Select
              mode="multiple"
              value={selectedExplanationKeywords}
              onChange={(values) => setSelectedExplanationKeywords(values)}
              style={{ width: '100%' }}
              placeholder="请选择要写入解释字段的属性关键词"
              options={currentPropertyKeywordOptions.map((item) => ({ label: item, value: item }))}
            />
          </>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前实体暂无可用属性关键词" />
        )}
      </Modal>

      <Modal
        title={editingPropertyIndex === null ? '新增属性' : '编辑属性'}
        open={propertyModalVisible}
        onCancel={() => setPropertyModalVisible(false)}
        onOk={saveProperty}
        destroyOnHidden
      >
        <Form form={propertyForm} layout="vertical">
          <Form.Item name="name" label="属性英文名" rules={[{ required: true, message: '请输入属性英文名' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="cnName" label="属性中文名" rules={[{ required: true, message: '请输入属性中文名' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select>
              <Select.Option value="string">string</Select.Option>
              <Select.Option value="int">int</Select.Option>
              <Select.Option value="float">float</Select.Option>
              <Select.Option value="boolean">boolean</Select.Option>
              <Select.Option value="datetime">datetime</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="isPrimaryKey" label="主键" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            name="enable_query_entity"
            label="参与问实体识别"
            valuePropName="checked"
            extra="开启后，该属性会作为问实体的关键属性参与识别。"
          >
            <Switch checkedChildren="参与" unCheckedChildren="不参与" />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 数据预览弹窗 */}
      <Modal
        title={previewTitle}
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={null}
        width={1100}
        destroyOnHidden
      >
        <Table
          size="small"
          loading={previewLoading}
          dataSource={previewRows}
          columns={previewColumns}
          rowKey={(_: any, i?: number) => String(i ?? 0)}
          pagination={{ pageSize: 10, showSizeChanger: true, size: 'small' }}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: '暂无预览数据' }}
        />
      </Modal>

    </Layout>
  );
};

export default ModelTreeManager;
