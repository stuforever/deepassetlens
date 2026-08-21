/**
 * S3a（G8 自动图表）形态检测纯函数。
 * 依据 S 阶段设计 §S3a：仅形态可识别时返回图表形态（不可识别返回 null，前端不显示切换）。
 *
 * 规则：
 * - 两列（维度 + 数值）-> bar（横向占比条 TopN=10）；
 * - 首列可解析为时间（且存在数值列）-> minibar（迷你柱状时间序列）；
 * - 其余 -> null（不切换）。
 */

export type ChartShape =
  | { kind: 'bar' }     // 两列（维度+数值）-> 横向占比条 TopN=10
  | { kind: 'minibar' } // 首列时间 + 数值 -> 迷你柱状
  | null;

const NUM_RE = /^-?\d+(\.\d+)?$/;

/** 宽松数值解析（number 或数字字符串 -> number；否则 null） */
export function toNumber(v: unknown): number | null {
  if (typeof v === 'number' && !Number.isNaN(v)) return v;
  if (typeof v === 'string' && NUM_RE.test(v.trim())) return Number(v.trim());
  return null;
}

/** 时间解析（Date / ISO 字符串 / 数字时间戳[毫秒或秒] -> Date；否则 null） */
export function toDateVal(v: unknown): Date | null {
  if (v === null || v === undefined) return null;
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : v;
  if (typeof v === 'number') {
    const d = new Date(v > 1e12 ? v : v * 1000);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  if (typeof v === 'string') {
    const t = v.trim();
    if (!t) return null;
    const d = new Date(t);
    if (!Number.isNaN(d.getTime())) return d;
    if (NUM_RE.test(t)) {
      const n = Number(t);
      const d2 = new Date(n > 1e12 ? n : n * 1000);
      if (!Number.isNaN(d2.getTime())) return d2;
    }
  }
  return null;
}

/** 取行内第 ci 列单元格（兼容 rows 为数组或对象数组） */
export function cellAt(row: unknown, columns: string[], ci: number): unknown {
  if (Array.isArray(row)) return row[ci];
  if (row && typeof row === 'object') return (row as Record<string, unknown>)[columns[ci]];
  return undefined;
}

/** 行 -> 数组（对象数组按列序展开，统一下游消费） */
export function rowToArray(row: unknown, columns: string[]): unknown[] {
  if (Array.isArray(row)) return row;
  if (row && typeof row === 'object') return columns.map((c) => (row as Record<string, unknown>)[c]);
  return [];
}

/**
 * 形态检测：两列（维度+数值）-> bar；首列时间且含数值列 -> minibar；否则 null。
 * 时间优先（时间序列画迷你柱状比占比条更贴切）；两列非时间 -> 占比条。
 */
export function detectChartShape(columns: string[] | undefined, rows: unknown[] | undefined): ChartShape {
  if (!columns || columns.length === 0 || !rows || rows.length === 0) return null;
  const firstCell = cellAt(rows[0], columns, 0);
  const isTimeSeries = toDateVal(firstCell) !== null;
  // 首列时间 -> 迷你柱状（需存在数值列；取首个数值列或第 2 列）
  if (isTimeSeries) {
    const valueCol = columns.findIndex((_, ci) => {
      if (ci === 0) return false;
      return rows.some((r) => toNumber(cellAt(r, columns, ci)) !== null);
    });
    if (valueCol >= 0) return { kind: 'minibar' };
    return null; // 只有时间列无数值 -> 不可识别
  }
  // 两列且第 2 列为数值 -> 占比条
  if (columns.length === 2) {
    const hasNum = rows.some((r) => toNumber(cellAt(r, columns, 1)) !== null);
    if (hasNum) return { kind: 'bar' };
  }
  return null;
}
