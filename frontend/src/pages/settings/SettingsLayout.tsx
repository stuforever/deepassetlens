/**
 * 批5 5.3：设置中心二级布局 SettingsLayout（源 (utility)/settings/layout.tsx 复刻——antd 重建 + tupu 二级侧栏）。
 * 源 layout 逐字保留：SettingsProvider + SettingsMain{children} + SettingsTourOverlay（挂布局层，
 * 引导跨路由存活）。tupu 增强（任务书 5.3）：主内容左侧挂「设置专属二级侧栏」——分区口径四组：
 *   通用 / 服务 / Agent / 进阶（Agent 组只挂 agents 一项，六家子页由 agents 枢纽在主区内部导航）。
 * 当前页高亮（location.pathname 精确匹配）；点击 navigate('/settings/<页>')。
 * 主区 = SettingsMain（并行件 5.2 壳族：面包屑/工具栏/滚动容器 1:1）
 *        {isHub ? <SettingsHub /> : <Outlet />}。
 *   —— KeepAlive 页签架构无 <Routes>（Outlet 无嵌套上下文渲染 null）：/settings 页签渲染本布局，
 *   枢纽态直接渲染并行件 SettingsHub（源 settings/page.tsx 141B 逐字语义）；子页态走 <Outlet />
 *   （react-router 嵌套接线落位后生效；子页依赖本布局的 SettingsProvider——接线批注意）。
 * SETTINGS_SECTIONS 分区表由本文件导出（源 lib/settings-nav 语义的 tupu 分区口径；清单外不落新文件）。
 */
import type { ComponentType } from 'react';
import { Menu } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  ApiOutlined,
  AppstoreOutlined,
  AudioOutlined,
  BgColorsOutlined,
  BookOutlined,
  ClusterOutlined,
  ControlOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  FilePdfOutlined,
  FileSearchOutlined,
  MessageOutlined,
  NodeIndexOutlined,
  PaperClipOutlined,
  PictureOutlined,
  PoweroffOutlined,
  ReadOutlined,
  RobotOutlined,
  RocketOutlined,
  SearchOutlined,
  SoundOutlined,
  KeyOutlined, SafetyOutlined, TeamOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';

import { tokens } from '../../theme/tokens';
import { SettingsProvider } from '../../components/settings/SettingsContext';
import SettingsMain from '../../components/settings/SettingsMain';
import { SettingsTourOverlay } from '../../components/settings/SettingsTourOverlay';
import SettingsHub from '../../components/settings/SettingsHub';

/** 分区导航项：path=路由路径（Menu 选中键与 navigate 目标同源）。 */
export interface SettingsNavItem {
  /** 路由路径（/settings/<页>） */
  path: string;
  label: string;
  icon: ComponentType<any>;
}

/** 分区（通用/服务/Agent/进阶）。 */
export interface SettingsSection {
  key: string;
  title: string;
  items: SettingsNavItem[];
}

/**
 * 设置信息架构（源 web/lib/settings-nav.ts 的 tupu 分区口径）。
 * lucide→antd 最近图标映射（登记）：Palette→BgColorsOutlined、Paperclip→PaperClipOutlined、
 * MessagesSquare→MessageOutlined、Network→ClusterOutlined、Search→SearchOutlined、
 * Brain→RobotOutlined、Database→DatabaseOutlined、Mic→AudioOutlined、AudioLines→SoundOutlined、
 * Image→PictureOutlined、Clapperboard→VideoCameraOutlined、FileScan→FileSearchOutlined、
 * Boxes→AppstoreOutlined、BrainCircuit→DeploymentUnitOutlined、Wrench→ToolOutlined、
 * SlidersHorizontal→ControlOutlined、Bot→RobotOutlined。
 * 「进阶」预留分区：curriculum/attachments 已并语义外迁（教学设置/对话附件上限承接），暂无挂项。
 */
/**
 * 设置信息架构（批⑥ v4§5.3 八分区重排——取代批5 5.3 的四组口径）：
 * 通用/模型与服务/知识与检索/智能体/数据探索/数据治理/安全/私塾教学。
 * 批③过渡期挂 ⚙ 面板的平台能力/治理项在此收口：技能管理/金标锚定/专家赋权→智能体，
 * 知识库→知识与检索，运行观测/引擎工作台→数据治理，安全控制中心→安全，记忆管理→数据探索。
 * 缺页登记（§5.3 有名无页，不造页）：个人信息/Rerank/OCR/全文检索/图谱检索/向量索引/
 * 元模型版本/审计与血缘/认证与 RBAC/数据权限/作文参数/意图类别/日志——随后续需求批补。
 * lucide→antd 最近图标映射（登记）：Palette→BgColorsOutlined、Paperclip→PaperClipOutlined、
 * MessagesSquare→MessageOutlined、Network→ClusterOutlined、Search→SearchOutlined、
 * Brain→RobotOutlined、Database→DatabaseOutlined、Mic→AudioOutlined、AudioLines→SoundOutlined、
 * Image→PictureOutlined、Clapperboard→VideoCameraOutlined、FileScan→FileSearchOutlined、
 * Boxes→AppstoreOutlined、BrainCircuit→DeploymentUnitOutlined、Wrench→ToolOutlined、
 * SlidersHorizontal→ControlOutlined、Bot→RobotOutlined。
 */
export const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    key: 'general',
    title: '通用',
    items: [
      { path: '/settings/appearance', label: '外观', icon: BgColorsOutlined },
      { path: '/settings/attachments', label: '附件', icon: PaperClipOutlined },
      { path: '/settings/chat', label: '聊天', icon: MessageOutlined },
      { path: '/settings/network', label: '网络', icon: ClusterOutlined },
      { path: '/settings/status', label: '状态', icon: DashboardOutlined },
      { path: '/settings/search', label: '搜索', icon: SearchOutlined },
    ],
  },
  {
    key: 'models',
    title: '模型与服务',
    items: [
      { path: '/settings/llm', label: 'LLM', icon: RobotOutlined },
      { path: '/settings/embedding', label: '嵌入模型', icon: DatabaseOutlined },
      { path: '/settings/stt', label: '语音识别', icon: AudioOutlined },
      { path: '/settings/tts', label: '语音合成', icon: SoundOutlined },
      { path: '/settings/image', label: '文生图', icon: PictureOutlined },
      { path: '/settings/video', label: '文生视频', icon: VideoCameraOutlined },
      { path: '/settings/models', label: '模型', icon: AppstoreOutlined },
      { path: '/settings/mineru', label: 'MinerU', icon: FilePdfOutlined },
      { path: '/settings/mcp', label: 'MCP', icon: ApiOutlined },
    ],
  },
  {
    key: 'knowledge',
    title: '知识与检索',
    items: [
      { path: '/vector', label: '知识库管理', icon: BookOutlined },
      { path: '/settings/document-parsing', label: '文档解析', icon: FileSearchOutlined },
    ],
  },
  {
    key: 'agents',
    title: '智能体',
    items: [
      { path: '/settings/tools', label: '工具', icon: ToolOutlined },
      { path: '/settings/capabilities', label: '能力', icon: ControlOutlined },
      { path: '/settings/agents', label: '伙伴和智能体', icon: RobotOutlined },
      { path: '/skills', label: '技能管理', icon: RocketOutlined },
      { path: '/golden-qa', label: '金标锚定', icon: FileSearchOutlined },
      { path: '/expert-grants', label: '专家赋权', icon: TeamOutlined },
    ],
  },
  {
    key: 'explore',
    title: '数据探索',
    items: [
      { path: '/settings/memory', label: '记忆', icon: DeploymentUnitOutlined },
      { path: '/memory-admin', label: '记忆管理', icon: BookOutlined },
    ],
  },
  {
    key: 'governance',
    title: '数据治理',
    items: [
      { path: '/governance', label: '运行观测', icon: DashboardOutlined },
      { path: '/engine-workbench', label: '引擎工作台', icon: ThunderboltOutlined },
    ],
  },
  {
    key: 'security',
    title: '安全',
    items: [{ path: '/security-controls', label: '安全控制中心', icon: PoweroffOutlined }],
  },
  {
    key: 'iam',
    title: '权限管理',
    items: [
      { path: '/settings/iam/users', label: '用户管理', icon: TeamOutlined },
      { path: '/settings/iam/roles', label: '角色管理', icon: SafetyOutlined },
      { path: '/expert-grants', label: '专家赋权', icon: KeyOutlined },
      { path: '/settings/iam/audit', label: '审计日志', icon: FileSearchOutlined },
    ],
  },
  {
    key: 'teaching',
    title: '私塾教学',
    items: [
      { path: '/settings/curriculum-textbooks', label: '课本管理', icon: BookOutlined },
      { path: '/settings/curriculum-chapters', label: '章节管理', icon: ReadOutlined },
      { path: '/settings/curriculum-knowledge-points', label: '知识点管理', icon: NodeIndexOutlined },
    ],
  },
];

/** 侧栏菜单 items（空分区不渲染——antd Menu type:group）。 */
const sidebarMenuItems = SETTINGS_SECTIONS.filter((s) => s.items.length > 0).map((section) => ({
  key: section.key,
  label: section.title,
  type: 'group' as const,
  children: section.items.map((item) => ({
    key: item.path,
    icon: <item.icon />,
    label: item.label,
  })),
}));

/**
 * 设置中心二级布局：左侧分区侧栏 + 右侧 SettingsMain（面包屑/工具栏/主区）。
 * 枢纽态（pathname==='/settings'）主区渲染 SettingsHub（并行件——无 <Routes> 架构下
 * Outlet 为空，见文件头注）；子页态 = <Outlet />。Provider/TourOverlay 沿源 layout 挂布局层。
 */
export default function SettingsLayout({ children }: { children?: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const isHub = location.pathname === '/settings';

  return (
    <SettingsProvider>
      <div style={{ display: 'flex', height: '100%', minHeight: 0 }}>
        <aside data-testid="settings-layout-sidebar"
          style={{
            width: 200,
            flexShrink: 0,
            borderRight: `1px solid ${tokens.colors.border}`,
            background: tokens.colors.bgContent,
            overflowY: 'auto',
            paddingTop: 12,
            paddingBottom: 12,
          }}
        >
          <Menu
            mode="inline"
            items={sidebarMenuItems}
            selectedKeys={[location.pathname]}
            onClick={({ key }) => navigate(String(key))}
            style={{ borderInlineEnd: 'none', background: 'transparent' }}
          />
        </aside>
        <main style={{ flex: 1, minWidth: 0 }}>
          <SettingsMain>{isHub ? <SettingsHub /> : (children ?? <Outlet />)}</SettingsMain>
        </main>
      </div>
      {/* 挂布局层：跨路由引导在枢纽与子页间导航时存活（源 layout 注释语义） */}
      <SettingsTourOverlay />
    </SettingsProvider>
  );
}
