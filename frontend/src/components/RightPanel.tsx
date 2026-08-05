import React, { useState, useEffect } from 'react';
import { Card, Descriptions, Empty, Tag, Divider, Table, Button, Space, Typography, Modal, Form, Input, message, Spin, List, Switch, Select } from 'antd';
import { useStore } from '../store/useStore';
import { EditOutlined, LinkOutlined, DatabaseOutlined, SettingOutlined, PlusOutlined, DeploymentUnitOutlined, DeleteOutlined, ShareAltOutlined } from '@ant-design/icons';
import { entityApi, mappingApi, entityRelationApi, conceptApi } from '../services/api';
import LineageGraph from './LineageGraph';
import { StatusTag } from './shell';

const { Text } = Typography;

type Props = {
  onOpenTarget?: (menuKey: string) => void;
};

const RightPanel: React.FC<Props> = ({ onOpenTarget }) => {
  const { selectedNode, setSelectedNode, fetchConcepts } = useStore();
  const [isAddEntityModalVisible, setAddEntityModalVisible] = useState(false);
  const [lineageData, setLineageData] = useState<any>(null);
  const [loadingLineage, setLoadingLineage] = useState(false);
  const [lineageGraphVisible, setLineageGraphVisible] = useState(false);
  const [form] = Form.useForm();
  const [relationForm] = Form.useForm();
  
  const [editingEntity, setEditingEntity] = useState<any>(null);
  const [editingRelation, setEditingRelation] = useState<any>(null);
  const [entityRelations, setEntityRelations] = useState<any[]>([]);
  const [isRelationModalVisible, setRelationModalVisible] = useState(false);
  const [allEntities, setAllEntities] = useState<any[]>([]); // 用于关系选择目标实体
  const [l2Concepts, setL2Concepts] = useState<any[]>([]); // 用于实体关联 L2

  const [propertiesForm] = Form.useForm();
  const [isPropertiesModalVisible, setPropertiesModalVisible] = useState(false);
  const [isPropertyListModalVisible, setPropertyListModalVisible] = useState(false);
  const [isConceptModalVisible, setConceptModalVisible] = useState(false);
  const [conceptModalMode, setConceptModalMode] = useState<'create' | 'edit'>('create');
  const [conceptForm] = Form.useForm();

  const isVirtualConceptNode = (node: any) => {
    if (!node) return false;
    return node.id === 'root';
  };

  const calcCreateConceptContext = () => {
    if (!selectedNode) return { level: 1, parent_id: null as any, area_index: 1 };
    if (selectedNode.id === 'root') {
      return { level: 1, parent_id: null as any, area_index: 1 };
    }
    const currentLevel = selectedNode.level || 1;
    if (currentLevel >= 4) return null;
    return {
      level: currentLevel + 1,
      parent_id: selectedNode.id,
      area_index: selectedNode.area_index || 1,
    };
  };

  const handleOpenPropertiesModal = () => {
    // 确保从最新的 selectedNode 中读取
    const props = selectedNode.properties_schema || [];
    propertiesForm.setFieldsValue({ properties: props });
    setPropertiesModalVisible(true);
  };

  const handleSaveProperties = async () => {
    try {
      const values = await propertiesForm.validateFields();
      
      // 调用真实后端 API 更新实体属性
      const res = await entityApi.updateEntity(selectedNode.id, {
        properties_schema: values.properties || []
      });
      
      message.success('属性规格保存成功');
      
      // 更新当前选中的节点状态以触发重绘
      setSelectedNode({
        ...selectedNode,
        properties_schema: res.data.properties_schema || values.properties || []
      });
      
      // 如果需要在图谱层级同步刷新数据，可调用外部传入的 fetchConcepts (如果存在)
      if (typeof fetchConcepts === 'function') {
        fetchConcepts();
      }
      
      setPropertiesModalVisible(false);
    } catch (error) {
      console.error(error);
      message.error('属性规格保存失败，请检查填写内容');
    }
  };

  const handleOpenCreateConcept = () => {
    const ctx = calcCreateConceptContext();
    if (!ctx) {
      message.warning('L4 概念下不能继续新增下级概念');
      return;
    }
    setConceptModalMode('create');
    conceptForm.setFieldsValue({
      level: ctx.level,
      parent_id: ctx.parent_id,
      name: '',
      description: '',
    });
    setConceptModalVisible(true);
  };

  const handleOpenEditConcept = () => {
    if (!selectedNode || isVirtualConceptNode(selectedNode) || isEntity) return;
    setConceptModalMode('edit');
    conceptForm.setFieldsValue({
      name: selectedNode.name || selectedNode.label,
      description: selectedNode.description || '',
    });
    setConceptModalVisible(true);
  };

  const handleSaveConcept = async () => {
    try {
      const values = await conceptForm.validateFields();
      if (conceptModalMode === 'create') {
        await conceptApi.createConcept({
          ...values,
          level: Number(values.level),
          parent_id: values.parent_id ? values.parent_id : null,
        });
        message.success('概念新增成功');
      } else {
        await conceptApi.updateConcept(selectedNode.id, {
          name: values.name,
          description: values.description,
        });
        message.success('概念更新成功');
      }
      setConceptModalVisible(false);
      await fetchConcepts();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '概念保存失败');
    }
  };

  const handleDeleteConcept = () => {
    if (!selectedNode || isVirtualConceptNode(selectedNode) || isEntity) return;
    Modal.confirm({
      title: '确认删除当前概念节点？',
      content: '仅当该概念下无子概念且无数据实体时才允许删除。',
      onOk: async () => {
        try {
          await conceptApi.deleteConcept(selectedNode.id);
          message.success('概念删除成功');
          setSelectedNode(null);
          await fetchConcepts();
        } catch (e: any) {
          message.error(e?.response?.data?.detail || '概念删除失败');
        }
      }
    });
  };
  useEffect(() => {
    const fetchAllEntities = async () => {
      try {
        const res = await conceptApi.getGraphData();
        const entities = res.data.nodes.filter((n: any) => n.type === 'entity');
        // 将 label 映射回 entity_name 以便渲染
        setAllEntities(entities.map((e: any) => ({ ...e, entity_name: e.label, entity_code: e.entity_code || e.id })));
      } catch (e) {}
    };
    fetchAllEntities();

    const fetchL2 = async () => {
      try {
        const res = await conceptApi.getConcepts(2);
        setL2Concepts(res.data || []);
      } catch (e) {}
    };
    fetchL2();
  }, []);

  const isEntity = selectedNode?.isEntity || selectedNode?.type === 'entity';
  const isConcept = !isEntity;

  const toMappingRows = (mappingLogic: any) => {
    let obj: any = mappingLogic;
    if (typeof mappingLogic === 'string') {
      try {
        obj = JSON.parse(mappingLogic);
      } catch {
        obj = null;
      }
    }
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return [];
    return Object.entries(obj).map(([k, v]) => ({ target: String(k), source: String(v) }));
  };

  const toPrettyText = (value: any) => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  };

  const toInlineText = (value: any, fallback = '-') => {
    if (value === null || value === undefined || value === '') return fallback;
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };

  // 选中实体时获取溯源信息和实体关系
  useEffect(() => {
    if (selectedNode && isEntity) {
      const fetchLineageAndRelations = async () => {
        setLoadingLineage(true);
        try {
          const [lineageRes, relRes] = await Promise.all([
            mappingApi.getLineage(selectedNode.id).catch(() => ({ data: null })),
            entityRelationApi.getRelations(selectedNode.id).catch(() => ({ data: [] }))
          ]);
          setLineageData(lineageRes.data);
          setEntityRelations(relRes.data || []);
        } catch (error) {
          console.error('Failed to fetch data:', error);
        } finally {
          setLoadingLineage(false);
        }
      };
      fetchLineageAndRelations();
    } else {
      setLineageData(null);
      setEntityRelations([]);
    }
  }, [selectedNode, isEntity]);

  if (!selectedNode) {
    return (
      <Card title="详情配置" style={{ height: '100%' }}>
        <Empty description="请在左侧画布选择节点" />
      </Card>
    );
  }

  const handleOpenMapping = () => {
    try {
      const firstMappingId = (lineageData?.lineage || [])[0]?.mapping_id;
      sessionStorage.setItem(
        'mapping_jump_params',
        JSON.stringify({
          from: 'graph_detail',
          entity_id: selectedNode?.id,
          mapping_id: firstMappingId || null,
          ts: Date.now(),
        })
      );
    } catch {}
    onOpenTarget?.('mapping');
  };

  const handleAddEntity = async () => {
    try {
      const values = await form.validateFields();
      if (editingEntity) {
        await entityApi.updateEntity(editingEntity.id, values);
        message.success('实体更新成功');
      } else {
        await entityApi.createEntity({
          ...values,
          concept_id: selectedNode.id,
        });
        message.success('实体创建成功');
      }
      setAddEntityModalVisible(false);
      setEditingEntity(null);
      form.resetFields();
      // 刷新数据以显示新实体
      fetchConcepts();
      
      // 如果当前正在查看这个实体，更新选中的节点状态
      if (editingEntity && selectedNode.id === editingEntity.id) {
        setSelectedNode({ ...selectedNode, ...values });
      }
    } catch (error) {
      console.error('Failed to save entity:', error);
      message.error('实体保存失败');
    }
  };

  const handleDeleteEntity = (e: React.MouseEvent, entityId: string) => {
    e.stopPropagation();
    Modal.confirm({
      title: '确认删除该数据实体吗？',
      content: '删除后无法恢复，且会同步删除其相关映射和关系配置。',
      onOk: async () => {
        try {
          await entityApi.deleteEntity(entityId);
          message.success('删除成功');
          fetchConcepts();
          if (selectedNode?.id === entityId) {
            setSelectedNode(null);
          }
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  const handleEditEntity = (e: React.MouseEvent, entity: any) => {
    e.stopPropagation();
    setEditingEntity(entity);
    form.setFieldsValue({
      entity_name: entity.entity_name,
      entity_en_name: entity.entity_en_name,
      entity_code: entity.entity_code,
      description: entity.description,
      is_main_table: entity.is_main_table,
      data_layer: entity.data_layer,
      concept_ids: entity.concept_ids || [],
    });
    setAddEntityModalVisible(true);
  };

  const handleOpenAddEntity = () => {
    setEditingEntity(null);
    form.resetFields();
    setAddEntityModalVisible(true);
  };

  const handleOpenCreateRelation = () => {
    setEditingRelation(null);
    relationForm.resetFields();
    setRelationModalVisible(true);
  };

  const handleOpenEditRelation = (rel: any) => {
    setEditingRelation(rel);
    relationForm.setFieldsValue({
      target_entity_id: rel.target_entity_id,
      relation_name: rel.relation_name,
      direction: rel.direction || 'forward',
      cardinality: rel.cardinality || 'N:N',
      join_expr: rel.join_expr,
      description: rel.description,
    });
    setRelationModalVisible(true);
  };

  const handleAddRelation = async () => {
    try {
      const values = await relationForm.validateFields();
      if (editingRelation) {
        await entityRelationApi.updateRelation(editingRelation.id, {
          ...values,
          source_entity_id: selectedNode.id,
        });
        message.success('关系更新成功');
      } else {
        await entityRelationApi.createRelation({
          ...values,
          source_entity_id: selectedNode.id,
        });
        message.success('关系创建成功');
      }
      setRelationModalVisible(false);
      setEditingRelation(null);
      relationForm.resetFields();
      const relRes = await entityRelationApi.getRelations(selectedNode.id);
      setEntityRelations(relRes.data || []);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      const detailText = Array.isArray(detail)
        ? detail.map((x: any) => x?.msg || JSON.stringify(x)).join('; ')
        : (typeof detail === 'object' && detail !== null)
          ? JSON.stringify(detail)
          : detail;
      message.error(detailText || (editingRelation ? '关系更新失败' : '关系保存失败'));
    }
  };

  const handleDeleteRelation = async (relId: string) => {
    try {
      await entityRelationApi.deleteRelation(relId);
      message.success('关系删除成功');
      const relRes = await entityRelationApi.getRelations(selectedNode.id);
      setEntityRelations(relRes.data || []);
    } catch (error) {
      message.error('关系删除失败');
    }
  };

  return (
    <Card 
      title={
        <Space>
          <DatabaseOutlined />
          <span>{toInlineText(selectedNode.name || selectedNode.label, '')}</span>
        </Space>
      }
      extra={
        isConcept && !isVirtualConceptNode(selectedNode)
          ? <Button type="link" icon={<EditOutlined />} onClick={handleOpenEditConcept}>编辑概念</Button>
          : null
      }
      style={{ height: '100%', overflowY: 'auto' }}
    >
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="ID">{selectedNode.id}</Descriptions.Item>
        <Descriptions.Item label="类型">
          <StatusTag preset={isConcept ? 'info' : 'error'}>
            {isConcept ? `概念分类 (L${selectedNode.level})` : '数据实体'}
          </StatusTag>
        </Descriptions.Item>
        {!isConcept && (
          <>
            <Descriptions.Item label="实体中文名称">
              {toInlineText(selectedNode.entity_name || selectedNode.label)}
            </Descriptions.Item>
            <Descriptions.Item label="实体落地英文表名">
              {toInlineText(selectedNode.entity_en_name || selectedNode.landing_table_en_name)}
            </Descriptions.Item>
            <Descriptions.Item label="实体唯一编码">
              {toInlineText(selectedNode.entity_code || selectedNode.id)}
            </Descriptions.Item>
          </>
        )}
        {isConcept && (
          <Descriptions.Item label="说明">
            {toInlineText(selectedNode.description, '分类节点，下属数据实体')}
          </Descriptions.Item>
        )}
      </Descriptions>

      {isConcept && (selectedNode.level === 2 || selectedNode.level === 4) && (
        <>
          <Divider orientation="left">下属数据实体</Divider>
          <div style={{ padding: '8px 0' }}>
            {selectedNode.entities && selectedNode.entities.length > 0 ? (
              <List
                size="small"
                bordered
                dataSource={selectedNode.entities}
                renderItem={(item: any) => (
                  <List.Item
                    style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between' }}
                    onClick={() => setSelectedNode({ ...item, type: 'entity' })}
                    actions={[
                      <EditOutlined key="edit" onClick={(e) => handleEditEntity(e, item)} style={{ color: 'var(--color-primary)' }} />,
                      <DeleteOutlined key="delete" onClick={(e) => handleDeleteEntity(e, item.id)} style={{ color: 'var(--color-error)' }} />
                    ]}
                  >
                    <div>
                      <Typography.Text strong>{toInlineText(item.entity_name, '')}</Typography.Text>
                      <br/>
                      <Typography.Text type="secondary" style={{ fontSize: '12px' }}>
                        {toInlineText(item.entity_code, '')}{item.entity_en_name ? ` | ${toInlineText(item.entity_en_name, '')}` : ''}
                      </Typography.Text>
                    </div>
                    {item.is_main_table && <StatusTag preset="info" style={{ marginLeft: '8px' }}>主表</StatusTag>}
                  </List.Item>
                )}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无下属实体" />
            )}
            <div style={{ marginTop: '12px' }}>
              <Button 
                size="small" 
                type="dashed" 
                block 
                icon={<PlusOutlined />}
                onClick={handleOpenAddEntity}
              >
                新增实体
              </Button>
            </div>
          </div>
        </>
      )}

      {isConcept && (
        <>
          <Divider orientation="left">概念节点管理</Divider>
          <Space style={{ marginBottom: 12 }}>
            <Button type="dashed" icon={<PlusOutlined />} onClick={handleOpenCreateConcept}>新增下级概念</Button>
            {!isVirtualConceptNode(selectedNode) && (
              <Button type="default" icon={<EditOutlined />} onClick={handleOpenEditConcept}>编辑当前概念</Button>
            )}
            {!isVirtualConceptNode(selectedNode) && (
              <Button danger type="default" icon={<DeleteOutlined />} onClick={handleDeleteConcept}>删除当前概念</Button>
            )}
          </Space>
        </>
      )}

      {!isConcept && (
        <>
          <Divider orientation="left">实体间关系</Divider>
          <div style={{ padding: '8px 0' }}>
            {entityRelations && entityRelations.length > 0 ? (
              <List
                size="small"
                bordered
                dataSource={entityRelations}
                renderItem={(rel: any) => {
                  const isSource = rel.source_entity_id === selectedNode.id;
                  const targetEntityId = isSource ? rel.target_entity_id : rel.source_entity_id;
                  const relatedEntity = allEntities.find(e => e.id === targetEntityId);
                  
                  return (
                    <List.Item
                      actions={[
                        <EditOutlined key="edit" onClick={() => handleOpenEditRelation(rel)} style={{ color: 'var(--color-primary)' }} />,
                        <DeleteOutlined key="delete" onClick={() => handleDeleteRelation(rel.id)} style={{ color: 'var(--color-error)' }} />
                      ]}
                    >
                      <Space>
                        <StatusTag preset={isSource ? 'success' : 'warning'}>{isSource ? '正向' : '反向'}</StatusTag>
                        <Text strong>{rel.relation_name}</Text>
                        <StatusTag preset="ai">{rel.direction === 'reverse' ? '反向定义' : '正向定义'}</StatusTag>
                        <StatusTag preset="info">{rel.cardinality || 'N:N'}</StatusTag>
                        {rel.join_expr ? <StatusTag preset="info">{rel.join_expr}</StatusTag> : null}
                        <Text type="secondary">({relatedEntity ? relatedEntity.entity_name : '未知实体'})</Text>
                      </Space>
                    </List.Item>
                  );
                }}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无实体关系" />
            )}
            <Button 
              size="small" 
              type="dashed" 
              block 
              icon={<ShareAltOutlined />}
              onClick={handleOpenCreateRelation}
              style={{ marginTop: '12px' }}
            >
              添加关系
            </Button>
          </div>

          <Divider orientation="left">属性规格</Divider>
          <div style={{ padding: '8px 0' }}>
            <Table 
              size="small"
              pagination={false}
              rowKey="name"
              columns={[
                { title: '属性英文名', dataIndex: 'name', key: 'name', width: '20%' },
                { title: '属性中文名', dataIndex: 'cnName', key: 'cnName', width: '20%', render: (v) => <div style={{ whiteSpace: 'normal', wordBreak: 'break-all' }}>{v || '-'}</div> },
                { title: '类型', dataIndex: 'type', key: 'type', width: '15%' },
                { title: '是否主键', dataIndex: 'isPrimaryKey', key: 'isPrimaryKey', width: '15%', render: (val) => val ? <StatusTag preset="error">是</StatusTag> : <Tag>否</Tag> },
                { title: '说明', dataIndex: 'description', key: 'description', render: (v) => <div style={{ whiteSpace: 'normal', wordBreak: 'break-all' }}>{v || '-'}</div> }
              ]}
              dataSource={selectedNode.properties_schema || []}
              locale={{ emptyText: '暂无属性，请点击下方添加' }}
            />
            <Space style={{ width: '100%', marginTop: '12px' }}>
              <Button
                size="small"
                type="default"
                block
                onClick={() => setPropertyListModalVisible(true)}
              >
                查看属性清单
              </Button>
              <Button 
                size="small" 
                type="dashed" 
                block 
                icon={<SettingOutlined />}
                onClick={handleOpenPropertiesModal}
              >
                管理属性规格
              </Button>
            </Space>
          </div>

          <Divider orientation="left">映射规则详情（与映射规则模块一致）</Divider>
          {loadingLineage ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <Spin tip="加载映射规则中..." />
            </div>
          ) : lineageData?.lineage && lineageData.lineage.length > 0 ? (
            <Space direction="vertical" style={{ width: '100%' }}>
              {lineageData.lineage.map((item: any) => (
                <Card 
                  size="small" 
                  type="inner" 
                  key={item.mapping_id}
                  title={
                    <Space>
                      <DatabaseOutlined style={{ color: 'var(--color-primary)' }} />
                      <span>{item.source_table.table_name}</span>
                    </Space>
                  }
                  extra={<StatusTag preset="success">已同步</StatusTag>}
                >
                  <div style={{ marginBottom: '8px' }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>映射规则(JSON): </Text>
                    <div style={{ 
                      background: 'var(--bg-hover)', 
                      padding: '8px', 
                      borderRadius: '4px', 
                      fontSize: '11px',
                      fontFamily: 'monospace',
                      maxHeight: '100px',
                      overflowY: 'auto'
                    }}>
                      {toPrettyText(item.mapping_logic)}
                    </div>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>映射字段明细: </Text>
                    <Table
                      size="small"
                      pagination={false}
                      rowKey="target"
                      dataSource={toMappingRows(item.mapping_logic)}
                      columns={[
                        { title: '目标字段', dataIndex: 'target', width: '45%' },
                        { title: '来源字段', dataIndex: 'source' },
                      ]}
                      locale={{ emptyText: '暂无可解析字段映射' }}
                    />
                  </div>
                  {item.sql_fragment && (
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>映射SQL片段: </Text>
                      <div style={{ 
                        background: 'var(--bg-hover)', 
                        padding: '8px', 
                        borderRadius: '4px', 
                        fontSize: '11px',
                        fontFamily: 'monospace',
                        color: 'var(--text-secondary)'
                      }}>
                        {toPrettyText(item.sql_fragment)}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
              <Button block icon={<LinkOutlined />} onClick={handleOpenMapping}>进入映射规则维护</Button>
            </Space>
          ) : (
            <Empty 
              image={Empty.PRESENTED_IMAGE_SIMPLE} 
              description="暂无映射规则，点击下方维护"
            >
              <Button type="primary" size="small" icon={<LinkOutlined />} onClick={handleOpenMapping}>
                去维护映射规则
              </Button>
            </Empty>
          )}
          
          <Divider orientation="left">智能路径</Divider>
           <Button 
             block 
             icon={<DeploymentUnitOutlined />} 
             type="dashed"
             disabled={!lineageData}
             onClick={() => setLineageGraphVisible(true)}
           >
             可视化溯源链路
           </Button>
         </>
       )}

      <LineageGraph 
        visible={lineageGraphVisible} 
        onClose={() => setLineageGraphVisible(false)} 
        data={lineageData} 
      />

      <Modal
        title={editingEntity ? "编辑数据实体" : "新增数据实体"}
        open={isAddEntityModalVisible}
        onOk={handleAddEntity}
        onCancel={() => setAddEntityModalVisible(false)}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="entity_name"
            label="实体中文名称"
            rules={[{ required: true, message: '请输入实体中文名称' }]}
          >
            <Input placeholder="例如：用电户" />
          </Form.Item>
          <Form.Item
            name="entity_en_name"
            label="实体落地英文表名"
          >
            <Input placeholder="例如：dim_02_cms20_elec_cons_cust" />
          </Form.Item>
          <Form.Item
            name="entity_code"
            label="实体唯一编码"
            rules={[{ required: true, message: '请输入实体唯一编码' }]}
          >
            <Input placeholder="例如：E_ELEC_ACCOUNT" disabled={!!editingEntity} />
          </Form.Item>
          <Form.Item
            name="description"
            label="实体详细描述"
          >
            <Input.TextArea placeholder="请输入实体的详细说明..." />
          </Form.Item>
          <Form.Item
            name="data_layer"
            label="数据层级"
          >
            <Select placeholder="请选择数据层级" allowClear>
              <Select.Option value="ODS">ODS 贴源层</Select.Option>
              <Select.Option value="DWD">DWD 明细层</Select.Option>
              <Select.Option value="DWS">DWS 汇总层</Select.Option>
              <Select.Option value="ADS">ADS 应用层</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="concept_ids"
            label="关联主数据 (L2 概念)"
          >
            <Select 
              mode="multiple" 
              placeholder="选择关联的主数据分类" 
              allowClear 
              showSearch
              optionFilterProp="children"
            >
              {l2Concepts.map(c => (
                <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="is_main_table"
            label="是否主表"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={conceptModalMode === 'create' ? '新增概念节点' : '编辑概念节点'}
        open={isConceptModalVisible}
        onCancel={() => setConceptModalVisible(false)}
        onOk={handleSaveConcept}
        destroyOnHidden
      >
        <Form form={conceptForm} layout="vertical">
          {conceptModalMode === 'create' && (
            <>
              <Form.Item name="level" label="层级" rules={[{ required: true }]}>
                <Input disabled />
              </Form.Item>
              <Form.Item name="parent_id" label="父节点ID">
                <Input disabled />
              </Form.Item>
            </>
          )}
          <Form.Item name="name" label="概念名称" rules={[{ required: true, message: '请输入概念名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingRelation ? "编辑实体关系" : "添加实体关系"}
        open={isRelationModalVisible}
        onOk={handleAddRelation}
        onCancel={() => {
          setRelationModalVisible(false);
          setEditingRelation(null);
        }}
        destroyOnHidden
      >
        <Form form={relationForm} layout="vertical">
          <Form.Item
            name="target_entity_id"
            label="目标实体"
            rules={[{ required: true, message: '请选择目标实体' }]}
          >
            <Select placeholder="选择关联的实体" showSearch optionFilterProp="children">
              {allEntities.filter(e => e.id !== selectedNode?.id).map(e => (
                <Select.Option key={e.id} value={e.id}>{e.entity_name} ({e.entity_code})</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="relation_name"
            label="关系名称"
            rules={[{ required: true, message: '请输入关系名称' }]}
          >
            <Input placeholder="例如：属于、关联、依赖" />
          </Form.Item>
          <Form.Item
            name="direction"
            label="关系方向"
            rules={[{ required: true, message: '请选择关系方向' }]}
            initialValue="forward"
          >
            <Select
              options={[
                { value: 'forward', label: '正向' },
                { value: 'reverse', label: '反向' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="cardinality"
            label="关系基数"
            rules={[{ required: true, message: '请选择关系基数' }]}
            initialValue="N:N"
          >
            <Select
              options={[
                { value: '1:N', label: '1:N' },
                { value: 'N:1', label: 'N:1' },
                { value: 'N:N', label: 'N:N' },
                { value: '1:1', label: '1:1' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="join_expr"
            label="关联字段表达式(join_expr)"
            rules={[{ required: true, message: '请输入关联字段表达式，如 A.ID = B.ID' }]}
          >
            <Input placeholder="例如：dim_02_cms20_elec_cons_cust.cons_no = dim_02_cms20_cert_set.cons_no" />
          </Form.Item>
          <Form.Item
            name="description"
            label="关系描述"
          >
            <Input.TextArea placeholder="请输入关于此关系的说明..." />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="维护实体属性规格"
        open={isPropertiesModalVisible}
        onOk={handleSaveProperties}
        onCancel={() => setPropertiesModalVisible(false)}
        width={800}
        destroyOnHidden
      >
        <Form form={propertiesForm} layout="vertical">
          <Form.List name="properties">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                    <Form.Item
                      {...restField}
                      name={[name, 'name']}
                      rules={[{ required: true, message: '必填' }]}
                    >
                      <Input placeholder="属性英文名(id)" style={{ width: 130 }} />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'cnName']}
                      rules={[{ required: true, message: '必填' }]}
                    >
                      <Input placeholder="属性中文名" style={{ width: 130 }} />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'type']}
                      rules={[{ required: true, message: '必填' }]}
                    >
                      <Select placeholder="数据类型" style={{ width: 110 }}>
                        <Select.Option value="string">string</Select.Option>
                        <Select.Option value="int">int</Select.Option>
                        <Select.Option value="float">float</Select.Option>
                        <Select.Option value="boolean">boolean</Select.Option>
                        <Select.Option value="datetime">datetime</Select.Option>
                      </Select>
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'isPrimaryKey']}
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="主键" unCheckedChildren="非主键" />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'enable_query_entity']}
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="问实体" unCheckedChildren="不识别" />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'description']}
                    >
                      <Input placeholder="说明备注" style={{ width: 150 }} />
                    </Form.Item>
                    <DeleteOutlined onClick={() => remove(name)} style={{ color: 'var(--color-error)' }} />
                  </Space>
                ))}
                <Form.Item>
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    添加属性字段
                  </Button>
                </Form.Item>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      <Modal
        title="实体属性清单"
        open={isPropertyListModalVisible}
        onCancel={() => setPropertyListModalVisible(false)}
        footer={null}
        width={980}
      >
        <Table
          size="middle"
          rowKey={(r: any, idx) => `${r?.name || 'p'}-${idx}`}
          pagination={{ pageSize: 10 }}
          dataSource={selectedNode?.properties_schema || []}
          locale={{ emptyText: '暂无属性清单' }}
          columns={[
            { title: '属性英文名', dataIndex: 'name', width: 180 },
            { title: '属性中文名', dataIndex: 'cnName', width: 220, render: (v) => <div style={{ whiteSpace: 'normal', wordBreak: 'break-all' }}>{v || '-'}</div> },
            { title: '类型', dataIndex: 'type', width: 120 },
            { title: '主键', dataIndex: 'isPrimaryKey', width: 90, render: (val) => val ? <StatusTag preset="error">是</StatusTag> : <Tag>否</Tag> },
            { title: '问实体识别', dataIndex: 'enable_query_entity', width: 110, render: (val) => val ? <StatusTag preset="success">是</StatusTag> : <Tag>否</Tag> },
            { title: '说明', dataIndex: 'description', render: (v) => <div style={{ whiteSpace: 'normal', wordBreak: 'break-all' }}>{v || '-'}</div> },
          ]}
        />
      </Modal>
    </Card>
  );
};

export default RightPanel;
