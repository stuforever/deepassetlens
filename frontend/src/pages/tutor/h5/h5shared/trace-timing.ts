/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 lib/trace-timing.ts，61 行）。
 * 消费方：h5shared/TracePanels.tsx（批9 F2 闭包，随本波次交付）。
 * 替换点：仅 import 路径 "@/lib/unified-ws" → "../../admin/unified-ws"（批8 件，
 * StreamEvent 契约一致）；其余逐字未改。
 */
import type { StreamEvent } from "../../admin/unified-ws";

/**
 * Elapsed seconds for the turn the ``events`` belong to.
 *
 * Returns ``null`` when the stream has not produced any timestamped
 * event yet (e.g. the optimistic assistant placeholder before the
 * first server frame arrives).
 *
 * While ``isStreaming`` is true the upper bound floats to
 * ``nowSeconds`` so the label ticks up in real time; once streaming
 * ends the bound collapses to the latest event timestamp and the
 * duration freezes.
 */
export function getTurnDurationSeconds(
  events: StreamEvent[],
  nowSeconds: number,
  isStreaming: boolean,
): number | null {
  let min = Number.POSITIVE_INFINITY;
  let max = 0;
  for (const event of events) {
    const ts = event.timestamp;
    if (typeof ts !== "number") continue;
    if (ts < min) min = ts;
    if (ts > max) max = ts;
  }
  if (!Number.isFinite(min)) return null;
  const end = isStreaming ? Math.max(nowSeconds, max) : max;
  return Math.max(0, end - min);
}

/** Compact human-readable duration: ``"12s"``, ``"1m 4s"``, ``"1h 2m"``. */
export function formatTurnDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  if (total < 60) return `${total}s`;
  const minutes = Math.floor(total / 60);
  const remSeconds = total % 60;
  if (minutes < 60) {
    return remSeconds === 0 ? `${minutes}m` : `${minutes}m ${remSeconds}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remMinutes = minutes % 60;
  return remMinutes === 0 ? `${hours}h` : `${hours}h ${remMinutes}m`;
}
