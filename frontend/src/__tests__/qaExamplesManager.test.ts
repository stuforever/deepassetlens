/**
 * M2a 示例库管理页（融合设计 §4.1）纯函数测试：状态/类型映射完整性。
 *
 * 状态与类型都回落到管理页 UI（StatusTag 预设、启停/审核操作分支），
 * 断言三者语义一致：已知状态/类型都有标签且 preset 合法、操作语义自洽。
 */
import { STATUS_META, TYPE_META } from '../pages/QaExamplesManager';

describe('示例库管理页（G1 §4.1）', () => {
  test('三状态都有中文标签且 preset 合法（成功/警示/停用）', () => {
    const keys = Object.keys(STATUS_META).sort();
    expect(keys).toEqual(['disabled', 'enabled', 'review']);
    for (const [k, v] of Object.entries(STATUS_META)) {
      expect(v.label.length).toBeGreaterThan(0);
      expect(['success', 'warning', 'disabled', 'info']).toContain(v.preset);
      // 启停语义自洽：enabled=成功 且 label=启用，disabled=停用
      if (k === 'enabled') { expect(v.preset).toBe('success'); expect(v.label).toBe('启用'); }
      if (k === 'disabled') { expect(v.label).toBe('停用'); }
      if (k === 'review') { expect(v.preset).toBe('warning'); expect(v.label).toBe('待审核'); }
    }
  });

  test('三类示例类型都有标签与 preset', () => {
    const keys = Object.keys(TYPE_META).sort();
    expect(keys).toEqual(['golden', 'manual', 'user_confirmed']);
    for (const v of Object.values(TYPE_META)) {
      expect(v.label.length).toBeGreaterThan(0);
      expect(['success', 'info', 'ai']).toContain(v.preset);
    }
    expect(TYPE_META.golden.preset).toBe('ai');          // 金标与 AI 语义一致
    expect(TYPE_META.user_confirmed.preset).toBe('success'); // 用户确认即成功语义
  });
});
