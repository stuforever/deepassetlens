// IA批5 lib 补件：1:1 移植自 DeepTutor web/lib/settings-nav.ts。
// 设置中心信息架构唯一源（六类目块/子中枢叶块/面包屑）。
// 替换点：lucide 图标 → @ant-design/icons（icon 以 <Icon style={{fontSize}}/> 调用——
// settings-nav 落盘侧同为 antd 图标，与 components/settings/SettingsHub 头注契约一致）；
// `tile` 为类名字符串（消费方 className={leaf.tile}）——tupu 无 tailwind，类定义由本模块
// 加载时注入一次 <style id="dsh-settings-nav-tile-styles">（shared.tsx 同款模式）。
// agent 六家 Glyph 复用仓内既有 1:1 件 pages/tutor/h5/h5shared/agent-icons（经
// components/agents/agent-icons 适配 re-export）。
import React from "react";
import {
  ApartmentOutlined,
  AppstoreOutlined,
  AudioOutlined,
  BgColorsOutlined,
  BlockOutlined,
  BookFilled,
  BulbOutlined,
  ControlOutlined,
  CustomerServiceOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  FileSearchOutlined,
  MessageOutlined,
  PaperClipOutlined,
  PartitionOutlined,
  PictureOutlined,
  ReadOutlined,
  RobotOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  VideoCameraOutlined,
} from "@ant-design/icons";

import {
  ClaudeGlyph,
  CodexGlyph,
  GeminiGlyph,
  KimiGlyph,
  MimoGlyph,
  OpencodeGlyph,
} from "../components/agents/agent-icons";
import type { ServiceName } from "../components/settings/SettingsContext";

/**
 * Settings information architecture.
 *
 * Two levels, deliberately unlike the flat Learning Space dashboard:
 *   • The hub (`/settings`) shows six category blocks + a resident Status
 *     module — nothing else.
 *   • Categories with several settings (Models, Chat) open a sub-hub page
 *     that lists their leaves as tiles; single-setting categories link
 *     straight to their leaf page.
 *
 * This module is the single source for the blocks, the sub-hub tiles, and the
 * breadcrumb trail rendered top-left on every page.
 */

export type Lang = { zh: string; en: string };

/** lucide LucideIcon 的 antd 等价：图标组件（size 以 style.fontSize 传入）。 */
export type NavIcon = React.ComponentType<{
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}>;

export interface SettingsLeaf {
  key: string;
  href: string;
  label: Lang;
  blurb: Lang;
  icon: NavIcon;
  /** Colored icon-tile accent for the sub-hub grid (full class strings). */
  tile: string;
  /** Model-service leaves carry a configured/not chip from the catalog. */
  service?: ServiceName;
  /** Hidden from non-admin users (the backend rejects them anyway). */
  adminOnly?: boolean;
}

export interface SettingsCategory {
  key: string;
  label: Lang;
  /** One-line descriptor shown on the hub block. */
  blurb: Lang;
  icon: NavIcon;
  /** Where clicking the block lands — a sub-hub or a leaf page. */
  href: string;
  /** Leaves listed on the sub-hub page (omitted for direct-leaf categories). */
  children?: SettingsLeaf[];
}

// tile 色彩类：源 tailwind `bg-<c>-500/10 text-<c>-600` 的 antd 时代等价——
// 类名保留源语义命名，定义由下方注入样式实现（底色 10% 透明 + 同色系文字）。
const TILE_CLASSES = `
.dsh-tile-violet{background:rgba(139,92,246,.1);color:#7c3aed}
.dsh-tile-emerald{background:rgba(16,185,129,.1);color:#059669}
.dsh-tile-amber{background:rgba(245,158,11,.1);color:#d97706}
.dsh-tile-rose{background:rgba(244,63,94,.1);color:#e11d48}
.dsh-tile-pink{background:rgba(236,72,153,.1);color:#db2777}
.dsh-tile-fuchsia{background:rgba(217,70,239,.1);color:#c026d3}
.dsh-tile-indigo{background:rgba(99,102,241,.1);color:#4f46e5}
.dsh-tile-sky{background:rgba(14,165,233,.1);color:#0284c7}
.dsh-tile-orange{background:rgba(249,115,22,.1);color:#ea580c}
.dsh-tile-lime{background:rgba(132,204,22,.1);color:#65a30d}
.dsh-tile-teal{background:rgba(20,184,166,.1);color:#0d9488}
.dsh-tile-blue{background:rgba(59,130,246,.1);color:#2563eb}
.dsh-tile-zinc{background:rgba(113,113,122,.1);color:#3f3f46}
.dsh-tile-neutral{background:rgba(163,163,163,.12);color:#525252}
`;
if (typeof document !== "undefined" && !document.getElementById("dsh-settings-nav-tile-styles")) {
  const style = document.createElement("style");
  style.id = "dsh-settings-nav-tile-styles";
  style.textContent = TILE_CLASSES;
  document.head.appendChild(style);
}

const MODEL_CHILDREN: SettingsLeaf[] = [
  {
    key: "llm",
    href: "/settings/llm",
    label: { zh: "LLM", en: "LLM" },
    blurb: {
      zh: "语言模型供应商与当前档位。",
      en: "Language model providers and active profile.",
    },
    icon: ThunderboltOutlined,
    tile: "dsh-tile-violet",
    service: "llm",
  },
  {
    key: "embedding",
    href: "/settings/embedding",
    label: { zh: "嵌入模型", en: "Embedding" },
    blurb: {
      zh: "向量模型供应商与维度。",
      en: "Embedding model providers and dimensions.",
    },
    icon: DatabaseOutlined,
    tile: "dsh-tile-emerald",
    service: "embedding",
  },
  {
    key: "search",
    href: "/settings/search",
    label: { zh: "搜索", en: "Search" },
    blurb: { zh: "联网搜索供应商。", en: "Web search providers." },
    icon: SearchOutlined,
    tile: "dsh-tile-amber",
    service: "search",
  },
  {
    key: "tts",
    href: "/settings/tts",
    label: { zh: "语音合成", en: "Text-to-Speech" },
    blurb: {
      zh: "朗读助手回复的 TTS 供应商。",
      en: "Text-to-speech for reading replies aloud.",
    },
    icon: AudioOutlined,
    tile: "dsh-tile-rose",
    service: "tts",
  },
  {
    key: "stt",
    href: "/settings/stt",
    label: { zh: "语音识别", en: "Speech-to-Text" },
    blurb: {
      zh: "转写麦克风录音的 STT 供应商。",
      en: "Speech-to-text for the composer microphone.",
    },
    icon: CustomerServiceOutlined,
    tile: "dsh-tile-pink",
    service: "stt",
  },
  {
    key: "imagegen",
    href: "/settings/image",
    label: { zh: "文生图", en: "Image Generation" },
    blurb: {
      zh: "chat imagegen 工具使用的文生图模型。",
      en: "Text-to-image model for the chat imagegen tool.",
    },
    icon: PictureOutlined,
    tile: "dsh-tile-fuchsia",
    service: "imagegen",
  },
  {
    key: "videogen",
    href: "/settings/video",
    label: { zh: "文生视频", en: "Video Generation" },
    blurb: {
      zh: "chat videogen 工具使用的文生视频模型。",
      en: "Text-to-video model for the chat videogen tool.",
    },
    icon: VideoCameraOutlined,
    tile: "dsh-tile-indigo",
    service: "videogen",
  },
];

const CURRICULUM_CHILDREN: SettingsLeaf[] = [
  {
    key: "curriculum-textbooks",
    href: "/settings/curriculum/textbooks",
    label: { zh: "课本管理", en: "Textbooks" },
    blurb: {
      zh: "教材的增删改与 PDF 导入（拆页成图）。",
      en: "Manage textbooks and import PDFs into page images.",
    },
    icon: BookFilled,
    tile: "dsh-tile-sky",
  },
  {
    key: "curriculum-chapters",
    href: "/settings/curriculum/chapters",
    label: { zh: "章节管理", en: "Chapters" },
    blurb: {
      zh: "教材章节体系（权威源，自主学习章节来源于此）与知识点关联。",
      en: "Authoritative chapter tree, also driving self-learning.",
    },
    icon: PartitionOutlined,
    tile: "dsh-tile-orange",
  },
  {
    key: "curriculum-knowledge-points",
    href: "/settings/curriculum/knowledge-points",
    label: { zh: "知识点管理", en: "Knowledge Points" },
    blurb: {
      zh: "按学科/学段管理知识树：总结、讲解、实例、公式推导与关系图谱。",
      en: "Knowledge tree with summaries, explanations, examples, formulas and relations.",
    },
    icon: BulbOutlined,
    tile: "dsh-tile-amber",
  },
];

const CHAT_CHILDREN: SettingsLeaf[] = [
  {
    key: "tools",
    href: "/settings/tools",
    label: { zh: "工具", en: "Tools" },
    blurb: {
      zh: "对话智能体可调用的内置工具。",
      en: "Built-in tools the chat agent can invoke.",
    },
    icon: ToolOutlined,
    tile: "dsh-tile-orange",
  },
  {
    key: "capabilities",
    href: "/settings/capabilities",
    label: { zh: "能力", en: "Capabilities" },
    blurb: {
      zh: "各能力的 LLM 参数与运行时旋钮。",
      en: "Per-capability LLM parameters and runtime knobs.",
    },
    icon: ControlOutlined,
    tile: "dsh-tile-lime",
  },
  {
    key: "attachments",
    href: "/settings/attachments",
    label: { zh: "附件", en: "Attachments" },
    blurb: {
      zh: "聊天附件的大小上限与文本提取预算。",
      en: "Upload caps and extraction budgets for chat attachments.",
    },
    icon: PaperClipOutlined,
    tile: "dsh-tile-teal",
    adminOnly: true,
  },
];

const AGENT_CHILDREN: SettingsLeaf[] = [
  {
    key: "agent-claude-code",
    href: "/settings/agents/claude-code",
    label: { zh: "Claude Code", en: "Claude Code" },
    blurb: {
      zh: "DeepTutor 调用本机 Claude Code 时的模型、推理强度与运行参数。",
      en: "Model, reasoning effort, and run params for the local Claude Code.",
    },
    // Brand glyph shares the lucide call signature (size/className).
    icon: ClaudeGlyph as unknown as NavIcon,
    tile: "dsh-tile-orange",
    adminOnly: true,
  },
  {
    key: "agent-codex",
    href: "/settings/agents/codex",
    label: { zh: "Codex", en: "Codex" },
    blurb: {
      zh: "DeepTutor 调用本机 Codex 时的模型、推理强度与运行参数。",
      en: "Model, reasoning effort, and run params for the local Codex.",
    },
    icon: CodexGlyph as unknown as NavIcon,
    tile: "dsh-tile-blue",
    adminOnly: true,
  },
  {
    key: "agent-gemini",
    href: "/settings/agents/gemini",
    label: { zh: "Gemini CLI", en: "Gemini CLI" },
    blurb: {
      zh: "DeepTutor 调用本机 Gemini CLI 时的模型与运行参数。",
      en: "Model and run params for the local Gemini CLI.",
    },
    icon: GeminiGlyph as unknown as NavIcon,
    tile: "dsh-tile-sky",
    adminOnly: true,
  },
  {
    key: "agent-kimi",
    href: "/settings/agents/kimi",
    label: { zh: "Kimi CLI", en: "Kimi CLI" },
    blurb: {
      zh: "DeepTutor 调用本机 Kimi CLI 时的模型与运行参数。",
      en: "Model and run params for the local Kimi CLI.",
    },
    icon: KimiGlyph as unknown as NavIcon,
    tile: "dsh-tile-zinc",
    adminOnly: true,
  },
  {
    key: "agent-opencode",
    href: "/settings/agents/opencode",
    label: { zh: "opencode", en: "opencode" },
    blurb: {
      zh: "DeepTutor 调用本机 opencode 时的模型、推理强度与运行参数。",
      en: "Model, reasoning effort, and run params for the local opencode.",
    },
    icon: OpencodeGlyph as unknown as NavIcon,
    tile: "dsh-tile-neutral",
    adminOnly: true,
  },
  {
    key: "agent-mimo",
    href: "/settings/agents/mimo",
    label: { zh: "MiMo Code", en: "MiMo Code" },
    blurb: {
      zh: "DeepTutor 调用本机 MiMo Code 时的模型、推理强度与运行参数。",
      en: "Model, reasoning effort, and run params for the local MiMo Code.",
    },
    icon: MimoGlyph as unknown as NavIcon,
    tile: "dsh-tile-orange",
    adminOnly: true,
  },
];

export const SETTINGS_CATEGORIES: SettingsCategory[] = [
  {
    key: "appearance",
    label: { zh: "外观", en: "Appearance" },
    blurb: { zh: "视觉主题与界面语言", en: "Theme and interface language" },
    icon: BgColorsOutlined,
    href: "/settings/appearance",
  },
  {
    key: "network",
    label: { zh: "网络", en: "Network" },
    blurb: {
      zh: "端口、浏览器 API 地址与 CORS",
      en: "Ports, browser API base, and CORS",
    },
    icon: ApartmentOutlined,
    href: "/settings/network",
  },
  {
    key: "models",
    label: { zh: "模型", en: "Models" },
    blurb: {
      zh: "语言、向量、搜索、语音与生成模型",
      en: "Language, embedding, search, voice, and generation models",
    },
    icon: AppstoreOutlined,
    href: "/settings/models",
    children: MODEL_CHILDREN,
  },
  {
    key: "knowledge",
    label: { zh: "知识库", en: "Knowledge Base" },
    blurb: { zh: "文档解析引擎", en: "Document parsing engine" },
    icon: ReadOutlined,
    href: "/settings/document-parsing",
  },
  {
    key: "curriculum",
    label: { zh: "设置管理", en: "Curriculum" },
    blurb: {
      zh: "课本、章节与知识点：课程体系的权威管理入口。",
      en: "Textbooks, chapters and knowledge points.",
    },
    icon: BlockOutlined,
    href: "/settings/curriculum",
    children: CURRICULUM_CHILDREN,
  },
  {
    key: "chat",
    label: { zh: "聊天", en: "Chat" },
    blurb: {
      zh: "工具、能力与附件",
      en: "Tools, capabilities, and attachments",
    },
    icon: MessageOutlined,
    href: "/settings/chat",
    children: CHAT_CHILDREN,
  },
  {
    key: "agents",
    label: { zh: "伙伴和智能体", en: "Partners & Agents" },
    blurb: {
      zh: "配置可在对话中调用的子智能体",
      en: "Configure the subagents you can call on in chat",
    },
    icon: RobotOutlined,
    href: "/settings/agents",
    children: AGENT_CHILDREN,
  },
  {
    key: "memory",
    label: { zh: "记忆", en: "Memory" },
    blurb: {
      zh: "分块、预算、去重与引用策略",
      en: "Chunking, budget, dedup, and reference policies",
    },
    icon: DeploymentUnitOutlined,
    href: "/settings/memory",
  },
];

// 兼容说明：Palette→BgColorsOutlined、Boxes→AppstoreOutlined、Bot→RobotOutlined、
// Mic→CustomerServiceOutlined、ListTree→PartitionOutlined、Layers→BlockOutlined、
// Library→ReadOutlined——最近语义对位（文件头已登记）。

export const SETTINGS_HUB_HREF = "/settings";
const HUB_LABEL: Lang = { zh: "设置", en: "Settings" };

/** Routes that are pure navigation (hub + sub-hubs) — no Save/Apply toolbar. */
const NAV_ONLY_ROUTES = new Set<string>([
  SETTINGS_HUB_HREF,
  ...SETTINGS_CATEGORIES.filter((c) => c.children).map((c) => c.href),
  // 课程管理是 CRUD 页（自带保存按钮），不显示 Settings 工具栏
  ...CURRICULUM_CHILDREN.map((l) => l.href),
]);

export function isNavOnlyRoute(pathname: string): boolean {
  return NAV_ONLY_ROUTES.has(pathname);
}

// The on-disk file (under data/user/settings/) each leaf module persists to.
// Surfaced in the toolbar status line so every page says where its parameters
// live, without duplicating the string on each page.
const STORAGE_PATHS: Record<string, string> = {
  "/settings/appearance": "data/user/settings/interface.json",
  "/settings/network": "data/user/settings/system.json",
  "/settings/llm": "data/user/settings/model_catalog.json",
  "/settings/embedding": "data/user/settings/model_catalog.json",
  "/settings/search": "data/user/settings/model_catalog.json",
  "/settings/tts": "data/user/settings/model_catalog.json",
  "/settings/stt": "data/user/settings/model_catalog.json",
  "/settings/image": "data/user/settings/model_catalog.json",
  "/settings/video": "data/user/settings/model_catalog.json",
  "/settings/document-parsing": "data/user/settings/document_parsing.json",
  "/settings/curriculum/textbooks": "data/user/workspace/curriculum/textbooks.json",
  "/settings/curriculum/chapters": "data/user/workspace/curriculum/chapters.json",
  "/settings/curriculum/knowledge-points": "data/user/workspace/curriculum/knowledge_points.json",
  "/settings/tools": "data/user/settings/interface.json",
  "/settings/attachments": "data/user/settings/system.json",
  "/settings/capabilities": "data/user/settings/main.yaml · agents.yaml",
  "/settings/memory": "data/user/settings/main.yaml",
  "/settings/agents/claude-code": "data/user/settings/subagent.json",
  "/settings/agents/codex": "data/user/settings/subagent.json",
  "/settings/agents/gemini": "data/user/settings/subagent.json",
  "/settings/agents/kimi": "data/user/settings/subagent.json",
  "/settings/agents/opencode": "data/user/settings/subagent.json",
  "/settings/agents/mimo": "data/user/settings/subagent.json",
};

export function storagePathFor(pathname: string): string | null {
  return STORAGE_PATHS[pathname] ?? null;
}

export interface Crumb {
  label: Lang;
  /** Omitted on the current (last) crumb. */
  href?: string;
}

/**
 * The breadcrumb trail for a settings route, e.g.
 *   /settings/llm  →  设置 / 模型 / LLM
 *   /settings/network  →  设置 / 网络
 * Returns just [设置] for the hub itself.
 */
export function breadcrumbFor(pathname: string): Crumb[] {
  const root: Crumb = { label: HUB_LABEL, href: SETTINGS_HUB_HREF };
  if (pathname === SETTINGS_HUB_HREF) return [{ label: HUB_LABEL }];

  // Direct-leaf or sub-hub category landed on its own href.
  const category = SETTINGS_CATEGORIES.find((c) => c.href === pathname);
  if (category) return [root, { label: category.label }];

  // A leaf inside a sub-hub category.
  for (const c of SETTINGS_CATEGORIES) {
    const leaf = c.children?.find((l) => l.href === pathname);
    if (leaf) {
      return [root, { label: c.label, href: c.href }, { label: leaf.label }];
    }
  }

  // Unknown sub-route (e.g. a legacy redirect target rendered directly).
  return [root];
}
