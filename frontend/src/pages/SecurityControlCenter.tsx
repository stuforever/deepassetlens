/**
 * SecurityControlCenter - 安全控制中心（《安全控制中心实施设计》3.3，/security-controls）
 *
 * 六张控制卡（五类+审批轨），每卡：
 *   · 风险 Badge(🔴/🟡/🟢) + title + Switch（PATCH loading 防连点）
 *   · 一行说明（what 截断）+ 展开三段式完整说明（what/lose/remain）
 *   · 统计行：24h 拦截 · 7天 · 最近拦截（StatusTag）
 *   · 按钮组：[试探单] [参数] [拦截记录]
 * 两个 Drawer：参数编辑（按 params 动态渲染）/ 拦截记录表（DataTableShell 分页）
 * 顶栏：[全部恢复默认(Popconfirm)] [导出配置 JSON] 全局版本号 v{n}
 * 关闭确认风险分级：🟢直接切 / 🟡单 Modal / 🔴双 Modal+必填理由(<10字禁止)；开启一律直接切
 * 试探单双向验证：开启时=✓已拦截(控制生效)；关闭后=✗未拦截(证明开关不是摆设)
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert, Badge, Button, Card, Col, Drawer, Form, Input, List, message,
  Modal, Popconfirm, Row, Select, Space, Spin, Switch, Tag, Tooltip, Typography,
} from 'antd';
import {
  PoweroffOutlined, SafetyCertificateOutlined, ExperimentOutlined,
  SettingOutlined, HistoryOutlined, ReloadOutlined, DownloadOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import { guardsApi, type GuardItem, type GuardEventItem, type GuardDescription } from '../services/api';
import { PageShell, StatusTag, DataTableShell, DrawerFooter } from '../components/shell';
import { tokens } from '../theme/tokens';

const { Text, Paragraph } = Typography;

const RISK_META: Record<string, { color: string; label: string }> = {
  red: { color: 'red', label: '高风险' },
  yellow: { color: 'orange', label: '中风险' },
  green: { color: 'green', label: '低风险' },
};

const ACTION_META: Record<string, { label: string; preset: 'success' | 'warning' | 'info' | 'disabled' }> = {
  block: { label: '拦截', preset: 'warning' },
  warn: { label: '告警', preset: 'info' },
  pass: { label: '放行', preset: 'success' },
  probe: { label: '试探', preset: 'info' },
  toggle: { label: '变更', preset: 'info' },
  reset: { label: '重置', preset: 'info' },
};

const SecurityControlCenter: React.FC = () => {
  const [items, setItems] = useState<GuardItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [globalVersion, setGlobalVersion] = useState(0);
  // PATCH 中 guard（防连点）
  const [togglingId, setTogglingId] = useState<string | null>(null);
  // 探针
  const [probingId, setProbingId] = useState<string | null>(null);
  const [probeResult, setProbeResult] = useState<{ guardId: string; ok: boolean; text: string } | null>(null);
  // 关闭确认流程：黄级单 Modal / 红级双 Modal
  const [yellowTarget, setYellowTarget] = useState<GuardItem | null>(null);
  const [redTarget, setRedTarget] = useState<GuardItem | null>(null);
  const [redAck, setRedAck] = useState(false);
  const [redReason, setRedReason] = useState('');
  const [closing, setClosing] = useState(false);
  // Drawer
  const [paramTarget, setParamTarget] = useState<GuardItem | null>(null);
  const [paramForm] = Form.useForm();
  const [paramSaving, setParamSaving] = useState(false);
  const [eventsOpen, setEventsOpen] = useState(false);
  const [eventsGuard, setEventsGuard] = useState<string>('');
  const [eventsItems, setEventsItems] = useState<GuardEventItem[]>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsPage, setEventsPage] = useState(1);
  const eventsSize = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await guardsApi.list();
      const data = res.data;
      setItems(Array.isArray(data.items) ? data.items : []);
      setGlobalVersion(data.global_version ?? 0);
    } catch { /* http 拦截器已提示 */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = useCallback(async (item: GuardItem, next: boolean, reason?: string) => {
    setTogglingId(item.guard_id);
    try {
      await guardsApi.update(item.guard_id, { enabled: next, confirm: true, close_reason: reason });
      message.success(next ? `已开启「${item.title}」（回到安全态）` : `已关闭「${item.title}」`);
      await load();
    } catch { /* http 拦截器已提示 */ }
    finally { setTogglingId(null); }
  }, [load]);

  // ---- Switch 处理：开启一律直接切；关闭按风险分级 ----
  const onSwitch = (item: GuardItem, checked: boolean) => {
    if (checked) {
      toggle(item, true);
      return;
    }
    if (item.risk_level === 'red') {
      setRedTarget(item); setRedAck(false); setRedReason('');
    } else if (item.risk_level === 'yellow') {
      setYellowTarget(item);
    } else {
      toggle(item, false); // 绿级直接切
    }
  };

  // ---- 试探单 ----
  const runProbe = async (item: GuardItem) => {
    setProbingId(item.guard_id);
    setProbeResult(null);
    try {
      const res = await guardsApi.probe(item.guard_id);
      const d = res.data;
      const ok = d.verdict === 'probe_ok';
      setProbeResult({
        guardId: item.guard_id, ok,
        text: ok
          ? `已拦截：${d.blocked_reason || '控制生效'}（${d.elapsed_ms}ms）`
          : `未拦截：${d.passed_reason || '探针通过！该控制当前未生效'}（${d.elapsed_ms}ms）`,
      });
    } catch { /* http 拦截器已提示 */ }
    finally { setProbingId(null); }
  };

  // ---- 黄级确认关闭 ----
  const confirmYellowClose = async () => {
    if (!yellowTarget) return;
    setClosing(true);
    try {
      await toggle(yellowTarget, false);
      setYellowTarget(null);
    } finally { setClosing(false); }
  };

  // ---- 红级确认关闭（双 Modal）----
  const confirmRedClose = async () => {
    if (!redTarget || !redAck) return;
    const reason = redReason.trim();
    if (reason.length < 10) {
      message.warning('请填写至少 10 字的关闭理由');
      return;
    }
    setClosing(true);
    try {
      await toggle(redTarget, false, reason);
      setRedTarget(null);
    } finally { setClosing(false); }
  };

  // ---- 参数编辑 ----
  const openParam = (item: GuardItem) => {
    setParamTarget(item);
    const init: Record<string, unknown> = {};
    const p = item.params || {};
    Object.entries(p).forEach(([k, v]) => {
      init[k] = Array.isArray(v) ? (v as unknown[]).join(',') : v;
    });
    paramForm.setFieldsValue(init);
  };
  const saveParam = async () => {
    if (!paramTarget) return;
    setParamSaving(true);
    try {
      const vals = await paramForm.validateFields();
      const params: Record<string, unknown> = {};
      Object.entries(vals).forEach(([k, v]) => {
        const raw = paramTarget.params?.[k];
        if (Array.isArray(raw)) params[k] = String(v).split(',').map(s => s.trim()).filter(Boolean);
        else if (typeof raw === 'number') params[k] = Number(v);
        else if (typeof raw === 'boolean') params[k] = v === true || v === 'true';
        else params[k] = v;
      });
      await guardsApi.update(paramTarget.guard_id, { params, confirm: true });
      message.success(`已更新「${paramTarget.title}」参数`);
      setParamTarget(null);
      await load();
    } catch { /* validateFields 或 http 错误 */ }
    finally { setParamSaving(false); }
  };

  // ---- 拦截记录 ----
  const openEvents = async (guardId: string) => {
    setEventsOpen(true); setEventsGuard(guardId); setEventsPage(1);
    await fetchEvents(guardId, 1);
  };
  const fetchEvents = async (guardId: string, page: number) => {
    setEventsLoading(true);
    try {
      const res = await guardsApi.events({ guard_id: guardId || undefined, range: '7d', page, page_size: eventsSize });
      setEventsItems(res.data.items || []);
      setEventsTotal(res.data.total || 0);
    } catch { /* http 拦截器已提示 */ }
    finally { setEventsLoading(false); }
  };

  // ---- 导出配置 ----
  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ items, global_version: globalVersion, exported_at: new Date().toISOString() }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `security-controls-v${globalVersion}.json`; a.click();
    URL.revokeObjectURL(url);
  };

  const resetDefaults = async () => {
    setLoading(true);
    try {
      const res = await guardsApi.resetDefaults();
      setItems(res.data.items || []);
      setGlobalVersion(res.data.global_version ?? 0);
      message.success('已全部恢复默认（六卡回到开启+基线参数）');
    } catch { /* http 拦截器已提示 */ }
    finally { setLoading(false); }
  };

  const probeCard = useMemo(() => probeResult ? items.find(i => i.guard_id === probeResult.guardId) : null, [probeResult, items]);

  const renderCard = (item: GuardItem) => {
    const risk = RISK_META[item.risk_level] || RISK_META.yellow;
    const d: GuardDescription = item.description || { what: '', lose: '', remain: '' };
    const stats = item.stats || { h24: 0, h7d: 0, last_block_at: null };
    return (
      <Card
        key={item.guard_id}
        size="small"
        style={{ marginBottom: 12, borderColor: probeResult?.guardId === item.guard_id && !probeResult.ok ? '#ff4d4f' : undefined }}
        title={
          <Space>
            <Badge color={risk.color} text={<Text style={{ fontSize: 13, fontWeight: 600 }}>{item.title}</Text>} />
            {item.risk_level === 'red' ? <Tag color="red">红级</Tag> : item.risk_level === 'yellow' ? <Tag color="orange">黄级</Tag> : <Tag color="green">绿级</Tag>}
            <Text type="secondary" style={{ fontSize: 11 }}>v{item.version}</Text>
          </Space>
        }
        extra={
          <Tooltip title={item.enabled ? '关闭该控制（按风险分级确认）' : '开启该控制（回到安全态，直接生效）'}>
            <Switch
              checked={item.enabled}
              loading={togglingId === item.guard_id}
              onChange={(c) => onSwitch(item, c)}
              checkedChildren={<SafetyCertificateOutlined />}
              unCheckedChildren={<PoweroffOutlined />}
            />
          </Tooltip>
        }
      >
        <Paragraph style={{ marginBottom: 4, fontSize: 12 }} ellipsis={{ rows: 1, expandable: true, symbol: '展开说明' }}>
          {d.what || '（无说明）'}
        </Paragraph>
        {d.lose || d.remain ? (
          <Space direction="vertical" size={2} style={{ marginBottom: 6, display: 'block' }}>
            {d.lose ? <Text type="warning" style={{ fontSize: 11, display: 'block' }}><InfoCircleOutlined /> 关闭后：{d.lose}</Text> : null}
            {d.remain ? <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>剩余防线：{d.remain}</Text> : null}
          </Space>
        ) : null}
        <Row gutter={12} align="middle" style={{ marginBottom: 6 }}>
          <Col>
            <StatusTag preset="warning">24h 拦截 {stats.h24}</StatusTag>
          </Col>
          <Col>
            <StatusTag preset="info">7天 {stats.h7d}</StatusTag>
          </Col>
          <Col>
            {stats.last_block_at
              ? <Text type="secondary" style={{ fontSize: 11 }}>最近拦截 {new Date(stats.last_block_at).toLocaleString('zh-CN')}</Text>
              : <Text type="secondary" style={{ fontSize: 11 }}>暂无拦截记录</Text>}
          </Col>
        </Row>
        <Space>
          <Button
            size="small" icon={<ExperimentOutlined />} loading={probingId === item.guard_id}
            onClick={() => runProbe(item)}
          >试探单</Button>
          {Object.keys(item.params || {}).length > 0 ? (
            <Button size="small" icon={<SettingOutlined />} onClick={() => openParam(item)}>参数</Button>
          ) : null}
          <Button size="small" icon={<HistoryOutlined />} onClick={() => openEvents(item.guard_id)}>拦截记录</Button>
        </Space>
      </Card>
    );
  };

  return (
    <PageShell title="安全控制中心" description="五类守卫 + 审批轨的开关 / 参数 / 试探单 / 拦截统计">
      <div style={{ overflow: 'auto', flex: 1, minHeight: 0, paddingBottom: 24 }}>
      {/* 顶栏操作区 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Popconfirm title="恢复全部默认（六卡回到开启+基线参数）？" onConfirm={resetDefaults}>
              <Button icon={<ReloadOutlined />} loading={loading}>全部恢复默认</Button>
            </Popconfirm>
            <Button icon={<DownloadOutlined />} onClick={exportJson}>导出配置 JSON</Button>
          </Space>
        </Col>
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>全局配置版本 v{globalVersion}</Text>
        </Col>
      </Row>

      {/* 试探结果 Banner */}
      {probeResult ? (
        <Alert
          style={{ marginBottom: 12 }}
          type={probeResult.ok ? 'success' : 'error'}
          showIcon
          message={probeResult.ok ? '✓ 控制生效凭证' : '✗ 控制未生效'}
          description={
            <Space direction="vertical" size={2}>
              <Text>{probeResult.text}</Text>
              {!probeResult.ok ? <Text type="secondary" style={{ fontSize: 12 }}>连续两次未拦截请检查配置与 run_guards 接线</Text> : null}
            </Space>
          }
          closable onClose={() => setProbeResult(null)}
        />
      ) : null}

      {/* 控制卡列表 */}
      {loading && items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
      ) : (
        items.map(renderCard)
      )}

      {/* 最近变更尾巴条 */}
      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
        最近变更记录见各卡「拦截记录」Drawer（含 toggle/reset/probe/block 全量事件，30 天留存）
      </Text>

      {/* 黄级关闭确认 Modal */}
      <Modal
        open={!!yellowTarget}
        title={yellowTarget ? `确认关闭「${yellowTarget.title}」` : ''}
        onCancel={() => setYellowTarget(null)}
        onOk={confirmYellowClose}
        okText="确认关闭"
        okButtonProps={{ danger: true, loading: closing }}
      >
        {yellowTarget ? (
          <Space direction="vertical" size={6} style={{ display: 'block' }}>
            <Paragraph style={{ marginBottom: 0 }}>{yellowTarget.description?.lose || '关闭后该控制将不再拦截。'}</Paragraph>
            <Text type="secondary">{yellowTarget.description?.remain ? `剩余防线：${yellowTarget.description.remain}` : ''}</Text>
          </Space>
        ) : null}
      </Modal>

      {/* 红级关闭确认 Modal①（风险认知） */}
      <Modal
        open={!!redTarget && !redAck}
        title={redTarget ? `关闭高风险控制「${redTarget.title}」` : ''}
        onCancel={() => setRedTarget(null)}
        okText="我已了解风险"
        okButtonProps={{ danger: true }}
        onOk={() => setRedAck(true)}
      >
        {redTarget ? (
          <Space direction="vertical" size={6} style={{ display: 'block' }}>
            <Alert type="error" showIcon message="高风险控制，关闭将显著扩大系统暴露面" />
            <Paragraph style={{ marginTop: 8, marginBottom: 0 }}>{redTarget.description?.what}</Paragraph>
            <Text type="warning">{redTarget.description?.lose}</Text>
            <Text type="secondary" style={{ display: 'block' }}>{redTarget.description?.remain ? `剩余防线：${redTarget.description.remain}` : ''}</Text>
          </Space>
        ) : null}
      </Modal>

      {/* 红级关闭确认 Modal②（必填理由） */}
      <Modal
        open={!!redTarget && redAck}
        title={redTarget ? `填写关闭理由（必填，≥10 字）` : ''}
        onCancel={() => { setRedTarget(null); setRedAck(false); }}
        onOk={confirmRedClose}
        okText="确认关闭"
        okButtonProps={{ danger: true, loading: closing, disabled: redReason.trim().length < 10 }}
      >
        <Input.TextArea
          rows={3} maxLength={500}
          placeholder="说明为何需要关闭此高风险控制（审计留痕）"
          value={redReason}
          onChange={(e) => setRedReason(e.target.value)}
          showCount
        />
        <Text type={redReason.trim().length >= 10 ? 'success' : 'secondary'} style={{ fontSize: 11 }}>
          {redReason.trim().length >= 10 ? '✓ 理由已满足要求' : `还需 ${10 - redReason.trim().length} 字`}
        </Text>
      </Modal>

      {/* Drawer① 参数编辑 */}
      <Drawer
        title={paramTarget ? `参数编辑 - ${paramTarget.title}` : '参数编辑'}
        width={520}
        open={!!paramTarget}
        onClose={() => setParamTarget(null)}
        footer={
          <DrawerFooter>
            <Space>
              <Button onClick={() => setParamTarget(null)}>取消</Button>
              <Button type="primary" loading={paramSaving} onClick={saveParam}>保存</Button>
            </Space>
          </DrawerFooter>
        }
      >
        {paramTarget ? (
          <Form form={paramForm} layout="vertical">
            {Object.entries(paramTarget.params || {}).map(([k, v]) => {
              if (Array.isArray(v)) {
                return (
                  <Form.Item key={k} name={k} label={k} extra="逗号分隔多个值">
                    <Input placeholder="a,b,c" />
                  </Form.Item>
                );
              }
              if (typeof v === 'number') {
                return (
                  <Form.Item key={k} name={k} label={k}>
                    <Input type="number" />
                  </Form.Item>
                );
              }
              if (typeof v === 'boolean') {
                return (
                  <Form.Item key={k} name={k} label={k} valuePropName="checked">
                    <Switch />
                  </Form.Item>
                );
              }
              return (
                <Form.Item key={k} name={k} label={k}>
                  <Input />
                </Form.Item>
              );
            })}
          </Form>
        ) : null}
      </Drawer>

      {/* Drawer② 拦截记录 */}
      <Drawer
        title={`拦截记录${eventsGuard ? ` - ${items.find(i => i.guard_id === eventsGuard)?.title || eventsGuard}` : ''}`}
        width={720}
        open={eventsOpen}
        onClose={() => setEventsOpen(false)}
      >
        <DataTableShell
          loading={eventsLoading}
          tableProps={{
            rowKey: 'id',
            dataSource: eventsItems,
            pagination: {
              current: eventsPage, pageSize: eventsSize, total: eventsTotal, showSizeChanger: false,
              onChange: (p: number) => { setEventsPage(p); fetchEvents(eventsGuard, p); },
            },
            columns: [
              { title: '时间', dataIndex: 'ts', width: 160, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
              { title: '守卫', dataIndex: 'guard_id', width: 120 },
              {
                title: '动作', dataIndex: 'action', width: 80,
                render: (v: string) => { const m = ACTION_META[v] || { label: v, preset: 'info' as const }; return <StatusTag preset={m.preset}>{m.label}</StatusTag>; },
              },
              { title: '判定', dataIndex: 'verdict', width: 100, render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
              { title: '操作人', dataIndex: 'updated_by', width: 100, render: (v: string) => v || '-' },
              { title: '详情', dataIndex: 'detail', ellipsis: true, render: (v: Record<string, unknown>) => v ? JSON.stringify(v).slice(0, 80) : '-' },
            ],
          }}
        />
      </Drawer>
      </div>
    </PageShell>
  );
};

export default SecurityControlCenter;
