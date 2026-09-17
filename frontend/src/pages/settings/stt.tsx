/**
 * 批5 5.3：/settings/stt（源 (utility)/settings/stt/page.tsx 逐字移植）。
 * 差异登记：源 "use client"/react-i18next 层省略——t('English') 直接取 locales/zh/app.json 译文。
 * 共享组件 ServiceConfigEditor / SettingsPageHeader(shared) 为并行件（按名 import，暂红属预期）。
 */
import { ServiceConfigEditor } from '../../components/settings/ServiceConfigEditor';
import { SettingsPageHeader } from '../../components/settings/shared';

export default function SttSettingsPage() {
  return (
    <div>
      <SettingsPageHeader
        title="语音识别"
        description="转写聊天输入框的麦克风录音。兼容任意 OpenAI 风格的音频接口——OpenAI、Groq、SiliconFlow、Azure 或本地服务。"
      />
      <ServiceConfigEditor service="stt" />
    </div>
  );
}
