/**
 * CanvasToolbar - 画布页统一工具栏（44px）。
 * 左右两段布局：左侧放模式切换/搜索，右侧放画布操作（适应/缩放/刷新/图例）。
 * 配色走 token，底部 1px 分割线。
 */
import React from 'react';
import { tokens } from '../../theme/tokens';

interface CanvasToolbarProps {
  /** 左侧工具区（模式切换、搜索等） */
  left?: React.ReactNode;
  /** 右侧工具区（画布操作按钮） */
  right?: React.ReactNode;
  /** 等同 left，便于直接写子节点 */
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

const CanvasToolbar: React.FC<CanvasToolbarProps> = ({ left, right, children, style }) => (
  <div
    style={{
      height: 44,
      flexShrink: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: `0 ${tokens.space.s4}px`,
      background: tokens.colors.bgContent,
      borderBottom: `1px solid ${tokens.colors.border}`,
      gap: tokens.space.s3,
      ...style,
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: tokens.space.s3, minWidth: 0 }}>
      {left}
      {children}
    </div>
    {right ? (
      <div style={{ display: 'flex', alignItems: 'center', gap: tokens.space.s2 }}>{right}</div>
    ) : null}
  </div>
);

export default CanvasToolbar;
