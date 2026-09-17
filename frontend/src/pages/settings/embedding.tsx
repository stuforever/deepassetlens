/**
 * 批5 5.3：/settings/embedding（源 (utility)/settings/embedding/page.tsx 逐字移植）。
 * 差异登记：源 "use client"/react-i18next 层省略——t('English') 直接取 locales/zh/app.json 译文。
 * 共享组件 ServiceConfigEditor / SettingsPageHeader(shared) 为并行件（按名 import，暂红属预期）。
 */
import { ServiceConfigEditor } from '../../components/settings/ServiceConfigEditor';
import { SettingsPageHeader } from '../../components/settings/shared';

export default function EmbeddingSettingsPage() {
  return (
    <div>
      <SettingsPageHeader
        title="嵌入模型"
        description="配置嵌入模型。用于检索和知识库入库。"
      />
      <ServiceConfigEditor service="embedding" />
    </div>
  );
}
