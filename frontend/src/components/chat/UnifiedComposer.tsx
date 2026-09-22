/**
 * UnifiedComposer（三轨M7(U2) §3.2/§3.3）：全局统一对话输入组件。
 * 版式契约：S3 阴影 + 聚焦主色描边环 + 渐变发送钮 + 多行自适应；
 * 左 slot（模型选择/学段选择器等）+ 中 textarea + 右发送；
 * 供各专家对话页复用（数据资产探查 FreePlanChat 为标杆原实现）。
 * testid：unified-composer / unified-composer-send。
 */
import React from 'react';
import { Button, Input } from 'antd';
import { SendOutlined, StopOutlined } from '@ant-design/icons';
import { tokens } from '../../theme/tokens';

export interface UnifiedComposerProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  disabled?: boolean;
  minRows?: number;
  maxRows?: number;
  leftSlot?: React.ReactNode;
  testId?: string;
  /** v4§九：busy 时发送钮切换「停止生成」（白底红边，沿 FreePlanChat P3 规格） */
  isBusy?: boolean;
  onStop?: () => void;
}

const UnifiedComposer: React.FC<UnifiedComposerProps> = ({
  value, onChange, onSubmit, placeholder = '想问什么数据？',
  disabled = false, minRows = 2, maxRows = 6, leftSlot, testId = 'unified-composer',
  isBusy = false, onStop,
}) => (
  <div
    className="dal-composer"
    data-testid={testId}
    style={{
      borderRadius: 12,
      border: '1px solid var(--color-border)',
      background: 'var(--bg-content)',
      overflow: 'hidden',
      boxShadow: tokens.elevation.s3,
    }}
  >
    <Input.TextArea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      rows={minRows}
      placeholder={placeholder}
      autoSize={{ minRows, maxRows }}
      variant="borderless"
      onPressEnter={(e) => {
        if (!e.shiftKey) {
          e.preventDefault();
          if (!disabled && value.trim()) onSubmit();
        }
      }}
      style={{ padding: '14px 16px 4px', resize: 'none' }}
    />
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '2px 8px 8px 12px' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {leftSlot}
        <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Shift+Enter 换行</span>
      </div>
      {isBusy && onStop ? (
        /* v4§九：停止生成（白底红边，沿 FreePlanChat P3 规格；此态下不 disabled） */
        <Button
          shape="circle"
          icon={<StopOutlined />}
          onClick={onStop}
          aria-label="停止生成"
          data-testid={`${testId}-stop`}
          style={{ background: 'var(--bg-content)', borderColor: tokens.colors.error, color: tokens.colors.error }}
        />
      ) : (
        <Button
          type="primary"
          shape="circle"
          data-testid={`${testId}-send`}
          icon={<SendOutlined />}
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
        />
      )}
    </div>
  </div>
);

export default UnifiedComposer;
