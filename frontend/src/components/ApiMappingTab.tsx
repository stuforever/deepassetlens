import React, { useEffect, useState } from 'react';
import { Tabs, Row, Col, Card, Button, List, Modal, Form, Input, Select, Table, Space, Tag, message, Popconfirm, Empty, Collapse } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ThunderboltOutlined, PlayCircleOutlined, ApiOutlined, DatabaseOutlined, MinusCircleOutlined, SearchOutlined } from '@ant-design/icons';
import { apiEndpointApi, entityApiMappingApi, entityApi } from '../services/api';
import { StatusTag } from './shell';

const { TextArea } = Input;
const TYPE_OPTIONS = ['VARCHAR', 'INTEGER', 'BIGINT', 'DOUBLE', 'BOOLEAN', 'DATE', 'TIMESTAMP'].map(t => ({ value: t }));

// ===================== 对象API映射 section（主） =====================
function EntityApiMappingSection({ entityId }: { entityId?: string }) {
  const [mappings, setMappings] = useState<any[]>([]);
  const [entities, setEntities] = useState<any[]>([]);
  const [endpoints, setEndpoints] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedMapId, setSelectedMapId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<any>({ name: '', entity_id: '', api_endpoint_ids: [], pseudo_sql: '', description: '' });
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);
  const [filterText, setFilterText] = useState('');

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [mRes, eRes, epRes] = await Promise.all([entityApiMappingApi.list(), entityApi.listEntities(), apiEndpointApi.list()]);
      setMappings(mRes.data?.data || []);
      setEntities(eRes.data?.data?.items || eRes.data?.data || []);
      setEndpoints(epRes.data?.data || []);
    } catch (e) { console.error('[ApiMappingTab] fetchAll error:', e); message.error('加载失败'); }
    setLoading(false);
  };
  useEffect(() => { fetchAll(); }, []);

  // 外部传入 entityId 时自动选中/新建
  useEffect(() => {
    if (!entityId || mappings.length === 0) return;
    const match = mappings.find(m => m.entity_id === entityId);
    if (match) {
      selectMapping(match);
    } else {
      // 该实体尚无 API 映射，预填 entity_id 进右侧表单
      setEditingId(null);
      setSelectedMapId(null);
      const ent = entities.find(e => e.id === entityId);
      setForm({ name: ent?.entity_name || '', entity_id: entityId, api_endpoint_ids: [], pseudo_sql: '', description: '' });
      setVerifyResult(null);
    }
  }, [entityId, mappings]); // eslint-disable-line

  const entityName = (id: string) => entities.find(e => e.id === id)?.entity_name || id;
  const entityCode = (id: string) => entities.find(e => e.id === id)?.entity_code || '';
  const entityOptions = entities.map(e => ({ label: `${e.entity_name} (${e.entity_code})`, value: e.id }));
  const endpointOptions = endpoints.map(ep => ({ label: `${ep.name} [${ep.table_name}]`, value: ep.id }));
  // 列表过滤：entityId 跳转过滤 + 搜索框过滤
  const filteredMappings = (entityId ? mappings.filter(m => m.entity_id === entityId) : mappings)
    .filter(m => !filterText.trim()
      || entityName(m.entity_id).toLowerCase().includes(filterText.toLowerCase())
      || entityCode(m.entity_id).toLowerCase().includes(filterText.toLowerCase()));

  const openCreate = () => {
    setEditingId(null);
    setSelectedMapId(null);
    setForm({ name: '', entity_id: '', api_endpoint_ids: [], pseudo_sql: '', description: '' });
    setVerifyResult(null);
  };
  const selectMapping = (m: any) => {
    setSelectedMapId(m.id);
    setEditingId(m.id);
    setForm({ name: m.name || '', entity_id: m.entity_id, api_endpoint_ids: m.api_endpoint_ids || [], pseudo_sql: m.pseudo_sql, description: m.description || '' });
    setVerifyResult(null);
  };

  const handleSave = async () => {
    if (!form.entity_id || !form.pseudo_sql) { message.warning('对象和伪逻辑SQL必填'); return; }
    const payload = { ...form, name: form.name || entityName(form.entity_id) };
    try {
      if (editingId) { await entityApiMappingApi.update(editingId, payload); message.success('已更新'); }
      else { const res = await entityApiMappingApi.create(payload); setEditingId(res.data?.data?.id); message.success('已新增，可点验证'); }
      fetchAll();
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败'); }
  };

  const handleVerify = async () => {
    if (!editingId) { message.warning('请先保存再验证'); return; }
    setVerifying(true);
    try {
      const res = await entityApiMappingApi.verify(editingId);
      const d = res.data?.data || {};
      if (d.error) { message.error('验证失败: ' + d.error); setVerifyResult(null); }
      else { setVerifyResult({ columns: d.columns, rows: d.rows, pushed_down: d.pushed_down }); message.success(`验证成功，返回 ${d.row_count} 行`); }
    } catch { message.error('验证失败'); }
    setVerifying(false);
  };

  const handleDelete = async (id: string) => {
    try { await entityApiMappingApi.delete(id); message.success('已删除'); fetchAll(); } catch { message.error('删除失败'); }
  };

  const resultColumns = verifyResult?.columns?.map((c: string) => ({ title: c, dataIndex: c, ellipsis: true })) || [];
  const resultData = verifyResult?.rows?.map((r: any[], i: number) => {
    const obj: any = { _key: i };
    (verifyResult.columns || []).forEach((c: string, j: number) => { obj[c] = r[j]; });
    return obj;
  }) || [];

  return (
    <div>
      <Row gutter={12}>
        <Col span={8}>
          <Card title={<Space><DatabaseOutlined />对象API映射</Space>} size="small"
            extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreate}>新增</Button>}
            bodyStyle={{ overflowY: 'auto', maxHeight: 'calc(100vh - 320px)' }}>
            <Input allowClear prefix={<SearchOutlined />} placeholder="按对象名称/编码搜索" value={filterText} onChange={e => setFilterText(e.target.value)} style={{ marginBottom: 8 }} />
            <List size="small" loading={loading} dataSource={filteredMappings} locale={{ emptyText: '暂无对象API映射，点新增配置' }}
              renderItem={(m: any) => (
                <List.Item style={{ cursor: 'pointer', background: m.id === selectedMapId ? 'var(--color-primary-bg)' : undefined, padding: '6px 8px' }}
                  actions={[
                    <Popconfirm title="确认删除?" onConfirm={() => handleDelete(m.id)}><Button size="small" type="link" danger icon={<DeleteOutlined />} /></Popconfirm>,
                  ]}
                  onClick={() => selectMapping(m)}>
                  <List.Item.Meta title={entityName(m.entity_id)} description={<Space size={4} wrap><StatusTag preset="info">{entityCode(m.entity_id)}</StatusTag><span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{(m.api_endpoint_ids || []).length}个端点</span></Space>} />
                </List.Item>
              )} />
          </Card>
        </Col>
        <Col span={16}>
          {/* 右上：映射配置（inline，不弹窗） */}
          <Card title={<Space><EditOutlined />映射配置{editingId ? <StatusTag preset="info">编辑中</StatusTag> : <StatusTag preset="success">新增</StatusTag>}</Space>} size="small"
            extra={<Space>
              <Button size="small" icon={<ThunderboltOutlined />} onClick={handleVerify} loading={verifying} disabled={!editingId}>验证SQL</Button>
              <Button size="small" type="primary" icon={<PlusOutlined />} onClick={handleSave}>保存</Button>
            </Space>}>
            <Form layout="vertical" size="small">
              <Row gutter={12}>
                <Col span={12}><Form.Item label="对象(主数据/业务活动)" required>
                  <Select showSearch optionFilterProp="label" options={entityOptions} value={form.entity_id || undefined} onChange={v => setForm({ ...form, entity_id: v })} placeholder="选择对象" />
                </Form.Item></Col>
                <Col span={12}><Form.Item label="名称(可空，默认用对象名)">
                  <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="留空自动用对象名" />
                </Form.Item></Col>
              </Row>
              <Form.Item label="API端点(虚拟表，可多选)" required tooltip="选择要整合的API端点，伪逻辑SQL里用其 table_name">
                <Select mode="multiple" options={endpointOptions} value={form.api_endpoint_ids} onChange={v => setForm({ ...form, api_endpoint_ids: v })} placeholder="选择API端点" />
              </Form.Item>
              <Form.Item label="描述"><Input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></Form.Item>
            </Form>
          </Card>
          {/* 右下：伪逻辑SQL + 验证结果 */}
          <Card title={<Space><EditOutlined />伪逻辑SQL与验证结果</Space>} size="small" style={{ marginTop: 8 }}>
            <div style={{ marginBottom: 4, fontSize: 12, color: 'var(--text-tertiary)' }}>引用虚拟表名，不含 WHERE（LLM 调用时动态加 WHERE 下推）</div>
            <TextArea rows={6} value={form.pseudo_sql} onChange={e => setForm({ ...form, pseudo_sql: e.target.value })} style={{ fontFamily: 'monospace', fontSize: 13 }}
              placeholder="SELECT d.budget_id, d.wbs_element, a.total_budget FROM dim_ps_wbs_budget_dim d JOIN dim_ps_wbs_budget_amt a ON d.budget_id=a.budget_id" />
            {verifyResult ? (
              <div style={{ marginTop: 8 }}>
                {verifyResult.pushed_down && <div style={{ fontSize: 12, color: 'var(--color-success)', marginBottom: 4 }}>下推参数: {JSON.stringify(verifyResult.pushed_down)}</div>}
                <Table columns={resultColumns} dataSource={resultData} rowKey="_key" size="small" pagination={{ pageSize: 10 }} />
              </div>
            ) : <Empty style={{ marginTop: 12 }} description={editingId ? '点上方「验证SQL」查看执行结果' : '保存后可验证执行'} />}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

// ===================== API端点管理 section（辅，底层虚拟表配置） =====================
function ApiEndpointSection() {
  const [endpoints, setEndpoints] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<any>({ name: '', table_name: '', api_url: '', method: 'POST', data_path: '', headers: '', description: '' });
  const [paramsArr, setParamsArr] = useState<any[]>([{ name: 'pspid', column: 'pspid', map_to: 'query' }]);
  const [columnsArr, setColumnsArr] = useState<any[]>([{ name: 'pspid', json_path: 'pspid', type: 'VARCHAR' }]);
  const [selectedEpId, setSelectedEpId] = useState<string | null>(null);
  const [sql, setSql] = useState('');
  const [result, setResult] = useState<any>(null);
  const [execLoading, setExecLoading] = useState(false);

  const fetchEndpoints = async () => {
    setLoading(true);
    try { const res = await apiEndpointApi.list(); setEndpoints(res.data?.data || []); } catch { message.error('加载端点失败'); }
    setLoading(false);
  };
  useEffect(() => { fetchEndpoints(); }, []);

  // 按 table_name 前缀派生分类（无 system 字段，靠前缀分组）
  const categoryOf = (ep: any) => {
    const t = ep.table_name || '';
    if (t.startsWith('dim_ps_')) return 'ES 主数据源';
    return '其他';
  };
  // 分类分组（保持插入顺序）
  const grouped = endpoints.reduce((acc: { name: string; items: any[] }[], ep) => {
    const cat = categoryOf(ep);
    let g = acc.find(x => x.name === cat);
    if (!g) { g = { name: cat, items: [] }; acc.push(g); }
    g.items.push(ep);
    return acc;
  }, []);

  // 选中端点 -> 用其 columns + table_name 生成 SELECT，填入 SQL 模拟区
  const selectEndpoint = (ep: any) => {
    setSelectedEpId(ep.id);
    const cols = (ep.columns || []).map((c: any) => c.name).filter(Boolean);
    const select = cols.length ? cols.join(', ') : '*';
    setSql(`SELECT ${select} FROM ${ep.table_name}`);
    setResult(null);
  };
  const genSqlForId = (id: string) => {
    const ep = endpoints.find(e => e.id === id);
    if (ep) selectEndpoint(ep);
  };

  const openCreate = () => {
    setEditingId(null);
    setForm({ name: '', table_name: '', api_url: '', method: 'POST', data_path: '', headers: '', description: '' });
    setParamsArr([{ name: 'pspid', column: 'pspid', map_to: 'query' }]);
    setColumnsArr([{ name: 'pspid', json_path: 'pspid', type: 'VARCHAR' }]);
    setModalOpen(true);
  };
  const openEdit = (ep: any) => {
    setEditingId(ep.id);
    setForm({ name: ep.name || '', table_name: ep.table_name || '', api_url: ep.api_url || '', method: ep.method || 'POST', data_path: ep.data_path || '', headers: ep.headers ? JSON.stringify(ep.headers) : '', description: ep.description || '' });
    setParamsArr(ep.params?.length ? ep.params : []);
    setColumnsArr(ep.columns?.length ? ep.columns : []);
    setModalOpen(true);
  };
  const updParam = (i: number, k: string, v: string) => setParamsArr(arr => arr.map((x, idx) => idx === i ? { ...x, [k]: v } : x));
  const updCol = (i: number, k: string, v: string) => setColumnsArr(arr => arr.map((x, idx) => idx === i ? { ...x, [k]: v } : x));

  const handleSave = async () => {
    if (!form.name || !form.table_name || !form.api_url) { message.warning('名称/表名/URL必填'); return; }
    if (!columnsArr.length) { message.warning('至少配一个返回列'); return; }
    let headersObj: any = null;
    if (form.headers) { try { headersObj = JSON.parse(form.headers); } catch { message.error('headers JSON 格式错误'); return; } }
    const payload = { name: form.name, table_name: form.table_name, api_url: form.api_url, method: form.method, params: paramsArr.filter(p => p.name && p.column), columns: columnsArr.filter(c => c.name), data_path: form.data_path || null, headers: headersObj, description: form.description || null };
    try {
      if (editingId) { await apiEndpointApi.update(editingId, payload); message.success('已更新'); }
      else { await apiEndpointApi.create(payload); message.success('已新增'); }
      setModalOpen(false); fetchEndpoints();
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败'); }
  };
  const handleDelete = async (id: string) => { try { await apiEndpointApi.delete(id); message.success('已删除'); fetchEndpoints(); if (selectedEpId === id) { setSelectedEpId(null); setSql(''); setResult(null); } } catch { message.error('删除失败'); } };
  const handleTest = async (id: string) => {
    // 测试 = 选中该端点并生成 SQL + 执行，一步到位
    genSqlForId(id);
    setSelectedEpId(id);
    try { const res = await apiEndpointApi.test(id); const d = res.data?.data || {}; if (d.error) { message.error('测试失败: ' + d.error); return; } message.success(`测试成功，返回 ${d.row_count} 行`); setResult({ columns: d.columns, rows: d.rows }); } catch { message.error('测试失败'); }
  };
  const handleExecute = async () => {
    if (!sql.trim()) { message.warning('SQL不能为空'); return; }
    setExecLoading(true);
    try { const res = await apiEndpointApi.execute(sql); const d = res.data?.data || {}; if (d.error) { message.error('执行失败: ' + d.error); setResult(null); } else { setResult({ columns: d.columns, rows: d.rows, pushed_down: d.pushed_down }); message.success(`返回 ${d.row_count} 行`); } } catch (e: any) { message.error(e?.response?.data?.detail || '执行失败'); }
    setExecLoading(false);
  };

  const resultColumns = result?.columns?.map((c: string) => ({ title: c, dataIndex: c, ellipsis: true })) || [];
  const resultData = result?.rows?.map((r: any[], i: number) => { const obj: any = { _key: i }; (result.columns || []).forEach((c: string, j: number) => { obj[c] = r[j]; }); return obj; }) || [];

  return (
    <div>
      <Row gutter={12}>
        <Col span={8}>
          <Card title={<Space><ApiOutlined />远程调用API</Space>} size="small"
            extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreate}>新增</Button>}
            bodyStyle={{ overflowY: 'auto', maxHeight: 'calc(100vh - 320px)' }}>
            {grouped.length === 0 ? <Empty description="暂无端点" /> : (
              <Collapse size="small" defaultActiveKey={grouped.length ? [grouped[0].name] : []} items={grouped.map(g => ({
                key: g.name,
                label: <Space><span>{g.name}</span><Tag>{g.items.length}</Tag></Space>,
                children: (
                  <List size="small" dataSource={g.items} split={false} renderItem={(ep: any) => (
                    <List.Item style={{ cursor: 'pointer', background: ep.id === selectedEpId ? 'var(--color-primary-bg)' : undefined, padding: '6px 8px', border: 'none' }}
                      actions={[
                        <Button size="small" type="link" icon={<ThunderboltOutlined />} onClick={(e) => { e.stopPropagation(); handleTest(ep.id); }}>测</Button>,
                        <Button size="small" type="link" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); openEdit(ep); }} />,
                        <Popconfirm title="确认删除?" onConfirm={(e) => { e?.stopPropagation(); handleDelete(ep.id); }}><Button size="small" type="link" danger icon={<DeleteOutlined />} onClick={e => e.stopPropagation()} /></Popconfirm>,
                      ]}
                      onClick={() => selectEndpoint(ep)}>
                      <List.Item.Meta title={ep.name} description={<Space size={4}><StatusTag preset="info">{ep.table_name}</StatusTag><Tag>{ep.method}</Tag></Space>} />
                    </List.Item>
                  )} />
                ),
              }))} />
            )}
          </Card>
        </Col>
        <Col span={16}>
          <Card title={<Space><PlayCircleOutlined />SQL 模拟{selectedEpId && <StatusTag preset="success">已选端点</StatusTag>}</Space>} size="small"
            extra={<Button type="primary" size="small" icon={<PlayCircleOutlined />} onClick={handleExecute} loading={execLoading} disabled={!sql.trim()}>执行</Button>}>
            {selectedEpId ? (
              <div style={{ marginBottom: 6, fontSize: 12, color: 'var(--text-tertiary)' }}>
                选中端点已自动生成 SELECT（基于其返回列 + 虚拟表名），可直接执行或手动编辑后执行；WHERE/JOIN 参数会自动下推。
              </div>
            ) : (
              <div style={{ marginBottom: 6, fontSize: 12, color: 'var(--color-warning)' }}>← 左侧选择一个端点，自动生成该端点的查询 SQL</div>
            )}
            <TextArea rows={6} value={sql} onChange={e => setSql(e.target.value)} style={{ fontFamily: 'monospace', fontSize: 13 }}
              placeholder="选择左侧端点后自动生成 SQL，或在此手写联邦查询 SQL" />
          </Card>
          {result?.pushed_down && <div style={{ marginTop: 4, fontSize: 12, color: 'var(--color-success)' }}>下推参数: {JSON.stringify(result.pushed_down)}</div>}
          <Card title="执行结果" size="small" style={{ marginTop: 8 }} bodyStyle={{ overflowY: 'auto', maxHeight: '260px' }}>
            {result?.columns?.length ? <Table columns={resultColumns} dataSource={resultData} rowKey="_key" size="small" pagination={{ pageSize: 10 }} /> : <Empty description="执行SQL后显示结果" />}
          </Card>
        </Col>
      </Row>

      <Modal open={modalOpen} title={editingId ? '编辑API端点' : '新增API端点'} onOk={handleSave} onCancel={() => setModalOpen(false)} width={780} destroyOnHidden>
        <Form layout="vertical">
          <Row gutter={12}>
            <Col span={12}><Form.Item label="中文名" required><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Form.Item></Col>
            <Col span={12}><Form.Item label="虚拟表名(DuckDB用,英文唯一)" required><Input value={form.table_name} onChange={e => setForm({ ...form, table_name: e.target.value })} placeholder="dim_ps_xxx" /></Form.Item></Col>
          </Row>
          <Form.Item label="API URL" required><Input value={form.api_url} onChange={e => setForm({ ...form, api_url: e.target.value })} placeholder="http://localhost:1200/tupu_dim_ps_xxx/_search" /></Form.Item>
          <Row gutter={12}>
            <Col span={6}><Form.Item label="方法"><Select value={form.method} onChange={v => setForm({ ...form, method: v })} options={[{ value: 'GET' }, { value: 'POST' }]} /></Form.Item></Col>
            <Col span={18}><Form.Item label="响应数据路径(如 data.TABLES.PROJECT_DEFINITION)"><Input value={form.data_path} onChange={e => setForm({ ...form, data_path: e.target.value })} /></Form.Item></Col>
          </Row>
          <Form.Item label="过滤参数 params" tooltip='column匹配SQL列(含JOIN条件列),name是API请求参数名'>
            <div style={{ marginBottom: 4, fontSize: 12, color: 'var(--text-tertiary)' }}><Row gutter={4}><Col span={7}>API参数名(name)</Col><Col span={7}>SQL列名(column)</Col><Col span={6}>map_to</Col><Col span={4}></Col></Row></div>
            {paramsArr.map((p, i) => (
              <Row key={i} gutter={4} style={{ marginBottom: 4 }}>
                <Col span={7}><Input size="small" placeholder="pspid" value={p.name} onChange={e => updParam(i, 'name', e.target.value)} /></Col>
                <Col span={7}><Input size="small" placeholder="pspid" value={p.column} onChange={e => updParam(i, 'column', e.target.value)} /></Col>
                <Col span={6}><Input size="small" placeholder="query" value={p.map_to} onChange={e => updParam(i, 'map_to', e.target.value)} /></Col>
                <Col span={4}><Button size="small" danger icon={<MinusCircleOutlined />} onClick={() => setParamsArr(arr => arr.filter((_, idx) => idx !== i))} /></Col>
              </Row>
            ))}
            <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => setParamsArr([...paramsArr, { name: '', column: '', map_to: 'query' }])}>加参数</Button>
          </Form.Item>
          <Form.Item label="返回列 columns" tooltip='name是SQL列名,json_path是API响应JSON字段,type是DuckDB类型'>
            <div style={{ marginBottom: 4, fontSize: 12, color: 'var(--text-tertiary)' }}><Row gutter={4}><Col span={6}>列名(name)</Col><Col span={9}>JSON字段(json_path)</Col><Col span={6}>类型(type)</Col><Col span={3}></Col></Row></div>
            {columnsArr.map((c, i) => (
              <Row key={i} gutter={4} style={{ marginBottom: 4 }}>
                <Col span={6}><Input size="small" placeholder="pspid" value={c.name} onChange={e => updCol(i, 'name', e.target.value)} /></Col>
                <Col span={9}><Input size="small" placeholder="pspid" value={c.json_path} onChange={e => updCol(i, 'json_path', e.target.value)} /></Col>
                <Col span={6}><Select size="small" value={c.type} onChange={v => updCol(i, 'type', v)} options={TYPE_OPTIONS} showSearch /></Col>
                <Col span={3}><Button size="small" danger icon={<MinusCircleOutlined />} onClick={() => setColumnsArr(arr => arr.filter((_, idx) => idx !== i))} /></Col>
              </Row>
            ))}
            <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => setColumnsArr([...columnsArr, { name: '', json_path: '', type: 'VARCHAR' }])}>加列</Button>
          </Form.Item>
          <Form.Item label="请求头 headers (JSON,可选)"><TextArea rows={2} value={form.headers} onChange={e => setForm({ ...form, headers: e.target.value })} style={{ fontFamily: 'monospace', fontSize: 12 }} placeholder='{"Authorization":"Bearer xxx"}' /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default function ApiMappingTab({ entityId }: { entityId?: string }) {
  return (
    <div style={{ height: 'calc(100vh - 200px)', overflowY: 'auto', padding: '12px 16px 32px' }}>
      <Tabs defaultActiveKey="entity" size="small" items={[
        { key: 'entity', label: <Space><DatabaseOutlined />对象API映射</Space>, children: <EntityApiMappingSection entityId={entityId} /> },
        { key: 'endpoint', label: <Space><ApiOutlined />远程调用API</Space>, children: <ApiEndpointSection /> },
      ]} />
    </div>
  );
}
