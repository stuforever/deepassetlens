/**
 * ResizeObserver loop 良性告警修复逻辑单测（生产代码 suppressResizeObserverLoop.ts）。
 *
 * 覆盖：
 * 1. patchResizeObserverLoop：回调经 requestAnimationFrame 延迟执行（打破同帧循环，根因修复）；
 * 2. patchResizeObserverLoop：重复 patch 幂等，不叠加包装；
 * 3. suppressResizeObserverLoopError："ResizeObserver loop" 消息被吞（后续监听器不触发），
 *    其他错误消息正常透传；
 * 4. initResizeObserverLoopGuard：一键初始化根因 + 兜底。
 */
import {
  patchResizeObserverLoop,
  suppressResizeObserverLoopError,
  initResizeObserverLoopGuard,
} from '../utils/suppressResizeObserverLoop';

describe('ResizeObserver loop 告警修复', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('patchResizeObserverLoop（根因：rAF 延迟回调）', () => {
    test('回调经 requestAnimationFrame 延迟执行', () => {
      let capturedCb: ((entries: any, obs: any) => void) | null = null;
      class FakeRO {
        constructor(cb: (entries: any, obs: any) => void) {
          capturedCb = cb;
        }
        observe() {}
        unobserve() {}
        disconnect() {}
      }
      const nativeRO = window.ResizeObserver;
      (window as any).ResizeObserver = FakeRO;
      const cleanup = patchResizeObserverLoop();

      const cb = jest.fn();
      new (window.ResizeObserver as any)(cb);
      expect(capturedCb).not.toBeNull();

      // rAF 被 mock 为立即执行：回调经 rAF 后执行一次
      const raf = jest
        .spyOn(window, 'requestAnimationFrame')
        .mockImplementation((fn: any) => {
          fn(0);
          return 0;
        });
      capturedCb!([], null);
      expect(cb).toHaveBeenCalledTimes(1);
      expect(raf).toHaveBeenCalledTimes(1);

      raf.mockRestore();
      cleanup();
      (window as any).ResizeObserver = nativeRO;
    });

    test('重复 patch 幂等（不叠加包装）', () => {
      // jsdom 无原生 ResizeObserver，先注入一个真值类
      class FakeRO2 {
        constructor(_cb: any) {}
        observe() {}
        unobserve() {}
        disconnect() {}
      }
      (window as any).ResizeObserver = FakeRO2;
      const nativeRO = window.ResizeObserver;
      const cleanup1 = patchResizeObserverLoop();
      const patched = window.ResizeObserver;
      expect(patched).not.toBe(nativeRO);
      const cleanup2 = patchResizeObserverLoop();
      // 第二次 patch 不改变（防叠加包装导致回调被延迟多层）
      expect(window.ResizeObserver).toBe(patched);
      cleanup1();
      cleanup2();
    });
  });

  describe('suppressResizeObserverLoopError（兜底：吞特定错误消息）', () => {
    test('ResizeObserver loop 消息被吞掉（不触发后续监听器）', () => {
      const cleanup = suppressResizeObserverLoopError();
      const secondHandler = jest.fn();
      window.addEventListener('error', secondHandler);

      const event = new ErrorEvent('error', {
        message: 'ResizeObserver loop completed with undelivered notifications.',
      });
      const preventDefaultSpy = jest.spyOn(event, 'preventDefault');
      window.dispatchEvent(event);

      expect(secondHandler).not.toHaveBeenCalled();
      expect(preventDefaultSpy).toHaveBeenCalled();

      window.removeEventListener('error', secondHandler);
      cleanup();
    });

    test('其他错误消息不受影响，正常透传', () => {
      const cleanup = suppressResizeObserverLoopError();
      const secondHandler = jest.fn();
      window.addEventListener('error', secondHandler);

      const event = new ErrorEvent('error', { message: 'Something else broke' });
      window.dispatchEvent(event);

      expect(secondHandler).toHaveBeenCalledTimes(1);

      window.removeEventListener('error', secondHandler);
      cleanup();
    });
  });

  describe('initResizeObserverLoopGuard（一键初始化）', () => {
    test('初始化不抛错，cleanup 幂等可调用', () => {
      const cleanup = initResizeObserverLoopGuard();
      expect(typeof cleanup).toBe('function');
      cleanup();
      cleanup(); // 二次调用不抛错
    });
  });
});
