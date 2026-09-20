/**
 * 批5 5.4 防双轨跳转：/settings/curriculum → /e/sishu/admin/settings/curriculum（replace）。
 * 源 (utility)/settings/curriculum/page.tsx=<SettingsSectionGrid categoryKey="curriculum" />
 * （设置管理/课程管理：课本/章节/知识点磁贴入口）；tupu 该语义已由教学设置页承接
 * （expertPages e:sishu:admin:settings:curriculum——curriculum→教学设置先例），
 * 保留路由仅作跳转壳防双轨，不再复刻分区磁贴。
 * KeepAlive 页签架构规避口径：重定向组件会被常驻挂载——useEffect 单次触发 + Spinner 兜底
 * （沿 routes.tsx「不使用重定向组件」批注先例：挂载即跳、不留死页）。
 */
import { useEffect } from 'react';
import { Spin } from 'antd';
import { useNavigate } from 'react-router-dom';

export default function CurriculumSettingsPage() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/e/sishu/admin/settings/curriculum', { replace: true });
  }, [navigate]);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        padding: 48,
        fontSize: 13,
      }}
    >
      <Spin size="small" />
      <span>正在前往教学设置…</span>
    </div>
  );
}
