/**
 * 专家门户（三轨M7(U2) §3.1「一问直达」起点页）——路径 /：
 * 上半屏：中央提问框 ≤720px（专家选择器 + 悬浮 composer + 推荐问法 chips ×4）；
 *   提交 = 携问题（sessionStorage 一次性预填）跳对应专家对话页并发出。
 * 下半屏：三专家卡（定高 320px 同构）——空间色图标（wenshu 蓝/sishu 琥珀/h5 青）、
 *   知识源 ≤3 +「+N」Tooltip 全名、工具数收右上齿轮角标、建议语独立一行置底。
 * 最近动态条：一行滚动（当前用户最近会话）。
 * testid 契约：portal-ask-input / portal-ask-send / portal-ask-expert / portal-card-{slug} / portal-recent-strip。
 */
import React, { useContext, useEffect, useMemo, useState } from 'react';
import { Button, Card, Input, Select, Tag, Tooltip, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  MobileOutlined, ReadOutlined, SearchOutlined, SendOutlined, SettingOutlined,
} from '@ant-design/icons';
import { expertsApi } from '../services/api';
import type { ExpertCard } from '../services/api';
import { EXPERT_PAGES } from '../config/expertPages';
import { AuthCtx } from '../auth/AuthGate';
import { tokens, spaceColors } from '../theme/tokens';
import { useStore } from '../store/useStore';

const { Text } = Typography;

const SLUG_ICON: Record<string, React.ComponentType<any>> = {
  wenshu: SearchOutlined,
  sishu: ReadOutlined,
  'tutor-h5': MobileOutlined,
};
const SLUG_BG: Record<string, string> = {
  wenshu: spaceColors.wenshu,
  sishu: spaceColors.sishu,
  'tutor-h5': spaceColors.h5,
};
const SUGGESTED_ASKS = [
  '查询用电客户总数',
  '帮我出一道鸡兔同笼的变式题',
  '鸡兔同笼问题讲解',
  '用_quad_四区建模分析主数据',
];

const ExpertPortal: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthCtx);
  const isAdminUser = ((((user as any)?.roles || []) as string[])).includes('admin');
  const [cards, setCards] = useState<ExpertCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [askExpert, setAskExpert] = useState<string>('wenshu');
  const [askText, setAskText] = useState('');
  const sessions = useStore((s) => s.sessions);

  useEffect(() => {
    (async () => {
      try {
        const res = await expertsApi.list({ enabled: true });
        setCards((res.data?.items as ExpertCard[]) || []);
      } catch {
        setCards([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const submitAsk = () => {
    const text = askText.trim();
    if (!text) return;
    sessionStorage.setItem('dal_chat_prefill', text);
    navigate(`/e/${askExpert}/chat`);
  };

  const openChatWithPrefill = (slug: string, text: string) => {
    sessionStorage.setItem('dal_chat_prefill', text);
    navigate(`/e/${slug}/chat`);
  };

  const recent = useMemo(
    () => (sessions || []).slice(0, 8).map((s: any) => ({
      id: s.id, title: s.title || '未命名会话', expertId: s.expertId || 'wenshu',
    })),
    [sessions],
  );

  const kbTags = (c: ExpertCard) => {
    const ks = c.knowledge_sources || [];
    const head = ks.slice(0, 3);
    const rest = ks.slice(3);
    return (
      <>
        {head.map((k) => (
          <Tag key={k} style={{ fontSize: 11, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {k.length > 8 ? `${k.slice(0, 8)}…` : k}
          </Tag>
        ))}
        {rest.length > 0 && (
          <Tooltip title={rest.join('、')}>
            <Tag style={{ fontSize: 11 }}>+{rest.length}</Tag>
          </Tooltip>
        )}
      </>
    );
  };

  return (
    <div style={{ flex: 1, overflow: 'auto', background: tokens.colors.bgPage }} data-testid="portal-page">
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '48px 24px 32px' }}>
        {/* 上半屏：一问直达 */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ fontSize: 26, fontWeight: tokens.fontWeight.bold, color: 'var(--text-primary)', marginBottom: 8 }}>
            DeepAssetLens
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 24 }}>
            选一个专家，直接开始提问
          </div>
          <div
            style={{
              maxWidth: 720, margin: '0 auto', background: tokens.colors.bgContent,
              borderRadius: tokens.radius.card, boxShadow: tokens.elevation.s3,
              padding: 16, border: `1px solid ${tokens.colors.border}`,
            }}
          >
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <Select
                value={askExpert}
                onChange={setAskExpert}
                style={{ width: 150, flexShrink: 0 }}
                size="large"
                data-testid="portal-ask-expert"
                options={cards.map((c) => ({ value: c.expert_id, label: c.name }))}
              />
              <Input.TextArea
                data-testid="portal-ask-input"
                value={askText}
                onChange={(e) => setAskText(e.target.value)}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault();
                    submitAsk();
                  }
                }}
                placeholder="想问什么数据？"
                autoSize={{ minRows: 1, maxRows: 5 }}
                style={{ fontSize: 14, border: 'none', boxShadow: 'none', padding: '8px 4px' }}
              />
              <Button
                type="primary"
                shape="circle"
                icon={<SendOutlined />}
                data-testid="portal-ask-send"
                onClick={submitAsk}
                disabled={!askText.trim()}
              />
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10, justifyContent: 'center' }}>
              {SUGGESTED_ASKS.map((s) => (
                <Tag
                  key={s}
                  style={{ fontSize: 12, cursor: 'pointer', borderRadius: 999, paddingInline: 10 }}
                  onClick={() => setAskText(s)}
                >
                  {s}
                </Tag>
              ))}
            </div>
          </div>
        </div>

        {/* 下半屏：三专家卡（定高 320 同构） */}
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-tertiary)' }}>加载中…</div>
        ) : cards.length === 0 ? (
          <div style={{ padding: 64, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 15 }}>
            暂无可用专家
          </div>
        ) : (
          <div
            style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}
            data-testid="portal-card-grid"
          >
            {cards.map((c) => {
              const Icon = SLUG_ICON[c.expert_id] || SearchOutlined;
              const bg = SLUG_BG[c.expert_id] || tokens.colors.primary;
              return (
                <Card
                  key={c.expert_id}
                  hoverable
                  data-testid={`portal-card-${c.expert_id}`}
                  onClick={() => navigate(`/e/${c.expert_id}/chat`)}
                  style={{
                    borderRadius: tokens.radius.card, boxShadow: tokens.elevation.s2,
                    height: 320, display: 'flex', flexDirection: 'column', position: 'relative',
                    borderTop: `3px solid ${bg}`,
                  }}
                  styles={{ body: { padding: 20, flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' } }}
                >
                  {/* 右上齿轮（工具数收角标） */}
                  {isAdminUser && (
                    <Tooltip title={`工具 ${c.tools?.length ?? 0} 件 · 后台`}>
                      <SettingOutlined
                        data-testid={`portal-card-gear-${c.expert_id}`}
                        onClick={(e) => { e.stopPropagation(); navigate(`/e/${c.expert_id}/admin`); }}
                        style={{ position: 'absolute', top: 14, right: 16, color: 'var(--text-tertiary)', cursor: 'pointer' }}
                      />
                    </Tooltip>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div
                      style={{
                        width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: bg, color: '#fff', fontSize: 20,
                      }}
                    >
                      <Icon />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>{c.name}</div>
                      <Text type="secondary" style={{ fontSize: 12 }} ellipsis>{c.tagline || c.description || ' '}</Text>
                    </div>
                  </div>
                  <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                    {kbTags(c)}
                  </div>
                  {/* 功能页 chips */}
                  {(EXPERT_PAGES[c.expert_id] || []).length > 0 && (
                    <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {(EXPERT_PAGES[c.expert_id] || []).slice(0, 5).map((pg) => (
                        <Tag
                          key={pg.menuKey}
                          style={{ fontSize: 11, cursor: 'pointer' }}
                          onClick={(e) => { e.stopPropagation(); navigate(pg.path); }}
                        >
                          {pg.label}
                        </Tag>
                      ))}
                    </div>
                  )}
                  {/* 建议语置底 */}
                  <div style={{ marginTop: 'auto', paddingTop: 10 }}>
                    {(c.suggestions || []).slice(0, 3).map((s, i) => (
                      <Text
                        key={`sugg-${i}`}
                        onClick={(e) => { e.stopPropagation(); openChatWithPrefill(c.expert_id, s); }}
                        style={{ fontSize: 12, color: tokens.colors.primary, cursor: 'pointer', display: 'block' }}
                        ellipsis
                      >
                        · {s}
                      </Text>
                    ))}
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* 最近动态条（一行滚动） */}
        {recent.length > 0 && (
          <div
            data-testid="portal-recent-strip"
            style={{
              marginTop: 24, display: 'flex', gap: 8, alignItems: 'center', overflowX: 'auto',
              padding: '8px 4px', whiteSpace: 'nowrap',
            }}
          >
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)', flexShrink: 0 }}>最近：</span>
            {recent.map((r) => (
              <Tag
                key={r.id}
                style={{ fontSize: 12, cursor: 'pointer', flexShrink: 0 }}
                onClick={() => navigate(`/e/${r.expertId}/chat`)}
              >
                {r.title.slice(0, 18)}
              </Tag>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ExpertPortal;
