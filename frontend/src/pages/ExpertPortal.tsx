/**
 * 专家门户（专家地基①，spec §七）——路径 /：
 * expertsApi.list({enabled:true}) 拉启用卡 → 卡片墙（icon/名称/tagline/知识源徽标）；
 * 点击跳 /e/{expert_id}/chat。全关空态居中提示。沿用 PageShell。
 * 附件四 A-1：功能页 chips（label 点击 stopPropagation 后 navigate）+后台角标（admin）
 * +suggestions 区（≤3 条可点——跳 chat 预填，sessionStorage 一次性消费）。
 */
import React, { useContext, useEffect, useState } from 'react';
import { Card, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { SearchOutlined, SettingOutlined } from '@ant-design/icons';
import { PageShell } from '../components/shell';
import { expertsApi } from '../services/api';
import type { ExpertCard } from '../services/api';
import { EXPERT_PAGES } from '../config/expertPages';
import { AuthCtx } from '../auth/AuthGate';
import { tokens } from '../theme/tokens';

const { Text } = Typography;

const ExpertPortal: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthCtx);
  const isAdminUser = (((user as any)?.roles || []) as string[]).includes('admin');
  const [cards, setCards] = useState<ExpertCard[]>([]);
  const [loading, setLoading] = useState(true);

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

  const openChatWithPrefill = (slug: string, text: string) => {
    sessionStorage.setItem('dal_chat_prefill', text);
    navigate(`/e/${slug}/chat`);
  };

  return (
    <PageShell title="专家门户" description="按业务域选择专家开始对话；每个专家拥有独立的提示词基座、工具面与知识路径">
      <div style={{ maxWidth: 960, margin: '0 auto' }}>
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-tertiary)' }}>加载中…</div>
        ) : cards.length === 0 ? (
          <div style={{ padding: 64, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 15 }}>
            暂无可用专家
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
            {cards.map((c) => (
              <Card
                key={c.expert_id}
                hoverable
                onClick={() => navigate(`/e/${c.expert_id}/chat`)}
                style={{ borderRadius: tokens.radius.card, boxShadow: tokens.elevation.s2 }}
                styles={{ body: { padding: 20 } }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div
                    style={{
                      width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: tokens.brandGradient, color: '#fff', fontSize: 20,
                    }}
                  >
                    <SearchOutlined />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>{c.name}</div>
                    <Text type="secondary" style={{ fontSize: 12 }} ellipsis>{c.tagline || c.description || ' '}</Text>
                  </div>
                </div>
                <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                  {(c.knowledge_sources || []).map((k) => (
                    <Tag key={k} color="blue" style={{ fontSize: 11 }}>{k}</Tag>
                  ))}
                  <Tag style={{ fontSize: 11 }}>工具 {c.tools?.length ?? 0} 件</Tag>
                  {/* 附件四 A-1：后台角标（admin 可见；点击进后台不触发整卡跳转） */}
                  {isAdminUser && (
                    <Tag
                      color="gold"
                      style={{ fontSize: 11, cursor: 'pointer' }}
                      icon={<SettingOutlined />}
                      onClick={(e) => { e.stopPropagation(); navigate(`/e/${c.expert_id}/admin`); }}
                    >
                      后台
                    </Tag>
                  )}
                </div>
                {/* 附件四 A-1：功能页 chips（label 点击 stopPropagation 后 navigate——整卡跳 chat 语义不动） */}
                {(EXPERT_PAGES[c.expert_id] || []).length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {(EXPERT_PAGES[c.expert_id] || []).map((p) => (
                      <Tag
                        key={p.menuKey}
                        style={{ fontSize: 11, cursor: 'pointer' }}
                        onClick={(e) => { e.stopPropagation(); navigate(p.path); }}
                      >
                        {p.label}
                      </Tag>
                    ))}
                  </div>
                )}
                {/* 附件四 A-1：suggestions 区（≤3 条可点——跳 chat 预填） */}
                {(c.suggestions || []).length > 0 && (
                  <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {(c.suggestions || []).slice(0, 3).map((s, i) => (
                      <Text
                        key={`sugg-${i}`}
                        onClick={(e) => { e.stopPropagation(); openChatWithPrefill(c.expert_id, s); }}
                        style={{ fontSize: 12, color: tokens.colors.primary, cursor: 'pointer' }}
                        ellipsis
                      >
                        · {s}
                      </Text>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </PageShell>
  );
};

export default ExpertPortal;
