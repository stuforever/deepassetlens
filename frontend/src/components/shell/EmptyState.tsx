/**
 * EmptyState - 空状态。
 * 中性风格：图标 + 标题 + 描述 + 操作，不用 antd Empty 默认大图。
 */
import React from 'react';
import { InboxOutlined } from '@ant-design/icons';
import { tokens } from '../../theme/tokens';

interface EmptyStateProps {
  icon?: React.ReactNode;
  /** B4 增强：插画位（比 icon 更大，空态图形/情感位；传入则替换默认图标位） */
  illustration?: React.ReactNode;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  style?: React.CSSProperties;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  illustration,
  title = '暂无数据',
  description,
  action,
  style,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: `${tokens.space.s7}px ${tokens.space.s5}px`,
        color: tokens.colors.textTertiary,
        ...style,
      }}
    >
      {illustration ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: tokens.space.s3 }}>
          {illustration}
        </div>
      ) : (
        <div style={{ fontSize: 40, color: tokens.colors.textDisabled, marginBottom: tokens.space.s3 }}>
          {icon ?? <InboxOutlined />}
        </div>
      )}
      <div style={{ fontSize: tokens.fontSize.body, color: tokens.colors.textSecondary, fontWeight: tokens.fontWeight.medium }}>
        {title}
      </div>
      {description ? (
        <div style={{ marginTop: tokens.space.s1, fontSize: tokens.fontSize.caption, color: tokens.colors.textTertiary, textAlign: 'center', maxWidth: 360 }}>
          {description}
        </div>
      ) : null}
      {action ? <div style={{ marginTop: tokens.space.s4 }}>{action}</div> : null}
    </div>
  );
};

export default EmptyState;
