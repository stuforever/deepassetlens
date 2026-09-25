/**
 * 权限重构T4：SuperTokens 会话前端存储（自研登录页配套——不引 supertokens-web-js）。
 * - access_token 入 localStorage，axios 默认头注入（与旧 dev token 通道同型）；
 * - refresh_token 入 localStorage（401 拦截器先刷新重放）；服务端同时写 HttpOnly
 *   cookie 双保险（design §4.4）。
 * - T7 切换后 oidc.ts 退役；本文件为其接替者。
 */
const ACCESS_KEY = "tupu_st_access";
const REFRESH_KEY = "tupu_st_refresh";

export function saveSession(accessToken: string, refreshToken: string): void {
  try {
    localStorage.setItem(ACCESS_KEY, accessToken);
    localStorage.setItem(REFRESH_KEY, refreshToken);
  } catch {
    // 隐私模式等 localStorage 不可用场景——会话仅存于内存/cookie，尽力而为
  }
}

export function getAccessToken(): string {
  try {
    return localStorage.getItem(ACCESS_KEY) || "";
  } catch {
    return "";
  }
}

export function getRefreshToken(): string {
  try {
    return localStorage.getItem(REFRESH_KEY) || "";
  } catch {
    return "";
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  } catch {
    // 同上
  }
}

/** JWT exp 预判（秒级余量 30s）——非安全边界，仅减少无谓 401 往返。 */
export function isAccessTokenFresh(token: string): boolean {
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" && payload.exp * 1000 > Date.now() + 30_000;
  } catch {
    return true; // 非 JWT 形态（理论不会）——交给后端判
  }
}


/** 登出：撤销 ST 会话（服务端 revoke）+ 清本地存储。 */
export async function logoutST(): Promise<void> {
  try {
    const t = getAccessToken();
    if (t) {
      await fetch('/api/v1/auth/session', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${t}` },
      });
    }
  } catch {
    // 尽力而为——本地会话必清
  }
  clearSession();
}

/** 身份层配置（T7 起 ST-only 口径）。 */
export async function fetchAuthConfig(): Promise<{ enableAuth: boolean; provider: string }> {
  const r = await fetch('/api/v1/auth/config');
  if (!r.ok) throw new Error(`auth/config 失败 ${r.status}`);
  const j = await r.json();
  const d = j.data || {};
  return { enableAuth: Boolean(d.enable_auth), provider: d.provider || 'supertokens' };
}

/** 当前用户（/auth/me；ST 通道）。 */
export async function fetchMeST(): Promise<any> {
  const t = getAccessToken();
  const headers: Record<string, string> = t ? { Authorization: `Bearer ${t}` } : {};
  const r = await fetch('/api/v1/auth/me', { headers });
  if (!r.ok) throw new Error(`me 失败 ${r.status}`);
  const j = await r.json();
  return j.data;
}
