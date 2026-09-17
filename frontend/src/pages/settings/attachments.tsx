/**
 * IA批5 5.4 防双轨跳转壳：/settings/attachments → /attachment-settings。
 * B0 已把「对话附件上限」语义并入 /attachment-settings（最小页已挂后台配置组）——
 * 此处仅跳转，防同一语义双轨（对齐 curriculum→教学设置先例）。
 * 注：DT 原页为全功能附件设置页（大小限制+提取预算+全局 Apply）——源文在原仓
 * web/app/(utility)/settings/attachments/page.tsx，可按复刻纪律随时恢复（台账 E-13 登记）。
 */
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spin } from 'antd';

export default function SettingsAttachmentsRedirect() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate('/attachment-settings', { replace: true });
  }, [navigate]);
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 320, gap: 12 }}>
      <Spin />
      <span style={{ color: 'var(--text-secondary, #666)' }}>正在前往对话附件设置…</span>
    </div>
  );
}
