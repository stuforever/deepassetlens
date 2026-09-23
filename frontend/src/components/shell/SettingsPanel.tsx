/**
 * SettingsPanel（v3 §二，批③ §十三换壳；批⑥ v4§5.3 八分区）：⚙设置面板内容——设置中心 8 分区镜像。
 * 数据源=SETTINGS_SECTIONS（pages/settings/SettingsLayout 注册表，单一事实源——面板与
 * 二级侧栏同口径）；批③过渡期挂面板底部的平台能力/治理分组已收口进分区（技能管理/金标锚定/
 * 专家赋权→智能体，知识库→知识与检索，运行观测/引擎工作台→数据治理，安全控制中心→安全，
 * 记忆管理→数据探索，LLM 配置→模型与服务）。
 * 平台路径项（/skills 等）与 /settings 项混排——点击即导航，面包屑由目标页自理。
 * 宽度/背景/边框由统一壳 ShellPanel 提供（本组件只渲染滚动内容区）。
 */
import { SETTINGS_SECTIONS } from '../../pages/settings/SettingsLayout';

export function SettingsPanel({ onNavigate, onClose }: {
  onNavigate: (path: string) => void; onClose: () => void;
}) {
  return (
    <div
      data-testid="settings-panel"
      style={{ overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 4 }}
    >
      {SETTINGS_SECTIONS.filter((s) => s.items.length > 0).map((section) => (
        <div key={section.key} data-testid={`settings-panel-section-${section.key}`}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary, #888)', margin: '6px 0 4px', fontWeight: 600 }}>
            {section.title}
          </div>
          {section.items.map((it) => (
            <div
              key={it.path}
              role="button"
              tabIndex={0}
              data-testid={`settings-panel-item-${it.path.replace(/\//g, '-').replace(/^-/, '')}`}
              onClick={() => { onNavigate(it.path); onClose(); }}
              onKeyDown={(e) => { if (e.key === 'Enter') { onNavigate(it.path); onClose(); } }}
              style={{
                display: 'flex', gap: 8, alignItems: 'center', padding: '7px 10px',
                borderRadius: 8, cursor: 'pointer', fontSize: 13,
              }}
              onMouseEnter={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'var(--muted, #f5f5f5)'; }}
              onMouseLeave={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
            >
              <it.icon />
              <span>{it.label}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default SettingsPanel;
