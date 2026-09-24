/**
 * ContextRail（批①b——v4§十三.3；UX3批3 可拖宽+Tooltip）：对话页右栏——40px 细条三图标 → 点击展开 320px 面板。
 * 三面板：evidence=依据（EvidenceCapsule 数据展开）/ config=本场配置（附件条镜像）/
 * artifacts=产物（本会话 SQL 结果 CSV、回答 Markdown、已存笔记入口）。
 * 展开面板可拖宽（左缘拖柄 clamp 280-560，localStorage rail:width 持久）。
 * 钉住态主区让位；展开状态 localStorage `rail:{expert}:open` 记忆。
 */
import React, { useRef, useState } from 'react';
import { Button, Tooltip, Typography } from 'antd';
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

/** UX3批3（反馈④）：右栏拖宽档位（镜像 ShellPanel 模式） */
export const RAIL_WIDTH_MIN = 280;
export const RAIL_WIDTH_MAX = 560;
export const RAIL_WIDTH_DEFAULT = 320;

const ContextRail: React.FC<{
  expertId: string;
  evidence?: React.ReactNode;
  config?: React.ReactNode;
  artifacts?: React.ReactNode;
  testId?: string;
  width?: number;
  onWidthChange?: (w: number, commit: boolean) => void;
}> = ({ expertId, evidence, config, artifacts, testId = 'context-rail', width, onWidthChange }) => {
  const [tab, setTab] = useState<RailTab>(() => {
    try {
      return (localStorage.getItem(`rail:${expertId}:open`) as RailTab) || null;
    } catch {
      return null;
    }
  });

  // UX3批3：受控宽（父级持久化）或内部 state
  const [innerW, setInnerW] = useState(() => {
    try {
      const v = Number(localStorage.getItem('rail:width'));
      return v >= RAIL_WIDTH_MIN && v <= RAIL_WIDTH_MAX ? v : RAIL_WIDTH_DEFAULT;
    } catch {
      return RAIL_WIDTH_DEFAULT;
    }
  });
  const railW = width ?? innerW;
  const setRailW = (w: number, commit: boolean) => {
    if (onWidthChange) onWidthChange(w, commit);
    else {
      setInnerW(w);
      if (commit) {
        try { localStorage.setItem('rail:width', String(w)); } catch { /* ignore */ }
      }
    }
  };

  const draggingRef = useRef(false);
  const startDrag = (e: React.MouseEvent) => {
    e.preventDefault();
    const root = (e.currentTarget as HTMLElement).closest('[data-testid="context-rail-panel"]');
    if (!root) return;
    const left = root.getBoundingClientRect().left;
    draggingRef.current = true;
    const clamp = (x: number) => Math.min(RAIL_WIDTH_MAX, Math.max(RAIL_WIDTH_MIN, Math.round(x - left)));
    const move = (ev: MouseEvent) => { if (draggingRef.current) setRailW(clamp(ev.clientX), false); };
    const up = (ev: MouseEvent) => {
      draggingRef.current = false;
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
      setRailW(clamp(ev.clientX), true);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

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
      {/* 展开面板（可拖宽——左缘拖柄 clamp 280-560） */}
      {tab ? (
        <div
          data-testid="context-rail-panel"
          style={{
            width: railW, flexShrink: 0, borderLeft: '1px solid var(--border-subtle, #eee)',
            background: 'var(--bg-content, #fff)', display: 'flex', flexDirection: 'column',
            overflow: 'hidden', position: 'relative',
          }}
        >
          {/* 拖柄：左缘（面板在右侧，拖左缘调宽） */}
          <div
            data-testid="context-rail-resize"
            onMouseDown={startDrag}
            style={{ position: 'absolute', left: -3, top: 0, bottom: 0, width: 6, cursor: 'col-resize', zIndex: 2 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', padding: '10px 12px', borderBottom: '1px solid var(--border-subtle, #eee)' }}>
            <Text strong style={{ fontSize: 13, flex: 1 }}>{meta?.label}</Text>
            <Button size="small" type="text" icon={<CloseOutlined />} onClick={() => switchTab(null)} aria-label="收起右栏" />
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>{content}</div>
        </div>
      ) : null}
      {/* 40px 细条（图标加 Tooltip） */}
      <div
        data-testid="context-rail-strip"
        style={{
          width: 40, flexShrink: 0, borderLeft: '1px solid var(--border-subtle, #eee)',
          background: 'var(--bg-content, #fff)', display: 'flex', flexDirection: 'column',
          alignItems: 'center', paddingTop: 12, gap: 4,
        }}
      >
        {TAB_META.map((t) => (
          <Tooltip key={t.key} title={t.label} placement="left">
            <Button
              size="small"
              type="text"
              icon={t.icon}
              data-testid={`context-rail-icon-${t.key}`}
              onClick={() => switchTab(t.key === tab ? null : t.key)}
              style={{
                color: tab === t.key ? 'var(--brand, #2563EB)' : 'var(--text-secondary, #888)',
              }}
            />
          </Tooltip>
        ))}
      </div>
    </div>
  );
};

export default ContextRail;
