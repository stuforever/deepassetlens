/**
 * AppSider - 左侧导航 + 会话区（可收起 64px）。
 * 上部：数据资产探查（首页顶层项）+ 5 分组 inline Menu（手风琴模式）。
 * 下部：最近对话会话列表（从 Zustand store 读取，点击切到首页并激活该会话）。
 * 底部：收起/展开按钮。
 */
import React, { useState, useEffect, useMemo, useContext, useCallback } from 'react';
import { Layout, Menu, Tooltip, Input, Typography, Popconfirm, message } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
  MessageOutlined,
  CloseOutlined,
  EditOutlined,
  CheckOutlined,
  SearchOutlined,
  CommentOutlined,
  ReadOutlined,
  SettingOutlined,
  DownOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { NAV_GROUPS, HOME_NAV_ITEM } from '../config/navigation';
import { EXPERT_PAGES } from '../config/expertPages';
import { expertsApi } from '../services/api';
import type { ExpertCard } from '../services/api';
import { AuthCtx } from '../auth/AuthGate';
import { tokens } from '../theme/tokens';
import { useStore } from '../store/useStore';
import type { ExpertId } from '../store/useStore';
import { listSessions, updateSessionTitle, deleteSession } from '../pages/tutor/admin/session-api';
import type { SessionSummary } from '../pages/tutor/admin/session-api';

const { Sider } = Layout;
const { Text } = Typography;

const OPEN_KEYS_STORAGE = 'dal_sider_open_keys';

/** 根据 menuKey 找到所属分组 key */
function findGroupKey(menuKey: string): string | undefined {
  for (const g of NAV_GROUPS) {
    if (g.items.some((it) => it.menuKey === menuKey)) return g.key;
  }
  return undefined;
}

interface AppSiderProps {
  collapsed: boolean;
  onToggle: () => void;
  selectedKey: string;
  onSelect: (menuKey: string) => void;
}

const AppSider: React.FC<AppSiderProps> = ({ collapsed, onToggle, selectedKey, onSelect }) => {
  // 附件四 A-1：后台入口可见性（role-based 雏形——A-4 升级 ACL use/manage）
  const { user } = useContext(AuthCtx);
  const isAdminUser = (((user as any)?.roles || []) as string[]).includes('admin');

  // Session store
  const sessions = useStore((s) => s.sessions);
  const activeSessionId = useStore((s) => s.activeSessionId);
  const setActiveSessionId = useStore((s) => s.setActiveSessionId);
  const deleteSessionById = useStore((s) => s.deleteSessionById);
  const renameSessionById = useStore((s) => s.renameSessionById);

  // 会话重命名 UI 状态
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  // 手风琴 openKeys：同时只展开 1 组
  const [openKeys, setOpenKeys] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem(OPEN_KEYS_STORAGE);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return [parsed[0]];
      }
    } catch { /* ignore */ }
    const gk = findGroupKey(selectedKey);
    return gk ? [gk] : [];
  });

  useEffect(() => {
    const gk = findGroupKey(selectedKey);
    if (gk && !openKeys.includes(gk)) {
      setOpenKeys([gk]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKey]);

  useEffect(() => {
    try { localStorage.setItem(OPEN_KEYS_STORAGE, JSON.stringify(openKeys)); } catch { /* ignore */ }
  }, [openKeys]);

  // 专家地基①：拉启用专家卡渲染「专家」动态区（失败静默=空区，不阻导航）
  const [expertCards, setExpertCards] = useState<ExpertCard[]>([]);
  useEffect(() => {
    (async () => {
      try {
        const res = await expertsApi.list({ enabled: true });
        setExpertCards((res.data?.items as ExpertCard[]) || []);
      } catch { /* 静默：门户自身会再拉 */ }
    })();
  }, []);

  const onOpenChange = (keys: string[]) => {
    const latest = keys.find((k) => !openKeys.includes(k));
    setOpenKeys(latest ? [latest] : []);
  };

  // ---- IA 件批2 2.3：会话面板按专家三分组（数据探索/私塾先生/私塾先生h5，q5 统一方案+终审裁定④）----
  const navigate = useNavigate();
  const location = useLocation();
  const createNewSession = useStore((s) => s.createNewSession);
  // h5 组数据源=vendor sessions API（平台两组走本 store 过滤）
  const [h5Sessions, setH5Sessions] = useState<SessionSummary[]>([]);
  const refreshH5Sessions = useCallback(() => {
    listSessions(50, 0).then((rows) => setH5Sessions(rows || [])).catch(() => { /* 静默：h5 组显示空态 */ });
  }, []);
  useEffect(() => {
    void refreshH5Sessions();
  }, [refreshH5Sessions, location.pathname]);
  // 当前路由所属专家（/e/tutor-h5/* → tutor-h5；/e/tutor/* → tutor；其余 → wenshu）
  const currentExpert: ExpertId = location.pathname.startsWith('/e/tutor-h5')
    ? 'tutor-h5'
    : location.pathname.startsWith('/e/tutor')
      ? 'tutor'
      : 'wenshu';
  // 组名=专家卡名实时取（拉取失败回退静态名）；组顺序=当前专家组置顶，其余按固定序
  const groupNameOf = (id: ExpertId, fallback: string) =>
    expertCards.find((c) => c.expert_id === id)?.name || fallback;
  // 分组展开态：当前路由所属专家的组自动展开，其余折叠（手动切换后尊重手动）
  const [sessionGroupsOpen, setSessionGroupsOpen] = useState<Record<string, boolean>>({});
  useEffect(() => {
    setSessionGroupsOpen((prev) => (prev[currentExpert] ? prev : { ...prev, [currentExpert]: true }));
  }, [currentExpert]);
  const activeH5SessionId = (() => {
    try { return new URLSearchParams(location.search).get('session') || ''; } catch { return ''; }
  })();
  const relTime = (ts: number) => {
    if (!ts) return '';
    const t = ts < 1e12 ? ts * 1000 : ts; // vendor updated_at=秒（DT 语义），<1e12 视为秒归一为毫秒
    const d = Date.now() - t;
    if (d < 60_000) return '刚刚';
    if (d < 3_600_000) return `${Math.floor(d / 60_000)}分钟前`;
    if (d < 86_400_000) return `${Math.floor(d / 3_600_000)}小时前`;
    if (d < 7 * 86_400_000) return `${Math.floor(d / 86_400_000)}天前`;
    return new Date(t).toLocaleDateString();
  };

  const items = useMemo(
    () => [
      // 首页顶层项（专家地基①：HOME_NAV_ITEM=专家门户）
      {
        key: HOME_NAV_ITEM.menuKey,
        icon: <HOME_NAV_ITEM.icon />,
        label: HOME_NAV_ITEM.label,
      },
      // 专家地基①：「专家」动态区——启用卡实时渲染。
      // 附件四 A-1：每 enabled 专家从单 chat 项变子菜单（对话+功能页+后台*）。
      // *后台仅 admin 可见（A-4 升级为 ACL use/manage 分层）；EXPERT_PAGES[slug] 空数组
      // 的专家（wenshu）保持现状单 chat 项——等值分支。
      // ⑤R F4（批11）：菜单终版——hideInMenu 页（详情路由/先行版）不出菜单；
      // 后台段=adminTop 三项（母题库管理/书源管理/教学设置，admin-only）。
      ...(expertCards.length > 0
        ? [{
            key: 'expert_section',
            type: 'group' as const,
            label: '专家',
            children: expertCards.flatMap((c) => {
              // ⑤R F4（批11）+R2 修正：adminTop 三项只在 admin 段渲染（从 pages 段排除，
              // 否则同 menuKey 双挂→React 重复 key 告警+菜单项重复）
              const pages = (EXPERT_PAGES[c.expert_id] || []).filter((p) => !p.hideInMenu && !p.adminTop);
              const adminTops = (EXPERT_PAGES[c.expert_id] || []).filter((p) => p.adminTop);
              const adminEntry = isAdminUser
                ? adminTops.map((p) => ({ key: p.menuKey, icon: <SettingOutlined />, label: p.label }))
                : [];
              if (pages.length === 0 && adminEntry.length === 0) {
                return [{ key: `e:${c.expert_id}:chat`, icon: <SearchOutlined />, label: c.name }];
              }
              return [{
                key: `e:${c.expert_id}`,
                icon: <SearchOutlined />,
                label: c.name,
                children: [
                  { key: `e:${c.expert_id}:chat`, icon: <CommentOutlined />, label: '对话' },
                  // IA 批1 后 h5 组 menuKey 前缀=e:tutor-h5:*，与生成对话项同键——过滤防 antd Menu 重复 key
                  ...pages.filter((p) => p.menuKey !== `e:${c.expert_id}:chat`).map((p) => ({ key: p.menuKey, icon: <ReadOutlined />, label: p.label })),
                  ...adminEntry,
                ],
              }];
            }),
          }]
        : []),
      // 专家地基①：既有五组整体归入「平台管理」区（结构零删）
      { key: 'platform_section', type: 'group' as const, label: '平台管理' },
      // 分组子菜单
      ...NAV_GROUPS.map((g) => ({
        key: g.key,
        icon: <g.icon />,
        label: g.title,
        children: g.items.map((it) => ({
          key: it.menuKey,
          icon: <it.icon />,
          label: (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              {it.label}
              {it.placeholder && (
                <span style={{ fontSize: 10, color: tokens.colors.warning, lineHeight: 1 }}>
                  ·开发中
                </span>
              )}
            </span>
          ),
        })),
      })),
    ],
    [expertCards]
  );

  const startEdit = (sid: string, currentTitle: string) => {
    setEditingId(sid);
    setEditTitle(currentTitle);
  };

  const saveEdit = (sid: string) => {
    renameSessionById(sid, editTitle);
    setEditingId(null);
  };

  const handleDelete = async (sid: string) => {
    const ok = await deleteSessionById(sid);
    if (ok) {
      message.success('已删除对话');
    } else {
      message.warning('服务端记忆清理失败，当前会话未删除，下次问答可能仍受旧上下文影响');
    }
  };

  return (
    <Sider
      width={tokens.layout.siderWidth}
      collapsedWidth={tokens.layout.siderCollapsedWidth}
      collapsible
      collapsed={collapsed}
      trigger={null}
      theme="light"
      style={{
        background: tokens.colors.bgContent,
        borderRight: `1px solid ${tokens.colors.border}`,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <div className="dal-sider" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* 导航菜单 */}
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        openKeys={collapsed ? [] : openKeys}
        onOpenChange={onOpenChange}
        items={items}
        onClick={(e) => {
          // 「数据资产探查」= 首页 = 新建（重置为空白欢迎页，不创建空会话）
          if (e.key === HOME_NAV_ITEM.menuKey) {
            setActiveSessionId('');
          }
          onSelect(e.key as string);
        }}
        style={{ borderInlineEnd: 'none', paddingTop: collapsed ? 0 : tokens.space.s2, flexShrink: 0 }}
      />

        {/* 会话区 - 展开时显示（IA 件批2：按专家三分组——数据探索/私塾先生/私塾先生h5） */}
        {!collapsed && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', borderTop: `1px solid ${tokens.colors.border}` }}>
            <div style={{ padding: '6px 8px', flexShrink: 0 }}>
              <Text type="secondary" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.5 }}>最近对话</Text>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '0 4px' }}>
              {([
                { gid: 'wenshu' as ExpertId, label: groupNameOf('wenshu', '数据探索') },
                { gid: 'tutor' as ExpertId, label: groupNameOf('tutor', '私塾先生') },
                { gid: 'tutor-h5' as ExpertId, label: groupNameOf('tutor-h5', '私塾先生h5') },
              ]).map(({ gid, label }) => {
                const isOpen = !!sessionGroupsOpen[gid];
                const platformRows = sessions.filter((s) => s.expertId === gid && s.messages.length > 0);
                const vendorRows = gid === 'tutor-h5' ? [...h5Sessions].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0)) : [];
                const count = gid === 'tutor-h5' ? vendorRows.length : platformRows.length;
                return (
                  <div key={gid} style={{ marginBottom: 2 }}>
                    {/* 组头=专家卡名+新建（新建不重设计：平台组=空白欢迎页会话首条消息时落 expertId；h5 组=无 session 参数新会话） */}
                    <div
                      onClick={() => setSessionGroupsOpen((prev) => ({ ...prev, [gid]: !isOpen }))}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', cursor: 'pointer',
                        color: tokens.colors.textSecondary, fontSize: 11, fontWeight: 600, borderRadius: 4,
                        background: gid === currentExpert ? tokens.colors.primaryBg : 'transparent',
                      }}
                    >
                      {isOpen ? <DownOutlined style={{ fontSize: 9 }} /> : <RightOutlined style={{ fontSize: 9 }} />}
                      <Text style={{ flex: 1, fontSize: 11, fontWeight: 600 }}>{label}</Text>
                      <Tooltip title={`新建${label}对话`}>
                        <PlusOutlined
                          style={{ color: tokens.colors.primary, cursor: 'pointer', fontSize: 12 }}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (gid === 'tutor-h5') {
                              navigate(`/e/tutor-h5/chat?new=${Date.now()}`);
                            } else {
                              setActiveSessionId('');
                              navigate(`/e/${gid}/chat`);
                            }
                          }}
                        />
                      </Tooltip>
                      {count > 0 && <Text type="secondary" style={{ fontSize: 10 }}>{count}</Text>}
                    </div>
                    {isOpen && gid !== 'tutor-h5' && platformRows.map((s) => (
                      <div
                        key={s.id}
                        onClick={() => { setActiveSessionId(s.id); gid === 'tutor' ? navigate('/e/tutor/chat') : onSelect('home'); }}
                        className="dal-session-row"
                        style={{
                          padding: '6px 8px', cursor: 'pointer', borderRadius: 4, marginBottom: 1,
                          background: s.id === activeSessionId ? tokens.colors.primaryBg : 'transparent',
                          borderLeft: s.id === activeSessionId ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                          display: 'flex', alignItems: 'center', gap: 4,
                        }}
                      >
                        <MessageOutlined style={{ color: s.id === activeSessionId ? tokens.colors.primary : tokens.colors.textTertiary, fontSize: 11, flexShrink: 0 }} />
                        {editingId === s.id ? (
                          <Input
                            size="small"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            onPressEnter={() => saveEdit(s.id)}
                            suffix={<CheckOutlined onClick={() => saveEdit(s.id)} style={{ color: tokens.colors.success, cursor: 'pointer' }} />}
                            style={{ flex: 1, fontSize: 12 }}
                          />
                        ) : (
                          <Text
                            ellipsis
                            style={{ flex: 1, fontSize: 12, fontWeight: s.id === activeSessionId ? 500 : 400 }}
                            onDoubleClick={() => startEdit(s.id, s.title)}
                          >
                            {s.title}
                          </Text>
                        )}
                        {editingId !== s.id && (
                          <div className="dal-session-actions" style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                            <EditOutlined
                              style={{ color: tokens.colors.textTertiary, fontSize: 10, cursor: 'pointer', flexShrink: 0 }}
                              onClick={(e) => { e.stopPropagation(); startEdit(s.id, s.title); }}
                            />
                            <Popconfirm
                              title="删除此对话？"
                              onConfirm={(e) => { e?.stopPropagation(); handleDelete(s.id); }}
                              onCancel={(e) => e?.stopPropagation()}
                            >
                              <CloseOutlined
                                style={{ color: tokens.colors.textTertiary, fontSize: 10, cursor: 'pointer', flexShrink: 0 }}
                                onClick={(e) => e.stopPropagation()}
                              />
                            </Popconfirm>
                          </div>
                        )}
                      </div>
                    ))}
                    {isOpen && gid === 'tutor-h5' && vendorRows.map((vs) => {
                      const sid = vs.session_id || vs.id;
                      const isActive = sid === activeH5SessionId;
                      return (
                        <div
                          key={sid}
                          onClick={() => navigate(`/e/tutor-h5/chat?session=${encodeURIComponent(sid)}`)}
                          className="dal-session-row"
                          style={{
                            padding: '6px 8px', cursor: 'pointer', borderRadius: 4, marginBottom: 1,
                            background: isActive ? tokens.colors.primaryBg : 'transparent',
                            borderLeft: isActive ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                            display: 'flex', alignItems: 'center', gap: 4,
                          }}
                        >
                          <MessageOutlined style={{ color: isActive ? tokens.colors.primary : tokens.colors.textTertiary, fontSize: 11, flexShrink: 0 }} />
                          <Text ellipsis style={{ flex: 1, fontSize: 12, fontWeight: isActive ? 500 : 400 }}>{vs.title}</Text>
                          <Text type="secondary" style={{ fontSize: 10, flexShrink: 0 }}>{relTime(vs.updated_at)}</Text>
                          <div className="dal-session-actions" style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                            <EditOutlined
                              style={{ color: tokens.colors.textTertiary, fontSize: 10, cursor: 'pointer', flexShrink: 0 }}
                              onClick={async (e) => {
                                e.stopPropagation();
                                const title = window.prompt('输入新标题', '');
                                if (title === null || !title.trim()) return;
                                try { await updateSessionTitle(sid, title.trim()); refreshH5Sessions(); } catch { /* ignore */ }
                              }}
                            />
                            <Popconfirm
                              title="删除此对话？"
                              onConfirm={async (e) => {
                                e?.stopPropagation();
                                try { await deleteSession(sid); refreshH5Sessions(); } catch { /* ignore */ }
                              }}
                              onCancel={(e) => e?.stopPropagation()}
                            >
                              <CloseOutlined
                                style={{ color: tokens.colors.textTertiary, fontSize: 10, cursor: 'pointer', flexShrink: 0 }}
                                onClick={(e) => e.stopPropagation()}
                              />
                            </Popconfirm>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 收起按钮 */}
        <div
          style={{
            flexShrink: 0,
            height: 36,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderTop: `1px solid ${tokens.colors.border}`,
            background: tokens.colors.bgContent,
            cursor: 'pointer',
          }}
          onClick={onToggle}
        >
          <Tooltip title={collapsed ? '展开导航' : '收起导航'} placement="right">
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </Tooltip>
        </div>
      </div>
    </Sider>
  );
};

export default AppSider;
