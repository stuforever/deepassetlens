/**
 * ContextRail（批①b——v4§十三.3）：对话页右栏——40px 细条三图标 → 点击展开 320px 面板。
 * 三面板：evidence=依据（EvidenceCapsule 数据展开）/ config=本场配置（附件条镜像）/
 * artifacts=产物（本会话 SQL 结果 CSV、回答 Markdown、已存笔记入口）。
 * 钉住态主区右移让位；展开状态 localStorage `rail:{expert}:open` 记忆。
 */
import React, { useState } from 'react';
import { Button, Typography } from 'antd';
import {
  PaperClipOutlined, SettingOutlined, InboxOutlined, CloseOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

type RailTab = 'evidence' | 'config' | 'artifacts' | null;

const TAB_META: { key: NonNullable<RailTab>; label: string; icon: React.ReactNode }[] = [
  { key: 'evidence', label: '依据', icon: <PaperClipOutlined /> },
  { key: 'config', label: '本场配置', icon: <SettingOutlined /> },
  { key: 'artifacts', label: '产物', icon: <InboxOutlined /> },
];

const ContextRail: React.FC<{
  expertId: string;
  evidence?: React.ReactNode;
  config?: React.ReactNode;
  artifacts?: React.ReactNode;
  testId?: string;
}> = ({ expertId, evidence, config, artifacts, testId = 'context-rail' }) => {
  const [tab, setTab] = useState<RailTab>(() => {
    try {
      return (localStorage.getItem(`rail:${expertId}:open`) as RailTab) || null;
    } catch {
      return null;
    }
  });

  const switchTab = (k: RailTab) => {
    setTab(k);
    try {
      if (k) localStorage.setItem(`rail:${expertId}:open`, k);
      else localStorage.removeItem(`rail:${expertId}:open`);
    } catch { /* ignore */ }
  };

  const content = tab === 'evidence' ? evidence : tab === 'config' ? config : tab === 'artifacts' ? artifacts : null;
  const meta = TAB_META.find((t) => t.key === tab);

  return (
    <div data-testid={testId} style={{ display: 'flex', alignItems: 'stretch', flexShrink: 0, height: '100%' }}>
      {/* 320px 展开面板 */}
      {tab ? (
        <div
          data-testid="context-rail-panel"
          style={{
            width: 320, flexShrink: 0, borderLeft: '1px solid var(--border-subtle, #eee)',
            background: 'var(--bg-content, #fff)', display: 'flex', flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', padding: '10px 12px', borderBottom: '1px solid var(--border-subtle, #eee)' }}>
            <Text strong style={{ fontSize: 13, flex: 1 }}>{meta?.label}</Text>
            <Button size="small" type="text" icon={<CloseOutlined />} onClick={() => switchTab(null)} aria-label="收起右栏" />
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>{content}</div>
        </div>
      ) : null}
      {/* 40px 细条 */}
      <div
        data-testid="context-rail-strip"
        style={{
          width: 40, flexShrink: 0, borderLeft: '1px solid var(--border-subtle, #eee)',
          background: 'var(--bg-content, #fff)', display: 'flex', flexDirection: 'column',
          alignItems: 'center', paddingTop: 12, gap: 4,
        }}
      >
        {TAB_META.map((t) => (
          <Button
            key={t.key}
            size="small"
            type="text"
            icon={t.icon}
            aria-label={t.label}
            data-testid={`context-rail-${t.key}`}
            onClick={() => switchTab(tab === t.key ? null : t.key)}
            style={{
              color: tab === t.key ? 'var(--color-primary)' : 'var(--text-tertiary)',
              background: tab === t.key ? 'var(--color-primary-bg, #e6f0ff)' : 'transparent',
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default ContextRail;
