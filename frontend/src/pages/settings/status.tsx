/**
 * 批5 5.3：/settings/status（源 (utility)/settings/status/page.tsx 逐字移植——重定向页）。
 * tupu 落点：/settings（设置枢纽）。
 * KeepAlive 页签架构规避口径：useEffect 单次触发 + Spinner 兜底（挂载即跳、不留死页）。
 */
import { useEffect } from 'react';
import { Spin } from 'antd';
import { useNavigate } from 'react-router-dom';

// Status was demoted to a resident module on the settings hub. Keep this route
// as a redirect so existing bookmarks/links (and the guided tour fallback)
// still land somewhere sensible.
export default function StatusSettingsPage() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/settings', { replace: true });
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
      <span>正在前往设置中心…</span>
    </div>
  );
}
