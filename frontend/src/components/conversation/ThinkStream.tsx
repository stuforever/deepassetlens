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
  kind?: 'plan' | 'skill' | 'decision' | 'draft' | 'answer';  // 规划(write_todos) | 技能调用 | 判定决策(LLM推理) | 答案草稿流式(不进总结) | 最终答案生成(answer_committed)
  result_summary?: string;  // 工具返回的自然语言结论
  input_summary?: string;   // 工具输入参数摘要
  raw_log?: string;         // 原始工具日志（kg_api 返回的 log 字段）
  draft?: string;           // 最终答案草稿流式(小探思考区, 实时打字; 完成后保留作为推理记录, phase:'done' 时停光标)
  // v3.4 实时流式字段
  phase?: 'drafting' | 'committed' | 'running' | 'done' | 'error' | 'rejected' | 'cancelled';  // 单一阶段状态机
  step_id?: number;         // 步骤序号(前端按 id 区分同名步骤)
  step_no?: number;
  tool_name?: string;
  tool_call_id?: string;
  round_id?: string;        // LLM 推理轮 id(草稿按 round_id 归并)
  sql_full?: string;        // execute_sql 完整语句
  started_at_ms?: number;   // 工具开始执行时间戳(前端算实时耗时)
  duration_ms?: number;     // 工具完成耗时
  reject_reason?: string;   // 闸门拒绝原因（范围校验失败等具体原因）
  candidate_content?: string; // 闸门拒绝时 LLM 实际写的候选内容
  retry_of_step?: number;   // R1: 补判重试关联的被拒绝步骤号（前端显示"修正#N"）
  superseded?: boolean;     // R1: 被后续重试取代的 rejected 步骤标记
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

/* 实时耗时计时器：工具 running 期间每秒刷新已耗时, started_at_ms 为起点 */
const LiveTimer: React.FC<{ startedAtMs?: number }> = ({ startedAtMs }) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!startedAtMs) return;
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, [startedAtMs]);
  if (!startedAtMs) return null;
  const elapsed = Math.max(0, now - startedAtMs);
  const secs = (elapsed / 1000).toFixed(1);
  return (
    <Text style={{ fontSize: 10, color: tokens.colors.primary, fontFamily: 'Consolas, monospace' }}>
      {secs}s
    </Text>
  );
};

/* result_status 中文映射（批13-Q：原值 locked/rejected 对用户不可读） */
const _STATUS_CN: Record<string, string> = {
  done: '已完成',
  running: '执行中',
  error: '执行异常',
  rejected: '已拦截',
  locked: '已锁定交付',
};

/* JSX 缩进清洗（批13-Q：pre-wrap 会把模板缩进空格原样渲染成大段空白） */
const _tidy = (s?: string | null): string =>
  typeof s === 'string' ? s.replace(/[ \t]+/g, ' ').trim() : '';

/* 步骤项：一级(标题+状态) / 二级(技术日志)，点击一级展开二级。 */
const StepItem: React.FC<{ item: ThinkItem; index: number; isLast: boolean; isActive: boolean }> = ({ item, index, isLast, isActive }) => {
  const [expanded, setExpanded] = useState(false);
  const detailRef = useRef<HTMLDivElement>(null);

  const strat = STRATEGY_LABEL[item.strategy || ''] || { label: item.strategy || '未知', preset: 'default' as StatusPreset };
  const isLocked = item.locked === true || item.result_status === 'locked';
  const isErr = item.result_status === 'error';
  const isRejected = item.phase === 'rejected' || item.result_status === 'rejected';
  const isRunning = item.phase === 'running' || item.result_status === 'running';
  const isDrafting = item.phase === 'drafting';
  const isInProgress = isRunning || isDrafting;
  const hasProcess = item.process && typeof item.process === 'object' && Object.keys(item.process).length > 0;
  const stepRef = useRef<HTMLDivElement>(null);
  const _stepNo = item.step_no;
  const _toolName = item.tool_name;
  const _durMs = item.duration_ms;

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
          answer:   { icon: <BulbOutlined style={{ color: 'var(--bg-content)', fontSize: 10 }} />,  active: 'var(--color-ai)', done: '#d3adf7' },
        };
        const ks = KIND_ICON[item.kind || 'skill'] || KIND_ICON.skill;
        // 进行中(running/drafting)用 active 色, 拒绝用 error 色, 否则按 isActive
        const bg = isLocked ? 'var(--color-error)' : isRejected ? 'var(--color-warning, #faad14)' : (isActive || isInProgress) ? ks.active : ks.done;
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
        {_stepNo ? <Text style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-tertiary)', fontFamily: 'Consolas, monospace' }}>#{_stepNo}</Text> : null}
        <Text style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.task || ''}</Text>
        {/* 一级摘要：running 显示"正在执行...", drafting 显示"判定中...", rejected 显示失败原因摘要; 否则 result_summary */}
        {isRunning ? (
          <Text style={{ fontSize: 12, color: tokens.colors.primary, flex: 1, minWidth: 0 }}>- 正在执行...<DotAnimation /></Text>
        ) : isDrafting ? (
          <Text style={{ fontSize: 12, color: 'var(--color-ai)', flex: 1, minWidth: 0 }}>- 判定中...<DotAnimation /></Text>
        ) : isRejected ? (
          <Text style={{ fontSize: 12, color: 'var(--color-warning, #faad14)', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            - {(item.reject_reason || item.result_summary || '判定需补充信息·补判中').slice(0, 60)}
          </Text>
        ) : item.result_summary ? (
          <Text style={{ fontSize: 12, color: isErr ? 'var(--color-error)' : 'var(--color-success)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, minWidth: 0 }}>- {item.result_summary}</Text>
        ) : null}
        {/* R1: 修正后重试标记--关联到被拒绝的步骤 */}
        {item.retry_of_step ? (
          <Text style={{ fontSize: 10, color: 'var(--color-warning, #faad14)', fontStyle: 'italic' }}>↻ 修正#{item.retry_of_step}</Text>
        ) : null}
        <StatusTag preset={strat.preset} style={{ margin: 0, fontSize: 11 }}>{strat.label}</StatusTag>
        {item.action ? <Text type="secondary" style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.action}</Text> : null}
        {_toolName ? <Text code style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>{_toolName}</Text> : null}
        {/* 耗时：running 显示实时计时器, 完成后显示 duration_ms */}
        {isRunning && item.started_at_ms ? (
          <LiveTimer startedAtMs={item.started_at_ms} />
        ) : _durMs != null ? (
          <Text style={{ fontSize: 10, color: 'var(--text-tertiary)', fontFamily: 'Consolas, monospace' }}>{_durMs >= 1000 ? `${(_durMs / 1000).toFixed(1)}s` : `${_durMs}ms`}</Text>
        ) : null}
        <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{expanded ? '▾' : '▸'}</Text>
      </div>

      {/* v3.5: 折叠态判断文本预览 -- 无需展开就能看懂"为什么进入下一步"（2行截断） */}
      {!expanded && item.live_reason ? (
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, marginTop: 2, paddingLeft: 0,
                     overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as any }}>
          {item.live_reason.replace(/^【下一步判断】\s*\n?/, '').trim()}
        </div>
      ) : null}

      {/* 二级展开内容：看二级动态，自动滚动跟随最新 */}
      {expanded ? (
        <div ref={detailRef} style={{ paddingBottom: 8 }}>
          {/* 答案草稿流式（draft）：最终答案实时打字，紫色主题，带光标（完成后停光标） */}
          {item.draft ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-ai)' }}><BulbOutlined /> 答案生成：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>
                {item.draft}
                {item.phase !== 'done' ? (
                  <span style={{ display: 'inline-block', width: 6, height: 12, background: 'var(--color-ai)', marginLeft: 2, animation: 'ts-draft-cursor 1s step-end infinite', verticalAlign: 'middle' }} />
                ) : null}
              </Text>
              <style>{`@keyframes ts-draft-cursor { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }`}</style>
            </div>
          ) : null}

          {/* LLM 实时流式推理（live_reason）：模型同轮"下一步判断"(已知/判断/因此)，紫色主题 */}
          {item.live_reason ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-ai)' }}><BulbOutlined /> 为什么执行这一步：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>
                {item.live_reason}
                {isInProgress ? (
                  <span style={{ display: 'inline-block', width: 6, height: 12, background: 'var(--color-ai)', marginLeft: 2, animation: 'ts-cursor 1s step-end infinite', verticalAlign: 'middle' }} />
                ) : null}
              </Text>
              <style>{`@keyframes ts-cursor { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }`}</style>
            </div>
          ) : null}

          {/* 技术明细(思考过程/技能执行/SQL/结果)，展开即全部可见 */}
          {/* LLM 思考过程（reason），紫色主题 */}
          {item.reason ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-ai)' }}><BulbOutlined /> 思考过程：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>{_tidy(item.reason)}</Text>
            </div>
          ) : null}

          {/* 技能执行（detail）：自然语言描述 + 输入摘要，蓝色主题 */}
          {item.detail ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: tokens.colors.primary }}><ToolOutlined /> 技能执行：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>{_tidy(item.detail)}</Text>
              {item.input_summary ? (
                <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4, fontFamily: 'Consolas, Monaco, monospace' }}>{_tidy(item.input_summary)}</Text>
              ) : null}
            </div>
          ) : null}

          {/* 完整 SQL（sql_full）：execute_sql 时后端推送的完整语句, 可复制, 等宽字体折叠 */}
          {item.sql_full ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6, border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <Text style={{ fontSize: 11, fontWeight: 600, color: tokens.colors.primary }}><ToolOutlined /> 执行SQL：</Text>
                <Text copyable={{ text: item.sql_full }} style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>复制</Text>
              </div>
              <pre style={{
                margin: 0, padding: 8, fontSize: 11, lineHeight: 1.5, maxHeight: 200, overflow: 'auto',
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--text-primary)',
                background: 'var(--bg-content)', borderRadius: 4,
              }}>
{item.sql_full}
              </pre>
            </div>
          ) : null}

          {/* 步骤结果表（sql_result）：该步 execute_sql 返回的数据, 前10行预览 + 行数 */}
          {(() => {
            const sr = (item as any).sql_result;
            if (!sr || !sr.columns || !sr.columns.length) return null;
            const cols = sr.columns.slice(0, 6);
            const previewRows = (sr.rows || []).slice(0, 10);
            return (
              <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
                <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-success)' }}>返回 {sr.row_count || 0} 行{sr.row_count > 10 ? '（预览前10行）' : ''}：</Text>
                <div style={{ marginTop: 4, overflowX: 'auto' }}>
                  <table style={{ borderCollapse: 'collapse', fontSize: 11, width: '100%' }}>
                    <thead>
                      <tr>{cols.map((c: string, i: number) => (<th key={i} style={{ border: '1px solid var(--border-color)', padding: '3px 6px', background: 'var(--bg-content)', textAlign: 'left', whiteSpace: 'nowrap' }}>{c}</th>))}</tr>
                    </thead>
                    <tbody>
                      {previewRows.map((r: any[], i: number) => (
                        <tr key={i}>{cols.map((c: string, j: number) => (<td key={j} style={{ border: '1px solid var(--border-color)', padding: '3px 6px', whiteSpace: 'nowrap', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>{String(r[j] ?? '')}</td>))}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })()}

          {/* 结果结论（result_summary）：绿色主题，自然语言结论 */}
          {item.result_summary ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: isRejected ? 'var(--color-warning, #faad14)' : 'var(--color-success)' }}>{isRejected ? '判定结果：' : '获取结果：'}</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>{_tidy(item.result_summary)}</Text>
            </div>
          ) : null}

          {/* 拒绝原因（reject_reason）：警告色，闸门给出的具体原因 */}
          {isRejected && item.reject_reason ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'rgba(250, 173, 20, 0.08)', borderRadius: 6, border: '1px solid rgba(250, 173, 20, 0.2)' }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-warning, #faad14)' }}>拒绝原因：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>{_tidy(item.reject_reason)}</Text>
            </div>
          ) : null}

          {/* 候选内容（candidate_content）：紫色主题，LLM 实际写的被拒内容 */}
          {isRejected && item.candidate_content ? (
            <div style={{ marginBottom: 6, padding: '8px 10px', background: 'rgba(114, 46, 209, 0.06)', borderRadius: 6 }}>
              <Text style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-ai, #722ed1)' }}>候选内容（被拒）：</Text>
              <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>{_tidy(item.candidate_content)}</Text>
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

          {item.result_status && item.result_status !== 'done' ? (
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 11, fontWeight: 600 }}>状态: </Text>
              {/* 批13-Q：result_status 原值（locked/rejected/error）直出对用户不可读，映射中文 */}
              <StatusTag
                preset={item.result_status === 'locked' ? 'success' : (item.result_status === 'error' || item.result_status === 'rejected') ? 'error' : 'warning'}
                style={{ fontSize: 11 }}
              >
                {_STATUS_CN[item.result_status] || item.result_status}
              </StatusTag>
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
  traces?: any[];
}> = ({ items, active = false, liveStatus, metaInfo, traces }) => {
  // 点击步骤展开/折叠，展开即看全部详细日志（思考过程/技能执行/SQL/结果）
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastStepRef = useRef<HTMLDivElement>(null);
  // 用户定调（2026-08-24）：头部可点击折叠/展开全部步骤日志，默认折叠——
  // 折叠时头部标题仍是实时状态投影（进展可见），展开才显示历史轨迹明细
  const [collapsed, setCollapsed] = useState(true);

  // 自动滚动到最新内容（折叠时不滚动）
  useEffect(() => {
    if (!collapsed && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [items, liveStatus, collapsed]);

  if (!items || items.length === 0 && !liveStatus) return null;

  // 批13-O：头部标题 = 实时状态投影（单一状态源）。active 且上游传入动态文案时，
  // 替换静态「正在定位数据」——进展在最上面随框架事件实时变化；无信号时回落原文案。
  const title = active ? (liveStatus || '小探 正在定位数据...') : '小探 已准备好答案';
  const meta = active
    ? `正在推理 · 已定位 ${items.length} 步`
    : `推理完成 · 定位 ${items.length} 步`;

  return (
    <div style={{ marginBottom: 8 }}>
      {/* 头部(标题+步数摘要)，整行可点击折叠/展开步骤日志 */}
      <div
        onClick={() => setCollapsed((c) => !c)}
        style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0, cursor: 'pointer', userSelect: 'none' }}
        title={collapsed ? '展开执行日志' : '收起执行日志'}
      >
        <EyeIcon spinning={active && !collapsed ? true : active} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
            {title}
            {active ? <DotAnimation /> : null}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>{meta}</div>
        </div>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)', flexShrink: 0 }}>{collapsed ? '▸ 展开' : '▾ 收起'}</span>
      </div>

      {/* 步骤列表(两级: 一级标题+状态 / 二级技术日志)；默认折叠，点头部展开 */}
      {!collapsed ? (
      <div ref={scrollRef} style={{ padding: '4px 14px 12px 34px' }}>
        <div ref={lastStepRef}>
          {items.map((item, idx) => (
            <StepItem
              key={(item.tool_call_id || (item.step_id != null ? `s${item.step_id}` : '') || item.round_id || idx) as any}
              item={item}
              index={idx}
              isLast={idx === items.length - 1}
              isActive={active && idx === items.length - 1}
            />
          ))}
          {/* 执行轨迹(trace) */}
          {traces && traces.length > 0 ? (
            <details style={{ marginTop: 8, paddingLeft: 0 }}>
              <summary style={{ fontSize: 11, color: 'var(--text-tertiary)', cursor: 'pointer', padding: '4px 0', fontWeight: 600 }}>🔎 执行轨迹（{traces.length} 条）</summary>
              <div style={{ marginTop: 4 }}>
                {traces.map((t, i) => (
                  <div key={i} style={{ fontSize: 11, lineHeight: 1.7, padding: '2px 0 2px 8px', borderLeft: '2px solid var(--border-color)', marginBottom: 2 }}>
                    <Text style={{ fontWeight: 600, color: tokens.colors.primary }}>{t.node || ''}</Text>
                    {t.status ? <Text type="secondary" style={{ margin: '0 4px' }}>· {t.status}</Text> : null}
                    {typeof t.row_count === 'number' ? <Text style={{ color: 'var(--color-success)' }}>· {t.row_count} 行</Text> : null}
                    {t.l2_name ? <Text type="secondary" style={{ marginLeft: 4 }}>· {t.l2_name}</Text> : null}
                    {t.detail ? <Text type="secondary" style={{ display: 'block', color: 'var(--text-tertiary)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{t.detail}</Text> : null}
                  </div>
                ))}
              </div>
            </details>
          ) : null}
          {/* 批13-O：liveStatus 已上移至头部标题位（单一状态源，不在步骤列表底部重复显示） */}
        </div>
      </div>
      ) : null}

      <style>{`
        @keyframes ts-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
      `}</style>
    </div>
  );
};

export default ThinkStream;
