"use client";

import { useCallback, useEffect, useState } from "react";

export function useMeasuredHeight<T extends HTMLElement>() {
  // 三轨M6 顺手修(:9)：callback ref——目标元素条件渲染/换节点时重新观察
  //（原 effect 空依赖 + ref.current 一次性捕获 → height 恒 0 或观察已脱离 DOM 旧节点）。
  const [node, setNode] = useState<T | null>(null);
  const [height, setHeight] = useState(0);

  const ref = useCallback((element: T | null) => {
    setNode(element);
  }, []);

  useEffect(() => {
    if (!node || typeof ResizeObserver === "undefined") return;

    const updateHeight = () =>
      setHeight(node.getBoundingClientRect().height);
    updateHeight();

    const observer = new ResizeObserver(() => updateHeight());
    observer.observe(node);
    return () => observer.disconnect();
  }, [node]);

  return { ref, height };
}
