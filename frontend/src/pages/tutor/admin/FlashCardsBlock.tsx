/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/FlashCardsBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next，i18n 中文直出（zh/app.json）：
 *   "Flash Cards"→闪卡、"Answer"→答案、"Question"→题目、"Hint"→提示、
 *   "Prev"→上一张、"Flip"→翻转、"Next"→下一个。
 * lucide：ChevronLeft→LeftOutlined、ChevronRight→RightOutlined、RotateCcw→UndoOutlined。
 * Tailwind → antd Button + 内联样式（卡片翻面按钮/上一张/翻转/下一个），
 * hover 主色边框由 antd Button 自带，语义对应原 hover:border-primary/40。
 */
import { useState } from "react";
import {
  LeftOutlined,
  RightOutlined,
  UndoOutlined,
} from "@ant-design/icons";
import { Button } from "antd";
import type { Block } from './book-types';

const borderColor = "#e4e4e7";
const foreground = "rgba(0,0,0,0.88)";
const mutedForeground = "#6b7280";

interface Card {
  front?: string;
  back?: string;
  hint?: string;
}

export interface FlashCardsBlockProps {
  block: Block;
}

export default function FlashCardsBlock({ block }: FlashCardsBlockProps) {
  const cards = (block.payload?.cards as Card[] | undefined) || [];
  const [idx, setIdx] = useState(0);
  const [showBack, setShowBack] = useState(false);
  if (cards.length === 0) return null;
  const card = cards[Math.min(idx, cards.length - 1)] || {};

  return (
    <div
      style={{
        borderRadius: 16,
        border: `1px solid ${borderColor}`,
        background: "#fff",
        padding: 16,
        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.16em",
            color: "#1677ff",
          }}
        >
          {"闪卡"}
        </span>
        <span style={{ fontSize: 12, color: mutedForeground }}>
          {idx + 1} / {cards.length}
        </span>
      </div>
      <Button
        block
        onClick={() => setShowBack((v) => !v)}
        style={{
          marginTop: 12,
          height: 160,
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          borderRadius: 12,
          border: `1px solid ${borderColor}`,
          background: "#f5f5f5",
          padding: "0 24px",
          textAlign: "center",
        }}
      >
        <span
          style={{
            fontSize: 10,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: mutedForeground,
          }}
        >
          {showBack ? "答案" : "题目"}
        </span>
        <span style={{ fontSize: 16, fontWeight: 500, color: foreground }}>
          {showBack ? card.back : card.front}
        </span>
        {!showBack && card.hint && (
          <span
            style={{ fontSize: 12, fontStyle: "italic", color: mutedForeground }}
          >
            {"提示"}: {card.hint}
          </span>
        )}
      </Button>
      <div style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Button
          size="small"
          icon={<LeftOutlined style={{ fontSize: 14 }} />}
          onClick={() => {
            setShowBack(false);
            setIdx((i) => Math.max(0, i - 1));
          }}
          disabled={idx === 0}
          style={{ borderRadius: 6, fontSize: 12, display: "inline-flex", alignItems: "center", gap: 4 }}
        >
          {"上一张"}
        </Button>
        <Button
          size="small"
          icon={<UndoOutlined style={{ fontSize: 14 }} />}
          onClick={() => setShowBack((v) => !v)}
          style={{ borderRadius: 6, fontSize: 12, display: "inline-flex", alignItems: "center", gap: 4 }}
        >
          {"翻转"}
        </Button>
        <Button
          size="small"
          icon={<RightOutlined style={{ fontSize: 14 }} />}
          iconPosition="end"
          onClick={() => {
            setShowBack(false);
            setIdx((i) => Math.min(cards.length - 1, i + 1));
          }}
          disabled={idx >= cards.length - 1}
          style={{ borderRadius: 6, fontSize: 12, display: "inline-flex", alignItems: "center", gap: 4 }}
        >
          {"下一个"}
        </Button>
      </div>
    </div>
  );
}
