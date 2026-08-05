/**
 * 左侧导航分组配置 -- DeepAssetLens 资产深度探查平台。
 * 顶部独立项：数据资产探查（首页）。
 * 5 分组：图谱建模 / 数据资产 / 语义指标 / 能力管理 / 系统配置。
 * menuKey 与 routes.tsx 对齐；placeholder=true 表示该页为占位（待开发）。
 */
import type { ComponentType } from 'react';
import {
  SearchOutlined,
  ApartmentOutlined,
  ShareAltOutlined,
  PartitionOutlined,
  TableOutlined,
  NodeIndexOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  BranchesOutlined,
  UnorderedListOutlined,
  RocketOutlined,
  BookOutlined,
  SettingOutlined,
} from '@ant-design/icons';

export interface NavItem {
  menuKey: string;
  label: string;
  path: string;
  icon: ComponentType<any>;
  placeholder?: boolean;
}

export interface NavGroup {
  key: string;
  title: string;
  icon: ComponentType<any>;
  items: NavItem[];
}

/** 首页导航项（顶层独立项，不属任何分组） */
export const HOME_NAV_ITEM: NavItem = {
  menuKey: 'home',
  label: '首页-新对话',
  path: '/home',
  icon: SearchOutlined,
};

export const NAV_GROUPS: NavGroup[] = [
  {
    key: 'graph_modeling',
    title: '图谱建模',
    icon: ApartmentOutlined,
    items: [
      { menuKey: 'graph', label: '图谱管理', path: '/graph', icon: ShareAltOutlined },
      { menuKey: 'tree_model', label: '四区建模', path: '/tree-model', icon: PartitionOutlined },
      { menuKey: 'matrix_model', label: '资产矩阵', path: '/matrix', icon: TableOutlined },
      { menuKey: 'entity_relation_manage', label: '实体关系', path: '/entity-relation', icon: NodeIndexOutlined },
    ],
  },
  {
    key: 'data_asset',
    title: '数据资产',
    icon: DatabaseOutlined,
    items: [
      { menuKey: 'master_data', label: '主数据', path: '/master-data', icon: DatabaseOutlined },
      { menuKey: 'activity_data', label: '活动数据', path: '/activity', icon: NodeIndexOutlined },
      { menuKey: 'source', label: '来源表管理', path: '/source', icon: TableOutlined },
      { menuKey: 'mapping', label: '映射管理', path: '/mapping', icon: BranchesOutlined },
      { menuKey: 'datasource', label: '数据源', path: '/datasource', icon: CloudServerOutlined },
    ],
  },
  {
    key: 'semantic_metric',
    title: '语义指标',
    icon: UnorderedListOutlined,
    items: [
      { menuKey: 'metric_manager', label: '指标管理', path: '/metrics', icon: UnorderedListOutlined },
    ],
  },
  {
    key: 'capability',
    title: '能力管理',
    icon: RocketOutlined,
    items: [
      { menuKey: 'skills', label: '技能管理', path: '/skills', icon: RocketOutlined },
      { menuKey: 'vector_manage', label: '向量管理', path: '/vector', icon: BookOutlined },
    ],
  },
  {
    key: 'system',
    title: '系统配置',
    icon: SettingOutlined,
    items: [
      { menuKey: 'doris_config', label: 'Doris 配置', path: '/doris-config', icon: DatabaseOutlined },
      { menuKey: 'llmconfig', label: 'LLM 配置', path: '/llm-config', icon: SettingOutlined },
    ],
  },
];

/** menuKey -> label（页签标题、面包屑用） */
export const MENU_LABELS: Record<string, string> = (() => {
  const out: Record<string, string> = { home: '数据资产探查' };
  for (const g of NAV_GROUPS) {
    for (const it of g.items) out[it.menuKey] = it.label;
  }
  return out;
})();

/** menuKey -> path */
export const menuKeyToPath: Record<string, string> = (() => {
  const out: Record<string, string> = { home: '/home' };
  for (const g of NAV_GROUPS) {
    for (const it of g.items) out[it.menuKey] = it.path;
  }
  return out;
})();

/** path -> menuKey */
export const pathToMenuKey: Record<string, string> = (() => {
  const out: Record<string, string> = { '/home': 'home', '/': 'home' };
  for (const g of NAV_GROUPS) {
    for (const it of g.items) out[it.path] = it.menuKey;
  }
  // 兼容旧路径 /free-plan -> 首页
  out['/free-plan'] = 'home';
  return out;
})();

/** 画布类页面：需要接收 onOpenTarget 回调 */
export const NEEDS_OPEN_TARGET = new Set([
  'graph',
  'tree_model',
  'matrix_model',
  'mapping',
  'master_data',
  'activity_data',
]);

/** 画布类页面：内容区取消内边距（自撑满） */
export const CANVAS_MENU_KEYS = new Set([
  'graph',
  'tree_model',
  'matrix_model',
  'entity_relation_manage',
]);
