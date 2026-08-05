/**
 * AssistantCanvas - 单画布连续流（豆包/ZCode/同花顺风格）
 *
 * 回答结构（数据智能工作台视觉规范）：
 *   1. 关键指标/结果表：sql_result 置顶预览（若有）
 *   2. 思考过程：ThinkStream 折叠控件，默认折叠
 *   3. 答案：ReactMarkdown 连续渲染 final_answer（## 标题 + 表格 + 代码块 + 列表）
 *   4. SQL 与执行过程：默认折叠（final_answer_structured.sql / execution_process）
 *   5. 推荐问题：融入画布底部，虚线分隔，可点击
 *
 * 配色全部走 token，零硬编码。
 */
import React from 'react';
import { Collapse, Table } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ThinkStream from './ThinkStream';
import type { ChatMessagePayload } from './types';
import { tokens } from '../../theme/tokens';

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

const AssistantCanvas: React.FC<{
  payload?: ChatMessagePayload;
  isLast: boolean;
  liveMetaInfo?: string;
  liveFinalAnswer?: string;
  onSelectRecommendation?: (rec: any) => void;
}> = ({ payload, isLast, liveMetaInfo, liveFinalAnswer, onSelectRecommendation }) => {
  const thinkStream = payload?.thinkStream || [];
  const finalAnswer = payload?.final_answer || (isLast ? liveFinalAnswer : undefined);
  const recommendations = payload?.recommendations || [];
  const sqlResult = payload?.sql_result || null;
  const structured = payload?.final_answer_structured || null;
  const sqlText = structured?.sql || sqlResult?.sql || '';
  const execProcess = structured?.execution_process || '';

  const resultColumns = sqlResult?.columns?.map((c: string) => ({ title: c, dataIndex: c, key: c, ellipsis: true })) || [];
  const resultRows = (sqlResult?.rows || []).slice(0, 5).map((r: any, i: number) => {
    if (Array.isArray(r)) {
      const obj: any = { _key: i };
      sqlResult?.columns?.forEach((c: string, ci: number) => { obj[c] = r[ci]; });
      return obj;
    }
    return { _key: i, ...r };
  });

  return (
    <div style={{ fontSize: 14, color: tokens.colors.textPrimary }}>
      {/* 1. 关键指标/结果表：sql_result 置顶预览 */}
      {sqlResult && sqlResult.rows && sqlResult.rows.length > 0 ? (
        <div style={{ marginBottom: 8 }}>
          <Table
            size="small"
            rowKey="_key"
            columns={resultColumns}
            dataSource={resultRows}
            pagination={false}
            scroll={{ x: 'max-content' }}
            style={{ borderRadius: tokens.radius.card, overflow: 'hidden' }}
          />
          <div style={{ fontSize: 12, color: tokens.colors.textTertiary, marginTop: 4 }}>
            共 {sqlResult.row_count ?? sqlResult.rows.length} 行{sqlResult.rows.length > 5 ? `，已预览前 5 行` : ''}
          </div>
        </div>
      ) : null}

      {/* 2. 思考过程：折叠控件，默认折叠 */}
      {thinkStream.length > 0 ? (
        <div style={{ marginBottom: 8 }}>
          <ThinkStream items={thinkStream} active={false} metaInfo={isLast ? liveMetaInfo : undefined} />
        </div>
      ) : null}

      {/* 3. 答案：连续 Markdown */}
      {finalAnswer ? (
        <div style={{ padding: '0 4px' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {finalAnswer}
          </ReactMarkdown>
        </div>
      ) : null}

      {/* 4. SQL 与执行过程：默认折叠 */}
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

      {/* 5. 推荐问题：虚线分隔，可点击填入输入框 */}
      {recommendations.length > 0 ? (
        <div style={{ marginTop: 12, paddingTop: 8, borderTop: `1px dashed ${tokens.colors.border}` }}>
          {recommendations.map((r, i) => (
            <div
              key={i}
              onClick={() => onSelectRecommendation?.(r)}
              style={{ padding: '4px 0', cursor: 'pointer', color: tokens.colors.primary, fontSize: 13, lineHeight: 1.8 }}
            >
              {i + 1}. {r.label}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default AssistantCanvas;
