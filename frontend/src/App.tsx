import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Input, AutoComplete, ConfigProvider, Badge } from 'antd';
import { SearchOutlined, ThunderboltFilled } from '@ant-design/icons';
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
import { expertPageRoutes, matchExpertPage } from './config/expertPages';

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

  // ⑤R F1：参数路由（:mid 等）页签记忆——切回页签时导航到最后一次真实路径（字面 ':mid' 不可导航）
  const lastPathByMenuKey = useRef<Map<string, string>>(new Map());

  const switchToMenu = useCallback(
    (menuKey: string) => {
      // 附件四 A-1：专家区动态键（e:{slug}:{chat|admin|page}）——EXPERT_PAGES 注册表优先，
      // chat/admin 动态拼路径（menuKeyToPath 静态表不覆盖 /e/ 动态段——与下方 L80 同款运行时分支）。
      if (menuKey.startsWith('e:')) {
        const segs = menuKey.split(':');
        const slug = segs[1] || 'wenshu';
        // ⑤R F4（批11）：legacy 三段键 e:{slug}:admin → 旧后台骨架；四段键（e:sishu:admin:mq 等）
        // =后台注册页，走下方 EXPERT_PAGES 查表（母题库管理/书源管理/教学设置三项顶级入口）
        if (segs.length === 3 && segs[2] === 'admin') { navigate(`/e/${slug}/admin`); return; }
        const pg = expertPageRoutes().find((p) => p.menuKey === menuKey);
        if (pg && pg.path.includes(':')) {
          navigate(lastPathByMenuKey.current.get(menuKey) || pg.path);
          return;
        }
        navigate(pg ? pg.path : `/e/${slug}/chat`);
        return;
      }
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
    // 专家地基①：/e/{slug}/chat 动态段——静态映射不覆盖，运行时分支（页签 key 沿 menuKey）
    // ⑤批4（⑤e）：专家自定义页精确匹配（EXPERT_PAGES 注册表 menuKey= e:{slug}:{page}），
    // 未命中才回退 chat 页签（四页与 chat 各自独立页签——KeepAlive 互不串扰）。
    if (location.pathname.startsWith('/e/')) {
      const slug = location.pathname.split('/')[2] || 'wenshu';
      // 附件四 A-1：后台路径特判（admin 不在 EXPERT_PAGES 注册表——独立页签）
      const isAdminPath = location.pathname.endsWith('/admin');
      // ⑤R F1：先精确后参数模式（:mid 详情页等参数路由——原精确匹配永不命中落 chat 兜底）
      const pageCfg = matchExpertPage(location.pathname);
      const menuKey = isAdminPath ? `e:${slug}:admin` : (pageCfg ? pageCfg.menuKey : `e:${slug}:chat`);
      const label = isAdminPath ? `${slug} 后台` : (pageCfg ? pageCfg.label : `专家 ${slug}`);
      if (menuKey.startsWith('e:')) lastPathByMenuKey.current.set(menuKey, location.pathname);
      setPageTabs((prev) => {
        if (prev.find((t) => t.key === menuKey)) return prev;
        const newTabs = [...prev, { key: menuKey, label, menuKey }];
        return newTabs.length > 12 ? newTabs.slice(newTabs.length - 12) : newTabs;
      });
      setActiveTabKey(menuKey);
      setActiveMenuKey(menuKey);
      return;
    }
    const menuKey = pathToMenuKey[location.pathname];
    if (!menuKey) return;
    if (menuKey === 'graph') setCanvasMode('force');
    else if (menuKey === 'tree_model') setCanvasMode('quad');
    else if (menuKey === 'matrix_model') setCanvasMode('matrix');
    else if (menuKey === 'gallery') setCanvasMode('neo4j');
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

  const headerTitle = useMemo(() => 'DeepAssetLens', []);

  // B1 美化：环境徽标（dev=warning 色点 / prod=success 色点）
  const isProdEnv = process.env.NODE_ENV === 'production' && process.env.REACT_APP_ENV !== 'dev';

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{ token: antdThemeToken, components: antdComponents, cssVar: { key: 'tupu' } }}
    >
      <Layout style={{ height: '100vh', overflow: 'hidden' }}>
        {/* 顶部栏 48px（B1 美化：玻璃拟态 = 半透明白 + backdrop blur） */}
        <Header
          style={{
            background: 'rgba(255,255,255,.8)',
            WebkitBackdropFilter: 'blur(8px) saturate(1.5)',
            backdropFilter: 'blur(8px) saturate(1.5)',
            borderBottom: `1px solid ${tokens.colors.border}`,
            padding: 0,
            height: tokens.layout.headerHeight,
            lineHeight: 'normal',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingInline: tokens.space.s5,
            flexShrink: 0,
            zIndex: 100,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: tokens.space.s3 }}>
            {/* B1 美化：24×24 渐变 logo 块（品牌渐变克制使用：此处 + AI 徽标 + 主发送按钮） */}
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: tokens.radius.default,
                background: tokens.brandGradient,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <ThunderboltFilled style={{ color: tokens.colors.textInverse, fontSize: 14 }} />
            </div>
            <div
              style={{
                fontWeight: tokens.fontWeight.bold,
                fontSize: 16,
                color: tokens.colors.textPrimary,
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
            <Badge status={isProdEnv ? 'success' : 'warning'} text={isProdEnv ? '生产' : '开发'} />
            <AutoComplete
              value={searchText}
              onChange={setSearchText}
              options={searchOptions}
              onSelect={(value: string) => {
                switchToMenu(value);
                setSearchText('');
              }}
              style={{ width: 260 }}
              placeholder="搜索页面…"
            >
              <Input
                className="dal-global-search"
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
