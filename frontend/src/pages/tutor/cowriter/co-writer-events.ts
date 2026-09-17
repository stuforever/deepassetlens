/**
 * 逐字移植自原仓 web/lib/co-writer-events.ts（28 行）。
 * 纯浏览器事件总线，无依赖、无替换点（typeof window 守卫保留）。
 */

const EVENT_NAME = "co-writer:changed";

type Listener = () => void;

function getTarget(): EventTarget | null {
  if (typeof window === "undefined") return null;
  return window;
}

export function notifyCoWriterChanged(): void {
  const target = getTarget();
  if (!target) return;
  target.dispatchEvent(new Event(EVENT_NAME));
}

export function subscribeCoWriterChanges(listener: Listener): () => void {
  const target = getTarget();
  if (!target) return () => {};
  target.addEventListener(EVENT_NAME, listener);
  return () => target.removeEventListener(EVENT_NAME, listener);
}
