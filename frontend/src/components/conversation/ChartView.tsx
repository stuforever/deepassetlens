/**
 * S3a（G8 自动图表）—— 查询结果自动图表（零新依赖，全 inline-style + tokens）。
 *
 * 形态（由 utils/chartShape.detectChartShape 判定，仅形态可识别时渲染）：
 * - bar     : 两列（维度+数值）-> 横向占比条 TopN=10（行高 22px / 行距 6px / 条高 10px 圆角 5px /
 *             宽度=值/最大值百分比 / chartPalette 顺序循环 / 左维度名 12px textSecondary ellipsis 8 字 /
 *             右数值 dal-num 12px textPrimary）
 * - minibar : 首列时间 + 数值列 -> 迷你柱状（容器高 120px / 柱宽自适应 min 8px / 柱色 chartPalette[0] /
 *             hover antd Tooltip（维度+值）/ 基线 1px 分割线 colorBorderSecondary）
 */
import React, { useMemo } from 'react';
import { Tooltip } from 'antd';
import { tokens } from '../../theme/tokens';
import { toNumber, cellAt, rowToArray } from '../../utils/chartShape';
import type { ChartShape } from '../../utils/chartShape';
import type { SqlResultData } from './SqlResultTable';

const BAR_TOP_N = 10;
const DIM_MAX_CHARS = 8;

type ChartViewProps = {
  data: SqlResultData | null;
  shape: ChartShape;
};

const ChartView: React.FC<ChartViewProps> = ({ data, shape }) => {
  const columns = useMemo(() => data?.columns || [], [data]);
  const rows = useMemo(() => data?.rows || [], [data]);

  // —— 占比条数据（维度 + 数值，TopN=10，降序）——
  const barItems = useMemo(() => {
    if (shape?.kind !== 'bar' || columns.length < 2) return [];
    return rows
      .map((r) => {
        const arr = rowToArray(r, columns);
        const dim = String(arr[0] ?? '').trim();
        const val = toNumber(arr[1]);
        return { dim, val: val === null ? 0 : val };
      })
      .filter((i) => i.dim !== '')
      .sort((a, b) => b.val - a.val)
      .slice(0, BAR_TOP_N);
  }, [shape, columns, rows]);

  // —— 迷你柱状数据（时间标签 + 首个数值列）——
  const miniItems = useMemo(() => {
    if (shape?.kind !== 'minibar' || columns.length < 2) return [];
    const valueCol = columns.findIndex((_, ci) =>
      ci > 0 && rows.some((r) => toNumber(cellAt(r, columns, ci)) !== null),
    );
    if (valueCol < 0) return [];
    return rows.map((r) => {
      const arr = rowToArray(r, columns);
      const label = String(arr[0] ?? '');
      const val = toNumber(arr[valueCol]);
      return { label, val: val === null ? 0 : val };
    });
  }, [shape, columns, rows]);

  // 图表
  const node = useMemo(() => {
    if (shape?.kind === 'bar') {
      const max = Math.max(1, ...barItems.map((i) => i.val));
      if (barItems.length === 0) return null;
      return (
        <div style={{ padding: '4px 4px 8px' }}>
          {barItems.map((i, idx) => {
            const pct = Math.max(1, Math.round((i.val / max) * 100));
            const color = tokens.chartPalette[idx % tokens.chartPalette.length];
            return (
              <div
                key={`${i.dim}-${idx}`}
                style={{ display: 'flex', alignItems: 'center', gap: 8, height: 22, marginBottom: 6 }}
              >
                <span
                  style={{
                    width: 140,
                    flex: '0 0 140px',
                    fontSize: 12,
                    color: tokens.colors.textSecondary,
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                  }}
                  title={i.dim.length > DIM_MAX_CHARS ? i.dim : undefined}
                >
                  {i.dim.length > DIM_MAX_CHARS ? `${i.dim.slice(0, DIM_MAX_CHARS)}…` : i.dim}
                </span>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ flex: 1, height: 10, background: tokens.colors.bgSubtle, borderRadius: 5 }}>
                    <div
                      style={{
                        width: `${pct}%`,
                        height: 10,
                        borderRadius: 5,
                        background: color,
                        transition: `width ${tokens.motion.duration.base}ms ${tokens.motion.easing.enter}`,
                      }}
                    />
                  </div>
                  <span className="dal-num" style={{ fontSize: 12, color: tokens.colors.textPrimary, minWidth: 48, textAlign: 'right' }}>
                    {i.val}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      );
    }
    if (shape?.kind === 'minibar') {
      const max = Math.max(1, ...miniItems.map((i) => i.val));
      if (miniItems.length === 0) return null;
      const n = miniItems.length;
      const gap = 8;
      const barW = Math.max(8, Math.floor((100 - gap * (n - 1)) / n));
      return (
        <div style={{ padding: '4px 4px 0', height: 120, display: 'flex', alignItems: 'flex-end', gap, position: 'relative' }}>
          <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 1, background: tokens.colors.border }} />
          {miniItems.map((i, idx) => {
            const h = Math.max(2, Math.round((i.val / max) * 100));
            return (
              <Tooltip key={`${i.label}-${idx}`} title={`${i.label}：${i.val}`}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: barW, height: '100%', justifyContent: 'flex-end', cursor: 'default' }}>
                  <div
                    style={{
                      width: barW,
                      height: h,
                      borderRadius: 3,
                      background: tokens.chartPalette[0],
                      transition: `height ${tokens.motion.duration.base}ms ${tokens.motion.easing.enter}`,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 10,
                      color: tokens.colors.textTertiary,
                      maxWidth: 72,
                      overflow: 'hidden',
                      whiteSpace: 'nowrap',
                      textOverflow: 'ellipsis',
                      lineHeight: '12px',
                    }}
                  >
                    {i.label}
                  </span>
                </div>
              </Tooltip>
            );
          })}
        </div>
      );
    }
    return null;
  }, [shape, barItems, miniItems]);

  if (!node) return null;
  return (
    <div style={{ marginTop: 8, border: `1px solid ${tokens.colors.border}`, borderRadius: tokens.radius.card, padding: '4px 12px 8px', background: tokens.colors.bgContent, boxShadow: tokens.elevation.s1 }}>
      {node}
    </div>
  );
};

export default React.memo(ChartView);
