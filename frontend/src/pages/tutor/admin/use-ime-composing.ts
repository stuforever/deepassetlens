/**
 * 复刻自 DeepTutor 原仓 web/lib/use-ime-composing.ts（整件 1:1，无替换点）。
 * 聊天输入框共享的 IME 组合态守卫：组合期间 Enter 确认候选词而非提交。
 */

import { useCallback, useRef } from "react";

export function useImeComposing() {
  const isComposingRef = useRef(false);

  const onCompositionStart = useCallback(() => {
    isComposingRef.current = true;
  }, []);

  const onCompositionEnd = useCallback(() => {
    // Some IMEs fire compositionend before the Enter keydown that confirms
    // a candidate, so keep the guard through the current event turn.
    setTimeout(() => {
      isComposingRef.current = false;
    }, 0);
  }, []);

  return { isComposingRef, onCompositionStart, onCompositionEnd };
}
