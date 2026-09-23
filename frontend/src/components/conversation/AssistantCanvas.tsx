/**
 * AssistantCanvas - 单画布连续流（豆包/ZCode/同花顺风格）
 *
 * 最终结果交付展示（统一交付协议，页面顺序固定）：
 *   0. 思考过程：ThinkStream 折叠控件，默认折叠
 *   1. 最终结果标题（final_delivery.title，兜底"查询结果"）
 *   2. 摘要 / 关键发现 / 告警（final_delivery.summary / findings / warnings）
 *   3. 答案正文：ReactMarkdown 连续渲染 final_answer（## 标题 + 表格 + 代码块 + 列表）
 *   4. 查询结果表格（sql_result，前端分页；row_count > 0 时无论模型是否生成文本都显示）
 *   5. 推荐问题：融入画布底部，虚线分隔，可点击
 *   6. SQL 与执行过程：默认折叠
 *
 * 降级提示只说明"结果已基于实际查询数据生成"，不放在业务用户主视图造成"答案不可靠"感受。
 * 配色全部走 token，零硬编码。
 */
import React, { useState } from 'react';
import { Collapse, Spin, Tag, Tooltip, Typography } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ThinkStream from './ThinkStream';
import SqlResultTable from './SqlResultTable';
import ContractCardsPanel from './contractCards/ContractCardsPanel';
import EvidenceCapsule, { evidenceToSources } from '../chat/EvidenceCapsule';
import type { ChatMessagePayload, FinalFinding } from './types';
import { buildFinalDeliveryView } from '../../utils/finalDelivery';
import { tokens } from '../../theme/tokens';

const { Text } = Typography;

// 批⓪ ContractCardsPanel 前台折叠下线：对话页只留「发问-回答-依据」（v4 §十二.3），
// 路由/契约/策略/模板字样移后台——批⑥ 引擎台「路由模拟」Tab 复用本组件。
const CONTRACT_CARDS_VISIBLE = false;

/** S3b（G9）：追问改写透明性 —— 「理解为：xxx」小字 + 点击展开原文对照 */
const FollowupRewriteNote: React.FC<{ note: { original: string; rewritten: string } }> = ({ note }) => {
  const [showOriginal, setShowOriginal] = useState(false);
  return (
    <div
      style={{
        fontSize: 12, color: tokens.colors.textTertiary, lineHeight: '20px',
        padding: '2px 8px', marginBottom: 6, background: tokens.colors.bgSubtle,
        borderRadius: tokens.radius.default,
      }}
    >
      理解为：{note.rewritten}
      <Text
        style={{ marginLeft: 8, fontSize: 12, color: tokens.colors.textTertiary, cursor: 'pointer', textDecoration: 'underline dotted' }}
        onClick={() => setShowOriginal(!showOriginal)}
      >
        {showOriginal ? '收起原文' : '原文对照'}
      </Text>
      {showOriginal ? (
        <div style={{ marginTop: 2, color: tokens.colors.textTertiary, wordBreak: 'break-all' }}>原文：{note.original}</div>
      ) : null}
    </div>
  );
};

/* Markdown 元素样式：连续流，无卡片包裹，仅标题加左竖线区分 */
const mdComponents = {
  h1: (props: any) => <h1 style={{ fontSize: 17, fontWeight: 700, margin: '16px 0 8px', color: tokens.colors.textPrimary, letterSpacing: '-0.01em' }} {...props} />,
  h2: (props: any) => <h2 style={{ fontSize: 16, fontWeight: 600, margin: '14px 0 6px', color: tokens.colors.textPrimary, letterSpacing: '-0.01em', paddingLeft: 8, borderLeft: `3px solid ${tokens.colors.primary}` }} {...props} />,
  h3: (props: any) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: '10px 0 4px', color: tokens.colors.textSecondary }} {...props} />,
  p: (props: any) => <p style={{ margin: '4px 0', lineHeight: 1.8, color: tokens.colors.textSecondary }} {...props} />,
  ul: (props: any) => <ul style={{ margin: '4px 0', paddingLeft: 20, lineHeight: 1.8 }} {...props} />,
  ol: (props: any) => <ol style={{ margin: '4px 0', paddingLeft: 20, lineHeight: 1.8 }} {...props} />,
  li: (props: any) => <li style={{ margin: '2px 0', color: tokens.colors.textSecondary }} {...props} />,
  table: (props: any) => <table style={{ width: '100%', borderCollapse: 'collapse', margin: '8px 0', fontSize: 13 }} {...props} />,
  thead: (props: any) => <thead style={{ background: tokens.colors.bgSubtle }} {...props} />,
  th: (props: any) => <th style={{ border: `1px solid ${tokens.colors.border}`, padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: tokens.colors.textPrimary }} {...props} />,
  td: (props: any) => <td style={{ border: `1px solid ${tokens.colors.border}`, padding: '6px 10px', color: tokens.colors.textSecondary }} {...props} />,
  code: (props: any) => <code style={{ background: tokens.colors.bgSubtle, padding: '2px 6px', borderRadius: 3, fontSize: 12, fontFamily: 'Consolas, Monaco, monospace', color: tokens.colors.error }} {...props} />,
  pre: (props: any) => <pre style={{ background: tokens.colors.bgSubtle, padding: 12, borderRadius: 6, overflowX: 'auto', fontSize: 12, margin: '8px 0' }} {...props} />,
  blockquote: (props: any) => <blockquote style={{ borderLeft: `3px solid ${tokens.colors.border}`, margin: '6px 0', padding: '2px 12px', color: tokens.colors.textTertiary }} {...props} />,
  strong: (props: any) => <strong style={{ color: tokens.colors.textPrimary, fontWeight: 600 }} {...props} />,
  a: (props: any) => <a style={{ color: tokens.colors.primary }} {...props} />,
};

/* 关键发现级别 -> 颜色（token） */
const findingColors: Record<string, string> = {
  info: tokens.colors.info,
  success: tokens.colors.success,
  warning: tokens.colors.warning,
  error: tokens.colors.error,
};

const FindingItem: React.FC<{ finding: FinalFinding }> = ({ finding }) => {
  const color = findingColors[finding.level || 'info'] || tokens.colors.info;
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 10px', borderRadius: 6,
      background: tokens.colors.bgSubtle, border: `1px solid ${tokens.colors.border}`,
      fontSize: 13,
    }}>
      <span style={{ fontWeight: 600, color: tokens.colors.textPrimary }}>
        {finding.label || ''}
      </span>
      {finding.value ? <span style={{ color }}>{finding.value}</span> : null}
    </div>
  );
};

const AssistantCanvas: React.FC<{
  payload?: ChatMessagePayload;
  isLast: boolean;
  liveMetaInfo?: string;
  liveFinalAnswer?: string;
  onSelectRecommendation?: (rec: any) => void;
}> = ({ payload, isLast, liveMetaInfo, liveFinalAnswer, onSelectRecommendation }) => {
  const thinkStream = payload?.thinkStream || [];
  const traceLogs = payload?.traceLogs || [];
  // 批1-A 答案直出：final 后 final_answer 权威校准覆盖；loading 中显示 streaming_answer 逐字成型
  const finalAnswer = payload?.final_answer || payload?.streaming_answer || (isLast ? liveFinalAnswer : undefined);
  const answerRevising = !!payload?.answer_revising;
  const recommendations = payload?.recommendations || [];
  const sqlResult = payload?.sql_result || null;
  const structured = payload?.final_answer_structured || null;
  const sqlText = structured?.sql || sqlResult?.sql || '';
  const execProcess = structured?.execution_process || '';
  const route = payload?.route || null;
  const contract = payload?.contract || null;
  // 融合 M3 G7：证据链 + 置信度三级（高/中/低）
  const evidence = payload?.evidence || null;
  const confidence = payload?.confidence;
  // 评审 P1-1（三轮）：完成态也要展示执行期间累积的策略/模板事件（徽标 + 展开后审计列表）
  const policyEvents = payload?.policy_events || [];
  const templateEvents = payload?.template_events || [];
  // 统一最终交付视图（含标题/摘要/发现/告警/表格开关/降级提示）
  const view = buildFinalDeliveryView(payload);
  // 展示兜底：存在权威查询结果表时，屏蔽模型 final_answer 里的 GFM Markdown 表格节点
  // （明细只由前端结果表展示一次；保留段落/列表/标题）。不用正则删表，避免误删代码块。
  const maskMarkdownTables = view.maskMarkdownTables;
  const renderComponents = maskMarkdownTables
    ? { ...mdComponents, table: () => null, thead: () => null, tbody: () => null, tr: () => null, th: () => null, td: () => null }
    : mdComponents;

  return (
    <div style={{ fontSize: 14, color: tokens.colors.textPrimary }}>
      {/* 0.1 受控 Skill 问答平台 v2：六张业务卡（路由/范围/数据访问/执行决策/终止条件/证据），默认折叠状态条
          批⓪ 前台折叠下线：对话页只留「发问-回答-依据」（v4 §十二.3）——批⑥ 引擎台后台复用 */}
      {CONTRACT_CARDS_VISIBLE && (route || contract) ? (
        <div style={{ marginBottom: 8 }}>
          <ContractCardsPanel route={route} contract={contract} policyEvents={policyEvents} templateEvents={templateEvents} evidence={evidence} confidence={confidence} />
        </div>
      ) : null}

      {/* 0. 思考过程：折叠控件，默认折叠 */}
      {thinkStream.length > 0 ? (
        <div style={{ marginBottom: 8 }}>
          <ThinkStream items={thinkStream} active={false} metaInfo={isLast ? liveMetaInfo : undefined} traces={traceLogs} />
        </div>
      ) : null}

      {/* 0.2 EvidenceCapsule（批①a——v4§11.2/§12.2）：证据胶囊——「依据什么」；
          思考链讲怎么想的、胶囊讲依据什么（替代批⓪折叠的 ContractCardsPanel 证据面） */}
      {(() => {
        const sources = evidenceToSources(evidence);
        return sources.length > 0 ? (
          <div style={{ marginBottom: 8 }}>
            <EvidenceCapsule sources={sources} confidence={confidence as any} />
          </div>
        ) : null;
      })()}

      {/* 1. 最终结果标题：必须明显显示（含融合 M3 G7 置信度三级小徽标） */}
      {(view.title || view.summary.length > 0 || view.findings.length > 0 || view.showTable) ? (
        <div style={{ display: 'flex', alignItems: 'center', margin: '10px 0 6px' }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: tokens.colors.textPrimary, letterSpacing: '-0.01em', paddingLeft: 8, borderLeft: `3px solid ${tokens.colors.primary}` }}>
            {view.title}
          </h2>
          {confidence ? (() => {
            const confColor = confidence === '高' ? tokens.colors.success : (confidence === '低' ? tokens.colors.error : tokens.colors.warning);
            // 批3-F：分段计时外露（悬停显示，不常驻占屏）——首token/首工具/作答/自评/总
            const _t = payload?.timing;
            const _sec = (v?: number) => (v != null && v > 0 ? `${(v / 1000).toFixed(1)}s` : '—');
            const _tt = _t ? (
              `首 token ${_sec(_t.first_answer_token)} · 首工具 ${_sec(_t.first_tool_start)} · 作答 ${_sec(_t.first_answer_token ? (_t.total ?? 0) - _t.first_answer_token : undefined)} · 自评 ${_sec(_t.rubric_ms)} · 总 ${_sec(_t.total)}`
            ) : undefined;
            const _badge = (
              <Tag
                style={{
                  marginLeft: 10, color: confColor, border: `1px solid ${confColor}`,
                  background: 'transparent', borderRadius: tokens.radius.pill,
                  fontSize: 11, lineHeight: '18px', padding: '0 8px',
                }}
              >
                置信度{confidence}
              </Tag>
            );
            return _tt ? <Tooltip title={_tt}><span>{_badge}</span></Tooltip> : _badge;
          })() : null}
        </div>
      ) : null}

      {/* 2. 摘要 / 关键发现 / 告警 */}
      {(view.summary.length > 0 || view.findings.length > 0 || view.warnings.length > 0) ? (
        <div style={{ padding: '0 4px', marginBottom: 6 }}>
          {view.summary.map((s, i) => (
            <p key={`s-${i}`} style={{ margin: '2px 0', lineHeight: 1.7, color: tokens.colors.textSecondary }}>{s}</p>
          ))}
          {view.findings.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
              {view.findings.map((f, i) => <FindingItem key={`f-${i}`} finding={f} />)}
            </div>
          ) : null}
          {view.warnings.map((w, i) => (
            <div key={`w-${i}`} style={{ marginTop: 4, fontSize: 13, color: tokens.colors.warning, lineHeight: 1.7 }}>
              ⚠️ {w}
            </div>
          ))}
        </div>
      ) : null}

      {/* 3. 答案正文：连续 Markdown（存在权威查询结果表时屏蔽其中的 Markdown 表格） */}
      {finalAnswer ? (
        <div style={{ padding: '0 4px' }}>
          {/* S3b（G9）：追问改写透明性 —— 最终答案上方「理解为：xxx」（可点击展开原文对照） */}
          {payload?.followup_rewritten && payload.followup_rewritten.rewritten ? (
            <FollowupRewriteNote note={payload.followup_rewritten} />
          ) : null}
          {/* 批1-A：rubric 修订中徽标（新一轮答案生成中，内容即将续流替换） */}
          {answerRevising ? (
            <Tag color="warning" style={{ fontSize: 12, marginBottom: 6 }}>
              <Spin size="small" style={{ marginRight: 4 }} />校验修订中
            </Tag>
          ) : null}
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={renderComponents}>
            {finalAnswer}
          </ReactMarkdown>
          {/* 降级提示：只说明"结果已基于实际查询数据生成"，不造成"答案不可靠"感受 */}
          {view.degradedNotice ? (
            <div style={{ marginTop: 6, fontSize: 11, color: tokens.colors.textTertiary }}>
              <Tag color="blue" style={{ fontSize: 10, marginRight: 4 }}>{view.degradedNotice}</Tag>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* 4. 查询结果表格：row_count > 0 时无论模型是否生成文本都显示，前端分页 */}
      {view.showTable ? (
        <div style={{ padding: '0 4px' }}>
          <SqlResultTable data={sqlResult} />
        </div>
      ) : null}

      {/* 5. 推荐问题（B2 美化：chip 胶囊流，点击填入输入框） */}
      {recommendations.length > 0 ? (
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: `1px dashed ${tokens.colors.border}`, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <Text type="secondary" style={{ fontSize: 12, lineHeight: '24px' }}>猜你想问：</Text>
          {recommendations.map((r, i) => (
            <span
              key={i}
              onClick={() => onSelectRecommendation?.(r)}
              style={{
                padding: '3px 12px', borderRadius: tokens.radius.pill,
                background: tokens.colors.primaryBg, color: tokens.colors.primary,
                fontSize: 12, cursor: 'pointer', lineHeight: '22px', whiteSpace: 'nowrap',
                border: `1px solid ${tokens.colors.primaryBg}`,
                transition: `box-shadow ${tokens.motion.duration.fast}ms ${tokens.motion.easing.enter}`,
              }}
            >
              {r.label}
            </span>
          ))}
        </div>
      ) : null}

      {/* 6. SQL 与执行过程：默认折叠 */}
      {sqlText || execProcess ? (
        <div style={{ marginTop: 8 }}>
          <Collapse
            ghost
            items={[{
              key: 'sql',
              label: <span style={{ fontSize: 13, color: tokens.colors.textTertiary }}>SQL 与执行过程</span>,
              children: (
                <div>
                  {sqlText ? (
                    <pre style={{ background: tokens.colors.bgSubtle, padding: 10, borderRadius: 6, fontSize: 12, overflowX: 'auto', margin: 0, fontFamily: 'Consolas, Monaco, monospace', color: tokens.colors.textSecondary }}>
                      {sqlText}
                    </pre>
                  ) : null}
                  {execProcess ? (
                    <div style={{ marginTop: 6, fontSize: 13, color: tokens.colors.textTertiary, lineHeight: 1.7 }}>{execProcess}</div>
                  ) : null}
                </div>
              ),
            }]}
          />
        </div>
      ) : null}
    </div>
  );
};

export default React.memo(AssistantCanvas);
