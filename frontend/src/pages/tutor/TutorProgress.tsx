/**
 * ⑤批4（⑤e §一）：学情页 /e/tutor/progress——掌握度列表+色阶映射
 * （retention/mastery → 绿/黄/红：≥0.7 绿｜≥0.4 黄｜<0.4 红；⑤f 视觉调优后迭代）。
 */
import React, { useEffect, useState } from 'react';
import { Card, Empty, List, Progress, Space, Tag, message } from 'antd';

interface MasteryItem {
  knowledge_point_id: string;
  mastery: number;
  attempts: number;
}

/** 色阶映射（⑤e 验收断言色阶映射——导出纯函数供测试）。 */
export function masteryColor(m: number): string {
  if (m >= 0.7) return 'green';
  if (m >= 0.4) return 'orange';
  return 'red';
}

const TutorProgress: React.FC = () => {
  const [items, setItems] = useState<MasteryItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const r = await fetch('/api/tutor/mastery');
        const j = await r.json();
        setItems(j?.data?.items || []);
      } catch {
        message.error('学情获取失败');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const mastered = items.filter((x) => x.mastery >= 0.7).length;

  return (
    <Card title="学情" extra={items.length > 0 ? <Space>已掌握 <b>{mastered}</b> / {items.length}</Space> : null} style={{ margin: 16 }}>
      <List
        loading={loading}
        dataSource={items}
        locale={{ emptyText: <Empty description="暂无学情数据（先去练习页答题）" /> }}
        renderItem={(item) => (
          <List.Item>
            <List.Item.Meta
              title={<Space>{item.knowledge_point_id}<Tag color={masteryColor(item.mastery)}>{masteryColor(item.mastery) === 'green' ? '已掌握' : masteryColor(item.mastery) === 'orange' ? '巩固中' : '待加强'}</Tag></Space>}
              description={
                <Space size="large">
                  <span style={{ width: 200, display: 'inline-block' }}>
                    <Progress percent={Math.round(item.mastery * 100)} size="small"
                      strokeColor={masteryColor(item.mastery)} />
                  </span>
                  <span>练习 {item.attempts} 次</span>
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  );
};

export default TutorProgress;
