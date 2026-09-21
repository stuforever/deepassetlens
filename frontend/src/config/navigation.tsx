/**
 * 左侧导航分组配置 -- DeepAssetLens 资产深度探查平台。
 * 顶部独立项：专家门户（HOME_NAV_ITEM）。
 * IA 批3 3.1：七组（数据探索专家/私塾先生/私塾先生h5/技能配置/后台配置/设置中心——
 * 原五组 items 全部并入；menuKey 现状键为准，口径差登记 E-1）。
 * menuKey 与 routes.tsx 对齐；placeholder=true 表示该页为占位（待开发）。
 */
/**
 * IA 件批3 3.1：NAV_GROUPS 七组重构（spec §3.1 终版——原五组 graph_modeling/data_asset/
 * semantic_metric/capability/system 的 items 全部并入下组；现状键为准，口径差登记 E-1）。
 * 三空间组静态注册=下拉 bug 根因2 修复（结构永不依赖网络）；组内 adminTop 项语义见 3.3/3.4。
 */
import type { ComponentType, ReactNode } from 'react';
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
  CommentOutlined,
  ReadOutlined,
  EditOutlined,
  VideoCameraOutlined,
  RedoOutlined,
  FormOutlined,
  TrophyOutlined,
  BarChartOutlined,
  ProfileOutlined,
  HomeOutlined,
  MobileOutlined,
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
  icon: HomeOutlined,
};

export const NAV_GROUPS: NavGroup[] = [  // ── 三轨M6(U1) 侧栏 4 区重构（ui-audit 规格 §2.2）：7 组 47 项 → 4 区——
  // h5 12 项移出桌面侧栏（桌面唯一展台入口）；sishu 功能页留路由经门户专家卡进入；
  // sishu 管理三项保留在工作区（裁定原文「保留在空间组内」）。
  {
    key: 'workspace_group',
    title: '工作区',
    icon: CommentOutlined,
    items: [
      { menuKey: 'e:wenshu:chat', label: '数据探索对话', path: '/e/wenshu/chat', icon: CommentOutlined },
      { menuKey: 'e:sishu:chat', label: '私塾先生对话', path: '/e/sishu/chat', icon: ReadOutlined },
      { menuKey: 'e:tutor-h5:chat', label: 'h5 展台', path: '/e/tutor-h5/chat', icon: MobileOutlined },
      { menuKey: 'e:sishu:admin:mq', label: '母题库管理', path: '/e/sishu/admin/mother-questions', icon: BookOutlined },
      { menuKey: 'e:sishu:admin:book', label: '书源管理', path: '/e/sishu/admin/book', icon: BookOutlined },
      { menuKey: 'e:sishu:admin:settings', label: '教学设置', path: '/e/sishu/admin/settings', icon: SettingOutlined },
    ],
  },
  {
    key: 'asset_group',
    title: '资产管理',
    icon: DatabaseOutlined,
    items: [
      // 建模
      { menuKey: 'graph', label: '图谱管理', path: '/graph', icon: ShareAltOutlined },
      { menuKey: 'tree_model', label: '四区建模', path: '/tree-model', icon: PartitionOutlined },
      { menuKey: 'matrix_model', label: '资产矩阵', path: '/matrix', icon: TableOutlined },
      { menuKey: 'gallery', label: '图库', path: '/gallery', icon: DeploymentUnitOutlined },
      { menuKey: 'entity_relation_manage', label: '实体关系', path: '/entity-relation', icon: NodeIndexOutlined },
      // 数据
      { menuKey: 'master_data', label: '主数据', path: '/master-data', icon: DatabaseOutlined },
      { menuKey: 'activity_data', label: '活动数据', path: '/activity', icon: NodeIndexOutlined },
      { menuKey: 'source', label: '来源表管理', path: '/source', icon: TableOutlined },
      { menuKey: 'mapping', label: '映射管理', path: '/mapping', icon: BranchesOutlined },
      // 接入
      { menuKey: 'datasource', label: '数据源', path: '/datasource', icon: CloudServerOutlined },
      { menuKey: 'doris_config', label: 'Doris 配置', path: '/doris-config', icon: DatabaseOutlined },
      // 语义
      { menuKey: 'metric_manager', label: '指标管理', path: '/metrics', icon: UnorderedListOutlined },
    ],
  },
  {
    key: 'platform_group',
    title: '平台能力',
    icon: RocketOutlined,
    items: [
      { menuKey: 'skills', label: '通用技能', path: '/skills', icon: RocketOutlined },
      { menuKey: 'skills:wenshu', label: '数据探索个性技能', path: '/skills?expert=wenshu', icon: DatabaseOutlined },
      { menuKey: 'skills:tutor', label: '私塾先生个性技能', path: '/skills?expert=tutor', icon: ReadOutlined },
      { menuKey: 'vector_manage', label: '知识库管理', path: '/vector', icon: BookOutlined },
      { menuKey: 'golden_qa', label: '金标锚定管理', path: '/golden-qa', icon: FileSearchOutlined },
    ],
  },
  {
    key: 'system_group',
    title: '系统',
    icon: SettingOutlined,
    items: [
      { menuKey: 'governance', label: '运行观测', path: '/governance', icon: FundOutlined },
      { menuKey: 'engine_workbench', label: '引擎工作台', path: '/engine-workbench', icon: ThunderboltOutlined },
      { menuKey: 'llmconfig', label: 'LLM 配置', path: '/llm-config', icon: SettingOutlined },
      { menuKey: 'memory_admin', label: '记忆管理', path: '/memory-admin', icon: BookOutlined },
      { menuKey: 'expert_grants', label: '专家赋权', path: '/expert-grants', icon: TeamOutlined },
      { menuKey: 'security_controls', label: '安全控制中心', path: '/security-controls', icon: PoweroffOutlined },
      { menuKey: 'settings_hub', label: '设置中心', path: '/settings', icon: SettingOutlined },
    ],
  },
];

// IA批5 接线：设置中心子页注册表（menuKey 口径 'settings:<页>'，与 routes.tsx settings 路由块
// 逐一对应）——只进页签/面包屑映射，不进侧栏 NAV_GROUPS（主菜单唯一入口=设置中心）。
const SETTINGS_PAGES: Array<{ key: string; label: string; path: string }> = [
  { key: 'settings:agents', label: '伙伴和智能体', path: '/settings/agents' },
  { key: 'settings:agents-claude-code', label: 'Claude Code', path: '/settings/agents/claude-code' },
  { key: 'settings:agents-codex', label: 'Codex', path: '/settings/agents/codex' },
  { key: 'settings:agents-gemini', label: 'Gemini CLI', path: '/settings/agents/gemini' },
  { key: 'settings:agents-kimi', label: 'Kimi CLI', path: '/settings/agents/kimi' },
  { key: 'settings:agents-mimo', label: 'MiMo Code', path: '/settings/agents/mimo' },
  { key: 'settings:agents-opencode', label: 'opencode', path: '/settings/agents/opencode' },
  { key: 'settings:chat', label: '聊天', path: '/settings/chat' },
  { key: 'settings:curriculum', label: '设置管理', path: '/settings/curriculum' },
  { key: 'settings:attachments', label: '附件', path: '/settings/attachments' },
  { key: 'settings:appearance', label: '外观', path: '/settings/appearance' },
  { key: 'settings:network', label: '网络', path: '/settings/network' },
  { key: 'settings:llm', label: 'LLM', path: '/settings/llm' },
  { key: 'settings:embedding', label: '嵌入模型', path: '/settings/embedding' },
  { key: 'settings:stt', label: '语音识别', path: '/settings/stt' },
  { key: 'settings:tts', label: '语音合成', path: '/settings/tts' },
  { key: 'settings:image', label: '文生图', path: '/settings/image' },
  { key: 'settings:video', label: '文生视频', path: '/settings/video' },
  { key: 'settings:document-parsing', label: '文档解析', path: '/settings/document-parsing' },
  { key: 'settings:mineru', label: 'MinerU', path: '/settings/mineru' },
  { key: 'settings:models', label: '模型', path: '/settings/models' },
  { key: 'settings:mcp', label: 'MCP', path: '/settings/mcp' },
  { key: 'settings:memory', label: '记忆', path: '/settings/memory' },
  { key: 'settings:tools', label: '工具', path: '/settings/tools' },
  { key: 'settings:capabilities', label: '能力', path: '/settings/capabilities' },
  { key: 'settings:search', label: '搜索', path: '/settings/search' },
  { key: 'settings:status', label: '状态', path: '/settings/status' },
  { key: 'settings:curriculum-textbooks', label: '课本管理', path: '/settings/curriculum/textbooks' },
  { key: 'settings:curriculum-chapters', label: '章节管理', path: '/settings/curriculum/chapters' },
  { key: 'settings:curriculum-knowledge-points', label: '知识点管理', path: '/settings/curriculum/knowledge-points' },
];

/**
 * v3 §二（迁移完成后精简入口）：管理台面板分组平铺——六组 18 项。
 * menuKey 全部复用 NAV_GROUPS/既有注册表实测键（Task 1 逐项核对：
 * entity_relation_manage/datasource/doris_config/vector_manage/master_data/activity_data/
 * source/mapping/metric_manager/governance/engine_workbench/llmconfig/memory_admin/
 * expert_grants/security_controls/e:sishu:admin:* ——计划示意键（entity_relation/doris/
 * master/activity/lineage/metric/engine/llm/memory/grants/security/sishu_*）均不存在，已换实）。
 * 「图谱画布」=Task 6 图谱 4 合 1 单入口（/graph 页内四视图）；「技能管理」=3 合 1（/skills?expert=）。
 */
export interface NavPanelItem { menuKey: string; label: string; icon: ReactNode; }
export interface NavPanelGroup { title: string; items: NavPanelItem[]; }
export const NAV_PANEL_GROUPS: NavPanelGroup[] = [
  { title: '数据建模', items: [
    { menuKey: 'graph', label: '图谱画布', icon: <ShareAltOutlined /> },
    { menuKey: 'entity_relation_manage', label: '实体关系', icon: <NodeIndexOutlined /> } ] },
  { title: '数据接入', items: [
    { menuKey: 'datasource', label: '数据源', icon: <CloudServerOutlined /> },
    { menuKey: 'doris_config', label: 'Doris 配置', icon: <DatabaseOutlined /> } ] },
  { title: '平台能力', items: [
    { menuKey: 'skills', label: '技能管理', icon: <RocketOutlined /> },
    { menuKey: 'vector_manage', label: '知识库', icon: <BookOutlined /> },
    { menuKey: 'golden_qa', label: '金标锚定', icon: <FileSearchOutlined /> } ] },
  { title: '数据资产', items: [
    { menuKey: 'master_data', label: '主数据', icon: <DatabaseOutlined /> },
    { menuKey: 'activity_data', label: '活动数据', icon: <NodeIndexOutlined /> },
    { menuKey: 'source', label: '来源表', icon: <TableOutlined /> },
    { menuKey: 'mapping', label: '映射管理', icon: <BranchesOutlined /> },
    { menuKey: 'metric_manager', label: '指标管理', icon: <UnorderedListOutlined /> } ] },
  { title: '治理与系统', items: [
    { menuKey: 'governance', label: '运行观测', icon: <FundOutlined /> },
    { menuKey: 'engine_workbench', label: '引擎台', icon: <ThunderboltOutlined /> },
    { menuKey: 'llmconfig', label: 'LLM 配置', icon: <SettingOutlined /> },
    { menuKey: 'memory_admin', label: '记忆', icon: <BookOutlined /> },
    { menuKey: 'expert_grants', label: '专家赋权', icon: <TeamOutlined /> },
    { menuKey: 'security_controls', label: '安全中心', icon: <PoweroffOutlined /> } ] },
  { title: '私塾管理', items: [
    { menuKey: 'e:sishu:admin:mq', label: '母题库', icon: <BookOutlined /> },
    { menuKey: 'e:sishu:admin:book', label: '书源', icon: <ReadOutlined /> },
    { menuKey: 'e:sishu:admin:settings', label: '教学设置', icon: <SettingOutlined /> },
    // { menuKey: 'h5_publish', label: 'H5 发布管理', icon: <MobileOutlined /> },  // Task 5 落地后启用
  ] },
];

/** menuKey -> label（页签标题、面包屑用） */
export const MENU_LABELS: Record<string, string> = (() => {
  const out: Record<string, string> = { home: '数据资产探查' };
  for (const g of NAV_GROUPS) {
    for (const it of g.items) out[it.menuKey] = it.label;
  }
  // IA批5：设置中心子页页签标题（子页不在 NAV_GROUPS，主菜单唯一入口）
  for (const p of SETTINGS_PAGES) out[p.key] = p.label;
  return out;
})();

/** menuKey -> path */
export const menuKeyToPath: Record<string, string> = (() => {
  // 专家地基①：portal=/；home 保留映射（老会话侧栏点击经 /home 重定向进专家对话页）
  const out: Record<string, string> = { home: '/home', portal: '/' };
  for (const g of NAV_GROUPS) {
    for (const it of g.items) out[it.menuKey] = it.path;
  }
  for (const p of SETTINGS_PAGES) out[p.key] = p.path;
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
  out['/e/sishu/h5'] = 'e:tutor-h5:home';
  out['/e/sishu/h5/chat'] = 'e:tutor-h5:chat';
  out['/e/sishu/h5/learn'] = 'e:tutor-h5:learn';
  out['/e/sishu/h5/learn/textbook'] = 'e:tutor-h5:learn:textbook';
  out['/e/sishu/h5/classroom'] = 'e:tutor-h5:classroom';
  out['/e/sishu/h5/review'] = 'e:tutor-h5:review';
  out['/e/sishu/h5/wrong'] = 'e:tutor-h5:wrong';
  out['/e/sishu/h5/wrongbook'] = 'e:tutor-h5:wrongbook';
  out['/e/sishu/h5/paths'] = 'e:tutor-h5:paths';
  out['/e/sishu/h5/report'] = 'e:tutor-h5:report';
  out['/e/sishu/h5/atlas'] = 'e:tutor-h5:atlas';
  out['/e/sishu/h5/me'] = 'e:tutor-h5:me';
  out['/e/sishu/h5/share'] = 'e:tutor-h5:share';
  out['/e/sishu/notebook'] = 'e:tutor-h5:notebook';
  // IA批5：设置中心子页 path→menuKey（页签切换；hideInMenu 不进侧栏）
  for (const p of SETTINGS_PAGES) out[p.path] = p.key;
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
