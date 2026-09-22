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
  Alert, Badge, Button, Card, Checkbox, Col, Drawer, Form, Input, InputNumber, List, message,
  Modal, Popconfirm, Row, Select, Space, Spin, Switch, Tabs, Tag, Tooltip, Typography,
} from 'antd';
import {
  PoweroffOutlined, SafetyCertificateOutlined, ExperimentOutlined,
  SettingOutlined, HistoryOutlined, ReloadOutlined, DownloadOutlined, InfoCircleOutlined,
  LockOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import { guardsApi, capabilitiesApi, type GuardItem, type GuardEventItem, type GuardDescription, type CapabilityItem, type SubagentSpec, type AssemblyManifest } from '../services/api';
import { PageShell, StatusTag, DataTableShell, DrawerFooter } from '../components/shell';
import { tokens } from '../theme/tokens';

const { Text, Paragraph } = Typography;

/**
 * 批13-W 十步 Tab 改版（用户 2026-09-04 定调，终版设计 §三）：
 * 每项配置挂到它实际影响的装配步骤（deepagents graph.py 十步），教学即运维。
 * 守卫 Tab 保留独立——运行期裁决（PATCH→TTL 5s 热生效）与装配期（PATCH→version+1→缓存键变→重装配）
 * 是两条生效链路，不并入十步。
 */
const STEP_TITLES: Record<number, string> = {
  0: '全局 · 缓存与版本',
  1: '步1 · 模型与档案',
  2: '步2 · 体检',
  3: '步3 · 工具说明书',
  4: '步4 · 文件柜',
  5: '步5 · 小弟',
  6: '步6 · 主栈',
  7: '步7 · 筛与拼',
  8: '步8/9 · 状态与查白',
  10: '步10 · 出厂',
};

const CAP_STEP_MAP: Record<string, number> = {
  approval_track: 0,      // 版本键成分（缓存键 c{ver}），归全局
  prompt_caching: 0,      // 全局装配特性（Anthropic 专属，当前物理锁定）
  filesystem_tools: 4,    // 文件柜：CompositeBackend+StoreBackend 路由
  store: 4,               // 长期记忆库
  subagents: 5,           // 小弟：task 委派+规格编辑器
  skills: 6,              // 主栈：技能站
  memory: 6,              // 主栈：记忆
  permissions: 6,         // 主栈：文件权限规则
  debug: 6,               // 主栈：调试
  patch_tool_calls: 6,    // 框架自动件（🔒锁定灰显）
  message_eviction: 6,    // 框架自动件（🔒锁定灰显）
  summarization: 7,       // 筛与拼：摘要排除栏条件化
  tool_availability: 7,   // 筛与拼：W-1 白名单打勾
  decision_gate: 7,       // 筛与拼：检查站卡（W-4a 装卸+W-4b scope_tools）
  response_format: 10,    // 出厂：结构化最终交付
  rubric: 10,             // 出厂：评分 mode（skill_prompt 自检段注入步10 系统提示词）
};

/** 十步教学文案（与装配机制同源知识；框架升级时需人工核对——设计 §五.4 漂移风险登记） */
const STEP_TEACH: Record<number, { teach: string; reason: string }> = {
  1: {
    teach: '步1 装配模型档案：从连接池取当前连接的模型实例，注册 HarnessProfile（key 双保险：openai:DeepSeek-V4-Flash + 小写变体），档案里的 excluded_tools 决定步7 的工具排除结算。',
    reason: '模型实例来自 LLM 配置页管理的连接（改连接走 LLM 配置页，不在此改）；档案排除清单由步7 白名单换算产生，此处只读。',
  },
  2: {
    teach: '步2 体检保护名单 {FilesystemMiddleware, SubAgentMiddleware}：文件工具与权限的娘家、task 委派的娘家。保护名单内的站不可被排除栏排除。',
    reason: '保护名单是框架安全机制（防止排除栏误杀文件/子代理能力），无配置面——动了它文件工具或 task 就会静默失效。',
  },
  3: {
    teach: '步3 工具说明书（description 改写）：改写栏三次消费点=调用者工具（kg_api 家族）/文件工具（read_file/ls）/task 工具。当前无改写项（X-3 缓议不实施）。',
    reason: '改写项按 YAGNI 缓议（X-3）：没有真实行为偏差证据前不预支适配代码；将来适配加在 tupu_deepagent 注册处。',
  },
  8: {
    teach: '步8/9 状态与查白：各中间件小抽屉收编状态汇总（步8），排除栏覆盖结算（步9）——查「该撤的撤没撤」：白名单换算后的排除清单在步9 一次性生效于 Agent 工具表。',
    reason: '这两步是框架内的状态结算过程（无外部可配项）；结算结果看 manifest 探针（tool_availability_installed 记录换算后的排除清单）。',
  },
};

const RISK_META: Record<string, { color: string; label: string }> = {
  red: { color: 'red', label: '高风险' },
  yellow: { color: 'orange', label: '中风险' },
  green: { color: 'green', label: '低风险' },
};

const CAP_ACTION_META: Record<string, { label: string; preset: 'success' | 'warning' | 'info' | 'disabled' }> = {
  toggle: { label: '变更', preset: 'info' },
  rebuild: { label: '重建', preset: 'info' },
  probe: { label: '试探', preset: 'info' },
  task_invoke: { label: '委派', preset: 'success' },
  task_reject: { label: '拒委派', preset: 'warning' },
  spec_invalid: { label: '坏规格', preset: 'warning' },
  fallback: { label: '回退', preset: 'warning' },
  reset: { label: '重置', preset: 'info' },
};

const ACTION_META: Record<string, { label: string; preset: 'success' | 'warning' | 'info' | 'disabled' }> = {
  block: { label: '拦截', preset: 'warning' },
  warn: { label: '告警', preset: 'info' },
  pass: { label: '放行', preset: 'success' },
  probe: { label: '试探', preset: 'info' },
  toggle: { label: '变更', preset: 'info' },
  reset: { label: '重置', preset: 'info' },
};

/**
 * CapabilityPanel - 能力开关 Tab（批13-Q 七）。
 * 14 可切能力卡（五件套同款：开关/三段说明/统计/探针/参数；含批13-J 工具黑名单）+ 4 灰显锁定区。
 * subagents 卡特殊：🔴 徽标 + 参数区=规格编辑器（specs JSON + max_concurrent 步进 + 校验按钮）。
 * 关闭确认风险分级与 Tab1 同款（🔴双 Modal+必填理由 / 🟡单 Modal / 🟢直接切）。
 */
const CapabilityPanel: React.FC<{ stepFilter?: number }> = ({ stepFilter }) => {
  const [items, setItems] = useState<CapabilityItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [capVersion, setCapVersion] = useState(0);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [probingId, setProbingId] = useState<string | null>(null);
  const [probeResult, setProbeResult] = useState<{ capId: string; ok: boolean; text: string } | null>(null);
  const [yellowTarget, setYellowTarget] = useState<CapabilityItem | null>(null);
  const [redTarget, setRedTarget] = useState<CapabilityItem | null>(null);
  const [redAck, setRedAck] = useState(false);
  const [redReason, setRedReason] = useState('');
  const [closing, setClosing] = useState(false);
  const [paramTarget, setParamTarget] = useState<CapabilityItem | null>(null);
  const [specText, setSpecText] = useState('');
  const [specValid, setSpecValid] = useState<null | { ok: boolean; msg: string }>(null);
  const [paramForm] = Form.useForm();
  const [paramSaving, setParamSaving] = useState(false);
  const [eventsOpen, setEventsOpen] = useState(false);
  const [eventsCap, setEventsCap] = useState('');
  const [eventsItems, setEventsItems] = useState<Array<{ id: number; capability_id: string; ts?: string | null; action: string; detail?: Record<string, unknown>; updated_by?: string | null }>>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsPage, setEventsPage] = useState(1);
  const [toolMf, setToolMf] = useState<AssemblyManifest | null>(null);
  const eventsSize = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await capabilitiesApi.list();
      setItems(Array.isArray(res.data.items) ? res.data.items : []);
      setCapVersion(res.data.capability_version ?? 0);
    } catch { /* http 拦截器已提示 */ }
    finally { setLoading(false); }
  }, []);

  // 批13-W：manifest（勾选域全集/锁定集）——ToolChecklistParam 数据源
  const loadMf = useCallback(async () => {
    try {
      const res = await capabilitiesApi.manifest();
      setToolMf(res.data as AssemblyManifest);
    } catch { /* http 拦截器已提示 */ }
  }, []);

  useEffect(() => { load(); loadMf(); }, [load, loadMf]);

  const toggle = async (item: CapabilityItem, next: boolean, reason?: string) => {
    setTogglingId(item.capability_id);
    try {
      await capabilitiesApi.update(item.capability_id, { enabled: next, confirm: true, close_reason: reason });
      message.success(next ? `已开启「${item.title}」` : `已关闭「${item.title}」（下一问按新配置重建 Agent）`);
      await load();
    } catch { /* http 拦截器已提示 */ }
    finally { setTogglingId(null); }
  };

  const onSwitch = (item: CapabilityItem, checked: boolean) => {
    if (item.physical_blocked) return;
    if (checked) { toggle(item, true); return; }
    if (item.risk_level === 'red') { setRedTarget(item); setRedAck(false); setRedReason(''); }
    else if (item.risk_level === 'yellow') setYellowTarget(item);
    else toggle(item, false);
  };

  const runProbe = async (item: CapabilityItem) => {
    setProbingId(item.capability_id);
    setProbeResult(null);
    try {
      const res = await capabilitiesApi.probe(item.capability_id);
      const d = res.data;
      const ok = d.verdict === 'probe_ok';
      setProbeResult({
        capId: item.capability_id, ok,
        text: ok ? `已命中：${d.blocked_reason || '控制生效'}（${d.elapsed_ms}ms）`
                 : `未命中：${d.passed_reason || '探针通过！该控制当前未生效'}（${d.elapsed_ms}ms）`,
      });
    } catch { /* http 拦截器已提示 */ }
    finally { setProbingId(null); }
  };

  const openParam = (item: CapabilityItem) => {
    setParamTarget(item);
    setSpecValid(null);
    if (item.capability_id === 'subagents') {
      const specs = (item.params?.specs as SubagentSpec[] | undefined) || [];
      setSpecText(JSON.stringify(specs, null, 2));
      paramForm.setFieldsValue({ max_concurrent: item.params?.max_concurrent ?? 2 });
    } else {
      const init: Record<string, unknown> = {};
      Object.entries(item.params || {}).forEach(([k, v]) => {
        init[k] = Array.isArray(v) ? (v as unknown[]).join(',') : v;
      });
      paramForm.setFieldsValue(init);
    }
  };

  const validateSpecs = () => {
    try {
      const parsed = JSON.parse(specText);
      if (!Array.isArray(parsed)) { setSpecValid({ ok: false, msg: '必须是规格数组' }); return; }
      for (const s of parsed) {
        if (!s.name || !s.description || !s.prompt || !Array.isArray(s.tools) || s.tools.length === 0) {
          setSpecValid({ ok: false, msg: `规格 ${s.name || '?'} 缺少 name/description/prompt/tools` });
          return;
        }
      }
      setSpecValid({ ok: true, msg: `✓ ${parsed.length} 个规格格式合法（工具交集后端二次校验）` });
    } catch (e) {
      setSpecValid({ ok: false, msg: `JSON 解析失败: ${(e as Error).message}` });
    }
  };

  const saveParam = async () => {
    if (!paramTarget) return;
    setParamSaving(true);
    try {
      let params: Record<string, unknown>;
      if (paramTarget.capability_id === 'subagents') {
        let specs: unknown;
        try { specs = JSON.parse(specText); } catch (e) {
          message.error(`specs JSON 解析失败: ${(e as Error).message}`); return;
        }
        params = { specs, max_concurrent: paramForm.getFieldValue('max_concurrent') ?? 2 };
      } else {
        const vals = await paramForm.validateFields();
        params = {};
        Object.entries(vals).forEach(([k, v]) => {
          const raw = paramTarget.params?.[k];
          if (Array.isArray(raw)) params[k] = String(v).split(',').map(s => s.trim()).filter(Boolean);
          else if (typeof raw === 'number') params[k] = Number(v);
          else if (typeof raw === 'boolean') params[k] = v === true || v === 'true';
          else params[k] = v;
        });
      }
      await capabilitiesApi.update(paramTarget.capability_id, { params, confirm: true });
      message.success(`已更新「${paramTarget.title}」参数`);
      setParamTarget(null);
      await load();
    } catch { /* validateFields 或 http 错误 */ }
    finally { setParamSaving(false); }
  };

  const fetchEvents = async (capId: string, page: number) => {
    setEventsLoading(true);
    try {
      const res = await capabilitiesApi.events({ capability_id: capId || undefined, range: '7d', page, page_size: eventsSize });
      setEventsItems(res.data.items || []);
      setEventsTotal(res.data.total || 0);
    } catch { /* http 拦截器已提示 */ }
    finally { setEventsLoading(false); }
  };

  const resetDefaults = async () => {
    setLoading(true);
    try {
      const res = await capabilitiesApi.resetDefaults();
      setItems(res.data.items || []);
      setCapVersion(res.data.capability_version ?? 0);
      message.success('已全部恢复默认（能力回到基线，下一问重建 Agent）');
    } catch { /* http 拦截器已提示 */ }
    finally { setLoading(false); }
  };

  const renderCapCard = (item: CapabilityItem) => {
    const risk = RISK_META[item.risk_level] || RISK_META.yellow;
    const d = item.description || {};
    const stats = item.stats || {};
    const isSub = item.capability_id === 'subagents';
    return (
      <Card
        key={item.capability_id}
        size="small"
        style={{ marginBottom: 12, borderColor: probeResult?.capId === item.capability_id && !probeResult.ok ? '#ff4d4f' : undefined }}
        title={
          <Space>
            <Badge color={risk.color} text={<Text style={{ fontSize: 13, fontWeight: 600 }}>{item.title}</Text>} />
            {item.risk_level === 'red' ? <Tag color="red">红级</Tag> : item.risk_level === 'yellow' ? <Tag color="orange">黄级</Tag> : <Tag color="green">绿级</Tag>}
            {isSub ? <Tag color="purple">受限</Tag> : null}
            <Text type="secondary" style={{ fontSize: 11 }}>v{item.version}</Text>
          </Space>
        }
        extra={
          <Tooltip title={item.enabled ? '关闭该能力（按风险分级确认）' : '开启该能力（下一问按新配置重建）'}>
            <Switch
              checked={item.enabled}
              loading={togglingId === item.capability_id}
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
        <Space direction="vertical" size={2} style={{ marginBottom: 6, display: 'block' }}>
          {d.lose ? <Text type="warning" style={{ fontSize: 11, display: 'block' }}><InfoCircleOutlined /> 关闭后：{d.lose}</Text> : null}
          {d.remain ? <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>剩余防线：{d.remain}</Text> : null}
        </Space>
        <Row gutter={12} align="middle" style={{ marginBottom: 6 }}>
          <Col>
            <StatusTag preset="info">探针通过率 {stats.probe_pass_rate != null ? `${Math.round(stats.probe_pass_rate * 100)}%` : '—'}</StatusTag>
          </Col>
          <Col>
            <StatusTag preset="success">7天委派 {stats.task_invoke_7d ?? 0}</StatusTag>
          </Col>
          <Col>
            {stats.last_change
              ? <Text type="secondary" style={{ fontSize: 11 }}>最近变更 {new Date(stats.last_change).toLocaleString('zh-CN')}</Text>
              : <Text type="secondary" style={{ fontSize: 11 }}>暂无变更</Text>}
          </Col>
        </Row>
        <Space>
          <Button size="small" icon={<ExperimentOutlined />} loading={probingId === item.capability_id} onClick={() => runProbe(item)}>试探单</Button>
          {item.capability_id === 'subagents' || Object.keys(item.params || {}).length > 0 ? (
            <Button size="small" icon={<SettingOutlined />} onClick={() => openParam(item)}>参数</Button>
          ) : null}
          <Button size="small" icon={<HistoryOutlined />} onClick={() => { setEventsOpen(true); setEventsCap(item.capability_id); setEventsPage(1); fetchEvents(item.capability_id, 1); }}>审计记录</Button>
        </Space>
      </Card>
    );
  };

  // 批13-W 十步 Tab：stepFilter 有值时只渲染该步的能力项（教学即运维）；无 filter=全局视图
  const steped = (list: CapabilityItem[]) =>
    stepFilter == null ? list : list.filter(i => (CAP_STEP_MAP[i.capability_id] ?? 6) === stepFilter);
  const switchable = steped(items.filter(i => !i.physical_blocked));
  const locked = steped(items.filter(i => i.physical_blocked));

  return (
    <div style={{ overflow: 'auto', flex: 1, minHeight: 0, paddingBottom: 24 }}>
      {stepFilter == null && (
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Popconfirm title="恢复全部默认（能力回基线，下一问重建 Agent）？" onConfirm={resetDefaults}>
            <Button icon={<ReloadOutlined />} loading={loading}>全部恢复默认</Button>
          </Popconfirm>
          <Button icon={<DownloadOutlined />} style={{ marginLeft: 8 }}
            onClick={() => {
              const blob = new Blob([JSON.stringify({ items, capability_version: capVersion, exported_at: new Date().toISOString() }, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url; a.download = `capabilities-v${capVersion}.json`; a.click();
              URL.revokeObjectURL(url);
            }}>导出配置 JSON</Button>
        </Col>
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>能力版本 v{capVersion}</Text>
        </Col>
      </Row>
      )}

      {probeResult ? (
        <Alert
          style={{ marginBottom: 12 }}
          type={probeResult.ok ? 'success' : 'error'}
          showIcon
          message={probeResult.ok ? '✓ 控制生效凭证' : '✗ 控制未生效'}
          description={<Text>{probeResult.text}</Text>}
          closable onClose={() => setProbeResult(null)}
        />
      ) : null}

      {loading && items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
      ) : (
        <>
          {switchable.map(renderCapCard)}
          <Card size="small" style={{ marginBottom: 12, background: tokens.colors.bgContent, borderColor: tokens.colors.border }} title={
            <Space><LockOutlined style={{ color: tokens.colors.textSecondary }} /><Text type="secondary" style={{ fontWeight: 600 }}>灰显锁定（物理不可用或安全红线，不可变更）</Text></Space>
          }>
            {locked.map(item => (
              <Row key={item.capability_id} align="middle" gutter={12} style={{ padding: '6px 0', borderBottom: `1px dashed ${tokens.colors.border}` }}>
                <Col flex="none"><Switch size="small" disabled checked={false} /></Col>
                <Col flex="none"><Text type="secondary" style={{ fontWeight: 600 }}>{item.title}</Text></Col>
                <Col flex="auto">
                  <Tooltip title={item.blocked_reason || '物理不可用'}>
                    <Text type="secondary" style={{ fontSize: 11 }}><LockOutlined /> {item.blocked_reason}</Text>
                  </Tooltip>
                </Col>
              </Row>
            ))}
          </Card>
        </>
      )}

      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
        变更即时生效：装配类开关 PATCH 后 version+1，下一问按新配置重建 Agent（rebuild 事件见各卡「审计记录」）；旧版本实例 LRU 保留 2 档（在跑请求不断）
      </Text>

      {/* 黄级关闭确认 */}
      <Modal
        open={!!yellowTarget}
        title={yellowTarget ? `确认关闭「${yellowTarget.title}」` : ''}
        onCancel={() => setYellowTarget(null)}
        onOk={async () => { setClosing(true); try { await toggle(yellowTarget!, false); setYellowTarget(null); } finally { setClosing(false); } }}
        okText="确认关闭"
        okButtonProps={{ danger: true, loading: closing }}
      >
        <Paragraph style={{ marginBottom: 0 }}>{yellowTarget?.description?.lose || '关闭后该能力将不再装配。'}</Paragraph>
      </Modal>

      {/* 红级关闭确认 Modal① */}
      <Modal
        open={!!redTarget && !redAck}
        title={redTarget ? `关闭高风险能力「${redTarget.title}」` : ''}
        onCancel={() => setRedTarget(null)}
        okText="我已了解风险"
        okButtonProps={{ danger: true }}
        onOk={() => setRedAck(true)}
      >
        {redTarget ? (
          <Space direction="vertical" size={6} style={{ display: 'block' }}>
            <Alert type="error" showIcon message="高风险能力，关闭将扩大委派面或失去能力控制" />
            <Paragraph style={{ marginTop: 8, marginBottom: 0 }}>{redTarget.description?.what}</Paragraph>
            <Text type="warning">{redTarget.description?.lose}</Text>
            <Text type="secondary" style={{ display: 'block' }}>{redTarget.description?.remain ? `剩余防线：${redTarget.description.remain}` : ''}</Text>
          </Space>
        ) : null}
      </Modal>

      {/* 红级关闭确认 Modal② */}
      <Modal
        open={!!redTarget && redAck}
        title="填写关闭理由（必填，≥10 字）"
        onCancel={() => { setRedTarget(null); setRedAck(false); }}
        onOk={async () => {
          const reason = redReason.trim();
          if (reason.length < 10) { message.warning('请填写至少 10 字的关闭理由'); return; }
          setClosing(true);
          try { await toggle(redTarget!, false, reason); setRedTarget(null); } finally { setClosing(false); }
        }}
        okText="确认关闭"
        okButtonProps={{ danger: true, loading: closing, disabled: redReason.trim().length < 10 }}
      >
        <Input.TextArea
          rows={3} maxLength={500}
          placeholder="说明为何需要关闭此高风险能力（审计留痕）"
          value={redReason}
          onChange={(e) => setRedReason(e.target.value)}
          showCount
        />
        <Text type={redReason.trim().length >= 10 ? 'success' : 'secondary'} style={{ fontSize: 11 }}>
          {redReason.trim().length >= 10 ? '✓ 理由已满足要求' : `还需 ${10 - redReason.trim().length} 字`}
        </Text>
      </Modal>

      {/* 参数 Drawer（subagents=规格编辑器） */}
      <Drawer
        title={paramTarget ? `参数编辑 - ${paramTarget.title}` : '参数编辑'}
        width={560}
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
        {paramTarget?.capability_id === 'subagents' ? (
          <Space direction="vertical" size={12} style={{ display: 'block' }}>
            <Alert type="info" showIcon
              message="委派规格（数据化：改配置不改代码）"
              description="每个规格含 name/description/prompt/tools；tools 将与全局工具注册表取交集（护栏3），空交集拒装配。"
            />
            <div>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>specs（JSON 数组）</Text>
              <Input.TextArea
                rows={14}
                value={specText}
                onChange={(e) => setSpecText(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: 12 }}
              />
              <Space style={{ marginTop: 8 }}>
                <Button size="small" onClick={validateSpecs}>校验格式</Button>
                {specValid ? <Text type={specValid.ok ? 'success' : 'danger'} style={{ fontSize: 12 }}>{specValid.msg}</Text> : null}
              </Space>
            </div>
            <Form form={paramForm} layout="vertical">
              <Form.Item name="max_concurrent" label="max_concurrent（最大并行委派数）" extra="注入子代理提示词的并发约束">
                <InputNumber min={1} max={8} style={{ width: 120 }} />
              </Form.Item>
            </Form>
          </Space>
        ) : (paramTarget?.capability_id === 'tool_availability' || paramTarget?.capability_id === 'decision_gate') && toolMf ? (
  <ToolChecklistParam
    target={paramTarget}
    universe={toolMf.tool_universe}
    locked={toolMf.tool_locked}
    onDone={async () => { setParamTarget(null); await load(); }}
  />
) : paramTarget ? (
          <Form form={paramForm} layout="vertical">
            {Object.entries(paramTarget.params || {}).map(([k, v]) => {
              if (typeof v === 'number') {
                return <Form.Item key={k} name={k} label={k}><InputNumber style={{ width: 160 }} /></Form.Item>;
              }
              if (typeof v === 'boolean') {
                return <Form.Item key={k} name={k} label={k} valuePropName="checked"><Switch /></Form.Item>;
              }
              if (Array.isArray(v)) {
                return <Form.Item key={k} name={k} label={k} extra="逗号分隔多个值"><Input /></Form.Item>;
              }
              return <Form.Item key={k} name={k} label={k}><Input /></Form.Item>;
            })}
          </Form>
        ) : null}
      </Drawer>

      {/* 审计记录 Drawer */}
      <Drawer
        title={`审计记录${eventsCap ? ` - ${items.find(i => i.capability_id === eventsCap)?.title || eventsCap}` : ''}`}
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
              onChange: (p: number) => { setEventsPage(p); fetchEvents(eventsCap, p); },
            },
            columns: [
              { title: '时间', dataIndex: 'ts', width: 150, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
              { title: '能力', dataIndex: 'capability_id', width: 110 },
              {
                title: '动作', dataIndex: 'action', width: 90,
                render: (v: string) => { const m = CAP_ACTION_META[v] || { label: v, preset: 'info' as const }; return <StatusTag preset={m.preset}>{m.label}</StatusTag>; },
              },
              { title: '操作人', dataIndex: 'updated_by', width: 90, render: (v: string) => v || '-' },
              { title: '详情', dataIndex: 'detail', ellipsis: true, render: (v: Record<string, unknown>) => v ? JSON.stringify(v).slice(0, 90) : '-' },
            ],
          }}
        />
      </Drawer>
    </div>
  );
};

/**
 * ToolChecklistParam（批13-W W-1/W-4）：工具打勾参数编辑器（参数 Drawer 内 tool_availability /
 * decision_gate 特判渲染）。数据源=manifest 端点的装配期勾选域全集（新框架工具自动落未勾选态，
 * 白名单语义天然免疫）；tool_availability 的锁定件（∩勾选域）灰显不可取消。
 */
const ToolChecklistParam: React.FC<{
  target: CapabilityItem;
  universe: string[];
  locked: string[];
  onDone: () => Promise<void>;
}> = ({ target, universe, locked, onDone }) => {
  const isAllowlist = target.capability_id === 'tool_availability';
  const paramKey = isAllowlist ? 'allowed' : 'scope_tools';
  const [checked, setChecked] = useState<string[]>(
    Array.isArray(target.params?.[paramKey]) ? (target.params?.[paramKey] as string[]) : [],
  );
  const [saving, setSaving] = useState(false);
  // 白名单锁定件强制保留（运行时也兜底，前端灰显只是第一道）
  const hardLocked = isAllowlist ? locked.filter(t => universe.includes(t)) : [];
  const options = universe.map(u => ({ label: u, value: u, disabled: hardLocked.includes(u) }));
  const offUniverse = universe.filter(u => !checked.includes(u));

  const save = async () => {
    if (isAllowlist && offUniverse.length > 0) {
      // 🔴 语义：取消域内工具 = 排除清单变化 = 下一问重建。风险确认走 PATCH 前本 Modal。
      Modal.confirm({
        title: `取消 ${offUniverse.length} 件工具的勾选？`,
        content: `将取消：${offUniverse.join('、')}。这些工具下一问起从 Agent 工具表移除（取消业务工具属 🔴 高风险操作）。`,
        okText: '确认取消勾选', okButtonProps: { danger: true },
        onOk: doSave,
      });
      return;
    }
    await doSave();
  };
  const doSave = async () => {
    setSaving(true);
    try {
      await capabilitiesApi.update(target.capability_id, { params: { [paramKey]: checked }, confirm: true });
      message.success(`已更新「${target.title}」（下一问按新配置重建 Agent）`);
      await onDone();
    } catch { /* http 拦截器已提示 */ }
    finally { setSaving(false); }
  };

  return (
    <div>
      <Alert
        type="info" showIcon style={{ marginBottom: 12 }}
        message={isAllowlist ? '白名单打勾制（W-1）：没打勾即禁' : '范围强校验工具集（W-4b）'}
        description={isAllowlist
          ? '勾选=允许进入 Agent 工具表；取消=排除（装配换算 excluded=红线件∪(勾选域-allowed)）。框架升级新增工具自动落未勾选态（白名单天然免疫漏网）。锁定件灰显不可取消。'
          : '勾选的工具在决策门开启时做客户名范围强校验（须 ⊆ 可信范围）；理由校验（已知/判断/因此）对全部工具恒生效。'}
      />
      <Checkbox.Group
        style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
        options={options}
        value={checked}
        onChange={(v) => setChecked(v as string[])}
      />
      <Button type="primary" size="small" style={{ marginTop: 12 }} loading={saving} onClick={save}>
        保存（version+1，下一问重建）
      </Button>
    </div>
  );
};

/**
 * Tab0Panel（批13-W 十步 Tab0）：装配 manifest 总览——四 mode 字段+缓存键成分+探针记录+白名单勾选域。
 * 只读总览；下方挂全局能力卡（approval_track/prompt_caching，CAP_STEP_MAP 归 0）。
 */
const Tab0Panel: React.FC = () => {
  const [mf, setMf] = useState<AssemblyManifest | null>(null);
  const load = useCallback(async () => {
    try {
      const res = await capabilitiesApi.manifest();
      setMf(res.data as AssemblyManifest);
    } catch { /* http 拦截器已提示 */ }
  }, []);
  useEffect(() => { load(); }, [load]);
  const it = mf?.items || {};
  const modeRows: Array<[string, unknown, string]> = [
    ['summarization_mode（摘要模式）', it.summarization_mode, '官方工厂双件套=official_factory / 关闭=disabled'],
    ['data_summary_mode（数据摘要模式）', it.data_summary_mode, '工具端暂存+SSE result_ref 派发（13-AB4）'],
    ['rubric_mode（评分模式）', it.rubric_mode, 'skill_prompt=自检段进提示词 / middleware=独立评分站'],
    ['backend_mode（后端模式）', it.backend_mode, 'store=官方 StoreBackend 路由（13-Y）'],
  ];
  return (
    <div style={{ overflow: 'auto', flex: 1, minHeight: 0, paddingBottom: 24 }}>
      <Alert
        type="info" showIcon style={{ marginBottom: 12 }}
        message="缓存键四成分：{连接}#g{守卫ver}#c{能力ver}#f{files_hash}"
        description={`任一成分变化 → 缓存失配 → 下一问重装配（LRU 保留 2 版）。当前能力版本 v${mf?.capability_version ?? '-'}，agent_key=${mf?.agent_key || '-'}。配置 PATCH 只走「改当前值」：默认值=代码常量（审计锚点），reset-defaults 回代码基准。`}
      />
      <Card size="small" style={{ marginBottom: 12 }} title="装配 manifest 总览（最近一次装配实证）">
        {modeRows.map(([k, v, note]) => (
          <Row key={k} align="middle" gutter={12} style={{ padding: '4px 0', borderBottom: `1px dashed ${tokens.colors.border}` }}>
            <Col flex="220px"><Text type="secondary" style={{ fontSize: 12 }}>{k}</Text></Col>
            <Col flex="140px"><Tag color={v === 'disabled' ? 'orange' : 'green'}>{String(v ?? '-')}</Tag></Col>
            <Col flex="auto"><Text type="secondary" style={{ fontSize: 11 }}>{note}</Text></Col>
          </Row>
        ))}
        <Row align="middle" gutter={12} style={{ padding: '4px 0' }}>
          <Col flex="220px"><Text type="secondary" style={{ fontSize: 12 }}>tool_availability_installed（白名单换算排除清单）</Text></Col>
          <Col flex="auto"><Text style={{ fontSize: 12 }}>{Array.isArray(it.tool_availability_installed) ? (it.tool_availability_installed as string[]).join('、') : '-'}</Text></Col>
        </Row>
        <Row align="middle" gutter={12} style={{ padding: '4px 0' }}>
          <Col flex="220px"><Text type="secondary" style={{ fontSize: 12 }}>decision_gate_installed / scope_gated_installed</Text></Col>
          <Col flex="auto"><Text style={{ fontSize: 12 }}>{String(it.decision_gate_installed ?? '-')} / {(it.scope_gated_installed as string[])?.join('、') || '-'}</Text></Col>
        </Row>
        <Row align="middle" gutter={12} style={{ padding: '4px 0' }}>
          <Col flex="220px"><Text type="secondary" style={{ fontSize: 12 }}>files_hash / seeded_files（13-Y）</Text></Col>
          <Col flex="auto"><Text style={{ fontSize: 12 }}>{String(it.files_hash ?? '-')} / {String(it.seeded_files ?? '-')}</Text></Col>
        </Row>
      </Card>
      <Card size="small" style={{ marginBottom: 12, background: tokens.colors.bgContent, borderColor: tokens.colors.border }} title={
        <Space><InfoCircleOutlined /><Text type="secondary" style={{ fontWeight: 600 }}>白名单勾选域（装配期全集，{mf?.tool_universe.length ?? '-'} 件）</Text></Space>
      }>
        <Text type="secondary" style={{ fontSize: 11 }}>{mf?.generics_note}</Text>
        <div style={{ marginTop: 6 }}>
          {(mf?.tool_universe || []).map(t => {
            const isLocked = (mf?.tool_locked || []).includes(t);
            return <Tag key={t} style={{ marginBottom: 4 }} color={isLocked ? 'gold' : 'default'}>{isLocked ? '🔒 ' : ''}{t}</Tag>;
          })}
        </div>
      </Card>
      <CapabilityPanel stepFilter={0} />
    </div>
  );
};

/** TeachPanel（批13-W）：只读教学页——头部一句话教学+底部「本步不可配置原因」（教学即运维纪律）。 */
const TeachPanel: React.FC<{ step: number }> = ({ step }) => {
  const t = STEP_TEACH[step];
  if (!t) return <Alert type="warning" message={`步${step} 教学内容待补`} />;
  return (
    <div style={{ overflow: 'auto', flex: 1, minHeight: 0, paddingBottom: 24 }}>
      <Alert type="info" showIcon message={`${STEP_TITLES[step]}（只读教学）`} description={t.teach} style={{ marginBottom: 12 }} />
      <Card size="small" style={{ background: tokens.colors.bgContent, borderColor: tokens.colors.border }} title={
        <Space><LockOutlined style={{ color: tokens.colors.textSecondary }} /><Text type="secondary" style={{ fontWeight: 600 }}>本步不可配置原因</Text></Space>
      }>
        <Text type="secondary" style={{ fontSize: 12 }}>{t.reason}</Text>
      </Card>
    </div>
  );
};

/** 件 A/C 模式预设：加载中的预设键（plan 代码块用 ModeKey，本页原无此类型——实况最小适配；含 null=空闲） */
type ModeKey = 'turbo' | 'safe' | null;

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

  // —— 件 A/C（2026-09-12 极速模式 spec §三）：模式预设 ——
  const [presetMode, setPresetMode] = useState<'turbo' | 'safe' | 'custom'>('custom');
  const [presetLoading, setPresetLoading] = useState<ModeKey>(null);

  const refreshPresetMode = useCallback(async () => {
    try {
      const [g, c] = await Promise.all([guardsApi.list(), capabilitiesApi.list()]);
      const ge = (id: string) => g.data?.items?.find((x: any) => x.guard_id === id)?.enabled;
      const ce = (id: string) => c.data?.items?.find((x: any) => x.capability_id === id)?.enabled;
      const turbo = ge('template') === false && ge('output') === false && ge('engine_lock') === false
        && ge('approval_track') === false && ge('capability') === false && ce('decision_gate') === false;
      const safe = ge('template') === true && ge('output') === true && ge('engine_lock') === true
        && ge('approval_track') === true && ge('capability') === true && ce('decision_gate') === true;
      setPresetMode(turbo ? 'turbo' : safe ? 'safe' : 'custom');
    } catch { /* 读失败显示「自定义」，不阻断页面 */ }
  }, []);

  useEffect(() => { refreshPresetMode(); }, [refreshPresetMode]);

  const applyPreset = (mode: 'turbo' | 'safe') => {
    const doApply = async () => {
      setPresetLoading(mode);
      try {
        await guardsApi.preset(mode);
        message.success(mode === 'turbo'
          ? '已切换极速模式（后台预热中，下一问生效）'
          : '已切换安全模式（全站回位，后台预热中）');
        await refreshPresetMode();
      } catch (e: any) {
        message.error(`预设切换失败: ${e?.response?.data?.detail || e?.message || '未知错误'}`);
      } finally { setPresetLoading(null); }
    };
    if (mode === 'turbo') {
      Modal.confirm({                       // 红级确认范式：极速模式风险必须显式确认
        title: '切换到极速模式（turbo）？',
        width: 640,
        content: (
          <div style={{ lineHeight: 1.8 }}>
            <p><b>将关闭</b>：下一步判断闸门、模板控制、输出控制、引擎锁、审批轨、工具白名单守卫；
            <b>保留</b>：SQL 安全控制（SELECT-only+强制 LIMIT）与定位预算（死循环防护）。</p>
            <p><b>风险账</b>（spec 2026-09-12 §三 C）：SQL 不再过模板校验（错表/错口径 SQL 会真执行）；
            输出契约不校验、无范围声明/一轮单工具纪律、无工具白名单。</p>
            <p>数据破坏风险≈0（引擎只读：duckdb/Doris 外部 catalog，且 sql_safety 保留）；
            主要风险=<b>查询质量与行为不确定性</b>——零拒绝依赖模型自律（实验 2/2 成功，样本小）。</p>
          </div>
        ),
        okText: '切换到极速', okButtonProps: { danger: true }, cancelText: '取消',
        onOk: doApply,
      });
    } else { doApply(); }                    // 回安全=恢复防护，直接切
  };

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

  const guardsTab = (
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
        width={560}
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
  );

  return (
    <PageShell title="安全控制中心" description="按装配十步组织（批13-W 终版）：配置挂实际影响的装配步骤，教学即运维；守卫是运行期裁决（热生效）独立保留">
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space size={16} wrap>
          <SafetyCertificateOutlined />
          <Text strong>模式预设：</Text>
          {presetMode === 'turbo' ? <Tag color="orange">当前：极速 turbo</Tag>
            : presetMode === 'safe' ? <Tag color="green">当前：安全 safe</Tag>
            : <Tag>当前：自定义</Tag>}
          <Button danger icon={<ThunderboltOutlined />} loading={presetLoading === 'turbo'}
            onClick={() => applyPreset('turbo')}>极速模式</Button>
          <Button type="primary" loading={presetLoading === 'safe'}
            onClick={() => applyPreset('safe')}>安全模式</Button>
          <Text type="secondary">
            极速=六站关+SQL安全/定位预算保留（零拒绝提速 2.2~2.4 倍）；安全=全站回位
          </Text>
        </Space>
      </Card>
      {/* 三轨M10(U5) §六：4Tab 重构——Tab2 装配十步=左锚点+右文档式（E-78② 裁定，
         2026-09-20 用户裁定优先于批13-W 十步平铺；面板组件零改动全复用） */}
      <Tabs
        defaultActiveKey="tab0"
        style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        items={[
          { key: 'tab0', label: '模式预设', children: <Tab0Panel /> },
          { key: 'guards', label: '守卫（运行期）', children: guardsTab },
          {
            key: 'steps', label: '装配十步',
            children: (
              <SecurityStepsAnchored
                renderStep={(s) =>
                  s === 8 ? <TeachPanel step={8} /> : s === 1 || s === 2 || s === 3 ? <TeachPanel step={s} /> : <CapabilityPanel stepFilter={s} />
                }
              />
            ),
          },
          { key: 'allcaps', label: '能力总览', children: <CapabilityPanel /> },
        ]}
      />
    </PageShell>
  );
};

export default SecurityControlCenter;


/**
 * SecurityStepsAnchored（三轨M10(U5) §六）：装配十步左锚点+右文档式容器。
 * 左=十步锚点列表（步号+标题+步头说明一行）；右=该步面板（复用既有组件零改动）。
 */
const SecurityStepsAnchored: React.FC<{
  renderStep: (step: number) => React.ReactNode;
}> = ({ renderStep }) => {
  const [active, setActive] = useState<number>(1);
  const steps = [1, 2, 3, 4, 5, 6, 7, 8, 10];
  return (
    <div
      data-testid="security-steps-anchored"
      style={{ display: 'flex', gap: 16, flex: 1, minHeight: 0, overflow: 'hidden' }}
    >
      <div
        style={{
          width: 232, flexShrink: 0, overflowY: 'auto',
          borderRight: `1px solid ${tokens.colors.border}`, paddingRight: 8,
        }}
      >
        {steps.map((s) => {
          const isActive = s === active;
          return (
            <div
              key={s}
              data-testid={`security-step-anchor-${s}`}
              onClick={() => setActive(s)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '9px 12px', marginBottom: 4, cursor: 'pointer',
                borderRadius: tokens.radius.default, fontSize: 13,
                background: isActive ? tokens.colors.primaryBg : 'transparent',
                color: isActive ? tokens.colors.primary : tokens.colors.textSecondary,
                fontWeight: isActive ? tokens.fontWeight.semibold : tokens.fontWeight.regular,
                borderLeft: isActive ? `3px solid ${tokens.colors.primary}` : '3px solid transparent',
              }}
            >
              <span style={{ fontSize: 11, opacity: 0.75 }}>{s}</span>
              {(STEP_TITLES[s] || `步${s}`).replace(/^步\d+\s*·\s*/, '')}
            </div>
          );
        })}
      </div>
      <div style={{ flex: 1, minWidth: 0, overflowY: 'auto' }}>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
          {STEP_TEACH[active]?.teach || ''}
        </Text>
        {renderStep(active)}
      </div>
    </div>
  );
};
