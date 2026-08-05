/**
 * OIDC PKCE 登录 / Token 管理 / 注销
 *
 * 流程：
 *  1. 未登录访问任何页面 → AuthGate 检测 localStorage 无 token → 生成 code_verifier+state → 跳 Authentik /authorize
 *  2. Authentik 登录后回调 /auth/callback?code=xxx&state=yyy
 *  3. AuthGate 用 code 换 token → 写 localStorage → 路由到原页面
 *  4. axios 拦截器自动塞 Bearer
 *  5. 401 → 清 token → 重新走 1
 */

const STORAGE_KEY = 'tupu.oidc';
const VERIFIER_KEY = 'tupu.oidc.code_verifier';
const STATE_KEY = 'tupu.oidc.state';
const RETURN_KEY = 'tupu.oidc.return_to';

export interface OidcConfig {
  enable_auth: boolean;
  issuer: string;
  client_id: string;
  redirect_uri: string;
  authorization_endpoint: string;
  token_endpoint: string;
  end_session_endpoint: string;
  scopes: string[];
}

export interface TokenBundle {
  access_token: string;
  id_token?: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  obtained_at: number;
  scope?: string;
}

let _config: OidcConfig | null = null;

export async function fetchAuthConfig(): Promise<OidcConfig> {
  if (_config) return _config;
  const r = await fetch('/api/v1/auth/config');
  const json = await r.json();
  _config = json.data as OidcConfig;
  return _config;
}

export function isAuthEnabled(): boolean {
  return _config?.enable_auth === true;
}

export function getStoredToken(): TokenBundle | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as TokenBundle;
  } catch {
    return null;
  }
}

export function isTokenValid(t: TokenBundle | null): boolean {
  if (!t) return false;
  const now = Math.floor(Date.now() / 1000);
  return t.obtained_at + t.expires_in - 30 > now;
}

export function clearToken(): void {
  localStorage.removeItem(STORAGE_KEY);
}

// ----- PKCE helpers -----

function _b64url(buf: ArrayBuffer): string {
  let s = '';
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.byteLength; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function _sha256(text: string): Promise<ArrayBuffer> {
  const enc = new TextEncoder().encode(text);
  return await crypto.subtle.digest('SHA-256', enc);
}

function _randomString(len = 64): string {
  const arr = new Uint8Array(len);
  crypto.getRandomValues(arr);
  let s = '';
  for (let i = 0; i < arr.length; i++) {
    s += (arr[i] % 36).toString(36);
  }
  return s;
}

export async function startLogin(returnTo: string = window.location.pathname + window.location.search): Promise<void> {
  const cfg = await fetchAuthConfig();
  const verifier = _randomString(64);
  const challenge = _b64url(await _sha256(verifier));
  const state = _randomString(32);

  sessionStorage.setItem(VERIFIER_KEY, verifier);
  sessionStorage.setItem(STATE_KEY, state);
  sessionStorage.setItem(RETURN_KEY, returnTo);

  const url = new URL(cfg.authorization_endpoint);
  url.searchParams.set('client_id', cfg.client_id);
  url.searchParams.set('redirect_uri', cfg.redirect_uri);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('scope', cfg.scopes.join(' '));
  url.searchParams.set('state', state);
  url.searchParams.set('code_challenge', challenge);
  url.searchParams.set('code_challenge_method', 'S256');

  window.location.href = url.toString();
}

export async function exchangeCode(code: string, state: string): Promise<TokenBundle> {
  const cfg = await fetchAuthConfig();
  const expectedState = sessionStorage.getItem(STATE_KEY);
  if (!expectedState || expectedState !== state) {
    throw new Error('OIDC state mismatch');
  }
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!verifier) throw new Error('OIDC code_verifier missing');

  const body = new URLSearchParams();
  body.set('grant_type', 'authorization_code');
  body.set('code', code);
  body.set('redirect_uri', cfg.redirect_uri);
  body.set('client_id', cfg.client_id);
  body.set('code_verifier', verifier);

  const r = await fetch(cfg.token_endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`Token 交换失败 ${r.status}: ${txt}`);
  }
  const json = await r.json();
  const bundle: TokenBundle = {
    access_token: json.access_token,
    id_token: json.id_token,
    refresh_token: json.refresh_token,
    token_type: json.token_type || 'Bearer',
    expires_in: json.expires_in || 3600,
    obtained_at: Math.floor(Date.now() / 1000),
    scope: json.scope,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(bundle));

  // 清理 PKCE 工作内存
  sessionStorage.removeItem(VERIFIER_KEY);
  sessionStorage.removeItem(STATE_KEY);
  return bundle;
}

export function popReturnTo(): string {
  const v = sessionStorage.getItem(RETURN_KEY) || '/';
  sessionStorage.removeItem(RETURN_KEY);
  return v;
}

export async function logout(): Promise<void> {
  const cfg = await fetchAuthConfig().catch(() => null);
  const t = getStoredToken();
  clearToken();
  if (cfg && t?.id_token) {
    const url = new URL(cfg.end_session_endpoint);
    url.searchParams.set('id_token_hint', t.id_token);
    url.searchParams.set('post_logout_redirect_uri', window.location.origin + '/');
    window.location.href = url.toString();
    return;
  }
  window.location.href = '/';
}

// ----- userinfo（从 backend /me） -----

export async function fetchMe(): Promise<any> {
  const t = getStoredToken();
  const headers: Record<string, string> = {};
  if (t) headers['Authorization'] = `${t.token_type} ${t.access_token}`;
  const r = await fetch('/api/v1/auth/me', { headers });
  if (!r.ok) throw new Error(`me 失败 ${r.status}`);
  const json = await r.json();
  return json.data;
}
