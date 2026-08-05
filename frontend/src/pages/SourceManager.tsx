import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Card, Tabs, Layout, Tree, Table, Input, Space, Button, Modal, Descriptions, message, Upload, Spin, Divider, Form, Popconfirm, Select } from 'antd';
import { SearchOutlined, DatabaseOutlined, ClusterOutlined, AppstoreOutlined, UploadOutlined, DownloadOutlined, PlusOutlined, EditOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons';
import { uploadApi, sourceFieldApi, sourceTableApi } from '../services/api';
import { TERMS, SOURCE_TABLE_TEMPLATE_HEADERS } from '../constants/standardTerms';
import { PageShell, StatusTag } from '../components/shell';
import { tokens } from '../theme/tokens';

const { Sider, Content } = Layout;

const escapeCsvCell = (value: any) => {
  const text = value == null ? '' : String(value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
};

const normalizeText = (value: any) => String(value ?? '').trim().toLowerCase();

const normalizeGroupValue = (value: any, fallback: string) => {
  const text = String(value ?? '').trim();
  return text || fallback;
};

const buildFilterTreeKey = (prefix: string, value: string, scopeParts: string[] = []) =>
  `${prefix}${encodeURIComponent(JSON.stringify({ value, scopeParts }))}`;

const extractFilterTreeValue = (prefix: string, key: React.Key) => {
  const text = String(key);
  if (!text.startsWith(prefix)) {
    return null;
  }
  try {
    const payload = JSON.parse(decodeURIComponent(text.slice(prefix.length)));
    return typeof payload?.value === 'string' ? payload.value : null;
  } catch {
    return text.slice(prefix.length);
  }
};

const parseCsvRows = (text: string) => {
  const content = text.replace(/^\uFEFF/, '');
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = '';
  let inQuotes = false;

  for (let i = 0; i < content.length; i += 1) {
    const char = content[i];
    const nextChar = content[i + 1];

    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          cell += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        cell += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
    } else if (char === ',') {
      row.push(cell.trim());
      cell = '';
    } else if (char === '\n') {
      row.push(cell.trim());
      rows.push(row);
      row = [];
      cell = '';
    } else if (char === '\r') {
      if (nextChar === '\n') {
        continue;
      }
      row.push(cell.trim());
      rows.push(row);
      row = [];
      cell = '';
    } else {
      cell += char;
    }
  }

  if (cell.length > 0 || row.length > 0) {
    row.push(cell.trim());
    rows.push(row);
  }

  return rows.filter((item) => item.some((cellValue) => String(cellValue || '').trim()));
};

const filterTreeNodes = (nodes: any[], keyword: string): any[] => {
  if (!keyword) {
    return nodes;
  }
  return nodes
    .map((node) => {
      const children = filterTreeNodes(node.children || [], keyword);
      const matched = normalizeText(node.title).includes(keyword);
      if (matched || children.length > 0) {
        return { ...node, children };
      }
      return null;
    })
    .filter(Boolean) as any[];
};

const collectExpandedKeys = (nodes: any[]): React.Key[] => {
  const keys: React.Key[] = [];
  const walk = (items: any[]) => {
    items.forEach((item) => {
      if (Array.isArray(item.children) && item.children.length > 0) {
        keys.push(item.key);
        walk(item.children);
      }
    });
  };
  walk(nodes);
  return keys;
};

type Props = {
  initialTab?: string;
  hideTabs?: boolean;
};

const SourceManager: React.FC<Props> = ({ initialTab = '1', hideTabs = false }) => {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [masterData, setMasterData] = useState<any[]>([]);
  const [businessData, setBusinessData] = useState<any[]>([]);
  const [referenceData, setReferenceData] = useState<any[]>([]);
  
  const [allFields, setAllFields] = useState<any[]>([]);
  const [fieldsLoading, setFieldsLoading] = useState(false);
  const [relationSubTab, setRelationSubTab] = useState<'l2' | 'l4' | 'cross'>('l2');
  const [l2Relations, setL2Relations] = useState<any[]>([]);
  const [l4Relations, setL4Relations] = useState<any[]>([]);
  const [crossRelations, setCrossRelations] = useState<any[]>([]);

  // 树形过滤状态
  const [masterFilterL2, setMasterFilterL2] = useState<string | null>(null);
  const [businessFilterL4, setBusinessFilterL4] = useState<string | null>(null);
  const [refFilterCategory, setRefFilterCategory] = useState<string | null>(null);
  const [masterTreeSearch, setMasterTreeSearch] = useState('');
  const [businessTreeSearch, setBusinessTreeSearch] = useState('');
  const [referenceTreeSearch, setReferenceTreeSearch] = useState('');
  const [masterSelectedKeys, setMasterSelectedKeys] = useState<React.Key[]>([]);
  const [businessSelectedKeys, setBusinessSelectedKeys] = useState<React.Key[]>([]);
  const [referenceSelectedKeys, setReferenceSelectedKeys] = useState<React.Key[]>([]);
  const [masterExpandedKeys, setMasterExpandedKeys] = useState<React.Key[]>([]);
  const [businessExpandedKeys, setBusinessExpandedKeys] = useState<React.Key[]>([]);
  const [referenceExpandedKeys, setReferenceExpandedKeys] = useState<React.Key[]>([]);
  
  // 字段过滤状态
  const [fieldSearchSys, setFieldSearchSys] = useState<string>('');
  const [fieldSearchTable, setFieldSearchTable] = useState<string>('');

  // 表详情模态框状态
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<any>(null);
  const [tableFields, setTableFields] = useState<any[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [tableInfo, setTableInfo] = useState<any>({});
  const detailRequestIdRef = useRef(0);

  // 表单模态框状态 (新增/修改)
  const [modalVisible, setModalVisible] = useState(false);
  const [modalType, setModalType] = useState<'create' | 'edit'>('create');
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState<any>(null);

  useEffect(() => {
    fetchTables();
    fetchRelations();
    if (activeTab === '4') {
      fetchFields();
    }
  }, [activeTab]);

  useEffect(() => {
    setMasterFilterL2(null);
    setBusinessFilterL4(null);
    setRefFilterCategory(null);
    setMasterSelectedKeys([]);
    setBusinessSelectedKeys([]);
    setReferenceSelectedKeys([]);
  }, [activeTab]);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const fetchTables = async () => {
    try {
      const res = await sourceTableApi.getAllTables();
      const data = res.data.data;
      setMasterData(Array.isArray(data?.master) ? data.master : []);
      setBusinessData(Array.isArray(data?.business) ? data.business : []);
      setReferenceData(Array.isArray(data?.reference) ? data.reference : []);
    } catch (e) {
      console.error('Failed to fetch tables:', e);
      setMasterData([]);
      setBusinessData([]);
      setReferenceData([]);
    }
  };

  const fetchFields = async () => {
    setFieldsLoading(true);
    try {
      const res = await sourceFieldApi.getAllFields();
      setAllFields(res.data.data || []);
    } catch (e) {
      message.error('获取字段列表失败');
      setAllFields([]);
    } finally {
      setFieldsLoading(false);
    }
  };

  const fetchRelations = async () => {
    try {
      const res = await sourceTableApi.getAllRelations();
      const data = res?.data?.data;
      setL2Relations(Array.isArray(data?.l2_relations) ? data.l2_relations : []);
      setL4Relations(Array.isArray(data?.l4_relations) ? data.l4_relations : []);
      setCrossRelations(Array.isArray(data?.cross_relations) ? data.cross_relations : []);
    } catch (e) {
      console.error('Failed to fetch table relations:', e);
      setL2Relations([]);
      setL4Relations([]);
      setCrossRelations([]);
    }
  };

  const showDetail = async (record: any) => {
    const requestId = detailRequestIdRef.current + 1;
    detailRequestIdRef.current = requestId;
    setCurrentRecord(record);
    setDetailVisible(true);
    setDetailLoading(true);
    setTableFields([]);
    setTableInfo({});
    try {
      const res = await uploadApi.getSourceTableFields(record.sysCode, record.enName);
      if (detailRequestIdRef.current !== requestId) {
        return;
      }
      setTableFields(Array.isArray(res.data.fields) ? res.data.fields : []);
      setTableInfo(res.data.table_info || {});
    } catch (e) {
      if (detailRequestIdRef.current !== requestId) {
        return;
      }
      setTableFields([]);
      setTableInfo({});
      message.error('获取表字段信息失败');
    } finally {
      if (detailRequestIdRef.current === requestId) {
        setDetailLoading(false);
      }
    }
  };

  const getSourceTableCsvMeta = (tab: string) => {
    if (tab === '1') {
      return {
        headers: SOURCE_TABLE_TEMPLATE_HEADERS.master,
        filename: '主数据表导入模板.csv',
        rows: masterData.map((item) => [
          item.id,
          item.major,
          item.deploy,
          item.sysName,
          item.sysCode,
          item.l1,
          item.l2,
          item.enName,
          item.cnName,
          item.type,
        ]),
      };
    }
    if (tab === '2') {
      return {
        headers: SOURCE_TABLE_TEMPLATE_HEADERS.business,
        filename: '业务数据表导入模板.csv',
        rows: businessData.map((item) => [
          item.id,
          item.major,
          item.deploy,
          item.sysName,
          item.sysCode,
          item.l3,
          item.l4,
          item.enName,
          item.cnName,
          item.type,
          item.relL1,
          item.relL2,
        ]),
      };
    }
    if (tab === '3') {
      return {
        headers: SOURCE_TABLE_TEMPLATE_HEADERS.reference,
        filename: '参考数据表导入模板.csv',
        rows: referenceData.map((item) => [
          item.id,
          item.major,
          item.deploy,
          item.sysName,
          item.sysCode,
          item.category,
          item.enName,
          item.cnName,
          item.type,
        ]),
      };
    }
    if (tab === '4') {
      return {
        headers: SOURCE_TABLE_TEMPLATE_HEADERS.fields,
        filename: '表字段导入模板.csv',
        rows: allFields.map((item) => [
          item.seq_no,
          item.table_cn,
          item.table_en,
          item.sys_code,
          item.table_def,
          item.field_cn,
          item.field_en,
          item.field_desc,
          item.data_type,
          item.length_precision,
          item.scale,
          item.pk_fk,
          item.is_ref_data,
          item.ref_data_desc,
          item.ref_table_en,
          item.ref_data_usage_desc,
          item.is_history,
          item.mod_status,
          item.mod_time,
          item.mod_reason,
          item.app_scope,
        ]),
      };
    }
    return null;
  };

  const handleDownloadTemplate = (tab: string) => {
    const csvMeta = getSourceTableCsvMeta(tab);
    if (!csvMeta) {
      return;
    }
    const body = csvMeta.rows
      .map((row) => row.map((cell) => escapeCsvCell(cell)).join(','))
      .join('\n');
    const csvContent = `\uFEFF${csvMeta.headers}\n${body}`.trimEnd();
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', csvMeta.filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    message.success(tab === '4' ? '模板下载成功！' : '模板下载成功，已附带当前数据导出。');
  };

  const handleSourceFieldImport = (file: File) => {
    Modal.confirm({
      title: '确认覆盖导入字段目录',
      content: `来源字段目录批量导入会先清空现有 ${allFields.length} 条字段数据，再导入文件内容，是否继续？`,
      okText: '确认清空并导入',
      cancelText: '取消',
      onOk: async () => {
        try {
          const formData = new FormData();
          formData.append('file', file);
          formData.append('clear_existing', 'true');
          const res = await uploadApi.uploadSourceFields(formData);
          message.success(`已清空原字段数据并导入 ${res.data?.imported_count || 0} 条`);
          if (activeTab === '4') {
            fetchFields();
          }
        } catch (e: any) {
          message.error(e?.response?.data?.detail || '字段导入失败');
        }
      },
    });
    return false;
  };

  const parseCSVLocal = (file: File, tab: string) => {
    // 尝试先以 UTF-8 读取
    const reader = new FileReader();
    
    reader.onload = (e) => {
      let text = e.target?.result as string;
      
      // 如果发现乱码特征 (如包含 � 字符)，则可能原本是 GBK 编码，尝试重新以 GBK 读取
      if (text.includes('�')) {
        const gbkReader = new FileReader();
        gbkReader.onload = (gbkEvent) => {
          processCSVText(gbkEvent.target?.result as string, tab);
        };
        gbkReader.readAsText(file, 'gbk');
      } else {
        processCSVText(text, tab);
      }
    };
    reader.readAsText(file, 'utf-8');
    return false; // 阻止默认上传
  };

  const processCSVText = (text: string, tab: string) => {
    const rows = parseCsvRows(text);
    const newItems: any[] = [];
    for (let i = 1; i < rows.length; i++) {
      const cols = rows[i];
      if (cols.length < 5) continue;
      
      const id = Date.now() + i;
      if (tab === '1') {
        newItems.push({ id, major: cols[1], deploy: cols[2], sysName: cols[3], sysCode: cols[4], l1: cols[5], l2: cols[6], enName: cols[7], cnName: cols[8], type: cols[9] || '主数据' });
      } else if (tab === '2') {
        newItems.push({ id, major: cols[1], deploy: cols[2], sysName: cols[3], sysCode: cols[4], l3: cols[5], l4: cols[6], enName: cols[7], cnName: cols[8], type: cols[9] || '业务表', relL1: cols[10], relL2: cols[11] });
      } else if (tab === '3') {
        newItems.push({ id, major: cols[1], deploy: cols[2], sysName: cols[3], sysCode: cols[4], category: cols[5], enName: cols[6], cnName: cols[7], type: cols[8] || '参考数据表' });
      } else if (tab === '5') {
        if (relationSubTab === 'l2') {
          newItems.push({
            id: `l2rel_${Date.now()}_${i}`,
            l1: cols[0] || '',
            l2: cols[1] || '',
            relation_desc: cols[2] || '',
            main_table_cn: cols[3] || '',
            main_table_en: cols[4] || '',
            related_table_cn: cols[5] || '',
            related_table_en: cols[6] || '',
            relation_category: cols[7] || '',
            relation_expr: cols[8] || '',
            remark: cols[9] || '',
          });
        } else {
          newItems.push({
            id: `${relationSubTab}rel_${Date.now()}_${i}`,
            l1: cols[0] || '',
            l2: cols[1] || '',
            l3: cols[2] || '',
            l4: cols[3] || '',
            relation_desc: cols[4] || '',
            main_table_cn: cols[5] || '',
            main_table_en: cols[6] || '',
            related_table_cn: cols[7] || '',
            related_table_en: cols[8] || '',
            relation_category: cols[9] || '',
            relation_expr: cols[10] || '',
            remark: cols[11] || '',
          });
        }
      }
    }
    
    if (['1', '2', '3'].includes(tab)) {
      const labelMap: Record<string, string> = {
        '1': '主数据来源表',
        '2': '业务来源表',
        '3': '参考来源表',
      };
      Modal.confirm({
        title: '确认覆盖导入',
        content: `${labelMap[tab]}批量导入会先清空当前页已有数据，再按文件内容重新导入，共识别 ${newItems.length} 条，是否继续？`,
        okText: '确认清空并导入',
        cancelText: '取消',
        onOk: () => {
          if (tab === '1') setMasterData(newItems);
          if (tab === '2') setBusinessData(newItems);
          if (tab === '3') setReferenceData(newItems);
          message.success(`已清空当前数据并导入 ${newItems.length} 条，请记得点击“保存当前所有表数据”入库。`);
        },
      });
      return;
    }

    if (tab === '5') setCurrentRelations([...getCurrentRelations(), ...newItems]);
    
    message.success(`成功导入 ${newItems.length} 条数据`);
  };

  const handleSaveLocalData = async () => {
    try {
      await sourceTableApi.bulkSaveTables({
        master_data: masterData,
        business_data: businessData,
        reference_data: referenceData
      });
      message.success('当前所有表数据保存成功！');
    } catch (e) {
      message.error('保存表数据失败');
    }
  };

  const handleSaveRelations = async () => {
    try {
      await sourceTableApi.bulkSaveRelations({
        l2_relations: l2Relations.map(({ id, ...rest }) => ({ ...rest, relation_scope: 'l2' })),
        l4_relations: l4Relations.map(({ id, ...rest }) => ({ ...rest, relation_scope: 'l4' })),
        cross_relations: crossRelations.map(({ id, ...rest }) => ({ ...rest, relation_scope: 'cross' })),
      });
      message.success('表间关联关系保存成功（已入库）');
      fetchRelations();
    } catch (e) {
      message.error('表间关联关系保存失败');
    }
  };

  const updateFieldInline = async (id: string, patch: Record<string, any>) => {
    try {
      await sourceFieldApi.updateField(id, patch);
      setAllFields(prev => prev.map(item => item.id === id ? { ...item, ...patch } : item));
      message.success('字段更新成功');
    } catch (e) {
      message.error('字段更新失败');
    }
  };

  const getCurrentRelations = () => {
    if (relationSubTab === 'l2') return l2Relations;
    if (relationSubTab === 'l4') return l4Relations;
    return crossRelations;
  };

  const setCurrentRelations = (next: any[]) => {
    if (relationSubTab === 'l2') setL2Relations(next);
    else if (relationSubTab === 'l4') setL4Relations(next);
    else setCrossRelations(next);
  };

  const exportRelationsTemplate = () => {
    const headers = relationSubTab === 'l2'
      ? 'L1名称,L2名称,关联说明,主表中文名,主表英文名,关联表中文名,关联表英文名,关系类别,关联条件说明,备注\n'
      : 'L1名称,L2名称,L3名称,L4名称,关联说明,主表中文名,主表英文名,关联表中文名,关联表英文名,关系类别,关联条件说明,备注\n';
    const blob = new Blob(['\uFEFF' + headers], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', '表间关联关系导入模板.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    message.success('关联关系模板下载成功');
  };

  const exportRelationsData = () => {
    const headers = relationSubTab === 'l2'
      ? 'L1名称,L2名称,关联说明,主表中文名,主表英文名,关联表中文名,关联表英文名,关系类别,关联条件说明,备注\n'
      : 'L1名称,L2名称,L3名称,L4名称,关联说明,主表中文名,主表英文名,关联表中文名,关联表英文名,关系类别,关联条件说明,备注\n';
    const body = getCurrentRelations().map(r => {
      if (relationSubTab === 'l2') {
        return `${r.l1 || ''},${r.l2 || ''},${r.relation_desc || ''},${r.main_table_cn || ''},${r.main_table_en || ''},${r.related_table_cn || ''},${r.related_table_en || ''},${r.relation_category || ''},${r.relation_expr || ''},${r.remark || ''}`;
      }
      return `${r.l1 || ''},${r.l2 || ''},${r.l3 || ''},${r.l4 || ''},${r.relation_desc || ''},${r.main_table_cn || ''},${r.main_table_en || ''},${r.related_table_cn || ''},${r.related_table_en || ''},${r.relation_category || ''},${r.relation_expr || ''},${r.remark || ''}`;
    }).join('\n');
    const blob = new Blob(['\uFEFF' + headers + body], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', '表间关联关系导出.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    message.success('关联关系导出成功');
  };

  // CRUD 操作
  const handleAdd = () => {
    setModalType('create');
    setEditingId(null);
    if (activeTab === '5') {
      form.setFieldsValue({
        relation_category: '主外键',
      });
    } else {
      form.resetFields();
    }
    setModalVisible(true);
  };

  const handleEdit = (record: any) => {
    setModalType('edit');
    setEditingId(record.id);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: string | number) => {
    if (activeTab === '1') setMasterData(masterData.filter(item => item.id !== id));
    if (activeTab === '2') setBusinessData(businessData.filter(item => item.id !== id));
    if (activeTab === '3') setReferenceData(referenceData.filter(item => item.id !== id));
    if (activeTab === '5') {
      setCurrentRelations(getCurrentRelations().filter(item => item.id !== id));
      message.success('删除成功');
      return;
    }
    if (activeTab === '4') {
      try {
        await sourceFieldApi.deleteField(id as string);
        message.success('删除成功');
        fetchFields();
      } catch (e) {
        message.error('删除失败');
      }
    } else {
      message.success('删除成功');
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      if (activeTab === '5') {
        const rel = { ...values, id: editingId || `${relationSubTab}rel_${Date.now()}` };
        if (modalType === 'create') {
          setCurrentRelations([...getCurrentRelations(), rel]);
          message.success('新增关联关系成功');
        } else {
          setCurrentRelations(getCurrentRelations().map(item => item.id === editingId ? rel : item));
          message.success('修改关联关系成功');
        }
      } else if (activeTab === '4') {
        if (modalType === 'create') {
          await sourceFieldApi.createField(values);
          message.success('新增字段成功');
        } else {
          await sourceFieldApi.updateField(editingId, values);
          message.success('修改字段成功');
        }
        fetchFields();
      } else {
        const newRecord = { ...values, id: editingId || Date.now() };
        if (activeTab === '1') {
          if (modalType === 'create') setMasterData([...masterData, newRecord]);
          else setMasterData(masterData.map(item => item.id === editingId ? newRecord : item));
        } else if (activeTab === '2') {
          if (modalType === 'create') setBusinessData([...businessData, newRecord]);
          else setBusinessData(businessData.map(item => item.id === editingId ? newRecord : item));
        } else if (activeTab === '3') {
          if (modalType === 'create') setReferenceData([...referenceData, newRecord]);
          else setReferenceData(referenceData.map(item => item.id === editingId ? newRecord : item));
        }
        message.success(`${modalType === 'create' ? '新增' : '修改'}成功`);
      }
      setModalVisible(false);
    } catch (e) {
      console.error(e);
    }
  };

  // ---------------- 主数据 ----------------
  const masterColumns = [
    { title: '序号', dataIndex: 'id', width: 70, fixed: 'left' as const },
    { title: '系统名称', dataIndex: 'sysName', width: 120 },
    { title: '系统编码', dataIndex: 'sysCode', width: 90 },
    { title: 'L1-主数据', dataIndex: 'l1', width: 100 },
    { title: 'L2-主数据对象', dataIndex: 'l2', width: 120 },
    { 
      title: TERMS.sourceTableEnName, 
      dataIndex: 'enName', 
      width: 180,
      render: (text: string, record: any) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => showDetail(record)}>
          <StatusTag preset="info" style={{ cursor: 'pointer' }}>{text}</StatusTag>
        </Button>
      ) 
    },
    { title: TERMS.sourceTableCnName, dataIndex: 'cnName', width: 180, ellipsis: true },
    { title: '表类型', dataIndex: 'type', width: 100, render: (text: string) => <StatusTag preset="success">{text}</StatusTag> },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="确定删除吗?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ---------------- 业务数据 ----------------
  const businessColumns = [
    { title: '序号', dataIndex: 'id', width: 70, fixed: 'left' as const },
    { title: '系统名称', dataIndex: 'sysName', width: 130 },
    { title: '系统编码', dataIndex: 'sysCode', width: 90 },
    { title: 'L3-业务模块', dataIndex: 'l3', width: 160, ellipsis: true },
    { title: 'L4-业务活动对象', dataIndex: 'l4', width: 160, ellipsis: true },
    { 
      title: TERMS.sourceTableEnName, 
      dataIndex: 'enName', 
      width: 180,
      render: (text: string, record: any) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => showDetail(record)}>
          <StatusTag preset="info" style={{ cursor: 'pointer' }}>{text}</StatusTag>
        </Button>
      ) 
    },
    { title: TERMS.sourceTableCnName, dataIndex: 'cnName', width: 180, ellipsis: true },
    { title: '关联L1', dataIndex: 'relL1', width: 100, ellipsis: true },
    { title: '关联L2', dataIndex: 'relL2', width: 120, ellipsis: true },
    { title: '表类型', dataIndex: 'type', width: 100, render: (text: string) => <StatusTag preset="info">{text}</StatusTag> },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="确定删除吗?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ---------------- 参考数据 ----------------
  const referenceColumns = [
    { title: '序号', dataIndex: 'id', width: 70, fixed: 'left' as const },
    { title: '系统名称', dataIndex: 'sysName', width: 120 },
    { title: '系统编码', dataIndex: 'sysCode', width: 90 },
    { title: '参考数据分类', dataIndex: 'category', width: 130 },
    { 
      title: TERMS.sourceTableEnName, 
      dataIndex: 'enName', 
      width: 180,
      render: (text: string, record: any) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => showDetail(record)}>
          <StatusTag preset="info" style={{ cursor: 'pointer' }}>{text}</StatusTag>
        </Button>
      ) 
    },
    { title: TERMS.sourceTableCnName, dataIndex: 'cnName', width: 180, ellipsis: true },
    { title: '表类型', dataIndex: 'type', width: 120, render: (text: string) => <StatusTag preset="warning">{text}</StatusTag> },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="确定删除吗?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ---------------- 字段管理 ----------------
  const fieldColumns = [
    { title: '序号', dataIndex: 'seq_no', width: 70, fixed: 'left' as const },
    { title: '来源系统编码', dataIndex: 'sys_code', width: 120, fixed: 'left' as const },
    { title: TERMS.sourceTableCnName, dataIndex: 'table_cn', width: 150, fixed: 'left' as const, ellipsis: true },
    { title: TERMS.sourceTableEnName, dataIndex: 'table_en', width: 150, fixed: 'left' as const, ellipsis: true },
    { title: '库表定义', dataIndex: 'table_def', width: 150, ellipsis: true },
    { title: TERMS.sourceFieldCnName, dataIndex: 'field_cn', width: 150, ellipsis: true },
    { title: TERMS.sourceFieldEnName, dataIndex: 'field_en', width: 150, ellipsis: true },
    { title: '字段描述', dataIndex: 'field_desc', width: 200, ellipsis: true },
    { title: '数据类型', dataIndex: 'data_type', width: 120 },
    { title: '长度/精度', dataIndex: 'length_precision', width: 100 },
    { title: '小数位', dataIndex: 'scale', width: 80 },
    { title: '主/外键', dataIndex: 'pk_fk', width: 100 },
    {
      title: '是否参考数据',
      dataIndex: 'is_ref_data',
      width: 130,
      render: (val: string, record: any) => (
        <Select
          size="small"
          style={{ width: 110 }}
          value={val || '否'}
          options={[{ value: '是', label: '是' }, { value: '否', label: '否' }]}
          onChange={(v: string) => updateFieldInline(record.id, { ...record, is_ref_data: v })}
        />
      )
    },
    {
      title: '参考数据引用说明',
      dataIndex: 'ref_data_desc',
      width: 180,
      render: (val: string, record: any) => (
        <Input
          size="small"
          value={val}
          placeholder="例如：引用 ADM_REGN.code"
          onChange={(e) => setAllFields(prev => prev.map(item => item.id === record.id ? { ...item, ref_data_desc: e.target.value } : item))}
          onBlur={(e) => updateFieldInline(record.id, { ...record, ref_data_desc: e.target.value })}
        />
      )
    },
    {
      title: '引用参考数据表',
      dataIndex: 'ref_table_en',
      width: 180,
      render: (val: string, record: any) => (
        <Select
          size="small"
          allowClear
          showSearch
          value={val}
          style={{ width: 160 }}
          options={referenceData.map(item => ({ value: item.enName, label: `${item.enName} (${item.cnName})` }))}
          onChange={(v: string) => updateFieldInline(record.id, { ...record, ref_table_en: v })}
        />
      )
    },
    {
      title: '参考数据调用说明',
      dataIndex: 'ref_data_usage_desc',
      width: 180,
      render: (val: string, record: any) => (
        <Input
          size="small"
          value={val}
          placeholder="调用场景/接口说明"
          onChange={(e) => setAllFields(prev => prev.map(item => item.id === record.id ? { ...item, ref_data_usage_desc: e.target.value } : item))}
          onBlur={(e) => updateFieldInline(record.id, { ...record, ref_data_usage_desc: e.target.value })}
        />
      )
    },
    { title: '是否建历史表', dataIndex: 'is_history', width: 120 },
    { title: '修改状态', dataIndex: 'mod_status', width: 100 },
    { title: '修改时间', dataIndex: 'mod_time', width: 120 },
    { title: '变更原因', dataIndex: 'mod_reason', width: 150, ellipsis: true },
    { title: '应用范围', dataIndex: 'app_scope', width: 150, ellipsis: true },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="确定删除吗?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 动态构建主数据树: 来源系统 -> L1 -> L2
  const masterTreeData = useMemo(() => {
    const sysMap = new Map();
    masterData.forEach(item => {
      const sysName = normalizeGroupValue(item.sysName, '未命名系统');
      const sysCode = normalizeGroupValue(item.sysCode, '未编码');
      const sysKey = `${sysName} (${sysCode})`;
      if (!sysMap.has(sysKey)) sysMap.set(sysKey, new Map());
      const l1Map = sysMap.get(sysKey);
      const l1Val = normalizeGroupValue(item.l1, '未分类L1');
      if (!l1Map.has(l1Val)) l1Map.set(l1Val, new Set());
      const l2Val = normalizeGroupValue(item.l2, '未分类L2');
      l1Map.get(l1Val).add(l2Val);
    });
    
    const nodes = Array.from(sysMap.entries()).map(([sysKey, l1Map]) => ({
      title: sysKey,
      key: `master_sys_${sysKey}`,
      icon: <DatabaseOutlined />,
      children: Array.from(l1Map.entries() as IterableIterator<[string, Set<string>]>).map(([l1, l2Set]) => ({
        title: `L1 ${l1}`,
        key: `master_l1_${sysKey}_${l1}`,
        icon: <ClusterOutlined />,
        children: Array.from(l2Set).map(l2 => ({
          title: `L2 ${l2}`,
          key: buildFilterTreeKey('master_l2_filter_', l2, [sysKey, l1]),
          icon: <AppstoreOutlined />
        }))
      }))
    }));
    return filterTreeNodes(nodes, normalizeText(masterTreeSearch));
  }, [masterData, masterTreeSearch]);

  // 动态构建业务数据树: 来源系统 -> L3 -> L4
  const businessTreeData = useMemo(() => {
    const sysMap = new Map();
    businessData.forEach(item => {
      const sysName = normalizeGroupValue(item.sysName, '未命名系统');
      const sysCode = normalizeGroupValue(item.sysCode, '未编码');
      const sysKey = `${sysName} (${sysCode})`;
      if (!sysMap.has(sysKey)) sysMap.set(sysKey, new Map());
      const l3Map = sysMap.get(sysKey);
      const l3Val = normalizeGroupValue(item.l3, '未分类L3');
      if (!l3Map.has(l3Val)) l3Map.set(l3Val, new Set());
      const l4Val = normalizeGroupValue(item.l4, '未分类L4');
      l3Map.get(l3Val).add(l4Val);
    });
    
    const nodes = Array.from(sysMap.entries()).map(([sysKey, l3Map]) => ({
      title: sysKey,
      key: `business_sys_${sysKey}`,
      icon: <DatabaseOutlined />,
      children: Array.from(l3Map.entries() as IterableIterator<[string, Set<string>]>).map(([l3, l4Set]) => ({
        title: `L3 ${l3}`,
        key: `business_l3_${sysKey}_${l3}`,
        icon: <ClusterOutlined />,
        children: Array.from(l4Set).map(l4 => ({
          title: `L4 ${l4}`,
          key: buildFilterTreeKey('business_l4_filter_', l4, [sysKey, l3]),
          icon: <AppstoreOutlined />
        }))
      }))
    }));
    return filterTreeNodes(nodes, normalizeText(businessTreeSearch));
  }, [businessData, businessTreeSearch]);

  // 动态构建参考数据树: 来源系统 -> 分类
  const referenceTreeData = useMemo(() => {
    const sysMap = new Map();
    referenceData.forEach(item => {
      const sysName = normalizeGroupValue(item.sysName, '未命名系统');
      const sysCode = normalizeGroupValue(item.sysCode, '未编码');
      const sysKey = `${sysName} (${sysCode})`;
      if (!sysMap.has(sysKey)) sysMap.set(sysKey, new Set());
      const category = normalizeGroupValue(item.category, '未分类');
      sysMap.get(sysKey).add(category);
    });
    
    const nodes = Array.from(sysMap.entries()).map(([sysKey, catSet]) => ({
      title: sysKey,
      key: `reference_sys_${sysKey}`,
      icon: <DatabaseOutlined />,
      children: Array.from(catSet as Set<string>).map(cat => ({
        title: cat,
        key: buildFilterTreeKey('reference_cat_filter_', cat, [sysKey]),
        icon: <AppstoreOutlined />
      }))
    }));
    return filterTreeNodes(nodes, normalizeText(referenceTreeSearch));
  }, [referenceData, referenceTreeSearch]);

  useEffect(() => {
    setMasterExpandedKeys(collectExpandedKeys(masterTreeData));
  }, [masterTreeData]);

  useEffect(() => {
    setBusinessExpandedKeys(collectExpandedKeys(businessTreeData));
  }, [businessTreeData]);

  useEffect(() => {
    setReferenceExpandedKeys(collectExpandedKeys(referenceTreeData));
  }, [referenceTreeData]);

  return (
    <PageShell title="来源表管理">
      {!hideTabs ? (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{ padding: '0 24px', background: tokens.colors.bgContent }}
          items={[
            { key: '1', label: '来源表管理-主数据' },
            { key: '2', label: '来源表管理-业务' },
            { key: '3', label: '来源表管理-参考' },
            { key: '4', label: TERMS.sourceFieldCatalog },
            { key: '5', label: '表间关联关系管理' },
          ]}
        />
      ) : null}

      <Layout style={{ flex: 1, background: tokens.colors.bgContent }}>
        {activeTab === '1' && (
          <Sider width={280} style={{ background: tokens.colors.bgContent, borderRight: `1px solid ${tokens.colors.border}`, padding: '16px' }}>
            <div style={{ marginBottom: '16px' }}>
              <Input
                placeholder="搜索来源系统/L1/L2"
                prefix={<SearchOutlined />}
                value={masterTreeSearch}
                onChange={(e) => setMasterTreeSearch(e.target.value)}
                allowClear
              />
            </div>
            <Tree
              showIcon
              treeData={masterTreeData}
              selectedKeys={masterSelectedKeys}
              expandedKeys={masterExpandedKeys}
              onExpand={(keys) => setMasterExpandedKeys(keys)}
              onSelect={(keys) => {
                setMasterSelectedKeys(keys);
                if (keys.length > 0 && String(keys[0]).startsWith('master_l2_filter_')) {
                  setMasterFilterL2(extractFilterTreeValue('master_l2_filter_', keys[0]));
                } else {
                  setMasterFilterL2(null);
                }
              }}
            />
          </Sider>
        )}

        {activeTab === '2' && (
          <Sider width={280} style={{ background: 'var(--bg-content)', borderRight: '1px solid var(--color-border)', padding: '16px' }}>
            <div style={{ marginBottom: '16px' }}>
              <Input
                placeholder="搜索来源系统/L3/L4"
                prefix={<SearchOutlined />}
                value={businessTreeSearch}
                onChange={(e) => setBusinessTreeSearch(e.target.value)}
                allowClear
              />
            </div>
            <Tree
              showIcon
              treeData={businessTreeData}
              selectedKeys={businessSelectedKeys}
              expandedKeys={businessExpandedKeys}
              onExpand={(keys) => setBusinessExpandedKeys(keys)}
              onSelect={(keys) => {
                setBusinessSelectedKeys(keys);
                if (keys.length > 0 && String(keys[0]).startsWith('business_l4_filter_')) {
                  setBusinessFilterL4(extractFilterTreeValue('business_l4_filter_', keys[0]));
                } else {
                  setBusinessFilterL4(null);
                }
              }}
            />
          </Sider>
        )}

        {activeTab === '3' && (
          <Sider width={280} style={{ background: 'var(--bg-content)', borderRight: '1px solid var(--color-border)', padding: '16px' }}>
            <div style={{ marginBottom: '16px' }}>
              <Input
                placeholder="搜索来源系统/分类"
                prefix={<SearchOutlined />}
                value={referenceTreeSearch}
                onChange={(e) => setReferenceTreeSearch(e.target.value)}
                allowClear
              />
            </div>
            <Tree
              showIcon
              treeData={referenceTreeData}
              selectedKeys={referenceSelectedKeys}
              expandedKeys={referenceExpandedKeys}
              onExpand={(keys) => setReferenceExpandedKeys(keys)}
              onSelect={(keys) => {
                setReferenceSelectedKeys(keys);
                if (keys.length > 0 && String(keys[0]).startsWith('reference_cat_filter_')) {
                  setRefFilterCategory(extractFilterTreeValue('reference_cat_filter_', keys[0]));
                } else {
                  setRefFilterCategory(null);
                }
              }}
            />
          </Sider>
        )}
        
        <Content style={{ padding: '16px' }}>
          <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between' }}>
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增{activeTab === '4' ? TERMS.sourceFieldCatalog : activeTab === '5' ? '关联关系' : TERMS.sourceTableCatalog}配置</Button>
              {activeTab === '4' ? (
                <Upload beforeUpload={handleSourceFieldImport} showUploadList={false}>
                  <Button icon={<UploadOutlined />}>批量导入{TERMS.sourceFieldCatalog}</Button>
                </Upload>
              ) : activeTab === '5' ? (
                <Upload name="file" beforeUpload={(f) => parseCSVLocal(f, activeTab)} showUploadList={false}>
                  <Button icon={<UploadOutlined />}>批量导入关联关系</Button>
                </Upload>
              ) : (
                <Upload name="file" beforeUpload={(f) => parseCSVLocal(f, activeTab)} showUploadList={false}>
                  <Button icon={<UploadOutlined />}>批量覆盖导入{TERMS.sourceTableCatalog}</Button>
                </Upload>
              )}
              <Button icon={<DownloadOutlined />} onClick={() => activeTab === '5' ? exportRelationsTemplate() : handleDownloadTemplate(activeTab)}>
                {['1', '2', '3'].includes(activeTab) ? '下载导入模板/数据' : '下载导入模板'}
              </Button>
              {activeTab === '5' && (
                <Button icon={<DownloadOutlined />} onClick={exportRelationsData}>导出关联关系</Button>
              )}
            </Space>
            
            {['1', '2', '3'].includes(activeTab) && (
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveLocalData} style={{ backgroundColor: 'var(--color-success)' }}>
                保存当前所有表数据
              </Button>
            )}
            {activeTab === '5' && (
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveRelations} style={{ backgroundColor: 'var(--color-success)' }}>
                保存三类关联关系
              </Button>
            )}
          </div>
          
          {activeTab === '1' && (
            <Table 
              columns={masterColumns} 
              dataSource={masterFilterL2 ? masterData.filter(item => item.l2 === masterFilterL2) : masterData} 
              rowKey="id" 
              size="small"
              pagination={{ pageSize: 15 }}
              bordered
              scroll={{ x: 'max-content' }}
            />
          )}

          {activeTab === '2' && (
            <Table 
              columns={businessColumns} 
              dataSource={businessFilterL4 ? businessData.filter(item => item.l4 === businessFilterL4) : businessData} 
              rowKey="id" 
              size="small"
              pagination={{ pageSize: 15 }}
              bordered
              scroll={{ x: 'max-content' }}
            />
          )}

          {activeTab === '3' && (
            <Table 
              columns={referenceColumns} 
              dataSource={refFilterCategory ? referenceData.filter(item => item.category === refFilterCategory) : referenceData} 
              rowKey="id" 
              size="small"
              pagination={{ pageSize: 15 }}
              bordered
              scroll={{ x: 'max-content' }}
            />
          )}

          {activeTab === '4' && (
            <>
              <div style={{ marginBottom: '16px' }}>
                <Space>
                  <Input 
                    placeholder="按来源系统编码搜索" 
                    value={fieldSearchSys}
                    onChange={(e) => setFieldSearchSys(e.target.value)}
                    style={{ width: 200 }}
                  />
                  <Input 
                    placeholder={`按${TERMS.sourceTableEnName}/${TERMS.sourceTableCnName}搜索`} 
                    value={fieldSearchTable}
                    onChange={(e) => setFieldSearchTable(e.target.value)}
                    style={{ width: 250 }}
                  />
                </Space>
              </div>
              <Table 
                columns={fieldColumns} 
                dataSource={allFields.filter(item => {
                  const matchSys = fieldSearchSys ? item.sys_code?.toLowerCase().includes(fieldSearchSys.toLowerCase()) : true;
                  const matchTable = fieldSearchTable ? (
                    (item.table_en && item.table_en.toLowerCase().includes(fieldSearchTable.toLowerCase())) || 
                    (item.table_cn && item.table_cn.toLowerCase().includes(fieldSearchTable.toLowerCase()))
                  ) : true;
                  return matchSys && matchTable;
                })} 
                rowKey="id" 
                size="small"
                loading={fieldsLoading}
                pagination={{ pageSize: 15 }}
                bordered
                scroll={{ x: 'max-content' }}
              />
            </>
          )}
          {activeTab === '5' && (
            <>
              <Tabs
                activeKey={relationSubTab}
                onChange={(k) => setRelationSubTab(k as 'l2' | 'l4' | 'cross')}
                items={[
                  {
                    key: 'l2',
                    label: 'L2对象关系',
                    children: (
                      <Table
                        rowKey="id"
                        size="small"
                        bordered
                        pagination={{ pageSize: 15 }}
                        dataSource={l2Relations}
                        scroll={{ x: 'max-content' }}
                        columns={[
                          { title: 'L1名称', dataIndex: 'l1', width: 120 },
                          { title: 'L2名称', dataIndex: 'l2', width: 140 },
                          { title: '关联说明', dataIndex: 'relation_desc', width: 180 },
                          { title: '主表中文名', dataIndex: 'main_table_cn', width: 140 },
                          { title: '主表英文名', dataIndex: 'main_table_en', width: 140 },
                          { title: '关联表中文名', dataIndex: 'related_table_cn', width: 140 },
                          { title: '关联表英文名', dataIndex: 'related_table_en', width: 140 },
                          { title: '关系类别', dataIndex: 'relation_category', width: 120 },
                          { title: '关联条件说明', dataIndex: 'relation_expr', width: 260 },
                          { title: '备注', dataIndex: 'remark', width: 160 },
                          {
                            title: '操作',
                            width: 100,
                            render: (_: any, record: any) => (
                              <Space size="small">
                                <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
                                <Popconfirm title="确定删除该关系吗?" onConfirm={() => handleDelete(record.id)}>
                                  <Button type="link" danger icon={<DeleteOutlined />} />
                                </Popconfirm>
                              </Space>
                            )
                          }
                        ]}
                      />
                    )
                  },
                  {
                    key: 'l4',
                    label: 'L4活动关系',
                    children: (
                      <Table
                        rowKey="id"
                        size="small"
                        bordered
                        pagination={{ pageSize: 15 }}
                        dataSource={l4Relations}
                        scroll={{ x: 'max-content' }}
                        columns={[
                          { title: 'L1名称', dataIndex: 'l1', width: 120 },
                          { title: 'L2名称', dataIndex: 'l2', width: 120 },
                          { title: 'L3名称', dataIndex: 'l3', width: 180 },
                          { title: 'L4名称', dataIndex: 'l4', width: 160 },
                          { title: '关联说明', dataIndex: 'relation_desc', width: 180 },
                          { title: '主表中文名', dataIndex: 'main_table_cn', width: 140 },
                          { title: '主表英文名', dataIndex: 'main_table_en', width: 140 },
                          { title: '关联表中文名', dataIndex: 'related_table_cn', width: 140 },
                          { title: '关联表英文名', dataIndex: 'related_table_en', width: 140 },
                          { title: '关系类别', dataIndex: 'relation_category', width: 120 },
                          { title: '关联条件说明', dataIndex: 'relation_expr', width: 260 },
                          { title: '备注', dataIndex: 'remark', width: 160 },
                          {
                            title: '操作',
                            width: 100,
                            render: (_: any, record: any) => (
                              <Space size="small">
                                <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
                                <Popconfirm title="确定删除该关系吗?" onConfirm={() => handleDelete(record.id)}>
                                  <Button type="link" danger icon={<DeleteOutlined />} />
                                </Popconfirm>
                              </Space>
                            )
                          }
                        ]}
                      />
                    )
                  },
                  {
                    key: 'cross',
                    label: 'L4主表-L2主表关系',
                    children: (
                      <Table
                        rowKey="id"
                        size="small"
                        bordered
                        pagination={{ pageSize: 15 }}
                        dataSource={crossRelations}
                        scroll={{ x: 'max-content' }}
                        columns={[
                          { title: 'L1名称', dataIndex: 'l1', width: 120 },
                          { title: 'L2名称', dataIndex: 'l2', width: 120 },
                          { title: 'L3名称', dataIndex: 'l3', width: 180 },
                          { title: 'L4名称', dataIndex: 'l4', width: 160 },
                          { title: '关联说明', dataIndex: 'relation_desc', width: 180 },
                          { title: '主表中文名(L4前)', dataIndex: 'main_table_cn', width: 160 },
                          { title: '主表英文名(L4前)', dataIndex: 'main_table_en', width: 160 },
                          { title: '关联表中文名(L2后)', dataIndex: 'related_table_cn', width: 160 },
                          { title: '关联表英文名(L2后)', dataIndex: 'related_table_en', width: 160 },
                          { title: '关系类别', dataIndex: 'relation_category', width: 120 },
                          { title: '关联条件说明', dataIndex: 'relation_expr', width: 260 },
                          { title: '备注', dataIndex: 'remark', width: 160 },
                          {
                            title: '操作',
                            width: 100,
                            render: (_: any, record: any) => (
                              <Space size="small">
                                <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
                                <Popconfirm title="确定删除该关系吗?" onConfirm={() => handleDelete(record.id)}>
                                  <Button type="link" danger icon={<DeleteOutlined />} />
                                </Popconfirm>
                              </Space>
                            )
                          }
                        ]}
                      />
                    )
                  }
                ]}
              />
            </>
          )}
        </Content>
      </Layout>

      {/* 动态表单模态框 */}
      <Modal
        title={`${modalType === 'create' ? '新增' : '修改'}${activeTab === '4' ? '字段' : activeTab === '5' ? '关联关系' : '表'}`}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        width={650}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          {['1', '2', '3'].includes(activeTab) && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Form.Item name="sysName" label="来源系统名称" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="sysCode" label="来源系统编码" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="cnName" label={TERMS.sourceTableCnName} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="enName" label={TERMS.sourceTableEnName} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="major" label="专业"><Input /></Form.Item>
              <Form.Item name="deploy" label="部署方式"><Input /></Form.Item>
              <Form.Item name="type" label="表类型"><Input /></Form.Item>
            </div>
          )}
          {activeTab === '1' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Form.Item name="l1" label="L1-主数据"><Input /></Form.Item>
              <Form.Item name="l2" label="L2-主数据对象"><Input /></Form.Item>
            </div>
          )}
          {activeTab === '2' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Form.Item name="l3" label="L3-业务模块"><Input /></Form.Item>
              <Form.Item name="l4" label="L4-业务活动对象"><Input /></Form.Item>
              <Form.Item name="relL1" label="关联主数据大类"><Input /></Form.Item>
              <Form.Item name="relL2" label="关联主数据小类"><Input /></Form.Item>
            </div>
          )}
          {activeTab === '3' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Form.Item name="category" label="参考数据分类"><Input /></Form.Item>
            </div>
          )}
          {activeTab === '4' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Form.Item name="table_cn" label={TERMS.sourceTableCnName} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="table_en" label={TERMS.sourceTableEnName} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="field_cn" label={TERMS.sourceFieldCnName} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="field_en" label={TERMS.sourceFieldEnName} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="data_type" label="数据类型"><Input /></Form.Item>
              <Form.Item name="length_precision" label="长度/精度"><Input /></Form.Item>
              <Form.Item name="pk_fk" label="主/外键"><Input /></Form.Item>
              <Form.Item name="is_ref_data" label="是否参考数据"><Select options={[{value: '是', label: '是'}, {value: '否', label: '否'}]} /></Form.Item>
              <Form.Item name="ref_table_en" label="引用参考数据表英文名">
                <Select
                  allowClear
                  showSearch
                  options={referenceData.map(item => ({ value: item.enName, label: `${item.enName} (${item.cnName})` }))}
                />
              </Form.Item>
              <Form.Item name="ref_data_desc" label="参考数据引用说明" style={{ gridColumn: 'span 2' }}><Input.TextArea /></Form.Item>
              <Form.Item name="ref_data_usage_desc" label="参考数据调用说明" style={{ gridColumn: 'span 2' }}><Input.TextArea /></Form.Item>
              <Form.Item name="field_desc" label="字段描述" style={{ gridColumn: 'span 2' }}><Input.TextArea /></Form.Item>
            </div>
          )}
          {activeTab === '5' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Form.Item name="l1" label="L1名称"><Input /></Form.Item>
              <Form.Item name="l2" label="L2名称"><Input /></Form.Item>
              {relationSubTab !== 'l2' && <Form.Item name="l3" label="L3名称"><Input /></Form.Item>}
              {relationSubTab !== 'l2' && <Form.Item name="l4" label="L4名称"><Input /></Form.Item>}
              <Form.Item name="relation_desc" label="关联说明"><Input /></Form.Item>
              <Form.Item name="relation_category" label="关系类别"><Input /></Form.Item>
              <Form.Item name="main_table_cn" label={relationSubTab === 'cross' ? '主表中文名(L4前)' : '主表中文名'}><Input /></Form.Item>
              <Form.Item name="main_table_en" label={relationSubTab === 'cross' ? '主表英文名(L4前)' : '主表英文名'} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="related_table_cn" label={relationSubTab === 'cross' ? '关联表中文名(L2后)' : '关联表中文名'}><Input /></Form.Item>
              <Form.Item name="related_table_en" label={relationSubTab === 'cross' ? '关联表英文名(L2后)' : '关联表英文名'} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="relation_expr" label="关联条件说明（关联表达式）" style={{ gridColumn: 'span 2' }} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="remark" label="备注" style={{ gridColumn: 'span 2' }}><Input.TextArea /></Form.Item>
            </div>
          )}
        </Form>
      </Modal>

      <Modal
        title="表详情与全量字段列表"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={1000}
      >
        <Spin spinning={detailLoading}>
          {currentRecord && (
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label={TERMS.sourceTableEnName} span={1}><StatusTag preset="info">{currentRecord.enName}</StatusTag></Descriptions.Item>
              <Descriptions.Item label={TERMS.sourceTableCnName} span={1}>{tableInfo.table_cn || currentRecord.cnName}</Descriptions.Item>
              <Descriptions.Item label="系统名称">{currentRecord.sysName}</Descriptions.Item>
              <Descriptions.Item label="表类型"><StatusTag preset="success">{currentRecord.type}</StatusTag></Descriptions.Item>
            </Descriptions>
          )}
          <Divider orientation="left">表字段列表</Divider>
          <Table 
            size="small"
            rowKey={(record) => `${record.seq_no || 'no_seq'}_${record.field_en || 'no_field'}`}
            dataSource={tableFields}
            pagination={false}
            scroll={{ y: 400, x: 'max-content' }}
            columns={[
              { title: TERMS.sourceFieldEnName, dataIndex: 'field_en', width: 160 },
              { title: TERMS.sourceFieldCnName, dataIndex: 'field_cn', width: 160 },
              { title: '数据类型', dataIndex: 'data_type', width: 120 },
              { title: '字段描述', dataIndex: 'field_desc', width: 250 },
            ]}
          />
        </Spin>
      </Modal>
    </PageShell>
  );
};

export default SourceManager;
