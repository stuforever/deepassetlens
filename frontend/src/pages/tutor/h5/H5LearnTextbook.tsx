/**
 * H5 原文阅读（design T3）：教材原文逐页翻阅——原仓 app/h5/learn/textbook/page.tsx 1:1 移植。
 * 等价替换：删除 "use client"；next/link → react-router Link；useSearchParams →
 * react-router-dom；lucide（Loader2/ChevronLeft/ChevronRight/BookOpen/FileText/
 * RotateCw）→ @ant-design/icons（LoadingOutlined/LeftOutlined/RightOutlined/
 * ReadOutlined/FileTextOutlined/ReloadOutlined）；Tailwind → 内联样式逐项对位
 * （active:* 伪类无法内联，已省略）；路由前缀映射：原 /h5/* → /e/tutor-h5/*。
 * 数据源：/curriculum/textbooks/{tid}/pages -> [{page_num, image_url, ocr_text}]。
 * 页图（PNG）+ OCR 文本双显，支持手势翻页按钮。
 */

import { useCallback, useEffect, useState, Suspense } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  LoadingOutlined, LeftOutlined, RightOutlined, ReadOutlined, FileTextOutlined, ReloadOutlined,
} from "@ant-design/icons";
import { fetchTextbookTree, fetchTextbookPages, type TextbookNode } from "./h5shared/selfLearningApi";
import { withU } from "./h5shared/h5Utils";
import { readLastTextbook, rememberTextbook } from "./h5shared/h5LearnMemory";
import { postReadingEvent } from "./h5shared/sessionRecap";
import { H5Shell } from "./h5shared/H5Shell";
import { H5Sheet } from "./h5shared/H5Sheet";
import { H5ExportButtons } from "./learn/H5ExportButtons";

interface PageItem {
  id?: string;
  page_num: number;
  image_url?: string | null;
  ocr_text?: string | null;
  [k: string]: unknown;
}

function H5TextbookContent() {
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const [textbooks, setTextbooks] = useState<TextbookNode[]>([]);
  const [selectedTbId, setSelectedTbId] = useState<string>("");
  const [pages, setPages] = useState<PageItem[]>([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pagesLoading, setPagesLoading] = useState(false);
  const [picker, setPicker] = useState(false);

  useEffect(() => {
    fetchTextbookTree()
      .then((list) => {
        const arr = Array.isArray(list) ? list : [];
        setTextbooks(arr);
        if (arr.length > 0) {
          // S5（M23-E）：per-u 上次教材——树里仍存在则直接恢复
          const last = readLastTextbook(u || "");
          const memHit = last ? arr.find((t) => t.id === last.textbook_id) : null;
          if (memHit) {
            setSelectedTbId(memHit.id);
            return;
          }
          setSelectedTbId(arr[0].id);
          // 默认选中有已导入原文页的教材，避免打开即「暂未导入」空态
          void Promise.all(
            arr.map((tb) =>
              fetchTextbookPages(tb.id)
                .then((d: unknown) => {
                  const items = Array.isArray(d)
                    ? d
                    : Array.isArray((d as { items?: unknown[] })?.items)
                      ? ((d as { items: unknown[] }).items as unknown[])
                      : [];
                  return { id: tb.id, count: items.length };
                })
                .catch(() => ({ id: tb.id, count: 0 })),
            ),
          ).then((counts) => {
            const withPages = counts.find((c) => c.count > 0);
            // 仅当当前选中教材确实无页面时切换（不覆盖用户手动选择）
            setSelectedTbId((cur) => {
              const curCount = counts.find((c) => c.id === cur)?.count ?? 0;
              return curCount === 0 && withPages ? withPages.id : cur;
            });
          });
        }
      })
      .finally(() => setLoading(false));
  }, []);

  // S5：选中教材变化即记忆（含初始恢复后的确认写入；用户手动切换覆盖旧值）
  useEffect(() => {
    if (!selectedTbId) return;
    const tb = textbooks.find((t) => t.id === selectedTbId);
    if (tb) rememberTextbook(u || "", tb.id, tb.name);
  }, [selectedTbId, textbooks, u]);

  useEffect(() => {
    if (!selectedTbId) return;
    setPagesLoading(true);
    setIdx(0);
    fetchTextbookPages(selectedTbId)
      .then((data) => {
        const items = Array.isArray(data)
          ? data
          : Array.isArray(data?.items)
            ? data.items
            : [];
        const sorted = [...items].sort((a, b) => (a.page_num || 0) - (b.page_num || 0));
        setPages(sorted);
      })
      .catch(() => setPages([]))
      .finally(() => setPagesLoading(false));
  }, [selectedTbId]);

  const current = pages[idx];

  // C2（M18-C）：教材翻页回流（book_id=textbook:<tid>，page=页码）
  useEffect(() => {
    if (!selectedTbId || !current) return;
    postReadingEvent(u, `textbook:${selectedTbId}`, "教材原文", current.page_num || idx + 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTbId, idx, pages.length]);

  return (
    <H5Shell active="learn">
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(to right, #334155, #0f172a)", color: "#fff", padding: 16, borderBottomLeftRadius: 24, borderBottomRightRadius: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link
            to={withU("/e/tutor-h5/learn", u)}
            style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "#cbd5e1", textDecoration: "none" }}
          >
            <LeftOutlined style={{ fontSize: 14 }} /> 返回学习
          </Link>
          <div style={{ fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
            <ReadOutlined style={{ fontSize: 20 }} /> 原文阅读
          </div>
          <button
            onClick={() => setPicker(true)}
            style={{ fontSize: 12, color: "#cbd5e1", border: "1px solid rgba(100,116,139,0.4)", borderRadius: 9999, padding: "2px 8px", background: "transparent", cursor: "pointer" }}
          >
            选教材
          </button>
        </div>
        <div style={{ marginTop: 8, fontSize: 14, color: "#e2e8f0" }}>
          {textbooks.find((t) => t.id === selectedTbId)?.name || "教材原文"}
        </div>
        <div style={{ marginTop: 8 }}>
          <H5ExportButtons textbookId={selectedTbId} tab="original" />
        </div>
      </div>

      {/* 选教材抽屉（S1/M23：H5Sheet 统一基座） */}
      <H5Sheet open={picker} onClose={() => setPicker(false)} title="选择教材">
        <div style={{ paddingLeft: 20, paddingRight: 20, paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
          {textbooks.map((tb) => (
            <button
              key={tb.id}
              onClick={() => {
                setSelectedTbId(tb.id);
                setPicker(false);
              }}
              style={{
                width: "100%", textAlign: "left", minHeight: 44, padding: "10px 12px",
                borderRadius: 12, fontSize: 14, marginBottom: 4, border: "none", cursor: "pointer",
                background: selectedTbId === tb.id ? "#1e293b" : "transparent",
                color: selectedTbId === tb.id ? "#fff" : "inherit",
              }}
            >
              <ReadOutlined style={{ fontSize: 16, marginRight: 6 }} />
              {tb.name}
              <span style={{ marginLeft: 8, fontSize: 10, opacity: 0.7 }}>{tb.subject} · {tb.grade || "—"}</span>
            </button>
          ))}
        </div>
      </H5Sheet>

      {/* 正文 */}
      <div style={{ paddingLeft: 16, paddingRight: 16, marginTop: 16, paddingBottom: 40 }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 0", color: "#94a3b8" }}>
            <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载教材…
          </div>
        ) : pagesLoading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 0", color: "#94a3b8" }}>
            <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载页…
          </div>
        ) : pages.length === 0 ? (
          <div style={{ textAlign: "center", padding: "64px 0", color: "#94a3b8" }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📄</div>
            该教材暂未导入原文
            <div style={{ fontSize: 14, marginTop: 8 }}>教材原文需先在后台导入（PDF 拆页 + OCR）</div>
          </div>
        ) : (
          <>
            {/* 页码条 */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <button
                onClick={() => setIdx((i) => Math.max(0, i - 1))}
                disabled={idx === 0}
                style={{
                  display: "flex", alignItems: "center", gap: 4, padding: "6px 12px",
                  borderRadius: 12, border: "1px solid #e5e7eb", fontSize: 14,
                  background: "transparent", color: "inherit", cursor: "pointer",
                  opacity: idx === 0 ? 0.4 : undefined,
                }}
              >
                <LeftOutlined style={{ fontSize: 14 }} /> 上一页
              </button>
              <span style={{ fontSize: 14, color: "#64748b" }}>
                第 {idx + 1} / {pages.length} 页
              </span>
              <button
                onClick={() => setIdx((i) => Math.min(pages.length - 1, i + 1))}
                disabled={idx === pages.length - 1}
                style={{
                  display: "flex", alignItems: "center", gap: 4, padding: "6px 12px",
                  borderRadius: 12, border: "1px solid #e5e7eb", fontSize: 14,
                  background: "transparent", color: "inherit", cursor: "pointer",
                  opacity: idx === pages.length - 1 ? 0.4 : undefined,
                }}
              >
                下一页 <RightOutlined style={{ fontSize: 14 }} />
              </button>
            </div>

            {/* 页图 + OCR 文本 */}
            <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", border: "1px solid #e5e7eb", overflow: "hidden" }}>
              {current?.image_url && (
                <div style={{ background: "#f1f5f9", display: "flex", alignItems: "center", justifyContent: "center", padding: 12 }}>
                  <img
                    src={current.image_url}
                    alt={`第 ${current.page_num} 页`}
                    style={{ maxWidth: "100%", maxHeight: "60vh", objectFit: "contain", borderRadius: 8 }}
                  />
                </div>
              )}
              <div style={{ padding: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, fontSize: 12, color: "#94a3b8" }}>
                  <FileTextOutlined style={{ fontSize: 14 }} />
                  OCR 文本 · 第 {current?.page_num} 页
                </div>
                {current?.ocr_text ? (
                  <div style={{ fontSize: 14, color: "#334155", lineHeight: 1.625, whiteSpace: "pre-wrap" }}>
                    {current.ocr_text}
                  </div>
                ) : (
                  <div style={{ fontSize: 14, color: "#94a3b8" }}>
                    本页暂无 OCR 文本，可查看上方原图。
                  </div>
                )}
              </div>
            </div>

            {/* 翻页提示 */}
            <div style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, fontSize: 12, color: "#94a3b8" }}>
              <ReloadOutlined style={{ fontSize: 12 }} />
              左右按钮翻页 · 原文图片可点击放大查看
            </div>
          </>
        )}
      </div>
    </H5Shell>
  );
}

export default function H5TextbookPage() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <LoadingOutlined style={{ fontSize: 20, marginRight: 8 }} spin /> 加载中…
        </div>
      }
    >
      <H5TextbookContent />
    </Suspense>
  );
}
