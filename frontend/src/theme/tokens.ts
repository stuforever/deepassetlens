/**
 * 设计 Token —— 数据智能工作台视觉规范的唯一来源。
 *
 * 三种消费方式：
 *   1. antd 组件：通过 ConfigProvider 的 theme.token 注入（见 App.tsx），组件内用 theme.useToken() 读取。
 *   2. 自定义组件：直接 import { tokens } 取常量，避免硬编码。
 *   3. 全局/CSS：index.css 的 :root 已同步同名 CSS 变量（--color-primary 等）。
 *
 * 铁律：新代码不得新增零散硬编码颜色/间距/圆角，一律走本文件或 antd token。
 */
import type { ThemeConfig } from 'antd';

/* ---------- 颜色 ---------- */
export const colors = {
  // 品牌色
  primary: '#2563EB', // 主操作色
  primaryHover: '#1D4ED8',
  primaryActive: '#1E40AF',
  primaryBg: '#EFF6FF', // 主色浅底（选中态/提示条）

  // AI 辅助色（仅用于智能/AI 能力标识）
  ai: '#7C3AED',
  aiBg: '#F5F3FF',

  // 语义色
  success: '#16A34A',
  successBg: '#F0FDF4',
  warning: '#D97706',
  warningBg: '#FFFBEB',
  error: '#DC2626',
  errorBg: '#FEF2F2',
  info: '#2563EB',
  infoBg: '#EFF6FF',

  // 中性色（slate 冷色调）
  bgPage: '#F6F8FC', // 页面背景
  bgContent: '#FFFFFF', // 内容背景
  bgSubtle: '#F9FAFB', // 次级容器背景（表头/悬浮行）
  bgHover: '#F3F4F6',

  textPrimary: '#0F172A',
  textSecondary: '#64748B',
  textTertiary: '#94A3B8',
  textDisabled: '#9CA3AF',
  textInverse: '#FFFFFF',

  border: '#E2E8F0',
  borderStrong: '#CBD5E1',
} as const;

/* ---------- 间距（只用 4/8/12/16/20/24/32） ---------- */
export const space = {
  s1: 4,
  s2: 8,
  s3: 12,
  s4: 16,
  s5: 20,
  s6: 24,
  s7: 32,
} as const;

/* ---------- 圆角 ---------- */
export const radius = {
  default: 6, // 默认控件
  card: 8, // 卡片/容器
  pill: 999, // 胶囊/标签
} as const;

/* ---------- 字号 ---------- */
export const fontSize = {
  display: 28, // 落地页主视觉（仅此一处）
  pageTitle: 20, // 页面标题
  sectionTitle: 16, // 区块标题
  body: 14, // 正文
  caption: 12, // 表格辅助/说明
  small: 12,
} as const;

export const fontWeight = {
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const;

/* ---------- 控件高度 ---------- */
export const controlHeight = {
  default: 32, // 默认按钮/输入
  primary: 36, // 主要页面操作
  tableRow: 44, // 标准表格行
  tableRowCompact: 36, // 紧凑表格行
} as const;

/* ---------- 布局尺寸 ---------- */
export const layout = {
  headerHeight: 48,
  siderWidth: 216,
  siderCollapsedWidth: 64,
  tabsHeight: 36,
  contentPadding: 20,
  // 数据问答工作台
  chatSiderWidth: 180,
  chatContextWidth: 320,
  chatAnswerMaxWidth: 1040,
  chatInputMinHeight: 56,
  chatInputMaxHeight: 140,
} as const;

/* ---------- 阴影层级（新增，S0-S3） ---------- */
export const elevation = {
  s0: 'none', // 默认平铺
  s1: '0 1px 2px rgba(15,23,42,.04), 0 1px 3px rgba(15,23,42,.06)', // 卡片静置/结果表容器
  s2: '0 4px 12px rgba(15,23,42,.08), 0 2px 4px rgba(15,23,42,.04)', // 悬浮/Popover/悬停卡片
  s3: '0 12px 32px rgba(15,23,42,.14), 0 4px 8px rgba(15,23,42,.06)', // Modal/Drawer/输入 composer
} as const;

/* ---------- 品牌渐变（新增，克制：仅落地页主视觉 / AI 徽标 / 主发送按钮 3 处） ---------- */
export const brandGradient = 'linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)';

/* ---------- 图表色板（新增，画布/图谱循环取色，禁止随机色） ---------- */
export const chartPalette = [
  '#2563EB', '#7C3AED', '#0891B2', '#059669',
  '#D97706', '#DC2626', '#64748B', '#BE185D',
] as const;

/* ---------- 三轨M8(U3)：画布实体语义色（五页共用——§四统一，消灭两套并存） ---------- */
export const entitySemanticColors = {
  master: '#2563EB',  // 主数据 蓝
  activity: '#0891B2', // 活动 青
  data: '#DC2626',     // 数据 红
  concept: '#7C3AED',  // 概念 紫
} as const;

/* ---------- 动效 token（新增） ---------- */
export const motion = {
  duration: { fast: 120, base: 200, slow: 320 },
  easing: { enter: 'cubic-bezier(.2,.8,.2,1)', exit: 'cubic-bezier(.4,0,.6,1)' },
} as const;

/* ---------- antd 主题 token（注入 ConfigProvider） ---------- */
export const antdThemeToken = {
  colorPrimary: colors.primary,
  colorSuccess: colors.success,
  colorWarning: colors.warning,
  colorError: colors.error,
  colorInfo: colors.info,

  colorTextBase: colors.textPrimary,
  colorText: colors.textPrimary,
  colorTextSecondary: colors.textSecondary,
  colorTextTertiary: colors.textTertiary,
  colorTextDescription: colors.textTertiary,

  colorBgLayout: colors.bgPage,
  colorBgContainer: colors.bgContent,
  colorBgElevated: colors.bgContent,
  colorBorder: colors.border,
  colorBorderSecondary: colors.border,

  borderRadius: radius.default,
  borderRadiusLG: radius.card,
  borderRadiusSM: 4,

  fontSize: fontSize.body,
  fontSizeHeading5: fontSize.sectionTitle,
  fontSizeLG: fontSize.body,

  controlHeight: controlHeight.default,
  controlHeightLG: controlHeight.primary,

  // 链接色跟随主色
  colorLink: colors.primary,
  colorLinkHover: colors.primaryHover,
  colorLinkActive: colors.primaryActive,

  // 阴影层级（B1 美化：S1 普通容器 / S2 悬浮）
  boxShadow: elevation.s1,
  boxShadowSecondary: elevation.s2,
} as const;

/* ---------- antd 组件级 token ---------- */
export const antdComponents: ThemeConfig['components'] = {
  Menu: {
    itemHeight: 36,
    itemMarginInline: 0,
    subMenuItemBg: 'transparent',
    itemSelectedBg: colors.primaryBg,
    itemSelectedColor: colors.primary,
    itemBorderRadius: radius.default, // B1 美化：0 => 6（左导航 hover 浮起）
  },
  Layout: {
    headerBg: colors.bgContent,
    siderBg: colors.bgContent,
    bodyBg: colors.bgPage,
  },
  Tabs: {
    horizontalItemPadding: '8px 16px',
    horizontalMargin: '0px',
    cardPadding: '6px 16px',
    titleFontSize: 13,
    inkBarColor: colors.primary,
    itemColor: colors.textTertiary,
    itemSelectedColor: colors.primary,
    itemHoverColor: colors.textSecondary,
  },
  Table: {
    headerBg: colors.bgSubtle,
    headerColor: colors.textSecondary,
    rowHoverBg: colors.bgHover,
    borderColor: colors.border,
    cellPaddingBlock: 12,
    cellPaddingInline: 12,
  },
  Card: {
    borderRadiusLG: radius.card,
    paddingLG: space.s5,
  },
  Button: {
    borderRadius: radius.default,
    controlHeight: controlHeight.default,
    controlHeightLG: controlHeight.primary,
  },
  Input: {
    borderRadius: radius.default,
    controlHeight: controlHeight.default,
  },
  Select: {
    borderRadius: radius.default,
    controlHeight: controlHeight.default,
  },
  Drawer: {
    borderRadiusLG: radius.card,
  },
  Modal: {
    boxShadow: elevation.s3, // B1 美化：Modal 抬升到 S3
  },
};

/* ---------- 三轨M6(U1) §2.4：空间色 token（落点仅三处：侧栏空间组图标着色、
 * 激活项左 3px 色条、对话页页头 3px 色条；DT 域内容区不动——路线 B 边界） ---------- */
export const spaceColors = {
  wenshu: '#2563EB', // 数据探索 蓝
  sishu: '#D97706',  // 私塾先生 琥珀
  h5: '#0891B2',     // 私塾先生h5 青
} as const;

/* ---------- 聚合导出（自定义组件消费） ---------- */
export const tokens = {
  colors,
  space,
  radius,
  fontSize,
  fontWeight,
  controlHeight,
  layout,
  elevation,
  brandGradient,
  chartPalette,
  motion,
  entitySemanticColors,
  spaceColors,
} as const;
