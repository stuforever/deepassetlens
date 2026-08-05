/**
 * 最终答案组件 - 问财(同花顺)风格
 *
 * 特性：
 *   1. 支持 token 级流式渲染（灰色实时文本 + 闪烁光标）
 *   2. 流式结束后按问财风格解析 markdown-like 文本：
 *      - 数字标题 1. 2. 3. -> 加粗标题
 *      - ● 项目符号，冒号前加粗
 *      - 结论: / 一句话总结: 前缀加粗
 *      - **text** -> 蓝色高亮
 *      - 空行 -> 段落间距
 *      - 每段末尾附 🔗 图标
 *   3. variant='table' 时以 antd Table 渲染 SQL 结果（最多预览 5 行）
 *   4. 扁平长文排版，无 Card 包裹，由父组件提供卡片
 */
import React, { useMemo } from 'react';
import { Space, Table, Typography } from 'antd';
import { LinkOutlined } from '@ant-design/icons';
import { tokens } from '../../theme/tokens';

const { Text } = Typography;

interface FinalAnswerProps {
  /** 完整答案文本（markdown-like） */
  answer: string;
  /** 累积的 token，用于流式实时渲染 */
  tokens: string[];
  /** 是否正在流式输出 token */
  isStreaming: boolean;
  /** 渲染变体：markdown=知识问答，table=数据查询 */
  variant?: 'markdown' | 'table';
  /** SQL 结果数据，仅 variant='table' 时使用 */
  tableData?: { columns: string[]; rows: any[][]; row_count: number };
}

/** 段落末尾的链接图标（小、灰色） */
const LinkIcon: React.FC = () => (
  <LinkOutlined style={{ fontSize: 12, color: 'var(--border-color)', marginLeft: 4, verticalAlign: 'middle' }} />
);

/**
 * 解析行内 **text** 标记，将包裹文本渲染为蓝色高亮
 * 其余文本按原样输出
 */
const renderInline = (text: string): React.ReactNode[] => {
  if (!text) return [];
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <span key={i} style={{ color: tokens.colors.primary }}>
          {part.slice(2, -2)}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
};

/**
 * 按问财风格逐行解析完整答案
 */
const renderMarkdown = (answer: string): React.ReactNode => {
  if (!answer) return null;
  const lines = answer.split('\n');

  return lines.map((line, idx) => {
    // 空行 -> 段落间距
    if (line.trim() === '') {
      return <div key={idx} style={{ height: 8 }} />;
    }

    // 数字标题：1. 2. 3. -> 加粗标题（17px / 深色 / 600）
    const titleMatch = line.match(/^\d+\.\s+(.*)$/);
    if (titleMatch) {
      return (
        <div
          key={idx}
          style={{
            fontSize: 17,
            color: 'var(--text-primary)',
            fontWeight: 600,
            lineHeight: 1.8,
            marginTop: 4,
            marginBottom: 2,
          }}
        >
          {renderInline(line)}
          <LinkIcon />
        </div>
      );
    }

    // 项目符号：● 冒号前加粗
    if (line.startsWith('● ')) {
      const content = line.slice(2);
      const colonIdx = content.search(/[:：]/);
      let label = '';
      let rest = '';
      if (colonIdx >= 0) {
        label = content.slice(0, colonIdx + 1);
        rest = content.slice(colonIdx + 1);
      } else {
        rest = content;
      }
      return (
        <div key={idx} style={{ display: 'flex', lineHeight: 1.8, margin: '2px 0' }}>
          <span style={{ color: 'var(--text-primary)', marginRight: 6, flexShrink: 0 }}>●</span>
          <span style={{ flex: 1 }}>
            {label ? <span style={{ fontWeight: 600 }}>{renderInline(label)}</span> : null}
            {renderInline(rest)}
            <LinkIcon />
          </span>
        </div>
      );
    }

    // 结论: 前缀加粗
    if (line.startsWith('结论: ')) {
      return (
        <div key={idx} style={{ lineHeight: 1.8, margin: '2px 0' }}>
          <span style={{ fontWeight: 600 }}>结论: </span>
          {renderInline(line.slice(4))}
          <LinkIcon />
        </div>
      );
    }

    // 一句话总结: 前缀加粗
    if (line.startsWith('一句话总结: ')) {
      return (
        <div key={idx} style={{ lineHeight: 1.8, margin: '2px 0' }}>
          <span style={{ fontWeight: 600 }}>一句话总结: </span>
          {renderInline(line.slice(7))}
          <LinkIcon />
        </div>
      );
    }

    // 普通段落
    return (
      <div key={idx} style={{ lineHeight: 1.8, margin: '2px 0' }}>
        {renderInline(line)}
        <LinkIcon />
      </div>
    );
  });
};

/**
 * 表格变体：上方一行加粗摘要 + antd Table（最多预览 5 行）+ 共 N 行
 */
const TableAnswer: React.FC<{ answer: string; tableData: NonNullable<FinalAnswerProps['tableData']> }> = ({
  answer,
  tableData,
}) => {
  const { columns, rows, row_count } = tableData;

  // 构造 antd Table 列定义
  const tableColumns = useMemo(
    () =>
      (columns || []).map((c, i) => ({
        title: c,
        dataIndex: `col_${i}`,
        key: `col_${i}`,
        ellipsis: true,
        render: (v: any) =>
          v === null || v === undefined ? (
            <Text type="secondary">NULL</Text>
          ) : (
            String(v)
          ),
      })),
    [columns],
  );

  // 最多预览 5 行
  const dataSource = useMemo(() => {
    const preview = (rows || []).slice(0, 5);
    return preview.map((row, i) => {
      const obj: any = { key: i };
      row.forEach((v, j) => {
        obj[`col_${j}`] = v;
      });
      return obj;
    });
  }, [rows]);

  const total = typeof row_count === 'number' ? row_count : (rows || []).length;

  return (
    <div style={{ padding: 16 }}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {/* 表格上方一行加粗摘要 */}
        <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)', lineHeight: 1.8 }}>
          {renderInline(answer)}
        </div>

        <Table
          size="small"
          columns={tableColumns}
          dataSource={dataSource}
          pagination={false}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: '查询结果为空' }}
        />

        {/* 表格下方共 N 行 */}
        <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>共 {total} 行</div>
      </Space>
    </div>
  );
};

const FinalAnswer: React.FC<FinalAnswerProps> = ({
  answer,
  tokens,
  isStreaming,
  variant = 'markdown',
  tableData,
}) => {
  // 1. 流式渲染优先：拼接 token 为灰色实时文本 + 闪烁光标
  if (isStreaming && tokens && tokens.length > 0) {
    const live = tokens.join('');
    return (
      <div
        style={{
          padding: 16,
          color: 'var(--text-secondary)',
          fontSize: 14,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          lineHeight: 1.8,
        }}
      >
        {live}
        <span className="final-answer-cursor">|</span>
        <style>{`
          .final-answer-cursor {
            color: var(--color-primary);
            font-weight: 300;
            margin-left: 1px;
            animation: final-answer-blink 1s step-end infinite;
          }
          @keyframes final-answer-blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
          }
        `}</style>
      </div>
    );
  }

  // 2. 表格变体：SQL 结果
  if (variant === 'table' && tableData) {
    return <TableAnswer answer={answer} tableData={tableData} />;
  }

  // 3. 默认 markdown 变体：问财风格扁平长文
  return (
    <div style={{ padding: 16, fontSize: 14, color: 'var(--text-primary)', lineHeight: 1.8 }}>
      {renderMarkdown(answer)}
    </div>
  );
};

export default FinalAnswer;
