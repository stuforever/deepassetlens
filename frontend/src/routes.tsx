import { Navigate } from 'react-router-dom';
import React, { lazy } from 'react';
import { MENU_LABELS } from './config/navigation';
// ⑤批4（⑤e）：专家自定义页注册表（import 在顶部——eslint import/first）。
import { expertPageRoutes } from './config/expertPages';
// 附件四 A-1：守卫雏形（role-based——A-4 升级 ACL use/manage 分层）
import RequireAdmin from './components/RequireAdmin';
// IA批5 接线：KeepAlive 无 <Routes> 嵌套上下文——settings 子页直接渲染，useSettings 需自备
// Provider（统一壳：每页签独立 Provider，保存/引导/主题状态互不串扰）。
import { SettingsProvider } from './components/settings/SettingsContext';

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
const settingsPage = (Comp: React.ComponentType): React.FC =>
  function SettingsPageShell() {
    return (
      <SettingsProvider>
        <Comp />
      </SettingsProvider>
    );
  };
// IA批5 5.5：LLMConfigManager 退役（/llm-config 改挂设置中心复刻 llm 页——上方 settings 路由块）
const GovernanceObservatory = lazy(() => import(/* webpackChunkName: "governance" */ './pages/GovernanceObservatory'));
const EngineWorkbench = lazy(() => import(/* webpackChunkName: "workbench" */ './pages/EngineWorkbench'));
const GoldenQaManager = lazy(() => import(/* webpackChunkName: "goldenqa" */ './pages/GoldenQaManager'));
const SecurityControlCenter = lazy(() => import(/* webpackChunkName: "security" */ './pages/SecurityControlCenter'));
// 专家地基①：专家门户 + 专家对话。/home 与 /e/:slug/chat 同挂 ExpertChat（slug 缺省 wenshu）——
// KeepAlive 架构按页签 menuKey 渲染组件（无 <Routes>），重定向组件会被常驻挂载引发循环，故不使用重定向。
const ExpertPortal = lazy(() => import(/* webpackChunkName: "expert-portal" */ './pages/ExpertPortal'));
const PublishManager = lazy(() => import(/* webpackChunkName: "h5-publish" */ './pages/h5/PublishManager'));
const ExpertChat = lazy(() => import(/* webpackChunkName: "expert-chat" */ './pages/expert/ExpertChat'));
// 记忆插槽②批6：记忆管理页（平台管理区，admin-only）
const MemoryAdmin = lazy(() => import(/* webpackChunkName: "memory-admin" */ './pages/MemoryAdmin'));
// ⑤R F3（批10）：对话附件上限设置（chat-attachments 最小补件，admin-only）
const AttachmentSettings = lazy(() => import(/* webpackChunkName: "attachment-settings" */ './pages/AttachmentSettings'));
const ExpertGrants = lazy(() => import(/* webpackChunkName: "expert-grants" */ './pages/ExpertGrants'));
// 批5 5.3+5.4：DeepTutor 设置中心——布局 + 21 薄页/跳转壳（本批）+ 10 厚页（并行件已落盘）。
// chunk 命名口径 'settings-<页>'；厚页/并行件 import 暂红属预期（落盘后自愈）。
const SettingsLayout = lazy(() => import(/* webpackChunkName: "settings-layout" */ './pages/settings/SettingsLayout'));
const SettingsHub = lazy(() => import(/* webpackChunkName: "settings-hub" */ './pages/settings'));
const SettingsAgents = lazy(() => import(/* webpackChunkName: "settings-agents" */ './pages/settings/agents'));
const SettingsAgentsClaudeCode = lazy(() => import(/* webpackChunkName: "settings-agents-claude-code" */ './pages/settings/agents-claude-code'));
const SettingsAgentsCodex = lazy(() => import(/* webpackChunkName: "settings-agents-codex" */ './pages/settings/agents-codex'));
const SettingsAgentsGemini = lazy(() => import(/* webpackChunkName: "settings-agents-gemini" */ './pages/settings/agents-gemini'));
const SettingsAgentsKimi = lazy(() => import(/* webpackChunkName: "settings-agents-kimi" */ './pages/settings/agents-kimi'));
const SettingsAgentsMimo = lazy(() => import(/* webpackChunkName: "settings-agents-mimo" */ './pages/settings/agents-mimo'));
const SettingsAgentsOpencode = lazy(() => import(/* webpackChunkName: "settings-agents-opencode" */ './pages/settings/agents-opencode'));
const SettingsChat = lazy(() => import(/* webpackChunkName: "settings-chat" */ './pages/settings/chat'));
const SettingsCurriculum = lazy(() => import(/* webpackChunkName: "settings-curriculum" */ './pages/settings/curriculum'));
const SettingsAttachments = lazy(() => import(/* webpackChunkName: "settings-attachments" */ './pages/settings/attachments'));
const SettingsLlm = lazy(() => import(/* webpackChunkName: "settings-llm" */ './pages/settings/llm'));
const SettingsEmbedding = lazy(() => import(/* webpackChunkName: "settings-embedding" */ './pages/settings/embedding'));
const SettingsStt = lazy(() => import(/* webpackChunkName: "settings-stt" */ './pages/settings/stt'));
const SettingsTts = lazy(() => import(/* webpackChunkName: "settings-tts" */ './pages/settings/tts'));
const SettingsImage = lazy(() => import(/* webpackChunkName: "settings-image" */ './pages/settings/image'));
const SettingsVideo = lazy(() => import(/* webpackChunkName: "settings-video" */ './pages/settings/video'));
const SettingsDocumentParsing = lazy(() => import(/* webpackChunkName: "settings-document-parsing" */ './pages/settings/document-parsing'));
const SettingsMineru = lazy(() => import(/* webpackChunkName: "settings-mineru" */ './pages/settings/mineru'));
const SettingsModels = lazy(() => import(/* webpackChunkName: "settings-models" */ './pages/settings/models'));
const SettingsMcp = lazy(() => import(/* webpackChunkName: "settings-mcp" */ './pages/settings/mcp'));
const SettingsMemory = lazy(() => import(/* webpackChunkName: "settings-memory" */ './pages/settings/memory'));
const SettingsTools = lazy(() => import(/* webpackChunkName: "settings-tools" */ './pages/settings/tools'));
const SettingsCapabilities = lazy(() => import(/* webpackChunkName: "settings-capabilities" */ './pages/settings/capabilities'));
const SettingsAppearance = lazy(() => import(/* webpackChunkName: "settings-appearance" */ './pages/settings/appearance'));
const SettingsNetwork = lazy(() => import(/* webpackChunkName: "settings-network" */ './pages/settings/network'));
const SettingsSearch = lazy(() => import(/* webpackChunkName: "settings-search" */ './pages/settings/search'));
const SettingsStatus = lazy(() => import(/* webpackChunkName: "settings-status" */ './pages/settings/status'));
const SettingsCurriculumTextbooks = lazy(() => import(/* webpackChunkName: "settings-curriculum-textbooks" */ './pages/settings/curriculum-textbooks'));
const SettingsCurriculumChapters = lazy(() => import(/* webpackChunkName: "settings-curriculum-chapters" */ './pages/settings/curriculum-chapters'));
const SettingsCurriculumKnowledgePoints = lazy(() => import(/* webpackChunkName: "settings-curriculum-knowledge-points" */ './pages/settings/curriculum-knowledge-points'));
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
  { path: '/home', element: (() => <Navigate to="/" replace />) as any, label: '数据资产探查', menuKey: 'home' },
  { path: '/e/:slug/chat', element: ExpertChat, label: '专家对话', menuKey: 'expert_chat' },
  // v3 §三（Task5）：H5 发布管理页（12 页卡+手机框预览+二维码）
  { path: '/h5-publish', element: PublishManager, label: 'H5 发布管理', menuKey: 'h5_publish' },
  { path: '/graph', element: GraphManager, label: '图谱管理', menuKey: 'graph' },
  // v3 #10/#17（Task6）：三旧画布路由重定向 /graph?view=...（4 合 1 单入口；pathToMenuKey 旧键保留）
  { path: '/tree-model', element: (() => <Navigate to="/graph?view=quad" replace />) as any, label: '四区建模', menuKey: 'tree_model' },
  { path: '/matrix', element: (() => <Navigate to="/graph?view=matrix" replace />) as any, label: '资产矩阵', menuKey: 'matrix_model' },
  { path: '/gallery', element: (() => <Navigate to="/graph?view=neo4j" replace />) as any, label: '图库', menuKey: 'gallery' },
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
  // IA批5 5.5：LLM 合一页——/llm-config 承接设置中心复刻页（ServiceConfigEditor service="llm"，
// 形态/字段/交互 1:1）；LLMConfigManager 退役 git rm + M00 登记。
{ path: '/llm-config', element: (() => <Navigate to="/settings/llm" replace />) as any, label: 'LLM 配置', menuKey: 'llmconfig' },
  { path: '/memory-admin', element: MemoryAdmin, label: '记忆管理', menuKey: 'memory_admin' },
  { path: '/attachment-settings', element: AttachmentSettings, label: '对话附件上限', menuKey: 'attachment_settings' },
  // ⑥-2a B-2：专家赋权管理面（平台配置层——grant 三端点复用，admin-only）
  { path: '/expert-grants', label: '专家赋权', menuKey: 'expert_grants',
    element: (() => <RequireAdmin><ExpertGrants /></RequireAdmin>) as any },
  // ⑤批4（⑤e）：专家自定义页（EXPERT_PAGES 注册表驱动；⑤R R1（批12）先行版六页已退役）
  ...expertPageRoutes().map((p) => ({ path: p.path, element: p.element as any, label: p.label, menuKey: p.menuKey })),
  // ── 批5 5.3+5.4：DeepTutor 设置中心（31 页口径）——枢纽 + 薄页/跳转壳 22 页 + 厚页 10 页（并行件）。
  //    子页 menuKey 口径 'settings:<页>'、hideInMenu=true——主菜单仅「设置中心」一个入口（NAV_GROUPS
  //    settings_group 已挂 settings_hub）。RouteConfig 未收 hideInMenu 字段——as unknown as 收敛，
  //    保留运行时元数据（口径同 expertPages 的 ExpertPageConfig.hideInMenu；接线批扩字段后可去断言）。
  { path: '/settings', element: SettingsLayout, label: '设置中心', menuKey: 'settings_hub' },
  ...([
    { path: '/settings/agents', element: settingsPage(SettingsAgents), label: '伙伴和智能体', menuKey: 'settings:agents', hideInMenu: true },
    { path: '/settings/agents/claude-code', element: settingsPage(SettingsAgentsClaudeCode), label: 'Claude Code', menuKey: 'settings:agents-claude-code', hideInMenu: true },
    { path: '/settings/agents/codex', element: settingsPage(SettingsAgentsCodex), label: 'Codex', menuKey: 'settings:agents-codex', hideInMenu: true },
    { path: '/settings/agents/gemini', element: settingsPage(SettingsAgentsGemini), label: 'Gemini CLI', menuKey: 'settings:agents-gemini', hideInMenu: true },
    { path: '/settings/agents/kimi', element: settingsPage(SettingsAgentsKimi), label: 'Kimi CLI', menuKey: 'settings:agents-kimi', hideInMenu: true },
    { path: '/settings/agents/mimo', element: settingsPage(SettingsAgentsMimo), label: 'MiMo Code', menuKey: 'settings:agents-mimo', hideInMenu: true },
    { path: '/settings/agents/opencode', element: settingsPage(SettingsAgentsOpencode), label: 'opencode', menuKey: 'settings:agents-opencode', hideInMenu: true },
    { path: '/settings/chat', element: settingsPage(SettingsChat), label: '聊天', menuKey: 'settings:chat', hideInMenu: true },
    { path: '/settings/curriculum', element: settingsPage(SettingsCurriculum), label: '设置管理', menuKey: 'settings:curriculum', hideInMenu: true },
    { path: '/settings/attachments', element: settingsPage(SettingsAttachments), label: '附件', menuKey: 'settings:attachments', hideInMenu: true },
    { path: '/settings/appearance', element: settingsPage(SettingsAppearance), label: '外观', menuKey: 'settings:appearance', hideInMenu: true },
    { path: '/settings/network', element: settingsPage(SettingsNetwork), label: '网络', menuKey: 'settings:network', hideInMenu: true },
    { path: '/settings/llm', element: settingsPage(SettingsLlm), label: 'LLM', menuKey: 'settings:llm', hideInMenu: true },
    { path: '/settings/embedding', element: settingsPage(SettingsEmbedding), label: '嵌入模型', menuKey: 'settings:embedding', hideInMenu: true },
    { path: '/settings/stt', element: settingsPage(SettingsStt), label: '语音识别', menuKey: 'settings:stt', hideInMenu: true },
    { path: '/settings/tts', element: settingsPage(SettingsTts), label: '语音合成', menuKey: 'settings:tts', hideInMenu: true },
    { path: '/settings/image', element: settingsPage(SettingsImage), label: '文生图', menuKey: 'settings:image', hideInMenu: true },
    { path: '/settings/video', element: settingsPage(SettingsVideo), label: '文生视频', menuKey: 'settings:video', hideInMenu: true },
    { path: '/settings/document-parsing', element: settingsPage(SettingsDocumentParsing), label: '文档解析', menuKey: 'settings:document-parsing', hideInMenu: true },
    { path: '/settings/mineru', element: settingsPage(SettingsMineru), label: 'MinerU', menuKey: 'settings:mineru', hideInMenu: true },
    { path: '/settings/models', element: settingsPage(SettingsModels), label: '模型', menuKey: 'settings:models', hideInMenu: true },
    { path: '/settings/mcp', element: settingsPage(SettingsMcp), label: 'MCP', menuKey: 'settings:mcp', hideInMenu: true },
    { path: '/settings/memory', element: settingsPage(SettingsMemory), label: '记忆', menuKey: 'settings:memory', hideInMenu: true },
    { path: '/settings/tools', element: settingsPage(SettingsTools), label: '工具', menuKey: 'settings:tools', hideInMenu: true },
    { path: '/settings/capabilities', element: settingsPage(SettingsCapabilities), label: '能力', menuKey: 'settings:capabilities', hideInMenu: true },
    { path: '/settings/search', element: settingsPage(SettingsSearch), label: '搜索', menuKey: 'settings:search', hideInMenu: true },
    { path: '/settings/status', element: settingsPage(SettingsStatus), label: '状态', menuKey: 'settings:status', hideInMenu: true },
    { path: '/settings/curriculum/textbooks', element: settingsPage(SettingsCurriculumTextbooks), label: '课本管理', menuKey: 'settings:curriculum-textbooks', hideInMenu: true },
    { path: '/settings/curriculum/chapters', element: settingsPage(SettingsCurriculumChapters), label: '章节管理', menuKey: 'settings:curriculum-chapters', hideInMenu: true },
    { path: '/settings/curriculum/knowledge-points', element: settingsPage(SettingsCurriculumKnowledgePoints), label: '知识点管理', menuKey: 'settings:curriculum-knowledge-points', hideInMenu: true },
  ] as unknown as RouteConfig[]),
  // ⑤R R1（批12）：旧 tutor 后台骨架 /e/sishu/admin 退役（AdminHome/AdminZones 删除；
  // 后台三项顶级入口=ExpertPages 注册 adminTop 件；legacy 键 e:{slug}:admin 由 App.tsx 回落 chat）
  { path: '*', element: ExpertPortal, label: '专家门户', menuKey: 'portal' },
];

export { MENU_LABELS as menuLabels };
// 向后兼容：原 routes.tsx 导出的两个映射，现由 navigation.tsx 维护
export { menuKeyToPath, pathToMenuKey } from './config/navigation';
