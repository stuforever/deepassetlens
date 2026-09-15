/**
 * ⑤批4（⑤e §一）：复习页 /e/tutor/review——到期卡列表+评分四键（Again/Hard/Good/Easy）
 * →POST /api/tutor/review-submit（fsrs_review 引擎，user 会话取）→刷新下一张。
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Button, Card, Empty, List, Space, Tag, message } from 'antd';

interface DueItem {
  card_id: string;
  kind: string;
  item_id: string;
  stability: number;
  reps: number;
  lapses: number;
  due: string;
  overdue_days: number;
}

const RATINGS: Array<{ value: number; label: string; color: string }> = [
  { value: 1, label: 'Again', color: 'red' },
  { value: 2, label: 'Hard', color: 'orange' },
  { value: 3, label: 'Good', color: 'blue' },
  { value: 4, label: 'Easy', color: 'green' },
];

const TutorReview: React.FC = () => {
  const [items, setItems] = useState<DueItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/tutor/due?limit=50');
      const j = await r.json();
      setItems(j?.data?.items || []);
    } catch {
      message.error('到期清单获取失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const submit = async (item: DueItem, rating: number) => {
    setSubmitting(item.card_id);
    try {
      const r = await fetch('/api/tutor/review-submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: item.item_id, kind: item.kind, rating }),
      });
      const j = await r.json();
      if (r.ok && j?.code === 200) {
        message.success(`已评分：下次间隔 ${j.data.interval_days} 天`);
        setItems((prev) => prev.filter((x) => x.card_id !== item.card_id));
      } else {
        message.error(j?.detail || '评分失败');
      }
    } catch {
      message.error('评分提交失败');
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <Card title="到期复习" extra={<a onClick={load}>刷新</a>} style={{ margin: 16 }}>
      <List
        loading={loading}
        dataSource={items}
        locale={{ emptyText: <Empty description="暂无到期复习" /> }}
        renderItem={(item) => (
          <List.Item
            actions={RATINGS.map((rt) => (
              <Button
                key={rt.value}
                size="small"
                type={rt.value === 3 ? 'primary' : 'default'}
                danger={rt.value === 1}
                loading={submitting === item.card_id}
                onClick={() => submit(item, rt.value)}
              >
                {rt.label}
              </Button>
            ))}
          >
            <List.Item.Meta
              title={<Space>{item.item_id}<Tag>{item.kind === 'mother_question' ? '母题' : '知识点'}</Tag></Space>}
              description={
                <Space size="small" wrap>
                  <Tag color={item.overdue_days > 0 ? 'volcano' : 'default'}>
                    {item.overdue_days > 0 ? `逾期 ${item.overdue_days} 天` : '今天到期'}
                  </Tag>
                  <span>reps {item.reps}</span>
                  <span>lapses {item.lapses}</span>
                  <span>stability {Number(item.stability).toFixed(2)}</span>
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  );
};

export default TutorReview;
