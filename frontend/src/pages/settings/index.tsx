/**
 * 批5 5.3：设置枢纽 /settings（源 (utility)/settings/page.tsx 141B 逐字移植）。
 * 源页全文即 <SettingsHub />；组件为并行件（批5 5.2 壳族整件 1:1——标题+Status 常驻模块+
 * 分类块网格，next/link→react-router Link、lucide→antd、i18n 恒中文）。
 * tupu 二级侧栏（四分区）由 SettingsLayout 承载；枢纽态主区同样渲染本组件（见 SettingsLayout）。
 */
import SettingsHub from '../../components/settings/SettingsHub';

export default function SettingsIndexPage() {
  return <SettingsHub />;
}
