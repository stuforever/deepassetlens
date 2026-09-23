// API configuration and utility functions.
//
// IA批5 lib 补件：1:1 移植自 DeepTutor web/lib/api.ts（ tupu 无 Next 中间件——
// CRA setupProxy.js 已把 /api/* 转发到 28000，apiUrl/wsUrl 保持恒等直通语义不变）。
// backendUrl 的 NEXT_PUBLIC_API_BASE → CRA 侧 REACT_APP_API_BASE（无配置时同样回退直通）。

/**
 * Construct a full API URL from a path.
 *
 * Pass-through: returns the path unchanged. The actual backend URL is
 * determined at request time by CRA `setupProxy.js`, which forwards `/api/*`
 * to the tupu backend (28000).
 *
 * @param path - API path (e.g., '/api/v1/knowledge/list')
 * @returns The same path, unchanged
 */
export function apiUrl(path: string): string {
  return path;
}

/**
 * Construct a direct backend URL (bypasses the dev proxy).
 *
 * Use for long-running endpoints (e.g., batch OCR) where the proxy
 * timeout would kill the request. Falls back to the proxy path when the
 * backend base URL isn't exposed to the browser.
 *
 * @param path - API path (e.g., '/api/v1/mother-questions/batch_recognize_all')
 * @returns Direct backend URL, or the path unchanged if no base is available
 */
export function backendUrl(path: string): string {
  const base = process.env.REACT_APP_API_BASE || "";
  if (base && /^https?:\/\//.test(base)) return base + path;
  return path;
}

/**
 * Construct a WebSocket URL from a path.
 *
 * Pass-through: returns the path unchanged. `setupProxy.js`（ws:true）转发
 * `/api/*` 升级请求到后端，scheme 由页面协议推导。
 *
 * @param path - WebSocket path (e.g., '/api/v1/solve')
 * @returns The same path, unchanged
 */
export function wsUrl(path: string): string {
  return path;
}

/**
 * Parse a "DEEPTUTOR_AUTH_ENABLED"-style flag at runtime.
 *
 * Used by both `apiFetch` (frontend) and the proxy layer (auth redirect) to
 * decide whether to gate requests. Evaluated with a runtime regex so the
 * value can be set at runtime (no build-time inlining).
 */
export function parseAuthEnabled(raw: string | undefined): boolean {
  return /^(1|true|yes|on)$/i.test((raw ?? "").trim());
}

// Whether auth is enabled, learned at runtime — NOT from a build-time env var.
// `fetchAuthStatus()` in `lib/auth.ts` calls `setRuntimeAuthEnabled()` once the
// backend reports the real state. Until then it defaults to `false`, so a
// stray 401 in the default auth-disabled deployment never bounces the user to
// /login. This flag only drives the client's in-session 401 → /login redirect.
let runtimeAuthEnabled = false;

/** Record the backend-reported auth state for `apiFetch`'s 401 redirect gate. */
export function setRuntimeAuthEnabled(enabled: boolean): void {
  runtimeAuthEnabled = enabled;
}

/** R5批④：读当前运行时认证态——裸 fetch 调用方的 401 门控与 apiFetch 同源对齐。 */
export function isRuntimeAuthEnabled(): boolean {
  return runtimeAuthEnabled;
}

/**
 * Authenticated fetch wrapper. Behaves identically to `fetch` but automatically
 * redirects to /login when the backend returns 401 (expired / invalid token).
 *
 * Pass `skipAuthRedirect: true` for endpoints where a 401 is an expected,
 * recoverable response that the caller wants to handle inline — most notably
 * the login/register endpoints, where 401 means "wrong credentials" and must
 * surface as a form error rather than reload the page.
 */
export async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit & { skipAuthRedirect?: boolean },
): Promise<Response> {
  const { skipAuthRedirect, ...fetchInit } = init ?? {};
  const res = await fetch(input, { credentials: "include", ...fetchInit });

  if (
    res.status === 401 &&
    runtimeAuthEnabled &&
    !skipAuthRedirect &&
    typeof window !== "undefined"
  ) {
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `/login?next=${next}`;
    return new Promise(() => {});
  }

  return res;
}
