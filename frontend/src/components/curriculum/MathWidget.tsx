"use client";

import { useEffect, useRef } from "react";

const WIDGET_JS = encodeURI(
  "/api/v1/grade7/数学/assets/scripts/math-widgets.js",
);
const WIDGET_CSS = encodeURI(
  "/api/v1/grade7/数学/assets/scripts/math-widgets.css",
);

declare global {
  interface Window {
    MATH_mountWidgets?: () => void;
    MATH_initNumberLine?: (el: HTMLElement, opt: unknown) => void;
    MATH_initBalance?: (el: HTMLElement, opt: unknown) => void;
    MATH_initGeoBoard?: (el: HTMLElement, opt: unknown) => void;
  }
}

let assetsLoaded: Promise<void> | null = null;

function loadWidgetAssets(): Promise<void> {
  if (assetsLoaded) return assetsLoaded;
  if (typeof window === "undefined") {
    return Promise.reject(new Error("window unavailable"));
  }
  assetsLoaded = new Promise((resolve, reject) => {
    // CSS
    if (!document.querySelector(`link[href="${WIDGET_CSS}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = WIDGET_CSS;
      document.head.appendChild(link);
    }
    // JS
    if (window.MATH_mountWidgets) {
      resolve();
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${WIDGET_JS}"]`,
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => {
        assetsLoaded = null;
        reject(new Error("math-widgets.js failed to load"));
      });
      return;
    }
    const script = document.createElement("script");
    script.src = WIDGET_JS;
    script.onload = () => resolve();
    script.onerror = () => {
      assetsLoaded = null;
      reject(new Error("math-widgets.js failed to load"));
    };
    document.head.appendChild(script);
  });
  return assetsLoaded;
}

export interface MathFigure {
  type: string;
  config?: Record<string, unknown>;
}

/**
 * 可拖拽数学小控件（离线 math-widgets）：数轴 numberline / 方程天平 balance / 几何画板 geoboard。
 * 加载一次 math-widgets.js，按 data-math-widget + data-opt 挂载拖拽控件。
 */
export function MathWidget({
  figure,
  className = "",
}: {
  figure: MathFigure | null | undefined;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!figure || !figure.type) return;
    let cancelled = false;

    loadWidgetAssets()
      .then(() => {
        if (cancelled || !window.MATH_mountWidgets) return;
        el.innerHTML = "";
        const node = document.createElement("div");
        node.setAttribute("data-math-widget", figure.type);
        node.setAttribute(
          "data-opt",
          JSON.stringify(figure.config || {}),
        );
        el.appendChild(node);
        window.MATH_mountWidgets();
      })
      .catch(() => {
        /* 控件加载失败时静默降级（保留公式/文字说明） */
      });

    return () => {
      cancelled = true;
      if (el) el.innerHTML = "";
    };
  }, [figure?.type, figure?.config]); // R3批 Minor：deps 对齐实际消费字段（整对象引用变化不重渲染）

  if (!figure || !figure.type) return null;

  return (
    <div
      ref={containerRef}
      data-testid="math-widget"
      data-math-figure-type={figure.type}
      className={`mw-host overflow-hidden rounded-lg border bg-background ${className}`}
    />
  );
}
