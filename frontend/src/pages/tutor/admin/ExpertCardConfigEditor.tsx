/**
 * ⑤R 批8 F1（8.2）：专家卡配置编辑面——自 AdminHome（附件四 A-2 成果）原样搬移为共享件：
 * settings/curriculum「专家卡配置」tab 与 tutor 后台首页共用（§10.2 双入口，零新逻辑）。
 * 写路径=①CRUD（expertsApi.update）；前端只预检，合法性由①校验兜底（422 上屏）。
 * 槽配置只读总览（编辑走②管理面，不重复造）。
 */
import React, { useContext, useEffect, useState } from 'react';
import {
  Button, Card, Checkbox, Form, Input, Modal, Select, Space, Switch, Tag, Typography, message,
} from 'antd';
import { expertsApi, llmAdminApi, knowledgeBaseApi } from '../../../services/api';
import type { ExpertCard } from '../../../services/api';
import { AuthCtx } from '../../../auth/AuthGate';

const { Text } = Typography;

const ExpertCardConfigEditor: React.FC = () => {
  const { user } = useContext(AuthCtx);
  const isAdminUser = (((user as any)?.roles || []) as string[]).includes('admin');
  const [card, setCard] = useState<ExpertCard | null>(null);
  const [connections, setConnections] = useState<any[]>([]);
  const [kbs, setKbs] = useState<any[]>([]);
  const [toolUniverse, setToolUniverse] = useState<string[]>([]);
  const [enabled, setEnabled] = useState(false);
  const [connId, setConnId] = useState<string | undefined>(undefined);
  const [tools, setTools] = useState<string[]>([]);
  const [ksGraph, setKsGraph] = useState(true);
  const [ksKbs, setKsKbs] = useState<string[]>([]);
  const [otherKs, setOtherKs] = useState<string[]>([]);  // R1批(:106)：未建模知识源类型保真
  const [suggs, setSuggs] = useState<string[]>([]);
  const [slots, setSlots] = useState<any[]>([]);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);
  const [closeReason, setCloseReason] = useState('');

  const load = async () => {
    try {
      const res = await expertsApi.get('sishu');
      const c = (res.data as ExpertCard) || null;
      setCard(c);
      if (c) {
        setEnabled(!!c.enabled);
        setConnId(c.llm_connection_id || undefined);
        setTools(c.tools || []);
        const ks = c.knowledge_sources || [];
        setKsGraph(ks.includes('ontology_graph'));
        setKsKbs(ks.filter((k) => k.startsWith('kb:')));
        // R1批(:106)：保留未建模类型（未来新增 knowledge_sources 类型不再被保存静默删除）
        setOtherKs(ks.filter((k) => k !== 'ontology_graph' && !k.startsWith('kb:')));
        setSuggs(c.suggestions || []);
        const mem: any = c.memory;
        setSlots(Array.isArray(mem) ? [] : (mem?.slots || []));
      }
    } catch {
      // 读取失败不可静默——card=null 时 onSaveCore 全部 diff 跳过=静默丢数据（R0 重放批修复）
      setLoadFailed(true);
    }
  };

  useEffect(() => {
    if (!isAdminUser) return;
    let cancelled = false;  // R1批(:54)：取消守卫——卸载/切换后慢响应不再 setState（防旧响应覆盖新数据）
    (async () => {
      await load();
      if (cancelled) return;
      try {
        const c = await llmAdminApi.getConnections();
        if (cancelled) return;
        const raw: any = c.data;
        const arr = Array.isArray(raw) ? raw : (raw?.items || raw?.connections || raw?.data || []);
        setConnections(Array.isArray(arr) ? arr : []);
      } catch { /* 连接列表失败不阻卡编辑 */ }
      if (cancelled) return;
      try {
        const k = await knowledgeBaseApi.list();
        if (cancelled) return;
        const raw: any = k.data;
        const arr = Array.isArray(raw) ? raw : (raw?.items || raw?.knowledge_bases || raw?.data || []);
        setKbs(Array.isArray(arr) ? arr : []);
      } catch { /* KB 列表失败不阻卡编辑 */ }
    })();
    return () => { cancelled = true; };
  }, [isAdminUser]);

  // 工具选项=活注册表实测清单（manifest 端点 tool_universe——装配期静态注册全集）
  useEffect(() => {
    if (!isAdminUser) return;
    (async () => {
      try {
        const r = await fetch('/api/capabilities/manifest');
        if (!r.ok) throw new Error(`manifest ${r.status}`);  // R1批(:75)：非 2xx 不再盲 json
        const j = await r.json();
        setToolUniverse(j.tool_universe || []);
      } catch { /* manifest 失败则多选框空——提交仍由①校验兜底 */ }
    })();
  }, [isAdminUser]);

  if (!isAdminUser) return null;

  const patch = async (fields: Record<string, unknown>) => {
    setSaving(true);
    try {
      const r = await expertsApi.update('sishu', fields);
      message.success(`已保存（version ${r.data?.version ?? '?'})`);
      await load();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '保存失败';
      message.error(`422/错误：${detail}`);          // ①校验兜底上屏
    } finally {
      setSaving(false);
    }
  };

  const onSaveCore = () => {
    if (!card) {
      message.error('卡未加载（读取失败）——保存已阻止，防止空基线静默丢数据');
      return;
    }
    const fields: Record<string, unknown> = {};
    if (card && JSON.stringify(card.tools || []) !== JSON.stringify(tools)) {
      fields.tools = tools;
    }
    const ks = [
      ...(ksGraph ? ['ontology_graph'] : []),
      ...ksKbs,
      ...otherKs,  // R1批(:106)：未建模类型原样带回（防保存即删）
    ];
    if (card && JSON.stringify(card.knowledge_sources || []) !== JSON.stringify(ks)) {
      fields.knowledge_sources = ks;
    }
    if (card && JSON.stringify(card.suggestions || []) !== JSON.stringify(suggs.filter((s) => s.trim()))) {
      fields.suggestions = suggs.filter((s) => s.trim());
    }
    // R0 重放批（清单:101）：llm_connection_id 纳入 diff——原实现只 setConnId 本地态，
    // 保存不含该字段=改选连接被静默丢弃；null 归一（①校验空值约定）
    const connNorm = connId || null;
    if (card && (card.llm_connection_id || null) !== connNorm) {
      fields.llm_connection_id = connNorm;
    }
    if (Object.keys(fields).length === 0) {
      message.info('无变更');
      return;
    }
    patch(fields);
  };

  const onEnabledChange = async (v: boolean) => {
    if (v === enabled) return;
    if (!v) {
      setCloseOpen(true);                              // 红级关闭需 close_reason（①校验）
      return;
    }
    // R1批(:129)：先落库成功再同步本地态（乐观写失败=UI 与服务端状态脱节）
    await patch({ enabled: true });
  };

  const confirmClose = async () => {
    if (closeReason.trim().length < 10) {
      message.warning('关停理由至少 10 字（①红级校验）');
      return;
    }
    // R1批(:138)：await patch + saving 守卫（双击=两次无效关停写）；成功后才清理本地态
    setCloseOpen(false);
    await patch({ enabled: false, close_reason: closeReason.trim() });
    setCloseReason('');
  };

  return (
    <div style={{ maxWidth: 880, margin: '0 auto' }}>
      <Card
        title={(
          <Space>
            <span>专家卡配置（编辑面）</span>
            {card && <Tag color="blue">version {card.version}</Tag>}
            <Tag color={enabled ? 'green' : 'red'}>{enabled ? '启用' : '关停'}</Tag>
          </Space>
        )}
        style={{ borderRadius: 12 }}
      >
        <Form layout="vertical">
          <Form.Item label="enabled（卡开关——关闭=面不可用，红级需理由）">
            <Switch checked={enabled} onChange={onEnabledChange} loading={saving} />
          </Form.Item>
          <Form.Item label="llm_connection_id（③连接列表；缺省=平台默认）">
            <Select
              allowClear
              placeholder="平台默认"
              style={{ maxWidth: 420 }}
              value={connId}
              onChange={(v) => setConnId(v)}
              options={(connections || []).map((c: any) => ({
                value: c.id || c.connection_id, label: c.name || c.id || c.connection_id,
              }))}
            />
          </Form.Item>
          <Form.Item label={`tools（活注册表 ${toolUniverse.length} 件——提交走①校验兜底）`}>
            <Select
              mode="multiple"
              style={{ width: '100%' }}
              value={tools}
              onChange={setTools}
              options={toolUniverse.map((t) => ({ value: t, label: t }))}
            />
          </Form.Item>
          <Form.Item label="knowledge_sources（ontology_graph + kb:{id}）">
            <Space direction="vertical" size={6}>
              <Checkbox
                checked={ksGraph}
                onChange={(e) => setKsGraph(e.target.checked)}
              >
                ontology_graph（图谱知识源）
              </Checkbox>
              <Select
                mode="multiple"
                allowClear
                placeholder="选择文档知识库（④ KB 列表）"
                style={{ minWidth: 380 }}
                value={ksKbs}
                onChange={setKsKbs}
                options={(kbs || []).map((k: any) => ({
                  value: `kb:${k.id}`, label: k.name || k.id,
                }))}
              />
            </Space>
          </Form.Item>
          <Form.Item label={`suggestions（卡级建议 ${suggs.length}/5——每条 ≤120 字，门户/欢迎页可点）`}>
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              {suggs.map((s, i) => (
                <Space key={i} style={{ width: '100%' }}>
                  <Input
                    style={{ width: 480 }}
                    value={s}
                    maxLength={120}
                    onChange={(e) => {
                      const next = [...suggs];
                      next[i] = e.target.value;
                      setSuggs(next);
                    }}
                  />
                  <Button
                    danger
                    size="small"
                    onClick={() => setSuggs(suggs.filter((_, j) => j !== i))}
                  >
                    删
                  </Button>
                </Space>
              ))}
              {suggs.length < 5 && (
                <Button size="small" onClick={() => setSuggs([...suggs, ''])}>+ 加一条</Button>
              )}
            </Space>
          </Form.Item>
          <Space>
            <Button type="primary" loading={saving} disabled={!card} title={loadFailed ? "卡读取失败，保存已禁用" : undefined} onClick={onSaveCore}>
              保存卡配置（①CRUD PATCH）
            </Button>
            <Button onClick={load}>重载</Button>
          </Space>
        </Form>
      </Card>

      <Card title="槽配置（只读总览——编辑走②管理面，不重复造）" style={{ borderRadius: 12, marginTop: 16 }}>
        {(slots || []).length > 0 ? (
          <Space wrap>
            {(slots || []).map((s: any, i: number) => (
              <Tag key={i} color="geekblue">
                {s.slot_key || s.key || s.type} · {s.type}
                {s.surface ? ` · ${s.surface}` : ''}
              </Tag>
            ))}
          </Space>
        ) : (
          <Text type="secondary">（卡 memory 为 legacy 列表形状或无槽声明）</Text>
        )}
      </Card>

      <Modal
        title="关停专家卡（红级）"
        open={closeOpen}
        okButtonProps={{ loading: saving, disabled: saving }} onOk={confirmClose}
        onCancel={() => setCloseOpen(false)}
        okText="确认关停"
        cancelText="取消"
      >
        <Text type="secondary">关停=面不可用（①校验：理由至少 10 字）。</Text>
        <Input.TextArea
          rows={3}
          style={{ marginTop: 8 }}
          value={closeReason}
          onChange={(e) => setCloseReason(e.target.value)}
          placeholder="填写关停理由（至少 10 字）"
        />
      </Modal>
    </div>
  );
};

export default ExpertCardConfigEditor;
