/**
 * AppSider - 左侧导航 + 会话区（可收起 64px）。
 * 上部：数据资产探查（首页顶层项）+ 5 分组 inline Menu（手风琴模式）。
 * 下部：最近对话会话列表（从 Zustand store 读取，点击切到首页并激活该会话）。
 * 底部：收起/展开按钮。
 */
import React, { useState, useEffect, useMemo } from 'react';
import { Layout, Menu, Tooltip, Input, Typography, Popconfirm, message } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
  MessageOutlined,
  CloseOutlined,
  EditOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { NAV_GROUPS, HOME_NAV_ITEM } from '../config/navigation';
import { tokens } from '../theme/tokens';
import { useStore } from '../store/useStore';

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

  const onOpenChange = (keys: string[]) => {
    const latest = keys.find((k) => !openKeys.includes(k));
    setOpenKeys(latest ? [latest] : []);
  };

  const items = useMemo(
    () => [
      // 首页顶层项
      {
        key: HOME_NAV_ITEM.menuKey,
        icon: <HOME_NAV_ITEM.icon />,
        label: HOME_NAV_ITEM.label,
      },
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
    []
  );

  const handleSessionClick = (id: string) => {
    setActiveSessionId(id);
    onSelect('home');
  };

  const handleNewSession = () => {
    setActiveSessionId('');
    onSelect('home');
  };

  const startEdit = (sid: string, currentTitle: string) => {
    setEditingId(sid);
    setEditTitle(currentTitle);
  };

  const saveEdit = (sid: string) => {
    renameSessionById(sid, editTitle);
    setEditingId(null);
  };

  const handleDelete = (sid: string) => {
    deleteSessionById(sid);
    message.success('已删除对话');
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
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
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

        {/* 会话区 - 展开时显示 */}
        {!collapsed && (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', borderTop: `1px solid ${tokens.colors.border}` }}>
            <div style={{ padding: '6px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
              <Text type="secondary" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.5 }}>最近对话</Text>
              <Tooltip title="新建对话">
                <PlusOutlined
                  style={{ color: tokens.colors.primary, cursor: 'pointer', fontSize: 12 }}
                  onClick={handleNewSession}
                />
              </Tooltip>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '0 4px' }}>
              {sessions.filter((s) => s.messages.length > 0).map((s) => (
                <div
                  key={s.id}
                  onClick={() => handleSessionClick(s.id)}
                  style={{
                    padding: '6px 8px',
                    cursor: 'pointer',
                    borderRadius: 4,
                    marginBottom: 1,
                    background: s.id === activeSessionId ? tokens.colors.primaryBg : 'transparent',
                    borderLeft: s.id === activeSessionId ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
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
                    <>
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
                    </>
                  )}
                </div>
              ))}
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
