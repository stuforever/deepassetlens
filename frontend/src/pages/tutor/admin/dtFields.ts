/**
 * ⑤R F1：DT 教学域共享字段常量/类型/payload 构建器（复刻自原仓
 * web/components/mother-questions/MotherQuestionFields.tsx 契约面——
 * 值即后端契约（提交值保持中文原文/英文枚举），显示映射原样；i18n key 在此直出中文）。
 */

export interface KnowledgePoint { id: string; name: string; parent_id: string | null; }
export interface Textbook { id: string; name: string; grade: string | null; subject: string | null; }
export interface Chapter { id: string; name: string; textbook_id: string; parent_id: string | null; }

export const GRADES = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级'];
export const CATEGORIES = ['应用题', '计算', '几何', '统计', '综合'];
export const SUBJECTS: Record<string, string> = {
  math: '数学', chinese: '语文', english: '英语',
  physics: '物理', chemistry: '化学', biology: '生物',
  history: '历史', geography: '地理', politics: '政治', other: '其他',
};
export const SUBJECT_COLORS: Record<string, string> = {
  math: '#3b82f6', chinese: '#ef4444', english: '#8b5cf6',
  physics: '#f59e0b', chemistry: '#10b981', biology: '#84cc16',
  history: '#a855f7', geography: '#06b6d4', politics: '#ec4899',
  other: '#6b7280',
};

/** 显示映射（原 i18n key → 中文直出，原仓 zh locale 语义） */
export const SUBJECT_DISPLAY: Record<string, string> = {
  math: '数学', chinese: '语文', english: '英语',
  physics: '物理', chemistry: '化学', biology: '生物',
  history: '历史', geography: '地理', politics: '政治', other: '其他',
};
export const GRADE_DISPLAY: Record<string, string> = {
  一年级: '一年级', 二年级: '二年级', 三年级: '三年级',
  四年级: '四年级', 五年级: '五年级', 六年级: '六年级',
};
export const CATEGORY_DISPLAY: Record<string, string> = {
  应用题: '应用题', 计算: '计算', 几何: '几何', 统计: '统计', 综合: '综合',
};
/** 掌握度显示（原 i18n mastery.* key 直出中文） */
export const MASTERY_DISPLAY: Record<string, string> = {
  not_mastered: '未掌握', reviewing: '复习中', mastered: '已掌握',
};

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
  key_points: string;
  tags: string;
  photo_url: string | null;
  wrong_answer_image_url: string | null;
  wrong_reason: string;
  is_wrong: boolean;
}

export function toFormData(m: Record<string, any>): MotherQuestionData {
  return {
    title: m.title ?? '',
    question_text: m.question_text ?? '',
    subject: m.subject ?? 'math',
    grade: m.grade ?? '四年级',
    category: m.category ?? '应用题',
    difficulty: m.difficulty ?? 3,
    knowledge_point_id: m.knowledge_point_id ?? '',
    textbook_id: m.textbook_id ?? '',
    chapter_id: m.chapter_id ?? '',
    standard_answer: m.standard_answer ?? '',
    wrong_answer: m.wrong_answer ?? '',
    detailed_analysis: m.detailed_analysis ?? '',
    note: m.note ?? '',
    key_points: Array.isArray(m.key_points) ? m.key_points.join('；') : (m.key_points ?? ''),
    tags: Array.isArray(m.tags) ? m.tags.join('；') : (m.tags ?? ''),
    photo_url: m.photo_url ?? null,
    wrong_answer_image_url: m.wrong_answer_image_url ?? null,
    wrong_reason: m.wrong_reason ?? '',
    is_wrong: m.is_wrong !== false,
  };
}

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
    key_points: d.key_points ? d.key_points.split('；').filter(Boolean) : [],
    photo_url: d.photo_url,
    wrong_answer_image_url: d.wrong_answer_image_url,
    tags: d.tags ? d.tags.split('；').filter(Boolean) : [],
    wrong_reason: d.wrong_reason || null,
    ...extra,
  };
}

/** 掌握度色（原仓 masteryColor 语义） */
export const MASTERY_COLOR: Record<string, string> = {
  mastered: '#10b981', reviewing: '#f59e0b', not_mastered: '#ef4444',
};
