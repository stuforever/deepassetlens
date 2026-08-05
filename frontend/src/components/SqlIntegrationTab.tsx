import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Button, List, Table, Space, Select, message, Empty, Modal, Alert, Input } from 'antd';
import { DatabaseOutlined, ThunderboltOutlined, SaveOutlined, ArrowLeftOutlined, ExperimentOutlined, SearchOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import { entityApi, integrationSqlApi, llmAdminApi } from '../services/api';
import { StatusTag } from './shell';

/**
 * 虚拟SQL映射 Tab（sql_integration 模式，Doris 引擎）
 * 浏览模式：左 对象列表 + 右 Catalog下拉 + Monaco SQL编辑器 + 验证结果
 * 跳转模式（entityId 传入）：全宽只显示该对象 SQL 编辑器，无需左选；可点「查看全部对象」切回浏览
 */
export default function SqlIntegrationTab({ entityId }: { entityId?: string }) {
  const [entities, setEntities] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [integrationSql, setIntegrationSql] = useState('');
  const [dorisCatalog, setDorisCatalog] = useState('');
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);
  const [saving, setSaving] = useState(false);
  // AI 校验改写
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<any>(null);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  // LLM 模型连接（AI 校验改写用，自动选默认连接）
  const [selectedConnId, setSelectedConnId] = useState<string | undefined>(undefined);
  // 跳转模式下用户可手动切回「查看全部对象」
  const [browseAll, setBrowseAll] = useState(false);
  // 对象列表搜索
  const [filterText, setFilterText] = useState('');

  const fetchEntities = async () => {
    try {
      const res = await entityApi.listEntities();
      const all = res.data?.data?.items || res.data?.data || [];
      // 只列勾选了虚拟Doris映射(sql_integration)的对象，不把100+无关对象都列出来
      setEntities(all.filter((e: any) => e.source_mode === 'sql_integration'));
    } catch { message.error('加载对象失败'); }
  };

  const fetchDefaultConn = async () => {
    try {
      const res = await llmAdminApi.getConnections();
      const all = res.data?.data || [];
      const chat = all.filter((c: any) => c.enabled && c.capability === 'chat');
      // 默认选中 is_default 的那条（无则第一条）
      const def = chat.find((c: any) => c.is_default) || chat[0];
      setSelectedConnId(def?.id);
    } catch { /* LLM 配置未就绪时静默 */ }
  };

  useEffect(() => { fetchEntities(); fetchDefaultConn(); }, []);

  // 跳转模式：entityId 变化时重置 browseAll 并自动选中
  useEffect(() => {
    if (entityId) setBrowseAll(false);
  }, [entityId]);

  useEffect(() => {
    if (entityId && entities.length > 0) {
      const ent = entities.find(e => e.id === entityId);
      if (ent && ent.id !== selectedId) selectEntity(ent);
    }
  }, [entityId, entities]); // eslint-disable-line

  const selected = entities.find(e => e.id === selectedId);
  const jumpMode = !!entityId && !browseAll;
  // 列表按搜索框过滤
  const filteredEntities = filterText.trim()
    ? entities.filter(e => (e.entity_name || '').toLowerCase().includes(filterText.toLowerCase()) || (e.entity_code || '').toLowerCase().includes(filterText.toLowerCase()))
    : entities;

  const selectEntity = (e: any) => {
    setSelectedId(e.id);
    setIntegrationSql(e.integration_sql || '');
    setDorisCatalog(e.doris_catalog || '');
    setVerifyResult(null);
  };

  const handleSave = async () => {
    if (!selectedId) return;
    setSaving(true);
    try {
      await entityApi.updateEntity(selectedId, { integration_sql: integrationSql, doris_catalog: dorisCatalog });
      message.success('已保存');
      setEntities(arr => arr.map(e => e.id === selectedId ? { ...e, integration_sql: integrationSql, doris_catalog: dorisCatalog } : e));
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败'); }
    setSaving(false);
  };

  const handleVerify = async () => {
    if (!integrationSql.trim()) { message.warning('请先填 integration_sql'); return; }
    setVerifying(true);
    try {
      const res = await integrationSqlApi.verify(integrationSql, dorisCatalog || undefined);
      const d = res.data?.data || {};
      if (d.error) { message.error('验证失败: ' + d.error); setVerifyResult(null); }
      else { setVerifyResult({ columns: d.columns, rows: d.rows }); message.success(`验证成功，返回 ${d.row_count} 行`); }
    } catch (e: any) { message.error(e?.response?.data?.detail || '验证失败'); }
    setVerifying(false);
  };

  const handleAiRewrite = async () => {
    if (!selectedId) { message.warning('请先选择对象'); return; }
    if (!integrationSql.trim()) { message.warning('请先填 integration_sql'); return; }
    setAiLoading(true);
    try {
      const res = await integrationSqlApi.aiRewrite(integrationSql, selectedId, dorisCatalog || undefined, selectedConnId);
      const d = res.data?.data || {};
      setAiResult(d);
      setAiModalOpen(true);
      if (d.error) message.error(d.error);
      else if (d.matched) message.success('字段完全匹配');
      else message.warning('存在不匹配，已生成改写 SQL');
    } catch (e: any) { message.error(e?.response?.data?.detail || 'AI 校验失败'); }
    setAiLoading(false);
  };

  const resultColumns = verifyResult?.columns?.map((c: string) => ({ title: c, dataIndex: c, ellipsis: true })) || [];
  const resultData = verifyResult?.rows?.map((r: any[], i: number) => {
    const obj: any = { _key: i };
    (verifyResult.columns || []).forEach((c: string, j: number) => { obj[c] = r[j]; });
    return obj;
  }) || [];

  // 编辑器区块（浏览模式与跳转模式共用）
  // 外层限高+内部滚动：右侧编辑器(300px)+验证结果(300px)累加会远超视口，
  // 不限高会撑高整页超出屏幕。左侧对象列表已有 maxHeight，这里对称限制右侧。
  const editorSection = selected ? (
    <div style={{ maxHeight: 'calc(100vh - 240px)', overflowY: 'auto', paddingRight: 4 }}>
      <Card title={<Space>integration_sql 编辑器<StatusTag preset="success">Doris 引擎</StatusTag></Space>} size="small"
        extra={<Space>
          <Button size="small" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>保存</Button>
          <Button size="small" type="primary" icon={<ThunderboltOutlined />} onClick={handleVerify} loading={verifying}>验证执行</Button>
          <Button size="small" icon={<ExperimentOutlined />} onClick={handleAiRewrite} loading={aiLoading}>AI 校验改写</Button>
        </Space>}>
        <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>对象: {selected.entity_name} ({selected.entity_code}) | source_mode: {selected.source_mode}</span>
        </div>
        <Editor
          height="200px"
          language="sql"
          theme="vs"
          value={integrationSql}
          onChange={(v) => setIntegrationSql(v || '')}
          onMount={(editor) => {
            // Antd Tabs 中容器初始尺寸可能未就绪，Monaco 会塌缩成 5x5 不可见；
            // automaticLayout 不一定能在 mount 时校正，这里强制 layout 一次。
            editor.layout();
            setTimeout(() => editor.layout(), 120);
          }}
          options={{ minimap: { enabled: false }, wordWrap: 'on', fontSize: 13, scrollBeyondLastLine: false, automaticLayout: true }}
        />
        <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-tertiary)' }}>
          提示: SQL 用 3 段命名（catalog.db.table）。不含 WHERE，LLM 调用时动态加 filters 下推。
        </div>
      </Card>
      <Card title="验证结果" size="small" style={{ marginTop: 4 }}>
        {verifyResult?.columns?.length ? <Table columns={resultColumns} dataSource={resultData} rowKey="_key" size="small" pagination={{ pageSize: 5, showSizeChanger: false }} /> : <Empty description="填 integration_sql 后点验证" />}
      </Card>
    </div>
  ) : <Empty description="左侧选择对象配置 integration_sql" style={{ marginTop: 80 }} />;

  return (
    <div style={{ padding: 12 }}>
      {jumpMode ? (
        <div>
          <div style={{ marginBottom: 8 }}>
            <Space>
              <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => { setBrowseAll(true); setSelectedId(null); setVerifyResult(null); }}>查看全部对象</Button>
              <StatusTag preset="info">当前对象: {selected?.entity_name} ({selected?.entity_code})</StatusTag>
              <StatusTag preset={selected?.source_mode === 'sql_integration' ? 'success' : 'default'}>{selected?.source_mode}</StatusTag>
            </Space>
          </div>
          {editorSection}
        </div>
      ) : (
        <Row gutter={12}>
          <Col span={8}>
            <Card title={<Space><DatabaseOutlined />对象列表<StatusTag preset="success">sql_integration</StatusTag></Space>} size="small" bodyStyle={{ overflowY: 'auto', maxHeight: 'calc(100vh - 240px)' }}>
              <Input allowClear prefix={<SearchOutlined />} placeholder="按名称/编码搜索" value={filterText} onChange={e => setFilterText(e.target.value)} style={{ marginBottom: 8 }} />
              <List size="small" dataSource={filteredEntities} locale={{ emptyText: filteredEntities.length ? '无匹配对象' : '无 sql_integration 对象' }}
                renderItem={(e: any) => (
                  <List.Item onClick={() => selectEntity(e)} style={{ cursor: 'pointer', background: e.id === selectedId ? 'var(--color-primary-bg)' : undefined }}>
                    <List.Item.Meta title={e.entity_name} description={<Space size={4}>
                      <StatusTag preset={e.source_mode === 'sql_integration' ? 'success' : 'default'}>{e.source_mode}</StatusTag>
                      <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{e.entity_code}</span>
                    </Space>} />
                  </List.Item>
                )} />
            </Card>
          </Col>
          <Col span={16}>
            {editorSection}
          </Col>
        </Row>
      )}
      <Modal
        title="AI 字段校验与改写"
        open={aiModalOpen}
        width={900}
        onCancel={() => setAiModalOpen(false)}
        footer={[
          <Button key="cancel" onClick={() => setAiModalOpen(false)}>放弃</Button>,
          <Button key="apply" type="primary" disabled={!aiResult?.rewritten_sql || aiResult?.matched || aiResult?.error}
            onClick={() => { if (aiResult?.rewritten_sql) { setIntegrationSql(aiResult.rewritten_sql); setAiModalOpen(false); message.success('已应用改写后的 SQL'); } }}>
            应用改写
          </Button>,
        ]}
      >
        {aiResult?.error ? (
          <Alert type="error" message={aiResult.error} showIcon />
        ) : aiResult?.matched ? (
          <Alert type="success" message="字段完全匹配，无需改写" showIcon />
        ) : (
          <Alert type="warning" message="存在不匹配，已生成改写 SQL（见下方预览）" showIcon />
        )}
        {aiResult?.model && (
          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-tertiary)' }}>
            使用模型: {aiResult.model.name} ({aiResult.model.model_name})
          </div>
        )}
        {aiResult?.differences?.length > 0 && (
          <Card title="差异明细" size="small" style={{ marginTop: 12 }}>
            {aiResult.differences.map((d: any, i: number) => (
              <div key={i} style={{ marginBottom: 4 }}>
                <StatusTag preset="warning">{d.issue}</StatusTag>
                <b>{d.field}</b>: {d.detail}
              </div>
            ))}
          </Card>
        )}
        {aiResult?.entity_fields && aiResult?.sql_columns && (
          <Card title="字段对照（实体 ↔ SQL 输出）" size="small" style={{ marginTop: 12 }}>
            <Table size="small" pagination={false} rowKey="name" dataSource={
              aiResult.entity_fields.map((ef: any) => {
                const sc = aiResult.sql_columns.find((c: any) => c.name === ef.name);
                return { name: ef.name, entity_type: ef.type || '-', sql_name: sc?.name || '(缺失)', sql_type: sc?.type || '(缺失)', match: !!sc };
              })
            } columns={[
              { title: '实体字段', dataIndex: 'name' },
              { title: '实体类型', dataIndex: 'entity_type' },
              { title: 'SQL列名', dataIndex: 'sql_name' },
              { title: 'SQL类型', dataIndex: 'sql_type' },
              { title: '匹配', dataIndex: 'match', render: (v: boolean) => v ? <StatusTag preset="success">是</StatusTag> : <StatusTag preset="error">否</StatusTag> },
            ]} />
          </Card>
        )}
        {aiResult?.rewritten_sql && !aiResult?.matched && !aiResult?.error && (
          <Card title="改写后 SQL 预览" size="small" style={{ marginTop: 12 }}>
            <Editor height="200px" language="sql" theme="vs" value={aiResult.rewritten_sql}
              onMount={(editor) => { editor.layout(); setTimeout(() => editor.layout(), 120); }}
              options={{ readOnly: true, minimap: { enabled: false }, wordWrap: 'on', fontSize: 12, automaticLayout: true }} />
          </Card>
        )}
      </Modal>
    </div>
  );
}
