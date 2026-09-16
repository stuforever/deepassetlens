/**
 * MemoryAdmin - 记忆管理页（记忆插槽② spec §九 + 批10 F3 并入 DeepTutor memory 分层视图）：
 * 单套不双轨——不建新路由，全部以 antd Tabs 并入本页（admin-only）。
 *
 * tab 结构：
 *  ①「树与固化」——本页原有 178 行能力原样保留为第一个 tab（零功能删改）：
 *    树浏览器（专家下拉←expertsApi.list；用户手输/默认 anonymous→左侧文件树→右侧预览）、
 *    槽状态、手动固化（「立即固化」→ memoryApi.consolidate → 报告浮层）、台账流水。
 *  ②「Hub 总览」③「L1 工作台」④「L2 工作台」⑤「L3 工作台」⑥「记忆图谱」——
 *    复刻自 DeepTutor 原仓 app/(utility)/memory/ 8 薄壳 + components/memory/ 六件（组内私有
 *    落位于 ./memory/），原 Next.js 多路由壳的 deep-link 契约转为 tab 内 state 语义：
 *
 *    deep-link 契约转译（useSearchParams 读参驱动初始 tab/焦点，URL 只驱动初始 state）：
 *      ?ref=notebook:3a563e6f 或 ?surface=notebook&ref=3a563e6f / ?surface=notebook
 *        → 切「L1 工作台」并传 initialSurface/initialFocusRef（原 l1/page.tsx 解析逻辑逐字）；
 *      ?layer=l2&key=notebook&focus=m_xxx → 切「L2 工作台」传 initialKey/initialFocus
 *        （原 /memory/l2/[surface]?focus= 契约；key 非法时按原 notFound() 语义忽略深链落默认 tab）；
 *      ?layer=l3&key=profile&focus=m_xxx → 切「L3 工作台」同上（原 /memory/l3/[slot] 契约）；
 *      ?id=m_xxx → 切「解析定位」并自动执行 resolve（原 /memory/resolve?id= 契约）。
 *      组件内 Link/router.replace 的原路径形状（"/memory/l2"、"/memory/l2/{key}"、
 *      "/memory/l1?ref=..."、"/memory/resolve?id=..."、"/memory/graph"、"/memory"）
 *      经 onNavigate 回调传入本页 navigateMemory 统一映射为 tab 切换。
 *
 *  ⑦「解析定位」——原 resolve/page.tsx 语义内嵌：输入 m_<ULID> →
 *    GET /api/v1/memory/resolve_entry/{id} → 成功切到对应 L2/L3 tab 并定位 focus 条目；
 *    失败中文文案逐字（404/其它/异常/缺参）；「返回记忆」按钮切回 Hub。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button, Card, Col, Empty, Input, message, Modal, Row, Select, Space, Spin, Table, Tabs, Tag, Tree, Typography } from 'antd';
import { FileTextOutlined, FolderOutlined, ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { PageShell } from '../components/shell';
import { expertsApi, memoryApi } from '../services/api';
import { MemoryHub } from './memory/MemoryHub';
import { MemoryL1Workbench } from './memory/MemoryL1Workbench';
import { MemoryWorkbench } from './memory/MemoryWorkbench';
import { MemoryGraph } from './memory/MemoryGraph';
import { t } from './memory/zhT';

// ── deep-link 契约常量（与原仓薄壳逐字一致）──────────────────────────

type Surface =
  | 'chat'
  | 'notebook'
  | 'quiz'
  | 'kb'
  | 'book'
  | 'partner'
  | 'cowriter';

const VALID_SURFACES: ReadonlySet<string> = new Set([
  'chat',
  'notebook',
  'quiz',
  'kb',
  'book',
  'partner',
  'cowriter',
]);

const L2_SURFACES = ['chat', 'notebook', 'quiz', 'kb', 'book', 'partner', 'cowriter'];
const L3_SLOTS = ['recent', 'profile', 'scope'];

// 原 l1/page.tsx 的 ?ref= / ?surface= 解析逻辑逐字：
//   ``?ref=notebook:3a563e6f`` or ``?surface=notebook&ref=3a563e6f``.
function parseL1Link(
  rawRef: string | null,
  rawSurface: string | null,
): { surface?: Surface; focusRef?: string } {
  let surface: Surface | undefined;
  let focusRef: string | undefined;
  if (rawRef) {
    if (rawRef.includes(':')) {
      const [pfx, rest] = rawRef.split(':', 2);
      if (pfx && VALID_SURFACES.has(pfx)) {
        surface = pfx as Surface;
        focusRef = `${pfx}:${rest}`;
      }
    } else if (rawSurface && VALID_SURFACES.has(rawSurface)) {
      surface = rawSurface as Surface;
      focusRef = `${rawSurface}:${rawRef}`;
    }
  } else if (rawSurface && VALID_SURFACES.has(rawSurface)) {
    surface = rawSurface as Surface;
  }
  return { surface, focusRef };
}

interface DeepLink {
  tab: string;
  l1?: { surface?: Surface; focusRef?: string };
  l2?: { key?: string; focus?: string };
  l3?: { key?: string; focus?: string };
  resolveId?: string;
}

function parseDeepLink(params: URLSearchParams): DeepLink {
  const id = params.get('id');
  if (id) return { tab: 'resolve', resolveId: id };
  const layer = params.get('layer');
  const key = params.get('key');
  const focus = params.get('focus') || undefined;
  if (layer === 'l2' && key && L2_SURFACES.includes(key)) {
    // 原 l2/[surface] 契约：``?focus=m_xxx`` — scroll the matching bullet into view + flash it.
    return { tab: 'l2', l2: { key, focus } };
  }
  if (layer === 'l3' && key && L3_SLOTS.includes(key)) {
    // 原 l3/[slot] 契约：focus 参数为对称性而透传。
    return { tab: 'l3', l3: { key, focus } };
  }
  // 原 l1/page.tsx 契约（?ref= / ?surface=）。
  const l1 = parseL1Link(params.get('ref'), params.get('surface'));
  if (l1.surface || l1.focusRef) return { tab: 'l1', l1 };
  return { tab: 'tree' };
}

// ── 解析定位（原 resolve/page.tsx 语义内嵌）──────────────────────────

interface ResolveResponse {
  layer: string;
  key: string;
  entry_id: string;
}

const ResolveTab: React.FC<{
  autoId?: string;
  onResolved: (layer: string, key: string, entryId: string) => void;
  onBack: () => void;
}> = ({ autoId, onResolved, onBack }) => {
  const [input, setInput] = useState<string>(autoId || '');
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);
  const autoConsumed = React.useRef<string | null>(null);

  const runResolve = useCallback(async (id: string) => {
    if (!id) return;
    setResolving(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/memory/resolve_entry/${encodeURIComponent(id)}`);
      if (!res.ok) {
        setError(
          res.status === 404
            ? t(
                'Entry {{id}} not found in any L2 doc — it may have been deleted.',
                { id },
              )
            : t('Resolver failed ({{code}})', { code: res.status }),
        );
        return;
      }
      const data = (await res.json()) as ResolveResponse;
      onResolved(data.layer, data.key, data.entry_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('Resolver failed'));
    } finally {
      setResolving(false);
    }
  }, [onResolved]);

  // 原 ?id= 深链自动触发（一次）。
  useEffect(() => {
    if (!autoId) return;
    if (autoConsumed.current === autoId) return;
    autoConsumed.current = autoId;
    setInput(autoId);
    void runResolve(autoId);
  }, [autoId, runResolve]);

  const message_ = error;

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: 420, padding: '40px 24px' }}>
      <div style={{ maxWidth: 448, display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'center', fontSize: 13, width: '100%' }}>
        {message_ ? (
          <>
            <p style={{ color: 'var(--foreground, rgba(0,0,0,0.88))', margin: 0 }}>{message_}</p>
            <div>
              <Button
                size="small"
                onClick={onBack}
                style={{ fontSize: 12 }}
              >
                {t('Back to memory')}
              </Button>
            </div>
          </>
        ) : resolving ? (
          <Space style={{ justifyContent: 'center', color: 'var(--muted-foreground, rgba(0,0,0,0.45))' }}>
            <Spin size="small" />
            <span>{t('Resolving entry…')}</span>
          </Space>
        ) : (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              输入 L3 引文条目 id（m_&lt;ULID&gt;），解析其所属 L2/L3 文档并定位。
            </Typography.Text>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="m_01HZK…"
                onPressEnter={() => void runResolve(input.trim())}
              />
              <Button type="primary" onClick={() => void runResolve(input.trim())} disabled={!input.trim()}>
                解析
              </Button>
            </Space.Compact>
          </>
        )}
      </div>
    </div>
  );
};

// ── 主组件 ──────────────────────────────────────────────────────────

const MemoryAdmin: React.FC = () => {
  // ── tab 与 deep-link state ──
  const [searchParams] = useSearchParams();
  const deepLink = useMemo(() => parseDeepLink(searchParams), [searchParams]);
  const [activeTab, setActiveTab] = useState<string>(deepLink.tab);
  const [l1Link, setL1Link] = useState<{ surface?: Surface; focusRef?: string } | undefined>(deepLink.l1);
  const [l2Key, setL2Key] = useState<string | undefined>(deepLink.l2?.key);
  const [l2Focus, setL2Focus] = useState<string | undefined>(deepLink.l2?.focus);
  const [l3Key, setL3Key] = useState<string | undefined>(deepLink.l3?.key);
  const [l3Focus, setL3Focus] = useState<string | undefined>(deepLink.l3?.focus);
  const [resolveAutoId, setResolveAutoId] = useState<string | undefined>(deepLink.resolveId);

  // ── 原 178 行能力（树与固化）state：原样保留 ──
  const [experts, setExperts] = useState<{ expert_id: string; name: string }[]>([]);
  const [expertId, setExpertId] = useState<string>('wenshu');
  const [user, setUser] = useState<string>('anonymous');
  const [treeItems, setTreeItems] = useState<any[]>([]);
  const [preview, setPreview] = useState<{ path: string; content: string } | null>(null);
  const [report, setReport] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [consolidating, setConsolidating] = useState<boolean>(false);
  const [treeRoot, setTreeRoot] = useState<string>('user');

  const loadTree = useCallback(async () => {
    if (!expertId || !user) return;
    setLoading(true);
    try {
      const r = await memoryApi.tree({ expert_id: expertId, user, root: treeRoot } as any);
      setTreeItems(r.data?.items || []);
    } catch {
      setTreeItems([]);
    } finally {
      setLoading(false);
    }
  }, [expertId, user, treeRoot]);

  const loadEvents = useCallback(async () => {
    try {
      const r = await memoryApi.events({ expert_id: expertId });
      setEvents(r.data?.items || []);
    } catch {
      setEvents([]);
    }
  }, [expertId]);

  useEffect(() => { (async () => {
    try {
      const r = await expertsApi.list();
      setExperts((r.data?.items || []).map((x: any) => ({ expert_id: x.expert_id, name: x.name })));
    } catch { /* 列表失败不阻页面（可手输 expert） */ }
  })(); }, []);

  useEffect(() => { loadTree(); loadEvents(); }, [loadTree, loadEvents]);

  const buildTreeData = () => {
    // 平铺 items → antd Tree（目录树两级结构足够——记忆树按 flat 相对路径展示）
    const dirs: Record<string, any[]> = {};
    for (const it of treeItems) {
      const parts = it.path.replace(/^\/memory\//, '').split('/');
      const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '/';
      (dirs[dir] = dirs[dir] || []).push(it);
    }
    return Object.entries(dirs).map(([dir, items]) => ({
      title: dir === '/' ? '/memory/' : `/memory/${dir}/`,
      key: `dir:${dir}`,
      icon: <FolderOutlined />,
      selectable: false,
      children: items.map((it) => ({
        title: `${it.path.replace(/^\/memory\//, '').split('/').pop()}${it.is_dir ? '/' : ''} (${it.size}B)`,
        key: it.path,
        icon: it.is_dir ? <FolderOutlined /> : <FileTextOutlined />,
        isLeaf: !it.is_dir,
      })),
    }));
  };

  const onPreview = async (key: string) => {
    if (!key.startsWith('/memory/') || key.endsWith('/')) return;
    try {
      const r = await memoryApi.file({ expert_id: expertId, user, path: key, root: treeRoot } as any);
      setPreview({ path: key, content: r.data?.content || '' });
    } catch {
      message.error('读取失败');
    }
  };

  const onConsolidate = async () => {
    setConsolidating(true);
    try {
      const r = await memoryApi.consolidate({ expert_id: expertId, user });
      setReport(r.data);
      loadEvents();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '固化失败');
    } finally {
      setConsolidating(false);
    }
  };

  // ── 壳语义转译：原路径形状 → tab 切换（deep-link 契约见文件头注）──
  const handleResolved = useCallback((layer: string, key: string, entryId: string) => {
    const layerPath = layer.toLowerCase();
    if (layerPath === 'l2') {
      setL2Key(key);
      setL2Focus(entryId);
      setActiveTab('l2');
    } else if (layerPath === 'l3') {
      setL3Key(key);
      setL3Focus(entryId);
      setActiveTab('l3');
    } else {
      message.warning(t('Resolver failed'));
    }
  }, []);

  const navigateMemory = useCallback((path: string) => {
    const [pathname, query] = path.split('?');
    const params = new URLSearchParams(query || '');
    if (pathname === '/memory' || pathname === '') {
      setActiveTab('hub');
      return;
    }
    if (pathname === '/memory/graph') {
      setActiveTab('graph');
      return;
    }
    if (pathname === '/memory/resolve') {
      const id = params.get('id') || '';
      setResolveAutoId(id || undefined);
      setActiveTab('resolve');
      return;
    }
    if (pathname === '/memory/l1') {
      const l1 = parseL1Link(params.get('ref'), params.get('surface'));
      if (l1.surface || l1.focusRef) setL1Link(l1);
      setActiveTab('l1');
      return;
    }
    if (pathname.startsWith('/memory/l2')) {
      const key = pathname.slice('/memory/l2/'.length) || undefined;
      if (key && L2_SURFACES.includes(key)) setL2Key(key);
      const focus = params.get('focus') || undefined;
      if (focus) setL2Focus(focus);
      setActiveTab('l2');
      return;
    }
    if (pathname.startsWith('/memory/l3')) {
      const key = pathname.slice('/memory/l3/'.length) || undefined;
      if (key && L3_SLOTS.includes(key)) setL3Key(key);
      const focus = params.get('focus') || undefined;
      if (focus) setL3Focus(focus);
      setActiveTab('l3');
      return;
    }
    // 其余原仓内部路径（/settings/memory 等）tupu 无对应 tab——维持原状。
  }, []);

  const tabItems = [
    {
      key: 'tree',
      label: '树与固化',
      children: (
        <>
          <Card size="small" style={{ marginBottom: 12 }}>
            <Space wrap>
              <span>专家：</span>
              <Select style={{ width: 180 }} value={expertId} onChange={setExpertId}
                options={experts.map((e) => ({ value: e.expert_id, label: `${e.name} (${e.expert_id})` }))}
                showSearch optionFilterProp="label" />
              <span>用户：</span>
              <Select style={{ width: 150 }} value={user} onChange={setUser}
                options={['anonymous', 'admin'].map((u) => ({ value: u, label: u }))} showSearch />
              <span>根：</span>
              <Select style={{ width: 120 }} value={treeRoot} onChange={setTreeRoot}
                options={[{ value: 'user', label: '用户树' }, { value: 'expert', label: '专家根' }]} />
              <Button icon={<ReloadOutlined />} onClick={() => { loadTree(); loadEvents(); }}>刷新</Button>
              <Button type="primary" icon={<ThunderboltOutlined />} loading={consolidating} onClick={onConsolidate}>
                立即固化
              </Button>
              <Tag color="blue">树条目: {treeItems.length}</Tag>
            </Space>
          </Card>

          <Row gutter={12}>
            <Col span={10}>
              <Card size="small" title="记忆树（/memory/）">
                {treeItems.length === 0 ? (
                  <Empty description="该树暂无记忆文件（对话产生 L1 后出现）" />
                ) : (
                  <Tree showIcon treeData={buildTreeData()} onSelect={(keys) => keys.length && onPreview(String(keys[0]))} height={420} />
                )}
              </Card>
            </Col>
            <Col span={14}>
              <Card size="small" title={preview ? `预览：${preview.path}` : '文件预览'}>
                {preview ? (
                  <pre style={{ maxHeight: 420, overflow: 'auto', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}>{preview.content}</pre>
                ) : (
                  <Empty description="左侧选择文件查看内容" />
                )}
              </Card>
            </Col>
          </Row>

          <Card size="small" title="台账流水（memory_write / memory_consolidated）" style={{ marginTop: 12 }}>
            <Table
              size="small" rowKey={(r) => `${r.ts}-${r.kind}-${Math.random()}`}
              dataSource={events}
              columns={[
                { title: '时间', dataIndex: 'ts', width: 190 },
                { title: '专家', dataIndex: 'expert_id', width: 100 },
                { title: '类型', dataIndex: 'kind', width: 170,
                  render: (k: string) => <Tag color={k === 'memory_write' ? 'green' : 'purple'}>{k}</Tag> },
                { title: '明细', dataIndex: 'detail',
                  render: (d: any) => <Typography.Text code style={{ fontSize: 11 }}>{JSON.stringify(d)}</Typography.Text> },
              ]}
              pagination={{ pageSize: 8 }}
            />
          </Card>

          <Modal open={!!report} title="固化报告" onCancel={() => setReport(null)} footer={null}>
            {report ? (
              <div>
                <p><b>读入 L1 行数：</b>{report.read_lines}</p>
                <p><b>L2 写入：</b>{report.l2_written} · <b>L3 写入：</b>{report.l3_written}</p>
                <p><b>对冲审计：</b>画像 {report.audit?.total ?? 0} 条，其中对冲句式 {report.audit?.hedged ?? 0} 条</p>
                <p><b>耗时：</b>{report.elapsed_ms} ms</p>
                {(report.audit?.total ?? 0) > 0 && (report.audit?.hedged ?? 0) < (report.audit?.total ?? 0) && (
                  <p style={{ color: '#cf1322' }}>存在未对冲句式的画像条目（{report.audit.total - report.audit.hedged} 条）——检查 L3 文件质量。</p>
                )}
              </div>
            ) : null}
          </Modal>
        </>
      ),
    },
    {
      key: 'hub',
      label: 'Hub 总览',
      children: (
        // 原 memory/page.tsx 壳包装 1:1（max-w-6xl 容器 + 滚动）
        <div style={{ height: '100%', overflowY: 'auto', scrollbarGutter: 'stable' }}>
          <div style={{ maxWidth: 1152, margin: '0 auto', padding: '40px 24px 64px' }}>
            <MemoryHub onNavigate={navigateMemory} />
          </div>
        </div>
      ),
    },
    {
      key: 'l1',
      label: 'L1 工作台',
      children: (
        // 原 l1/page.tsx 壳：deep-link 契约经 l1Link state 传入
        <div style={{ height: 640 }}>
          <MemoryL1Workbench
            initialSurface={l1Link?.surface}
            initialFocusRef={l1Link?.focusRef}
            onNavigate={navigateMemory}
          />
        </div>
      ),
    },
    {
      key: 'l2',
      label: 'L2 工作台',
      children: (
        // 原 l2/page.tsx + l2/[surface] 壳：initialKey/initialFocus 转为 tab 内 state
        <div style={{ height: 640 }}>
          <MemoryWorkbench layer="L2" initialKey={l2Key} initialFocus={l2Focus} onNavigate={navigateMemory} />
        </div>
      ),
    },
    {
      key: 'l3',
      label: 'L3 工作台',
      children: (
        // 原 l3/page.tsx + l3/[slot] 壳
        <div style={{ height: 640 }}>
          <MemoryWorkbench layer="L3" initialKey={l3Key} initialFocus={l3Focus} onNavigate={navigateMemory} />
        </div>
      ),
    },
    {
      key: 'graph',
      label: '记忆图谱',
      children: (
        // 原 graph/page.tsx 壳：<MemoryGraph /> 直接渲染
        <div style={{ height: 640 }}>
          <MemoryGraph onNavigate={navigateMemory} />
        </div>
      ),
    },
    {
      key: 'resolve',
      label: '解析定位',
      children: (
        <ResolveTab
          autoId={resolveAutoId}
          onResolved={handleResolved}
          onBack={() => setActiveTab('hub')}
        />
      ),
    },
  ];

  return (
    <PageShell title="记忆管理" description="三层记忆树浏览 · 手动固化 · 台账 · DeepTutor 记忆分层视图（admin-only）">
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </PageShell>
  );
};

export default MemoryAdmin;
