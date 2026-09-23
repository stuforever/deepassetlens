/**
 * 1:1 复刻自原仓 DeepTutor web/app/(workspace)/mother-questions/photo/page.tsx（拍照录入）。
 * 技术栈等价替换：next/navigation→react-router-dom(useNavigate)；lucide-react→@ant-design/icons；
 * notify→antd message；i18n→原仓 zh locale 中文直出；next/image→<img>；Suspense 外壳去掉（无 lazy）。
 * 原仓 MotherQuestionFields（components/mother-questions/MotherQuestionFields.tsx）目标仓无对应组件，
 * 按其调用面（showClassification/showWrongToggle=true，photoMode/readOnly=false）1:1 内联实现。
 * API 契约原样：fetch('/api/v1/mother-questions/...')，multipart 上传/降级 OCR/查重/入库/转正确题逐字保留。
 */
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Checkbox, Input, Select, Tag, message } from 'antd';
import {
  ArrowLeftOutlined, CameraOutlined, CheckCircleOutlined, CloseCircleOutlined, DeleteOutlined,
  LoadingOutlined, SaveOutlined, ScanOutlined, UploadOutlined, ZoomInOutlined,
} from '@ant-design/icons';
import {
  CATEGORIES, CATEGORY_DISPLAY, GRADES, GRADE_DISPLAY, SUBJECTS, SUBJECT_DISPLAY,
  buildPayload, toFormData,
} from './dtFields';
import type { Chapter, KnowledgePoint, MotherQuestionData, Textbook } from './dtFields';

/** 原仓 group-hover 悬浮遮罩（Tailwind 无法内联，注入一次） */
const HOVER_CSS = `
.mqf-img-overlay{position:absolute;inset:0;border-radius:4px;display:flex;align-items:center;justify-content:center;gap:8px;opacity:0;transition:opacity .15s;background:rgba(0,0,0,0);}
.mqf-img-group:hover .mqf-img-overlay{opacity:1;background:rgba(0,0,0,.3);}
`;

interface PhotoItem {
  id: string;
  data: MotherQuestionData;
  selected: boolean;
  saved: 'none' | 'ok' | 'fail';
}

/** 原仓 text-xs text-muted-foreground 字段标签 */
function Label({ children, testid }: { children: React.ReactNode; testid?: string }) {
  return <div style={{ fontSize: 12, color: '#6b7280' }} data-testid={testid}>{children}</div>;
}

/** lucide Sparkles 图标的内联 SVG 等价（@ant-design/icons 无对应图标） */
function SparklesIcon({ style }: { style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={style} aria-hidden="true">
      <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
      <path d="M20 3v4" /><path d="M22 5h-4" /><path d="M4 17v2" /><path d="M5 18H3" />
    </svg>
  );
}

// ---- ImageUpload 子组件（原仓共享组件 1:1）----
function ImageUpload({
  label, url, onChange, ocr = false, onOcrText, readOnly = false, areaTestId,
}: {
  label: string;
  url: string | null;
  onChange: (url: string | null) => void;
  ocr?: boolean;
  onOcrText?: (text: string) => void;
  readOnly?: boolean;
  areaTestId?: string;
}) {
  const [uploading, setUploading] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const onFile = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const endpoint = ocr ? '/api/v1/mother-questions/ocr-upload' : '/api/v1/mother-questions/upload_image';
      const res = await fetch(endpoint, { method: 'POST', body: fd });
      if (!res.ok) throw new Error();
      const data = await res.json();
      onChange(data.photo_url || data.url);
      if (ocr && data.text) onOcrText?.(data.text);
      message.success(ocr ? `识别到 ${data.line_count || 0} 行` : '图片已上传');
    } catch {
      message.error(ocr ? 'OCR 识别失败' : '上传失败');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div data-testid={areaTestId}>
      <Label>{label}</Label>
      <div style={{ marginTop: 4, display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        {url ? (
          <div style={{ position: 'relative' }} className="mqf-img-group">
            <img
              src={url} alt={label}
              style={{ width: 128, height: 128, objectFit: 'cover', borderRadius: 4, border: '1px solid #e5e7eb', cursor: 'pointer' }}
              onClick={() => setZoomOpen(true)}
              data-testid={areaTestId ? `${areaTestId}-preview` : undefined}
            />
            {!readOnly && (
              <div className="mqf-img-overlay">
                <Button size="small" icon={<ZoomInOutlined />} title="大图预览" onClick={() => setZoomOpen(true)} />
                <Button size="small" icon={<DeleteOutlined />} title="删除图片" onClick={() => onChange(null)} />
              </div>
            )}
          </div>
        ) : readOnly ? (
          <div style={{ width: 128, height: 128, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e5e7eb', borderRadius: 4, fontSize: 12, color: '#6b7280' }}>无图</div>
        ) : (
          <Button
            type="dashed"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
            data-testid={areaTestId ? `${areaTestId}-btn` : undefined}
            style={{ width: 128, height: 128, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4, fontSize: 12, color: '#6b7280' }}
          >
            {uploading ? <LoadingOutlined spin style={{ fontSize: 24 }} /> : (
              <><UploadOutlined style={{ fontSize: 24 }} /><span>点击上传</span></>
            )}
          </Button>
        )}
        {!readOnly && (
          <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ''; }} />
        )}
      </div>
      {zoomOpen && url && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 60, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={() => setZoomOpen(false)}>
          <img src={url} alt={label} style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain' }} onClick={(e) => e.stopPropagation()} />
          <Button type="text" icon={<DeleteOutlined style={{ fontSize: 24, color: '#fff' }} />} style={{ position: 'absolute', top: 16, right: 16 }} onClick={() => setZoomOpen(false)} />
        </div>
      )}
    </div>
  );
}

// ---- MotherQuestionFields 组件（原仓 1:1，调用面 photoMode=false/showWrongToggle=true）----
function MotherQuestionFields({
  value, onChange, showClassification = true, photoMode = false, showWrongToggle = false, readOnly = false,
}: {
  value: MotherQuestionData;
  onChange: (patch: Partial<MotherQuestionData>) => void;
  showClassification?: boolean;
  photoMode?: boolean;
  showWrongToggle?: boolean;
  readOnly?: boolean;
}) {
  const [kps, setKps] = useState<KnowledgePoint[]>([]);
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [aiFilling, setAiFilling] = useState(false);

  useEffect(() => {
    fetch('/api/v1/mother-questions/dict')
      .then((r) => r.json())
      .then((d) => {
        setKps(d.knowledge_points ?? []);
        setTextbooks(d.textbooks ?? []);
        setChapters(d.chapters ?? []);
      })
      .catch(() => {});
  }, []);

  const filteredChapters = value.textbook_id
    ? chapters.filter((c) => c.textbook_id === value.textbook_id)
    : chapters;

  const onAiFill = async () => {
    if (!value.question_text && !value.photo_url) {
      message.error('请先输入题干或上传题目图');
      return;
    }
    setAiFilling(true);
    try {
      const res = await fetch('/api/v1/mother-questions/recognize_text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: value.question_text,
          image_url: value.photo_url,
          subject: value.subject,
          wrong_answer: value.wrong_answer,
          title: value.title,
        }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      if (data.fields) {
        const f = data.fields;
        onChange({
          ...(f.title ? { title: f.title } : {}),
          ...(f.question_text ? { question_text: f.question_text } : {}),
          ...(f.standard_answer ? { standard_answer: f.standard_answer } : {}),
          ...(f.wrong_answer ? { wrong_answer: f.wrong_answer } : {}),
          ...(f.detailed_analysis ? { detailed_analysis: f.detailed_analysis } : {}),
          ...(f.wrong_reason ? { wrong_reason: f.wrong_reason } : {}),
          ...(f.category ? { category: f.category } : {}),
          ...(f.difficulty ? { difficulty: Number(f.difficulty) } : {}),
          ...(Array.isArray(f.key_points) ? { key_points: f.key_points.join('；') } : {}),
        });
        message.success(data.fallback ? 'AI 填充降级（已填部分字段）' : 'AI 智能填充完成');
      } else {
        message.warning(data.msg || 'AI 未返回有效字段');
      }
    } catch {
      message.error('AI 填充失败');
    } finally {
      setAiFilling(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }} data-testid="mqf-root">
      {/* 错题/正确题 toggle */}
      {showWrongToggle && (
        <div style={{ display: 'flex', gap: 8 }} data-testid="mqf-wrong-toggle">
          <Button
            style={value.is_wrong ? { flex: 1, background: '#f43f5e', color: '#fff', borderColor: '#f43f5e' } : { flex: 1 }}
            onClick={() => onChange({ is_wrong: true })}
            disabled={readOnly}
            data-testid="mqf-toggle-wrong"
            data-active={value.is_wrong ? 'true' : 'false'}
          >
            <CloseCircleOutlined style={{ marginInlineEnd: 4 }} />错题
          </Button>
          <Button
            style={!value.is_wrong ? { flex: 1, background: '#10b981', color: '#fff', borderColor: '#10b981' } : { flex: 1 }}
            onClick={() => onChange({ is_wrong: false })}
            disabled={readOnly}
            data-testid="mqf-toggle-correct"
            data-active={!value.is_wrong ? 'true' : 'false'}
          >
            <CheckCircleOutlined style={{ marginInlineEnd: 4 }} />正确题
          </Button>
        </div>
      )}

      {/* 标题 + AI填充 */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Label>标题 *</Label>
          {!readOnly && (
            <Button
              size="small"
              onClick={onAiFill}
              loading={aiFilling}
              icon={aiFilling ? undefined : <SparklesIcon />}
              data-testid="mqf-ai-fill"
              title="AI 智能填充：从题干/图片中自动提取字段"
              style={{ fontSize: 12, background: '#9333ea', color: '#fff', borderColor: '#9333ea' }}
            >
              AI 智能填充
            </Button>
          )}
        </div>
        <Input
          style={{ marginTop: 4 }}
          value={value.title}
          onChange={(e) => onChange({ title: e.target.value })}
          readOnly={readOnly}
          data-testid="mqf-title"
          placeholder="如：鸡兔同笼"
        />
      </div>

      {/* 题干 */}
      <div>
        <Label>题干 *</Label>
        <Input.TextArea
          style={{ marginTop: 4 }}
          autoSize={{ minRows: 4 }}
          value={value.question_text}
          onChange={(e) => onChange({ question_text: e.target.value })}
          readOnly={readOnly}
          data-testid="mqf-question-text"
        />
      </div>

      {/* 图片上传区 */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
        ...(photoMode ? { border: '2px solid #c084fc', borderRadius: 8, padding: 12, background: 'rgba(147,51,234,0.05)' } : {}),
      }}>
        <ImageUpload
          label={photoMode ? '题目图（上传即自动识别）' : '题目图（原题截图）'}
          url={value.photo_url}
          onChange={(url) => onChange({ photo_url: url })}
          ocr={photoMode}
          readOnly={readOnly}
          areaTestId="mqf-photo"
          onOcrText={photoMode ? (text) => {
            onChange({ question_text: text });
            if (!value.title) {
              const firstLine = text.split('\n')[0] || '';
              onChange({ title: firstLine.slice(0, 20) });
            }
          } : undefined}
        />
        <ImageUpload
          label="错误答案截图"
          url={value.wrong_answer_image_url}
          onChange={(url) => onChange({ wrong_answer_image_url: url })}
          readOnly={readOnly}
          areaTestId="mqf-wrong-image"
        />
      </div>
      {photoMode && value.photo_url && !aiFilling && !readOnly && (
        <Button
          onClick={onAiFill}
          data-testid="mqf-photo-ai-fill"
          icon={<SparklesIcon />}
          style={{ background: '#9333ea', color: '#fff', borderColor: '#9333ea' }}
        >
          AI 智能填充（从图片提取答案、解析等）
        </Button>
      )}

      {/* 你的答案 + 标准答案 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <Label testid="mqf-wrong-answer-label">{value.is_wrong ? '你的答案（错误答案）' : '你的答案'}</Label>
          <Input.TextArea
            style={{ marginTop: 4, ...(value.is_wrong ? { borderColor: '#fda4af' } : {}) }}
            autoSize={{ minRows: 3 }}
            value={value.wrong_answer}
            onChange={(e) => onChange({ wrong_answer: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-wrong-answer"
            placeholder="如：12（学生的错误答案）"
          />
        </div>
        <div>
          <Label>标准答案</Label>
          <Input.TextArea
            style={{ marginTop: 4 }}
            autoSize={{ minRows: 3 }}
            value={value.standard_answer}
            onChange={(e) => onChange({ standard_answer: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-standard-answer"
          />
        </div>
      </div>

      {/* 错误原因 + 详细解析 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <Label>错因</Label>
          <Input
            style={{ marginTop: 4 }}
            value={value.wrong_reason}
            onChange={(e) => onChange({ wrong_reason: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-wrong-reason"
            placeholder="如：计算时忘记进位"
          />
        </div>
        <div>
          <Label>详细解析</Label>
          <Input.TextArea
            style={{ marginTop: 4 }}
            autoSize={{ minRows: 3 }}
            value={value.detailed_analysis}
            onChange={(e) => onChange({ detailed_analysis: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-detailed-analysis"
            placeholder="知识点、解题思路、易错点"
          />
        </div>
      </div>

      {/* 要点 + 标签 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <Label>要点（用；分隔）</Label>
          <Input
            style={{ marginTop: 4 }}
            value={value.key_points}
            onChange={(e) => onChange({ key_points: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-key-points"
            placeholder="如：假设法；方程法"
          />
        </div>
        <div>
          <Label>标签（用；分隔）</Label>
          <Input
            style={{ marginTop: 4 }}
            value={value.tags}
            onChange={(e) => onChange({ tags: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-tags"
            placeholder="如：期中考试；易错题"
          />
        </div>
      </div>

      {/* 科目 / 年级 / 题型 / 难度 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
        <div>
          <Label>科目</Label>
          <Select
            style={{ width: '100%', marginTop: 4 }}
            value={value.subject}
            onChange={(v) => onChange({ subject: v })}
            disabled={readOnly}
            data-testid="mqf-subject"
            options={Object.entries(SUBJECTS).map(([k]) => ({ value: k, label: SUBJECT_DISPLAY[k] }))}
          />
        </div>
        <div>
          <Label>年级</Label>
          <Select
            style={{ width: '100%', marginTop: 4 }}
            value={value.grade}
            onChange={(v) => onChange({ grade: v })}
            disabled={readOnly}
            data-testid="mqf-grade"
            options={GRADES.map((g) => ({ value: g, label: GRADE_DISPLAY[g] || g }))}
          />
        </div>
        <div>
          <Label>题型</Label>
          <Select
            style={{ width: '100%', marginTop: 4 }}
            value={value.category}
            onChange={(v) => onChange({ category: v })}
            disabled={readOnly}
            data-testid="mqf-category"
            options={CATEGORIES.map((c) => ({ value: c, label: CATEGORY_DISPLAY[c] || c }))}
          />
        </div>
        <div>
          <Label>难度</Label>
          <Select
            style={{ width: '100%', marginTop: 4 }}
            value={value.difficulty}
            onChange={(v) => onChange({ difficulty: Number(v) })}
            disabled={readOnly}
            data-testid="mqf-difficulty"
            options={[1, 2, 3, 4, 5].map((d) => ({ value: d, label: '★'.repeat(d) }))}
          />
        </div>
      </div>

      {/* 教材 / 章节 / 知识点 */}
      {showClassification && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          <div>
            <Label>教材</Label>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={value.textbook_id}
              onChange={(v) => onChange({ textbook_id: v, chapter_id: '' })}
              disabled={readOnly}
              data-testid="mqf-textbook"
              options={[
                { value: '', label: '未指定' },
                ...textbooks.map((tb) => ({ value: tb.id, label: tb.name + (tb.grade ? ` (${GRADE_DISPLAY[tb.grade] || tb.grade})` : '') })),
              ]}
            />
          </div>
          <div>
            <Label>章节</Label>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={value.chapter_id}
              onChange={(v) => onChange({ chapter_id: v })}
              disabled={!value.textbook_id || readOnly}
              data-testid="mqf-chapter"
              options={[
                { value: '', label: '未指定' },
                ...filteredChapters.map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
          </div>
          <div>
            <Label>知识点</Label>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={value.knowledge_point_id}
              onChange={(v) => onChange({ knowledge_point_id: v })}
              disabled={readOnly}
              data-testid="mqf-kp"
              options={[
                { value: '', label: '未挂载' },
                ...kps.map((k) => ({ value: k.id, label: k.name })),
              ]}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function PhotoEntryContent() {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [recognizing, setRecognizing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [items, setItems] = useState<PhotoItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const onUpload = async (file: File) => {
    setUploading(true);
    setRecognizing(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/v1/mother-questions/batch_recognize_all', {
        method: 'POST',
        body: fd,
      });
      if (!res.ok) {
        // 降级到单张 OCR
        const ocrRes = await fetch('/api/v1/mother-questions/ocr-upload', {
          method: 'POST',
          body: fd,
        });
        if (!ocrRes.ok) throw new Error();
        const data = await ocrRes.json();
        const text = data.text || '';
        const firstLine = text.split('\n')[0] || '';
        setItems([{
          id: crypto.randomUUID(),
          data: toFormData({ title: firstLine.slice(0, 20), question_text: text, photo_url: data.photo_url }),
          selected: true,
          saved: 'none',
        }]);
        message.success(`识别到 ${data.line_count || 0} 行`);
        return;
      }
      const data = await res.json();
      const questions = data.questions || [];
      if (questions.length === 0) {
        message.warning('未识别到题目，请手动添加');
        setItems([{ id: crypto.randomUUID(), data: toFormData({}), selected: true, saved: 'none' }]);
        return;
      }
      setItems(questions.map((q: { text?: string; qno?: string; crop_url?: string | null }) => {
        const firstLine = (q.text || '').split('\n')[0] || '';
        return {
          id: crypto.randomUUID(),
          data: toFormData({
            title: (q.qno || firstLine).slice(0, 20),
            question_text: q.text || '',
            photo_url: q.crop_url || null,
          }),
          selected: true,
          saved: 'none' as const,
        };
      }));
      message.success(`识别到 ${questions.length} 道题`);
    } catch {
      message.error('识别失败');
    } finally {
      setUploading(false);
      setRecognizing(false);
    }
  };

  const updateItem = (id: string, patch: Partial<MotherQuestionData>) =>
    setItems((prev) => prev.map((it) => it.id === id ? { ...it, data: { ...it.data, ...patch } } : it));
  const toggleSelect = (id: string) =>
    setItems((prev) => prev.map((it) => it.id === id ? { ...it, selected: !it.selected } : it));
  const removeItem = (id: string) =>
    setItems((prev) => prev.filter((it) => it.id !== id));
  const addBlank = () =>
    setItems((prev) => [...prev, { id: crypto.randomUUID(), data: toFormData({}), selected: true, saved: 'none' as const }]);

  const saveAll = async () => {
    const selected = items.filter((it) => it.selected);
    if (selected.length === 0) { message.error('未选择任何题目'); return; }
    setSaving(true);
    let okCount = 0, failCount = 0;
    for (const item of selected) {
      try {
        // 重复检测
        const dupRes = await fetch('/api/v1/mother-questions/check_duplicate', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: item.data.title, question_text: item.data.question_text }),
        });
        const dupData = await dupRes.json().catch(() => ({}));
        if (dupData.duplicates?.length > 0) {
          if (!window.confirm(`「${item.data.title}」发现相似母题，确认创建？`)) {
            setItems((prev) => prev.map((it) => it.id === item.id ? { ...it, saved: 'fail' } : it));
            failCount++;
            continue;
          }
        }
        const payload = buildPayload(item.data, { force: true });
        const res = await fetch('/api/v1/mother-questions', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error();
        // 若标记为正确题，再调用转正确题接口
        if (!item.data.is_wrong) {
          const data = await res.json();
          await fetch('/api/v1/mother-questions/' + data.id + '/transfer-to-correct', { method: 'POST' });
        }
        setItems((prev) => prev.map((it) => it.id === item.id ? { ...it, saved: 'ok' } : it));
        okCount++;
      } catch {
        setItems((prev) => prev.map((it) => it.id === item.id ? { ...it, saved: 'fail' } : it));
        failCount++;
      }
    }
    setSaving(false);
    if (failCount === 0) {
      message.success(`已保存 ${okCount} 道题`);
      setTimeout(() => navigate('/e/sishu/admin/mother-questions'), 1500);
    } else {
      message.warning(`成功 ${okCount} 道，失败 ${failCount} 道`);
    }
  };

  const wrongCount = items.filter((it) => it.data.is_wrong).length;
  const correctCount = items.filter((it) => !it.data.is_wrong).length;
  const selectedCount = items.filter((it) => it.selected).length;

  return (
    <div style={{ height: '100%', overflowY: 'auto', background: '#f5f5f5' }} data-testid="mq-photo-page">
      <style>{HOVER_CSS}</style>
      <div style={{ position: 'sticky', top: 0, zIndex: 40, background: '#fff', borderBottom: '1px solid #e5e7eb', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/e/sishu/admin/mother-questions')} data-testid="mq-back-btn" />
          <div style={{ fontSize: 18, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }} data-testid="mq-photo-title">
            <CameraOutlined style={{ color: '#1677ff' }} /> 拍照录入
          </div>
        </div>
        {items.length > 0 && (
          <Button type="primary" loading={saving} icon={saving ? undefined : <SaveOutlined />} disabled={saving || selectedCount === 0}
            onClick={saveAll} data-testid="mq-photo-save-all">
            {`保存全部（${selectedCount}题）`}
          </Button>
        )}
      </div>

      <div style={{ maxWidth: 768, margin: '0 auto', padding: 24 }}>
        {items.length === 0 ? (
          <section style={{ padding: 16, borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff' }} data-testid="mq-photo-upload">
            <div style={{ fontWeight: 600, marginBottom: 12 }}>上传题目图片</div>
            <div>
              <div
                onClick={() => inputRef.current?.click()}
                style={{ border: '2px dashed #d9d9d9', borderRadius: 8, padding: 48, textAlign: 'center', cursor: 'pointer', background: 'transparent' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = '#f5f5f5'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                {uploading || recognizing ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <LoadingOutlined spin style={{ fontSize: 40, color: '#1677ff' }} />
                    <div style={{ fontSize: 14, color: '#6b7280' }}>{recognizing ? '识别中...' : '上传中...'}</div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <UploadOutlined style={{ fontSize: 40, color: '#9ca3af' }} />
                    <div style={{ fontSize: 14, color: '#6b7280' }}>点击选择题目图片（支持拍照 / 截图，自动切多题）</div>
                  </div>
                )}
              </div>
              <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); e.target.value = ''; }} />
            </div>
          </section>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, padding: '0 4px' }} data-testid="mq-photo-summary">
              <span style={{ fontSize: 14, color: '#6b7280' }}>
                {`共 ${items.length} 题（错题 ${wrongCount} / 正确题 ${correctCount}）`}
              </span>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button size="small" onClick={addBlank} data-testid="mq-photo-add-one">+ 新增一条</Button>
                <Button size="small" icon={<ScanOutlined />} onClick={() => inputRef.current?.click()} data-testid="mq-photo-retake">重新拍照</Button>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }} data-testid="mq-photo-list">
              {items.map((item, idx) => (
                <div key={item.id} style={{
                  borderRadius: 8, border: '2px solid ' + (
                    item.saved === 'ok' ? '#34d399' :
                    item.saved === 'fail' ? '#f87171' :
                    item.data.is_wrong ? '#fecdd3' : '#a7f3d0'
                  ),
                  boxShadow: item.saved === 'ok' ? '0 0 0 2px #a7f3d0' : item.saved === 'fail' ? '0 0 0 2px #fecaca' : undefined,
                  padding: 16,
                }} data-testid={`mq-photo-item-${idx}`} data-saved={item.saved}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <Checkbox checked={item.selected} onChange={() => toggleSelect(item.id)} data-testid={`mq-photo-select-${idx}`} />
                      <span style={{ fontSize: 14, fontWeight: 500 }}>{`第 ${idx + 1} 题`}</span>
                      <Tag style={{ marginInlineEnd: 0, fontSize: 12, border: '1px solid transparent', background: item.data.is_wrong ? '#ffe4e6' : '#d1fae5', color: item.data.is_wrong ? '#be123c' : '#047857' }} data-testid={`mq-photo-kind-${idx}`}>
                        {item.data.is_wrong ? '错题' : '正确题'}
                      </Tag>
                      {item.saved === 'ok' && <span style={{ fontSize: 12, color: '#059669' }}>✓ 已保存</span>}
                      {item.saved === 'fail' && <span style={{ fontSize: 12, color: '#dc2626' }}>✗ 保存失败</span>}
                    </div>
                    <Button type="text" size="small" icon={<DeleteOutlined />} title="删除此题" onClick={() => removeItem(item.id)} data-testid={`mq-photo-remove-${idx}`} />
                  </div>
                  <MotherQuestionFields
                    value={item.data}
                    onChange={(patch) => updateItem(item.id, patch)}
                    showClassification={true}
                    showWrongToggle={true}
                  />
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// 原仓外层 PhotoPage 的 Suspense"加载中…"外壳为 Next.js lazy 专用，本页无 lazy 直接导出
export default function MotherQuestionPhoto() {
  return <PhotoEntryContent />;
}
