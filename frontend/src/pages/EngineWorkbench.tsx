import React, { useEffect, useState, useCallback } from 'react';
import {
  Card, Row, Col, Tabs, Table, Button, Space, Tag, Input, message, Popconfirm, Tooltip, Switch,
} from 'antd';
import {
  ReloadOutlined, CodeOutlined, CheckCircleOutlined, CloseCircleOutlined,
  ExperimentOutlined, ThunderboltOutlined, DatabaseOutlined, ApiOutlined,
} from '@ant-design/icons';
import { PageShell, StatusTag } from '../components/shell';
import { tokens } from '../theme/tokens';
import { engineApi, dorisApi } from '../services/api';

const ENGINE_CN: Record<string, string> = { doris: 'Doris', duckdb: 'DuckDB 联邦', pg: 'PG 业务库' };

/** 引擎工作台（P5）：三 Tab —— 总览(健康/缓存/查询历史) / Doris(catalog/EXPLAIN/Profile) / DuckDB(Pushdown调试/熔断/加速器) */
const EngineWorkbench: React.FC = () => {
  // 总览
  const [health, setHealth] = useState<Record<string, any>>({});
  const [healthLoading, setHealthLoading] = useState(false);
  const [cacheStats, setCacheStats] = useState<any>(null);
  const [queries, setQueries] = useState<any[]>([]);
  const [queriesLoading, setQueriesLoading] = useState(false);

  // Doris tab
  const [catalogs, setCatalogs] = useState<any[]>([]);
  const [catLoading, setCatLoading] = useState(false);
  const [probing, setProbing] = useState<string | null>(null);
  const [probeResult, setProbeResult] = useState<Record<string, any>>({});
  const [explainSql, setExplainSql] = useState('SELECT * FROM test_db.dim_cst_elec_cons_cust LIMIT 5');
  const [explainVerbose, setExplainVerbose] = useState(false);
  const [explainPlan, setExplainPlan] = useState('');
  const [explaining, setExplaining] = useState(false);
  const [profileId, setProfileId] = useState('');
  const [profileOut, setProfileOut] = useState('');
  const [profiling, setProfiling] = useState(false);

  // DuckDB tab
  const [debugSql, setDebugSql] = useState('SELECT * FROM dim_ps_wbs_budget_amt WHERE budget_amt >= 100 AND budget_amt <= 500 AND name IN (\'a\',\'b\') AND name LIKE \'A%\'');
  const [debugOut, setDebugOut] = useState<any>(null);
  const [debugging, setDebugging] = useState(false);
  const [circuits, setCircuits] = useState<Record<string, any>>({});
  const [accelerators, setAccelerators] = useState<any[]>([]);
  const [accLoading, setAccLoading] = useState(false);
  const [refreshing, setRefreshing] = useState<string | null>(null);

  // ---- 总览 ----
  const loadHealth = useCallback(async () => {
    setHealthLoading(true);
    try { const r = await engineApi.health({ silent: true }); setHealth(r.data?.data || {}); }
    catch { /* 忽略 */ } finally { setHealthLoading(false); }
  }, []);
  const loadCache = useCallback(async () => {
    try { const r = await engineApi.cacheStats({ silent: true }); setCacheStats(r.data?.data || null); } catch { /* 忽略 */ }
  }, []);
  const loadQueries = useCallback(async () => {
    setQueriesLoading(true);
    try { const r = await engineApi.queries({ limit: 50 }, { silent: true }); setQueries(r.data?.data?.items || []); }
    catch { /* 忽略 */ } finally { setQueriesLoading(false); }
  }, []);

  // ---- Doris ----
  const loadCatalogs = useCallback(async () => {
    setCatLoading(true);
    try { const r = await dorisApi.listCatalogs({ silent: true }); setCatalogs(r.data?.data || []); }
    catch { /* 忽略 */ } finally { setCatLoading(false); }
  }, []);
  const probeCatalog = async (name: string) => {
    setProbing(name);
    try { const r = await dorisApi.probeCatalog(name, { silent: true }); setProbeResult((p) => ({ ...p, [name]: r.data?.data || {} })); message.success(`${name} 探活成功`); }
    catch (e: any) { message.error(`探活失败: ${e?.response?.data?.detail || e?.message}`); }
    finally { setProbing(null); }
  };
  const runExplain = async () => {
    if (!explainSql.trim()) { message.warning('请输入 SQL'); return; }
    setExplaining(true);
    try {
      const r = await engineApi.explain(explainSql.trim(), undefined, explainVerbose, { silent: true });
      if (r.data?.code === 200) setExplainPlan(r.data.data?.plan || '(空计划)');
      else setExplainPlan(`[错误] ${r.data?.data?.error || 'EXPLAIN 失败'}`);
    } catch (e: any) { setExplainPlan(`[请求失败] ${e?.message}`); }
    finally { setExplaining(false); }
  };
  const runProfile = async () => {
    if (!profileId.trim()) { message.warning('请输入 QueryId'); return; }
    setProfiling(true);
    try {
      const r = await engineApi.profile(profileId.trim(), { silent: true });
      setProfileOut(r.data?.code === 200 ? JSON.stringify(r.data.data?.profile || {}, null, 2) : `[错误] ${r.data?.data?.error || '无 profile'}`);
    } catch (e: any) { setProfileOut(`[请求失败] ${e?.message}`); }
    finally { setProfiling(false); }
  };

  // ---- DuckDB ----
  const runDebug = async () => {
    if (!debugSql.trim()) { message.warning('请输入 SQL'); return; }
    setDebugging(true);
    try {
      const r = await engineApi.pushdownDebug(debugSql.trim(), { silent: true });
      setDebugOut(r.data?.data || { error: '无输出' });
    } catch (e: any) { setDebugOut({ error: e?.response?.data?.data?.error || e?.message }); }
    finally { setDebugging(false); }
  };
  const loadCircuits = useCallback(async () => {
    try { const r = await engineApi.circuits({ silent: true }); setCircuits(r.data?.data || {}); } catch { /* 忽略 */ }
  }, []);
  const loadAccelerators = useCallback(async () => {
    setAccLoading(true);
    try { const r = await engineApi.accelerators({ silent: true }); setAccelerators(r.data?.data || []); }
    catch { /* 忽略 */ } finally { setAccLoading(false); }
  }, []);
  const refreshAcc = async (id: string) => {
    setRefreshing(id);
    try { await engineApi.acceleratorRefresh(id, { silent: true }); message.success('已刷新'); loadAccelerators(); }
    catch (e: any) { message.error(`刷新失败: ${e?.response?.data?.data?.error || e?.message}`); }
    finally { setRefreshing(null); }
  };
  const refreshAll = async () => {
    try { await engineApi.acceleratorRefreshAll({ silent: true }); message.success('已触发到期刷新'); loadAccelerators(); }
    catch (e: any) { message.error(`刷新失败: ${e?.message}`); }
  };
  const toggleAcc = async (a: any) => {
    try {
      await engineApi.acceleratorUpdate(a.id, { ...a, enabled: !a.enabled }, { silent: true });
      message.success(a.enabled ? '已停用' : '已启用');
      loadAccelerators();
    } catch (e: any) { message.error(`更新失败: ${e?.message}`); }
  };

  useEffect(() => {
    loadHealth(); loadCache(); loadQueries(); loadCatalogs(); loadCircuits(); loadAccelerators();
  }, [loadHealth, loadCache, loadQueries, loadCatalogs, loadCircuits, loadAccelerators]);

  const queryColumns = [
    { title: '时间', dataIndex: 'created_at', render: (v: string) => v || '-' },
    { title: '引擎', dataIndex: 'engine', render: (v: string) => <Tag>{v}</Tag> },
    { title: '状态', dataIndex: 'status', render: (v: string) => <StatusTag preset={v === 'ok' ? 'success' : 'error'}>{v}</StatusTag> },
    { title: '行数', dataIndex: 'rows_returned', width: 70 },
    { title: '耗时ms', dataIndex: 'duration_ms', width: 80 },
    { title: 'error_class', dataIndex: 'error_class', width: 110, render: (v: string) => v ? <Tag color="default">{v}</Tag> : '-' },
    { title: 'SQL', dataIndex: 'sql', ellipsis: true, render: (v: string) => <span style={{ fontFamily: 'Consolas, monospace', fontSize: 12 }}>{v}</span> },
  ];

  const catColumns = [
    { title: 'Catalog', dataIndex: 'name', render: (v: string) => <StatusTag preset="info">{v}</StatusTag> },
    { title: '类型', dataIndex: 'catalog_type' },
    {
      title: '探活',
      render: (_: any, r: any) => {
        const p = probeResult?.[r.name];
        return p ? <span style={{ fontSize: 12, color: tokens.colors.textSecondary }}>{p.databases?.length || 0} 库 · {p.sample_tables} 表</span> : <span style={{ fontSize: 12, color: tokens.colors.textTertiary }}>-</span>;
      },
    },
    {
      title: '操作', render: (_: any, r: any) => (
        <Space size={4}>
          <Button size="small" icon={<ExperimentOutlined />} loading={probing === r.name} onClick={() => probeCatalog(r.name)}>探活</Button>
        </Space>
      ),
    },
  ];

  const circuitRows = Object.entries(circuits).map(([id, st]: [string, any]) => ({
    key: id, id, state: st?.state || 'CLOSED', failures: st?.failures || 0, opened_at: st?.opened_at || null,
  }));
  const circuitColumns = [
    { title: '端点 ID', dataIndex: 'id', ellipsis: true },
    { title: '状态', dataIndex: 'state', render: (v: string) => <StatusTag preset={v === 'OPEN' ? 'error' : v === 'HALF_OPEN' ? 'warning' : 'success'} dot>{v}</StatusTag> },
    { title: '连续失败', dataIndex: 'failures', width: 90 },
  ];

  const accColumns = [
    { title: '名称', dataIndex: 'name' },
    { title: '覆盖表', dataIndex: 'source_tables', render: (v: string[]) => (v || []).map((t) => <Tag key={t}>{t}</Tag>) },
    { title: '聚合', dataIndex: 'agg_expr', render: (v: string) => v ? <Tag color="processing">{v}</Tag> : <Tag>分组直查</Tag> },
    { title: '目标表', dataIndex: 'target_table', render: (v: string, r: any) => <span style={{ fontSize: 12 }}>{r.target_db}.{v}</span> },
    { title: '数据截至', dataIndex: 'last_refresh_at', render: (v: string) => v ? <span style={{ fontSize: 12 }}>{v.slice(11, 16)}</span> : <span style={{ fontSize: 12, color: tokens.colors.textTertiary }}>未刷新</span> },
    { title: '状态', dataIndex: 'last_status', render: (v: string) => v ? <StatusTag preset={v === 'ok' ? 'success' : 'error'}>{v}</StatusTag> : <Tag>未刷新</Tag> },
    {
      title: '操作', render: (_: any, a: any) => (
        <Space size={4}>
          <Button size="small" icon={<ReloadOutlined />} loading={refreshing === a.id} onClick={() => refreshAcc(a.id)}>刷新</Button>
          <Switch size="small" checked={a.enabled} onChange={() => toggleAcc(a)} />
        </Space>
      ),
    },
  ];

  return (
    <PageShell title="引擎工作台">
      <Tabs
        defaultActiveKey="overview"
        items={[
          {
            key: 'overview', label: <span><ThunderboltOutlined /> 总览</span>,
            children: (
              <Row gutter={12}>
                <Col span={10}>
                  <Card size="small" title={<Space><DatabaseOutlined />三引擎健康</Space>}
                    extra={<Button size="small" icon={<ReloadOutlined />} loading={healthLoading} onClick={loadHealth}>刷新</Button>}>
                    <Space direction="vertical" size={10}>
                      {Object.keys(ENGINE_CN).map((k) => {
                        const h = health?.[k];
                        const ok = h?.status === 'ok';
                        return (
                          <Space key={k} size={8}>
                            <StatusTag preset={ok ? 'success' : 'error'} dot icon={ok ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
                              {ENGINE_CN[k]} · {h ? (ok ? `正常 ${h.latency_ms}ms` : '不可用') : '探测中'}
                            </StatusTag>
                            {h?.checked_at_str ? <span style={{ fontSize: 12, color: tokens.colors.textTertiary }}>@{h.checked_at_str}</span> : null}
                          </Space>
                        );
                      })}
                    </Space>
                  </Card>
                  <Card size="small" title="缓存" style={{ marginTop: 12 }}
                    extra={<Button size="small" icon={<ReloadOutlined />} onClick={loadCache}>刷新</Button>}>
                    {cacheStats ? (
                      <Space size="large">
                        <span>命中率 <b>{((cacheStats.hit_rate || 0) * 100).toFixed(0)}%</b></span>
                        <span>命中 {cacheStats.hit} / 未命中 {cacheStats.miss}</span>
                        <span>内存 {cacheStats.entries}/{cacheStats.max}</span>
                        <span>落盘 parquet {cacheStats.disk_entries} 个</span>
                      </Space>
                    ) : <span style={{ color: tokens.colors.textTertiary }}>加载中…</span>}
                  </Card>
                </Col>
                <Col span={14}>
                  <Card size="small" title="查询历史（EngineQueryLog，含 run_id）"
                    extra={<Button size="small" icon={<ReloadOutlined />} onClick={loadQueries}>刷新</Button>}>
                    <Table size="small" rowKey="id" columns={queryColumns} dataSource={queries} loading={queriesLoading} pagination={{ pageSize: 8 }} scroll={{ x: 'max-content', y: 320 }} />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'doris', label: <span><DatabaseOutlined /> Doris</span>,
            children: (
              <Row gutter={12}>
                <Col span={10}>
                  <Card size="small" title="Catalog 探活" extra={<Button size="small" icon={<ReloadOutlined />} onClick={loadCatalogs}>刷新</Button>}>
                    <Table size="small" rowKey="name" columns={catColumns} dataSource={catalogs} loading={catLoading} pagination={false} />
                  </Card>
                </Col>
                <Col span={14}>
                  <Card size="small" title="EXPLAIN（两档）" extra={<Space>
                    <span style={{ fontSize: 12 }}>VERBOSE</span><Switch size="small" checked={explainVerbose} onChange={setExplainVerbose} />
                    <Button size="small" type="primary" icon={<CodeOutlined />} loading={explaining} onClick={runExplain}>执行</Button>
                  </Space>}>
                    <Input.TextArea value={explainSql} onChange={(e) => setExplainSql(e.target.value)} autoSize={{ minRows: 3, maxRows: 5 }} style={{ fontFamily: 'Consolas, monospace', fontSize: 12 }} />
                    {explainPlan ? <pre style={{ marginTop: 10, padding: 10, borderRadius: tokens.radius.card, background: tokens.colors.bgSubtle, fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 260, overflow: 'auto' }}>{explainPlan}</pre> : null}
                  </Card>
                  <Card size="small" title="Profile 代理（FE 18030，含 run_id）" style={{ marginTop: 12 }}>
                    <Space.Compact style={{ width: '100%' }}>
                      <Input value={profileId} onChange={(e) => setProfileId(e.target.value)} placeholder="QueryId（在查询历史 SQL 的 run_id 附近 / Doris 审计中获取）" />
                      <Button type="primary" icon={<ExperimentOutlined />} loading={profiling} onClick={runProfile}>查询</Button>
                    </Space.Compact>
                    {profileOut ? <pre style={{ marginTop: 8, padding: 10, borderRadius: tokens.radius.card, background: tokens.colors.bgSubtle, fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 220, overflow: 'auto' }}>{profileOut}</pre> : null}
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'duckdb', label: <span><ApiOutlined /> DuckDB</span>,
            children: (
              <Row gutter={12}>
                <Col span={12}>
                  <Card size="small" title="Pushdown 调试器（解析下推树，不真实执行）"
                    extra={<Button size="small" type="primary" icon={<CodeOutlined />} loading={debugging} onClick={runDebug}>调试</Button>}>
                    <Input.TextArea value={debugSql} onChange={(e) => setDebugSql(e.target.value)} autoSize={{ minRows: 4, maxRows: 6 }} style={{ fontFamily: 'Consolas, monospace', fontSize: 12 }} />
                    {debugOut ? (
                      <div style={{ marginTop: 10, fontSize: 12 }}>
                        <div>表：{(debugOut.tables ? Object.entries(debugOut.tables).map(([a, t]) => `${a}->${t}`) : []).join('、') || '-'}</div>
                        {(debugOut.pushdown_trace ? Object.entries(debugOut.pushdown_trace) : []).map(([tbl, tr]: [string, any]) => (
                          <div key={tbl} style={{ marginTop: 6 }}>
                            <StatusTag preset="info">{tbl}</StatusTag>
                            {tr?.cols ? Object.entries(tr.cols).map(([col, c]: [string, any]) => (
                              <Tag key={col} color={c?.pushed_to_api ? 'success' : 'default'} style={{ marginTop: 2 }}>
                                {col}: {c?.kind}{c?.pushed_to_api ? ' ✓下推' : ' 内存过滤'}
                              </Tag>
                            )) : null}
                          </div>
                        ))}
                        {debugOut.not_pushed?.length ? (
                          <div style={{ marginTop: 8, color: tokens.colors.textSecondary }}>
                            <b>未下推：</b>{debugOut.not_pushed.map((n: any) => `${n.table}.${n.column}(${n.kind})`).join('、')}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </Card>
                  <Card size="small" title="熔断 / 限速状态" style={{ marginTop: 12 }}
                    extra={<Button size="small" icon={<ReloadOutlined />} onClick={loadCircuits}>刷新</Button>}>
                    <Table size="small" rowKey="id" columns={circuitColumns} dataSource={circuitRows} pagination={false} />
                  </Card>
                </Col>
                <Col span={12}>
                  <Card size="small" title="预聚合加速器"
                    extra={<Space><Button size="small" icon={<ReloadOutlined />} loading={accLoading} onClick={loadAccelerators}>刷新</Button>
                      <Button size="small" type="primary" icon={<ThunderboltOutlined />} onClick={refreshAll}>刷新全部到期</Button></Space>}>
                    <Table size="small" rowKey="id" columns={accColumns} dataSource={accelerators} loading={accLoading} pagination={false} />
                    <div style={{ marginTop: 8, fontSize: 12, color: tokens.colors.textTertiary }}>
                      单值加速器（COUNT/SUM）命中同形查询时平台层自动拦截改写并标注「预聚合·数据截至」；分组加速器目标表可直查。
                    </div>
                  </Card>
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </PageShell>
  );
};

export default EngineWorkbench;
