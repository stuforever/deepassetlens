/**
 * 教学设置合页 tab 上下文：原仓三个路由页（textbooks/chapters/knowledge-points）
 * 合为 antd Tabs 后，页内流转路径链接（next/link）等价替换为切 tab 动作。
 * 独立文件避免外壳↔子页循环引用；脱离外壳单独渲染时为安全 no-op。
 */
import { createContext, useContext } from 'react';

export interface CurriculumTabCtx {
  goToTab: (key: 'textbooks' | 'chapters' | 'knowledge-points' | string) => void;
}

export const CurriculumTabContext = createContext<CurriculumTabCtx>({
  goToTab: () => {},
});

export function useCurriculumTab(): CurriculumTabCtx {
  return useContext(CurriculumTabContext);
}
