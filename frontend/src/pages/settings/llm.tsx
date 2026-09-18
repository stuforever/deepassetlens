/**
 * 批5 5.3：/settings/llm（源 (utility)/settings/llm/page.tsx 逐字移植）。
 * 差异登记：源 "use client"/react-i18next 层省略——t('English') 直接取 locales/zh/app.json 译文。
 * 共享组件 ServiceConfigEditor / SettingsPageHeader(shared) 为并行件（按名 import，暂红属预期）。
 */
import { ServiceConfigEditor } from '../../components/settings/ServiceConfigEditor';
import { SettingsPageHeader } from '../../components/settings/shared';
import { SettingsToolbar } from '../../components/settings/SettingsToolbar';

export default function LlmSettingsPage() {
  return (
    <div>
      {/* 引擎批8 8.1：补 DT 叶页形态——sticky 保存/应用工具栏（IA批5 壳族未挂
          SettingsMain，目录编辑器无处落盘；/llm-config 与 /settings/llm 同组件同生效）。
          /llm-config 数据面已切③连接目录（SettingsContext llmDirectory 适配器）。 */}
      <SettingsToolbar />
      <SettingsPageHeader
        title="LLM"
        description="配置语言模型。当前激活的模型用于聊天和大多数 agent 推理。"
      />
      <ServiceConfigEditor service="llm" />
    </div>
  );
}
