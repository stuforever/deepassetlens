/**
 * 批5 5.3：/settings/models 子枢纽（源 (utility)/settings/models/page.tsx 逐字移植）。
 * 共享分区网格 SettingsSectionGrid 为并行件（按名 import，暂红属预期）。
 */
import SettingsSectionGrid from '../../components/settings/SettingsSectionGrid';

export default function ModelsSettingsPage() {
  return <SettingsSectionGrid categoryKey="models" />;
}
