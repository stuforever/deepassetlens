/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/PlaceholderBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next，i18n 中文直出（zh/app.json）：
 *   LABELS 英文值经 t() 的译文直接落为中文（Figure→图示、Interactive→交互、
 *   Animation→动画、Code Sandbox→代码沙盒、Timeline→时间线、Flash Cards→闪卡、
 *   Deep Dive→深入学习）；fallback t(block.type) 用 BLOCK_TYPE_LABELS（zh/app.json
 *   的块类型键名译文）；占位文案 "Coming in Phase 2 – {{type}} …"→
 *   "第二阶段上线后，{{type}} 内容块会显示在这里。"。
 * lucide Sparkles → ThunderboltOutlined；Tailwind → 内联样式。
 */
import { ThunderboltOutlined } from "@ant-design/icons";
import type { Block, BlockType } from './book-types';

export interface PlaceholderBlockProps {
  block: Block;
}

// 块类型键名 → 中文（zh/app.json 同名 key 译文，供 t(block.type)/t(intended) 直出）。
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

// 原 LABELS 值（英文）经 t() 后的中文直出对照。
const LABELS: Record<string, string> = {
  figure: "图示",
  interactive: "交互",
  animation: "动画",
  code: "代码沙盒",
  timeline: "时间线",
  flash_cards: "闪卡",
  deep_dive: "深入学习",
};

export default function PlaceholderBlock({ block }: PlaceholderBlockProps) {
  const label = LABELS[block.type] || BLOCK_TYPE_LABELS[block.type] || block.type;
  const intendedType = block.params?.intended_block_type
    ? String(block.params.intended_block_type)
    : block.type;
  const intendedLabel =
    BLOCK_TYPE_LABELS[intendedType as BlockType] ?? intendedType;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        borderRadius: 16,
        border: "1px dashed #e4e4e7",
        background: "rgba(244,244,245,0.3)",
        padding: "12px 16px",
        fontSize: 14,
        color: "#6b7280",
      }}
    >
      <ThunderboltOutlined style={{ fontSize: 16, color: "#1677ff" }} />
      <div>
        <div style={{ fontWeight: 500, color: "rgba(0,0,0,0.88)" }}>{label}</div>
        <div style={{ fontSize: 12 }}>
          {`第二阶段上线后，${intendedLabel} 内容块会显示在这里。`}
        </div>
      </div>
    </div>
  );
}
