/**
 * ⑤批4（⑤e）：EXPERT_PAGES 实体化——①spec §七预留的静态注册表（{slug: [自定义页]}），
 * 首个真实用户=tutor 四页。routes.tsx 消费本表拼接专家自定义路由（扩展点验证）。
 * 纪律：页面是代码，卡是数据——本表只登记路由与组件映射，开关由卡 enabled 决定。
 */
import type { ComponentType } from 'react';
import { lazy } from 'react';

// ⑤e 四页（懒加载，chunk 独立）+ ⑤补补-3 自主学习页 + ⑤补补-4 精通之路页
export const TutorPractice = lazy(() => import(/* webpackChunkName: "tutor-practice" */ '../pages/tutor/TutorPractice'));
export const TutorWrongBook = lazy(() => import(/* webpackChunkName: "tutor-wrongbook" */ '../pages/tutor/TutorWrongBook'));
export const TutorReview = lazy(() => import(/* webpackChunkName: "tutor-review" */ '../pages/tutor/TutorReview'));
export const TutorProgress = lazy(() => import(/* webpackChunkName: "tutor-progress" */ '../pages/tutor/TutorProgress'));
export const TutorLearn = lazy(() => import(/* webpackChunkName: "tutor-learn" */ '../pages/tutor/TutorLearn'));
export const TutorPath = lazy(() => import(/* webpackChunkName: "tutor-path" */ '../pages/tutor/TutorPath'));

export interface ExpertPageConfig {
  path: string;            // 完整路由（/e/{slug}/...）
  element: ComponentType<any>;
  label: string;           // 页签名
  menuKey: string;         // 页签 key（AppTabs/KeepAlive 语义）
}

export const EXPERT_PAGES: Record<string, ExpertPageConfig[]> = {
  tutor: [
    { path: '/e/tutor/learn', element: TutorLearn, label: '自主学习', menuKey: 'e:tutor:learn' },
    { path: '/e/tutor/path', element: TutorPath, label: '精通之路', menuKey: 'e:tutor:path' },
    { path: '/e/tutor/practice', element: TutorPractice, label: '练习', menuKey: 'e:tutor:practice' },
    { path: '/e/tutor/review', element: TutorReview, label: '复习', menuKey: 'e:tutor:review' },
    { path: '/e/tutor/wrong-book', element: TutorWrongBook, label: '错题本', menuKey: 'e:tutor:wrongbook' },
    { path: '/e/tutor/progress', element: TutorProgress, label: '学情', menuKey: 'e:tutor:progress' },
  ],
};

/** 汇总所有专家自定义路由（routes.tsx 消费）。 */
export function expertPageRoutes(): ExpertPageConfig[] {
  return Object.values(EXPERT_PAGES).flat();
}
