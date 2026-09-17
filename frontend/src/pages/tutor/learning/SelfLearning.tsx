/**
 * SelfLearning —— 自主学习（桌面 workspace）。
 * 1:1 复刻自原仓 DeepTutor web/app/(workspace)/self-learning/page.tsx（169 行，批6 6.3）；
 * 子组件 ChapterTree（源 components/ChapterTree.tsx，102 行）内联移植（清单外文件不落盘）。
 * 复刻来源：Next.js("use client") + Tailwind + react-i18next + lucide-react + next/navigation
 * 替换点：
 *  - "use client" 删除；Suspense 包裹结构与 fallback 逐字保留（react-router 的
 *    useSearchParams 无挂起语义，包裹为等价结构）；
 *  - useSearchParams/useRouter(next/navigation) → react-router-dom 同名 hook；
 *    源 router.replace(`/self-learning?${params}`, { scroll: false }) →
 *    navigate(`${pathname}?${params}`, { replace: true })（pathname 动态取当前挂载路径，
 *    "当前页 replace 且不滚动"语义等价）；
 *  - react-i18next → 中文直出（译文逐键取自原仓 web/locales/zh/app.json，含 tab.* 键：
 *    Self-directed Learning→自主学习、{{count}} textbooks · …→{{count}} 本教材 · …、
 *    ◀ Collapse→◀ 收起目录、▶ Expand→▶ 展开目录、Select a chapter to start learning→
 *    选择一个章节开始学习、Loading textbook data...→加载教材数据...、Loading chapter
 *    data...→加载章节数据...、Loading...→加载中…、{{count}} chapters→{{count}} 章、
 *    No textbook data...→暂无教材数据...；插值用本地 fmt()）；
 *  - @/lib/self-learning-api → 复用本仓已移植件 ../h5/h5shared/selfLearningApi
 *    （fetchTextbookTree/fetchChapterOverview + TextbookNode/ChapterNode/ChapterOverview
 *    类型，同源自 lib/self-learning-api.ts，导出名与契约逐字一致）；
 *  - lucide-react → @ant-design/icons 语义就近（沿用 BookLibrary/H5Learn 先例）：
 *    BookOpen→ReadOutlined、GraduationCap→ReadOutlined、Loader2→LoadingOutlined(spin)、
 *    ChevronDown→DownOutlined、ChevronRight→RightOutlined、FileText→FileTextOutlined；
 *  - Tailwind → antd 组件 + 内联样式 + <style> 注入（树节点/tab 的 hover 态与选中
 *    ring 无法用内联 style 表达，语义注入 <style>）；颜色映射沿用 BookLibrary 登记口径：
 *    border→#e4e4e7、muted→#f4f4f5、muted-foreground→#6b7280、foreground→rgba(0,0,0,0.88)、
 *    primary→#1677ff、accent hover→rgba(0,0,0,0.03)、bg-card/50→rgba(255,255,255,0.5)、
 *    bg-muted/20→rgba(244,244,245,0.2)、primary/10→rgba(22,119,255,0.1)；
 *  - next/image：本页无图片。
 * 边界登记（批6 6.3 计划圈定「章节树/学习动线入口」）：源 ChapterTabs 引用的 11 个
 * tabs/* 正文组件（OriginalTextTab/KnowledgePointsTab/InternalBooksTab/WrongQuestionsTab/
 * CoursewareTab/ExerciseTab/NotesTab/MemoryTab/AIResourceTab/VoiceVideoTab/ReciteTab）
 * 属清单外文件，本批不创建；TabBar（11 页签/emoji/徽标计数）/overview 加载态 1:1，
 * tab 正文区做「学习动线入口」提示卡 + 跳转 h5 学习动线 /e/tutor/h5/learn?chapter_id=<id>
 * （与 h5 版各自 1:1 并存），后续批补齐正文。
 * 不变：URL 参数自动选章（chapter_id/textbook_id/tab 三级 else-if 链、findFirst 递归）、
 *       章节 URL replace 同步、data-testid 全量（self-learning-sidebar-toggle、chapter-tree、
 *       tree-chapter-<id>、tree-textbook-<id>、self-learning-main、self-learning-empty、
 *       chapter-tabs、chapter-tab-<id>、chapter-tab-content、chapter-tab-loading）、
 *       树展开 Set、order 排序。
 */
import { Suspense, useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "antd";
import {
  DownOutlined,
  FileTextOutlined,
  LoadingOutlined,
  ReadOutlined,
  RightOutlined,
} from "@ant-design/icons";
import {
  fetchChapterOverview,
  fetchTextbookTree,
} from "../h5/h5shared/selfLearningApi";
import type {
  ChapterNode,
  ChapterOverview,
  TextbookNode,
} from "../h5/h5shared/selfLearningApi";

/** 直出中文模板渲染（替代 i18next 插值）：{{var}} → 值 */
function fmt(tpl: string, vars?: Record<string, string | number>): string {
  if (!vars) return tpl;
  return tpl.replace(/\{\{(\w+)\}\}/g, (m, k: string) =>
    Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : m,
  );
}

/** 树节点/tab 的悬停态、选中态（hover:bg-accent、bg-primary/10+ring、border-b-2 页签）。 */
const SL_CSS = `
.sl-tree-item { display: flex; align-items: center; gap: 4px; padding: 6px 8px; border-radius: 6px; cursor: pointer; font-size: 14px; color: rgba(0, 0, 0, 0.88); transition: background-color 0.15s; }
.sl-tree-item:hover { background: rgba(0, 0, 0, 0.03); }
.sl-tree-item[data-selected="1"] { background: rgba(22, 119, 255, 0.1); box-shadow: 0 0 0 1px rgba(22, 119, 255, 0.3); font-weight: 500; }
.sl-tree-toggle { border: none; background: transparent; padding: 2px; border-radius: 4px; cursor: pointer; line-height: 0; color: rgba(0, 0, 0, 0.88); }
.sl-tree-toggle:hover { background: rgba(0, 0, 0, 0.03); }
.sl-tab { border: none; background: transparent; padding: 8px 12px; font-size: 14px; white-space: nowrap; cursor: pointer; border-bottom: 2px solid transparent; border-radius: 0; color: #6b7280; transition: color 0.15s, background-color 0.15s, border-color 0.15s; }
.sl-tab:hover { color: rgba(0, 0, 0, 0.88); background: rgba(0, 0, 0, 0.03); }
.sl-tab[data-active="1"] { color: #1677ff; border-bottom-color: #1677ff; font-weight: 500; background: rgba(22, 119, 255, 0.05); }
`;

/* ── ChapterTree（内联自源 components/ChapterTree.tsx，1:1 逻辑）───────────── */

interface ChapterTreeProps {
  textbooks: TextbookNode[];
  selectedChapterId: string | null;
  onSelectChapter: (chapter: ChapterNode, textbook: TextbookNode) => void;
}

export function ChapterTree({ textbooks, selectedChapterId, onSelectChapter }: ChapterTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const renderChapter = (ch: ChapterNode, textbook: TextbookNode, depth: number) => {
    const hasChildren = ch.children && ch.children.length > 0;
    const isExpanded = expanded.has(ch.id);
    const isSelected = selectedChapterId === ch.id;

    return (
      <div key={ch.id}>
        <div
          className="sl-tree-item"
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
          onClick={() => onSelectChapter(ch, textbook)}
          data-testid={`tree-chapter-${ch.id}`}
          data-selected={isSelected ? "1" : "0"}
        >
          {hasChildren ? (
            <button
              className="sl-tree-toggle"
              onClick={(e) => { e.stopPropagation(); toggle(ch.id); }}
            >
              {isExpanded ? <DownOutlined style={{ fontSize: 14 }} /> : <RightOutlined style={{ fontSize: 14 }} />}
            </button>
          ) : (
            <FileTextOutlined style={{ fontSize: 14, color: "#6b7280", marginLeft: 4 }} />
          )}
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ch.name}</span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {ch.children
              .sort((a, b) => a.order - b.order)
              .map((child) => renderChapter(child, textbook, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (textbooks.length === 0) {
    return (
      <div style={{ padding: 16, fontSize: 14, color: "#6b7280" }}>
        暂无教材数据。请在 设置 → 设置管理 中添加教材和章节。
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {textbooks.map((tb) => {
        const isExpanded = expanded.has(tb.id);
        return (
          <div key={tb.id}>
            <div
              className="sl-tree-item"
              style={{ padding: "8px 8px", gap: 6, fontWeight: 600 }}
              onClick={() => toggle(tb.id)}
              data-testid={`tree-textbook-${tb.id}`}
            >
              {isExpanded ? <DownOutlined style={{ fontSize: 16 }} /> : <RightOutlined style={{ fontSize: 16 }} />}
              <ReadOutlined style={{ fontSize: 16, color: "#1677ff" }} />
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{tb.name}</span>
              <span style={{ fontSize: 12, color: "#6b7280", marginLeft: "auto" }}>{fmt("{{count}} 章", { count: tb.chapters?.length || 0 })}</span>
            </div>
            {isExpanded && (
              <div>
                {(tb.chapters || [])
                  .sort((a, b) => a.order - b.order)
                  .map((ch) => renderChapter(ch, tb, 0))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── ChapterTabs（内联自源 components/ChapterTabs.tsx）──────────────────────
 * TabBar/徽标/加载态 1:1；labelKey(tab.*)→中文直出。正文 11 个 tabs/* 组件为清单外
 * 文件（见文件头边界登记），正文区按计划做「学习动线入口」提示卡。
 */

const TABS = [
  { id: "original", label: "原文", labelKey: "tab.original", icon: "📄" },
  { id: "internal_books", label: "内部书籍", labelKey: "tab.internal_books", icon: "📖" },
  { id: "courseware", label: "课件", labelKey: "tab.courseware", icon: "📚" },
  { id: "voice", label: "语音视频", labelKey: "tab.voice", icon: "📣" },
  { id: "recite", label: "背诵默写", labelKey: "tab.recite", icon: "🎙" },
  { id: "knowledge", label: "知识点总结", labelKey: "tab.knowledge", icon: "💡" },
  { id: "exercise", label: "练习", labelKey: "tab.exercise", icon: "🎯" },
  { id: "wrong", label: "错题", labelKey: "tab.wrong", icon: "❌" },
  { id: "notes", label: "笔记", labelKey: "tab.notes", icon: "📝" },
  { id: "memory", label: "学情", labelKey: "tab.memory", icon: "🧠" },
  { id: "ai", label: "AI资源", labelKey: "tab.ai", icon: "✨" },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** 批6 6.3 边界占位：tab 正文入口卡（跳 h5 学习动线），后续批以 tabs/* 正文组件替换。 */
function ChapterTabEntry({
  tabLabel,
  chapterId,
  chapterName,
  textbookName,
}: {
  tabLabel: string;
  chapterId: string;
  chapterName: string;
  textbookName: string;
}) {
  const navigate = useNavigate();
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 320,
        padding: 32,
      }}
    >
      <div style={{ textAlign: "center", maxWidth: 448 }}>
        <ReadOutlined style={{ fontSize: 40, color: "#1677ff", marginBottom: 16 }} />
        <h3 style={{ margin: 0, marginBottom: 8, fontSize: 16, fontWeight: 600, color: "rgba(0,0,0,0.88)" }}>
          「{tabLabel}」学习动线
        </h3>
        <p style={{ margin: 0, marginBottom: 16, fontSize: 14, lineHeight: 1.625, color: "#6b7280" }}>
          当前章节：{textbookName} / {chapterName}。该页签完整功能由 h5 学习动线承载，前往移动端学习页继续本章学习。
        </p>
        <Button
          type="primary"
          icon={<ReadOutlined />}
          onClick={() => navigate(`/e/tutor/h5/learn?chapter_id=${encodeURIComponent(chapterId)}`)}
        >
          前往 h5 学习动线
        </Button>
      </div>
    </div>
  );
}

export function ChapterTabs({
  chapter,
  textbook,
  initialTab,
}: {
  chapter: ChapterNode;
  textbook: TextbookNode;
  initialTab?: string;
}) {
  const [activeTab, setActiveTab] = useState<TabId>("original");
  const [overview, setOverview] = useState<ChapterOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setActiveTab((initialTab as TabId) || "original");
    fetchChapterOverview(chapter.id)
      .then((data) => { setOverview(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [chapter.id, initialTab]);

  // Badge counts for tab labels
  const badges: Partial<Record<TabId, number>> = {};
  if (overview) {
    badges.knowledge = overview.knowledge_points?.length || 0;
    badges.wrong = overview.wrong_questions?.count || 0;
    badges.courseware = overview.related_books?.length || 0;
  }

  const activeDef = TABS.find((t) => t.id === activeTab);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Tab Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          padding: "0 8px",
          borderBottom: "1px solid #e4e4e7",
          overflowX: "auto",
          flexShrink: 0,
        }}
        data-testid="chapter-tabs"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className="sl-tab"
            onClick={() => setActiveTab(tab.id)}
            data-testid={`chapter-tab-${tab.id}`}
            data-active={activeTab === tab.id ? "1" : "0"}
          >
            <span style={{ marginRight: 4 }}>{tab.icon}</span>
            {tab.label}
            {badges[tab.id] !== undefined && badges[tab.id]! > 0 && (
              <span
                style={{
                  marginLeft: 4,
                  fontSize: 12,
                  padding: "2px 6px",
                  borderRadius: 9999,
                  background: "rgba(22, 119, 255, 0.1)",
                  color: "#1677ff",
                }}
              >
                {badges[tab.id]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={{ flex: 1, overflowY: "auto" }} data-testid="chapter-tab-content">
        {loading ? (
          <div
            style={{
              padding: 32,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#6b7280",
            }}
            data-testid="chapter-tab-loading"
          >
            <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载章节数据...
          </div>
        ) : (
          activeDef && (
            <ChapterTabEntry
              tabLabel={activeDef.label}
              chapterId={chapter.id}
              chapterName={chapter.name}
              textbookName={textbook.name}
            />
          )
        )}
      </div>
    </div>
  );
}

/* ── 页面（源 page.tsx 逐区块移植）────────────────────────────────────────── */

function SelfLearningContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [textbooks, setTextbooks] = useState<TextbookNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChapter, setSelectedChapter] = useState<ChapterNode | null>(null);
  const [selectedTextbook, setSelectedTextbook] = useState<TextbookNode | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const initialTab = searchParams.get("tab") || undefined;

  // Load textbooks
  useEffect(() => {
    fetchTextbookTree()
      .then((data) => {
        setTextbooks(data || []);
        setLoading(false);

        // Auto-select from URL params
        const chapterId = searchParams.get("chapter_id");
        const textbookId = searchParams.get("textbook_id");
        const requestedTab = searchParams.get("tab");
        if (chapterId) {
          for (const tb of data || []) {
            const findInTree = (chapters: ChapterNode[]): ChapterNode | null => {
              for (const ch of chapters) {
                if (ch.id === chapterId) return ch;
                if (ch.children) {
                  const found = findInTree(ch.children);
                  if (found) return found;
                }
              }
              return null;
            };
            const found = findInTree(tb.chapters || []);
            if (found) {
              setSelectedChapter(found);
              setSelectedTextbook(tb);
              return;
            }
          }
        } else if (textbookId) {
          const tb = (data || []).find((t) => t.id === textbookId);
          if (tb) setSelectedTextbook(tb);
        } else if (requestedTab) {
          // H5 入口（拍错题/学情）未指定章节时自动选第一个可用章节
          for (const tb of data || []) {
            const findFirst = (chapters: ChapterNode[]): ChapterNode | null => {
              if (!chapters.length) return null;
              const first = chapters[0];
              if (first.children && first.children.length) return findFirst(first.children);
              return first;
            };
            const first = findFirst(tb.chapters || []);
            if (first) {
              setSelectedChapter(first);
              setSelectedTextbook(tb);
              return;
            }
          }
        }
      })
      .catch(() => setLoading(false));
  }, [searchParams]);

  const onSelectChapter = useCallback((chapter: ChapterNode, textbook: TextbookNode) => {
    setSelectedChapter(chapter);
    setSelectedTextbook(textbook);
    // Update URL without full navigation
    const params = new URLSearchParams();
    params.set("chapter_id", chapter.id);
    params.set("textbook_id", textbook.id);
    navigate(`${location.pathname}?${params.toString()}`, { replace: true });
  }, [navigate, location.pathname]);

  if (loading) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#6b7280" }}>
        <LoadingOutlined spin style={{ fontSize: 24, marginRight: 8 }} /> 加载教材数据...
      </div>
    );
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: "1px solid #e4e4e7",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ReadOutlined style={{ fontSize: 20, color: "#1677ff" }} />
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: "rgba(0,0,0,0.88)" }}>自主学习</h1>
          <span style={{ fontSize: 12, color: "#6b7280" }}>
            {fmt("{{count}} 本教材 · 以课本章节为主线串联所有学习内容", { count: textbooks.length })}
          </span>
        </div>
        <Button
          size="small"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          data-testid="self-learning-sidebar-toggle"
        >
          {sidebarOpen ? "◀ 收起目录" : "▶ 展开目录"}
        </Button>
      </div>

      {/* Main: sidebar + content */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Left: Chapter Tree */}
        {sidebarOpen && (
          <aside
            style={{
              width: 288,
              flexShrink: 0,
              borderRight: "1px solid #e4e4e7",
              overflowY: "auto",
              background: "rgba(255, 255, 255, 0.5)",
              padding: 4,
            }}
            data-testid="chapter-tree"
          >
            <ChapterTree
              textbooks={textbooks}
              selectedChapterId={selectedChapter?.id || null}
              onSelectChapter={onSelectChapter}
            />
          </aside>
        )}

        {/* Right: Tab Content */}
        <main style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }} data-testid="self-learning-main">
          {selectedChapter && selectedTextbook ? (
            <>
              {/* Chapter Header */}
              <div
                style={{
                  padding: "8px 16px",
                  borderBottom: "1px solid #e4e4e7",
                  flexShrink: 0,
                  background: "rgba(244, 244, 245, 0.2)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
                  <ReadOutlined style={{ fontSize: 16, color: "#1677ff" }} />
                  <span style={{ color: "#6b7280" }}>{selectedTextbook.name}</span>
                  <span style={{ color: "#6b7280" }}>/</span>
                  <span style={{ fontWeight: 500, color: "rgba(0,0,0,0.88)" }}>{selectedChapter.name}</span>
                </div>
              </div>
              {/* Tabs */}
              <div style={{ flex: 1, overflow: "hidden" }}>
                <ChapterTabs chapter={selectedChapter} textbook={selectedTextbook} initialTab={initialTab} />
              </div>
            </>
          ) : (
            <div
              style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}
              data-testid="self-learning-empty"
            >
              <div style={{ textAlign: "center", maxWidth: 448 }}>
                <ReadOutlined style={{ fontSize: 48, color: "#6b7280", marginBottom: 16 }} />
                <h2 style={{ margin: 0, marginBottom: 8, fontSize: 18, fontWeight: 600, color: "rgba(0,0,0,0.88)" }}>选择一个章节开始学习</h2>
                <p style={{ margin: 0, fontSize: 14, color: "#6b7280" }}>
                  从左侧目录中选择教材和章节，系统将展示该章节的原文、内部书籍、课件、语音视频、知识点总结、练习、错题、笔记、记忆和 AI 资源。
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default function SelfLearningPage() {
  return (
    <Suspense
      fallback={
        <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#6b7280" }}>
          <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载中…
        </div>
      }
    >
      <SelfLearningContent />
    </Suspense>
  );
}
