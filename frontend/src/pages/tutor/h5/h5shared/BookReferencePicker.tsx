/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/BookReferencePicker.tsx，441 行）。
 * 替换点：删除 "use client"；lucide BookOpen/Check/ChevronRight/Layers3/Loader2/
 * Search→BookOutlined/CheckOutlined/RightOutlined/AppstoreOutlined(图层近似)/
 * LoadingOutlined(spin)/SearchOutlined；PickerShell/PickerHeader→本目录件；
 * book-api→../../admin/book-api（批8 件，bookApi.list/get 契约一致）、book-types→
 * ../../admin/book-types、book-references→../../admin/book-references（批8 件）；
 * Tailwind→内联样式（grid-cols-[300px_minmax(0,1fr)]→gridTemplateColumns）；
 * t() 译文命中 zh/app.json 直出（"Select Book Chapters"→选择书籍章节、
 * "Choose generated book chapters to ground the next answer."→选择已生成的书籍章节，
 * 作为下一次回答的依据。、"Search books"→搜索书籍、"Untitled book"→未命名书籍、
 * "Untitled chapter"→未命名章节、"Unassigned pages"→未分配页面、"chapters"→章、
 * "pages"→页、"No books found."→未找到书籍。、"Select a book to view chapters."→
 * 选择一本书查看章节。、"No chapters selected"→尚未选择章节、"Clear"→清空、
 * "Apply"→应用），"{{count}} chapters selected" 未命中按 i18next 回退直出。
 * 章节/页面多选、按 spine 分组、孤页归组逐字未改。
 */
import { useEffect, useMemo, useState } from "react";
import {
  BookOutlined,
  CheckOutlined,
  RightOutlined,
  AppstoreOutlined,
  LoadingOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import PickerShell from "./PickerShell";
import PickerHeader from "./PickerHeader";
import { bookApi } from "../../admin/book-api";
import type { Book, BookDetail, Chapter, Page } from "../../admin/book-types";
import type {
  SelectedBookPage,
  SelectedBookReference,
} from "../../admin/book-references";
import { DT, ellipsis } from "./dtStyle";

interface BookReferencePickerProps {
  open: boolean;
  initialReferences: SelectedBookReference[];
  onClose: () => void;
  onApply: (references: SelectedBookReference[]) => void;
}

function pageKey(bookId: string, pageId: string): string {
  return `${bookId}:${pageId}`;
}

function groupPages(detail: BookDetail | null): Array<{
  chapter: Chapter | null;
  pages: Page[];
}> {
  if (!detail) return [];
  const byId = new Map(detail.pages.map((page) => [page.id, page]));
  const used = new Set<string>();
  const groups: Array<{ chapter: Chapter | null; pages: Page[] }> = (
    detail.spine?.chapters || []
  ).map((chapter) => {
    const pages = chapter.page_ids
      .map((pageId) => byId.get(pageId))
      .filter((page): page is Page => Boolean(page));
    pages.forEach((page) => used.add(page.id));
    return { chapter, pages };
  });
  const orphanPages = detail.pages.filter((page) => !used.has(page.id));
  if (orphanPages.length) groups.push({ chapter: null, pages: orphanPages });
  return groups.filter((group) => group.pages.length > 0);
}

export default function BookReferencePicker({
  open,
  initialReferences,
  onClose,
  onApply,
}: BookReferencePickerProps) {
  const [books, setBooks] = useState<Book[]>([]);
  const [details, setDetails] = useState<Record<string, BookDetail>>({});
  const [activeBookId, setActiveBookId] = useState<string | null>(null);
  const [selected, setSelected] = useState<SelectedBookReference[]>([]);
  const [query, setQuery] = useState("");
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    if (!open) return;
    let mounted = true;
    // Re-seed selection each time the picker opens.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected(initialReferences);
    setLoadingBooks(true);
    void bookApi
      .list()
      .then((data) => {
        if (!mounted) return;
        setBooks(data.books || []);
        setActiveBookId((current) => current || data.books?.[0]?.id || null);
      })
      .catch(() => {
        if (mounted) setBooks([]);
      })
      .finally(() => {
        if (mounted) setLoadingBooks(false);
      });
    return () => {
      mounted = false;
    };
  }, [initialReferences, open]);

  useEffect(() => {
    if (!open || !activeBookId || details[activeBookId]) return;
    let mounted = true;
    // Show detail loading before the async book lookup resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingDetail(true);
    void bookApi
      .get(activeBookId)
      .then((detail) => {
        if (!mounted) return;
        setDetails((prev) => ({ ...prev, [activeBookId]: detail }));
      })
      .catch(() => undefined)
      .finally(() => {
        if (mounted) setLoadingDetail(false);
      });
    return () => {
      mounted = false;
    };
  }, [activeBookId, details, open]);

  const filteredBooks = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return books;
    return books.filter((book) =>
      `${book.title} ${book.description}`.toLowerCase().includes(keyword),
    );
  }, [books, query]);

  const activeBook = books.find((book) => book.id === activeBookId) || null;
  const activeDetail = activeBookId ? details[activeBookId] || null : null;
  const pageGroups = useMemo(() => groupPages(activeDetail), [activeDetail]);
  const selectedKeys = useMemo(() => {
    const keys = new Set<string>();
    selected.forEach((book) =>
      book.pages.forEach((page) => keys.add(pageKey(book.bookId, page.pageId))),
    );
    return keys;
  }, [selected]);

  const togglePage = (book: Book, page: Page, chapter: Chapter | null) => {
    const nextPage: SelectedBookPage = {
      bookId: book.id,
      bookTitle: book.title || "未命名书籍",
      pageId: page.id,
      pageTitle: page.title || "未命名章节",
      chapterId: chapter?.id || page.chapter_id,
      chapterTitle: chapter?.title || page.title || "未命名章节",
    };
    setSelected((prev) => {
      const existing = prev.find((ref) => ref.bookId === book.id);
      const selectedAlready = existing?.pages.some((p) => p.pageId === page.id);
      if (selectedAlready) {
        return prev
          .map((ref) =>
            ref.bookId === book.id
              ? { ...ref, pages: ref.pages.filter((p) => p.pageId !== page.id) }
              : ref,
          )
          .filter((ref) => ref.pages.length > 0);
      }
      if (existing) {
        return prev.map((ref) =>
          ref.bookId === book.id
            ? { ...ref, pages: [...ref.pages, nextPage] }
            : ref,
        );
      }
      return [
        ...prev,
        {
          bookId: book.id,
          bookTitle: book.title || "未命名书籍",
          pages: [nextPage],
        },
      ];
    });
  };

  const toggleChapter = (
    book: Book,
    chapter: Chapter | null,
    pages: Page[],
  ) => {
    const allSelected = pages.every((page) =>
      selectedKeys.has(pageKey(book.id, page.id)),
    );
    setSelected((prev) => {
      const existing = prev.find((ref) => ref.bookId === book.id);
      const existingPages = existing?.pages || [];
      const pageIds = new Set(pages.map((page) => page.id));
      const remaining = allSelected
        ? existingPages.filter((page) => !pageIds.has(page.pageId))
        : [
            ...existingPages,
            ...pages
              .filter(
                (page) => !existingPages.some((p) => p.pageId === page.id),
              )
              .map((page) => ({
                bookId: book.id,
                bookTitle: book.title || "未命名书籍",
                pageId: page.id,
                pageTitle: page.title || "未命名章节",
                chapterId: chapter?.id || page.chapter_id,
                chapterTitle:
                  chapter?.title || page.title || "未命名章节",
              })),
          ];
      const nextRef = {
        bookId: book.id,
        bookTitle: book.title || "未命名书籍",
        pages: remaining,
      };
      const others = prev.filter((ref) => ref.bookId !== book.id);
      return nextRef.pages.length ? [...others, nextRef] : others;
    });
  };

  const selectedCount = selected.reduce(
    (total, ref) => total + ref.pages.length,
    0,
  );

  return (
    <PickerShell
      open={open}
      onClose={onClose}
      labelledBy="book-picker-title"
      backdropClass="rgba(255,255,255,0.65)"
    >
      <div
        style={{
          display: "flex",
          height: "78vh",
          width: "100%",
          maxWidth: 1024,
          flexDirection: "column",
          overflow: "hidden",
          borderRadius: 16,
          border: `1px solid ${DT.border}`,
          background: DT.card,
          color: DT.foreground,
          boxShadow: "0 22px 70px rgba(0,0,0,0.18)",
        }}
      >
        <PickerHeader
          icon={BookOutlined}
          titleId="book-picker-title"
          title={"选择书籍章节"}
          subtitle={"选择已生成的书籍章节，作为下一次回答的依据。"}
          onClose={onClose}
        />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "300px minmax(0, 1fr)",
            minHeight: 0,
            flex: 1,
          }}
        >
          <aside
            style={{
              display: "flex",
              minHeight: 0,
              flexDirection: "column",
              borderRight: `1px solid ${DT.border}`,
              background: "rgba(255,255,255,0.4)",
              padding: 16,
            }}
          >
            <div style={{ position: "relative", marginBottom: 12 }}>
              <SearchOutlined
                style={{
                  pointerEvents: "none",
                  position: "absolute",
                  left: 12,
                  top: "50%",
                  fontSize: 14,
                  transform: "translateY(-50%)",
                  color: DT.mutedForeground,
                }}
              />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={"搜索书籍"}
                style={{
                  width: "100%",
                  borderRadius: 12,
                  border: `1px solid ${DT.border}`,
                  background: DT.card,
                  padding: "10px 12px 10px 36px",
                  fontSize: 13,
                  color: DT.foreground,
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>
            <div
              style={{
                minHeight: 0,
                flex: 1,
                overflowY: "auto",
                borderRadius: 16,
                border: `1px solid ${DT.border}`,
                background: DT.card,
              }}
            >
              {loadingBooks ? (
                <div style={{ display: "flex", height: "100%", minHeight: 220, alignItems: "center", justifyContent: "center" }}>
                  <LoadingOutlined spin style={{ fontSize: 20, color: DT.mutedForeground }} />
                </div>
              ) : filteredBooks.length ? (
                <div>
                  {filteredBooks.map((book, idx) => {
                    const active = book.id === activeBookId;
                    const selectedPages =
                      selected.find((ref) => ref.bookId === book.id)?.pages
                        .length || 0;
                    return (
                      <button
                        key={book.id}
                        onClick={() => setActiveBookId(book.id)}
                        onMouseEnter={(e) => {
                          if (!active) {
                            e.currentTarget.style.background = DT.mutedAlpha(0.4);
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = active
                            ? DT.primaryAlpha(0.08)
                            : "transparent";
                        }}
                        style={{
                          display: "flex",
                          width: "100%",
                          alignItems: "center",
                          gap: 12,
                          padding: "12px 12px",
                          textAlign: "left",
                          border: "none",
                          cursor: "pointer",
                          background: active ? DT.primaryAlpha(0.08) : "transparent",
                          font: "inherit",
                          borderTop: idx > 0 ? `1px solid ${DT.border}` : undefined,
                        }}
                      >
                        <BookOutlined
                          style={{ fontSize: 16, flexShrink: 0, color: DT.mutedForeground }}
                        />
                        <span style={{ minWidth: 0, flex: 1 }}>
                          <span style={{ display: "block", ...ellipsis, fontSize: 13, fontWeight: 500, color: DT.foreground }}>
                            {book.title || "未命名书籍"}
                          </span>
                          <span style={{ display: "block", marginTop: 2, fontSize: 11, color: DT.mutedForeground }}>
                            {book.page_count || 0} 章
                          </span>
                        </span>
                        {selectedPages > 0 && (
                          <span
                            style={{
                              borderRadius: 999,
                              background: DT.primaryAlpha(0.1),
                              padding: "1px 6px",
                              fontSize: 9,
                              fontWeight: 600,
                              color: DT.primary,
                            }}
                          >
                            {selectedPages}
                          </span>
                        )}
                        <RightOutlined style={{ fontSize: 14, color: DT.mutedForeground }} />
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div style={{ padding: "48px 20px", textAlign: "center", fontSize: 13, color: DT.mutedForeground }}>
                  未找到书籍。
                </div>
              )}
            </div>
          </aside>

          <section style={{ minHeight: 0, overflowY: "auto", padding: 20 }}>
            {!activeBook ? (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, color: DT.mutedForeground }}>
                选择一本书查看章节。
              </div>
            ) : loadingDetail && !activeDetail ? (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <LoadingOutlined spin style={{ fontSize: 20, color: DT.mutedForeground }} />
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", rowGap: 16 }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: DT.foreground }}>
                    {activeBook.title || "未命名书籍"}
                  </h3>
                  {activeBook.description && (
                    <p
                      style={{
                        margin: "4px 0 0",
                        fontSize: 14,
                        color: DT.mutedForeground,
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}
                    >
                      {activeBook.description}
                    </p>
                  )}
                </div>
                {pageGroups.map(({ chapter, pages }) => {
                  const allSelected = pages.every((page) =>
                    selectedKeys.has(pageKey(activeBook.id, page.id)),
                  );
                  const showPageRows = pages.length > 1;
                  const firstPage = pages[0];
                  return (
                    <div
                      key={chapter?.id || pages[0]?.id}
                      style={{
                        overflow: "hidden",
                        borderRadius: 16,
                        border: `1px solid ${DT.border}`,
                        background: "rgba(255,255,255,0.35)",
                      }}
                    >
                      <button
                        onClick={() =>
                          toggleChapter(activeBook, chapter, pages)
                        }
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = DT.mutedAlpha(0.35);
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                        }}
                        style={{
                          display: "flex",
                          width: "100%",
                          alignItems: "flex-start",
                          gap: 12,
                          padding: "12px 16px",
                          textAlign: "left",
                          border: "none",
                          cursor: "pointer",
                          background: "transparent",
                          borderBottom: showPageRows
                            ? `1px solid ${DT.border}`
                            : undefined,
                          font: "inherit",
                          transition: "background-color 150ms",
                        }}
                      >
                        <span
                          style={{
                            marginTop: 2,
                            display: "flex",
                            height: 20,
                            width: 20,
                            flexShrink: 0,
                            alignItems: "center",
                            justifyContent: "center",
                            borderRadius: 6,
                            border: `1px solid ${allSelected ? DT.primary : DT.border}`,
                            background: allSelected ? DT.primary : "transparent",
                            color: allSelected ? DT.primaryForeground : "transparent",
                            transition: "background-color 150ms, border-color 150ms",
                          }}
                        >
                          <CheckOutlined style={{ fontSize: 12 }} />
                        </span>
                        <AppstoreOutlined
                          style={{ marginTop: 2, fontSize: 16, flexShrink: 0, color: DT.mutedForeground }}
                        />
                        <span style={{ minWidth: 0, flex: 1 }}>
                          <span style={{ display: "block", ...ellipsis, fontSize: 13, fontWeight: 500, color: DT.foreground }}>
                            {chapter?.title ||
                              firstPage?.title ||
                              "未分配页面"}
                          </span>
                          <span style={{ fontSize: 11, color: DT.mutedForeground }}>
                            {pages.length} 页
                          </span>
                          {!showPageRows &&
                          firstPage?.learning_objectives?.length ? (
                            <span
                              style={{
                                marginTop: 4,
                                display: "-webkit-box",
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: "vertical",
                                overflow: "hidden",
                                fontSize: 12,
                                lineHeight: "20px",
                                color: DT.mutedForeground,
                              }}
                            >
                              {firstPage.learning_objectives.join("; ")}
                            </span>
                          ) : null}
                        </span>
                      </button>
                      {showPageRows && (
                        <div>
                          {pages.map((page, pageIdx) => {
                            const checked = selectedKeys.has(
                              pageKey(activeBook.id, page.id),
                            );
                            return (
                              <button
                                key={page.id}
                                onClick={() =>
                                  togglePage(activeBook, page, chapter)
                                }
                                onMouseEnter={(e) => {
                                  if (!checked) {
                                    e.currentTarget.style.background = DT.mutedAlpha(0.3);
                                  }
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.background = checked
                                    ? DT.primaryAlpha(0.08)
                                    : "transparent";
                                }}
                                style={{
                                  display: "flex",
                                  width: "100%",
                                  alignItems: "flex-start",
                                  gap: 12,
                                  padding: "12px 20px",
                                  textAlign: "left",
                                  border: "none",
                                  cursor: "pointer",
                                  background: checked
                                    ? DT.primaryAlpha(0.08)
                                    : "transparent",
                                  font: "inherit",
                                  borderTop:
                                    pageIdx > 0 ? `1px solid ${DT.border}` : undefined,
                                }}
                              >
                                <span
                                  style={{
                                    marginTop: 2,
                                    display: "flex",
                                    height: 20,
                                    width: 20,
                                    flexShrink: 0,
                                    alignItems: "center",
                                    justifyContent: "center",
                                    borderRadius: 6,
                                    border: `1px solid ${checked ? DT.primary : DT.border}`,
                                    background: checked ? DT.primary : "transparent",
                                    color: checked ? DT.primaryForeground : "transparent",
                                    transition: "background-color 150ms, border-color 150ms",
                                  }}
                                >
                                  <CheckOutlined style={{ fontSize: 12 }} />
                                </span>
                                <span style={{ minWidth: 0, flex: 1 }}>
                                  <span style={{ display: "block", fontSize: 13, fontWeight: 500, color: DT.foreground }}>
                                    {page.title || "未命名章节"}
                                  </span>
                                  {page.learning_objectives?.length ? (
                                    <span
                                      style={{
                                        marginTop: 4,
                                        display: "-webkit-box",
                                        WebkitLineClamp: 2,
                                        WebkitBoxOrient: "vertical",
                                        overflow: "hidden",
                                        fontSize: 12,
                                        lineHeight: "20px",
                                        color: DT.mutedForeground,
                                      }}
                                    >
                                      {page.learning_objectives.join("; ")}
                                    </span>
                                  ) : null}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, borderTop: `1px solid ${DT.border}`, padding: "16px 20px" }}>
          <div style={{ fontSize: 14, color: DT.mutedForeground }}>
            {selectedCount
              ? `${selectedCount} chapters selected`
              : "尚未选择章节"}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              onClick={() => setSelected([])}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = DT.muted;
                e.currentTarget.style.color = DT.foreground;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = DT.mutedForeground;
              }}
              style={{
                borderRadius: 12,
                border: `1px solid ${DT.border}`,
                background: "transparent",
                padding: "8px 16px",
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
                color: DT.mutedForeground,
                transition: "background-color 150ms, color 150ms",
                font: "inherit",
              }}
            >
              清空
            </button>
            <button
              onClick={() => {
                onApply(selected);
                onClose();
              }}
              style={{
                borderRadius: 12,
                border: "none",
                cursor: "pointer",
                background: DT.primary,
                padding: "8px 16px",
                fontSize: 14,
                fontWeight: 500,
                color: DT.primaryForeground,
                transition: "opacity 150ms",
                font: "inherit",
              }}
            >
              应用
            </button>
          </div>
        </div>
      </div>
    </PickerShell>
  );
}

// 具名再导出：批9 SA-A FollowupChatComposer 以 lazy(() => import(...).then((m) => ({ default: m.BookReferencePicker }))) 消费（桌面原件仅 default 导出，此为批内契约对齐，非新逻辑）。
export { BookReferencePicker };
