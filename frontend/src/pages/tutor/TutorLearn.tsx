/**
 * ⑤补补-3 步骤 3：自主学习页 /e/tutor/learn——章节浏览（图谱树）→知识点精讲→今日任务→「去练习」动线。
 * 数据源：GET /api/tutor/chapters（图谱章节树）+ GET /api/tutor/chapter/{id}/overview（一屏聚合）
 *       + GET /api/tutor/today-tasks（policy 今日任务）。
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, List, Progress, Spin, Tag, Typography, message } from 'antd';
import { PageShell } from '../../components/shell';
import { tokens } from '../../theme/tokens';

const { Text, Paragraph } = Typography;

interface ChapterItem { code: string; name: string; textbook: string }
interface KpItem {
  code: string; name: string; explanation: string; examples: string[];
  mastery: number; reps: number;
}
interface Overview {
  chapter: { code: string; name: string };
  kps: KpItem[];
  wrong_questions: { wq_id: string; variant_text: string; status: string }[];
  wrong_count: number;
  learned_count: number;
}
interface TaskItem { kind: string; item_id: string; title: string; reason: string }

const TutorLearn: React.FC = () => {
  const navigate = useNavigate();
  const [chapters, setChapters] = useState<ChapterItem[]>([]);
  const [active, setActive] = useState<string>('');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [openKp, setOpenKp] = useState<string>('');

  useEffect(() => {
    (async () => {
      try {
        const [c, t] = await Promise.all([
          fetch('/api/tutor/chapters').then((r) => r.json()),
          fetch('/api/tutor/today-tasks?limit=6').then((r) => r.json()),
        ]);
        const items: ChapterItem[] = c?.data?.items || [];
        setChapters(items);
        setTasks(t?.data?.items || []);
        if (items.length > 0) setActive(items[0].code);
      } catch {
        message.error('章节加载失败');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (!active) return;
    (async () => {
      try {
        const r = await fetch(`/api/tutor/chapter/${encodeURIComponent(active)}/overview`);
        const j = await r.json();
        setOverview(j?.data || null);
      } catch {
        setOverview(null);
      }
    })();
  }, [active]);

  return (
    <PageShell title="自主学习" description="章节浏览 → 知识点精讲 → 今日任务 → 练习动线（⑤补-3）">
      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* 左：章节树 */}
        <Card
          title="课程章节"
          size="small"
          style={{ width: 300, borderRadius: 12, flexShrink: 0 }}
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
          ) : chapters.length === 0 ? (
            <Empty description="暂无章节（种子后可查）" imageStyle={{ height: 48 }} />
          ) : (
            <List
              size="small"
              dataSource={chapters}
              renderItem={(ch) => (
                <List.Item
                  onClick={() => setActive(ch.code)}
                  style={{
                    cursor: 'pointer', borderRadius: 8, padding: '8px 10px',
                    background: ch.code === active ? 'var(--bg-hover)' : undefined,
                  }}
                >
                  <div>
                    <Text strong={ch.code === active}>{ch.name}</Text>
                    {ch.textbook && (
                      <div><Text type="secondary" style={{ fontSize: 12 }}>{ch.textbook}</Text></div>
                    )}
                  </div>
                </List.Item>
              )}
            />
          )}
        </Card>

        {/* 右：一屏聚合 */}
        <div style={{ flex: 1, minWidth: 480, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card
            title={overview ? `章节：${overview.chapter.name}` : '章节详情'}
            size="small"
            style={{ borderRadius: 12 }}
            extra={overview && (
              <span>
                <Tag color="blue">知识点 {overview.kps.length}</Tag>
                <Tag color={overview.wrong_count > 0 ? 'red' : 'default'}>错题 {overview.wrong_count}</Tag>
                <Tag color="green">已学 {overview.learned_count}</Tag>
              </span>
            )}
          >
            {!overview ? (
              <Empty description="选择左侧章节" imageStyle={{ height: 48 }} />
            ) : (
              <List
                size="small"
                dataSource={overview.kps}
                renderItem={(kp) => (
                  <List.Item
                    style={{ cursor: 'pointer', display: 'block' }}
                    onClick={() => setOpenKp(openKp === kp.code ? '' : kp.code)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <Text strong>{kp.name}</Text>
                      <Tag color={kp.mastery >= 0.8 ? 'green' : kp.mastery > 0 ? 'blue' : 'default'}>
                        {kp.mastery >= 0.8 ? '已掌握' : kp.mastery > 0 ? '学习中' : '未学'}
                      </Tag>
                      <div style={{ flex: 1, maxWidth: 140 }}>
                        <Progress percent={Math.round(kp.mastery * 100)} size="small" showInfo={false} />
                      </div>
                    </div>
                    {openKp === kp.code && (
                      <div style={{ marginTop: 8, padding: '8px 12px', background: 'var(--bg-hover)', borderRadius: 8 }}>
                        <Paragraph style={{ marginBottom: 6 }}>{kp.explanation || '（精讲待补）'}</Paragraph>
                        {kp.examples.length > 0 && (
                          <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-tertiary)' }}>
                            {kp.examples.map((e, i) => <li key={i} style={{ fontSize: 12 }}>{e}</li>)}
                          </ul>
                        )}
                      </div>
                    )}
                  </List.Item>
                )}
              />
            )}
          </Card>

          <Card title="今日任务" size="small" style={{ borderRadius: 12 }}>
            {tasks.length === 0 ? (
              <Empty description="今日无到期/薄弱任务" imageStyle={{ height: 48 }} />
            ) : (
              <List
                size="small"
                dataSource={tasks}
                renderItem={(t) => (
                  <List.Item>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <Tag color={t.reason === '到期复习' ? 'orange' : 'red'}>{t.reason}</Tag>
                      <Text>{t.title}</Text>
                    </div>
                  </List.Item>
                )}
              />
            )}
            <Button
              type="primary"
              style={{ marginTop: 12, background: tokens.brandGradient }}
              onClick={() => navigate('/e/tutor/practice')}
            >
              去练习
            </Button>
          </Card>
        </div>
      </div>
    </PageShell>
  );
};

export default TutorLearn;
