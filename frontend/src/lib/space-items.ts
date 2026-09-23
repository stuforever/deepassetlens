"use client";

import {
  ClipboardList,
  History,
  NotebookPen,
  type LucideIcon,
} from "lucide-react";

// R5批⑩：收敛键表——agents/personas/skills 三键从未被任何消费方命中
// （桌面 ChatSpaceMenu ITEM_ORDER=attach/knowledge/chat_history/my_agents/books/
// notebooks/question_bank/persona/memory，my_agents/persona 为消费方内联条目）；
// h5 域用 h5shared/spaceItems.ts 自有副本，与本件无关。
export type SpaceItemKey =
  | "chat_history"
  | "notebooks"
  | "question_bank";

export type SpaceMemoryFile = "summary" | "profile";

export interface SpaceItem {
  key: SpaceItemKey;
  href: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

export const SPACE_ITEMS: SpaceItem[] = [
  {
    key: "chat_history",
    href: "/space/chat-history",
    label: "Chat History",
    description: "Review and reopen previous conversations.",
    icon: History,
  },
  {
    key: "notebooks",
    href: "/space/notebooks",
    label: "Notebooks",
    description:
      "Organize saved outputs from chat, research, Co-Writer, and more.",
    icon: NotebookPen,
  },
  {
    key: "question_bank",
    href: "/space/questions",
    label: "Question Bank",
    description: "Review and organize quiz questions across sessions.",
    icon: ClipboardList,
  },
];
