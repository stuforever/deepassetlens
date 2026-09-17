"use client";

import { useEffect, useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Loader2, Upload, ZoomIn, Trash2, Sparkles, XCircle, CheckCircle2 } from "lucide-react";
import { notify } from "../../lib/notifications";
import { apiUrl } from "../../lib/api";

// ---- Shared types & constants ----

export interface KnowledgePoint { id: string; name: string; parent_id: string | null; }
export interface Textbook { id: string; name: string; grade: string | null; subject: string | null; }
export interface Chapter { id: string; name: string; textbook_id: string; parent_id: string | null; }

// 数据常量：值即后端契约（提交值），必须保持中文原文；显示时经 *_DISPLAY 映射到 i18n key 翻译
export const GRADES = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"];
export const CATEGORIES = ["应用题", "计算", "几何", "统计", "综合"];
export const SUBJECTS: Record<string, string> = {
  math: "数学", chinese: "语文", english: "英语",
  physics: "物理", chemistry: "化学", biology: "生物",
  history: "历史", geography: "地理", politics: "政治", other: "其他",
};
export const SUBJECT_COLORS: Record<string, string> = {
  math: "#3b82f6", chinese: "#ef4444", english: "#8b5cf6",
  physics: "#f59e0b", chemistry: "#10b981", biology: "#84cc16",
  history: "#a855f7", geography: "#06b6d4", politics: "#ec4899",
  other: "#6b7280",
};

/** 值 -> i18n key 映射（显示翻译用）。key 用点号字面量避免与语言名（Chinese/English）冲突。 */
export const SUBJECT_DISPLAY: Record<string, string> = {
  math: "subject.math", chinese: "subject.chinese", english: "subject.english",
  physics: "subject.physics", chemistry: "subject.chemistry", biology: "subject.biology",
  history: "subject.history", geography: "subject.geography", politics: "subject.politics", other: "subject.other",
};
export const GRADE_DISPLAY: Record<string, string> = {
  "一年级": "grade.1", "二年级": "grade.2", "三年级": "grade.3", "四年级": "grade.4", "五年级": "grade.5", "六年级": "grade.6",
};
export const CATEGORY_DISPLAY: Record<string, string> = {
  "应用题": "category.word_problems", "计算": "category.arithmetic", "几何": "category.geometry",
  "统计": "category.statistics", "综合": "category.comprehensive",
};

/** 表单数据结构（受控组件的 value 类型） */
export interface MotherQuestionData {
  title: string;
  question_text: string;
  subject: string;
  grade: string;
  category: string;
  difficulty: number;
  knowledge_point_id: string;
  textbook_id: string;
  chapter_id: string;
  standard_answer: string;
  wrong_answer: string;
  detailed_analysis: string;
  note: string;
  key_points: string;       // 分号分隔
  tags: string;             // 分号分隔
  photo_url: string | null;
  wrong_answer_image_url: string | null;
  wrong_reason: string;
  is_wrong: boolean;        // 错题/正确题 toggle
}

/** 从 MotherQuestion API 对象构建表单数据 */
export function toFormData(m: Record<string, any>): MotherQuestionData {
  return {
    title: m.title ?? "",
    question_text: m.question_text ?? "",
    subject: m.subject ?? "math",
    grade: m.grade ?? "四年级",
    category: m.category ?? "应用题",
    difficulty: m.difficulty ?? 3,
    knowledge_point_id: m.knowledge_point_id ?? "",
    textbook_id: m.textbook_id ?? "",
    chapter_id: m.chapter_id ?? "",
    standard_answer: m.standard_answer ?? "",
    wrong_answer: m.wrong_answer ?? "",
    detailed_analysis: m.detailed_analysis ?? "",
    note: m.note ?? "",
    key_points: Array.isArray(m.key_points) ? m.key_points.join("；") : (m.key_points ?? ""),
    tags: Array.isArray(m.tags) ? m.tags.join("；") : (m.tags ?? ""),
    photo_url: m.photo_url ?? null,
    wrong_answer_image_url: m.wrong_answer_image_url ?? null,
    wrong_reason: m.wrong_reason ?? "",
    is_wrong: m.is_wrong !== false,
  };
}

/** 表单数据 -> API payload（POST/PATCH 用） */
export function buildPayload(d: MotherQuestionData, extra?: Record<string, any>) {
  return {
    title: d.title,
    question_text: d.question_text,
    subject: d.subject,
    grade: d.grade,
    category: d.category,
    difficulty: Number(d.difficulty),
    knowledge_point_id: d.knowledge_point_id || null,
    textbook_id: d.textbook_id || null,
    chapter_id: d.chapter_id || null,
    standard_answer: d.standard_answer || null,
    wrong_answer: d.wrong_answer || null,
    detailed_analysis: d.detailed_analysis || null,
    note: d.note || null,
    key_points: d.key_points ? d.key_points.split("；").filter(Boolean) : [],
    photo_url: d.photo_url,
    wrong_answer_image_url: d.wrong_answer_image_url,
    tags: d.tags ? d.tags.split("；").filter(Boolean) : [],
    wrong_reason: d.wrong_reason || null,
    ...extra,
  };
}

// ---- ImageUpload sub-component (shared) ----

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
  const { t } = useTranslation();
  const [uploading, setUploading] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const areaProps = areaTestId ? { "data-testid": areaTestId } : {};

  const onFile = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const endpoint = ocr ? "/api/v1/mother-questions/ocr-upload" : "/api/v1/mother-questions/upload_image";
      const res = await fetch(apiUrl(endpoint), { method: "POST", body: fd });
      if (!res.ok) throw new Error();
      const data = await res.json();
      onChange(data.photo_url || data.url);
      if (ocr && data.text) onOcrText?.(data.text);
      notify.success(ocr ? t("Recognized {{count}} lines", { count: data.line_count || 0 }) : t("Image uploaded"));
    } catch {
      notify.error(ocr ? t("OCR recognition failed") : t("Upload failed"));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div {...areaProps}>
      <label className="text-xs text-muted-foreground">{label}</label>
      <div className="mt-1 flex items-start gap-3">
        {url ? (
          <div className="relative group">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={url} alt={label} className="w-32 h-32 object-cover rounded border cursor-pointer" onClick={() => setZoomOpen(true)} data-testid={areaTestId ? `${areaTestId}-preview` : undefined} />
            {!readOnly && (
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition rounded flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                <button type="button" onClick={() => setZoomOpen(true)} className="p-1.5 bg-white/80 rounded hover:bg-white" title={t("View large image")}>
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button type="button" onClick={() => onChange(null)} className="p-1.5 bg-white/80 rounded hover:bg-white" title={t("Delete image")}>
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        ) : readOnly ? (
          <p className="text-xs text-muted-foreground italic w-32 h-32 flex items-center justify-center border rounded">{t("No image")}</p>
        ) : (
          <button type="button" onClick={() => inputRef.current?.click()} disabled={uploading} data-testid={areaTestId ? `${areaTestId}-btn` : undefined}
            className="w-32 h-32 border-2 border-dashed rounded flex flex-col items-center justify-center text-xs text-muted-foreground hover:bg-accent">
            {uploading ? <Loader2 className="w-6 h-6 animate-spin" /> : (
              <><Upload className="w-6 h-6 mb-1" /><span>{t("Click to upload")}</span></>
            )}
          </button>
        )}
        {!readOnly && (
          <input ref={inputRef} type="file" accept="image/*" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
        )}
      </div>
      {zoomOpen && url && (
        <div className="fixed inset-0 z-[60] bg-black/80 flex items-center justify-center" onClick={() => setZoomOpen(false)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={url} alt={label} className="max-w-[90vw] max-h-[90vh] object-contain" onClick={(e) => e.stopPropagation()} />
          <button onClick={() => setZoomOpen(false)} className="absolute top-4 right-4 p-2 bg-white/20 rounded text-white hover:bg-white/30">
            <Trash2 className="w-6 h-6" />
          </button>
        </div>
      )}
    </div>
  );
}

// ---- Main MotherQuestionFields component ----

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
  const { t } = useTranslation();
  const [kps, setKps] = useState<KnowledgePoint[]>([]);
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [aiFilling, setAiFilling] = useState(false);

  useEffect(() => {
    fetch(apiUrl("/api/v1/mother-questions/dict"))
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
      notify.error(t("Please enter the question text or upload a question image first"));
      return;
    }
    setAiFilling(true);
    try {
      const res = await fetch(apiUrl("/api/v1/mother-questions/recognize_text"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
          ...(Array.isArray(f.key_points) ? { key_points: f.key_points.join("；") } : {}),
        });
        notify.success(data.fallback ? t("AI fill degraded (some fields filled)") : t("AI auto-fill complete"));
      } else {
        notify.warning(data.msg || t("AI returned no valid fields"));
      }
    } catch {
      notify.error(t("AI auto-fill failed"));
    } finally {
      setAiFilling(false);
    }
  };

  return (
    <div className="space-y-3" data-testid="mqf-root">
      {/* 错题/正确题 toggle */}
      {showWrongToggle && (
        <div className="flex gap-2" data-testid="mqf-wrong-toggle">
          <button
            type="button"
            onClick={() => onChange({ is_wrong: true })}
            disabled={readOnly}
            data-testid="mqf-toggle-wrong"
            data-active={value.is_wrong ? "true" : "false"}
            className={`flex-1 px-3 py-2 rounded text-sm font-medium border transition-colors ${value.is_wrong ? "bg-rose-500 text-white border-transparent" : "border-border hover:bg-accent"} disabled:opacity-60`}
          >
            <XCircle className="w-4 h-4 inline mr-1" />{t("Wrong Question")}
          </button>
          <button
            type="button"
            onClick={() => onChange({ is_wrong: false })}
            disabled={readOnly}
            data-testid="mqf-toggle-correct"
            data-active={!value.is_wrong ? "true" : "false"}
            className={`flex-1 px-3 py-2 rounded text-sm font-medium border transition-colors ${!value.is_wrong ? "bg-emerald-500 text-white border-transparent" : "border-border hover:bg-accent"} disabled:opacity-60`}
          >
            <CheckCircle2 className="w-4 h-4 inline mr-1" />{t("Correct Question")}
          </button>
        </div>
      )}

      {/* 标题 + AI填充 */}
      <div>
        <div className="flex items-center justify-between">
          <label className="text-xs text-muted-foreground">{t("Title *")}</label>
          {!readOnly && (
            <button
              type="button"
              onClick={onAiFill}
              disabled={aiFilling}
              data-testid="mqf-ai-fill"
              className="text-xs px-2 py-1 rounded bg-purple-600 text-white flex items-center gap-1 hover:bg-purple-700 disabled:opacity-50"
              title={t("AI auto-fill: extract fields from the question text or image")}
            >
              {aiFilling ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
              {t("AI auto-fill")}
            </button>
          )}
        </div>
        <input
          className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm"
          value={value.title}
          onChange={(e) => onChange({ title: e.target.value })}
          readOnly={readOnly}
          data-testid="mqf-title"
          placeholder={t("e.g. chickens and rabbits in a cage")}
        />
      </div>

      {/* 题干 */}
      <div>
        <label className="text-xs text-muted-foreground">{t("Question Text *")}</label>
        <textarea
          className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm min-h-[100px]"
          value={value.question_text}
          onChange={(e) => onChange({ question_text: e.target.value })}
          readOnly={readOnly}
          data-testid="mqf-question-text"
        />
      </div>

      {/* 图片上传区 */}
      <div className={`grid grid-cols-2 gap-4 ${photoMode ? "ring-2 ring-purple-400 rounded-lg p-3 bg-purple-50/50 dark:bg-purple-950/20" : ""}`}>
        <ImageUpload
          label={photoMode ? t("Question image (auto-recognized on upload)") : t("Question image (original screenshot)")}
          url={value.photo_url}
          onChange={(url) => onChange({ photo_url: url })}
          ocr={photoMode}
          readOnly={readOnly}
          areaTestId="mqf-photo"
          onOcrText={photoMode ? (text) => {
            onChange({ question_text: text });
            if (!value.title) {
              const firstLine = text.split("\n")[0] || "";
              onChange({ title: firstLine.slice(0, 20) });
            }
          } : undefined}
        />
        <ImageUpload
          label={t("Wrong answer screenshot")}
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
          className="w-full px-3 py-2 rounded bg-purple-600 text-white text-sm flex items-center justify-center gap-1 hover:bg-purple-700"
        >
          <Sparkles className="w-4 h-4" /> {t("AI auto-fill (extract answers, analysis from image)")}
        </button>
      )}

      {/* 你的答案 + 标准答案 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-muted-foreground" data-testid="mqf-wrong-answer-label">{value.is_wrong ? t("Your answer (wrong answer)") : t("Your answer")}</label>
          <textarea
            className={`w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm min-h-[60px] ${value.is_wrong ? "border-rose-300 dark:border-rose-700" : ""}`}
            value={value.wrong_answer}
            onChange={(e) => onChange({ wrong_answer: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-wrong-answer"
            placeholder={t("e.g. 12 (student's wrong answer)")}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">{t("Standard Answer")}</label>
          <textarea
            className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm min-h-[60px]"
            value={value.standard_answer}
            onChange={(e) => onChange({ standard_answer: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-standard-answer"
          />
        </div>
      </div>

      {/* 错误原因 + 详细解析 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-muted-foreground">{t("Reason for Error")}</label>
          <input
            className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm"
            value={value.wrong_reason}
            onChange={(e) => onChange({ wrong_reason: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-wrong-reason"
            placeholder={t("e.g. forgot to carry when calculating")}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">{t("Detailed Analysis")}</label>
          <textarea
            className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm min-h-[60px]"
            value={value.detailed_analysis}
            onChange={(e) => onChange({ detailed_analysis: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-detailed-analysis"
            placeholder={t("Knowledge points, solution approach, common mistakes")}
          />
        </div>
      </div>

      {/* 要点 + 标签 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-muted-foreground">{t("Key points (separated by ;)")}</label>
          <input
            className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm"
            value={value.key_points}
            onChange={(e) => onChange({ key_points: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-key-points"
            placeholder={t("e.g. assumption method; equation method")}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">{t("Tags (separated by ;)")}</label>
          <input
            className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm"
            value={value.tags}
            onChange={(e) => onChange({ tags: e.target.value })}
            readOnly={readOnly}
            data-testid="mqf-tags"
            placeholder={t("e.g. midterm exam; tricky question")}
          />
        </div>
      </div>

      {/* 科目 / 年级 / 题型 / 难度 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div>
          <label className="text-xs text-muted-foreground">{t("Subject")}</label>
          <select className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm" value={value.subject} onChange={(e) => onChange({ subject: e.target.value })} disabled={readOnly} data-testid="mqf-subject">
            {Object.entries(SUBJECTS).map(([k, v]) => <option key={k} value={k}>{t(SUBJECT_DISPLAY[k])}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground">{t("Grade")}</label>
          <select className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm" value={value.grade} onChange={(e) => onChange({ grade: e.target.value })} disabled={readOnly} data-testid="mqf-grade">
            {GRADES.map((g) => <option key={g} value={g}>{t(GRADE_DISPLAY[g])}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground">{t("Question Type")}</label>
          <select className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm" value={value.category} onChange={(e) => onChange({ category: e.target.value })} disabled={readOnly} data-testid="mqf-category">
            {CATEGORIES.map((c) => <option key={c} value={c}>{t(CATEGORY_DISPLAY[c])}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground">{t("Difficulty")}</label>
          <select className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm" value={value.difficulty} onChange={(e) => onChange({ difficulty: Number(e.target.value) })} disabled={readOnly} data-testid="mqf-difficulty">
            {[1, 2, 3, 4, 5].map((d) => <option key={d} value={d}>{"★".repeat(d)}</option>)}
          </select>
        </div>
      </div>

      {/* 教材 / 章节 / 知识点 */}
      {showClassification && (
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-xs text-muted-foreground">{t("Textbook")}</label>
            <select
              className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm"
              value={value.textbook_id}
              onChange={(e) => onChange({ textbook_id: e.target.value, chapter_id: "" })}
              disabled={readOnly}
              data-testid="mqf-textbook"
            >
              <option value="">{t("Not specified")}</option>
              {textbooks.map((tb) => <option key={tb.id} value={tb.id}>{tb.name}{tb.grade ? ` (${t(GRADE_DISPLAY[tb.grade] || tb.grade)})` : ""}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">{t("Chapter")}</label>
            <select className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm" value={value.chapter_id} onChange={(e) => onChange({ chapter_id: e.target.value })} disabled={!value.textbook_id || readOnly} data-testid="mqf-chapter">
              <option value="">{t("Not specified")}</option>
              {filteredChapters.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">{t("Knowledge Point")}</label>
            <select className="w-full mt-1 px-2 py-1.5 rounded border bg-transparent text-sm" value={value.knowledge_point_id} onChange={(e) => onChange({ knowledge_point_id: e.target.value })} disabled={readOnly} data-testid="mqf-kp">
              <option value="">{t("Not attached")}</option>
              {kps.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
