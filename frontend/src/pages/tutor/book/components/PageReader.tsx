"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Loader2,
  RefreshCcw,
  Plus,
  ChevronDown,
  ChevronUp,
  Volume2,
  VolumeX,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Block, BlockType, Page } from "../../../../lib/book-types";
import BlockRenderer from "./blocks/BlockRenderer";
import PageOutlineNav from "./PageOutlineNav";
import PageSpeechBar from "./PageSpeechBar";
import { pageToSegments } from "./speech-segments";
import { usePageSpeech } from "../../../../hooks/usePageSpeech";

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
  const { t } = useTranslation();
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
      <div className="flex h-full items-center justify-center text-[var(--muted-foreground)]">
        {t("Select a chapter to start reading.")}
      </div>
    );
  }

  const expandTip = t("Expand header");
  const collapseTip = t("Collapse header");
  const failedBlocks = page.blocks.filter((block) => block.status === "error");
  const hasFailedBlocks = failedBlocks.length > 0;

  return (
    // The outer container is `relative` so the floating outline nav can
    // anchor to the viewport-stable column instead of being trapped inside
    // the scrollable inner div.
    <div className="relative flex h-full flex-col">
      <header
        className={[
          "border-b border-[var(--border)] bg-[var(--card)]/60 backdrop-blur transition-all duration-200 ease-out",
          headerCollapsed ? "px-8 py-2" : "px-8 py-5",
        ].join(" ")}
      >
        <div className="mx-auto flex w-full max-w-[78ch] items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h1
              data-testid="book-reader-title"
              className={[
                "font-semibold leading-tight tracking-tight text-[var(--foreground)] transition-all duration-200",
                headerCollapsed ? "truncate text-[15px]" : "text-[26px]",
              ].join(" ")}
              title={page.title || t("Untitled chapter")}
            >
              {page.title || t("Untitled chapter")}
            </h1>
            {!headerCollapsed && page.learning_objectives.length > 0 && (
              <ul className="mt-3 space-y-0.5 text-[12.5px] text-[var(--muted-foreground)]">
                {page.learning_objectives.map((obj, idx) => (
                  <li key={idx}>• {obj}</li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {!headerCollapsed && (
              <span className="rounded-full bg-[var(--muted)] px-2.5 py-0.5 text-[11px] uppercase tracking-wider text-[var(--muted-foreground)]">
                {t(page.status)}
              </span>
            )}
            {speech.supported && speechSegments.length > 0 && (
              <button
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
                    ? t("停止朗读", "Stop reading aloud")
                    : t("朗读本页", "Read this page aloud")
                }
                className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium ${
                  speechActive
                    ? "border-[var(--primary)]/50 bg-[var(--primary)]/10 text-[var(--primary)]"
                    : "border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:border-[var(--primary)]/40 hover:text-[var(--primary)]"
                }`}
              >
                {speechActive ? (
                  <VolumeX className="h-3.5 w-3.5" />
                ) : (
                  <Volume2 className="h-3.5 w-3.5" />
                )}
                {speechActive
                  ? t("停止", "Stop")
                  : t("朗读", "Read aloud")}
              </button>
            )}
            {!headerCollapsed && onRecompile && (
              <button
                onClick={onRecompile}
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--card)] px-2.5 py-1 text-xs font-medium text-[var(--muted-foreground)] hover:border-[var(--primary)]/40 hover:text-[var(--primary)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCcw className="h-3.5 w-3.5" />
                )}
                {loading ? t("Regenerating…") : t("Force regenerate")}
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                setHeaderCollapsed((v) => !v);
                setUserToggled(true);
              }}
              title={headerCollapsed ? expandTip : collapseTip}
              aria-label={headerCollapsed ? expandTip : collapseTip}
              className="inline-flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted-foreground)] hover:bg-[var(--background)] hover:text-[var(--foreground)]"
            >
              {headerCollapsed ? (
                <ChevronDown className="h-3.5 w-3.5" />
              ) : (
                <ChevronUp className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
        </div>
      </header>

      <div
        ref={setScrollContainer}
        className="flex-1 overflow-y-auto px-8 py-8"
      >
        {loading && page.blocks.length === 0 ? (
          <div className="mx-auto flex w-full max-w-[78ch] items-center gap-2 text-sm text-[var(--muted-foreground)]">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t("Compiling page…")}
          </div>
        ) : (
          <article className="mx-auto flex w-full max-w-[78ch] flex-col gap-6 [&>:first-child]:mt-0">
            {hasFailedBlocks && (
              <div className="rounded-2xl border border-amber-300/70 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <div className="font-semibold">
                    {failedBlocks.length === 1
                      ? t("{{count}} block failed", {
                          count: failedBlocks.length,
                        })
                      : t("{{count}} blocks failed", {
                          count: failedBlocks.length,
                        })}
                  </div>
                  {onRecompile && (
                    <button
                      onClick={onRecompile}
                      disabled={loading}
                      className="inline-flex items-center gap-1 rounded-md border border-current px-2 py-1 text-xs font-medium hover:bg-white/40 dark:hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {loading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <RefreshCcw className="h-3.5 w-3.5" />
                      )}
                      {loading ? t("Regenerating…") : t("Regenerate page")}
                    </button>
                  )}
                </div>
                <div className="space-y-1.5 text-xs opacity-90">
                  {failedBlocks.slice(0, 5).map((block) => {
                    const failure = block.metadata?.failure as
                      | { kind?: string; message?: string }
                      | undefined;
                    return (
                      <div
                        key={block.id}
                        className="flex flex-wrap items-center gap-2"
                      >
                        <code className="rounded bg-white/50 px-1.5 py-0.5 dark:bg-white/10">
                          {block.type}
                        </code>
                        <span>
                          {failure?.kind || t("error")}:{" "}
                          {block.error ||
                            failure?.message ||
                            t("Unknown error")}
                        </span>
                        {onRegenerateBlock && (
                          <button
                            onClick={() => onRegenerateBlock(block)}
                            className="rounded border border-current px-1.5 py-0.5 text-[11px] font-medium hover:bg-white/40 dark:hover:bg-white/10"
                          >
                            {t("Retry block")}
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
                className={`scroll-mt-6 rounded-xl transition-shadow ${
                  currentSpeechBlockId === block.id
                    ? "ring-2 ring-[var(--primary)]/60 shadow-md"
                    : ""
                }`}
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
              <div className="text-sm text-[var(--muted-foreground)]">
                {t("This page has no blocks yet.")}
              </div>
            )}

            {onInsertBlock && (
              <div className="relative mt-2 flex justify-center">
                <button
                  onClick={() => setShowInsertMenu((v) => !v)}
                  disabled={inserting}
                  className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs font-medium text-[var(--muted-foreground)] hover:border-[var(--primary)]/50 hover:text-[var(--primary)] disabled:opacity-60"
                >
                  {inserting ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Plus className="h-3.5 w-3.5" />
                  )}
                  {t("Insert block")}
                </button>
                {showInsertMenu && (
                  <div className="absolute top-full mt-1 z-10 grid w-72 grid-cols-2 gap-1 rounded-lg border border-[var(--border)] bg-[var(--card)] p-2 shadow-lg">
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
                        className="rounded px-2 py-1 text-left text-xs text-[var(--foreground)] hover:bg-[var(--background)]"
                      >
                        {t(blockType)}
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
        <div className="fixed bottom-5 right-5 z-50 w-[min(26rem,calc(100vw-2.5rem))]">
          <PageSpeechBar speech={speech} onClose={() => { speech.stop(); setSpeechOpen(false); }} />
        </div>
      )}
    </div>
  );
}
