import React, { useEffect, useMemo, useState } from 'react';
import {
  Layout,
  Card,
  Space,
  Button,
  Form,
  message,
  Popconfirm,
  Upload,
  Checkbox,
} from 'antd';
import {
  PlusOutlined,
  ExportOutlined,
  ImportOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { conceptApi, entityApi, entityRelationManagerApi, mappingApi, kgApi, dataSourceApi } from '../services/api';
import { useStore } from '../store/useStore';
import {
  MODE_CONFIG,
  LEVEL_LABELS,
  getEntityCategoryLabel,
  buildExplanationItems,
  mergeExplanationItems,
  serializeExplanationItems,
  splitExplanationTerms,
  getPropertyKeywordOptions,
  buildTree,
  type Mode,
  type ExplanationItem,
} from './model-tree/modelTree';
import ModelTreeSidebar from './model-tree/ModelTreeSidebar';
import ModelDetailPanel from './model-tree/ModelDetailPanel';
import ModelFormDrawer from './model-tree/ModelFormDrawer';
import { useModelTreeQuery } from './model-tree/useModelTreeQuery';

const { Content } = Layout;

type Props = {
  mode: Mode;
  pageTitle: string;
  readOnly?: boolean;
  embedded?: boolean;
  onOpenTarget?: (menuKey: string) => void;
  initialEntityId?: string;  // 图谱抽屉传入：自动定位到该实体
};

const ModelTreeManager: React.FC<Props> = ({ mode, pageTitle, readOnly = false, embedded = false, onOpenTarget, initialEntityId }) => {
  const config = MODE_CONFIG[mode];
  const { relationHighlight, modelingInitialKey, setMappingFilterEntityId, setMappingJumpTab } = useStore();
  const {
    loading, concepts, setConcepts, allEntities, setAllEntities,
    selectedKey, setSelectedKey, expandedKeys, setExpandedKeys,
    setRelationRows, loadingDetail, setLoadingDetail,
    relationFilter, setRelationFilter,
    mergedRelations, filteredRelations, refreshData,
  } = useModelTreeQuery({ mode, config, initialEntityId });

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


  useEffect(() => {
    if (!relationHighlight || !allEntities.length || !concepts.length) return;
    const focusEntityId = mode === 'master' ? relationHighlight.masterEntityId : relationHighlight.activityEntityId;
    const focusEntity = allEntities.find((item: any) => item.id === focusEntityId);
    if (!focusEntity) return;
    const focusConcept = concepts.find((item: any) => item.id === focusEntity.concept_id);
    if (!focusConcept || focusConcept.level !== config.leafLevel) return;
    setRelationFilter('matrix');
    setSelectedKey(`entity-${focusEntityId}`);
  }, [allEntities, concepts, config.leafLevel, mode, relationHighlight, setRelationFilter, setSelectedKey]);

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
        console.error('[ModelTreeManager] 加载实体详情失败:', error);
        message.error('加载实体详情失败');
      } finally {
        setLoadingDetail(false);
      }
    };
    loadEntityDetails();
  }, [selectedMeta, setRelationRows, setLoadingDetail]);

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
    dataSourceApi.list({ silent: true }).then((res) => {
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


    return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <Card
        style={{ width: '100%', maxWidth: '100%', height: '100%', display: 'flex', flexDirection: 'column', boxShadow: embedded ? 'none' : undefined, overflow: 'hidden' }}
        styles={{ body: { padding: 0, flex: 1, overflow: 'hidden' } }}
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
            <ModelTreeSidebar
              rootName={config.rootName}
              readOnly={readOnly}
              loading={loading}
              treeData={treeData}
              selectedKey={selectedKey}
              expandedKeys={expandedKeys}
              onExpand={(keys) => setExpandedKeys(keys)}
              onSelect={(key) => setSelectedKey(key)}
            />
          )}
          <Content style={{ padding: 16, overflow: 'auto' }}>
            <ModelDetailPanel
              selectedMeta={selectedMeta}
              config={config}
              readOnly={readOnly}
              dataSources={dataSources}
              sourceMode={sourceMode}
              savingSourceMode={savingSourceMode}
              savingDataSource={savingDataSource}
              previewLoading={previewLoading}
              loadingDetail={loadingDetail}
              relationFilter={relationFilter}
              mergedRelations={mergedRelations}
              filteredRelations={filteredRelations}
              relationHighlight={relationHighlight}
              onSetSelectedKey={setSelectedKey}
              onOpenCreateChildConcept={openCreateChildConcept}
              onOpenCreateEntity={openCreateEntity}
              onOpenEditConcept={openEditConcept}
              onOpenEditEntity={openEditEntity}
              onDeleteConcept={deleteConcept}
              onDeleteEntity={deleteEntity}
              onOpenCreateProperty={openCreateProperty}
              onOpenEditProperty={openEditProperty}
              onDeleteProperty={deleteProperty}
              onConfigMapping={handleConfigMapping}
              onDataPreview={handleDataPreview}
              onSourceModeChange={handleSourceModeChange}
              onDataSourceChange={handleDataSourceChange}
              onRelationFilterChange={setRelationFilter}
            />
          </Content>
        </Layout>
      </Card>

      <ModelFormDrawer
        conceptForm={conceptForm}
        conceptModalMode={conceptModalMode}
        conceptModalVisible={conceptModalVisible}
        conceptFormLevel={conceptFormLevel}
        selectedMeta={selectedMeta}
        onCancelConcept={() => setConceptModalVisible(false)}
        onSaveConcept={saveConcept}
        entityForm={entityForm}
        editingEntity={editingEntity}
        entityTargetConcept={entityTargetConcept}
        entityModalVisible={entityModalVisible}
        loadingExplanationSuggest={loadingExplanationSuggest}
        explanationItems={explanationItems}
        explanationValue={explanationValue}
        explanationStats={explanationStats}
        currentPropertyKeywordOptions={currentPropertyKeywordOptions}
        newManualExplanation={newManualExplanation}
        onCancelEntity={() => {
          setEntityModalVisible(false);
          setExplanationKeywordModalVisible(false);
        }}
        onSaveEntity={saveEntity}
        onAutoSuggestExplanation={handleAutoSuggestExplanation}
        onOpenKeywordPicker={openExplanationKeywordPicker}
        onNewManualExplanationChange={setNewManualExplanation}
        onAddManualExplanation={addManualExplanationItems}
        onUpdateExplanationItem={updateExplanationItem}
        onRemoveExplanationItem={removeExplanationItem}
        onClearExplanationItems={clearExplanationItems}
        explanationKeywordModalVisible={explanationKeywordModalVisible}
        selectedExplanationKeywords={selectedExplanationKeywords}
        onCancelKeywordModal={() => setExplanationKeywordModalVisible(false)}
        onKeywordSelectChange={setSelectedExplanationKeywords}
        onApplyKeywords={applySelectedExplanationKeywords}
        propertyForm={propertyForm}
        editingPropertyIndex={editingPropertyIndex}
        propertyModalVisible={propertyModalVisible}
        onCancelProperty={() => setPropertyModalVisible(false)}
        onSaveProperty={saveProperty}
        previewTitle={previewTitle}
        previewOpen={previewOpen}
        previewLoading={previewLoading}
        previewRows={previewRows}
        previewColumns={previewColumns}
        onCancelPreview={() => setPreviewOpen(false)}
      />
    </Layout>
  );
};

export default ModelTreeManager;
