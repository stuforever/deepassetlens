/**
 * 批5 5.3：/settings/mineru（源 (utility)/settings/mineru/page.tsx 逐字移植——重定向页）。
 * tupu 落点：/settings/document-parsing（厚页并行件）。
 * KeepAlive 页签架构规避口径：useEffect 单次触发 + Spinner 兜底（挂载即跳、不留死页）。
 */
import { useEffect } from 'react';
import { Spin } from 'antd';
import { useNavigate } from 'react-router-dom';

// The MinerU settings page was generalized into the multi-engine Document
// Parsing page. Keep this route as a redirect so existing bookmarks/links work.
export default function MinerUSettingsRedirect() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/settings/document-parsing', { replace: true });
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
      <span>正在前往文档解析…</span>
    </div>
  );
}
