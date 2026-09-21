/**
 * SettingsPanel（v3 §二）：⚙设置滑出面板——设置中心 6 分区入口平铺，进 /settings 体系。
 * 数据源=SETTINGS_CATEGORIES 顶层六分区（lib/settings-nav.ts，E-78⑤ 终版）。
 */
import { SETTINGS_CATEGORIES } from '../../lib/settings-nav';

export function SettingsPanel({ onNavigate, onClose }: {
  onNavigate: (path: string) => void; onClose: () => void;
}) {
  return (
    <div
      data-testid="settings-panel"
      style={{
        width: 300, flexShrink: 0, overflowY: 'auto', padding: 16,
        background: 'var(--bg-content, #fff)', borderRight: '1px solid var(--border-subtle, #eee)',
      }}
    >
      <div style={{ fontSize: 12, color: 'var(--text-secondary, #888)', margin: '2px 0 8px', fontWeight: 600 }}>
        设置中心
      </div>
      {SETTINGS_CATEGORIES.map((c) => (
        <div
          key={c.key}
          role="button"
          tabIndex={0}
          data-testid={`settings-panel-${c.key}`}
          onClick={() => { onNavigate(c.href); onClose(); }}
          onKeyDown={(e) => { if (e.key === 'Enter') { onNavigate(c.href); onClose(); } }}
          style={{
            display: 'flex', gap: 8, alignItems: 'center', padding: '8px 10px',
            borderRadius: 8, cursor: 'pointer', fontSize: 13,
          }}
          onMouseEnter={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'var(--muted, #f5f5f5)'; }}
          onMouseLeave={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
        >
          <c.icon />
          <span>{c.label.zh}</span>
        </div>
      ))}
    </div>
  );
}

export default SettingsPanel;
