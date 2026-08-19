/**
 * ThinkStream 事件聚合 Reducer（P2-2：从 FreePlanChat.tsx 提取，供测试直接覆盖生产代码）
 *
 * 核心规则：
 * 1. 同名工具连续执行不串台（按 tool_call_id / step_id 区分，不按 task 名降级）
 * 2. 补判不删除 rejected 步骤，改为标记 superseded（保留完整转折历史）
 * 3. running 最终转 done/error
 * 4. tool_call_id 精确关联（decision ↔ tool）
 */

export interface ThinkItem {
  task?: string;
  kind?: string;
  tool_call_id?: string;
  step_id?: number | null;
  phase?: string;
  result_status?: string;
  result_summary?: string;
  live_reason?: string;
  round_id?: string;
  tool_name?: string;
  reason?: string;
  duration_ms?: number;
  superseded?: boolean;
  retry_of_step?: number;   // R1: 补判重试关联的被拒绝步骤号
  reject_reason?: string;   // R1: 闸门拒绝原因
  [key: string]: any;
}

/**
 * think 事件聚合：按 tool_call_id / step_id 匹配现有步骤，找不到新建。
 * v3.6: 不按 task 名降级（防同名工具串台）。
 */
export function thinkReducer(currentThink: ThinkItem[], thinkItem: ThinkItem): ThinkItem[] {
  const tcidKey = thinkItem.tool_call_id;
  const sidKey = thinkItem.step_id;
  let existIdx = -1;
  if (tcidKey) existIdx = currentThink.findIndex((t) => t.tool_call_id === tcidKey);
  if (existIdx === -1 && sidKey != null) existIdx = currentThink.findIndex((t) => t.step_id === sidKey);
  // v3.6: 不按 task 名降级（防串台）

  if (existIdx >= 0) {
    // 合并：保留已有 live_reason（来自 decision_committed），thinkItem 的 live_reason 作兜底
    return currentThink.map((t, idx) =>
      idx === existIdx
        ? { ...t, ...thinkItem, live_reason: t.live_reason || thinkItem.live_reason }
        : t
    );
  }
  return [...currentThink, thinkItem];
}

/**
 * decision_committed 事件聚合：补判通过时，不删除 rejected 步骤，
 * 改为标记 superseded（P2-2：保留完整转折和修正过程）。
 */
export function decisionCommittedReducer(
  ts: ThinkItem[],
  payload: {
    tool_call_id?: string;
    round_id?: string;
    tool_name?: string;
    content?: string;
    task?: string;
  }
): ThinkItem[] {
  const { tool_call_id: tcid, round_id: roundId, tool_name: toolName, content, task } = payload;
  // P2-2: 不删除 rejected 步骤，改为标记 superseded（保留补判失败历史）
  const marked = toolName
    ? ts.map((t) =>
        t.phase === 'rejected' && t.tool_name === toolName && !t.superseded
          ? { ...t, superseded: true }
          : t
      )
    : ts;

  let idx = -1;
  if (roundId) idx = marked.findIndex((t) => t.round_id === roundId);
  if (idx === -1 && tcid) idx = marked.findIndex((t) => t.tool_call_id === tcid);
  if (idx === -1) {
    // 新建 committed 步骤
    return [...marked, {
      task,
      strategy: 'free_plan',
      kind: 'decision',
      phase: 'committed',
      tool_call_id: tcid,
      live_reason: content,
      round_id: roundId,
      tool_name: toolName,
    }];
  }
  // 覆盖校准：用完整 content 覆盖
  return marked.map((t, i) =>
    i === idx
      ? { ...t, phase: 'committed', live_reason: content, tool_call_id: tcid, task: task || t.task }
      : t
  );
}

/**
 * applyResponse 终态兜底：running/drafting/committed -> done。
 * result_status 保留 error，其它统一标 done。
 */
export function finalizeReducer(ts: ThinkItem[]): ThinkItem[] {
  return ts.map((t) => {
    if (t.phase === 'running' || t.phase === 'drafting' || t.phase === 'committed') {
      return { ...t, phase: 'done', result_status: t.result_status === 'error' ? 'error' : 'done' };
    }
    return t;
  });
}
