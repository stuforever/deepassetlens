/**
 * AppTabs - 页面页签条 + KeepAlive 内容区。
 *
 * 标签栏：自定义 div（token 配色），右键 Dropdown 提供"关闭其他/关闭右侧/关闭全部"。
 * 固定首页(home)不可关。
 * 内容区：KeepAlive -- 所有已开页签同时挂载，display:none 隐藏非活动页，切换不重载。
 */
import React, { Suspense, useRef } from 'react';
import { Dropdown, Spin, type MenuProps } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import type { RouteConfig } from '../routes';
import { tokens } from '../theme/tokens';

export type PageTab = { key: string; label: string; menuKey: string };

const PINNED_KEY = 'home'; // 固定首页不可关

interface AppTabsProps {
  pageTabs: PageTab[];
  activeTabKey: string;
  routes: RouteConfig[];
  canvasMenuKeys: Set<string>;
  needsOpenTarget: Set<string>;
  onSwitch: (menuKey: string) => void;
  onClose: (key: string) => void;
  onCloseOthers: (key: string) => void;
  onCloseRight: (key: string) => void;
  onCloseAll: () => void;
  onOpenTarget: (menuKey: string) => void;
}

const AppTabs: React.FC<AppTabsProps> = ({
  pageTabs,
  activeTabKey,
  routes,
  canvasMenuKeys,
  needsOpenTarget,
  onSwitch,
  onClose,
  onCloseOthers,
  onCloseRight,
  onCloseAll,
  onOpenTarget,
}) => {
  const ctxKeyRef = useRef<string>('');

  const buildContextMenu = (tab: PageTab): MenuProps['items'] => {
    const isPinned = tab.key === PINNED_KEY;
    const idx = pageTabs.findIndex((t) => t.key === tab.key);
    const hasRight = idx < pageTabs.length - 1;
    const hasOther = pageTabs.length > 1 && (pageTabs.length > 2 || pageTabs[0].key !== tab.key);
    return [
      { key: 'closeOthers', label: '关闭其他', disabled: !hasOther, onClick: () => onCloseOthers(tab.key) },
      { key: 'closeRight', label: '关闭右侧', disabled: !hasRight, onClick: () => onCloseRight(tab.key) },
      { type: 'divider' },
      { key: 'closeAll', label: '关闭全部', disabled: pageTabs.length <= 1, onClick: () => onCloseAll() },
    ];
  };

  return (
    <>
      {/* 标签栏（B1 美化：背景 bgPage，让激活页签白底"连接"内容区） */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          height: tokens.layout.tabsHeight,
          padding: `0 ${tokens.space.s3}px`,
          background: tokens.colors.bgPage,
          borderBottom: `1px solid ${tokens.colors.border}`,
          flexShrink: 0,
          overflowX: 'auto',
          overflowY: 'hidden',
          gap: tokens.space.s1,
        }}
      >
        {pageTabs.map((tab) => {
          const isActive = tab.key === activeTabKey;
          const isPinned = tab.key === PINNED_KEY;
          const tabNode = (
            <div
              onClick={() => onSwitch(tab.menuKey)}
              onContextMenu={(e) => { ctxKeyRef.current = tab.key; }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: `0 ${tokens.space.s3}px`,
                height: 28,
                flexShrink: 0,
                cursor: 'pointer',
                fontSize: 13,
                whiteSpace: 'nowrap',
                // B1 美化：Chrome 页签形态 —— 激活 = 白底 + 2px 主色顶边 + 仅顶部圆角
                background: isActive ? tokens.colors.bgContent : 'transparent',
                color: isActive ? tokens.colors.primary : tokens.colors.textTertiary,
                fontWeight: isActive ? tokens.fontWeight.semibold : tokens.fontWeight.regular,
                borderTop: isActive ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                borderRadius: isActive ? '6px 6px 0 0' : tokens.radius.default,
                transition: `color ${tokens.motion.duration.fast}ms ${tokens.motion.easing.enter}, background ${tokens.motion.duration.fast}ms ${tokens.motion.easing.enter}`,
              }}
            >
              {tab.label}
              {!isPinned ? (
                <CloseOutlined
                  style={{ fontSize: 10, color: tokens.colors.textDisabled }}
                  onClick={(e) => { e.stopPropagation(); onClose(tab.key); }}
                />
              ) : null}
            </div>
          );
          return (
            <Dropdown key={tab.key} trigger={['contextMenu']} menu={{ items: buildContextMenu(tab) }}>
              {tabNode}
            </Dropdown>
          );
        })}
      </div>

      {/* KeepAlive 内容区：外层 Suspense 兜底路由 lazy 的首次加载（不影响已挂载页签） */}
      <Suspense fallback={<div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin size="large" /></div>}>
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          {pageTabs.map((tab) => {
            // 专家地基①：动态专家页签（e:{slug}:chat）回退到 expert_chat 路由渲染（KeepAlive 无路径匹配）
            const route = routes.find((r) => r.menuKey === tab.menuKey)
              || (tab.menuKey.startsWith('e:') ? routes.find((r) => r.menuKey === 'expert_chat') : undefined);
            if (!route) return null;
            const Component = route.element;
            const isActive = tab.key === activeTabKey;
            const isCanvas = canvasMenuKeys.has(route.menuKey);
            return (
              <div
                key={tab.key}
                style={{
                  display: isActive ? 'flex' : 'none',
                  flex: 1,
                  overflow: 'hidden',
                  flexDirection: 'column',
                  minHeight: 0,
                  padding: isCanvas ? 0 : tokens.layout.contentPadding,
                }}
              >
                {needsOpenTarget.has(route.menuKey) ? <Component onOpenTarget={onOpenTarget} /> : <Component />}
              </div>
            );
          })}
        </div>
      </Suspense>
    </>
  );
};

export default AppTabs;
