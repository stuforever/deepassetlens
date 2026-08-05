/**
 * ErrorState - 错误状态。
 * 用于请求失败位：原因 + 重试 + 修改，不弹全局 message。
 */
import React from 'react';
import { Button, Space } from 'antd';
import { ExclamationCircleOutlined, ReloadOutlined, EditOutlined } from '@ant-design/icons';
import { tokens } from '../../theme/tokens';

interface ErrorStateProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
  onRetry?: () => void;
  onModify?: () => void;
  retryText?: React.ReactNode;
  modifyText?: React.ReactNode;
  style?: React.CSSProperties;
}

const ErrorState: React.FC<ErrorStateProps> = ({
  title = '请求失败',
  description,
  onRetry,
  onModify,
  retryText = '重试',
  modifyText = '修改问题',
  style,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: `${tokens.space.s6}px ${tokens.space.s5}px`,
        background: tokens.colors.errorBg,
        border: `1px solid ${tokens.colors.errorBg}`,
        borderRadius: tokens.radius.card,
        textAlign: 'center',
        ...style,
      }}
    >
      <ExclamationCircleOutlined style={{ fontSize: 28, color: tokens.colors.error }} />
      <div style={{ marginTop: tokens.space.s2, fontSize: tokens.fontSize.body, color: tokens.colors.textPrimary, fontWeight: tokens.fontWeight.medium }}>
        {title}
      </div>
      {description ? (
        <div style={{ marginTop: tokens.space.s1, fontSize: tokens.fontSize.caption, color: tokens.colors.textTertiary, maxWidth: 420 }}>
          {description}
        </div>
      ) : null}
      {(onRetry || onModify) ? (
        <Space style={{ marginTop: tokens.space.s4 }}>
          {onModify ? (
            <Button size="small" icon={<EditOutlined />} onClick={onModify}>{modifyText}</Button>
          ) : null}
          {onRetry ? (
            <Button type="primary" size="small" icon={<ReloadOutlined />} onClick={onRetry}>{retryText}</Button>
          ) : null}
        </Space>
      ) : null}
    </div>
  );
};

export default ErrorState;
