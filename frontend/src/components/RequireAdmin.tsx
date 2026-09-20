/**
 * 附件四 A-4：守卫收口——ACL use/manage 分层（与 B 件联调，role 雏形退役）。
 * 后台路由查 manage、功能页查 use（前端守卫管体验不管安全——数据面已被 API 四执法点挡）。
 * 判定走轻量面 GET /api/v1/auth/check（auth=0 匿名=admin 全通——开发链路不破）。
 */
import React, { useContext, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthCtx } from '../auth/AuthGate';
import { getStoredToken } from '../auth/oidc';

const RequireExpert: React.FC<{
  children: React.ReactNode;
  action?: 'use' | 'manage';          // 后台=manage，功能页=use
  expertId?: string;                   // 专家 slug（单专家域路由显式传）
}> = ({ children, action = 'manage', expertId = 'sishu' }) => {
  const { user, authReady } = useContext(AuthCtx);
  const [allowed, setAllowed] = useState<boolean | null>(null);

  // auth=0 快路径：匿名=admin（角色面放行，免一次 check 请求）
  const roles: string[] = ((user as any)?.roles || []) as string[];
  const isAdmin = roles.includes('admin');

  useEffect(() => {
    if (!authReady || isAdmin) { setAllowed(true); return; }
    let alive = true;
    (async () => {
      try {
        // ⑤R R3 权限联调修复：check 请求必须带 Bearer（auth=1 下裸 fetch=401 一律拒）
        const t = getStoredToken();
        const headers: Record<string, string> = {};
        if (t) headers['Authorization'] = `${t.token_type} ${t.access_token}`;
        const r = await fetch(`/api/v1/auth/check?resource_type=expert&resource_id=${encodeURIComponent(expertId)}&action=${action}`, { headers });
        const j = await r.json();
        if (alive) setAllowed(!!j?.data?.allowed);
      } catch {
        if (alive) setAllowed(false);
      }
    })();
    return () => { alive = false; };
  }, [authReady, isAdmin, action, expertId]);

  // A-2 纪律：鉴权未就绪/判定未回不渲染（防闪跳重定向打断 KeepAlive 挂载）
  if (!authReady || allowed === null) return null;
  if (!allowed) return <Navigate to="/" replace />;
  return <>{children}</>;
};

/** 向后兼容别名：既有 admin 后台调用点语义=manage。 */
export const RequireAdmin: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <RequireExpert action="manage" expertId="tutor">{children}</RequireExpert>
);

export default RequireExpert;
