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
  ClusterOutlined,
  ControlOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  FilePdfOutlined,
  FileSearchOutlined,
  MessageOutlined,
  PaperClipOutlined,
  PictureOutlined,
  RobotOutlined,
  SearchOutlined,
  SoundOutlined,
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
    key: 'service',
    title: '服务',
    items: [
      { path: '/settings/llm', label: 'LLM', icon: RobotOutlined },
      { path: '/settings/embedding', label: '嵌入模型', icon: DatabaseOutlined },
      { path: '/settings/stt', label: '语音识别', icon: AudioOutlined },
      { path: '/settings/tts', label: '语音合成', icon: SoundOutlined },
      { path: '/settings/image', label: '文生图', icon: PictureOutlined },
      { path: '/settings/video', label: '文生视频', icon: VideoCameraOutlined },
      { path: '/settings/document-parsing', label: '文档解析', icon: FileSearchOutlined },
      { path: '/settings/mineru', label: 'MinerU', icon: FilePdfOutlined },
      { path: '/settings/models', label: '模型', icon: AppstoreOutlined },
      { path: '/settings/mcp', label: 'MCP', icon: ApiOutlined },
      { path: '/settings/memory', label: '记忆', icon: DeploymentUnitOutlined },
      { path: '/settings/tools', label: '工具', icon: ToolOutlined },
      { path: '/settings/capabilities', label: '能力', icon: ControlOutlined },
    ],
  },
  {
    key: 'agent',
    title: 'Agent',
    items: [{ path: '/settings/agents', label: '伙伴和智能体', icon: RobotOutlined }],
  },
  {
    key: 'advanced',
    title: '进阶',
    // 预留分区（挂项随后续批补位；空组不渲染）
    items: [],
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
export default function SettingsLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const isHub = location.pathname === '/settings';

  return (
    <SettingsProvider>
      <div style={{ display: 'flex', height: '100%', minHeight: 0 }}>
        <aside
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
          <SettingsMain>{isHub ? <SettingsHub /> : <Outlet />}</SettingsMain>
        </main>
      </div>
      {/* 挂布局层：跨路由引导在枢纽与子页间导航时存活（源 layout 注释语义） */}
      <SettingsTourOverlay />
    </SettingsProvider>
  );
}
