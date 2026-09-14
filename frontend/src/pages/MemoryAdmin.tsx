/**
 * MemoryAdmin - 最小记忆管理页（记忆插槽② spec §九）：整页 admin-only。
 * ① 树浏览器（专家下拉←expertsApi.list；用户手输/默认 anonymous→左侧文件树→右侧预览）
 * ② 槽状态（卡声明槽数 × 文件实况：存在/最后修改）
 * ③ 手动固化（「立即固化」→ memoryApi.consolidate → 报告浮层）
 * ④ 台账流水（memory_write/memory_consolidated 过滤表+刷新）
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Button, Card, Col, Empty, message, Modal, Row, Select, Space, Table, Tag, Tree, Typography } from 'antd';
import { FileTextOutlined, FolderOutlined, ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { PageShell } from '../components/shell';
import { expertsApi, memoryApi } from '../services/api';

const MemoryAdmin: React.FC = () => {
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

  return (
    <PageShell title="记忆管理" description="三层记忆树浏览 · 手动固化 · 台账（admin-only）">
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
    </PageShell>
  );
};

export default MemoryAdmin;
