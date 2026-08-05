import React, { useEffect, useState, useMemo } from 'react';
import { Drawer, Table, Button, Form, Input, Select, Space, Alert, message, Tag, Empty, Spin, Typography } from 'antd';
import { LinkOutlined, ThunderboltOutlined, SaveOutlined, EyeOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { mappingApi, entityApi, entityApiMappingApi, apiEndpointApi, kgApi } from '../services/api';
import { useStore } from '../store/useStore';
import { StatusTag } from './shell';

const { TextArea } = Input;
const { Text } = Typography;

type Props = {
  entity: any;
  sourceMode: string;
  open: boolean;
  onClose: () => void;
  onOpenTarget?: (menuKey: string) => void;
};

const MODE_LABEL: Record<string, string> = {
  physical_table: '物理数据表',
  sql_integration: '多源SQL整合(Doris)',
  api_integration: '多源API整合(DuckDB)',
};

/**
 * 单实体映射 Drawer：按 source_mode 显示该实体的对应映射（查看/编辑），不跳转。
 *  - physical_table：字段映射明细（属性<-源表.字段），只读 + 跳映射管理页编辑
 *  - sql_integration：integration_sql 编辑器 + 验证执行
 *  - api_integration：EntityApiMapping 表单（1:1）+ 验证 + 预览
 * 消除"数据来源配置"与"映射规则"的割裂。
 */
const EntityMappingDrawer: React.FC<Props> = ({ entity, sourceMode, open, onClose, onOpenTarget }) => {
  const { setMappingFilterEntityId } = useStore();
  const entityId = entity?.id;

  return (
    <Drawer
      width={760}
      open={open}
      onClose={onClose}
      title={
        <Space>
          <span>映射配置</span>
          {entity && <StatusTag preset="info">{entity.entity_name}</StatusTag>}
          <Tag>{MODE_LABEL[sourceMode] || sourceMode}</Tag>
        </Space>
      }
      destroyOnHidden
    >
      {!entity ? (
        <Empty description="未选中实体" />
      ) : sourceMode === 'physical_table' ? (
        <PhysicalView entityId={entityId} entity={entity} onJump={() => { setMappingFilterEntityId(entityId); onOpenTarget?.('mapping'); }} />
      ) : sourceMode === 'sql_integration' ? (
        <SqlView entityId={entityId} initialSql={entity.integration_sql || ''} />
      ) : sourceMode === 'api_integration' ? (
        <ApiView entityId={entityId} entityCode={entity.entity_code} />
      ) : (
        <Empty description={`未知模式: ${sourceMode}`} />
      )}
    </Drawer>
  );
};

// --------------------------------------------------------------------------- //
// physical_table：字段映射明细（只读 + 跳编辑）
// --------------------------------------------------------------------------- //
const PhysicalView: React.FC<{ entityId: string; entity: any; onJump: () => void }> = ({ entityId, entity, onJump }) => {
  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);

  useEffect(() => {
    if (!entityId) return;
    setLoading(true);
    Promise.all([mappingApi.getMappingRules(entityId), mappingApi.getSources()])
      .then(([rRes, sRes]) => {
        setRules(rRes.data?.data || []);
        setSources(sRes.data?.data || []);
      })
      .catch(() => message.error('加载字段映射失败'))
      .finally(() => setLoading(false));
  }, [entityId]);

  const rows = useMemo(() => {
    const out: any[] = [];
    const allTables = sources || [];
    rules.forEach((rule: any) => {
      const fm = rule.field_mappings || {};
      Object.keys(fm).forEach((key) => {
        if (key === '__meta__') return;
        const m = fm[key];
        const eid = key.split('_')[0];
        const propEn = key.slice(eid.length + 1);
        if (eid !== entityId) return;
        const prop = (entity?.properties_schema || []).find((p: any) => p.name === propEn) || {};
        const rawSources = Array.isArray(m?.source) ? m.source : (m?.source ? [m.source] : (typeof m === 'string' ? [m] : []));
        const sourceDesc = rawSources.map((sv: string) => {
          const matched = allTables.find((t: any) => sv.startsWith(`${t.id}_`));
          if (matched) return `${matched.enName || matched.table_en || '?'}.${sv.slice(matched.id.length + 1)}`;
          return sv;
        }).join(' | ');
        out.push({ key, propEn, propCn: prop.cnName || '', source: sourceDesc || '-', isPk: m?.is_pk ? '是' : '否', desc: m?.desc || '' });
      });
    });
    return out;
  }, [rules, sources, entityId, entity]);

  return (
    <Spin spinning={loading}>
      <Alert
        type="info"
        showIcon
        message={`实体「${entity?.entity_name}」直接读取物理表「${entity?.entity_en_name || '-'}」的数据`}
        description="字段映射规则定义了实体属性与源表字段的对应关系。完整编辑（新增/修改字段映射）请在映射规则管理页进行。"
        style={{ marginBottom: 12 }}
      />
      {rows.length === 0 ? (
        <Empty description="该实体未配置字段映射规则" style={{ margin: '32px 0' }} />
      ) : (
        <Table
          size="small"
          dataSource={rows}
          pagination={false}
          scroll={{ y: 420 }}
          columns={[
            { title: '属性', dataIndex: 'propEn', width: 140, render: (v: string, r: any) => (<><Text strong>{v}</Text>{r.propCn ? <><br /><Text type="secondary" style={{ fontSize: 12 }}>{r.propCn}</Text></> : null}</>) },
            { title: '源表.字段', dataIndex: 'source' },
            { title: '主键', dataIndex: 'isPk', width: 60, render: (v: string) => (v === '是' ? <StatusTag preset="warning">PK</StatusTag> : '-') },
            { title: '说明', dataIndex: 'desc', ellipsis: true },
          ]}
        />
      )}
      <Button type="dashed" icon={<ArrowRightOutlined />} block style={{ marginTop: 16 }} onClick={onJump}>
        去映射规则管理页编辑
      </Button>
    </Spin>
  );
};

// --------------------------------------------------------------------------- //
// sql_integration：integration_sql 编辑器 + 验证执行
// --------------------------------------------------------------------------- //
const SqlView: React.FC<{ entityId: string; initialSql: string }> = ({ entityId, initialSql }) => {
  const [sql, setSql] = useState(initialSql);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => { setSql(initialSql); }, [initialSql]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await entityApi.updateEntity(entityId, { integration_sql: sql });
      message.success('整合 SQL 已保存');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally { setSaving(false); }
  };

  const handleVerify = async () => {
    if (!sql.trim()) { message.warning('请先填写整合 SQL'); return; }
    setVerifying(true); setResult(null);
    try {
      const res = await kgApi.executeSql(sql);
      const data = res.data || {};
      if (data.error) { message.error(data.error); return; }
      setResult(data);
      message.success(`执行成功，返回 ${data.row_count || (data.rows || []).length} 行`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.response?.data?.error || '执行失败');
    } finally { setVerifying(false); }
  };

  const cols = result?.columns || [];
  const rows2d = result?.rows || [];

  return (
    <div>
      <Alert
        type="info"
        showIcon
        message="通过 Doris 执行下方整合 SQL 获取实体数据"
        description="SQL 可跨多源数据库整合，结果集字段需与实体属性对应。"
        style={{ marginBottom: 12 }}
      />
      <TextArea
        rows={8}
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        placeholder={'-- 整合 SQL 示例：\n-- SELECT cust_no, cust_name, ec_addr\n-- FROM doris_db.dim_cst_elec_cons_cust'}
        style={{ fontFamily: 'monospace', fontSize: 12 }}
      />
      <Space style={{ marginTop: 8 }}>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>保存整合 SQL</Button>
        <Button icon={<ThunderboltOutlined />} loading={verifying} onClick={handleVerify}>验证执行</Button>
      </Space>
      {result && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>执行结果（{result.row_count || rows2d.length} 行）：</Text>
          <Table
            size="small"
            rowKey={(_, i) => String(i)}
            style={{ marginTop: 6 }}
            dataSource={rows2d.map((r: any[], i: number) => Object.fromEntries(cols.map((c: string, j: number) => [c, r[j]])))}
            columns={cols.map((c: string) => ({ title: c, dataIndex: c, ellipsis: true, width: 150 }))}
            pagination={false}
            scroll={{ x: 'max-content', y: 300 }}
          />
        </div>
      )}
    </div>
  );
};

// --------------------------------------------------------------------------- //
// api_integration：EntityApiMapping 表单（1:1）+ 验证 + 预览
// --------------------------------------------------------------------------- //
const ApiView: React.FC<{ entityId: string; entityCode: string }> = ({ entityId, entityCode }) => {
  const [loading, setLoading] = useState(false);
  const [mapping, setMapping] = useState<any>(null);
  const [endpoints, setEndpoints] = useState<any[]>([]);
  const [form, setForm] = useState<any>({ name: '', api_endpoint_ids: [], pseudo_sql: '', description: '' });
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<any>(null);

  useEffect(() => {
    if (!entityId) return;
    setLoading(true);
    Promise.all([entityApiMappingApi.list(entityId), apiEndpointApi.list()])
      .then(([mRes, epRes]) => {
        const list = mRes.data?.data || [];
        const m = list[0] || null;
        setMapping(m);
        if (m) setForm({ name: m.name || '', api_endpoint_ids: m.api_endpoint_ids || [], pseudo_sql: m.pseudo_sql || '', description: m.description || '' });
        setEndpoints(epRes.data?.data || []);
      })
      .catch(() => message.error('加载 API 映射失败'))
      .finally(() => setLoading(false));
  }, [entityId]);

  const endpointOptions = endpoints.map((ep: any) => ({ label: `${ep.name} [${ep.table_name}]`, value: ep.id }));

  const handleSave = async () => {
    if (!form.pseudo_sql.trim() || form.api_endpoint_ids.length === 0) {
      message.warning('API 端点 和 伪逻辑SQL 为必填');
      return;
    }
    setSaving(true);
    try {
      const payload = { ...form, entity_id: entityId, name: form.name || undefined };
      if (mapping?.id) {
        await entityApiMappingApi.update(mapping.id, payload);
        message.success('已更新');
      } else {
        const res = await entityApiMappingApi.create(payload);
        setMapping(res.data?.data || { id: res.data?.data?.id });
        message.success('已创建');
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally { setSaving(false); }
  };

  const handleVerify = async () => {
    if (!mapping?.id) { message.warning('请先保存'); return; }
    setVerifying(true); setPreview(null);
    try {
      const res = await entityApiMappingApi.verify(mapping.id);
      const d = res.data?.data || {};
      if (d.error) message.error(d.error);
      else { setPreview(d); message.success(`验证成功，返回 ${d.row_count || (d.rows || []).length} 行`); }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '验证失败');
    } finally { setVerifying(false); }
  };

  const handlePreview = async () => {
    setPreviewing(true); setPreview(null);
    try {
      const res = await mappingApi.previewEntityData(entityId, 20);
      const d = res.data?.data || {};
      setPreview(d);
      if (d.hint) message.warning(d.hint);
      else message.success(`预览成功，${d.row_count || 0} 行`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '预览失败');
    } finally { setPreviewing(false); }
  };

  const cols = preview?.columns || [];
  const rows2d = preview?.rows || [];
  const isObjRows = rows2d.length > 0 && !Array.isArray(rows2d[0]);
  const tableData = isObjRows ? rows2d : rows2d.map((r: any[], i: number) => Object.fromEntries(cols.map((c: string, j: number) => [c, r?.[j]])));
  const tableCols = (isObjRows ? Object.keys(rows2d[0] || {}) : cols).map((c: string) => ({ title: c, dataIndex: c, ellipsis: true, width: 150 }));

  return (
    <Spin spinning={loading}>
      <Alert
        type="info"
        showIcon
        message="通过 DuckDB 联邦查询整合 API 数据（EntityApiMapping）"
        description="配置该实体关联的 API 端点与伪逻辑 SQL，预览/取数将走 DuckDB 联邦查询。一个实体仅一条 API 映射。"
        style={{ marginBottom: 12 }}
      />
      <Form layout="vertical">
        <Form.Item label="名称(可空)">
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="默认用实体名" />
        </Form.Item>
        <Form.Item label="API 端点(虚拟表，可多选)" required>
          <Select mode="multiple" options={endpointOptions} value={form.api_endpoint_ids} onChange={(v) => setForm({ ...form, api_endpoint_ids: v })} placeholder="选择 API 端点" />
        </Form.Item>
        <Form.Item label="伪逻辑 SQL(引用虚拟表名，不含 WHERE)" required>
          <TextArea rows={6} value={form.pseudo_sql} onChange={(e) => setForm({ ...form, pseudo_sql: e.target.value })} style={{ fontFamily: 'monospace', fontSize: 13 }}
            placeholder="SELECT * FROM dim_ps_wbs_element" />
        </Form.Item>
        <Form.Item label="描述">
          <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Form.Item>
      </Form>
      <Space wrap style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>{mapping?.id ? '更新' : '创建'}</Button>
        <Button icon={<ThunderboltOutlined />} loading={verifying} onClick={handleVerify} disabled={!mapping?.id}>验证 SQL 执行</Button>
        <Button icon={<EyeOutlined />} loading={previewing} onClick={handlePreview}>数据预览</Button>
      </Space>
      {preview && (
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>结果（{preview.row_count || tableData.length} 行）：</Text>
          <Table size="small" rowKey={(_, i) => String(i)} style={{ marginTop: 6 }} dataSource={tableData} columns={tableCols} pagination={false} scroll={{ x: 'max-content', y: 320 }} />
        </div>
      )}
    </Spin>
  );
};

export default EntityMappingDrawer;
