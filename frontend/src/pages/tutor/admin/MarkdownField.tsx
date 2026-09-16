/**
 * 知识点长文本字段（1:1 复刻自原仓 web/components/curriculum/MarkdownField.tsx）：
 * textarea 编辑 + Markdown 预览（编辑/预览切换，激活态淡蓝底）。
 */
import React, { useState } from 'react';
import { Input } from 'antd';
import { EditOutlined, EyeOutlined } from '@ant-design/icons';
import LiteMarkdown from './dtMarkdown';

export function MarkdownField({
  label,
  value,
  onChange,
  placeholder,
  rows = 4,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  const [mode, setMode] = useState<'edit' | 'preview'>('edit');
  const btn = (m: 'edit' | 'preview') =>
    ({
      padding: '2px 6px',
      borderRadius: 4,
      fontSize: 11,
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      cursor: 'pointer',
      border: 'none',
      background: mode === m ? 'rgba(22,119,255,0.1)' : 'transparent',
      color: mode === m ? '#1677ff' : 'rgba(0,0,0,0.45)',
    }) as React.CSSProperties;
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <label style={{ fontSize: 12, fontWeight: 500, color: 'rgba(0,0,0,0.45)' }}>{label}</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <button type="button" style={btn('edit')} onClick={() => setMode('edit')}>
            <EditOutlined style={{ fontSize: 11 }} /> 编辑
          </button>
          <button type="button" style={btn('preview')} onClick={() => setMode('preview')}>
            <EyeOutlined style={{ fontSize: 11 }} /> 预览
          </button>
        </div>
      </div>
      {mode === 'edit' ? (
        <Input.TextArea
          style={{ fontSize: 14, lineHeight: 1.7 }}
          rows={rows}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <div style={{ minHeight: 48, padding: '6px 8px', borderRadius: 6, border: '1px solid #d9d9d9', background: 'rgba(0,0,0,0.02)', fontSize: 14 }}>
          <LiteMarkdown content={value || '_暂无内容_'} />
        </div>
      )}
    </div>
  );
}

export default MarkdownField;
