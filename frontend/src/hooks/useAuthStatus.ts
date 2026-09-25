/**
 * 运行时认证状态 hook——权限重构T6批3 起 vendor /api/v1/auth/status 面退役，
 * 数据源改平台 /api/v1/auth/me 口径：
 * - auth=0（匿名 admin，开发态语义）：me 200 + is_anonymous → enabled=false
 *   （UI 视作「未启用认证」，行为同旧 status enabled=false 全通口径）；
 * - auth=1 未登录：me 401 → enabled=true, authenticated=false；
 * - auth=1 已登录：me 200 → authenticated + isAdmin=roles 含 admin。
 * in-flight 共享（同页多消费者只发一次请求）。
 */
import { useEffect, useState } from "react";
import { getAccessToken, getRefreshToken } from "../auth/st";
import { tryRefresh } from "../services/http";

export interface AuthStatusState {
  /** 请求失败（网络/5xx）置 true——与「认证未开启」可区分 */
  failed?: boolean;
  /** Whether auth is enabled on the backend. */
  enabled: boolean;
  /** Whether the current session is authenticated. */
  authenticated: boolean;
  /** Whether the authenticated user is an admin. */
  isAdmin: boolean;
  /** True until the first status fetch resolves. */
  loading: boolean;
}

const INITIAL: AuthStatusState = {
  enabled: false,
  authenticated: false,
  isAdmin: false,
  loading: true,
};

// Several components mount this hook at once. Share a single in-flight request
// so a page load makes one /api/v1/auth/me call instead of one per consumer,
// and clear it once settled so a later mount fetches fresh.
let inflight: Promise<AuthStatusState> | null = null;

async function fetchMeOnce(): Promise<Response> {
  const t = getAccessToken();
  const headers: Record<string, string> = t ? { Authorization: `Bearer ${t}` } : {};
  return fetch("/api/v1/auth/me", { headers });
}

function loadAuthStatus(): Promise<AuthStatusState> {
  if (!inflight) {
    // TS4.9 无自引用收窄豁免：先落局部 const 再赋 inflight（语义等价）。
    const p = (async () => {
      let res = await fetchMeOnce();
      if (res.status === 401 && getRefreshToken()) {
        const ok = await tryRefresh();
        if (ok) res = await fetchMeOnce();
      }
      if (!res.ok) {
        // 401/其他 → 认证开启但未通过（网络 5xx 与 401 此处同归未认证态）
        return {
          enabled: true,
          authenticated: false,
          isAdmin: false,
          loading: false,
          failed: false,
        } satisfies AuthStatusState;
      }
      const j = await res.json();
      const u = j?.data || {};
      const roles: string[] = Array.isArray(u.roles) ? u.roles : [];
      const isAdmin = roles.includes("admin");
      return {
        enabled: !u.is_anonymous,
        authenticated: true,
        isAdmin,
        loading: false,
        failed: false,
      } satisfies AuthStatusState;
    })()
      .catch(() => ({
        // 失败态不再折叠成「未开启认证」——failed=true 供 UI 区分
        enabled: false,
        authenticated: false,
        isAdmin: false,
        loading: false,
        failed: true,
      }) satisfies AuthStatusState)
      .finally(() => {
        inflight = null;
      });
    inflight = p;
    return p;
  }
  return inflight;
}

export function useAuthStatus(): AuthStatusState {
  const [state, setState] = useState<AuthStatusState>(INITIAL);

  useEffect(() => {
    let alive = true;
    loadAuthStatus().then((next) => {
      if (alive) setState(next);
    });
    return () => {
      alive = false;
    };
  }, []);

  return state;
}
