/**
 * S3a（G8）图表渲染冒烟测试 —— 本会话无 IAB 浏览器工具（mcp__node_repl__js 不可用），
 * 用 jsdom（CRA jest 默认环境）+ React 18 createRoot 渲染 ChartView / SqlResultTable，
 * 等价覆盖「图表渲染路径 0 渲染错误 + Segmented 切换出现」的验收项③（浏览器直测的降级替代）。
 *
 * 零新依赖：只用 react-dom + react（项目既有）。
 */
import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import ChartView from '../components/conversation/ChartView';
import SqlResultTable from '../components/conversation/SqlResultTable';
import type { ChartShape } from '../utils/chartShape';
import type { SqlResultData } from '../components/conversation/SqlResultTable';

// antd v5 依赖 matchMedia（响应式）；jsdom 无此 API，需 polyfill 否则渲染即抛错
if (!window.matchMedia) {
  (window as any).matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

function renderInto(jsx: React.ReactElement): { container: HTMLDivElement; root: any } {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => { root.render(jsx); });
  return { container, root };
}

function unmount(root: any) {
  act(() => { root.unmount(); });
}

describe('S3a 图表渲染冒烟（jsdom 替代浏览器直测）', () => {
  test('占比条：两列数值 -> 维度名 + 数值可见，无渲染错误', () => {
    const shape: ChartShape = { kind: 'bar' };
    const data: SqlResultData = {
      columns: ['电压等级', '客户数'],
      rows: [['承压名称1', 3], ['承压名称2', 5], ['承压名称3', 1]],
      row_count: 3,
    };
    const { container, root } = renderInto(<ChartView shape={shape} data={data} />);
    const text = container.textContent || '';
    expect(text).toContain('承压名称1');
    expect(text).toContain('承压名称2');
    expect(text).toContain('承压名称3');
    expect(text).toContain('5');
    unmount(root);
  });

  test('迷你柱状：时间首列 -> 时间标签渲染，无渲染错误', () => {
    const shape: ChartShape = { kind: 'minibar' };
    const data: SqlResultData = {
      columns: ['日期', '客户数'],
      rows: [['2024-03-30', 3], ['2024-04-18', 2]],
      row_count: 2,
    };
    const { container, root } = renderInto(<ChartView shape={shape} data={data} />);
    const text = container.textContent || '';
    expect(text).toContain('2024-03-30');
    expect(text).toContain('2024-04-18');
    unmount(root);
  });

  test('形状为 null -> 不渲染（空），无渲染错误', () => {
    const data: SqlResultData = { columns: ['a'], rows: [['x']], row_count: 1 };
    const { container, root } = renderInto(<ChartView shape={null} data={data} />);
    expect((container.textContent || '').trim()).toBe('');
    unmount(root);
  });

  test('SqlResultTable：两列数值 -> 「表格|图表」Segmented 出现，无渲染错误', () => {
    const data: SqlResultData = {
      columns: ['电压等级', '客户数'],
      rows: [['承压名称1', 3], ['承压名称2', 5]],
      row_count: 2,
    };
    const { container, root } = renderInto(<SqlResultTable data={data} />);
    const text = container.textContent || '';
    expect(text).toContain('表格');
    expect(text).toContain('图表');
    expect(text).toContain('承压名称1');
    unmount(root);
  });
});

describe('明细表头中英双显（2026-09-12 用户需求）', () => {
  test('columns_cn 有值 -> 表头中文主行 + 英文技术名次行同现', () => {
    const data: SqlResultData = {
      columns: ['wbs_element', 'objnr'],
      columns_cn: ['WBS元素', '对象编号'],
      rows: [['元素A', 'PD1'], ['元素B', 'PD2']],
      row_count: 2,
    };
    const { container, root } = renderInto(<SqlResultTable data={data} />);
    const text = container.textContent || '';
    expect(text).toContain('WBS元素');       // 中文主行
    expect(text).toContain('对象编号');
    expect(text).toContain('wbs_element');  // 英文次行保留
    expect(text).toContain('objnr');
    unmount(root);
  });

  test('无 columns_cn / 映射缺失 -> 回退单行英文现状（不渲染空行）', () => {
    const data: SqlResultData = {
      columns: ['wbs_element', '重过载台区数'],
      rows: [['元素A', 3], ['元素B', 5]],
      row_count: 2,
    };
    const { container, root } = renderInto(<SqlResultTable data={data} />);
    const text = container.textContent || '';
    expect(text).toContain('wbs_element');
    expect(text).toContain('重过载台区数');
    unmount(root);
  });
});
