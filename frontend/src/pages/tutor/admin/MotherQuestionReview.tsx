/**
 * 复习页（FSRS 翻转卡复习，复刻自原仓 web/app/(workspace)/mother-questions/review/page.tsx，1:1）。
 * 技术栈替换：next/navigation → react-router-dom；lucide-react → @ant-design/icons；
 * notify → antd message；i18n key → 中文直出（原仓 zh/app.json 原文）；
 * 共享常量 SUBJECT_COLORS/SUBJECT_DISPLAY/GRADE_DISPLAY/CATEGORY_DISPLAY ← ./dtFields（同原仓契约面）；
 * fetch(apiUrl("/api/v1/...")) → fetch('/api/v1/...')（路径/参数/请求体逐字一致）。
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { LoadingOutlined, LeftOutlined, RotateLeftOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { Button, message } from 'antd';
import { SUBJECT_COLORS, SUBJECT_DISPLAY, GRADE_DISPLAY, CATEGORY_DISPLAY } from './dtFields';

interface ReviewItem {
  id: string;
  title: string;
  question_text: string;
  subject: string;
  difficulty: number;
  grade: string | null;
  category: string | null;
  mastery_status: string;
  standard_answer?: string | null;
  photo_url?: string | null;
}

interface CardInfo {
  stability: number;
  difficulty: number;
  reps: number;
  lapses: number;
  due: number | null;
  retention: number;
  interval_days: number;
  state: string;
}

const MUTED = '#6b7280';
const PRIMARY = '#1677ff';

export default function MotherQuestionReview() {
  const navigate = useNavigate();
  const [queue, setQueue] = useState<ReviewItem[]>([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [flipped, setFlipped] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [card, setCard] = useState<CardInfo | null>(null);
  const [retention, setRetention] = useState<number>(0);
  const [completed, setCompleted] = useState(0);
  const startTimeRef = useRef<number>(Date.now());

  const loadQueue = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/mother-questions/reviews/due?max_items=50');
      if (!res.ok) throw new Error();
      const data = await res.json();
      const items = (data.items ?? []).map((m: ReviewItem) => ({
        id: m.id, title: m.title, question_text: m.question_text,
        subject: m.subject, difficulty: m.difficulty,
        grade: m.grade, category: m.category,
        mastery_status: m.mastery_status,
        standard_answer: m.standard_answer, photo_url: m.photo_url,
      }));
      setQueue(items);
      setIdx(0);
      setCompleted(0);
      if (items.length > 0) {
        loadCard(items[0].id);
      }
    } catch {
      message.error('加载复习队列失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCard = async (mid: string) => {
    try {
      const res = await fetch(`/api/v1/mother-questions/${mid}/review/state`);
      if (!res.ok) return;
      const data = await res.json();
      setCard(data.card ?? null);
      setRetention(data.retention ?? 0);
    } catch { /* ignore */ }
  };

  useEffect(() => { loadQueue(); }, [loadQueue]);

  const current = queue[idx];

  const submitRating = async (rating: number) => {
    if (!current) return;
    setSubmitting(true);
    const timeSpent = (Date.now() - startTimeRef.current) / 1000;
    try {
      const res = await fetch(`/api/v1/mother-questions/${current.id}/review/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, time_spent: timeSpent }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setCard(data.card ?? null);
      setRetention(data.retention ?? 0);
      setCompleted((c) => c + 1);
      message.success(
        rating === 1 ? '再来一次' : rating === 2 ? '困难' : rating === 3 ? '良好' : '简单'
      );
      // 下一题
      setTimeout(() => {
        setFlipped(false);
        startTimeRef.current = Date.now();
        if (idx + 1 < queue.length) {
          setIdx(idx + 1);
          loadCard(queue[idx + 1].id);
        } else {
          // 全部完成
          setQueue([]);
        }
      }, 500);
    } catch {
      message.error('提交失败');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '80px 0' }}>
        <LoadingOutlined style={{ fontSize: 32, color: MUTED }} spin />
      </div>
    );
  }

  if (queue.length === 0) {
    return (
      <div style={{ padding: '80px 24px', maxWidth: 768, margin: '0 auto', textAlign: 'center' }} data-testid="mq-review-done">
        <div style={{ fontSize: 60, marginBottom: 16 }}>🎉</div>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          {completed > 0 ? `已完成 ${completed} 道复习！` : '暂无待复习题目'}
        </h2>
        <p style={{ color: MUTED, marginBottom: 24 }}>
          {completed > 0 ? '今天的复习任务已完成' : '所有题目都不需要复习'}
        </p>
        <Button
          onClick={() => navigate('/e/tutor/admin/mother-questions')}
          data-testid="mq-review-back"
        >
          返回母题库
        </Button>
      </div>
    );
  }

  const subjColor = SUBJECT_COLORS[current.subject] || SUBJECT_COLORS.other;
  const progress = ((idx) / queue.length) * 100;

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 24, maxWidth: 768, margin: '0 auto' }} data-testid="mq-review-page">
      {/* 进度条 */}
      <div style={{ marginBottom: 16 }} data-testid="mq-review-progress">
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: MUTED, marginBottom: 4 }}>
          <span>复习进度 {idx + 1} / {queue.length}</span>
          <span>已完成 {completed}</span>
        </div>
        <div style={{ height: 8, background: '#f3f4f6', borderRadius: 999, overflow: 'hidden' }}>
          <div style={{ height: '100%', background: PRIMARY, transition: 'all 0.3s', width: `${progress}%` }} />
        </div>
      </div>

      {/* 保留率显示 */}
      {card && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16, fontSize: 12 }} data-testid="mq-review-retention">
          <span style={{ color: MUTED }}>
            保留率: <span style={{ fontWeight: 700, color: retention > 80 ? '#16a34a' : retention > 50 ? '#ca8a04' : '#dc2626' }}>{retention}%</span>
          </span>
          {card.reps > 0 && (
            <>
              <span style={{ color: MUTED }}>复习次数: {card.reps}</span>
              <span style={{ color: MUTED }}>遗忘次数: {card.lapses}</span>
              <span style={{ color: MUTED }}>稳定度: {card.stability}</span>
            </>
          )}
        </div>
      )}

      {/* 翻转卡片 */}
      <div
        style={{ position: 'relative', cursor: 'pointer', minHeight: 400, marginBottom: 24, perspective: '1000px' }}
        onClick={() => setFlipped(!flipped)}
        data-testid="mq-review-card"
      >
        <div
          style={{
            position: 'relative', width: '100%', height: '100%', transition: 'transform 0.5s',
            transformStyle: 'preserve-3d',
            transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
            minHeight: 400,
          }}
        >
          {/* 正面 - 题目 */}
          <div
            style={{
              position: 'absolute', top: 0, right: 0, bottom: 0, left: 0,
              border: '2px solid #e5e7eb', borderRadius: 12, padding: 24, background: '#fff',
              display: 'flex', flexDirection: 'column', backfaceVisibility: 'hidden',
            }}
            data-testid="mq-review-front"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <div style={{ width: 8, height: 24, borderRadius: 999, backgroundColor: subjColor }} />
              <span style={{ fontSize: 12, color: MUTED }}>{SUBJECT_DISPLAY[current.subject] || current.subject}</span>
              {current.grade && <span style={{ fontSize: 12, color: MUTED }}>· {GRADE_DISPLAY[current.grade] || current.grade}</span>}
              {current.category && <span style={{ fontSize: 12, color: MUTED }}>· {CATEGORY_DISPLAY[current.category] || current.category}</span>}
              <span style={{ fontSize: 12, color: '#eab308', marginLeft: 'auto' }}>{"★".repeat(current.difficulty)}</span>
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12, marginTop: 0 }}>{current.title}</h3>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              <p style={{ fontSize: 14, whiteSpace: 'pre-wrap', margin: 0 }}>{current.question_text}</p>
              {current.photo_url && (
                <img src={current.photo_url} alt="题目图" style={{ marginTop: 16, maxWidth: '100%', borderRadius: 4, border: '1px solid #e5e7eb' }} />
              )}
            </div>
            <div style={{ textAlign: 'center', fontSize: 12, color: MUTED, marginTop: 16 }}>
              点击卡片查看答案 →
            </div>
          </div>

          {/* 背面 - 答案 */}
          <div
            style={{
              position: 'absolute', top: 0, right: 0, bottom: 0, left: 0,
              border: '2px solid #e5e7eb', borderRadius: 12, padding: 24, background: '#f0fdf4',
              display: 'flex', flexDirection: 'column',
              backfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
            }}
            data-testid="mq-review-answer-face"
          >
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12, marginTop: 0, color: '#15803d' }}>✓ 答案</h3>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              <p style={{ fontSize: 14, whiteSpace: 'pre-wrap', margin: 0 }}>
                {current.standard_answer || '（暂无标准答案）'}
              </p>
            </div>
            <div style={{ textAlign: 'center', fontSize: 12, color: MUTED, marginTop: 16 }}>
              ← 点击卡片返回题目
            </div>
          </div>
        </div>
      </div>

      {/* FSRS 评分按钮 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }} data-testid="mq-rate-group">
        <button
          onClick={(e) => { e.stopPropagation(); submitRating(1); }}
          disabled={submitting}
          data-testid="mq-rate-1"
          style={{ padding: '12px 16px', borderRadius: 8, background: '#fee2e2', color: '#b91c1c', fontSize: 14, fontWeight: 500, border: 'none', cursor: 'pointer', opacity: submitting ? 0.5 : 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
        >
          <CloseOutlined style={{ fontSize: 16 }} />
          <span>再来</span>
          <span style={{ fontSize: 12, opacity: 0.6 }}>{"<1min"}</span>
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); submitRating(2); }}
          disabled={submitting}
          data-testid="mq-rate-2"
          style={{ padding: '12px 16px', borderRadius: 8, background: '#ffedd5', color: '#c2410c', fontSize: 14, fontWeight: 500, border: 'none', cursor: 'pointer', opacity: submitting ? 0.5 : 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
        >
          <span style={{ fontSize: 12 }}>😰</span>
          <span>困难</span>
          <span style={{ fontSize: 12, opacity: 0.6 }}>1d</span>
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); submitRating(3); }}
          disabled={submitting}
          data-testid="mq-rate-3"
          style={{ padding: '12px 16px', borderRadius: 8, background: '#dbeafe', color: '#1d4ed8', fontSize: 14, fontWeight: 500, border: 'none', cursor: 'pointer', opacity: submitting ? 0.5 : 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
        >
          <CheckOutlined style={{ fontSize: 16 }} />
          <span>良好</span>
          <span style={{ fontSize: 12, opacity: 0.6 }}>3d</span>
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); submitRating(4); }}
          disabled={submitting}
          data-testid="mq-rate-4"
          style={{ padding: '12px 16px', borderRadius: 8, background: '#dcfce7', color: '#15803d', fontSize: 14, fontWeight: 500, border: 'none', cursor: 'pointer', opacity: submitting ? 0.5 : 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
        >
          <span style={{ fontSize: 12 }}>😎</span>
          <span>简单</span>
          <span style={{ fontSize: 12, opacity: 0.6 }}>7d+</span>
        </button>
      </div>

      {/* 底部导航 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
        <Button
          icon={<LeftOutlined />}
          onClick={() => navigate('/e/tutor/admin/mother-questions')}
          data-testid="mq-review-exit"
        >
          退出
        </Button>
        <Button
          icon={<RotateLeftOutlined />}
          onClick={() => { setFlipped(false); loadQueue(); }}
          data-testid="mq-review-reload"
        >
          重新加载
        </Button>
      </div>
    </div>
  );
}
