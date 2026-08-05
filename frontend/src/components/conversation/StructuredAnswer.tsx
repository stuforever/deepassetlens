/**
 * 结构化答案 - 解析 LLM 输出的"一/二/三/四"Markdown 分块
 *
 * LLM 按 system prompt 要求输出：
 *   ## 一、综合结论
 *   ## 二、定位实体
 *   ## 三、返回数据
 *   ## 四、推荐问题
 *
 * 前端解析为 4 张分块卡片，单色风格（豆包/Trae），并在
 * "二、定位实体"叠加 confirmed 标签，"三、返回数据"叠加 sql_result 表格，
 * "四、推荐问题"叠加 recommendations 可点击列表。
 */
import React from 'react';
import { Typography, Table, Tag, Empty } from 'antd';
import { tokens } from '../../theme/tokens';
import { StatusTag } from '../shell';

const { Text, Paragraph } = Typography;

/** 从 Markdown 提取指定序号分块正文（## 一、... 到下一个 ## X、或文末） */
function extractSection(md: string, numeral: string): string {
  if (!md) return '';
  // 不带 m 标志：$ 匹配字符串尾，避免行尾提前截断捕获组
  const re = new RegExp(`##\\s*${numeral}、[^\\n]*\\n([\\s\\S]*?)(?=##\\s*[一二三四五六]、|$)`);
  const m = md.match(re);
  return m ? m[1].trim() : '';
}

/** 解析"四、推荐问题"为列表（兼容 LLM 输出的 1. 2. 或 - 项） */
function parseRecommendItems(text: string): string[] {
  if (!text) return [];
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  const items: string[] = [];
  for (const line of lines) {
    // 去掉前缀 "1." "2." "-" "*" "1、"
    const cleaned = line.replace(/^(\d+[\.\、]|[-*])\s*/, '');
    if (cleaned) items.push(cleaned);
  }
  return items;
}

type SqlResult = { columns?: string[]; rows?: any[]; row_count?: number; sql?: string } | null;

/* 分块卡片：单色风格，浅灰底 + 左侧蓝色竖线 */
const SectionCard: React.FC<{
  title: string;
  content: string;
  extra?: React.ReactNode;
}> = ({ title, content, extra }) => {
  const hasContent = Boolean(content && content.trim());
  const hasExtra = Boolean(extra);
  if (!hasContent && !hasExtra) return null;
  return (
    <div style={{
      marginBottom: 8, padding: '10px 14px',
      background: 'var(--bg-subtle)', borderRadius: 8,
      borderLeft: '3px solid var(--color-primary)',
    }}>
      <Text strong style={{ fontSize: 13, color: 'var(--text-primary)', display: 'block', marginBottom: 4 }}>{title}</Text>
      {hasContent ? (
        <Paragraph style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: extra ? 8 : 0, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
          {content}
        </Paragraph>
      ) : null}
      {extra}
    </div>
  );
};

/* 定位实体标签：从 confirmed 渲染 L2/主表/属性/联接表 */
const LocationTags: React.FC<{ confirmed?: Record<string, any> }> = ({ confirmed }) => {
  if (!confirmed) return null;
  const { L2, L2X, L2X_name, attributes, extra_entities, relations } = confirmed;
  if (!L2 && !L2X) return null;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
      {L2 ? <StatusTag preset="ai" style={{ fontSize: 12 }}>业务域: {L2}</StatusTag> : null}
      {L2X ? <StatusTag preset="info" style={{ fontSize: 12 }}>主表: {L2X_name || L2X}</StatusTag> : null}
      {attributes && attributes.length ? <Tag style={{ fontSize: 12 }}>属性: {attributes.length} 个</Tag> : null}
      {extra_entities && extra_entities.length ? <StatusTag preset="warning" style={{ fontSize: 12 }}>联接表: {extra_entities.length} 个</StatusTag> : null}
      {relations && relations.length ? <StatusTag preset="success" style={{ fontSize: 12 }}>关系: {relations.length} 条</StatusTag> : null}
    </div>
  );
};

/* 数据表格：antd Table，>5 行折叠 */
const SqlTable: React.FC<{ data: SqlResult }> = ({ data }) => {
  if (!data || !data.columns || data.columns.length === 0) return null;
  const columns = data.columns.map((c) => ({ title: c, dataIndex: c, key: c, ellipsis: true }));
  const rows = (data.rows || []).map((r, i) => {
    const obj: any = { key: i };
    data.columns!.forEach((c, j) => { obj[c] = r[j]; });
    return obj;
  });
  return (
    <div style={{ marginTop: 6 }}>
      <Table
        size="small"
        columns={columns}
        dataSource={rows}
        pagination={rows.length > 5 ? { pageSize: 5, size: 'small' } : false}
        scroll={{ x: 'max-content' }}
      />
    </div>
  );
};

/* 推荐问题列表：可点击填入输入框 */
const RecList: React.FC<{
  items: string[];
  recs?: Array<{ label: string; shortcut?: string }>;
  onSelect?: (rec: any) => void;
}> = ({ items, recs, onSelect }) => {
  // 优先用 Markdown 解析的 items，兜底用 recs
  const list = items.length > 0 ? items.map((t) => ({ label: t, shortcut: t }))
    : (recs || []).map((r) => ({ label: r.label, shortcut: r.shortcut || r.label }));
  if (list.length === 0) return null;
  return (
    <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
      {list.map((it, i) => (
        <div
          key={i}
          onClick={() => onSelect && onSelect(it)}
          style={{
            padding: '6px 10px', background: 'var(--bg-content)', borderRadius: 6,
            border: '1px solid var(--border-color)', cursor: 'pointer', fontSize: 12,
            color: tokens.colors.primary, transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-primary-bg)'; e.currentTarget.style.borderColor = 'var(--color-primary-bg)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-content)'; e.currentTarget.style.borderColor = 'var(--border-color)'; }}
        >
          <span style={{ color: 'var(--text-tertiary)', marginRight: 6 }}>{i + 1}.</span>{it.label}
        </div>
      ))}
    </div>
  );
};

const StructuredAnswer: React.FC<{
  finalAnswer?: string;
  sqlResult?: SqlResult;
  confirmed?: Record<string, any>;
  recommendations?: Array<{ label: string; shortcut?: string }>;
  onSelectRecommendation?: (rec: any) => void;
}> = ({ finalAnswer, sqlResult, confirmed, recommendations, onSelectRecommendation }) => {
  const md = finalAnswer || '';
  const conclusion = extractSection(md, '一');
  const location = extractSection(md, '二');
  const dataText = extractSection(md, '三');
  const recommendText = extractSection(md, '四');
  const recItems = parseRecommendItems(recommendText);

  // 兜底：LLM 未按格式输出（整段文本），直接显示
  const hasAnySection = conclusion || location || dataText || recommendText;
  if (!hasAnySection && md) {
    return (
      <SectionCard title="一、综合结论" content={md} />
    );
  }

  return (
    <div>
      <SectionCard title="一、综合结论" content={conclusion} />
      <SectionCard title="二、定位实体" content={location} extra={<LocationTags confirmed={confirmed} />} />
      <SectionCard title="三、返回数据" content={dataText} extra={<SqlTable data={sqlResult ?? null} />} />
      <SectionCard title="四、推荐问题" content={recommendItemsToContent(recItems)}
        extra={<RecList items={recItems} recs={recommendations} onSelect={onSelectRecommendation} />} />
    </div>
  );
};

/** 推荐问题文本（用于卡片正文，列表形式） */
function recommendItemsToContent(items: string[]): string {
  if (items.length === 0) return '';
  return items.map((it, i) => `${i + 1}. ${it}`).join('\n');
}

export default StructuredAnswer;
