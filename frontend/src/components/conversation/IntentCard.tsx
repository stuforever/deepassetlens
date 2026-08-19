/**
 * 意图理解卡（P0 信任卡）
 * 置顶显示：① AI 理解的查询任务 + 过滤条件（执行前推 intent 事件）
 *          ② 实际 SQL 的 WHERE + 返回行数（执行后推 filter_check 事件，与用户过滤意图对照）
 * 让用户一眼确认"AI 听懂了"并能核对过滤是否落实，消除黑箱感。
 */
import React from 'react';
import { Typography } from 'antd';
import { AimOutlined } from '@ant-design/icons';
import { tokens } from '../../theme/tokens';

const { Text } = Typography;

export type IntentData = {
  task: string;
  entities?: string[];
  filters: Array<{ desc: string; field: string; values: string[] }>;
};

export type FilterCheck = { sql_where: string; row_count: number };

const IntentCard: React.FC<{ intent?: IntentData | null; filterCheck?: FilterCheck | null }> = ({ intent, filterCheck }) => {
  if (!intent) return null;
  return (
    <div style={{ marginBottom: 8, padding: '10px 12px', background: 'var(--bg-subtle)', borderRadius: 8, border: '1px solid var(--color-ai)' }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-ai)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
        <AimOutlined /> 意图理解
      </div>
      <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>
        <div><Text strong style={{ fontSize: 13 }}>任务：</Text>{intent.task}</div>
        {intent.entities && intent.entities.length > 0 ? (
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>对象：{intent.entities.join('、')}</div>
        ) : null}
        {intent.filters && intent.filters.length > 0 ? (
          <div style={{ marginTop: 6 }}>
            {intent.filters.map((f, i) => (
              <div key={i} style={{ fontSize: 12, marginTop: 2 }}>
                <span style={{ color: 'var(--color-ai)', fontWeight: 600 }}>过滤</span>
                <span>：{f.field} = {f.values.join(' / ')}</span>
                <span style={{ color: 'var(--text-tertiary)' }}>（你说：{f.desc}）</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>（未指定过滤条件，全量检索）</div>
        )}
      </div>
      {filterCheck ? (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px dashed var(--border-color)' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: tokens.colors.primary }}>过滤对照（执行后）</div>
          <div style={{ fontSize: 11, fontFamily: 'Consolas, Monaco, monospace', color: 'var(--text-secondary)', marginTop: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-all', lineHeight: 1.6 }}>
            WHERE {filterCheck.sql_where}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>返回 {filterCheck.row_count} 行</div>
        </div>
      ) : null}
    </div>
  );
};

export default IntentCard;
