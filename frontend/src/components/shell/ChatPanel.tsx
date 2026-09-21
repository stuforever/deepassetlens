/**
 * ChatPanel（v3 §二）：💬对话滑出面板——新建对话 + 三专家直达 + 最近对话列表。
 * 最近对话=平台 store 会话（wenshu/sishu）+ h5 vendor 会话合并（沿 AppSider 数据源迁移）。
 */
import { useCallback, useEffect, useState } from 'react';
import { Button, Typography } from 'antd';
import { PlusOutlined, MessageOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import type { ExpertId } from '../../store/useStore';
import { listSessions, updateSessionTitle, deleteSession } from '../../pages/tutor/admin/session-api';
import type { SessionSummary } from '../../pages/tutor/admin/session-api';

const { Text } = Typography;

const EXPERTS: { id: ExpertId; label: string; path: string; color: string }[] = [
  { id: 'wenshu', label: '问数', path: '/e/wenshu/chat', color: '#2563EB' },
  { id: 'sishu', label: '私塾', path: '/e/sishu/chat', color: '#D97706' },
  // Task 5 落地后改指 /h5-publish（发布管理页）；本任务先指展台对话页保链路活
  { id: 'tutor-h5', label: 'H5', path: '/e/tutor-h5/chat', color: '#0891B2' },
];

const relTime = (ts?: number) => {
  if (!ts) return '';
  const t = ts < 1e12 ? ts * 1000 : ts; // vendor updated_at=秒（DT 语义）归一
  const d = Date.now() - t;
  if (d < 60_000) return '刚刚';
  if (d < 3_600_000) return `${Math.floor(d / 60_000)}分钟前`;
  if (d < 86_400_000) return `${Math.floor(d / 3_600_000)}小时前`;
  if (d < 7 * 86_400_000) return `${Math.floor(d / 86_400_000)}天前`;
  return new Date(t).toLocaleDateString();
};

interface Row { sid: string; title: string; expert: ExpertId; ts: number; open: () => void; }

export function ChatPanel({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const sessions = useStore((s) => s.sessions);
  const setActiveSessionId = useStore((s) => s.setActiveSessionId);

  const [h5Rows, setH5Rows] = useState<SessionSummary[]>([]);
  const refreshH5 = useCallback(() => {
    listSessions(50, 0).then((rows) => setH5Rows(rows || [])).catch(() => { /* 静默空态 */ });
  }, []);
  useEffect(() => { void refreshH5(); }, [refreshH5, location.pathname]);

  const rows: Row[] = [];
  for (const s of sessions) {
    if (!s.messages.length) continue;
    rows.push({
      sid: s.id, title: s.title, expert: (s.expertId || 'wenshu') as ExpertId,
      ts: s.createdAt,
      open: () => {
        setActiveSessionId(s.id);
        navigate(s.expertId === 'sishu' ? '/e/sishu/chat' : '/e/wenshu/chat');
        onClose();
      },
    });
  }
  for (const vs of [...h5Rows].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0))) {
    const sid = vs.session_id || vs.id;
    rows.push({
      sid, title: vs.title || '(未命名)', expert: 'tutor-h5', ts: vs.updated_at || 0,
      open: () => {
        navigate(`/e/tutor-h5/chat?session=${encodeURIComponent(sid)}`);
        onClose();
      },
    });
  }
  rows.sort((a, b) => b.ts - a.ts);

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
        {rows.slice(0, 30).map((r) => (
          <div
            key={`${r.expert}-${r.sid}`}
            onClick={r.open}
            style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '7px 8px',
              borderRadius: 8, cursor: 'pointer', fontSize: 13,
            }}
            onMouseEnter={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'var(--muted, #f5f5f5)'; }}
            onMouseLeave={(ev) => { (ev.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
          >
            <span style={{ width: 8, height: 8, borderRadius: 99, flexShrink: 0, background: EXPERTS.find((e) => e.id === r.expert)?.color || '#999' }} />
            <MessageOutlined style={{ color: 'var(--text-tertiary, #bbb)', fontSize: 12, flexShrink: 0 }} />
            <Text ellipsis style={{ flex: 1, fontSize: 13 }}>{r.title}</Text>
            <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>{relTime(r.ts)}</Text>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ChatPanel;
