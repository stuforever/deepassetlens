/**
 * ── 复刻来源与替换点（tupu antd 复刻，批9 F2 / SA-D）────────────────────────
 * 源文件：DeepTutor web/app/h5/book/[bookId]/page.tsx
 * 目标：frontend/src/pages/tutor/h5/H5BookRead.tsx（1:1 复刻，逻辑逐字保留）
 * 路由：/h5/book/[bookId] → /e/tutor/h5/book/:bookId（useParams 取 bookId）
 * 替换点：
 * - "use client" 删除；next/link → react-router Link；next/navigation → react-router；
 * - lucide（Loader2/ChevronLeft/ListTree/Volume2/VolumeX/BookOpen/CheckCircle2/XCircle/
 *   RotateCw）→ @ant-design/icons（LoadingOutlined/LeftOutlined/UnorderedListOutlined/
 *   SoundOutlined/AudioMutedOutlined/ReadOutlined/RedoOutlined）；CheckCircle2/XCircle
 *   原仓 import 后未使用，不移植；
 * - "@/lib/book-api" → "../admin/book-api"（批8 已就绪，导出名 bookApi 一致）；
 *   "@/lib/book-types" → "../admin/book-types"；"@/app/(workspace)/book/components/
 *   speech-segments" → "../admin/speech-segments"；"@/hooks/usePageSpeech" →
 *   "../admin/usePageSpeech"（opts.u 已支持，T2 服务端按用户隔离朗读语义保留）；
 * - "@/components/h5/session-recap" → "./h5shared/sessionRecap"（postReadingEvent
 *   调用点原样：翻页即上报 book_progress，同一页会话内只报一次）；
 * - "../../components/H5Shell"、"@/components/h5/H5Sheet" → "./h5shared/*"；
 *   链接前缀 /h5/* → /e/tutor/h5/*；
 * - Tailwind → 内联样式逐项对位；[&_svg]:max-w-full [&_svg]:h-auto → 注入 CSS 类
 *   .dsh-h5-svg-wrap svg 等价实现。
 * ─────────────────────────────────────────────────────────────────────
 */
import React, { useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  LoadingOutlined,
  LeftOutlined,
  UnorderedListOutlined,
  SoundOutlined,
  AudioMutedOutlined,
  ReadOutlined,
  RedoOutlined,
} from "@ant-design/icons";
import { bookApi } from "../admin/book-api";
import type { Page, Spine, Block } from "../admin/book-types";
import { pageToSegments } from "../admin/speech-segments";
import { usePageSpeech } from "../admin/usePageSpeech";
import { withU } from "./h5shared/h5Utils";
import { postReadingEvent } from "./h5shared/sessionRecap";
import { H5Shell } from "./h5shared/H5Shell";
import { H5Sheet } from "./h5shared/H5Sheet";

/**
 * H5 内部书阅读器（design T4）：H5 自包含内嵌阅读，不跳桌面 /book。
 * 数据源：/api/v1/book/{id}/spine + /pages/{pid}（内容全局共享）。
 * 渲染：轻量块渲染（text/callout/section/quiz/表格/列表）+ 原生 TTS 朗读。
 */

const BLOCK_TYPE_LABEL: Record<string, string> = {
  text: "正文",
  callout: "提示",
  section: "小节",
  quiz: "练习",
  user_note: "笔记",
  figure: "图",
  code: "代码",
  timeline: "时间线",
  flash_cards: "闪卡",
  deep_dive: "深潜",
  interactive: "互动",
  animation: "动画",
  concept_graph: "概念图",
};

/** 富块 → 占位卡元数据（P1-B：figure 外类型手机端占位，指引用学习对话/桌面查看）。 */
const PLACEHOLDER_META: Record<string, { icon: string; msg: string }> = {
  figure: { icon: "📈", msg: "图表 · 请在桌面端查看" },
  animation: { icon: "🎬", msg: "互动动画 · 请在桌面端查看" },
  interactive: { icon: "🎯", msg: "互动组件 · 请在桌面端查看" },
  timeline: { icon: "📅", msg: "时间线" },
  flash_cards: { icon: "🃏", msg: "记忆卡片 · 桌面端可翻转练习" },
  concept_graph: { icon: "🕸️", msg: "概念图 · 请在桌面端查看" },
  diagnostic: { icon: "🎯", msg: "学习活动 · 请通过学习对话进行" },
  pretest: { icon: "🎯", msg: "学习活动 · 请通过学习对话进行" },
  retrieval_practice: { icon: "🎯", msg: "学习活动 · 请通过学习对话进行" },
  error_diagnosis: { icon: "🎯", msg: "学习活动 · 请通过学习对话进行" },
  module_test: { icon: "🎯", msg: "学习活动 · 请通过学习对话进行" },
  progress_dashboard: { icon: "📊", msg: "学情看板 · 请在桌面端查看" },
};

type RenderedBlock =
  | { kind: "text" | "code"; type: string; title: string; body: string; jump?: { href: string; label: string } }
  | { kind: "figure_svg"; type: string; title: string; body: string; svg: string }
  | { kind: "placeholder"; type: string; title: string; body: string; icon: string; msg: string;
      jump?: { href: string; label: string } };

/** C2（M18-C）：学习活动占位卡 → 真跳转（quiz→本章闯关 / retrieval→错题本重练 /
 *  error_diagnosis→问AI带上下文）。u/chapter 用于构造直达链接。 */
function jumpForType(type: string, u: string, chapterTitle: string): { href: string; label: string } | undefined {
  const chQs = (extra?: Record<string, string>) => {
    const p = new URLSearchParams({ ...(extra || {}) });
    if (chapterTitle) p.set("from_book_ch", chapterTitle);
    const s = p.toString();
    return s ? `&${s}` : "";
  };
  switch (type) {
    case "quiz":
    case "module_test":
    case "pretest":
      return {
        href: withU(`/e/tutor/h5/learn?tab=practice${chQs()}`, u),
        label: "去本章闯关练习 →",
      };
    case "retrieval_practice":
      return { href: withU("/e/tutor/h5/wrongbook", u), label: "去错题重练 →" };
    case "error_diagnosis":
      return {
        href: withU(
          `/e/tutor/h5/chat?text=${encodeURIComponent(`我在读《${chapterTitle || "本书"}》时想做个错因诊断，帮我分析易错点。`)}`,
          u,
        ),
        label: "问 AI 错因诊断 →",
      };
    default:
      return undefined;
  }
}

function fmtBlocks(blocks: Block[], u = "", chapterTitle = ""): RenderedBlock[] {
  const out: RenderedBlock[] = [];
  for (const b of blocks || []) {
    if (b.status !== "ready") continue;
    const p = (b.payload || {}) as Record<string, unknown>;
    let body = "";
    let title = b.title || "";
    switch (b.type) {
      case "text":
        body = String(p.body ?? "");
        break;
      case "callout":
        title = String(p.label ?? b.title ?? "");
        body = String(p.body ?? "");
        break;
      case "section": {
        const intro = String(p.intro ?? "");
        const takeaway = String(p.key_takeaway ?? "");
        const subs = Array.isArray(p.subsections)
          ? (p.subsections as Array<Record<string, unknown>>)
          : [];
        const subBodies = subs
          .map((s) => {
            const st = String(s?.title ?? "");
            const sb = String(s?.body ?? "");
            return st ? `**${st}**\n${sb}` : sb;
          })
          .filter(Boolean)
          .join("\n\n");
        body = [intro, subBodies, takeaway ? `> 要点：${takeaway}` : ""]
          .filter(Boolean)
          .join("\n\n");
        break;
      }
      case "quiz": {
        const questions = Array.isArray(p.questions)
          ? (p.questions as Array<Record<string, unknown>>)
          : [];
        body = questions
          .map((q, i) => {
            const opts = Array.isArray(q?.options)
              ? (q.options as Array<Record<string, unknown>>)
              : [];
            const optsTxt = opts
              .map((o) => {
                const label = String(o?.label ?? "");
                const text = String(o?.text ?? "");
                return `${label}${label && text ? ". " : ""}${text}`;
              })
              .join("\n");
            return `**第${i + 1}题** ${String(q?.question ?? "")}\n${optsTxt}`;
          })
          .join("\n\n");
        break;
      }
      case "user_note":
      case "deep_dive": {
        body = String(p.body ?? p.note ?? "");
        break;
      }
      case "figure": {
        title = String(p.caption ?? b.title ?? "");
        const renderType = String(p.render_type ?? "");
        const code = String((p.code as Record<string, unknown>)?.content ?? "");
        // P1-B：SVG 源码可直接内联真图；chartjs/mermaid 给占位卡
        if (renderType === "svg" && code.trim()) {
          out.push({ kind: "figure_svg", type: b.type, title, body: "", svg: code });
          continue;
        }
        const meta = PLACEHOLDER_META.figure;
        out.push({
          kind: "placeholder",
          type: b.type,
          title,
          body: "",
          icon: meta.icon,
          msg: meta.msg,
        });
        continue;
      }
      case "timeline": {
        const items = Array.isArray(p.items)
          ? (p.items as Array<Record<string, unknown>>)
          : [];
        body = items
          .map((it) => `- **${String(it?.when ?? it?.title ?? "")}** ${String(it?.event ?? it?.what ?? "")}`)
          .filter((l) => l !== "- **")
          .join("\n");
        break;
      }
      case "code": {
        const code = String(p.code ?? p.content ?? "");
        out.push({ kind: "code", type: b.type, title: b.title || "", body: code });
        continue;
      }
      case "flash_cards": {
        const cards = Array.isArray(p.cards)
          ? (p.cards as Array<Record<string, unknown>>)
          : [];
        body = cards
          .map((c) => `- ${String(c?.front ?? c?.term ?? "")}：${String(c?.back ?? c?.definition ?? "")}`)
          .join("\n");
        break;
      }
      default: {
        // 富块（animation/interactive/concept_graph/诊断类）→ 占位卡
        const meta = PLACEHOLDER_META[b.type];
        if (meta) {
          out.push({
            kind: "placeholder",
            type: b.type,
            title: b.title || "",
            body: "",
            icon: meta.icon,
            msg: meta.msg,
            jump: jumpForType(b.type, u, chapterTitle),
          });
          continue;
        }
        // 其他类型：尝试提取 body/text/content
        body = String(p.body ?? p.text ?? p.content ?? "");
        break;
      }
    }
    if (body.trim()) {
      const jump = b.type === "quiz" ? jumpForType("quiz", u, chapterTitle) : undefined;
      out.push({ kind: "text", type: b.type, title, body: body.trim(), jump });
    }
  }
  return out;
}

/** 极简 inline markdown：**加粗** / 换行 / 图片占位。 */
function InlineBody({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 15, lineHeight: 1.625, color: "#334155" }}>
      {lines.map((line, i) => {
        if (line.startsWith("**") && line.endsWith("**")) {
          return (
            <div key={i} style={{ fontWeight: 600, color: "#0f172a", paddingTop: 4 }}>
              {line.slice(2, -2)}
            </div>
          );
        }
        if (line.startsWith("> ")) {
          return (
            <div key={i} style={{ borderLeft: "2px solid #7dd3fc", background: "rgba(240,249,255,0.6)", borderRadius: "0 8px 8px 0", padding: "6px 12px", color: "#075985" }}>
              {line.slice(2)}
            </div>
          );
        }
        if (line.startsWith("![](") && line.endsWith(")")) {
          const src = line.slice(4, -1);
          return <img key={i} src={src} alt="" style={{ borderRadius: 12, maxWidth: "100%", margin: "4px 0" }} />;
        }
        if (/^[-•]\s/.test(line)) {
          return (
            <div key={i} style={{ display: "flex", gap: 6 }}>
              <span style={{ color: "#94a3b8" }}>•</span>
              <span>{line.replace(/^[-•]\s/, "")}</span>
            </div>
          );
        }
        return <div key={i}>{line}</div>;
      })}
    </div>
  );
}

function BlockCard({ block }: { block: RenderedBlock }) {
  // C2（M18-C）：占位卡/quiz 卡带真跳转按钮
  const jump = "jump" in block ? block.jump : undefined;
  const jumpBtn = jump ? (
    <Link
      to={jump.href}
      style={{ display: "inline-flex", alignItems: "center", gap: 4, marginTop: 8, padding: "6px 12px", borderRadius: 8, background: "#4f46e5", color: "#fff", fontSize: 12, fontWeight: 500, textDecoration: "none" }}
    >
      {jump.label}
    </Link>
  ) : null;
  // P1-B 占位卡：富块在手机上无声丢失 → 图标+去向指引
  if (block.kind === "placeholder") {
    return (
      <div style={{ borderRadius: 16, border: "1px dashed #cbd5e1", background: "#f8fafc", padding: 16, textAlign: "center" }}>
        <div style={{ fontSize: 24 }}>{block.icon}</div>
        <div style={{ fontSize: 14, color: "#64748b", marginTop: 4 }}>
          {block.title && <span style={{ fontWeight: 500, color: "#475569" }}>{block.title} · </span>}
          {block.msg}
        </div>
        {jumpBtn}
      </div>
    );
  }
  // P1-B figure SVG 源码 → 直接内联真图
  if (block.kind === "figure_svg") {
    return (
      <div style={{ borderRadius: 16, border: "1px solid #e2e8f0", background: "#fff", padding: 8 }}>
        {block.title && (
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: "#94a3b8", background: "#f1f5f9", borderRadius: 4, padding: "2px 6px", display: "inline-block", marginBottom: 6 }}>
            {BLOCK_TYPE_LABEL[block.type] || block.type}
          </div>
        )}
        <div
          className="dsh-h5-svg-wrap"
          style={{ overflowX: "auto" }}
          dangerouslySetInnerHTML={{ __html: block.svg }}
        />
        {block.title && (
          <div style={{ fontSize: 12, color: "#64748b", textAlign: "center", marginTop: 4 }}>{block.title}</div>
        )}
      </div>
    );
  }
  return (
    <div
      style={{
        borderRadius: 16, border: "1px solid",
        padding: 14,
        borderColor:
          block.type === "callout" ? "#bae6fd" : block.type === "quiz" ? "#ddd6fe" : "#e2e8f0",
        background:
          block.type === "callout" ? "rgba(240,249,255,0.6)" : block.type === "quiz" ? "rgba(245,243,255,0.5)" : "#fff",
      }}
    >
      {block.title && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
          <span style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: "#94a3b8", background: "#f1f5f9", borderRadius: 4, padding: "2px 6px" }}>
            {BLOCK_TYPE_LABEL[block.type] || block.type}
          </span>
          <span style={{ fontWeight: 600, color: "#1e293b", fontSize: 14 }}>{block.title}</span>
        </div>
      )}
      {block.kind === "code" ? (
        <pre style={{ fontSize: 13, fontFamily: "monospace", whiteSpace: "pre-wrap", background: "#0f172a", color: "#f1f5f9", borderRadius: 12, padding: 12, overflowX: "auto", margin: 0 }}>
          {block.body}
        </pre>
      ) : (
        <InlineBody text={block.body} />
      )}
      {jumpBtn}
    </div>
  );
}

function H5BookContent() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const bookId = String(params?.bookId || "");

  const [detail, setDetail] = useState<{ book?: { title: string; language?: string }; spine: Spine | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [spine, setSpine] = useState<Spine | null>(null);
  const [chapterIdx, setChapterIdx] = useState(0);
  const [pageIds, setPageIds] = useState<string[]>([]);
  const [pageId, setPageId] = useState<string>("");
  const [page, setPage] = useState<Page | null>(null);
  const [pageLoading, setPageLoading] = useState(false);
  const [tocOpen, setTocOpen] = useState(false);

  // ── 加载书 + spine ──
  useEffect(() => {
    if (!bookId) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const [meta, spineRes] = await Promise.all([
          bookApi.get(bookId).catch(() => null),
          bookApi.getSpine(bookId).catch(() => null),
        ]);
        if (cancelled) return;
        setDetail(meta ? { book: meta.book, spine: spineRes?.spine ?? null } : { spine: spineRes?.spine ?? null });
        const sp = spineRes?.spine ?? null;
        setSpine(sp);
        if (sp?.chapters?.length) {
          const first = sp.chapters[0];
          setPageIds(first.page_ids || []);
          setPageId(first.page_ids?.[0] || "");
          setChapterIdx(0);
        } else {
          setPageIds([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [bookId]);

  // ── 加载当前页 ──
  useEffect(() => {
    if (!bookId || !pageId) return;
    let cancelled = false;
    setPageLoading(true);
    bookApi
      .getPage(bookId, pageId)
      .then((d) => {
        if (!cancelled) setPage(d.page);
      })
      .catch(() => {
        if (!cancelled) setPage(null);
      })
      .finally(() => {
        if (!cancelled) setPageLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [bookId, pageId]);

  const segments = useMemo(() => pageToSegments(page), [page]);
  // T2（第十二篇）：传 u —— 服务端朗读按用户隔离
  const speech = usePageSpeech(segments, { u });
  const speechActive = speech.state === "speaking" || speech.state === "paused";

  // 切页停止朗读
  useEffect(() => {
    speech.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageId]);

  const selectChapter = (idx: number) => {
    const ch = spine?.chapters?.[idx];
    if (!ch) return;
    setChapterIdx(idx);
    setPageIds(ch.page_ids || []);
    setPageId(ch.page_ids?.[0] || "");
    setTocOpen(false);
  };

  const chapter = spine?.chapters?.[chapterIdx];

  // C2（M18-C）：阅读回流——翻页即上报 book_progress（同一页只报一次）
  useEffect(() => {
    if (!pageId || !chapter) return;
    const idx = (chapter.page_ids || []).indexOf(pageId);
    postReadingEvent(u, bookId, chapter.title || "", Math.max(0, idx));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageId, chapter?.title, bookId]);

  const rendered = page ? fmtBlocks(page.blocks, u, chapter?.title || "") : [];

  return (
    <H5Shell active="learn" hideNav>
      <style>{".dsh-h5-svg-wrap svg{max-width:100%;height:auto;}"}</style>
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(90deg, #047857, #0f766e)", color: "#fff", padding: 16, borderRadius: "0 0 24px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link to={withU("/e/tutor/h5/learn", u)} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "#a7f3d0", textDecoration: "none" }}>
            <LeftOutlined style={{ fontSize: 16 }} /> 返回学习
          </Link>
          <div style={{ fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 6, overflow: "hidden" }}>
            <ReadOutlined style={{ fontSize: 20, flexShrink: 0 }} />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{detail?.book?.title || "内部书"}</span>
          </div>
          <button
            onClick={() => setTocOpen((v) => !v)}
            style={{ fontSize: 12, color: "#a7f3d0", border: "1px solid rgba(52,211,153,0.4)", borderRadius: 999, padding: "2px 8px", display: "flex", alignItems: "center", gap: 4, background: "none", cursor: "pointer", flexShrink: 0 }}
          >
            <UnorderedListOutlined style={{ fontSize: 14 }} /> 目录
          </button>
        </div>
      </div>

      {/* 目录抽屉（S1/M23：H5Sheet 统一基座） */}
      <H5Sheet open={tocOpen} onClose={() => setTocOpen(false)} title="目录">
        <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
          {(spine?.chapters || []).map((ch, i) => (
            <button
              key={ch.id}
              onClick={() => selectChapter(i)}
              className={i === chapterIdx ? undefined : "dsh-h5-press-slate"}
              style={{
                width: "100%", textAlign: "left", minHeight: 44, padding: "10px 12px",
                borderRadius: 12, fontSize: 14, marginBottom: 4, border: "none", cursor: "pointer",
                boxSizing: "border-box",
                background: i === chapterIdx ? "#ecfdf5" : "transparent",
                color: i === chapterIdx ? "#047857" : "inherit",
                fontWeight: i === chapterIdx ? 500 : 400,
              }}
            >
              {ch.order + 1}. {ch.title}
            </button>
          ))}
          {!spine?.chapters?.length && (
            <div style={{ fontSize: 14, color: "#94a3b8", padding: "24px 0", textAlign: "center" }}>暂无章节</div>
          )}
        </div>
      </H5Sheet>

      {/* 正文 */}
      <div style={{ padding: "16px 16px 40px" }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 0", color: "#94a3b8" }}>
            <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载书…
          </div>
        ) : pageLoading && !page ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 0", color: "#94a3b8" }}>
            <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载页…
          </div>
        ) : !page ? (
          <div style={{ textAlign: "center", padding: "64px 0", color: "#94a3b8" }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📕</div>
            暂无内容
          </div>
        ) : (
          <>
            {/* 页头：章节 + 朗读 */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: "#059669" }}>{chapter?.title || ""}</div>
                <h2 style={{ fontWeight: 600, color: "#1e293b", fontSize: 16, lineHeight: 1.375, margin: 0 }}>{page.title}</h2>
              </div>
              {speech.supported && segments.length > 0 && (
                <button
                  onClick={() => (speechActive ? speech.stop() : speech.toggle())}
                  style={{
                    flexShrink: 0, display: "flex", alignItems: "center", gap: 4, padding: "6px 12px",
                    borderRadius: 999, border: "1px solid", fontSize: 12, fontWeight: 500, cursor: "pointer",
                    borderColor: speechActive ? "#34d399" : "#e2e8f0",
                    background: speechActive ? "#ecfdf5" : "transparent",
                    color: speechActive ? "#047857" : "#64748b",
                  }}
                >
                  {speechActive ? <AudioMutedOutlined style={{ fontSize: 14 }} /> : <SoundOutlined style={{ fontSize: 14 }} />}
                  {speechActive ? "停止" : "朗读"}
                </button>
              )}
            </div>

            {/* 学习目标 */}
            {page.learning_objectives?.length > 0 && (
              <div style={{ marginBottom: 12, padding: 12, borderRadius: 16, border: "1px solid #a7f3d0", background: "rgba(236,253,245,0.6)" }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: "#047857", marginBottom: 4 }}>学习目标</div>
                {page.learning_objectives.map((o, i) => (
                  <div key={i} style={{ fontSize: 14, color: "#475569", display: "flex", gap: 6 }}>
                    <span style={{ color: "#10b981" }}>•</span> {o}
                  </div>
                ))}
              </div>
            )}

            {/* 块渲染 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {rendered.map((b, i) => (
                <BlockCard key={i} block={b} />
              ))}
              {rendered.length === 0 && (
                <div style={{ textAlign: "center", padding: "40px 0", color: "#94a3b8", fontSize: 14 }}>本页暂无内容</div>
              )}
            </div>

            {/* 朗读进度条 */}
            {speechActive && (
              <div style={{ marginTop: 16, padding: 12, borderRadius: 16, background: "#1e293b", color: "#fff" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12, marginBottom: 8 }}>
                  <span style={{ color: "#cbd5e1" }}>
                    {speech.currentIndex + 1}/{segments.length} 段
                  </span>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => speech.prev()} style={{ padding: "2px 8px", borderRadius: 4, background: "#334155", border: "none", color: "#fff", cursor: "pointer" }}>⏮</button>
                    <button onClick={() => speech.toggle()} style={{ padding: "2px 8px", borderRadius: 4, background: "#334155", border: "none", color: "#fff", cursor: "pointer" }}>
                      {speech.state === "paused" ? "▶" : "⏸"}
                    </button>
                    <button onClick={() => speech.next()} style={{ padding: "2px 8px", borderRadius: 4, background: "#334155", border: "none", color: "#fff", cursor: "pointer" }}>⏭</button>
                  </div>
                </div>
                <div style={{ height: 4, borderRadius: 999, background: "#334155", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%", background: "#34d399", transition: "all .15s",
                      width: `${segments.length ? ((speech.currentIndex + 1) / segments.length) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            )}

            {/* 页内导航 */}
            <div style={{ marginTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <button
                onClick={() => {
                  const i = pageIds.indexOf(pageId);
                  if (i > 0) setPageId(pageIds[i - 1]);
                }}
                disabled={pageIds.indexOf(pageId) <= 0}
                style={{ display: "flex", alignItems: "center", gap: 4, padding: "6px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, background: "none", cursor: "pointer", opacity: pageIds.indexOf(pageId) <= 0 ? 0.4 : 1 }}
              >
                <RedoOutlined style={{ fontSize: 14, transform: "rotate(180deg)" }} /> 上一节
              </button>
              <span style={{ fontSize: 12, color: "#94a3b8" }}>
                {pageIds.indexOf(pageId) + 1}/{pageIds.length} 节
              </span>
              <button
                onClick={() => {
                  const i = pageIds.indexOf(pageId);
                  if (i < pageIds.length - 1) setPageId(pageIds[i + 1]);
                  else if (chapterIdx < (spine?.chapters?.length || 0) - 1) selectChapter(chapterIdx + 1);
                }}
                disabled={pageIds.indexOf(pageId) >= pageIds.length - 1 && chapterIdx >= (spine?.chapters?.length || 0) - 1}
                style={{ display: "flex", alignItems: "center", gap: 4, padding: "6px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, background: "none", cursor: "pointer", opacity: pageIds.indexOf(pageId) >= pageIds.length - 1 && chapterIdx >= (spine?.chapters?.length || 0) - 1 ? 0.4 : 1 }}
              >
                下一节 <RedoOutlined style={{ fontSize: 14 }} />
              </button>
            </div>
          </>
        )}
      </div>
    </H5Shell>
  );
}

export default function H5BookPage() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载中…
        </div>
      }
    >
      <H5BookContent />
    </Suspense>
  );
}
