/**
 * H5 自包含拍错题页（design: H5 自包含闭环，不跳桌面）
 * ——原仓 app/h5/wrong/page.tsx 1:1 移植。
 *
 * 等价替换（与批8 F1 约定一致）：
 *  - next/navigation useSearchParams → react-router-dom useSearchParams；next/link → react-router Link；
 *  - 路由前缀映射：原 /h5/* → tupu /e/tutor/h5/*；
 *  - fetch(apiUrl(...)) / fetch(backendUrl(...)) → fetch('/api/v1/...') 逐字
 *    （原仓两函数均为 pass-through；tupu 由 setupProxy 统一转发 28000，直连/代理语义合一）；
 *  - lucide-react → @ant-design/icons 语义就近（Loader2→LoadingOutlined、Volume2 类比、
 *    Sparkles→ThunderboltOutlined、Trash2→DeleteOutlined、CheckCircle2→CheckCircleOutlined、
 *    XCircle→CloseCircleOutlined、BookMarked→BookOutlined、ChevronDown→DownOutlined、Camera→CameraOutlined）；
 *  - Tailwind → antd+内联样式逐项对位（active:/hover: 伪类内联不可表达，随 h5shared 先例略去）；
 *  - readLastChapter（原 @/lib/h5-learn-memory）→ h5shared/h5LearnMemory（SA-B 移植件）；
 *  - window.alert/alert 原样保留（中文文案逐字）。
 *
 * 拍照/选图 → OCR 识别题目 → AI 讲解（知识点/分步/易错点）
 * → 一键存入错题本（POST /mother-questions）。
 * 用户标识 u 透传（?u=小明）。
 */
import { useState, useCallback, useRef, useEffect, Suspense } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  CameraOutlined,
  DownOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  DeleteOutlined,
  BookOutlined,
} from "@ant-design/icons";
import { readLastChapter } from "./h5shared/h5LearnMemory";
import { withU } from "./h5shared/h5Utils";
import { H5Shell } from "./h5shared/H5Shell";
import { H5PageHeader } from "./h5shared/H5PageHeader";

const SLATE = {
  100: "#f1f5f9", 200: "#e2e8f0", 300: "#cbd5e1", 400: "#94a3b8",
  500: "#64748b", 600: "#475569", 700: "#334155",
};
const BTN_BASE: React.CSSProperties = { border: "none", cursor: "pointer", background: "none", padding: 0, fontFamily: "inherit" };

function H5WrongContent() {
  // react-router useSearchParams 返回元组（next/navigation 返回 URLSearchParams 实例）——等价解构
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const fileRef = useRef<HTMLInputElement>(null);

  const [imagePreview, setImagePreview] = useState<string>("");
  const [imageBase64, setImageBase64] = useState<string>("");
  const [questionText, setQuestionText] = useState<string>("");
  const [phase, setPhase] = useState<"idle" | "asking" | "done" | "error">("idle");
  const [answer, setAnswer] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  // U7（第六篇）：连拍模式（存错题后自动回拍照态）+ 已拍计数
  const [quickPhoto, setQuickPhoto] = useState(false);
  const [shotCount, setShotCount] = useState(0);
  // W3（第八篇 M16-B）：拍照错题章节归属——两级下拉（数据源 /dict），批量共用一次选择
  const [dictData, setDictData] = useState<{ textbooks: any[]; chapters: any[] } | null>(null);
  const [selTextbook, setSelTextbook] = useState("");
  const [selChapter, setSelChapter] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);

  const openPicker = async () => {
    setPickerOpen((v) => !v);
    if (!dictData) {
      try {
        const res = await fetch("/api/v1/mother-questions/dict");
        const data = await res.json();
        setDictData(data);
        // S5（M23-E）：预填当前学习章节（拍当前章的题少点一次）
        const last = readLastChapter(u || "");
        if (last?.chapter_id && Array.isArray(data.chapters)) {
          const ch = data.chapters.find((c: any) => c.id === last.chapter_id);
          if (ch) {
            setSelTextbook(ch.textbook_id || "");
            setSelChapter(ch.id);
          }
        }
      } catch {
        /* ignore */
      }
    }
  };

  useEffect(() => {
    try {
      setQuickPhoto(localStorage.getItem("h5_quick_photo") === "1");
    } catch {
      /* ignore */
    }
  }, []);

  const toggleQuickPhoto = (v: boolean) => {
    setQuickPhoto(v);
    try {
      localStorage.setItem("h5_quick_photo", v ? "1" : "0");
    } catch {
      /* ignore */
    }
  };

  // 清空当前拍照态回拍照（保留 saved toast 确认）
  const resetPhoto = () => {
    setImagePreview("");
    setImageBase64("");
    setQuestionText("");
    setAnswer("");
    setPhase("idle");
    setShotCount((c) => c + 1);
  };

  const onFile = useCallback((file: File | null) => {
    if (!file) return;
    setSaved(false);
    setPhase("idle");
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setImagePreview(dataUrl);
      // strip data-url prefix -> raw base64
      const comma = dataUrl.indexOf(",");
      setImageBase64(dataUrl.slice(comma + 1));
    };
    reader.readAsDataURL(file);
  }, []);

  const ask = async () => {
    if (!imageBase64 && !questionText.trim()) {
      setErrorMsg("请先拍照或输入题目文字");
      setPhase("error");
      return;
    }
    setPhase("asking");
    setErrorMsg("");
    setAnswer("");
    try {
      // P9 门禁③：LLM 讲解实测 25-50s，apiUrl 代理有 30s 硬超时（500）——
      // 按 lib/api.ts 长耗时端点规约改 backendUrl() 直连（拍照录入先例）。
      // tupu：backendUrl() 在原仓同为 pass-through，此处按约定 #2 内联为相对路径，
      // 由 setupProxy 转发 28000（无独立 30s 代理超时）。
      const res = await fetch("/api/v1/learning/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: questionText,
          u: u || undefined,
          image_base64: imageBase64,
        }),
      });
      // 非 JSON 500 体（如代理/网关纯文本）容错：先读文本再 try parse
      const raw = await res.text();
      let data: any = {};
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        data = { ok: false, msg: raw.slice(0, 200) || `HTTP ${res.status}` };
      }
      if (!res.ok || !data.ok) {
        setErrorMsg(data.msg || "答疑失败，请稍后再试");
        setPhase("error");
        return;
      }
      setAnswer(data.answer || "");
      setPhase("done");
    } catch (e: any) {
      setErrorMsg(e?.message || "网络错误，请重试");
      setPhase("error");
    }
  };

  const saveToWrongBook = async () => {
    if (!answer && !imagePreview) return;
    setSaving(true);
    try {
      const title = questionText.trim().slice(0, 20) || "H5 拍照错题";
      const qs = u ? `?u=${encodeURIComponent(u)}` : "";
      const res = await fetch(`/api/v1/mother-questions${qs}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          question_text: questionText.trim() || title,
          detailed_analysis: answer,
          photo_url: imagePreview || "",
          ocr_text: questionText.trim(),
          chapter_id: selChapter || undefined, // W3：拍照错题章节归属
          tags: ["h5", "src:photo", ...(u ? [`u:${u}`] : [])],
          subject: "math",
        }),
      });
      setSaving(false);
      if (res.ok) {
        setSaved(true);
        // U7：连拍模式——存错题后自动回拍照态，拍下一题（保留已存确认）
        if (quickPhoto) resetPhoto();
      } else {
        const data = await res.json().catch(() => ({}));
        setErrorMsg(data.detail || "存入错题本失败");
        setPhase("error");
      }
    } catch (e: any) {
      setSaving(false);
      setErrorMsg(e?.message || "网络错误，请重试");
      setPhase("error");
    }
  };

  // F7（M14-C）：相册批量拍题——多选 -> batch_recognize OCR -> 逐张入库 -> 汇总
  const [batchProcessing, setBatchProcessing] = useState(false);

  const batchImport = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBatchProcessing(true);
    const qs = u ? `?u=${encodeURIComponent(u)}` : "";
    try {
      const fd = new FormData();
      for (const f of Array.from(files)) fd.append("files", f);
      const recRes = await fetch(
        `/api/v1/mother-questions/batch_recognize${qs}`,
        { method: "POST", body: fd },
      );
      const recData = await recRes.json();
      const items: any[] = recData.items || [];
      let saved = 0;
      let skipped = 0;
      for (const it of items) {
        const text = (it.text || "").trim();
        if (!it.ok || !text) {
          skipped++;
          continue;
        }
        const title = text.slice(0, 20) || "H5 批量错题";
        const res = await fetch(`/api/v1/mother-questions${qs}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title,
            question_text: text,
            ocr_text: text,
            chapter_id: selChapter || undefined, // W3：批量共用一次章节选择
            tags: ["h5", "batch", "src:photo", ...(u ? [`u:${u}`] : [])],
            subject: "math",
          }),
        });
        if (res.ok) saved++;
        else skipped++;
      }
      alert(`📖 识别 ${items.length} 张，入库 ${saved} 题${skipped ? `，跳过 ${skipped} 张` : ""}`);
    } catch (e: any) {
      alert("批量识别失败：" + (e?.message || "网络错误"));
    } finally {
      setBatchProcessing(false);
    }
  };

  return (
    <H5Shell active="wrongbook">
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(to right, #f43f5e, #db2777)", color: "#fff", padding: 16, borderBottomLeftRadius: 24, borderBottomRightRadius: 24 }}>
        <H5PageHeader title="📷 拍错题" />
        <div style={{ marginTop: 8, fontSize: 14, color: "#ffe4e6" }}>拍一道题，AI 帮你识别并讲解，还能存入错题本</div>
      </div>

      <div style={{ padding: "0 16px", marginTop: 16, display: "flex", flexDirection: "column", gap: 16 }}>
        {/* 拍照区 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06)", border: `1px solid ${SLATE[200]}`, padding: 16 }}>
          {/* U7：连拍模式开关（localStorage 记忆） */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 14, color: SLATE[600] }}>📸 连拍模式</span>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: SLATE[400] }}>
              存错题后自动拍下一题
              <input
                type="checkbox"
                checked={quickPhoto}
                onChange={(e) => toggleQuickPhoto(e.target.checked)}
                style={{ accentColor: "#f43f5e", width: 20, height: 20 }}
              />
            </label>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: "none" }}
            onChange={(e) => onFile(e.target.files?.[0] || null)}
          />
          {/* F7（M14-C）：相册批量——多选图片批量 OCR 入库 */}
          <label
            style={{
              marginTop: 8, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, width: "100%",
              padding: "10px 0", borderRadius: 12, border: "2px dashed #fecdd3", color: "#f43f5e",
              fontSize: 14, fontWeight: 500, transition: "all .15s",
              ...(batchProcessing ? { opacity: 0.6, pointerEvents: "none" as const } : { cursor: "pointer" }),
            }}
          >
            {batchProcessing ? (
              <>
                <LoadingOutlined style={{ fontSize: 16 }} spin /> 批量识别中…
              </>
            ) : (
              <>
                <CameraOutlined style={{ fontSize: 16 }} /> 🖼️ 相册批量（一次选多张）
              </>
            )}
            <input
              type="file"
              accept="image/*"
              multiple
              style={{ display: "none" }}
              disabled={batchProcessing}
              onChange={(e) => {
                void batchImport(e.target.files);
                e.target.value = "";
              }}
            />
          </label>
          {imagePreview ? (
            <div style={{ position: "relative" }}>
              <img src={imagePreview} alt="题目照片" style={{ width: "100%", borderRadius: 12, border: `1px solid ${SLATE[200]}`, maxHeight: 288, objectFit: "contain", background: SLATE[100], display: "block" }} />
              <button
                onClick={() => {
                  setImagePreview("");
                  setImageBase64("");
                  setAnswer("");
                  setPhase("idle");
                  setSaved(false);
                }}
                style={{ ...BTN_BASE, position: "absolute", top: 8, right: 8, padding: 6, borderRadius: 9999, background: "rgba(0,0,0,0.5)", color: "#fff" }}
              >
                <DeleteOutlined style={{ fontSize: 16 }} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => fileRef.current?.click()}
              style={{ ...BTN_BASE, width: "100%", padding: "40px 0", borderRadius: 12, border: "2px dashed #fecdd3", display: "flex", flexDirection: "column", alignItems: "center", color: SLATE[400], transition: "all .15s" }}
            >
              <CameraOutlined style={{ fontSize: 40, color: "#fb7185", marginBottom: 8 }} />
              <span style={{ fontSize: 14 }}>{shotCount > 0 ? "继续拍下一题" : "点击拍照 / 从相册选题目照片"}</span>
            </button>
          )}
        </div>

        {/* 题目文字（可编辑） */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06)", border: `1px solid ${SLATE[200]}`, padding: 16 }}>
          <h3 style={{ fontWeight: 600, fontSize: 14, marginBottom: 8, margin: "0 0 8px" }}>✏️ 题目文字（可手动修改）</h3>
          <textarea
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="AI 会从照片识别；也可直接输入题目"
            style={{ width: "100%", boxSizing: "border-box", minHeight: 80, padding: "8px 12px", borderRadius: 12, border: `1px solid #e5e7eb`, fontSize: 14, background: "transparent", resize: "vertical" }}
          />
          <button
            onClick={ask}
            disabled={phase === "asking" || saving}
            style={{ ...BTN_BASE, marginTop: 12, width: "100%", padding: "12px 0", borderRadius: 12, background: "linear-gradient(to right, #f43f5e, #db2777)", color: "#fff", fontWeight: 500, boxShadow: "0 1px 2px rgba(0,0,0,.1)", opacity: phase === "asking" || saving ? 0.6 : 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
          >
            {phase === "asking" ? (
              <>
                <LoadingOutlined style={{ fontSize: 16 }} spin /> AI 正在讲解…
              </>
            ) : (
              <>
                <ThunderboltOutlined style={{ fontSize: 16 }} /> 立即讲解
              </>
            )}
          </button>
          {/* F4（M14-B）：深度解题——带题目文字直达 /h5/chat?capability=deep_solve */}
          <Link
            to={
              questionText.trim()
                ? withU(`/e/tutor/h5/chat?capability=deep_solve&text=${encodeURIComponent(questionText.trim())}`, u)
                : withU("/e/tutor/h5/chat?capability=deep_solve", u)
            }
            style={{ marginTop: 8, width: "100%", padding: "12px 0", borderRadius: 12, border: "2px solid #7dd3fc", background: "#f0f9ff", color: "#0369a1", fontWeight: 500, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, textDecoration: "none" }}
          >
            <ThunderboltOutlined style={{ fontSize: 16 }} /> 深度解题（多步推理）
          </Link>
        </div>

        {/* 讲解结果 */}
        {phase === "done" && answer && (
          <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06)", border: `1px solid ${SLATE[200]}`, padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <CheckCircleOutlined style={{ fontSize: 16, color: "#10b981" }} />
              <h3 style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>🧠 AI 讲解</h3>
            </div>
            <pre style={{ fontSize: 14, whiteSpace: "pre-wrap", lineHeight: 1.625, color: SLATE[700], fontFamily: "inherit", margin: 0 }}>{answer}</pre>
            {/* W3（第八篇 M16-B）：归属章节（可选）——两级下拉，拍照错题进章节错题 Tab */}
            <div style={{ marginTop: 12 }}>
              <button
                onClick={() => void openPicker()}
                style={{ ...BTN_BASE, width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 12, border: `1px solid ${SLATE[200]}`, fontSize: 14, color: SLATE[600] }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                  <BookOutlined style={{ fontSize: 14, color: SLATE[400], flexShrink: 0 }} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {(() => {
                      const tb = dictData?.textbooks.find((x) => x.id === selTextbook);
                      const ch = dictData?.chapters.find((x) => x.id === selChapter);
                      return selChapter && ch
                        ? `📍 ${tb?.name || ""} · ${ch.name}`
                        : "📍 归属章节（可选，用于章节错题联动）";
                    })()}
                  </span>
                </span>
                <DownOutlined style={{ fontSize: 16, flexShrink: 0, transition: "all .15s", transform: pickerOpen ? "rotate(180deg)" : "none" }} />
              </button>
              {pickerOpen && dictData && (
                <div style={{ marginTop: 8, maxHeight: 224, overflowY: "auto", borderRadius: 12, border: `1px solid ${SLATE[200]}`, background: "#fff" }}>
                  {!selTextbook ? (
                    <div style={{ padding: 6, display: "flex", flexDirection: "column", gap: 2 }}>
                      {dictData.textbooks.map((tb) => (
                        <button
                          key={tb.id}
                          onClick={() => {
                            setSelTextbook(tb.id);
                            setSelChapter("");
                          }}
                          style={{ ...BTN_BASE, width: "100%", textAlign: "left", padding: "8px 12px", borderRadius: 4, fontSize: 14, color: "inherit" }}
                        >
                          {tb.name}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div style={{ padding: 6, display: "flex", flexDirection: "column", gap: 2 }}>
                      <button
                        onClick={() => setSelTextbook("")}
                        style={{ ...BTN_BASE, width: "100%", textAlign: "left", padding: "6px 12px", borderRadius: 4, fontSize: 12, color: "#4f46e5" }}
                      >
                        ← 换教材（{dictData.textbooks.find((x) => x.id === selTextbook)?.name || ""}）
                      </button>
                      {dictData.chapters
                        .filter((c) => c.textbook_id === selTextbook && !c.parent_id)
                        .map((ch) => {
                          const kids = dictData.chapters.filter((c) => c.parent_id === ch.id);
                          return (
                            <div key={ch.id} style={{ marginBottom: 4 }}>
                              <button
                                onClick={() => {
                                  setSelChapter(ch.id);
                                  setPickerOpen(false);
                                }}
                                style={{ ...BTN_BASE, width: "100%", textAlign: "left", padding: "8px 12px", borderRadius: 4, fontSize: 14, fontWeight: 500, color: "inherit" }}
                              >
                                {ch.name}
                              </button>
                              {kids.length > 0 && (
                                <div style={{ marginLeft: 12, display: "flex", flexDirection: "column", gap: 2, borderLeft: `1px solid ${SLATE[100]}`, paddingLeft: 8 }}>
                                  {kids.map((k) => (
                                    <button
                                      key={k.id}
                                      onClick={() => {
                                        setSelChapter(k.id);
                                        setPickerOpen(false);
                                      }}
                                      style={{ ...BTN_BASE, width: "100%", textAlign: "left", padding: "6px 8px", borderRadius: 4, fontSize: 12, color: SLATE[600] }}
                                    >
                                      {k.name}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
              <button
                onClick={saveToWrongBook}
                disabled={saving}
                style={{ ...BTN_BASE, flex: 1, padding: "12px 0", borderRadius: 12, background: "#10b981", color: "#fff", fontSize: 14, fontWeight: 500, opacity: saving ? 0.6 : 1 }}
              >
                {saving ? "保存中…" : saved ? "✅ 已存入错题本" : "存入错题本"}
              </button>
              {/* U7：再拍一题主按钮（44px 触点，保留已存 toast） */}
              <button
                onClick={resetPhoto}
                style={{ ...BTN_BASE, flex: 1, padding: "12px 0", borderRadius: 12, background: "#f43f5e", color: "#fff", fontSize: 14, fontWeight: 500 }}
              >
                📷 再拍一题
              </button>
            </div>
            {saved && (
              <p style={{ fontSize: 12, color: "#059669", marginTop: 8 }}>
                已存入错题本，FSRS 会安排到期复习；回到首页看「学情」掌握度变化。
              </p>
            )}
          </div>
        )}

        {/* 错误提示 */}
        {phase === "error" && errorMsg && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: 12, borderRadius: 16, border: "1px solid #fecdd3", background: "#fff1f2", fontSize: 14, color: "#e11d48" }}>
            <CloseCircleOutlined style={{ fontSize: 16, flexShrink: 0 }} />
            {errorMsg}
          </div>
        )}

        {/* 说明 */}
        <div style={{ fontSize: 12, color: SLATE[400], padding: "0 8px", display: "flex", flexDirection: "column", gap: 4 }}>
          <p style={{ margin: 0 }}>· 拍照后 AI 自动识别题目文字并分步讲解</p>
          <p style={{ margin: 0 }}>· 存入错题本后，系统会按遗忘曲线安排复习</p>
          <p style={{ margin: 0 }}>· 学情画像会自动记录你的薄弱点</p>
        </div>
      </div>
    </H5Shell>
  );
}

export default function H5WrongPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: SLATE[400] }}><LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载中…</div>}>
      <H5WrongContent />
    </Suspense>
  );
}
