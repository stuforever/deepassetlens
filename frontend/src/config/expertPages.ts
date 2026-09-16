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

// ⑤R F1（批8）：工作台组→tutor 后台（复刻原仓 (workspace)/mother-questions×6+book+(utility)/settings/curriculum）
const MotherQuestionsAdmin = lazy(() => import(/* webpackChunkName: "dt-mq-admin" */ '../pages/tutor/admin/MotherQuestionsAdmin'));
const MotherQuestionNew = lazy(() => import(/* webpackChunkName: "dt-mq-new" */ '../pages/tutor/admin/MotherQuestionNew'));
const MotherQuestionPhoto = lazy(() => import(/* webpackChunkName: "dt-mq-photo" */ '../pages/tutor/admin/MotherQuestionPhoto'));
const MotherQuestionPhotoCenter = lazy(() => import(/* webpackChunkName: "dt-mq-photocenter" */ '../pages/tutor/admin/MotherQuestionPhotoCenter'));
const MotherQuestionAnalysis = lazy(() => import(/* webpackChunkName: "dt-mq-analysis" */ '../pages/tutor/admin/MotherQuestionAnalysis'));
const MotherQuestionReview = lazy(() => import(/* webpackChunkName: "dt-mq-review" */ '../pages/tutor/admin/MotherQuestionReview'));
const MotherQuestionTrash = lazy(() => import(/* webpackChunkName: "dt-mq-trash" */ '../pages/tutor/admin/MotherQuestionTrash'));
const BookAdmin = lazy(() => import(/* webpackChunkName: "dt-book-admin" */ '../pages/tutor/admin/BookAdmin'));
const SettingsAdmin = lazy(() => import(/* webpackChunkName: "dt-settings-admin" */ '../pages/tutor/admin/SettingsAdmin'));
const MotherQuestionDetail = lazy(() => import(/* webpackChunkName: "dt-mq-detail" */ '../pages/tutor/admin/MotherQuestionDetail'));

const TUTOR_ADMIN_PAGES: ExpertPageConfig[] = [
  { path: '/e/tutor/admin/mother-questions', element: MotherQuestionsAdmin, label: '母题库', menuKey: 'e:tutor:admin:mq' },
  { path: '/e/tutor/admin/mother-questions/new', element: MotherQuestionNew, label: '录题', menuKey: 'e:tutor:admin:mq:new' },
  { path: '/e/tutor/admin/mother-questions/photo', element: MotherQuestionPhoto, label: '拍照录题', menuKey: 'e:tutor:admin:mq:photo' },
  { path: '/e/tutor/admin/mother-questions/photo-center', element: MotherQuestionPhotoCenter, label: '拍照中心', menuKey: 'e:tutor:admin:mq:photocenter' },
  { path: '/e/tutor/admin/mother-questions/analysis', element: MotherQuestionAnalysis, label: '错题分析', menuKey: 'e:tutor:admin:mq:analysis' },
  { path: '/e/tutor/admin/mother-questions/review', element: MotherQuestionReview, label: '复习', menuKey: 'e:tutor:admin:mq:review' },
  { path: '/e/tutor/admin/mother-questions/trash', element: MotherQuestionTrash, label: '回收站', menuKey: 'e:tutor:admin:mq:trash' },
  // ⑤R F1：原仓 [mid] 详情页（卡片点击可达——功能 1:1 闭环，底册枚举外补齐）
  { path: '/e/tutor/admin/mother-questions/:mid', element: MotherQuestionDetail, label: '母题详情', menuKey: 'e:tutor:admin:mq:detail' },
  { path: '/e/tutor/admin/book', element: BookAdmin, label: '书源管理', menuKey: 'e:tutor:admin:book' },
  { path: '/e/tutor/admin/settings', element: SettingsAdmin, label: '教学设置', menuKey: 'e:tutor:admin:settings' },
  // ⑤R F1：原仓「设置管理」按钮目标 /settings/curriculum 的等值落点（与 /settings 同页 tab）
  { path: '/e/tutor/admin/settings/curriculum', element: SettingsAdmin, label: '教学设置', menuKey: 'e:tutor:admin:settings:curriculum' },
];

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
    ...TUTOR_ADMIN_PAGES,
  ],
};

/** 汇总所有专家自定义路由（routes.tsx 消费）。 */
export function expertPageRoutes(): ExpertPageConfig[] {
  return Object.values(EXPERT_PAGES).flat();
}

/**
 * ⑤R F1：路径解析（先精确后参数模式）——KeepAlive 页签架构无 <Routes>，
 * App.tsx 页签同步原用精确 pathname 匹配，:mid 等参数路由永不命中（落 chat 兜底）。
 * 本解析器补参数段匹配（':seg' 通配单段，段数必须相等）。
 */
export function matchExpertPage(pathname: string): ExpertPageConfig | undefined {
  const all = expertPageRoutes();
  const exact = all.find((p) => p.path === pathname);
  if (exact) return exact;
  const segs = pathname.split('/');
  return all.find((p) => {
    if (!p.path.includes(':')) return false;
    const ps = p.path.split('/');
    if (ps.length !== segs.length) return false;
    return ps.every((s, i) => s.startsWith(':') || s === segs[i]);
  });
}
