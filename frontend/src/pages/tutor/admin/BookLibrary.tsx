/**
 * BookLibrary —— 书目列表（书库网格）。
 * 1:1 复刻自原仓 DeepTutor web/app/(workspace)/book/components/BookLibrary.tsx（500 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/lib/book-types"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json，模板插值用本地 fmt()）；
 *  - lucide-react → @ant-design/icons 语义就近（Library→DatabaseOutlined、Search→SearchOutlined、Plus→PlusOutlined、
 *    Trash2→DeleteOutlined、BookOpen/GraduationCap→ReadOutlined、Sparkles→ThunderboltOutlined、Loader2→LoadingOutlined、
 *    Layers→AppstoreOutlined、Clock3→ClockCircleOutlined、FileText→FileTextOutlined）；
 *  - import 契约：@/lib/book-types → './book-types'（并行 Agent 同步产出，导出名与原仓一致）；
 *  - Tailwind → antd 组件 + 最小内联样式（颜色映射见 AGENTS 复刻规则：border→#e4e4e7、muted-foreground→#6b7280、
 *    foreground→rgba(0,0,0,0.88)、primary→#1677ff、muted→#f4f4f5 等）；
 *  - hover:bg-accent 类交互 → onMouseEnter/Leave 内联置 background rgba(0,0,0,0.03)；
 *  - 卡片 hover 阴影/位移（hover:-translate-y-0.5 hover:shadow-md）→ 悬停态内联样式；
 *  - 加载态/空态/状态徽标优先 antd（Tag / Empty / Button / Input）。
 * 不变：props 契约（books/loading/onNewBook/onSelectBook/onDeleteBook/onLearn?）、封面调色板、
 *       相对时间文案、两次点击删除确认交互、data-testid。
 */
import { useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { Button, Empty, Input, Tag } from "antd";
import {
  AppstoreOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  FileTextOutlined,
  LoadingOutlined,
  PlusOutlined,
  ReadOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

import type { Book, BookStatus } from "./book-types";

/** 直出中文模板渲染（替代 i18next 插值）：{{var}} → 值 */
function fmt(tpl: string, vars?: Record<string, string | number>): string {
  if (!vars) return tpl;
  return tpl.replace(/\{\{(\w+)\}\}/g, (m, k: string) =>
    Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : m,
  );
}

/** -webkit-line-clamp 截断 */
function clampLines(n: number): CSSProperties {
  return {
    display: "-webkit-box",
    WebkitLineClamp: n,
    WebkitBoxOrient: "vertical",
    overflow: "hidden",
  };
}

const STATUS_STYLES: Record<
  BookStatus,
  { label: string; bg: string; color: string; dot: string; pulse?: boolean }
> = {
  draft: { label: "草稿", bg: "#fffbeb", color: "#b45309", dot: "#f59e0b" },
  spine_ready: { label: "大纲", bg: "#f0f9ff", color: "#0369a1", dot: "#0ea5e9" },
  compiling: {
    label: "编译中",
    bg: "#f5f3ff",
    color: "#6d28d9",
    dot: "#8b5cf6",
    pulse: true,
  },
  ready: { label: "就绪", bg: "#ecfdf5", color: "#047857", dot: "#10b981" },
  error: { label: "错误", bg: "#fff1f2", color: "#be123c", dot: "#f43f5e" },
  archived: { label: "已归档", bg: "#f4f4f5", color: "#52525b", dot: "#a1a1aa" },
};

function relativeTime(seconds: number): string {
  if (!seconds || Number.isNaN(seconds)) return "";
  const diff = Date.now() / 1000 - seconds;
  if (diff < 60) return "刚刚";
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins} 分钟前`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} 小时前`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days} 天前`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} 个月前`;
  return `${Math.floor(months / 12)} 年前`;
}

// Stable, deterministic palette per book id so each cover feels distinct
// without resorting to placeholder letters.
const COVER_PALETTES: Array<{
  base: string;
  accent: string;
  spine: string;
  glow: string;
}> = [
  {
    base: "linear-gradient(135deg, #fdf3e7 0%, #f6dcc1 55%, #e9b88a 100%)",
    accent: "#c97a3f",
    spine: "rgba(168, 87, 35, 0.55)",
    glow: "rgba(255, 198, 140, 0.6)",
  },
  {
    base: "linear-gradient(135deg, #eef5ff 0%, #cfe1f7 55%, #9ec0e8 100%)",
    accent: "#3b6fb6",
    spine: "rgba(43, 89, 156, 0.55)",
    glow: "rgba(150, 196, 255, 0.55)",
  },
  {
    base: "linear-gradient(135deg, #f6efff 0%, #e2cff8 55%, #c2a3ec 100%)",
    accent: "#8254cf",
    spine: "rgba(96, 56, 159, 0.55)",
    glow: "rgba(204, 162, 255, 0.55)",
  },
  {
    base: "linear-gradient(135deg, #ecf8f0 0%, #c8eddc 55%, #93d6b6 100%)",
    accent: "#3a9c72",
    spine: "rgba(36, 117, 80, 0.55)",
    glow: "rgba(160, 232, 199, 0.55)",
  },
  {
    base: "linear-gradient(135deg, #fff4e9 0%, #fcd9b7 55%, #f4ad7d 100%)",
    accent: "#d2683a",
    spine: "rgba(178, 75, 35, 0.55)",
    glow: "rgba(255, 195, 145, 0.6)",
  },
  {
    base: "linear-gradient(135deg, #f1efff 0%, #d6d2f6 55%, #a7a1e6 100%)",
    accent: "#5d54c6",
    spine: "rgba(64, 56, 158, 0.55)",
    glow: "rgba(189, 184, 255, 0.55)",
  },
];

function paletteFor(id: string) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return COVER_PALETTES[hash % COVER_PALETTES.length];
}

export interface BookLibraryProps {
  books: Book[];
  loading: boolean;
  onNewBook: () => void;
  onSelectBook: (id: string) => void;
  onDeleteBook: (id: string) => void;
  onLearn?: (book: Book) => void;
}

export default function BookLibrary({
  books,
  loading,
  onNewBook,
  onSelectBook,
  onDeleteBook,
  onLearn,
}: BookLibraryProps) {
  const [query, setQuery] = useState("");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  // 悬停的书籍卡片 id（替代 Tailwind group-hover）
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return books;
    return books.filter((b) => {
      const t = (b.title || "").toLowerCase();
      const d = (b.description || "").toLowerCase();
      return t.includes(q) || d.includes(q);
    });
  }, [books, query]);

  const stats = useMemo(() => {
    const total = books.length;
    const ready = books.filter((b) => b.status === "ready").length;
    const inProgress = books.filter(
      (b) =>
        b.status === "compiling" ||
        b.status === "spine_ready" ||
        b.status === "draft",
    ).length;
    const chapters = books.reduce((acc, b) => acc + (b.chapter_count || 0), 0);
    return { total, ready, inProgress, chapters };
  }, [books]);

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        minHeight: "100%",
        flexDirection: "column",
        overflow: "hidden",
        background: "#fff",
      }}
    >
      {/* 编译期注入的脉冲动画（compiling 状态圆点，等价 animate-pulse） */}
      <style>{`@keyframes dsh-bl-pulse { 50% { opacity: 0.5; } }`}</style>

      {/* Header bar */}
      <header
        style={{
          display: "flex",
          flexShrink: 0,
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #e4e4e7",
          padding: "12px 24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <DatabaseOutlined
            style={{ fontSize: 18, color: "#6b7280" }}
            aria-label="Library"
          />
          <div>
            <div
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: "rgba(0,0,0,0.88)",
              }}
            >
              书籍
            </div>
            <div style={{ fontSize: 12, color: "#6b7280" }}>
              生成、浏览并学习你的 AI 编写书籍。
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              position: "relative",
              display: "flex",
              alignItems: "center",
            }}
          >
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索书籍"
              prefix={
                <SearchOutlined
                  style={{ color: "rgba(107,114,128,0.7)", fontSize: 13 }}
                />
              }
              style={{
                width: 224,
                height: 32,
                borderRadius: 6,
                fontSize: 12,
                background: "rgba(244,244,245,0.3)",
              }}
            />
          </div>
          <Button
            type="primary"
            onClick={onNewBook}
            data-testid="book-new"
            icon={<PlusOutlined style={{ fontSize: 12 }} />}
            style={{
              height: 30,
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 500,
              padding: "0 12px",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            新建书籍
          </Button>
        </div>
      </header>

      <main style={{ flex: 1, overflowY: "auto", padding: 24 }}>
        {/* Stats row */}
        <div
          style={{
            marginBottom: 24,
            display: "grid",
            gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
            gap: 12,
          }}
        >
          <StatCard
            icon={<ReadOutlined style={{ fontSize: 14 }} />}
            label="书籍总数"
            value={stats.total}
          />
          <StatCard
            icon={<ThunderboltOutlined style={{ fontSize: 14 }} />}
            label="就绪"
            value={stats.ready}
            accent="#059669"
          />
          <StatCard
            icon={<LoadingOutlined style={{ fontSize: 14 }} />}
            label="进行中"
            value={stats.inProgress}
            accent="#7c3aed"
          />
          <StatCard
            icon={<AppstoreOutlined style={{ fontSize: 14 }} />}
            label="章节"
            value={stats.chapters}
          />
        </div>

        {/* Section heading */}
        <div
          style={{
            marginBottom: 12,
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div
              style={{
                fontSize: 11,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.16em",
                color: "#6b7280",
              }}
            >
              我的书库
            </div>
            <div style={{ fontSize: 12, color: "rgba(107,114,128,0.8)" }}>
              {fmt("共 {{total}} 本，显示 {{shown}} 本", {
                shown: filtered.length,
                total: books.length,
              })}
              {query ? ` · 匹配“${query}”` : ""}
            </div>
          </div>
        </div>

        {loading ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              padding: "80px 0",
              fontSize: 14,
              color: "#6b7280",
            }}
          >
            <LoadingOutlined spin style={{ fontSize: 16 }} />
            正在加载书籍…
          </div>
        ) : books.length === 0 ? (
          <EmptyState onNewBook={onNewBook} />
        ) : filtered.length === 0 ? (
          <div
            style={{
              borderRadius: 12,
              border: "1px dashed #e4e4e7",
              background: "rgba(244,244,245,0.3)",
              padding: "48px 24px",
              textAlign: "center",
              fontSize: 14,
              color: "#6b7280",
            }}
          >
            {`没有书籍匹配“${query}”。`}
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: 16,
            }}
          >
            {filtered.map((book) => {
              const isPendingDelete = pendingDeleteId === book.id;
              const status = STATUS_STYLES[book.status] || STATUS_STYLES.draft;
              const palette = paletteFor(book.id);
              const coverStyle: CSSProperties = { background: palette.base };
              const glowStyle: CSSProperties = {
                background: `radial-gradient(circle at 80% 25%, ${palette.glow} 0%, transparent 60%)`,
              };
              const isHovered = hoveredId === book.id;

              return (
                <div
                  key={book.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectBook(book.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectBook(book.id);
                    }
                  }}
                  onMouseEnter={() => setHoveredId(book.id)}
                  onMouseLeave={() =>
                    setHoveredId((prev) => (prev === book.id ? null : prev))
                  }
                  style={{
                    position: "relative",
                    display: "flex",
                    flexDirection: "column",
                    cursor: "pointer",
                    overflow: "hidden",
                    borderRadius: 12,
                    border: `1px solid ${isHovered ? "rgba(22,119,255,0.4)" : "#e4e4e7"}`,
                    background: "rgba(255,255,255,0.7)",
                    boxShadow: isHovered
                      ? "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)"
                      : undefined,
                    transform: isHovered ? "translateY(-2px)" : undefined,
                    transition: "all 0.2s",
                  }}
                >
                  {/* Cover */}
                  <div
                    style={{
                      position: "relative",
                      height: 112,
                      width: "100%",
                      overflow: "hidden",
                      ...coverStyle,
                    }}
                  >
                    {/* Soft glow accent */}
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        pointerEvents: "none",
                        ...glowStyle,
                      }}
                    />
                    {/* Stylized "book spine" stripes on the left edge */}
                    <div
                      style={{
                        position: "absolute",
                        top: 0,
                        bottom: 0,
                        left: 0,
                        width: 8,
                        pointerEvents: "none",
                        background: `linear-gradient(180deg, ${palette.spine} 0%, transparent 100%)`,
                      }}
                    />
                    <div
                      style={{
                        position: "absolute",
                        top: 12,
                        bottom: 12,
                        left: 14,
                        width: 1,
                        pointerEvents: "none",
                        background: palette.spine,
                        opacity: 0.45,
                      }}
                    />
                    {/* Decorative diagonal line pattern */}
                    <svg
                      style={{
                        position: "absolute",
                        inset: 0,
                        height: "100%",
                        width: "100%",
                        opacity: 0.07,
                        pointerEvents: "none",
                      }}
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden
                    >
                      <defs>
                        <pattern
                          id={`diag-${book.id}`}
                          width="14"
                          height="14"
                          patternUnits="userSpaceOnUse"
                          patternTransform="rotate(35)"
                        >
                          <line
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="14"
                            stroke="currentColor"
                            strokeWidth="1"
                          />
                        </pattern>
                      </defs>
                      <rect
                        width="100%"
                        height="100%"
                        fill={`url(#diag-${book.id})`}
                      />
                    </svg>
                    <ReadOutlined
                      style={{
                        position: "absolute",
                        bottom: 12,
                        right: 12,
                        opacity: 0.5,
                        fontSize: 20,
                        color: palette.accent,
                      }}
                    />

                    <Tag
                      style={{
                        position: "absolute",
                        left: 16,
                        top: 12,
                        margin: 0,
                        border: "none",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                        borderRadius: 999,
                        padding: "1px 8px",
                        lineHeight: "16px",
                        fontSize: 10,
                        fontWeight: 500,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        background: status.bg,
                        color: status.color,
                      }}
                    >
                      <span
                        style={{
                          display: "inline-block",
                          width: 6,
                          height: 6,
                          borderRadius: 999,
                          background: status.dot,
                          animation: status.pulse
                            ? "dsh-bl-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite"
                            : undefined,
                        }}
                      />
                      {status.label}
                    </Tag>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        if (isPendingDelete) {
                          onDeleteBook(book.id);
                          setPendingDeleteId(null);
                        } else {
                          setPendingDeleteId(book.id);
                        }
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = isPendingDelete
                          ? "rgba(244,63,94,0.15)"
                          : "rgba(244,63,94,0.1)";
                        e.currentTarget.style.color = "#f43f5e";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = isPendingDelete
                          ? "rgba(244,63,94,0.15)"
                          : "rgba(255,255,255,0.6)";
                        e.currentTarget.style.color = isPendingDelete
                          ? "#f43f5e"
                          : "#6b7280";
                      }}
                      title={isPendingDelete ? "再次点击确认" : "删除书籍"}
                      style={{
                        position: "absolute",
                        right: 8,
                        top: 8,
                        borderRadius: 6,
                        padding: 6,
                        lineHeight: 0,
                        cursor: "pointer",
                        border: "none",
                        transition: "opacity 0.2s, background 0.2s, color 0.2s",
                        opacity: isHovered ? 1 : 0,
                        backdropFilter: "blur(4px)",
                        background: isPendingDelete
                          ? "rgba(244,63,94,0.15)"
                          : "rgba(255,255,255,0.6)",
                        color: isPendingDelete ? "#f43f5e" : "#6b7280",
                      }}
                    >
                      <DeleteOutlined style={{ fontSize: 13 }} />
                    </button>
                  </div>

                  {/* Body */}
                  <div
                    style={{
                      display: "flex",
                      flex: 1,
                      flexDirection: "column",
                      gap: 8,
                      padding: 16,
                    }}
                  >
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
                    <p
                      style={{
                        ...clampLines(3),
                        flex: 1,
                        margin: 0,
                        fontSize: 12,
                        lineHeight: 1.625,
                        color: "#6b7280",
                      }}
                    >
                      {book.description || "暂无描述。打开书籍查看大纲。"}
                    </p>
                    <div
                      style={{
                        marginTop: "auto",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        fontSize: 10,
                        color: "rgba(107,114,128,0.8)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span
                          style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                        >
                          <AppstoreOutlined style={{ fontSize: 11 }} />
                          {fmt("{{count}} 章", { count: book.chapter_count || 0 })}
                        </span>
                        <span
                          style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                        >
                          <FileTextOutlined style={{ fontSize: 11 }} />
                          {fmt("{{count}} 页", { count: book.page_count || 0 })}
                        </span>
                      </div>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                        <ClockCircleOutlined style={{ fontSize: 11 }} />
                        {relativeTime(book.updated_at) || "—"}
                      </span>
                    </div>
                    {onLearn && book.status === "ready" && (
                      <Button
                        type="primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          onLearn(book);
                        }}
                        icon={<ReadOutlined style={{ fontSize: 13 }} />}
                        style={{
                          marginTop: 8,
                          height: 30,
                          borderRadius: 6,
                          fontSize: 12,
                          fontWeight: 500,
                          padding: "0 12px",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          alignSelf: "flex-start",
                        }}
                      >
                        开始学习
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  accent?: string;
}) {
  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid #e4e4e7",
        background: "rgba(244,244,245,0.4)",
        padding: "12px 16px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 11,
          fontWeight: 500,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: "#6b7280",
        }}
      >
        <span style={{ color: accent || "#6b7280", lineHeight: 0 }}>{icon}</span>
        {label}
      </div>
      <div
        style={{
          marginTop: 4,
          fontSize: 20,
          fontWeight: 600,
          color: accent || "rgba(0,0,0,0.88)",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function EmptyState({ onNewBook }: { onNewBook: () => void }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 16,
        borderRadius: 12,
        border: "1px dashed #e4e4e7",
        background: "rgba(244,244,245,0.3)",
        padding: "64px 32px",
        textAlign: "center",
      }}
    >
      <Empty
        image={
          <ReadOutlined
            style={{ fontSize: 28, color: "rgba(107,114,128,0.5)" }}
          />
        }
        description={
          <>
            <p
              style={{
                margin: 0,
                fontSize: 16,
                fontWeight: 500,
                color: "rgba(0,0,0,0.88)",
              }}
            >
              暂无书籍
            </p>
            <p style={{ margin: "4px 0 0", fontSize: 14, color: "#6b7280" }}>
              从知识库、聊天片段，或一个主题开始创建你的第一本 AI 书籍。
            </p>
          </>
        }
        style={{ margin: 0 }}
      />
      <Button
        type="primary"
        onClick={onNewBook}
        icon={<PlusOutlined style={{ fontSize: 14 }} />}
        style={{
          height: 32,
          borderRadius: 6,
          fontSize: 14,
          fontWeight: 500,
          padding: "0 12px",
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        新建书籍
      </Button>
    </div>
  );
}
