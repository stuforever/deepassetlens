/**
 * H5 错题本页（design §二 错题闭环 / M2 + 第十一篇 N6 完整复刻桌面版）
 * ——原仓 app/h5/wrongbook/page.tsx 1:1 移植。
 *
 * 等价替换（与批8 F1 约定一致）：
 *  - next/navigation useSearchParams → react-router-dom useSearchParams；next/link → react-router Link；
 *  - 路由前缀映射：原 /h5/* → tupu /e/tutor/h5/*；
 *  - fetch(apiUrl('/api/v1/...')) → fetch('/api/v1/...') 逐字（路径/方法/headers/body/query 一字不改）；
 *  - lucide-react → @ant-design/icons 语义就近（Loader2→LoadingOutlined、Volume2→SoundOutlined、
 *    Sparkles→ThunderboltOutlined、RotateCcw→ReloadOutlined、SlidersHorizontal→ControlOutlined、
 *    Undo2→UndoOutlined、Square→BorderOutlined、FileDown→DownloadOutlined、其余同名 Outlined）；
 *  - window.alert/window.confirm 原样保留（中文文案逐字）；
 *  - Tailwind → antd+内联样式逐项对位（active: 伪类内联样式不可表达，随 h5shared 先例略去）；
 *  - GRADES/CATEGORIES（原 @/components/mother-questions/MotherQuestionFields 同源常量）→ admin/dtFields；
 *  - MarkdownRenderer（原 @/components/common/MarkdownRenderer）→ admin/MarkdownRenderer 已落地移植件；
 *  - postSessionSummary → h5shared/sessionRecap；withU → h5shared/h5Utils；h5Speak → h5shared/h5Tts。
 *
 * 保留：FSRS 复习流 / 变式 / 归因 / explain / ai_solve / 搜索 / 标签 / 删除 / ?mid= 直达 / 问 AI。
 * N6 补齐（全部复用桌面同源 API，零新增后端）：
 * a) 高级筛选（学科/年级/类别/教材→章节级联(/dict)/标签/排序）+ 上拉分页
 * b) 手动新建（CreateMotherRequest 全字段表单）
 * c) 编辑（PATCH /{mid}）
 * d) 回收站（/trash + restore + DELETE ?hard=true）
 * e) 多选导出 Word（POST /export → .docx 下载）
 * f) 分析仪表盘四卡（comprehensive-stats / error-patterns / trends，轻量 SVG）
 * g) 答题记录（GET /{mid}/attempts 折叠区）
 */
import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  LoadingOutlined,
  SoundOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  SearchOutlined,
  DeleteOutlined,
  MessageOutlined,
  ControlOutlined,
  PlusOutlined,
  EditOutlined,
  BarChartOutlined,
  UndoOutlined,
  CheckSquareOutlined,
  BorderOutlined,
  DownloadOutlined,
  HistoryOutlined,
  DownOutlined,
  CloseCircleOutlined,
  CheckCircleOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { GRADES, CATEGORIES } from "../admin/dtFields";
import { withU } from "./h5shared/h5Utils";
import MarkdownRenderer from "../admin/MarkdownRenderer";
import { postSessionSummary } from "./h5shared/sessionRecap";
import { H5Shell } from "./h5shared/H5Shell";
import { H5Sheet } from "./h5shared/H5Sheet";
import { H5PageHeader } from "./h5shared/H5PageHeader";
import { h5Speak } from "./h5shared/h5Tts";

interface DueItem {
  id: string;
  title: string;
  question_text: string;
  subject?: string;
  standard_answer?: string;
  detailed_analysis?: string;
  difficulty?: number;
  tags?: string[];
  [k: string]: unknown;
}

const SUBJECT_LABELS: Record<string, string> = {
  math: "数学",
  chinese: "语文",
  english: "英语",
  physics: "物理",
  chemistry: "化学",
  biology: "生物",
  history: "历史",
  geography: "地理",
  politics: "政治",
  other: "其他",
};

const WRONG_REASON_LABELS: Record<string, string> = {
  concept_gap: "概念不清",
  careless: "粗心失误",
  method_wrong: "方法错误",
  calculation: "计算错误",
  time_pressure: "时间不够",
  misread: "审题错误",
};

function labelOf(v?: string): string {
  if (!v) return "";
  return SUBJECT_LABELS[v] || WRONG_REASON_LABELS[v] || v;
}

interface DictData {
  textbooks: { id: string; name: string; grade?: string; subject?: string }[];
  chapters: { id: string; name: string; textbook_id: string }[];
  knowledge_points: { id: string; name: string; subject?: string }[];
  tags: string[];
  subjects: string[];
}

const EMPTY_FORM = {
  title: "",
  question_text: "",
  subject: "math",
  grade: "",
  category: "",
  standard_answer: "",
  wrong_answer: "",
  detailed_analysis: "",
  note: "",
  solution_steps: "",
  key_points: "",
  difficulty: 3,
  knowledge_point_id: "",
  textbook_id: "",
  chapter_id: "",
  tags: "",
  // WQ2/3（M24）：双图上传 + 错题/正确题 toggle + 错因
  photo_url: "",
  wrong_answer_image_url: "",
  wrong_reason: "",
  is_wrong: true,
};

type FormShape = typeof EMPTY_FORM;

// --------------------------------------------------------------------------- //
// Tailwind → 内联样式对位用的公共样式片段（逐项对应原 className）
// --------------------------------------------------------------------------- //
const SLATE = {
  50: "#f8fafc", 100: "#f1f5f9", 200: "#e2e8f0", 300: "#cbd5e1", 400: "#94a3b8",
  500: "#64748b", 600: "#475569", 700: "#334155", 800: "#1e293b",
};
const BTN_BASE: React.CSSProperties = { border: "none", cursor: "pointer", background: "none", padding: 0, fontFamily: "inherit" };
const clamp2: React.CSSProperties = {
  display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
};
const cardWhite: React.CSSProperties = { background: "#fff", borderRadius: 16, border: `1px solid ${SLATE[200]}` };
const centerLoading: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 0", color: SLATE[400],
};

function WrongBookContent() {
  // react-router useSearchParams 返回元组（next/navigation 返回 URLSearchParams 实例）——等价解构
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  // ?mid=：章节错题直达——初始定位到该题（自动切到「全部错题」视图）
  const midParam = searchParams.get("mid") || "";
  const [items, setItems] = useState<DueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [idx, setIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [explainText, setExplainText] = useState("");
  const [done, setDone] = useState(0);
  // 变式练习（design §5.2）
  const [variant, setVariant] = useState<{
    id: string;
    question_text?: string;
    answer?: string | null;
    difficulty?: number;
    variant_type?: string;
  } | null>(null);
  const [variantLoading, setVariantLoading] = useState(false);
  const [variantAnswer, setVariantAnswer] = useState("");
  const [variantRevealed, setVariantRevealed] = useState(false);
  const [variantSelfOk, setVariantSelfOk] = useState(false);
  // P2-B 错因 LLM 归因
  const [attrLoading, setAttrLoading] = useState(false);
  const [wrongReason, setWrongReason] = useState("");
  const [wrongAdvice, setWrongAdvice] = useState("");
  const [batchAttr, setBatchAttr] = useState(false);

  const qs = u ? `?u=${encodeURIComponent(u)}` : "";

  // F6（M14-C）：错题本管理面——搜索 / 标签筛选 / 删除回收站 / ai_solve 分步解题
  const [view, setView] = useState<"due" | "list" | "trash" | "analysis">(
    midParam ? "list" : "due",
  );
  const [listItems, setListItems] = useState<any[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [activeTag, setActiveTag] = useState("");
  const [listTags, setListTags] = useState<string[]>([]);
  const [solvingId, setSolvingId] = useState<string | null>(null);
  const [solveTexts, setSolveTexts] = useState<Record<string, string>>({});
  const [highlightId, setHighlightId] = useState(midParam || "");

  // ---- N6-a：高级筛选 + 分页 ----
  const [filterOpen, setFilterOpen] = useState(false);
  const [dict, setDict] = useState<DictData | null>(null);
  const [fSubject, setFSubject] = useState("");
  const [fGrade, setFGrade] = useState("");
  const [fCategory, setFCategory] = useState("");
  const [fTextbook, setFTextbook] = useState("");
  const [fChapter, setFChapter] = useState("");
  const [fSortBy, setFSortBy] = useState("create_time");
  const [fSortOrder, setFSortOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // ---- N6-d：回收站 ----
  const [trashItems, setTrashItems] = useState<any[]>([]);
  const [trashLoading, setTrashLoading] = useState(false);

  // ---- N6-b/c：新建 / 编辑表单 ----
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState("");
  const [form, setForm] = useState<FormShape>({ ...EMPTY_FORM });
  const [formSaving, setFormSaving] = useState(false);

  // ---- N6-e：多选导出 ----
  const [multiMode, setMultiMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);

  // ---- N6-f：分析 ----
  const [analysis, setAnalysis] = useState<{
    stats: any;
    patterns: { reason: string; count: number }[];
    trends: { date: string; count: number }[];
  } | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  // ---- N6-g：答题记录 ----
  const [attemptsOpen, setAttemptsOpen] = useState("");
  const [attempts, setAttempts] = useState<Record<string, any>>({});

  const chapterOptions = useMemo(
    () => (dict?.chapters || []).filter((c) => !fTextbook || c.textbook_id === fTextbook),
    [dict, fTextbook],
  );

  const loadList = useCallback(
    async (nextPage = 1, append = false) => {
      setListLoading(true);
      try {
        const params = new URLSearchParams({
          page: String(nextPage),
          page_size: "20",
          sort_by: fSortBy,
          sort_order: fSortOrder,
        });
        if (keyword.trim()) params.set("keyword", keyword.trim());
        if (activeTag) params.set("tag", activeTag);
        if (fSubject) params.set("subject", fSubject);
        if (fGrade) params.set("grade", fGrade);
        if (fCategory) params.set("category", fCategory);
        if (fTextbook) params.set("textbook_id", fTextbook);
        if (fChapter) params.set("chapter_id", fChapter);
        if (u) params.set("u", u);
        const res = await fetch(`/api/v1/mother-questions?${params}`);
        if (!res.ok) {
          if (!append) setListItems([]);
          return;
        }
        const data = await res.json();
        const newItems = Array.isArray(data.items) ? data.items : [];
        setTotal(typeof data.total === "number" ? data.total : newItems.length);
        setListItems((prev) => (append ? [...prev, ...newItems] : newItems));
        setPage(nextPage);
        // 聚合 top 标签（chip 筛选）
        const tagCount = new Map<string, number>();
        for (const it of append ? [...listItems, ...newItems] : newItems) {
          for (const t of it.tags || []) tagCount.set(t, (tagCount.get(t) || 0) + 1);
        }
        setListTags(
          // target es5 下 Map 迭代器展开需 downlevelIteration——等价 Array.from
          Array.from(tagCount.entries()).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([t]) => t),
        );
      } catch {
        if (!append) setListItems([]);
      } finally {
        setListLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [keyword, activeTag, u, fSubject, fGrade, fCategory, fTextbook, fChapter, fSortBy, fSortOrder],
  );

  useEffect(() => {
    if (view === "list") void loadList(1, false);
  }, [view, loadList]);

  const refreshCurrent = useCallback(async () => {
    if (view === "due") await load();
    else if (view === "list") await loadList(1, false);
    else if (view === "trash") await loadTrash();
    else if (view === "analysis") await loadAnalysis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, loadList]);

  // ?mid= 直达：列表渲染后滚动定位 + 高亮该题
  useEffect(() => {
    if (view !== "list" || !highlightId) return;
    const t = setTimeout(() => {
      const el = document.getElementById(`mq-${highlightId}`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 350);
    return () => clearTimeout(t);
  }, [view, highlightId, listItems]);

  // ---- N6-d：回收站 ----
  const loadTrash = useCallback(async () => {
    setTrashLoading(true);
    try {
      const res = await fetch(`/api/v1/mother-questions/trash?u=${encodeURIComponent(u)}`);
      const data = res.ok ? await res.json() : { items: [] };
      setTrashItems(Array.isArray(data.items) ? data.items : []);
    } catch {
      setTrashItems([]);
    } finally {
      setTrashLoading(false);
    }
  }, [u]);

  const restoreItem = useCallback(
    async (id: string) => {
      try {
        await fetch(`/api/v1/mother-questions/${id}/restore${qs}`, { method: "POST" });
        setTrashItems((prev) => prev.filter((t) => t.id !== id));
      } catch {
        /* ignore */
      }
    },
    [qs],
  );

  const hardDelete = useCallback(
    async (id: string) => {
      if (!window.confirm("彻底删除？不可恢复！")) return;
      try {
        await fetch(`/api/v1/mother-questions/${id}?hard=true${qs ? `&${qs.slice(1)}` : ""}`, {
          method: "DELETE",
        });
        setTrashItems((prev) => prev.filter((t) => t.id !== id));
      } catch {
        /* ignore */
      }
    },
    [qs],
  );

  // ---- N6-f：分析 ----
  const loadAnalysis = useCallback(async () => {
    setAnalysisLoading(true);
    try {
      const aqs = u ? `?u=${encodeURIComponent(u)}` : "";
      const [statsRes, patternsRes, trendsRes] = await Promise.all([
        fetch(`/api/v1/mother-questions/analysis/comprehensive-stats${aqs}`),
        fetch(`/api/v1/mother-questions/analysis/error-patterns${aqs}`),
        fetch(`/api/v1/mother-questions/analysis/trends?days=30${u ? `&u=${encodeURIComponent(u)}` : ""}`),
      ]);
      setAnalysis({
        stats: statsRes.ok ? await statsRes.json() : null,
        patterns: patternsRes.ok ? (await patternsRes.json()).patterns || [] : [],
        trends: trendsRes.ok ? (await trendsRes.json()).trends || [] : [],
      });
    } catch {
      setAnalysis(null);
    } finally {
      setAnalysisLoading(false);
    }
  }, [u]);

  useEffect(() => {
    if (view === "trash" && trashItems.length === 0) void loadTrash();
    if (view === "analysis" && !analysis) void loadAnalysis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  // ---- N6-b/c：字典 + 表单 ----
  // 字典按需加载：新建表单与筛选弹层共用；失败静默，下次打开自动重试
  const ensureDict = useCallback(async () => {
    if (dict) return;
    try {
      const res = await fetch("/api/v1/mother-questions/dict");
      if (res.ok) setDict(await res.json());
    } catch {
      /* dict 失败不阻塞表单/筛选 */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dict]);
  const openForm = async (editing?: any) => {
    if (!dict) await ensureDict();
    if (editing) {
      setEditingId(editing.id);
      setForm({
        title: editing.title || "",
        question_text: editing.question_text || "",
        subject: editing.subject || "math",
        grade: editing.grade || "",
        category: editing.category || "",
        standard_answer: editing.standard_answer || "",
        wrong_answer: editing.wrong_answer || "",
        detailed_analysis: editing.detailed_analysis || "",
        note: editing.note || "",
        solution_steps: (editing.solution_steps || [])
          .map((s: any) => (typeof s === "string" ? s : s.step || s.description || ""))
          .filter(Boolean)
          .join("\n"),
        key_points: (editing.key_points || []).join("，"),
        difficulty: editing.difficulty || 3,
        knowledge_point_id: editing.knowledge_point_id || "",
        textbook_id: editing.textbook_id || "",
        chapter_id: editing.chapter_id || "",
        tags: (editing.tags || [])
          .filter((t: string) => !t.startsWith("src:") && !t.startsWith("u:") && !t.startsWith("claimed:"))
          .join("，"),
        // WQ2/3（M24）：双图/is_wrong/错因随编辑回填
        photo_url: editing.photo_url || "",
        wrong_answer_image_url: editing.wrong_answer_image_url || "",
        wrong_reason: editing.wrong_reason || "",
        is_wrong: editing.is_wrong !== false,
      });
    } else {
      setEditingId("");
      setForm({ ...EMPTY_FORM, subject: fSubject || "math", textbook_id: fTextbook || "", chapter_id: fChapter || "" });
    }
    setFormOpen(true);
  };

  const saveForm = useCallback(async () => {
    if (!form.title.trim() || !form.question_text.trim()) {
      window.alert("标题和题干必填");
      return;
    }
    setFormSaving(true);
    try {
      const body = {
        title: form.title.trim(),
        question_text: form.question_text.trim(),
        subject: form.subject || "math",
        grade: form.grade || null,
        category: form.category || null,
        standard_answer: form.standard_answer || null,
        wrong_answer: form.wrong_answer || null,
        detailed_analysis: form.detailed_analysis || null,
        note: form.note || null,
        solution_steps: form.solution_steps
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((s, i) => ({ order: i + 1, step: s })),
        key_points: form.key_points
          .split(/[,，、]/)
          .map((s) => s.trim())
          .filter(Boolean),
        difficulty: Number(form.difficulty) || 3,
        knowledge_point_id: form.knowledge_point_id || null,
        textbook_id: form.textbook_id || null,
        chapter_id: form.chapter_id || null,
        tags: [
          ...form.tags
            .split(/[,，、]/)
            .map((s) => s.trim())
            .filter(Boolean),
          "h5",
          "src:manual",
          ...(u ? [`u:${u}`] : []),
        ],
        // WQ2/3（M24）：双图/is_wrong/错因入 payload
        photo_url: form.photo_url || null,
        wrong_answer_image_url: form.wrong_answer_image_url || null,
        is_wrong: form.is_wrong,
        wrong_reason: form.wrong_reason || null,
      };
      const res = editingId
        ? await fetch(`/api/v1/mother-questions/${editingId}${qs}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          })
        : await fetch(`/api/v1/mother-questions${qs}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
      if (res.status === 409) {
        const data = await res.json().catch(() => ({}));
        window.alert(data.detail || "与现有题目重复");
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        window.alert("保存失败：" + (data.detail || res.status));
        return;
      }
      setFormOpen(false);
      if (view === "list") void loadList(1, false);
    } catch {
      window.alert("网络错误，请重试");
    } finally {
      setFormSaving(false);
    }
  }, [form, editingId, qs, u, view, loadList]);

  // ---- WQ1/2（M24）：AI 填充 + 表单双图上传 ----
  const [aiFilling, setAiFilling] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadingWrongPhoto, setUploadingWrongPhoto] = useState(false);

  const aiFill = useCallback(async () => {
    if (!form.question_text.trim() && !form.photo_url) {
      window.alert("请先填写题干或上传题目图，再使用 AI 填充");
      return;
    }
    setAiFilling(true);
    try {
      const res = await fetch(`/api/v1/mother-questions/recognize_text${qs}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: form.question_text,
          image_url: form.photo_url,
          subject: form.subject,
          wrong_answer: form.wrong_answer,
          title: form.title,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        window.alert(data.detail || "AI 填充失败");
        return;
      }
      const data = await res.json();
      if (data.fields) {
        const f = data.fields;
        setForm((prev) => ({
          ...prev,
          ...(f.title ? { title: f.title } : {}),
          ...(f.question_text ? { question_text: f.question_text } : {}),
          ...(f.standard_answer ? { standard_answer: f.standard_answer } : {}),
          ...(f.wrong_answer ? { wrong_answer: f.wrong_answer } : {}),
          ...(f.detailed_analysis ? { detailed_analysis: f.detailed_analysis } : {}),
          ...(f.wrong_reason ? { wrong_reason: f.wrong_reason } : {}),
          ...(f.category ? { category: f.category } : {}),
          ...(f.difficulty ? { difficulty: Number(f.difficulty) } : {}),
          ...(Array.isArray(f.key_points) ? { key_points: f.key_points.join("；") } : {}),
        }));
      } else {
        window.alert(data.msg || "AI 未能提取有效字段，请手动填写");
      }
    } catch {
      window.alert("AI 填充失败（网络错误）");
    } finally {
      setAiFilling(false);
    }
  }, [form, qs]);

  const uploadFormImage = useCallback(
    async (file: File, which: "photo_url" | "wrong_answer_image_url") => {
      const fd = new FormData();
      fd.append("file", file);
      const isPhoto = which === "photo_url";
      if (isPhoto) setUploadingPhoto(true);
      else setUploadingWrongPhoto(true);
      try {
        // 题目图走 ocr-upload（识别文字回填题干，镜像桌面 photoMode）；错答图走 upload_image
        const endpoint = isPhoto
          ? `/api/v1/mother-questions/ocr-upload${qs}`
          : `/api/v1/mother-questions/upload_image${qs}`;
        const res = await fetch(endpoint, { method: "POST", body: fd });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          window.alert(data.detail || "上传失败");
          return;
        }
        const data = await res.json();
        const url = data.photo_url || data.url;
        setForm((prev) => ({ ...prev, [which]: url }));
        if (isPhoto && data.text && data.text.trim()) {
          const text = data.text.trim();
          setForm((prev) => ({
            ...prev,
            question_text: prev.question_text ? prev.question_text : text,
            title: prev.title ? prev.title : text.split("\n")[0].slice(0, 20),
          }));
        }
      } catch {
        window.alert("上传失败（网络错误）");
      } finally {
        if (isPhoto) setUploadingPhoto(false);
        else setUploadingWrongPhoto(false);
      }
    },
    [qs],
  );

  // ---- N6-e：导出 Word（tab_export）----
  const exportSelected = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setExporting(true);
    try {
      const res = await fetch(`/api/v1/mother-questions/export${qs}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: Array.from(selectedIds), with_answer: true, with_image: true, title: "错题本导出" }),
      });
      if (!res.ok) {
        window.alert("导出失败：" + res.status);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `错题本_${new Date().toISOString().slice(0, 10)}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 3000);
      setMultiMode(false);
      setSelectedIds(new Set());
    } catch {
      window.alert("导出失败，请重试");
    } finally {
      setExporting(false);
    }
  }, [selectedIds]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // ---- N6-g：答题记录 ----
  const toggleAttempts = async (id: string) => {
    if (attemptsOpen === id) {
      setAttemptsOpen("");
      return;
    }
    setAttemptsOpen(id);
    if (!attempts[id]) {
      try {
        const res = await fetch(`/api/v1/mother-questions/${id}/attempts?limit=10${qs}`);
        const data = res.ok ? await res.json() : null;
        if (data) setAttempts((prev) => ({ ...prev, [id]: data }));
      } catch {
        /* ignore */
      }
    }
  };

  // ai_solve：SSE 流式分步解题（text/plain，逐块渲染）
  const startSolve = useCallback(
    async (id: string) => {
      setSolvingId(id);
      setSolveTexts((p) => ({ ...p, [id]: "" }));
      try {
        const res = await fetch(
          `/api/v1/mother-questions/${id}/ai_solve${qs}`,
          { method: "POST" },
        );
        if (!res.ok || !res.body) {
          setSolveTexts((p) => ({ ...p, [id]: "无法获取解题过程" }));
          return;
        }
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let acc = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          acc += dec.decode(value, { stream: true });
          setSolveTexts((p) => ({ ...p, [id]: acc }));
        }
      } catch (e: any) {
        setSolveTexts((p) => ({ ...p, [id]: `出错：${e?.message || e}` }));
      } finally {
        setSolvingId(null);
      }
    },
    [qs],
  );

  const removeItem = useCallback(
    async (id: string) => {
      if (!window.confirm("删除到回收站？")) return;
      try {
        await fetch(`/api/v1/mother-questions/${id}${qs}`, {
          method: "DELETE",
        });
      } catch {
        /* ignore */
      }
      void loadList(1, false);
    },
    [qs, loadList],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/mother-questions/reviews/due${qs}`);
      if (!res.ok) {
        setItems([]);
        return;
      }
      const data = await res.json();
      setItems(Array.isArray(data.items) ? data.items : []);
      setIdx(0);
      setRevealed(false);
      setExplainText("");
      setDone(0);
      setVariant(null);
      setVariantAnswer("");
      setVariantRevealed(false);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [qs]);

  // ---- WQ4（M24）：状态转移——标记已掌握 / 撤回复习 ----
  const toggleMastery = useCallback(
    async (it: any) => {
      const mastered = it.mastery_status === "mastered";
      const action = mastered ? "transfer-to-active" : "transfer-to-mastered";
      if (!window.confirm(mastered ? "撤回复习？" : "标记为已掌握？")) return;
      try {
        const res = await fetch(`/api/v1/mother-questions/${it.id}/${action}${qs}`, {
          method: "POST",
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          window.alert(data.detail || "操作失败");
          return;
        }
        if (view === "list") void loadList(1, false);
        else void load();
      } catch {
        window.alert("网络错误，请重试");
      }
    },
    [qs, view, loadList, load],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const current = items[idx];

  const submit = useCallback(
    async (rating: number) => {
      if (!current || submitting) return;
      setSubmitting(true);
      try {
        const res = await fetch(
          `/api/v1/mother-questions/${current.id}/review/submit${qs}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              rating,
              source: "h5_review",
              time_spent: 5,
            }),
          },
        );
        if (res.ok) {
          setDone((d) => d + 1);
          if (idx + 1 < items.length) {
            setIdx(idx + 1);
            setRevealed(false);
            setExplainText("");
          } else {
            // C5（M18-B）：复习收尾入 episodic 记忆
            const finished = done + 1;
            postSessionSummary(u, {
              topics: [],
              wins: [`完成 ${finished} 道到期错题复习`],
              stuck: "",
              questions: finished,
              correct: finished,
              source: "review",
            });
            setItems([]);
            setIdx(0);
          }
        }
      } catch {
        /* ignore */
      } finally {
        setSubmitting(false);
      }
    },
    [current, submitting, idx, items.length, qs, done, u],
  );

  const explain = useCallback(async () => {
    if (!current || explaining) return;
    setExplaining(true);
    setExplainText("");
    try {
      const res = await fetch(
        `/api/v1/mother-questions/${current.id}/explain${qs}`,
        { method: "POST" },
      );
      const data = await res.json();
      setExplainText(data.explain || data.msg || "（暂无讲解）");
    } catch {
      setExplainText("讲解失败，请重试");
    } finally {
      setExplaining(false);
    }
  }, [current, explaining, qs]);

  // 变式练习（design §5.2）：取已有变式 / 无则生成；作答后 attempt 上报
  const openVariant = useCallback(async () => {
    if (!current || variantLoading) return;
    setVariantLoading(true);
    setVariant(null);
    setVariantAnswer("");
    setVariantRevealed(false);
    setVariantSelfOk(false);
    try {
      const res = await fetch(
        `/api/v1/mother-questions/${current.id}/variants${qs}`,
      );
      if (!res.ok) {
        setVariant({ id: "__empty__" });
        return;
      }
      const data = await res.json();
      const vItems = Array.isArray(data.items) ? data.items : [];
      if (vItems.length > 0) {
        setVariant(vItems[0]);
      } else {
        setVariant({ id: "__empty__" });
      }
    } catch {
      setVariant({ id: "__empty__" });
    } finally {
      setVariantLoading(false);
    }
  }, [current, variantLoading, qs]);

  const generateVariant = useCallback(async () => {
    if (!current || variantLoading) return;
    setVariantLoading(true);
    try {
      const res = await fetch(
        `/api/v1/mother-questions/${current.id}/generate_variants${qs}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ count: 3 }),
        },
      );
      const data = await res.json();
      const vItems = Array.isArray(data.items) ? data.items : [];
      if (vItems.length > 0) {
        setVariant(vItems[0]);
        setVariantAnswer("");
        setVariantRevealed(false);
      } else {
        setVariant({ id: "__empty__" });
      }
    } catch {
      setVariant({ id: "__empty__" });
    } finally {
      setVariantLoading(false);
    }
  }, [current, variantLoading, qs]);

  const submitVariantAttempt = useCallback(
    async (isCorrect: boolean) => {
      if (!current || !variant || variant.id === "__empty__") return;
      setVariantSelfOk(true);
      try {
        await fetch(`/api/v1/mother-questions/${current.id}/attempts${qs}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mother_id: current.id,
            variant_id: variant.id !== "__empty__" ? variant.id : null,
            is_correct: isCorrect,
            user_answer: variantAnswer || null,
            source: "h5_variant",
            time_spent: 5,
          }),
        });
      } catch {
        /* 上报失败不打断 */
      }
    },
    [current, variant, variantAnswer, qs],
  );

  // P2-B 一键分析错因（LLM 归因到六枚举）
  const analyzeWrong = useCallback(async () => {
    if (!current || attrLoading) return;
    setAttrLoading(true);
    try {
      const res = await fetch(
        `/api/v1/mother-questions/${current.id}/attribute${qs}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        },
      );
      const data = await res.json();
      if (res.ok && data.wrong_reason) {
        setWrongReason(data.wrong_reason);
        setWrongAdvice(data.advice || "");
      } else {
        setWrongReason("");
        setWrongAdvice(typeof data.detail === "string" ? data.detail : "分析失败（LLM 未配置？）");
      }
    } catch {
      setWrongReason("");
      setWrongAdvice("网络错误，请重试");
    } finally {
      setAttrLoading(false);
    }
  }, [current, attrLoading, qs]);

  // P2-B 批量归因（对未归因错题批量 LLM 分析）
  const runBatchAttribute = useCallback(async () => {
    if (batchAttr) return;
    setBatchAttr(true);
    try {
      const res = await fetch(`/api/v1/mother-questions/attribute-batch${qs}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 20 }),
      });
      const data = await res.json();
      if (data && typeof data.attributed === "number" && data.attributed > 0) {
        window.alert(`已批量归因 ${data.attributed} 道题的错因`);
        await load();
      } else {
        window.alert("暂无待归因的错题");
      }
    } catch {
      window.alert("批量归因失败");
    } finally {
      setBatchAttr(false);
    }
  }, [batchAttr, qs, load]);

  return (
    <H5Shell active="wrongbook" onRefresh={refreshCurrent}>
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(to right, #f97316, #d97706)", color: "#fff", padding: 16, borderBottomLeftRadius: 24, borderBottomRightRadius: 24 }}>
        <H5PageHeader
          title="📖 错题本"
          right={
            <>
              <button
                onClick={() => void runBatchAttribute()}
                disabled={batchAttr}
                style={{
                  ...BTN_BASE, display: "flex", alignItems: "center", gap: 2, fontSize: 11,
                  color: "#fef3c7", border: "1px solid rgba(252,211,77,0.4)", borderRadius: 9999,
                  padding: "2px 8px", opacity: batchAttr ? 0.5 : 1,
                }}
              >
                <ThunderboltOutlined style={{ fontSize: 12 }} />
                {batchAttr ? "归因中…" : "批量归因"}
              </button>
            </>
          }
        />
        <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, background: "rgba(255,255,255,0.15)", borderRadius: 9999, padding: 2 }}>
            {(
              [
                { key: "due", label: "📚 待复习" },
                { key: "list", label: "📋 全部错题" },
                { key: "trash", label: "🗑️ 回收站" },
                { key: "analysis", label: "📊 分析" },
              ] as const
            ).map((t) => (
              <button
                key={t.key}
                onClick={() => setView(t.key)}
                style={{
                  ...BTN_BASE, padding: "4px 10px", borderRadius: 9999, fontSize: 12,
                  transition: "all .15s",
                  background: view === t.key ? "#fff" : "transparent",
                  color: view === t.key ? "#b45309" : "#fef3c7",
                  fontWeight: view === t.key ? 500 : 400,
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
          {view === "due" && done > 0 && (
            <span style={{ color: "#fef3c7", fontSize: 12 }}>已完成 {done} 题 ✓</span>
          )}
        </div>
      </div>

      <div style={{ padding: "0 16px", marginTop: 16, display: "flex", flexDirection: "column", gap: 16 }}>
        {view === "list" ? (
          /* F6 + N6：全部错题——搜索 / 高级筛选 / 多选导出 / 新建 / 分步解题 / 编辑 / 删除 */
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, background: "#fff", borderRadius: 16, border: `1px solid ${SLATE[200]}`, padding: "8px 12px" }}>
              <SearchOutlined style={{ fontSize: 16, color: SLATE[400], flexShrink: 0 }} />
              <input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void loadList(1, false);
                }}
                placeholder="搜索题目 / 题干 / 错因 / 标签"
                style={{ flex: 1, minWidth: 0, fontSize: 14, background: "transparent", border: "none", outline: "none", padding: 0 }}
              />
              <button
                onClick={() => {
                  setFilterOpen((v) => {
                    if (!v) void ensureDict();
                    return !v;
                  });
                }}
                data-testid="wb-filter-btn"
                style={{
                  ...BTN_BASE, flexShrink: 0, display: "flex", alignItems: "center", gap: 2, fontSize: 12,
                  borderRadius: 9999, padding: "4px 8px",
                  ...(fSubject || fGrade || fCategory || fTextbook || fChapter
                    ? { background: "#f59e0b", color: "#fff", border: "1px solid #f59e0b" }
                    : { color: "#d97706", border: "1px solid #fde68a" }),
                }}
              >
                <ControlOutlined style={{ fontSize: 12 }} /> 筛选
              </button>
              <button
                onClick={() => void openForm()}
                data-testid="wb-new-btn"
                aria-label="新建错题"
                style={{ ...BTN_BASE, flexShrink: 0, width: 32, height: 32, borderRadius: 9999, background: "#f59e0b", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}
              >
                <PlusOutlined style={{ fontSize: 16 }} />
              </button>
            </div>

            {/* N6-a：筛选弹层 */}
            {filterOpen && (
              <div style={{ ...cardWhite, padding: 12, display: "flex", flexDirection: "column", gap: 8 }} data-testid="wb-filter-panel">
                {!dict ? (
                  <div style={{ fontSize: 12, color: SLATE[400], padding: "8px 0", textAlign: "center" }}>加载字典…</div>
                ) : (
                  <>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      <select
                        value={fSubject}
                        onChange={(e) => setFSubject(e.target.value)}
                        style={{ padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 12 }}
                      >
                        <option value="">学科：全部</option>
                        {(dict.subjects || []).map((s) => (
                          <option key={s} value={s}>
                            {SUBJECT_LABELS[s] || s}
                          </option>
                        ))}
                      </select>
                      <select
                        value={fTextbook}
                        onChange={(e) => {
                          setFTextbook(e.target.value);
                          setFChapter("");
                        }}
                        style={{ padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 12 }}
                      >
                        <option value="">教材：全部</option>
                        {(dict.textbooks || []).map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                      <select
                        value={fChapter}
                        onChange={(e) => setFChapter(e.target.value)}
                        style={{ padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 12 }}
                      >
                        <option value="">章节：全部</option>
                        {chapterOptions.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                      <select
                        value={`${fSortBy}:${fSortOrder}`}
                        onChange={(e) => {
                          const [sb, so] = e.target.value.split(":");
                          setFSortBy(sb);
                          setFSortOrder(so);
                        }}
                        style={{ padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 12 }}
                      >
                        <option value="create_time:desc">最新创建优先</option>
                        <option value="create_time:asc">最早创建优先</option>
                        <option value="difficulty:desc">难度从高到低</option>
                        <option value="difficulty:asc">难度从低到高</option>
                      </select>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        onClick={() => {
                          setFSubject("");
                          setFGrade("");
                          setFCategory("");
                          setFTextbook("");
                          setFChapter("");
                          void loadList(1, false);
                        }}
                        style={{ ...BTN_BASE, flex: 1, padding: "8px 0", borderRadius: 12, border: `1px solid ${SLATE[200]}`, color: SLATE[500], fontSize: 12, background: "#fff" }}
                      >
                        重置
                      </button>
                      <button
                        onClick={() => {
                          void loadList(1, false);
                          setFilterOpen(false);
                        }}
                        data-testid="wb-filter-apply"
                        style={{ ...BTN_BASE, flex: 1, padding: "8px 0", borderRadius: 12, background: "#f59e0b", color: "#fff", fontSize: 12, fontWeight: 500 }}
                      >
                        应用筛选
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* N6-e：多选模式操作条 */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                onClick={() => {
                  setMultiMode((v) => !v);
                  setSelectedIds(new Set());
                }}
                style={{
                  ...BTN_BASE, fontSize: 12, padding: "6px 12px", borderRadius: 9999,
                  ...(multiMode
                    ? { background: "#4f46e5", color: "#fff", border: "1px solid #4f46e5" }
                    : { background: "#fff", color: SLATE[500], border: `1px solid ${SLATE[200]}` }),
                }}
              >
                {multiMode ? "退出多选" : "多选导出"}
              </button>
              {multiMode && (
                <>
                  <span style={{ fontSize: 12, color: SLATE[400] }}>已选 {selectedIds.size} 题</span>
                  <button
                    onClick={() => void exportSelected()}
                    disabled={selectedIds.size === 0 || exporting}
                    data-testid="wb-export-btn"
                    style={{ ...BTN_BASE, display: "flex", alignItems: "center", gap: 4, fontSize: 12, padding: "6px 12px", borderRadius: 9999, background: "#059669", color: "#fff", opacity: selectedIds.size === 0 || exporting ? 0.5 : 1 }}
                  >
                    {exporting ? <LoadingOutlined style={{ fontSize: 12 }} spin /> : <DownloadOutlined style={{ fontSize: 12 }} />}
                    导出 Word
                  </button>
                </>
              )}
              <span style={{ marginLeft: "auto", fontSize: 12, color: SLATE[400] }}>共 {total} 题</span>
            </div>

            {listTags.length > 0 && (
              <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 4 }}>
                <button
                  onClick={() => setActiveTag("")}
                  style={{
                    ...BTN_BASE, flexShrink: 0, padding: "4px 12px", borderRadius: 9999, fontSize: 12,
                    ...(!activeTag
                      ? { background: "#f59e0b", color: "#fff", border: "1px solid #f59e0b" }
                      : { background: "#fff", color: SLATE[500], border: `1px solid ${SLATE[200]}` }),
                  }}
                >
                  全部
                </button>
                {listTags.map((t) => (
                  <button
                    key={t}
                    onClick={() => setActiveTag(activeTag === t ? "" : t)}
                    style={{
                      ...BTN_BASE, flexShrink: 0, padding: "4px 12px", borderRadius: 9999, fontSize: 12,
                      ...(activeTag === t
                        ? { background: "#f59e0b", color: "#fff", border: "1px solid #f59e0b" }
                        : { background: "#fff", color: SLATE[500], border: `1px solid ${SLATE[200]}` }),
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            )}
            {listLoading && listItems.length === 0 ? (
              <div style={centerLoading}>
                <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载错题…
              </div>
            ) : listItems.length === 0 ? (
              <div style={{ textAlign: "center", padding: "64px 0", color: SLATE[400], fontSize: 14 }}>没有匹配的错题</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {listItems.map((it) => {
                  const title = it.title || it.question_text || "";
                  const solving = solvingId === it.id;
                  const solText = solveTexts[it.id] || "";
                  const att = attempts[it.id];
                  return (
                    <div
                      key={it.id}
                      id={`mq-${it.id}`}
                      style={{
                        ...cardWhite, padding: "12px 14px", transition: "all .15s",
                        ...(highlightId === it.id
                          ? { border: "1px solid #818cf8", boxShadow: "0 0 0 2px #c7d2fe" }
                          : {}),
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                        {multiMode && (
                          <button
                            onClick={() => toggleSelect(it.id)}
                            aria-label="选择"
                            style={{ ...BTN_BASE, flexShrink: 0, marginTop: 2, color: "#6366f1" }}
                          >
                            {selectedIds.has(it.id) ? (
                              <CheckSquareOutlined style={{ fontSize: 20 }} />
                            ) : (
                              <BorderOutlined style={{ fontSize: 20, color: SLATE[300] }} />
                            )}
                          </button>
                        )}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 14, fontWeight: 500, color: SLATE[800], ...clamp2 }}>{title}</div>
                        </div>
                      </div>
                      {(it.tags || []).length > 0 && (
                        <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 4 }}>
                          {(it.tags || [])
                            .slice(0, 5)
                            .map((t: string) => (
                              <span
                                key={t}
                                style={{ fontSize: 11, background: SLATE[100], color: SLATE[500], borderRadius: 9999, padding: "2px 8px" }}
                              >
                                {t}
                              </span>
                            ))}
                        </div>
                      )}
                      <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
                        {/* WQ4（M24）：标记已掌握 / 撤回复习 */}
                        <button
                          onClick={() => void toggleMastery(it)}
                          data-testid={it.mastery_status === "mastered" ? "unmark-mastered" : "mark-mastered"}
                          style={{ ...BTN_BASE, flexShrink: 0, padding: "8px 10px", borderRadius: 12, background: SLATE[50], color: SLATE[500], fontSize: 11, fontWeight: 500 }}
                        >
                          {it.mastery_status === "mastered" ? "撤回复习" : "标为已掌握"}
                        </button>
                        <button
                          onClick={() => void startSolve(it.id)}
                          disabled={solving}
                          style={{ ...BTN_BASE, flex: 1, padding: "8px 0", borderRadius: 12, background: "#f0f9ff", border: "1px solid #bae6fd", color: "#0369a1", fontSize: 12, fontWeight: 500, opacity: solving ? 0.5 : 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}
                        >
                          <ThunderboltOutlined style={{ fontSize: 12 }} />
                          {solving
                            ? "解析中…"
                            : solText
                              ? "重新解析"
                              : "🧮 分步解题"}
                        </button>
                        <button
                          onClick={() => void openForm(it)}
                          aria-label="编辑"
                          style={{ ...BTN_BASE, flexShrink: 0, width: 36, height: 36, borderRadius: 12, background: SLATE[50], color: SLATE[400], display: "flex", alignItems: "center", justifyContent: "center" }}
                        >
                          <EditOutlined style={{ fontSize: 16 }} />
                        </button>
                        <button
                          onClick={() => void removeItem(it.id)}
                          aria-label="删除"
                          style={{ ...BTN_BASE, flexShrink: 0, width: 36, height: 36, borderRadius: 12, background: SLATE[50], color: SLATE[400], display: "flex", alignItems: "center", justifyContent: "center" }}
                        >
                          <DeleteOutlined style={{ fontSize: 16 }} />
                        </button>
                      </div>
                      {solText && (
                        <div style={{ marginTop: 8, padding: 12, borderRadius: 12, background: SLATE[50], border: `1px solid ${SLATE[100]}`, fontSize: 13 }}>
                          <MarkdownRenderer content={solText} />
                        </div>
                      )}
                      {/* N6-g：答题记录折叠区 */}
                      <button
                        onClick={() => void toggleAttempts(it.id)}
                        style={{ ...BTN_BASE, marginTop: 8, display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: SLATE[400] }}
                      >
                        <HistoryOutlined style={{ fontSize: 12 }} />
                        答题记录
                        <DownOutlined
                          style={{ fontSize: 12, transition: "transform .15s", transform: attemptsOpen === it.id ? "rotate(180deg)" : "none" }}
                        />
                      </button>
                      {attemptsOpen === it.id && (
                        <div style={{ marginTop: 6, padding: 10, borderRadius: 12, background: SLATE[50], border: `1px solid ${SLATE[100]}`, fontSize: 12 }} data-testid="attempts-panel">
                          {!att ? (
                            <span style={{ color: SLATE[400] }}>加载中…</span>
                          ) : att.total === 0 ? (
                            <span style={{ color: SLATE[400] }}>还没有作答记录</span>
                          ) : (
                            <>
                              <div style={{ color: SLATE[600], marginBottom: 4 }}>
                                共 {att.total} 次 · 正确 {att.correct} 次 · 正确率{" "}
                                {Math.round((att.accuracy || 0) * 100)}%
                              </div>
                              {(att.items || []).slice(0, 10).map((a: any, i: number) => (
                                <div key={a.id || i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "2px 0", borderTop: i === 0 ? "none" : `1px solid ${SLATE[100]}` }}>
                                  <span style={{ color: a.is_correct ? "#059669" : "#f43f5e" }}>
                                    {a.is_correct ? "✓" : "✗"} {a.source || "review"}
                                  </span>
                                  <span style={{ color: SLATE[300] }}>
                                    {a.created_at
                                      ? new Date(a.created_at * 1000).toLocaleDateString()
                                      : ""}
                                  </span>
                                </div>
                              ))}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
                {/* N6-a：上拉加载更多 */}
                {listItems.length < total && (
                  <button
                    onClick={() => void loadList(page + 1, true)}
                    disabled={listLoading}
                    style={{ ...BTN_BASE, width: "100%", padding: "12px 0", borderRadius: 16, border: `1px solid ${SLATE[200]}`, background: "#fff", color: SLATE[500], fontSize: 14, opacity: listLoading ? 0.5 : 1 }}
                  >
                    {listLoading ? "加载中…" : `加载更多（已显示 ${listItems.length}/${total}）`}
                  </button>
                )}
              </div>
            )}
          </div>
        ) : view === "trash" ? (
          /* N6-d：回收站 */
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }} data-testid="wb-trash">
            {trashLoading ? (
              <div style={centerLoading}>
                <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载回收站…
              </div>
            ) : trashItems.length === 0 ? (
              <div style={{ textAlign: "center", padding: "64px 0", color: SLATE[400], fontSize: 14 }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>🗑️</div>
                回收站是空的
              </div>
            ) : (
              trashItems.map((t) => (
                <div key={t.id} style={{ ...cardWhite, padding: "12px 14px" }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: SLATE[700], ...clamp2 }}>
                    {t.title || t.question_text}
                  </div>
                  <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                    <button
                      onClick={() => void restoreItem(t.id)}
                      style={{ ...BTN_BASE, flex: 1, padding: "8px 0", borderRadius: 12, background: "#ecfdf5", border: "1px solid #a7f3d0", color: "#047857", fontSize: 12, fontWeight: 500, display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}
                    >
                      <UndoOutlined style={{ fontSize: 14 }} /> 恢复
                    </button>
                    <button
                      onClick={() => void hardDelete(t.id)}
                      style={{ ...BTN_BASE, flex: 1, padding: "8px 0", borderRadius: 12, background: "#fff1f2", border: "1px solid #fecdd3", color: "#e11d48", fontSize: 12, fontWeight: 500, display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}
                    >
                      <DeleteOutlined style={{ fontSize: 14 }} /> 彻底删除
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : view === "analysis" ? (
          /* N6-f：分析仪表盘四卡（轻量 SVG，不引图表库） */
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }} data-testid="wb-analysis">
            {analysisLoading || !analysis ? (
              <div style={centerLoading}>
                <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 生成分析…
              </div>
            ) : (
              <>
                <div style={{ fontSize: 12, color: SLATE[400], padding: "0 4px" }}>
                  共 {analysis.stats?.total ?? 0} 道错题 · 平均难度 {analysis.stats?.avg_difficulty ?? "-"}
                </div>
                {/* 卡1：掌握分布（环形） */}
                <div style={{ ...cardWhite, padding: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: SLATE[700], marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                    <BarChartOutlined style={{ fontSize: 16, color: "#f59e0b" }} /> 掌握分布
                  </div>
                  <MasteryDonut byStatus={analysis.stats?.by_status || {}} />
                </div>
                {/* 卡2：难度分布（条形） */}
                <div style={{ ...cardWhite, padding: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: SLATE[700], marginBottom: 8 }}>难度分布</div>
                  <DifficultyBars byDifficulty={analysis.stats?.by_difficulty || {}} />
                </div>
                {/* 卡3：错因分布 */}
                <div style={{ ...cardWhite, padding: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: SLATE[700], marginBottom: 8 }}>错因分布</div>
                  {analysis.patterns.length === 0 ? (
                    <div style={{ fontSize: 12, color: SLATE[400], padding: "12px 0", textAlign: "center" }}>
                      暂无错因数据（复习时点「一键分析错因」可生成）
                    </div>
                  ) : (
                    <ReasonBars patterns={analysis.patterns} />
                  )}
                </div>
                {/* 卡4：30 天趋势 */}
                <div style={{ ...cardWhite, padding: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: SLATE[700], marginBottom: 8 }}>近 30 天录入趋势</div>
                  <TrendLine trends={analysis.trends} />
                </div>
              </>
            )}
          </div>
        ) : (
          <>
        {loading ? (
          <div style={centerLoading}>
            <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载错题…
          </div>
        ) : !current ? (
          <div style={{ textAlign: "center", padding: "64px 0", color: SLATE[400] }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🎉</div>
            {items.length === 0 && done === 0 ? (
              <>
                <div style={{ fontWeight: 500, color: SLATE[500] }}>暂时没有到期复习</div>
                <div style={{ fontSize: 14, marginTop: 8 }}>
                  先去「拍错题」录入，或过一段时间再来巩固
                </div>
                <Link
                  to={withU("/e/tutor/h5/wrong", u)}
                  style={{ marginTop: 16, display: "inline-block", padding: "8px 16px", borderRadius: 12, background: "#f43f5e", color: "#fff", fontSize: 14, textDecoration: "none" }}
                >
                  📷 去拍错题
                </Link>
              </>
            ) : (
              <div style={{ fontWeight: 500, color: SLATE[500] }}>本轮复习完成！</div>
            )}
          </div>
        ) : (
          <>
            {/* 进度 */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: SLATE[400], padding: "0 4px" }}>
              <span>
                第 {idx + 1} / {items.length} 题
              </span>
              <div style={{ flex: 1, height: 6, background: SLATE[200], borderRadius: 9999, overflow: "hidden" }}>
                <div
                  style={{ height: "100%", background: "#f59e0b", borderRadius: 9999, transition: "all .15s", width: `${((idx + 1) / items.length) * 100}%` }}
                />
              </div>
            </div>

            {/* 题目卡 */}
            <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06)", border: `1px solid ${SLATE[200]}`, padding: 16 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 12, color: SLATE[400] }}>
                  {labelOf(current.subject) || "数学"} · 难度 {current.difficulty ?? 3}/5
                </span>
                <button
                  onClick={() => void h5Speak(current.title + "。" + (current.question_text || ""))}
                  aria-label="朗读题目"
                  style={{ ...BTN_BASE, color: SLATE[400] }}
                >
                  <SoundOutlined style={{ fontSize: 16 }} />
                </button>
              </div>
              <div style={{ fontSize: 15, fontWeight: 500, color: SLATE[800] }}>
                {current.title}
              </div>
              {current.question_text && (
                <div style={{ marginTop: 8, fontSize: 15, lineHeight: 1.625, color: SLATE[700], whiteSpace: "pre-wrap" }}>
                  {current.question_text}
                </div>
              )}

              {/* 答案 */}
              {revealed && (
                <div style={{ marginTop: 16, padding: 12, borderRadius: 16, background: "#ecfdf5", border: "1px solid #a7f3d0" }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#047857", marginBottom: 4 }}>
                    参考答案
                  </div>
                  <div style={{ fontSize: 14, color: SLATE[700], whiteSpace: "pre-wrap" }}>
                    {current.standard_answer || "（暂无标准答案）"}
                  </div>
                  {current.detailed_analysis && (
                    <div style={{ marginTop: 8, fontSize: 14, color: SLATE[600], whiteSpace: "pre-wrap", borderTop: "1px solid #d1fae5", paddingTop: 8 }}>
                      {current.detailed_analysis}
                    </div>
                  )}
                </div>
              )}

              {/* P2-B 错因分析（LLM 归因，revealed 后展示/触发） */}
              {revealed && (
                <div style={{ marginTop: 12 }}>
                  {wrongReason ? (
                    <div style={{ padding: 12, borderRadius: 16, background: "#f5f3ff", border: "1px solid #ddd6fe" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14, fontWeight: 600, color: "#6d28d9", marginBottom: 4 }}>
                        <ThunderboltOutlined style={{ fontSize: 14 }} /> 错因分析
                      </div>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 8, flexWrap: "wrap" }}>
                        <span style={{ padding: "2px 8px", borderRadius: 9999, background: "#ede9fe", color: "#6d28d9", fontSize: 12, fontWeight: 500 }}>
                          {labelOf(wrongReason) || wrongReason}
                        </span>
                        {wrongAdvice && (
                          <span style={{ fontSize: 12, color: SLATE[600] }}>{wrongAdvice}</span>
                        )}
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => void analyzeWrong()}
                      disabled={attrLoading}
                      style={{ ...BTN_BASE, width: "100%", padding: "10px 0", borderRadius: 16, border: "1px solid #ddd6fe", background: "#f5f3ff", color: "#6d28d9", fontSize: 14, fontWeight: 500, opacity: attrLoading ? 0.5 : 1 }}
                    >
                      {attrLoading ? "分析中…" : "✨ 一键分析错因"}
                    </button>
                  )}
                </div>
              )}

              {/* W4（第八篇 M16-C）：一键问 AI——带题干+我的错答+错因进对话 */}
              {revealed && (
                <Link
                  to={withU(
                    `/e/tutor/h5/chat?text=${encodeURIComponent(
                      [
                        current.question_text || current.title || "",
                        current.wrong_answer ? `我的错答：${current.wrong_answer}` : "",
                        wrongReason ? `错因：${labelOf(wrongReason) || wrongReason}` : "",
                      ]
                        .filter(Boolean)
                        .join("\n"),
                    )}`,
                    u,
                  )}
                  style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, width: "100%", padding: "10px 0", borderRadius: 16, border: "1px solid #bae6fd", background: "#f0f9ff", color: "#0369a1", fontSize: 14, fontWeight: 500, textDecoration: "none" }}
                >
                  <MessageOutlined style={{ fontSize: 16 }} /> 问 AI 这道题
                </Link>
              )}

              {/* AI 讲解 */}
              {explainText && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 16, background: "#f0f9ff", border: "1px solid #bae6fd" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 14, fontWeight: 600, color: "#0369a1", marginBottom: 4 }}>
                    <ThunderboltOutlined style={{ fontSize: 14 }} /> AI 讲解
                  </div>
                  <div style={{ fontSize: 14, color: SLATE[700], whiteSpace: "pre-wrap" }}>
                    {explainText}
                  </div>
                </div>
              )}

              {!revealed ? (
                <button
                  onClick={() => setRevealed(true)}
                  style={{ ...BTN_BASE, marginTop: 16, width: "100%", padding: "12px 0", borderRadius: 16, background: "#4f46e5", color: "#fff", fontWeight: 500, fontSize: 14, transition: "all .15s" }}
                >
                  回忆一下，然后看答案
                </button>
              ) : (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 12, color: SLATE[400], marginBottom: 8, textAlign: "center" }}>
                    记得怎么样？选择后按遗忘曲线安排下次复习
                  </div>
                  {/* G4（M24-A）：与桌面 4 档 FSRS 对齐（1 忘记 / 2 困难 / 3 良好 / 4 简单） */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
                    <button
                      onClick={() => submit(1)}
                      disabled={submitting}
                      style={{ ...BTN_BASE, padding: "12px 0", borderRadius: 16, background: "#fff1f2", border: "1px solid #fecdd3", color: "#e11d48", fontSize: 14, fontWeight: 500, opacity: submitting ? 0.5 : 1 }}
                    >
                      忘了 😵
                    </button>
                    <button
                      onClick={() => submit(2)}
                      disabled={submitting}
                      style={{ ...BTN_BASE, padding: "12px 0", borderRadius: 16, background: "#fffbeb", border: "1px solid #fde68a", color: "#d97706", fontSize: 14, fontWeight: 500, opacity: submitting ? 0.5 : 1 }}
                    >
                      模糊 🤔
                    </button>
                    <button
                      onClick={() => submit(3)}
                      disabled={submitting}
                      style={{ ...BTN_BASE, padding: "12px 0", borderRadius: 16, background: "#f0f9ff", border: "1px solid #bae6fd", color: "#0284c7", fontSize: 14, fontWeight: 500, opacity: submitting ? 0.5 : 1 }}
                    >
                      记住 🙂
                    </button>
                    <button
                      onClick={() => submit(4)}
                      disabled={submitting}
                      style={{ ...BTN_BASE, padding: "12px 0", borderRadius: 16, background: "#ecfdf5", border: "1px solid #a7f3d0", color: "#059669", fontSize: 14, fontWeight: 500, opacity: submitting ? 0.5 : 1 }}
                    >
                      简单 😄
                    </button>
                  </div>
                </div>
              )}

              <button
                onClick={() => void explain()}
                disabled={explaining}
                style={{ ...BTN_BASE, marginTop: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, width: "100%", padding: "10px 0", borderRadius: 16, border: "1px solid #bae6fd", color: "#0284c7", fontSize: 14, fontWeight: 500, opacity: explaining ? 0.5 : 1 }}
              >
                <ThunderboltOutlined style={{ fontSize: 16 }} />
                {explaining ? "讲解中…" : "AI 讲解这道题"}
              </button>

              {/* 变式练习（design §5.2） */}
              <button
                onClick={() => void openVariant()}
                disabled={variantLoading}
                style={{ ...BTN_BASE, marginTop: 8, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, width: "100%", padding: "10px 0", borderRadius: 16, border: "1px solid #a7f3d0", color: "#059669", fontSize: 14, fontWeight: 500, opacity: variantLoading ? 0.5 : 1 }}
              >
                <ReloadOutlined style={{ fontSize: 16 }} />
                {variantLoading ? "加载中…" : variant ? "换一道变式" : "🔁 做道变式"}
              </button>

              {variant && variant.id !== "__empty__" && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 16, background: "rgba(236,253,245,0.6)", border: "1px solid #a7f3d0" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "#047857" }}>
                      变式 · {variant.variant_type || "综合变式"}
                      {variant.difficulty ? ` · 难度 ${variant.difficulty}/5` : ""}
                    </div>
                    <button onClick={() => setVariant(null)} style={{ ...BTN_BASE, fontSize: 12, color: SLATE[400] }}>
                      关闭
                    </button>
                  </div>
                  <div style={{ fontSize: 14, color: SLATE[700], whiteSpace: "pre-wrap" }}>
                    {variant.question_text || "（变式题干）"}
                  </div>

                  {!variantRevealed ? (
                    <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                      <input
                        value={variantAnswer}
                        onChange={(e) => setVariantAnswer(e.target.value)}
                        placeholder="写答案（或空提交看答案）"
                        style={{ flex: 1, minWidth: 0, padding: "8px 12px", borderRadius: 8, border: `1px solid #e5e7eb`, background: "#fff", fontSize: 14 }}
                      />
                      <button
                        onClick={() => setVariantRevealed(true)}
                        style={{ ...BTN_BASE, padding: "8px 12px", borderRadius: 8, background: "#059669", color: "#fff", fontSize: 14 }}
                      >
                        提交
                      </button>
                    </div>
                  ) : (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 14, color: SLATE[600], background: "#fff", borderRadius: 8, padding: 8, border: "1px solid #d1fae5" }}>
                        <span style={{ fontWeight: 500, color: "#047857" }}>参考答案：</span>
                        {variant.answer || "（无标准答案）"}
                      </div>
                      {!variantSelfOk && (
                        <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                          <button
                            onClick={() => submitVariantAttempt(true)}
                            style={{ ...BTN_BASE, padding: "8px 0", borderRadius: 8, background: "#d1fae5", color: "#047857", fontSize: 14, fontWeight: 500 }}
                          >
                            我做对了 ✓
                          </button>
                          <button
                            onClick={() => submitVariantAttempt(false)}
                            style={{ ...BTN_BASE, padding: "8px 0", borderRadius: 8, background: "#ffe4e6", color: "#e11d48", fontSize: 14, fontWeight: 500 }}
                          >
                            还不对 ✗
                          </button>
                        </div>
                      )}
                      {variantSelfOk && (
                        <div style={{ marginTop: 8, textAlign: "center", fontSize: 12, color: "#059669" }}>
                          已记录本次作答 ✓
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {variant && variant.id === "__empty__" && !variantLoading && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 16, background: SLATE[50], border: `1px solid ${SLATE[200]}`, textAlign: "center" }}>
                  <div style={{ fontSize: 14, color: SLATE[500], marginBottom: 8 }}>这道题还没有变式</div>
                  <button
                    onClick={() => void generateVariant()}
                    disabled={variantLoading}
                    style={{ ...BTN_BASE, padding: "8px 16px", borderRadius: 12, background: "linear-gradient(to right, #10b981, #0d9488)", color: "#fff", fontSize: 14, fontWeight: 500 }}
                  >
                    ✨ 生成变式
                  </button>
                </div>
              )}
            </div>

            <div style={{ fontSize: 12, color: SLATE[400], padding: "0 8px" }}>
              提示：先自己回忆再对答案，记忆效果更好。忘记的题会更快再次出现。
            </div>
          </>
        )}
          </>
        )}
      </div>

      {/* N6-b/c：新建 / 编辑表单（底部弹层；S1/M23 H5Sheet 统一基座） */}
      <H5Sheet
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editingId ? "✏️ 编辑错题" : "➕ 新建错题"}
        testId="wb-form"
      >
        <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {/* WQ3（M24）：错题/正确题 toggle（红/绿双键，默认错题） */}
              <div style={{ display: "flex", gap: 8 }} data-testid="is-wrong-toggle">
                <button
                  type="button"
                  onClick={() => setForm({ ...form, is_wrong: true })}
                  style={{ ...BTN_BASE, flex: 1, minHeight: 44, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, padding: "8px 12px", borderRadius: 12, fontSize: 14, fontWeight: 500, transition: "color .15s, background-color .15s", ...(form.is_wrong ? { background: "#f43f5e", color: "#fff", border: "1px solid transparent" } : { border: `1px solid ${SLATE[200]}`, color: SLATE[600] }) }}
                >
                  <CloseCircleOutlined style={{ fontSize: 16 }} /> 错题
                </button>
                <button
                  type="button"
                  onClick={() => setForm({ ...form, is_wrong: false })}
                  style={{ ...BTN_BASE, flex: 1, minHeight: 44, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, padding: "8px 12px", borderRadius: 12, fontSize: 14, fontWeight: 500, transition: "color .15s, background-color .15s", ...(!form.is_wrong ? { background: "#10b981", color: "#fff", border: "1px solid transparent" } : { border: `1px solid ${SLATE[200]}`, color: SLATE[600] }) }}
                >
                  <CheckCircleOutlined style={{ fontSize: 16 }} /> 正确题
                </button>
              </div>

              {/* WQ1（M24）：AI 填充——从题干/图片抽取补全字段 */}
              <button
                type="button"
                onClick={() => void aiFill()}
                disabled={aiFilling}
                data-testid="ai-fill-btn"
                style={{ ...BTN_BASE, width: "100%", minHeight: 44, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "10px 12px", borderRadius: 12, background: "#9333ea", color: "#fff", fontSize: 14, fontWeight: 500, opacity: aiFilling ? 0.5 : 1 }}
              >
                {aiFilling ? <LoadingOutlined style={{ fontSize: 16 }} spin /> : <ThunderboltOutlined style={{ fontSize: 16 }} />}
                {aiFilling ? "AI 填充中…" : "✨ AI 填充（从题干/图片补全字段）"}
              </button>

              {/* WQ2（M24）：双图上传——题目图（OCR 回填题干）+ 错答图 */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <Field label="题目图（OCR 自动识别）">
                  {form.photo_url ? (
                    <div style={{ position: "relative" }}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={form.photo_url} alt="题目图" style={{ width: "100%", height: 128, objectFit: "cover", borderRadius: 12, border: `1px solid #e5e7eb`, display: "block" }} />
                      <button
                        type="button"
                        onClick={() => setForm({ ...form, photo_url: "" })}
                        style={{ ...BTN_BASE, position: "absolute", top: 6, right: 6, padding: 6, background: "rgba(255,255,255,0.9)", borderRadius: 9999, boxShadow: "0 1px 2px rgba(0,0,0,.1)" }}
                        aria-label="删除题目图"
                      >
                        <DeleteOutlined style={{ fontSize: 16, color: SLATE[500] }} />
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => document.getElementById("form-photo-input")?.click()}
                      disabled={uploadingPhoto}
                      style={{ ...BTN_BASE, width: "100%", height: 128, border: "2px dashed #e5e7eb", borderRadius: 12, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontSize: 12, color: SLATE[400], opacity: uploadingPhoto ? 0.6 : 1 }}
                    >
                      {uploadingPhoto ? <LoadingOutlined style={{ fontSize: 24 }} spin /> : (
                        <>
                          <UploadOutlined style={{ fontSize: 24, marginBottom: 4 }} />
                          <span>上传题目图</span>
                        </>
                      )}
                    </button>
                  )}
                  <input
                    id="form-photo-input"
                    type="file"
                    accept="image/*"
                    data-testid="form-photo-input"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void uploadFormImage(f, "photo_url");
                      e.target.value = "";
                    }}
                  />
                </Field>
                <Field label="错答图">
                  {form.wrong_answer_image_url ? (
                    <div style={{ position: "relative" }}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={form.wrong_answer_image_url} alt="错答图" style={{ width: "100%", height: 128, objectFit: "cover", borderRadius: 12, border: `1px solid #e5e7eb`, display: "block" }} />
                      <button
                        type="button"
                        onClick={() => setForm({ ...form, wrong_answer_image_url: "" })}
                        style={{ ...BTN_BASE, position: "absolute", top: 6, right: 6, padding: 6, background: "rgba(255,255,255,0.9)", borderRadius: 9999, boxShadow: "0 1px 2px rgba(0,0,0,.1)" }}
                        aria-label="删除错答图"
                      >
                        <DeleteOutlined style={{ fontSize: 16, color: SLATE[500] }} />
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => document.getElementById("form-wrong-photo-input")?.click()}
                      disabled={uploadingWrongPhoto}
                      style={{ ...BTN_BASE, width: "100%", height: 128, border: "2px dashed #e5e7eb", borderRadius: 12, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontSize: 12, color: SLATE[400], opacity: uploadingWrongPhoto ? 0.6 : 1 }}
                    >
                      {uploadingWrongPhoto ? <LoadingOutlined style={{ fontSize: 24 }} spin /> : (
                        <>
                          <UploadOutlined style={{ fontSize: 24, marginBottom: 4 }} />
                          <span>上传错答图</span>
                        </>
                      )}
                    </button>
                  )}
                  <input
                    id="form-wrong-photo-input"
                    type="file"
                    accept="image/*"
                    data-testid="form-wrong-photo-input"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void uploadFormImage(f, "wrong_answer_image_url");
                      e.target.value = "";
                    }}
                  />
                </Field>
              </div>

              <Field label="标题 *">
                <input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="如：一元一次方程应用题"
                  style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                  maxLength={60}
                />
              </Field>
              <Field label="题干 *">
                <textarea
                  value={form.question_text}
                  onChange={(e) => setForm({ ...form, question_text: e.target.value })}
                  placeholder="完整题目内容"
                  rows={3}
                  style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14, resize: "none" }}
                />
              </Field>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <Field label="学科">
                  <select
                    value={form.subject}
                    onChange={(e) => setForm({ ...form, subject: e.target.value })}
                    style={{ width: "100%", boxSizing: "border-box", padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                  >
                    {Object.entries(SUBJECT_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="难度（1-5）">
                  <select
                    value={form.difficulty}
                    onChange={(e) => setForm({ ...form, difficulty: Number(e.target.value) })}
                    style={{ width: "100%", boxSizing: "border-box", padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        {"★".repeat(n)}{"☆".repeat(5 - n)}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <Field label="年级">
                  {/* WQ5（M24）：年级枚举化（与桌面 GRADES 同源） */}
                  <select
                    value={form.grade}
                    onChange={(e) => setForm({ ...form, grade: e.target.value })}
                    data-testid="form-grade"
                    style={{ width: "100%", boxSizing: "border-box", padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                  >
                    <option value="">不指定</option>
                    {GRADES.map((g) => (
                      <option key={g} value={g} title={g}>
                        {g}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="类别">
                  {/* WQ5（M24）：类别枚举化（与桌面 CATEGORIES 同源） */}
                  <select
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    data-testid="form-category"
                    style={{ width: "100%", boxSizing: "border-box", padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                  >
                    <option value="">不指定</option>
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c} title={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <Field label="标准答案">
                <textarea
                  value={form.standard_answer}
                  onChange={(e) => setForm({ ...form, standard_answer: e.target.value })}
                  rows={2}
                  style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14, resize: "none" }}
                />
              </Field>
              {/* WQ3（M24）：正确题隐藏「我的错答」 */}
              {form.is_wrong && (
                <Field label="我的错答">
                  <div data-testid="form-wrong-answer">
                    <input
                      value={form.wrong_answer}
                      onChange={(e) => setForm({ ...form, wrong_answer: e.target.value })}
                      style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                    />
                  </div>
                </Field>
              )}
              <Field label="详解">
                <textarea
                  value={form.detailed_analysis}
                  onChange={(e) => setForm({ ...form, detailed_analysis: e.target.value })}
                  rows={3}
                  style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14, resize: "none" }}
                />
              </Field>
              <Field label="解答步骤（每行一步）">
                <textarea
                  value={form.solution_steps}
                  onChange={(e) => setForm({ ...form, solution_steps: e.target.value })}
                  rows={2}
                  style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14, resize: "none" }}
                />
              </Field>
              <Field label="要点（逗号分隔）">
                <input
                  value={form.key_points}
                  onChange={(e) => setForm({ ...form, key_points: e.target.value })}
                  placeholder="如：设未知数，列方程"
                  style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                />
              </Field>
              <Field label="笔记">
                <input
                  value={form.note}
                  onChange={(e) => setForm({ ...form, note: e.target.value })}
                  style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                />
              </Field>
              {dict && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <Field label="教材">
                    <select
                      value={form.textbook_id}
                      onChange={(e) => setForm({ ...form, textbook_id: e.target.value, chapter_id: "" })}
                      style={{ width: "100%", boxSizing: "border-box", padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                    >
                      <option value="">不指定</option>
                      {(dict.textbooks || []).map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="章节">
                    <select
                      value={form.chapter_id}
                      onChange={(e) => setForm({ ...form, chapter_id: e.target.value })}
                      style={{ width: "100%", boxSizing: "border-box", padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                    >
                      <option value="">不指定</option>
                      {(dict.chapters || [])
                        .filter((c) => !form.textbook_id || c.textbook_id === form.textbook_id)
                        .map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                    </select>
                  </Field>
                </div>
              )}
              {dict && (dict.knowledge_points || []).length > 0 && (
                <Field label="知识点">
                  <select
                    value={form.knowledge_point_id}
                    onChange={(e) => setForm({ ...form, knowledge_point_id: e.target.value })}
                    style={{ width: "100%", boxSizing: "border-box", padding: 8, borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                  >
                    <option value="">不指定</option>
                    {(dict.knowledge_points || []).map((k) => (
                      <option key={k.id} value={k.id}>
                        {k.name}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              <Field label="标签（逗号分隔）">
                <input
                  value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                  placeholder="如：几何，期中"
                  style={{ width: "100%", boxSizing: "border-box", padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14 }}
                />
              </Field>
              <button
                onClick={() => void saveForm()}
                disabled={formSaving}
                style={{ ...BTN_BASE, width: "100%", padding: "12px 0", borderRadius: 16, background: "#f59e0b", color: "#fff", fontSize: 14, fontWeight: 500, opacity: formSaving ? 0.5 : 1 }}
              >
                {formSaving ? "保存中…" : editingId ? "保存修改" : "创建错题"}
              </button>
            </div>
        </div>
      </H5Sheet>
    </H5Shell>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "block" }}>
      <span style={{ display: "block", fontSize: 12, color: SLATE[400], marginBottom: 4 }}>{label}</span>
      {children}
    </label>
  );
}

// --------------------------------------------------------------------------- //
// N6-f：轻量 SVG 图表（不引图表库）
// --------------------------------------------------------------------------- //

const STATUS_COLORS: Record<string, string> = {
  mastered: "#10b981",
  reviewing: "#f59e0b",
  not_mastered: "#f43f5e",
};
const STATUS_NAMES: Record<string, string> = {
  mastered: "已掌握",
  reviewing: "复习中",
  not_mastered: "未掌握",
};

function MasteryDonut({ byStatus }: { byStatus: Record<string, number> }) {
  const entries = Object.entries(byStatus).filter(([, v]) => v > 0);
  const total = entries.reduce((s, [, v]) => s + v, 0);
  if (total === 0) {
    return <div style={{ fontSize: 12, color: SLATE[400], padding: "12px 0", textAlign: "center" }}>暂无数据</div>;
  }
  const R = 40;
  const C = 2 * Math.PI * R;
  let offset = 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <svg width="110" height="110" viewBox="0 0 110 110">
        <circle cx="55" cy="55" r={R} fill="none" stroke="#f1f5f9" strokeWidth="14" />
        {entries.map(([k, v]) => {
          const frac = v / total;
          const dash = frac * C;
          const el = (
            <circle
              key={k}
              cx="55"
              cy="55"
              r={R}
              fill="none"
              stroke={STATUS_COLORS[k] || "#94a3b8"}
              strokeWidth="14"
              strokeDasharray={`${dash} ${C - dash}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 55 55)"
            />
          );
          offset += dash;
          return el;
        })}
        <text x="55" y="60" textAnchor="middle" style={{ fill: SLATE[700] }} fontSize="16" fontWeight="bold">
          {total}
        </text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
        {entries.map(([k, v]) => (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span
              style={{ width: 10, height: 10, borderRadius: 2, display: "inline-block", background: STATUS_COLORS[k] || "#94a3b8" }}
            />
            <span style={{ color: SLATE[600] }}>
              {STATUS_NAMES[k] || k} {v} 题（{Math.round((v / total) * 100)}%）
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DifficultyBars({ byDifficulty }: { byDifficulty: Record<string, number> }) {
  const entries = [1, 2, 3, 4, 5].map((d) => [String(d), byDifficulty[String(d)] || 0] as const);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {entries.map(([d, v]) => (
        <div key={d} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 32, fontSize: 12, color: SLATE[400], textAlign: "right" }}>{d}★</span>
          <div style={{ flex: 1, height: 16, background: SLATE[100], borderRadius: 9999, overflow: "hidden" }}>
            <div
              style={{ height: "100%", borderRadius: 9999, background: "linear-gradient(to right, #fbbf24, #f97316)", width: `${(v / max) * 100}%` }}
            />
          </div>
          <span style={{ width: 24, fontSize: 12, color: SLATE[500] }}>{v}</span>
        </div>
      ))}
    </div>
  );
}

function ReasonBars({ patterns }: { patterns: { reason: string; count: number }[] }) {
  const max = Math.max(1, ...patterns.map((p) => p.count));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {patterns.slice(0, 6).map((p) => (
        <div key={p.reason} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 64, fontSize: 12, color: SLATE[500], textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {labelOf(p.reason)}
          </span>
          <div style={{ flex: 1, height: 16, background: SLATE[100], borderRadius: 9999, overflow: "hidden" }}>
            <div
              style={{ height: "100%", borderRadius: 9999, background: "linear-gradient(to right, #a78bfa, #a855f7)", width: `${(p.count / max) * 100}%` }}
            />
          </div>
          <span style={{ width: 24, fontSize: 12, color: SLATE[500] }}>{p.count}</span>
        </div>
      ))}
    </div>
  );
}

function TrendLine({ trends }: { trends: { date: string; count: number }[] }) {
  if (trends.length === 0) {
    return <div style={{ fontSize: 12, color: SLATE[400], padding: "12px 0", textAlign: "center" }}>近 30 天没有新错题</div>;
  }
  const max = Math.max(1, ...trends.map((t) => t.count));
  const W = 280;
  const H = 60;
  const step = trends.length > 1 ? W / (trends.length - 1) : W;
  const points = trends
    .map((t, i) => `${i * step},${H - (t.count / max) * (H - 8) - 4}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%" }} width={W} height={H}>
      <polyline points={points} fill="none" stroke="#f59e0b" strokeWidth="2" />
      {trends.map((t, i) => (
        <circle key={t.date} cx={i * step} cy={H - (t.count / max) * (H - 8) - 4} r="2.5" fill="#f59e0b" />
      ))}
    </svg>
  );
}

export default function H5WrongBookPage() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: SLATE[400] }}>
          <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载中…
        </div>
      }
    >
      <WrongBookContent />
    </Suspense>
  );
}
