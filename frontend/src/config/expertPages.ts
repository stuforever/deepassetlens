/**
 * ⑤批4（⑤e）：EXPERT_PAGES 实体化——①spec §七预留的静态注册表（{slug: [自定义页]}），
 * 首个真实用户=tutor 四页。routes.tsx 消费本表拼接专家自定义路由（扩展点验证）。
 * 纪律：页面是代码，卡是数据——本表只登记路由与组件映射，开关由卡 enabled 决定。
 */
import type { ComponentType } from 'react';
import { createElement, lazy } from 'react';
import RequireAdmin from '../components/RequireAdmin';

/**
 * ⑤R F4（批11）11.3：ACL 联调位——tutor 后台页面统一包 RequireAdmin（manage 语义，
 * 前端守卫管体验不管安全，执法在批16 vendor shim 统一门）。auth=0 快路径匿名=admin 不破开发链路。
 */
const withAdminGuard = (C: ComponentType<any>): ComponentType<any> => (props: any) =>
  createElement(RequireAdmin, null, createElement(C, props));

// ⑤R R1（批12）：先行版六页退役（TutorLearn/Path/Practice/Review/WrongBook/Progress）——
// §3.3.5 终版菜单由 DT h5 复刻件（TUTOR_H5_PAGES）取代，本表注册项随批12 移除。

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

// ⑤R F2（批9）：h5 组→tutor 空间（复刻原仓 app/h5/*——移动形态 H5Shell 壳+12 页）
const H5Home = lazy(() => import(/* webpackChunkName: "dt-h5-home" */ '../pages/tutor/h5/H5Home'));
const H5Chat = lazy(() => import(/* webpackChunkName: "dt-h5-chat" */ '../pages/tutor/h5/H5Chat'));
const H5Learn = lazy(() => import(/* webpackChunkName: "dt-h5-learn" */ '../pages/tutor/h5/H5Learn'));
const H5LearnTextbook = lazy(() => import(/* webpackChunkName: "dt-h5-learn-tb" */ '../pages/tutor/h5/H5LearnTextbook'));
const H5Classroom = lazy(() => import(/* webpackChunkName: "dt-h5-classroom" */ '../pages/tutor/h5/H5Classroom'));
const H5Review = lazy(() => import(/* webpackChunkName: "dt-h5-review" */ '../pages/tutor/h5/H5Review'));
const H5Wrong = lazy(() => import(/* webpackChunkName: "dt-h5-wrong" */ '../pages/tutor/h5/H5Wrong'));
const H5WrongBook = lazy(() => import(/* webpackChunkName: "dt-h5-wrongbook" */ '../pages/tutor/h5/H5WrongBook'));
const H5Paths = lazy(() => import(/* webpackChunkName: "dt-h5-paths" */ '../pages/tutor/h5/H5Paths'));
const H5PathBook = lazy(() => import(/* webpackChunkName: "dt-h5-path-book" */ '../pages/tutor/h5/H5PathBook'));
const H5Report = lazy(() => import(/* webpackChunkName: "dt-h5-report" */ '../pages/tutor/h5/H5Report'));
const H5Atlas = lazy(() => import(/* webpackChunkName: "dt-h5-atlas" */ '../pages/tutor/h5/H5Atlas'));
const H5BookRead = lazy(() => import(/* webpackChunkName: "dt-h5-book" */ '../pages/tutor/h5/H5BookRead'));
const H5Me = lazy(() => import(/* webpackChunkName: "dt-h5-me" */ '../pages/tutor/h5/H5Me'));
const H5Share = lazy(() => import(/* webpackChunkName: "dt-h5-share" */ '../pages/tutor/h5/H5Share'));

const TUTOR_H5_PAGES: ExpertPageConfig[] = [
  { path: '/e/tutor/h5', element: H5Home, label: '首页', menuKey: 'e:tutor:h5:home' },
  { path: '/e/tutor/h5/chat', element: H5Chat, label: '对话', menuKey: 'e:tutor:h5:chat' },
  { path: '/e/tutor/h5/learn', element: H5Learn, label: '学习', menuKey: 'e:tutor:h5:learn' },
  { path: '/e/tutor/h5/learn/textbook', element: H5LearnTextbook, label: '教材学', menuKey: 'e:tutor:h5:learn:textbook' },
  { path: '/e/tutor/h5/classroom', element: H5Classroom, label: '课堂', menuKey: 'e:tutor:h5:classroom' },
  { path: '/e/tutor/h5/review', element: H5Review, label: '复习', menuKey: 'e:tutor:h5:review' },
  { path: '/e/tutor/h5/wrong', element: H5Wrong, label: '错题录入', menuKey: 'e:tutor:h5:wrong' },
  { path: '/e/tutor/h5/wrongbook', element: H5WrongBook, label: '错题本', menuKey: 'e:tutor:h5:wrongbook' },
  { path: '/e/tutor/h5/paths', element: H5Paths, label: '精通之路', menuKey: 'e:tutor:h5:paths' },
  // ⑤R F4（批11）：详情路由（书路径/教材阅读）不进菜单—— flows 内可达
  { path: '/e/tutor/h5/paths/:bookId', element: H5PathBook, label: '书路径', menuKey: 'e:tutor:h5:paths:book', hideInMenu: true },
  { path: '/e/tutor/h5/report', element: H5Report, label: '学情报告', menuKey: 'e:tutor:h5:report' },
  { path: '/e/tutor/h5/atlas', element: H5Atlas, label: '知识地图', menuKey: 'e:tutor:h5:atlas' },
  { path: '/e/tutor/h5/book/:bookId', element: H5BookRead, label: '教材阅读', menuKey: 'e:tutor:h5:book', hideInMenu: true },
  { path: '/e/tutor/h5/me', element: H5Me, label: '我的', menuKey: 'e:tutor:h5:me' },
  { path: '/e/tutor/h5/share', element: H5Share, label: '分享', menuKey: 'e:tutor:h5:share' },
];

const TUTOR_ADMIN_PAGES: ExpertPageConfig[] = [
  // ⑤R F4（批11）：后台三项顶级入口（adminTop）——AppSider admin 段；子页/详情页 hideInMenu
  { path: '/e/tutor/admin/mother-questions', element: withAdminGuard(MotherQuestionsAdmin), label: '母题库管理', menuKey: 'e:tutor:admin:mq', adminTop: true },
  { path: '/e/tutor/admin/mother-questions/new', element: withAdminGuard(MotherQuestionNew), label: '录题', menuKey: 'e:tutor:admin:mq:new', hideInMenu: true },
  { path: '/e/tutor/admin/mother-questions/photo', element: withAdminGuard(MotherQuestionPhoto), label: '拍照录题', menuKey: 'e:tutor:admin:mq:photo', hideInMenu: true },
  { path: '/e/tutor/admin/mother-questions/photo-center', element: withAdminGuard(MotherQuestionPhotoCenter), label: '拍照中心', menuKey: 'e:tutor:admin:mq:photocenter', hideInMenu: true },
  { path: '/e/tutor/admin/mother-questions/analysis', element: withAdminGuard(MotherQuestionAnalysis), label: '错题分析', menuKey: 'e:tutor:admin:mq:analysis', hideInMenu: true },
  { path: '/e/tutor/admin/mother-questions/review', element: withAdminGuard(MotherQuestionReview), label: '复习', menuKey: 'e:tutor:admin:mq:review', hideInMenu: true },
  { path: '/e/tutor/admin/mother-questions/trash', element: withAdminGuard(MotherQuestionTrash), label: '回收站', menuKey: 'e:tutor:admin:mq:trash', hideInMenu: true },
  // ⑤R F1：原仓 [mid] 详情页（卡片点击可达——功能 1:1 闭环，底册枚举外补齐）
  { path: '/e/tutor/admin/mother-questions/:mid', element: withAdminGuard(MotherQuestionDetail), label: '母题详情', menuKey: 'e:tutor:admin:mq:detail', hideInMenu: true },
  { path: '/e/tutor/admin/book', element: withAdminGuard(BookAdmin), label: '书源管理', menuKey: 'e:tutor:admin:book', adminTop: true },
  { path: '/e/tutor/admin/settings', element: withAdminGuard(SettingsAdmin), label: '教学设置', menuKey: 'e:tutor:admin:settings', adminTop: true },
  // ⑤R F1：原仓「设置管理」按钮目标 /settings/curriculum 的等值落点（与 /settings 同页 tab）
  { path: '/e/tutor/admin/settings/curriculum', element: withAdminGuard(SettingsAdmin), label: '教学设置', menuKey: 'e:tutor:admin:settings:curriculum', hideInMenu: true },
];

export interface ExpertPageConfig {
  path: string;            // 完整路由（/e/{slug}/...）
  element: ComponentType<any>;
  label: string;           // 页签名
  menuKey: string;         // 页签 key（AppTabs/KeepAlive 语义）
  /** ⑤R F4（批11）：侧栏菜单终版——详情路由/先行版页不出菜单（路由保留至 R1 退役） */
  hideInMenu?: boolean;
  /** ⑤R F4（批11）：tutor 后台三项顶级入口（母题库管理/书源管理/教学设置）——AppSider admin 段消费 */
  adminTop?: boolean;
}

export const EXPERT_PAGES: Record<string, ExpertPageConfig[]> = {
  tutor: [
    // ⑤R R1（批12）：先行版六页退役移除（§3.3.5 终版=DT h5 复刻件）
    ...TUTOR_ADMIN_PAGES,
    ...TUTOR_H5_PAGES,
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
