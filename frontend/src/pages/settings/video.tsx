/**
 * 批5 5.3：/settings/video（源 (utility)/settings/video/page.tsx 逐字移植）。
 * 差异登记：源 "use client"/react-i18next 层省略——t('English') 直接取 locales/zh/app.json 译文。
 * 共享组件 ServiceConfigEditor / SettingsPageHeader(shared) 为并行件（按名 import，暂红属预期）。
 */
import { ServiceConfigEditor } from '../../components/settings/ServiceConfigEditor';
import { SettingsPageHeader } from '../../components/settings/shared';

export default function VideoGenSettingsPage() {
  return (
    <div>
      <SettingsPageHeader
        title="文生视频"
        description="chat「videogen」工具使用的文生视频模型。渲染为异步任务，可能需要一分钟以上。使用火山引擎 Seedance 等异步任务供应商。"
      />
      <ServiceConfigEditor service="videogen" />
    </div>
  );
}
