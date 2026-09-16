/**
 * 轻量 Markdown 渲染（等价替换原仓 MarkdownRenderer 的 prose 场景：
 * 标题/列表/粗体/行内代码/代码块/$...$ 公式以等宽高亮展示——tupu 技术栈
 * 约束下无 KaTeX 依赖，公式降级为等宽文本，其余语义 1:1）。
 */
import React from 'react';

const INLINE_RE = /(\*\*[^*]+\*\*|`[^`]+`|\$\$[^$]+\$\$|\$[^$\n]+\$)/g;

const codeStyle: React.CSSProperties = {
  fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
  fontSize: '0.92em',
  background: 'rgba(0,0,0,0.06)',
  borderRadius: 3,
  padding: '1px 4px',
};
const mathStyle: React.CSSProperties = {
  ...codeStyle,
  background: 'rgba(22,119,255,0.08)',
  color: '#1677ff',
};

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  return text.split(INLINE_RE).map((p, i) => {
    if (!p) return null;
    const key = `${keyPrefix}-${i}`;
    if (p.startsWith('**') && p.endsWith('**') && p.length > 4) return <strong key={key}>{p.slice(2, -2)}</strong>;
    if (p.startsWith('`') && p.endsWith('`') && p.length > 2) return <code key={key} style={codeStyle}>{p.slice(1, -1)}</code>;
    if (p.startsWith('$$') && p.endsWith('$$') && p.length > 4) return <code key={key} style={mathStyle}>{p.slice(2, -2)}</code>;
    if (p.startsWith('$') && p.endsWith('$') && p.length > 2) return <code key={key} style={mathStyle}>{p.slice(1, -1)}</code>;
    return <span key={key}>{p}</span>;
  });
}

export function LiteMarkdown({ content }: { content: string }) {
  const lines = (content || '').split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let key = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.trim().startsWith('```')) {
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        buf.push(lines[i]);
        i += 1;
      }
      i += 1; // 跳过收尾 fence
      blocks.push(
        <pre key={`k${key++}`} style={{ background: 'rgba(0,0,0,0.04)', borderRadius: 6, padding: '8px 10px', overflowX: 'auto', fontSize: 12, margin: '4px 0' }}>
          <code>{buf.join('\n')}</code>
        </pre>,
      );
      continue;
    }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const sizes: Record<number, number> = { 1: 18, 2: 16, 3: 15, 4: 14 };
      blocks.push(
        <div key={`k${key++}`} style={{ fontWeight: 600, fontSize: sizes[h[1].length], margin: '8px 0 4px' }}>
          {renderInline(h[2], `h${key}`)}
        </div>,
      );
      i += 1;
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ''));
        i += 1;
      }
      blocks.push(
        <ul key={`k${key++}`} style={{ margin: '4px 0', paddingLeft: 20 }}>
          {items.map((it, j) => (
            <li key={j} style={{ margin: '2px 0' }}>{renderInline(it, `li${key}-${j}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
        i += 1;
      }
      blocks.push(
        <ol key={`k${key++}`} style={{ margin: '4px 0', paddingLeft: 20 }}>
          {items.map((it, j) => (
            <li key={j} style={{ margin: '2px 0' }}>{renderInline(it, `ol${key}-${j}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }
    if (line.trim() === '') {
      i += 1;
      continue;
    }
    const buf: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].trim().startsWith('```') &&
      !/^(#{1,4})\s+/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i])
    ) {
      buf.push(lines[i]);
      i += 1;
    }
    blocks.push(
      <p key={`k${key++}`} style={{ margin: '4px 0' }}>{renderInline(buf.join(' '), `p${key}`)}</p>,
    );
  }
  return <div>{blocks}</div>;
}

export default LiteMarkdown;
