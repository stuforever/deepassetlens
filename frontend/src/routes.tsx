import React from 'react';
import FreePlanChat from './pages/FreePlanChat';
import GraphManager from './pages/GraphManager';
import MasterDataManager from './pages/MasterDataManager';
import ActivityManager from './pages/ActivityManager';
import EntityRelationManager from './pages/EntityRelationManager';
import SourceManager from './pages/SourceManager';
import MappingManager from './pages/MappingManager';
import MetricManager from './pages/MetricManager';
import SkillManagerV2 from './pages/SkillManagerV2';
import DataSourceConfigPage from './pages/DataSourceConfig';
import DorisConfigPage from './pages/DorisConfig';
import VectorManagePanel from './components/VectorManagePanel';
import LLMConfigManager from './pages/LLMConfigManager';
import { MENU_LABELS } from './config/navigation';

export type RouteConfig = {
  path: string;
  element: React.ComponentType<any>;
  label: string;
  menuKey: string;
};

export const routes: RouteConfig[] = [
  { path: '/home', element: FreePlanChat, label: '数据资产探查', menuKey: 'home' },
  { path: '/graph', element: GraphManager, label: '图谱管理', menuKey: 'graph' },
  { path: '/tree-model', element: GraphManager, label: '四区建模', menuKey: 'tree_model' },
  { path: '/matrix', element: GraphManager, label: '资产矩阵', menuKey: 'matrix_model' },
  { path: '/master-data', element: MasterDataManager, label: '主数据', menuKey: 'master_data' },
  { path: '/activity', element: ActivityManager, label: '活动数据', menuKey: 'activity_data' },
  { path: '/entity-relation', element: EntityRelationManager, label: '实体关系', menuKey: 'entity_relation_manage' },
  { path: '/source', element: SourceManager, label: '来源表管理', menuKey: 'source' },
  { path: '/mapping', element: MappingManager, label: '映射管理', menuKey: 'mapping' },
  { path: '/metrics', element: MetricManager, label: '指标管理', menuKey: 'metric_manager' },
  { path: '/skills', element: SkillManagerV2, label: '技能管理', menuKey: 'skills' },
  { path: '/datasource', element: DataSourceConfigPage, label: '数据源', menuKey: 'datasource' },
  { path: '/doris-config', element: DorisConfigPage, label: 'Doris 配置', menuKey: 'doris_config' },
  { path: '/vector', element: VectorManagePanel, label: '向量管理', menuKey: 'vector_manage' },
  { path: '/llm-config', element: LLMConfigManager, label: 'LLM 配置', menuKey: 'llmconfig' },
  { path: '*', element: FreePlanChat, label: '数据资产探查', menuKey: 'home' },
];

export { MENU_LABELS as menuLabels };
// 向后兼容：原 routes.tsx 导出的两个映射，现由 navigation.tsx 维护
export { menuKeyToPath, pathToMenuKey } from './config/navigation';
