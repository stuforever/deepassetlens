import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Collapse, Empty, Space, Spin, Tag, Typography } from 'antd';
import type { RunEventRecord } from './types';
import { tokens } from '../../theme/tokens';
import { StatusTag, type StatusPreset } from '../shell';

const { Text } = Typography;

type StepStatus = 'running' | 'completed' | 'failed';

type TraceNode = {
  key: string;
  type: 'context' | 'step' | 'draft';
  step_order: number;
  runtime_context?: any;
  step_id?: string;
  step_name?: string;
  status?: StepStatus;
  skill_code?: string;
  duration_ms?: number | null;
  input?: any;
  output?: any;
  error?: any;
  logs?: string[];
  llm_stream?: string;
  draft_text?: string;
  draft_title?: string;
};

const STATUS_META: Record<StepStatus, { preset: StatusPreset; text: string; border: string; background: string }> = {
  running: { preset: 'info', text: '执行中', border: 'var(--color-primary-bg)', background: 'var(--color-primary-bg)' },
  completed: { preset: 'success', text: '已完成', border: 'var(--color-success-bg)', background: 'var(--color-success-bg)' },
  failed: { preset: 'error', text: '失败', border: 'var(--color-error-bg)', background: 'var(--color-error-bg)' },
};

const isPresent = (value: any) => value !== undefined && value !== null && !(typeof value === 'string' && value.trim() === '');

const normalizeStatus = (status: any): StepStatus => {
  if (status === 'failed') return 'failed';
  if (status === 'running') return 'running';
  return 'completed';
};

const prettyDuration = (value?: number | null) => {
  if (!value || value < 0) return '-';
  if (value >= 1000) return `${(value / 1000).toFixed(2)} s`;
  return `${value} ms`;
};

const renderJsonBlock = (value: any, emptyText: string) =>
  isPresent(value) ? (
    <pre
      style={{
        margin: 0,
        background: 'var(--bg-subtle)',
        padding: 8,
        borderRadius: 6,
        fontSize: 12,
        maxHeight: 220,
        overflow: 'auto',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-all',
      }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  ) : (
    <Text type="secondary">{emptyText}</Text>
  );

const buildExecutionTrace = (events: RunEventRecord[] = [], stepTrace: any[] = []): TraceNode[] => {
  const nodes: TraceNode[] = [];
  const stepMap = new Map<string, TraceNode>();
  let seenOrder = 0;

  // 1. 运行时上下文（第 0 步）
  const ctxEvent = events.find((e) => e?.event_type === 'context.prepared');
  const runtimeContext = ctxEvent?.payload?.runtime_context || null;
  if (runtimeContext) {
    nodes.push({ key: 'context', type: 'context', step_order: 0, runtime_context: runtimeContext });
  }

  // 2. 步骤节点（来自 step.started/completed/failed）
  events.forEach((event) => {
    if (!['step.started', 'step.completed', 'step.failed'].includes(event?.event_type || '')) return;
    const rawPayload = event?.payload || {};
    const payload = rawPayload?.payload && typeof rawPayload.payload === 'object' ? rawPayload.payload : rawPayload;
    const stepId = String(payload?.step_id || rawPayload?.step_id || '').trim();
    if (!stepId) return;
    const explicitOrder = Number(payload?.step_order ?? rawPayload?.step_order ?? 0);
    const stepOrder = explicitOrder > 0 ? explicitOrder : stepMap.get(stepId)?.step_order || ++seenOrder;
    const current: TraceNode = stepMap.get(stepId) || {
      key: stepId,
      type: 'step',
      step_id: stepId,
      step_name: payload?.step_name || payload?.name || stepId,
      step_order: stepOrder,
      status: 'running',
      logs: [],
    };
    current.step_name = payload?.step_name || payload?.name || current.step_name || stepId;
    current.step_order = stepOrder;
    current.skill_code = payload?.skill_code || current.skill_code;
    current.input = isPresent(payload?.input_payload) ? payload.input_payload : current.input;
    current.output = isPresent(payload?.output_payload) ? payload.output_payload : current.output;
    current.error = isPresent(payload?.error_message) ? payload.error_message : current.error;
    current.duration_ms = payload?.duration_ms ?? current.duration_ms ?? null;
    current.status = normalizeStatus(
      event?.event_type === 'step.completed' ? 'completed' : event?.event_type === 'step.failed' ? 'failed' : 'running'
    );
    stepMap.set(stepId, current);
  });

  // 3. stepTrace 补充（结果回填后的完整轨迹）
  (stepTrace || []).forEach((item, index) => {
    if (!item?.step_id) return;
    const sid = String(item.step_id);
    const existing = stepMap.get(sid);
    if (existing) {
      existing.input = isPresent(item.input) ? item.input : existing.input;
      existing.output = isPresent(item.output) ? item.output : existing.output;
      existing.error = isPresent(item.error) ? item.error : existing.error;
      existing.duration_ms = item.duration_ms ?? existing.duration_ms ?? null;
    } else {
      stepMap.set(sid, {
        key: sid,
        type: 'step',
        step_id: sid,
        step_name: item.step_name || item.name || sid,
        step_order: Number(item.step_order ?? index + 1),
        status: normalizeStatus(item.status),
        skill_code: item.skill_code,
        input: item.input,
        output: item.output,
        error: item.error,
        duration_ms: item.duration_ms ?? null,
        logs: [],
      });
    }
  });

  // 4. tool.delta 日志关联到步骤
  events.forEach((event) => {
    if (event?.event_type !== 'tool.delta') return;
    const p = event?.payload || {};
    const sid = String(p?.step_id || '').trim();
    const msg = p?.message;
    if (sid && msg && stepMap.has(sid)) {
      stepMap.get(sid)!.logs!.push(msg);
    }
  });

  // 5. assistant.delta 流式输出关联到 LLM 推理步骤（step5 / inference / llm）
  const llmDeltas = events.filter((e) => e?.event_type === 'assistant.delta');
  if (llmDeltas.length > 0) {
    const llmStep =
      Array.from(stepMap.values()).find((s) => /step5|inference|llm|推理/i.test(s.step_id || s.step_name || '')) ||
      null;
    const streamText = llmDeltas
      .map((e) => e?.payload?.delta || e?.payload?.text || '')
      .join('');
    if (llmStep) {
      llmStep.llm_stream = (llmStep.llm_stream || '') + streamText;
    }
  }

  const stepNodes = Array.from(stepMap.values()).sort((a, b) => a.step_order - b.step_order);
  nodes.push(...stepNodes);

  // 6. 助手回复草稿（最后一步）
  const blockEvents = events.filter((e) => e?.event_type === 'block.completed');
  if (blockEvents.length > 0) {
    const draftText = blockEvents
      .map((e) => e?.payload?.text || '')
      .join('')
      .trim();
    if (draftText) {
      nodes.push({
        key: 'draft',
        type: 'draft',
        step_order: 999,
        draft_text: draftText,
        draft_title: blockEvents[0]?.payload?.title || '助手回复草稿',
      });
    }
  }

  return nodes;
};

const WorkflowExecutionTimeline: React.FC<{
  title?: string;
  stepTrace?: any[];
  events?: RunEventRecord[];
  loading?: boolean;
  emptyText?: string;
}> = ({ title = '流程执行过程', stepTrace = [], events = [], loading = false, emptyText = '当前还没有步骤执行记录' }) => {
  const traceNodes = useMemo(() => buildExecutionTrace(events, stepTrace), [events, stepTrace]);
  const [activeKeys, setActiveKeys] = useState<string[]>([]);
  const initedRef = useRef(false);

  useEffect(() => {
    const runningKeys = traceNodes.filter((n) => n.status === 'running').map((n) => n.key);
    if (!initedRef.current) {
      initedRef.current = true;
      const contextKeys = traceNodes.filter((n) => n.type === 'context').map((n) => n.key);
      setActiveKeys([...contextKeys, ...runningKeys]);
    } else if (runningKeys.length > 0) {
      setActiveKeys((prev) => {
        const additions = runningKeys.filter((k) => !prev.includes(k));
        return additions.length > 0 ? [...prev, ...additions] : prev;
      });
    }
  }, [traceNodes]);

  if (traceNodes.length === 0) {
    return loading ? (
      <Space>
        <Spin size="small" />
        <Text type="secondary">等待流程开始并同步真实步骤事件...</Text>
      </Space>
    ) : (
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />
    );
  }

  const renderContextBody = (rc: any) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <Text type="secondary">{`场景：${rc?.scene_code || '-'} / 页面：${rc?.page_code || '-'}`}</Text>
      <Text type="secondary">{`工作区：${rc?.workspace?.workspace_code || '-'} / 会话轮数：${rc?.memory?.turn_count || 0}`}</Text>
      <Text type="secondary">{`近期话题：${(rc?.memory?.recent_topics || []).length ? rc.memory.recent_topics.join('、') : '无'}`}</Text>
    </div>
  );

  const renderLlmStream = (stream?: string) => {
    if (!stream) return null;
    const lines = stream.split('\n').filter((l) => l.trim());
    return (
      <div style={{ marginTop: 8 }}>
        <Text strong style={{ display: 'block', marginBottom: 4 }}>大模型流式输出（{lines.length} 行）</Text>
        <Collapse
          ghost
          size="small"
          defaultActiveKey={['llm-stream']}
          items={[{
            key: 'llm-stream',
            label: <Text type="secondary" style={{ fontSize: 12 }}>点击展开/收起</Text>,
            children: (
              <div
                style={{
                  background: 'var(--color-success-bg)',
                  color: 'var(--color-success)',
                  border: '1px solid var(--color-success-bg)',
                  padding: 10,
                  borderRadius: 6,
                  fontSize: 12,
                  fontFamily: 'SFMono-Regular, Consolas, monospace',
                  lineHeight: 1.6,
                  maxHeight: 320,
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {lines.map((line, i) => (
                  <div key={i} style={{ borderBottom: i < lines.length - 1 ? '1px dashed var(--border-strong)' : 'none', padding: '2px 0' }}>
                    <span style={{ color: 'var(--text-tertiary)', marginRight: 8 }}>{String(i + 1).padStart(2, '0')}</span>
                    {line}
                  </div>
                ))}
              </div>
            ),
          }]}
        />
      </div>
    );
  };

  return (
    <Collapse
      ghost
      activeKey={activeKeys}
      onChange={(keys) => setActiveKeys(Array.isArray(keys) ? keys.map(String) : keys ? [String(keys)] : [])}
      items={traceNodes.map((node, index) => {
        if (node.type === 'context') {
          return {
            key: node.key,
            label: (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Text strong>{`0. 运行时上下文`}</Text>
                <Tag>{node.runtime_context?.scene_code || '-'}</Tag>
              </div>
            ),
            children: renderContextBody(node.runtime_context),
          };
        }
        if (node.type === 'draft') {
          return {
            key: node.key,
            label: (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Text strong>{`助手回复草稿`}</Text>
                <StatusTag preset="ai">最终输出</StatusTag>
              </div>
            ),
            children: (
              <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: 'var(--bg-subtle)', padding: 10, borderRadius: 6 }}>
                {node.draft_text}
              </div>
            ),
          };
        }
        // step node
        const meta = STATUS_META[node.status || 'running'];
        const stepIndex = index;
        return {
          key: node.key,
          label: (
            <div style={{ border: `1px solid ${meta.border}`, background: meta.background, borderRadius: 12, padding: '8px 12px' }}>
              <Space align="start" style={{ width: '100%', justifyContent: 'space-between' }}>
                <div>
                  <Text strong style={{ display: 'block' }}>{`${stepIndex}. ${node.step_name}`}</Text>
                  <Space wrap size={[8, 4]}>
                    {node.skill_code ? <Text type="secondary" style={{ fontSize: 12 }}>{node.skill_code}</Text> : null}
                    <Text type="secondary" style={{ fontSize: 12 }}>{`耗时：${prettyDuration(node.duration_ms)}`}</Text>
                  </Space>
                </div>
                <StatusTag preset={meta.preset}>{meta.text}</StatusTag>
              </Space>
            </div>
          ),
          children: (
            <Space direction="vertical" style={{ width: '100%' }} size={10}>
              {node.logs && node.logs.length > 0 && (
                <div>
                  <Text strong style={{ display: 'block', marginBottom: 4 }}>执行日志</Text>
                  {node.logs.map((log, i) => (
                    <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '2px 0', whiteSpace: 'pre-wrap' }}>
                      <span style={{ color: tokens.colors.primary, marginRight: 6 }}>●</span>{log}
                    </div>
                  ))}
                </div>
              )}
              {renderLlmStream(node.llm_stream)}
              <div>
                <Text strong>真实输入</Text>
                <div style={{ marginTop: 6 }}>{renderJsonBlock(node.input, '该步骤暂无真实输入记录')}</div>
              </div>
              <div>
                <Text strong>真实输出</Text>
                <div style={{ marginTop: 6 }}>{renderJsonBlock(node.output, '该步骤暂无真实输出记录')}</div>
              </div>
              {isPresent(node.error) ? (
                <div>
                  <Text strong>错误</Text>
                  <div style={{ marginTop: 6 }}>{renderJsonBlock(node.error, '该步骤没有错误')}</div>
                </div>
              ) : null}
            </Space>
          ),
        };
      })}
    />
  );
};

export default WorkflowExecutionTimeline;
