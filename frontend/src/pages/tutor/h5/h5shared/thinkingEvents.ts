// 复刻自 DeepTutor 原仓 web/lib/thinking-events.ts（整件 1:1，零替换点）。
// —— H5 深度思考状态行的纯函数层
export interface ThinkingBurst {
  startedAt: number;
  count: number;
}

const BOUNDARY_TYPES = new Set(["content", "tool_call", "tool_result"]);

export function getActiveThinkingBurst(events: any[]): ThinkingBurst | null {
  if (!events || events.length === 0) return null;
  let burstStart = -1;
  let count = 0;
  for (const ev of events) {
    const type = String(ev?.type || "");
    if (BOUNDARY_TYPES.has(type)) {
      burstStart = -1;
      count = 0;
      continue;
    }
    if (type === "thinking") {
      if (burstStart < 0) {
        burstStart =
          typeof ev?.timestamp === "number" ? ev.timestamp : Date.now() / 1000;
        count = 0;
      }
      count += 1;
    }
    // progress / observation / sources 等不打断段
  }
  return burstStart >= 0 ? { startedAt: burstStart, count } : null;
}

export function formatThinkingElapsed(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  if (total < 60) return `${total}秒`;
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}分${String(s).padStart(2, "0")}秒`;
}
