/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/AnimationBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next，i18n 中文直出（zh/app.json）：
 *   "(Animation payload is empty)"→（动画内容为空）、"Animation frame"→动画帧、
 *   "Open in new tab"→在新标签页打开、"Open"→打开、"Download video"→下载视频。
 * apiUrl(url) → 相对路径原样返回（tupu 由 dev proxy/网关转发到后端 28000，
 * fetch()/媒体 src 均走相对路径）；lucide：Download→DownloadOutlined、
 * ExternalLink→ExportOutlined（size={11}→fontSize:11）；
 * MarkdownRenderer → LiteMarkdown（'./dtMarkdown'，variant 忽略）；
 * VisualizationViewer → './VisualizationViewer'；Tailwind → 内联样式。
 */
import { useState, type CSSProperties, type ReactNode } from "react";
import {
  DownloadOutlined,
  ExportOutlined,
} from "@ant-design/icons";
import { LiteMarkdown } from './dtMarkdown';
import type { Block } from './book-types';
import VisualizationViewer from './VisualizationViewer';
import type { VisualizeResult } from './visualize-types';

export interface AnimationBlockProps {
  block: Block;
}

interface Artifact {
  type?: string;
  url?: string;
  filename?: string;
  content_type?: string;
  label?: string;
}

// 原仓：非 http(s) 时经 apiUrl() 拼接 API 前缀；tupu 直接用相对路径（proxy 转发）。
function resolveAssetUrl(url: string): string {
  if (!url) return url;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return url;
}

// 视频右上角悬浮徽标链接（原 Tailwind：bg-black/40 → hover:bg-black/60 的半透明徽标）。
function OverlayLink({
  href,
  title,
  download,
  children,
}: {
  href: string;
  title: string;
  download?: string;
  children: ReactNode;
}) {
  const [hovered, setHovered] = useState(false);
  const style: CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    borderRadius: 6,
    background: hovered ? "rgba(0,0,0,0.6)" : "rgba(0,0,0,0.4)",
    padding: "4px 8px",
    fontSize: 10,
    fontWeight: 500,
    color: "rgba(255,255,255,0.9)",
    textDecoration: "none",
    cursor: "pointer",
  };
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      title={title}
      {...(download !== undefined ? { download } : {})}
      style={style}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </a>
  );
}

export default function AnimationBlock({ block }: AnimationBlockProps) {
  const payload = (block.payload || {}) as Record<string, unknown>;
  const renderType = String(payload.render_type || "");
  const code = (payload.code as { language?: string; content?: string } | undefined) || {};
  const htmlContent = String(code.content || "");
  const rawVideoUrl = String(payload.video_url || "");
  const summary = String(payload.summary || "");
  const description = String(payload.description || "");
  const artifacts = (payload.artifacts as Artifact[] | undefined) || [];

  if (renderType === "html" && htmlContent.trim()) {
    const result: VisualizeResult = {
      response: description,
      render_type: "html",
      code: { language: "html", content: htmlContent },
      analysis: {
        render_type: "html",
        description,
        data_description: "",
        chart_type: String(payload.chart_type || "animation"),
        visual_elements: [],
        rationale: "",
      },
      review: {
        optimized_code: "",
        changed: false,
        review_notes: "",
      },
    };

    return (
      <figure
        style={{
          borderRadius: 16,
          border: "1px solid #e4e4e7",
          background: "#fff",
          padding: 12,
          boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
          margin: 0,
        }}
      >
        <VisualizationViewer result={result} />
        {(summary || description) && (
          <figcaption
            style={{ marginTop: 12, fontSize: 12, lineHeight: 1.375, color: "#6b7280" }}
          >
            <LiteMarkdown content={summary || description} />
          </figcaption>
        )}
      </figure>
    );
  }

  if (!rawVideoUrl && artifacts.length === 0) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px dashed #e4e4e7",
          background: "rgba(255,255,255,0.4)",
          padding: 16,
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        （动画内容为空）
      </div>
    );
  }

  const primaryRaw = rawVideoUrl || artifacts[0]?.url || "";
  const primary = resolveAssetUrl(primaryRaw);
  const isVideo =
    primaryRaw.endsWith(".mp4") ||
    primaryRaw.endsWith(".webm") ||
    artifacts.some((a) => (a.content_type || "").startsWith("video/"));
  const filename =
    String(payload.filename || "") || artifacts[0]?.filename || "";

  return (
    <figure
      style={{
        borderRadius: 16,
        border: "1px solid #e4e4e7",
        background: "#fff",
        padding: 12,
        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
        margin: 0,
      }}
    >
      <div
        style={{
          position: "relative",
          overflow: "hidden",
          borderRadius: 12,
          background: "#000",
        }}
      >
        {isVideo ? (
          <video
            src={primary}
            controls
            playsInline
            preload="metadata"
            style={{
              aspectRatio: "16/9",
              height: "auto",
              width: "100%",
              objectFit: "contain",
            }}
          />
        ) : (
          <img
            src={primary}
            alt={description || "动画帧"}
            style={{ height: "auto", width: "100%" }}
          />
        )}
        {primary && (
          <div
            style={{
              position: "absolute",
              right: 8,
              top: 8,
              zIndex: 10,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <OverlayLink href={primary} title={"在新标签页打开"}>
              <ExportOutlined style={{ fontSize: 11 }} />
              {"打开"}
            </OverlayLink>
            {isVideo && (
              <OverlayLink
                href={primary}
                title={"下载视频"}
                download={filename || (true as unknown as string)}
              >
                <DownloadOutlined style={{ fontSize: 11 }} />
              </OverlayLink>
            )}
          </div>
        )}
      </div>
      {(summary || description) && (
        <figcaption
          style={{ marginTop: 12, fontSize: 12, lineHeight: 1.375, color: "#6b7280" }}
        >
          <LiteMarkdown
            content={summary || description}
          />
        </figcaption>
      )}
    </figure>
  );
}
