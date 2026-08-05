/**
 * 思考面板 - Trae 风格
 *
 * 设计原则（对齐 Trae IDE 对话风格）：
 *   1. 固定高度区域，内部滚动，不撑开外层布局
 *   2. 折叠态：约 7-8 行高度，只显示最新内容，自动滚到底部
 *   3. 展开态：显示全部步骤，自动滚动到最新执行中的步骤
 *   4. 二级（步骤内）展开：看二级动态，自动跟随；二级完成后点折叠回到一级
 *   5. 永远定位最新，滚动效果
 */
import React, { useState, useEffect, useRef } from 'react';
import { Typography } from 'antd';
import { EyeOutlined, CheckCircleFilled, ToolOutlined, BulbOutlined, FlagOutlined } from '@ant-design/icons';
import { tokens } from '../../theme/tokens';
import { StatusTag, type StatusPreset } from '../shell';

const { Text } = Typography;

export type ThinkItem = {
  task?: string;
  attempt?: number;
  strategy?: string;
  action?: string;
  reason?: string;
  live_reason?: string;
  result_status?: string;
  candidates_count?: number;
  locked?: boolean;
  level?: string;
  code?: string;
  input_query?: string;
  process?: any;
  todos?: { content: string; status: string }[];
  detail?: string;  // 工具调用详细日志（kg_api 返回的 log 字段）
  kind?: 'plan' | 'skill' | 'decision';  // 规划(write_todos) | 技能调用 | 判定决策(LLM推理)
  result_summary?: string;  // 工具返回的自然语言结论
  input_summary?: string;   // 工具输入参数摘要
  raw_log?: string;         // 原始工具日志（kg_api 返回的 log 字段）
};

const STRATEGY_LABEL: Record<string, { label: string; preset: StatusPreset }> = {
  vector_llm: { label: '向量召回+LLM', preset: 'info' },
  vector_recall: { label: '向量召回', preset: 'info' },
  llm_classify: { label: 'LLM推理+分类', preset: 'ai' },
  precise_query: { label: '精准查询', preset: 'success' },
  llm_infer: { label: 'LLM推理', preset: 'ai' },
  graph_retrieve_llm: { label: '图谱检索+LLM', preset: 'info' },
  graph_traverse: { label: '图谱遍历', preset: 'info' },
  llm_generate: { label: 'LLM生成', preset: 'ai' },
  rule_assemble: { label: '规则拼装', preset: 'warning' },
  tool_call: { label: '工具调用', preset: 'info' },
  todo_plan: { label: '任务规划', preset: 'info' },
};

/* 眼睛图标：旋转=思考中，静态=已完成 */
const EyeIcon: React.FC<{ spinning: boolean }> = ({ spinning }) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 20, height: 20, borderRadius: '50%', background: tokens.colors.primary, flexShrink: 0 }}>
    <EyeOutlined style={{ color: 'var(--bg-content)', fontSize: 11, animation: spinning ? 'eye-spin 1.5s linear infinite' : 'none' }} />
    <style>{`@keyframes eye-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
  </span>
);

/* 动态点点动画 */
const DotAnimation: React.FC = () => (
  <span style={{ display: 'inline-flex', gap: 3, marginLeft: 6, verticalAlign: 'middle' }}>
    <span className="ts-dot" />
    <span className="ts-dot" />
    <span className="ts-dot" />
    <style>{`
      .ts-dot { width: 4px; height: 4px; border-radius: 50%; background: var(--color-primary); display: inline-block; animation: ts-bounce 1.2s infinite ease-in-out; }
      .ts-dot:nth-child(2) { animation-delay: 0.15s; }
      .ts-dot:nth-child(3) { animation-delay: 0.3s; }
      @keyframes ts-bounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-4px); opacity: 1; } }
    `}</style>
  </span>
);

/* 步骤项：二级展开看动态，完成后可折叠回一级 */
const StepItem: React.FC<{ item: ThinkItem; index: number; isLast: boolean; isActive: boolean }> = ({ item, index, isLast, isActive }) => {
  // 活跃步骤或有内容的已完成步骤都默认展开（reason/process/level/code 等任一非空）
  // 这样查历史对话时推理详情可见，不需要挨个点开
  const hasDetail = Boolean(
    item.reason || item.live_reason || item.process || item.result_status ||
    item.detail ||
    (item.level && item.code) || typeof item.candidates_count === 'number'
  );
  const [expanded, setExpanded] = useState(false);
  const detailRef = useRef<HTMLDivElement>(null);

  // 步骤详情默认折叠，用户主动点击 ▸ 展开（任意折叠/展开，不自动展开）

  const strat = STRATEGY_LABEL[item.strategy || ''] || { label: item.strategy || '未知', preset: 'default' as StatusPreset };
  const isLocked = item.locked === true || item.result_status === 'locked';
  const hasProcess = item.process && typeof item.process === 'object' && Object.keys(item.process).length > 0;
  const stepRef = useRef<HTMLDivElement>(null);

  return (
    <div ref={stepRef} style={{ position: 'relative', paddingLeft: 28, paddingBottom: isLast ? 0 : 4 }}>
      {/* 左侧蓝色竖线 */}
      {!isLast ? (
        <div style={{ position: 'absolute', left: 9, top: 24, bottom: 0, width: 2, background: tokens.colors.primary, opacity: 0.3 }} />
      ) : null}
      {/* 步骤图标：三类完全不同 - plan(规划-橙旗帜) / skill(技能-蓝工具) / decision(判定-紫灯泡)，locked覆盖为红对勾 */}
      {(() => {
        const KIND_ICON: Record<string, { icon: React.ReactNode; active: string; done: string }> = {
          plan:     { icon: <FlagOutlined style={{ color: 'var(--bg-content)', fontSize: 10 }} />,  active: '#fa8c16' /* domain color for plan step */, done: '#ffd591' },
          skill:    { icon: <ToolOutlined style={{ color: 'var(--bg-content)', fontSize: 10 }} />,  active: tokens.colors.primary, done: 'var(--border-color)' },
          decision: { icon: <BulbOutlined style={{ color: 'var(--bg-content)', fontSize: 10 }} />,  active: 'var(--color-ai)', done: '#d3adf7' /* 决策完成态浅紫，无对应 token */ },
        };
        const ks = KIND_ICON[item.kind || 'skill'] || KIND_ICON.skill;
        const bg = isLocked ? 'var(--color-error)' : isActive ? ks.active : ks.done;
        const icon = isLocked ? <CheckCircleFilled style={{ color: 'var(--bg-content)', fontSize: 12 }} /> : ks.icon;
        return (
          <div style={{ position: 'absolute', left: 0, top: 2, width: 20, height: 20, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: bg, flexShrink: 0 }}>
            {icon}
          </div>
        );
      })()}

      {/* 步骤头部（点击切换二级展开） */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', minHeight: 24, marginBottom: expanded ? 6 : 0 }}
      >
        <Text style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.task || ''}</Text>
        <StatusTag preset={strat.preset} style={{ margin: 0, fontSize: 11 }}>{strat.label}</StatusTag>
        {item.action ? <Text type="secondary" style={{ fontSize: 12, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.action}</Text> : null}
        {isActive ? <DotAnimation /> : null}
        <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{expanded ? '▾' : '▸'}</Text>
      </div>

      {/* 二级展开内容：看二级动态，自动滚动跟随最新 */}
      {expanded ? (
        <div ref={detailRef} style={{ paddingBottom: 8 }}>
          {/* LLM 实时流式推理（live_reason）：逐 token 显示，光标闪烁，紫色主题 */}
          {item.live_reason ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-ai)' }}><BulbOutlined /> 思考决策：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>
                {item.live_reason}
                <span style={{ display: 'inline-block', width: 6, height: 12, background: 'var(--color-ai)', marginLeft: 2, animation: 'ts-cursor 1s step-end infinite', verticalAlign: 'middle' }} />
              </Text>
              <style>{`@keyframes ts-cursor { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }`}</style>
            </div>
          ) : null}

          {/* LLM 思考过程（reason），紫色主题 */}
          {item.reason ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-ai)' }}><BulbOutlined /> LLM 推理：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>
                {item.reason}
              </Text>
            </div>
          ) : null}

          {/* 技能执行（detail）：自然语言描述 + 输入摘要，蓝色主题 */}
          {item.detail ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: tokens.colors.primary }}><ToolOutlined /> 技能执行：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>
                {item.detail}
              </Text>
              {item.input_summary ? (
                <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4, fontFamily: 'Consolas, Monaco, monospace' }}>
                  {item.input_summary}
                </Text>
              ) : null}
            </div>
          ) : null}

          {/* 结果结论（result_summary）：绿色主题，自然语言结论 */}
          {item.result_summary ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-success)' }}>获取结果：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>
                {item.result_summary}
              </Text>
            </div>
          ) : null}

          {/* 原始工具日志（raw_log）：等宽字体，折叠展示 */}
          {item.raw_log ? (
            <details style={{ marginBottom: 6 }}>
              <summary style={{ fontSize: 11, color: 'var(--text-tertiary)', cursor: 'pointer', padding: '2px 0' }}>原始日志</summary>
              <pre style={{
                margin: '4px 0 0 0', padding: 8, fontSize: 11, lineHeight: 1.6,
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--text-secondary)',
                background: 'var(--bg-subtle)', border: '1px solid var(--border-color)', borderRadius: 4,
              }}>
                {item.raw_log}
              </pre>
            </details>
          ) : null}

          {item.result_status ? (
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 11, fontWeight: 600 }}>结果: </Text>
              <StatusTag preset={item.result_status === 'locked' ? 'success' : 'warning'} style={{ fontSize: 11 }}>{item.result_status}</StatusTag>
              {typeof item.candidates_count === 'number' ? <Text type="secondary" style={{ fontSize: 11 }}> ({item.candidates_count} 候选)</Text> : null}
            </div>
          ) : null}

          {item.locked && item.level ? (
            <div style={{ marginBottom: 4 }}>
              <StatusTag preset="info">{item.level}</StatusTag>
              {item.code ? <Text code style={{ fontSize: 11 }}>{item.code}</Text> : null}
            </div>
          ) : null}

          {item.input_query ? (
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 11, fontWeight: 600 }}>查询: </Text>
              <span style={{ display: 'inline-block', background: 'var(--bg-hover)', borderRadius: 4, padding: '2px 8px', fontSize: 11, color: 'var(--text-secondary)' }}>🔍 {item.input_query}</span>
            </div>
          ) : null}

          {/* #9: 任务清单（write_todos 产出，来自 process.todos） */}
          {(() => {
            const todos = item.todos || (item.process?.todos);
            if (!Array.isArray(todos) || todos.length === 0) return null;
            const colorMap: Record<string, string> = { pending: 'var(--text-tertiary)', in_progress: tokens.colors.primary, completed: 'var(--color-success)' };
            const bgMap: Record<string, string> = { pending: 'var(--bg-hover)', in_progress: 'var(--color-primary-bg)', completed: 'var(--color-success-bg)' };
            return (
              <div style={{ marginBottom: 6, padding: 8, background: 'var(--bg-content)', borderRadius: 4, border: '1px solid var(--border-color)' }}>
                <Text type="secondary" style={{ fontSize: 11, fontWeight: 600 }}>📋 任务清单</Text>
                <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {todos.map((t, i) => {
                    const st = t.status || 'pending';
                    return (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, padding: '2px 6px', background: bgMap[st] || 'var(--bg-hover)', borderRadius: 3 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: colorMap[st] || 'var(--text-tertiary)', flexShrink: 0 }} />
                        <Text style={{ fontSize: 11, color: colorMap[st] || 'var(--text-secondary)', textDecoration: st === 'completed' ? 'line-through' : 'none' }}>{t.content}</Text>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}

          {hasProcess ? <ProcessDetail process={item.process} /> : null}
        </div>
      ) : null}
    </div>
  );
};

const ProcessDetail: React.FC<{ process: any }> = ({ process }) => {
  if (!process || typeof process !== 'object') return null;
  const entries = Object.entries(process);
  return (
    <div style={{ marginTop: 4, padding: 8, background: 'var(--bg-content)', borderRadius: 4, border: '1px solid var(--border-color)' }}>
      <Text type="secondary" style={{ fontSize: 11, fontWeight: 600 }}>📋 详细过程</Text>
      <div style={{ marginTop: 4 }}>
        {entries.map(([key, val]) => (
          <div key={key} style={{ marginTop: 4, fontSize: 11, lineHeight: 1.6 }}>
            <Text type="secondary" style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{key}: </Text>
            {renderVal(key, val)}
          </div>
        ))}
      </div>
    </div>
  );
};

const renderVal = (key: string, val: any): React.ReactNode => {
  if (val === null || val === undefined) return <Text type="secondary" style={{ fontSize: 11 }}>无</Text>;
  if (val === '') return <Text type="secondary" style={{ fontSize: 11 }}>(空)</Text>;
  if (typeof val === 'string') {
    if (val.length > 200) {
      return <Text style={{ fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginLeft: 8, color: 'var(--text-secondary)', background: 'var(--bg-hover)', padding: 4, borderRadius: 3 }}>{val}</Text>;
    }
    return <Text style={{ fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--text-secondary)' }}>{val}</Text>;
  }
  if (typeof val === 'number' || typeof val === 'boolean') return <Text style={{ fontSize: 11, color: tokens.colors.primary }}>{String(val)}</Text>;
  if (Array.isArray(val)) {
    if (val.length === 0) return <Text type="secondary" style={{ fontSize: 11 }}>[]</Text>;
    return (
      <div style={{ marginTop: 2, marginLeft: 8 }}>
        {val.map((item, i) => (
          <div key={i}>
            {typeof item === 'object' && item !== null ? (
              <Text code style={{ fontSize: 10, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(item)}</Text>
            ) : (
              <Text style={{ fontSize: 11, color: 'var(--text-secondary)' }}>· {String(item)}</Text>
            )}
          </div>
        ))}
      </div>
    );
  }
  if (typeof val === 'object') {
    const json = JSON.stringify(val, null, 1);
    return <Text code style={{ fontSize: 10, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', color: 'var(--text-secondary)' }}>{json}</Text>;
  }
  return <Text style={{ fontSize: 11 }}>{String(val)}</Text>;
};

/* 主组件：Trae 风格固定高度 + 内部滚动 + 自动定位最新 */
const ThinkStream: React.FC<{
  items: ThinkItem[];
  active?: boolean;
  liveStatus?: string;
  metaInfo?: string;
}> = ({ items, active = false, liveStatus, metaInfo }) => {
  // 折叠策略：
  // - active=true（当前正在流式）→ 默认展开，让用户看到实时推理
  // - active=false（历史消息）→ 默认折叠，避免历史会话信息过载
  // 用户可手动点击展开/折叠
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastStepRef = useRef<HTMLDivElement>(null);

  // 始终折叠：用户主动点击 ▾ 才展开，不因 active 自动展开

  // 自动滚动到最新内容（折叠态和展开态都滚）
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [items, liveStatus, expanded]);

  if (!items || items.length === 0 && !liveStatus) return null;

  const title = active ? '数据助手 正在定位数据...' : '数据助手 已准备好答案';
  const meta = metaInfo || (active
    ? `正在推理 · 已定位 ${items.length} 步`
    : `推理完成 · 定位 ${items.length} 步`);

  return (
    <div style={{
      marginBottom: 8,
    }}>
      {/* 头部 */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}
      >
        <EyeIcon spinning={active} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
            {title}
            {active ? <DotAnimation /> : null}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>{meta}</div>
        </div>
        <Text style={{ fontSize: 14, color: 'var(--text-tertiary)' }}>{expanded ? '▴' : '▾'}</Text>
      </div>

      {/* 内容区：固定高度 + 内部滚动 + 自动定位最新 */}
      <div
        ref={scrollRef}
        style={{
          padding: '4px 14px 12px 34px',
        }}
      >
        {!expanded ? (
          // 折叠态：只头部入口一行；内容区仅流式中显示 liveStatus
          liveStatus ? (
            <div ref={lastStepRef} style={{ paddingBottom: 4 }}>
              <Text style={{ fontSize: 12, color: tokens.colors.primary }}>{liveStatus}</Text>
            </div>
          ) : null
        ) : (
          // 展开态：全部步骤时间线，自动滚动到最新
          <div ref={lastStepRef}>
            {items.map((item, idx) => (
              <StepItem
                key={idx}
                item={item}
                index={idx}
                isLast={idx === items.length - 1}
                isActive={active && idx === items.length - 1}
              />
            ))}
          </div>
        )}
      </div>

      <style>{`
        @keyframes ts-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
      `}</style>
    </div>
  );
};

export default ThinkStream;
