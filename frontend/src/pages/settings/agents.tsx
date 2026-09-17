/**
 * 批5 5.3：/settings/agents 枢纽（源 (utility)/settings/agents/page.tsx 逐字移植）。
 * 共享分区网格 SettingsSectionGrid 为并行件（按名 import，暂红属预期）。
 * 六家子页（claude-code/codex/gemini/kimi/mimo/opencode）由本枢纽在主区内部导航（侧栏只挂本项）。
 */
import SettingsSectionGrid from '../../components/settings/SettingsSectionGrid';

export default function AgentsSettingsPage() {
  return <SettingsSectionGrid categoryKey="agents" />;
}
