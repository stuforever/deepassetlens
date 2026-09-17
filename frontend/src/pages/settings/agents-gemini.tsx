/**
 * 批5 5.3：/settings/agents/gemini（源 (utility)/settings/agents/gemini/page.tsx 逐字移植）。
 * 共享编辑器 SubagentSettingsEditor 为并行件（按名 import，暂红属预期）。
 */
import { SubagentSettingsEditor } from '../../components/settings/SubagentSettingsEditor';

export default function GeminiAgentSettingsPage() {
  return <SubagentSettingsEditor kind="gemini" />;
}
