/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/BlockRenderer.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next，i18n 中文直出（zh/app.json）：
 *   "Generating {{type}}…"→正在生成{type}…、"{type} block failed"→{type} 内容块生成失败、
 *   "not retryable"→不可重试、"Unknown error"→未知错误、"Retry"→重试、
 *   "Move up"→上移、"Move down"→下移、"Change type"→更改类型、"Regenerate"→重新生成、
 *   "Delete"→删除；t(block.type)/t(type) 用 BLOCK_TYPE_LABELS（块类型键名译文）。
 * lucide → @ant-design/icons：Loader2→LoadingOutlined(spin)、AlertTriangle→WarningOutlined、
 *   RefreshCw→RedoOutlined、Trash2→DeleteOutlined、ArrowUp/Down→ArrowUp/DownOutlined、
 *   Replace→SwapOutlined。
 * MarkdownRenderer → LiteMarkdown（'./dtMarkdown'，variant 忽略）；
 * @/lib/book-types → './book-types'；Tailwind → antd Button/Dropdown + 内联样式
 * （group-hover 显隐工具条 → 容器 hovered state + opacity/transform；
 *  rose 系错误态按 Tailwind 色值：rose-300/60、rose-50、rose-900、rose-400/60）。
 * props 契约（BlockRendererProps）与 data-testid="book-block-regenerate" 原样保留。
 */
import { useState } from "react";
import {
  WarningOutlined,
  LoadingOutlined,
  RedoOutlined,
  DeleteOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import { Button, Dropdown } from "antd";
import type { Block, BlockType } from './book-types';
import { LiteMarkdown } from './dtMarkdown';

import TextBlock from "./TextBlock";
import CalloutBlock from "./CalloutBlock";
import QuizBlock from "./QuizBlock";
import UserNoteBlock from "./UserNoteBlock";
import FigureBlock from "./FigureBlock";
import InteractiveBlock from "./InteractiveBlock";
import AnimationBlock from "./AnimationBlock";
import CodeBlock from "./CodeBlock";
import TimelineBlock from "./TimelineBlock";
import FlashCardsBlock from "./FlashCardsBlock";
import DeepDiveBlock from "./DeepDiveBlock";
import ConceptGraphBlock from "./ConceptGraphBlock";
import SectionBlock from "./SectionBlock";
import PlaceholderBlock from "./PlaceholderBlock";

const borderColor = "#e4e4e7";
const foreground = "rgba(0,0,0,0.88)";
const mutedForeground = "#6b7280";

// 块类型键名 → 中文（zh/app.json 同名 key 译文，供 t(block.type)/t(type) 直出）。
const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  text: "文本",
  callout: "提示",
  quiz: "测验",
  user_note: "用户笔记",
  figure: "图示",
  interactive: "交互",
  animation: "动画",
  code: "代码",
  timeline: "时间线",
  flash_cards: "闪卡",
  deep_dive: "深入学习",
  section: "章节",
  concept_graph: "概念图",
};

const CHANGEABLE_TYPES: BlockType[] = [
  "text",
  "section",
  "callout",
  "quiz",
  "code",
  "timeline",
  "flash_cards",
  "figure",
  "interactive",
  "animation",
  "deep_dive",
];

// 原仓 hover:bg-[var(--background)] hover:text-[var(--foreground)] 的工具条小图标按钮。
const toolButtonStyle = {
  padding: 4,
  borderRadius: 4,
  color: mutedForeground,
  height: "auto",
} as const;

export interface BlockRendererProps {
  block: Block;
  onRegenerate?: (block: Block) => void;
  onDelete?: (block: Block) => void;
  onMove?: (block: Block, direction: "up" | "down") => void;
  onChangeType?: (block: Block, newType: BlockType) => void;
  onDeepDive?: (topic: string, blockId: string) => Promise<void> | void;
  onQuizAttempt?: (
    block: Block,
    args: { questionId?: string; userAnswer?: string; isCorrect: boolean },
  ) => void;
  pendingDeepDiveTopic?: string | null;
  bookId?: string;
  currentPageId?: string;
  bookLanguage?: string;
}

export default function BlockRenderer({
  block,
  onRegenerate,
  onDelete,
  onMove,
  onChangeType,
  onDeepDive,
  onQuizAttempt,
  pendingDeepDiveTopic,
  bookId,
  currentPageId,
  bookLanguage,
}: BlockRendererProps) {
  const [showTypeMenu, setShowTypeMenu] = useState(false);
  // 原仓 group/group-hover 显隐工具条 → 容器 hover state。
  const [hovered, setHovered] = useState(false);

  if (block.status === "pending" || block.status === "generating") {
    const typeLabel = BLOCK_TYPE_LABELS[block.type] ?? block.type;
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          borderRadius: 16,
          border: `1px dashed ${borderColor}`,
          background: "#fff",
          padding: "12px 16px",
          fontSize: 14,
          color: mutedForeground,
        }}
      >
        <LoadingOutlined spin style={{ fontSize: 16 }} />
        <span>{`正在生成${typeLabel}…`}</span>
      </div>
    );
  }
  if (block.status === "error") {
    const failure = block.metadata?.failure as
      | { kind?: string; message?: string; retryable?: boolean }
      | undefined;
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid rgba(253,164,175,0.6)",
          background: "#fff1f2",
          padding: "12px 16px",
          fontSize: 14,
          color: "#881337",
        }}
      >
        <div
          style={{
            marginBottom: 4,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontWeight: 500,
          }}
        >
          <WarningOutlined style={{ fontSize: 16 }} />
          {`${BLOCK_TYPE_LABELS[block.type] ?? block.type} 内容块生成失败`}
        </div>
        {failure?.kind && (
          <div
            style={{
              marginBottom: 4,
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              opacity: 0.7,
            }}
          >
            {failure.kind}
            {failure.retryable === false ? ` · 不可重试` : ""}
          </div>
        )}
        <div style={{ fontSize: 12, opacity: 0.8 }}>
          {block.error || failure?.message || "未知错误"}
        </div>
        {onRegenerate && (
          <Button
            size="small"
            onClick={() => onRegenerate(block)}
            style={{
              marginTop: 8,
              display: "inline-flex",
              borderRadius: 6,
              border: "1px solid rgba(251,113,133,0.6)",
              background: "rgba(255,255,255,0.4)",
              padding: "4px 8px",
              fontSize: 12,
              fontWeight: 500,
              color: "#881337",
              height: "auto",
            }}
          >
            {"重试"}
          </Button>
        )}
      </div>
    );
  }

  let body: React.ReactNode;
  switch (block.type) {
    case "text":
      body = <TextBlock block={block} />;
      break;
    case "section":
      body = <SectionBlock block={block} />;
      break;
    case "callout":
      body = <CalloutBlock block={block} />;
      break;
    case "quiz":
      body = <QuizBlock block={block} onAttempt={onQuizAttempt} />;
      break;
    case "user_note":
      body = <UserNoteBlock block={block} />;
      break;
    case "figure":
      body = <FigureBlock block={block} />;
      break;
    case "interactive":
      body = <InteractiveBlock block={block} />;
      break;
    case "animation":
      body = <AnimationBlock block={block} />;
      break;
    case "code":
      body = <CodeBlock block={block} />;
      break;
    case "timeline":
      body = <TimelineBlock block={block} />;
      break;
    case "flash_cards":
      body = <FlashCardsBlock block={block} />;
      break;
    case "deep_dive":
      body = (
        <DeepDiveBlock
          block={block}
          onDeepDive={onDeepDive}
          pendingTopic={pendingDeepDiveTopic}
        />
      );
      break;
    case "concept_graph":
      body = (
        <ConceptGraphBlock
          block={block}
          bookId={bookId}
          currentPageId={currentPageId}
          language={bookLanguage}
        />
      );
      break;
    default:
      body = <PlaceholderBlock block={block} />;
  }

  const hasActions = !!onRegenerate || !!onDelete || !!onMove || !!onChangeType;

  const bridgeText = String(
    (block.payload as Record<string, unknown> | undefined)?.bridge_text ?? "",
  ).trim();
  const showBridge = bridgeText.length > 0;

  return (
    <div
      style={{ position: "relative" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {showBridge && (
        <div style={{ marginBottom: 12, color: foreground }}>
          <LiteMarkdown content={bridgeText} />
        </div>
      )}
      {hasActions && (
        <div
          style={{
            position: "absolute",
            top: -12,
            right: 8,
            zIndex: 10,
            display: "flex",
            alignItems: "center",
            gap: 4,
            borderRadius: 6,
            border: `1px solid ${borderColor}`,
            background: "#fff",
            padding: "2px 4px",
            color: mutedForeground,
            boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
            opacity: hovered ? 1 : 0,
            transform: hovered ? "translateY(0)" : "translateY(4px)",
            pointerEvents: hovered ? "auto" : "none",
            transition: "opacity 0.15s ease, transform 0.15s ease",
          }}
        >
          {onMove && (
            <>
              <Button
                type="text"
                size="small"
                onClick={() => onMove(block, "up")}
                style={toolButtonStyle}
                title={"上移"}
                icon={<ArrowUpOutlined style={{ fontSize: 14 }} />}
              />
              <Button
                type="text"
                size="small"
                onClick={() => onMove(block, "down")}
                style={toolButtonStyle}
                title={"下移"}
                icon={<ArrowDownOutlined style={{ fontSize: 14 }} />}
              />
            </>
          )}
          {onChangeType && (
            <Dropdown
              trigger={["click"]}
              open={showTypeMenu}
              onOpenChange={setShowTypeMenu}
              menu={{
                items: CHANGEABLE_TYPES.filter((type) => type !== block.type).map(
                  (type) => ({
                    key: type,
                    label: BLOCK_TYPE_LABELS[type] ?? type,
                  }),
                ),
                onClick: ({ key }) => {
                  setShowTypeMenu(false);
                  onChangeType(block, key as BlockType);
                },
              }}
              overlayStyle={{ minWidth: 176, maxHeight: 240, overflowY: "auto" }}
            >
              <Button
                type="text"
                size="small"
                style={toolButtonStyle}
                title={"更改类型"}
                icon={<SwapOutlined style={{ fontSize: 14 }} />}
              />
            </Dropdown>
          )}
          {onRegenerate && (
            <Button
              type="text"
              size="small"
              onClick={() => onRegenerate(block)}
              data-testid="book-block-regenerate"
              style={toolButtonStyle}
              title={"重新生成"}
              icon={<RedoOutlined style={{ fontSize: 14 }} />}
            />
          )}
          {onDelete && (
            <Button
              type="text"
              size="small"
              danger
              onClick={() => onDelete(block)}
              style={{ ...toolButtonStyle, background: "transparent" }}
              title={"删除"}
              icon={<DeleteOutlined style={{ fontSize: 14 }} />}
            />
          )}
        </div>
      )}
      {body}
    </div>
  );
}
