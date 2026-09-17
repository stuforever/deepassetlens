/**
 * 批5 5.3：/settings/chat 子枢纽（源 (utility)/settings/chat/page.tsx 逐字移植）。
 * 共享分区网格 SettingsSectionGrid 为并行件（按名 import，暂红属预期）。
 */
import SettingsSectionGrid from '../../components/settings/SettingsSectionGrid';

export default function ChatSettingsPage() {
  return <SettingsSectionGrid categoryKey="chat" />;
}
