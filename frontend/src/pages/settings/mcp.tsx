/**
 * 批5 5.3：/settings/mcp（源 (utility)/settings/mcp/page.tsx 逐字移植——重定向页）。
 * tupu 登记注释：/space/mcp（学习空间 MCP 管理）tupu 尚未落位——跳转后仅 URL 变更、
 * 页签不切换属预期，待后续批补位后自愈。
 * KeepAlive 页签架构规避口径：useEffect 单次触发 + Spinner 兜底（挂载即跳、不留死页）。
 */
import { useEffect } from 'react';
import { Spin } from 'antd';
import { useNavigate } from 'react-router-dom';

// MCP moved out of Settings: servers are now per-account, managed in the Learning
// Space store at /space/mcp — which also hosts the deployment-wide registry this
// page used to be, behind an admin check. Kept as a redirect so shipped links and
// bookmarks still land somewhere real.
export default function McpSettingsRedirect() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/space/mcp', { replace: true });
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
      <span>正在前往 MCP 管理…</span>
    </div>
  );
}
