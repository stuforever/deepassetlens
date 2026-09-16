/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/QuestionBankPicker.tsx，319 行）。
 * 替换点：删除 "use client"；lucide Bookmark/Check/ClipboardList/FolderOpen/
 * Loader2/Search→TagOutlined(Bookmark)/CheckOutlined/SnippetsOutlined/
 * FolderOpenOutlined/LoadingOutlined(spin)/SearchOutlined；PickerShell/PickerHeader→
 * 本目录件；notebook-api→../../admin/notebook-api（批8 件，listCategories/
 * listNotebookEntries/NotebookCategory/NotebookEntry 契约一致）；Tailwind→内联样式
 * （difficulty 徽章 dark: 前缀在 tupu 单亮色主题降级，亮色分支取字面值）；t() 译文
 * 命中 zh/app.json 直出（"Select Question Bank Entries"→选择题库题目、
 * "Choose quiz questions to ground the next request."→选择题库题目作为本次提问的
 * 上下文。、"All"→全部、"Bookmarked"→已收藏、"Wrong Only"→仅错题、
 * "Search questions by content"→按题目内容搜索、"Clear"→清空、"Correct"→正确、
 * "Incorrect"→错误、"No quiz entries yet."→暂无题目记录。、"No matching questions
 * found."→未找到匹配的题目?——原键缺「未找到匹配的题目」译法时按原文件值、
 * "1 question selected"→已选择 1 道题目），未命中键按 i18next 回退直出原 key。
 * 过滤/分类/搜索/多选交互逐字未改。
 */
import { useEffect, useMemo, useState } from "react";
import {
  TagOutlined,
  CheckOutlined,
  SnippetsOutlined,
  FolderOpenOutlined,
  LoadingOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import PickerShell from "./PickerShell";
import PickerHeader from "./PickerHeader";
import {
  listCategories,
  listNotebookEntries,
  type NotebookCategory,
  type NotebookEntry,
} from "../../admin/notebook-api";
import { DT, ellipsis } from "./dtStyle";

export interface SelectedQuestionEntry {
  id: number;
  question: string;
  session_title: string;
  is_correct: boolean;
  difficulty: string;
}

interface QuestionBankPickerProps {
  open: boolean;
  onClose: () => void;
  onApply: (entries: SelectedQuestionEntry[]) => void;
}

type FilterMode = "all" | "bookmarked" | "wrong";

const FILTER_MODES: { value: FilterMode; label: string }[] = [
  { value: "all", label: "All" },
  { value: "bookmarked", label: "Bookmarked" },
  { value: "wrong", label: "Wrong Only" },
];

// zh/app.json 原译文替换表（t() 中文直出）。
const ZH: Record<string, string> = {
  All: "全部",
  Bookmarked: "已收藏",
  "Wrong Only": "仅错题",
  Clear: "清空",
  Correct: "正确",
  Incorrect: "错误",
};

function zh(text: string): string {
  return ZH[text] ?? text;
}

export default function QuestionBankPicker({
  open,
  onClose,
  onApply,
}: QuestionBankPickerProps) {
  const [entries, setEntries] = useState<NotebookEntry[]>([]);
  const [categories, setCategories] = useState<NotebookCategory[]>([]);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let mounted = true;
    void (async () => {
      try {
        setCategories(await listCategories());
      } catch {
        if (mounted) setCategories([]);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    let mounted = true;
    setLoading(true);
    void (async () => {
      try {
        const result = await listNotebookEntries({
          bookmarked: filter === "bookmarked" ? true : undefined,
          is_correct: filter === "wrong" ? false : undefined,
          category_id: activeCategoryId ?? undefined,
          limit: 200,
        });
        if (!mounted) return;
        setEntries(result.items);
      } catch {
        if (!mounted) return;
        setEntries([]);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [open, filter, activeCategoryId]);

  const filteredEntries = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return entries;
    return entries.filter((entry) => {
      const question = String(entry.question || "").toLowerCase();
      const session = String(entry.session_title || "").toLowerCase();
      return question.includes(keyword) || session.includes(keyword);
    });
  }, [entries, query]);

  const toggleEntry = (entryId: number) => {
    setSelectedIds((prev) =>
      prev.includes(entryId)
        ? prev.filter((id) => id !== entryId)
        : [...prev, entryId],
    );
  };

  const handleApply = () => {
    const selectedSet = new Set(selectedIds);
    const selectedEntries = entries
      .filter((entry) => selectedSet.has(entry.id))
      .map((entry) => ({
        id: entry.id,
        question: entry.question,
        session_title: entry.session_title,
        is_correct: entry.is_correct,
        difficulty: entry.difficulty || "",
      }));
    onApply(selectedEntries);
    onClose();
  };

  const difficultyChipStyle = (difficulty: string): React.CSSProperties => {
    if (difficulty === "hard") {
      return { background: "#fef2f2", color: "#dc2626" };
    }
    if (difficulty === "medium") {
      return { background: "#fffbeb", color: "#d97706" };
    }
    return { background: "#f0fdf4", color: "#16a34a" };
  };

  return (
    <PickerShell
      open={open}
      onClose={onClose}
      labelledBy="question-bank-picker-title"
      backdropClass="rgba(255,255,255,0.65)"
    >
      <div
        style={{
          width: "100%",
          maxWidth: 896,
          overflow: "hidden",
          borderRadius: 16,
          border: `1px solid ${DT.border}`,
          background: DT.card,
          color: DT.foreground,
          boxShadow: "0 22px 70px rgba(0,0,0,0.18)",
          padding: 16,
        }}
      >
        <PickerHeader
          icon={SnippetsOutlined}
          titleId="question-bank-picker-title"
          title={"选择题库题目"}
          subtitle={"选择题库题目作为本次提问的上下文。"}
          onClose={onClose}
        />

        <div style={{ background: "rgba(255,255,255,0.4)", padding: 20 }}>
          {/* Filter row */}
          <div style={{ marginBottom: 12, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 4 }}>
            {FILTER_MODES.map(({ value, label }) => {
              const active = filter === value && activeCategoryId === null;
              return (
                <button
                  key={value}
                  onClick={() => {
                    setFilter(value);
                    setActiveCategoryId(null);
                  }}
                  onMouseEnter={(e) => {
                    if (!active) e.currentTarget.style.color = DT.foreground;
                  }}
                  onMouseLeave={(e) => {
                    if (!active) e.currentTarget.style.color = DT.mutedForeground;
                  }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    borderRadius: 8,
                    border: "none",
                    cursor: "pointer",
                    padding: "6px 12px",
                    fontSize: 12,
                    background: active ? DT.muted : "transparent",
                    fontWeight: active ? 500 : 400,
                    color: active ? DT.foreground : DT.mutedForeground,
                    transition: "background-color 150ms, color 150ms",
                    font: "inherit",
                  }}
                >
                  {zh(label)}
                </button>
              );
            })}
            {categories.length > 0 && (
              <span style={{ margin: "0 4px", color: DT.border }}>|</span>
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
                  onMouseEnter={(e) => {
                    if (!active) e.currentTarget.style.color = DT.foreground;
                  }}
                  onMouseLeave={(e) => {
                    if (!active) e.currentTarget.style.color = DT.mutedForeground;
                  }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    borderRadius: 8,
                    border: "none",
                    cursor: "pointer",
                    padding: "6px 12px",
                    fontSize: 12,
                    background: active ? DT.muted : "transparent",
                    fontWeight: active ? 500 : 400,
                    color: active ? DT.foreground : DT.mutedForeground,
                    transition: "background-color 150ms, color 150ms",
                    font: "inherit",
                  }}
                >
                  <FolderOpenOutlined style={{ fontSize: 11 }} />
                  {cat.name}
                </button>
              );
            })}
          </div>

          <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ position: "relative", flex: 1 }}>
              <SearchOutlined
                style={{
                  pointerEvents: "none",
                  position: "absolute",
                  left: 12,
                  top: "50%",
                  height: 16,
                  width: 16,
                  fontSize: 14,
                  transform: "translateY(-50%)",
                  color: DT.mutedForeground,
                }}
              />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={"按题目内容搜索"}
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
            <button
              onClick={() => setSelectedIds([])}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = DT.muted;
                e.currentTarget.style.color = DT.foreground;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = DT.card;
                e.currentTarget.style.color = DT.mutedForeground;
              }}
              style={{
                borderRadius: 12,
                border: `1px solid ${DT.border}`,
                background: DT.card,
                padding: "10px 12px",
                fontSize: 12,
                fontWeight: 500,
                cursor: "pointer",
                color: DT.mutedForeground,
                transition: "background-color 150ms, color 150ms",
                font: "inherit",
              }}
            >
              清空
            </button>
          </div>

          <div
            style={{
              maxHeight: "56vh",
              overflowY: "auto",
              borderRadius: 16,
              border: `1px solid ${DT.border}`,
              background: DT.card,
            }}
          >
            {loading ? (
              <div style={{ minHeight: 280, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <LoadingOutlined spin style={{ fontSize: 20, color: DT.mutedForeground }} />
              </div>
            ) : filteredEntries.length ? (
              <div>
                {filteredEntries.map((entry, idx) => {
                  const selected = selectedIds.includes(entry.id);
                  return (
                    <button
                      key={entry.id}
                      onClick={() => toggleEntry(entry.id)}
                      onMouseEnter={(e) => {
                        if (!selected) {
                          e.currentTarget.style.background = DT.mutedAlpha(0.4);
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = selected
                          ? DT.primaryAlpha(0.08)
                          : "transparent";
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
                        background: selected ? DT.primaryAlpha(0.08) : "transparent",
                        font: "inherit",
                        borderTop: idx > 0 ? `1px solid ${DT.border}` : undefined,
                      }}
                    >
                      <div
                        style={{
                          marginTop: 2,
                          display: "flex",
                          height: 20,
                          width: 20,
                          flexShrink: 0,
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 6,
                          border: `1px solid ${selected ? DT.primary : DT.border}`,
                          background: selected ? DT.primary : "transparent",
                          color: selected ? DT.primaryForeground : "transparent",
                          transition: "background-color 150ms, border-color 150ms",
                        }}
                      >
                        <CheckOutlined style={{ fontSize: 12 }} />
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
                          {entry.difficulty && (
                            <span
                              style={{
                                borderRadius: 6,
                                padding: "2px 6px",
                                fontSize: 10,
                                fontWeight: 500,
                                textTransform: "uppercase",
                                ...difficultyChipStyle(entry.difficulty),
                              }}
                            >
                              {entry.difficulty}
                            </span>
                          )}
                          {entry.question_type && (
                            <span
                              style={{
                                borderRadius: 6,
                                background: DT.muted,
                                padding: "2px 6px",
                                fontSize: 10,
                                fontWeight: 500,
                                color: DT.mutedForeground,
                              }}
                            >
                              {entry.question_type}
                            </span>
                          )}
                          <span
                            style={{
                              borderRadius: 6,
                              padding: "2px 6px",
                              fontSize: 10,
                              fontWeight: 600,
                              background: entry.is_correct ? "#dcfce7" : "#fee2e2",
                              color: entry.is_correct ? "#15803d" : "#b91c1c",
                            }}
                          >
                            {entry.is_correct ? "正确" : "错误"}
                          </span>
                          {entry.bookmarked && (
                            <TagOutlined
                              style={{ fontSize: 11, color: DT.primary }}
                            />
                          )}
                        </div>
                        <p
                          style={{
                            margin: "4px 0 0",
                            fontSize: 13,
                            lineHeight: "20px",
                            color: DT.foreground,
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                          }}
                        >
                          {entry.question}
                        </p>
                        {entry.session_title && (
                          <div style={{ marginTop: 4, ...ellipsis, fontSize: 11, color: DT.mutedForegroundAlpha(0.85) }}>
                            {entry.session_title}
                          </div>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div style={{ padding: "56px 24px", textAlign: "center", fontSize: 13, color: DT.mutedForeground }}>
                {entries.length === 0
                  ? "暂无题目记录。"
                  : "未找到匹配的会话。"}
              </div>
            )}
          </div>

          <div style={{ marginTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div style={{ fontSize: 12, color: DT.mutedForeground }}>
              {selectedIds.length === 1
                ? "已选择 1 道题目"
                : `${selectedIds.length} questions selected`}
            </div>
            <button
              onClick={handleApply}
              disabled={!selectedIds.length}
              style={{
                borderRadius: 12,
                border: "none",
                cursor: !selectedIds.length ? "not-allowed" : "pointer",
                background: DT.primary,
                padding: "10px 16px",
                fontSize: 13,
                fontWeight: 500,
                color: DT.primaryForeground,
                opacity: !selectedIds.length ? 0.4 : 1,
                transition: "opacity 150ms",
                font: "inherit",
              }}
            >
              {`Use Selected Questions (${selectedIds.length})`}
            </button>
          </div>
        </div>
      </div>
    </PickerShell>
  );
}

// 具名再导出：批9 SA-A FollowupChatComposer 以 lazy(() => import(...).then((m) => ({ default: m.QuestionBankPicker }))) 消费（桌面原件仅 default 导出，此为批内契约对齐，非新逻辑）。
export { QuestionBankPicker };
