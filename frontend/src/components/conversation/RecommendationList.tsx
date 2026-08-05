/**
 * 推荐相似问题列表 - 问财（同花顺）风格
 *
 * 用于在 AI 回答卡片底部展示「你可能还想问：」推荐问题列表。
 * 特性：
 *   1. 纯内联样式，不依赖 antd 组件
 *   2. 每条推荐包含红色弯曲箭头 ↪ 与蓝色可点击文本
 *   3. 整行（箭头 + 文本）作为一个整体可点击
 *   4. hover 时文本加深、背景变浅蓝
 *   5. 列表为空时返回 null，不渲染任何内容
 */
import React, { useState } from 'react';
import { tokens } from '../../theme/tokens';

// 单条推荐问题对象
interface RecommendationItem {
  label: string;
  shortcut?: string;
}

interface RecommendationListProps {
  questions: Array<RecommendationItem>;
  onSelect?: (question: RecommendationItem) => void;
  title?: string; // 默认：「你可能还想问：」
}

const RecommendationList: React.FC<RecommendationListProps> = ({
  questions,
  onSelect,
  title = '你可能还想问：',
}) => {
  // 记录当前 hover 的项索引，用于模拟 :hover 效果
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // 列表为空或未传入时不渲染
  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        padding: 12,
        background: 'var(--bg-subtle)',
        borderRadius: 8,
        marginTop: 12,
      }}
    >
      {/* 标题：灰色小字 */}
      <div
        style={{
          color: 'var(--text-tertiary)',
          fontSize: 12,
          marginBottom: 8,
        }}
      >
        {title}
      </div>

      {/* 推荐问题列表 */}
      <div>
        {questions.map((question, index) => {
          const isHovered = hoveredIndex === index;
          const isLast = index === questions.length - 1;
          return (
            <div
              key={`${question.label}-${index}`}
              onClick={() => onSelect?.(question)}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 4px',
                cursor: 'pointer',
                background: isHovered ? 'var(--color-primary-bg)' : 'transparent',
                borderBottom: isLast ? 'none' : '1px solid var(--color-border)',
                transition: 'background 0.2s',
              }}
            >
              {/* 左侧红色弯曲箭头 */}
              <span
                style={{
                  fontSize: 14,
                  color: 'var(--color-error)',
                  fontWeight: 'bold',
                  marginRight: 6,
                  flexShrink: 0,
                  lineHeight: 1,
                }}
              >
                ↪
              </span>
              {/* 问题文本：蓝色，hover 时加深 */}
              <span
                style={{
                  fontSize: 13,
                  color: isHovered ? 'var(--color-primary-hover)' : tokens.colors.primary,
                  transition: 'color 0.2s',
                }}
              >
                {question.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RecommendationList;
