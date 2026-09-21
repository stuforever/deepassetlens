/**
 * NavPanel（v3 §二）：管理台滑出面板——六组平铺、无折叠层级，点项开主区页签。
 * 数据源=NAV_PANEL_GROUPS（menuKey 全复用既有注册表，menuKeyToPath 映射跳转）。
 */
import { NAV_PANEL_GROUPS, menuKeyToPath } from '../../config/navigation';

export function NavPanel({ visible, onNavigate, onClose }: {
  visible: boolean; onNavigate: (path: string) => void; onClose: () => void;
}) {
  if (!visible) return null;
  return (
    <div
      data-testid="nav-panel"
      style={{
        width: 560, flexShrink: 0, overflowY: 'auto', padding: 16,
        background: 'var(--bg-content, #fff)', borderRight: '1px solid var(--border-subtle, #eee)',
      }}
    >
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px 24px' }}>
        {NAV_PANEL_GROUPS.map((g) => (
          <div key={g.title} data-testid={`nav-panel-group-${g.title}`}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary, #888)', margin: '4px 0 8px', fontWeight: 600 }}>
              {g.title}
            </div>
            {g.items.map((it) => {
              const path = menuKeyToPath[it.menuKey] || '/';
              return (
                <div
                  key={it.menuKey}
                  role="button"
                  tabIndex={0}
                  data-testid={`nav-item-${it.menuKey}`}
                  onClick={() => { onNavigate(path); onClose(); }}
                  onKeyDown={(e) => { if (e.key === 'Enter') { onNavigate(path); onClose(); } }}
                  style={{
                    display: 'flex', gap: 8, alignItems: 'center', padding: '6px 8px',
                    borderRadius: 8, cursor: 'pointer', fontSize: 13,
                  }}
                  onMouseEnter={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'var(--muted, #f5f5f5)'; }}
                  onMouseLeave={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
                >
                  {it.icon}
                  <span>{it.label}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

export default NavPanel;
