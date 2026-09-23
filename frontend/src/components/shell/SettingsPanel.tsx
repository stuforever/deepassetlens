/**
 * SettingsPanel（v3 §二，批③ §十三换壳）：⚙设置面板内容——设置中心 6 分区入口平铺，进 /settings 体系。
 * 数据源=SETTINGS_CATEGORIES 顶层六分区（lib/settings-nav.ts，E-78⑤ 终版）；
 * 宽度/背景/边框由统一壳 ShellPanel 提供（本组件只渲染滚动内容区）。
 */
import { SETTINGS_CATEGORIES } from '../../lib/settings-nav';
import { MENU_LABELS, menuKeyToPath } from '../../config/navigation';

// 批③ §5.3 过渡期保留（Task 10 设置八分区落地后移除）：管理台面板原「平台能力」「治理与系统」
// 两组移入设置中心——过渡期成员暂挂本面板底部，label/path 复用 navigation 注册表键值。
const TRANSITION_PANEL_ITEMS = ['skills', 'vector_manage', 'golden_qa', 'governance', 'engine_workbench', 'llmconfig', 'memory_admin', 'expert_grants', 'security_controls'];

export function SettingsPanel({ onNavigate, onClose }: {
  onNavigate: (path: string) => void; onClose: () => void;
}) {
  return (
    <div
      data-testid="settings-panel"
      style={{
        overflowY: 'auto', padding: 16,
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
      {/* 批③ §5.3 过渡期保留（Task 10 设置八分区落地后移除） */}
      <div style={{ borderTop: '1px solid var(--border-subtle, #eee)', margin: '10px 0 8px' }} />
      <div style={{ fontSize: 12, color: 'var(--text-secondary, #888)', margin: '2px 0 8px', fontWeight: 600 }}>
        平台能力与治理（过渡期）
      </div>
      {TRANSITION_PANEL_ITEMS.map((key) => (
        <div
          key={key}
          role="button"
          tabIndex={0}
          data-testid={`settings-panel-navitem-${key}`}
          onClick={() => { onNavigate(menuKeyToPath[key]); onClose(); }}
          onKeyDown={(e) => { if (e.key === 'Enter') { onNavigate(menuKeyToPath[key]); onClose(); } }}
          style={{
            display: 'flex', gap: 8, alignItems: 'center', padding: '8px 10px',
            borderRadius: 8, cursor: 'pointer', fontSize: 13,
          }}
          onMouseEnter={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'var(--muted, #f5f5f5)'; }}
          onMouseLeave={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
        >
          <span>{MENU_LABELS[key]}</span>
        </div>
      ))}
    </div>
  );
}

export default SettingsPanel;
