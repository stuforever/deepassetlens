/**
 * 母题回收站——1:1 移植自原仓 web/app/(workspace)/mother-questions/trash/page.tsx
 * （Next.js+Tailwind → React+antd；列表/恢复/永久删除/空态文案逐字保留，i18n 直出中文）。
 * API 契约：GET /api/v1/mother-questions/trash、POST /{mid}/restore、DELETE /{mid}?hard=true。
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Spin, message } from 'antd';
import { ArrowLeftOutlined, CloseOutlined, DeleteOutlined, LoadingOutlined, UndoOutlined } from '@ant-design/icons';
import { SUBJECT_COLORS, SUBJECT_DISPLAY, GRADE_DISPLAY } from './dtFields';

interface Mother {
  id: string;
  title: string;
  subject: string;
  grade: string | null;
  category: string | null;
  difficulty: number;
  question_text: string;
  deleted_time: number | null;
  update_time: number;
}

export default function TrashPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Mother[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/mother-questions/trash?page=${page}&page_size=50`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch {
      message.error('加载回收站失败');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  const restore = async (mid: string) => {
    setRestoring(mid);
    try {
      const res = await fetch(`/api/v1/mother-questions/${mid}/restore`, { method: 'POST' });
      if (!res.ok) throw new Error();
      message.success('已恢复');
      load();
    } catch {
      message.error('恢复失败');
    } finally {
      setRestoring(null);
    }
  };

  const hardDelete = async (mid: string) => {
    if (!window.confirm('永久删除后无法恢复，确认？')) return;
    try {
      const res = await fetch(`/api/v1/mother-questions/${mid}?hard=true`, { method: 'DELETE' });
      if (!res.ok) throw new Error();
      message.success('已永久删除');
      load();
    } catch {
      message.error('删除失败');
    }
  };

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 24, maxWidth: 1024, margin: '0 auto' }} data-testid="mq-trash-page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <Button type="text" onClick={() => navigate(-1)} icon={<ArrowLeftOutlined style={{ fontSize: 20 }} />} data-testid="mq-back-btn" />
        <h1 style={{ fontSize: 20, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, margin: 0 }} data-testid="mq-trash-title">
          <DeleteOutlined style={{ fontSize: 20 }} />
          回收站
        </h1>
        <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }} data-testid="mq-trash-count">共 {total} 条已删除</span>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '80px 0' }}>
          <Spin size="large" />
        </div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '80px 0', color: 'rgba(0,0,0,0.45)' }} data-testid="mq-trash-empty">
          <DeleteOutlined style={{ fontSize: 48, display: 'block', margin: '0 auto 12px', opacity: 0.3 }} />
          <p>回收站为空</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }} data-testid="mq-trash-list">
          {items.map((m) => {
            const subjColor = SUBJECT_COLORS[m.subject] || SUBJECT_COLORS.other;
            return (
              <div
                key={m.id}
                onMouseEnter={() => setHoveredId(m.id)}
                onMouseLeave={() => setHoveredId(null)}
                style={{ border: '1px solid #d9d9d9', borderRadius: 8, padding: 12, display: 'flex', alignItems: 'center', gap: 12, background: hoveredId === m.id ? 'rgba(0,0,0,0.03)' : '#fff' }}
                data-testid={`mq-trash-item-${m.id}`}
              >
                <div
                  style={{ width: 4, height: 48, borderRadius: 999, flexShrink: 0, backgroundColor: subjColor }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 500, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.title}</span>
                    <span style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)', flexShrink: 0 }}>{SUBJECT_DISPLAY[m.subject] || m.subject}</span>
                    {m.grade && <span style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)', flexShrink: 0 }}>{GRADE_DISPLAY[m.grade] || m.grade}</span>}
                  </div>
                  <p style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 2, marginBottom: 0 }}>{m.question_text}</p>
                  <p style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)', marginTop: 2, marginBottom: 0 }}>
                    删除时间：{m.deleted_time ? new Date(m.deleted_time * 1000).toLocaleString('zh-CN') : '未知'}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                  <Button
                    type="text"
                    onClick={() => restore(m.id)}
                    disabled={restoring === m.id}
                    title="恢复"
                    data-testid={`mq-restore-${m.id}`}
                    icon={restoring === m.id ? <LoadingOutlined spin style={{ color: '#16a34a' }} /> : <UndoOutlined style={{ color: '#16a34a' }} />}
                  />
                  <Button
                    type="text"
                    onClick={() => hardDelete(m.id)}
                    title="永久删除"
                    data-testid={`mq-hard-delete-${m.id}`}
                    icon={<CloseOutlined style={{ color: '#dc2626' }} />}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
