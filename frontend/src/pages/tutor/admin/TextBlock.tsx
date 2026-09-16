/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/TextBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client"；MarkdownRenderer(@/components/common/MarkdownRenderer)
 * → LiteMarkdown（'./dtMarkdown'，props≈{content:string}，variant 附加参数忽略）；
 * @/lib/book-types → './book-types'（并行 Agent 产出，导出名一致）。
 */
import { LiteMarkdown } from './dtMarkdown';
import type { Block } from './book-types';

export interface TextBlockProps {
  block: Block;
}

export default function TextBlock({ block }: TextBlockProps) {
  // 渲染键契约：body 是正键（deeptutor/book/blocks/text.py 标准生成器落库键）；
  // content 是 book 引擎总览页确定性 TEXT 块的遗留键（engine.py
  // _materialize_overview_page），且存量总览页数据已按 content 落库——
  // 兼容读取双键，否则导览引言/章节索引零高度不可见。
  const body = String(
    block.payload?.body ?? block.payload?.content ?? "",
  );

  return (
    <div style={{ color: "rgba(0,0,0,0.88)" }}>
      <LiteMarkdown content={body} />
    </div>
  );
}
