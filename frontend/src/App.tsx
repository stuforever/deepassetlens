import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Input, AutoComplete, theme, ConfigProvider } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';

import { routes } from './routes';
import {
  NAV_GROUPS,
  MENU_LABELS,
  menuKeyToPath,
  pathToMenuKey,
  NEEDS_OPEN_TARGET,
  CANVAS_MENU_KEYS,
} from './config/navigation';
import { useStore } from './store/useStore';
import { antdThemeToken, antdComponents, tokens } from './theme/tokens';
import UserBadge from './components/UserBadge';
import AppSider from './components/AppSider';
import AppTabs, { type PageTab } from './components/AppTabs';

const { Header, Content } = Layout;

const PINNED_KEY = 'home';

const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const setCanvasMode = useStore((state) => state.setCanvasMode);
  const setActiveMenuKey = useStore((state) => state.setActiveMenuKey);

  const currentMenu = pathToMenuKey[location.pathname] || 'home';

  const [collapsed, setCollapsed] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [pageTabs, setPageTabs] = useState<PageTab[]>([
    { key: PINNED_KEY, label: MENU_LABELS[PINNED_KEY] || '首页', menuKey: PINNED_KEY },
  ]);
  const [activeTabKey, setActiveTabKey] = useState(PINNED_KEY);

  const switchToMenu = useCallback(
    (menuKey: string) => {
      const path = menuKeyToPath[menuKey];
      if (path) navigate(path);
    },
    [navigate]
  );

  // 全局搜索：过滤导航项，选中后跳转
  const searchOptions = useMemo(() => {
    if (!searchText) return [];
    const lower = searchText.toLowerCase();
    return NAV_GROUPS.flatMap((g) =>
      g.items
        .filter((it) => it.label.toLowerCase().includes(lower))
        .map((it) => ({
          value: it.menuKey,
          label: (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
              <it.icon style={{ color: tokens.colors.textTertiary }} />
              <span>
                <span style={{ color: tokens.colors.textTertiary }}>{g.title} / </span>
                {it.label}
              </span>
              {it.placeholder && (
                <span style={{ fontSize: 10, color: tokens.colors.warning }}>开发中</span>
              )}
            </div>
          ),
        }))
    ).slice(0, 10);
  }, [searchText]);

  // 路由变化 -> 同步页签/画布模式/激活 key
  useEffect(() => {
    // 默认首页重定向
    if (location.pathname === '/') {
      navigate('/home', { replace: true });
      return;
    }
    const menuKey = pathToMenuKey[location.pathname];
    if (!menuKey) return;
    if (menuKey === 'graph') setCanvasMode('force');
    else if (menuKey === 'tree_model') setCanvasMode('quad');
    else if (menuKey === 'matrix_model') setCanvasMode('matrix');
    const label = MENU_LABELS[menuKey] || menuKey;
    setPageTabs((prev) => {
      if (prev.find((t) => t.key === menuKey)) return prev;
      const newTabs = [...prev, { key: menuKey, label, menuKey }];
      return newTabs.length > 12 ? newTabs.slice(newTabs.length - 12) : newTabs;
    });
    setActiveTabKey(menuKey);
    setActiveMenuKey(menuKey);
  }, [location.pathname, setCanvasMode, setActiveMenuKey, navigate]);

  // 关闭页签
  const closeTab = useCallback(
    (targetKey: string) => {
      if (targetKey === PINNED_KEY) return;
      setPageTabs((prev) => {
        const filtered = prev.filter((t) => t.key !== targetKey);
        return filtered.length === 0 ? prev : filtered;
      });
      setActiveTabKey((cur) => {
        if (cur === targetKey) {
          const filtered = pageTabs.filter((t) => t.key !== targetKey);
          const next = filtered[filtered.length - 1] || { key: PINNED_KEY, menuKey: PINNED_KEY };
          navigate(menuKeyToPath[next.menuKey] || '/home');
          return next.key;
        }
        return cur;
      });
    },
    [pageTabs, navigate]
  );

  const closeOthers = useCallback(
    (keepKey: string) => {
      setPageTabs((prev) => prev.filter((t) => t.key === keepKey || t.key === PINNED_KEY));
    },
    []
  );

  const closeRight = useCallback(
    (keepKey: string) => {
      setPageTabs((prev) => {
        const idx = prev.findIndex((t) => t.key === keepKey);
        if (idx < 0) return prev;
        return prev.slice(0, idx + 1).filter((t) => true);
      });
    },
    []
  );

  const closeAll = useCallback(() => {
    setPageTabs([{ key: PINNED_KEY, label: MENU_LABELS[PINNED_KEY] || '首页', menuKey: PINNED_KEY }]);
    setActiveTabKey(PINNED_KEY);
    navigate('/home');
  }, [navigate]);

  // 全局 navigate 事件（非菜单入口跳转）
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.menu) switchToMenu(detail.menu);
    };
    window.addEventListener('navigate', handler);
    return () => window.removeEventListener('navigate', handler);
  }, [switchToMenu]);

  const handleOpenTarget = useCallback(
    (menuKey: string) => switchToMenu(menuKey),
    [switchToMenu]
  );

  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const headerTitle = useMemo(() => 'DeepAssetLens', []);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{ token: antdThemeToken, components: antdComponents, cssVar: { key: 'tupu' } }}
    >
      <Layout style={{ height: '100vh', overflow: 'hidden' }}>
        {/* 顶部栏 48px */}
        <Header
          style={{
            background: colorBgContainer,
            borderBottom: `1px solid ${tokens.colors.border}`,
            padding: 0,
            height: tokens.layout.headerHeight,
            lineHeight: 'normal',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingInline: tokens.space.s5,
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.space.s5 }}>
            <div
              style={{
                fontWeight: tokens.fontWeight.bold,
                fontSize: 16,
                color: tokens.colors.primary,
                whiteSpace: 'nowrap',
                letterSpacing: '-0.01em',
              }}
            >
              {headerTitle}
              <span style={{ fontSize: 12, fontWeight: tokens.fontWeight.regular, color: tokens.colors.textTertiary, marginLeft: tokens.space.s2 }}>
                资产深度探查平台
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.space.s4 }}>
            <AutoComplete
              value={searchText}
              onChange={setSearchText}
              options={searchOptions}
              onSelect={(value: string) => {
                switchToMenu(value);
                setSearchText('');
              }}
              style={{ width: 220 }}
              placeholder="搜索页面…"
            >
              <Input
                prefix={<SearchOutlined style={{ color: tokens.colors.textTertiary }} />}
                allowClear
                onClear={() => setSearchText('')}
              />
            </AutoComplete>
            <UserBadge />
          </div>
        </Header>

        <Layout style={{ flexDirection: 'row', overflow: 'hidden', flex: 1, minHeight: 0 }}>
          {/* 左侧导航 */}
          <AppSider
            collapsed={collapsed}
            onToggle={() => setCollapsed((c) => !c)}
            selectedKey={currentMenu}
            onSelect={switchToMenu}
          />
          {/* 内容区：页签 + KeepAlive */}
          <Content
            style={{
              margin: 0,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              background: tokens.colors.bgPage,
              flex: 1,
              minWidth: 0,
            }}
          >
            <AppTabs
              pageTabs={pageTabs}
              activeTabKey={activeTabKey}
              routes={routes}
              canvasMenuKeys={CANVAS_MENU_KEYS}
              needsOpenTarget={NEEDS_OPEN_TARGET}
              onSwitch={switchToMenu}
              onClose={closeTab}
              onCloseOthers={closeOthers}
              onCloseRight={closeRight}
              onCloseAll={closeAll}
              onOpenTarget={handleOpenTarget}
            />
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

export default App;
