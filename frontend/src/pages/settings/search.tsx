/**
 * 批5 5.3：/settings/search（源 (utility)/settings/search/page.tsx 逐字移植）。
 * 差异登记：源 "use client"/react-i18next 层省略——t('English') 直接取 locales/zh/app.json 译文。
 * 共享组件 ServiceConfigEditor / SettingsPageHeader(shared) 为并行件（按名 import，暂红属预期）。
 */
import { ServiceConfigEditor } from '../../components/settings/ServiceConfigEditor';
import { SettingsPageHeader } from '../../components/settings/shared';

export default function SearchSettingsPage() {
  return (
    <div>
      <SettingsPageHeader
        title="搜索"
        description="配置网络搜索供应商。web_search 工具和任何访问公开网络的 agent 步骤都会用到。"
      />
      <ServiceConfigEditor service="search" />
    </div>
  );
}
