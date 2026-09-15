/**
 * ⑤补补-4 步骤 2：精通之路页 /e/tutor/path——图谱结构×PG 掌握度→模块卡片三色。
 * 色阶（A4 映射，pass_threshold=0.7 语义）：无卡=灰未学 / 低 retention=蓝学习中 /
 * 高 retention≥0.7=绿已精通。数据源：GET /api/tutor/path。
 */
import React, { useEffect, useState } from 'react';
import { Card, Empty, Spin, Tag, Typography } from 'antd';
import { PageShell } from '../../components/shell';

const { Text } = Typography;

interface KpNode { code: string; name: string; color: 'gray' | 'blue' | 'green'; retention: number; stability: number }
interface ModuleNode { code: string; name: string; textbook: string; color: string; kps: KpNode[] }
interface PathData { textbooks: { code: string; name: string }[]; modules: ModuleNode[]; pass_threshold: number }

const COLOR_META: Record<string, { label: string; bg: string; border: string }> = {
  gray: { label: '未学', bg: 'var(--bg-hover)', border: 'var(--border)' },
  blue: { label: '学习中', bg: 'rgba(22,119,255,0.08)', border: 'rgba(22,119,255,0.45)' },
  green: { label: '已精通', bg: 'rgba(82,196,26,0.10)', border: 'rgba(82,196,26,0.5)' },
};

const TutorPath: React.FC = () => {
  const [data, setData] = useState<PathData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/tutor/path');
        const j = await r.json();
        setData(j?.data || null);
      } catch { /* 失败静默——空态 */ } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <PageShell title="精通之路" description="模块/阶段三色路线图（⑤补-4）">
        <div style={{ textAlign: 'center', padding: 64 }}><Spin size="large" /></div>
      </PageShell>
    );
  }

  return (
    <PageShell title="精通之路" description="模块/阶段三色路线图（⑤补-4）——绿=已精通（retention≥0.7）/蓝=学习中/灰=未学">
      {!data || data.modules.length === 0 ? (
        <Empty description="暂无学习模块（种子后可查）" imageStyle={{ height: 64 }} />
      ) : (
        <>
          <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
            {Object.entries(COLOR_META).map(([k, v]) => (
              <Tag key={k} style={{ borderRadius: 6 }}>{v.label}</Tag>
            ))}
            <Text type="secondary" style={{ fontSize: 12, alignSelf: 'center' }}>
              pass_threshold = {data.pass_threshold}（DeepTutor 语义）
            </Text>
          </div>
          {data.modules.map((m) => (
            <Card
              key={m.code}
              size="small"
              title={(
                <span>
                  {m.name}
                  <Tag color={m.color === 'green' ? 'green' : m.color === 'blue' ? 'blue' : 'default'}
                    style={{ marginLeft: 8 }}>
                    {COLOR_META[m.color]?.label || m.color}
                  </Tag>
                </span>
              )}
              style={{
                borderRadius: 12, marginBottom: 12,
                borderColor: COLOR_META[m.color]?.border,
                background: COLOR_META[m.color]?.bg,
              }}
            >
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {m.kps.map((kp) => (
                  <div
                    key={kp.code}
                    style={{
                      padding: '6px 12px', borderRadius: 8, fontSize: 13,
                      background: COLOR_META[kp.color]?.bg,
                      border: `1px solid ${COLOR_META[kp.color]?.border}`,
                    }}
                  >
                    {kp.name}
                    {kp.color !== 'gray' && (
                      <span style={{ marginLeft: 6, fontSize: 11, opacity: 0.75 }}>
                        R={Math.round(kp.retention * 100)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </>
      )}
    </PageShell>
  );
};

export default TutorPath;
