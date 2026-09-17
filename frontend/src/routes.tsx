import React, { lazy } from 'react';
import { MENU_LABELS } from './config/navigation';
// ⑤批4（⑤e）：专家自定义页注册表（import 在顶部——eslint import/first）。
import { expertPageRoutes } from './config/expertPages';
// 附件四 A-1：守卫雏形（role-based——A-4 升级 ACL use/manage 分层）
import RequireAdmin from './components/RequireAdmin';

// 路由懒加载：每页独立 chunk（webpackChunkName 控制产物名）。
// KeepAlive 语义不受影响——lazy 只影响「首次打开某页签时的模块加载」，已挂载页签不卸载。
// 注：FreePlanChat.tsx 保留为 ExpertChat 的复制基线（专家地基①后不再直接路由）。
const GraphManager = lazy(() => import(/* webpackChunkName: "graph" */ './pages/GraphManager'));
const MasterDataManager = lazy(() => import(/* webpackChunkName: "entity" */ './pages/MasterDataManager'));
const ActivityManager = lazy(() => import(/* webpackChunkName: "entity" */ './pages/ActivityManager'));
const EntityRelationManager = lazy(() => import(/* webpackChunkName: "entity" */ './pages/EntityRelationManager'));
const SourceManager = lazy(() => import(/* webpackChunkName: "source" */ './pages/SourceManager'));
const MappingManager = lazy(() => import(/* webpackChunkName: "mapping" */ './pages/MappingManager'));
const MetricManager = lazy(() => import(/* webpackChunkName: "metrics" */ './pages/MetricManager'));
const SkillManagerV2 = lazy(() => import(/* webpackChunkName: "skills" */ './pages/SkillManagerV2'));
const DataSourceConfigPage = lazy(() => import(/* webpackChunkName: "config" */ './pages/DataSourceConfig'));
const DorisConfigPage = lazy(() => import(/* webpackChunkName: "config" */ './pages/DorisConfig'));
// IA批4 4.5：知识中心 16 件复刻承接 /vector（menuKey vector_manage 不变）；VectorManagePanel 退役 git rm
const KnowledgePage = lazy(() => import(/* webpackChunkName: "knowledge" */ './pages/knowledge/KnowledgePage'));
const LLMConfigManager = lazy(() => import(/* webpackChunkName: "llmconfig" */ './pages/LLMConfigManager'));
const GovernanceObservatory = lazy(() => import(/* webpackChunkName: "governance" */ './pages/GovernanceObservatory'));
const EngineWorkbench = lazy(() => import(/* webpackChunkName: "workbench" */ './pages/EngineWorkbench'));
const GoldenQaManager = lazy(() => import(/* webpackChunkName: "goldenqa" */ './pages/GoldenQaManager'));
const SecurityControlCenter = lazy(() => import(/* webpackChunkName: "security" */ './pages/SecurityControlCenter'));
// 专家地基①：专家门户 + 专家对话。/home 与 /e/:slug/chat 同挂 ExpertChat（slug 缺省 wenshu）——
// KeepAlive 架构按页签 menuKey 渲染组件（无 <Routes>），重定向组件会被常驻挂载引发循环，故不使用重定向。
const ExpertPortal = lazy(() => import(/* webpackChunkName: "expert-portal" */ './pages/ExpertPortal'));
const ExpertChat = lazy(() => import(/* webpackChunkName: "expert-chat" */ './pages/expert/ExpertChat'));
// 记忆插槽②批6：记忆管理页（平台管理区，admin-only）
const MemoryAdmin = lazy(() => import(/* webpackChunkName: "memory-admin" */ './pages/MemoryAdmin'));
// ⑤R F3（批10）：对话附件上限设置（chat-attachments 最小补件，admin-only）
const AttachmentSettings = lazy(() => import(/* webpackChunkName: "attachment-settings" */ './pages/AttachmentSettings'));
const ExpertGrants = lazy(() => import(/* webpackChunkName: "expert-grants" */ './pages/ExpertGrants'));
// ⑤批4（⑤e）：专家自定义页——EXPERT_PAGES 注册表（①spec §七预留扩展点）实体化注入。
// 卡是数据页面是代码：路由静态注册，可见性由卡 enabled 决定（卡关=门户/侧栏不渲染）。
// ⑤R R1（批12）：TutorAdminHome（旧后台骨架）退役移除。

export type RouteConfig = {
  path: string;
  element: React.ComponentType<any> | React.LazyExoticComponent<React.ComponentType<any>>;
  label: string;
  menuKey: string;
};

export const routes: RouteConfig[] = [
  { path: '/', element: ExpertPortal, label: '专家门户', menuKey: 'portal' },
  { path: '/home', element: ExpertChat, label: '数据资产探查', menuKey: 'home' },
  { path: '/e/:slug/chat', element: ExpertChat, label: '专家对话', menuKey: 'expert_chat' },
  { path: '/graph', element: GraphManager, label: '图谱管理', menuKey: 'graph' },
  { path: '/tree-model', element: GraphManager, label: '四区建模', menuKey: 'tree_model' },
  { path: '/matrix', element: GraphManager, label: '资产矩阵', menuKey: 'matrix_model' },
  { path: '/gallery', element: GraphManager, label: '图库', menuKey: 'gallery' },
  { path: '/master-data', element: MasterDataManager, label: '主数据', menuKey: 'master_data' },
  { path: '/activity', element: ActivityManager, label: '活动数据', menuKey: 'activity_data' },
  { path: '/entity-relation', element: EntityRelationManager, label: '实体关系', menuKey: 'entity_relation_manage' },
  { path: '/source', element: SourceManager, label: '来源表管理', menuKey: 'source' },
  { path: '/mapping', element: MappingManager, label: '映射管理', menuKey: 'mapping' },
  { path: '/metrics', element: MetricManager, label: '指标管理', menuKey: 'metric_manager' },
  { path: '/skills', element: SkillManagerV2, label: '技能管理', menuKey: 'skills' },
  { path: '/governance', element: GovernanceObservatory, label: '运行观测', menuKey: 'governance' },
  { path: '/engine-workbench', element: EngineWorkbench, label: '引擎工作台', menuKey: 'engine_workbench' },
  { path: '/golden-qa', element: GoldenQaManager, label: '金标锚定管理', menuKey: 'golden_qa' },
  { path: '/security-controls', element: SecurityControlCenter, label: '安全控制中心', menuKey: 'security_controls' },
  { path: '/datasource', element: DataSourceConfigPage, label: '数据源', menuKey: 'datasource' },
  { path: '/doris-config', element: DorisConfigPage, label: 'Doris 配置', menuKey: 'doris_config' },
  // IA批4 4.5：/vector 承接=知识中心复刻页（名「知识库管理」保留）；/knowledge 别名同页（pathToMenuKey 已映射 vector_manage）
  { path: '/vector', element: KnowledgePage, label: '知识库管理', menuKey: 'vector_manage' },
  { path: '/knowledge', element: KnowledgePage, label: '知识库管理', menuKey: 'vector_manage' },
  { path: '/llm-config', element: LLMConfigManager, label: 'LLM 配置', menuKey: 'llmconfig' },
  { path: '/memory-admin', element: MemoryAdmin, label: '记忆管理', menuKey: 'memory_admin' },
  { path: '/attachment-settings', element: AttachmentSettings, label: '对话附件上限', menuKey: 'attachment_settings' },
  // ⑥-2a B-2：专家赋权管理面（平台配置层——grant 三端点复用，admin-only）
  { path: '/expert-grants', label: '专家赋权', menuKey: 'expert_grants',
    element: (() => <RequireAdmin><ExpertGrants /></RequireAdmin>) as any },
  // ⑤批4（⑤e）：专家自定义页（EXPERT_PAGES 注册表驱动；⑤R R1（批12）先行版六页已退役）
  ...expertPageRoutes().map((p) => ({ path: p.path, element: p.element as any, label: p.label, menuKey: p.menuKey })),
  // ⑤R R1（批12）：旧 tutor 后台骨架 /e/tutor/admin 退役（AdminHome/AdminZones 删除；
  // 后台三项顶级入口=ExpertPages 注册 adminTop 件；legacy 键 e:{slug}:admin 由 App.tsx 回落 chat）
  { path: '*', element: ExpertPortal, label: '专家门户', menuKey: 'portal' },
];

export { MENU_LABELS as menuLabels };
// 向后兼容：原 routes.tsx 导出的两个映射，现由 navigation.tsx 维护
export { menuKeyToPath, pathToMenuKey } from './config/navigation';
