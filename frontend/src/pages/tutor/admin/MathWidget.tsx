/**
 * 可拖拽数学小控件宿主（1:1 复刻自原仓 web/components/curriculum/MathWidget.tsx）：
 * 离线 math-widgets 资产按需注入，按 data-math-widget + data-opt 挂载
 * 数轴 numberline / 方程天平 balance / 几何画板 geoboard。加载失败静默降级。
 */
import { useEffect, useRef } from 'react';

const WIDGET_JS = encodeURI(
  '/api/v1/grade7/数学/assets/scripts/math-widgets.js',
);
const WIDGET_CSS = encodeURI(
  '/api/v1/grade7/数学/assets/scripts/math-widgets.css',
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
  assetsLoaded = new Promise((resolve, reject) => {
    // CSS
    if (!document.querySelector(`link[href="${WIDGET_CSS}"]`)) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
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
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () => {
        assetsLoaded = null;
        reject(new Error('math-widgets.js failed to load'));
      });
      return;
    }
    const script = document.createElement('script');
    script.src = WIDGET_JS;
    script.onload = () => resolve();
    script.onerror = () => {
      assetsLoaded = null;
      reject(new Error('math-widgets.js failed to load'));
    };
    document.head.appendChild(script);
  });
  return assetsLoaded;
}

export interface MathFigure {
  type: string;
  config?: Record<string, unknown>;
}

export function MathWidget({
  figure,
  className = '',
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
        el.innerHTML = '';
        const node = document.createElement('div');
        node.setAttribute('data-math-widget', figure.type);
        // setAttribute 存原始字符串（HTML 实体转义只适用于 innerHTML 写法——
        // 带 &quot; 的 JSON 使 mountWidgets 解析 data-opt 必败=控件挂载失败）
        node.setAttribute('data-opt', JSON.stringify(figure.config || {}));
        el.appendChild(node);
        window.MATH_mountWidgets();
      })
      .catch(() => {
        /* 控件加载失败时静默降级（保留公式/文字说明） */
      });

    return () => {
      cancelled = true;
      if (el) el.innerHTML = '';
    };
  }, [figure]);

  if (!figure || !figure.type) return null;

  return (
    <div
      ref={containerRef}
      data-testid="math-widget"
      data-math-figure-type={figure.type}
      className={`mw-host overflow-hidden rounded-lg border bg-background ${className}`}
      style={{ overflow: 'hidden', borderRadius: 8, border: '1px solid #f0f0f0', background: '#fff' }}
    />
  );
}

export default MathWidget;
