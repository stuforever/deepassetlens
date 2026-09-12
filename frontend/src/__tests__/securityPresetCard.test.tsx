/**
 * 件 A/C（2026-09-12 极速模式 spec §三）安全控制中心「模式预设卡」最小前端测试。
 *
 * 遵循 chartRender.test.tsx 既有 jsdom 冒烟范式（零新依赖、无 testing-library）：
 * jest.mock 掉 ../services/api（页面挂载即拉清单），createRoot 渲染整页，断言：
 * ① 预设卡文案锚点（模式预设/极速模式/安全模式/当前：自定义）；
 * ② guards/capabilities 站态反推当前模式（turbo 组合 → 当前：极速 turbo；safe 组合 → 当前：安全 safe）；
 * ③ 极速按钮 = 风险确认弹窗（风险账文案）→ 确认后调 guardsApi.preset('turbo')；
 * ④ 安全按钮 = 直接切（无弹窗）→ guardsApi.preset('safe')。
 */
import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { Modal } from 'antd';
import SecurityControlCenter from '../pages/SecurityControlCenter';
import { guardsApi, capabilitiesApi } from '../services/api';

jest.mock('../services/api', () => ({
  guardsApi: {
    list: jest.fn(() => Promise.resolve({ data: { items: [], global_version: 0 } })),
    update: jest.fn(() => Promise.resolve({ data: {} })),
    probe: jest.fn(() => Promise.resolve({ data: {} })),
    events: jest.fn(() => Promise.resolve({ data: { items: [], total: 0 } })),
    resetDefaults: jest.fn(() => Promise.resolve({ data: {} })),
    preset: jest.fn(() => Promise.resolve({ data: { mode: 'turbo', stations: [], all_ok: true } })),
  },
  capabilitiesApi: {
    list: jest.fn(() => Promise.resolve({ data: { items: [], capability_version: 0 } })),
    manifest: jest.fn(() => Promise.resolve({ data: {} })),
    update: jest.fn(() => Promise.resolve({ data: {} })),
    probe: jest.fn(() => Promise.resolve({ data: {} })),
    events: jest.fn(() => Promise.resolve({ data: { items: [], total: 0 } })),
    resetDefaults: jest.fn(() => Promise.resolve({ data: {} })),
  },
}));

// antd v5 依赖 matchMedia（响应式）；jsdom 无此 API，需 polyfill 否则渲染即抛错（同 chartRender.test.tsx）
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
// rc-tabs/rc-trigger 在部分路径消费 ResizeObserver；jsdom 无此 API（stub 零依赖）
if (typeof (window as any).ResizeObserver === 'undefined') {
  (window as any).ResizeObserver = class {
    observe() {} unobserve() {} disconnect() {}
  };
}

const guardsList = guardsApi.list as jest.Mock;
const capsList = capabilitiesApi.list as jest.Mock;
const presetFn = guardsApi.preset as jest.Mock;

/** 最小守卫/能力桩（renderCapCard 等对缺省字段均 || 兜底，桩只需 id+enabled） */
const guard = (id: string, enabled: boolean) => ({ guard_id: id, title: id, enabled });
const cap = (id: string, enabled: boolean) => ({ capability_id: id, title: id, enabled });

/** turbo 组合（与后端 PRESET_STATIONS.turbo 同源：六站关二保留） */
const turboStations = () => {
  guardsList.mockImplementation(() => Promise.resolve({
    data: { items: [guard('template', false), guard('output', false), guard('engine_lock', false), guard('approval_track', false), guard('capability', false), guard('sql_safety', true)], global_version: 1 },
  }));
  capsList.mockImplementation(() => Promise.resolve({
    data: { items: [cap('decision_gate', false), cap('locate_budget', true)], capability_version: 1 },
  }));
};

/** safe 组合（全站开） */
const safeStations = () => {
  guardsList.mockImplementation(() => Promise.resolve({
    data: { items: [guard('template', true), guard('output', true), guard('engine_lock', true), guard('approval_track', true), guard('capability', true), guard('sql_safety', true)], global_version: 2 },
  }));
  capsList.mockImplementation(() => Promise.resolve({
    data: { items: [cap('decision_gate', true), cap('locate_budget', true)], capability_version: 2 },
  }));
};

const click = (el: Element) => act(() => {
  el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
});

/** 冲刷挂起任务：antd5 Modal.confirm 走独立并发根，需让出宏任务让 Scheduler 落盘 */
const flush = async (ms = 50) => {
  await act(async () => { await new Promise((r) => setTimeout(r, ms)); });
};

/** 渲染整页并冲刷挂载期 effect/promise（list 拉取→反推模式） */
async function renderPage() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => { root.render(<SecurityControlCenter />); });
  await flush();                        // 冲刷 list promise → setPresetMode
  return { container, root, unmount: () => act(() => { root.unmount(); }) };
}

const bodyText = () => document.body.textContent || '';
const buttonWithText = (text: string) =>
  Array.from(document.querySelectorAll('button')).find((b) => (b.textContent || '').includes(text));

beforeEach(() => {
  document.body.innerHTML = '';
  guardsList.mockImplementation(() => Promise.resolve({ data: { items: [], global_version: 0 } }));
  capsList.mockImplementation(() => Promise.resolve({ data: { items: [], capability_version: 0 } }));
  presetFn.mockImplementation(() => Promise.resolve({ data: { mode: 'turbo', stations: [], all_ok: true } }));
});

afterEach(() => {
  Modal.destroyAll();                   // 清理静态 confirm 独立根，防跨测试泄漏
});

describe('件 A/C 模式预设卡（安全控制中心，jsdom 冒烟）', () => {
  test('预设卡渲染：两按钮+当前模式默认自定义+说明行文案锚点，无渲染错误', async () => {
    const { container, unmount } = await renderPage();
    const text = container.textContent || '';
    expect(text).toContain('模式预设');
    expect(text).toContain('当前：自定义');
    expect(text).toContain('极速=六站关+SQL安全/定位预算保留');
    expect(text).toContain('安全=全站回位');
    expect(buttonWithText('极速模式')).toBeTruthy();
    expect(buttonWithText('安全模式')).toBeTruthy();
    unmount();
  });

  test('站态反推：turbo 组合（六站关二保留）→ 当前：极速 turbo', async () => {
    turboStations();
    const { container, unmount } = await renderPage();
    expect(container.textContent || '').toContain('当前：极速 turbo');
    unmount();
  });

  test('站态反推：safe 组合（全站开）→ 当前：安全 safe', async () => {
    safeStations();
    const { container, unmount } = await renderPage();
    expect(container.textContent || '').toContain('当前：安全 safe');
    unmount();
  });

  test('极速按钮：先弹风险确认（含风险账文案），确认后才调 preset("turbo")', async () => {
    const { unmount } = await renderPage();
    expect(presetFn).not.toHaveBeenCalled();
    click(buttonWithText('极速模式')!);
    await flush();                                            // 冲刷弹窗独立并发根
    expect(bodyText()).toContain('切换到极速模式（turbo）？');
    expect(bodyText()).toContain('SQL 不再过模板校验');        // 风险账：SQL 越界
    expect(bodyText()).toContain('数据破坏风险≈0');            // 风险账：引擎只读边界
    click(buttonWithText('切换到极速')!);                      // 弹窗 OK（danger 按钮）
    await flush();                                            // 冲刷 onOk promise 链
    expect(presetFn).toHaveBeenCalledTimes(1);
    expect(presetFn).toHaveBeenCalledWith('turbo');
    unmount();
  });

  test('安全按钮：无确认弹窗直接切，调 preset("safe")', async () => {
    const { unmount } = await renderPage();
    click(buttonWithText('安全模式')!);
    await flush();
    expect(bodyText()).not.toContain('切换到极速模式（turbo）？');
    expect(presetFn).toHaveBeenCalledTimes(1);
    expect(presetFn).toHaveBeenCalledWith('safe');
    unmount();
  });
});
