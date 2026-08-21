/**
 * S3a（G8 自动图表）形态检测纯函数单测（直接覆盖生产代码 utils/chartShape.ts）
 *
 * 验证核心场景：
 * 1. 两列（维度+数值）-> bar（横向占比条）
 * 2. 首列时间 + 数值列 -> minibar（迷你柱状，时间优先于占比条）
 * 3. 其余（单列无值 / 三列 / 无数值 / 空数据）-> null（不显示切换）
 */

import { detectChartShape, toNumber, toDateVal } from '../utils/chartShape';

describe('detectChartShape 形态检测（S3a）', () => {
  test('两列 维度+数值 -> bar（占比条）', () => {
    const cols = ['承压名称', '客户数'];
    const rows = [['承压名称1', 3], ['承压名称2', 5], ['承压名称3', 2]];
    expect(detectChartShape(cols, rows)).toEqual({ kind: 'bar' });
  });

  test('首列时间 + 数值 -> minibar（时间优先）', () => {
    const cols = ['月份', '金额'];
    const rows = [['2026-07', 120], ['2026-08', 88]];
    expect(detectChartShape(cols, rows)).toEqual({ kind: 'minibar' });
  });

  test('数字字符串时间（时间戳/日期串）也可识别为 minibar', () => {
    const cols = ['日期', '数量'];
    const rows = [['2026-08-20', 3], ['2026-08-21', 5]];
    expect(detectChartShape(cols, rows)).toEqual({ kind: 'minibar' });
  });

  test('单列无数值 -> null（不可识别）', () => {
    const cols = ['客户名称'];
    const rows = [['客户1'], ['客户2']];
    expect(detectChartShape(cols, rows)).toBeNull();
  });

  test('三列 -> null（超出两列形态）', () => {
    const cols = ['客户', '合同容量', '运行容量'];
    const rows = [['客户1', 1, 2], ['客户2', 3, 4]];
    expect(detectChartShape(cols, rows)).toBeNull();
  });

  test('两列但第 2 列非数值 -> null', () => {
    const cols = ['维度', '名称'];
    const rows = [['A', '名称1'], ['B', '名称2']];
    expect(detectChartShape(cols, rows)).toBeNull();
  });

  test('空数据 / 空列 -> null', () => {
    expect(detectChartShape([], [])).toBeNull();
    expect(detectChartShape(['a', 'b'], [])).toBeNull();
    expect(detectChartShape(undefined, undefined)).toBeNull();
  });

  test('对象数组行（兼容后端 rows 为对象）', () => {
    const cols = ['维度', '数量'];
    const rows = [{ 维度: 'A', 数量: 3 }, { 维度: 'B', 数量: 5 }];
    expect(detectChartShape(cols, rows as unknown as unknown[])).toEqual({ kind: 'bar' });
  });
});

describe('toNumber / toDateVal 宽松解析', () => {
  test('数值与数字字符串', () => {
    expect(toNumber(3)).toBe(3);
    expect(toNumber('3.5')).toBe(3.5);
    expect(toNumber('abc')).toBeNull();
    expect(toNumber(null)).toBeNull();
  });

  test('时间解析', () => {
    expect(toDateVal('2026-08-20')).not.toBeNull();
    expect(toDateVal('2026-08-20 10:00:00')).not.toBeNull();
    expect(toDateVal('not-a-date')).toBeNull();
  });
});
