// 逐行移植自源仓 web/components/chat/preview/previewers/DocxPreview.tsx。
// 差异：去 "use client"；lucide AlertCircle/Loader2 → antd 图标；t() → 中文；
// docx-preview 动态 import 保留（依赖已安装）。

import { useEffect, useRef, useState } from "react";
import { ExclamationCircleOutlined, LoadingOutlined } from "@ant-design/icons";
import { useBinarySource } from "./useBinarySource";

const MIN_FIT_SCALE = 0.5;

function fitRenderedDocx(viewport: HTMLElement, host: HTMLElement) {
  const wrapper = host.querySelector<HTMLElement>(".docx-wrapper");
  const pages = Array.from(host.querySelectorAll<HTMLElement>("section.docx"));
  if (!wrapper || pages.length === 0) return;

  wrapper.style.setProperty("box-sizing", "border-box");
  wrapper.style.setProperty("width", "max-content");
  wrapper.style.setProperty("min-width", "100%");
  wrapper.style.setProperty("align-items", "center");
  wrapper.style.setProperty("padding", "16px 12px 0");
  wrapper.style.setProperty("transform-origin", "top center");

  // Measure unscaled page width, then use CSS zoom for layout-aware fitting.
  // If a browser ignores zoom, overflow-auto still exposes the full page.
  wrapper.style.removeProperty("zoom");
  const pageWidth = Math.max(...pages.map((page) => page.offsetWidth || 0));
  if (!pageWidth) return;

  const availableWidth = Math.max(viewport.clientWidth - 32, 240);
  const scale = Math.min(
    1,
    Math.max(MIN_FIT_SCALE, availableWidth / pageWidth),
  );
  wrapper.style.setProperty("zoom", String(scale));
}

/**
 * Faithful DOCX preview via ``docx-preview`` (lazy-loaded so the parser only
 * ships when a Word doc is actually opened). It lays the document out as
 * page-shaped HTML with the original styles, which reads far better than the
 * extracted-text fallback. On any parse/layout failure we surface a quiet
 * error — the tab's Download button is the escape hatch.
 */
export default function DocxPreview({ url }: { url: string }) {
  const src = useBinarySource(url);
  const viewportRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [rendering, setRendering] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (src.kind === "error") {
      setRendering(false);
      setFailed(true);
      return;
    }
    if (src.kind !== "ready") return;
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    let frame = 0;
    const scheduleFit = () => {
      if (cancelled) return;
      if (frame) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const viewport = viewportRef.current;
        if (viewport && containerRef.current) {
          fitRenderedDocx(viewport, containerRef.current);
        }
      });
    };

    setRendering(true);
    setFailed(false);
    (async () => {
      try {
        const { renderAsync } = await import("docx-preview");
        if (cancelled) return;
        container.innerHTML = "";
        await renderAsync(src.buffer, container, undefined, {
          className: "docx",
          inWrapper: true,
          breakPages: true,
          ignoreLastRenderedPageBreak: true,
          useBase64URL: true,
        });
        if (cancelled) return;
        scheduleFit();
        const viewport = viewportRef.current;
        if (viewport) {
          resizeObserver = new ResizeObserver(scheduleFit);
          resizeObserver.observe(viewport);
        }
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setRendering(false);
      }
    })();

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      if (frame) cancelAnimationFrame(frame);
    };
  }, [src]);

  return (
    <div
      ref={viewportRef}
      className="relative h-full w-full overflow-auto bg-[var(--muted)]/30"
    >
      {rendering && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
          <div className="flex items-center gap-2 text-[12px] text-[var(--muted-foreground)]">
            <LoadingOutlined spin style={{ fontSize: 14 }} />
            <span>正在加载预览…</span>
          </div>
        </div>
      )}
      {failed ? (
        <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center text-[12px] text-[var(--muted-foreground)]">
          <ExclamationCircleOutlined style={{ fontSize: 18 }} className="opacity-70" />
          <p>无法渲染此文档——请用下载打开。</p>
        </div>
      ) : (
        // docx-preview injects its own page-shaped layout (white pages on a
        // grey deck); the wrapper is fitted after render so narrow side
        // panels do not clip the page.
        <div ref={containerRef} className="dt-docx-host min-w-full py-4" />
      )}
    </div>
  );
}
