/**
 * ── 复刻来源与替换点（tupu antd 复刻）─────────────────────────────────
 * 源文件：DeepTutor web/app/(workspace)/book/components/PageOutlineNav.tsx
 * 目标：frontend/src/pages/tutor/admin/PageOutlineNav.tsx
 * 悬浮大纲导航（阅读进度高亮 + 点击跳转 + 折叠手柄），布局/交互/文案 1:1。
 * 替换点：
 * - "use client" 已删除；
 * - react-i18next useTranslation → 中文直出：已在 zh/app.json 查到
 *   "On this page"→本页内容、"Hide outline"→隐藏目录、"Show outline"→显示目录；
 *   块类型标签沿用 zh/app.json 现有 key（text→文本、flash_cards→闪卡、
 *   deep_dive→深入学习、concept_graph→概念图 等）；
 * - lucide-react 图标 → @ant-design/icons 语义就近：
 *   AlertCircle→ExclamationCircleOutlined、AlignLeft→AlignLeftOutlined、
 *   BookOpen→ReadOutlined、ChevronRight→RightOutlined、Code2→CodeOutlined、
 *   FileText→FileTextOutlined、Film→VideoCameraOutlined、Image→PictureOutlined、
 *   Layers→AppstoreOutlined、ListChecks→CheckSquareOutlined、
 *   Loader2→LoadingOutlined(spin)、MessageCircle→MessageOutlined、
 *   MousePointerClick→SelectOutlined、Sparkles→ThunderboltOutlined、
 *   Sticker→TagOutlined；h-3.5 w-3.5 → fontSize:14，h-3 w-3 → 12；
 * - "@/lib/book-types" → "./book-types"；
 * - Tailwind → 最小内联样式：border→#e4e4e7、muted-foreground→#6b7280、
 *   foreground→rgba(0,0,0,0.88)、primary→#1677ff、primary/10→rgba(22,119,255,0.1)、
 *   emerald-500→#10b981、amber-400→#fbbf24、rose-500→#f43f5e、rounded-md→6、xl→12。
 * - 保留差异：Tailwind 的 hover:*／group-hover:*／animate-pulse 为 CSS 伪类/动画，
 *   内联样式无法表达，已省略（静态外观与原仓一致）。
 * 导出形式（default PageOutlineNav + PageOutlineNavProps）与 props 契约不变。
 * ─────────────────────────────────────────────────────────────────────
 */

import { useEffect, useMemo, useState } from "react";
import type { ComponentType, CSSProperties } from "react";
import {
  AlignLeftOutlined,
  AppstoreOutlined,
  CheckSquareOutlined,
  CodeOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  LoadingOutlined,
  MessageOutlined,
  PictureOutlined,
  ReadOutlined,
  RightOutlined,
  SelectOutlined,
  TagOutlined,
  ThunderboltOutlined,
  VideoCameraOutlined,
} from "@ant-design/icons";

import type { Block, BlockType, BlockStatus } from "./book-types";

type IconComponent = ComponentType<{ style?: CSSProperties }>;

const TYPE_ICON: Record<BlockType, IconComponent> = {
  text: AlignLeftOutlined,
  section: ReadOutlined,
  callout: ThunderboltOutlined,
  quiz: CheckSquareOutlined,
  user_note: FileTextOutlined,
  figure: PictureOutlined,
  interactive: SelectOutlined,
  animation: VideoCameraOutlined,
  code: CodeOutlined,
  timeline: AppstoreOutlined,
  flash_cards: TagOutlined,
  deep_dive: MessageOutlined,
  concept_graph: AppstoreOutlined,
};

// 原 TYPE_LABEL_EN + t() 直出：译文取自 zh/app.json 对应 key（Flash cards /
// Deep dive / Concept graph 三项查无独立 key，沿用 flash_cards/deep_dive/
// concept_graph 的既有译文）。
const TYPE_LABEL: Record<BlockType, string> = {
  text: "文本",
  section: "章节",
  callout: "提示",
  quiz: "测验",
  user_note: "笔记",
  figure: "图示",
  interactive: "交互",
  animation: "动画",
  code: "代码",
  timeline: "时间线",
  flash_cards: "闪卡",
  deep_dive: "深入学习",
  concept_graph: "概念图",
};

function shortLabel(block: Block, fallback: string): string {
  const title = (block.title || "").trim();
  if (title) return title;
  const params = (block.params || {}) as Record<string, unknown>;
  const focus = typeof params.focus === "string" ? params.focus.trim() : "";
  if (focus) return focus;
  const role = typeof params.role === "string" ? params.role.trim() : "";
  if (role) return `${fallback} · ${role}`;
  const variant =
    typeof params.variant === "string" ? params.variant.trim() : "";
  if (variant) return `${fallback} · ${variant}`;
  return fallback;
}

// 原 statusDotClass（bg-emerald-500 / bg-amber-400 animate-pulse / …）→ 圆点颜色。
function statusDotColor(status: BlockStatus): string {
  switch (status) {
    case "ready":
      return "#10b981"; // emerald-500
    case "generating":
      return "#fbbf24"; // amber-400（原带 animate-pulse，内联样式省略动画）
    case "pending":
      return "rgba(107,114,128,0.4)";
    case "error":
      return "#f43f5e"; // rose-500
    case "hidden":
      return "rgba(107,114,128,0.2)";
    default:
      return "rgba(107,114,128,0.4)";
  }
}

export interface PageOutlineNavProps {
  blocks: Block[];
  scrollContainer?: HTMLElement | null;
  language?: string;
}

export default function PageOutlineNav({
  blocks,
  scrollContainer,
  language: _language,
}: PageOutlineNavProps) {
  const headerText = "本页内容"; // t("On this page")
  const collapseTip = "隐藏目录"; // t("Hide outline")
  const expandTip = "显示目录"; // t("Show outline")

  // Default: expanded; PageReader keys this component by page id.
  const [collapsed, setCollapsed] = useState(false);

  // Track which block is currently in view for active highlight.
  const [activeId, setActiveId] = useState<string | null>(null);
  const visibleBlocks = useMemo(
    () => blocks.filter((b) => b.status !== "hidden"),
    [blocks],
  );

  useEffect(() => {
    if (!scrollContainer || visibleBlocks.length === 0) return;
    const ids = visibleBlocks.map((b) => `block-${b.id}`);
    const elements = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => !!el);
    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Pick the entry closest to the top of the viewport that is intersecting.
        const intersecting = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (intersecting.length > 0) {
          const id = intersecting[0].target.id.replace(/^block-/, "");
          setActiveId(id);
        }
      },
      {
        root: scrollContainer,
        rootMargin: "-20% 0px -65% 0px",
        threshold: 0,
      },
    );
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [scrollContainer, visibleBlocks]);

  const handleJump = (blockId: string) => {
    const el = document.getElementById(`block-${blockId}`);
    if (!el) return;
    setActiveId(blockId);
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (visibleBlocks.length === 0) return null;

  // Smooth easing tuned to feel natural — same curve framer-motion uses for
  // its `easeOut` token, just expressed as a CSS bezier.
  const EASE = "cubic-bezier(0.22, 1, 0.36, 1)";

  return (
    <div
      style={{
        pointerEvents: "none",
        position: "absolute",
        right: 0,
        top: "50%",
        zIndex: 20,
        transform: "translateY(-50%)",
        transition: `transform 320ms ${EASE}`,
      }}
    >
      {/* Single morphing card. Width / border-radius / x-translate transition
          between slim-handle and full-nav, while the inner nav drives the
          card's height naturally via max-height (so it never balloons past
          its own content). */}
      <div
        style={{
          pointerEvents: "auto",
          position: "relative",
          overflow: "hidden",
          border: "1px solid #e4e4e7",
          borderRight: collapsed ? "none" : "1px solid #e4e4e7",
          background: "rgba(255,255,255,0.85)",
          boxShadow:
            "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)",
          backdropFilter: "blur(8px)",
          width: collapsed ? 24 : 224, // w-6 / w-56
          borderRadius: collapsed ? "6px 0 0 6px" : 12, // rounded-l-md / rounded-xl
          transition: [
            `width 320ms ${EASE}`,
            `border-radius 320ms ${EASE}`,
            `transform 320ms ${EASE}`,
            `box-shadow 200ms ease-out`,
          ].join(", "),
          transform: collapsed ? "translateX(0)" : "translateX(-12px)",
        }}
      >
        {/* ── Expanded content: full outline list. Stays in flow so its
            height drives the parent card; collapses to 64px (matches
            handle height) via max-height when hidden. The fixed inner
            width keeps content laid out during the width transition; the
            parent overflow:hidden clips it cleanly. */}
        <nav
          aria-label={headerText}
          aria-hidden={collapsed}
          style={{
            display: "flex",
            width: 224,
            flexDirection: "column",
            fontSize: "12.5px",
            pointerEvents: collapsed ? "none" : "auto",
            maxHeight: collapsed ? "64px" : "min(70vh, 520px)",
            opacity: collapsed ? 0 : 1,
            transform: collapsed ? "translateX(8px)" : "translateX(0)",
            transition: collapsed
              ? `max-height 320ms ${EASE}, opacity 140ms ease-out, transform 220ms ${EASE}`
              : `max-height 320ms ${EASE}, opacity 220ms ease-out 100ms, transform 320ms ${EASE} 60ms`,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 8,
              borderBottom: "1px solid #e4e4e7",
              padding: "8px 12px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                fontWeight: 500,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "#6b7280",
              }}
            >
              <AppstoreOutlined style={{ fontSize: 12 }} />
              <span>{headerText}</span>
            </div>
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              title={collapseTip}
              aria-label={collapseTip}
              style={{
                borderRadius: 4,
                padding: 4,
                background: "transparent",
                border: "none",
                color: "#6b7280",
                cursor: "pointer",
              }}
            >
              <RightOutlined style={{ fontSize: 14 }} />
            </button>
          </div>

          <ol
            style={{
              flex: 1,
              overflowY: "auto",
              padding: 6,
              margin: 0,
              listStyle: "none",
            }}
          >
            {visibleBlocks.map((block, idx) => {
              const Icon = TYPE_ICON[block.type] || FileTextOutlined;
              const fallbackLabel = TYPE_LABEL[block.type] || block.type;
              const label = shortLabel(block, fallbackLabel);
              const isActive = block.id === activeId;
              const isError = block.status === "error";
              const isLoading =
                block.status === "pending" || block.status === "generating";

              return (
                <li key={block.id}>
                  <button
                    type="button"
                    onClick={() => handleJump(block.id)}
                    style={{
                      display: "flex",
                      width: "100%",
                      alignItems: "center",
                      gap: 8,
                      borderRadius: 6,
                      padding: "6px 8px",
                      textAlign: "left",
                      cursor: "pointer",
                      border: "none",
                      background: isActive
                        ? "rgba(22,119,255,0.1)"
                        : "transparent",
                      color: isActive ? "rgba(0,0,0,0.88)" : "#6b7280",
                      transition: "color 150ms, background-color 150ms",
                    }}
                  >
                    <span
                      style={{
                        flexShrink: 0,
                        color: isActive ? "#1677ff" : "#6b7280",
                      }}
                    >
                      {isLoading ? (
                        <LoadingOutlined spin style={{ fontSize: 14 }} />
                      ) : isError ? (
                        <ExclamationCircleOutlined
                          style={{ fontSize: 14, color: "#f43f5e" }}
                        />
                      ) : (
                        <Icon style={{ fontSize: 14 }} />
                      )}
                    </span>
                    <span
                      style={{
                        display: "flex",
                        minWidth: 0,
                        flex: 1,
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <span
                        style={{
                          flexShrink: 0,
                          fontSize: "10.5px",
                          fontVariantNumeric: "tabular-nums",
                          color: "rgba(107,114,128,0.7)",
                        }}
                      >
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                      <span
                        style={{
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                        title={`${fallbackLabel} · ${label}`}
                      >
                        {label}
                      </span>
                    </span>
                    <span
                      style={{
                        flexShrink: 0,
                        width: 6,
                        height: 6,
                        borderRadius: 999,
                        background: statusDotColor(block.status),
                      }}
                    />
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>

        {/* ── Collapsed handle: chevron-only button overlays the same card  */}
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          title={expandTip}
          aria-label={expandTip}
          aria-hidden={!collapsed}
          tabIndex={collapsed ? 0 : -1}
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#6b7280",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            pointerEvents: collapsed ? "auto" : "none",
            opacity: collapsed ? 1 : 0,
            transform: collapsed ? "translateX(0)" : "translateX(-6px)",
            transition: collapsed
              ? `opacity 220ms ease-out 120ms, transform 320ms ${EASE} 80ms`
              : `opacity 140ms ease-out, transform 220ms ${EASE}`,
          }}
        >
          <RightOutlined
            style={{
              fontSize: 14,
              transform: "rotate(180deg)",
              transition: "transform 200ms",
            }}
          />
        </button>
      </div>
    </div>
  );
}
