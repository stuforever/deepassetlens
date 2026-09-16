/**
 * 母题详情页 —— 1:1 复刻自原仓 DeepTutor
 * web/app/(workspace)/mother-questions/[mid]/page.tsx（Next.js+Tailwind → React+antd）。
 * 复刻纪律：区块顺序/按钮文案/确认弹窗/空态逐字保留（i18n key 直出原仓 locales/zh/app.json 中文）；
 * 技术栈替换：next/navigation → react-router-dom（useParams/useNavigate/useSearchParams）；
 * lucide-react → @ant-design/icons；notify → antd message；fetch(apiUrl(...)) → fetch('/api/v1/...')。
 * 共享常量/表单数据构建器走同目录 dtFields.ts，表单件复用 ./MotherQuestionForm 的 MotherQuestionFields。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeftOutlined, CaretRightOutlined, CheckCircleOutlined, ClockCircleOutlined,
  CloseCircleOutlined, CloseOutlined, FilterOutlined, FormOutlined, PlayCircleOutlined,
  QuestionCircleOutlined, ReloadOutlined, RobotOutlined, SaveOutlined,
  ThunderboltOutlined, VideoCameraOutlined,
} from '@ant-design/icons';
import { Button, Col, Input, Row, message } from 'antd';
import { MotherQuestionFields } from './MotherQuestionForm';
import {
  buildPayload, toFormData, CATEGORY_DISPLAY, GRADE_DISPLAY, MASTERY_COLOR,
  MASTERY_DISPLAY, SUBJECT_COLORS, SUBJECT_DISPLAY,
  type MotherQuestionData,
} from './dtFields';

interface Variant { id: string; question_text: string; answer?: string; difficulty: number; variant_type?: string; source?: string; }
interface Mother {
  id: string; title: string; question_text: string; standard_answer?: string;
  wrong_answer?: string; detailed_analysis?: string; note?: string;
  solution_steps?: { step?: number; text?: string }[]; key_points?: string[];
  difficulty: number; grade?: string; category?: string; knowledge_point_id?: string;
  subject?: string; textbook_id?: string; chapter_id?: string;
  variant_count: number; video_count: number; mastery_status?: string; variants?: Variant[];
  photo_url?: string; wrong_answer_image_url?: string; ocr_text?: string;
  wrong_reason?: string; tags?: string[]; assets?: { url: string; type: string; ocr_text?: string }[];
  related_lecture_doc_ids?: string[]; correct_transferred_at?: number;
}

function formatPrediction(ts: number | null): string | null {
  if (!ts) return null;
  const d = new Date(ts * 1000);
  const now = new Date();
  const diffDays = Math.ceil((d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return '今天';
  if (diffDays === 1) return '明天';
  if (diffDays <= 7) return `${diffDays} 天后`;
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

interface ReviewState {
  retention: number;
  interval_index?: number;
  total_reviews?: number;
  card: { stability: number; difficulty: number; reps: number; lapses: number; due?: number | null; state?: string };
  state?: { due?: number | null; next_review_at?: number | null };
}

interface ReviewHistory {
  total: number;
  correct?: number;
  accuracy?: number;
}

interface Attempts {
  total: number;
  correct: number;
  accuracy: number;
  items?: { is_correct: boolean; create_time: number; rating?: number; time_spent?: number }[];
}

interface SimilarQuestion {
  id: string;
  title: string;
  similarity: number;
  snippet?: string;
}

// ---- 样式常量（Tailwind 语义 → 内联样式） ----
const MUTED = '#6b7280';
const PRIMARY = '#1677ff';
const CARD: CSSProperties = { border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, background: '#fff' };
const rowStyle: CSSProperties = { display: 'flex', justifyContent: 'space-between' };
const clampStyle: CSSProperties = { display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' } as CSSProperties;
const rateBtnStyle = (color: string): CSSProperties => ({
  padding: '6px 8px', borderRadius: 4, background: color, color: '#fff', fontSize: 12, border: 'none', cursor: 'pointer',
});
const sectionTitleStyle: CSSProperties = { margin: 0, fontSize: 16, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 };
const mb12TitleStyle = (extra?: CSSProperties): CSSProperties => ({ ...sectionTitleStyle, marginBottom: 12, ...extra });

export default function MotherQuestionDetail() {
  // ⑤R F1 集成修正：KeepAlive 页签架构无 <Routes>，useParams() 恒空（详情永不取到 mid，
  // 连 GET 都不发直接「母题不存在」）——改从 pathname 尾段解析（/:mid 路由段约定）。
  const location = useLocation();
  const mid = location.pathname.split('/').filter(Boolean).pop() || '';
  const navigate = useNavigate();
  const [m, setM] = useState<Mother | null>(null);
  const [loading, setLoading] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [reviewQ, setReviewQ] = useState<Variant | null>(null);
  const [reviewHistory, setReviewHistory] = useState<ReviewHistory | null>(null);
  const [reviewState, setReviewState] = useState<ReviewState | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState<MotherQuestionData | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [zoomUrl, setZoomUrl] = useState<string | null>(null);
  const [aiSolving, setAiSolving] = useState(false);
  const [aiText, setAiText] = useState('');
  const [attempts, setAttempts] = useState<Attempts | null>(null);
  const [noteText, setNoteText] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  const [similarQs, setSimilarQs] = useState<SimilarQuestion[] | null>(null);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [transferring, setTransferring] = useState(false);
  const [lectureDocId, setLectureDocId] = useState('');
  const [linkingLecture, setLinkingLecture] = useState(false);

  const load = useCallback(async () => {
    if (!mid) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/mother-questions/${mid}`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setM(data);
      setNoteText(data.note || '');
    } catch { message.error('加载失败'); }
    finally { setLoading(false); }
  }, [mid]);

  const loadHistory = useCallback(async () => {
    if (!mid) return;
    try {
      const [hRes, sRes, aRes] = await Promise.all([
        fetch(`/api/v1/mother-questions/${mid}/review/history`),
        fetch(`/api/v1/mother-questions/${mid}/review/state`),
        fetch(`/api/v1/mother-questions/${mid}/attempts?limit=20`),
      ]);
      setReviewHistory(await hRes.json());
      if (sRes.ok) setReviewState(await sRes.json());
      if (aRes.ok) setAttempts(await aRes.json());
    } catch { /* 原仓空 catch：历史/状态加载失败静默 */ }
  }, [mid]);

  useEffect(() => { load(); loadHistory(); }, [load, loadHistory]);

  const [searchParams, setSearchParams] = useSearchParams();
  // ?edit=1 深链只在挂载消费一次（按 mid 记账防重入）：进入编辑态立即清除 edit
  // 参数——否则保存成功后 editMode 翻 false 会再次命中本 effect 重进编辑态，
  // 页面永退不出（P6 门禁实测：PATCH 200 仍停留"编辑中"）。
  const editConsumedFor = useRef<string | null>(null);
  const startEdit = useCallback(() => {
    if (!m) return;
    setEditForm(toFormData(m));
    setEditMode(true);
  }, [m]);
  useEffect(() => {
    if (editConsumedFor.current === mid) return;
    if (searchParams.get('edit') === '1' && m) {
      editConsumedFor.current = mid ?? null;
      startEdit();
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, m, startEdit, setSearchParams, mid]);

  // View-mode form data (memoized; must be before any early return to satisfy Rules of Hooks)
  const viewForm = useMemo(() => (m ? toFormData(m) : toFormData({})), [m]);

  // ---- All handlers (no hooks below this point) ----

  const startReview = async () => {
    setReviewing(true);
    try {
      const res = await fetch(`/api/v1/mother-questions/${mid}/review/next`);
      if (!res.ok) { message.error('无变式题可复习'); return; }
      setShowAnswer(false);
      setReviewQ(await res.json());
    } catch { message.error('取复习题失败'); }
    finally { setReviewing(false); }
  };

  const submitReview = async (rating: number) => {
    if (!reviewQ) return;
    try {
      await fetch(`/api/v1/mother-questions/${mid}/review/submit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variant_id: reviewQ.id, rating }),
      });
      const labels: Record<number, string> = { 1: '再来一次', 2: '困难', 3: '良好', 4: '简单' };
      message.success(labels[rating] || '已记录');
      setReviewQ(null); await loadHistory(); await load();
    } catch { message.error('提交失败'); }
  };

  const startAiSolve = async () => {
    setAiSolving(true);
    setAiText('');
    try {
      const res = await fetch(`/api/v1/mother-questions/${mid}/ai_solve`, { method: 'POST' });
      if (!res.ok || !res.body) throw new Error();
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let acc = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        acc += decoder.decode(value, { stream: true });
        setAiText(acc);
      }
    } catch { message.error('AI 解题失败'); }
    finally { setAiSolving(false); }
  };

  const transfer = async (target: 'mastered' | 'not_mastered') => {
    const ep = target === 'mastered' ? 'transfer-to-mastered' : 'transfer-to-active';
    try {
      await fetch(`/api/v1/mother-questions/${mid}/${ep}`, { method: 'POST' });
      message.success(target === 'mastered' ? '已标记掌握' : '已转回未掌握');
      await load();
    } catch { message.error('转换失败'); }
  };

  const onDelete = async () => {
    if (!window.confirm('确认删除此母题？此操作不可撤销。')) return;
    try {
      await fetch(`/api/v1/mother-questions/${mid}`, { method: 'DELETE' });
      message.success('已删除');
      navigate('/e/tutor/admin/mother-questions');
    } catch { message.error('删除失败'); }
  };

  const saveNote = async () => {
    setSavingNote(true);
    try {
      await fetch(`/api/v1/mother-questions/${mid}/note`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: noteText }),
      });
      message.success('笔记已保存');
      await load();
    } catch { message.error('保存失败'); }
    finally { setSavingNote(false); }
  };

  const transferToCorrect = async () => {
    if (!window.confirm('确认将此题转入正确题库？将标记为已掌握。')) return;
    setTransferring(true);
    try {
      await fetch(`/api/v1/mother-questions/${mid}/transfer-to-correct`, { method: 'POST' });
      message.success('已转入正确题库');
      await load();
    } catch { message.error('转换失败'); }
    finally { setTransferring(false); }
  };

  const findSimilar = async () => {
    setLoadingSimilar(true);
    setSimilarQs(null);
    try {
      const res = await fetch(`/api/v1/mother-questions/${mid}/similar?top_k=5`, { method: 'POST' });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setSimilarQs(data.items || []);
    } catch { message.error('查找相似题失败'); }
    finally { setLoadingSimilar(false); }
  };

  const linkLecture = async () => {
    const docId = lectureDocId.trim();
    if (!docId) return;
    setLinkingLecture(true);
    try {
      await fetch(`/api/v1/mother-questions/${mid}/lectures/${encodeURIComponent(docId)}`, { method: 'POST' });
      message.success('已关联讲义');
      setLectureDocId('');
      await load();
    } catch { message.error('关联失败'); }
    finally { setLinkingLecture(false); }
  };

  const unlinkLecture = async (docId: string) => {
    try {
      await fetch(`/api/v1/mother-questions/${mid}/lectures/${encodeURIComponent(docId)}`, { method: 'DELETE' });
      message.success('已取消关联');
      await load();
    } catch { message.error('操作失败'); }
  };

  const cancelEdit = () => { setEditMode(false); setEditForm(null); };
  const saveEdit = async () => {
    if (!editForm || !m) return;
    if (!editForm.title || !editForm.question_text) { message.error('标题和题干必填'); return; }
    setSavingEdit(true);
    try {
      const payload = buildPayload(editForm);
      const res = await fetch(`/api/v1/mother-questions/${m.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error();
      message.success('已更新');
      setEditMode(false);
      setEditForm(null);
      load();
    } catch { message.error('保存失败'); }
    finally { setSavingEdit(false); }
  };
  const saveEditAndTransfer = async () => {
    if (!editForm || !m) return;
    setSavingEdit(true);
    try {
      const payload = buildPayload(editForm);
      await fetch(`/api/v1/mother-questions/${m.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      await fetch(`/api/v1/mother-questions/${m.id}/transfer-to-correct`, { method: 'POST' });
      message.success('已保存并转入正确题');
      setEditMode(false);
      setEditForm(null);
      load();
    } catch { message.error('操作失败'); }
    finally { setSavingEdit(false); }
  };

  if (loading && !m) return <div style={{ padding: 32, textAlign: 'center', color: MUTED }} data-testid="mq-detail-loading">加载中…</div>;
  if (!m) return <div style={{ padding: 32, textAlign: 'center', color: MUTED }} data-testid="mq-detail-missing">母题不存在</div>;

  const variants = m.variants ?? [];
  const subjColor = SUBJECT_COLORS[m.subject || 'other'] || SUBJECT_COLORS.other;
  const nextReviewTs = reviewState?.card?.due ?? reviewState?.state?.due ?? reviewState?.state?.next_review_at ?? null;
  const nextReview = formatPrediction(nextReviewTs);

  return (
    <div style={{ height: '100%', overflowY: 'auto', background: '#fff', padding: 16 }} data-testid="mq-detail-page">
      {/* AI 解题流式输出末尾光标闪烁（原 Tailwind animate-pulse 等价） */}
      <style>{'@keyframes mqAiCursor { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }'}</style>
      {/* ---- Header ---- */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
          <Button type="text" onClick={() => navigate('/e/tutor/admin/mother-questions')} data-testid="mq-back-btn" style={{ flexShrink: 0, padding: 8 }} icon={<ArrowLeftOutlined style={{ fontSize: 20 }} />} />
          <span style={{ fontSize: 12, padding: '2px 6px', borderRadius: 4, color: '#fff', flexShrink: 0, backgroundColor: subjColor }}>{SUBJECT_DISPLAY[m.subject || 'other']}</span>
          <h1 data-testid="mq-detail-title" style={{ fontSize: 20, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis', margin: 0 }}>
            <QuestionCircleOutlined style={{ color: PRIMARY, flexShrink: 0 }} />{m.title}
          </h1>
          <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 4, background: '#f1f5f9', flexShrink: 0 }}>{"★".repeat(m.difficulty)}</span>
          {m.grade && <span style={{ fontSize: 12, color: MUTED, flexShrink: 0 }}>{GRADE_DISPLAY[m.grade] || m.grade}</span>}
          {m.category && <span style={{ fontSize: 12, color: MUTED, flexShrink: 0 }}>· {CATEGORY_DISPLAY[m.category] || m.category}</span>}
          {m.mastery_status && <span data-testid="mq-mastery-status" style={{ fontSize: 12, flexShrink: 0, color: MASTERY_COLOR[m.mastery_status] }}>· {MASTERY_DISPLAY[m.mastery_status]}</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {editMode ? (
            <>
              <Button onClick={cancelEdit} data-testid="mq-cancel-edit-btn">取消</Button>
              <Button type="primary" onClick={saveEdit} loading={savingEdit} icon={<SaveOutlined />} data-testid="mq-save-edit-btn">保存</Button>
              <Button onClick={saveEditAndTransfer} disabled={savingEdit} data-testid="mq-save-transfer-btn" style={{ color: '#059669' }}>保存并转正确题</Button>
            </>
          ) : (
            <>
              <Button onClick={startEdit} data-testid="mq-edit-btn">修改</Button>
              <Button onClick={onDelete} data-testid="mq-delete-btn" style={{ color: '#e11d48' }}>删除</Button>
              {m.mastery_status !== 'mastered' ? (
                <Button onClick={() => transfer('mastered')} data-testid="mq-transfer-mastered-btn" style={{ color: '#059669' }}>标记掌握</Button>
              ) : (
                <Button onClick={() => transfer('not_mastered')} data-testid="mq-transfer-active-btn" style={{ color: '#e11d48' }}>转回未掌握</Button>
              )}
              <Button onClick={transferToCorrect} loading={transferring} icon={<CheckCircleOutlined />} data-testid="mq-transfer-correct-btn" style={{ color: '#059669' }}>转正确题</Button>
            </>
          )}
          <Button type="primary" onClick={() => navigate('/e/tutor/admin/book')} data-testid="mq-generate-video-btn" icon={<ThunderboltOutlined />}>生成视频</Button>
          <Button onClick={load} data-testid="mq-reload-btn" icon={<ReloadOutlined />} />
        </div>
      </div>

      {/* ---- Two-column layout ---- */}
      <Row gutter={16}>
        {/* ===== LEFT: MotherQuestionFields (read-only in view, editable in edit) ===== */}
        <Col xs={24} lg={14}>
          <div style={CARD}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <h2 style={sectionTitleStyle}>
                <QuestionCircleOutlined style={{ color: PRIMARY }} />
                {editMode ? '编辑母题' : '母题内容'}
              </h2>
              {editMode && (
                <span style={{ fontSize: 12, color: '#d97706', background: '#fffbeb', padding: '2px 8px', borderRadius: 4 }}>编辑中</span>
              )}
            </div>
            <MotherQuestionFields
              value={editMode && editForm ? editForm : viewForm}
              onChange={(patch) => setEditForm((f) => (f ? { ...f, ...patch } : f))}
              readOnly={!editMode}
              showClassification={true}
            />
          </div>
        </Col>

        {/* ===== RIGHT: Extended capabilities ===== */}
        <Col xs={24} lg={10}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* 笔记 */}
            <section style={CARD} data-testid="mq-note-section">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h2 style={sectionTitleStyle}><FormOutlined style={{ color: '#f59e0b' }} /> 我的笔记</h2>
                <Button size="small" onClick={saveNote} loading={savingNote} data-testid="mq-save-note-btn">保存笔记</Button>
              </div>
              <Input.TextArea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="在这里记录你的学习心得、解题思路、易错点分析..."
                style={{ minHeight: 100 }}
                data-testid="mq-note-input"
              />
            </section>

            {/* 复习预测 */}
            <section style={CARD}>
              <h2 style={mb12TitleStyle()}><ClockCircleOutlined style={{ color: PRIMARY }} /> 复习预测</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 14 }}>
                {nextReview ? (
                  <div style={rowStyle}>
                    <span style={{ color: MUTED }}>下次复习</span>
                    <span style={{ fontWeight: 600, color: PRIMARY }}>{nextReview}</span>
                  </div>
                ) : (
                  <p style={{ color: MUTED, margin: 0 }}>暂无复习记录</p>
                )}
                {reviewState?.card && (
                  <>
                    <div style={rowStyle}>
                      <span style={{ color: MUTED }}>保留率</span>
                      <span style={{ fontWeight: 600, color: reviewState.retention > 80 ? '#059669' : reviewState.retention > 50 ? '#d97706' : '#e11d48' }}>{reviewState.retention}%</span>
                    </div>
                    <div style={rowStyle}><span style={{ color: MUTED }}>稳定度</span><span>{reviewState.card.stability}</span></div>
                    <div style={rowStyle}><span style={{ color: MUTED }}>难度</span><span>{reviewState.card.difficulty}</span></div>
                    <div style={rowStyle}><span style={{ color: MUTED }}>复习次数</span><span>{reviewState.card.reps}</span></div>
                    {reviewState.card.lapses > 0 && (
                      <div style={rowStyle}><span style={{ color: MUTED }}>遗忘次数</span><span style={{ color: '#e11d48' }}>{reviewState.card.lapses}</span></div>
                    )}
                  </>
                )}
                {!reviewState?.card && reviewState?.interval_index !== undefined && (
                  <div style={rowStyle}><span style={{ color: MUTED }}>当前间隔档</span><span>{reviewState.interval_index}</span></div>
                )}
                {reviewState?.total_reviews !== undefined && (
                  <div style={rowStyle}><span style={{ color: MUTED }}>累计复习</span><span>{reviewState.total_reviews} 次</span></div>
                )}
              </div>
            </section>

            {/* 复习变式题 */}
            <section style={CARD} data-testid="mq-review-section">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h2 style={sectionTitleStyle}><PlayCircleOutlined style={{ color: PRIMARY }} /> 复习变式题</h2>
                <Button size="small" onClick={startReview} disabled={reviewing || variants.length === 0} loading={reviewing} icon={<CaretRightOutlined />} data-testid="mq-review-next-btn">出一道变式题</Button>
              </div>
              {reviewQ ? (
                <div style={{ padding: 12, border: '1px solid #e5e7eb', borderRadius: 6, background: '#fff' }} data-testid="mq-review-card">
                  <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>{reviewQ.variant_type ?? '变式'} · {"★".repeat(reviewQ.difficulty)}</div>
                  <p style={{ marginBottom: 12, whiteSpace: 'pre-wrap', fontSize: 14 }}>{reviewQ.question_text}</p>
                  {!showAnswer ? (
                    <Button size="small" onClick={() => setShowAnswer(true)} data-testid="mq-show-answer-btn">显示答案</Button>
                  ) : (
                    <div style={{ marginBottom: 12, padding: 8, borderRadius: 4, background: '#f1f5f9', fontSize: 14 }}>点击下方按钮评分（FSRS 1-4 级）</div>
                  )}
                  {showAnswer && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }} data-testid="mq-rate-group">
                      <button onClick={() => submitReview(1)} data-testid="mq-rate-1" style={rateBtnStyle('#e11d48')}>Again</button>
                      <button onClick={() => submitReview(2)} data-testid="mq-rate-2" style={rateBtnStyle('#d97706')}>困难</button>
                      <button onClick={() => submitReview(3)} data-testid="mq-rate-3" style={rateBtnStyle('#0284c7')}>Good</button>
                      <button onClick={() => submitReview(4)} data-testid="mq-rate-4" style={rateBtnStyle('#059669')}>简单</button>
                    </div>
                  )}
                  <button onClick={() => { setReviewQ(null); setShowAnswer(false); }} data-testid="mq-review-skip" style={{ marginTop: 8, padding: '4px 12px', border: '1px solid #d9d9d9', borderRadius: 4, background: 'transparent', fontSize: 12, cursor: 'pointer' }}>跳过</button>
                </div>
              ) : reviewHistory && reviewHistory.total > 0 ? (
                <p style={{ fontSize: 14, color: MUTED }}>已复习 {reviewHistory.total} 次，正确率 {reviewHistory.accuracy}</p>
              ) : (
                <p style={{ fontSize: 14, color: MUTED, padding: '12px 0' }}>{variants.length === 0 ? '暂无变式题' : '点击上方按钮开始复习'}</p>
              )}
            </section>

            {/* AI 解题 */}
            <section style={CARD} data-testid="mq-ai-section">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h2 style={sectionTitleStyle}><RobotOutlined style={{ color: '#9333ea' }} /> AI 解题</h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Button size="small" onClick={startAiSolve} loading={aiSolving} icon={<ThunderboltOutlined />} data-testid="mq-ai-solve-btn">{aiSolving ? '解题中...' : 'AI 解题'}</Button>
                  <Button size="small" onClick={findSimilar} loading={loadingSimilar} icon={<FilterOutlined />} data-testid="mq-similar-btn">相似错题</Button>
                </div>
              </div>
              {aiText && (
                <div style={{ padding: 12, border: '1px solid #e5e7eb', borderRadius: 6, background: '#fff', fontSize: 14, whiteSpace: 'pre-wrap', lineHeight: 1.625, maxHeight: 400, overflowY: 'auto' }} data-testid="mq-ai-text">
                  {aiText}
                  {aiSolving && <span style={{ display: 'inline-block', width: 8, height: 16, background: '#a855f7', marginLeft: 2, verticalAlign: 'text-bottom', animation: 'mqAiCursor 1.2s ease-in-out infinite' }} />}
                </div>
              )}
              {!aiText && !aiSolving && (
                <p style={{ fontSize: 14, color: MUTED, padding: '8px 0' }}>点击“AI 解题”获取详细解题思路和步骤</p>
              )}
              {similarQs && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #e5e7eb' }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>相似错题 ({similarQs.length})</h3>
                  {similarQs.length === 0 ? (
                    <p style={{ fontSize: 14, color: MUTED }}>未找到相似题</p>
                  ) : (
                    <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {similarQs.map((s, i) => (
                        <li key={i} style={{ padding: 8, border: '1px solid #e5e7eb', borderRadius: 4, fontSize: 14, cursor: 'pointer' }} onClick={() => navigate(`/e/tutor/admin/mother-questions/${s.id}`)}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                            <span style={{ fontWeight: 500 }}>{s.title}</span>
                            <span style={{ fontSize: 12, color: MUTED }}>相似度 {Math.round(s.similarity * 100)}%</span>
                          </div>
                          <p style={{ fontSize: 12, color: MUTED, margin: 0, ...clampStyle }}>{s.snippet}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </section>

            {/* 教学视频 */}
            <section style={CARD}>
              <h2 style={mb12TitleStyle()}><VideoCameraOutlined style={{ color: PRIMARY }} /> 教学视频</h2>
              <p style={{ fontSize: 14, color: MUTED, marginBottom: 8 }}>已生成 {m.video_count} 个视频。</p>
              <Button type="primary" size="small" onClick={() => navigate('/e/tutor/admin/book')} icon={<ThunderboltOutlined />}>生成教学视频</Button>
            </section>

            {/* 变式题列表 */}
            <section style={CARD}>
              <h2 style={mb12TitleStyle()}><FilterOutlined /> 变式题 ({variants.length})</h2>
              {variants.length === 0 ? (
                <p style={{ fontSize: 14, color: MUTED, padding: '12px 0', textAlign: 'center' }}>暂无变式题</p>
              ) : (
                <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {variants.map((v) => (
                    <li key={v.id} style={{ padding: 8, border: '1px solid #e5e7eb', borderRadius: 4, fontSize: 14 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontSize: 12, padding: '2px 6px', borderRadius: 4, background: '#f1f5f9' }}>{v.variant_type ?? '变式'} · {"★".repeat(v.difficulty)}</span>
                        <span style={{ fontSize: 12, color: MUTED }}>{v.source ?? ''}</span>
                      </div>
                      <div style={clampStyle}>{v.question_text}</div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* 答题记录 */}
            {attempts && attempts.total > 0 && (
              <section style={CARD}>
                <h2 style={mb12TitleStyle()}><ClockCircleOutlined style={{ color: PRIMARY }} /> 答题记录 ({attempts.total})</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 8, fontSize: 14 }}>
                  <div style={rowStyle}><span style={{ color: MUTED }}>总答题</span><span>{attempts.total}</span></div>
                  <div style={rowStyle}><span style={{ color: MUTED }}>答对</span><span style={{ color: '#059669' }}>{attempts.correct}</span></div>
                  <div style={rowStyle}><span style={{ color: MUTED }}>正确率</span><span>{Math.round(attempts.accuracy * 100)}%</span></div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 160, overflowY: 'auto' }}>
                  {attempts.items?.slice(0, 10).map((a: { is_correct: boolean; create_time: number; rating?: number; time_spent?: number }, i: number) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, padding: 6, borderRadius: 4, border: '1px solid #e5e7eb' }}>
                      {a.is_correct ? <CheckCircleOutlined style={{ color: '#059669', flexShrink: 0 }} /> : <CloseCircleOutlined style={{ color: '#e11d48', flexShrink: 0 }} />}
                      <span style={{ color: MUTED }}>{new Date(a.create_time * 1000).toLocaleString('zh-CN')}</span>
                      {a.rating && <span style={{ color: MUTED }}>· 评分{a.rating}</span>}
                      {a.time_spent && <span style={{ color: MUTED }}>· {Math.round(a.time_spent)}s</span>}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 关联讲义 */}
            <section style={CARD}>
              <h2 style={mb12TitleStyle()}><QuestionCircleOutlined style={{ color: '#f59e0b' }} /> 关联讲义 ({m.related_lecture_doc_ids?.length || 0})</h2>
              {m.textbook_id && <p style={{ fontSize: 12, color: MUTED, marginBottom: 8 }}>教材: {m.textbook_id}</p>}
              {m.chapter_id && <p style={{ fontSize: 12, color: MUTED, marginBottom: 8 }}>章节: {m.chapter_id}</p>}
              {m.related_lecture_doc_ids && m.related_lecture_doc_ids.length > 0 ? (
                <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 12 }}>
                  {m.related_lecture_doc_ids.map((docId, i) => (
                    <li key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12, padding: 6, borderRadius: 4, border: '1px solid #e5e7eb' }}>
                      <span style={{ color: MUTED, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{docId}</span>
                      <button onClick={() => unlinkLecture(docId)} style={{ color: '#f43f5e', background: 'transparent', border: 'none', cursor: 'pointer', flexShrink: 0, marginLeft: 8, fontSize: 12 }}>取消</button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: 12, color: MUTED, marginBottom: 12 }}>未关联讲义。RAG 检索时会用全讲义库。</p>
              )}
              <div style={{ display: 'flex', gap: 4 }}>
                <Input value={lectureDocId} onChange={(e) => setLectureDocId(e.target.value)} placeholder="输入讲义文档ID" style={{ flex: 1, fontSize: 12 }} />
                <button onClick={linkLecture} disabled={linkingLecture || !lectureDocId.trim()} style={{ padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 12, cursor: 'pointer', background: 'transparent', opacity: linkingLecture || !lectureDocId.trim() ? 0.5 : 1 }}>
                  {linkingLecture ? '...' : '+ 关联'}
                </button>
              </div>
            </section>

            {/* 复习统计 */}
            {reviewHistory && reviewHistory.total > 0 && (
              <section style={CARD}>
                <h2 style={mb12TitleStyle()}>复习统计</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 14 }}>
                  <div style={rowStyle}><span style={{ color: MUTED }}>复习次数</span><span>{reviewHistory.total}</span></div>
                  <div style={rowStyle}><span style={{ color: MUTED }}>答对次数</span><span>{reviewHistory.correct}</span></div>
                  <div style={rowStyle}><span style={{ color: MUTED }}>正确率</span><span>{reviewHistory.accuracy}</span></div>
                </div>
              </section>
            )}
          </div>
        </Col>
      </Row>

      {/* 大图预览 */}
      {zoomUrl && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1060, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={() => setZoomUrl(null)}>
          <img src={zoomUrl} alt="题目大图" style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain' }} onClick={(e) => e.stopPropagation()} />
          <button onClick={() => setZoomUrl(null)} style={{ position: 'absolute', top: 16, right: 16, padding: 8, background: 'rgba(255,255,255,0.2)', borderRadius: 6, color: '#fff', border: 'none', cursor: 'pointer' }}>
            <CloseOutlined style={{ fontSize: 24 }} />
          </button>
        </div>
      )}
    </div>
  );
}
