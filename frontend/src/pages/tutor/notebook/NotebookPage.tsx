/**
 * NotebookPage 笔记本页（题库）——原仓 app/(utility)/notebook/page.tsx 1:1 移植。
 *
 * ⑤R R3 补建（F2 9.1「笔记本」复查发现仅有 picker 组件链、页面本体缺位——
 * spec 2.6 #7 规划 /e/sishu/notebook）。数据源 question-notebook API（后端
 * question_notebook.router 已挂载，活探 200）。
 *
 * 等价替换清单（同 H5Me/批8 规则）：
 * - "use client"/next/dynamic 删除；next/link → react-router-dom Link；
 * - lucide → @ant-design/icons：AlertTriangle→WarningOutlined、Bookmark→BookOutlined、
 *   ChevronDown→DownOutlined、ExternalLink→ExportOutlined、FolderOpen→FolderOpenOutlined、
 *   Loader2→LoadingOutlined、MessageSquare→MessageOutlined、NotebookPen→FormOutlined、
 *   Pencil→EditOutlined、Plus→PlusOutlined、Trash2→DeleteOutlined、X→CloseOutlined；
 * - useTranslation t(键) → locales/zh/app.json 中文值逐字直用（原渲染即中文）；
 * - fetch(apiUrl(x)) → fetch(x)（notebook-api.ts 同源替换已完成）；
 * - Tailwind → 内联样式逐项对位（CSS 变量带 fallback，同 MemoryWorkbench 先例）；
 *   hover:/dark: 变体随共享层先例省略；
 * - 原会话深链 `/?session=X` → `/e/sishu/chat?session=X`（tupu ExpertChat 消费同名参数，
 *   平台等价接线见 ExpertChat.tsx R3 注记）；
 * - window.confirm 中文文案逐字保留（t("Delete this entry?")→「确定删除此条目吗？」）。
 * - 交互逐字未改：分类管理折叠/新建/重命名（inline+Enter/Escape/blur）/删除、
 *   三态筛选（全部/已收藏/仅错题）+分类 chips 互斥、收藏切换、从分类移除、
 *   选择题选项着色（正确/误选）、主观题答案对照（coding 题围 python 栅栏）、解析、
 *   底部原会话/追问对话链接+时间戳。
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  WarningOutlined,
  BookOutlined,
  DownOutlined,
  ExportOutlined,
  FolderOpenOutlined,
  LoadingOutlined,
  MessageOutlined,
  FormOutlined,
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import {
  createCategory,
  deleteCategory,
  deleteNotebookEntry,
  listCategories,
  listNotebookEntries,
  removeEntryFromCategory,
  renameCategory,
  updateNotebookEntry,
  type NotebookCategory,
  type NotebookEntry,
} from "../admin/notebook-api";
import MarkdownRenderer from "../admin/MarkdownRenderer";

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const CARD = "var(--card, #ffffff)";
const MUTED = "var(--muted, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";

type FilterMode = "all" | "bookmarked" | "wrong";

export default function NotebookPage() {
  const [items, setItems] = useState<NotebookEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [categories, setCategories] = useState<NotebookCategory[]>([]);
  const [pendingId, setPendingId] = useState<number | null>(null);

  const [showCategoryManager, setShowCategoryManager] = useState(false);
  const [newCatName, setNewCatName] = useState("");
  const [renamingCat, setRenamingCat] = useState<{
    id: number;
    name: string;
  } | null>(null);

  const loadCategories = useCallback(async () => {
    try {
      setCategories(await listCategories());
    } catch {
      /* ignore */
    }
  }, []);

  const loadItems = useCallback(
    async (mode: FilterMode, catId: number | null) => {
      setRefreshing(true);
      setError(null);
      try {
        const response = await listNotebookEntries({
          bookmarked: mode === "bookmarked" ? true : undefined,
          is_correct: mode === "wrong" ? false : undefined,
          category_id: catId ?? undefined,
          limit: 200,
        });
        setItems(response.items);
        setTotal(response.total);
      } catch (err) {
        setError(String(err instanceof Error ? err.message : err));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadItems(filter, activeCategoryId);
    void loadCategories();
  }, [filter, activeCategoryId, loadItems, loadCategories]);

  const handleToggleBookmark = useCallback(
    async (item: NotebookEntry) => {
      const next = !item.bookmarked;
      setPendingId(item.id);
      try {
        await updateNotebookEntry(item.id, { bookmarked: next });
        setItems((prev) =>
          filter === "bookmarked" && !next
            ? prev.filter((e) => e.id !== item.id)
            : prev.map((e) =>
                e.id === item.id ? { ...e, bookmarked: next } : e,
              ),
        );
        if (filter === "bookmarked" && !next)
          setTotal((p) => Math.max(0, p - 1));
      } catch {
        /* ignore */
      }
      setPendingId(null);
    },
    [filter],
  );

  const handleDelete = useCallback(
    async (item: NotebookEntry) => {
      if (!window.confirm("确定删除此条目吗？")) return;
      setPendingId(item.id);
      try {
        await deleteNotebookEntry(item.id);
        setItems((prev) => prev.filter((e) => e.id !== item.id));
        setTotal((p) => Math.max(0, p - 1));
      } catch {
        /* ignore */
      }
      setPendingId(null);
    },
    [],
  );

  const handleRemoveFromCategory = useCallback(
    async (item: NotebookEntry) => {
      if (activeCategoryId === null) return;
      setPendingId(item.id);
      try {
        await removeEntryFromCategory(item.id, activeCategoryId);
        setItems((prev) => prev.filter((e) => e.id !== item.id));
        setTotal((p) => Math.max(0, p - 1));
      } catch {
        /* ignore */
      }
      setPendingId(null);
    },
    [activeCategoryId],
  );

  const handleCreateCategory = useCallback(async () => {
    if (!newCatName.trim()) return;
    try {
      await createCategory(newCatName.trim());
      setNewCatName("");
      await loadCategories();
    } catch {
      /* ignore */
    }
  }, [loadCategories, newCatName]);

  const handleRenameCategory = useCallback(async () => {
    if (!renamingCat || !renamingCat.name.trim()) return;
    try {
      await renameCategory(renamingCat.id, renamingCat.name.trim());
      setRenamingCat(null);
      await loadCategories();
    } catch {
      /* ignore */
    }
  }, [loadCategories, renamingCat]);

  const handleDeleteCategory = useCallback(
    async (catId: number) => {
      if (!window.confirm("确定删除此分类吗？")) return;
      try {
        await deleteCategory(catId);
        if (activeCategoryId === catId) setActiveCategoryId(null);
        await loadCategories();
      } catch {
        /* ignore */
      }
    },
    [activeCategoryId, loadCategories],
  );

  const FILTERS: { mode: FilterMode; label: string }[] = [
    { mode: "all", label: "全部" },
    { mode: "bookmarked", label: "已收藏" },
    { mode: "wrong", label: "仅错题" },
  ];

  return (
    <div style={{ height: "100%", overflowY: "auto", scrollbarGutter: "stable" } as React.CSSProperties}>
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "32px 24px" }}>
        {/* Header */}
        <div style={{ marginBottom: 24, display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 600, letterSpacing: "-0.01em", color: FG, margin: 0, fontFamily: "serif" }}>
              题库
            </h1>
            <p style={{ marginTop: 4, fontSize: 13, color: MUTED_FG }}>
              跨会话回顾和整理测验题目。
            </p>
          </div>
        </div>

        <div
          style={{
            marginBottom: 16,
            overflow: "hidden",
            borderRadius: 12,
            border: `1px solid ${BORDER}`,
            transition: "border-color 0.2s",
            background: showCategoryManager ? CARD : "transparent",
          }}
        >
          <button
            onClick={() => setShowCategoryManager((v) => !v)}
            style={{
              display: "flex",
              width: "100%",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "10px 16px",
              fontSize: 13,
              fontWeight: 500,
              color: FG,
              background: "none",
              border: "none",
              cursor: "pointer",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <FolderOpenOutlined style={{ fontSize: 14, color: MUTED_FG }} />
              管理分类
              {categories.length > 0 && (
                <span style={{ borderRadius: 999, background: MUTED, padding: "1px 6px", fontSize: 10, color: MUTED_FG }}>
                  {categories.length}
                </span>
              )}
            </span>
            <DownOutlined
              style={{
                fontSize: 12,
                color: MUTED_FG,
                transition: "transform 0.2s",
                transform: showCategoryManager ? "rotate(180deg)" : "none",
              }}
            />
          </button>

          {showCategoryManager && (
            <div style={{ borderTop: `1px solid ${BORDER}`, padding: "12px 16px 16px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {categories.map((cat) => (
                  <div
                    key={cat.id}
                    style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, borderRadius: 8, background: "rgba(0,0,0,0.02)", padding: "8px 12px" }}
                  >
                    {renamingCat?.id === cat.id ? (
                      <input
                        autoFocus
                        value={renamingCat.name}
                        onChange={(e) =>
                          setRenamingCat({
                            ...renamingCat,
                            name: e.target.value,
                          })
                        }
                        onKeyDown={(e) => {
                          if (e.key === "Enter") void handleRenameCategory();
                          if (e.key === "Escape") setRenamingCat(null);
                        }}
                        onBlur={() => void handleRenameCategory()}
                        style={{ flex: 1, borderRadius: 4, border: `1px solid ${BORDER}`, background: "var(--background, #fff)", padding: "2px 8px", fontSize: 12, color: FG, outline: "none" }}
                      />
                    ) : (
                      <span style={{ fontSize: 12, color: FG }}>
                        {cat.name}
                        <span style={{ marginLeft: 6, color: MUTED_FG }}>
                          ({cat.entry_count})
                        </span>
                      </span>
                    )}
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <button
                        onClick={() =>
                          setRenamingCat({ id: cat.id, name: cat.name })
                        }
                        style={{ borderRadius: 4, padding: 4, color: MUTED_FG, background: "none", border: "none", cursor: "pointer" }}
                      >
                        <EditOutlined style={{ fontSize: 12 }} />
                      </button>
                      <button
                        onClick={() => void handleDeleteCategory(cat.id)}
                        style={{ borderRadius: 4, padding: 4, color: MUTED_FG, background: "none", border: "none", cursor: "pointer" }}
                      >
                        <DeleteOutlined style={{ fontSize: 12 }} />
                      </button>
                    </div>
                  </div>
                ))}
                {!categories.length && (
                  <p style={{ padding: "8px 0", textAlign: "center", fontSize: 12, color: MUTED_FG }}>
                    暂无分类
                  </p>
                )}
              </div>
              <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <input
                  value={newCatName}
                  onChange={(e) => setNewCatName(e.target.value)}
                  onKeyDown={(e) =>
                    e.key === "Enter" && void handleCreateCategory()
                  }
                  placeholder="新分类名称..."
                  style={{ flex: 1, borderRadius: 8, border: `1px solid ${BORDER}`, background: "var(--background, #fff)", padding: "6px 12px", fontSize: 12, color: FG, outline: "none" }}
                />
                <button
                  onClick={() => void handleCreateCategory()}
                  disabled={!newCatName.trim()}
                  style={{ borderRadius: 8, background: PRIMARY, padding: "6px 12px", fontSize: 12, fontWeight: 500, color: "#fff", border: "none", cursor: "pointer", opacity: newCatName.trim() ? 1 : 0.3 }}
                >
                  <PlusOutlined style={{ fontSize: 13 }} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Filter bar */}
        <div style={{ marginBottom: 20, display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid rgba(0,0,0,0.06)`, paddingBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, overflowX: "auto" }}>
            {FILTERS.map(({ mode, label }) => {
              const active = filter === mode && activeCategoryId === null;
              return (
                <button
                  key={mode}
                  onClick={() => {
                    setFilter(mode);
                    setActiveCategoryId(null);
                  }}
                  style={{
                    display: "inline-flex",
                    flexShrink: 0,
                    alignItems: "center",
                    gap: 6,
                    borderRadius: 8,
                    padding: "6px 12px",
                    fontSize: 13,
                    background: active ? MUTED : "transparent",
                    fontWeight: active ? 500 : 400,
                    color: active ? FG : MUTED_FG,
                    border: "none",
                    cursor: "pointer",
                    transition: "color 0.2s",
                  }}
                >
                  {label}
                </button>
              );
            })}
            {categories.length > 0 && (
              <span style={{ margin: "0 4px", color: BORDER }}>|</span>
            )}
            {categories.map((cat) => {
              const active = activeCategoryId === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => {
                    setActiveCategoryId(cat.id);
                    setFilter("all");
                  }}
                  style={{
                    display: "inline-flex",
                    flexShrink: 0,
                    alignItems: "center",
                    gap: 6,
                    borderRadius: 8,
                    padding: "6px 12px",
                    fontSize: 13,
                    background: active ? MUTED : "transparent",
                    fontWeight: active ? 500 : 400,
                    color: active ? FG : MUTED_FG,
                    border: "none",
                    cursor: "pointer",
                    transition: "color 0.2s",
                  }}
                >
                  <FolderOpenOutlined style={{ fontSize: 12 }} />
                  {cat.name}
                </button>
              );
            })}
          </div>
          <span style={{ flexShrink: 0, fontSize: 12, color: MUTED_FG }}>
            总计: {total}
          </span>
        </div>

        {/* Content */}
        {loading ? (
          <div style={{ minHeight: 420, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <LoadingOutlined style={{ fontSize: 20, color: MUTED_FG }} spin={refreshing} />
          </div>
        ) : error ? (
          <div style={{ minHeight: 320, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", borderRadius: 12, border: `1px dashed #f0b0b0`, textAlign: "center" }}>
            <div style={{ marginBottom: 12, borderRadius: 12, background: "#fff1f0", padding: 10, color: "#ff4d4f" }}>
              <WarningOutlined style={{ fontSize: 18 }} />
            </div>
            <p style={{ fontSize: 14, fontWeight: 500, color: FG }}>
              加载失败
            </p>
            <p style={{ marginTop: 6, maxWidth: 320, fontSize: 13, color: MUTED_FG }}>
              {error}
            </p>
            <button
              onClick={() => void loadItems(filter, activeCategoryId)}
              style={{ marginTop: 12, borderRadius: 8, background: PRIMARY, padding: "6px 16px", fontSize: 12, fontWeight: 500, color: "#fff", border: "none", cursor: "pointer" }}
            >
              重试
            </button>
          </div>
        ) : items.length === 0 ? (
          <div style={{ minHeight: 320, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", borderRadius: 12, border: `1px dashed ${BORDER}`, textAlign: "center" }}>
            <div style={{ marginBottom: 12, borderRadius: 12, background: MUTED, padding: 10, color: MUTED_FG }}>
              <FormOutlined style={{ fontSize: 18 }} />
            </div>
            <p style={{ fontSize: 14, fontWeight: 500, color: FG }}>
              暂无题目
            </p>
            <p style={{ marginTop: 6, maxWidth: 320, fontSize: 13, color: MUTED_FG }}>
              测验中的题目将汇总到此处。
            </p>
          </div>
        ) : (
          <ul style={{ display: "flex", flexDirection: "column", gap: 12, listStyle: "none", margin: 0, padding: 0 }}>
            {items.map((item) => {
              const disabled = pendingId === item.id;
              return (
                <li
                  key={item.id}
                  style={{
                    borderRadius: 12,
                    border: `1px solid ${BORDER}`,
                    padding: "16px 20px",
                    transition: "opacity 0.2s",
                    opacity: disabled ? 0.6 : 1,
                  }}
                >
                  {/* Question header */}
                  <div style={{ marginBottom: 12, display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ marginBottom: 6, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
                        {item.difficulty && (
                          <span
                            style={{
                              borderRadius: 6,
                              padding: "2px 6px",
                              fontSize: 10,
                              fontWeight: 500,
                              textTransform: "uppercase",
                              ...(item.difficulty === "hard"
                                ? { background: "#fff1f0", color: "#f5222d" }
                                : item.difficulty === "medium"
                                  ? { background: "#fffbe6", color: "#d48806" }
                                  : { background: "#f6ffed", color: "#389e0d" }),
                            }}
                          >
                            {item.difficulty}
                          </span>
                        )}
                        {item.question_type && (
                          <span style={{ borderRadius: 6, background: MUTED, padding: "2px 6px", fontSize: 10, fontWeight: 500, color: MUTED_FG }}>
                            {item.question_type}
                          </span>
                        )}
                        <span
                          style={{
                            borderRadius: 6,
                            padding: "2px 6px",
                            fontSize: 10,
                            fontWeight: 600,
                            ...(item.is_correct
                              ? { background: "#f0fff0", color: "#389e0d" }
                              : { background: "#fff1f0", color: "#f5222d" }),
                          }}
                        >
                          {item.is_correct ? "正确" : "错误"}
                        </span>
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: FG }}>
                        <MarkdownRenderer
                          content={item.question}
                          variant="prose"
                          className="text-[14px] leading-relaxed"
                        />
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <button
                        onClick={() => void handleToggleBookmark(item)}
                        disabled={disabled}
                        title={
                          item.bookmarked ? "取消收藏" : "收藏"
                        }
                        style={{
                          borderRadius: 8,
                          padding: 6,
                          transition: "color 0.2s",
                          opacity: disabled ? 0.4 : 1,
                          color: item.bookmarked ? PRIMARY : MUTED_FG,
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                        }}
                      >
                        <BookOutlined
                          style={{ fontSize: 16 }}
                        />
                      </button>
                      {activeCategoryId !== null && (
                        <button
                          onClick={() => void handleRemoveFromCategory(item)}
                          disabled={disabled}
                          title="从分类中移除"
                          style={{ borderRadius: 8, padding: 6, color: MUTED_FG, transition: "color 0.2s", opacity: disabled ? 0.4 : 1, background: "none", border: "none", cursor: "pointer" }}
                        >
                          <CloseOutlined style={{ fontSize: 16 }} />
                        </button>
                      )}
                      <button
                        onClick={() => void handleDelete(item)}
                        disabled={disabled}
                        title="删除"
                        style={{ borderRadius: 8, padding: 6, color: MUTED_FG, transition: "color 0.2s", opacity: disabled ? 0.4 : 1, background: "none", border: "none", cursor: "pointer" }}
                      >
                        <DeleteOutlined style={{ fontSize: 16 }} />
                      </button>
                    </div>
                  </div>

                  {/* Options for choice questions */}
                  {item.options && Object.keys(item.options).length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      {Object.entries(item.options).map(([key, text]) => {
                        const isUserAnswer =
                          item.user_answer?.toUpperCase() === key.toUpperCase();
                        const isCorrectAnswer =
                          item.correct_answer?.toUpperCase() ===
                          key.toUpperCase();
                        const isWrongPick = isUserAnswer && !item.is_correct;
                        return (
                          <div
                            key={key}
                            style={{
                              display: "flex",
                              alignItems: "flex-start",
                              gap: 10,
                              borderRadius: 8,
                              border: `1px solid ${
                                isCorrectAnswer
                                  ? "#b7eb8f"
                                  : isWrongPick
                                    ? "#ffa39e"
                                    : "transparent"
                              }`,
                              background: isCorrectAnswer
                                ? "rgba(246,255,237,0.6)"
                                : isWrongPick
                                  ? "rgba(255,241,240,0.6)"
                                  : "rgba(0,0,0,0.02)",
                              padding: "8px 12px",
                              fontSize: 13,
                              marginBottom: 6,
                              transition: "color 0.2s",
                            }}
                          >
                            <span
                              style={{
                                marginTop: 1,
                                flexShrink: 0,
                                fontWeight: 600,
                                color: isCorrectAnswer
                                  ? "#389e0d"
                                  : isWrongPick
                                    ? "#f5222d"
                                    : MUTED_FG,
                              }}
                            >
                              {key}.
                            </span>
                            <span
                              style={{
                                flex: 1,
                                color:
                                  isCorrectAnswer || isWrongPick
                                    ? FG
                                    : MUTED_FG,
                              }}
                            >
                              {text}
                            </span>
                            {isCorrectAnswer && (
                              <span style={{ marginTop: 1, flexShrink: 0, fontSize: 10, fontWeight: 500, color: "#389e0d" }}>
                                ✓ 正确
                              </span>
                            )}
                            {isWrongPick && (
                              <span style={{ marginTop: 1, flexShrink: 0, fontSize: 10, fontWeight: 500, color: "#f5222d" }}>
                                ✗ 你的选择
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Answers for coding / written / fill-in questions */}
                  {(!item.options ||
                    Object.keys(item.options).length === 0) && (
                    <div style={{ marginBottom: 12 }}>
                      <div
                        style={{
                          borderRadius: 8,
                          border: `1px solid ${
                            !item.is_correct
                              ? "rgba(255,163,158,0.6)"
                              : "rgba(183,235,143,0.6)"
                          }`,
                          background: !item.is_correct
                            ? "rgba(255,241,240,0.4)"
                            : "rgba(246,255,237,0.4)",
                          padding: "10px 12px",
                          marginBottom: 8,
                          fontSize: 13,
                        }}
                      >
                        <div
                          style={{
                            marginBottom: 4,
                            fontSize: 11,
                            fontWeight: 500,
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                            color: !item.is_correct ? "#f5222d" : "#389e0d",
                          }}
                        >
                          你的答案 {item.is_correct ? "✓" : "✗"}
                        </div>
                        <div style={{ color: FG }}>
                          {item.user_answer ? (
                            item.question_type === "coding" ? (
                              <MarkdownRenderer
                                content={"```python\n" + item.user_answer + "\n```"}
                                variant="prose"
                                className="text-[13px]"
                              />
                            ) : (
                              <MarkdownRenderer
                                content={item.user_answer}
                                variant="prose"
                                className="text-[13px] leading-relaxed"
                              />
                            )
                          ) : (
                            <span style={{ color: MUTED_FG }}>
                              —
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ borderRadius: 8, border: "1px solid rgba(183,235,143,0.6)", background: "rgba(246,255,237,0.4)", padding: "10px 12px", fontSize: 13 }}>
                        <div style={{ marginBottom: 4, fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em", color: "#389e0d" }}>
                          参考答案
                        </div>
                        <div style={{ color: FG }}>
                          {item.correct_answer ? (
                            item.question_type === "coding" ? (
                              <MarkdownRenderer
                                content={
                                  item.correct_answer
                                    .trimStart()
                                    .startsWith("```")
                                    ? item.correct_answer
                                    : "```python\n" + item.correct_answer + "\n```"
                                }
                                variant="prose"
                                className="text-[13px]"
                              />
                            ) : (
                              <MarkdownRenderer
                                content={item.correct_answer}
                                variant="prose"
                                className="text-[13px] leading-relaxed"
                              />
                            )
                          ) : (
                            <span style={{ color: MUTED_FG }}>
                              —
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Explanation */}
                  {item.explanation && (
                    <div style={{ marginBottom: 12, borderRadius: 8, border: "1px solid rgba(145,202,255,0.6)", background: "rgba(230,244,255,0.3)", padding: "10px 12px" }}>
                      <div style={{ marginBottom: 4, fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em", color: "#1677ff" }}>
                        解析
                      </div>
                      <div style={{ fontSize: 13, lineHeight: 1.625, color: FG }}>
                        <MarkdownRenderer
                          content={item.explanation}
                          variant="prose"
                          className="text-[13px] leading-relaxed"
                        />
                      </div>
                    </div>
                  )}

                  {/* Footer */}
                  <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 8, fontSize: 11 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Link
                        to={`/e/sishu/chat?session=${encodeURIComponent(item.session_id)}`}
                        style={{ display: "inline-flex", alignItems: "center", gap: 6, borderRadius: 6, border: `1px solid ${BORDER}`, background: "rgba(0,0,0,0.02)", padding: "4px 10px", color: MUTED_FG, transition: "background 0.2s" }}
                      >
                        <ExportOutlined style={{ fontSize: 10 }} />
                        {item.session_title || "原始会话"}
                      </Link>
                      {item.followup_session_id && (
                        <Link
                          to={`/e/sishu/chat?session=${encodeURIComponent(item.followup_session_id)}`}
                          style={{ display: "inline-flex", alignItems: "center", gap: 6, borderRadius: 6, border: `1px solid ${BORDER}`, background: "rgba(0,0,0,0.02)", padding: "4px 10px", color: MUTED_FG, transition: "background 0.2s" }}
                        >
                          <MessageOutlined style={{ fontSize: 10 }} />
                          追问对话
                        </Link>
                      )}
                    </div>
                    <span style={{ color: MUTED_FG }}>
                      {new Date(item.created_at * 1000).toLocaleString()}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
