import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Input, AutoComplete, ConfigProvider, Spin } from 'antd';
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
import ActivityBar, { type ShellPanel as ShellPanelId } from './components/shell/ActivityBar';
import NavPanel from './components/shell/NavPanel';
import ChatPanel from './components/shell/ChatPanel';
import SettingsPanel from './components/shell/SettingsPanel';
import ShellPanel, { PANEL_WIDTH_DEFAULT } from './components/shell/ShellPanel';
import CommandPalette from './components/shell/CommandPalette';
import AppTabs, { type PageTab } from './components/AppTabs';
import { expertPageRoutes, matchExpertPage } from './config/expertPages';

const { Header, Content } = Layout;

// 批③ v4 §十三：三面板统一壳标题（调用方传入 ShellPanel；emoji 直接放字符串，文件内已有 emoji 先例）
const SHELL_PANEL_TITLES: Record<Exclude<ShellPanelId, null>, string> = {
  chat: '💬 对话',
  console: '🗂 管理台',
  settings: '⚙ 设置',
};

// 三轨M6(U1) D1：A 模板页（对话型）取消页签——切走即卸载（ChatGPT 一致），历史入口=侧栏最近对话
const TABLESS_MENU_KEYS = (menuKey: string): boolean =>
  menuKey === 'portal' || menuKey === 'home' || /^e:[^:]+:chat$/.test(menuKey);

const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const setActiveMenuKey = useStore((state) => state.setActiveMenuKey);

  // 三轨M6(U1) D1：/home → / 重定向（老链接兼容；pathToMenuKey.home 保留仅作映射）
  useEffect(() => {
    if (location.pathname === '/home') navigate('/', { replace: true });
  }, [location.pathname, navigate]);

  const currentMenu = pathToMenuKey[location.pathname] || (location.pathname.startsWith('/e/') ? '' : 'portal');

  // 批③ §十三：图标条 + 统一三态壳（ShellPanel：floating 浮层 / pinned 钉住 / 收起）——Esc 收起（v3 §二 沿革）
  const [shellPanel, setShellPanel] = useState<ShellPanelId>(null);
  // 批③ v4 §十三：三面板钉住状态各自独立、localStorage 持久化（全站记住）
  const [pinnedPanels, setPinnedPanels] = useState<Record<'chat' | 'console' | 'settings', boolean>>(() => ({
    chat: localStorage.getItem('shell:pinned:chat') === '1',
    console: localStorage.getItem('shell:pinned:console') === '1',
    settings: localStorage.getItem('shell:pinned:settings') === '1',
  }));
  const togglePin = (p: 'chat' | 'console' | 'settings') =>
    setPinnedPanels((m) => {
      const next = { ...m, [p]: !m[p] };
      localStorage.setItem(`shell:pinned:${p}`, next[p] ? '1' : '0');
      return next;
    });
  // UX批② 反馈④：三面板可拖宽——默认 400，拖动实时回报（commit=false），松手落库 shell:width:{panel}
  const [panelWidths, setPanelWidths] = useState<Record<'chat' | 'console' | 'settings', number>>(() => ({
    chat: Number(localStorage.getItem('shell:width:chat')) || PANEL_WIDTH_DEFAULT,
    console: Number(localStorage.getItem('shell:width:console')) || PANEL_WIDTH_DEFAULT,
    settings: Number(localStorage.getItem('shell:width:settings')) || PANEL_WIDTH_DEFAULT,
  }));
  const changePanelWidth = (p: 'chat' | 'console' | 'settings', w: number, commit: boolean) => {
    setPanelWidths((m) => ({ ...m, [p]: w }));
    if (commit) localStorage.setItem(`shell:width:${p}`, String(w));
  };

  // UX3批1（P0-A）：浮层面板外点关闭改 pointerdown-outside——透明 backdrop 会吃掉主区第一击
  useEffect(() => {
    if (!shellPanel || pinnedPanels[shellPanel]) return;
    const onDoc = (e: PointerEvent) => {
      const t = e.target as Element | null;
      if (t?.closest?.('[data-testid="shell-panel"], [data-shell-iconbar]')) return;
      setShellPanel(null);
    };
    document.addEventListener('pointerdown', onDoc);
    return () => document.removeEventListener('pointerdown', onDoc);
  }, [shellPanel, pinnedPanels]);
  // UX2批⑦（反馈⑥套娃）：钉住=锁定——面板内导航/会话点击不再自隐（原 onClose 无视钉住态强制隐藏）
  const closeUnlessPinned = (p: 'chat' | 'console' | 'settings') => {
    if (!pinnedPanels[p]) setShellPanel(null);
  };
  // v3 #8：⌘K 命令面板
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [pageTabs, setPageTabs] = useState<PageTab[]>([]);
  const [activeTabKey, setActiveTabKey] = useState('');

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

  // v3 §二：Esc 收起滑出面板
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShellPanel(null);
      // v3 #8：Ctrl+K / ⌘K 唤起命令面板
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setCmdkOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

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
      if (!TABLESS_MENU_KEYS(menuKey)) {
        setPageTabs((prev) => {
          if (prev.find((t) => t.key === menuKey)) return prev;
          const newTabs = [...prev, { key: menuKey, label, menuKey }];
          return newTabs.length > 12 ? newTabs.slice(newTabs.length - 12) : newTabs;
        });
        setActiveTabKey(menuKey);
      }
      setActiveMenuKey(menuKey);
      return;
    }
    const menuKey = pathToMenuKey[location.pathname];
    if (!menuKey) return;
    // R#8：旧 canvasMode 映射删除——?view= 深链由 GraphManager 单一管理（init effect 随 search 生效）；
    // 此处按菜单硬设视图会覆盖深链/图内切视图（回归：/graph?view=matrix 落 force）。
    const label = MENU_LABELS[menuKey] || menuKey;
    if (!TABLESS_MENU_KEYS(menuKey)) {
      setPageTabs((prev) => {
        if (prev.find((t) => t.key === menuKey)) return prev;
        const newTabs = [...prev, { key: menuKey, label, menuKey }];
        return newTabs.length > 12 ? newTabs.slice(newTabs.length - 12) : newTabs;
      });
      setActiveTabKey(menuKey);
    }
    setActiveMenuKey(menuKey);
  }, [location.pathname, setActiveMenuKey, navigate]);

  // 关闭页签
  const closeTab = useCallback(
    (targetKey: string) => {
      setPageTabs((prev) => {
        const filtered = prev.filter((t) => t.key !== targetKey);
        return filtered.length === 0 ? prev : filtered;
      });
      setActiveTabKey((cur) => {
        if (cur === targetKey) {
          const filtered = pageTabs.filter((t) => t.key !== targetKey);
          const next = filtered[filtered.length - 1];
          if (next && next.menuKey) navigate(menuKeyToPath[next.menuKey] || '/');
          return next ? next.key : '';
        }
        return cur;
      });
    },
    [pageTabs, navigate]
  );

  const closeOthers = useCallback(
    (keepKey: string) => {
      setPageTabs((prev) => prev.filter((t) => t.key === keepKey));
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
    setPageTabs([]);
    setActiveTabKey('');
    navigate('/');
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

  // 三轨M6(U1) §2.1：⌘K/Ctrl+K 全局聚焦搜索（window keydown 一处）
  const searchRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        const el = document.querySelector<HTMLInputElement>('.dal-global-search input, input.dal-global-search');
        (el || searchRef.current)?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  void searchRef;

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
            <div
              role="button"
              tabIndex={0}
              data-testid="global-search"
              onClick={() => setCmdkOpen(true)}
              style={{
                width: 320, height: 32, display: 'flex', alignItems: 'center', gap: 8,
                padding: '0 12px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                background: 'var(--bg-content, #fff)', border: '1px solid var(--border-subtle, #e5e7eb)',
                color: 'var(--text-tertiary, #999)',
              }}
            >
              <SearchOutlined style={{ color: tokens.colors.textTertiary }} />
              搜索页面…（Ctrl+K）
            </div>
            <UserBadge />
          </div>
        </Header>

        <Layout style={{ flexDirection: 'row', overflow: 'hidden', flex: 1, minHeight: 0, position: 'relative' }}>
          {/* 左侧：图标条 + 统一三态壳（批③ v4 §十三：floating 浮层不挤主区 / pinned 流内让位；Esc/再点/点外部收起） */}
          <ActivityBar
            activePanel={shellPanel}
            onToggle={(p) => setShellPanel(shellPanel === p ? null : p)}
          />
          {shellPanel && (
            <>
              {/* UX3批1（P0-A）：透明 backdrop 已删——外点关闭改 document pointerdown-outside
                  （backdrop 会吃掉主区第一击：点发送/表格等首击只收面板不出效果） */}
              <ShellPanel
                panel={shellPanel}
                title={SHELL_PANEL_TITLES[shellPanel]}
                pinned={pinnedPanels[shellPanel]}
                width={panelWidths[shellPanel]}
                onWidthChange={(w, commit) => changePanelWidth(shellPanel, w, commit)}
                onTogglePin={() => togglePin(shellPanel)}
                onClose={() => closeUnlessPinned(shellPanel)}
              >
                {shellPanel === 'console' && (
                  <NavPanel visible onClose={() => closeUnlessPinned('console')} onNavigate={(path) => navigate(path)} />
                )}
                {shellPanel === 'chat' && <ChatPanel onClose={() => closeUnlessPinned('chat')} />}
                {shellPanel === 'settings' && <SettingsPanel onClose={() => closeUnlessPinned('settings')} onNavigate={(path) => navigate(path)} />}
              </ShellPanel>
            </>
          )}
          <CommandPalette open={cmdkOpen} onClose={() => setCmdkOpen(false)} />
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
            {TABLESS_MENU_KEYS(currentMenu) ? (
              /* 三轨M6(U1) D1：tabless 直渲单实例（不进 KeepAlive 多开——切走即卸载） */
              (() => {
                const tablessRoute =
                  routes.find((r) => r.menuKey === currentMenu)
                  || (currentMenu.startsWith('e:') ? routes.find((r) => r.menuKey === 'expert_chat') : undefined);
                if (!tablessRoute) return null;
                const TComp = tablessRoute.element;
                const isCanvas = CANVAS_MENU_KEYS.has(tablessRoute.menuKey);
                return (
                  <div
                    style={{
                      display: 'flex', flex: 1, overflow: 'hidden',
                      flexDirection: 'column', minHeight: 0,
                      padding: isCanvas ? 0 : tokens.layout.contentPadding,
                    }}
                  >
                    <Suspense fallback={
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Spin size="large" />
                      </div>
                    }>
                      {NEEDS_OPEN_TARGET.has(tablessRoute.menuKey)
                        ? <TComp onOpenTarget={handleOpenTarget} />
                        : <TComp />}
                    </Suspense>
                  </div>
                );
              })()
            ) : (
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
            )}
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

export default App;
