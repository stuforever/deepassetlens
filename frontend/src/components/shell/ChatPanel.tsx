/**
 * ChatPanel（v3 §二）：💬对话滑出面板——新建对话 + 三专家直达 + 最近对话列表。
 * 最近对话=平台 store 会话（wenshu/sishu）+ h5 vendor 会话合并（沿 AppSider 数据源迁移）。
 * v4§九：会话行 hover ⋯ 菜单（重命名/删除）接回（0ef1420 换壳回归修复）——
 * 平台行走 store deleteSessionById/renameSessionById；h5 行走 vendor session-api 并刷新。
 * R#9：行 ts 统一 normTs 归一（vendor updated_at=秒 → ms）后再排序，h5 会话不再恒沉底。
 */
import { useCallback, useEffect, useState } from 'react';
import { Button, Dropdown, Input, Modal, Typography } from 'antd';
import type { MenuProps } from 'antd';
import { MoreOutlined, PlusOutlined, MessageOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import type { ExpertId } from '../../store/useStore';
import { listSessions, updateSessionTitle, deleteSession } from '../../pages/tutor/admin/session-api';
import type { SessionSummary } from '../../pages/tutor/admin/session-api';

const { Text } = Typography;

const EXPERTS: { id: ExpertId; label: string; path: string; color: string }[] = [
  { id: 'wenshu', label: '问数', path: '/e/wenshu/chat', color: '#2563EB' },
  { id: 'sishu', label: '私塾', path: '/e/sishu/chat', color: '#D97706' },
  { id: 'tutor-h5', label: 'H5', path: '/h5-publish', color: '#0891B2' },
];

/** 归一化时间戳：vendor updated_at=秒（DT 语义）→ ms；批④ 历史分类复用 */
export const normTs = (ts?: number | null): number => {
  const t = ts || 0;
  return t < 1e12 ? t * 1000 : t;
};

const relTime = (ts?: number | null) => {
  const t = normTs(ts);
  if (!t) return '';
  const d = Date.now() - t;
  if (d < 60_000) return '刚刚';
  if (d < 3_600_000) return `${Math.floor(d / 60_000)}分钟前`;
  if (d < 86_400_000) return `${Math.floor(d / 3_600_000)}小时前`;
  if (d < 7 * 86_400_000) return `${Math.floor(d / 86_400_000)}天前`;
  return new Date(t).toLocaleDateString();
};

interface Row {
  sid: string; title: string; expert: ExpertId; ts: number;
  open: () => void;
  rename: (title: string) => Promise<void> | void;
  remove: () => Promise<void> | void;
}

export function ChatPanel({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const sessions = useStore((s) => s.sessions);
  const setActiveSessionId = useStore((s) => s.setActiveSessionId);
  const deleteSessionById = useStore((s) => s.deleteSessionById);
  const renameSessionById = useStore((s) => s.renameSessionById);

  const [h5Rows, setH5Rows] = useState<SessionSummary[]>([]);
  const [hoverKey, setHoverKey] = useState('');
  const [renamingKey, setRenamingKey] = useState('');
  const [renameVal, setRenameVal] = useState('');
  const refreshH5 = useCallback(() => {
    listSessions(50, 0).then((rows) => setH5Rows(rows || [])).catch(() => { /* 静默空态 */ });
  }, []);
  useEffect(() => { void refreshH5(); }, [refreshH5, location.pathname]);

  const rows: Row[] = [];
  for (const s of sessions) {
    if (!s.messages.length) continue;
    rows.push({
      sid: s.id, title: s.title, expert: (s.expertId || 'wenshu') as ExpertId,
      ts: normTs(s.createdAt),
      open: () => {
        setActiveSessionId(s.id);
        navigate(s.expertId === 'sishu' ? '/e/sishu/chat' : '/e/wenshu/chat');
        onClose();
      },
      rename: (t) => renameSessionById(s.id, t),
      remove: async () => { await deleteSessionById(s.id); },
    });
  }
  for (const vs of [...h5Rows].sort((a, b) => normTs(b.updated_at) - normTs(a.updated_at))) {
    const sid = vs.session_id || vs.id;
    rows.push({
      sid, title: vs.title || '(未命名)', expert: 'tutor-h5', ts: normTs(vs.updated_at),
      open: () => {
        navigate(`/e/tutor-h5/chat?session=${encodeURIComponent(sid)}`);
        onClose();
      },
      rename: async (t) => { await updateSessionTitle(sid, t); refreshH5(); },
      remove: async () => { await deleteSession(sid); refreshH5(); },
    });
  }
  rows.sort((a, b) => b.ts - a.ts);

  const commitRename = (r: Row) => {
    const t = renameVal.trim();
    setRenamingKey('');
    if (t && t !== r.title) void r.rename(t);
  };

  const confirmDelete = (r: Row) => {
    Modal.confirm({
      title: '删除此会话？',
      content: `「${r.title}」将连同后端记录一并删除，不可恢复。`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => r.remove(),
    });
  };

  const rowMenu = (r: Row): MenuProps => ({
    items: [
      { key: 'rename', label: '重命名' },
      { key: 'delete', label: '删除' },
    ],
    onClick: (info) => {
      info.domEvent.stopPropagation();
      if (info.key === 'rename') { setRenameVal(r.title); setRenamingKey(`${r.expert}-${r.sid}`); }
      if (info.key === 'delete') confirmDelete(r);
    },
  });

  return (
    <div
      data-testid="chat-panel"
      style={{
        width: 300, flexShrink: 0, overflowY: 'auto', padding: 16,
        background: 'var(--bg-content, #fff)', borderRight: '1px solid var(--border-subtle, #eee)',
        display: 'flex', flexDirection: 'column', gap: 12,
      }}
    >
      <Button
        type="primary"
        block
        icon={<PlusOutlined />}
        data-testid="chat-panel-new"
        onClick={() => { setActiveSessionId(''); navigate('/'); onClose(); }}
      >
        新建对话
      </Button>
      <div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary, #888)', margin: '2px 0 6px', fontWeight: 600 }}>三专家直达</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {EXPERTS.map((e) => (
            <div
              key={e.id}
              role="button"
              tabIndex={0}
              data-testid={`chat-panel-expert-${e.id}`}
              onClick={() => { navigate(e.path); onClose(); }}
              style={{
                flex: 1, padding: '8px 10px', borderRadius: 10, cursor: 'pointer', fontSize: 13,
                border: '1px solid var(--border-subtle, #eee)', display: 'flex', alignItems: 'center', gap: 6,
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: 99, background: e.color, flexShrink: 0 }} />
              {e.label}
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <div style={{ fontSize: 12, color: 'var(--text-secondary, #888)', margin: '2px 0 6px', fontWeight: 600 }}>最近对话</div>
        {rows.length === 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>暂无对话记录</Text>
        )}
        {rows.slice(0, 30).map((r) => {
          const key = `${r.expert}-${r.sid}`;
          const hovered = hoverKey === key;
          return (
            <div
              key={key}
              data-testid="chat-panel-session-row"
              onClick={r.open}
              onMouseEnter={() => setHoverKey(key)}
              onMouseLeave={() => setHoverKey('')}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '7px 8px',
                borderRadius: 8, cursor: 'pointer', fontSize: 13,
                background: hovered ? 'var(--muted, #f5f5f5)' : 'transparent',
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: 99, flexShrink: 0, background: EXPERTS.find((e) => e.id === r.expert)?.color || '#999' }} />
              <MessageOutlined style={{ color: 'var(--text-tertiary, #bbb)', fontSize: 12, flexShrink: 0 }} />
              {renamingKey === key ? (
                <Input
                  size="small"
                  autoFocus
                  value={renameVal}
                  onChange={(e) => setRenameVal(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  onPressEnter={() => commitRename(r)}
                  onBlur={() => commitRename(r)}
                  onKeyDown={(e) => { if (e.key === 'Escape') setRenamingKey(''); }}
                  style={{ flex: 1 }}
                  data-testid="chat-panel-rename-input"
                />
              ) : (
                <Text ellipsis style={{ flex: 1, fontSize: 13 }}>{r.title}</Text>
              )}
              <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>{relTime(r.ts)}</Text>
              <Dropdown menu={rowMenu(r)} trigger={['click']} placement="bottomRight">
                <Button
                  size="small"
                  type="text"
                  icon={<MoreOutlined />}
                  aria-label="会话操作"
                  data-testid="chat-panel-row-more"
                  onClick={(e) => e.stopPropagation()}
                  style={{ opacity: hovered ? 1 : 0, flexShrink: 0, width: 22, height: 22, marginRight: -6 }}
                />
              </Dropdown>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ChatPanel;
