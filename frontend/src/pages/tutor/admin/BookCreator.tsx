/**
 * BookCreator —— AI 教材创建器（1:1 复刻自 DeepTutor）
 *
 * 来源：DeepTutor web/app/(workspace)/book/components/BookCreator.tsx（1174 行）
 * 复刻原则：所有区块 / 步骤 / 文案 1:1 保留，不裁剪。
 *
 * 替换点：
 *  - "use client" 删除；react-i18next（useTranslation / t()）→ 中文直出，
 *    译文逐条取自 DeepTutor locales/zh/app.json；原文按 count 单复数取不同 key 的，
 *    中文译文两支一致，故内联为单一文案。
 *  - lucide-react → @ant-design/icons 语义就近：Loader2→LoadingOutlined(spin)、
 *    Sparkles→ThunderboltOutlined、Database→DatabaseOutlined、NotebookPen→FormOutlined、
 *    ClipboardList→SnippetsOutlined、MessagesSquare→MessageSquareOutlined、Pencil→EditOutlined、
 *    RefreshCw→RedoOutlined、ChevronDown/Right/Up→DownOutlined/RightOutlined/UpOutlined。
 *  - Tailwind → antd 组件（Segmented / Button / Input / Select / Row / Col）+ 最小内联样式；
 *    颜色映射：border→#e4e4e7、muted→#f4f4f5、muted-foreground→#6b7280、
 *    foreground→rgba(0,0,0,0.88)、primary→#1677ff、card/background→#fff。
 *  - useAppShell 改由本目录 './appShellContext' 提供（另一 Agent 产出，导出 useAppShell）；
 *    BookProposal 来自 './book-types'，会话 API 契约同 './session-api'。
 *  - 导出形式与 props 契约（onCreate / loading / proposal / onConfirmProposal /
 *    confirmLoading）一字不改。
 */
import { useEffect, useRef, useState } from "react";
import type { CSSProperties, MouseEvent as ReactMouseEvent } from "react";
import {
  DatabaseOutlined,
  DownOutlined,
  EditOutlined,
  FormOutlined,
  LoadingOutlined,
  MessageOutlined,
  RedoOutlined,
  RightOutlined,
  SnippetsOutlined,
  ThunderboltOutlined,
  UpOutlined,
} from "@ant-design/icons";
import { Button, Col, Input, Row, Segmented, Select } from "antd";
import { useAppShell } from "./appShellContext";
import type { BookProposal } from "./book-types";
import { listKnowledgeBases, type KnowledgeBaseSummary } from "./knowledge-api";
import {
  getNotebook,
  listCategories,
  listNotebookEntries,
  listNotebooks,
  type NotebookCategory,
  type NotebookEntry,
  type NotebookRecordItem,
  type NotebookSummary,
} from "./notebook-api";
import {
  getSession,
  listSessions,
  type SessionMessage,
  type SessionSummary,
} from "./session-api";

const { TextArea } = Input;

// ── Tailwind 变量到字面量的最小映射 ──────────────────────────────────────
const BORDER = "#e4e4e7";
const MUTED_BG = "#f4f4f5";
const MUTED_FG = "#6b7280";
const FG = "rgba(0, 0, 0, 0.88)";
const PRIMARY = "#1677ff";
const CARD = "#fff";
const SHADOW_SM = "0 1px 2px 0 rgba(0, 0, 0, 0.05)";
const TRUNCATE: CSSProperties = {
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
};

/** hover 背景的行内样式等价实现（Tailwind hover:bg-* 无法用纯内联样式表达）。 */
function hoverBg(bg: string): {
  onMouseEnter: (e: ReactMouseEvent<HTMLElement>) => void;
  onMouseLeave: (e: ReactMouseEvent<HTMLElement>) => void;
} {
  return {
    onMouseEnter: (e) => {
      e.currentTarget.style.backgroundColor = bg;
    },
    onMouseLeave: (e) => {
      e.currentTarget.style.backgroundColor = "transparent";
    },
  };
}

type SourceTab = "knowledge" | "notebooks" | "questions" | "chats";

type ParentSelection<TChild extends string | number> =
  | { mode: "all" }
  | { mode: "subset"; ids: Set<TChild> };

type ParentMap<
  TParent extends string | number,
  TChild extends string | number,
> = Map<TParent, ParentSelection<TChild>>;

export interface BookCreatorProps {
  onCreate: (payload: {
    user_intent: string;
    chat_session_id: string;
    chat_selections: Array<{ session_id: string; message_ids: number[] }>;
    knowledge_bases: string[];
    notebook_refs: Array<Record<string, unknown>>;
    question_categories: number[];
    question_entries: number[];
    language: string;
  }) => void | Promise<void>;
  loading?: boolean;
  proposal?: BookProposal | null;
  onConfirmProposal?: (edited: BookProposal) => void | Promise<void>;
  confirmLoading?: boolean;
}

export default function BookCreator({
  onCreate,
  loading = false,
  proposal = null,
  onConfirmProposal,
  confirmLoading = false,
}: BookCreatorProps) {
  const { language: appLanguage } = useAppShell();
  const [intent, setIntent] = useState("");
  const [language, setLanguage] = useState(appLanguage);
  const languageTouchedRef = useRef(false);
  const [tab, setTab] = useState<SourceTab>("knowledge");

  // Knowledge bases (flat selection)
  const [kbs, setKbs] = useState<KnowledgeBaseSummary[]>([]);
  const [kbsLoading, setKbsLoading] = useState(false);
  const [selectedKbs, setSelectedKbs] = useState<Set<string>>(new Set());

  // Notebooks → records (tree selection)
  const [notebooks, setNotebooks] = useState<NotebookSummary[]>([]);
  const [notebooksLoading, setNotebooksLoading] = useState(false);
  const [notebookSelection, setNotebookSelection] = useState<
    ParentMap<string, string>
  >(new Map());
  const [notebookExpanded, setNotebookExpanded] = useState<Set<string>>(
    new Set(),
  );
  const [notebookRecords, setNotebookRecords] = useState<
    Record<string, NotebookRecordItem[]>
  >({});
  const [notebookRecordsLoading, setNotebookRecordsLoading] = useState<
    Record<string, boolean>
  >({});

  // Question bank: categories → entries
  const [categories, setCategories] = useState<NotebookCategory[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [questionSelection, setQuestionSelection] = useState<
    ParentMap<number, number>
  >(new Map());
  const [questionExpanded, setQuestionExpanded] = useState<Set<number>>(
    new Set(),
  );
  const [questionEntries, setQuestionEntries] = useState<
    Record<number, NotebookEntry[]>
  >({});
  const [questionEntriesLoading, setQuestionEntriesLoading] = useState<
    Record<number, boolean>
  >({});

  // Chat history: sessions → messages
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [chatSelection, setChatSelection] = useState<ParentMap<string, number>>(
    new Map(),
  );
  const [chatExpanded, setChatExpanded] = useState<Set<string>>(new Set());
  const [chatMessages, setChatMessages] = useState<
    Record<string, SessionMessage[]>
  >({});
  const [chatMessagesLoading, setChatMessagesLoading] = useState<
    Record<string, boolean>
  >({});

  const [editProposal, setEditProposal] = useState<BookProposal | null>(null);
  const [formCollapsed, setFormCollapsed] = useState(false);
  const lastSeenProposalIdRef = useRef<string | null>(null);

  // Auto-collapse the form once the proposal first arrives (never overwrites
  // a manual expand later because we only fire on identity change).
  useEffect(() => {
    const id = proposal ? proposal.title || "_proposal_" : null;
    if (id && id !== lastSeenProposalIdRef.current) {
      setFormCollapsed(true);
    }
    lastSeenProposalIdRef.current = id;
  }, [proposal]);

  const refreshKbs = async () => {
    setKbsLoading(true);
    try {
      setKbs(await listKnowledgeBases({ force: true }));
    } catch {
      setKbs([]);
    } finally {
      setKbsLoading(false);
    }
  };
  const refreshNotebooks = async () => {
    setNotebooksLoading(true);
    try {
      setNotebooks(await listNotebooks());
    } catch {
      setNotebooks([]);
    } finally {
      setNotebooksLoading(false);
    }
  };
  const refreshCategories = async () => {
    setCategoriesLoading(true);
    try {
      setCategories(await listCategories());
    } catch {
      setCategories([]);
    } finally {
      setCategoriesLoading(false);
    }
  };
  const refreshSessions = async () => {
    setSessionsLoading(true);
    try {
      setSessions(await listSessions(50, 0, { force: true }));
    } catch {
      setSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  };

  useEffect(() => {
    void refreshKbs();
    void refreshNotebooks();
    void refreshCategories();
    void refreshSessions();
  }, []);

  useEffect(() => {
    if (!languageTouchedRef.current) setLanguage(appLanguage);
  }, [appLanguage]);

  // ── selection counts ─────────────────────────────────────────────
  const countSelection = <P extends string | number, C extends string | number>(
    map: ParentMap<P, C>,
  ): number => {
    let n = 0;
    map.forEach((sel) => {
      n += sel.mode === "all" ? 1 : sel.ids.size;
    });
    return n;
  };
  const nbCount = countSelection(notebookSelection);
  const qCount = countSelection(questionSelection);
  const chatCount = countSelection(chatSelection);
  const totalSelected = selectedKbs.size + nbCount + qCount + chatCount;

  // ── generic tree-selection helpers ───────────────────────────────
  const toggleParent = <P extends string | number, C extends string | number>(
    map: ParentMap<P, C>,
    parent: P,
  ): ParentMap<P, C> => {
    const next = new Map(map);
    if (next.has(parent)) next.delete(parent);
    else next.set(parent, { mode: "all" });
    return next;
  };
  const toggleChild = <P extends string | number, C extends string | number>(
    map: ParentMap<P, C>,
    parent: P,
    child: C,
    knownChildren: C[],
  ): ParentMap<P, C> => {
    const next = new Map(map);
    const current = next.get(parent);
    let ids: Set<C>;
    if (!current) {
      ids = new Set([child]);
    } else if (current.mode === "all") {
      // materialize: all known children except the one being unchecked
      ids = new Set(knownChildren.filter((c) => c !== child));
    } else {
      ids = new Set(current.ids);
      if (ids.has(child)) ids.delete(child);
      else ids.add(child);
    }
    if (ids.size === 0) next.delete(parent);
    else next.set(parent, { mode: "subset", ids });
    return next;
  };

  const toggleKb = (name: string) => {
    setSelectedKbs((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  // ── lazy children loaders ────────────────────────────────────────
  const ensureNotebookRecords = async (id: string) => {
    if (notebookRecords[id] || notebookRecordsLoading[id]) return;
    setNotebookRecordsLoading((p) => ({ ...p, [id]: true }));
    try {
      const detail = await getNotebook(id);
      setNotebookRecords((p) => ({ ...p, [id]: detail.records ?? [] }));
    } catch {
      setNotebookRecords((p) => ({ ...p, [id]: [] }));
    } finally {
      setNotebookRecordsLoading((p) => ({ ...p, [id]: false }));
    }
  };
  const ensureQuestionEntries = async (id: number) => {
    if (questionEntries[id] || questionEntriesLoading[id]) return;
    setQuestionEntriesLoading((p) => ({ ...p, [id]: true }));
    try {
      const result = await listNotebookEntries({ category_id: id, limit: 200 });
      setQuestionEntries((p) => ({ ...p, [id]: result.items }));
    } catch {
      setQuestionEntries((p) => ({ ...p, [id]: [] }));
    } finally {
      setQuestionEntriesLoading((p) => ({ ...p, [id]: false }));
    }
  };
  const ensureChatMessages = async (sid: string) => {
    if (chatMessages[sid] || chatMessagesLoading[sid]) return;
    setChatMessagesLoading((p) => ({ ...p, [sid]: true }));
    try {
      const detail = await getSession(sid);
      setChatMessages((p) => ({ ...p, [sid]: detail.messages ?? [] }));
    } catch {
      setChatMessages((p) => ({ ...p, [sid]: [] }));
    } finally {
      setChatMessagesLoading((p) => ({ ...p, [sid]: false }));
    }
  };

  // ── submit ───────────────────────────────────────────────────────
  const handleCreate = async () => {
    if (!intent.trim()) return;

    const notebook_refs: Array<{ notebook_id: string; record_ids: string[] }> =
      [];
    notebookSelection.forEach((sel, id) => {
      notebook_refs.push({
        notebook_id: id,
        record_ids: sel.mode === "all" ? [] : Array.from(sel.ids),
      });
    });

    const question_categories: number[] = [];
    const question_entries: number[] = [];
    questionSelection.forEach((sel, id) => {
      if (sel.mode === "all") question_categories.push(id);
      else sel.ids.forEach((eid) => question_entries.push(eid));
    });

    const chat_selections: Array<{
      session_id: string;
      message_ids: number[];
    }> = [];
    chatSelection.forEach((sel, sid) => {
      chat_selections.push({
        session_id: sid,
        message_ids: sel.mode === "all" ? [] : Array.from(sel.ids),
      });
    });

    await onCreate({
      user_intent: intent,
      chat_session_id: "",
      chat_selections,
      knowledge_bases: Array.from(selectedKbs),
      notebook_refs,
      question_categories,
      question_entries,
      language,
    });
  };

  const currentProposal = editProposal || proposal;

  const tabConfig: Array<{
    key: SourceTab;
    label: string;
    icon: typeof DatabaseOutlined;
    count: number;
  }> = [
    {
      key: "knowledge",
      label: "知识库",
      icon: DatabaseOutlined,
      count: selectedKbs.size,
    },
    {
      key: "notebooks",
      label: "笔记本",
      icon: FormOutlined,
      count: nbCount,
    },
    {
      key: "questions",
      label: "题目列表",
      icon: SnippetsOutlined,
      count: qCount,
    },
    { key: "chats", label: "聊天", icon: MessageOutlined, count: chatCount },
  ];

  // Summary chips shown in the collapsed form header so users always see what
  // sources their proposal was generated from (even after collapsing).
  const summaryChips: Array<{ icon: typeof DatabaseOutlined; label: string }> =
    [];
  if (selectedKbs.size > 0) {
    summaryChips.push({
      icon: DatabaseOutlined,
      label: `${selectedKbs.size} 个知识库`,
    });
  }
  if (nbCount > 0) {
    summaryChips.push({
      icon: FormOutlined,
      label: `${nbCount} 条笔记记录`,
    });
  }
  if (qCount > 0) {
    summaryChips.push({
      icon: SnippetsOutlined,
      label: `${qCount} 道题目`,
    });
  }
  if (chatCount > 0) {
    summaryChips.push({
      icon: MessageOutlined,
      label: `${chatCount} 条聊天内容`,
    });
  }

  return (
    <div
      style={{
        width: "100%",
        maxWidth: 672,
        margin: "0 auto",
        padding: 24,
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <h1
          style={{
            margin: 0,
            fontFamily: 'Georgia, "Songti SC", SimSun, serif',
            fontSize: 24,
            fontWeight: 600,
            color: FG,
          }}
        >
          创建新书
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: MUTED_FG }}>
          描述你想学习的内容，然后选择知识来源，融合成一本结构化、可交互的书。
        </p>
      </div>

      <div
        style={{
          borderRadius: 16,
          border: `1px solid ${BORDER}`,
          background: CARD,
          boxShadow: SHADOW_SM,
        }}
      >
        <button
          type="button"
          onClick={() => setFormCollapsed((v) => !v)}
          {...hoverBg("rgba(244, 244, 245, 0.4)")}
          style={{
            display: "flex",
            width: "100%",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            padding: "12px 20px",
            textAlign: "left",
            borderTopLeftRadius: 16,
            borderTopRightRadius: 16,
            border: "none",
            background: "transparent",
            cursor: "pointer",
          }}
        >
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: FG }}>
                {formCollapsed ? "输入" : "配置输入"}
              </span>
              {formCollapsed && intent.trim() && (
                <span style={{ ...TRUNCATE, fontSize: 12, color: MUTED_FG }}>
                  · {clip(intent, 90)}
                </span>
              )}
            </div>
            {formCollapsed && (
              <div
                style={{
                  marginTop: 4,
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                {summaryChips.length === 0 ? (
                  <span style={{ fontSize: 11, color: MUTED_FG }}>
                    尚未选择知识来源
                  </span>
                ) : (
                  summaryChips.map((chip, i) => (
                    <span
                      key={i}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                        borderRadius: 999,
                        background: "rgba(22, 119, 255, 0.1)",
                        padding: "2px 8px",
                        fontSize: 11,
                        fontWeight: 500,
                        color: PRIMARY,
                      }}
                    >
                      <chip.icon style={{ fontSize: 12 }} />
                      {chip.label}
                    </span>
                  ))
                )}
              </div>
            )}
          </div>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              borderRadius: 4,
              padding: "4px 8px",
              fontSize: 11,
              color: MUTED_FG,
            }}
          >
            {formCollapsed ? (
              <>
                <EditOutlined style={{ fontSize: 12 }} />
                编辑
              </>
            ) : (
              <UpOutlined style={{ fontSize: 14 }} />
            )}
          </span>
        </button>

        {!formCollapsed && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 16,
              padding: "0 20px 20px",
            }}
          >
            <label style={{ display: "block" }}>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.16em",
                  color: MUTED_FG,
                }}
              >
                学习意图
              </span>
              <TextArea
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
                rows={5}
                data-testid="book-intent-input"
                placeholder="例如：通过推导和练习建立对 Transformer 注意力机制的直觉。"
                style={{
                  marginTop: 6,
                  resize: "none",
                  borderRadius: 12,
                  fontSize: 14,
                }}
              />
            </label>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.16em",
                    color: MUTED_FG,
                  }}
                >
                  知识来源
                  {totalSelected > 0 && (
                    <span
                      style={{
                        marginLeft: 8,
                        borderRadius: 999,
                        background: "rgba(22, 119, 255, 0.15)",
                        padding: "2px 8px",
                        fontSize: 10,
                        fontWeight: 600,
                        color: PRIMARY,
                      }}
                    >
                      {`已选择 ${totalSelected} 项`}
                    </span>
                  )}
                </span>
                <Button
                  type="text"
                  size="small"
                  icon={<RedoOutlined style={{ fontSize: 12 }} />}
                  onClick={() => {
                    if (tab === "knowledge") void refreshKbs();
                    else if (tab === "notebooks") void refreshNotebooks();
                    else if (tab === "questions") void refreshCategories();
                    else void refreshSessions();
                  }}
                  style={{ fontSize: 11, color: MUTED_FG, height: 24, padding: "0 8px" }}
                >
                  刷新
                </Button>
              </div>

              <Segmented
                block
                value={tab}
                onChange={(v) => setTab(v as SourceTab)}
                style={{
                  width: "100%",
                  background: MUTED_BG,
                  border: `1px solid ${BORDER}`,
                  padding: 2,
                  borderRadius: 8,
                }}
                options={tabConfig.map((item) => ({
                  value: item.key,
                  label: (
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        fontSize: 12,
                        fontWeight: 500,
                      }}
                    >
                      <item.icon style={{ fontSize: 13 }} />
                      {item.label}
                      {item.count > 0 && (
                        <span
                          style={{
                            marginLeft: 2,
                            borderRadius: 999,
                            padding: "0 6px",
                            fontSize: 10,
                            fontWeight: 600,
                            background:
                              tab === item.key
                                ? "rgba(22, 119, 255, 0.15)"
                                : "rgba(228, 228, 231, 0.7)",
                            color: tab === item.key ? PRIMARY : MUTED_FG,
                          }}
                        >
                          {item.count}
                        </span>
                      )}
                    </span>
                  ),
                }))}
              />

              <div
                style={{
                  maxHeight: 288,
                  overflowY: "auto",
                  borderRadius: 12,
                  border: `1px solid ${BORDER}`,
                  background: CARD,
                  padding: 6,
                }}
              >
                {tab === "knowledge" && (
                  <FlatList
                    loading={kbsLoading}
                    emptyHint="暂无知识库。请先在“知识”页面创建一个。"
                    items={kbs.map((kb) => ({
                      key: kb.name,
                      primary: kb.name,
                      secondary: kb.is_default ? "默认" : kb.status || "",
                      checked: selectedKbs.has(kb.name),
                      onToggle: () => toggleKb(kb.name),
                    }))}
                  />
                )}

                {tab === "notebooks" && (
                  <TreeList
                    loading={notebooksLoading}
                    emptyHint="暂无笔记本。请先将聊天输出保存到笔记本。"
                    parents={notebooks.map((nb) => {
                      const records = notebookRecords[nb.id];
                      return {
                        id: nb.id,
                        title: nb.name,
                        subtitle: parentSubtitle(
                          notebookSelection.get(nb.id),
                          records?.length ?? nb.record_count ?? 0,
                          "条记录",
                          "条记录",
                        ),
                        expanded: notebookExpanded.has(nb.id),
                        childrenLoading: !!notebookRecordsLoading[nb.id],
                        children: (records ?? []).map((rec) => ({
                          id: rec.id,
                          title: rec.title || "（未命名）",
                          subtitle: rec.summary || "",
                        })),
                        selection: notebookSelection.get(nb.id),
                      };
                    })}
                    onToggleParent={(id) =>
                      setNotebookSelection((prev) => toggleParent(prev, id))
                    }
                    onToggleChild={(parentId, childId, knownChildren) =>
                      setNotebookSelection((prev) =>
                        toggleChild(prev, parentId, childId, knownChildren),
                      )
                    }
                    onToggleExpand={(id) => {
                      setNotebookExpanded((prev) => {
                        const next = new Set(prev);
                        if (next.has(id)) next.delete(id);
                        else {
                          next.add(id);
                          void ensureNotebookRecords(id);
                        }
                        return next;
                      });
                    }}
                  />
                )}

                {tab === "questions" && (
                  <TreeList<number, number>
                    loading={categoriesLoading}
                    emptyHint="暂无题目分类。请先将题目收藏到某个分类。"
                    parents={categories.map((cat) => {
                      const entries = questionEntries[cat.id];
                      return {
                        id: cat.id,
                        title: cat.name,
                        subtitle: parentSubtitle(
                          questionSelection.get(cat.id),
                          entries?.length ?? cat.entry_count ?? 0,
                          "条目",
                          "条目",
                        ),
                        expanded: questionExpanded.has(cat.id),
                        childrenLoading: !!questionEntriesLoading[cat.id],
                        children: (entries ?? []).map((e) => ({
                          id: e.id,
                          title: e.question || "（无题干）",
                          subtitle: `${e.is_correct ? "✓" : "✗"} ${
                            e.user_answer
                              ? `你的答案：${e.user_answer}`
                              : "未作答"
                          } · ${`正确答案：${e.correct_answer}`}`,
                        })),
                        selection: questionSelection.get(cat.id),
                      };
                    })}
                    onToggleParent={(id) =>
                      setQuestionSelection((prev) => toggleParent(prev, id))
                    }
                    onToggleChild={(parentId, childId, knownChildren) =>
                      setQuestionSelection((prev) =>
                        toggleChild(prev, parentId, childId, knownChildren),
                      )
                    }
                    onToggleExpand={(id) => {
                      setQuestionExpanded((prev) => {
                        const next = new Set(prev);
                        if (next.has(id)) next.delete(id);
                        else {
                          next.add(id);
                          void ensureQuestionEntries(id);
                        }
                        return next;
                      });
                    }}
                  />
                )}

                {tab === "chats" && (
                  <TreeList<string, number>
                    loading={sessionsLoading}
                    emptyHint="暂无聊天会话。"
                    parents={sessions.map((s) => {
                      const msgs = chatMessages[s.session_id];
                      return {
                        id: s.session_id,
                        title: s.title || "（未命名聊天）",
                        subtitle: parentSubtitle(
                          chatSelection.get(s.session_id),
                          msgs?.length ?? s.message_count ?? 0,
                          "条消息",
                          "条消息",
                        ),
                        expanded: chatExpanded.has(s.session_id),
                        childrenLoading: !!chatMessagesLoading[s.session_id],
                        children: (msgs ?? []).map((m) => ({
                          id: m.id,
                          title: `${m.role}${m.capability ? ` · ${m.capability}` : ""}`,
                          subtitle: clip(m.content, 140),
                        })),
                        selection: chatSelection.get(s.session_id),
                      };
                    })}
                    onToggleParent={(id) =>
                      setChatSelection((prev) => toggleParent(prev, id))
                    }
                    onToggleChild={(parentId, childId, knownChildren) =>
                      setChatSelection((prev) =>
                        toggleChild(prev, parentId, childId, knownChildren),
                      )
                    }
                    onToggleExpand={(id) => {
                      setChatExpanded((prev) => {
                        const next = new Set(prev);
                        if (next.has(id)) next.delete(id);
                        else {
                          next.add(id);
                          void ensureChatMessages(id);
                        }
                        return next;
                      });
                    }}
                  />
                )}
              </div>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <label style={{ fontSize: 12, color: MUTED_FG }}>
                语言{" "}
                <Select
                  size="small"
                  value={language}
                  onChange={(v) => {
                    languageTouchedRef.current = true;
                    setLanguage(v as "en" | "zh");
                  }}
                  style={{ marginLeft: 4, minWidth: 76 }}
                  options={[
                    { value: "en", label: "English" },
                    { value: "zh", label: "中文" },
                  ]}
                />
              </label>
              <Button
                type="primary"
                onClick={handleCreate}
                disabled={loading || !intent.trim()}
                data-testid="book-create-submit"
                icon={
                  loading ? (
                    <LoadingOutlined spin style={{ fontSize: 16 }} />
                  ) : (
                    <ThunderboltOutlined style={{ fontSize: 16 }} />
                  )
                }
                style={{
                  borderRadius: 12,
                  padding: "8px 16px",
                  height: "auto",
                  fontSize: 14,
                }}
              >
                生成方案
              </Button>
            </div>
          </div>
        )}
      </div>

      {currentProposal && onConfirmProposal && (
        <div
          data-testid="book-proposal-card"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 16,
            borderRadius: 16,
            border: `1px solid ${BORDER}`,
            background: CARD,
            padding: 20,
            boxShadow: SHADOW_SM,
          }}
        >
          <div>
            <h2
              style={{
                margin: 0,
                fontSize: 16,
                fontWeight: 600,
                color: FG,
              }}
            >
              方案
            </h2>
            <p style={{ margin: 0, fontSize: 12, color: MUTED_FG }}>
              可编辑下方内容，确认后生成章节主线。
            </p>
          </div>
          <ProposalForm
            proposal={currentProposal}
            onChange={setEditProposal}
            selectedKbs={Array.from(selectedKbs)}
          />
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Button
              type="primary"
              onClick={() =>
                editProposal
                  ? onConfirmProposal(editProposal)
                  : onConfirmProposal(currentProposal)
              }
              disabled={confirmLoading}
              data-testid="book-proposal-confirm"
              icon={
                confirmLoading ? (
                  <LoadingOutlined spin style={{ fontSize: 16 }} />
                ) : undefined
              }
              style={{
                borderRadius: 12,
                padding: "8px 16px",
                height: "auto",
                fontSize: 14,
              }}
            >
              确认方案并生成主线
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── helpers ───────────────────────────────────────────────────────────

function clip(text: string, n: number): string {
  if (!text) return "";
  const t = text.replace(/\s+/g, " ").trim();
  return t.length <= n ? t : t.slice(0, n) + "…";
}

function parentSubtitle<C extends string | number>(
  sel: ParentSelection<C> | undefined,
  total: number,
  unit: string,
  unitPlural?: string,
): string {
  const plural = unitPlural || `${unit}s`;
  const fmt = (n: number) => `${n} ${n === 1 ? unit : plural}`;
  if (!sel) return total > 0 ? fmt(total) : `0 ${plural}`;
  if (sel.mode === "all") {
    return total > 0 ? `全部 ${fmt(total)}` : "全部";
  }
  return total > 0
    ? `已选 ${sel.ids.size} / ${fmt(total)}`
    : `已选择 ${sel.ids.size} 项`;
}

// ─── checkbox icon ─────────────────────────────────────────────────────

function CheckBox({ state }: { state: "off" | "on" | "indeterminate" }) {
  if (state === "off") {
    return (
      <span
        style={{
          display: "flex",
          height: 16,
          width: 16,
          flexShrink: 0,
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 4,
          border: `1px solid ${BORDER}`,
          background: CARD,
          boxSizing: "border-box",
        }}
      />
    );
  }
  if (state === "indeterminate") {
    return (
      <span
        style={{
          display: "flex",
          height: 16,
          width: 16,
          flexShrink: 0,
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 4,
          border: `1px solid ${PRIMARY}`,
          background: PRIMARY,
        }}
      >
        <span style={{ height: 2, width: 8, borderRadius: 2, background: "#fff" }} />
      </span>
    );
  }
  return (
    <span
      style={{
        display: "flex",
        height: 16,
        width: 16,
        flexShrink: 0,
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 4,
        border: `1px solid ${PRIMARY}`,
        background: PRIMARY,
        color: "#fff",
      }}
    >
      <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
        <path
          d="M2.5 6.5L5 9L9.5 3.5"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

// ─── flat list (for KB tab) ────────────────────────────────────────────

function FlatList({
  loading,
  emptyHint,
  items,
}: {
  loading: boolean;
  emptyHint: string;
  items: Array<{
    key: string;
    primary: string;
    secondary?: string;
    checked: boolean;
    onToggle: () => void;
  }>;
}) {
  if (loading)
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          padding: "24px 0",
          fontSize: 12,
          color: MUTED_FG,
        }}
      >
        <LoadingOutlined spin style={{ fontSize: 14 }} />
        加载中…
      </div>
    );
  if (items.length === 0)
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px 12px",
          textAlign: "center",
          fontSize: 12,
          color: MUTED_FG,
        }}
      >
        {emptyHint}
      </div>
    );
  return (
    <ul
      style={{
        listStyle: "none",
        margin: 0,
        padding: 0,
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      {items.map((item) => (
        <li key={item.key}>
          <button
            type="button"
            onClick={item.onToggle}
            {...(item.checked ? {} : hoverBg("rgba(244, 244, 245, 0.6)"))}
            style={{
              display: "flex",
              width: "100%",
              alignItems: "center",
              gap: 10,
              borderRadius: 4,
              padding: "6px 8px",
              textAlign: "left",
              fontSize: 13,
              border: "none",
              cursor: "pointer",
              background: item.checked
                ? "rgba(22, 119, 255, 0.1)"
                : "transparent",
              color: "inherit",
            }}
          >
            <CheckBox state={item.checked ? "on" : "off"} />
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ ...TRUNCATE, fontWeight: 500, color: FG }}>
                {item.primary}
              </div>
              {item.secondary && (
                <div style={{ ...TRUNCATE, fontSize: 11, color: MUTED_FG }}>
                  {item.secondary}
                </div>
              )}
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}

// ─── tree list (for notebooks / questions / chats) ─────────────────────

interface TreeChild<C extends string | number> {
  id: C;
  title: string;
  subtitle?: string;
}

interface TreeParent<P extends string | number, C extends string | number> {
  id: P;
  title: string;
  subtitle?: string;
  expanded: boolean;
  childrenLoading: boolean;
  children: TreeChild<C>[];
  selection: ParentSelection<C> | undefined;
}

function TreeList<
  P extends string | number = string,
  C extends string | number = string,
>({
  loading,
  emptyHint,
  parents,
  onToggleParent,
  onToggleChild,
  onToggleExpand,
}: {
  loading: boolean;
  emptyHint: string;
  parents: TreeParent<P, C>[];
  onToggleParent: (id: P) => void;
  onToggleChild: (parentId: P, childId: C, knownChildren: C[]) => void;
  onToggleExpand: (id: P) => void;
}) {
  if (loading)
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          padding: "24px 0",
          fontSize: 12,
          color: MUTED_FG,
        }}
      >
        <LoadingOutlined spin style={{ fontSize: 14 }} />
        加载中…
      </div>
    );
  if (parents.length === 0)
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px 12px",
          textAlign: "center",
          fontSize: 12,
          color: MUTED_FG,
        }}
      >
        {emptyHint}
      </div>
    );

  return (
    <ul
      style={{
        listStyle: "none",
        margin: 0,
        padding: 0,
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      {parents.map((p) => {
        const sel = p.selection;
        const parentState: "on" | "off" | "indeterminate" = !sel
          ? "off"
          : sel.mode === "all"
            ? "on"
            : "indeterminate";

        return (
          <li key={String(p.id)}>
            <div
              {...(sel ? {} : hoverBg("rgba(244, 244, 245, 0.6)"))}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                borderRadius: 4,
                paddingRight: 8,
                background: sel ? "rgba(22, 119, 255, 0.08)" : "transparent",
              }}
            >
              <button
                type="button"
                onClick={() => onToggleExpand(p.id)}
                aria-label={p.expanded ? "收起" : "展开"}
                style={{
                  display: "flex",
                  height: 28,
                  width: 24,
                  flexShrink: 0,
                  alignItems: "center",
                  justifyContent: "center",
                  color: MUTED_FG,
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                {p.expanded ? (
                  <DownOutlined style={{ fontSize: 14 }} />
                ) : (
                  <RightOutlined style={{ fontSize: 14 }} />
                )}
              </button>
              <button
                type="button"
                onClick={() => onToggleParent(p.id)}
                style={{
                  display: "flex",
                  minWidth: 0,
                  flex: 1,
                  alignItems: "center",
                  gap: 10,
                  padding: "6px 0",
                  textAlign: "left",
                  fontSize: 13,
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                <CheckBox state={parentState} />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ ...TRUNCATE, fontWeight: 500, color: FG }}>
                    {p.title}
                  </div>
                  {p.subtitle && (
                    <div style={{ ...TRUNCATE, fontSize: 11, color: MUTED_FG }}>
                      {p.subtitle}
                    </div>
                  )}
                </div>
              </button>
            </div>

            {p.expanded && (
              <div
                style={{
                  marginLeft: 24,
                  marginTop: 2,
                  borderLeft: `1px solid ${BORDER}`,
                  paddingLeft: 6,
                }}
              >
                {p.childrenLoading ? (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "8px 8px",
                      fontSize: 11,
                      color: MUTED_FG,
                    }}
                  >
                    <LoadingOutlined spin style={{ fontSize: 12 }} />
                    加载中…
                  </div>
                ) : p.children.length === 0 ? (
                  <div
                    style={{
                      padding: "8px 8px",
                      fontSize: 11,
                      color: MUTED_FG,
                    }}
                  >
                    里面暂无内容。
                  </div>
                ) : (
                  <ul
                    style={{
                      listStyle: "none",
                      margin: 0,
                      padding: 0,
                      maxHeight: 224,
                      display: "flex",
                      flexDirection: "column",
                      gap: 2,
                      overflowY: "auto",
                      paddingRight: 2,
                    }}
                  >
                    {p.children.map((c) => {
                      const checked =
                        !!sel && (sel.mode === "all" || sel.ids.has(c.id));
                      const knownChildren = p.children.map((x) => x.id);
                      return (
                        <li key={String(c.id)}>
                          <button
                            type="button"
                            onClick={() =>
                              onToggleChild(p.id, c.id, knownChildren)
                            }
                            {...(checked ? {} : hoverBg("rgba(244, 244, 245, 0.6)"))}
                            style={{
                              display: "flex",
                              width: "100%",
                              alignItems: "flex-start",
                              gap: 10,
                              borderRadius: 4,
                              padding: "4px 8px",
                              textAlign: "left",
                              fontSize: 12,
                              border: "none",
                              cursor: "pointer",
                              background: checked
                                ? "rgba(22, 119, 255, 0.1)"
                                : "transparent",
                              color: "inherit",
                            }}
                          >
                            <span style={{ paddingTop: 2 }}>
                              <CheckBox state={checked ? "on" : "off"} />
                            </span>
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div style={{ ...TRUNCATE, color: FG }}>
                                {c.title}
                              </div>
                              {c.subtitle && (
                                <div
                                  style={{
                                    ...TRUNCATE,
                                    fontSize: 10.5,
                                    color: MUTED_FG,
                                  }}
                                >
                                  {c.subtitle}
                                </div>
                              )}
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

// ─── proposal form (unchanged) ─────────────────────────────────────────

function ProposalForm({
  proposal,
  onChange,
  selectedKbs,
}: {
  proposal: BookProposal;
  onChange: (p: BookProposal) => void;
  selectedKbs: string[];
}) {
  const update = (patch: Partial<BookProposal>) =>
    onChange({ ...proposal, ...patch });
  const fieldLabel: CSSProperties = {
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: MUTED_FG,
  };
  return (
    <Row gutter={[12, 12]}>
      <Col span={24}>
        <label style={{ display: "block" }}>
          <span style={fieldLabel}>标题</span>
          <Input
            value={proposal.title}
            onChange={(e) => update({ title: e.target.value })}
            data-testid="book-proposal-title"
            style={{ marginTop: 4, fontSize: 14 }}
          />
        </label>
      </Col>
      <Col span={24}>
        <label style={{ display: "block" }}>
          <span style={fieldLabel}>描述</span>
          <TextArea
            value={proposal.description}
            onChange={(e) => update({ description: e.target.value })}
            rows={3}
            style={{ marginTop: 4, resize: "none", fontSize: 14 }}
          />
        </label>
      </Col>
      <Col xs={24} sm={12}>
        <label style={{ display: "block" }}>
          <span style={fieldLabel}>范围</span>
          <Input
            value={proposal.scope}
            onChange={(e) => update({ scope: e.target.value })}
            style={{ marginTop: 4, fontSize: 14 }}
          />
        </label>
      </Col>
      <Col xs={24} sm={12}>
        <label style={{ display: "block" }}>
          <span style={fieldLabel}>目标水平</span>
          <Input
            value={proposal.target_level}
            onChange={(e) => update({ target_level: e.target.value })}
            style={{ marginTop: 4, fontSize: 14 }}
          />
        </label>
      </Col>
      <Col xs={24} sm={12}>
        <label style={{ display: "block" }}>
          <span style={fieldLabel}>预计章节数</span>
          <Input
            type="number"
            min={2}
            max={14}
            value={proposal.estimated_chapters}
            onChange={(e) =>
              update({ estimated_chapters: Number(e.target.value) || 0 })
            }
            data-testid="book-proposal-est-chapters"
            style={{ marginTop: 4, fontSize: 14 }}
          />
        </label>
      </Col>
      <Col span={24}>
        <div style={{ display: "block" }}>
          <span style={fieldLabel}>使用的知识库</span>
          <div
            style={{
              marginTop: 6,
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
            }}
          >
            {selectedKbs.length === 0 ? (
              <span
                style={{ fontSize: 12, fontStyle: "italic", color: MUTED_FG }}
              >
                未选择知识库。本书将依赖通用知识生成。
              </span>
            ) : (
              selectedKbs.map((kb) => (
                <span
                  key={kb}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    borderRadius: 999,
                    border: `1px solid ${BORDER}`,
                    background: "rgba(244, 244, 245, 0.4)",
                    padding: "2px 10px",
                    fontSize: 11,
                    color: FG,
                  }}
                >
                  {kb}
                </span>
              ))
            )}
          </div>
        </div>
      </Col>
    </Row>
  );
}
