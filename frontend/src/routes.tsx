import React, { lazy } from 'react';
import { MENU_LABELS } from './config/navigation';

// 路由懒加载：每页独立 chunk（webpackChunkName 控制产物名）。
// KeepAlive 语义不受影响——lazy 只影响「首次打开某页签时的模块加载」，已挂载页签不卸载。
const FreePlanChat = lazy(() => import(/* webpackChunkName: "home" */ './pages/FreePlanChat'));
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
const VectorManagePanel = lazy(() => import(/* webpackChunkName: "vector" */ './components/VectorManagePanel'));
const LLMConfigManager = lazy(() => import(/* webpackChunkName: "llmconfig" */ './pages/LLMConfigManager'));
const GovernanceObservatory = lazy(() => import(/* webpackChunkName: "governance" */ './pages/GovernanceObservatory'));
const EngineWorkbench = lazy(() => import(/* webpackChunkName: "workbench" */ './pages/EngineWorkbench'));
const QaExamplesManager = lazy(() => import(/* webpackChunkName: "qaexamples" */ './pages/QaExamplesManager'));

export type RouteConfig = {
  path: string;
  element: React.ComponentType<any> | React.LazyExoticComponent<React.ComponentType<any>>;
  label: string;
  menuKey: string;
};

export const routes: RouteConfig[] = [
  { path: '/home', element: FreePlanChat, label: '数据资产探查', menuKey: 'home' },
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
  { path: '/qa-examples', element: QaExamplesManager, label: '示例库管理', menuKey: 'qa_examples' },
  { path: '/datasource', element: DataSourceConfigPage, label: '数据源', menuKey: 'datasource' },
  { path: '/doris-config', element: DorisConfigPage, label: 'Doris 配置', menuKey: 'doris_config' },
  { path: '/vector', element: VectorManagePanel, label: '向量管理', menuKey: 'vector_manage' },
  { path: '/llm-config', element: LLMConfigManager, label: 'LLM 配置', menuKey: 'llmconfig' },
  { path: '*', element: FreePlanChat, label: '数据资产探查', menuKey: 'home' },
];

export { MENU_LABELS as menuLabels };
// 向后兼容：原 routes.tsx 导出的两个映射，现由 navigation.tsx 维护
export { menuKeyToPath, pathToMenuKey } from './config/navigation';
