/**
 * 修复 ResizeObserver loop 良性告警（根因 + 兜底双层）。
 *
 * 根因：antd/rc-table/rc-select 等第三方组件内部用 ResizeObserver 做尺寸测量，
 * 在回调中改动元素尺寸，使浏览器在同一帧内检测到观察循环，报
 * "ResizeObserver loop completed with undelivered notifications"，并触发
 * webpack-dev-server 错误浮层（"Uncaught runtime errors:"）。
 *
 * 修复1（根因）：把 ResizeObserver 回调延迟到下一帧（requestAnimationFrame），
 *   打破同帧观察循环，浏览器不再生成该错误——任何监听通道都不会再收到它。
 * 修复2（兜底）：window 捕获阶段拦截该特定 error 消息，防止其他通道把错误喂给浮层。
 *
 * 用法：应用入口（index.tsx）render 前调用一次。
 */
const _RESIZE_OBSERVER_LOOP_RE = /ResizeObserver loop/i;

/** 标记：已 patch 的原生构造函数，防止重复包装 */
const _PATCHED_MARK = '__tupuRoPatched';

export function patchResizeObserverLoop(): () => void {
  const NativeRO: typeof ResizeObserver | undefined = window.ResizeObserver;
  if (!NativeRO) return () => {};

  // 防重复 patch（热更新 / 多次调用）
  if ((NativeRO as any)[_PATCHED_MARK]) return () => {};

  const PatchedRO = class extends NativeRO {
    constructor(callback: ResizeObserverCallback) {
      // 回调延迟到下一帧：观察循环被拆到两个帧，浏览器不再判定"同帧循环"
      super((entries, observer) => {
        requestAnimationFrame(() => callback(entries, observer));
      });
    }
  };
  (PatchedRO as any)[_PATCHED_MARK] = true;
  window.ResizeObserver = PatchedRO;

  return () => {
    window.ResizeObserver = NativeRO;
  };
}

/** 兜底：window 捕获阶段吞掉该特定错误消息（其他错误保持默认处理） */
export function suppressResizeObserverLoopError(): () => void {
  const handler = (event: ErrorEvent) => {
    const msg = event && event.message ? String(event.message) : '';
    if (_RESIZE_OBSERVER_LOOP_RE.test(msg)) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  };
  window.addEventListener('error', handler, true);
  return () => window.removeEventListener('error', handler, true);
}

/** 入口：根因 patch + 事件兜底一并生效；返回统一 cleanup */
export function initResizeObserverLoopGuard(): () => void {
  const cleanups: Array<() => void> = [
    patchResizeObserverLoop(),
    suppressResizeObserverLoopError(),
  ];
  return () => {
    cleanups.forEach((fn) => {
      try {
        fn();
      } catch {
        /* cleanup 失败不影响 */
      }
    });
  };
}
