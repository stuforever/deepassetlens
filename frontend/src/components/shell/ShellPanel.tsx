/**
 * ShellPanel（批③ v4§十三；UX批② 反馈④ 可拖宽）：对话/管理台/设置三面板统一三态壳容器——
 * floating（浮在主区上，带阴影不挤主区）与 pinned（流内常驻，主区让位随宽联动），收起态由调用方不渲染。
 * 宽度：默认 400，右缘拖拽手柄（浮层与钉住态同权）实时调整并落库，clamp 320-640，
 * localStorage shell:width:{panel} 持久（UX批② 反馈④——能固定也能拖动调宽）。
 * 宽度/背景/右边框/头部由本壳提供，children 只渲染内容区（children 自带的
 * nav-panel/chat-panel/settings-panel testid 原样保留，对拍脚本依赖）。
 */
import { useRef } from 'react';
import { Button } from 'antd';
import { CloseOutlined, PushpinFilled, PushpinOutlined } from '@ant-design/icons';

/** UX批② 反馈④：拖宽档位（320-640，默认 400） */
export const PANEL_WIDTH_MIN = 320;
export const PANEL_WIDTH_MAX = 640;
export const PANEL_WIDTH_DEFAULT = 400;

export function ShellPanel({ panel, title, pinned, width, onWidthChange, onTogglePin, onClose, children }: {
  panel: 'chat' | 'console' | 'settings';
  title: string;
  pinned: boolean;
  width: number;
  onWidthChange: (w: number, commit: boolean) => void;
  onTogglePin: () => void;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const draggingRef = useRef(false);

  // UX批② 反馈④：mousedown 捕获面板左缘 → mousemove 实时回报 → mouseup 落库（commit）
  const startDrag = (e: React.MouseEvent) => {
    e.preventDefault();
    const root = (e.currentTarget as HTMLElement).closest('[data-testid="shell-panel"]');
    if (!root) return;
    const left = root.getBoundingClientRect().left;
    draggingRef.current = true;
    const clamp = (x: number) => Math.min(PANEL_WIDTH_MAX, Math.max(PANEL_WIDTH_MIN, Math.round(x - left)));
    const move = (ev: MouseEvent) => {
      if (draggingRef.current) onWidthChange(clamp(ev.clientX), false);
    };
    const up = (ev: MouseEvent) => {
      draggingRef.current = false;
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
      onWidthChange(clamp(ev.clientX), true);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  return (
    <div
      data-testid="shell-panel"
      data-panel={panel}
      style={{
        width,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-content, #fff)',
        borderRight: '1px solid var(--border-subtle, #eee)',
        // floating：absolute 浮层（left:48 从图标条右侧起步）带阴影不挤主区；pinned：流内 flex 兄弟节点
        // relative=pinned 态拖宽手柄的定位祖先（floating 本就 absolute）
        ...(pinned
          ? { flexShrink: 0, position: 'relative' as const }
          : {
              position: 'absolute' as const,
              left: 48,
              top: 0,
              bottom: 0,
              zIndex: 100,
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            }),
      }}
    >
      {/* 头部：标题 + 弹性空隙 + 钉住钮 + 关闭钮 */}
      <div
        style={{
          height: 40,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          padding: '0 12px',
          borderBottom: '1px solid var(--border-subtle, #eee)',
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #333)' }}>{title}</span>
        <div style={{ flex: 1 }} />
        <Button
          type="text"
          size="small"
          icon={pinned ? <PushpinFilled /> : <PushpinOutlined />}
          title="钉住/取消钉住"
          data-testid="shell-panel-pin"
          onClick={onTogglePin}
        />
        <Button
          type="text"
          size="small"
          icon={<CloseOutlined />}
          data-testid="shell-panel-close"
          onClick={onClose}
        />
      </div>
      {/* 内部滚动由内容区承担；children 原宽度/背景/边框已剥离（换壳），testid 与 padding 原样 */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>{children}</div>
      {/* UX批② 反馈④：右缘拖宽手柄（贴右缘 6px 热区，col-resize） */}
      <div
        data-testid="shell-panel-resizer"
        onMouseDown={startDrag}
        title="拖动调宽"
        style={{
          position: 'absolute',
          top: 0,
          right: -3,
          bottom: 0,
          width: 6,
          cursor: 'col-resize',
          zIndex: 101,
        }}
      />
    </div>
  );
}

export default ShellPanel;
