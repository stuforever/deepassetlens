/**
 * 批5 5.3：/settings/image（源 (utility)/settings/image/page.tsx 逐字移植）。
 * 差异登记：源 "use client"/react-i18next 层省略——t('English') 直接取 locales/zh/app.json 译文。
 * 共享组件 ServiceConfigEditor / SettingsPageHeader(shared) 为并行件（按名 import，暂红属预期）。
 */
import { ServiceConfigEditor } from '../../components/settings/ServiceConfigEditor';
import { SettingsPageHeader } from '../../components/settings/shared';

export default function ImageGenSettingsPage() {
  return (
    <div>
      <SettingsPageHeader
        title="文生图"
        description="chat「imagegen」工具使用的文生图模型。兼容任意 OpenAI 风格的 /images/generations 接口——OpenAI、火山引擎 Seedream 或兼容网关。"
      />
      <ServiceConfigEditor service="imagegen" />
    </div>
  );
}
