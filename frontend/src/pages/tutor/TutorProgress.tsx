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
  const [analysis, setAnalysis] = useState<{ total: number; error_type_distribution: Record<string, { count: number; ratio: number }>; conclusion: string } | null>(null);

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
    (async () => {
      try {
        const r = await fetch('/api/tutor/analyze-wrong-questions');
        const j = await r.json();
        setAnalysis(j?.data || null);
      } catch { /* 错因分析失败静默 */ }
    })();
  }, []);

  const mastered = items.filter((x) => x.mastery >= 0.7).length;

  return (
    <div style={{ margin: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
    <Card title="学情" extra={items.length > 0 ? <Space>已掌握 <b>{mastered}</b> / {items.length}</Space> : null} style={{ borderRadius: 12 }}>
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
    {/* ⑤补补-5 步骤 6：错因分析卡片（analyze_wrong_questions 双面之学情页面） */}
    <Card title="错因分析" size="small" style={{ borderRadius: 12 }}>
      {!analysis || analysis.total === 0 ? (
        <span style={{ color: 'var(--text-tertiary)' }}>暂无错题记录。</span>
      ) : (
        <div>
          <div style={{ marginBottom: 6 }}>
            {Object.entries(analysis.error_type_distribution).map(([k, v]) => (
              <Tag key={k} color={k === 'concept' ? 'red' : k === 'careless' ? 'orange' : 'blue'}>
                {k} {v.count} 条（{Math.round(v.ratio * 100)}%）
              </Tag>
            ))}
          </div>
          <span style={{ fontSize: 13 }}>{analysis.conclusion}</span>
        </div>
      )}
    </Card>
    </div>
  );
};

export default TutorProgress;
