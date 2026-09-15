/**
 * ⑤批4（⑤e §一）：错题本 /e/tutor/wrong-book——列表（open/resolved 筛选）+
 * 详情抽屉+导出按钮（导出走 /api/tutor（后续接 export_wrong_book result_ref 下载））。
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Button, Card, Drawer, Empty, List, Segmented, Space, Tag, message } from 'antd';

interface WrongItem {
  wq_id: string;
  mother_question_id: string;
  variant_text: string;
  error_context: string;
  status: string;
  wrong_at: string;
  resolved_at: string | null;
}

const TutorWrongBook: React.FC = () => {
  const [items, setItems] = useState<WrongItem[]>([]);
  const [status, setStatus] = useState<string>('open');
  const [loading, setLoading] = useState(false);
  const [current, setCurrent] = useState<WrongItem | null>(null);

  const load = useCallback(async (st: string) => {
    setLoading(true);
    try {
      const r = await fetch(`/api/tutor/wrong-questions?status=${encodeURIComponent(st)}&page_size=100`);
      const j = await r.json();
      setItems(j?.data?.items || []);
    } catch {
      message.error('错题列表获取失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(status); }, [load, status]);

  const exportBook = async () => {
    try {
      const r = await fetch('/api/tutor/wrong-questions?status=&page_size=100');
      const j = await r.json();
      const all = j?.data?.items || [];
      const lines = ['# 错题本（前端导出）', ''];
      all.forEach((x: WrongItem) => {
        lines.push(`- [${x.status}] ${x.variant_text}`);
        if (x.error_context) lines.push(`  - 上下文: ${x.error_context}`);
      });
      const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'wrongbook.md';
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${all.length} 条`);
    } catch {
      message.error('导出失败');
    }
  };

  return (
    <Card
      title="错题本"
      extra={
        <Space>
          <Segmented
            value={status}
            onChange={(v) => setStatus(v as string)}
            options={[{ label: '未解决', value: 'open' }, { label: '已解决', value: 'resolved' }, { label: '全部', value: '' }]}
          />
          <Button onClick={exportBook}>导出</Button>
        </Space>
      }
      style={{ margin: 16 }}
    >
      <List
        loading={loading}
        dataSource={items}
        locale={{ emptyText: <Empty description="没有错题，继续保持" /> }}
        renderItem={(item) => (
          <List.Item onClick={() => setCurrent(item)} style={{ cursor: 'pointer' }}>
            <List.Item.Meta
              title={<Space><span>{item.variant_text}</span><Tag color={item.status === 'open' ? 'red' : 'green'}>{item.status === 'open' ? '未解决' : '已解决'}</Tag></Space>}
              description={item.mother_question_id ? `关联母题: ${item.mother_question_id}` : undefined}
            />
          </List.Item>
        )}
      />
      <Drawer
        title="错题详情"
        open={!!current}
        onClose={() => setCurrent(null)}
        width={480}
      >
        {current && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div><b>题面：</b>{current.variant_text}</div>
            {current.error_context && <div><b>错误上下文：</b>{current.error_context}</div>}
            <div><b>状态：</b><Tag color={current.status === 'open' ? 'red' : 'green'}>{current.status}</Tag></div>
            <div><b>记录时间：</b>{current.wrong_at}</div>
            {current.mother_question_id && <div><b>关联母题：</b>{current.mother_question_id}</div>}
          </Space>
        )}
      </Drawer>
    </Card>
  );
};

export default TutorWrongBook;
