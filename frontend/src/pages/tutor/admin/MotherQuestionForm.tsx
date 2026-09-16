/**
 * 母题表单字段组件（受控）——1:1 移植自原仓
 * web/components/mother-questions/MotherQuestionFields.tsx
 * （Next.js+Tailwind → React+antd；字段/占位符/API 契约逐字保留，i18n key 直出中文）。
 * 共享常量/类型/payload 构建器统一走同目录 dtFields.ts（值即后端契约）。
 * 依赖端点：/api/v1/mother-questions/dict、/recognize_text、/ocr-upload、/upload_image。
 */
import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { Input, Select, message } from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, DeleteOutlined, LoadingOutlined,
  ThunderboltOutlined, UploadOutlined, ZoomInOutlined,
} from '@ant-design/icons';
import {
  GRADES, CATEGORIES, SUBJECTS, SUBJECT_DISPLAY, GRADE_DISPLAY, CATEGORY_DISPLAY,
  type MotherQuestionData, type KnowledgePoint, type Textbook, type Chapter,
} from './dtFields';

const labelStyle: CSSProperties = { fontSize: 12, color: 'rgba(0,0,0,0.45)' };
const inputStyle: CSSProperties = { width: '100%', marginTop: 4 };
const hoverBtnStyle: CSSProperties = {
  padding: 6, background: 'rgba(255,255,255,0.8)', borderRadius: 6,
  border: 'none', cursor: 'pointer', lineHeight: 1,
};
const selectToggleStyle = (active: boolean, color: string): CSSProperties => ({
  flex: 1, padding: '8px 12px', borderRadius: 6, fontSize: 14, fontWeight: 500,
  cursor: 'pointer', border: active ? '1px solid transparent' : '1px solid #d9d9d9',
  background: active ? color : 'transparent', color: active ? '#fff' : 'inherit',
});

/** 图片上传控件：上传 / 预览 / 大图 / 删除 */
function ImageUpload({
  label, url, onChange, ocr = false, onOcrText, readOnly = false, areaTestId,
}: {
  label: string;
  url: string | null;
  onChange: (url: string | null) => void;
  ocr?: boolean;
  onOcrText?: (text: string) => void;
  readOnly?: boolean;
  /** e2e 选择器面：容器 testid 前缀（容器 / -btn / -preview 派生） */
  areaTestId?: string;
}) {
  const [uploading, setUploading] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const areaProps = areaTestId ? { 'data-testid': areaTestId } : {};

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
    <div {...areaProps}>
      <label style={labelStyle}>{label}</label>
      <div style={{ marginTop: 4, display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        {url ? (
          <div
            style={{ position: 'relative' }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
          >
            <img
              src={url}
              alt={label}
              onClick={() => setZoomOpen(true)}
              data-testid={areaTestId ? `${areaTestId}-preview` : undefined}
              style={{ width: 128, height: 128, objectFit: 'cover', borderRadius: 6, border: '1px solid #d9d9d9', cursor: 'pointer', display: 'block' }}
            />
            {!readOnly && (
              <div
                style={{
                  position: 'absolute', inset: 0, borderRadius: 6,
                  background: hovered ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  opacity: hovered ? 1 : 0, transition: 'opacity 0.2s',
                }}
              >
                <button type="button" onClick={() => setZoomOpen(true)} style={hoverBtnStyle} title="大图预览">
                  <ZoomInOutlined />
                </button>
                <button type="button" onClick={() => onChange(null)} style={hoverBtnStyle} title="删除图片">
                  <DeleteOutlined />
                </button>
              </div>
            )}
          </div>
        ) : readOnly ? (
          <p style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)', fontStyle: 'italic', width: 128, height: 128, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #d9d9d9', borderRadius: 6 }}>
            无图片
          </p>
        ) : (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            data-testid={areaTestId ? `${areaTestId}-btn` : undefined}
            style={{ width: 128, height: 128, border: '2px dashed #d9d9d9', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: 'rgba(0,0,0,0.45)', background: 'transparent', cursor: 'pointer' }}
          >
            {uploading ? <LoadingOutlined spin style={{ fontSize: 24 }} /> : (
              <><UploadOutlined style={{ fontSize: 24, marginBottom: 4 }} /><span>点击上传</span></>
            )}
          </button>
        )}
        {!readOnly && (
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ''; }}
          />
        )}
      </div>
      {/* 大图预览 */}
      {zoomOpen && url && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 1060, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setZoomOpen(false)}
        >
          <img
            src={url}
            alt={label}
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain' }}
          />
          <button
            onClick={() => setZoomOpen(false)}
            style={{ position: 'absolute', top: 16, right: 16, padding: 8, background: 'rgba(255,255,255,0.2)', borderRadius: 6, color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            <DeleteOutlined style={{ fontSize: 24 }} />
          </button>
        </div>
      )}
    </div>
  );
}

interface MotherQuestionFieldsProps {
  value: MotherQuestionData;
  onChange: (patch: Partial<MotherQuestionData>) => void;
  showClassification?: boolean;
  photoMode?: boolean;
  /** 是否显示错题/正确题 toggle（拍照录入/拍照中心用） */
  showWrongToggle?: boolean;
  /** 只读模式：详情页查看时复用同一表单，但不可编辑 */
  readOnly?: boolean;
}

export function MotherQuestionFields({
  value, onChange, showClassification = true, photoMode = false, showWrongToggle = false, readOnly = false,
}: MotherQuestionFieldsProps) {
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
          <button
            type="button"
            onClick={() => onChange({ is_wrong: true })}
            disabled={readOnly}
            data-testid="mqf-toggle-wrong"
            data-active={value.is_wrong ? 'true' : 'false'}
            style={{ ...selectToggleStyle(value.is_wrong, '#f43f5e'), opacity: readOnly ? 0.6 : 1 }}
          >
            <CloseCircleOutlined style={{ marginRight: 4 }} />错题
          </button>
          <button
            type="button"
            onClick={() => onChange({ is_wrong: false })}
            disabled={readOnly}
            data-testid="mqf-toggle-correct"
            data-active={!value.is_wrong ? 'true' : 'false'}
            style={{ ...selectToggleStyle(!value.is_wrong, '#10b981'), opacity: readOnly ? 0.6 : 1 }}
          >
            <CheckCircleOutlined style={{ marginRight: 4 }} />正确题
          </button>
        </div>
      )}

      {/* 标题 + AI填充 */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <label style={labelStyle}>标题 *</label>
          {!readOnly && (
            <button
              type="button"
              onClick={onAiFill}
              disabled={aiFilling}
              data-testid="mqf-ai-fill"
              title="AI 智能填充：从题干/图片中自动提取字段"
              style={{ fontSize: 12, padding: '2px 8px', borderRadius: 6, background: '#9333ea', color: '#fff', border: 'none', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', opacity: aiFilling ? 0.5 : 1 }}
            >
              {aiFilling ? <LoadingOutlined spin style={{ fontSize: 12 }} /> : <ThunderboltOutlined style={{ fontSize: 12 }} />}
              AI 智能填充
            </button>
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
        <label style={labelStyle}>题干 *</label>
        <Input.TextArea
          style={{ marginTop: 4, minHeight: 100 }}
          value={value.question_text}
          onChange={(e) => onChange({ question_text: e.target.value })}
          readOnly={readOnly}
          data-testid="mqf-question-text"
        />
      </div>

      {/* 图片上传区 */}
      <div style={photoMode ? { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, boxShadow: '0 0 0 2px #c084fc', borderRadius: 8, padding: 12, background: 'rgba(250,245,255,0.5)' } : { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
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
        <button
          type="button"
          onClick={onAiFill}
          data-testid="mqf-photo-ai-fill"
          style={{ width: '100%', padding: '8px 12px', borderRadius: 6, background: '#9333ea', color: '#fff', fontSize: 14, border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, cursor: 'pointer' }}
        >
          <ThunderboltOutlined /> AI 智能填充（从图片提取答案、解析等）
        </button>
      )}

      {/* 你的答案 + 标准答案 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <label style={labelStyle} data-testid="mqf-wrong-answer-label">{value.is_wrong ? '你的答案（错误答案）' : '你的答案'}</label>
          <Input.TextArea
            style={{ marginTop: 4, minHeight: 60, border: value.is_wrong ? '1px solid #fda4af' : undefined }}
            value={value.wrong_answer}
            onChange={(e) => onChange({ wrong_answer: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-wrong-answer"
            placeholder="如：12（学生的错误答案）"
          />
        </div>
        <div>
          <label style={labelStyle}>标准答案</label>
          <Input.TextArea
            style={{ marginTop: 4, minHeight: 60 }}
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
          <label style={labelStyle}>错因</label>
          <Input
            style={inputStyle}
            value={value.wrong_reason}
            onChange={(e) => onChange({ wrong_reason: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-wrong-reason"
            placeholder="如：计算时忘记进位"
          />
        </div>
        <div>
          <label style={labelStyle}>详细解析</label>
          <Input.TextArea
            style={{ marginTop: 4, minHeight: 60 }}
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
          <label style={labelStyle}>要点（用；分隔）</label>
          <Input
            style={inputStyle}
            value={value.key_points}
            onChange={(e) => onChange({ key_points: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-key-points"
            placeholder="如：假设法；方程法"
          />
        </div>
        <div>
          <label style={labelStyle}>标签（用；分隔）</label>
          <Input
            style={inputStyle}
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
          <label style={labelStyle}>科目</label>
          <Select
            style={inputStyle}
            value={value.subject}
            onChange={(v) => onChange({ subject: v })}
            disabled={readOnly}
            data-testid="mqf-subject"
            options={Object.entries(SUBJECTS).map(([k]) => ({ value: k, label: SUBJECT_DISPLAY[k] }))}
          />
        </div>
        <div>
          <label style={labelStyle}>年级</label>
          <Select
            style={inputStyle}
            value={value.grade}
            onChange={(v) => onChange({ grade: v })}
            disabled={readOnly}
            data-testid="mqf-grade"
            options={GRADES.map((g) => ({ value: g, label: GRADE_DISPLAY[g] }))}
          />
        </div>
        <div>
          <label style={labelStyle}>题型</label>
          <Select
            style={inputStyle}
            value={value.category}
            onChange={(v) => onChange({ category: v })}
            disabled={readOnly}
            data-testid="mqf-category"
            options={CATEGORIES.map((c) => ({ value: c, label: CATEGORY_DISPLAY[c] }))}
          />
        </div>
        <div>
          <label style={labelStyle}>难度</label>
          <Select
            style={inputStyle}
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
            <label style={labelStyle}>教材</label>
            <Select
              style={inputStyle}
              value={value.textbook_id}
              onChange={(v) => onChange({ textbook_id: v, chapter_id: '' })}
              disabled={readOnly}
              data-testid="mqf-textbook"
              options={[
                { value: '', label: '未指定' },
                ...textbooks.map((tb) => ({
                  value: tb.id,
                  label: `${tb.name}${tb.grade ? ` (${GRADE_DISPLAY[tb.grade] || tb.grade})` : ''}`,
                })),
              ]}
            />
          </div>
          <div>
            <label style={labelStyle}>章节</label>
            <Select
              style={inputStyle}
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
            <label style={labelStyle}>知识点</label>
            <Select
              style={inputStyle}
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

export default MotherQuestionFields;
