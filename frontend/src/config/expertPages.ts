/**
 * ⑤批4（⑤e）：EXPERT_PAGES 实体化——①spec §七预留的静态注册表（{slug: [自定义页]}），
 * 首个真实用户=tutor 四页。routes.tsx 消费本表拼接专家自定义路由（扩展点验证）。
 * 纪律：页面是代码，卡是数据——本表只登记路由与组件映射，开关由卡 enabled 决定。
 */
import type { ComponentType } from 'react';
import { createElement, lazy } from 'react';
import RequireExpert from '../components/RequireAdmin';

/**
 * ⑤R F4（批11）11.3：ACL 联调位——sishu 后台页面统一包 RequireAdmin（manage 语义，
 * 前端守卫管体验不管安全；数据面执法=v4批6-15 require_expert 全量挂载+批15 auth=1 探针组后方成立）。
 * auth=0 快路径匿名=admin 不破开发链路。
 * ⑤R R3（权限联调收口）：功能页（h5 组+笔记本）统一包 withUseGuard（use 语义，A-4 分层）——
 * R3 权限三态 e2e 发现 h5 页缺 use 守卫（student2 无 grant 直连可见内容），本批补齐联调位。
 * IA 件批1：守卫专家参数化（expertId 参数，默认 'sishu'）——tutor-h5 空间页传 'tutor-h5'。
 */
const withAdminGuard = (C: ComponentType<any>, expertId: string = 'sishu'): ComponentType<any> => (props: any) =>
  createElement(RequireExpert, { action: 'manage', expertId, children: createElement(C, props) });
const withUseGuard = (C: ComponentType<any>, expertId: string = 'sishu'): ComponentType<any> => (props: any) =>
  createElement(RequireExpert, { action: 'use', expertId, children: createElement(C, props) });

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
const BookWorkbench = lazy(() => import(/* webpackChunkName: "dt-book-workbench" */ '../pages/tutor/book/BookWorkbench'));
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

// ⑤R R3（笔记本页补建）：原仓 (utility)/notebook/page.tsx 1:1——spec 2.6 #7 规划
// /e/sishu/notebook（F2 复查发现仅 picker 链落位、页面本体缺位，R3 补齐）
// IA 件批1：笔记本随 h5 组迁入 tutor-h5 空间（spec §3.1 h5 组 12 项含笔记本）→ /e/tutor-h5/notebook
const NotebookPage = lazy(() => import(/* webpackChunkName: "dt-notebook" */ '../pages/tutor/notebook/NotebookPage'));

// IA批6 6.3：AI写作+伙伴+桌面自主学习（DT (workspace) 组复刻件落位）
// 编辑页/新建/详情为动线子页（hideInMenu——列表卡/新建入口可达，1:1 闭环）；
// 守卫：co-writer/self-learning=use；partners 三页=manage（plan 6.3 裁决，批3 comment 预告）。
const CowriterList = lazy(() => import(/* webpackChunkName: "dt-cowriter-list" */ '../pages/tutor/cowriter/CowriterList'));
const CowriterEditor = lazy(() => import(/* webpackChunkName: "dt-cowriter-editor" */ '../pages/tutor/cowriter/CowriterEditor'));
const PartnersList = lazy(() => import(/* webpackChunkName: "dt-partners-list" */ '../pages/tutor/partners/PartnersList'));
const PartnersNew = lazy(() => import(/* webpackChunkName: "dt-partners-new" */ '../pages/tutor/partners/PartnersNew'));
const PartnerDetail = lazy(() => import(/* webpackChunkName: "dt-partners-detail" */ '../pages/tutor/partners/PartnerDetail'));
const SelfLearning = lazy(() => import(/* webpackChunkName: "dt-self-learning" */ '../pages/tutor/learning/SelfLearning'));

// 引擎批2 2.5/2.6：DT 桌面对话窗口（home 页复刻壳+桥 SSE 态源——AgentChatContext）。
// 静态路径 /e/sishu/chat 压过 routes.tsx 的 /e/:slug/chat 参数路由（v6 静态优先）；
// ExpertChat 收归 wenshu（/e/wenshu/chat）——计划 2.6。
const TutorHomeChat = lazy(() => import(/* webpackChunkName: "dt-tutor-home-chat" */ '../pages/tutor/chat/TutorHomeChat'));

const TUTOR_H5_PAGES: ExpertPageConfig[] = [
  // IA 件批1：16 条路由从 /e/sishu/{h5,notebook} 迁出 → /e/tutor-h5/*（menuKey 同步换前缀）；
  // 守卫传 'tutor-h5'（use 语义不变——A-4 分层，API 面四执法点为真执法）
  { path: '/e/tutor-h5', element: withUseGuard(H5Home, 'tutor-h5'), label: '首页', menuKey: 'e:tutor-h5:home' },
  { path: '/e/tutor-h5/chat', element: withUseGuard(H5Chat, 'tutor-h5'), label: '对话', menuKey: 'e:tutor-h5:chat' },
  { path: '/e/tutor-h5/learn', element: withUseGuard(H5Learn, 'tutor-h5'), label: '学习', menuKey: 'e:tutor-h5:learn' },
  { path: '/e/tutor-h5/learn/textbook', element: withUseGuard(H5LearnTextbook, 'tutor-h5'), label: '教材学', menuKey: 'e:tutor-h5:learn:textbook' },
  { path: '/e/tutor-h5/classroom', element: withUseGuard(H5Classroom, 'tutor-h5'), label: '课堂', menuKey: 'e:tutor-h5:classroom' },
  { path: '/e/tutor-h5/review', element: withUseGuard(H5Review, 'tutor-h5'), label: '复习', menuKey: 'e:tutor-h5:review' },
  { path: '/e/tutor-h5/wrong', element: withUseGuard(H5Wrong, 'tutor-h5'), label: '错题录入', menuKey: 'e:tutor-h5:wrong' },
  { path: '/e/tutor-h5/wrongbook', element: withUseGuard(H5WrongBook, 'tutor-h5'), label: '错题本', menuKey: 'e:tutor-h5:wrongbook' },
  { path: '/e/tutor-h5/paths', element: withUseGuard(H5Paths, 'tutor-h5'), label: '精通之路', menuKey: 'e:tutor-h5:paths' },
  // ⑤R F4（批11）：详情路由（书路径/教材阅读）不进菜单—— flows 内可达
  { path: '/e/tutor-h5/paths/:bookId', element: withUseGuard(H5PathBook, 'tutor-h5'), label: '书路径', menuKey: 'e:tutor-h5:paths:book', hideInMenu: true },
  { path: '/e/tutor-h5/report', element: withUseGuard(H5Report, 'tutor-h5'), label: '学情报告', menuKey: 'e:tutor-h5:report' },
  { path: '/e/tutor-h5/atlas', element: withUseGuard(H5Atlas, 'tutor-h5'), label: '知识地图', menuKey: 'e:tutor-h5:atlas' },
  { path: '/e/tutor-h5/book/:bookId', element: withUseGuard(H5BookRead, 'tutor-h5'), label: '教材阅读', menuKey: 'e:tutor-h5:book', hideInMenu: true },
  { path: '/e/tutor-h5/me', element: withUseGuard(H5Me, 'tutor-h5'), label: '我的', menuKey: 'e:tutor-h5:me' },
  { path: '/e/tutor-h5/share', element: withUseGuard(H5Share, 'tutor-h5'), label: '分享', menuKey: 'e:tutor-h5:share' },
  // ⑤R R3：笔记本（题库——学习+题目两 tab 语义由 question-notebook 单面承接，spec 2.6 #7）
  { path: '/e/tutor-h5/notebook', element: withUseGuard(NotebookPage, 'tutor-h5'), label: '笔记本', menuKey: 'e:tutor-h5:notebook' },
];

const SISHU_ADMIN_PAGES: ExpertPageConfig[] = [
  // ⑤R F4（批11）：后台三项顶级入口（adminTop）——AppSider admin 段；子页/详情页 hideInMenu
  // IA 批3 3.4（终审裁定①·诚实账7）：管理三项数据面执法=批6 起平台 require_expert 接管——
  // 守卫 manage→use 对齐（A-4 manage 语义升级登记台账）；伙伴/推送守卫维持 manage（批6）
  { path: '/e/sishu/admin/mother-questions', element: withUseGuard(MotherQuestionsAdmin, 'sishu'), label: '母题库管理', menuKey: 'e:sishu:admin:mq', adminTop: true },
  { path: '/e/sishu/admin/mother-questions/new', element: withUseGuard(MotherQuestionNew, 'sishu'), label: '录题', menuKey: 'e:sishu:admin:mq:new', hideInMenu: true },
  { path: '/e/sishu/admin/mother-questions/photo', element: withUseGuard(MotherQuestionPhoto, 'sishu'), label: '拍照录题', menuKey: 'e:sishu:admin:mq:photo', hideInMenu: true },
  { path: '/e/sishu/admin/mother-questions/photo-center', element: withUseGuard(MotherQuestionPhotoCenter, 'sishu'), label: '拍照中心', menuKey: 'e:sishu:admin:mq:photocenter', hideInMenu: true },
  { path: '/e/sishu/admin/mother-questions/analysis', element: withUseGuard(MotherQuestionAnalysis, 'sishu'), label: '错题分析', menuKey: 'e:sishu:admin:mq:analysis', hideInMenu: true },
  { path: '/e/sishu/admin/mother-questions/review', element: withUseGuard(MotherQuestionReview, 'sishu'), label: '复习', menuKey: 'e:sishu:admin:mq:review', hideInMenu: true },
  { path: '/e/sishu/admin/mother-questions/trash', element: withUseGuard(MotherQuestionTrash, 'sishu'), label: '回收站', menuKey: 'e:sishu:admin:mq:trash', hideInMenu: true },
  // ⑤R F1：原仓 [mid] 详情页（卡片点击可达——功能 1:1 闭环，底册枚举外补齐）
  { path: '/e/sishu/admin/mother-questions/:mid', element: withUseGuard(MotherQuestionDetail, 'sishu'), label: '母题详情', menuKey: 'e:sishu:admin:mq:detail', hideInMenu: true },
  { path: '/e/sishu/admin/book', element: withUseGuard(BookAdmin, 'sishu'), label: '书源管理', menuKey: 'e:sishu:admin:book', adminTop: true },
  { path: '/e/sishu/admin/settings', element: withUseGuard(SettingsAdmin, 'sishu'), label: '教学设置', menuKey: 'e:sishu:admin:settings', adminTop: true },
  // ⑤R F1：原仓「设置管理」按钮目标 /settings/curriculum 的等值落点（与 /settings 同页 tab）
  { path: '/e/sishu/admin/settings/curriculum', element: withUseGuard(SettingsAdmin, 'sishu'), label: '教学设置', menuKey: 'e:sishu:admin:settings:curriculum', hideInMenu: true },
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
  // IA 件批1：拆分双空间——tutor=桌面后台；tutor-h5=移动学习空间（h5 15 页+笔记本）。
  // IA批6：桌面三功能页入 tutor 空间（AI写作/伙伴/自主学习——DT (workspace) 组复刻件）。
  // 数据面共用同一教学数据域（spec §一）。
  sishu: [
    // ⑤R R1（批12）：先行版六页退役移除（§3.3.5 终版=DT h5 复刻件）
    ...SISHU_ADMIN_PAGES,
    // IA批6 6.3：AI写作（列表 use + 编辑动线 :docId——CowriterList 跳 ?doc=<id>，
    // 编辑页 props 优先回退 ?doc=，双承接等价于源 /co-writer/[docId]）
    { path: '/e/sishu/co-writer', element: withUseGuard(CowriterList), label: 'AI写作', menuKey: 'e:sishu:co-writer' },
    { path: '/e/sishu/co-writer/:docId', element: withUseGuard(CowriterEditor), label: 'AI写作编辑', menuKey: 'e:sishu:co-writer:doc', hideInMenu: true },
    // IA批6 6.3：伙伴（三页 manage——plan 6.3 裁决；列表卡进详情、新建向导、详情四 Tab）
    { path: '/e/sishu/partners', element: withAdminGuard(PartnersList), label: '伙伴/推送', menuKey: 'e:sishu:partners' },
    { path: '/e/sishu/partners/new', element: withAdminGuard(PartnersNew), label: '新建伙伴', menuKey: 'e:sishu:partners:new', hideInMenu: true },
    { path: '/e/sishu/partners/:partnerId', element: withAdminGuard(PartnerDetail), label: '伙伴详情', menuKey: 'e:sishu:partners:detail', hideInMenu: true },
    // IA批6 6.3：桌面自主学习（use——与 h5 版 /e/tutor-h5/learn 并存，DT 本就两页各自 1:1）
    { path: '/e/sishu/self-learning', element: withUseGuard(SelfLearning), label: '自主学习', menuKey: 'e:sishu:self-learning' },
    // 引擎批2 2.6：DT 桌面对话窗口（navigation.tsx e:sishu:chat 既有占位→真路由）
    { path: '/e/sishu/chat', element: withUseGuard(TutorHomeChat, 'sishu'), label: '对话', menuKey: 'e:sishu:chat' },
    // 引擎批5 5.5：书籍工作台（DT book/page.tsx 1:1 壳件）
    { path: '/e/sishu/book', element: withUseGuard(BookWorkbench, 'sishu'), label: '书籍', menuKey: 'e:sishu:book' },
  ],
  'tutor-h5': [
    ...TUTOR_H5_PAGES,
  ],
};

/** 汇总所有专家自定义路由（routes.tsx 消费）。 */
export function expertPageRoutes(): ExpertPageConfig[] {
  return [...Object.values(EXPERT_PAGES).flat(), ...LEGACY_H5_ALIASES, ...LEGACY_TUTOR_ALIAS];
}

/**
 * IA 件批1 1.3：tutor-h5 迁移旧路径别名（16 条全量含 2 条参数路由）。
 * KeepAlive 架构无 <Navigate>——沿 /knowledge→/vector 先例：旧 path 注册同 element 实路由，
 * menuKey 用新键（页签/打开状态归同域）；hideInMenu=true（防 AppSider/ExpertPortal 泄漏重复项）。
 * 静态 14 条同时在 navigation.tsx pathToMenuKey 有别名（页签解析双保险）；
 * 含参数 2 条（paths/:bookId、book/:bookId）仅此处可表达（matchExpertPage 段数匹配）。
 */
// v4批1 1.3（E-41）：旧 /e/tutor/* 别名表（裁定③改名兼容）——沿 /knowledge→/vector 先例：
// KeepAlive 架构禁 redirect 组件（routes.tsx 头注），旧 path 注册同 element 实路由，
// menuKey 用新键（页签/打开状态归同域）；hideInMenu=true 防菜单泄漏重复项。
const LEGACY_TUTOR_ALIAS: ExpertPageConfig[] = [
  ...[...EXPERT_PAGES.sishu, ...SISHU_ADMIN_PAGES].map((p) => ({
    ...p,
    path: p.path.replace('/e/sishu', '/e/tutor'),
    hideInMenu: true,
  })),
];
const LEGACY_H5_ALIASES: ExpertPageConfig[] = [
  { path: '/e/sishu/h5', element: withUseGuard(H5Home, 'tutor-h5'), label: '首页', menuKey: 'e:tutor-h5:home', hideInMenu: true },
  { path: '/e/sishu/h5/chat', element: withUseGuard(H5Chat, 'tutor-h5'), label: '对话', menuKey: 'e:tutor-h5:chat', hideInMenu: true },
  { path: '/e/sishu/h5/learn', element: withUseGuard(H5Learn, 'tutor-h5'), label: '学习', menuKey: 'e:tutor-h5:learn', hideInMenu: true },
  { path: '/e/sishu/h5/learn/textbook', element: withUseGuard(H5LearnTextbook, 'tutor-h5'), label: '教材学', menuKey: 'e:tutor-h5:learn:textbook', hideInMenu: true },
  { path: '/e/sishu/h5/classroom', element: withUseGuard(H5Classroom, 'tutor-h5'), label: '课堂', menuKey: 'e:tutor-h5:classroom', hideInMenu: true },
  { path: '/e/sishu/h5/review', element: withUseGuard(H5Review, 'tutor-h5'), label: '复习', menuKey: 'e:tutor-h5:review', hideInMenu: true },
  { path: '/e/sishu/h5/wrong', element: withUseGuard(H5Wrong, 'tutor-h5'), label: '错题录入', menuKey: 'e:tutor-h5:wrong', hideInMenu: true },
  { path: '/e/sishu/h5/wrongbook', element: withUseGuard(H5WrongBook, 'tutor-h5'), label: '错题本', menuKey: 'e:tutor-h5:wrongbook', hideInMenu: true },
  { path: '/e/sishu/h5/paths', element: withUseGuard(H5Paths, 'tutor-h5'), label: '精通之路', menuKey: 'e:tutor-h5:paths', hideInMenu: true },
  { path: '/e/sishu/h5/paths/:bookId', element: withUseGuard(H5PathBook, 'tutor-h5'), label: '书路径', menuKey: 'e:tutor-h5:paths:book', hideInMenu: true },
  { path: '/e/sishu/h5/report', element: withUseGuard(H5Report, 'tutor-h5'), label: '学情报告', menuKey: 'e:tutor-h5:report', hideInMenu: true },
  { path: '/e/sishu/h5/atlas', element: withUseGuard(H5Atlas, 'tutor-h5'), label: '知识地图', menuKey: 'e:tutor-h5:atlas', hideInMenu: true },
  { path: '/e/sishu/h5/book/:bookId', element: withUseGuard(H5BookRead, 'tutor-h5'), label: '教材阅读', menuKey: 'e:tutor-h5:book', hideInMenu: true },
  { path: '/e/sishu/h5/me', element: withUseGuard(H5Me, 'tutor-h5'), label: '我的', menuKey: 'e:tutor-h5:me', hideInMenu: true },
  { path: '/e/sishu/h5/share', element: withUseGuard(H5Share, 'tutor-h5'), label: '分享', menuKey: 'e:tutor-h5:share', hideInMenu: true },
  { path: '/e/sishu/notebook', element: withUseGuard(NotebookPage, 'tutor-h5'), label: '笔记本', menuKey: 'e:tutor-h5:notebook', hideInMenu: true },
];

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
  return undefined;
}
