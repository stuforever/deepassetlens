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
  TeamOutlined,
  ShareAltOutlined,
  PartitionOutlined,
  TableOutlined,
  NodeIndexOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  BranchesOutlined,
  UnorderedListOutlined,
  DeploymentUnitOutlined,
  RocketOutlined,
  BookOutlined,
  SettingOutlined,
  FundOutlined,
  ThunderboltOutlined,
  FileSearchOutlined,
  PoweroffOutlined,
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

/** 顶层独立项：专家门户（专家地基①——原「首页-新对话」升格为门户入口，path 指向 /） */
export const HOME_NAV_ITEM: NavItem = {
  menuKey: 'portal',
  label: '专家门户',
  path: '/',
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
      { menuKey: 'gallery', label: '图库', path: '/gallery', icon: DeploymentUnitOutlined },
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
      { menuKey: 'governance', label: '运行观测', path: '/governance', icon: FundOutlined },
      { menuKey: 'engine_workbench', label: '引擎工作台', path: '/engine-workbench', icon: ThunderboltOutlined },
      // ⑤R F4（批11）11.1：§3.3.5 菜单更名——「向量管理」→「知识库管理」（/vector 路径保留，
      // DT knowledge 页 /knowledge 别名经 pathToMenuKey 重定向入本页）
      { menuKey: 'vector_manage', label: '知识库管理', path: '/vector', icon: BookOutlined },
      { menuKey: 'golden_qa', label: '金标锚定管理', path: '/golden-qa', icon: FileSearchOutlined },
      // 记忆插槽②批6：记忆管理（平台管理区，admin-only 页）
      { menuKey: 'memory_admin', label: '记忆管理', path: '/memory-admin', icon: BookOutlined },
      // ⑤R F4（批11）11.1：§3.3.5 菜单树 21 项定版——对话附件上限（/attachment-settings）
      // 不入菜单（路由保留，批10 最小补件，登记见 batch10_映射登记.json）
    ],
  },
  {
    key: 'system',
    title: '系统配置',
    icon: SettingOutlined,
    items: [
      { menuKey: 'doris_config', label: 'Doris 配置', path: '/doris-config', icon: DatabaseOutlined },
      { menuKey: 'llmconfig', label: 'LLM 配置', path: '/llm-config', icon: SettingOutlined },
      { menuKey: 'security_controls', label: '安全控制中心', path: '/security-controls', icon: PoweroffOutlined },
      // ⑥-2a B-2：专家赋权管理面（平台配置层——附件四 §10.2 治理层位置，admin-only）
      { menuKey: 'expert_grants', label: '专家赋权', path: '/expert-grants', icon: TeamOutlined },
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
  // 专家地基①：portal=/；home 保留映射（老会话侧栏点击经 /home 重定向进专家对话页）
  const out: Record<string, string> = { home: '/home', portal: '/' };
  for (const g of NAV_GROUPS) {
    for (const it of g.items) out[it.menuKey] = it.path;
  }
  return out;
})();

/** path -> menuKey */
export const pathToMenuKey: Record<string, string> = (() => {
  // 专家地基①：/ → portal（专家门户）；/home → home（重定向过渡态）
  const out: Record<string, string> = { '/home': 'home', '/': 'portal' };
  for (const g of NAV_GROUPS) {
    for (const it of g.items) out[it.path] = it.menuKey;
  }
  // 兼容旧路径 /free-plan -> 首页
  out['/free-plan'] = 'home';
  // ⑤R F4（批11）11.1：DT knowledge 页路径别名 → 知识库管理（/vector）——语义并入重定向
  out['/knowledge'] = 'vector_manage';
  // IA 件批1 1.3：tutor-h5 迁移旧路径别名（14 条静态——KeepAlive 架构无 Navigate，
  // 沿 /knowledge→/vector 先例=pathToMenuKey 别名；含参数旧路径走 expertPages LEGACY_H5_ALIASES）
  out['/e/tutor/h5'] = 'e:tutor-h5:home';
  out['/e/tutor/h5/chat'] = 'e:tutor-h5:chat';
  out['/e/tutor/h5/learn'] = 'e:tutor-h5:learn';
  out['/e/tutor/h5/learn/textbook'] = 'e:tutor-h5:learn:textbook';
  out['/e/tutor/h5/classroom'] = 'e:tutor-h5:classroom';
  out['/e/tutor/h5/review'] = 'e:tutor-h5:review';
  out['/e/tutor/h5/wrong'] = 'e:tutor-h5:wrong';
  out['/e/tutor/h5/wrongbook'] = 'e:tutor-h5:wrongbook';
  out['/e/tutor/h5/paths'] = 'e:tutor-h5:paths';
  out['/e/tutor/h5/report'] = 'e:tutor-h5:report';
  out['/e/tutor/h5/atlas'] = 'e:tutor-h5:atlas';
  out['/e/tutor/h5/me'] = 'e:tutor-h5:me';
  out['/e/tutor/h5/share'] = 'e:tutor-h5:share';
  out['/e/tutor/notebook'] = 'e:tutor-h5:notebook';
  return out;
})();

/** 画布类页面：需要接收 onOpenTarget 回调 */
export const NEEDS_OPEN_TARGET = new Set([
  'mapping',
  'master_data',
  'activity_data',
]);

/** 画布类页面：内容区取消内边距（自撑满） */
export const CANVAS_MENU_KEYS = new Set([
  'graph',
  'tree_model',
  'matrix_model',
  'gallery',
  'entity_relation_manage',
]);
