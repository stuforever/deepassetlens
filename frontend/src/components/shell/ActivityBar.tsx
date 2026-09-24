/**
 * ActivityBar（v3 §二）：左缘窄图标条 ≤48px，永远 3 图标——💬对话 / 🗂管理台 / ⚙设置。
 * 点击滑出对应面板；再点同图标/Esc 收起（收起逻辑在 App.tsx）。
 */
import { Tooltip } from 'antd';
import { MessageOutlined, AppstoreOutlined, SettingOutlined } from '@ant-design/icons';

export type ShellPanel = 'chat' | 'console' | 'settings' | null;

const ITEMS: { key: Exclude<ShellPanel, null>; icon: React.ReactNode; tip: string }[] = [
  { key: 'chat', icon: <MessageOutlined />, tip: '对话' },
  { key: 'console', icon: <AppstoreOutlined />, tip: '管理台' },
  { key: 'settings', icon: <SettingOutlined />, tip: '设置' },
];

export default function ActivityBar({ activePanel, onToggle }: {
  activePanel: ShellPanel; onToggle: (p: Exclude<ShellPanel, null>) => void;
}) {
  return (
    <div
      data-testid="activity-bar"
      data-shell-iconbar=""  // UX3批1：外点关闭豁免区标记
      style={{
        width: 48, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center',
        padding: '12px 0', gap: 8, background: 'var(--bg-content, #fff)',
        borderRight: '1px solid var(--border-subtle, #eee)',
      }}
    >
      {ITEMS.map((it) => (
        <Tooltip key={it.key} title={it.tip} placement="right">
          <button
            type="button"
            data-testid={`activity-${it.key}`}
            onClick={() => onToggle(it.key)}
            style={{
              width: 36, height: 36, border: 'none', borderRadius: 10, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17,
              background: activePanel === it.key ? 'var(--primary-50, #eff6ff)' : 'transparent',
              color: activePanel === it.key ? 'var(--brand, #2563EB)' : 'var(--text-secondary, #666)',
            }}
          >
            {it.icon}
          </button>
        </Tooltip>
      ))}
    </div>
  );
}
