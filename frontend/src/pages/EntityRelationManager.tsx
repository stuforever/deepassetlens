import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Col,
  Descriptions,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Upload,
  message,
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  ImportOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { conceptApi, entityRelationManagerApi } from '../services/api';
import { PageShell, DataTableShell, FilterBar, StatusTag } from '../components/shell';

const GROUP_OPTIONS = [
  { value: 'master_master', label: '主数据-主数据' },
  { value: 'master_activity', label: '主数据-业务活动' },
  { value: 'activity_activity', label: '业务活动-业务活动' },
];

const CATEGORY_OPTIONS = [
  { value: '手工维护', label: '手工维护' },
  { value: '打点维护', label: '打点维护' },
];

const CARDINALITY_OPTIONS = ['1:1', '1:N', 'N:1', 'N:N'];

const EntityRelationManager: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<any[]>([]);
  const [concepts, setConcepts] = useState<any[]>([]);
  const [groupFilter, setGroupFilter] = useState<string>();
  const [categoryFilter, setCategoryFilter] = useState<string>();
  const [keyword, setKeyword] = useState('');
  const [sourceEntityId, setSourceEntityId] = useState<string>();
  const [targetEntityId, setTargetEntityId] = useState<string>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<any>(null);
  const [form] = Form.useForm();
  const formGroup = Form.useWatch('relation_group', form);

  const fetchConcepts = useCallback(async () => {
    const res = await conceptApi.getConcepts(undefined, true);
    setConcepts(res?.data || []);
  }, []);

  const fetchRows = useCallback(async () => {
    setLoading(true);
    try {
      const res = await entityRelationManagerApi.listItems({
        relation_group: groupFilter,
        relation_category: categoryFilter,
        keyword: keyword || undefined,
        source_entity_id: sourceEntityId,
        target_entity_id: targetEntityId,
      });
      setRows(res.data?.data?.items || []);
    } catch (error) {
      console.error(error);
      message.error('加载实体关系失败');
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, groupFilter, keyword, sourceEntityId, targetEntityId]);

  useEffect(() => {
    fetchConcepts();
  }, [fetchConcepts]);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  // 维护类别由关系分组自动推导：master_activity -> 打点维护（与资产矩阵打点同义）；其它 -> 手工维护
  useEffect(() => {
    if (!modalOpen) return;
    form.setFieldsValue({
      relation_category: formGroup === 'master_activity' ? '打点维护' : '手工维护',
    });
  }, [formGroup, modalOpen, form]);

  const entityMetaMap = useMemo(() => {
    const map = new Map<string, any>();
    concepts.forEach((concept: any) => {
      (concept.entities || []).forEach((entity: any) => {
        if (!map.has(String(entity.id))) {
          map.set(String(entity.id), {
            ...entity,
            concept_level: concept.level,
            concept_name: concept.name,
          });
        }
      });
    });
    return map;
  }, [concepts]);

  const masterEntityOptions = useMemo(() => {
    return Array.from(entityMetaMap.values())
      .filter((item: any) => item.concept_level === 2)
      .sort((a: any, b: any) => String(a.entity_name || '').localeCompare(String(b.entity_name || ''), 'zh-CN'))
      .map((item: any) => ({
        value: String(item.id),
        label: `${item.entity_name} (${item.entity_code})${item.entity_en_name ? ` | ${item.entity_en_name}` : ''}`,
      }));
  }, [entityMetaMap]);

  const activityEntityOptions = useMemo(() => {
    return Array.from(entityMetaMap.values())
      .filter((item: any) => item.concept_level === 4)
      .sort((a: any, b: any) => String(a.entity_name || '').localeCompare(String(b.entity_name || ''), 'zh-CN'))
      .map((item: any) => ({
        value: String(item.id),
        label: `${item.entity_name} (${item.entity_code})${item.entity_en_name ? ` | ${item.entity_en_name}` : ''}`,
      }));
  }, [entityMetaMap]);

  const allEntityOptions = useMemo(() => {
    return [...masterEntityOptions, ...activityEntityOptions];
  }, [masterEntityOptions, activityEntityOptions]);

  const sourceOptions = useMemo(() => {
    if (formGroup === 'activity_activity') return activityEntityOptions;
    return masterEntityOptions;
  }, [activityEntityOptions, formGroup, masterEntityOptions]);

  const targetOptions = useMemo(() => {
    if (formGroup === 'master_master') return masterEntityOptions;
    if (formGroup === 'master_activity') return activityEntityOptions;
    if (formGroup === 'activity_activity') return activityEntityOptions;
    return [];
  }, [activityEntityOptions, formGroup, masterEntityOptions]);

  const openCreate = () => {
    setEditingRow(null);
    form.resetFields();
    form.setFieldsValue({
      relation_group: 'master_activity',
      relation_category: '打点维护',
      direction: 'forward',
      cardinality: '1:N',
    });
    setModalOpen(true);
  };

  const openEdit = (row: any) => {
    setEditingRow(row);
    form.setFieldsValue({
      relation_group: row.relation_group,
      source_entity_id: row.source_entity_id,
      target_entity_id: row.target_entity_id,
      relation_name: row.relation_name,
      relation_category: row.relation_category,
      direction: row.direction || 'forward',
      cardinality: row.cardinality,
      source_field_name: row.source_field_name,
      target_field_name: row.target_field_name,
      join_expr: row.join_expr,
      remark: row.remark,
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await entityRelationManagerApi.deleteItem(id);
      message.success('实体关系删除成功');
      fetchRows();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '实体关系删除失败');
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingRow) {
        await entityRelationManagerApi.updateItem(editingRow.id, values);
        message.success('实体关系更新成功');
      } else {
        await entityRelationManagerApi.createItem(values);
        message.success('实体关系新增成功');
      }
      setModalOpen(false);
      fetchRows();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || '实体关系保存失败');
    }
  };

  const handleExport = () => {
    window.open(entityRelationManagerApi.exportExcel({
      relation_group: groupFilter,
      relation_category: categoryFilter,
      keyword: keyword || undefined,
      source_entity_id: sourceEntityId,
      target_entity_id: targetEntityId,
    }), '_blank');
    message.success('导出任务已启动');
  };

  const handleImport = async (options: any) => {
    const { file, onSuccess, onError } = options;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await entityRelationManagerApi.importExcel(formData);
      const data = res.data?.data || {};
      const skipped = Array.isArray(data.skipped_rows) ? data.skipped_rows : [];
      if (skipped.length > 0) {
        message.warning(`导入完成：新增 ${data.created_count || 0}，更新 ${data.updated_count || 0}，跳过 ${skipped.length} 行`);
      } else {
        message.success(`导入成功：新增 ${data.created_count || 0}，更新 ${data.updated_count || 0}`);
      }
      onSuccess('ok');
      fetchRows();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '导入失败');
      onError(error);
    }
  };

  // 核心列（默认展示）+ 详情抽屉（次要字段）
  const [detailRow, setDetailRow] = useState<any>(null);

  const coreColumns = [
    {
      title: '关系分组',
      dataIndex: 'relation_group_label',
      width: 150,
      fixed: 'left' as const,
      render: (value: string) => <StatusTag preset="info">{value}</StatusTag>,
    },
    {
      title: '维护类别',
      dataIndex: 'relation_category',
      width: 120,
      render: (value: string) => <StatusTag preset={value === '打点维护' ? 'ai' : 'info'}>{value || '手工维护'}</StatusTag>,
    },
    { title: '关系名称', dataIndex: 'relation_name', width: 220, fixed: 'left' as const, ellipsis: true },
    { title: '源实体', dataIndex: 'source_entity_name', width: 180, ellipsis: true },
    { title: '目标实体', dataIndex: 'target_entity_name', width: 180, ellipsis: true },
    { title: '基数', dataIndex: 'cardinality', width: 100, ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, row: any) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); openEdit(row); }}>
            编辑
          </Button>
          <Popconfirm title="确认删除该实体关系？" onConfirm={(e) => { e?.stopPropagation(); handleDelete(row.id); }}>
            <Button size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageShell
      title="实体关系"
      description="维护实体间关系（主-主 / 主-活动 / 活动-活动）"
      extra={
        <Space>
          <Upload customRequest={handleImport} showUploadList={false} accept=".xlsx">
            <Button icon={<ImportOutlined />}>导入</Button>
          </Upload>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增关系</Button>
        </Space>
      }
      filters={{
        search: { placeholder: '关键字', value: keyword, onChange: setKeyword },
        filters: [
          <Select allowClear placeholder="关系分组" value={groupFilter} onChange={(value) => setGroupFilter(value)} options={GROUP_OPTIONS} style={{ minWidth: 150 }} />,
          <Select allowClear placeholder="维护类别" value={categoryFilter} onChange={(value) => setCategoryFilter(value)} options={CATEGORY_OPTIONS} style={{ minWidth: 120 }} />,
          <Select allowClear showSearch placeholder="源实体" value={sourceEntityId} onChange={(value) => setSourceEntityId(value)} options={allEntityOptions} optionFilterProp="label" style={{ minWidth: 220 }} />,
          <Select allowClear showSearch placeholder="目标实体" value={targetEntityId} onChange={(value) => setTargetEntityId(value)} options={allEntityOptions} optionFilterProp="label" style={{ minWidth: 220 }} />,
        ],
        extra: (
          <Button onClick={() => { setGroupFilter(undefined); setCategoryFilter(undefined); setSourceEntityId(undefined); setTargetEntityId(undefined); setKeyword(''); }}>重置</Button>
        ),
      }}
    >
      <DataTableShell
        compact
        tableProps={{
          dataSource: rows,
          rowKey: 'id',
          columns: coreColumns,
          loading,
          scroll: { x: 1100, y: 'calc(100vh - 360px)' },
          pagination: { pageSize: 10, style: { marginTop: 8 } },
          onRow: (row: any) => ({
            onClick: () => setDetailRow(row),
            style: { cursor: 'pointer' },
          }),
        }}
      />

      {/* 详情抽屉：展示次要字段 */}
      <Drawer
        title="关系详情"
        open={!!detailRow}
        onClose={() => setDetailRow(null)}
        width={720}
      >
        {detailRow && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="关系分组">{detailRow.relation_group_label}</Descriptions.Item>
            <Descriptions.Item label="维护类别">{detailRow.relation_category || '手工维护'}</Descriptions.Item>
            <Descriptions.Item label="关系名称" span={2}>{detailRow.relation_name}</Descriptions.Item>
            <Descriptions.Item label="源L1">{detailRow.source_l1_name}</Descriptions.Item>
            <Descriptions.Item label="源L2">{detailRow.source_l2_name}</Descriptions.Item>
            <Descriptions.Item label="源L3">{detailRow.source_l3_name}</Descriptions.Item>
            <Descriptions.Item label="源L4">{detailRow.source_l4_name}</Descriptions.Item>
            <Descriptions.Item label="源实体中文">{detailRow.source_entity_name}</Descriptions.Item>
            <Descriptions.Item label="源实体英文">{detailRow.source_entity_en_name}</Descriptions.Item>
            <Descriptions.Item label="源实体编码">{detailRow.source_entity_code}</Descriptions.Item>
            <Descriptions.Item label="基数">{detailRow.cardinality}</Descriptions.Item>
            <Descriptions.Item label="目标L1">{detailRow.target_l1_name}</Descriptions.Item>
            <Descriptions.Item label="目标L2">{detailRow.target_l2_name}</Descriptions.Item>
            <Descriptions.Item label="目标L3">{detailRow.target_l3_name}</Descriptions.Item>
            <Descriptions.Item label="目标L4">{detailRow.target_l4_name}</Descriptions.Item>
            <Descriptions.Item label="目标实体中文">{detailRow.target_entity_name}</Descriptions.Item>
            <Descriptions.Item label="目标实体英文">{detailRow.target_entity_en_name}</Descriptions.Item>
            <Descriptions.Item label="目标实体编码">{detailRow.target_entity_code}</Descriptions.Item>
            <Descriptions.Item label="源字段">{detailRow.source_field_name}</Descriptions.Item>
            <Descriptions.Item label="目标字段">{detailRow.target_field_name}</Descriptions.Item>
            <Descriptions.Item label="关联说明" span={2}>{detailRow.join_expr}</Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>{detailRow.remark}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      <Modal
        title={editingRow ? '编辑实体关系' : '新增实体关系'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        width={900}
        destroyOnHidden
        style={{ top: 20 }}
      >
        <Form form={form} layout="vertical">
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="relation_group" label="关系分组" rules={[{ required: true, message: '请选择关系分组' }]}>
                <Select
                  options={GROUP_OPTIONS}
                  onChange={() => {
                    form.setFieldsValue({ source_entity_id: undefined, target_entity_id: undefined });
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="cardinality" label="基数" rules={[{ required: true, message: '请选择基数' }]}>
                <Select options={CARDINALITY_OPTIONS.map((item) => ({ value: item, label: item }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="relation_category" label="维护类别（自动）">
                <Select options={CATEGORY_OPTIONS} disabled />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="direction" label="方向" rules={[{ required: true, message: '请选择方向' }]}>
                <Select options={[{ value: 'forward', label: '正向' }, { value: 'reverse', label: '反向' }]} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="source_entity_id" label="源实体" rules={[{ required: true, message: '请选择源实体' }]}>
                <Select showSearch optionFilterProp="label" options={sourceOptions} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="target_entity_id" label="目标实体" rules={[{ required: true, message: '请选择目标实体' }]}>
                <Select showSearch optionFilterProp="label" options={targetOptions} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="relation_name" label="关系名称">
                <Input placeholder="为空时自动按源实体和目标实体生成" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="source_field_name" label="源字段">
                <Input placeholder="如 cust_id" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="target_field_name" label="目标字段">
                <Input placeholder="如 customer_id" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="join_expr" label="关联说明">
                <Input.TextArea rows={3} placeholder="为空时自动按 源字段 = 目标字段 生成" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="remark" label="备注">
                <Input.TextArea rows={3} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </PageShell>
  );
};

export default EntityRelationManager;
