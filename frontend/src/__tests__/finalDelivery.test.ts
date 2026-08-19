/**
 * 统一最终交付显示逻辑单测（最终结果交付任务书 §7 前端验收）
 *
 * 直接覆盖生产代码 finalDelivery.ts（与 thinkStreamReducer.test.ts 同一模式）：
 * 1. final_answer 为空但 sql_result 有 101 行时，仍展示"共返回 101 条记录"和数据表
 * 2. final_delivery 有摘要时，显示在结果区，不进入 ThinkStream
 * 3. "兼容降级"不阻止最终答案和表格显示
 * 4. final 事件已到、done.final_answer 为空时，前端保留 final 事件中的答案，不得覆盖为空
 */

import { buildFinalDeliveryView, resolveFinalAnswer } from '../utils/finalDelivery';
import type { ChatMessagePayload } from '../components/conversation/types';

describe('统一最终交付显示（生产代码 finalDelivery.ts）', () => {
  describe('final_answer 为空但 sql_result 有数据时仍展示结果', () => {
    test('sql_result 101 行 -> 展示"共返回 101 条"与数据表开关', () => {
      const payload: ChatMessagePayload = {
        final_answer: '',
        sql_result: {
          columns: ['cust_name', 'transformer_name'],
          rows: Array.from({ length: 101 }, (_, i) => [i, i]),
          row_count: 101,
          result_available_for_ui: true,
        },
      };
      const view = buildFinalDeliveryView(payload);
      expect(view.showTable).toBe(true);
      expect(view.deliverySummaryLine).toContain('共返回 101 条');
      expect(view.deliverySummaryLine).toContain('完整明细见下方查询结果表');
    });

    test('无 final_delivery 时由 row_count 确定性生成摘要行', () => {
      const payload: ChatMessagePayload = {
        final_answer: '',
        sql_result: { columns: ['a'], rows: [[1], [2]], row_count: 2 },
      };
      const view = buildFinalDeliveryView(payload);
      expect(view.showTable).toBe(true);
      expect(view.deliverySummaryLine).toContain('2 条');
    });

    test('row_count 为 0 时不显示数据表', () => {
      const payload: ChatMessagePayload = {
        final_answer: '未查询到符合当前条件的数据。',
        sql_result: { columns: ['a'], rows: [], row_count: 0 },
      };
      const view = buildFinalDeliveryView(payload);
      expect(view.showTable).toBe(false);
      expect(view.deliverySummaryLine).toBeNull();
    });
  });

  describe('存在权威查询结果表时屏蔽模型 Markdown 表格', () => {
    test('result_available_for_ui=true 且 sql_result 有数据 -> maskMarkdownTables=true', () => {
      const payload: ChatMessagePayload = {
        final_answer: '| 客户类型 | 客户编号 |\n|---|---|\n| 用电户 | 101 |',
        final_delivery: { title: '查询结果', row_count: 101, result_available_for_ui: true },
        sql_result: { columns: ['客户类型'], rows: [['用电户']], row_count: 101 },
      };
      const view = buildFinalDeliveryView(payload);
      expect(view.maskMarkdownTables).toBe(true);
    });

    test('知识问答（无权威结果表）时不屏蔽 Markdown 表格', () => {
      const payload: ChatMessagePayload = {
        final_answer: '| 概念 | 定义 |\n|---|---|\n| 变压器 | ... |',
      };
      const view = buildFinalDeliveryView(payload);
      expect(view.showTable).toBe(false);
      expect(view.maskMarkdownTables).toBe(false);
    });
  });

  describe('final_delivery 摘要进入结果区而非 ThinkStream', () => {
    test('摘要显示在结果区，不进入 thinkStream', () => {
      const payload: ChatMessagePayload = {
        final_answer: '',
        final_delivery: {
          title: '查询结果',
          summary: ['共返回 101 条，完整明细见下方查询结果表。'],
        },
        thinkStream: [{ task: '执行SQL', kind: 'skill', draft: 'SQL 执行细节' }],
        sql_result: { columns: ['a'], rows: [[1]], row_count: 1 },
      };
      const view = buildFinalDeliveryView(payload);
      expect(view.summary[0]).toContain('共返回 101 条');
      // 摘要只进结果区（view.summary），不注入思考区（view 无 thinkStream 字段）
      expect((view as any).thinkStream).toBeUndefined();
    });
  });

  describe('兼容降级不阻止最终答案和表格显示', () => {
    test('degraded 时答案与表格仍保留，提示文案为"结果已基于实际查询数据生成"', () => {
      const payload: ChatMessagePayload = {
        final_answer: '结果已基于实际查询数据生成',
        final_delivery: { title: '查询结果', summary: ['共返回 101 条记录'] },
        response_format_degraded: true,
        sql_result: { columns: ['a'], rows: [[1]], row_count: 101 },
      };
      const view = buildFinalDeliveryView(payload);
      expect(view.showTable).toBe(true);
      expect(view.summary[0]).toContain('101');
      expect(view.degradedNotice).toBe('结果已基于实际查询数据生成');
    });

    test('降级提示只在有真实查询数据时显示（知识问答不误显示）', () => {
      const payload: ChatMessagePayload = {
        final_answer: '变压器是一种静止的电气设备。',
        response_format_degraded: true,
      };
      const view = buildFinalDeliveryView(payload);
      expect(view.showTable).toBe(false);
      expect(view.degradedNotice).toBeNull();
    });
  });

  describe('答案保留优先级（final 事件已到、done.final_answer 为空）', () => {
    test('done.final_answer 为空但 final 事件已写入 payload -> 保留，不覆盖为空', () => {
      const answer = resolveFinalAnswer('', '已通过 final 事件获得的答案', []);
      expect(answer).toBe('已通过 final 事件获得的答案');
    });

    test('done.final_answer 优先于 payload 答案', () => {
      const answer = resolveFinalAnswer('done 答案', 'final 事件答案', []);
      expect(answer).toBe('done 答案');
    });

    test('都为空时回退 answer draft', () => {
      const answer = resolveFinalAnswer('', '', [{ kind: 'answer', draft: '草稿答案' }]);
      expect(answer).toBe('草稿答案');
    });

    test('全为空返回空串（不产生虚假答案）', () => {
      expect(resolveFinalAnswer('', '', [])).toBe('');
    });
  });
});
