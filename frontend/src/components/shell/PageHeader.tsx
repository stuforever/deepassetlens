/**
 * PageHeader - 页面标题区（高 ~56）。
 * title(20/600) + description(14/辅助色) + 右侧 extra。底部分割线，不用卡片。
 */
import React from 'react';
import { tokens } from '../../theme/tokens';

interface PageHeaderProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  extra?: React.ReactNode;
  style?: React.CSSProperties;
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, description, extra, style }) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        gap: tokens.space.s4,
        paddingBottom: tokens.space.s3,
        marginBottom: tokens.space.s4,
        borderBottom: `1px solid ${tokens.colors.border}`,
        minHeight: 56,
        ...style,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
        <div
          style={{
            fontSize: tokens.fontSize.pageTitle,
            fontWeight: tokens.fontWeight.semibold,
            color: tokens.colors.textPrimary,
            lineHeight: 1.3,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {title}
        </div>
        {description ? (
          <div style={{ fontSize: tokens.fontSize.caption, color: tokens.colors.textTertiary, lineHeight: 1.5 }}>
            {description}
          </div>
        ) : null}
      </div>
      {extra ? (
        <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: tokens.space.s2 }}>
          {extra}
        </div>
      ) : null}
    </div>
  );
};

export default PageHeader;
