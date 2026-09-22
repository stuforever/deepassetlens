/**
 * H5 发布管理页（v3 §三 / Task 5）：左 12 页卡 + 右 390px 手机框 iframe 实时预览。
 * 访问地址运行时取 hostname（不硬编码 IP）；[复制链接][二维码] 复用 QrCode 组件（QrSvg）。
 * 12 页路径=routes 实测静态路由（排除 book/:bookId、paths/:bookId 参数页与 share/notebook 附属页）。
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Button, Tag, Typography, message } from 'antd';
import {
  MessageOutlined, ReadOutlined, BookOutlined, SoundOutlined, RedoOutlined,
  CameraOutlined, ProfileOutlined, NodeIndexOutlined, BarChartOutlined,
  GlobalOutlined, HomeOutlined, UserOutlined,
} from '@ant-design/icons';
import { QrSvg } from '../tutor/h5/h5shared/QrCode';

const { Text } = Typography;

interface H5Page { key: string; label: string; path: string; icon: React.ComponentType<any>; }

const H5_PAGES: H5Page[] = [
  { key: 'home', label: '首页', path: '/e/tutor-h5', icon: HomeOutlined },
  { key: 'chat', label: '对话', path: '/e/tutor-h5/chat', icon: MessageOutlined },
  { key: 'learn', label: '学习', path: '/e/tutor-h5/learn', icon: ReadOutlined },
  { key: 'learn-textbook', label: '教材学', path: '/e/tutor-h5/learn/textbook', icon: BookOutlined },
  { key: 'classroom', label: '课堂', path: '/e/tutor-h5/classroom', icon: SoundOutlined },
  { key: 'review', label: '复习', path: '/e/tutor-h5/review', icon: RedoOutlined },
  { key: 'wrong', label: '错题录入', path: '/e/tutor-h5/wrong', icon: CameraOutlined },
  { key: 'wrongbook', label: '错题本', path: '/e/tutor-h5/wrongbook', icon: ProfileOutlined },
  { key: 'paths', label: '精通之路', path: '/e/tutor-h5/paths', icon: NodeIndexOutlined },
  { key: 'report', label: '学情报告', path: '/e/tutor-h5/report', icon: BarChartOutlined },
  { key: 'atlas', label: '知识地图', path: '/e/tutor-h5/atlas', icon: GlobalOutlined },
  { key: 'me', label: '我的', path: '/e/tutor-h5/me', icon: UserOutlined },
];

function lanUrl(path: string): string {
  // 运行时取当前源（协议+主机+端口同 dev/prod 一致；审查 Minor：禁硬编码 :23000）
  return `${window.location.origin}${path}`;
}

const PublishManager: React.FC = () => {
  const [selected, setSelected] = useState<H5Page>(H5_PAGES[1]); // 默认「对话」
  const [copied, setCopied] = useState(false);

  const url = useMemo(() => lanUrl(selected.path), [selected]);
  const iframeSrc = `${selected.path}?onboarding=skip`;

  useEffect(() => { setCopied(false); }, [selected]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      message.success('链接已复制');
    } catch {
      message.warning('复制失败——请手动选择地址文本');
    }
  };

  return (
    <div data-testid="h5-publish" style={{ flex: 1, overflow: 'auto', background: 'var(--bg-page, #f7f8fa)' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>
        {/* 页头（C 模板变体：标题+唯一主操作） */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>H5 发布管理</h2>
            <Text type="secondary" style={{ fontSize: 12 }}>手机端页面清单与真机预览——点卡右侧实时预览</Text>
          </div>
          <Tag color="cyan">{H5_PAGES.length} 页</Tag>
        </div>

        <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
          {/* 左：12 页卡片网格 */}
          <div
            data-testid="h5-publish-grid"
            style={{
              flex: 1, display: 'grid', gap: 12,
              gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            }}
          >
            {H5_PAGES.map((pg) => {
              const active = pg.key === selected.key;
              return (
                <div
                  key={pg.key}
                  role="button"
                  tabIndex={0}
                  data-testid={`h5-card-${pg.key}`}
                  onClick={() => setSelected(pg)}
                  onKeyDown={(e) => { if (e.key === 'Enter') setSelected(pg); }}
                  style={{
                    padding: '14px 12px', borderRadius: 12, cursor: 'pointer',
                    border: active ? '2px solid #0891B2' : '1px solid var(--border-subtle, #e5e7eb)',
                    background: 'var(--bg-content, #fff)',
                    display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-start',
                  }}
                >
                  <pg.icon style={{ fontSize: 18, color: '#0891B2' }} />
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{pg.label}</div>
                  <Text type="secondary" style={{ fontSize: 11 }}>{pg.path}</Text>
                </div>
              );
            })}
          </div>

          {/* 右：390px 圆角手机框 iframe 预览 */}
          <div
            data-testid="h5-publish-preview"
            style={{
              width: 390, flexShrink: 0, borderRadius: 24, border: '8px solid #1f2937',
              overflow: 'hidden', background: '#fff', boxShadow: '0 8px 28px rgba(0,0,0,0.14)',
            }}
          >
            <div style={{ height: 24, background: '#1f2937', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: 80, height: 6, borderRadius: 3, background: '#4b5563' }} />
            </div>
            <iframe
              key={iframeSrc}
              src={iframeSrc}
              title={`h5 预览 ${selected.label}`}
              style={{ width: '100%', height: 680, border: 'none', display: 'block' }}
            />
          </div>
        </div>

        {/* 访问地址 + 复制链接 + 二维码 */}
        <div
          data-testid="h5-publish-share"
          style={{
            marginTop: 16, padding: '12px 16px', borderRadius: 12,
            background: 'var(--bg-content, #fff)', border: '1px solid var(--border-subtle, #e5e7eb)',
            display: 'flex', alignItems: 'center', gap: 12,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>访问地址（同网段真机/模拟器）</Text>
            <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {url}
            </div>
          </div>
          <Button size="small" onClick={copy} data-testid="h5-publish-copy">{copied ? '已复制' : '复制链接'}</Button>
          <div data-testid="h5-publish-qr" style={{ width: 64, height: 64, flexShrink: 0 }}>
            <QrSvg value={url} size={64} />
          </div>
        </div>

        {/* 移动端真机提示条 */}
        <div
          data-testid="h5-publish-mobile-hint"
          style={{
            marginTop: 12, padding: '10px 16px', borderRadius: 12, fontSize: 12,
            background: '#ecfeff', border: '1px solid #a5f3fc', color: '#155e75',
          }}
        >
          📱 移动端真机预览：手机扫码或同网段直接访问上方地址；桌面右侧为实时预览框。
        </div>
      </div>
    </div>
  );
};

export default PublishManager;
