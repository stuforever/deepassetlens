/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/space/ChatSpaceMenu.tsx，294 行）。
 * 替换点：删除 "use client"；lucide BookOpen/Bot/ChevronRight/Database/Paperclip/
 * UserRound→BookOutlined/RobotOutlined/RightOutlined/DatabaseOutlined/
 * PaperClipOutlined/UserOutlined；SPACE_ITEMS→./space-items、setPickerOrigin→
 * ./picker-origin；Tailwind→内联样式（token 见 dtStyle.ts）；hover→
 * onMouseEnter/Leave 直写 style（mention 变体的 activeIdx 高亮为状态）；t() 译文：
 * 命中 zh/app.json 直出（Attach files→上传附件、Knowledge→知识库、My Agents→
 * 我的智能体、Books→书籍、Chat History→聊天历史、Notebooks→笔记本、
 * Question Bank→题库、Skills→技能、Reference space→引用空间、部分描述句命中），
 * 未命中键按 i18next 回退行为直出原 key。ITEM_ORDER/键盘导航/计数徽标逐字未改。
 */
import { Fragment, memo, useEffect, useRef, useState, type ComponentType, type CSSProperties } from "react";
import {
  BookOutlined,
  RobotOutlined,
  RightOutlined,
  DatabaseOutlined,
  PaperClipOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { SPACE_ITEMS } from "./space-items";
import { setPickerOrigin } from "./picker-origin";
import { DT, ellipsis } from "./dtStyle";

type SelectableSpaceKey =
  | "attach"
  | "knowledge"
  | "chat_history"
  | "my_agents"
  | "books"
  | "notebooks"
  | "question_bank"
  | "persona"
  | "memory";

export interface ChatSpaceSelectionCounts {
  attachments: number;
  knowledge: number;
  chatHistory: number;
  myAgents: number;
  books: number;
  notebooks: number;
  questionBank: number;
  persona: number;
  memory: number;
}

interface ChatSpaceMenuProps {
  variant: "toolbar" | "mention";
  selectedCounts: ChatSpaceSelectionCounts;
  /** Hide the Knowledge entry when no knowledge bases are configured. */
  knowledgeAvailable?: boolean;
  /**
   * Hide the Persona entry. The main chat sets this to false — its
   * persona lives in the standalone toolbar selector (and `/persona`),
   * not in this menu. The quiz follow-up keeps the entry: this menu is
   * its only persona entry point.
   */
  personaAvailable?: boolean;
  /** Hide the My Agents entry (e.g. the quiz follow-up surface). */
  agentsAvailable?: boolean;
  onSelectItem: (key: SelectableSpaceKey) => void;
}

const ITEM_ORDER: SelectableSpaceKey[] = [
  "attach",
  "knowledge",
  "chat_history",
  "my_agents",
  "books",
  "notebooks",
  "question_bank",
  "persona",
  "memory",
];

// zh/app.json 原译文（t() 中文直出替换表；未命中键按 i18next 回退直出原 key）。
const I18N_ZH: Record<string, string> = {
  "Attach files": "上传附件",
  "Knowledge": "知识库",
  "My Agents": "我的智能体",
  "Books": "书籍",
  "Chat History": "聊天历史",
  "Notebooks": "笔记本",
  "Question Bank": "题库",
  "Skills": "技能",
  "Reference space": "引用空间",
  "Reference imported Claude Code / Codex conversations.":
    "引用导入的 Claude Code / Codex 对话。",
  "Review and organize quiz questions across sessions.":
    "跨会话回顾和整理测验题目。",
};

function zh(text: string): string {
  return I18N_ZH[text] ?? text;
}

function countFor(
  key: SelectableSpaceKey,
  counts: ChatSpaceSelectionCounts,
): number {
  switch (key) {
    case "attach":
      return counts.attachments;
    case "knowledge":
      return counts.knowledge;
    case "chat_history":
      return counts.chatHistory;
    case "my_agents":
      return counts.myAgents;
    case "books":
      return counts.books;
    case "notebooks":
      return counts.notebooks;
    case "question_bank":
      return counts.questionBank;
    case "persona":
      return counts.persona;
    case "memory":
      return counts.memory;
    default:
      return 0;
  }
}

export default memo(function ChatSpaceMenu({
  variant,
  selectedCounts,
  knowledgeAvailable = true,
  personaAvailable = true,
  agentsAvailable = true,
  onSelectItem,
}: ChatSpaceMenuProps) {
  const compact = variant === "toolbar";
  const isMention = variant === "mention";

  // Render the items in a fixed, hand-tuned order so the menu always reads
  // the same regardless of how SPACE_ITEMS may be reordered for navigation.
  const items = ITEM_ORDER.filter((key) => {
    if (key === "knowledge") return knowledgeAvailable;
    if (key === "persona") return personaAvailable;
    if (key === "my_agents") return agentsAvailable;
    return true;
  })
    .map((key) => {
      // The first two entries are composer-only concepts (not Space pages),
      // so they are defined here rather than in SPACE_ITEMS.
      if (key === "attach") {
        return {
          key,
          label: "Attach files",
          description: "Upload images, Office docs, code & text.",
          icon: PaperClipOutlined as ComponentType<{ className?: string; style?: CSSProperties }>,
        };
      }
      if (key === "knowledge") {
        return {
          key,
          label: "Knowledge",
          description: "Search the selected knowledge bases.",
          icon: DatabaseOutlined as ComponentType<{ className?: string; style?: CSSProperties }>,
        };
      }
      if (key === "my_agents") {
        return {
          key,
          label: "My Agents",
          description: "Reference imported Claude Code / Codex conversations.",
          icon: RobotOutlined as ComponentType<{ className?: string; style?: CSSProperties }>,
        };
      }
      if (key === "books") {
        return {
          key,
          label: "Books",
          description: "Reference generated book chapters in chat.",
          icon: BookOutlined as ComponentType<{ className?: string; style?: CSSProperties }>,
        };
      }
      if (key === "persona") {
        return {
          key,
          label: "Persona",
          description: "Apply a behavior persona for this turn.",
          icon: UserOutlined as ComponentType<{ className?: string; style?: CSSProperties }>,
        };
      }
      return SPACE_ITEMS.find((it) => it.key === key)!;
    })
    .filter(Boolean);

  // Active row index for keyboard navigation. Only meaningful in the
  // mention variant — the toolbar variant is mouse/click driven.
  const [activeIdx, setActiveIdx] = useState(0);
  // The keydown handler closes over `activeIdx`/`items`/`onSelectItem`;
  // stash them in refs so the document-level listener identity stays
  // stable and we don't re-attach it on every render. Refs are synced
  // in an effect (not during render) to satisfy `react-hooks/refs`.
  const activeIdxRef = useRef(activeIdx);
  const itemsRef = useRef(items);
  const onSelectItemRef = useRef(onSelectItem);
  useEffect(() => {
    activeIdxRef.current = activeIdx;
  }, [activeIdx]);
  useEffect(() => {
    itemsRef.current = items;
  }, [items]);
  useEffect(() => {
    onSelectItemRef.current = onSelectItem;
  }, [onSelectItem]);

  // Reset to the top whenever the menu first mounts (i.e. user typed `@`
  // and the popup appeared). The parent unmounts/remounts this component
  // on each open, so a fresh `useState(0)` initial value already gives us
  // the right behavior — no extra effect needed.

  // Attach a document-level keydown so Arrow/Enter while the textarea
  // still has focus drive the menu. The textarea's own handleKeyDown
  // continues to handle Escape and submit.
  useEffect(() => {
    if (!isMention) return;
    const handler = (e: KeyboardEvent) => {
      const list = itemsRef.current;
      if (list.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => (i + 1) % list.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => (i - 1 + list.length) % list.length);
      } else if (e.key === "Enter") {
        const item = list[activeIdxRef.current];
        if (!item) return;
        e.preventDefault();
        onSelectItemRef.current(item.key as SelectableSpaceKey);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isMention]);

  return (
    <div
      role={isMention ? "listbox" : undefined}
      aria-label={isMention ? "引用空间" : undefined}
      style={{
        borderRadius: 12,
        border: `1px solid ${DT.border}`,
        background: DT.popover,
        boxShadow:
          "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
        width: compact ? 280 : 256,
        padding: compact ? "6px 0" : 8,
      }}
    >
      <div style={compact ? undefined : { display: "flex", flexDirection: "column", rowGap: 4 }}>
        {items.map(({ key, label, description, icon: Icon }, idx) => {
          const count = countFor(key as SelectableSpaceKey, selectedCounts);
          const isActive = isMention && idx === activeIdx;
          // Two kinds of rows, Claude-style: "attach" is a direct action
          // (opens the file dialog), everything after it opens a
          // second-level picker — those get a trailing chevron, and a
          // divider separates the two groups.
          const opensPicker = key !== "attach";
          const baseBg = isActive ? DT.mutedAlpha(0.6) : "transparent";
          return (
            <Fragment key={key}>
              {idx === 1 && items[0]?.key === "attach" && (
                <div
                  style={{
                    borderTop: `1px solid ${DT.borderAlpha(0.6)}`,
                    margin: compact ? "4px 12px" : "4px",
                  }}
                />
              )}
              <button
                type="button"
                role={isMention ? "option" : undefined}
                aria-selected={isMention ? isActive : undefined}
                onMouseEnter={(e) => {
                  if (isMention) setActiveIdx(idx);
                  else e.currentTarget.style.background = DT.mutedAlpha(0.4);
                }}
                onMouseLeave={(e) => {
                  if (!isMention) e.currentTarget.style.background = baseBg;
                }}
                onClick={(e) => {
                  // Record the row's rect so the fullscreen picker can expand
                  // outward from exactly this clickable box.
                  setPickerOrigin(e.currentTarget.getBoundingClientRect());
                  onSelectItem(key as SelectableSpaceKey);
                }}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  gap: 10,
                  textAlign: "left",
                  border: "none",
                  cursor: "pointer",
                  background: baseBg,
                  borderRadius: compact ? 0 : 12,
                  padding: compact ? "8px 14px" : "10px 12px",
                  fontSize: 13,
                  font: "inherit",
                  ...(compact ? {} : {}),
                }}
              >
                <Icon
                  style={{
                    fontSize: 15,
                    flexShrink: 0,
                    color: DT.mutedForeground,
                  }}
                />
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{ display: "block", ...ellipsis, fontWeight: 500, color: DT.foreground }}>
                    {zh(label)}
                  </span>
                  {!compact && (
                    <span style={{ display: "block", marginTop: 2, ...ellipsis, fontSize: 11, color: DT.mutedForeground }}>
                      {zh(description)}
                    </span>
                  )}
                </span>
                {count > 0 && (
                  <span
                    style={{
                      flexShrink: 0,
                      borderRadius: 999,
                      background: DT.primaryAlpha(0.1),
                      padding: "1px 6px",
                      fontSize: 9,
                      fontWeight: 600,
                      color: DT.primary,
                    }}
                  >
                    {count}
                  </span>
                )}
                {opensPicker && (
                  <RightOutlined
                    style={{
                      fontSize: 14,
                      flexShrink: 0,
                      color: DT.mutedForegroundAlpha(0.55),
                    }}
                  />
                )}
              </button>
            </Fragment>
          );
        })}
      </div>
    </div>
  );
});
