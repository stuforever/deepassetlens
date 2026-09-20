import React, { useEffect, useState } from 'react';
import {
  Card, Button, Table, Space, Modal, Form, Input, InputNumber, message, Tag, Popconfirm, Select, Switch,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, ThunderboltOutlined, SaveOutlined, DatabaseOutlined,
  ReloadOutlined, CodeOutlined, CheckCircleOutlined, CloseCircleOutlined, ExperimentOutlined,
} from '@ant-design/icons';
import { PageShell, StatusTag } from '../components/shell';
import { tokens } from '../theme/tokens';
import { dorisApi, engineApi } from '../services/api';

interface Catalog {
  name: string;
  catalog_type: string;
  live_type?: string;
  in_db: boolean;
  jdbc_url?: string;
  jdbc_user?: string;
  driver_class?: string;
  driver_url?: string;
  es_hosts?: string;
  es_user?: string;
  created_at?: string;
}

const CATALOG_TYPE_CN: Record<string, string> = { jdbc: 'JDBC 联邦', es: 'Elasticsearch 联邦', internal: '内置' };

const DorisConfigPage: React.FC = () => {
  // Doris 连接配置
  const [cfg, setCfg] = useState<any>({ host: 'localhost', port: 9030, user: 'root', password: '', database: 'test_db', charset: 'utf8mb4', connect_timeout: 10 });
  const [cfgLoading, setCfgLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [savingCfg, setSavingCfg] = useState(false);
  const [cfgForm] = Form.useForm();

  // Catalog 管理
  const [catalogs, setCatalogs] = useState<Catalog[]>([]);
  const [catLoading, setCatLoading] = useState(false);
  const [catModalOpen, setCatModalOpen] = useState(false);
  const [catForm] = Form.useForm();

  // 批3：引擎健康徽标（doris/duckdb/pg）
  const [health, setHealth] = useState<Record<string, any>>({});
  const [healthLoading, setHealthLoading] = useState(false);
  // 批3：EXPLAIN
  const [explainOpen, setExplainOpen] = useState(false);
  const [explainSql, setExplainSql] = useState('');
  const [explainCatalog, setExplainCatalog] = useState('');
  const [explainVerbose, setExplainVerbose] = useState(false);
  const [explainPlan, setExplainPlan] = useState('');
  // P4：Catalog 探活/刷新
  const [probing, setProbing] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [probeResult, setProbeResult] = useState<Record<string, any>>({});
  const [explaining, setExplaining] = useState(false);

  const loadHealth = async () => {
    setHealthLoading(true);
    try {
      const res = await engineApi.health({ silent: true });
      setHealth(res.data?.data || {});
    } catch (e: any) {
      message.error('引擎健康探测失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setHealthLoading(false); }
  };

  const openExplain = () => { setExplainSql(''); setExplainPlan(''); setExplainOpen(true); };

  const runExplain = async () => {
    if (!explainSql.trim()) { message.warning('请输入待诊断的 SQL'); return; }
    setExplaining(true);
    try {
      const res = await engineApi.explain(explainSql.trim(), explainCatalog || undefined, explainVerbose, { silent: true });
      if (res.data?.code === 200) {
        setExplainPlan(res.data.data?.plan || '(空计划)');
      } else {
        setExplainPlan(`[错误] ${res.data?.data?.error || 'EXPLAIN 失败'}`);
      }
    } catch (e: any) {
      message.error('EXPLAIN 失败: ' + (e?.response?.data?.data?.error || e?.response?.data?.detail || e?.message));
    } finally { setExplaining(false); }
  };

  const ENGINE_CN: Record<string, string> = { doris: 'Doris', duckdb: 'DuckDB 联邦', pg: 'PG 业务库' };

  const loadCfg = async () => {
    setCfgLoading(true);
    try {
      const res = await dorisApi.getConfig({ silent: true });
      const d = res.data?.data || {};
      setCfg(d);
      cfgForm.setFieldsValue(d);
    } catch (e: any) {
      message.error('加载 Doris 配置失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setCfgLoading(false); }
  };

  const loadCatalogs = async () => {
    setCatLoading(true);
    try {
      const res = await dorisApi.listCatalogs({ silent: true });
      setCatalogs(res.data?.data || []);
    } catch (e: any) {
      message.error('加载 Catalog 列表失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setCatLoading(false); }
  };

  useEffect(() => { loadCfg(); loadCatalogs(); loadHealth(); }, []); // eslint-disable-line

  const testConn = async () => {
    const v = cfgForm.getFieldsValue();
    setTesting(true);
    try {
      await dorisApi.testConnection({ host: v.host, port: v.port, user: v.user, password: v.password }, { silent: true });
      message.success('Doris 连接测试成功');
    } catch (e: any) {
      message.error('连接失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setTesting(false); }
  };

  const saveCfg = async () => {
    const v = cfgForm.getFieldsValue();
    setSavingCfg(true);
    try {
      await dorisApi.putConfig(v, { silent: true });
      message.success('Doris 配置已保存');
    } catch (e: any) {
      message.error('保存失败: ' + (e?.response?.data?.detail || e?.message));
    } finally { setSavingCfg(false); }
  };

  const createCatalog = async (values: any) => {
    try {
      await dorisApi.createCatalog(values, { silent: true });
      message.success(`Catalog ${values.name} 创建成功`);
      setCatModalOpen(false);
      catForm.resetFields();
      loadCatalogs();
    } catch (e: any) {
      message.error('创建失败: ' + (e?.response?.data?.detail || e?.message));
    }
  };

  const deleteCatalog = async (name: string) => {
    try {
      await dorisApi.deleteCatalog(name, { silent: true });
      message.success(`Catalog ${name} 已删除`);
      loadCatalogs();
    } catch (e: any) {
      message.error('删除失败: ' + (e?.response?.data?.detail || e?.message));
    }
  };

  // P4：Catalog 探活（SHOW DATABASES FROM）+ 刷新元数据（REFRESH CATALOG）
  const probeCatalog = async (name: string) => {
    setProbing(name);
    try {
      const res = await dorisApi.probeCatalog(name, { silent: true });
      const d = res.data?.data || {};
      setProbeResult((prev) => ({ ...prev, [name]: d }));
      message.success(`Catalog ${name} 探活成功：${(d.databases || []).length} 个库（采样 ${d.sample_tables} 表）`);
    } catch (e: any) {
      message.error(`探活失败: ${e?.response?.data?.detail || e?.message}`);
    } finally { setProbing(null); }
  };

  const refreshCatalog = async (name: string) => {
    setRefreshing(name);
    try {
      await dorisApi.refreshCatalog(name, { silent: true });
      message.success(`Catalog ${name} 元数据已刷新`);
    } catch (e: any) {
      message.error(`刷新失败: ${e?.response?.data?.detail || e?.message}`);
    } finally { setRefreshing(null); }
  };

  const catColumns = [
    { title: 'Catalog 名称', dataIndex: 'name', render: (v: string) => <StatusTag preset="info">{v}</StatusTag> },
    {
      title: '类型', dataIndex: 'catalog_type',
      render: (v: string, r: Catalog) => {
        const raw: string = v || r.live_type || '';
        return <Tag color="default">{CATALOG_TYPE_CN[raw] || raw || '-'}</Tag>;
      },
    },
    {
      title: '纳管',
      dataIndex: 'in_db',
      render: (v: boolean) => v ? <StatusTag preset="success">已纳管</StatusTag> : <Tag>外部</Tag>,
    },
    {
      title: '地址', dataIndex: 'jdbc_url',
      render: (v: string, r: Catalog) => (v || r.es_hosts) ? <span style={{ fontSize: 12 }}>{v || r.es_hosts}</span> : '-',
    },
    {
      title: '探活结果',
      render: (_: any, r: Catalog) => {
        const p = probeResult?.[r.name];
        return p ? <span style={{ fontSize: 12, color: tokens.colors.textSecondary }}>
          {p.databases?.length || 0} 库 · 采样 {p.sample_tables} 表</span> : <span style={{ fontSize: 12, color: tokens.colors.textTertiary }}>未探测</span>;
      },
    },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v || '-' },
    {
      title: '操作',
      onCell: () => ({ className: 'dal-action-col' }),  // 三轨M9：操作列 hover 显现
      render: (_: any, r: Catalog) => (
        <Space size={4} wrap>
          <Button size="small" icon={<ExperimentOutlined />} loading={probing === r.name} onClick={() => probeCatalog(r.name)}>探活</Button>
          <Button size="small" icon={<ReloadOutlined />} loading={refreshing === r.name} onClick={() => refreshCatalog(r.name)}>刷新</Button>
          {/* 三轨M9：危险操作收「更多」标红 */}
          <Popconfirm title={`确认删除 Catalog ${r.name}？（Doris 与本地记录一并删除）`} onConfirm={() => deleteCatalog(r.name)}>
            <Button size="small" danger type="text" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageShell title="Doris 配置">
      <Card
        title={<Space><DatabaseOutlined />Doris 连接配置</Space>}
        size="small"
        loading={cfgLoading}
        extra={<Space>
          <Button icon={<ThunderboltOutlined />} loading={testing} onClick={testConn}>测试连接</Button>
          <Button type="primary" icon={<SaveOutlined />} loading={savingCfg} onClick={saveCfg}>保存配置</Button>
        </Space>}
      >
        <Form form={cfgForm} layout="inline" initialValues={cfg}>
          <Form.Item name="host" label="Host"><Input placeholder="localhost" style={{ width: 160 }} /></Form.Item>
          <Form.Item name="port" label="Port"><InputNumber min={1} max={65535} style={{ width: 100 }} /></Form.Item>
          <Form.Item name="user" label="用户名"><Input style={{ width: 120 }} /></Form.Item>
          <Form.Item name="password" label="密码"><Input.Password style={{ width: 140 }} /></Form.Item>
          <Form.Item name="database" label="默认库"><Input placeholder="test_db" style={{ width: 140 }} /></Form.Item>
          <Form.Item name="charset" label="charset"><Input style={{ width: 100 }} /></Form.Item>
          <Form.Item name="connect_timeout" label="连接超时(秒)"><InputNumber min={1} style={{ width: 90 }} /></Form.Item>
        </Form>
        <div style={{ marginTop: 8, fontSize: 12, color: tokens.colors.textTertiary }}>
          Doris FE 暴露 MySQL 协议（默认 9030），pymysql 直连。sql_integration 模式执行 integration_sql 时使用此连接。
        </div>
      </Card>

      {/* 批3：引擎健康徽标（懒探测 + 60s 缓存，GET /api/engine/health） */}
      <Card
        title={<Space><DatabaseOutlined />引擎健康</Space>}
        size="small"
        style={{ marginTop: 12 }}
        extra={<Button size="small" icon={<ReloadOutlined />} loading={healthLoading} onClick={loadHealth}>刷新</Button>}
      >
        <Space size="large" wrap>
          {Object.keys(ENGINE_CN).map((key) => {
            const h = health?.[key];
            const ok = h?.status === 'ok';
            const loading = !h;
            return (
              <Space key={key} size={6}>
                <StatusTag
                  preset={ok ? 'success' : 'error'}
                  dot
                  pulse={loading}
                  icon={ok ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                >
                  {ENGINE_CN[key]} · {loading ? '探测中' : ok ? `正常 ${h.latency_ms}ms` : '不可用'}
                </StatusTag>
                {h?.checked_at_str ? (
                  <span style={{ fontSize: 12, color: tokens.colors.textTertiary }}>@{h.checked_at_str}</span>
                ) : null}
              </Space>
            );
          })}
        </Space>
        <div style={{ marginTop: 8, fontSize: 12, color: tokens.colors.textTertiary }}>
          懒探测 + 60s 缓存；任一引擎不可用时会反映在对话结果诊断与「数据来源映射」路由提示中。
        </div>
      </Card>

      <Card
        title={<Space><DatabaseOutlined />Catalog 管理（jdbc / es 联邦）</Space>}
        size="small"
        style={{ marginTop: 12 }}
        extra={<Space>
          <Button icon={<CodeOutlined />} onClick={openExplain}>EXPLAIN 诊断</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { catForm.resetFields(); catForm.setFieldsValue({ catalog_type: 'jdbc', driver_class: 'com.mysql.cj.jdbc.Driver' }); setCatModalOpen(true); }}>新建 Catalog</Button>
        </Space>}
      >
        <Table size="small" dataSource={catalogs} rowKey="name" columns={catColumns} loading={catLoading} pagination={false} />
        <div style={{ marginTop: 8, fontSize: 12, color: tokens.colors.textTertiary }}>
          「外部」= Doris 已存在但未在本平台纳管（如 mysql_tupu），可直接在「数据来源映射」SQL 编辑器选用；「已纳管」= 本平台创建可重建/编辑。
        </div>
      </Card>

      <Modal
        title="新建 Catalog"
        open={catModalOpen}
        onOk={() => catForm.submit()}
        onCancel={() => { setCatModalOpen(false); catForm.resetFields(); }}
        destroyOnHidden
        width={620}
      >
        <Form form={catForm} layout="vertical" onFinish={createCatalog} preserve={false}>
          <Form.Item name="name" label="Catalog 名称" rules={[{ required: true, message: '名称必填' }, { pattern: /^[a-zA-Z_][a-zA-Z0-9_]*$/, message: '仅限字母/数字/下划线，首字符非数字' }]}>
            <Input placeholder="例如：mysql_tupu / my_es" />
          </Form.Item>
          <Form.Item name="catalog_type" label="类型" initialValue="jdbc">
            <Select
              options={[
                { value: 'jdbc', label: 'JDBC 联邦（MySQL/PG 等）' },
                { value: 'es', label: 'Elasticsearch 联邦' },
                { value: 'internal', label: 'internal（内置，无需创建）' },
              ]}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(p, c) => p.catalog_type !== c.catalog_type}>
            {({ getFieldValue }) => {
              const type = getFieldValue('catalog_type') || 'jdbc';
              if (type === 'es') {
                return (
                  <>
                    <Form.Item name="es_hosts" label="ES Hosts" rules={[{ required: true, message: 'ES 地址必填' }]}>
                      <Input placeholder="http://host.docker.internal:9200（逗号分隔多节点）" />
                    </Form.Item>
                    <Form.Item name="es_user" label="ES 用户名（可选）">
                      <Input placeholder="elastic（无鉴权可留空）" />
                    </Form.Item>
                    <Form.Item name="es_password" label="ES 密码（可选）">
                      <Input.Password placeholder="无鉴权可留空" />
                    </Form.Item>
                  </>
                );
              }
              if (type === 'internal') {
                return <div style={{ color: tokens.colors.textTertiary, fontSize: 12 }}>internal 为 Doris 内置 catalog，无需创建，直接保存即可登记。</div>;
              }
              return (
                <>
                  <Form.Item name="jdbc_url" label="JDBC URL" rules={[{ required: true, message: 'JDBC URL 必填' }]}>
                    <Input placeholder="jdbc:mysql://host.docker.internal:3306/tupu?useUnicode=true&characterEncoding=utf-8" />
                  </Form.Item>
                  <Form.Item name="jdbc_user" label="用户名" rules={[{ required: true, message: '用户名必填' }]}>
                    <Input placeholder="root" />
                  </Form.Item>
                  <Form.Item name="jdbc_password" label="密码" rules={[{ required: true, message: '密码必填' }]}>
                    <Input.Password placeholder="root" />
                  </Form.Item>
                  <Form.Item name="driver_class" label="Driver Class">
                    <Input placeholder="com.mysql.cj.jdbc.Driver" />
                  </Form.Item>
                  <Form.Item name="driver_url" label="Driver URL（jar 下载地址）">
                    <Input placeholder="http://172.28.80.2:8888/mysql-connector-j-8.0.33.jar" />
                  </Form.Item>
                </>
              );
            }}
          </Form.Item>
        </Form>
      </Modal>

      {/* 批3/P4：Doris EXPLAIN 执行计划诊断（两档：EXPLAIN / EXPLAIN VERBOSE） */}
      <Modal
        title="Doris EXPLAIN 诊断"
        open={explainOpen}
        onOk={runExplain}
        confirmLoading={explaining}
        okText={explainPlan ? '重新执行' : '执行 EXPLAIN'}
        onCancel={() => setExplainOpen(false)}
        destroyOnHidden
        width={720}
      >
        <Input.TextArea
          value={explainSql}
          onChange={(e) => setExplainSql(e.target.value)}
          placeholder="输入 Doris SQL，如：SELECT * FROM pg_tupu.public.dim_ps_wbs LIMIT 10"
          autoSize={{ minRows: 3, maxRows: 6 }}
          style={{ fontFamily: 'Consolas, monospace' }}
        />
        <Space style={{ marginTop: 8 }} wrap>
          <Input
            value={explainCatalog}
            onChange={(e) => setExplainCatalog(e.target.value)}
            placeholder="Catalog（可选，如 pg_tupu；留空用默认库）"
            style={{ fontFamily: 'Consolas, monospace', width: 300 }}
          />
          <span style={{ fontSize: 13 }}>
            <Switch size="small" checked={explainVerbose} onChange={setExplainVerbose} /> EXPLAIN VERBOSE（详细计划）
          </span>
        </Space>
        {explainPlan ? (
          <pre
            style={{
              marginTop: 12, padding: 12, borderRadius: tokens.radius.card,
              background: tokens.colors.bgSubtle, fontSize: 12, lineHeight: 1.6,
              whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 360, overflow: 'auto',
            }}
          >{explainPlan}</pre>
        ) : null}
      </Modal>
    </PageShell>
  );
};

export default DorisConfigPage;
