/**
 * 事件 Reducer 单测（P2-2：直接覆盖生产代码 thinkStreamReducer.ts）
 *
 * 验证核心场景：
 * 1. 同名工具连续执行不串台（按 tool_call_id 区分）
 * 2. 补判不删除 rejected 步骤，标记 superseded（保留完整转折历史）
 * 3. running 最终转 done/error
 * 4. tool_call_id 精确关联（decision ↔ tool）
 */

import { thinkReducer, decisionCommittedReducer, finalizeReducer, ThinkItem } from '../utils/thinkStreamReducer';

describe('ThinkStream 事件 Reducer（生产代码）', () => {
  describe('同名工具不串台', () => {
    test('两个 execute_sql 不同 tool_call_id 应产生两个步骤', () => {
      let ts: ThinkItem[] = [];
      ts = thinkReducer(ts, {
        task: '执行SQL', kind: 'skill', tool_call_id: 'call-001',
        step_id: 1, phase: 'running', result_status: 'running',
      });
      ts = thinkReducer(ts, {
        task: '执行SQL', kind: 'skill', tool_call_id: 'call-002',
        step_id: 2, phase: 'running', result_status: 'running',
      });
      expect(ts).toHaveLength(2);
      expect(ts[0].tool_call_id).toBe('call-001');
      expect(ts[1].tool_call_id).toBe('call-002');
    });

    test('同 tool_call_id 更新不新建', () => {
      let ts: ThinkItem[] = [];
      ts = thinkReducer(ts, { task: '执行SQL', tool_call_id: 'call-001', step_id: 1, phase: 'running' });
      ts = thinkReducer(ts, { task: '执行SQL', tool_call_id: 'call-001', step_id: 1, phase: 'done', result_summary: '返回3行' });
      expect(ts).toHaveLength(1);
      expect(ts[0].phase).toBe('done');
      expect(ts[0].result_summary).toBe('返回3行');
    });

    test('无 tool_call_id 且无 step_id 时新建不按 task 名合并', () => {
      let ts: ThinkItem[] = [];
      ts = thinkReducer(ts, { task: '读技能', phase: 'running' });
      ts = thinkReducer(ts, { task: '读技能', phase: 'running' });
      // v3.6: 去掉 task 名降级后，两个无 ID 的同 task 项应各为独立步骤
      expect(ts).toHaveLength(2);
    });
  });

  describe('补判保留失败历史（P2-2）', () => {
    test('rejected 后 committed 标记 superseded 而非删除', () => {
      let ts: ThinkItem[] = [];
      // 首次 decision_rejected 产生 rejected 步骤
      ts = thinkReducer(ts, {
        task: '执行SQL', kind: 'decision', tool_call_id: 'call-001',
        round_id: 'r1', tool_name: 'execute_sql', phase: 'rejected',
        live_reason: '范围与SQL不一致', result_status: 'error',
      });
      expect(ts).toHaveLength(1);
      expect(ts[0].phase).toBe('rejected');

      // 补判通过 committed
      ts = decisionCommittedReducer(ts, {
        tool_call_id: 'call-002', round_id: 'r2', tool_name: 'execute_sql',
        content: '已知:... 因此: 调用 execute_sql', task: '执行SQL',
      });

      // P2-2: rejected 步骤不删除，标记 superseded
      const rejectedStep = ts.find((t) => t.phase === 'rejected');
      expect(rejectedStep).toBeDefined();
      expect(rejectedStep!.superseded).toBe(true);

      // committed 步骤存在
      const committedStep = ts.find((t) => t.phase === 'committed');
      expect(committedStep).toBeDefined();
      expect(committedStep!.tool_call_id).toBe('call-002');
    });

    test('完整转折链：原判定 -> 拒绝 -> 修正 -> 成功', () => {
      let ts: ThinkItem[] = [];
      // 1. 原判定（committed，但将被拒绝重试）
      ts = decisionCommittedReducer(ts, {
        tool_call_id: 'call-001', round_id: 'r1', tool_name: 'execute_sql',
        content: '已知:查001 因此: 调用 execute_sql。范围: 客户001', task: '执行SQL',
      });
      // 2. 闸门拒绝（rejected）
      ts = thinkReducer(ts, {
        task: '执行SQL', kind: 'decision', tool_call_id: 'call-001',
        round_id: 'r1', tool_name: 'execute_sql', phase: 'rejected',
        result_status: 'error', live_reason: '范围校验失败: 越界',
      });
      // 3. 修正判定（committed，新 tool_call_id）
      ts = decisionCommittedReducer(ts, {
        tool_call_id: 'call-002', round_id: 'r2', tool_name: 'execute_sql',
        content: '已知:修正范围 因此: 调用 execute_sql。范围: 客户001,客户003', task: '执行SQL',
      });
      // 4. 执行成功
      ts = thinkReducer(ts, {
        task: '执行SQL', tool_call_id: 'call-002', step_id: 2, phase: 'done',
        result_summary: '返回3行',
      });

      // 验证完整历史保留
      expect(ts.length).toBeGreaterThanOrEqual(2); // rejected + committed
      const rejected = ts.find((t) => t.phase === 'rejected');
      const committed = ts.find((t) => t.phase === 'done' && t.tool_call_id === 'call-002');
      expect(rejected).toBeDefined();
      expect(rejected!.superseded).toBe(true);
      expect(committed).toBeDefined();
      expect(committed!.result_summary).toBe('返回3行');
    });
  });

  describe('running 转 done', () => {
    test('applyResponse 终态兜底：running -> done', () => {
      let ts: ThinkItem[] = [
        { task: '执行SQL', tool_call_id: 'call-001', phase: 'running', result_status: 'running' },
      ];
      ts = finalizeReducer(ts);
      expect(ts[0].phase).toBe('done');
      expect(ts[0].result_status).toBe('done');
    });

    test('error 状态不被 done 覆盖', () => {
      let ts: ThinkItem[] = [
        { task: '执行SQL', tool_call_id: 'call-001', phase: 'running', result_status: 'error' },
      ];
      ts = finalizeReducer(ts);
      expect(ts[0].phase).toBe('done');
      expect(ts[0].result_status).toBe('error');
    });

    test('rejected 状态不被 done 覆盖', () => {
      let ts: ThinkItem[] = [
        { task: '执行SQL', tool_call_id: 'call-001', phase: 'rejected', result_status: 'error' },
      ];
      ts = finalizeReducer(ts);
      expect(ts[0].phase).toBe('rejected');
    });
  });

  describe('tool_call_id 精确关联', () => {
    test('decision 和 tool 按 tool_call_id 关联', () => {
      let ts: ThinkItem[] = [];
      ts = decisionCommittedReducer(ts, {
        tool_call_id: 'call-001', round_id: 'r1', tool_name: 'execute_sql',
        content: '已知:... 因此: 调用 execute_sql', task: '执行SQL',
      });
      ts = thinkReducer(ts, {
        task: '执行SQL', tool_call_id: 'call-001', step_id: 1, phase: 'running',
      });
      expect(ts).toHaveLength(1);
      expect(ts[0].tool_call_id).toBe('call-001');
      expect(ts[0].live_reason).toContain('调用 execute_sql');
    });
  });

  describe('R1: 补判拆卡--retry_of_step 关联', () => {
    test('重试步骤带 retry_of_step 关联被拒绝步骤', () => {
      let ts: ThinkItem[] = [];
      // #1 首次校验SQL（rejected）
      ts = thinkReducer(ts, {
        task: '校验SQL', tool_call_id: 'call-001', step_id: 1, phase: 'rejected',
        tool_name: 'validate_safe_sql', result_status: 'rejected',
        reject_reason: 'SELECT 引用了 c.ind_cls_name，但 SQL 未 JOIN c',
      });
      // #2 修正后重试（后端推送 retry_of_step=1）
      ts = thinkReducer(ts, {
        task: '校验SQL', tool_call_id: 'call-002', step_id: 2, phase: 'running',
        tool_name: 'validate_safe_sql', result_status: 'running',
        retry_of_step: 1, live_reason: '已知:需补充 JOIN c。因此:修正后重新校验。',
      });

      // 验证两个独立步骤
      expect(ts).toHaveLength(2);
      const rejected = ts.find((t) => t.step_id === 1);
      const retry = ts.find((t) => t.step_id === 2);
      expect(rejected).toBeDefined();
      expect(rejected!.phase).toBe('rejected');
      expect(rejected!.reject_reason).toContain('未 JOIN c');
      expect(retry).toBeDefined();
      expect(retry!.retry_of_step).toBe(1);
      expect(retry!.live_reason).toContain('修正后重新校验');
    });

    test('rejected 步骤被重试后标记 superseded', () => {
      let ts: ThinkItem[] = [];
      ts = thinkReducer(ts, {
        task: '校验SQL', tool_call_id: 'call-001', step_id: 1, phase: 'rejected',
        tool_name: 'validate_safe_sql', result_status: 'rejected',
      });
      // 后端在推送 retry 步骤前，已把 rejected 步骤标记 superseded
      ts = ts.map((t) =>
        t.step_id === 1 && t.phase === 'rejected' && !t.superseded
          ? { ...t, superseded: true }
          : t
      );
      ts = thinkReducer(ts, {
        task: '校验SQL', tool_call_id: 'call-002', step_id: 2, phase: 'running',
        tool_name: 'validate_safe_sql', retry_of_step: 1,
      });

      const rejected = ts.find((t) => t.step_id === 1);
      expect(rejected!.superseded).toBe(true);
      const retry = ts.find((t) => t.step_id === 2);
      expect(retry!.retry_of_step).toBe(1);
    });
  });
});
