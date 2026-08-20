/**
 * 融合 M3 G7 前端测试：证据胶囊（第 6 枚）+ 置信度三级。
 *
 * 遵循项目纯函数测试模式（无 testing-library、零新依赖）：
 * 直接断言 buildCapsules 的产物——证据胶囊 key/label/summary/状态色点。
 */
import { buildCapsules } from '../components/conversation/contractCards/ContractCardsPanel';
import type { QueryContractView, RouteResult } from '../components/conversation/contractCards/types';

const route: RouteResult = { route_type: 'generic', skill_id: '__generic__' };
const contract: QueryContractView = {
  skill_id: '__generic__', workflow_step: 'generic', allowed_tools: ['search_entities'],
  scope: {}, selected_engine: 'doris', output_mode: 'single_result_table', stop_when: [],
};

describe('证据胶囊（融合 M3 G7）', () => {
  test('证据胶囊存在且为第 6 枚', () => {
    const caps = buildCapsules(route, contract, null, undefined);
    expect(caps.map((c) => c.key)).toEqual(['route', 'scope', 'engine', 'decision', 'stop', 'evidence']);
  });

  test('证据胶囊摘要：表清单 + 自评状态 + 置信度', () => {
    const evidence = {
      route: 'generic',
      tables: ['dim_cst_elec_cons_cust'],
      examples_used: [{ q: '统计用电客户总数', sim: 0.85 }],
      verification: { row_count: 3, null_rates: {}, warnings: [] },
      rubric: { status: 'satisfied', iterations: 1 },
      corrections: 0,
    };
    const caps = buildCapsules(route, contract, evidence, '高');
    const ev = caps.find((c) => c.key === 'evidence')!;
    expect(ev.label).toBe('证据');
    expect(ev.summary).toContain('1 表');
    expect(ev.summary).toContain('自评通过');
    expect(ev.summary).toContain('信高');
  });

  test('置信度三级 -> 状态色点（高绿/低红/缺省信息色）', () => {
    const evHi = buildCapsules(route, contract, null, '高').find((c) => c.key === 'evidence')!;
    const evLow = buildCapsules(route, contract, null, '低').find((c) => c.key === 'evidence')!;
    const evNone = buildCapsules(route, contract, null, undefined).find((c) => c.key === 'evidence')!;
    expect(evHi.dot).not.toBe(evLow.dot);
    expect(evNone.summary).toContain('未自评');
  });

  test('自纠次数进摘要（corrections>0）', () => {
    const evidence = { tables: [], rubric: { status: 'needs_revision' }, corrections: 2 };
    const caps = buildCapsules(route, contract, evidence, '中');
    const ev = caps.find((c) => c.key === 'evidence')!;
    expect(ev.summary).toContain('纠2');
    expect(ev.summary).toContain('信中');
  });

  test('无数据支撑告警进摘要（S1 零执行含数字）', () => {
    const evidence = { tables: [], rubric: null, corrections: 0, missing_data_support: true };
    const caps = buildCapsules(route, contract, evidence, '低');
    const ev = caps.find((c) => c.key === 'evidence')!;
    expect(ev.summary).toContain('无数据支撑');
    expect(ev.summary).toContain('信低');
  });
});
