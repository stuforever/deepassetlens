/**
 * ShellPanel（批③ v4 §十三）：对话/管理台/设置三面板统一三态壳容器——
 * floating（浮在主区上，带阴影不挤主区）与 pinned（流内常驻，主区让位）同宽 400，收起态由调用方不渲染。
 * 宽度/背景/右边框/头部由本壳提供，children 只渲染内容区（children 自带的
 * nav-panel/chat-panel/settings-panel testid 原样保留，对拍脚本依赖）。
 */
import { Button } from 'antd';
import { CloseOutlined, PushpinFilled, PushpinOutlined } from '@ant-design/icons';

/** v4 §十三：三面板同宽 400（floating 与 pinned 同宽），禁出现第三个宽度 */
const PANEL_WIDTH = 400;

export function ShellPanel({ panel, title, pinned, onTogglePin, onClose, children }: {
  panel: 'chat' | 'console' | 'settings';
  title: string;
  pinned: boolean;
  onTogglePin: () => void;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      data-testid="shell-panel"
      data-panel={panel}
      style={{
        width: PANEL_WIDTH,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-content, #fff)',
        borderRight: '1px solid var(--border-subtle, #eee)',
        // floating：absolute 浮层（left:48 从图标条右侧起步）带阴影不挤主区；pinned：流内 flex 兄弟节点
        ...(pinned
          ? { flexShrink: 0 }
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
    </div>
  );
}

export default ShellPanel;
