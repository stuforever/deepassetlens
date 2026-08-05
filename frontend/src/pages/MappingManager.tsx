import React, { useState, useEffect, useMemo } from 'react';
import { Card, Layout, TreeSelect, Table, Button, Space, Typography, Switch, Input, Row, Col, message, Empty, Upload, Divider, Tabs, Select, Collapse, Popconfirm, Modal, Form } from 'antd';
import { DatabaseOutlined, ApartmentOutlined, CodeOutlined, SaveOutlined, AppstoreOutlined, ThunderboltOutlined, UploadOutlined, DownloadOutlined, UnorderedListOutlined, ApiOutlined } from '@ant-design/icons';
import { conceptApi, sourceTableApi, mappingApi, uploadApi } from '../services/api';
import ApiMappingTab from '../components/ApiMappingTab';
import SqlIntegrationTab from '../components/SqlIntegrationTab';
import { TERMS, MAPPING_TEMPLATE_HEADERS } from '../constants/standardTerms';
import { useStore } from '../store/useStore';
import { PageShell, StatusTag } from '../components/shell';
import { tokens } from '../theme/tokens';

const { Content } = Layout;
const { Text } = Typography;
const { TextArea } = Input;

type Props = {
  onOpenTarget?: (menuKey: string) => void;
  initialTab?: string;
  visibleTabs?: string[];
};

const MappingManager: React.FC<Props> = ({ onOpenTarget, initialTab = '1', visibleTabs }) => {
  const { mappingFilterEntityId, setMappingFilterEntityId, mappingJumpTab, setMappingJumpTab } = useStore();
  const [activeTab, setActiveTab] = useState(initialTab);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [ruleModalMode, setRuleModalMode] = useState<'create' | 'edit' | 'view'>('create');
  const [ruleName, setRuleName] = useState('');
  const [sourceTableIds, setSourceTableIds] = useState<string[]>([]);
  const [entityIds, setEntityIds] = useState<string[]>([]);
  const [sqlContent, setSqlContent] = useState('');
  
  // 字段级映射关系状态 { "entityId_propName": ["sourceId_colName1", "sourceId_colName2"] }
  const [fieldMappings, setFieldMappings] = useState<Record<string, string[]>>({});
  // 字段级映射规则说明 { "entityId_propName": "description" }
  const [mappingDesc, setMappingDesc] = useState<Record<string, string>>({});

  const [dbEntities, setDbEntities] = useState<any[]>([]);
  const [dbConcepts, setDbConcepts] = useState<any[]>([]);
  
  const [sourceMaster, setSourceMaster] = useState<any[]>([]);
  const [sourceBusiness, setSourceBusiness] = useState<any[]>([]);
  const [sourceReference, setSourceReference] = useState<any[]>([]);
  const [mappingRules, setMappingRules] = useState<any[]>([]);
  const [currentRuleId, setCurrentRuleId] = useState<string | null>(null);
  const [viewingRuleId, setViewingRuleId] = useState<string | null>(null);
  const [viewingRuleName, setViewingRuleName] = useState('');
  const [viewSourceTableIds, setViewSourceTableIds] = useState<string[]>([]);
  const [viewEntityIds, setViewEntityIds] = useState<string[]>([]);
  const [viewFieldMappings, setViewFieldMappings] = useState<Record<string, string[]>>({});
  const [viewMappingDesc, setViewMappingDesc] = useState<Record<string, string>>({});
  const [viewMainSourceTableId, setViewMainSourceTableId] = useState<string>('');
  const [viewPkOverrides, setViewPkOverrides] = useState<Record<string, boolean>>({});
  const [viewSqlContent, setViewSqlContent] = useState('');
  const [queryKeyword, setQueryKeyword] = useState('');
  const [queryEntityId, setQueryEntityId] = useState<string>('');
  const [querySourceTableId, setQuerySourceTableId] = useState<string>('');
  const [detailEntityId, setDetailEntityId] = useState<string>('');
  const [detailSourceTableId, setDetailSourceTableId] = useState<string>('');
  const [sqlPreviewOpen, setSqlPreviewOpen] = useState(false);
  const [sqlPreviewContent, setSqlPreviewContent] = useState('');
  const [sqlPreviewTitle, setSqlPreviewTitle] = useState('');
  const [mainSourceTableId, setMainSourceTableId] = useState<string>('');
  const [pkOverrides, setPkOverrides] = useState<Record<string, boolean>>({});
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [previewTitle, setPreviewTitle] = useState('');
  const [fieldPickerOpen, setFieldPickerOpen] = useState(false);
  const [fieldPickerTitle, setFieldPickerTitle] = useState('');
  const [fieldPickerEntityId, setFieldPickerEntityId] = useState('');
  const [fieldPickerPropName, setFieldPickerPropName] = useState('');
  const [fieldPickerTableId, setFieldPickerTableId] = useState<string>('');
  const [fieldPickerTempValues, setFieldPickerTempValues] = useState<string[]>([]);

  // 存储已拉取到的源表字段信息 { tableId: fieldsArray }
  const [sourceTableFields, setSourceTableFields] = useState<Record<string, any[]>>({});
  const [jumpFromGraph, setJumpFromGraph] = useState(false);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  // 监听来自图谱建模页/数据来源配置的跳转请求
  useEffect(() => {
    if (mappingFilterEntityId) {
      setQueryEntityId(mappingFilterEntityId);
      setActiveTab(mappingJumpTab || '1'); // 按来源模式跳转对应 Tab
      setJumpFromGraph(true);
      // 清理状态，防止刷新时反复跳转
      setMappingFilterEntityId(null);
      setMappingJumpTab(null);
    }
  }, [mappingFilterEntityId, mappingJumpTab, setMappingFilterEntityId, setMappingJumpTab]);

  const getLandingTableEnName = (e: any) =>
    e?.landing_table_en_name || e?.entity_en_name || '';

  const normalizeUuid = (v: any) => String(v || '').toLowerCase();
  const ruleModalReadOnly = ruleModalMode === 'view';

  const preloadFieldsByTableIds = async (tableIds: string[], sourceRes: any) => {
    const allTables = [
      ...(sourceRes?.data?.data?.master || []),
      ...(sourceRes?.data?.data?.business || []),
      ...(sourceRes?.data?.data?.reference || []),
    ];
    for (const tableId of tableIds || []) {
      const tableInfo = allTables.find((t: any) => String(t.id) === String(tableId));
      if (!tableInfo) continue;
      try {
        const fRes = await uploadApi.getSourceTableFields(tableInfo.sysCode, tableInfo.enName);
        setSourceTableFields(prev => ({
          ...prev,
          [tableId]: fRes.data.fields || []
        }));
      } catch (e) {
        console.error('Failed to pre-fetch fields for', tableInfo.enName);
      }
    }
  };

  // Fetch saved mapping rules list only (不默认选中)
  const fetchMappingRules = async (sourceRes: any) => {
    try {
      const res = await mappingApi.getMappingRules();
      const rules = res.data?.data || [];
      setMappingRules(rules);

      // 不自动带入编辑区，只为映射信息查看预加载字段中文名
      // 兼容历史脏数据：source_table_ids 可能被错误写成 "tableId_fieldPrefix"
      const allTables = [
        ...(sourceRes?.data?.data?.master || []),
        ...(sourceRes?.data?.data?.business || []),
        ...(sourceRes?.data?.data?.reference || []),
      ];
      const allRuleTableIds = new Set<string>();
      rules.forEach((r: any) => {
        (r.source_table_ids || []).forEach((id: string) => {
          if (allTables.some((t: any) => String(t.id) === String(id))) {
            allRuleTableIds.add(String(id));
          }
        });
        const mappings = r.field_mappings || {};
        Object.keys(mappings).forEach(k => {
          const m = mappings[k];
          const values = Array.isArray(m?.source) ? m.source : (typeof m === 'string' ? [m] : []);
          values.forEach((mv: string) => {
            const table = allTables.find((t: any) => mv?.startsWith(`${String(t.id)}_`));
            if (table) allRuleTableIds.add(String(table.id));
          });
        });
      });
      await preloadFieldsByTableIds(Array.from(allRuleTableIds), sourceRes);
    } catch (e) {
      console.error('Failed to load mapping rules', e);
    }
  };

  const buildRuleWorkspace = (rule: any, sourceRes: any) => {
    const allKnownTableIdSet = new Set(
      [
        ...(sourceRes?.data?.data?.master || []),
        ...(sourceRes?.data?.data?.business || []),
        ...(sourceRes?.data?.data?.reference || []),
      ].map((t: any) => String(t.id))
    );
    const ids = (rule?.source_table_ids || []).filter((id: string) => allKnownTableIdSet.has(String(id)));

    const newFieldMappings: Record<string, string[]> = {};
    const newMappingDesc: Record<string, string> = {};
    const newRowSourceTableFilter: Record<string, string> = {};
    const newPkOverrides: Record<string, boolean> = {};
    const rawMappings = rule?.field_mappings || {};
    Object.keys(rawMappings).forEach(k => {
      if (k === '__meta__') return;
      const val = rawMappings[k];
      if (val && typeof val === 'object' && val.source) {
        newFieldMappings[k] = Array.isArray(val.source) ? val.source : [val.source];
        newMappingDesc[k] = val.desc || '';
      } else {
        newFieldMappings[k] = typeof val === 'string' ? [val] : (val || []);
      }

      // 反填“来源表英文名”下拉：按当前字段映射的第一条来源字段解析表ID
      const firstMappingVal = (newFieldMappings[k] || [])[0];
      if (firstMappingVal) {
        const { tableId } = parseMappingValue(firstMappingVal);
        if (tableId) {
          newRowSourceTableFilter[k] = tableId;
        }
      }

      // 历史兼容：如果某条规则在字段项上保存了主键信息，则回填
      if (val && typeof val === 'object' && typeof val.is_pk === 'boolean') {
        newPkOverrides[k] = !!val.is_pk;
      }
    });

    // 元信息回填：主表标记 + 主键覆盖
    const meta = rawMappings?.__meta__;
    if (meta && typeof meta === 'object') {
      if (meta.primary_key_overrides && typeof meta.primary_key_overrides === 'object') {
        Object.assign(newPkOverrides, meta.primary_key_overrides);
      }
    }

    return {
      ruleId: rule?.id || null,
      ruleName: rule?.name || '',
      sourceTableIds: ids,
      entityIds: rule?.entity_ids || [],
      fieldMappings: newFieldMappings,
      mappingDesc: newMappingDesc,
      rowSourceTableFilter: newRowSourceTableFilter,
      pkOverrides: newPkOverrides,
      mainSourceTableId: meta?.main_source_table_id ? String(meta.main_source_table_id) : '',
      sqlContent: rule?.sql_content || '',
    };
  };

  const resetEditorWorkspace = () => {
    setCurrentRuleId(null);
    setRuleName('');
    setSourceTableIds([]);
    setEntityIds([]);
    setFieldMappings({});
    setMappingDesc({});
    setPkOverrides({});
    setMainSourceTableId('');
    setRowSourceTableFilter({});
    setSqlContent('');
  };

  const resetViewerWorkspace = () => {
    setViewingRuleId(null);
    setViewingRuleName('');
    setViewSourceTableIds([]);
    setViewEntityIds([]);
    setViewFieldMappings({});
    setViewMappingDesc({});
    setViewMainSourceTableId('');
    setViewPkOverrides({});
    setViewSqlContent('');
  };

  const resetQueryFilters = () => {
    setQueryKeyword('');
    setQueryEntityId('');
    setQuerySourceTableId('');
  };

  const loadRuleToEditor = async (rule: any, sourceRes: any, switchToConfig = false) => {
    const workspace = buildRuleWorkspace(rule, sourceRes);
    setCurrentRuleId(workspace.ruleId);
    setRuleName(workspace.ruleName);
    setSourceTableIds(workspace.sourceTableIds);
    setEntityIds(workspace.entityIds);
    setFieldMappings(workspace.fieldMappings);
    setMappingDesc(workspace.mappingDesc);
    setRowSourceTableFilter(workspace.rowSourceTableFilter);
    setPkOverrides(workspace.pkOverrides);
    setMainSourceTableId(workspace.mainSourceTableId);
    setSqlContent(workspace.sqlContent);
    await preloadFieldsByTableIds(workspace.sourceTableIds, sourceRes);
    if (switchToConfig) {
      setActiveTab('1');
    }
  };

  const loadRuleToViewer = async (rule: any, sourceRes: any) => {
    const workspace = buildRuleWorkspace(rule, sourceRes);
    setViewingRuleId(workspace.ruleId);
    setViewingRuleName(workspace.ruleName);
    setViewSourceTableIds(workspace.sourceTableIds);
    setViewEntityIds(workspace.entityIds);
    setViewFieldMappings(workspace.fieldMappings);
    setViewMappingDesc(workspace.mappingDesc);
    setViewMainSourceTableId(workspace.mainSourceTableId);
    setViewPkOverrides(workspace.pkOverrides);
    setViewSqlContent(workspace.sqlContent);
    await preloadFieldsByTableIds(workspace.sourceTableIds, sourceRes);
    setActiveTab('1');
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 统一从 concepts 拉取，确保实体落地英文表名(entity_en_name)可见
        const conceptRes = await conceptApi.getConcepts();
        const concepts = conceptRes?.data || [];
        setDbConcepts(concepts);
        const entities = concepts.flatMap((c: any) =>
          (c.entities || []).map((e: any) => ({
            ...e,
            label: e.entity_name,
            type: 'entity',
            concept_id: c.id,
          }))
        );
        setDbEntities(entities);

        // Fetch source tables
        const sourceRes = await sourceTableApi.getAllTables();
        setSourceMaster(sourceRes.data.data.master || []);
        setSourceBusiness(sourceRes.data.data.business || []);
        setSourceReference(sourceRes.data.data.reference || []);
        
        // 数据加载完毕后，尝试拉取已保存的规则
        await fetchMappingRules(sourceRes);
        // 支持从图谱详情跳转到映射信息查看
        try {
          const raw = sessionStorage.getItem('mapping_jump_params');
          if (raw) {
            const jump = JSON.parse(raw);
            if (jump?.from === 'graph_detail') {
              setJumpFromGraph(true);
              setActiveTab('1');
              if (jump?.entity_id) {
                const jumpEntityId = String(jump.entity_id);
                setQueryEntityId(jumpEntityId);
                setViewEntityIds([jumpEntityId]);
              }
            }
            sessionStorage.removeItem('mapping_jump_params');
          }
        } catch {}
      } catch (error) {
        console.error('Failed to fetch mapping dependencies:', error);
      }
    };
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 构建源表 TreeData (按系统名称分组)
  const sourceTreeData = useMemo(() => {
    const buildTree = (data: any[], typeLabel: string) => {
      const sysMap = new Map<string, any[]>();
      data.forEach(item => {
        const sys = item.sysName || '未知系统';
        if (!sysMap.has(sys)) sysMap.set(sys, []);
        sysMap.get(sys)!.push(item);
      });
      return Array.from(sysMap.entries()).map(([sys, items]) => ({
        title: sys,
        value: `sys_${typeLabel}_${sys}`,
        selectable: false,
        children: items.map(item => ({
          title: `${item.enName || '未知'} (${item.cnName || '未知'})`,
          value: item.id, // 用真实 ID
          isTable: true,
          tableData: item
        }))
      }));
    };

    return [
      {
        title: '主数据来源表',
        value: 'type_master',
        selectable: false,
        children: buildTree(sourceMaster, 'master')
      },
      {
        title: '业务数据来源表',
        value: 'type_business',
        selectable: false,
        children: buildTree(sourceBusiness, 'business')
      },
      {
        title: '参考数据来源表',
        value: 'type_reference',
        selectable: false,
        children: buildTree(sourceReference, 'reference')
      }
    ];
  }, [sourceMaster, sourceBusiness, sourceReference]);

  // 构建实体 TreeData (按概念分组)
  const entityTreeData = useMemo(() => {
    // 过滤出有实体的概念节点
    const conceptsWithEntities = dbConcepts.filter(c => c.entities && c.entities.length > 0);
    
    return conceptsWithEntities.map(c => ({
      title: `L${c.level || '-'}：${c.name || '未命名概念'}`,
      value: `concept_${c.id}`,
      selectable: false,
      children: c.entities.map((e: any) => ({
        title: `${e.entity_name} (${e.entity_code})`,
        value: e.id,
        entityData: e
      }))
    }));
  }, [dbConcepts]);

  // 由概念中的实体明细建立 id -> 实体元信息映射，保证中英文名口径一致
  const entityMetaById = useMemo(() => {
    const map: Record<string, any> = {};
    dbConcepts.forEach((c: any) => {
      (c.entities || []).forEach((e: any) => {
        map[String(e.id)] = e;
      });
    });
    return map;
  }, [dbConcepts]);

  // 找出被选中的源表
  const selectedSourceTables = useMemo(() => {
    const allTables = [...sourceMaster, ...sourceBusiness, ...sourceReference];
    return allTables.filter(t => sourceTableIds.some(id => String(id) === String(t.id)));
  }, [sourceTableIds, sourceMaster, sourceBusiness, sourceReference]);

  // 找出被选中的实体
  const selectedEntities = useMemo(() => {
    return dbEntities
      .filter(e => entityIds.includes(e.id))
      .map(e => ({
        ...e,
        ...(entityMetaById[String(e.id)] || {}),
      }));
  }, [entityIds, dbEntities, entityMetaById]);

  const viewSelectedSourceTables = useMemo(() => {
    const allTables = [...sourceMaster, ...sourceBusiness, ...sourceReference];
    return allTables.filter(t => viewSourceTableIds.some(id => String(id) === String(t.id)));
  }, [viewSourceTableIds, sourceMaster, sourceBusiness, sourceReference]);

  const viewSelectedEntities = useMemo(() => {
    return dbEntities
      .filter(e => viewEntityIds.includes(e.id))
      .map(e => ({
        ...e,
        ...(entityMetaById[String(e.id)] || {}),
      }));
  }, [viewEntityIds, dbEntities, entityMetaById]);

  const filteredMappingRules = useMemo(() => {
    const kw = queryKeyword.trim().toLowerCase();
    return mappingRules.filter((rule: any) => {
      const hitKeyword = !kw || [
        rule?.name || '',
        rule?.id || '',
        ...(rule?.entity_ids || []),
        ...(rule?.source_table_ids || []),
      ].some((x: any) => String(x || '').toLowerCase().includes(kw));
      const hitEntity = !queryEntityId || (rule?.entity_ids || []).some((id: string) => String(id) === String(queryEntityId));
      const hitTable = !querySourceTableId || (rule?.source_table_ids || []).some((id: string) => String(id) === String(querySourceTableId));
      return hitKeyword && hitEntity && hitTable;
    });
  }, [mappingRules, queryKeyword, queryEntityId, querySourceTableId]);

  const mappingInfoRows = useMemo(() => {
    const rows: any[] = [];
    const allTables = [...sourceMaster, ...sourceBusiness, ...sourceReference];
    mappingRules.forEach((rule: any) => {
      const rawMappings = rule?.field_mappings || {};
      Object.keys(rawMappings).forEach((key) => {
        if (key === '__meta__') return;
        const mapping = rawMappings[key];
        const entityId = key.split('_')[0];
        const propEn = key.slice(entityId.length + 1);
        const entity = (entityMetaById[String(entityId)] || dbEntities.find((e) => String(e.id) === String(entityId))) || {};
        const prop = (entity?.properties_schema || []).find((p: any) => String(p.name) === String(propEn)) || {};
        const sourceValues = Array.isArray(mapping?.source) ? mapping.source : (mapping?.source ? [mapping.source] : (typeof mapping === 'string' ? [mapping] : []));
        const tableIds = new Set<string>();
        const tableEns: string[] = [];
        const tableCns: string[] = [];
        const sysNames: string[] = [];
        const fieldEns: string[] = [];
        const fieldCns: string[] = [];
        sourceValues.forEach((mv: string) => {
          const { tableId, fieldEn } = parseMappingValue(mv);
          if (!tableId) return;
          tableIds.add(String(tableId));
          fieldEns.push(fieldEn);
          const table = allTables.find((t) => String(t.id) === String(tableId));
          if (table) {
            tableEns.push(table.enName || '');
            tableCns.push(table.cnName || '');
            sysNames.push(table.sysName || table.sysCode || '');
          }
          const fieldInfo = (sourceTableFields[tableId] || []).find((f: any) => String(f.field_en) === String(fieldEn));
          fieldCns.push(fieldInfo?.field_cn || '');
        });
        rows.push({
          key: `${rule.id}_${propEn}`,
          ruleId: rule.id,
          ruleName: rule.name || '',
          entityId: String(entityId),
          entityCode: entity?.entity_code || '',
          entityName: entity?.entity_name || entity?.label || '',
          entityLandingTableEn: getLandingTableEnName(entity) || '',
          propEn,
          propCn: prop?.cnName || '',
          propType: prop?.type || '',
          isPk: mapping?.is_pk ? '是' : '否',
          sysName: Array.from(new Set(sysNames)).join(' | '),
          tableIds: Array.from(tableIds),
          tableEn: Array.from(new Set(tableEns)).join(' | '),
          tableCn: Array.from(new Set(tableCns)).join(' | '),
          fieldEn: fieldEns.join(' | '),
          fieldCn: fieldCns.join(' | '),
          desc: mapping?.desc || '',
        });
      });
    });
    return rows.filter((row) => {
      const hitEntity = !detailEntityId || String(row.entityId) === String(detailEntityId);
      const hitTable = !detailSourceTableId || row.tableIds.some((id: string) => String(id) === String(detailSourceTableId));
      return hitEntity && hitTable;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mappingRules, entityMetaById, dbEntities, sourceMaster, sourceBusiness, sourceReference, sourceTableFields, detailEntityId, detailSourceTableId]);

  // 当前实体正在配置时，用户在特定行下拉选择的过滤源表ID
  const [rowSourceTableFilter, setRowSourceTableFilter] = useState<Record<string, string>>({});

  function parseMappingValue(mappingVal: string) {
    const allTables = [...sourceMaster, ...sourceBusiness, ...sourceReference];
    if (!mappingVal || !mappingVal.includes('_')) {
      return { tableId: '', fieldEn: '' };
    }

    // 关键修复：字段英文名里可能含有下划线，不能直接 split('_') + pop()
    // 按“已知 tableId 前缀”匹配，剩余部分整体作为字段英文名。
    const matchedTable = allTables.find(t => mappingVal.startsWith(`${String(t.id)}_`));
    if (matchedTable) {
      const tableId = String(matchedTable.id);
      const fieldEn = mappingVal.slice(tableId.length + 1);
      return { tableId, fieldEn };
    }

    // 回退策略：按第一个下划线切分，避免整条失败
    const idx = mappingVal.indexOf('_');
    return {
      tableId: idx > -1 ? mappingVal.slice(0, idx) : '',
      fieldEn: idx > -1 ? mappingVal.slice(idx + 1) : '',
    };
  }

  const handleRowSourceTableChange = (entityId: string, propName: string, tableId: string) => {
    const key = `${entityId}_${propName}`;
    setRowSourceTableFilter(prev => ({
      ...prev,
      [key]: tableId
    }));
  };

  const handlePkChange = (entityId: string, propName: string, checked: boolean) => {
    const key = `${entityId}_${propName}`;
    setPkOverrides(prev => ({
      ...prev,
      [key]: checked
    }));
  };

  const handleMappingChange = (entityId: string, propName: string, sourceCols: string[]) => {
    const key = `${entityId}_${propName}`;
    setFieldMappings(prev => ({
      ...prev,
      [key]: sourceCols
    }));
  };

  const handleMappingDescChange = (entityId: string, propName: string, desc: string) => {
    const key = `${entityId}_${propName}`;
    setMappingDesc(prev => ({
      ...prev,
      [key]: desc
    }));
  };

  const normalizeName = (v: string) => (v || '').toLowerCase().replace(/[\s_-]/g, '');

  const openFieldPicker = (entity: any, record: any) => {
    const key = `${entity.id}_${record.name}`;
    const current = fieldMappings[key] || [];
    const tableId = rowSourceTableFilter[key] || '';
    setFieldPickerEntityId(entity.id);
    setFieldPickerPropName(record.name);
    setFieldPickerTableId(tableId);
    setFieldPickerTempValues(Array.isArray(current) ? [...current] : []);
    setFieldPickerTitle(`${entity.entity_name || entity.label}.${record.name} - 来源字段多选`);
    setFieldPickerOpen(true);
  };

  const saveFieldPicker = () => {
    handleMappingChange(fieldPickerEntityId, fieldPickerPropName, fieldPickerTempValues);
    if (fieldPickerTempValues.length > 0) {
      const { tableId } = parseMappingValue(fieldPickerTempValues[0]);
      if (tableId) handleRowSourceTableChange(fieldPickerEntityId, fieldPickerPropName, tableId);
    }
    setFieldPickerOpen(false);
  };

  const handleSourceTableChange = async (vals: string[]) => {
    setSourceTableIds(vals);
    // 若主表已不在已选来源表中，则清空主表标记
    if (mainSourceTableId && !vals.some(v => String(v) === String(mainSourceTableId))) {
      setMainSourceTableId('');
    }
    const allowedTableIdSet = new Set(vals.map(v => String(v)));
    setFieldMappings(prev => {
      const next: Record<string, any> = {};
      Object.keys(prev || {}).forEach((k) => {
        const raw = (prev as any)[k];
        const arr = typeof raw === 'string' ? [raw] : (Array.isArray(raw) ? raw : []);
        const filtered = arr.filter((mv: any) => {
          if (typeof mv !== 'string') return false;
          if (!mv.includes('_')) return true;
          const { tableId } = parseMappingValue(mv);
          if (!tableId) return true;
          return allowedTableIdSet.has(String(tableId));
        });
        next[k] = filtered;
      });
      return next;
    });
    setRowSourceTableFilter(prev => {
      const next = { ...(prev || {}) };
      Object.keys(next).forEach((k) => {
        const v = next[k];
        if (v && !allowedTableIdSet.has(String(v))) {
          next[k] = '';
        }
      });
      return next;
    });
    for (const tableId of vals) {
      if (!sourceTableFields[tableId]) {
        // 找出对应的表信息以获取 sysCode 和 enName
        const allTables = [...sourceMaster, ...sourceBusiness, ...sourceReference];
        const tableInfo = allTables.find(t => String(t.id) === String(tableId));
        if (tableInfo) {
          try {
            const res = await uploadApi.getSourceTableFields(tableInfo.sysCode, tableInfo.enName);
            setSourceTableFields(prev => ({
              ...prev,
              [tableId]: res.data.fields || []
            }));
          } catch (e) {
            console.error('Failed to fetch fields for', tableInfo.enName);
          }
        }
      }
    }
  };

  const autoMatchFields = () => {
    let matchedCount = 0;
    const newMappings = { ...fieldMappings };
    const newRowSourceTableFilter = { ...rowSourceTableFilter };

    selectedEntities.forEach(entity => {
      const props = entity.properties_schema || [];
      props.forEach((prop: any) => {
        const key = `${entity.id}_${prop.name}`;
        // 只有当前未映射的属性才进行自动匹配
        if (!newMappings[key] || newMappings[key].length === 0) {
          let matchedSourceCols: string[] = [];
          
          // 在已选源表的所有字段中寻找匹配项（大小写/下划线/中划线/空格不敏感）
          const propNameNorm = normalizeName(prop.name || '');
          const propCnNorm = normalizeName(prop.cnName || '');
          for (const tableId of sourceTableIds) {
            const fields = sourceTableFields[tableId] || [];
            const match = fields.find(f => 
              normalizeName(f.field_en || '') === propNameNorm ||
              normalizeName(f.field_cn || '') === propCnNorm ||
              normalizeName(f.field_en || '').includes(propNameNorm) ||
              (propNameNorm && propNameNorm.includes(normalizeName(f.field_en || '')))
            );
            
            if (match) {
              matchedSourceCols.push(`${tableId}_${match.field_en}`);
              newRowSourceTableFilter[key] = tableId;
              break; // 自动匹配时找到一个就跳出当前表循环，通常匹配最像的那个
            }
          }

          if (matchedSourceCols.length > 0) {
            newMappings[key] = matchedSourceCols;
            matchedCount++;
          }
        }
      });
    });

    setFieldMappings(newMappings);
    setRowSourceTableFilter(newRowSourceTableFilter);
    message.success(`自动匹配完成，共新增 ${matchedCount} 个字段映射`);
  };

  const generateSqlTemplate = () => {
    if (sourceTableIds.length === 0 || entityIds.length === 0) {
      message.warning('请选择源表和目标实体');
      return;
    }
    
    let sql = `-- 复杂 SQL 转换模板\nSELECT\n`;
    
    // 取第一个选中的实体做示范
    const entity = selectedEntities[0];
    const props = entity?.properties_schema || [];
    
    const usedTableIds = new Set<string>();
    props.forEach((prop: any) => {
      const mappingVals = fieldMappings[`${entity.id}_${prop.name}`] || [];
      mappingVals.forEach((val: string) => {
        const { tableId } = parseMappingValue(val);
        if (tableId) usedTableIds.add(String(tableId));
      });
    });
    if (usedTableIds.size === 0 && selectedSourceTables.length > 0) {
      usedTableIds.add(String(selectedSourceTables[0].id));
    }

    const usedTables = Array.from(usedTableIds)
      .map(tableId => selectedSourceTables.find(t => String(t.id) === String(tableId)))
      .filter(Boolean) as any[];
    const aliasByTableId: Record<string, string> = {};
    usedTables.forEach((t, idx) => {
      aliasByTableId[String(t.id)] = `T${idx + 1}`;
    });

    const selectLines = props.map((prop: any) => {
      const mappingVals = fieldMappings[`${entity.id}_${prop.name}`] || [];
      if (mappingVals.length > 0) {
        // 如果有多个，用 COALESCE 示范一下
        if (mappingVals.length > 1) {
          const colRefs = mappingVals.map(val => {
            const { tableId, fieldEn: colName } = parseMappingValue(val);
            const alias = aliasByTableId[String(tableId)] || 'T1';
            return `${alias}.${colName}`;
          });
          return `  COALESCE(${colRefs.join(', ')}) AS ${prop.name}`;
        } else {
          const val = mappingVals[0];
          const { tableId, fieldEn: colName } = parseMappingValue(val);
          const alias = aliasByTableId[String(tableId)] || 'T1';
          return `  ${alias}.${colName} AS ${prop.name}`;
        }
      } else {
        return `  NULL AS ${prop.name} -- 暂无映射`;
      }
    });

    sql += selectLines.join(',\n');
    
    sql += `\nFROM `;
    usedTables.forEach((t, idx) => {
      const alias = aliasByTableId[String(t.id)];
      if (idx === 0) {
        sql += `${t.enName} ${alias}\n`;
      } else {
        const baseAlias = aliasByTableId[String(usedTables[0].id)];
        sql += `LEFT JOIN ${t.enName} ${alias} ON ${alias}.ID = ${baseAlias}.ID -- 请修改JOIN条件\n`;
      }
    });

    setSqlContent(sql);
    message.success('已根据当前字段映射生成 SQL 模板');
  };

  const handleExportTemplate = () => {
    let csv = `${MAPPING_TEMPLATE_HEADERS.join(',')}\n`;
    
    // Dump current mappings
    selectedEntities.forEach(entity => {
      const props = entity.properties_schema || [];
      props.forEach((prop: any) => {
        const key = `${entity.id}_${prop.name}`;
        let mappingVals = fieldMappings[key] || [];
        // 兼容旧的单字符串映射值
        if (typeof mappingVals === 'string') {
          mappingVals = [mappingVals];
        }
        const desc = mappingDesc[key] || '';
        
        let tableEns = new Set<string>();
        let fieldEns: string[] = [];
        
        mappingVals.forEach(mappingVal => {
          if (mappingVal && mappingVal.includes('_')) {
             const { tableId, fieldEn } = parseMappingValue(mappingVal);
             fieldEns.push(fieldEn || '');
             const tableInfo = [...sourceMaster, ...sourceBusiness, ...sourceReference].find(t => String(t.id) === String(tableId));
             if (tableInfo?.enName) tableEns.add(tableInfo.enName);
          }
        });
        
        csv += `${entity.entity_code || entity.label},${getLandingTableEnName(entity) || ''},${prop.name},${Array.from(tableEns).join('|')},${fieldEns.join('|')},${desc},\n`;
      });
    });
    
    if (sqlContent) {
       const escapedSql = `"${sqlContent.replace(/"/g, '""')}"`;
       const lines = csv.split('\n');
       if (lines.length > 1) {
          lines[1] = lines[1].replace(/,$/, `,${escapedSql}`);
       } else {
          lines.push(`,,,,,,${escapedSql}`);
       }
       csv = lines.join('\n');
    }

    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', '映射规则导入模板.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleImportCSV = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const rows = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n').filter(row => row.trim());
      
      const newFieldMappings = { ...fieldMappings };
      const newMappingDesc = { ...mappingDesc };
      let importedSql = sqlContent;
      let newSourceTableIds = new Set(sourceTableIds);
      let newEntityIds = new Set(entityIds);

      const allTables = [...sourceMaster, ...sourceBusiness, ...sourceReference];

      const headerCols = rows[0].split(',').map(c => c.trim());
      const hasEntityEnColumn = headerCols.includes('实体英文名称') || headerCols.includes('实体落地英文表名');

      for (let i = 1; i < rows.length; i++) {
        // Simple CSV parser ignoring commas inside quotes
        const cols = [];
        let current = '';
        let inQuotes = false;
        for (let char of rows[i]) {
            if (char === '"') inQuotes = !inQuotes;
            else if (char === ',' && !inQuotes) { cols.push(current); current = ''; }
            else current += char;
        }
        cols.push(current);
        
        if (cols.length < 5) continue;

        const entityCode = cols[0]?.trim();
        const entityEnName = hasEntityEnColumn ? (cols[1]?.trim() || '') : '';
        const propName = hasEntityEnColumn ? cols[2]?.trim() : cols[1]?.trim();
        const tableEnStr = hasEntityEnColumn ? (cols[3]?.trim() || '') : (cols[2]?.trim() || '');
        const fieldEnStr = hasEntityEnColumn ? (cols[4]?.trim() || '') : (cols[3]?.trim() || '');
        const desc = hasEntityEnColumn ? cols[5]?.trim() : cols[4]?.trim();
        const sqlStr = hasEntityEnColumn ? cols[6]?.trim() : cols[5]?.trim();

        const entity = dbEntities.find(e =>
          e.entity_code === entityCode ||
          e.entity_name === entityCode ||
          e.label === entityCode ||
          (entityEnName && getLandingTableEnName(e) === entityEnName)
        );
        
        if (entity) newEntityIds.add(entity.id);
        
        const tableEns = tableEnStr.split('|').map(s => s.trim()).filter(Boolean);
        const fieldEns = fieldEnStr.split('|').map(s => s.trim()).filter(Boolean);

        if (entity && propName && fieldEns.length > 0) {
          const key = `${entity.id}_${propName}`;
          const currentCols: string[] = [];
          
          // 尝试去匹配每一列表，如果只有一张表就默认都是这张表，如果有多个表则按顺序匹配
          fieldEns.forEach((fieldEn, index) => {
            const tableEn = tableEns[index] || tableEns[0];
            const table = allTables.find(t => t.enName === tableEn);
            if (table) {
              newSourceTableIds.add(table.id);
              currentCols.push(`${table.id}_${fieldEn}`);
            }
          });
          
          if (currentCols.length > 0) {
            newFieldMappings[key] = currentCols;
            if (desc) {
              newMappingDesc[key] = desc;
            }
          }
        }
        
        if (sqlStr) {
          importedSql = sqlStr.replace(/""/g, '"');
        }
      }
      
      const newTableIdsArray = Array.from(newSourceTableIds);
      setSourceTableIds(newTableIdsArray);
      setEntityIds(Array.from(newEntityIds));
      setFieldMappings(newFieldMappings);
      setMappingDesc(newMappingDesc);
      if (importedSql) setSqlContent(importedSql);
      
      handleSourceTableChange(newTableIdsArray);
      message.success('映射规则导入成功！');
    };
    reader.readAsText(file, 'utf-8');
    return false;
  };

  const handleSave = async () => {
    if (sourceTableIds.length === 0 || entityIds.length === 0) {
      message.warning('请至少选择一个源表和一个目标实体！');
      return;
    }
    if (entityIds.length !== 1) {
      message.error('当前版本：映射规则必须且只能选择一个目标实体');
      return;
    }
    if (!currentRuleId) {
      const targetEntityId = String(entityIds[0]);
      const targetEntity = (entityMetaById[targetEntityId] || dbEntities.find((e) => String(e.id) === targetEntityId)) || {};
      const targetEntityName = String(targetEntity?.entity_name || targetEntity?.label || '').trim();
      const normTarget = targetEntityName.toLowerCase();
      const conflict = mappingRules.find((r: any) => {
        const eid = String((r?.entity_ids || [])[0] || '');
        const ent = (entityMetaById[eid] || dbEntities.find((e) => String(e.id) === eid)) || {};
        const n = String(ent?.entity_name || ent?.label || '').trim().toLowerCase();
        return n && normTarget && n === normTarget;
      });
      if (conflict) {
        message.error(`该目标实体已存在映射规则（rule_id=${conflict.id}）`);
        return;
      }
    }
    
    // 合并 fieldMappings 和 mappingDesc
    const combinedMappings: Record<string, any> = {};
    let activeSourceTableIds = new Set<string>();

    const allKnownTableIdSet = new Set(
      [...sourceMaster, ...sourceBusiness, ...sourceReference].map(t => String(t.id))
    );
    const selectedValidSourceIds = sourceTableIds.filter(id => allKnownTableIdSet.has(String(id)));
    const allowedTableIdSet = new Set(selectedValidSourceIds.map(id => String(id)));

    Object.keys(fieldMappings).forEach(k => {
      const mappingVals = fieldMappings[k] || [];
      const mappingValsArr = typeof mappingVals === 'string' ? [mappingVals] : mappingVals;
      const filteredValsArr = (mappingValsArr || []).filter((val: any) => {
        if (typeof val !== 'string') return false;
        if (!val.includes('_')) return true;
        const { tableId } = parseMappingValue(val);
        if (!tableId) return true;
        return allowedTableIdSet.has(String(tableId));
      });
      
      filteredValsArr.forEach((val: string) => {
        if (val && val.includes('_')) {
           const { tableId } = parseMappingValue(val);
           if (tableId) activeSourceTableIds.add(tableId);
        }
      });

      combinedMappings[k] = {
        source: filteredValsArr,
        desc: mappingDesc[k] || '',
        is_pk: !!pkOverrides[k],
      };
    });

    // 规则级元信息：主表 + 主键覆盖
    combinedMappings.__meta__ = {
      main_source_table_id: mainSourceTableId || null,
      primary_key_overrides: pkOverrides,
    };

    // 约束1：映射规则 + 字段英文名唯一
    const targetUniqueSet = new Set<string>();
    for (const k of Object.keys(combinedMappings)) {
      if (k === '__meta__') continue;
      const sepIdx = k.indexOf('_');
      if (sepIdx < 0) continue;
      const fieldEn = k.slice(sepIdx + 1);
      const uniqueKey = String(fieldEn || '').trim().toLowerCase();
      if (targetUniqueSet.has(uniqueKey)) {
        message.error(`保存失败：映射明细唯一约束冲突（映射规则+字段英文名） -> ${fieldEn}`);
        return;
      }
      targetUniqueSet.add(uniqueKey);
    }

    // 来源侧不做唯一约束：允许多个目标字段映射到同一个来源字段

    const payload = {
      name: (ruleName || '').trim() || `Mapping_${Date.now()}`,
      source_table_ids: Array.from(new Set(selectedValidSourceIds)),
      entity_ids: entityIds,
      field_mappings: combinedMappings,
      is_advanced_sql: false,
      sql_content: sqlContent || null
    };

    try {
      if (currentRuleId) {
        await mappingApi.updateMappingRule(currentRuleId, payload);
      } else {
        const saveRes = await mappingApi.createMappingRule(payload);
        if (saveRes?.data?.data?.id) {
          setCurrentRuleId(saveRes.data.data.id);
        }
      }
      message.success('映射规则保存成功（已入库）');
      const sourceResLike = { data: { data: { master: sourceMaster, business: sourceBusiness, reference: sourceReference } } };
      await fetchMappingRules(sourceResLike);
      setRuleModalOpen(false);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : detail?.message || '映射规则保存失败';
      message.error(msg);
    }
  };

  const handleCreateNewRule = () => {
    resetEditorWorkspace();
    setRuleModalMode('create');
    setRuleModalOpen(true);
  };

  const handleEditRule = async (rule: any) => {
    const sourceResLike = { data: { data: { master: sourceMaster, business: sourceBusiness, reference: sourceReference } } };
    const detailRes = await mappingApi.getMappingRuleDetail(rule.id);
    await loadRuleToEditor(detailRes?.data?.data || rule, sourceResLike, true);
    setRuleModalMode('edit');
    setRuleModalOpen(true);
  };

  const handleViewRule = async (rule: any) => {
    const sourceResLike = { data: { data: { master: sourceMaster, business: sourceBusiness, reference: sourceReference } } };
    const detailRes = await mappingApi.getMappingRuleDetail(rule.id);
    await loadRuleToViewer(detailRes?.data?.data || rule, sourceResLike);
    setRuleModalMode('view');
    setRuleModalOpen(true);
  };

  const handleDeleteRule = async (ruleId: string) => {
    try {
      await mappingApi.deleteMappingRule(ruleId);
      if (currentRuleId === ruleId) {
        resetEditorWorkspace();
      }
      if (viewingRuleId === ruleId) {
        resetViewerWorkspace();
      }
      const sourceResLike = { data: { data: { master: sourceMaster, business: sourceBusiness, reference: sourceReference } } };
      await fetchMappingRules(sourceResLike);
      message.success('映射规则已删除');
    } catch (e) {
      message.error('删除映射规则失败');
    }
  };

  const handlePreviewRuleSql = (rule: any) => {
    setSqlPreviewTitle(`${rule?.name || '未命名规则'} - 映射SQL`);
    setSqlPreviewContent(rule?.sql_content || '-- 该映射规则暂无SQL内容');
    setSqlPreviewOpen(true);
  };

  const allSourceTableEns = useMemo(() => {
    return [...sourceMaster, ...sourceBusiness, ...sourceReference].map(t => ({
      value: t.enName,
      label: `${t.enName} (${t.cnName || ''})`
    }));
  }, [sourceMaster, sourceBusiness, sourceReference]);

  const renderRulesTable = () => {
    const allTables = [...sourceMaster, ...sourceBusiness, ...sourceReference];
    const getRuleEntityId = (r: any) => String((r?.entity_ids || [])[0] || '');
    const getRuleEntity = (r: any) => {
      const eid = getRuleEntityId(r);
      return (entityMetaById[eid] || dbEntities.find((e) => String(e.id) === eid)) || {};
    };
    const getEntityModeling = (r: any) => {
      const eid = getRuleEntityId(r);
      const ent = (entityMetaById[eid] || dbEntities.find((e) => String(e.id) === eid));
      return ent ? { model_table_cn: ent.entity_en_name || '' } : undefined;
    };
    const formatSourceTableNames = (r: any) => {
      const ids: string[] = r?.source_table_ids || [];
      const names = ids
        .map((id) => allTables.find((t) => String(t.id) === String(id)))
        .filter(Boolean)
        .map((t: any) => String(t.cnName || t.enName || '').trim())
        .filter(Boolean);
      return Array.from(new Set(names)).join('、');
    };

    const columns = [
      { title: TERMS.graphEntityCnName, key: 'entityName', width: 180, render: (_: any, r: any) => getRuleEntity(r)?.entity_name || getRuleEntity(r)?.label || '-' },
      { title: '实体落地中文表名', key: 'landingTableCn', width: 180, render: (_: any, r: any) => getEntityModeling(r)?.model_table_cn || '-' },
      { title: '来源表名', key: 'sourceTables', width: 240, ellipsis: true, render: (_: any, r: any) => formatSourceTableNames(r) || '-' },
      { title: '规则ID', dataIndex: 'id', width: 220, ellipsis: true },
      { title: '创建时间', dataIndex: 'created_at', width: 180, ellipsis: true },
      {
        title: '操作',
        key: 'actions',
        width: 220,
        render: (_: any, record: any) => (
          <Space>
            <Button size="small" onClick={() => handleViewRule(record)}>查看</Button>
            <Button size="small" onClick={() => handlePreviewRuleSql(record)}>查看SQL</Button>
            <Button size="small" type="link" onClick={() => handleEditRule(record)}>修改</Button>
            <Popconfirm title="确认删除该映射规则？" onConfirm={() => handleDeleteRule(record.id)}>
              <Button size="small" danger type="link">删除</Button>
            </Popconfirm>
          </Space>
        )
      }
    ];

    return (
      <Card
        size="small"
        title={`${TERMS.mappingRule}列表`}
        style={{ marginBottom: 16 }}
        extra={
          <Space>
            <Button type="primary" onClick={handleCreateNewRule}>新建映射规则</Button>
          </Space>
        }
      >
        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col span={8}>
            <Input
              allowClear
              placeholder="按规则名/规则ID搜索"
              value={queryKeyword}
              onChange={(e) => setQueryKeyword(e.target.value)}
            />
          </Col>
          <Col span={7}>
            <Select
              allowClear
              showSearch
              placeholder="按图谱实体筛选"
              value={queryEntityId || undefined}
              onChange={(v) => setQueryEntityId(v || '')}
              options={dbEntities.map((e) => ({
                value: String(e.id),
                label: `${e.entity_name || e.label} (${e.entity_code})`,
              }))}
              optionFilterProp="label"
              style={{ width: '100%' }}
            />
          </Col>
          <Col span={7}>
            <Select
              allowClear
              showSearch
              placeholder="按来源表筛选"
              value={querySourceTableId || undefined}
              onChange={(v) => setQuerySourceTableId(v || '')}
              options={[...sourceMaster, ...sourceBusiness, ...sourceReference].map((t) => ({
                value: String(t.id),
                label: `${t.enName} (${t.cnName || ''})`,
              }))}
              optionFilterProp="label"
              style={{ width: '100%' }}
            />
          </Col>
          <Col span={2}>
            <Button style={{ width: '100%' }} onClick={resetQueryFilters}>重置</Button>
          </Col>
        </Row>
        <Table
          size="small"
          rowKey="id"
          dataSource={filteredMappingRules}
          columns={columns}
          scroll={{ x: 'max-content' }}
          pagination={{ pageSize: 8 }}
          rowClassName={(record: any) => String(record.id) === String(viewingRuleId || '') ? 'ant-table-row-selected' : ''}
          expandable={{
            expandedRowRender: (record: any) => {
              const rows = mappingInfoRows.filter((r: any) => String(r.ruleId) === String(record.id));
              return (
                <Table
                  size="small"
                  rowKey="key"
                  dataSource={rows}
                  pagination={false}
                  columns={[
                    { title: TERMS.entityFieldEnName, dataIndex: 'propEn', width: 120 },
                    { title: TERMS.entityFieldCnName, dataIndex: 'propCn', width: 120 },
                    { title: '是否主键', dataIndex: 'isPk', width: 80 },
                    { title: '字段类型', dataIndex: 'propType', width: 100 },
                    { title: TERMS.sourceTableEnName, dataIndex: 'tableEn', width: 150 },
                    { title: TERMS.sourceFieldEnName, dataIndex: 'fieldEn', width: 150 },
                    { title: TERMS.extractionLogic, dataIndex: 'desc' },
                  ]}
                  locale={{ emptyText: '该规则暂无字段映射明细' }}
                />
              );
            },
          }}
        />
      </Card>
    );
  };

  // 渲染映射信息明细管理
  const renderMappingInfoTable = () => {
    const columns = [
      { title: '规则名称', dataIndex: 'ruleName', width: 180, ellipsis: true },
      { title: '实体唯一编码', dataIndex: 'entityCode', width: 150 },
      { title: TERMS.graphEntityCnName, dataIndex: 'entityName', width: 150 },
      { title: TERMS.graphEntityEnName, dataIndex: 'entityLandingTableEn', width: 220, render: (v: string) => v || <StatusTag preset="error">未维护</StatusTag> },
      { title: TERMS.entityFieldEnName, dataIndex: 'propEn', width: 120 },
      { title: TERMS.entityFieldCnName, dataIndex: 'propCn', width: 120 },
      { title: '是否主键', dataIndex: 'isPk', width: 80 },
      { title: '字段类型', dataIndex: 'propType', width: 100 },
      { title: TERMS.sourceBizSystem, dataIndex: 'sysName', width: 120 },
      { title: TERMS.sourceTableCnName, dataIndex: 'tableCn', width: 150 },
      { title: TERMS.sourceTableEnName, dataIndex: 'tableEn', width: 150 },
      { title: '是否来源主表', dataIndex: 'isMainSource', width: 120 },
      { title: TERMS.sourceFieldEnName, dataIndex: 'fieldEn', width: 150 },
      { title: TERMS.sourceFieldCnName, dataIndex: 'fieldCn', width: 150 },
      { title: TERMS.extractionLogic, dataIndex: 'desc', width: 150, ellipsis: true },
      { title: '备注', dataIndex: 'remark', width: 100 },
    ];

    return (
      <Space direction="vertical" style={{ width: '100%' }} size={16}>
        <Card
          size="small"
          title="映射信息查询"
          extra={
            <Space>
              <Button onClick={() => { setDetailEntityId(''); setDetailSourceTableId(''); }}>重置筛选</Button>
              <Button icon={<DownloadOutlined />} onClick={handleExportTemplate}>导出模板</Button>
            </Space>
          }
        >
          <Row gutter={12}>
            <Col span={10}>
              <Select
                allowClear
                showSearch
                placeholder="输入或选择实体"
                value={detailEntityId || undefined}
                onChange={(v) => setDetailEntityId(v || '')}
                options={dbEntities.map((e) => ({
                  value: String(e.id),
                  label: `${e.entity_name || e.label} (${e.entity_code})`,
                }))}
                optionFilterProp="label"
                style={{ width: '100%' }}
              />
            </Col>
            <Col span={10}>
              <Select
                allowClear
                showSearch
                placeholder="输入或选择源端表"
                value={detailSourceTableId || undefined}
                onChange={(v) => setDetailSourceTableId(v || '')}
                options={[...sourceMaster, ...sourceBusiness, ...sourceReference].map((t) => ({
                  value: String(t.id),
                  label: `${t.enName} (${t.cnName || ''})`,
                }))}
                optionFilterProp="label"
                style={{ width: '100%' }}
              />
            </Col>
            <Col span={4}>
              <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
                <StatusTag preset="info">命中 {mappingInfoRows.length} 条</StatusTag>
              </div>
            </Col>
          </Row>
        </Card>
        <Card 
          size="small" 
          title="映射信息明细" 
        >
          <Table 
            size="small"
            dataSource={mappingInfoRows}
            columns={columns}
            scroll={{ x: 'max-content' }}
            pagination={{ pageSize: 15 }}
            locale={{ emptyText: '请选择实体或源端表后查看映射明细' }}
          />
        </Card>
      </Space>
    );
  };

  const renderEntityProperties = (entity: any, readOnly = false) => {
    const props = entity.properties_schema || [];
    const currentPkOverrides = readOnly ? viewPkOverrides : pkOverrides;
    const currentRowSourceTableFilter = readOnly ? {} : rowSourceTableFilter;
    const currentFieldMappings = readOnly ? viewFieldMappings : fieldMappings;
    const currentMappingDesc = readOnly ? viewMappingDesc : mappingDesc;
    const currentSelectedSourceTables = readOnly ? viewSelectedSourceTables : selectedSourceTables;
    return (
      <Card 
        size="small" 
        title={
          <Space>
            <AppstoreOutlined />
            {entity.label} 
            {entity.is_main_table ? <StatusTag preset="error">主表</StatusTag> : <StatusTag preset="default">辅表</StatusTag>}
          </Space>
        } 
        style={{ marginBottom: 16 }}
      >
        <Table 
          size="small"
          pagination={false}
          rowKey="name"
          dataSource={props}
          columns={[
            { title: TERMS.entityFieldEnName, dataIndex: 'name', key: 'name', width: 100, render: (text: string) => <Text strong>{text}</Text> },
            { title: TERMS.entityFieldCnName, dataIndex: 'cnName', key: 'cnName', width: 100, render: (text: string) => <Text type="secondary">{text}</Text> },
            { title: '是否主键', dataIndex: 'isPrimaryKey', width: 100, render: (_: boolean, record: any) => {
              const key = `${entity.id}_${record.name}`;
              if (readOnly) {
                return <StatusTag preset={currentPkOverrides[key] ? 'error' : 'default'}>{currentPkOverrides[key] ? '是' : '否'}</StatusTag>;
              }
              return (
                <Switch
                  checked={!!currentPkOverrides[key]}
                  checkedChildren="是"
                  unCheckedChildren="否"
                  onChange={(checked) => handlePkChange(entity.id, record.name, checked)}
                />
              );
            }},
            { title: '字段类型', dataIndex: 'type', width: 90 },
            { title: TERMS.sourceTableEnName, key: 'sourceTable', width: 140, render: (_: any, record: any) => {
                const key = `${entity.id}_${record.name}`;
                if (readOnly) {
                  const mappingVals = currentFieldMappings[key] || [];
                  const tableNames = (Array.isArray(mappingVals) ? mappingVals : [mappingVals]).map((mv: string) => {
                    const { tableId } = parseMappingValue(mv);
                    return currentSelectedSourceTables.find(t => String(t.id) === String(tableId))?.enName || '';
                  }).filter(Boolean);
                  return <Text>{Array.from(new Set(tableNames)).join(' | ') || '-'}</Text>;
                }
                return (
                  <Select 
                    style={{ width: '100%' }} 
                    placeholder="选择来源表英文名" 
                    allowClear
                    value={currentRowSourceTableFilter[key]}
                    onChange={(val) => handleRowSourceTableChange(entity.id, record.name, val)}
                  >
                    {currentSelectedSourceTables.map(t => (
                      <Select.Option key={t.id} value={t.id}>{t.enName}</Select.Option>
                    ))}
                  </Select>
                );
            }},
            { title: TERMS.sourceFieldEnName, key: 'mapping', width: 220, render: (_: any, record: any) => {
              const key = `${entity.id}_${record.name}`;
              const currentVals = currentFieldMappings[key] || [];
              if (readOnly) {
                return <Text>{(Array.isArray(currentVals) ? currentVals : [currentVals]).map((mv: string) => parseMappingValue(mv).fieldEn).filter(Boolean).join(' | ') || '-'}</Text>;
              }
              return (
                <Space direction="vertical" style={{ width: '100%' }} size={4}>
                  <Button size="small" onClick={() => openFieldPicker(entity, record)}>
                    选择来源字段(多选)
                  </Button>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    已选 {currentVals.length} 项
                  </Text>
                </Space>
            )}},
            { title: TERMS.extractionLogic, key: 'desc', width: 150, render: (_: any, record: any) => {
              const key = `${entity.id}_${record.name}`;
              if (readOnly) {
                return <Text>{currentMappingDesc[key] || '-'}</Text>;
              }
              return (
                <Input 
                  placeholder={TERMS.extractionLogic}
                  value={currentMappingDesc[key]}
                  onChange={(e) => handleMappingDescChange(entity.id, record.name, e.target.value)}
                />
              );
            }}
          ]}
          locale={{ emptyText: '该实体暂无属性，请先在资产管理中维护' }}
        />
      </Card>
    );
  };

  const fieldPickerRows = useMemo(() => {
    const tables = fieldPickerTableId
      ? selectedSourceTables.filter(t => String(t.id) === String(fieldPickerTableId))
      : selectedSourceTables;
    const rows: any[] = [];
    tables.forEach(t => {
      const fields = sourceTableFields[t.id] || [];
      fields.forEach((f: any) => {
        rows.push({
          key: `${t.id}_${f.field_en}`,
          tableEn: t.enName,
          tableCn: t.cnName,
          fieldEn: f.field_en,
          fieldCn: f.field_cn,
        });
      });
    });
    return rows;
  }, [fieldPickerTableId, selectedSourceTables, sourceTableFields]);

  const renderRuleModalContent = () => {
    const modalSourceIds = ruleModalReadOnly ? viewSourceTableIds : sourceTableIds;
    const modalEntityIds = ruleModalReadOnly ? viewEntityIds : entityIds;
    const modalSelectedSourceTables = ruleModalReadOnly ? viewSelectedSourceTables : selectedSourceTables;
    const modalSelectedEntities = ruleModalReadOnly ? viewSelectedEntities : selectedEntities;
    const modalMainSourceTableId = ruleModalReadOnly ? viewMainSourceTableId : mainSourceTableId;
    const modalSql = ruleModalReadOnly ? viewSqlContent : sqlContent;

    return (
      <Layout style={{ height: '70vh', background: 'var(--bg-content)' }}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--color-border)', background: 'var(--bg-subtle)' }}>
          <Row gutter={12} align="middle">
            <Col span={8}>
              <Text strong style={{ marginRight: 8 }}>规则名称：</Text>
              <Input
                placeholder="请输入映射规则名称"
                value={ruleModalReadOnly ? viewingRuleName : ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                disabled={ruleModalReadOnly}
              />
            </Col>
            <Col span={8}>
              <Text strong style={{ marginRight: 8 }}>选择{TERMS.sourceTableCatalog}：</Text>
              <TreeSelect
                style={{ width: '100%' }}
                treeData={sourceTreeData}
                value={modalSourceIds}
                onChange={handleSourceTableChange}
                treeCheckable
                showCheckedStrategy={TreeSelect.SHOW_CHILD}
                placeholder={`请选择${TERMS.sourceTableCatalog}`}
                allowClear
                showSearch
                disabled={ruleModalReadOnly}
                treeNodeFilterProp="title"
                maxTagCount={3}
              />
            </Col>
            <Col span={8}>
              <Text strong style={{ marginRight: 8 }}>选择图谱实体：</Text>
              <TreeSelect
                style={{ width: '100%' }}
                treeData={entityTreeData}
                value={modalEntityIds[0] || undefined}
                onChange={(v) => setEntityIds(v ? [String(v)] : [])}
                placeholder="请选择图谱实体"
                allowClear
                showSearch
                disabled={ruleModalReadOnly}
                treeNodeFilterProp="title"
                maxTagCount={3}
              />
            </Col>
          </Row>
        </div>
        <Content style={{ padding: '24px', overflowY: 'auto' }}>
          {modalSourceIds.length === 0 || modalEntityIds.length === 0 ? (
            <div style={{ textAlign: 'center', marginTop: 100 }}>
              <Empty description={`请先选择至少一个${TERMS.sourceTableCatalog}和图谱实体`} />
            </div>
          ) : (
            <div>
              <Card
                size="small"
                title={<Space><DatabaseOutlined />已选来源字段目录</Space>}
                type="inner"
                style={{ marginBottom: 16 }}
              >
                <Collapse ghost>
                  {modalSelectedSourceTables.map(t => (
                    <Collapse.Panel
                      key={t.id}
                      header={
                        <Space>
                          <StatusTag preset="info">{t.enName}</StatusTag>
                          <Text type="secondary">{t.cnName}</Text>
                          {String(modalMainSourceTableId) === String(t.id) ? <StatusTag preset="error">主表</StatusTag> : null}
                          {!ruleModalReadOnly ? (
                            <Button
                              size="small"
                              type={String(modalMainSourceTableId) === String(t.id) ? 'primary' : 'default'}
                              onClick={(e) => {
                                e.stopPropagation();
                                setMainSourceTableId(String(modalMainSourceTableId) === String(t.id) ? '' : String(t.id));
                              }}
                            >
                              {String(modalMainSourceTableId) === String(t.id) ? '取消主表' : '设为主表'}
                            </Button>
                          ) : null}
                        </Space>
                      }
                    >
                      <Table
                        size="small"
                        pagination={{ pageSize: 5 }}
                        rowKey="field_en"
                        dataSource={sourceTableFields[t.id] || []}
                        columns={[
                          { title: '列英文名', dataIndex: 'field_en', key: 'field_en', render: text => <Text code>{text}</Text> },
                          { title: '列中文名', dataIndex: 'field_cn', key: 'field_cn', render: text => <Text type="secondary" style={{ fontSize: 12 }}>{text}</Text> },
                        ]}
                        locale={{ emptyText: '该表暂未导入字段' }}
                      />
                    </Collapse.Panel>
                  ))}
                </Collapse>
              </Card>

              <Card
                size="small"
                title={<Space><AppstoreOutlined />目标实体映射配置</Space>}
                type="inner"
                extra={
                  !ruleModalReadOnly ? (
                    <Space>
                      <Upload beforeUpload={handleImportCSV} showUploadList={false} accept=".csv">
                        <Button icon={<UploadOutlined />}>导入映射</Button>
                      </Upload>
                      <Button type="dashed" icon={<ThunderboltOutlined />} onClick={autoMatchFields}>智能自动匹配</Button>
                      <Button type="dashed" icon={<CodeOutlined />} onClick={generateSqlTemplate}>生成SQL</Button>
                    </Space>
                  ) : null
                }
              >
                <div style={{ maxHeight: '40vh', overflowY: 'auto', marginBottom: 16 }}>
                  {modalSelectedEntities.map((entity) => renderEntityProperties(entity, ruleModalReadOnly))}
                </div>

                <Divider orientation="left">自定义 SQL</Divider>
                <TextArea
                  rows={6}
                  readOnly={ruleModalReadOnly}
                  style={{ fontFamily: 'monospace', background: '#1e1e1e', color: '#d4d4d4' }}
                  placeholder={`SELECT \n  A.ID AS id,\n  B.NAME AS customer_name\nFROM ${modalSelectedSourceTables[0]?.enName} A \nJOIN ... B ON A.ID = B.ID`}
                  value={modalSql}
                  onChange={e => setSqlContent(e.target.value)}
                />
              </Card>
            </div>
          )}
        </Content>
      </Layout>
    );
  };

  const tabItems = [
    {
      key: '1',
      label: <Space><AppstoreOutlined />落地实体表映射</Space>,
      children: (
        <div style={{ padding: '24px', height: 'calc(100vh - 200px)', overflowY: 'auto' }}>
          {renderRulesTable()}
        </div>
      )
    },
    {
      key: '2',
      label: <Space><CodeOutlined />虚拟SQL映射</Space>,
      children: <SqlIntegrationTab entityId={queryEntityId || undefined} />
    },
    {
      key: '3',
      label: <Space><ApiOutlined />多源API映射</Space>,
      children: <ApiMappingTab entityId={queryEntityId || undefined} />
    },
  ].filter((item) => !visibleTabs || visibleTabs.includes(item.key));

  return (
    <PageShell
      title="映射管理"
      extra={
        jumpFromGraph ? (
          <Button onClick={() => onOpenTarget?.('graph')}>返回图谱实体管理</Button>
        ) : null
      }
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        style={{ height: '100%' }}
        tabBarStyle={{ padding: '0 24px', margin: 0, backgroundColor: tokens.colors.bgSubtle }}
        items={tabItems}
      />
      <Modal
        title={ruleModalMode === 'create' ? '新建映射规则' : ruleModalMode === 'edit' ? '修改映射规则' : '查看映射规则'}
        open={ruleModalOpen}
        width={1400}
        onCancel={() => setRuleModalOpen(false)}
        destroyOnHidden={false}
        footer={
          ruleModalReadOnly ? [
            <Button key="close" onClick={() => setRuleModalOpen(false)}>关闭</Button>,
          ] : [
            <Button key="cancel" onClick={() => setRuleModalOpen(false)}>取消</Button>,
            <Button key="save" type="primary" icon={<SaveOutlined />} onClick={handleSave}>保存</Button>,
          ]
        }
      >
        {renderRuleModalContent()}
      </Modal>
      <Modal
        title={fieldPickerTitle}
        open={fieldPickerOpen}
        width={980}
        onOk={saveFieldPicker}
        onCancel={() => setFieldPickerOpen(false)}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Select
            allowClear
            placeholder="按来源表过滤字段"
            value={fieldPickerTableId || undefined}
            onChange={(v) => setFieldPickerTableId(v || '')}
            options={selectedSourceTables.map(t => ({ value: String(t.id), label: `${t.enName} (${t.cnName || ''})` }))}
            style={{ width: 360 }}
          />
          <Table
            size="small"
            rowKey="key"
            dataSource={fieldPickerRows}
            pagination={{ pageSize: 10 }}
            scroll={{ y: 360 }}
            rowSelection={{
              selectedRowKeys: fieldPickerTempValues,
              onChange: (keys) => setFieldPickerTempValues(keys as string[]),
            }}
            columns={[
              { title: TERMS.sourceTableEnName, dataIndex: 'tableEn', width: 180 },
              { title: TERMS.sourceTableCnName, dataIndex: 'tableCn', width: 160 },
              { title: TERMS.sourceFieldEnName, dataIndex: 'fieldEn', width: 200 },
              { title: TERMS.sourceFieldCnName, dataIndex: 'fieldCn', width: 220 },
            ]}
          />
        </Space>
      </Modal>
      <Modal
        title={sqlPreviewTitle}
        open={sqlPreviewOpen}
        width={900}
        onCancel={() => setSqlPreviewOpen(false)}
        footer={null}
      >
        <TextArea
          rows={18}
          readOnly
          value={sqlPreviewContent}
          style={{ fontFamily: 'monospace', background: '#1e1e1e', color: '#d4d4d4' }}
        />
      </Modal>
      <Modal
        title={previewTitle}
        open={previewModalOpen}
        width={1000}
        onCancel={() => setPreviewModalOpen(false)}
        footer={null}
      >
        <Table
          size="small"
          rowKey={(_row, idx) => String(idx)}
          dataSource={previewRows}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 'max-content', y: 420 }}
          columns={(previewRows[0] ? Object.keys(previewRows[0]) : []).map((k) => ({
            title: k,
            dataIndex: k,
            key: k,
            width: 180,
            ellipsis: true,
          }))}
          locale={{ emptyText: '暂无记录' }}
        />
      </Modal>
    </PageShell>
  );
};

export default MappingManager;
