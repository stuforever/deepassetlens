/**
 * ── 复刻来源与替换点（tupu antd 复刻）─────────────────────────────────
 * 源文件：DeepTutor web/app/(workspace)/book/components/PageReader.tsx
 * 目标：frontend/src/pages/tutor/admin/PageReader.tsx
 * book 阅读器主组件（可折叠头部 + 块渲染 + 失败块重试 + 插入块菜单 +
 * 朗读联动），布局/交互/文案 1:1。
 * 替换点：
 * - "use client" 已删除；
 * - react-i18next → 中文直出，译文取自 DeepTutor locales/zh/app.json 原样：
 *   "Select a chapter to start reading."→选择一个章节开始阅读。、
 *   "Expand header"→展开标题栏、"Collapse header"→折叠标题栏、
 *   "Untitled chapter"→未命名章节、"Compiling page…"→正在编译页面…、
 *   "Force regenerate"→强制重新生成、"Regenerating…"→正在重新生成…、
 *   "Regenerate page"→重新生成本页、"Retry block"→重试该块、
 *   "error"→错误、"Unknown error"→未知错误、"Insert block"→插入内容块、
 *   "This page has no blocks yet."→此页面还没有内容块。、
 *   "{{count}} block(s) failed"→{{count}} 个内容块生成失败（单复数 key 译文相同）；
 *   t("停止朗读"/"朗读本页"/"停止"/"朗读") 等 zh key 查无词条，按 key 语义直出；
 *   t(page.status) → PAGE_STATUS_LABELS（pending/planning/generating/ready/
 *   partial/error 中仅 pending=待处理、ready=就绪、error=错误 有词条，
 *   其余按语义补：规划中/生成中/部分完成）；t(blockType) → BLOCK_TYPE_LABEL
 *   （取 zh/app.json 现有 key 译文）；
 * - lucide-react → @ant-design/icons：Loader2→LoadingOutlined(spin)、
 *   RefreshCcw→RedoOutlined、Plus→PlusOutlined、ChevronDown→DownOutlined、
 *   ChevronUp→UpOutlined、Volume2→SoundOutlined、VolumeX→AudioMutedOutlined；
 *   h-3.5 w-3.5 → fontSize:14、h-4 w-4 → 16；
 * - "@/lib/book-types" → "./book-types"；"@/hooks/usePageSpeech" → "./usePageSpeech"；
 *   "./blocks/BlockRenderer" → "./BlockRenderer"；"./PageOutlineNav"/
 *   "./PageSpeechBar"/"./speech-segments" 不变；
 * - Tailwind → 最小内联样式（border→#e4e4e7、muted→#f4f4f5、muted-foreground→
 *   #6b7280、foreground→rgba(0,0,0,0.88)、primary→#1677ff、amber 横幅→#fffbeb/
 *   rgba(252,211,77,0.7)/#451a03、ring-primary/60→rgba(22,119,255,0.6)、
 *   rounded-md→6、xl→12、2xl→12、full→999、gap/space-y→N*4、text-*→12/14/26）；
 * - 简单操作按钮改用 antd Button（size="small"/type="text"/dashed），antd 默认
 *   视觉与原仓样式就近；仅 hover:*／dark:* 伪类无法内联，已省略。
 * 导出形式（default PageReader + PageReaderProps）与 props 契约一字未改。
 * ─────────────────────────────────────────────────────────────────────
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "antd";
import {
  AudioMutedOutlined,
  DownOutlined,
  LoadingOutlined,
  PlusOutlined,
  RedoOutlined,
  SoundOutlined,
  UpOutlined,
} from "@ant-design/icons";
import type { Block, BlockType, Page } from "./book-types";
import BlockRenderer from "./BlockRenderer";
import PageOutlineNav from "./PageOutlineNav";
import PageSpeechBar from "./PageSpeechBar";
import { pageToSegments } from "./speech-segments";
import { usePageSpeech } from "./usePageSpeech";

const INSERTABLE_TYPES: BlockType[] = [
  "text",
  "callout",
  "quiz",
  "code",
  "timeline",
  "flash_cards",
  "figure",
  "interactive",
  "animation",
  "deep_dive",
  "user_note",
];

// 原 t(blockType)：译文取自 zh/app.json 现有 key。
const BLOCK_TYPE_LABEL: Record<BlockType, string> = {
  text: "文本",
  section: "章节",
  callout: "提示",
  quiz: "测验",
  user_note: "用户笔记",
  figure: "图示",
  interactive: "交互",
  animation: "动画",
  code: "代码",
  timeline: "时间线",
  flash_cards: "闪卡",
  deep_dive: "深入学习",
  concept_graph: "概念图",
};

// 原 t(page.status)：pending/ready/error 取 zh/app.json 译文，
// planning/generating/partial 查无词条，按语义中文。
const PAGE_STATUS_LABEL: Record<string, string> = {
  pending: "待处理",
  planning: "规划中",
  generating: "生成中",
  ready: "就绪",
  partial: "部分完成",
  error: "错误",
};

export interface PageReaderProps {
  page: Page | null;
  onRegenerateBlock?: (block: Block) => void;
  onDeleteBlock?: (block: Block) => void;
  onMoveBlock?: (block: Block, direction: "up" | "down") => void;
  onChangeBlockType?: (block: Block, newType: BlockType) => void;
  onInsertBlock?: (block_type: BlockType) => Promise<void> | void;
  onDeepDive?: (topic: string, blockId: string) => Promise<void> | void;
  onQuizAttempt?: (
    block: Block,
    args: { questionId?: string; userAnswer?: string; isCorrect: boolean },
  ) => void;
  onRecompile?: () => void;
  pendingDeepDiveTopic?: string | null;
  loading?: boolean;
  bookId?: string;
  bookLanguage?: string;
}

export default function PageReader({
  page,
  onRegenerateBlock,
  onDeleteBlock,
  onMoveBlock,
  onChangeBlockType,
  onInsertBlock,
  onDeepDive,
  onQuizAttempt,
  onRecompile,
  pendingDeepDiveTopic,
  loading = false,
  bookId,
  bookLanguage,
}: PageReaderProps) {
  const [showInsertMenu, setShowInsertMenu] = useState(false);
  const [inserting, setInserting] = useState(false);
  const [scrollContainer, setScrollContainer] = useState<HTMLDivElement | null>(
    null,
  );

  // ── Read-aloud (speech) ────────────────────────────────────────────────
  const speechSegments = useMemo(() => pageToSegments(page), [page]);
  const speech = usePageSpeech(speechSegments);
  const [speechOpen, setSpeechOpen] = useState(false);
  const speechActive = speech.state === "speaking" || speech.state === "paused";
  // 当前朗读的 segment 对应的 block id（segment id 格式 `${blockId}:...`）。
  const currentSpeechBlockId = useMemo(() => {
    if (speech.state === "idle") return null;
    const seg = speechSegments[speech.currentIndex];
    if (!seg) return null;
    const sep = seg.id.indexOf(":");
    return sep > 0 ? seg.id.slice(0, sep) : seg.id;
  }, [speech.state, speech.currentIndex, speechSegments]);

  // 念到哪滚动到哪：当前朗读块进入视口。
  useEffect(() => {
    if (!currentSpeechBlockId || !scrollContainer) return;
    const el = document.getElementById(`block-${currentSpeechBlockId}`);
    if (!el) return;
    const containerTop = scrollContainer.getBoundingClientRect().top;
    const elTop = el.getBoundingClientRect().top;
    const delta = elTop - containerTop - 24; // 留一点上边距
    scrollContainer.scrollTo({ top: scrollContainer.scrollTop + delta, behavior: "smooth" });
  }, [currentSpeechBlockId, scrollContainer]);

  // ── Collapsible header ──────────────────────────────────────────────
  // Default expanded; collapse on user-initiated scroll-down past threshold;
  // re-expand when user returns to the very top. Manual toggle via button.
  const [headerCollapsed, setHeaderCollapsed] = useState(false);
  const [userToggled, setUserToggled] = useState(false);
  const lastScrollTopRef = useRef(0);

  // Reset header + scroll bookkeeping whenever we load a new page.
  useEffect(() => {
    setHeaderCollapsed(false);
    setUserToggled(false);
    lastScrollTopRef.current = 0;
  }, [page?.id]);

  // Stop read-aloud and close the speech bar when switching pages.
  useEffect(() => {
    speech.stop();
    setSpeechOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page?.id]);

  useEffect(() => {
    if (!scrollContainer) return;
    const handler = () => {
      const top = scrollContainer.scrollTop;
      const last = lastScrollTopRef.current;
      lastScrollTopRef.current = top;
      // Snap back to expanded when user scrolls all the way to the top,
      // even if they previously toggled manually.
      if (top <= 8) {
        setHeaderCollapsed(false);
        setUserToggled(false);
        return;
      }
      if (userToggled) return;
      // Collapse on downward scroll past a small threshold.
      if (top > last && top > 80) {
        setHeaderCollapsed(true);
      }
    };
    scrollContainer.addEventListener("scroll", handler, { passive: true });
    return () => scrollContainer.removeEventListener("scroll", handler);
  }, [scrollContainer, userToggled]);

  if (!page) {
    return (
      <div
        style={{
          display: "flex",
          height: "100%",
          alignItems: "center",
          justifyContent: "center",
          color: "#6b7280",
        }}
      >
        选择一个章节开始阅读。
      </div>
    );
  }

  const expandTip = "展开标题栏"; // t("Expand header")
  const collapseTip = "折叠标题栏"; // t("Collapse header")
  const failedBlocks = page.blocks.filter((block) => block.status === "error");
  const hasFailedBlocks = failedBlocks.length > 0;

  return (
    // The outer container is `relative` so the floating outline nav can
    // anchor to the viewport-stable column instead of being trapped inside
    // the scrollable inner div.
    <div
      style={{
        position: "relative",
        display: "flex",
        height: "100%",
        flexDirection: "column",
      }}
    >
      <header
        style={{
          borderBottom: "1px solid #e4e4e7",
          background: "rgba(255,255,255,0.6)",
          backdropFilter: "blur(8px)",
          transition: "all 200ms ease-out",
          padding: headerCollapsed ? "8px 32px" : "20px 32px",
        }}
      >
        <div
          style={{
            maxWidth: "78ch",
            marginLeft: "auto",
            marginRight: "auto",
            display: "flex",
            width: "100%",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div style={{ minWidth: 0, flex: 1 }}>
            <h1
              data-testid="book-reader-title"
              title={page.title || "未命名章节"}
              style={{
                margin: 0,
                fontWeight: 600,
                lineHeight: 1.25,
                letterSpacing: "-0.025em",
                color: "rgba(0,0,0,0.88)",
                transition: "all 200ms",
                fontSize: headerCollapsed ? 15 : 26,
                ...(headerCollapsed
                  ? {
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }
                  : {}),
              }}
            >
              {page.title || "未命名章节"}
            </h1>
            {!headerCollapsed && page.learning_objectives.length > 0 && (
              <ul
                style={{
                  margin: "12px 0 0",
                  padding: 0,
                  listStyle: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  fontSize: "12.5px",
                  color: "#6b7280",
                }}
              >
                {page.learning_objectives.map((obj, idx) => (
                  <li key={idx}>• {obj}</li>
                ))}
              </ul>
            )}
          </div>
          <div
            style={{
              display: "flex",
              flexShrink: 0,
              alignItems: "center",
              gap: 8,
            }}
          >
            {!headerCollapsed && (
              <span
                style={{
                  borderRadius: 999,
                  background: "#f4f4f5",
                  padding: "2px 10px",
                  fontSize: 11,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  color: "#6b7280",
                }}
              >
                {PAGE_STATUS_LABEL[page.status] || page.status}
              </span>
            )}
            {speech.supported && speechSegments.length > 0 && (
              <Button
                size="small"
                onClick={() => {
                  if (speechActive) {
                    speech.stop();
                    setSpeechOpen(false);
                  } else {
                    setSpeechOpen(true);
                    if (speech.state === "idle") speech.toggle();
                  }
                }}
                title={
                  speechActive
                    ? "停止朗读"
                    : "朗读本页"
                }
                icon={
                  speechActive ? (
                    <AudioMutedOutlined style={{ fontSize: 14 }} />
                  ) : (
                    <SoundOutlined style={{ fontSize: 14 }} />
                  )
                }
                style={{
                  fontSize: 12,
                  fontWeight: 500,
                  borderRadius: 6,
                  ...(speechActive
                    ? {
                        borderColor: "rgba(22,119,255,0.5)",
                        background: "rgba(22,119,255,0.1)",
                        color: "#1677ff",
                      }
                    : {
                        color: "#6b7280",
                      }),
                }}
              >
                {speechActive ? "停止" : "朗读"}
              </Button>
            )}
            {!headerCollapsed && onRecompile && (
              <Button
                size="small"
                onClick={onRecompile}
                disabled={loading}
                icon={
                  loading ? (
                    <LoadingOutlined spin style={{ fontSize: 14 }} />
                  ) : (
                    <RedoOutlined style={{ fontSize: 14 }} />
                  )
                }
                style={{ fontSize: 12, fontWeight: 500, borderRadius: 6, color: "#6b7280" }}
              >
                {loading ? "正在重新生成…" : "强制重新生成"}
              </Button>
            )}
            <Button
              type="text"
              size="small"
              onClick={() => {
                setHeaderCollapsed((v) => !v);
                setUserToggled(true);
              }}
              title={headerCollapsed ? expandTip : collapseTip}
              aria-label={headerCollapsed ? expandTip : collapseTip}
              icon={
                headerCollapsed ? (
                  <DownOutlined style={{ fontSize: 14 }} />
                ) : (
                  <UpOutlined style={{ fontSize: 14 }} />
                )
              }
              style={{
                width: 24,
                height: 24,
                minWidth: 24,
                padding: 0,
                borderRadius: 6,
                color: "#6b7280",
              }}
            />
          </div>
        </div>
      </header>

      <div
        ref={setScrollContainer}
        style={{ flex: 1, overflowY: "auto", padding: 32 }}
      >
        {loading && page.blocks.length === 0 ? (
          <div
            style={{
              maxWidth: "78ch",
              marginLeft: "auto",
              marginRight: "auto",
              display: "flex",
              width: "100%",
              alignItems: "center",
              gap: 8,
              fontSize: 14,
              color: "#6b7280",
            }}
          >
            <LoadingOutlined spin style={{ fontSize: 16 }} />
            正在编译页面…
          </div>
        ) : (
          <article
            style={{
              maxWidth: "78ch",
              marginLeft: "auto",
              marginRight: "auto",
              display: "flex",
              width: "100%",
              flexDirection: "column",
              gap: 24,
            }}
          >
            {hasFailedBlocks && (
              <div
                style={{
                  borderRadius: 12,
                  border: "1px solid rgba(252,211,77,0.7)",
                  background: "#fffbeb",
                  padding: "12px 16px",
                  fontSize: 14,
                  color: "#451a03",
                }}
              >
                <div
                  style={{
                    marginBottom: 8,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                  }}
                >
                  <div style={{ fontWeight: 600 }}>
                    {/* 原仓按单/复数取 t("{{count}} block failed" / "{{count}} blocks failed")，
                        两者 zh 译文相同：{{count}} 个内容块生成失败 */}
                    {failedBlocks.length} 个内容块生成失败
                  </div>
                  {onRecompile && (
                    <Button
                      size="small"
                      onClick={onRecompile}
                      disabled={loading}
                      icon={
                        loading ? (
                          <LoadingOutlined spin style={{ fontSize: 14 }} />
                        ) : (
                          <RedoOutlined style={{ fontSize: 14 }} />
                        )
                      }
                      style={{
                        fontSize: 12,
                        fontWeight: 500,
                        borderRadius: 6,
                        borderColor: "currentColor",
                        color: "inherit",
                        background: "transparent",
                        boxShadow: "none",
                      }}
                    >
                      {loading ? "正在重新生成…" : "重新生成本页"}
                    </Button>
                  )}
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                    fontSize: 12,
                    opacity: 0.9,
                  }}
                >
                  {failedBlocks.slice(0, 5).map((block) => {
                    const failure = block.metadata?.failure as
                      | { kind?: string; message?: string }
                      | undefined;
                    return (
                      <div
                        key={block.id}
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        <code
                          style={{
                            borderRadius: 4,
                            background: "rgba(255,255,255,0.5)",
                            padding: "2px 6px",
                          }}
                        >
                          {block.type}
                        </code>
                        <span>
                          {failure?.kind || "错误"}:{" "}
                          {block.error ||
                            failure?.message ||
                            "未知错误"}
                        </span>
                        {onRegenerateBlock && (
                          <button
                            onClick={() => onRegenerateBlock(block)}
                            style={{
                              borderRadius: 4,
                              border: "1px solid currentColor",
                              padding: "2px 6px",
                              fontSize: 11,
                              fontWeight: 500,
                              color: "inherit",
                              background: "transparent",
                              cursor: "pointer",
                            }}
                          >
                            重试该块
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {page.blocks.map((block) => (
              <div
                key={block.id}
                id={`block-${block.id}`}
                data-testid="book-block"
                style={{
                  scrollMarginTop: 24,
                  borderRadius: 12,
                  transition: "box-shadow 150ms",
                  boxShadow:
                    currentSpeechBlockId === block.id
                      ? "0 0 0 2px rgba(22,119,255,0.6), 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)"
                      : "none",
                }}
              >
                <BlockRenderer
                  block={block}
                  onRegenerate={onRegenerateBlock}
                  onDelete={onDeleteBlock}
                  onMove={onMoveBlock}
                  onChangeType={onChangeBlockType}
                  onDeepDive={onDeepDive}
                  onQuizAttempt={onQuizAttempt}
                  pendingDeepDiveTopic={pendingDeepDiveTopic}
                  bookId={bookId}
                  currentPageId={page.id}
                  bookLanguage={bookLanguage}
                />
              </div>
            ))}
            {page.blocks.length === 0 && (
              <div style={{ fontSize: 14, color: "#6b7280" }}>
                此页面还没有内容块。
              </div>
            )}

            {onInsertBlock && (
              <div
                style={{
                  position: "relative",
                  marginTop: 8,
                  display: "flex",
                  justifyContent: "center",
                }}
              >
                <Button
                  size="small"
                  onClick={() => setShowInsertMenu((v) => !v)}
                  disabled={inserting}
                  icon={
                    inserting ? (
                      <LoadingOutlined spin style={{ fontSize: 14 }} />
                    ) : (
                      <PlusOutlined style={{ fontSize: 14 }} />
                    )
                  }
                  style={{
                    fontSize: 12,
                    fontWeight: 500,
                    borderRadius: 999,
                    padding: "2px 12px",
                    color: "#6b7280",
                    borderStyle: "dashed",
                  }}
                >
                  插入内容块
                </Button>
                {showInsertMenu && (
                  <div
                    style={{
                      position: "absolute",
                      top: "100%",
                      marginTop: 4,
                      zIndex: 10,
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 4,
                      width: 288,
                      borderRadius: 8,
                      border: "1px solid #e4e4e7",
                      background: "#fff",
                      padding: 8,
                      boxShadow:
                        "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
                    }}
                  >
                    {INSERTABLE_TYPES.map((blockType) => (
                      <button
                        key={blockType}
                        onClick={async () => {
                          setShowInsertMenu(false);
                          setInserting(true);
                          try {
                            await onInsertBlock(blockType);
                          } finally {
                            setInserting(false);
                          }
                        }}
                        style={{
                          borderRadius: 4,
                          padding: "4px 8px",
                          textAlign: "left",
                          fontSize: 12,
                          color: "rgba(0,0,0,0.88)",
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                        }}
                      >
                        {BLOCK_TYPE_LABEL[blockType] || blockType}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </article>
        )}
      </div>

      {/* Floating outline lives outside the scroll container so it stays
          pinned to the viewport regardless of page scrolling. */}
      <PageOutlineNav
        key={page.id}
        blocks={page.blocks}
        scrollContainer={scrollContainer}
        language={bookLanguage}
      />

      {/* Floating read-aloud control window (bottom-right). */}
      {speechOpen && (
        <div
          style={{
            position: "fixed",
            bottom: 20,
            right: 20,
            zIndex: 50,
            width: "min(26rem, calc(100vw - 2.5rem))",
          }}
        >
          <PageSpeechBar speech={speech} onClose={() => { speech.stop(); setSpeechOpen(false); }} />
        </div>
      )}
    </div>
  );
}
