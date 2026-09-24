/**
 * ChatPanel（v3 §二，批③ §十三换壳，批④ v4§六 历史分类）：💬对话面板内容——新建对话 + 四层历史分类。
 * 分类层叠：📌置顶｜⭐收藏｜按专家（问数/私塾/H5+空间色点）｜组内时间组（今天/本周/更早）。
 * 置顶/收藏=纯前端 localStorage（hist:pinned/hist:fav，后端 conversation 标签列二期）。
 * v4§5.1：不设专家直达（进对话一律走新建对话或首屏专家 Tab）；EXPERTS 常量保留（分组空间色点仍用）。
 * 宽度/背景/边框由统一壳 ShellPanel 提供（本组件只渲染滚动内容区）。
 * 最近对话=平台 store 会话（wenshu/sishu）+ h5 vendor 会话合并（沿 AppSider 数据源迁移）。
 * v4§九：会话行 hover ⋯ 菜单（重命名/置顶/收藏/删除）——平台行走 store，h5 行走 vendor session-api 并刷新。
 * R#9：行 ts 统一 normTs 归一（vendor updated_at=秒 → ms）后再排序，h5 会话不再恒沉底。
 * 批④：>30 条默认截断，「查看全部」破截。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
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

/** 批④ 时间组（滚动 7 天窗）：今天 / 本周 / 更早 */
type TimeBucket = 'today' | 'week' | 'earlier';
const BUCKET_LABELS: Record<TimeBucket, string> = { today: '今天', week: '本周', earlier: '更早' };
const timeBucket = (ts?: number | null): TimeBucket => {
  const t = normTs(ts);
  if (!t) return 'earlier';
  const now = new Date();
  const d = new Date(t);
  if (d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()) return 'today';
  if (now.getTime() - t < 7 * 86_400_000) return 'week';
  return 'earlier';
};

/** 批④ 置顶/收藏 localStorage（键=「{expert}-{sid}」复合键；后端 conversation 标签列二期） */
const HIST_PIN_KEY = 'hist:pinned';
const HIST_FAV_KEY = 'hist:fav';
const loadHist = (key: string): string[] => {
  try {
    const raw = localStorage.getItem(key);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.filter((x) => typeof x === 'string') : [];
  } catch { return []; }
};
const saveHist = (key: string, ids: string[]) => {
  try { localStorage.setItem(key, JSON.stringify(ids)); } catch { /* ignore */ }
};

const ROW_CAP = 30;

interface Row {
  key: string;
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
  const [search, setSearch] = useState('');
  // UX2批⑥（反馈⑤）：历史区分类别 Tab（全部/问数/私塾/h5）——批④ 层叠在所选类别内保持
  const [catTab, setCatTab] = useState<'all' | ExpertId>('all');
  const [expanded, setExpanded] = useState(false);
  const [pins, setPins] = useState<string[]>(() => loadHist(HIST_PIN_KEY));
  const [favs, setFavs] = useState<string[]>(() => loadHist(HIST_FAV_KEY));
  const refreshH5 = useCallback(() => {
    listSessions(50, 0).then((rows) => setH5Rows(rows || [])).catch(() => { /* 静默空态 */ });
  }, []);
  useEffect(() => { void refreshH5(); }, [refreshH5, location.pathname]);

  const rows: Row[] = [];
  for (const s of sessions) {
    if (!s.messages.length) continue;
    rows.push({
      key: `${(s.expertId || 'wenshu') as string}-${s.id}`,
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
      key: `tutor-h5-${sid}`,
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

  const q = search.trim();
  const filtered = useMemo(
    () => (q ? rows.filter((r) => r.title.toLowerCase().includes(q.toLowerCase())) : rows),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [q, rows],
  );

  const toggleHist = (key: string, setter: React.Dispatch<React.SetStateAction<string[]>>, lsKey: string) => {
    setter((prev) => {
      const next = prev.includes(key) ? prev.filter((x) => x !== key) : [key, ...prev];
      saveHist(lsKey, next);
      return next;
    });
  };

  // UX2批⑥：类别 Tab 过滤（filtered 基础上按专家收窄）
  const scoped = catTab === 'all' ? filtered : filtered.filter((r) => r.expert === catTab);
  // 批④ 四层层叠：📌置顶 → ⭐收藏 → 按专家三组（组内 今天/本周/更早）
  const pinnedRows = scoped.filter((r) => pins.includes(r.key));
  const favRows = scoped.filter((r) => favs.includes(r.key) && !pins.includes(r.key));
  const rest = scoped.filter((r) => !pins.includes(r.key) && !favs.includes(r.key));

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
      { key: 'pin', label: pins.includes(r.key) ? '取消置顶' : '置顶' },
      { key: 'fav', label: favs.includes(r.key) ? '取消收藏' : '收藏' },
      { key: 'delete', label: '删除' },
    ],
    onClick: (info) => {
      info.domEvent.stopPropagation();
      if (info.key === 'rename') { setRenameVal(r.title); setRenamingKey(r.key); }
      if (info.key === 'pin') toggleHist(r.key, setPins, HIST_PIN_KEY);
      if (info.key === 'fav') toggleHist(r.key, setFavs, HIST_FAV_KEY);
      if (info.key === 'delete') confirmDelete(r);
    },
  });

  const renderRow = (r: Row) => {
    const hovered = hoverKey === r.key;
    return (
      <div
        key={r.key}
        data-testid="chat-panel-session-row"
        onClick={r.open}
        onMouseEnter={() => setHoverKey(r.key)}
        onMouseLeave={() => setHoverKey('')}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '7px 8px',
          borderRadius: 8, cursor: 'pointer', fontSize: 13,
          background: hovered ? 'var(--muted, #f5f5f5)' : 'transparent',
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: 99, flexShrink: 0, background: EXPERTS.find((e) => e.id === r.expert)?.color || '#999' }} />
        <MessageOutlined style={{ color: 'var(--text-tertiary, #bbb)', fontSize: 12, flexShrink: 0 }} />
        {renamingKey === r.key ? (
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
  };

  // 30 条硬截（渲染序=层叠序），「查看全部」破截
  const flat: Row[] = [
    ...pinnedRows,
    ...favRows,
    ...(['wenshu', 'sishu', 'tutor-h5'] as ExpertId[]).flatMap((ex) => rest.filter((r) => r.expert === ex)),
  ];
  const shown = expanded ? flat : flat.slice(0, ROW_CAP);
  const shownSet = new Set(shown.map((r) => r.key));

  const groupHeader = (label: string, color: string | null, testid: string) => (
    <div
      data-testid={testid}
      style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary, #888)', margin: '8px 0 4px', fontWeight: 600 }}
    >
      {color && <span style={{ width: 8, height: 8, borderRadius: 99, background: color, flexShrink: 0 }} />}
      {label}
    </div>
  );

  const renderLayer = (label: string, testid: string, list: Row[], color: string | null = null) => {
    const visible = list.filter((r) => shownSet.has(r.key));
    if (visible.length === 0) return null;
    return (
      <div>
        {groupHeader(label, color, testid)}
        {visible.map(renderRow)}
      </div>
    );
  };

  const renderExpertLayer = (ex: ExpertId) => {
    const meta = EXPERTS.find((e) => e.id === ex);
    if (!meta) return null;
    const list = rest.filter((r) => r.expert === ex && shownSet.has(r.key));
    if (list.length === 0) return null;
    const buckets: TimeBucket[] = ['today', 'week', 'earlier'];
    return (
      <div>
        {groupHeader(meta.label, meta.color, `hist-group-expert-${ex}`)}
        {buckets.map((bk) => {
          const bl = list.filter((r) => timeBucket(r.ts) === bk);
          if (bl.length === 0) return null;
          return (
            <div key={bk}>
              <div data-testid={`hist-bucket-${ex}-${bk}`} style={{ fontSize: 11, color: 'var(--text-tertiary, #aaa)', margin: '4px 0 2px', padding: '0 8px' }}>
                {BUCKET_LABELS[bk]}
              </div>
              {bl.map(renderRow)}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div
      data-testid="chat-panel"
      style={{
        overflowY: 'auto', padding: 16,
        display: 'flex', flexDirection: 'column', gap: 12,
      }}
    >
      <Button
        type="primary"
        block
        icon={<PlusOutlined />}
        data-testid="chat-panel-new"
        // UX3批1（P0-C）：新建留守当前空间（?new=1 契约=UX2批③），不再跳门户/关面板
        onClick={() => {
          setActiveSessionId('');
          const slug = location.pathname.startsWith('/e/') ? (location.pathname.split('/')[2] || 'wenshu') : 'wenshu';
          navigate(slug === 'tutor-h5' ? '/e/tutor-h5/chat' : `/e/${slug}/chat?new=1`);
        }}
      >
        新建对话
      </Button>
      <Input
        size="small"
        allowClear
        placeholder="搜索历史标题…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        data-testid="chat-panel-search"
      />
      <div style={{ flex: 1, minHeight: 0 }}>
        <div style={{ display: 'flex', gap: 4, marginBottom: 6 }} data-testid="chat-cat-tabs">
          {(['all', 'wenshu', 'sishu', 'tutor-h5'] as const).map((k) => (
            <div
              key={k}
              role="button"
              tabIndex={0}
              data-testid={`chat-cat-tab-${k}`}
              onClick={() => setCatTab(k)}
              style={{
                padding: '2px 10px', borderRadius: 999, fontSize: 12, cursor: 'pointer',
                background: catTab === k ? 'var(--primary-50, #eff6ff)' : 'transparent',
                color: catTab === k ? 'var(--brand, #2563EB)' : 'var(--text-secondary, #888)',
                border: `1px solid ${catTab === k ? 'var(--brand, #2563EB)' : 'var(--border-subtle, #e5e7eb)'}`,
              }}
            >
              {k === 'all' ? '全部' : (EXPERTS.find((e) => e.id === k)?.label || k)}
            </div>
          ))}
        </div>
        {scoped.length === 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>{q ? '无匹配会话' : '暂无对话记录'}</Text>
        )}
        {renderLayer('📌 置顶', 'hist-group-pinned', pinnedRows)}
        {renderLayer('⭐ 收藏', 'hist-group-fav', favRows)}
        {(['wenshu', 'sishu', 'tutor-h5'] as ExpertId[]).map((ex) => (
          <div key={ex}>{renderExpertLayer(ex)}</div>
        ))}
        {!expanded && flat.length > ROW_CAP && (
          <Button
            type="link"
            size="small"
            block
            data-testid="hist-expand"
            onClick={() => setExpanded(true)}
            style={{ marginTop: 8 }}
          >
            查看全部（共 {flat.length} 条）
          </Button>
        )}
      </div>
    </div>
  );
}

export default ChatPanel;
