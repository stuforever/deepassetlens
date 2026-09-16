/**
 * BookSidebar —— 书目详情页左侧章节树侧栏（可折叠）。
 * 1:1 复刻自原仓 DeepTutor web/app/(workspace)/book/components/BookSidebar.tsx（190 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/lib/book-types"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json）；
 *  - lucide-react → @ant-design/icons 语义就近（ArrowLeft→ArrowLeftOutlined、ChevronLeft→LeftOutlined、
 *    ChevronRight→RightOutlined、Loader2→LoadingOutlined spin、RotateCcw→RedoOutlined、Compass→GlobalOutlined）；
 *  - import 契约：@/lib/book-types → './book-types'（并行 Agent 同步产出，导出名与原仓一致）；
 *  - Tailwind → antd 组件 + 最小内联样式（border→#e4e4e7、muted-foreground→#6b7280、foreground→rgba(0,0,0,0.88)、
 *    primary/15→rgba(22,119,255,0.15)、muted/40 hover→rgba(0,0,0,0.03)、muted→#f4f4f5）；
 *  - hover:bg-[var(--muted)]/40 类交互 → onMouseEnter/Leave 内联置 background rgba(0,0,0,0.03)；
 *  - line-clamp-2 → -webkit-box 截断；状态小胶囊/重建按钮优先 antd（Tag / Button）。
 * 不变：props 契约（book/onBackToLibrary/pages/selectedPageId/onSelectPage/onRebuild/rebuilding）、
 *       STATUS_LABEL 映射、折叠/展开交互、data-testid="book-page-item"。
 */
import { useState } from "react";
import { Button, Tag } from "antd";
import {
  ArrowLeftOutlined,
  GlobalOutlined,
  LeftOutlined,
  LoadingOutlined,
  RedoOutlined,
  RightOutlined,
} from "@ant-design/icons";
import type { Book, Page } from "./book-types";

const STATUS_LABEL: Record<string, string> = {
  pending: "排队中",
  planning: "规划",
  generating: "编译中",
  ready: "就绪",
  partial: "部分完成",
  error: "失败",
};

/** 书籍主状态 → 中文（等价原 t(book.status)，key 取自原仓 zh/app.json） */
const BOOK_STATUS_LABEL: Record<string, string> = {
  draft: "草稿",
  spine_ready: "大纲就绪",
  compiling: "编译中",
  ready: "就绪",
  error: "错误",
  archived: "已归档",
};

/** -webkit-line-clamp 截断 */
function clampLines(n: number): React.CSSProperties {
  return {
    display: "-webkit-box",
    WebkitLineClamp: n,
    WebkitBoxOrient: "vertical",
    overflow: "hidden",
  };
}

export interface BookSidebarProps {
  book: Book | null;
  onBackToLibrary: () => void;
  pages?: Page[];
  selectedPageId?: string | null;
  onSelectPage?: (id: string) => void;
  onRebuild?: () => void;
  rebuilding?: boolean;
}

export default function BookSidebar({
  book,
  onBackToLibrary,
  pages = [],
  selectedPageId = null,
  onSelectPage,
  onRebuild,
  rebuilding = false,
}: BookSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <aside
        style={{
          display: "flex",
          height: "100%",
          width: 56,
          flexDirection: "column",
          alignItems: "center",
          gap: 12,
          borderRight: "1px solid #e4e4e7",
          background: "rgba(255,255,255,0.4)",
          padding: "16px 8px",
        }}
      >
        <button
          onClick={onBackToLibrary}
          title="全部书籍"
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(0,0,0,0.03)";
            e.currentTarget.style.color = "rgba(0,0,0,0.88)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "";
            e.currentTarget.style.color = "#6b7280";
          }}
          style={{
            display: "inline-flex",
            height: 32,
            width: 32,
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 6,
            border: "none",
            cursor: "pointer",
            color: "#6b7280",
            background: "transparent",
            transition: "background 0.2s, color 0.2s",
          }}
        >
          <ArrowLeftOutlined style={{ fontSize: 16 }} />
        </button>
        <button
          onClick={() => setCollapsed(false)}
          title="展开章节"
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(0,0,0,0.03)";
            e.currentTarget.style.color = "rgba(0,0,0,0.88)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "";
            e.currentTarget.style.color = "#6b7280";
          }}
          style={{
            display: "inline-flex",
            height: 32,
            width: 32,
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 6,
            border: "none",
            cursor: "pointer",
            color: "#6b7280",
            background: "transparent",
            transition: "background 0.2s, color 0.2s",
          }}
        >
          <RightOutlined style={{ fontSize: 16 }} />
        </button>
        <div style={{ marginTop: 4, height: 1, width: 32, background: "#e4e4e7" }} />
        <div
          style={{
            display: "flex",
            flex: 1,
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
            overflowY: "auto",
          }}
        >
          {pages.map((page, index) => {
            const active = page.id === selectedPageId;
            return (
              <button
                key={page.id}
                onClick={() => onSelectPage?.(page.id)}
                title={page.title || "未命名"}
                onMouseEnter={(e) => {
                  if (!active) {
                    e.currentTarget.style.background = "rgba(0,0,0,0.03)";
                    e.currentTarget.style.color = "rgba(0,0,0,0.88)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    e.currentTarget.style.background = "";
                    e.currentTarget.style.color = "#6b7280";
                  }
                }}
                style={{
                  display: "inline-flex",
                  height: 32,
                  width: 32,
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: 6,
                  border: "none",
                  cursor: "pointer",
                  fontSize: 11,
                  fontWeight: 600,
                  color: active ? "rgba(0,0,0,0.88)" : "#6b7280",
                  background: active ? "rgba(22,119,255,0.15)" : "transparent",
                  transition: "background 0.2s, color 0.2s",
                }}
              >
                {page.content_type === "overview" ? (
                  <GlobalOutlined style={{ fontSize: 14 }} />
                ) : (
                  index + 1
                )}
              </button>
            );
          })}
        </div>
      </aside>
    );
  }

  return (
    <aside
      style={{
        display: "flex",
        height: "100%",
        width: 232,
        flexDirection: "column",
        gap: 12,
        borderRight: "1px solid #e4e4e7",
        background: "rgba(255,255,255,0.4)",
        padding: "16px 12px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <button
          onClick={onBackToLibrary}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(0,0,0,0.03)";
            e.currentTarget.style.color = "rgba(0,0,0,0.88)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "";
            e.currentTarget.style.color = "#6b7280";
          }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            alignSelf: "flex-start",
            borderRadius: 6,
            border: "none",
            cursor: "pointer",
            padding: "4px 8px",
            fontSize: 12,
            fontWeight: 500,
            color: "#6b7280",
            background: "transparent",
            transition: "background 0.2s, color 0.2s",
          }}
        >
          <ArrowLeftOutlined style={{ fontSize: 14 }} /> 全部书籍
        </button>
        <button
          onClick={() => setCollapsed(true)}
          title="折叠章节"
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(0,0,0,0.03)";
            e.currentTarget.style.color = "rgba(0,0,0,0.88)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "";
            e.currentTarget.style.color = "#6b7280";
          }}
          style={{
            display: "inline-flex",
            height: 28,
            width: 28,
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 6,
            border: "none",
            cursor: "pointer",
            color: "#6b7280",
            background: "transparent",
            transition: "background 0.2s, color 0.2s",
          }}
        >
          <LeftOutlined style={{ fontSize: 14 }} />
        </button>
      </div>

      {book && (
        <div style={{ padding: "0 4px" }}>
          <div
            style={{
              ...clampLines(2),
              fontSize: 14,
              fontWeight: 600,
              color: "rgba(0,0,0,0.88)",
            }}
            title={book.title || "未命名书籍"}
          >
            {book.title || "未命名书籍"}
          </div>
          <div
            style={{
              marginTop: 2,
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "#6b7280",
            }}
          >
            {BOOK_STATUS_LABEL[book.status] || book.status} ·{" "}
            {`${book.chapter_count || 0} 章`}
          </div>
        </div>
      )}

      {onRebuild && (
        <Button
          onClick={onRebuild}
          disabled={rebuilding}
          block
          icon={
            rebuilding ? (
              <LoadingOutlined spin style={{ fontSize: 14 }} />
            ) : (
              <RedoOutlined style={{ fontSize: 14 }} />
            )
          }
          style={{
            height: 30,
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 500,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
          }}
        >
          重建书籍
        </Button>
      )}

      <section style={{ flex: 1, overflowY: "auto" }}>
        {pages.length === 0 ? (
          <div
            style={{
              borderRadius: 6,
              border: "1px dashed #e4e4e7",
              padding: "12px 8px",
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            确认章节主线后，页面会出现在这里。
          </div>
        ) : (
          <>
            <div
              style={{
                marginBottom: 8,
                fontSize: 11,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.16em",
                color: "#6b7280",
              }}
            >
              章节
            </div>
            <ul
              style={{
                listStyle: "none",
                margin: 0,
                padding: 0,
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              {pages.map((page) => {
                const active = page.id === selectedPageId;
                const isOverview = page.content_type === "overview";
                return (
                  <li key={page.id}>
                    <button
                      onClick={() => onSelectPage?.(page.id)}
                      data-testid="book-page-item"
                      onMouseEnter={(e) => {
                        if (!active) {
                          e.currentTarget.style.background = "rgba(0,0,0,0.03)";
                          e.currentTarget.style.color = "rgba(0,0,0,0.88)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!active) {
                          e.currentTarget.style.background = "";
                          e.currentTarget.style.color = "#6b7280";
                        }
                      }}
                      style={{
                        display: "flex",
                        width: "100%",
                        alignItems: "flex-start",
                        justifyContent: "space-between",
                        gap: 8,
                        borderRadius: 6,
                        border: isOverview
                          ? "1px dashed #e4e4e7"
                          : "1px solid transparent",
                        cursor: "pointer",
                        textAlign: "left",
                        padding: "6px 8px",
                        fontSize: 12,
                        color: active ? "rgba(0,0,0,0.88)" : "#6b7280",
                        background: active
                          ? "rgba(22,119,255,0.15)"
                          : "transparent",
                        transition: "background 0.2s, color 0.2s",
                      }}
                    >
                      <span
                        style={{
                          display: "flex",
                          minWidth: 0,
                          alignItems: "flex-start",
                          gap: 6,
                        }}
                      >
                        {isOverview && (
                          <GlobalOutlined
                            style={{
                              marginTop: 1,
                              fontSize: 12,
                              flexShrink: 0,
                              color: "#1677ff",
                            }}
                          />
                        )}
                        <span style={clampLines(2)}>
                          {page.title || "未命名"}
                        </span>
                      </span>
                      <Tag
                        style={{
                          flexShrink: 0,
                          margin: 0,
                          border: "none",
                          borderRadius: 999,
                          padding: "1px 6px",
                          lineHeight: "14px",
                          fontSize: 9,
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                          background: "#f4f4f5",
                          color: "#6b7280",
                        }}
                      >
                        {STATUS_LABEL[page.status] || page.status}
                      </Tag>
                    </button>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </section>
    </aside>
  );
}
