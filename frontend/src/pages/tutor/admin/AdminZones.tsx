/**
 * 附件四 A-3 步骤 2：tutor 后台四区——题库/学情看板/教材/复习调度。
 * questions 消费 C 补-1 /api/tutor-admin/questions CRUD；progress 消费 A-3 /progress；
 * materials 直调④既有端点（零新后端——视图归专家）；schedule 消费 /schedule GET/PUT。
 * 挂在 AdminHome 底部（Tabs）——A-2 配置表单零改动零回归。
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Button, Card, Descriptions, Form, Input, InputNumber, Modal, Space, Steps, Table, Tabs, Tag, message,
} from 'antd';
import { useNavigate } from 'react-router-dom';

interface Mq { mq_id: string; title: string; archetype_text: string; knowledge_point_id: string; enabled: boolean; variant_count?: number }
interface PRow { user_id: string; cards: number; due_now: number; mastery: { knowledge_point_id: string; retention: number }[] }
interface Sched { defaults: { desired_retention: number; w: number[] }; overrides: Record<string, any>; effective: { desired_retention: number; w: number[] } }
interface KbRow { kb_id?: string; id?: string; name?: string; title?: string }

const retentionColor = (r: number) => (r >= 0.7 ? 'green' : r >= 0.4 ? 'orange' : 'red');

/* ── 区一：题库（C 补-1 CRUD 消费）── */
const QuestionsZone: React.FC = () => {
  const [items, setItems] = useState<Mq[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState<{ open: boolean; editing?: Mq }>({ open: false });
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/tutor-admin/questions?limit=200');
      const j = await r.json();
      setItems(j?.data?.items || []);
    } catch { message.error('题库获取失败'); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    const v = await form.validateFields();
    const editing = modal.editing;
    const r = await fetch(editing ? `/api/tutor-admin/questions/${editing.mq_id}` : '/api/tutor-admin/questions', {
      method: editing ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(v),
    });
    const j = await r.json().catch(() => ({}));
    if (r.status !== 200) { message.error(j?.detail || '保存失败'); return; }
    message.success(editing ? '已更新' : '已创建');
    setModal({ open: false });
    form.resetFields();
    load();
  };

  const del = async (mq: Mq) => {
    const r = await fetch(`/api/tutor-admin/questions/${mq.mq_id}`, { method: 'DELETE' });
    if (r.status === 200) { message.success('已删除'); load(); } else { message.error('删除失败'); }
  };

  return (
    <div>
      <Button type="primary" style={{ marginBottom: 12 }} onClick={() => { setModal({ open: true }); form.resetFields(); }}>新建母题</Button>
      <Table<Mq>
        rowKey="mq_id" size="small" loading={loading} dataSource={items}
        pagination={{ pageSize: 8 }}
        columns={[
          { title: '题面', dataIndex: 'title', ellipsis: true },
          { title: '知识点', dataIndex: 'knowledge_point_id', width: 180, ellipsis: true },
          { title: '变式数', dataIndex: 'variant_count', width: 80 },
          { title: '启用', dataIndex: 'enabled', width: 70, render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '是' : '否'}</Tag> },
          {
            title: '操作', width: 130,
            render: (_: any, rec: Mq) => (
              <Space>
                <Button size="small" onClick={() => { setModal({ open: true, editing: rec }); form.setFieldsValue(rec); }}>编辑</Button>
                <Button size="small" danger onClick={() => del(rec)}>删</Button>
              </Space>
            ),
          },
        ]}
      />
      <Modal
        title={modal.editing ? '编辑母题' : '新建母题'} open={modal.open} onOk={save}
        onCancel={() => setModal({ open: false })} okText="保存" destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="母题标题" rules={[{ required: true, message: '必填' }]}>
            <Input placeholder="如：有理数分类母题" />
          </Form.Item>
          <Form.Item name="archetype_text" label="题干原型" rules={[{ required: true, message: '必填' }]}>
            <Input.TextArea rows={3} placeholder="母题题干（变式由此派生）" />
          </Form.Item>
          <Form.Item name="knowledge_point_id" label="知识点（图谱节点）" rules={[{ required: true, message: 'kp 必填（D7）' }]}>
            <Input placeholder="kp:…" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

/* ── 区二：学情看板（跨用户——A-3 /progress）── */
const ProgressZone: React.FC = () => {
  const [rows, setRows] = useState<PRow[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const r = await fetch('/api/tutor-admin/progress');
        const j = await r.json();
        setRows(j?.data?.items || []);
      } catch { message.error('学情看板获取失败'); } finally { setLoading(false); }
    })();
  }, []);
  return (
    <Table<PRow>
      rowKey="user_id" size="small" loading={loading} dataSource={rows}
      pagination={false}
      expandable={{
        expandedRowRender: (rec) => (
          <Space size={6} wrap>
            {(rec.mastery || []).map((m) => (
              <Tag key={m.knowledge_point_id} color={retentionColor(m.retention)}>
                {m.knowledge_point_id} · {Math.round(m.retention * 100)}%
              </Tag>
            ))}
            {(rec.mastery || []).length === 0 && <span style={{ color: 'var(--text-tertiary)' }}>暂无掌握度数据</span>}
          </Space>
        ),
      }}
      columns={[
        { title: '用户', dataIndex: 'user_id' },
        { title: '复习卡', dataIndex: 'cards', width: 100 },
        { title: '当前到期', dataIndex: 'due_now', width: 110, render: (v: number) => <Tag color={v > 0 ? 'red' : 'green'}>{v}</Tag> },
        { title: '薄弱点 Top5', width: 240, render: (_: any, rec: PRow) => <span>{(rec.mastery || []).length} 个知识点（展开看明细）</span> },
      ]}
    />
  );
};

/* ── 区三：教材（直调④既有端点——卡 kb:{id} 绑定视图，零新后端）── */
const MaterialsZone: React.FC = () => {
  const navigate = useNavigate();
  const [kbs, setKbs] = useState<KbRow[]>([]);
  const [card, setCard] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const cr = await fetch('/api/experts/tutor');
        setCard((await cr.json())?.data || {});
        const r = await fetch('/api/v1/knowledge-bases');
        const j = await r.json();
        const arr = Array.isArray(j?.data) ? j.data : j?.data?.items || [];
        setKbs(arr);
      } catch { /* ④端点不可达静默 */ } finally { setLoading(false); }
    })();
  }, []);
  const bound: string[] = (card?.knowledge_sources || []).map((s: string) => s.replace(/^kb:/, ''));
  return (
    <div>
      <div style={{ marginBottom: 10 }}>
        卡绑定知识源：<Space size={6} wrap>
          {bound.length === 0 && <span style={{ color: 'var(--text-tertiary)' }}>未绑定（在「专家配置」勾选）</span>}
          {bound.map((id) => <Tag key={id} color="blue">kb:{id}</Tag>)}
        </Space>
      </div>
      <Table<KbRow>
        rowKey={(r) => String(r.kb_id || r.id || r.name)} size="small" loading={loading} dataSource={kbs}
        pagination={{ pageSize: 8 }}
        columns={[
          { title: '知识库', render: (_: any, r: KbRow) => r.name || r.title || r.kb_id || r.id },
          { title: 'ID', width: 260, render: (_: any, r: KbRow) => String(r.kb_id || r.id || '') },
        ]}
        locale={{ emptyText: '④ 知识库列表不可达或为空' }}
      />
      <Button style={{ marginTop: 10 }} onClick={() => navigate('/knowledge')}>前往④知识库管理（上传/向量化）</Button>
    </div>
  );
};

/* ── 区四：复习调度（/schedule GET/PUT）── */
const ScheduleZone: React.FC = () => {
  const [sched, setSched] = useState<Sched | null>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/tutor-admin/schedule');
      const j = await r.json();
      setSched(j?.data || null);
      if (j?.data?.overrides?.desired_retention) form.setFieldsValue({ desired_retention: j.data.overrides.desired_retention });
    } catch { message.error('调度参数获取失败'); } finally { setLoading(false); }
  }, [form]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    const v = await form.validateFields();
    const body: Record<string, any> = {};
    if (v.desired_retention != null) body.desired_retention = v.desired_retention / 100;
    const r = await fetch('/api/tutor-admin/schedule', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    const j = await r.json().catch(() => ({}));
    if (r.status !== 200) { message.error(j?.detail || '覆写失败'); return; }
    message.success('已覆写（写回 tutor 卡 params.fsrs——version+1）');
    load();
  };

  if (loading || !sched) return <span style={{ color: 'var(--text-tertiary)' }}>加载中…</span>;
  return (
    <div style={{ maxWidth: 720 }}>
      <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
        <Descriptions.Item label="生效目标保持率">
          <Tag color="blue">{Math.round(sched.effective.desired_retention * 100)}%</Tag>
          {sched.overrides.desired_retention
            ? <span>（卡覆写）</span>
            : <span style={{ color: 'var(--text-tertiary)' }}>（默认 0.9）</span>}
        </Descriptions.Item>
        <Descriptions.Item label="生效权重 w">{sched.overrides.w ? <Tag color="blue">卡覆写 {sched.overrides.w.length} 个</Tag> : <span style={{ color: 'var(--text-tertiary)' }}>默认 FSRS-5（19 个）</span>}</Descriptions.Item>
      </Descriptions>
      <Form form={form} layout="inline" onFinish={save}>
        <Form.Item name="desired_retention" label="目标保持率 %（0.5~0.99）">
          <InputNumber min={50} max={99} placeholder="留空=不覆写" style={{ width: 160 }} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">覆写</Button>
        </Form.Item>
      </Form>
      <div style={{ marginTop: 10, color: 'var(--text-tertiary)', fontSize: 12 }}>
        w 权重覆写走 PUT /api/tutor-admin/schedule（19 个 FSRS-5 权重）——界面保留 desired_retention 常用面，算法体零改动。
      </div>
    </div>
  );
};

const AdminZones: React.FC = () => (
  <Card title="后台四区（题库 / 学情看板 / 教材 / 复习调度）" style={{ margin: 16, borderRadius: 12 }}>
    <Steps
      size="small" current={-1} style={{ marginBottom: 4 }}
      items={[{ title: '题库' }, { title: '学情看板' }, { title: '教材' }, { title: '复习调度' }]}
    />
    <Tabs
      items={[
        { key: 'questions', label: '题库', children: <QuestionsZone /> },
        { key: 'progress', label: '学情看板', children: <ProgressZone /> },
        { key: 'materials', label: '教材', children: <MaterialsZone /> },
        { key: 'schedule', label: '复习调度', children: <ScheduleZone /> },
      ]}
    />
  </Card>
);

export default AdminZones;
