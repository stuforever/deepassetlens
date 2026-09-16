/**
 * 复刻自 DeepTutor 原仓 web/lib/space-items.ts（整件 1:1）。
 * 替换点：删除 "use client"；lucide（Bot/ClipboardList/History/NotebookPen/UserRound/Wand2）
 * → @ant-design/icons 语义就近（RobotOutlined/SnippetsOutlined/HistoryOutlined/
 * FormOutlined/UserOutlined/ThunderboltOutlined）；LucideIcon → ComponentType 泛型
 * （antd 图标组件类型）。/space/* href 为桌面空间路由字符串，按原样保留。
 */
import type { ComponentType } from "react";
import {
  RobotOutlined,
  SnippetsOutlined,
  HistoryOutlined,
  FormOutlined,
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
  icon: ComponentType<{ style?: React.CSSProperties; className?: string }>;
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
    icon: FormOutlined,
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
