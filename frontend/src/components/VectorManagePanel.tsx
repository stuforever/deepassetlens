import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Drawer,
  Form,
  Input,
  List,
  message,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from 'antd';
import {
  DatabaseOutlined,
  DeleteOutlined,
  FileTextOutlined,
  InboxOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  SyncOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { knowledgeBaseApi, standardSemanticApi, vectorManageApi } from '../services/api';
import { StatusTag, type StatusPreset } from './shell';

const { Text, Paragraph } = Typography;

type CollectionKey = 'entity' | 'attribute';

interface CollectionMeta {
  key: CollectionKey;
  label: string;
  collectionName: string;
  description: string;
}

const COLLECTIONS: CollectionMeta[] = [
  {
    key: 'entity',
    label: '实体向量库',
    collectionName: 'entity_embeddings',
    description: 'kg_entities.entity_name -> 向量，供 locate_entity_attribute / explore 技能召回实体',
  },
  {
    key: 'attribute',
    label: '属性向量库',
    collectionName: 'attribute_embeddings',
    description: 'kg_entities.properties_schema 提炼属性名 -> 向量，供技能召回属性',
  },
];

// 自定义知识库状态 -> StatusTag preset 映射
const KB_STATUS_PRESET: Record<string, StatusPreset> = {
  ready: 'success',
  processing: 'warning',
  error: 'error',
};
const DOC_STATUS_PRESET: Record<string, StatusPreset> = {
  vectorized: 'success',
  pending: 'warning',
  error: 'error',
};

const VectorManagePanel: React.FC = () => {
  // ---- 默认双库 ----
  const [stats, setStats] = useState<Record<CollectionKey, any>>({ entity: null, attribute: null });
  const [loadingStats, setLoadingStats] = useState<Record<CollectionKey, boolean>>({ entity: false, attribute: false });
  const [syncing, setSyncing] = useState<CollectionKey | null>(null);

  // ---- 模型选择器 ----
  const [modelOptions, setModelOptions] = useState<{ label: string; value: string }[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('');
  const [modelLoading, setModelLoading] = useState(false);

  // ---- 查询测试（默认库）----
  const [queryCollection, setQueryCollection] = useState<CollectionKey>('entity');
  const [queryText, setQueryText] = useState('');
  const [queryTopK, setQueryTopK] = useState(10);
  const [queryResults, setQueryResults] = useState<any[]>([]);
  const [queryLoading, setQueryLoading] = useState(false);

  // ---- 自定义知识库 ----
  const [kbList, setKbList] = useState<any[]>([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);
  // 详情 Drawer
  const [activeKb, setActiveKb] = useState<any | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [vectorizing, setVectorizing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadFileList, setUploadFileList] = useState<UploadFile[]>([]);
  // KB 内检索测试
  const [kbQuery, setKbQuery] = useState('');
  const [kbTopK, setKbTopK] = useState(5);
  const [kbSearchResults, setKbSearchResults] = useState<any[]>([]);
  const [kbSearching, setKbSearching] = useState(false);

  // ---------- 默认库统计 ----------
  const fetchStats = useCallback(async (key: CollectionKey) => {
    setLoadingStats((s) => ({ ...s, [key]: true }));
    try {
      const res = key === 'entity' ? await vectorManageApi.getEntityVectorStats() : await vectorManageApi.getAttributeVectorStats();
      const data = res?.data?.data ?? res?.data ?? null;
      setStats((s) => ({ ...s, [key]: data }));
    } catch (e: any) {
      message.error(`查询${key === 'entity' ? '实体' : '属性'}库统计失败: ${e?.response?.data?.detail || e?.message}`);
    } finally {
      setLoadingStats((s) => ({ ...s, [key]: false }));
    }
  }, []);

  const fetchAllStats = useCallback(() => {
    fetchStats('entity');
    fetchStats('attribute');
  }, [fetchStats]);

  // ---------- 模型 ----------
  const fetchModelInfo = useCallback(async () => {
    setModelLoading(true);
    try {
      const [regRes, cfgRes] = await Promise.all([standardSemanticApi.getVectorModels(), standardSemanticApi.getModelConfig()]);
      const models = regRes?.data?.data?.models || [];
      setModelOptions(models.map((m: any) => ({ label: m.model_name || m.key, value: m.model_name || m.key })));
      setCurrentModel(cfgRes?.data?.data?.model_name || cfgRes?.data?.model_name || '');
    } catch (e: any) {
      // 模型加载失败不阻断页面
      console.warn('load model info failed', e);
    } finally {
      setModelLoading(false);
    }
  }, []);

  const handleModelChange = async (value: string) => {
    const prev = currentModel;
    setCurrentModel(value);
    try {
      await standardSemanticApi.updateModelConfig({ model_name: value });
      message.success(`向量模型已切换为 ${value}（后续向量化将使用新模型）`);
    } catch (e: any) {
      setCurrentModel(prev);
      message.error(`切换模型失败: ${e?.response?.data?.detail || e?.message}`);
    }
  };

  // ---------- 自定义知识库 ----------
  const fetchKbList = useCallback(async () => {
    setKbLoading(true);
    try {
      const res = await knowledgeBaseApi.list();
      setKbList(res?.data?.data || []);
    } catch (e: any) {
      message.error(`加载知识库列表失败: ${e?.response?.data?.detail || e?.message}`);
    } finally {
      setKbLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllStats();
    fetchModelInfo();
    fetchKbList();
  }, [fetchAllStats, fetchModelInfo, fetchKbList]);

  // ---- 同步：全量重建 / 增量同步 ----
  const handleSync = async (key: CollectionKey, force: boolean) => {
    setSyncing(key);
    try {
      const res = key === 'entity' ? await vectorManageApi.syncEntityVectors(force) : await vectorManageApi.syncAttributeVectors(force);
      const data = res?.data?.data ?? res?.data;
      message.success(res?.data?.message || `${force ? '全量重建' : '增量同步'}完成：${data?.synced ?? 0} 条`);
      fetchStats(key);
    } catch (e: any) {
      message.error(`同步失败: ${e?.response?.data?.detail || e?.message}`);
    } finally {
      setSyncing(null);
    }
  };

  // ---- 查询测试 ----
  const runQuery = async () => {
    if (!queryText.trim()) {
      message.warning('请输入查询文本');
      return;
    }
    setQueryLoading(true);
    try {
      const res = await vectorManageApi.queryVectors({ collection: queryCollection, query: queryText, top_k: queryTopK });
      setQueryResults((res?.data?.data?.matches || []) as any[]);
    } catch (e: any) {
      message.error(`查询失败: ${e?.response?.data?.detail || e?.message}`);
    } finally {
      setQueryLoading(false);
    }
  };

  // ---- 创建知识库 ----
  const handleCreateKb = async () => {
    try {
      const values = await createForm.validateFields();
      setCreating(true);
      const res = await knowledgeBaseApi.create({ name: values.name, description: values.description });
      message.success(res?.data?.message || '知识库已创建');
      setCreateModalOpen(false);
      createForm.resetFields();
      fetchKbList();
    } catch (e: any) {
      if (e?.errorFields) return; // 表单校验错误
      message.error(`创建失败: ${e?.response?.data?.detail || e?.message}`);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteKb = async (kb: any) => {
    Modal.confirm({
      title: '删除知识库',
      content: `确定删除「${kb.name}」？将同时清除其文档与向量，不可恢复。`,
      okType: 'danger',
      okText: '删除',
      cancelText: '取消',
      onOk: async () => {
        try {
          await knowledgeBaseApi.delete(kb.id);
          message.success('知识库已删除');
          if (activeKb?.id === kb.id) {
            setDrawerOpen(false);
            setActiveKb(null);
          }
          fetchKbList();
        } catch (e: any) {
          message.error(`删除失败: ${e?.response?.data?.detail || e?.message}`);
        }
      },
    });
  };

  // ---- 打开详情 Drawer ----
  const openKbDetail = async (kb: any) => {
    try {
      const res = await knowledgeBaseApi.get(kb.id);
      const detail = res?.data?.data || kb;
      setActiveKb(detail);
      setDrawerOpen(true);
      setKbQuery('');
      setKbSearchResults([]);
      setUploadFileList([]);
    } catch (e: any) {
      message.error(`加载详情失败: ${e?.response?.data?.detail || e?.message}`);
    }
  };

  const refreshActiveKb = async () => {
    if (!activeKb) return;
    try {
      const res = await knowledgeBaseApi.get(activeKb.id);
      setActiveKb(res?.data?.data || activeKb);
    } catch {
      // 静默
    }
  };

  // ---- 上传文档 ----
  const handleUpload = async () => {
    if (!activeKb) return;
    if (uploadFileList.length === 0) {
      message.warning('请先选择文件');
      return;
    }
    setUploading(true);
    try {
      for (const f of uploadFileList) {
        const file = f.originFileObj as File;
        if (!file) continue;
        await knowledgeBaseApi.upload(activeKb.id, file);
      }
      message.success(`已上传 ${uploadFileList.length} 个文档`);
      setUploadFileList([]);
      refreshActiveKb();
      fetchKbList();
    } catch (e: any) {
      message.error(`上传失败: ${e?.response?.data?.detail || e?.message}`);
    } finally {
      setUploading(false);
    }
  };

  // ---- 删除文档 ----
  const handleDeleteDoc = async (doc: any) => {
    if (!activeKb) return;
    try {
      await knowledgeBaseApi.deleteDoc(activeKb.id, doc.id);
      message.success('文档已删除');
      refreshActiveKb();
      fetchKbList();
    } catch (e: any) {
      message.error(`删除失败: ${e?.response?.data?.detail || e?.message}`);
    }
  };

  // ---- 向量化 ----
  const handleVectorize = async () => {
    if (!activeKb) return;
    setVectorizing(true);
    try {
      const res = await knowledgeBaseApi.vectorize(activeKb.id);
      message.success(res?.data?.message || '向量化完成');
      refreshActiveKb();
      fetchKbList();
    } catch (e: any) {
      message.error(`向量化失败: ${e?.response?.data?.detail || e?.message}`);
    } finally {
      setVectorizing(false);
    }
  };

  // ---- KB 检索测试 ----
  const runKbSearch = async () => {
    if (!activeKb) return;
    if (!kbQuery.trim()) {
      message.warning('请输入查询文本');
      return;
    }
    setKbSearching(true);
    try {
      const res = await knowledgeBaseApi.search(activeKb.id, kbQuery, kbTopK);
      setKbSearchResults((res?.data?.data?.matches || []) as any[]);
    } catch (e: any) {
      message.error(`检索失败: ${e?.response?.data?.detail || e?.message}`);
    } finally {
      setKbSearching(false);
    }
  };

  // ---------- 渲染：默认库卡片 ----------
  const renderStatsCard = (meta: CollectionMeta) => {
    const s = stats[meta.key];
    const total = s?.count ?? s?.total ?? 0;
    const exists = s?.exists ?? false;
    const loading = loadingStats[meta.key];
    const busy = syncing === meta.key;
    return (
      <Card
        size="small"
        title={
          <Space>
            <DatabaseOutlined />
            <Text strong>{meta.label}</Text>
            <StatusTag preset="info">{meta.collectionName}</StatusTag>
          </Space>
        }
        extra={
          <Space size="small">
            <Button
              size="small"
              danger
              icon={<ThunderboltOutlined />}
              loading={busy}
              onClick={() => handleSync(meta.key, true)}
            >
              全量重建
            </Button>
            <Button
              size="small"
              icon={<SyncOutlined spin={busy} />}
              loading={busy}
              onClick={() => handleSync(meta.key, false)}
            >
              增量同步
            </Button>
          </Space>
        }
      >
        <Spin spinning={loading}>
          <Space size="large" wrap>
            <Statistic title="向量数" value={total} valueStyle={{ color: total > 0 ? 'var(--color-success)' : undefined }} />
            <Statistic
              title="库状态"
              valueRender={() => (exists ? <StatusTag preset="success">已建库</StatusTag> : <StatusTag preset="default">未建库</StatusTag>)}
            />
          </Space>
          <Progress percent={exists ? 100 : 0} status={exists ? 'success' : 'normal'} style={{ marginTop: 12 }} />
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
            {meta.description}
          </Text>
        </Spin>
      </Card>
    );
  };

  // ---------- 渲染：查询测试列 ----------
  const queryColumns =
    queryCollection === 'entity'
      ? [
          { title: '实体名', key: 'name', width: 180, render: (_: any, r: any) => r.name || r.entity_name },
          { title: '编码', dataIndex: 'code', width: 180, render: (v: string) => v || '-' },
          { title: '层级', dataIndex: 'level', width: 80, render: (v: string) => (v ? <Tag>{v}</Tag> : '-') },
          { title: '链类型', dataIndex: 'chain_type', width: 90, render: (v: string) => (v ? <StatusTag preset="info">{v}</StatusTag> : '-') },
          { title: '主表', dataIndex: 'is_main_table', width: 70, render: (v: boolean) => (v ? <StatusTag preset="success">是</StatusTag> : '-') },
          { title: '相似度', dataIndex: 'score', width: 110, render: (v: number) => <StatusTag preset="ai">{(v || 0).toFixed(4)}</StatusTag> },
        ]
      : [
          { title: '属性名', dataIndex: 'attribute_name', width: 160 },
          { title: '属性编码', dataIndex: 'attribute_code', width: 160, render: (v: string) => v || '-' },
          { title: '所属实体', dataIndex: 'entity_name', width: 160 },
          { title: '实体编码', dataIndex: 'entity_code', width: 160, render: (v: string) => v || '-' },
          { title: '数据类型', dataIndex: 'data_type', width: 100, render: (v: string) => (v ? <Tag>{v}</Tag> : '-') },
          { title: '相似度', dataIndex: 'score', width: 110, render: (v: number) => <StatusTag preset="ai">{(v || 0).toFixed(4)}</StatusTag> },
        ];

  // ---------- 渲染：KB 卡片 ----------
  const renderKbCard = (kb: any) => {
    const preset = KB_STATUS_PRESET[kb.status] || 'default';
    return (
      <Card
        size="small"
        title={
          <Space>
            <FileTextOutlined />
            <Text strong>{kb.name}</Text>
            <StatusTag preset={preset as any}>{kb.status}</StatusTag>
          </Space>
        }
        extra={
          <Space size="small">
            <Button size="small" type="link" onClick={() => openKbDetail(kb)}>详情</Button>
            <Button size="small" type="link" danger icon={<DeleteOutlined />} onClick={() => handleDeleteKb(kb)} />
          </Space>
        }
      >
        <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8, minHeight: 20 }}>
          {kb.description || '（无描述）'}
        </Paragraph>
        <Space size="large" wrap>
          <Statistic title="文档数" value={kb.doc_count || 0} />
          <Statistic title="向量数" value={kb.vector_count || 0} valueStyle={{ color: (kb.vector_count || 0) > 0 ? 'var(--color-success)' : undefined }} />
        </Space>
        {kb.error_msg && (
          <Text type="danger" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
            {kb.error_msg}
          </Text>
        )}
      </Card>
    );
  };

  return (
    <Spin spinning={false}>
      <Space direction="vertical" style={{ width: '100%' }} size={12}>
        {/* 页头：标题（带 Tooltip）+ 模型选择器 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <Tooltip title="包括实体库和属性库，用于技能模糊检索需要">
            <Space>
              <DatabaseOutlined style={{ fontSize: 18 }} />
              <Text strong style={{ fontSize: 16 }}>向量管理</Text>
            </Space>
          </Tooltip>
          <Space>
            <Text type="secondary" style={{ fontSize: 12 }}>向量模型：</Text>
            <Select
              size="small"
              style={{ width: 200 }}
              loading={modelLoading}
              value={currentModel || undefined}
              onChange={handleModelChange}
              options={modelOptions}
              placeholder="选择模型"
              showSearch
              optionFilterProp="label"
            />
            <Button size="small" icon={<ReloadOutlined />} onClick={() => { fetchAllStats(); fetchModelInfo(); fetchKbList(); }}>刷新</Button>
          </Space>
        </div>

        {/* 默认双库 */}
        <Row gutter={[12, 12]}>
          {COLLECTIONS.map((meta) => (
            <Col xs={24} md={12} key={meta.key}>
              {renderStatsCard(meta)}
            </Col>
          ))}
        </Row>

        {/* 自定义知识库 */}
        <Card
          size="small"
          title={
            <Space>
              <FileTextOutlined />
              <Text strong>自定义知识库</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>（上传文档 → 向量化 → 检索增强）</Text>
            </Space>
          }
          extra={
            <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
              新建知识库
            </Button>
          }
        >
          <Spin spinning={kbLoading}>
            {kbList.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-tertiary)' }}>
                暂无自定义知识库，点击右上角「新建知识库」创建
              </div>
            ) : (
              <Row gutter={[12, 12]}>
                {kbList.map((kb) => (
                  <Col xs={24} sm={12} lg={8} key={kb.id}>
                    {renderKbCard(kb)}
                  </Col>
                ))}
              </Row>
            )}
          </Spin>
        </Card>

        {/* 默认库向量查询测试 */}
        <Card
          size="small"
          title={
            <Space>
              <SearchOutlined />
              <Text strong>向量查询测试</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>（默认库：下拉选择库，分开查询）</Text>
            </Space>
          }
        >
          <Space wrap style={{ marginBottom: 12 }}>
            <Select<CollectionKey>
              style={{ width: 180 }}
              value={queryCollection}
              onChange={setQueryCollection}
              options={COLLECTIONS.map((c) => ({ value: c.key, label: `${c.label} (${c.collectionName})` }))}
            />
            <Input
              style={{ width: 380 }}
              placeholder={queryCollection === 'entity' ? '输入实体名/编码，如 用电客户' : '输入属性名，如 联系电话'}
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onPressEnter={runQuery}
            />
            <Input style={{ width: 90 }} placeholder="TopK" value={String(queryTopK)} onChange={(e) => setQueryTopK(Number(e.target.value || 10))} />
            <Button type="primary" icon={<SearchOutlined />} loading={queryLoading} onClick={runQuery}>查询</Button>
            <Button onClick={() => { setQueryResults([]); setQueryText(''); }}>清空</Button>
          </Space>
          <Table
            size="small"
            rowKey={(r: any) => `${r.code || r.attribute_code || ''}-${r.score || 0}`}
            dataSource={queryResults}
            pagination={{ pageSize: 8 }}
            columns={queryColumns as any}
          />
        </Card>
      </Space>

      {/* 新建知识库 Modal */}
      <Modal
        title="新建知识库"
        open={createModalOpen}
        onOk={handleCreateKb}
        onCancel={() => setCreateModalOpen(false)}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入知识库名称' }]}>
            <Input placeholder="如：配网运维规程" maxLength={100} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="可选，知识库用途说明" rows={3} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 知识库详情 Drawer */}
      <Drawer
        title={activeKb ? `知识库：${activeKb.name}` : '知识库详情'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={680}
        destroyOnClose
      >
        {activeKb && (
          <Spin spinning={vectorizing || uploading} tip={vectorizing ? '向量化中...' : '上传中...'}>
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              {/* 基本信息 */}
              <Card size="small" title="基本信息">
                <Descriptions2 activeKb={activeKb} />
                <Space style={{ marginTop: 8 }}>
                  <Button type="primary" icon={<ThunderboltOutlined />} loading={vectorizing} onClick={handleVectorize}>
                    向量化全部文档
                  </Button>
                  <Text type="secondary" style={{ fontSize: 12 }}>（全量重建：会清空旧向量后重新生成）</Text>
                </Space>
              </Card>

              {/* 上传文档 */}
              <Card size="small" title="上传文档（支持 .txt / .md）">
                <Upload.Dragger
                  accept=".txt,.md,.markdown"
                  multiple
                  fileList={uploadFileList}
                  beforeUpload={(file) => {
                    const ext = (file.name.toLowerCase().match(/\.(\w+)$/) || [])[1];
                    if (!['txt', 'md', 'markdown'].includes(ext)) {
                      message.error(`${file.name} 不在支持范围（仅 .txt/.md）`);
                      return Upload.LIST_IGNORE;
                    }
                    return false; // 阻止自动上传，手动控制
                  }}
                  onChange={({ fileList }) => setUploadFileList(fileList)}
                  onRemove={(f) => setUploadFileList((list) => list.filter((x) => x.uid !== f.uid))}
                >
                  <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                  <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                  <p className="ant-upload-hint">支持 .txt / .md 文件，可多选</p>
                </Upload.Dragger>
                {uploadFileList.length > 0 && (
                  <Button type="primary" style={{ marginTop: 8 }} loading={uploading} onClick={handleUpload}>
                    上传 {uploadFileList.length} 个文件
                  </Button>
                )}
              </Card>

              {/* 文档列表 */}
              <Card size="small" title={`文档列表（${activeKb.documents?.length || 0}）`}>
                <List
                  size="small"
                  dataSource={activeKb.documents || []}
                  locale={{ emptyText: '暂无文档' }}
                  renderItem={(doc: any) => (
                    <List.Item
                      actions={[
                        <Button key="del" size="small" type="link" danger icon={<DeleteOutlined />} onClick={() => handleDeleteDoc(doc)} />,
                      ]}
                    >
                      <List.Item.Meta
                        title={<Text style={{ fontSize: 13 }}>{doc.filename}</Text>}
                        description={
                          <Space size="small" split={<Text type="secondary">·</Text>}>
                            <Text type="secondary" style={{ fontSize: 12 }}>{formatFileSize(doc.file_size)}</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>{doc.chunk_count || 0} 分块</Text>
                            <StatusTag preset={(DOC_STATUS_PRESET[doc.status] || 'default') as any}>{doc.status}</StatusTag>
                            {doc.error_msg && <Text type="danger" style={{ fontSize: 12 }}>{doc.error_msg}</Text>}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </Card>

              {/* 检索测试 */}
              <Card size="small" title="检索测试">
                <Space wrap style={{ marginBottom: 12 }}>
                  <Input
                    style={{ width: 380 }}
                    placeholder="输入查询文本，测试检索效果"
                    value={kbQuery}
                    onChange={(e) => setKbQuery(e.target.value)}
                    onPressEnter={runKbSearch}
                  />
                  <Input style={{ width: 80 }} placeholder="TopK" value={String(kbTopK)} onChange={(e) => setKbTopK(Number(e.target.value || 5))} />
                  <Button type="primary" icon={<SearchOutlined />} loading={kbSearching} onClick={runKbSearch}>检索</Button>
                  <Button onClick={() => { setKbSearchResults([]); setKbQuery(''); }}>清空</Button>
                </Space>
                <List
                  size="small"
                  dataSource={kbSearchResults}
                  locale={{ emptyText: '输入查询后点击检索查看结果' }}
                  renderItem={(item: any) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space size="small">
                            <StatusTag preset="ai">{(item.score || 0).toFixed(4)}</StatusTag>
                            <Text type="secondary" style={{ fontSize: 12 }}>{item.filename}</Text>
                          </Space>
                        }
                        description={<Text style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>{item.text}</Text>}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            </Space>
          </Spin>
        )}
      </Drawer>
    </Spin>
  );
};

// ---- 辅助：知识库基本信息描述 ----
const Descriptions2: React.FC<{ activeKb: any }> = ({ activeKb }) => (
  <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
    <div>
      <Text type="secondary" style={{ fontSize: 12 }}>文档数</Text>
      <div><Text strong>{activeKb.doc_count || 0}</Text></div>
    </div>
    <div>
      <Text type="secondary" style={{ fontSize: 12 }}>向量数</Text>
      <div><Text strong style={{ color: (activeKb.vector_count || 0) > 0 ? 'var(--color-success)' : undefined }}>{activeKb.vector_count || 0}</Text></div>
    </div>
    <div>
      <Text type="secondary" style={{ fontSize: 12 }}>状态</Text>
      <div><StatusTag preset={(KB_STATUS_PRESET[activeKb.status] || 'default') as any}>{activeKb.status}</StatusTag></div>
    </div>
    <div style={{ flexBasis: '100%' }}>
      <Text type="secondary" style={{ fontSize: 12 }}>描述</Text>
      <div><Text style={{ fontSize: 13 }}>{activeKb.description || '（无）'}</Text></div>
    </div>
  </div>
);

function formatFileSize(bytes: number): string {
  if (!bytes) return '0 B';
  const kb = bytes / 1024;
  if (kb < 1) return `${bytes} B`;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(2)} MB`;
}

export default VectorManagePanel;
