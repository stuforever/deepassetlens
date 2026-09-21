/**
 * 新建对话首页（v3 §二.1/§四——ExpertPortal 重写）：专家 Tab + 居中 composer + 问法 chips + 最近对话卡条。
 * 发送 → /e/{slug}/chat?new=1&q=...；h5 Tab → /h5-publish（发布管理页，Task 5）。
 */
import React, { useContext, useEffect, useMemo, useState } from 'react';
import { Typography } from 'antd';
import { SearchOutlined, ReadOutlined, MobileOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import UnifiedComposer from '../components/chat/UnifiedComposer';
import { expertsApi } from '../services/api';
import type { ExpertCard } from '../services/api';
import { AuthCtx } from '../auth/AuthGate';
import { tokens, spaceColors } from '../theme/tokens';
import { useStore } from '../store/useStore';
import { listSessions } from '../pages/tutor/admin/session-api';

const { Text } = Typography;

type ChatSlug = 'wenshu' | 'sishu' | 'h5';

const TAB_META: { slug: ChatSlug; label: string; color: string; title: string; placeholder: string; icon: React.ComponentType<any> }[] = [
  { slug: 'wenshu', label: '问数', color: spaceColors.wenshu, title: '有什么想探查的数据？', placeholder: '想问什么数据？', icon: SearchOutlined },
  { slug: 'sishu', label: '私塾', color: spaceColors.sishu, title: '今天想学点什么？', placeholder: '想学什么？可以让我出题、判分、安排复习', icon: ReadOutlined },
  { slug: 'h5', label: 'h5', color: spaceColors.h5, title: '手机上的私塾', placeholder: '选择页面在手机上打开', icon: MobileOutlined },
];

const FALLBACK_CHIPS: Record<ChatSlug, string[]> = {
  wenshu: ['统计用电客户总数', '什么是变压器', '配电变压器有哪些？列出编号和名称', '用电客户数据的来源'],
  sishu: ['出三道几何练习', '我今天该复习什么', '看看我的学情画像', '开始今天的复习'],
  h5: ['对话', '学习', '错题本', '学情报告'],
};

const NewChatHome: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthCtx);
  const sessions = useStore((s) => s.sessions);
  const [tab, setTab] = useState<ChatSlug>(() => {
    const saved = localStorage.getItem('newchat-tab');
    return saved === 'sishu' || saved === 'h5' || saved === 'wenshu' ? saved : 'wenshu';
  });
  const [question, setQuestion] = useState('');
  const [cards, setCards] = useState<Record<string, ExpertCard>>({});
  const [h5Rows, setH5Rows] = useState<{ sid: string; title: string; ts: number }[]>([]);

  useEffect(() => { localStorage.setItem('newchat-tab', tab); }, [tab]);

  useEffect(() => {
    (async () => {
      for (const slug of ['wenshu', 'sishu']) {
        try {
          const res = await expertsApi.get(slug);
          setCards((prev) => ({ ...prev, [slug]: res.data as ExpertCard }));
        } catch { /* 静默——chips 回落默认 */ }
      }
    })();
  }, []);

  useEffect(() => {
    listSessions(20, 0).then((rows) => {
      setH5Rows((rows || []).map((r) => ({ sid: r.session_id || r.id, title: r.title, ts: r.updated_at || 0 })));
    }).catch(() => { /* 静默 */ });
  }, []);

  const meta = TAB_META.find((t) => t.slug === tab)!;
  const chips: string[] = useMemo(() => {
    if (tab === 'h5') return FALLBACK_CHIPS.h5;
    const c = cards[tab];
    const suggs = (c?.suggestions && c.suggestions.length ? c.suggestions : undefined)
      ?? FALLBACK_CHIPS[tab];
    return suggs.slice(0, 4);
  }, [tab, cards]);

  // 最近对话卡条 ×5：平台 store 会话（wenshu/sishu，有消息）+ h5 vendor 会话，按近序
  const recent = useMemo(() => {
    const rows: { key: string; title: string; color: string; ts: number; open: () => void }[] = [];
    for (const s of sessions) {
      if (!s.messages.length) continue;
      const color = s.expertId === 'sishu' ? spaceColors.sishu : spaceColors.wenshu;
      rows.push({
        key: `p-${s.id}`, title: s.title, color, ts: s.createdAt,
        open: () => {
          useStore.getState().setActiveSessionId(s.id);
          navigate(s.expertId === 'sishu' ? '/e/sishu/chat' : '/e/wenshu/chat');
        },
      });
    }
    for (const r of h5Rows) {
      rows.push({
        key: `h-${r.sid}`, title: r.title || '(未命名)', color: spaceColors.h5, ts: r.ts,
        open: () => navigate(`/e/tutor-h5/chat?session=${encodeURIComponent(r.sid)}`),
      });
    }
    rows.sort((a, b) => b.ts - a.ts);
    return rows.slice(0, 5);
  }, [sessions, h5Rows, navigate]);

  const relTime = (ts: number) => {
    if (!ts) return '';
    const t = ts < 1e12 ? ts * 1000 : ts;
    const d = Date.now() - t;
    if (d < 60_000) return '刚刚';
    if (d < 3_600_000) return `${Math.floor(d / 60_000)}分钟前`;
    if (d < 86_400_000) return `${Math.floor(d / 3_600_000)}小时前`;
    if (d < 7 * 86_400_000) return `${Math.floor(d / 86_400_000)}天前`;
    return new Date(t).toLocaleDateString();
  };

  const send = () => {
    const q = question.trim();
    if (!q) return;
    if (tab === 'h5') { navigate('/h5-publish'); return; }
    navigate(`/e/${tab}/chat?new=1&q=${encodeURIComponent(q)}`);
  };

  void user;

  return (
    <div data-testid="newchat-home" style={{ flex: 1, overflow: 'auto', background: tokens.colors.bgPage }}>
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '72px 24px 32px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {/* 专家 Tab（页内 Tab 非页签条；选中=空间色下划线；localStorage 记忆） */}
        <div style={{ display: 'flex', gap: 28, marginBottom: 40 }} data-testid="newchat-tabs">
          {TAB_META.map((t) => {
            const active = t.slug === tab;
            return (
              <div
                key={t.slug}
                role="button"
                tabIndex={0}
                data-testid={`newchat-tab-${t.slug}`}
                onClick={() => setTab(t.slug)}
                onKeyDown={(e) => { if (e.key === 'Enter') setTab(t.slug); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, fontSize: 15,
                  cursor: 'pointer', paddingBottom: 8,
                  color: active ? t.color : 'var(--text-secondary, #888)',
                  fontWeight: active ? 600 : 400,
                  borderBottom: active ? `2px solid ${t.color}` : '2px solid transparent',
                }}
              >
                <t.icon />
                {t.label}
              </div>
            );
          })}
        </div>

        {/* 居中标题随专家切换 */}
        <h1 style={{ fontSize: 30, fontWeight: 600, color: 'var(--text-primary, #222)', margin: '0 0 28px', letterSpacing: '-0.01em' }}>
          {meta.title}
        </h1>

        {/* 中央 composer ≤720px（M7 统一组件复用） */}
        <div style={{ width: '100%', maxWidth: 720 }}>
          <UnifiedComposer
            testId="newchat-composer"
            value={question}
            onChange={setQuestion}
            onSubmit={send}
            placeholder={meta.placeholder}
          />
        </div>

        {/* 问法 chips ×4（随专家切换；h5=页面直达跳发布管理） */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center', marginTop: 20 }} data-testid="newchat-chips">
          {chips.map((c) => (
            <div
              key={c}
              role="button"
              tabIndex={0}
              onClick={() => {
                if (tab === 'h5') { navigate('/h5-publish'); return; }
                setQuestion(c);
                navigate(`/e/${tab}/chat?new=1&q=${encodeURIComponent(c)}`);
              }}
              onKeyDown={(e) => { if (e.key === 'Enter') setQuestion(c); }}
              style={{
                padding: '6px 14px', borderRadius: 999, cursor: 'pointer', fontSize: 13,
                border: '1px solid var(--border-subtle, #e5e7eb)', background: 'var(--bg-content, #fff)',
                color: 'var(--text-secondary, #555)',
              }}
            >
              {c}
            </div>
          ))}
        </div>

        {/* 最近对话横向卡条 ×5 */}
        {recent.length > 0 && (
          <div style={{ width: '100%', marginTop: 56 }} data-testid="newchat-recent">
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>最近对话</Text>
            <div style={{ display: 'flex', gap: 12, marginTop: 10, overflowX: 'auto', paddingBottom: 4 }}>
              {recent.map((r) => (
                <div
                  key={r.key}
                  role="button"
                  tabIndex={0}
                  onClick={r.open}
                  style={{
                    minWidth: 200, maxWidth: 220, padding: '10px 12px', borderRadius: 12, cursor: 'pointer',
                    border: '1px solid var(--border-subtle, #e5e7eb)', background: 'var(--bg-content, #fff)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 99, background: r.color, flexShrink: 0 }} />
                    <Text ellipsis style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{r.title}</Text>
                  </div>
                  <Text type="secondary" style={{ fontSize: 11 }}>{relTime(r.ts)}</Text>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NewChatHome;
