/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/ConceptGraphBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next，i18n 中文直出（zh/app.json）：
 *   "Chapter map · {{chapters}} chapters · {{dependencies}} dependencies"→
 *     章节图谱 · {{chapters}} 章 · {{dependencies}} 条依赖；
 *   "Concept map · {{concepts}} concepts · {{relations}} relations"→
 *     概念图 · {{concepts}} 个概念 · {{relations}} 条关系；
 *   "Chapter index"→章节索引、"(No chapters yet)"→（暂无章节）。
 * next/link <Link href="/book?book=..&page=.."> → react-router-dom useNavigate +
 * <a onClick={() => navigate('/e/sishu/admin/book?book=..&page=..')}>（query 编码保留）。
 * lucide Compass → CompassOutlined；MarkdownRenderer → LiteMarkdown（'./dtMarkdown'，
 * variant 忽略）；@/lib/book-types → './book-types'；Tailwind → 内联样式
 * （grid 两列 minmax(0,1fr)/minmax(0,260px)、line-clamp-2、max-h-[60vh]）。
 */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CompassOutlined } from "@ant-design/icons";

import { LiteMarkdown } from './dtMarkdown';
import type { Block, ConceptGraph } from './book-types';

const borderColor = "#e4e4e7";
const foreground = "rgba(0,0,0,0.88)";
const mutedForeground = "#6b7280";
const monoFont =
  'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace';

export interface ConceptGraphBlockProps {
  block: Block;
  bookId?: string;
  currentPageId?: string;
  language?: string;
}

interface ChapterIndexEntry {
  id: string;
  title: string;
  summary?: string;
  objectives?: string[];
  order?: number;
  content_type?: string;
  page_id?: string;
}

interface IndexPayload {
  chapters: ChapterIndexEntry[];
  node_to_chapter: Record<string, string>;
}

function asGraph(payload: unknown): ConceptGraph | null {
  if (!payload || typeof payload !== "object") return null;
  const candidate = payload as Partial<ConceptGraph>;
  if (!Array.isArray(candidate.nodes) || !Array.isArray(candidate.edges)) {
    return null;
  }
  return candidate as ConceptGraph;
}

function asIndex(payload: unknown): IndexPayload {
  if (!payload || typeof payload !== "object") {
    return { chapters: [], node_to_chapter: {} };
  }
  const candidate = payload as Partial<IndexPayload>;
  return {
    chapters: Array.isArray(candidate.chapters) ? candidate.chapters : [],
    node_to_chapter:
      candidate.node_to_chapter && typeof candidate.node_to_chapter === "object"
        ? candidate.node_to_chapter
        : {},
  };
}

// 原仓 next/link 章节条目（block rounded-md px-2 py-1.5 hover:bg-[var(--background)]）。
function ChapterLink({
  navigateTo,
  children,
}: {
  navigateTo: string;
  children: React.ReactNode;
}) {
  const navigate = useNavigate();
  const [hovered, setHovered] = useState(false);
  return (
    <a
      onClick={() => navigate(navigateTo)}
      style={{
        display: "block",
        borderRadius: 6,
        padding: "6px 8px",
        cursor: "pointer",
        textDecoration: "none",
        color: "inherit",
        background: hovered ? "#f5f5f5" : "transparent",
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </a>
  );
}

export default function ConceptGraphBlock({
  block,
  bookId,
  currentPageId: _currentPageId,
  language: _language,
}: ConceptGraphBlockProps) {
  const code =
    (block.payload?.code as
      | { language?: string; content?: string }
      | undefined) || {};
  const mermaidSrc = String(code.content || "").trim();
  const graph = asGraph(block.payload?.graph);
  const index = asIndex(block.payload?.index);

  const fenced = useMemo(
    () =>
      mermaidSrc
        ? `\`\`\`mermaid\n${mermaidSrc}\n\`\`\``
        : '```mermaid\ngraph TD\n  empty["(no concepts yet)"]\n```',
    [mermaidSrc],
  );

  const chapterNodes = graph?.nodes.filter((n) => n.chapter_id) ?? [];
  const isChapterMap = chapterNodes.length > 0;
  const nodeCount = graph?.nodes.length ?? 0;
  const edgeCount = graph?.edges.length ?? 0;

  return (
    <section
      style={{
        display: "grid",
        gap: 16,
        gridTemplateColumns: "minmax(0,1fr) minmax(0,260px)",
      }}
    >
      <figure
        style={{
          overflow: "hidden",
          borderRadius: 16,
          border: `1px solid ${borderColor}`,
          background: "#fff",
          padding: 12,
          boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
          margin: 0,
        }}
      >
        <header
          style={{
            marginBottom: 8,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 12,
            color: mutedForeground,
          }}
        >
          <CompassOutlined style={{ fontSize: 14 }} />
          <span>
            {isChapterMap
              ? `章节图谱 · ${chapterNodes.length} 章 · ${edgeCount} 条依赖`
              : `概念图 · ${nodeCount} 个概念 · ${edgeCount} 条关系`}
          </span>
        </header>
        <div style={{ maxHeight: "60vh", overflow: "auto" }}>
          <LiteMarkdown content={fenced} />
        </div>
      </figure>

      <aside
        style={{
          borderRadius: 16,
          border: `1px solid ${borderColor}`,
          background: "rgba(255,255,255,0.6)",
          padding: 12,
          boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
        }}
      >
        <h3
          style={{
            marginBottom: 8,
            fontSize: 12,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: mutedForeground,
            margin: "0 0 8px",
          }}
        >
          {"章节索引"}
        </h3>
        <ol
          style={{
            listStyle: "none",
            margin: 0,
            padding: 0,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {index.chapters.length === 0 && (
            <li style={{ fontSize: 12, color: mutedForeground }}>
              （暂无章节）
            </li>
          )}
          {index.chapters.map((chapter, idx) => {
            const label = (
              <span style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span
                  style={{
                    fontSize: 10,
                    fontFamily: monoFont,
                    color: mutedForeground,
                  }}
                >
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <span
                  style={{
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    fontSize: 12,
                    fontWeight: 500,
                    lineHeight: 1.375,
                    color: foreground,
                    textAlign: "left",
                  }}
                >
                  {chapter.title}
                </span>
              </span>
            );
            if (bookId && chapter.page_id) {
              return (
                <li key={chapter.id}>
                  <ChapterLink
                    navigateTo={`/e/sishu/admin/book?book=${encodeURIComponent(bookId)}&page=${encodeURIComponent(chapter.page_id)}`}
                  >
                    {label}
                  </ChapterLink>
                </li>
              );
            }
            return (
              <li
                key={chapter.id}
                style={{
                  borderRadius: 6,
                  padding: "6px 8px",
                  color: foreground,
                }}
              >
                {label}
              </li>
            );
          })}
        </ol>
      </aside>
    </section>
  );
}
