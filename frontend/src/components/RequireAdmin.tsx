/**
 * 附件四 A-1：守卫雏形（role-based）——非 admin 重定向首页。
 * A-4 与 B 件 ACL 联调后升级 use/manage 分层（本批仅占位语义）。
 */
import React, { useContext } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthCtx } from '../auth/AuthGate';

const RequireAdmin: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, authReady } = useContext(AuthCtx);
  // 附件四 A-2：鉴权未就绪不判定（防 user 异步加载中闪跳重定向打断 KeepAlive 挂载）
  if (!authReady) return null;
  const roles: string[] = ((user as any)?.roles || []) as string[];
  if (!roles.includes('admin')) return <Navigate to="/" replace />;
  return <>{children}</>;
};

export default RequireAdmin;
