/**
 * StatusTag - 统一状态标签。
 * preset 决定配色，颜色全部走 token，零硬编码。
 */
import React from 'react';
import { Tag } from 'antd';
import { tokens } from '../../theme/tokens';

export type StatusPreset = 'success' | 'warning' | 'error' | 'info' | 'disabled' | 'ai' | 'default';

const PRESET_MAP: Record<StatusPreset, { color: string; bg: string }> = {
  success: { color: tokens.colors.success, bg: tokens.colors.successBg },
  warning: { color: tokens.colors.warning, bg: tokens.colors.warningBg },
  error: { color: tokens.colors.error, bg: tokens.colors.errorBg },
  info: { color: tokens.colors.info, bg: tokens.colors.infoBg },
  disabled: { color: tokens.colors.textTertiary, bg: tokens.colors.bgSubtle },
  ai: { color: tokens.colors.ai, bg: tokens.colors.aiBg },
  default: { color: tokens.colors.textSecondary, bg: tokens.colors.bgSubtle },
};

interface StatusTagProps {
  preset?: StatusPreset;
  text?: React.ReactNode;
  children?: React.ReactNode;
  dot?: boolean;
  icon?: React.ReactNode;
  style?: React.CSSProperties;
}

const StatusTag: React.FC<StatusTagProps> = ({ preset = 'default', text, children, dot, icon, style }) => {
  const m = PRESET_MAP[preset];
  return (
    <Tag
      style={{
        margin: 0,
        color: m.color,
        background: m.bg,
        border: 'none',
        borderRadius: tokens.radius.default,
        fontSize: tokens.fontSize.caption,
        lineHeight: '20px',
        padding: '0 8px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        ...style,
      }}
    >
      {icon ?? null}
      {dot ? (
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: m.color, display: 'inline-block' }} />
      ) : null}
      {text ?? children}
    </Tag>
  );
};

export default StatusTag;
