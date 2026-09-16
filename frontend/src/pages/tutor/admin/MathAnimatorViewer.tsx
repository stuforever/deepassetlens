/**
 * 复刻自 DeepTutor：web/components/math-animator/MathAnimatorViewer.tsx
 * （VisualizationViewer 的 manim 分支子组件，按"内部依赖同样处理"平铺到 tupu）。
 * 替换点：
 *  - 删除 "use client" 与 react-i18next；文案按 zh/app.json 中文直出
 *    （视频输出/图片输出/查看 Manim 代码/全屏/全屏数学动画输出）。
 *    原代码未走 t() 的英文硬编码（"Visual review warning:"、"quality:"、"retries:"）逐字保留。
 *  - apiUrl(url) → 相对路径原样返回（tupu 由 dev proxy/网关转发到后端 28000）。
 *  - lucide-react → @ant-design/icons：Code2→CodeOutlined、Expand→ExpandOutlined、
 *    Image→PictureOutlined、Timer→FieldTimeOutlined、Video→VideoCameraOutlined。
 *  - @/lib/math-animator-types → './math-animator-types'（本目录产出）。
 *  - Tailwind → antd + 最小内联样式（muted→#f4f4f5、border→#e4e4e7、amber-500→#f59e0b 等）。
 */
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type CSSProperties,
} from "react";
import {
  CodeOutlined,
  ExpandOutlined,
  PictureOutlined,
  FieldTimeOutlined,
  VideoCameraOutlined,
} from "@ant-design/icons";
import type { MathAnimatorResult } from "./math-animator-types";

const borderColor = "#e4e4e7";
const foreground = "rgba(0,0,0,0.88)";
const mutedForeground = "#6b7280";

const iconStyle = (size: number): CSSProperties => ({ fontSize: size });

export default function MathAnimatorViewer({
  result,
}: {
  result: MathAnimatorResult;
}) {
  const [fullscreenUrl, setFullscreenUrl] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const images = useMemo(
    () => result.artifacts.filter((item) => item.type === "image"),
    [result.artifacts],
  );
  const videos = useMemo(
    () => result.artifacts.filter((item) => item.type === "video"),
    [result.artifacts],
  );
  // 原仓 apiUrl(url)；tupu 相对路径由 proxy 转发。
  const resolveAssetUrl = (url: string) => url;

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;

    const handler = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) < 1) return;

      // Don't intercept if the event target is inside a scrollable child
      // (e.g. the code <pre> block) that can still scroll in this direction.
      let node = e.target as HTMLElement | null;
      while (node && node !== el) {
        if (node.scrollHeight > node.clientHeight + 2) {
          const style = window.getComputedStyle(node);
          if (style.overflowY === "auto" || style.overflowY === "scroll") {
            const atBottom =
              node.scrollTop + node.clientHeight >= node.scrollHeight - 2;
            const atTop = node.scrollTop <= 2;
            if ((e.deltaY > 0 && !atBottom) || (e.deltaY < 0 && !atTop)) {
              return;
            }
          }
        }
        node = node.parentElement;
      }

      let scrollRoot: HTMLElement | null = el.closest(
        "[data-chat-scroll-root='true']",
      ) as HTMLElement | null;
      if (!scrollRoot) {
        let parent: HTMLElement | null = el.parentElement;
        while (parent) {
          const style = window.getComputedStyle(parent);
          if (
            (style.overflowY === "auto" || style.overflowY === "scroll") &&
            parent.scrollHeight > parent.clientHeight + 2
          ) {
            scrollRoot = parent;
            break;
          }
          parent = parent.parentElement;
        }
      }

      if (scrollRoot) {
        e.preventDefault();
        scrollRoot.scrollBy({ top: e.deltaY, behavior: "auto" });
      }
    };

    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  }, []);

  return (
    <div
      ref={rootRef}
      style={{
        marginBottom: 12,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        borderRadius: 16,
        border: `1px solid ${borderColor}`,
        background: "rgba(255,255,255,0.7)",
        padding: 12,
      }}
    >
      {videos.length > 0 ? (
        <section style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <Header
            icon={VideoCameraOutlined}
            title={"视频输出"}
          />
          {videos.map((item) => (
            <div key={item.url}>
              <video
                controls
                playsInline
                preload="metadata"
                style={{
                  aspectRatio: "16/9",
                  width: "100%",
                  borderRadius: 12,
                  border: `1px solid ${borderColor}`,
                  background: "#000",
                  objectFit: "contain",
                }}
                src={resolveAssetUrl(item.url)}
              />
            </div>
          ))}
        </section>
      ) : null}

      {images.length > 0 ? (
        <section style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <Header
            icon={PictureOutlined}
            title={"图片输出"}
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 8 }}>
            {images.map((item) => (
              <button
                key={item.url}
                type="button"
                onClick={() => setFullscreenUrl(resolveAssetUrl(item.url))}
                style={{
                  position: "relative",
                  overflow: "hidden",
                  borderRadius: 12,
                  border: `1px solid ${borderColor}`,
                  background: "#f5f5f5",
                  padding: 0,
                  cursor: "pointer",
                }}
              >
                <img
                  src={resolveAssetUrl(item.url)}
                  alt={item.label || item.filename}
                  style={{ maxHeight: 280, width: "100%", objectFit: "contain" }}
                />
                <span
                  style={{
                    position: "absolute",
                    right: 8,
                    top: 8,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    borderRadius: 6,
                    background: "rgba(0,0,0,0.55)",
                    padding: "2px 8px",
                    fontSize: 11,
                    color: "#fff",
                  }}
                >
                  <ExpandOutlined style={iconStyle(12)} />
                  {"全屏"}
                </span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {result.code.content ? (
        <details
          style={{
            overflow: "hidden",
            borderRadius: 12,
            border: `1px solid ${borderColor}`,
            background: "#f5f5f5",
          }}
        >
          <summary
            style={{
              display: "flex",
              cursor: "pointer",
              alignItems: "center",
              gap: 8,
              padding: "8px 12px",
              fontSize: 12,
              fontWeight: 500,
              color: foreground,
            }}
          >
            <CodeOutlined style={iconStyle(14)} />
            {"查看 Manim 代码"}
          </summary>
          <pre
            style={{
              maxHeight: 360,
              overflow: "auto",
              borderTop: `1px solid ${borderColor}`,
              padding: "12px 12px",
              fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
              fontSize: 11,
              lineHeight: 1.6,
              color: foreground,
              margin: 0,
            }}
          >
            {result.code.content}
          </pre>
        </details>
      ) : null}

      {result.render.visual_review &&
      result.render.visual_review.passed === false ? (
        <div
          style={{
            borderRadius: 12,
            border: "1px solid rgba(245,158,11,0.35)",
            background: "rgba(245,158,11,0.1)",
            padding: "10px 12px",
            fontSize: 12,
            lineHeight: 1.6,
            color: "#78350f",
          }}
        >
          <div style={{ fontWeight: 500 }}>
            Visual review warning:{" "}
            {result.render.visual_review.summary ||
              "The generated result still has presentation issues."}
          </div>
          {result.render.visual_review.issues &&
          result.render.visual_review.issues.length > 0 ? (
            <div style={{ marginTop: 4, opacity: 0.9 }}>
              {result.render.visual_review.issues.join(" ")}
            </div>
          ) : null}
        </div>
      ) : null}

      {result.render.retry_attempts ||
      Object.keys(result.timings).length > 0 ? (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 8,
            fontSize: 11,
            color: mutedForeground,
          }}
        >
          {result.render.quality ? (
            <span
              style={{
                borderRadius: 999,
                border: `1px solid ${borderColor}`,
                padding: "2px 8px",
              }}
            >
              quality: {result.render.quality}
            </span>
          ) : null}
          {typeof result.render.retry_attempts === "number" ? (
            <span
              style={{
                borderRadius: 999,
                border: `1px solid ${borderColor}`,
                padding: "2px 8px",
              }}
            >
              retries: {result.render.retry_attempts}
            </span>
          ) : null}
          {Object.keys(result.timings).length > 0 ? (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                borderRadius: 999,
                border: `1px solid ${borderColor}`,
                padding: "2px 8px",
              }}
            >
              <FieldTimeOutlined style={iconStyle(12)} />
              {Object.entries(result.timings)
                .map(([key, value]) => `${key} ${value}s`)
                .join(" · ")}
            </span>
          ) : null}
        </div>
      ) : null}

      {fullscreenUrl ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0,0,0,0.85)",
            padding: 24,
          }}
          onClick={() => setFullscreenUrl(null)}
        >
          <img
            src={fullscreenUrl}
            alt={"全屏数学动画输出"}
            style={{ maxHeight: "100%", maxWidth: "100%", objectFit: "contain" }}
          />
        </div>
      ) : null}
    </div>
  );
}

function Header({
  icon: Icon,
  title,
}: {
  icon: ComponentType<{ style?: CSSProperties }>;
  title: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontSize: 12,
        fontWeight: 500,
        color: foreground,
      }}
    >
      <Icon style={iconStyle(14)} />
      <span>{title}</span>
    </div>
  );
}
