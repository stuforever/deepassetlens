/**
 * 专家门户首页（UX2批① 用户反馈①⑤：两套入口不强融——首页只做三张高质感专家卡：
 * 图标+名称+能做什么介绍，点击分别进入各自入口 /e/wenshu/chat、/e/sishu/chat、/h5-publish。
 * 原集中 composer/模板宫格/Tab 退场——对话在各专家页内完成（8 建议卡 ExpertChat 首屏已有）。
 */
import React, { useContext } from 'react';
import {
  BarChartOutlined,
  ReadOutlined,
  MobileOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { AuthCtx } from '../auth/AuthGate';
import { spaceColors } from '../theme/tokens';

type ChatSlug = 'wenshu' | 'sishu' | 'h5';

const CARDS: {
  slug: ChatSlug;
  label: string;
  color: string;
  colorSoft: string;
  icon: React.ComponentType<any>;
  intro: string[];
  cta: string;
}[] = [
  {
    slug: 'wenshu',
    label: '问数',
    color: spaceColors.wenshu,
    colorSoft: 'rgba(37, 99, 235, 0.10)',
    icon: BarChartOutlined,
    intro: ['一句话查数据，自动出图', 'SQL 生成与口径解读', '血缘追溯 · 对比 · 趋势'],
    cta: '开始探索',
  },
  {
    slug: 'sishu',
    label: '私塾先生',
    color: spaceColors.sishu,
    colorSoft: 'rgba(217, 119, 6, 0.10)',
    icon: ReadOutlined,
    intro: ['出题 · 判分 · 错题本', '学情画像与复习规划', 'AI 教材与讲义生成'],
    cta: '开始学习',
  },
  {
    slug: 'h5',
    label: 'H5 展台',
    color: spaceColors.h5,
    colorSoft: 'rgba(8, 145, 178, 0.10)',
    icon: MobileOutlined,
    intro: ['手机端随时练题', '错题回顾与报告', '移动学习空间'],
    cta: '打开展台',
  },
];

const NewChatHome: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthCtx);

  const enter = (slug: ChatSlug) => {
    if (slug === 'h5') {
      navigate('/h5-publish');
      return;
    }
    navigate(`/e/${slug}/chat`);
  };

  return (
    <div data-testid="newchat-home" style={{ flex: 1, overflow: 'auto', background: tokens_bg() }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '96px 32px 48px' }}>
        <h1
          style={{
            fontSize: 30, fontWeight: 600, color: 'var(--text-primary, #222)',
            margin: '0 0 10px', letterSpacing: '-0.01em', textAlign: 'center',
          }}
          data-testid="portal-greeting"
        >
          {user?.sub ? `${user.sub}，今天想从哪儿开始？` : '今天想从哪儿开始？'}
        </h1>
        <p style={{ textAlign: 'center', color: 'var(--text-tertiary, #999)', margin: '0 0 56px', fontSize: 14 }}>
          选择一位专家进入对应工作台
        </p>

        <div
          style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}
          data-testid="portal-cards"
        >
          {CARDS.map((c) => (
            <div
              key={c.slug}
              role="button"
              tabIndex={0}
              data-testid={`portal-card-${c.slug}`}
              onClick={() => enter(c.slug)}
              onKeyDown={(e) => { if (e.key === 'Enter') enter(c.slug); }}
              onMouseEnter={(ev) => {
                ev.currentTarget.style.transform = 'translateY(-6px)';
                ev.currentTarget.style.boxShadow = `0 16px 40px ${c.colorSoft}, 0 4px 16px rgba(0,0,0,0.06)`;
                ev.currentTarget.style.borderColor = c.color;
              }}
              onMouseLeave={(ev) => {
                ev.currentTarget.style.transform = 'none';
                ev.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)';
                ev.currentTarget.style.borderColor = 'var(--border-subtle, #e5e7eb)';
              }}
              className="ux-portal-card"
              style={{
                position: 'relative', overflow: 'hidden',
                padding: '28px 24px 22px', borderRadius: 18, cursor: 'pointer',
                border: '1px solid var(--border-subtle, #e5e7eb)', background: 'var(--bg-content, #fff)',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                transition: 'transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease',
                display: 'flex', flexDirection: 'column', gap: 14,
              }}
            >
              {/* 顶部空间色渐变条 */}
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: `linear-gradient(90deg, ${c.color}, ${c.color}22)` }} />
              <div
                style={{
                  width: 60, height: 60, borderRadius: 16, display: 'flex', alignItems: 'center',
                  justifyContent: 'center', background: c.colorSoft,
                }}
              >
                <c.icon style={{ fontSize: 30, color: c.color }} />
              </div>
              <div style={{ fontSize: 21, fontWeight: 650, color: 'var(--text-primary, #222)' }}>{c.label}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 84 }}>
                {c.intro.map((line) => (
                  <div key={line} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary, #555)' }}>
                    <span style={{ width: 5, height: 5, borderRadius: 99, background: c.color, flexShrink: 0 }} />
                    {line}
                  </div>
                ))}
              </div>
              <div
                style={{
                  marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  paddingTop: 12, borderTop: '1px solid var(--border-subtle, #eef0f3)', fontSize: 13,
                  fontWeight: 600, color: c.color,
                }}
              >
                {c.cta}
                <ArrowRightOutlined />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

function tokens_bg(): string {
  return 'var(--bg-page, #f7f8fa)';
}

export default NewChatHome;
