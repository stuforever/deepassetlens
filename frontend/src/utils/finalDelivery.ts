/**
 * 统一最终交付显示逻辑（最终结果交付任务书 §5，从 AssistantCanvas/FreePlanChat 提取，供测试直接覆盖生产代码）
 *
 * 核心规则：
 * 1. sql_result.row_count > 0 时，无论模型是否生成文本，都显示结果表（前端分页）
 * 2. final_delivery.summary 显示在结果区（标题/摘要/发现/告警），不进入 ThinkStream
 * 3. "兼容降级"只说明"结果已基于实际查询数据生成"，不阻止最终答案和表格显示
 * 4. 答案保留优先级：done.final_answer → loading.payload.final_answer（final 事件已写入）→ answer draft
 */

import type { ChatMessagePayload, FinalDelivery, FinalFinding } from '../components/conversation/types';

export type FinalDeliveryView = {
  /** 最终结果标题（final_delivery.title，兜底"查询结果"） */
  title: string;
  /** 摘要（final_delivery.summary） */
  summary: string[];
  /** 关键发现（final_delivery.findings，指标卡/列表） */
  findings: FinalFinding[];
  /** 告警（final_delivery.warnings） */
  warnings: string[];
  /** 是否展示结果表（sql_result.row_count > 0 且有列） */
  showTable: boolean;
  /** 完整明细是否已由前端查询结果表展示（result_available_for_ui=true 或存在完整 sql_result） */
  result_available_for_ui: boolean;
  /** 存在权威查询结果表时，屏蔽 final_answer 中的 GFM Markdown 表格节点（明细只展示一次） */
  maskMarkdownTables: boolean;
  /** 主视图降级提示（有真实查询数据时显示"结果已基于实际查询数据生成"） */
  degradedNotice: string | null;
  /** 无模型文本时兜底展示的摘要行（"共 N 条，完整明细见下方查询结果表"） */
  deliverySummaryLine: string | null;
};

/**
 * 由消息 payload 构建最终交付视图模型。
 * final_answer 为空但 sql_result 有数据时，仍产出可展示的摘要行与表格开关。
 */
export function buildFinalDeliveryView(payload?: ChatMessagePayload | null): FinalDeliveryView {
  const delivery: FinalDelivery | undefined = payload?.final_delivery || undefined;
  const sqlResult = payload?.sql_result || null;
  const rows = sqlResult?.rows || [];
  const rowCount = sqlResult?.row_count ?? rows.length;
  const hasColumns = !!sqlResult?.columns && sqlResult.columns.length > 0;
  const showTable = rowCount > 0 && hasColumns;
  const degraded = !!(payload as any)?.response_format_degraded;
  const summary = delivery?.summary || [];
  const resultAvailableForUi = !!(delivery?.result_available_for_ui) || showTable;

  return {
    title: delivery?.title || '查询结果',
    summary,
    findings: delivery?.findings || [],
    warnings: delivery?.warnings || [],
    showTable,
    result_available_for_ui: resultAvailableForUi,
    // 存在权威查询结果表时屏蔽模型 Markdown 表格（明细只由前端结果表展示一次）
    maskMarkdownTables: resultAvailableForUi && showTable,
    // 降级提示只在有真实查询数据时展示，避免"知识问答"误显示
    degradedNotice: degraded && showTable ? '结果已基于实际查询数据生成' : null,
    // 无模型文本时：优先 delivery 摘要首行，其次按 row_count 确定性生成
    deliverySummaryLine:
      summary[0] ||
      (showTable ? `共返回 ${rowCount} 条，完整明细见下方查询结果表。` : null),
  };
}

/**
 * 最终答案保留优先级：done.final_answer → loading.payload.final_answer → answer draft。
 * final 事件已到、done.final_answer 为空时，保留 final 事件已写入的答案，不得覆盖为空。
 */
export function resolveFinalAnswer(
  doneFinalAnswer: string | undefined,
  payloadFinalAnswer: string | undefined,
  thinkStream?: Array<{ kind?: string; draft?: string; [k: string]: any }>,
): string {
  if (doneFinalAnswer) return doneFinalAnswer;
  if (payloadFinalAnswer) return payloadFinalAnswer;
  const draftItem = (thinkStream || []).find((t) => (t.kind === 'answer' || t.kind === 'draft') && t.draft);
  return draftItem?.draft || '';
}
