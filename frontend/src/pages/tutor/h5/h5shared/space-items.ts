/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/lib/space-items.ts，75 行）。
 * 替换点：删除 "use client"；lucide-react → @ant-design/icons：
 * History→HistoryOutlined、Bot→RobotOutlined、NotebookPen→HighlightOutlined、
 * ClipboardList→SnippetsOutlined、UserRound→UserOutlined、Wand2→ThunderboltOutlined；
 * LucideIcon 类型 → ComponentType<{className?;style?}>（icon 仅被 ChatSpaceMenu
 * 以 <Icon/> 形式渲染）。SPACE_ITEMS 数据逐字未改。
 */
import type { ComponentType, CSSProperties } from "react";
import {
  HistoryOutlined,
  RobotOutlined,
  HighlightOutlined,
  SnippetsOutlined,
  UserOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

export type SpaceItemKey =
  | "chat_history"
  | "agents"
  | "notebooks"
  | "question_bank"
  | "personas"
  | "skills";

export type SpaceMemoryFile = "summary" | "profile";

export interface SpaceItem {
  key: SpaceItemKey;
  href: string;
  label: string;
  description: string;
  icon: ComponentType<{ className?: string; style?: CSSProperties }>;
}

export const SPACE_ITEMS: SpaceItem[] = [
  {
    key: "chat_history",
    href: "/space/chat-history",
    label: "Chat History",
    description: "Review and reopen previous conversations.",
    icon: HistoryOutlined,
  },
  {
    key: "agents",
    href: "/space/agents",
    label: "My Agents",
    description: "Chat with imported Claude Code and Codex agents.",
    icon: RobotOutlined,
  },
  {
    key: "notebooks",
    href: "/space/notebooks",
    label: "Notebooks",
    description:
      "Organize saved outputs from chat, research, Co-Writer, and more.",
    icon: HighlightOutlined,
  },
  {
    key: "question_bank",
    href: "/space/questions",
    label: "Question Bank",
    description: "Review and organize quiz questions across sessions.",
    icon: SnippetsOutlined,
  },
  {
    key: "personas",
    href: "/space/personas",
    label: "Personas",
    description: "Behavior presets you can apply per chat turn.",
    icon: UserOutlined,
  },
  {
    key: "skills",
    href: "/space/skills",
    label: "Skills",
    description: "Capability playbooks the model reads on demand.",
    icon: ThunderboltOutlined,
  },
];
