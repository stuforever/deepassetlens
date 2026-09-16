/**
 * 背诵默写（M25 三年级上批次 T12）：桌面第 11 tab——原仓
 * app/(workspace)/self-learning/components/tabs/ReciteTab.tsx 1:1 移植。
 * 等价替换：删除 "use client"；apiFetch/apiUrl → 原生 fetch('/api/v1/...')；
 * react-i18next t() → 中文直出（取 locales/zh/app.json 原译文；"Recite" 键
 * zh/en 词表均缺，i18next 缺键回退显示原键，原 zh UI 实际显示即 "Recite"）；
 * lucide（BookOpen/Loader2/Mic/PencilLine/RotateCcw）→ @ant-design/icons
 * （ReadOutlined/LoadingOutlined/AudioOutlined/EditOutlined/UndoOutlined）；
 * Tailwind → 内联样式逐项对位（shadcn token 取原仓 globals.css 默认 :root 主题：
 * primary #b0501e / primary-foreground #fff / muted #f1ede2 / muted-foreground
 * #6d645a / accent #ece7d8 / 默认 border #e5e7eb）；hover:bg-* 伪类 →
 * onMouseEnter/Leave 内联置色（批8 同口径）；segmentClass 五类着色类串 →
 * SEG_STYLE 对照表（取值=原类名对应 tailwind 调色板色值）。逻辑/端点/testid
 * 零改动，data-testid 全部保留。
 *
 * 四步状态机（规格 §4.6）：material → mode → answer → result。
 * - 背诵(recite)含 语音/打字 两种输入；默写(dictation)仅打字。
 * - 默认逐段作答；材料归一化文本 >500 字强制逐段（整篇不可选）。
 * - 提交走 POST /recite/check（零 LLM 纯算法），结果视图按五类着色；
 *   recite-retry 只重背错段（验收判例 7）。
 * - STT 失败 → 就地重试提示，不判分（规格 §4.8）。
 * - 中途中断 → 已作答内容以 segmented=true partial 留档（调 attempts POST）。
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ReadOutlined,
  LoadingOutlined,
  AudioOutlined,
  EditOutlined,
  UndoOutlined,
} from "@ant-design/icons";
import { getH5User } from "../h5shared/h5Utils";
import { useVoiceRecorder } from "./useVoiceRecorder";
import {
  classifySegments,
  type DiffSegIn,
  type DiffCls,
} from "./reciteDiff";

type ReciteMode = "recite" | "dictation";
type InputMode = "voice" | "type";
type Step = "material" | "mode" | "answer" | "result";

interface ReciteSegment {
  idx: number;
  text: string;
  en?: string;
  zh?: string;
}

interface ReciteMaterial {
  id: string;
  subject: string;
  type: string;
  title: string;
  subtitle?: string;
  chapter_ids: string[];
  segments: ReciteSegment[];
  ocr_sourced?: boolean;
}

interface CheckResult {
  per_segment: { idx: number; score: number; diff: {
    wrong_chars: string[]; homophones: string[]; missing: string[]; extra: string[];
  } }[];
  total_score: number;
  wrong_chars: string[];
  homophones: string[];
}

/** 整篇作答的长度上限：超过则强制逐段（规格 §4.6）。 */
const WHOLE_MODE_MAX_CHARS = 500;

/**
 * 五类着色内联对照表（= 原仓 segmentClass 返回的 tailwind 类三元组取色：
 * ok 绿 / wrong 红 / homophone 黄 / missing 灰 / extra 蓝）。
 */
const SEG_STYLE: Record<DiffCls, { border: string; background: string; color: string }> = {
  ok: { border: "#86efac", background: "#f0fdf4", color: "#15803d" },
  wrong: { border: "#fca5a5", background: "#fef2f2", color: "#dc2626" },
  homophone: { border: "#fcd34d", background: "#fffbeb", color: "#d97706" },
  missing: { border: "#cbd5e1", background: "#f8fafc", color: "#475569" },
  extra: { border: "#93c5fd", background: "#eff6ff", color: "#2563eb" },
};

/** hover 背景的行内样式等价实现（Tailwind hover:bg-* 无法用纯内联样式表达）；离开时还原底色。 */
function hoverBg(base: string | undefined, hover: string) {
  return {
    onMouseEnter: (e: React.MouseEvent<HTMLElement>) => {
      e.currentTarget.style.background = hover;
    },
    onMouseLeave: (e: React.MouseEvent<HTMLElement>) => {
      e.currentTarget.style.background = base || "";
    },
  };
}

export function ReciteTab({ textbookId, chapterId, chapterName }: {
  textbookId: string;
  chapterId: string;
  chapterName: string;
}) {
  const [step, setStep] = useState<Step>("material");
  const [materials, setMaterials] = useState<ReciteMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [material, setMaterial] = useState<ReciteMaterial | null>(null);
  const [mode, setMode] = useState<ReciteMode>("recite");
  const [inputMode, setInputMode] = useState<InputMode>("type");
  const [scope, setScope] = useState<"segment" | "whole">("segment");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [wholeText, setWholeText] = useState("");
  const [segCursor, setSegCursor] = useState(0);
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);

  const answerSegs = material?.segments ?? [];
  const totalChars = answerSegs.reduce((n, s) => n + s.text.length, 0);
  const wholeAllowed = totalChars <= WHOLE_MODE_MAX_CHARS;

  const loadMaterials = useCallback(() => {
    setLoading(true);
    const u = getH5User();
    const qs = `textbook_id=${encodeURIComponent(textbookId)}&chapter_id=${encodeURIComponent(chapterId)}${u ? `&u=${encodeURIComponent(u)}` : ""}`;
    fetch(`/api/v1/self-learning/recite/materials?${qs}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setMaterials(d.items || []))
      .catch(() => setMaterials([]))
      .finally(() => setLoading(false));
  }, [chapterId, textbookId]);

  useEffect(() => { loadMaterials(); }, [loadMaterials]);

  // ---- partial 留档（中途中断）：已作答内容 segmented=true 入库 ----
  const answersRef = useRef(answers);
  answersRef.current = answers;
  const ctxRef = useRef({ material, mode, inputMode, chapterId, textbookId, step });
  ctxRef.current = { material, mode, inputMode, chapterId, textbookId, step };

  const archivePartial = useCallback(() => {
    const { material: m, mode: md, inputMode: im, chapterId: cid, textbookId: tid, step: st } = ctxRef.current;
    const answered = Object.entries(answersRef.current)
      .filter(([, text]) => text.trim())
      .map(([idx, text]) => ({ idx: Number(idx), text }));
    if (!m || st !== "answer" || answered.length === 0) return;
    const u = getH5User();
    const body = JSON.stringify({
      textbook_id: tid, chapter_id: cid, material_id: m.id,
      material_title: m.title, mode: md, input_mode: im,
      segmented: true, total_score: 0,
      per_segment: answered, wrong_chars: [], homophones: [],
    });
    try {
      // keepalive：页面卸载途中最尽力送达；失败静默（留档是 best-effort）。
      void fetch("/api/v1/self-learning/recite/attempts", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body, keepalive: true,
      });
    } catch { /* best-effort */ }
  }, []);

  useEffect(() => {
    return () => archivePartial();
  }, [archivePartial]);

  // ---- 录音：单 hook 实例，transcript 回填当前游标段 ----
  const segCursorRef = useRef(segCursor);
  segCursorRef.current = segCursor;
  const onTranscript = useCallback((text: string) => {
    const idx = answerSegs[segCursorRef.current]?.idx;
    if (idx === undefined) return;
    setAnswers((prev) => ({ ...prev, [idx]: text }));
  }, [answerSegs]);
  const recorder = useVoiceRecorder(onTranscript);

  const startAnswer = (m: ReciteMaterial, md: ReciteMode, im: InputMode, sc: "segment" | "whole") => {
    setMaterial(m); setMode(md); setInputMode(md === "dictation" ? "type" : im);
    setScope(sc); setAnswers({}); setWholeText(""); setSegCursor(0);
    setResult(null); setStep("answer");
  };

  const submit = useCallback(async () => {
    if (!material) return;
    setChecking(true);
    // 审查 R1-必修2 契约：整篇送 whole_text（参考=全部段拼接），逐段送 segments
    const segments = scope === "whole"
      ? []
      : answerSegs.map((s) => ({ idx: s.idx, text: answers[s.idx] || "" }));
    const u = getH5User();
    try {
      const resp = await fetch(`/api/v1/self-learning/recite/check${u ? `?u=${encodeURIComponent(u)}` : ""}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          material_id: material.id, mode, input_mode: inputMode, segments,
          ...(scope === "whole" ? { whole_text: wholeText } : {}),
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = (await resp.json()) as CheckResult;
      setResult(data);
      setStep("result");
      // 判例 9：完整判分后留档（成绩进学情 tab/H5 报告；不进 FSRS 复习队列）
      void fetch(`/api/v1/self-learning/recite/attempts${u ? `?u=${encodeURIComponent(u)}` : ""}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          textbook_id: textbookId, chapter_id: chapterId,
          material_id: material.id, material_title: material.title,
          mode, input_mode: inputMode, segmented: false,
          total_score: data.total_score,
          per_segment: data.per_segment, wrong_chars: data.wrong_chars,
          homophones: data.homophones,
        }),
      }).catch(() => { /* 留档 best-effort */ });
    } catch { /* 提交失败留在作答步，用户可重试提交 */ }
    finally { setChecking(false); }
  }, [answerSegs, answers, chapterId, inputMode, material, mode, scope, textbookId, wholeText]);

  // ---- 结果视图：五类着色分类（T14 recite-diff 纯函数统一映射） ----
  const diffSegs = (d: CheckResult["per_segment"][number]["diff"]): DiffSegIn[] => [
    ...d.wrong_chars.map((ch) => ({ type: "wrong" as const, text: ch })),
    ...d.homophones.map((ch) => ({ type: "homophone" as const, text: ch })),
    ...d.missing.map((ch) => ({ type: "missing" as const, text: ch })),
    ...d.extra.map((ch) => ({ type: "extra" as const, text: ch })),
  ];
  // 段卡片基调 = 最严重类（wrong > homophone > missing > extra > ok）——
  // 原仓取 segmentClass(...).split(" ").slice(0, 2)（边框+底色），此处同口径。
  const diffTone = (d: CheckResult["per_segment"][number]["diff"]) => {
    const tone: DiffCls = d.wrong_chars.length
      ? "wrong"
      : d.homophones.length
        ? "homophone"
        : d.missing.length
          ? "missing"
          : d.extra.length
            ? "extra"
            : "ok";
    const st = SEG_STYLE[tone];
    return { border: `1px solid ${st.border}`, background: st.background };
  };
  const diffLabel: Record<string, string> = {
    wrong: "错字", homophone: "同音", missing: "漏字", extra: "多字",
  };

  const retryWrongOnly = () => {
    if (!material || !result) return;
    const wrongIdx = new Set(
      result.per_segment.filter((p) => p.diff.wrong_chars.length || p.diff.homophones.length).map((p) => p.idx),
    );
    if (!wrongIdx.size) { setStep("material"); return; }
    if (scope === "whole") {
      // 整篇：单卡判定 → 重背即清空整篇作答
      setWholeText("");
      setResult(null); setStep("answer");
      return;
    }
    setAnswers(Object.fromEntries(answerSegs.filter((s) => wrongIdx.has(s.idx)).map((s) => [s.idx, ""])));
    setSegCursor(answerSegs.findIndex((s) => wrongIdx.has(s.idx)));
    setResult(null); setStep("answer");
  };

  // ================= 渲染 =================
  if (loading) {
    return (
      <div
        style={{ padding: 32, display: "flex", alignItems: "center", justifyContent: "center", color: "#6d645a" }}
        data-testid="tab-panel-recite"
      >
        <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载中…
      </div>
    );
  }

  // ---- 步 4：结果 ----
  if (step === "result" && material && result) {
    return (
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }} data-testid="tab-panel-recite">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontWeight: 500 }}>{material.title}</div>
          <div style={{ fontSize: 18, fontWeight: 600 }} data-testid="recite-score">
            得分: {Math.round(result.total_score * 100)}%
          </div>
        </div>
        {result.per_segment.map((p) => (
          <div key={p.idx} style={{ padding: 12, borderRadius: 4, ...diffTone(p.diff) }} data-testid={`recite-diff-seg-${p.idx}`}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 14 }}>
              <span style={{ fontWeight: 500 }}>段落 {p.idx + 1}</span>
              <span>{Math.round(p.score * 100)}%</span>
            </div>
            {/* 原仓 text-sm space-x-3 mt-1：inline span 流式排布（自然换行），仅底色+字色（类串无 border 宽度类，故无描边） */}
            <div style={{ fontSize: 14, marginTop: 4 }}>
              {(() => {
                const chips = classifySegments(diffSegs(p.diff));
                if (chips.length === 0) {
                  return <span style={{ color: SEG_STYLE.ok.color }}>全部正确</span>;
                }
                return chips.map((c, i) => (
                  <span
                    key={i}
                    style={{
                      background: SEG_STYLE[c.cls].background,
                      color: SEG_STYLE[c.cls].color,
                      marginLeft: i > 0 ? 12 : undefined,
                    }}
                    data-chip={c.cls}
                  >
                    {diffLabel[c.cls]}: {c.text}
                  </span>
                ));
              })()}
            </div>
          </div>
        ))}
        <div style={{ display: "flex", gap: 8, paddingTop: 4 }}>
          {(result.wrong_chars.length > 0 || result.homophones.length > 0) && (
            <button
              onClick={retryWrongOnly}
              data-testid="recite-retry"
              style={{
                padding: "6px 12px", fontSize: 14, borderRadius: 4, border: "1px solid #e5e7eb",
                background: "#fffbeb", color: "inherit", cursor: "pointer",
                display: "inline-flex", alignItems: "center", gap: 4,
              }}
              {...hoverBg("#fffbeb", "#fef3c7")}
            >
              <UndoOutlined style={{ fontSize: 16 }} /> 再试一次（只重背错段）
            </button>
          )}
          <button
            onClick={() => { setStep("material"); setMaterial(null); setResult(null); }}
            data-testid="recite-back-materials"
            style={{
              padding: "6px 12px", fontSize: 14, borderRadius: 4, border: "1px solid #e5e7eb",
              background: "transparent", color: "inherit", cursor: "pointer",
            }}
            {...hoverBg(undefined, "#ece7d8")}
          >
            返回素材列表
          </button>
        </div>
      </div>
    );
  }

  // ---- 步 3：作答 ----
  if (step === "answer" && material) {
    const seg = answerSegs[segCursor];
    const showRef = mode === "recite"; // 默写隐藏原文
    const last = scope === "whole" || segCursor >= answerSegs.length - 1;
    return (
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }} data-testid="tab-panel-recite">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 14 }}>
          <div style={{ fontWeight: 500 }}>{material.title}</div>
          {scope === "segment" && (
            <div style={{ color: "#6d645a" }}>
              {segCursor + 1} / {answerSegs.length}
            </div>
          )}
        </div>
        {scope === "whole" ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }} data-testid="recite-answer-whole">
            {showRef && (
              <div style={{ padding: 12, borderRadius: 4, border: "1px solid #e5e7eb", background: "rgba(241,237,226,0.4)", fontSize: 14, whiteSpace: "pre-wrap" }}>
                {answerSegs.map((s) => s.text).join("\n")}
              </div>
            )}
            <textarea
              data-testid="recite-answer-whole-text"
              style={{ width: "100%", minHeight: 160, padding: 8, borderRadius: 4, border: "1px solid #e5e7eb", fontSize: 14, boxSizing: "border-box" }}
              placeholder="凭记忆默写整篇"
              value={wholeText}
              onChange={(e) => setWholeText(e.target.value)}
            />
          </div>
        ) : (
          seg && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }} data-testid={`recite-answer-seg-${seg.idx}`}>
              {showRef ? (
                <div style={{ padding: 12, borderRadius: 4, border: "1px solid #e5e7eb", background: "rgba(241,237,226,0.4)", fontSize: 14, whiteSpace: "pre-wrap" }}>
                  {seg.text}
                </div>
              ) : (
                <div style={{ padding: 12, borderRadius: 4, border: "1px solid #e5e7eb", background: "rgba(241,237,226,0.4)", fontSize: 14, color: "#6d645a" }}>
                  {seg.zh ? seg.zh : `段落 ${seg.idx + 1}`}
                </div>
              )}
              <textarea
                data-testid={`recite-answer-text-${seg.idx}`}
                style={{ width: "100%", minHeight: 96, padding: 8, borderRadius: 4, border: "1px solid #e5e7eb", fontSize: 14, boxSizing: "border-box" }}
                placeholder="输入你记得的内容"
                value={answers[seg.idx] || ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [seg.idx]: e.target.value }))}
              />
              {inputMode === "voice" && (
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <button
                    onClick={recorder.toggle}
                    disabled={recorder.state === "transcribing"}
                    data-testid={`recite-answer-voice-${seg.idx}`}
                    style={{
                      padding: "6px 12px", fontSize: 14, borderRadius: 4,
                      border: recorder.state === "recording" ? "1px solid #fca5a5" : "1px solid #e5e7eb",
                      background: recorder.state === "recording" ? "#fef2f2" : "transparent",
                      color: recorder.state === "recording" ? "#dc2626" : "inherit",
                      cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4,
                      opacity: recorder.state === "transcribing" ? 0.5 : undefined,
                    }}
                    {...(recorder.state === "recording" ? {} : hoverBg(undefined, "#ece7d8"))}
                  >
                    <AudioOutlined style={{ fontSize: 16 }} />
                    {recorder.state === "recording" ? "松开结束"
                      : recorder.state === "transcribing" ? "识别中…" : "按住说话"}
                  </button>
                  {recorder.error && (
                    <span style={{ fontSize: 14, color: "#dc2626" }} data-testid="recite-stt-error">
                      识别失败，请重试{recorder.error ? `: ${recorder.error}` : ""}
                    </span>
                  )}
                </div>
              )}
            </div>
          )
        )}
        {scope === "segment" && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              disabled={segCursor === 0}
              onClick={() => setSegCursor((c) => Math.max(0, c - 1))}
              data-testid="recite-seg-prev"
              style={{
                padding: "6px 12px", fontSize: 14, borderRadius: 4, border: "1px solid #e5e7eb",
                background: "transparent", color: "inherit", cursor: "pointer",
                opacity: segCursor === 0 ? 0.4 : undefined,
              }}
              {...hoverBg(undefined, "#ece7d8")}
            >
              上一题
            </button>
            <button
              disabled={last}
              onClick={() => setSegCursor((c) => Math.min(answerSegs.length - 1, c + 1))}
              data-testid="recite-seg-next"
              style={{
                padding: "6px 12px", fontSize: 14, borderRadius: 4, border: "1px solid #e5e7eb",
                background: "transparent", color: "inherit", cursor: "pointer",
                opacity: last ? 0.4 : undefined,
              }}
              {...hoverBg(undefined, "#ece7d8")}
            >
              下一个
            </button>
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 4 }}>
          <button
            onClick={submit}
            disabled={checking}
            data-testid="recite-submit"
            style={{
              padding: "6px 16px", fontSize: 14, borderRadius: 4, border: "none",
              background: "#b0501e", color: "#ffffff", cursor: "pointer",
              display: "inline-flex", alignItems: "center", gap: 4,
              opacity: checking ? 0.5 : undefined,
            }}
            {...hoverBg("#b0501e", "rgba(176,80,30,0.9)")}
          >
            {checking && <LoadingOutlined style={{ fontSize: 16 }} spin />} 提交
          </button>
          <button
            onClick={() => { archivePartial(); setStep("material"); setMaterial(null); }}
            data-testid="recite-exit"
            style={{
              padding: "6px 12px", fontSize: 14, borderRadius: 4, border: "1px solid #e5e7eb",
              background: "transparent", color: "inherit", cursor: "pointer",
            }}
            {...hoverBg(undefined, "#ece7d8")}
          >
            退出并保存进度
          </button>
        </div>
      </div>
    );
  }

  // ---- 步 2：模式选择 ----
  if (step === "mode" && material) {
    const forcedSegment = !wholeAllowed;
    return (
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }} data-testid="tab-panel-recite">
        <div style={{ fontWeight: 500 }}>{material.title}</div>
        <div>
          <div style={{ fontSize: 14, color: "#6d645a", marginBottom: 4 }}>模式</div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setMode("recite")}
              data-testid="recite-mode-recite"
              style={{
                padding: "6px 12px", fontSize: 14, borderRadius: 4,
                border: mode === "recite" ? "1px solid #b0501e" : "1px solid #e5e7eb",
                background: mode === "recite" ? "rgba(176,80,30,0.05)" : "transparent",
                color: "inherit", cursor: "pointer",
              }}
              {...(mode === "recite" ? {} : hoverBg(undefined, "#ece7d8"))}
            >
              Recite
            </button>
            <button
              onClick={() => setMode("dictation")}
              data-testid="recite-mode-dictation"
              style={{
                padding: "6px 12px", fontSize: 14, borderRadius: 4,
                border: mode === "dictation" ? "1px solid #b0501e" : "1px solid #e5e7eb",
                background: mode === "dictation" ? "rgba(176,80,30,0.05)" : "transparent",
                color: "inherit", cursor: "pointer",
              }}
              {...(mode === "dictation" ? {} : hoverBg(undefined, "#ece7d8"))}
            >
              默写
            </button>
          </div>
        </div>
        {mode === "recite" && (
          <div>
            <div style={{ fontSize: 14, color: "#6d645a", marginBottom: 4 }}>输入方式</div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => setInputMode("voice")}
                data-testid="recite-input-voice"
                style={{
                  padding: "6px 12px", fontSize: 14, borderRadius: 4,
                  border: inputMode === "voice" ? "1px solid #b0501e" : "1px solid #e5e7eb",
                  background: inputMode === "voice" ? "rgba(176,80,30,0.05)" : "transparent",
                  color: "inherit", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4,
                }}
                {...(inputMode === "voice" ? {} : hoverBg(undefined, "#ece7d8"))}
              >
                <AudioOutlined style={{ fontSize: 16 }} /> 语音
              </button>
              <button
                onClick={() => setInputMode("type")}
                data-testid="recite-input-type"
                style={{
                  padding: "6px 12px", fontSize: 14, borderRadius: 4,
                  border: inputMode === "type" ? "1px solid #b0501e" : "1px solid #e5e7eb",
                  background: inputMode === "type" ? "rgba(176,80,30,0.05)" : "transparent",
                  color: "inherit", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4,
                }}
                {...(inputMode === "type" ? {} : hoverBg(undefined, "#ece7d8"))}
              >
                <EditOutlined style={{ fontSize: 16 }} /> 类型
              </button>
            </div>
          </div>
        )}
        <div>
          <div style={{ fontSize: 14, color: "#6d645a", marginBottom: 4 }}>范围</div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setScope("segment")}
              data-testid="recite-scope-segment"
              style={{
                padding: "6px 12px", fontSize: 14, borderRadius: 4,
                border: scope === "segment" ? "1px solid #b0501e" : "1px solid #e5e7eb",
                background: scope === "segment" ? "rgba(176,80,30,0.05)" : "transparent",
                color: "inherit", cursor: "pointer",
              }}
              {...(scope === "segment" ? {} : hoverBg(undefined, "#ece7d8"))}
            >
              逐段
            </button>
            <button
              onClick={() => wholeAllowed && setScope("whole")}
              disabled={forcedSegment}
              data-testid="recite-scope-whole"
              title={forcedSegment ? "素材过长，整篇模式不可用" : undefined}
              style={{
                padding: "6px 12px", fontSize: 14, borderRadius: 4,
                border: scope === "whole" ? "1px solid #b0501e" : "1px solid #e5e7eb",
                background: scope === "whole" ? "rgba(176,80,30,0.05)" : "transparent",
                color: "inherit",
                cursor: forcedSegment ? "not-allowed" : "pointer",
                opacity: forcedSegment ? 0.4 : undefined,
              }}
              {...(scope === "whole" || forcedSegment ? {} : hoverBg(undefined, "#ece7d8"))}
            >
              整篇
            </button>
          </div>
          {forcedSegment && (
            <div style={{ fontSize: 12, color: "#6d645a", marginTop: 4 }}>
              素材超过 500 字，仅支持逐段模式
            </div>
          )}
        </div>
        <button
          onClick={() => startAnswer(material, mode, inputMode, scope)}
          data-testid="recite-start"
          style={{
            alignSelf: "flex-start", padding: "6px 16px", fontSize: 14, borderRadius: 4,
            border: "none", background: "#b0501e", color: "#ffffff", cursor: "pointer",
          }}
          {...hoverBg("#b0501e", "rgba(176,80,30,0.9)")}
        >
          开始
        </button>
      </div>
    );
  }

  // ---- 步 1：材料选择 ----
  return (
    <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }} data-testid="tab-panel-recite">
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "#6d645a" }}>
        <ReadOutlined style={{ fontSize: 16, color: "#b0501e" }} />
        {chapterName}
      </div>
      {materials.length === 0 ? (
        <div style={{ fontSize: 14, color: "#6d645a" }} data-testid="recite-materials-empty">
          本章节暂无背诵素材
        </div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {materials.map((m) => (
            <button
              key={m.id}
              onClick={() => { setMaterial(m); setStep("mode"); }}
              data-testid={`recite-material-${m.id}`}
              style={{
                textAlign: "left", padding: 12, borderRadius: 4, border: "1px solid #e5e7eb",
                background: "transparent", color: "inherit", cursor: "pointer",
              }}
              {...hoverBg(undefined, "#ece7d8")}
            >
              <div style={{ fontSize: 14, fontWeight: 500 }}>{m.title}</div>
              {m.subtitle && <div style={{ fontSize: 12, color: "#6d645a" }}>{m.subtitle}</div>}
              <div style={{ fontSize: 12, color: "#6d645a", marginTop: 2 }}>
                分段: {m.segments.length}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
